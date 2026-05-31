import json
import requests
import uuid 

def generate_chat_id():
    return f"chat_{uuid.uuid4().hex}"

def call_chat_api(question, url="http://127.0.0.1:8080/v1/chat/", chat_id=generate_chat_id()):
    """
    Generates answers for a list of questions using the retrieval API.

    Args:
        questions (list): A list of questions.
        url (str): The URL of the retrieval API endpoint.

    Returns:
        list: A list of dictionaries, where each dictionary contains a question and its corresponding answer.
    """
    
    try:
        response = requests.post(url, json={"chat_id": chat_id, "message": question, "metadata": {}}, timeout=60)
        # print(response.text)

        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
        # answer_data = json.loads(response.text)
        return response
    except Exception as e:
        print(f"Error processing question '{question}': {e}")
        return None
    
def parse_chat_response(response):
    response_text = ""
    try:
        for chunk in response.iter_lines():
            if chunk:
                response_text += chunk.decode("utf-8")
        print("Successfully parsed streaming response")
        # logger.debug("Successfully parsed streaming response")
        return response_text
    except Exception as e:
        print(f"Error calling chat API: {e}")
        raise

def get_parsed_answer_from_chatapi(question, url="http://127.0.0.1:8080/v1/chat/", chat_id=generate_chat_id()):
    response = call_chat_api(question, url="http://127.0.0.1:8080/v1/chat/", chat_id=generate_chat_id())
    answer = parse_chat_response(response)
    return answer