import boto3
import json
import time

# Create Bedrock Runtime client
client = boto3.client("bedrock-runtime", region_name="us-east-1")

# Create API Gateway Management API client for WebSocket communication
api_gateway_management_api = boto3.client(
    'apigatewaymanagementapi',
    endpoint_url=f'https://dpyttqqe2e.execute-api.ap-northeast-1.amazonaws.com/production'  # Use https
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
                "content": prompt  
            }
        ],
    }

    request = json.dumps(native_request)

    # Invoke the model with the request and stream the response
    try:
        # Attempting streaming with Bedrock
        streaming_response = client.invoke_model_with_response_stream(
            modelId=model_id, body=request
        )

        # Process the streamed response
        for event in streaming_response["body"]:
            chunk = json.loads(event["chunk"]["bytes"])
            if chunk.get("type") == "content_block_delta":
                text = chunk.get("delta", {}).get("text", "")
                if text:
                    yield text
                    time.sleep(0.1)  # Simulating delay to mimic real-time streaming

    except Exception as e:
        print(f"Error while streaming from Bedrock: {e}")
        yield "Sorry, there was an issue processing your request."

# Lambda handler function
def lambda_handler(event, context):
    route_key = event.get('requestContext', {}).get('routeKey', None)
    connection_id = event['requestContext'].get('connectionId', '')  # Correctly get connectionId from event

    # Connection request handling (connect / disconnect)
    if route_key == '$connect':
        print(f"Client {connection_id} connected.")
        return {'statusCode': 200, 'body': 'Connected'}
    
    if route_key == '$disconnect':
        print(f"Client {connection_id} disconnected.")
        return {'statusCode': 200, 'body': 'Disconnected'}
    
    # Extract the message/question sent by the frontend
    question = event.get('queryStringParameters', {}).get('question', '').strip()

    if not question:
        return {'statusCode': 400, 'body': 'Invalid request, no question provided'}

    # Streaming responses to the frontend via SSE
    response_data = ""
    try:
        for text_chunk in get_answer_from_claude(question):
            response_data += text_chunk
            # Ensure you're using the correct connectionId
            api_gateway_management_api.post_to_connection(
                ConnectionId=connection_id,
                Data=json.dumps({"text": response_data}),
            )
        return {'statusCode': 200, 'body': 'Message sent'}

    except Exception as e:
        print(f"Error sending message: {e}")
        return {'statusCode': 500, 'body': 'Failed to get response'}
