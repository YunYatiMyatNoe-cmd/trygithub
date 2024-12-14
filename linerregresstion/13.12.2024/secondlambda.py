import json
import boto3

# Initialize Bedrock client
client = boto3.client("bedrock-runtime", region_name="us-east-1")

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
        response = client.invoke_model(
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


def lambda_handler(event, context):
    # Extract connection and message information
    connection_id = event['requestContext']['connectionId']
    domain_name = event['requestContext']['domainName']
    stage = event['requestContext']['stage']
    body = json.loads(event.get('body', '{}'))
    
    # The user question is passed in the body under the key 'question'
    user_question = body.get('question', '').strip()

    # Ensure that the question is not empty before proceeding
    if not user_question:
        return {
            'statusCode': 400,
            'body': json.dumps({"error": "No question provided."})
        }

    # Initialize API Gateway Management API client
    api_gateway = boto3.client('apigatewaymanagementapi', endpoint_url=f'https://dpyttqqe2e.execute-api.ap-northeast-1.amazonaws.com/production')

    # Send the question back to the client (confirmation or feedback message)
    try:
        api_gateway.post_to_connection(
            ConnectionId=connection_id,
            Data=json.dumps({"message": f"Received your question: {user_question}"})
        )
    except Exception as e:
        print(f"Error sending message: {e}")

    # Call Claude to generate an answer for the user's message (question)
    answer = get_answer_from_claude(user_question)

    # Send the generated answer back to the WebSocket client
    try:
        api_gateway.post_to_connection(
            ConnectionId=connection_id,
            Data=json.dumps({"message": f"Claude's answer: {answer}"})
        )
    except Exception as e:
        print(f"Error sending answer to client: {e}")

    # Return the response with the answer (if necessary)
    return {
        'statusCode': 200,
        'body': json.dumps({"answer": answer})
    }
