import boto3
import json
import os
import re
from supabase import create_client, Client
from datetime import datetime, timedelta

CORS_HEADERS = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type,Authorization',
    'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
}

SUPABASE_URL = "https://xsjzbkgsqtvlzyqeqbmx.supabase.co"
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_KEY:
    raise ValueError("SUPABASE_KEY environment variable is not set.")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

bedrock_client = boto3.client('bedrock-runtime', region_name='us-east-1')

#for invoke claude
def invoke_prediction_lambda(user_question):

    print("String"+user_question)
    payload = {
        "user_question": user_question  
    }
    target_lambda_arn = 'arn:aws:lambda:ap-northeast-1:284283223746:function:prediction'
    lambda_client = boto3.client('lambda', region_name='ap-northeast-1')

    try:
        response = lambda_client.invoke(
            FunctionName=target_lambda_arn,        
            InvocationType='RequestResponse',      
            Payload=json.dumps(payload)           
        )
       
        response_payload = json.loads(response['Payload'].read().decode('utf-8'))
        body = json.loads(response_payload['body'])
        prediction_text = body['response'][0]['text']
        
        # print("Response from Target Lambda:", prediction_text)
        return prediction_text

    except Exception as e:
        print(f"Error invoking target Lambda: {str(e)}")
        return {"error": "Failed to invoke the Lambda function."}

 
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
    
# def fetch_all_predictiondata():
#     try:
#         data = supabase.rpc('get_all_predictiondata').execute()
#         if data.data:
#             return data.data
#         print("No prediction data found.")
#         return None
#     except Exception as e:
#         print(f"Error fetching prediction data: {str(e)}")
#         return None


# search relevant data
def extract_relevant_data(user_question):
    if re.search(r'(現在時間|今)', user_question):
        return "current_data"
    if re.search(r'(不審者|suspicious)', user_question):
        return "suspicious"
    elif re.search(r'(入り|帰り)', user_question):
        return "project_times"
    elif re.search(r'(最大|最小|多い|少ない|一番多い|一番少ない)', user_question):
        return "max_min"
    elif re.search(r'(予測|prediction)', user_question):
        return "prediction"
    else:
        return "all"  

# Function to get the answer from Claude
def get_answer_from_claude(user_question, suspicious_data, project_times, max_min_data,  current_data, prediction_data):
    try:
        relevant_data_type = extract_relevant_data(user_question)
        if relevant_data_type == "suspicious":
            relevant_data = suspicious_data
        elif relevant_data_type == "current_data":
            relevant_data = current_data
        elif relevant_data_type == "project_times":
            relevant_data = project_times
        elif relevant_data_type == "max_min":
            relevant_data = max_min_data
        elif relevant_data_type == "prediction":
            relevant_data = prediction_data
        else:
            relevant_data = {
                "suspicious": suspicious_data,
                "project_times": project_times,
                "max_min": max_min_data,
                "current_data": current_data,
                "prediction": prediction_data
            }

        print("Formatted data for Claude:", relevant_data)
        formatted_data = format_data_for_claude(relevant_data, relevant_data_type)
        print("Result:", formatted_data)

        prompt = f"""あなたは建物の利用状況を分析するアシスタントです。以下のデータを基に、ユーザーの質問に正確に答えてください。

利用可能なデータ:
{formatted_data}

回答の指針:
注意火付けは日本の火付けです。
1. 時刻は常に「YYYY/MM/DD HH:MM」形式で表示し、ISO 8601形式（例: yyyy-mm-ddThh:mm:ss+00:00）は絶対に使用しない。曜日は日本のカレンダーから見てください。


以下の質問に基づいて回答してください: {user_question}

Please provide a clear, concise answer based on the available data:"""

        messages = [{"role": "user", "content": prompt}]
        input_data = {
            "messages": messages,
            "max_tokens": 300,
            "anthropic_version": "bedrock-2023-05-31"
        }

        response = bedrock_client.invoke_model(
            modelId="anthropic.claude-3-sonnet-20240229-v1:0",
            body=json.dumps(input_data),
            contentType='application/json'
        )

        response_body = json.loads(response['body'].read().decode('utf-8'))
        print("Response Body from Claude:", response_body)


        return response_body.get('content', "Sorry, I couldn't process your question.")
    except Exception as e:
        print(f"Error querying Bedrock: {str(e)}")
        return "Sorry, there was an error processing your question."

# Format Data for Claude Model
def format_data_for_claude(data, data_type):

    if data_type == "suspicious":
        return "\n不審者:\n" + "\n".join([f"• Time: {entry['event_time']} - Number of People: {entry['num']}" for entry in data])
    elif data_type == "project_times":
        return "\n入り帰りデータ:\n" + "\n".join([f"•入り時間: {entry['start_time']}, 帰り時間: {entry['last_time']}" for entry in data])
    elif data_type == "max_min":
        return "\n最大最小データ:\n" + "\n".join([f"• 一番多い人: {entry.get('max_num', 'N/A')} at {entry.get('max_time', 'N/A')}\n"                                                f"• 一番少ない人: {entry.get('min_num', 'N/A')} at {entry.get('min_time', 'N/A')}" for entry in data])
    elif data_type == "current_data":
        return "\n現在データ:\n" + "\n".join([f"• Time: {entry['time']} - Number of People: {entry['num']}" for entry in data])
    elif data_type == "prediction":
        return "\n予想データ:\n" + json.dumps(data, ensure_ascii=False, indent=2)

def lambda_handler(event, context):
    http_method = event.get('httpMethod', None)

    if http_method == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': CORS_HEADERS,
            'body': json.dumps({'message': 'CORS Preflight Successful'})
        }

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

    suspicious_data = fetch_suspicious_data()
    if not suspicious_data:
        return {
            'statusCode': 404,
            'headers': CORS_HEADERS,
            'body': json.dumps({'message': 'No suspicious data found.'})
        }


    project_times = fetch_start_last_times()
    if not project_times:
        return {
            'statusCode': 404,
            'headers': CORS_HEADERS,
            'body': json.dumps({'message': 'No project times data found.'})
        }

    max_min = fetch_get_max_min_data()
    if not max_min:
        return {
            'statusCode': 404,
            'headers': CORS_HEADERS,
            'body': json.dumps({'message': 'No max-min data found.'})
        }
    
    # prediction_data = invoke_prediction_lambda()
    # if not prediction_data:
    #     return {
    #         'statusCode': 404,
    #         'headers': CORS_HEADERS,
    #         'body': json.dumps({'message': 'No prediction data found.'})
    #     }
    
    current_data = fetch_current_data()
    if not current_data:
        return {
            'statusCode': 404,
            'headers': CORS_HEADERS,
            'body': json.dumps({'message': 'No current data found.'})
        }
    
    prediction_data = invoke_prediction_lambda(user_question)
    print("prediction data"+ prediction_data)
    if not prediction_data:
        return {
            'statusCode': 404,
            'headers': CORS_HEADERS,
            'body': json.dumps({'message': 'Failed to invoke the prediction Lambda.'})
        }


    answer = get_answer_from_claude(user_question, suspicious_data, project_times, max_min,  current_data, prediction_data)

    return {
        'statusCode': 200,
        'headers': CORS_HEADERS,
        'body': json.dumps({
            'question': user_question,
            'response': answer
        })
    }

