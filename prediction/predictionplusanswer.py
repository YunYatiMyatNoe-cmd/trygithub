import boto3
import json
import os
from supabase import create_client, Client
from datetime import datetime, timedelta

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
        print("No predictiondata found.")
        return None
    except Exception as e:
        print(f"Error fetching max-min data: {str(e)}")
        return None

def get_answer_from_claude(question, suspicious_data, start_last_times, max_min_data, prediction_data):
    try:
        # Format suspicious data
        context_suspicious = "\n不審者:\n" + "\n".join([f"• Time: {entry['event_time']} - Number of People: {entry['num']}" for entry in suspicious_data])
        print(context_suspicious)

        # Format project times
        context_project = "\n入り帰りデータ:\n" + "\n".join([f"•入り時間: {entry['start_time']}, 帰り時間: {entry['last_time']}" for entry in start_last_times])
        print(context_suspicious)

        # Format max-min data
        context_maxmin = "\n:\n" + "\n".join([f"• 一番多い人: {entry.get('max_num', 'N/A')} at {entry.get('max_time', 'N/A')}\n"
                                             f"• 一番少ない人: {entry.get('min_num', 'N/A')} at {entry.get('min_time', 'N/A')}" for entry in max_min_data])
        
        context_prediction_data = "\n予想データ:\n" + "\n".join([f"• Time: {entry['time']} - Number of People: {entry['num']} - Reason: {entry['reasons']}" for entry in prediction_data])

        print(context_maxmin)

        prompt = f"""あなたは建物の利用状況を分析するアシスタントです。以下のデータを基に、ユーザーの質問に正確に答えてください。

利用可能なデータ:
{context_suspicious}
{context_project}
{context_maxmin}
{context_prediction_data}

回答の指針:
1. 時刻は常に「YYYY/MM/DD (曜日) HH:MM」形式で表示し、ISO 8601形式（例: yyyy-mm-ddThh:mm:ss+00:00）は絶対に使用しない。
2. 人数を示す際は必ず「XX人」という形式で表示
3. 入り帰り時間帯について触れる際は、入り・帰り時刻を含める
4. 複数の時間帯を比較する場合は、わかりやすく整理して表示
5. データが存在しない場合は、その旨を明確に伝える
6.「XX月XX日の人数が最も多かった時間は、YYYY/MM/DD (曜日) HH:MMでXX人でした。」
7.「XX月XX日の人数が最も少なかった時間は、YYYY/MM/DD (曜日) HH:MMでXX人でした。」
8. 予想データを聞くとき時間、人数、理由をちゃんと答える。

特定の応答要件:
- 入り帰り時間帯に関する質問: 入り帰り時間帯から具体的な開始・終了時刻を参照
- 統計的な質問: 集計データを使用して最小・最大値を正確に提供
- 常に専門的で分析的な口調を維持
- 必要に応じて回答に関連する文脈を提供

以下の質問に基づいて回答してください: {question}

Please provide a clear, concise answer based on the available data:"""

        # Prepare the messages for Claude API
        messages = [{"role": "user", "content": prompt}]
        input_data = {
            "messages": messages,
            "max_tokens": 300,
            "anthropic_version": "bedrock-2023-05-31"
        }

        # Call Claude API
        response = bedrock_client.invoke_model(
            modelId="anthropic.claude-3-sonnet-20240229-v1:0",
            body=json.dumps(input_data),
            contentType='application/json'
        )

        # Process and return the response
        response_body = json.loads(response['body'].read().decode('utf-8'))
        return response_body.get('content', "Sorry, I couldn't process your question.")
    except Exception as e:
        print(f"Error querying Bedrock: {str(e)}")
        return "Sorry, there was an error processing your question."

def lambda_handler(event, context):
    # Handle preflight CORS request (OPTIONS method)
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
    
    prediction_data = fetch_all_predictiondata()
    if not prediction_data:
        return {
            'statusCode': 404,
            'headers': CORS_HEADERS,
            'body': json.dumps({'message': 'No prediction　data found.'})
        }

    # Step 4: Get answer from Claude
    answer = get_answer_from_claude(user_question, suspicious_data, project_times, max_min, prediction_data)

    # Step 5: Return the answer to the user
    return {
        'statusCode': 200,
        'headers': CORS_HEADERS,
        'body': json.dumps({
            'question': user_question,
            'response': answer
        })
    }
