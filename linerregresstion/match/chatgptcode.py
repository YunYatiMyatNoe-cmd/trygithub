import boto3
import json
import os
import re
import requests
from supabase import create_client, Client
from datetime import datetime, timedelta
from PyPDF2 import PdfReader

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
bedrock_client = boto3.client('bedrock-runtime', region_name='us-east-1')

# Fetch current data
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

# Fetch suspicious data   
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

# Fetch start and last times
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

# Fetch max and min data
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

# Function to fetch all prediction data
def fetch_all_predictiondata():
    url = "https://xsjzbkgsqtvlzyqeqbmx.supabase.co/storage/v1/object/public/ForLidar/Knowledge%20base%20/minohcSchdeule.pdf?t=2024-11-28T11%3A38%3A17.614Z"
    temp_file_path = "/tmp/minohcschedule.pdf"

    # Download PDF
    response = requests.get(url)
    if response.status_code == 200:
        with open(temp_file_path, 'wb') as f:
            f.write(response.content)
        print(f"File downloaded successfully to {temp_file_path}")
    else:
        print("Failed to download file.")
        return None  # Early return if the file download fails

    # Extract text from the PDF
    def extract_text_from_pdf(pdf_path):
        with open(pdf_path, 'rb') as file:
            reader = PdfReader(file)
            text = ""
            for page in reader.pages:
                text += page.extract_text()
        return text

    # Extract text from the downloaded PDF
    pdf_text = extract_text_from_pdf(temp_file_path)

    # Function to fetch third floor zone data from Supabase
    def fetch_thirdFloor_zone():
        try:
            data = supabase.rpc('get_thirdfloor_zones').execute()
            if data.data:
                return data.data
            print("No thirdFloor_zone data found.")
            return None
        except Exception as e:
            print(f"Error fetching thirdFloor_zone: {str(e)}")
            return None

    # Function to fetch data for the interval from Supabase
    def fetch_data_for_interval():
        try:
            data = supabase.rpc('get_thirdfloor_hourdata', {'hours_interval': 1}).execute()
            if data.data:
                return data.data
            print("No interval data found.")
            return None
        except Exception as e:
            print(f"Error fetching interval data: {str(e)}")
            return None

    # Function to fetch weather data for the next days from Supabase
    def fetch_weather_data_for_next_days():
        try:
            data = supabase.rpc('get_weather_data_for_next_days', {'num_days': 1}).execute()
            if data.data:
                return data.data
            print("No weather data found.")
            return None
        except Exception as e:
            print(f"Error fetching weather data: {str(e)}")
            return None

    # Fetch the required data
    third_floor_zone = fetch_thirdFloor_zone()
    interval_data = fetch_data_for_interval()
    weather_data = fetch_weather_data_for_next_days()

    if third_floor_zone is None or interval_data is None or weather_data is None:
        print("One or more data fetches failed.")
        return None

    # Now, let's return the fetched data and the extracted text
    return {
        "pdf_text": pdf_text,
        "thirdFloor_zone": third_floor_zone,
        "interval_data": interval_data,
        "weather_data": weather_data
    }

# Extract relevant data based on the user's question
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
def get_answer_from_claude(user_question, suspicious_data, project_times, max_min_data, prediction_data, current_data):
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
                "prediction": prediction_data,
                "current_data": current_data
            }

        formatted_data = format_data_for_claude(relevant_data, relevant_data_type)

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

        # Ensure to correctly handle the Bedrock response
        response = bedrock_client.invoke_model(
            modelId="anthropic.claude-3-sonnet-20240229-v1:0",
            body=json.dumps(input_data),
            contentType='application/json'
        )

        # Log the full raw response to debug
        raw_response = response['body'].read().decode('utf-8')
        print(f"Raw response: {raw_response}")

        # Parse the response body into a dictionary
        try:
            response_body = json.loads(raw_response)  # Parsing the response string to JSON
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON: {str(e)}")
            return "Sorry, there was an error processing your question."

        # Ensure response_body is a dictionary
        if isinstance(response_body, dict):
            response_content = response_body.get('response', "Sorry, there was an error processing your question.")
            return response_content
        else:
            print(f"Unexpected response format: {response_body}")
            return "Sorry, there was an error processing your question."

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
        return "\n最大最小データ:\n" + "\n".join([f"• 一番多い人: {entry.get('max_num', 'N/A')} at {entry.get('max_time', 'N/A')}, 一番少ない人: {entry.get('min_num', 'N/A')} at {entry.get('min_time', 'N/A')}" for entry in data])
    elif data_type == "prediction":
        return "\n予測データ:\n" + "\n".join([f"• 時間: {entry.get('time_interval', 'N/A')}, 予測人数: {entry.get('predicted_people', 'N/A')}" for entry in data])
    else:
        return "\n全てのデータ:\n" + "\n".join([f"{data_type}: {entry}" for entry in data])

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

    # Step 5: Fetch current data
    current_data = fetch_current_data()
    if not current_data:
        return {
            'statusCode': 404,
            'headers': CORS_HEADERS,
            'body': json.dumps({'message': 'No current data found.'})
        }

    # Step 6: Get answer from Claude
    answer = get_answer_from_claude(user_question, suspicious_data, project_times, max_min, prediction_data, current_data)

    # Step 7: Return the answer to the user
    return {
        'statusCode': 200,
        'headers': CORS_HEADERS,
        'body': json.dumps({
            'question': user_question,
            'response': answer
        })
    }