import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split
import json

# Step 1: Fetch last week's data
def get_last_week_data():
    data = pd.DataFrame({
        'timestamp': timestamps,
        'people_count': people_count
    })
    return data

# Step 2: Prepare data for the model
def prepare_data_for_model(data):
    data['hour'] = data['timestamp'].dt.hour
    data['minute'] = data['timestamp'].dt.minute
    data['day_of_week'] = data['timestamp'].dt.dayofweek  # 0=Monday, 6=Sunday
    X = data[['hour', 'minute', 'day_of_week']]
    y = data['people_count']
    return X, y

# Step 3: Train the model
def train_linear_regression(X, y):
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    model = LinearRegression()
    model.fit(X_train, y_train)
    r2_score = model.score(X_test, y_test)
    print(f'R² Score: {r2_score}')
    return model

# Step 4: Make predictions
def make_predictions(model, X):
    predictions = model.predict(X)
    return predictions

# Lambda function handler
def lambda_handler(event, context):
    # CORS Headers (you can modify these as per your needs)
    CORS_HEADERS = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type,Authorization',
        'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
    }

    # Check for CORS preflight request
    http_method = event.get('httpMethod', None)
    if http_method == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': CORS_HEADERS,
            'body': json.dumps({'message': 'CORS Preflight Successful'})
        }

    # Parse the incoming request body
    body = event.get('body', '{}')
    try:
        body = json.loads(body)
    except json.JSONDecodeError:
        return {
            'statusCode': 400,
            'headers': CORS_HEADERS,
            'body': json.dumps({'error': 'Invalid JSON in request body.'})
        }

    # Fetch last week's data
    data = get_last_week_data()

    # Prepare data for the model
    X, y = prepare_data_for_model(data)

    # Train the model
    model = train_linear_regression(X, y)

    # Make predictions on the input data
    predictions = make_predictions(model, X)

    # Prepare the predictions response
    predictions_json = [{"timestamp": ts, "predicted_people": int(pred)} 
                        for ts, pred in zip(data['timestamp'], predictions)]

    # Return predictions as JSON
    return {
        'statusCode': 200,
        'headers': CORS_HEADERS,
        'body': json.dumps({'predictions': predictions_json})
    }
