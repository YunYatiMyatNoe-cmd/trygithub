import json
import os
from supabase import create_client, Client

SUPABASE_URL = "https://xsjzbkgsqtvlzyqeqbmx.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inhzanpia2dzcXR2bHp5cWVxYm14Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzAzMzgxMTksImV4cCI6MjA0NTkxNDExOX0.RJp6Eto7a9bR5NjLPKmH_9oHC-7SNp7IEAdzQWQ8-HE"

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("SUPABASE_URL or SUPABASE_KEY environment variable is not set.")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def fetch_thirdFloor_zone():
    try:
        # Use the correct function name, ensuring the case is correct
        data = supabase.rpc('get_thirdfloor_zones').execute()  # Ensure correct case (lowercase 'f')
        if data.data:
            print(data.data)
            return data.data
        print("No thirdFloor_zone.")
        return None
    except Exception as e:
        print(f"Error fetching thirdFloor_zone: {str(e)}")
        return None
        
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
        data = supabase.rpc('get_weather_data_for_next_days', {'num_days': 1}).execute()
        if data.data:
            return data.data
        print("No weather data found.")
        return None
    except Exception as e:
        print(f"Error fetching weather data: {str(e)}")
        return None

# Example of how to call the functions
if __name__ == "__main__":
    thirdFloor_data = fetch_thirdFloor_zone()
    if thirdFloor_data:
        print(f"Third Floor Zone Data: {thirdFloor_data}")
    
    interval_data = fetch_data_for_interval()
    if interval_data:
        print(f"Data for Interval: {interval_data}")
    
    weather_data = fetch_weather_data_for_next_days()
    if weather_data:
        print(f"Weather Data: {weather_data}")
