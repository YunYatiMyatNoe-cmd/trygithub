import boto3
import json
import time
from datetime import datetime

# CORS Headers for enabling cross-origin resource sharing
CORS_HEADERS = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type,Authorization',
    'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
}


bedrock_client = boto3.client('bedrock-runtime', region_name='us-east-1')


def get_answer_from_claude(question):
    try:
        prompt = f"Please answer the following question: {question}"

       
        input_data = {
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 2048,
            "anthropic_version": "bedrock-2023-05-31"
        }

       
        response = bedrock_client.invoke_model(
            modelId="anthropic.claude-3-sonnet-20240229-v1:0",
            body=json.dumps(input_data),
            contentType='application/json'
        )

        response_body = json.loads(response['body'].read().decode('utf-8'))
        full_answer = response_body.get('content', "Sorry, I couldn't process your question.")

        return full_answer

    except Exception as e:
        print(f"Error querying Bedrock: {str(e)}")
        return "Sorry, there was an error processing your question."

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

    # Get the answer from Claude
    full_answer = get_answer_from_claude(user_question)

    # Simulating streaming of the response
    chunk_size = 500  # Adjust as necessary
    response_chunks = [full_answer[i:i + chunk_size] for i in range(0, len(full_answer), chunk_size)]

    simulated_streaming_response = ''
    for chunk in response_chunks:
        if isinstance(chunk, list):  # If chunk is a list, join it into a string
            chunk = ''.join(chunk)
        time.sleep(1)  # Simulate a delay for each chunk (streaming effect)
        simulated_streaming_response += chunk

        # Here, send the chunk to the user (can be through an API Gateway endpoint)
        # In a real-world scenario, you would use a WebSocket or SSE connection
        print(f"Sending chunk: {chunk}")

    # Returning full response after simulating streaming
    return {
        'statusCode': 200,
        'headers': CORS_HEADERS,
        'body': json.dumps({
            'question': user_question,
            'response': simulated_streaming_response
        })
    }
