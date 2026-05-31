import json
import os
from typing import List, Dict, Tuple
import pandas as pd  # type: ignore
from openai import OpenAI
import logging
import requests
import uuid
from tqdm.auto import tqdm
from fuzzywuzzy import fuzz  # type: ignore
from dotenv import load_dotenv  # Add this import
import argparse  # Add this import
import time  # Add this import

# from tests.retrieval_api.ret_test_utils import get_parsed_answer_from_chatapi
# from tests.retrieval_api.ret_test_utils import get_parsed_answer_from_chatapi
from ret_test_utils import get_parsed_answer_from_chatapi
# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler())

# Load environment variables from .env file
load_dotenv(dotenv_path="./deployment/.env", verbose=True, override=True)

# Validate OpenAI API key presence
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError(
        "OpenAI API key not found. Please set the OPENAI_API_KEY in your .env file."
    )

client = OpenAI(api_key=OPENAI_API_KEY)


def openai_llm(prompt: str) -> Dict:
    """Generic function to call OpenAI API with a prompt and return JSON response."""
    try:
        logger.debug("Using model: gpt-4o with temperature: 0.0")
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=4096,
            top_p=0.6,
            frequency_penalty=0.3,
            presence_penalty=0.3,
            n=1,
            response_format={"type": "json_object"},
        )
        if response.usage is None:
            logger.error("OpenAI response usage is None")
            raise ValueError("OpenAI response usage is None")
        logger.debug(f"OpenAI API response received. Token count: {response.usage.total_tokens}")
        content = response.choices[0].message.content
        if content is None:
            logger.error("OpenAI response content is None")
            raise ValueError("OpenAI response content is None")
        return json.loads(content)
    except Exception as e:
        logger.error(f"OpenAI API call failed: {str(e)}")
        raise


def llm_as_a_judge(
    question: str, generated_answer: str, ground_truth_answer: str
) -> Dict:
    """Evaluates the generated answer using GPT-4o and returns a detailed score."""
    logger.info("Starting LLM evaluation as judge")
    try:
        logger.debug(
            f"Question length: {len(question)}, Generated answer length: {len(generated_answer)}"
        )
        # Construct evaluation prompt with detailed scoring criteria
        prompt = f"""
        You are an evaluator comparing a generated answer to a ground truth answer for a given question.
        Evaluate the generated answer on the following criteria, providing a score from 0 to 5 (5 being best) and a brief explanation for each:

        Question: {question}
        Ground Truth Answer: {ground_truth_answer}
        Generated Answer: {generated_answer}

        Evaluation Criteria:
        1. Fluency: Assess grammatical correctness, natural language flow, and readability. Consider sentence structure, word choice, and overall clarity.
        2. Relevance: Evaluate how directly and comprehensively the answer addresses the main points of the question, including key concepts and specific details requested.
        3. Coherence: Examine logical flow, organization of ideas, and transitions between concepts. The answer should follow a clear structure without contradictions.
        4. Correctness: Compare factual accuracy with the ground truth, including technical details, numbers, dates, and specific claims made in the response.
        5. Harmfulness: Check for potentially harmful content including bias, discrimination, dangerous advice, or unethical suggestions. Higher score means less harmful content.
        6. Consistency: Analyze alignment between generated and ground truth answers in terms of key points, conclusions, and overall message.

        Provide your evaluation in JSON format:
        {{
            "fluency": {{
                "score": [0-5],
                "explanation": "Example: The response demonstrates proper grammar and natural flow, with clear sentence structure and appropriate vocabulary..."
            }},
            "relevance": {{
                "score": [0-5],
                "explanation": "Example: The answer directly addresses the main question about [topic] and covers key aspects including [specific points]..."
            }},
            "coherence": {{
                "score": [0-5],
                "explanation": "Example: Ideas are presented in a logical sequence, with clear connections between concepts and well-structured paragraphs..."
            }},
            "correctness": {{
                "score": [0-5],
                "explanation": "Example: The technical information matches the ground truth, with accurate details about [specific facts/figures]..."
            }},
            "harmfulness": {{
                "score": [0-5],
                "explanation": "Example: The response maintains neutrality and professionalism, avoiding any biased or potentially harmful content..."
            }},
            "consistency": {{
                "score": [0-5],
                "explanation": "Example: The key points align with the ground truth, maintaining similar conclusions about [specific aspects]..."
            }},
            "overall_score": [0-10],
            "overall_explanation": "Brief summary of strengths and areas for improvement across all criteria..."
        }}
        """

        logger.info("Initiating OpenAI API call for LLM as a judge")
        evaluation = openai_llm(prompt)
        logger.info(
            f"Evaluation completed. Overall score: {evaluation['overall_score']}"
        )
        return evaluation

    except Exception as e:
        logger.error(f"LLM evaluation failed: {str(e)}")
        logger.warning("Returning default zero scores due to evaluation failure")
        # Return default evaluation with zero scores on error
        return {
            "error": str(e),
            "fluency": {"score": 0, "explanation": "Evaluation failed."},
            "relevance": {"score": 0, "explanation": "Evaluation failed."},
            "coherence": {"score": 0, "explanation": "Evaluation failed."},
            "correctness": {"score": 0, "explanation": "Evaluation failed."},
            "harmfulness": {"score": 5, "explanation": "Evaluation failed."},
            "consistency": {"score": 0, "explanation": "Evaluation failed."},
            "overall_score": 0,
            "overall_explanation": "Evaluation failed due to an error.",
        }


def precision_top_k(
    retrieved_contexts: List[str], ground_truth_context: str, k: int = 5
) -> float:
    """Calculates precision@top k for retrieved contexts."""
    logger.debug(f"Calculating precision@{k}")
    try:
        if not ground_truth_context or not retrieved_contexts:
            logger.warning("Empty ground truth or retrieved contexts")
            return 0.0

        k = min(k, len(retrieved_contexts))
        top_k_retrieved = retrieved_contexts[:k]
        relevant_count = 0

        for context in top_k_retrieved:
            if (
                context.lower() in ground_truth_context.lower()
                or ground_truth_context.lower() in context.lower()
            ):
                relevant_count += 1
                continue

            ratio = fuzz.partial_ratio(context.lower(), ground_truth_context.lower())
            if ratio >= 95:
                relevant_count += 1

        logger.debug(
            f"Precision@{k} calculation complete. Score: {float(relevant_count / k)}"
        )
        return float(relevant_count / k) if k > 0 else 0.0

    except Exception as e:
        logger.error(f"Precision calculation failed: {str(e)}")
        return 0.0


def recall_score(
    retrieved_contexts: List[str], ground_truth_answer: str, k: int = 5
) -> float:
    """Calculate recall score by checking if any of the top k retrieved contexts can generate the ground truth answer."""
    try:
        if not ground_truth_answer or not retrieved_contexts:
            return 0.0

        # k = min(k, len(retrieved_contexts))
        # top_k_retrieved = retrieved_contexts[:k]

        combined_contexts = "\n\n\n".join(retrieved_contexts)

        prompt = f"""
            Given a context and a ground truth answer, determine if the context contains sufficient information 
            to generate the ground truth answer. Return a JSON response with a binary score (1 or 0).

            Context: {combined_contexts}
            Ground Truth Answer: {ground_truth_answer}

            Evaluate and respond in this JSON format:
            {{
                "score": [0 or 1],
                "explanation": "Brief explanation of why this context can or cannot generate the answer..."
            }}
            """

        logger.info("Initiating OpenAI API call for recall score")
        evaluation = openai_llm(prompt)
        logger.info(f"Evaluation: {evaluation}")
        
        if evaluation.get("score") == 1:
            return 1.0

        # for context in top_k_retrieved:
        #     prompt = f"""
        #     Given a context and a ground truth answer, determine if the context contains sufficient information 
        #     to generate the ground truth answer. Return a JSON response with a binary score (1 or 0).

        #     Context: {context}
        #     Ground Truth Answer: {ground_truth_answer}

        #     Evaluate and respond in this JSON format:
        #     {{
        #         "score": [0 or 1],
        #         "explanation": "Brief explanation of why this context can or cannot generate the answer..."
        #     }}
        #     """

        #     logger.info("Initiating OpenAI API call for recall score")
        #     evaluation = openai_llm(prompt)
        #     if evaluation.get("score") == 1:
        #         return 1.0

        return 0.0

    except Exception as e:
        logger.error(f"Error in recall_score: {e}")
        return 0.0


def retrieval_as_a_judge(
    question: str, retrieved_contexts: List[str], ground_truth_context: str
) -> Dict:
    """Evaluates retrieval quality by comparing retrieved contexts against a ground truth context string."""
    try:
        # Format retrieved contexts for prompt
        retrieved_contexts_str = "\n".join(
            [f"{i+1}. {ctx}" for i, ctx in enumerate(retrieved_contexts)]
        )

        # Construct evaluation prompt
        prompt = f"""
        You are an evaluator assessing the quality and relevance of retrieved contexts for a given question.
        
        Question: {question}
        
        Retrieved Contexts:
        {retrieved_contexts_str}
        
        Ground Truth Context:
        {ground_truth_context}
        
        Evaluate based on these criteria and provide scores (0-5, where 5 is best) and detailed explanations:
        
        1. Retrieved vs Question (retrieved_vs_question): Assess how well the retrieved contexts provide the necessary information to answer the question, including relevance, completeness, and specificity of information.
        
        2. Ground Truth vs Question (ground_truth_vs_question): Evaluate how comprehensively the ground truth context answers the question, considering information completeness and direct relevance to the query.
        
        3. Retrieved vs Ground Truth (retrieved_vs_ground_truth): Compare the retrieved contexts with the ground truth for information overlap, accuracy, and coverage of key points.
        
        Provide your evaluation in JSON format with detailed explanations for each criterion:
        {{
            "retrieved_vs_question": {{
                "score": [0-5],
                "explanation": "Example: The retrieved contexts [provide/lack] essential information about [specific aspects]. They [successfully/partially/fail to] cover key points such as [X, Y, Z] needed to answer the question. The information is [highly relevant/somewhat relevant/irrelevant] because..."
            }},
            "ground_truth_vs_question": {{
                "score": [0-5],
                "explanation": "Example: The ground truth context [fully/partially/doesn't] addresses the question by providing [specific details]. It contains [comprehensive/limited] information about [key aspects] and [does/doesn't] include all necessary details such as..."
            }},
            "retrieved_vs_ground_truth": {{
                "score": [0-5],
                "explanation": "Example: The retrieved contexts [match/partially align with/differ from] the ground truth in terms of [specific aspects]. Key information such as [X, Y, Z] is [present/missing] in the retrieved contexts compared to ground truth..."
            }},
            "overall_retrieval_score": [0-10],
            "overall_explanation": "Summary highlighting the main strengths and weaknesses of the retrieval performance, including specific examples of what was retrieved well or missed..."
        }}
        """

        logger.info("Initiating OpenAI API call for retrieval as a judge")
        evaluation = openai_llm(prompt)

        # Calculate weighted overall score
        weights = {
            "retrieved_vs_question": 0.4,
            "ground_truth_vs_question": 0.2,
            "retrieved_vs_ground_truth": 0.4,
        }

        weighted_sum = sum(
            evaluation[criterion]["score"] * weights[criterion] for criterion in weights
        )

        max_possible_score = 5 * sum(weights.values())
        overall_score = (weighted_sum / max_possible_score) * 10
        evaluation["overall_retrieval_score"] = round(overall_score, 2)

        return evaluation

    except Exception as e:
        logger.error(f"Error in retrieval_as_a_judge: {e}")
        return {
            "error": str(e),
            "retrieved_vs_question": {"score": 0, "explanation": "Evaluation failed."},
            "ground_truth_vs_question": {
                "score": 0,
                "explanation": "Evaluation failed.",
            },
            "retrieved_vs_ground_truth": {
                "score": 0,
                "explanation": "Evaluation failed.",
            },
            "overall_retrieval_score": 0,
            "overall_explanation": "Retrieval evaluation failed due to an error.",
        }


# def call_chat_api(question: str) -> str:
#     """Call the chat API and return the complete streaming response."""
#     logger.info(f"Calling chat API with question: {question[:100]}...")
    
#     # Add sleep timer
#     time.sleep(1)

#     # Dev API URL
#     url = "http://15.206.100.200:8000/v1/chat"

#     payload = {
#         "chat_id": str(uuid.uuid4()),
#         "query": question,
#         "category": "oil_gas",
#         "llm_model_type": "OPENAI",
#         "is_web_search": "False",
#         "collection_name": "v6_rag",
#         "persist_dir": "v6_persist",
#     }

#     try:
#         response = requests.post(url, json=payload, stream=True)
#         response.raise_for_status()  # Raise exception for bad status codes
#         logger.debug(f"Chat API call successful. Status code: {response.status_code}")
#         response_text = ""

#         for chunk in response.iter_lines():
#             if chunk:
#                 response_text += chunk.decode("utf-8")

#         logger.debug("Successfully parsed streaming response")
#         return response_text
#     except requests.exceptions.RequestException as e:
#         logger.error(f"Error calling chat API: {e}")
#         raise


def parse_streaming_response(response: str) -> Tuple[str, List[str]]:
    """Parse the streaming response to extract answer and context chunks."""
    logger.info("Starting to parse streaming response")
    try:
        # Split the response into individual JSON objects
        json_strings = []
        current_json = ""
        brace_count = 0

        for char in response:
            current_json += char
            if char == "{":
                brace_count += 1
            elif char == "}":
                brace_count -= 1
                if brace_count == 0:
                    json_strings.append(current_json)
                    current_json = ""

        # Parse each JSON object
        answer = ""
        chunks = []

        for json_str in json_strings:
            try:
                obj = json.loads(json_str)
                if obj.get("type") == "answer":
                    answer = obj.get("text", "")
                    logger.debug(f"Found answer with length: {len(answer)}")
                elif obj.get("type") == "context":
                    logger.debug("Processing context chunk")
                    try:
                        # Parse the nested JSON in the text field
                        context_data = json.loads(obj.get("text", "{}"))
                        # Extract chunks from all numbered entries
                        for entry in context_data.values():
                            if isinstance(entry, dict) and "chunk" in entry:
                                chunks.append(entry["chunk"])
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse context JSON: {str(e)}")
                        continue
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON object: {str(e)}")
                continue

        logger.info(
            f"Parsing complete. Found answer ({len(answer)} chars) and {len(chunks)} context chunks"
        )
        return answer, chunks
    except Exception as e:
        logger.error(f"Streaming response parsing failed: {str(e)}")
        raise


def evaluate_response(
    question: str,
    ground_truth_answer: str,
    generated_answer: str,
    retrieved_contexts: List[str],
    ground_truth_context: str,
) -> Dict:
    """Comprehensive evaluation of the response including answer quality and retrieval performance."""
    logger.info("Starting comprehensive response evaluation")
    try:
        logger.debug(f"Processing question: {question[:100]}...")

        answer_evaluation = llm_as_a_judge(
            question, generated_answer, ground_truth_answer
        )
        logger.debug(
            f"Answer evaluation complete. Score: {answer_evaluation['overall_score']}"
        )

        recall = recall_score(retrieved_contexts, ground_truth_answer)
        logger.debug(f"Recall calculation complete. Score: {recall}")

        precision_at_k = precision_top_k(retrieved_contexts, ground_truth_context)
        retrieval_evaluation = retrieval_as_a_judge(
            question, retrieved_contexts, ground_truth_context
        )

        evaluation_result = {
            "question": question,
            "answer_evaluation": answer_evaluation,
            "retrieval_evaluation": retrieval_evaluation,
            "precision_at_k": precision_at_k,
            "recall_score": recall,
            "generated_answer": generated_answer,
            "retrieved_contexts": retrieved_contexts,
        }

        logger.info(
            f"Evaluation complete. Answer score: {answer_evaluation['overall_score']}, Recall: {recall}"
        )

        return evaluation_result

    except Exception as e:
        logger.error(f"Response evaluation failed: {str(e)}")
        return {
            "error": str(e),
            "answer_evaluation": None,
            "retrieval_evaluation": None,
            "precision_at_k": 0.0,
            "recall_score": 0.0,
        }


def main() -> None:
    try:
        # Add argument parser
        parser = argparse.ArgumentParser(description='Evaluate RAG system responses against ground truth.')
        parser.add_argument(
            '--input_file',
            type=str,
            default='./data/tests/retrieval_api/input/v1_ground_truth.xlsx',
            help='Path to the ground truth Excel file (default: ground_truth.xlsx)'
        )
        args = parser.parse_args()

        logger.info("Starting evaluation process")

        if args.input_file.endswith('.xlsx'):
            # Load input data from Excel file
            logger.info(f"Loading data from {args.input_file}")
            df = pd.read_excel(args.input_file, engine="openpyxl")
            required_columns = ["question", "ground_truth_answer", "ground_truth_context"]

            # Validate required columns
            if not all(col in df.columns for col in required_columns):
                missing_cols = set(required_columns) - set(df.columns)
                logger.error(f"Missing required columns in Excel file: {missing_cols}")
                raise ValueError(f"Missing required columns in Excel file: {missing_cols}")

            logger.info(f"Processing {len(df)} questions")
        elif args.input_file.endswith('.json'):
            # Load input data from JSON file
            logger.info(f"Loading data from {args.input_file}")
            with open(args.input_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            df = pd.DataFrame(data)
            required_columns = ["question", "ground_truth_answer", "ground_truth_context"]
            if not all(col in df.columns for col in required_columns):
                missing_cols = set(required_columns) - set(df.columns)
                logger.error(f"Missing required columns in JSON file: {missing_cols}")
                raise ValueError(f"Missing required columns in JSON file: {missing_cols}")
            logger.info(f"Processing {len(df)} questions")
        results = []
        # Initialize lists to store scores for averaging
        llm_judge_scores = []
        precision_scores = []
        retrieval_judge_scores = []
        recall_scores = []
        # Add new score lists
        fluency_scores = []
        relevance_scores = []
        coherence_scores = []
        correctness_scores = []
        harmfulness_scores = []
        consistency_scores = []

        # Process each question and evaluate responses
        for idx, row in tqdm(
            df.iterrows(), total=len(df), desc="Evaluating questions..."
        ):
            try:
                logger.info(f"Processing question {idx + 1}/{len(df)}")
                question = str(row["question"])
                ground_truth_answer = str(row["ground_truth_answer"])
                ground_truth_context = str(row["ground_truth_context"])

                # Get API response and evaluate
                api_response = get_parsed_answer_from_chatapi(question)
                generated_answer, retrieved_chunks = parse_streaming_response(
                    api_response
                )
                retrieved_chunks = [str(chunk) for chunk in retrieved_chunks]

                logger.debug(f"Evaluating response for question {idx + 1}")
                evaluation_result = evaluate_response(
                    question,
                    ground_truth_answer,
                    generated_answer,
                    retrieved_chunks,
                    ground_truth_context,
                )

                # Collect scores for averaging
                llm_judge_scores.append(
                    evaluation_result["answer_evaluation"]["overall_score"]
                )
                precision_scores.append(evaluation_result["precision_at_k"])
                retrieval_judge_scores.append(
                    evaluation_result["retrieval_evaluation"]["overall_retrieval_score"]
                )
                recall_scores.append(evaluation_result["recall_score"])
                
                # Collect new scores
                fluency_scores.append(evaluation_result["answer_evaluation"]["fluency"]["score"])
                relevance_scores.append(evaluation_result["answer_evaluation"]["relevance"]["score"])
                coherence_scores.append(evaluation_result["answer_evaluation"]["coherence"]["score"])
                correctness_scores.append(evaluation_result["answer_evaluation"]["correctness"]["score"])
                harmfulness_scores.append(evaluation_result["answer_evaluation"]["harmfulness"]["score"])
                consistency_scores.append(evaluation_result["answer_evaluation"]["consistency"]["score"])

                results.append(evaluation_result)
                logger.info(f"Successfully processed question {idx + 1}")

            except Exception as row_error:
                logger.error(f"Error processing row {idx + 1}: {row_error}")
                continue

        # Save results in multiple formats
        logger.info("Saving evaluation results...")

        # 1. Save as formatted JSON
        with open("./data/tests/retrieval_api/evaluation_results.json", "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        # 2. Save as Excel with multiple sheets
        with pd.ExcelWriter("./data/tests/retrieval_api/evaluation_results.xlsx", engine="openpyxl") as writer:
            # Main summary sheet
            summary_data = []
            for r in results:
                summary_data.append(
                    {
                        "Question": r["question"],
                        "Generated Answer": r["generated_answer"],
                        "Overall Answer Score": r["answer_evaluation"]["overall_score"],
                        "Overall Retrieval Score": r["retrieval_evaluation"][
                            "overall_retrieval_score"
                        ],
                        "Precision@K": r["precision_at_k"],
                        "Recall Score": r["recall_score"],
                    }
                )
            pd.DataFrame(summary_data).to_excel(
                writer, sheet_name="Summary", index=False
            )

            # Detailed answer evaluation sheet
            answer_data = []
            for r in results:
                eval_data = r["answer_evaluation"]
                answer_data.append(
                    {
                        "Question": r["question"],
                        "Fluency Score": eval_data["fluency"]["score"],
                        "Fluency Explanation": eval_data["fluency"]["explanation"],
                        "Relevance Score": eval_data["relevance"]["score"],
                        "Relevance Explanation": eval_data["relevance"]["explanation"],
                        "Coherence Score": eval_data["coherence"]["score"],
                        "Coherence Explanation": eval_data["coherence"]["explanation"],
                        "Correctness Score": eval_data["correctness"]["score"],
                        "Correctness Explanation": eval_data["correctness"][
                            "explanation"
                        ],
                        "Overall Score": eval_data["overall_score"],
                        "Overall Explanation": eval_data["overall_explanation"],
                    }
                )
            pd.DataFrame(answer_data).to_excel(
                writer, sheet_name="Answer Evaluation", index=False
            )

            # Retrieval evaluation sheet
            retrieval_data = []
            for r in results:
                ret_eval = r["retrieval_evaluation"]
                retrieval_data.append(
                    {
                        "Question": r["question"],
                        "Retrieved vs Question Score": ret_eval[
                            "retrieved_vs_question"
                        ]["score"],
                        "Retrieved vs Question Explanation": ret_eval[
                            "retrieved_vs_question"
                        ]["explanation"],
                        "Ground Truth vs Question Score": ret_eval[
                            "ground_truth_vs_question"
                        ]["score"],
                        "Ground Truth vs Question Explanation": ret_eval[
                            "ground_truth_vs_question"
                        ]["explanation"],
                        "Overall Score": ret_eval["overall_retrieval_score"],
                        "Overall Explanation": ret_eval["overall_explanation"],
                    }
                )
            pd.DataFrame(retrieval_data).to_excel(
                writer, sheet_name="Retrieval Evaluation", index=False
            )

        # Calculate averages with rounding
        average_scores = {
            "average_llm_judge_score": round(
                sum(llm_judge_scores) / len(llm_judge_scores) if llm_judge_scores else 0, 2
            ),
            "average_precision_at_k": round(
                sum(precision_scores) / len(precision_scores) if precision_scores else 0, 2
            ),
            "average_retrieval_judge_score": round(
                sum(retrieval_judge_scores) / len(retrieval_judge_scores)
                if retrieval_judge_scores
                else 0, 2
            ),
            "average_recall_score": round(
                sum(recall_scores) / len(recall_scores) if recall_scores else 0, 2
            ),
            # Add new rounded average scores
            "average_fluency_score": round(
                sum(fluency_scores) / len(fluency_scores) if fluency_scores else 0, 2
            ),
            "average_relevance_score": round(
                sum(relevance_scores) / len(relevance_scores) if relevance_scores else 0, 2
            ),
            "average_coherence_score": round(
                sum(coherence_scores) / len(coherence_scores) if coherence_scores else 0, 2
            ),
            "average_correctness_score": round(
                sum(correctness_scores) / len(correctness_scores) if correctness_scores else 0, 2
            ),
            "average_harmfulness_score": round(
                sum(harmfulness_scores) / len(harmfulness_scores) if harmfulness_scores else 0, 2
            ),
            "average_consistency_score": round(
                sum(consistency_scores) / len(consistency_scores) if consistency_scores else 0, 2
            ),
            "total_questions_evaluated": len(llm_judge_scores),
        }

        # Save averages to JSON file with proper indentation
        with open("./data/tests/retrieval_api/eval_aggregates.json", "w", encoding="utf-8") as f:
            json.dump(average_scores, f, indent=4, ensure_ascii=False)

        logger.info(
            "Evaluation complete. Results saved to evaluation_results.json, evaluation_results.xlsx, and eval_aggregates.json"
        )

    except Exception as e:
        logger.error(f"Error in main: {e}")


if __name__ == "__main__":
    main()