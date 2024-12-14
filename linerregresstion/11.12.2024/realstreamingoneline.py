import boto3
import json
from datetime import datetime, timedelta

# CORS Headers
CORS_HEADERS = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type,Authorization',
    'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
}

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

    # Invoke the model with the request and return the response stream
    streaming_response = client.invoke_model_with_response_stream(
        modelId=model_id, body=request
    )

    # Extract and return the response text in real-time (simulating streaming)
    response_text = ""
    for event in streaming_response["body"]:
        chunk = json.loads(event["chunk"]["bytes"])
        if chunk["type"] == "content_block_delta":
            response_text += chunk["delta"].get("text", "")
    
    return response_text

# Function to simulate streaming chunks of a response (for Lambda)
def simulate_streaming_output(full_answer):
    # Split the full answer into chunks to simulate streaming
    chunk_size = 100  # Adjust the size of each chunk as needed
    for i in range(0, len(full_answer), chunk_size):
        yield full_answer[i:i + chunk_size]

# Lambda handler function
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

    # Get the answer from Claude 3
    full_answer = get_answer_from_claude(user_question)

    # Simulate streaming of the full answer in chunks
    response_chunks = list(simulate_streaming_output(full_answer))

    # Return chunks one by one (you may want to send them via an API Gateway WebSocket or EventBridge in real-world use)
    return {
        'statusCode': 200,
        'headers': CORS_HEADERS,
        'body': json.dumps({
            'question': user_question,
            'response': response_chunks
        })
    }
