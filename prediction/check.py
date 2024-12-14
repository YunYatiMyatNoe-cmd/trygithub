import boto3
import json
import os
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

# Initialize the AWS Bedrock client for Claude 3
bedrock_client = boto3.client('bedrock-runtime', region_name='us-east-1')

# URL for the PDF file
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
def fetch_last_week_data():
    try:
        data = supabase.rpc('get_last_week_data').execute()
        if data.data:
            return data.data
        print("No last_week_data.")
        return None
    except Exception as e:
        print(f"Error fetching thirdFloor_zone: {str(e)}")
        return None

# Function to fetch third floor zone data from Supabase
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

# Function to fetch data for the interval from Supabase
def fetch_data_for_interval():
    try:
        data = supabase.rpc('get_thirdfloor_hourdata', {'hours_interval': 1}).execute()
        if data.data:
            return data.data
        print("No data data found.")
        return None
    except Exception as e:
        print(f"Error fetching data: {str(e)}")
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

# Function to get an answer from Claude using the provided data
def get_answer_from_claude(question, interval_data, weather_data, zone_data, pdf_text, last_week_data):
    try:
        # Format suspicious data
        context_interval = "\n人流データ:\n" + "\n".join([f"• Time: {entry['time']} - Number of People: {entry['num']}" for entry in interval_data])

        # Format weather data
        context_weather = "\n気候データ:\n" + "\n".join([f"•気候時間: {entry['weather_time']}, "
                                                           f"temperature_2m_celsius: {entry['temperature_2m_celsius']}, "
                                                           f"relative_humidity_2m_percent: {entry['relative_humidity_2m_percent']}, "
                                                           f"apparent_temperature_celsius: {entry['apparent_temperature_celsius']}, "
                                                           f"precipitation_mm: {entry['precipitation_mm']}, "
                                                           f"snowfall_cm: {entry['snowfall_cm']}, "
                                                           f"weather_code_wmo_code: {entry['weather_code_wmo_code']}, "
                                                           f"cloud_cover_percent: {entry['cloud_cover_percent']}, "
                                                           f"wind_speed_10m_kmh: {entry['wind_speed_10m_kmh']}" for entry in weather_data])

        # Format zone data
        context_zone = "\n気候データ:\n" + "\n".join([f"•zone_id: {entry['zone_id']}, "
                                                           f"zone_no: {entry['zone_no']}, "
                                                           f"zone_name: {entry['zone_name']}, "
                                                           f"geometry: {entry['geometry']}, "
                                                           f"count_type: {entry['count_type']}, "
                                                           f"capacity: {entry['capacity']} " for entry in zone_data])

        # Include the extracted PDF text
        context_pdf = "\nPDF Data:\n" + pdf_text

        # Only send a portion of last_week_data if necessary
        context_last_week_data = "\n過去データ:\n" + "\n".join([f"• Time: {entry['time']} - Number of People: {entry['num']}" for entry in last_week_data])

        prompt = f"""あなたは建物の利用状況を分析するアシスタントです。以下のデータを基に、ユーザーの質問に正確に答えてください。

利用可能なデータ:
{context_interval}
{context_weather}
{context_zone}
{context_pdf}
{context_last_week_data}

This is minohc campus Osaka university of Japan data. context_last_week_data is the third floor data last 1 week. context_interval of num is the num of people is third floor canteen data and context_weather is the minohc campus of prediction weather and context_zone is the third floor area, context_pdf is the schedule of minoch campus I want to know prediction data after 30 minutes base these three data because I want to prepare food.

以下の質問に基づいて回答してください: {question}
time は予測
Please provide answer json format 
time = yyyy-mm-dd:hh:mm+00:00 ,
num = human number and
reasons in english language."""
        

        # Prepare the messages for Claude API
        messages = [{"role": "user", "content": prompt}]
        input_data = {
            "messages": messages,
            "max_tokens": 20000,
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

# Lambda handler function
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

    interval_data = fetch_data_for_interval()
    if not interval_data:
        return {
            'statusCode': 404,
            'headers': CORS_HEADERS,
            'body': json.dumps({'message': 'No fetch_data_for_interval.'})
        }

    weather_times = fetch_weather_data_for_next_days()
    if not weather_times:
        return {
            'statusCode': 404,
            'headers': CORS_HEADERS,
            'body': json.dumps({'message': 'No fetch_weather_data_for_next_days found.'})
        }
    
    zone_data = fetch_thirdFloor_zone()
    if not zone_data:
        return {
            'statusCode': 404,
            'headers': CORS_HEADERS,
            'body': json.dumps({'message': 'No fetch_3F_zone found.'})
        }
    
    last_week_data = fetch_last_week_data()
    if not last_week_data:
        return {
            'statusCode': 404,
            'headers': CORS_HEADERS,
            'body': json.dumps({'message': 'No fetch_3F_zone found.'})
        }

    answer = get_answer_from_claude(user_question, interval_data, weather_times, zone_data, pdf_text, last_week_data)

    try:
        # print("Raw response from Claude:", answer)
        
        if isinstance(answer, list) and len(answer) > 0:
            response_text = answer[0].get('text', '')  

            # change json format
            print("Response Text:", response_text)
            
            # If the text contains valid JSON, parse it
            if response_text:
                try:
                    # Parse the JSON string inside the text field
                    prediction_data = json.loads(response_text)
                    # print("Parsed Prediction Data:", prediction_data)

                    prediction_time = prediction_data.get('time')
                    predicted_num = prediction_data.get('num')
                    reasons = prediction_data.get('reasons')

                    print("prediction time:", prediction_time)
                    print("prediction num:", predicted_num)
                    print("reasons:", reasons)

                    if prediction_time and predicted_num is not None and reasons:
                        # Prepare the data to insert into Supabase
                        supabase_data = {
                            'time': prediction_time,
                            'num': predicted_num,
                            'reasons': reasons
                        }
                        # print(f"Supabase Data to Insert: {supabase_data}")

                        response = supabase.table('predictiondata').insert(supabase_data).execute()
                        print(f"Prediction data saved to Supabase: {supabase_data}")
                    else:
                        print("Prediction data is incomplete, not saving to Supabase.")
                except json.JSONDecodeError as e:
                    print(f"Error parsing prediction data JSON: {str(e)}")
            else:
                print("No prediction data found in the response text.")
        else:
            print("No valid response data found.")
                    
    except Exception as e:
        print(f"Error processing response: {str(e)}")
        
    return {
        'statusCode': 200,
        'headers': CORS_HEADERS,
        'body': json.dumps({
            'question': user_question,
            'response': answer
        })
    }
