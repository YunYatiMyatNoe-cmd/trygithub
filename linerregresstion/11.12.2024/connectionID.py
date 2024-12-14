import boto3
import json
import time
import logging
from datetime import datetime, timedelta

# CORS Headers
CORS_HEADERS = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type,Authorization',
    'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
}

# Set up logging
logging.basicConfig(level=logging.INFO)

# Create a Bedrock Runtime client in the AWS Region of your choice.
client = boto3.client("bedrock-runtime", region_name="us-east-1")

# Set the model ID (replace with the correct model ID).
model_id = "anthropic.claude-3-sonnet-20240229-v1:0"

# Function to invoke the Bedrock model and get the answer
def get_answer_from_claude(prompt):
    # Define the request payload to invoke the model
    native_request = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 512,
        "temperature": 0.5,
        "messages": [
            {
                "role": "user",
                "content": [{"type": "text", "text": prompt}],
            }
        ],
    }

    # Convert the native request to JSON
    request = json.dumps(native_request)

    # Invoke the model with the request and stream the response
    streaming_response = client.invoke_model_with_response_stream(
        modelId=model_id, body=request
    )

    # Process the response stream in real-time
    for event in streaming_response["body"]:
        chunk = json.loads(event["chunk"]["bytes"])
        if chunk["type"] == "content_block_delta":
            # Print the chunk of text to simulate real-time streaming to the user
            text = chunk["delta"].get("text", "")
            if text:
                yield text
                time.sleep(0.1)  # Simulate some delay to make it feel like a stream (optional)

# WebSocket message sending function
def send_message_to_websocket(connection_id, data):
    apigatewaymanagementapi = boto3.client('apigatewaymanagementapi', endpoint_url='https://YOUR_API_GATEWAY_URL')
    
    try:
        # Send the real-time data chunk to the client
        apigatewaymanagementapi.post_to_connection(
            ConnectionId=connection_id,
            Data=data
        )
    except apigatewaymanagementapi.exceptions.GoneException:
        # Handle case where the connection is no longer active
        logging.warning(f"Connection {connection_id} no longer active.")
        return

# Lambda handler function to handle WebSocket requests
def lambda_handler(event, context):
    http_method = event.get('httpMethod', None)

    # Handling preflight CORS requests
    if http_method == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': CORS_HEADERS,
            'body': json.dumps({'message': 'CORS Preflight Successful'})
        }

    # Handling incoming POST requests with the user question
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

    # Validate the question
    if not user_question:
        return {
            'statusCode': 400,
            'headers': CORS_HEADERS,
            'body': json.dumps({'message': 'No question provided.'})
        }

    # Extract connection ID for WebSocket
    connection_id = event['requestContext'].get('connectionId', None)
    
    if not connection_id:
        return {
            'statusCode': 400,
            'headers': CORS_HEADERS,
            'body': json.dumps({'error': 'Connection ID not found.'})
        }

    # Get the answer from Claude 3 and stream the result in chunks to WebSocket
    try:
        for chunk in get_answer_from_claude(user_question):
            send_message_to_websocket(connection_id, chunk)
            # You can add additional sleep/delay if you want to control the pacing
            time.sleep(1)

        return {
            'statusCode': 200,
            'headers': CORS_HEADERS,
            'body': json.dumps({'message': 'Response sent successfully'})
        }

    except Exception as e:
        logging.error(f"Error: {e}")
        return {
            'statusCode': 500,
            'headers': CORS_HEADERS,
            'body': json.dumps({'error': 'Internal server error.'})
        }
