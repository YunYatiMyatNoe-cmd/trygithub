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
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inhzanpia2dzcXR2bHp5cWVxYm14Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzAzMzgxMTksImV4cCI6MjA0NTkxNDExOX0.RJp6Eto7a9bR5NjLPKmH_9oHC-7SNp7IEAdzQWQ8-HE"

if not SUPABASE_KEY:
    raise ValueError("SUPABASE_KEY environment variable is not set.")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Initialize the AWS Bedrock client for Claude 3
bedrock_client = boto3.client('bedrock-runtime', region_name='us-east-1')

def fetch_thirdFloor_zone():
    try:
        # Use the correct function name, ensuring the case is correct
        data = supabase.rpc('get_thirdfloor_zones').execute()  # Ensure correct case (lowercase 'f')
        if data.data:
            return data.data
        print("No thirdFloor_zone.")
        return None
    except Exception as e:
        print(f"Error fetching thirdFloor_zone: {str(e)}")
        return None

# def fetch_data_for_interval():
#     try:
#         # Initialize variables for pagination
#         all_data = []  # This will hold all fetched data
#         start = 0       # Starting point of the query (pagination)
#         limit = 1000    # Maximum number of rows per query (Supabase default limit)
        
#         while True:
#             # Fetch a chunk of data using range (pagination)
#             data = supabase.rpc('get_data_for_interval', {'hours_interval': 168}).range(start, start + limit - 1).execute()
            
#             # Check if the data was fetched successfully
#             if data.data:
#                 # Add the fetched data to the all_data list
#                 all_data.extend(data.data)
#                 print(f"Fetched {len(data.data)} rows, Total fetched: {len(all_data)}")
                
#                 # If the number of rows fetched is less than the limit, we've reached the end
#                 if len(data.data) < limit:
#                     break  # Exit if fewer rows were returned than requested (end of data)
#                 else:
#                     # Otherwise, increase the starting point for the next query
#                     start += limit
#             else:
#                 print("No more data available.")
#                 break
        
#         print(f"Total rows fetched: {len(all_data)}")
#         return all_data

#     except Exception as e:
#         print(f"Error fetching data for interval: {str(e)}")
#         return None
        
def fetch_data_for_interval():
    try:
        # Call the RPC function with the correct parameter
        data = supabase.rpc('get_data_for_interval', {'hours_interval': 1}).execute()
        if data.data:
            return data.data
        print("No data data found.")
        return None
    except Exception as e:
        print(f"Error fetching data: {str(e)}")
        return None

def fetch_weather_data_for_next_days():
    try:
        # Call the RPC function with the correct parameter
        data = supabase.rpc('get_weather_data_for_next_days', {'num_days': 1}).execute()
        if data.data:
            return data.data
        print("No weather data found.")
        return None
    except Exception as e:
        print(f"Error fetching weather data: {str(e)}")
        return None


def get_answer_from_claude(question, interval_data, weather_data, zone_data):
    try:
        # Format suspicious data
        context_interval = "\n人流データ:\n" + "\n".join([f"• Time: {entry['time']} - Number of People: {entry['data']}" for entry in interval_data])
        # print(context_interval)

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
        # print(context_weather)

         # Format zone data
        context_zone = "\n気候データ:\n" + "\n".join([f"•zone_id: {entry['zone_id']}, "
                                                           f"zone_no: {entry['zone_no']}, "
                                                           f"zone_name: {entry['zone_name']}, "
                                                           f"geometry: {entry['geometry']}, "
                                                           f"count_type: {entry['count_type']}, "
                                                           f"capacity: {entry['capacity']} " for entry in zone_data])
        # print(context_weather)



        prompt = f"""あなたは建物の利用状況を分析するアシスタントです。以下のデータを基に、ユーザーの質問に正確に答えてください。

利用可能なデータ:
{context_interval}
{context_weather}
{context_zone}
This is minohc campus Osaka university of Japan data. context_interval of num is the num of people is third floor canteen data and context_weather is the minohc campus of prediction weather and context_zone is the third floor area I want to know prediction data after 30 minutes base these three data because I want to prepare food.

以下の質問に基づいて回答してください: {question}

Please provide answer only time human number and reasons english language."""

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
    interval_data = fetch_data_for_interval()
    if not interval_data:
        return {
            'statusCode': 404,
            'headers': CORS_HEADERS,
            'body': json.dumps({'message': 'No fetch_data_for_interval.'})
        }

    # Step 2: Fetch project times
    weather_times = fetch_weather_data_for_next_days()
    if not weather_times:
        return {
            'statusCode': 404,
            'headers': CORS_HEADERS,
            'body': json.dumps({'message': 'No fetch_weather_data_for_next_days found.'})
        }
    
    # Step 3: Fetch project times
    zone_data = fetch_thirdFloor_zone()
    if not zone_data:
        return {
            'statusCode': 404,
            'headers': CORS_HEADERS,
            'body': json.dumps({'message': 'No fetch_3F_zone found.'})
        }


    # Step 4: Get answer from Claude
    answer = get_answer_from_claude(user_question, interval_data, weather_times, zone_data)

    # Step 5: Return the answer to the user
    return {
        'statusCode': 200,
        'headers': CORS_HEADERS,
        'body': json.dumps({
            'question': user_question,
            'response': answer
        })
    }
