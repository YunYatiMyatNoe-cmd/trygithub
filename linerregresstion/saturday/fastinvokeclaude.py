import os
import json
import boto3
import requests
from supabase import create_client
from PyPDF2 import PdfReader
import concurrent.futures
import functools

# Global clients to reduce initialization overhead
BEDROCK_CLIENT = boto3.client('bedrock-runtime', region_name='us-east-1')
SUPABASE_CLIENT = create_client(
    os.getenv("SUPABASE_URL", ""),
    os.getenv("SUPABASE_KEY", "")
)

# Cached CORS headers
CORS_HEADERS = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type,Authorization',
    'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
}

def memoize(func):
    """Simple memoization decorator to cache expensive function calls."""
    cache = {}
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        key = str(args) + str(kwargs)
        if key not in cache:
            cache[key] = func(*args, **kwargs)
        return cache[key]
    return wrapper

@memoize
def download_and_extract_pdf(url):
    """
    Download and extract PDF text with memoization.
    
    Args:
        url (str): PDF URL to download
    
    Returns:
        str: Extracted PDF text
    """
    try:
        # Download PDF
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        
        # Save temporarily
        temp_path = f"/tmp/{hash(url)}.pdf"
        with open(temp_path, 'wb') as f:
            f.write(response.content)
        
        # Extract text
        with open(temp_path, 'rb') as file:
            reader = PdfReader(file)
            return " ".join(page.extract_text() for page in reader.pages)
    
    except Exception:
        return ""

def fast_parallel_fetch(functions):
    """
    Fetch multiple Supabase functions in parallel with minimal overhead.
    
    Args:
        functions (dict): Mapping of keys to Supabase RPC function names
    
    Returns:
        dict: Fetched data
    """
    def fetch_single(func_name):
        try:
            return SUPABASE_CLIENT.rpc(func_name).execute().data
        except Exception:
            return None
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(functions), 10)) as executor:
        futures = {
            key: executor.submit(fetch_single, func_name)
            for key, func_name in functions.items()
        }
        return {key: future.result() for key, future in futures.items()}

def generate_claude_prompt(question, data, pdf_texts):
    """
    Generate an ultra-compact prompt for Claude.
    
    Args:
        question (str): User's question
        data (dict): Fetched data
        pdf_texts (list): PDF texts
    
    Returns:
        str: Compact prompt
    """
    context = "\n".join([
        f"• {key}: {json.dumps(value[:5]) if isinstance(value, list) else value}"
        for key, value in data.items() if value
    ])
    
    pdf_context = "\n".join(pdf_texts) if pdf_texts else ""
    
    return f"""建物利用状況分析:
{context}
PDF情報: {pdf_context[:500]}

質問: {question}
簡潔かつ正確に回答してください。"""

def fast_claude_query(prompt):
    """
    Rapidly query Claude with minimal overhead.
    
    Args:
        prompt (str): Prepared prompt
    
    Returns:
        str: Claude's response
    """
    try:
        response = BEDROCK_CLIENT.invoke_model(
            modelId="anthropic.claude-3-sonnet-20240229-v1:0",
            body=json.dumps({
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 300,
                "temperature": 0.7,
                "anthropic_version": "bedrock-2023-05-31"
            }),
            contentType='application/json'
        )
        
        body = json.loads(response['body'].read().decode('utf-8'))
        return body.get('content', "処理できませんでした")
    
    except Exception:
        return "エラーが発生しました"

def lambda_handler(event, context):
    """
    Ultra-optimized Lambda handler with minimal overhead.
    """
    # Fast CORS handling
    if event.get('httpMethod') == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': CORS_HEADERS,
            'body': json.dumps({'message': 'OK'})
        }

    # Rapid input parsing
    try:
        body = json.loads(event.get('body', '{}'))
        question = body.get('question', '').strip()
        
        if not question:
            raise ValueError("No question")
    
    except (json.JSONDecodeError, ValueError):
        return {
            'statusCode': 400,
            'headers': CORS_HEADERS,
            'body': json.dumps({'error': 'Invalid request'})
        }

    # PDF URLs (consider making these configurable)
    pdf_urls = [
        "https://xsjzbkgsqtvlzyqeqbmx.supabase.co/storage/v1/object/public/ForLidar/Knowledge%20base%20/minohcSchdeule.pdf",
        "https://xsjzbkgsqtvlzyqeqbmx.supabase.co/storage/v1/object/public/ForLidar/Knowledge%20base%20/solvecrowd.pdf"
    ]

    # Parallel PDF text extraction
    with concurrent.futures.ThreadPoolExecutor() as executor:
        pdf_texts = list(executor.map(download_and_extract_pdf, pdf_urls))

    # Parallel Supabase data fetch
    data_functions = {
        'current_data': 'get_current_time_data',
        'last_week_data': 'get_last_week_data',
        'suspicious_data': 'get_find_suspicious',
        'project_times': 'get_start_time_and_last_time',
        'zone_data': 'get_thirdfloor_zones'
    }
    
    data = fast_parallel_fetch(data_functions)

    # Generate and query Claude
    prompt = generate_claude_prompt(question, data, pdf_texts)
    answer = fast_claude_query(prompt)

    return {
        'statusCode': 200,
        'headers': CORS_HEADERS,
        'body': json.dumps({
            'question': question,
            'response': answer
        })
    }