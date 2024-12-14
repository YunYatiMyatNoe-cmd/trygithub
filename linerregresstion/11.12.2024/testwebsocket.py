import boto3
import json
import time

# Create Bedrock Runtime client
client = boto3.client("bedrock-runtime", region_name="us-east-1")

# Create API Gateway Management API client for WebSocket communication
api_gateway_management_api = boto3.client(
    'apigatewaymanagementapi', 
    endpoint_url='wss://eu7amamfjf.execute-api.ap-northeast-1.amazonaws.com/production//@connections'
)

# Set the model ID
model_id = "anthropic.claude-3-sonnet-20240229-v1:0"

# Function to invoke the Bedrock model and get the answer in streaming
def get_answer_from_claude(prompt):
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

    request = json.dumps(native_request)

    # Invoke the model with the request and stream the response
    streaming_response = client.invoke_model_with_response_stream(
        modelId=model_id, body=request
    )

    # Process the streamed response
    for event in streaming_response["body"]:
        chunk = json.loads(event["chunk"]["bytes"])
        if chunk["type"] == "content_block_delta":
            text = chunk["delta"].get("text", "")
            if text:
                yield text
                time.sleep(0.1)  # Optional: simulate delay to make it feel like a real-time stream

# Lambda handler function
def lambda_handler(event, context):
    route_key = event.get('requestContext', {}).get('routeKey', None)
    connection_id = event['requestContext'].get('connectionId', '')

    # Connection request handling (connect / disconnect)
    if route_key == '$connect':
        print(f"Client {connection_id} connected.")
        return {'statusCode': 200, 'body': 'Connected'}
    
    if route_key == '$disconnect':
        print(f"Client {connection_id} disconnected.")
        return {'statusCode': 200, 'body': 'Disconnected'}
    
    # Handling user request
    if route_key == '/send_message':
        body = event.get('body', '{}')
        try:
            body = json.loads(body)
        except json.JSONDecodeError:
            return {
                'statusCode': 400,
                'headers': {'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'Invalid JSON in request body.'})
            }

        user_question = body.get('question', '').strip()

        if not user_question:
            return {
                'statusCode': 400,
                'headers': {'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'message': 'No question provided.'})
            }

        # Stream the answer from Claude 3 model to the WebSocket client in real-time
        for chunk in get_answer_from_claude(user_question):
            try:
                # Send the chunk to the WebSocket client immediately
                api_gateway_management_api.post_to_connection(
                    ConnectionId=connection_id,
                    Data=chunk
                )
                time.sleep(0.1)  # Optional: simulate a slight delay between responses
            except Exception as e:
                print(f"Error sending message to client {connection_id}: {e}")
                return {
                    'statusCode': 500,
                    'body': json.dumps({'error': f'Error sending message: {e}'})
                }

        # Optionally send a final message indicating that streaming is complete
        api_gateway_management_api.post_to_connection(
            ConnectionId=connection_id,
            Data="Streaming complete."
        )

        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'Streaming started'})
        }

    return {
        'statusCode': 400,
        'body': json.dumps({'message': 'Invalid route or action.'})
    }
