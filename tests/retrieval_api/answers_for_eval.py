import json
import requests
import uuid

def generate_chat_id():
    return f"chat_{uuid.uuid4().hex}"


def get_answers(questions, url="http://127.0.0.1:8000/generate_answer"):
    """
    Generates answers for a list of questions using the retrieval API.

    Args:
        questions (list): A list of questions.
        url (str): The URL of the retrieval API endpoint.

    Returns:
        list: A list of dictionaries, where each dictionary contains a question and its corresponding answer.
    """
    answers = []
    chat_id = generate_chat_id()
    for question in questions:
        try:
            response = requests.post(url, json={"chat_id": chat_id, "message": question, "metadata": {}}, timeout=60)
            # print(response.text)

            response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
            # answer_data = json.loads(response.text)
            # answer_data = response.json()
            # print(answer_data)
            # answers.append({"question": question, "answer": answer_data.get("answer", "No answer found.")})
            response_text = response.text
            
            # Parse the concatenated JSON objects
            decoder = json.JSONDecoder()
            pos = 0
            parsed_objects = []
            if response_text.strip(): # Ensure there's content to parse
                while pos < len(response_text):
                    try:
                        obj, new_pos = decoder.raw_decode(response_text, pos)
                        parsed_objects.append(obj)
                        pos = new_pos
                    except json.JSONDecodeError as e:
                        print(f"JSON decoding error at pos {pos} for question '{question}': {e}")
                        # Log the problematic part: print(f"Problematic JSON segment: {response_text[pos:pos+100]}")
                        break 
            
            extracted_answer = "No answer found in the expected format."
            for res_obj in parsed_objects:
                if isinstance(res_obj, dict) and res_obj.get("type") == "answer":
                    extracted_answer = res_obj.get("text", "Answer text missing in 'answer' type object.")
                    break 
            answers.append({"question": question, "answer": extracted_answer})
        except requests.exceptions.RequestException as e:
            print(f"Error processing question '{question}': {e}")
            answers.append({"question": question, "answer": "Error: Could not retrieve answer."})
            answers.append({"question": question, "answer": f"Error: Could not retrieve answer. ({type(e).__name__})"})
        except Exception as e: # Catch any other unexpected errors
            print(f"An unexpected error occurred for question '{question}': {e}")
            answers.append({"question": question, "answer": f"Error: Unexpected error. ({type(e).__name__})"})
        except requests.exceptions.RequestException as e:
            print(f"Error processing question '{question}': {e}")
            answers.append({"question": question, "answer": "Error: Could not retrieve answer."})
    return answers


def save_answers(answers, output_file="answers.json"):
    """
    Saves the questions and answers to a JSON file.

    Args:
        answers (list): A list of dictionaries, where each dictionary contains a question and its corresponding answer.
        output_file (str): The path to the output JSON file.
    """
    import os

    # Create the directory if it doesn't exist
    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    # Save the answers to the JSON file
    with open(output_file, "w") as f:
        json.dump(answers, f, indent=4)
    print(f"Answers saved to {output_file}")


if __name__ == "__main__":
    # Example usage:
    questions = [
        "Give me info about well-bore geometry of well GM2",
        "What does IBDP Basin scale simulations in nexus software tells about CO2 injection!!??",
        "well wise drilling permits and their timelines in IBDP field",
        "when were drilling permits obtained for ccs1, GM2 and CCS2 wells?",
        "summary of reservoir modelling and iterations of IBDP",
        "what are the updates done to static model in 2020 IBDP \
        fieldwhat are the updates done to static model in 2020 IBDP field",
        "Depth range of geophones used for seismic monitoring in IBDP field",
        "Give info about well bore geometry of well CCS1",
        "Give info about well bore geometry of well GM1",
        "Give info about well bore geometry of well VW1",
        "Give a summary of monitoring programme in well CCS1?",
        "Give a summary of injection fluid compatibility in well CCS1",
        "Give summary of hydraulic integrity testing in well VW1",
        "summary of preparation of monitoring well design of well VW1?",
        "summary of preparation of monitoring well design of well VW1?",
        "What does IBDP Basin scale simulations in nexus software tells about CO2 injection!!??",
        "give detailed explaination about PNX formation fluid analysis results?",
        "info about drilling permits in IBDP field?"
        "Depth range of geophones used for seismic monitoring in IBDP field.",
        "summary of reservoir modelling and iterations of IBDP",
        "what are the insights of mechanical wellbore integrity tests of well ccs1?",
        "What are the insights from PNX data Interpretation?",
        "give me wellbore integrity diagram of well CCS1",
    ]
    retrieval_url = "http://localhost:8080/v1/chat/"
    answers = get_answers(questions, url=retrieval_url)
    output_file_path = "./data/tests/retrieval_api/answers.json"
    save_answers(answers, output_file_path)