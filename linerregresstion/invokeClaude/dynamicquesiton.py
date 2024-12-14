import boto3
import json
import os
from supabase import create_client, Client

# CORS Headers
CORS_HEADERS = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type,Authorization',
    'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
}

# Initialize Supabase client
SUPABASE_URL = "https://xsjzbkgsqtvlzyqeqbmx.supabase.co"
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_KEY:
    raise ValueError("SUPABASE_KEY environment variable is not set.")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Initialize the AWS Bedrock client for Claude 3
bedrock_client = boto3.client('bedrock-runtime', region_name='us-east-1')

def fetch_current_data():
    try:
        data = supabase.rpc('get_current_time_data').execute()
        if data.data:
            return data.data
        print("No current data found.")
        return None
    except Exception as e:
        print(f"Error fetching current data: {str(e)}")
        return None

# Data Fetching Functions
def fetch_suspicious_data():
    try:
        data = supabase.rpc('get_find_suspicious').execute()
        if data.data:
            return data.data
        print("No suspicious data found.")
        return None
    except Exception as e:
        print(f"Error fetching suspicious data: {str(e)}")
        return None

def fetch_start_last_times():
    try:
        data = supabase.rpc('get_start_time_and_last_time').execute()
        if data.data:
            return data.data
        print("No project time data found.")
        return None
    except Exception as e:
        print(f"Error fetching project times: {str(e)}")
        return None

def fetch_get_max_min_data():
    try:
        data = supabase.rpc('get_max_min_data').execute()
        if data.data:
            return data.data
        print("No max-min data found.")
        return None
    except Exception as e:
        print(f"Error fetching max-min data: {str(e)}")
        return None

def fetch_all_predictiondata():
    try:
        data = supabase.rpc('get_all_predictiondata').execute()
        if data.data:
            return data.data
        print("No prediction data found.")
        return None
    except Exception as e:
        print(f"Error fetching prediction data: {str(e)}")
        return None

# Function to get the answer from Claude
def get_answer_from_claude(user_question, suspicious_data, project_times, max_min_data, prediction_data, curent_data):
    try:
        # Update the prompt to ask Claude to decide which data to use
        prompt = f"""あなたは建物の利用状況を分析するアシスタントです。以下のデータを基に、ユーザーの質問に正確に答えてください。

利用可能なデータ:
- 不審者データ (suspicious data): {json.dumps(suspicious_data)}
- 入り帰りデータ (project times): {json.dumps(project_times)}
- 最大最小データ (max-min data): {json.dumps(max_min_data)}
- 予測データ (prediction data): {json.dumps(prediction_data)}
- 現在データ (curent_data): {json.dumps(curent_data)}

回答の指針:
注意火付けは日本の火付けです。
1. 時刻は常に「YYYY/MM/DD HH:MM」形式で表示し、ISO 8601形式（例: yyyy-mm-ddThh:mm:ss+00:00）は絶対に使用しない。曜日は日本のカレンダーから見てください。

ユーザーの質問: "{user_question}"

あなたのタスクは、ユーザーの質問に最も適したデータを選び、そのデータに基づいて質問に回答することです。
質問に対して適切なデータを選び、回答を提供してください。もし質問に対してデータが不足している場合は、その旨を明記してください。"""

        # Sending the data and question to Claude
        messages = [{"role": "user", "content": prompt}]
        input_data = {
            "messages": messages,
            "max_tokens": 500,
            "anthropic_version": "bedrock-2023-05-31"
        }

        response = bedrock_client.invoke_model(
            modelId="anthropic.claude-3-sonnet-20240229-v1:0",
            body=json.dumps(input_data),
            contentType='application/json'
        )

        response_body = json.loads(response['body'].read().decode('utf-8'))
        return response_body.get('content', "Sorry, I couldn't process your question.")
    except Exception as e:
        print(f"Error querying Bedrock: {str(e)}")
        return "Sorry, there was an error processing your question."

# Lambda Handler Function
def lambda_handler(event, context):
    http_method = event.get('httpMethod', None)

    if http_method == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': CORS_HEADERS,
            'body': json.dumps({'message': 'CORS Preflight Successful'})
        }

    # Parse the body of the request
    body = event.get('body', '{}')
    try:
        body = json.loads(body)
    except json.JSONDecodeError:
        return {
            'statusCode': 400,
            'headers': CORS_HEADERS,
            'body': json.dumps({'error': 'Invalid JSON in request body.'})
        }

    user_question = body.get('question', '').strip()
    if not user_question:
        return {
            'statusCode': 400,
            'headers': CORS_HEADERS,
            'body': json.dumps({'message': 'No question provided.'})
        }

    # Step 1: Fetch suspicious data
    suspicious_data = fetch_suspicious_data()
    if not suspicious_data:
        return {
            'statusCode': 404,
            'headers': CORS_HEADERS,
            'body': json.dumps({'message': 'No suspicious data found.'})
        }

    # Step 2: Fetch project times
    project_times = fetch_start_last_times()
    if not project_times:
        return {
            'statusCode': 404,
            'headers': CORS_HEADERS,
            'body': json.dumps({'message': 'No project times data found.'})
        }

    # Step 3: Fetch max-min data
    max_min = fetch_get_max_min_data()
    if not max_min:
        return {
            'statusCode': 404,
            'headers': CORS_HEADERS,
            'body': json.dumps({'message': 'No max-min data found.'})
        }
    
    # Step 4: Fetch prediction data
    prediction_data = fetch_all_predictiondata()
    if not prediction_data:
        return {
            'statusCode': 404,
            'headers': CORS_HEADERS,
            'body': json.dumps({'message': 'No prediction data found.'})
        }
    
    curent_data = fetch_current_data()
    if not curent_data:
        return {
            'statusCode': 404,
            'headers': CORS_HEADERS,
            'body': json.dumps({'message': 'No curent data found.'})
        }

    # Step 5: Get answer from Claude
    answer = get_answer_from_claude(user_question, suspicious_data, project_times, max_min, prediction_data, curent_data)

    # Step 6: Return the answer to the user
    return {
        'statusCode': 200,
        'headers': CORS_HEADERS,
        'body': json.dumps({
            'question': user_question,
            'response': answer
        })
    }
