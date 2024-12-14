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

url2="https://xsjzbkgsqtvlzyqeqbmx.supabase.co/storage/v1/object/public/ForLidar/Knowledge%20base%20/solvecrowd.pdf?t=2024-12-05T14%3A12%3A59.141Z"
temp_solvecrowd_path = "/tmp/solvecrowd.pdf"

url = "https://xsjzbkgsqtvlzyqeqbmx.supabase.co/storage/v1/object/public/ForLidar/Knowledge%20base%20/minohcSchdeule.pdf?t=2024-11-28T11%3A38%3A17.614Z"
temp_file_path = "/tmp/minohcschedule.pdf"

# Download PDF
response = requests.get(url)
if response.status_code == 200:
    with open(temp_solvecrowd_path, 'wb') as f:
        f.write(response.content)
    print(f"File downloaded successfully to {temp_solvecrowd_path}")
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

#Change text 
pdf_text2 = extract_text_from_pdf(temp_solvecrowd_path)


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

#Change text 
pdf_text = extract_text_from_pdf(temp_file_path)

# third floor zone
def fetch_last_week_data():
    try:
        data = supabase.rpc('get_last_week_data').execute()
        if data.data:
            return data.data
        print("No Last Week data.")
        return None
    except Exception as e:
        print(f"Error fetching Last Week data: {str(e)}")
        return None

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
    


def get_answer_from_claude(question, suspicious_data, start_last_times, max_min_data, interval_data, weather_data, zone_data, pdf_text, current_data, last_week_data, pdf_text2):
    try:
        context_current = "\n不審者:\n" + "\n".join([f"• Time: {entry['time']} - Number of People: {entry['num']}" for entry in current_data])

        last_week_data = "\n不審者:\n" + "\n".join([f"• Time: {entry['time']} - Number of People: {entry['num']}" for entry in last_week_data])

        context_suspicious = "\n不審者:\n" + "\n".join([f"• Time: {entry['event_time']} - Number of People: {entry['num']}" for entry in suspicious_data])
     
        context_project = "\n入り帰りデータ:\n" + "\n".join([f"•入り時間: {entry['start_time']}, 帰り時間: {entry['last_time']}" for entry in start_last_times])

        context_maxmin = "\n:\n" + "\n".join([f"• 一番多い人: {entry.get('max_num', 'N/A')} at {entry.get('max_time', 'N/A')}\n"
                                             f"• 一番少ない人: {entry.get('min_num', 'N/A')} at {entry.get('min_time', 'N/A')}" for entry in max_min_data])
        context_interval = "\n人流データ:\n" + "\n".join([f"• Time: {entry['time']} - Number of People: {entry['num']}" for entry in interval_data])

        context_weather = "\n気候データ:\n" + "\n".join([f"•気候時間: {entry['weather_time']}, "
                                                           f"temperature_2m_celsius: {entry['temperature_2m_celsius']}, "
                                                           f"relative_humidity_2m_percent: {entry['relative_humidity_2m_percent']}, "
                                                           f"apparent_temperature_celsius: {entry['apparent_temperature_celsius']}, "
                                                           f"precipitation_mm: {entry['precipitation_mm']}, "
                                                           f"snowfall_cm: {entry['snowfall_cm']}, "
                                                           f"weather_code_wmo_code: {entry['weather_code_wmo_code']}, "
                                                           f"cloud_cover_percent: {entry['cloud_cover_percent']}, "
                                                           f"wind_speed_10m_kmh: {entry['wind_speed_10m_kmh']}" for entry in weather_data])

        context_zone = "\n気候データ:\n" + "\n".join([f"•zone_id: {entry['zone_id']}, "
                                                           f"zone_no: {entry['zone_no']}, "
                                                           f"zone_name: {entry['zone_name']}, "
                                                           f"geometry: {entry['geometry']}, "
                                                           f"count_type: {entry['count_type']}, "
                                                           f"capacity: {entry['capacity']} " for entry in zone_data])

        context_pdf = "\nPDF Data:\n" + pdf_text

        context_pdf2 = "\nPDF Data:\n" + pdf_text2

        prompt = f"""あなたは建物の利用状況を分析するアシスタントです。以下のデータを基に、ユーザーの質問に正確に答えてください。
        注意点は予測と関係ある質問のみcontext_interval、context_weather、context_zone、context_pdf, last_week_data ,context_currentのデータを使ってください。
        食堂混雑についてアドバイスするためにcontext_pdf2データを利用しください。

利用可能なデータ:
{context_suspicious}
{context_project}
{context_maxmin}
{context_interval}
{context_weather}
{context_zone}
{context_pdf}
{context_current}
{last_week_data}
{context_pdf2}


回答の指針:
0. 全ての時刻は日本の時刻です。日本のカレンダーから曜日を表示。
1. 時刻は常にYYYY/MM/DD (曜日) HH:MM」形式で表示し　、ISO 8601形式（例: yyyy-mm-ddThh:mm:ss+00:00）は絶対に使用しない。
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
        return response_body.get('content', "Sorry, I couldn't process your question.")
    except Exception as e:
        print(f"Error querying Bedrock: {str(e)}")
        return "Sorry, there was an error processing your question."

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
    
    current_data = fetch_current_data()
    if not current_data:
        return {
            'statusCode': 404,
            'headers': CORS_HEADERS,
            'body': json.dumps({'message': 'No current data found.'})
        }
    
    last_week_data= fetch_last_week_data()
    if not last_week_data:
        return {
            'statusCode': 404,
            'headers': CORS_HEADERS,
            'body': json.dumps({'message': 'No last week data found.'})
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

    answer = get_answer_from_claude(user_question, suspicious_data, project_times, max_min, interval_data, weather_times, zone_data, pdf_text, current_data, last_week_data, pdf_text2)

    return {
        'statusCode': 200,
        'headers': CORS_HEADERS,
        'body': json.dumps({
            'question': user_question,
            'response': answer
        })
    }
