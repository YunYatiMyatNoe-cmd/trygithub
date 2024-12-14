import os
import json
import httpx
import asyncio
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta
from mangum import Mangum  # For AWS Lambda
import pytz
from supabase import create_client, Client
import traceback

app = FastAPI()

# Supabase Configuration
SUPABASE_URL = "https://xsjzbkgsqtvlzyqeqbmx.supabase.co"
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# CORS Middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

weather_data_cache = []  # Cache for storing fetched weather data

async def fetch_weather_data():
    """Fetch weather data from an external API."""
    global weather_data_cache  # Correct reference to the global variable
    try:
        weather_url = f"https://api.open-meteo.com/v1/forecast?latitude=34.664967&longitude=135.451014&hourly=temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,snowfall,weather_code,cloud_cover,wind_speed_10m&timezone=Asia%2FTokyo&forecast_days=1"

        async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:  # Timeout set to 30 seconds
            response = await client.get(weather_url)

        print(f"Weather Data API Response: {response.status_code}, {response.text}")

        if response.status_code == 200:
            weather_data_cache = response.json()  # Update global cache
            await store_weather_data()  # Store data after fetching it
        else:
            print(f"API request failed: {response.status_code} - {response.text}")
            
    except httpx.ReadTimeout as e:
        print("HTTPX ReadTimeout occurred.")
        print("Traceback:", traceback.format_exc())  # Log detailed traceback
    except httpx.RequestError as e:
        print(f"HTTPX request error: {str(e)}")
        print("Traceback:", traceback.format_exc())  # Log detailed traceback
    except Exception as e:
        print(f"Error occurred while fetching data: {str(e)}")
        print("Traceback:", traceback.format_exc())  # Log detailed traceback

async def store_weather_data():
    """Store weather data in the Supabase database."""
    global weather_data_cache  # Correct reference to the global variable

    if not weather_data_cache:
        print("No data in cache to store.")
        return

    try:
        # Assuming weather contains hourly weather data
        hourly_data = weather_data_cache['hourly']  # Access the hourly data in the cache

        # Loop through each hourly data point and insert into the database
        for idx, time in enumerate(hourly_data['time']):
            insert_data = {
                "time": time,  # ISO8601 format from the API
                "temperature_2m_celsius": hourly_data['temperature_2m'][idx],
                "relative_humidity_2m_percent": hourly_data['relative_humidity_2m'][idx],
                "apparent_temperature_celsius": hourly_data['apparent_temperature'][idx],
                "precipitation_mm": hourly_data['precipitation'][idx],
                "snowfall_cm": hourly_data['snowfall'][idx],
                "weather_code_wmo_code": hourly_data['weather_code'][idx],
                "cloud_cover_percent": hourly_data['cloud_cover'][idx],
                "wind_speed_10m_kmh": hourly_data['wind_speed_10m'][idx],
            }

            # Insert each weather record into the Supabase database
            insert_response = supabase.table("weather_data").insert(insert_data).execute()

            # Log the entire insert response to inspect its structure
            print(f"Insert Response: {insert_response}")

            # Check if the response has an error or data attribute
            if hasattr(insert_response, 'error') and insert_response.error:
                print(f"Supabase insertion failed: {insert_response.error}")
            else:
                print(f"Data successfully inserted into Supabase: {insert_response.data}")

    except Exception as e:
        print(f"Error while processing and inserting weather data: {str(e)}")


@app.on_event("startup")
async def startup_event():
    """Startup event to fetch initial data."""
    try:
        await fetch_weather_data()
        print("Initial data fetch completed on startup.")
    except Exception as e:
        print(f"Error occurred during startup: {str(e)}")

# Lambda entry point using Mangum
mangum_handler = Mangum(app)

def lambda_handler(event, context):
    """AWS Lambda entry point."""
    print(f"Received event: {json.dumps(event)}")
    try:
        # Ensure the event loop is running for async tasks
        loop = asyncio.get_event_loop()
        if not loop.is_running():
            loop.run_until_complete(fetch_weather_data())  # Fetch and store weather data
        return {
            "statusCode": 200,
            "body": "Data fetched and stored successfully."
        }
    except Exception as e:
        return {
            "statusCode": 500,
            "body": f"Error occurred: {str(e)}"
        }
