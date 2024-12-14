import boto3
import json
import os
import requests
from PyPDF2 import PdfReader  # Make sure to install this module using `pip install pypdf2`
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

# Fetch project times
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

# Fetch max-min data
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

# Fetch third floor zone data
def fetch_thirdFloor_zone():
    try:
        data = supabase.rpc('get_thirdfloor_zones').execute()
        if data.data:
            return data.data
        print("No thirdFloor_zone.")
        return None
    except Exception as e:
        print(f"Error fetching thirdFloor_zone: {str(e)}")
        return None

# Fetch interval data
def fetch_data_for_interval():
    try:
        data = supabase.rpc('get_data_for_interval', {'hours_interval': 1}).execute()
        if data.data:
            return data.data
        print("No interval data found.")
        return None
    except Exception as e:
        print(f"Error fetching data: {str(e)}")
        return None

# Fetch weather data for the next days
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

# Download PDF
url = "https://xsjzbkgsqtvlzyqeqbmx.supabase.co/storage/v1/object/public/ForLidar/Knowledge%20base%20/minohcSchdeule.pdf?t=2024-11-28T11%3A38%3A17.614Z"
temp_file_path = "/tmp/minohcschedule.pdf"

response = requests.get(url)
if response.status_code == 200:
    with open(temp_file_path, 'wb') as f:
        f.write(response.content)
    print(f"File downloaded successfully to {temp_file_path}")
else:
    print("Failed to download file.")

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

# Function to get answer from Claude (AWS Bedrock)
def get_answer_from_claude(question, suspicious_data, start_last_times, max_min_data, interval_data, weather_data, zone_data, pdf_text):
    try:
        # Format suspicious data
        context_suspicious = "\n不審者:\n" + "\n".join([f"• Time: {entry['event_time']} - Number of People: {entry['num']}" for entry in suspicious_data])
        context_project = "\n入り帰りデータ:\n" + "\n".join([f"•入り時間: {entry['start_time']}, 帰り時間: {entry['last_time']}" for entry in start_last_times])
        context_maxmin = "\n:\n" + "\n".join([f"• 一番多い人: {entry.get('max_num', 'N/A')} at {entry.get('max_time', 'N/A')}\n"
                                             f"• 一番少ない人: {entry.get('min_num', 'N/A')} at {entry.get('min_time', 'N/A')}" for entry in max_min_data])

        # Build prompt with relevant data
        prompt = f"""
        あなたは建物の利用状況を分析するアシスタントです。以下のデータを基に、ユーザーの質問に正確に答えてください。

        利用可能なデータ:
        {context_suspicious}
        {context_project}
        {context_maxmin}
        """

        # Adding additional context
        prompt += "\n人流データ:\n" + "\n".join([f"• Time: {entry['time']} - Number of People: {entry['data']}" for entry in interval_data])
        prompt += "\n気候データ:\n" + "\n".join([f"•気候時間: {entry['weather_time']}, " f"temperature_2m_celsius: {entry['temperature_2m_celsius']}" for entry in weather_data])
        prompt += "\nゾーンデータ:\n" + "\n".join([f"•zone_id: {entry['zone_id']}, zone_name: {entry['zone_name']}" for entry in zone_data])
        prompt += "\nPDFデータ:\n" + pdf_text

        # Call Claude model using Bedrock client
        input_data = {
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 300,
            "anthropic_version": "bedrock-2023-05-31"
        }

        # Invoke the model
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

    # Fetch data
    suspicious_data = fetch_suspicious_data()
    project_times = fetch_start_last_times()
    max_min = fetch_get_max_min_data()
    interval_data = fetch_data_for_interval()
    weather_data = fetch_weather_data_for_next_days()
    zone_data = fetch_thirdFloor_zone()

    # Handle cases where data fetching fails
    if not suspicious_data or not project_times or not max_min or not interval_data or not weather_data or not zone_data:
        return {
            'statusCode': 500,
            'headers': CORS_HEADERS,
            'body': json.dumps({'error': 'Failed to fetch necessary data.'})
        }

    # Get the answer from Claude
    answer = get_answer_from_claude(user_question, suspicious_data, project_times, max_min, interval_data, weather_data, zone_data, pdf_text)
    
    return {
        'statusCode': 200,
        'headers': CORS_HEADERS,
        'body': json.dumps({'answer': answer})
    }
