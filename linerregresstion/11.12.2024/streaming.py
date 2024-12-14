import boto3
import json
import os
from datetime import datetime, timedelta

# CORS Headers
CORS_HEADERS = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type,Authorization',
    'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
}

# Initialize the AWS Bedrock client for Claude 3
bedrock_client = boto3.client('bedrock-runtime', region_name='us-east-1')

# Generate the prompt for Bedrock
def get_answer_from_claude(question):
    try:
        # Create the prompt using the user's question
        prompt = f"Please answer the following question: {question}"

        # Prepare the input data for Claude 3 model
        input_data = {
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 2048,
            "anthropic_version": "bedrock-2023-05-31"
        } 

        # Make the API call to AWS Bedrock
        response = bedrock_client.invoke_model(
            modelId="anthropic.claude-3-sonnet-20240229-v1:0",
            body=json.dumps(input_data),
            contentType='application/json'
        )

        # Parse the response and return the answer
        response_body = json.loads(response['body'].read().decode('utf-8'))
        return response_body.get('content', "Sorry, I couldn't process your question.")
    
    except Exception as e:
        print(f"Error querying Bedrock: {str(e)}")
        return "Sorry, there was an error processing your question."


# Function to simulate the streaming output in chunks
def simulate_streaming_output(response_text):
    # Split the response into chunks (you can adjust this logic)
    chunks = response_text.split(". ")
    
    # Yield each chunk one by one (simulating streaming)
    for chunk in chunks:
        yield chunk + "."  # Adding period back after splitting


# Lambda function handler
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
