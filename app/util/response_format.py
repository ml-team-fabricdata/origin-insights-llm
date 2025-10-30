def extract_response(response) -> str:
    if hasattr(response, 'message'):
        message = response.message
        if isinstance(message, dict) and 'content' in message:
            return message['content'][0]['text']
        return str(message)

    if isinstance(response, dict):
        if 'content' in response and isinstance(response['content'], list):
            return response['content'][0].get('text', '')
        if 'message' in response:
            return response['message']

    return str(response)
