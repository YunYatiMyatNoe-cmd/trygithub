def handle_user_question(user_question, data):
    # Categorize the question
    question_type = categorize_question(user_question)
    
    # Generate relevant data and prompt
    if question_type == "prediction":
        relevant_data = {
            "last_week_data": data.get("last_week_data", ""),
            "interval_data": data.get("interval_data", ""),
            "weather_data": data.get("weather_data", ""),
        }
        prompt = f"""
        You are an assistant analyzing building usage. Use only prediction-related data:
        - Historical data: {relevant_data['last_week_data']}
        - Recent trends: {relevant_data['interval_data']}
        - Weather forecast: {relevant_data['weather_data']}
        
        Question: {user_question}
        Answer with predicted numbers and reasoning.
        """
    else:
        relevant_data = {
            "current_data": data.get("current_data", ""),
            "suspicious_data": data.get("suspicious_data", ""),
            "project_times": data.get("project_times", ""),
        }
        prompt = f"""
        You are an assistant analyzing building usage. Use only current or past data:
        - Real-time data: {relevant_data['current_data']}
        - Suspicious activity: {relevant_data['suspicious_data']}
        - Historical usage: {relevant_data['project_times']}
        
        Question: {user_question}
        Answer accurately without making predictions.
        """
    
    # Send prompt to Claude
    try:
        print(f"Generated Prompt: {prompt}")
        response = bedrock_client.invoke_model(
            modelId="anthropic.claude-3-sonnet-20240229-v1:0",
            body=json.dumps({"messages": [{"role": "user", "content": prompt}]}),
            contentType='application/json'
        )
        response_body = json.loads(response['body'].read().decode('utf-8'))
        return response_body.get('content', "Unable to process your question.")
    except Exception as e:
        print(f"Error querying Claude: {e}")
        return "There was an error processing your question."
