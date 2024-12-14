import os
import json
import logging
from typing import Dict, Any, Optional
import requests
import boto3
import concurrent.futures
from supabase import create_client, Client
from PyPDF2 import PdfReader

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ConfigurationError(Exception):
    """Custom exception for configuration-related errors."""
    pass

class PDFProcessor:
    """Handles PDF download and text extraction."""
    @staticmethod
    def download_pdf(url: str, path: str) -> bool:
        """
        Download PDF from given URL and save to specified path.
        
        Args:
            url (str): URL of the PDF
            path (str): Local path to save the PDF
        
        Returns:
            bool: True if download successful, False otherwise
        """
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            with open(path, 'wb') as f:
                f.write(response.content)
            
            logger.info(f"Successfully downloaded PDF to {path}")
            return True
        except requests.RequestException as e:
            logger.error(f"PDF download error: {e}")
            return False
    
    @staticmethod
    def extract_text_from_pdf(pdf_path: str) -> str:
        """
        Extract text from a PDF file.
        
        Args:
            pdf_path (str): Path to the PDF file
        
        Returns:
            str: Extracted text from the PDF
        """
        try:
            with open(pdf_path, 'rb') as file:
                reader = PdfReader(file)
                return " ".join(page.extract_text() for page in reader.pages)
        except Exception as e:
            logger.error(f"PDF text extraction error: {e}")
            return ""

class SupabaseDataFetcher:
    """Manages data retrieval from Supabase."""
    def __init__(self, url: str, key: str):
        """
        Initialize Supabase client.
        
        Args:
            url (str): Supabase project URL
            key (str): Supabase API key
        """
        try:
            self.client: Client = create_client(url, key)
        except Exception as e:
            logger.error(f"Supabase client initialization error: {e}")
            raise ConfigurationError("Failed to initialize Supabase client")
    
    def fetch_data(self, function_name: str, params: Optional[Dict[str, Any]] = None) -> Optional[list]:
        """
        Fetch data using Supabase RPC.
        
        Args:
            function_name (str): Name of the stored procedure
            params (dict, optional): Parameters for the procedure
        
        Returns:
            list or None: Fetched data or None if error
        """
        try:
            result = self.client.rpc(function_name, params).execute()
            return result.data if result.data else None
        except Exception as e:
            logger.error(f"Data fetch error for {function_name}: {e}")
            return None

class BedrockAIAssistant:
    """Manages interactions with Claude 3 via AWS Bedrock."""
    def __init__(self, region_name: str = 'us-east-1'):
        """
        Initialize Bedrock client.
        
        Args:
            region_name (str): AWS region
        """
        self.client = boto3.client('bedrock-runtime', region_name=region_name)
    
    def generate_answer(self, question: str, context_data: Dict[str, Any]) -> str:
        """
        Generate an answer using Claude 3.
        
        Args:
            question (str): User's question
            context_data (dict): Contextual data for answer generation
        
        Returns:
            str: AI-generated answer
        """
        try:
            # Prepare context string
            context = "\n".join([
                f"• {key.replace('_', ' ').title()}:\n" + 
                "\n".join(f"  - {item}" for item in self._format_context_items(context_data.get(key, [])))
                for key in context_data
            ])

            prompt = f"""
あなたは建物の利用状況を分析するAIアシスタントです。
提供されたデータと背景情報を元に、以下の質問に正確かつ詳細に答えてください。

質問: {question}

利用可能なデータ:
{context}
"""
            
            input_data = {
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 500,
                "temperature": 0.7,
                "anthropic_version": "bedrock-2023-05-31"
            }

            response = self.client.invoke_model(
                modelId="anthropic.claude-3-sonnet-20240229-v1:0",
                body=json.dumps(input_data),
                contentType='application/json'
            )

            response_body = json.loads(response['body'].read().decode('utf-8'))
            return response_body.get('content', "質問を処理できませんでした。")
        
        except Exception as e:
            logger.error(f"Bedrock AI query error: {e}")
            return "申し訳ありません。質問の処理中にエラーが発生しました。"
    
    def _format_context_items(self, items: list) -> list:
        """
        Format context items for prompt generation.
        
        Args:
            items (list): List of context items
        
        Returns:
            list: Formatted context items
        """
        if not items:
            return ["利用可能なデータがありません"]
        
        return [
            f"{item.get('time', 'Unknown Time')} - {', '.join(f'{k}: {v}' for k, v in item.items() if k != 'time')}" 
            for item in items
        ]

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    AWS Lambda function handler for processing questions.
    
    Args:
        event (dict): Lambda event object
        context (object): Lambda context object
    
    Returns:
        dict: API Gateway response
    """
    # CORS Headers
    CORS_HEADERS = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type,Authorization',
        'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
    }

    # Handle OPTIONS request for CORS
    if event.get('httpMethod') == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': CORS_HEADERS,
            'body': json.dumps({'message': 'CORS Preflight Successful'})
        }

    # Validate request
    try:
        body = json.loads(event.get('body', '{}'))
        user_question = body.get('question', '').strip()
        
        if not user_question:
            raise ValueError("No question provided")
    
    except (json.JSONDecodeError, ValueError) as e:
        logger.error(f"Request validation error: {e}")
        return {
            'statusCode': 400,
            'headers': CORS_HEADERS,
            'body': json.dumps({'error': 'Invalid request'})
        }

    # Configuration setup
    try:
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_KEY')
        
        if not all([supabase_url, supabase_key]):
            raise ConfigurationError("Missing Supabase configuration")
    
    except ConfigurationError as e:
        logger.error(str(e))
        return {
            'statusCode': 500,
            'headers': CORS_HEADERS,
            'body': json.dumps({'error': 'Server configuration error'})
        }

    # Initialize services
    supabase_fetcher = SupabaseDataFetcher(supabase_url, supabase_key)
    ai_assistant = BedrockAIAssistant()

    # Fetch data concurrently
    data_functions = {
        'current_data': lambda: supabase_fetcher.fetch_data('get_current_time_data'),
        'last_week_data': lambda: supabase_fetcher.fetch_data('get_last_week_data'),
        'suspicious_data': lambda: supabase_fetcher.fetch_data('get_find_suspicious'),
        # Add other data fetch functions here
    }

    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = {key: executor.submit(func) for key, func in data_functions.items()}
        data = {key: future.result() for key, future in futures.items()}

    # Generate AI response
    answer = ai_assistant.generate_answer(user_question, data)

    return {
        'statusCode': 200,
        'headers': CORS_HEADERS,
        'body': json.dumps({
            'question': user_question,
            'response': answer
        })
    }