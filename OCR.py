import requests
import base64
from PIL import Image
import io
import os
from dotenv import load_dotenv
import sys
import time
import re
import json

load_dotenv()
sys.stdout.reconfigure(encoding='utf-8')

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
DEEPSEEK_MODEL_NAME = "deepseek/deepseek-chat"
GEMINI_MODEL_NAME = "google/gemini-flash-1.5-8b"

def get_question_from_image(image_path, api_key, max_retries=3, base_delay=2):
    """
    Extracts the full question (including diagram, options, etc.) from an image using Google Gemini.
    """
    if not os.path.exists(image_path):
        return json.dumps({"error": "Image file does not exist."})

    for attempt in range(max_retries):
        try:
            image = Image.open(image_path)
            if image.mode == "RGBA":
                image = image.convert("RGB")

            image_buffer = io.BytesIO()
            image.save(image_buffer, format="PNG")
            image_base64 = base64.b64encode(image_buffer.getvalue()).decode("utf-8")
            image_url = f"data:image/png;base64,{image_base64}"

            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }

            payload = {
                "model": GEMINI_MODEL_NAME,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": """
                                    **Objective:** Analyze the provided image and extract the full question, including any diagrams, options, or additional context. Provide detailed information as if preparing the input for another model.

                                    **Instructions:**
                                    1. **Question Extraction:** Identify the core question from the image. Preserve any formatting (bold, italics, etc.).
                                    2. **Diagram Description:** If the image contains a diagram, provide a detailed description, including axes, labels, shapes, and any other relevant details.
                                    3. **Options Extraction:** If the question has multiple-choice options, extract each option and preserve the formatting.
                                    4. **Equations and Formulas:** Ensure all equations and formulas are enclosed in `$` for inline equations and `$$` for display equations.
                                    5. **Output Format:** Provide the extracted information in a clear and structured format.
                                """
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": image_url
                                }
                            }
                        ]
                    }
                ],
                "max_tokens": 12000  # Increased max_tokens for Gemini
            }

            response = requests.post(OPENROUTER_API_URL, headers=headers, json=payload, timeout=30)
            response.raise_for_status()  # Raise an error for bad status codes
            json_response = response.json()
            if json_response and 'choices' in json_response and json_response['choices']:
                extracted_question = json_response['choices'][0]['message']['content']
                return json.dumps({"question": extracted_question})
            else:
                return json.dumps({"error": "No valid response from Gemini model"})

        except requests.exceptions.RequestException as e:
            if response and response.status_code == 429:
                wait_time = base_delay * (2**attempt)
                print(f"Rate limited (Gemini model). Retrying in {wait_time} seconds (attempt {attempt + 1}/{max_retries})...")
                time.sleep(wait_time)
                continue
            return json.dumps({"error": f"HTTP Request failed (Gemini model): {e}"})
        except Exception as e:
            return json.dumps({"error": f"An unexpected error occurred (Gemini model): {e}"})

    return json.dumps({"error": "Max retries reached (Gemini model), unable to get a response."})


def get_answer_from_question(question, api_key, max_retries=3, base_delay=2):
    """
    Answers the extracted question using DeepSeek model.
    """
    for attempt in range(max_retries):
        try:
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }

            payload = {
                "model": DEEPSEEK_MODEL_NAME,
                "messages": [
                    {
                        "role": "user",
                        "content": f"""
                            **Objective:** Answer the following question step-by-step. Stay focused on the task and avoid unnecessary explanations.

                            **Question:** {question}

                            **Instructions:**
                            1. Provide a detailed step-by-step explanation.
                            2. If options are provided, analyze each option and select the correct one(s).
                            3. Format the answer using Markdown.
                            4. Do not include any introductory or concluding remarks. Start directly with the solution.
                            5. If the question involves calculations, show all steps clearly.
                            6. If the question is theoretical, provide a concise and accurate explanation.
                            7. Ensure all equations and formulas are enclosed in `$` for inline equations and `$$` for display equations.
                        """
                    }
                ],
                "max_tokens": 12000  # Increased max_tokens for DeepSeek
            }

            response = requests.post(OPENROUTER_API_URL, headers=headers, json=payload, timeout=30)
            response.raise_for_status()  # Raise an error for bad status codes
            json_response = response.json()
            if json_response and 'choices' in json_response and json_response['choices']:
                answer = json_response['choices'][0]['message']['content']
                return json.dumps({"answer": answer})
            else:
                return json.dumps({"error": "No valid response from DeepSeek model"})

        except requests.exceptions.RequestException as e:
            if response and response.status_code == 429:
                wait_time = base_delay * (2**attempt)
                print(f"Rate limited (DeepSeek model). Retrying in {wait_time} seconds (attempt {attempt + 1}/{max_retries})...")
                time.sleep(wait_time)
                continue
            return json.dumps({"error": f"HTTP Request failed (DeepSeek model): {e}"})
        except Exception as e:
            return json.dumps({"error": f"An unexpected error occurred (DeepSeek model): {e}"})

    return json.dumps({"error": "Max retries reached (DeepSeek model), unable to get an answer."})


def format_answer_with_gemini(answer, api_key, max_retries=3, base_delay=2):
    """
    Reformats the answer using Google Gemini for proper Markdown rendering.
    """
    for attempt in range(max_retries):
        try:
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }

            payload = {
                "model": GEMINI_MODEL_NAME,
                "messages": [
                    {
                        "role": "user",
                        "content": f"""
                            Correct any formatting errors in the following text and reformat it so it's properly rendered on an educational website using markdown. Use the following guidelines:
                                1. Use ``` only for actual code blocks, not for equations
                                2. Use ** for bold text
                                3. Use * for italics
                                4. Use - for bullet points
                                5. For section headers:
                                    - Use ## for main sections
                                    - Use ### for subsections
                                    - Ensure proper spacing before and after headers
                                6. Separate chemical structures from text using clear labels
                                7. For mathematical equations:
                                    - Use $$...$$ for display equations
                                    - Use $...$ for inline equations
                                    - Never use code blocks (```) for equations
                                    - Preserve all LaTeX commands and environments
                                    - Ensure proper spacing around equations
                            Here is the text to format: {answer}
                        """
                    }
                ],
                "max_tokens": 12000  # Increased max_tokens for Gemini
            }

            response = requests.post(OPENROUTER_API_URL, headers=headers, json=payload, timeout=30)
            response.raise_for_status()  # Raise an error for bad status codes
            json_response = response.json()
            if json_response and 'choices' in json_response and json_response['choices']:
                formatted_answer = json_response['choices'][0]['message']['content']
                return json.dumps({"formatted_answer": formatted_answer})
            else:
                return json.dumps({"error": "No valid response from Gemini model"})

        except requests.exceptions.RequestException as e:
            if response and response.status_code == 429:
                wait_time = base_delay * (2**attempt)
                print(f"Rate limited (Gemini model). Retrying in {wait_time} seconds (attempt {attempt + 1}/{max_retries})...")
                time.sleep(wait_time)
                continue
            return json.dumps({"error": f"HTTP Request failed (Gemini model): {e}"})
        except Exception as e:
            return json.dumps({"error": f"An unexpected error occurred (Gemini model): {e}"})

    return json.dumps({"error": "Max retries reached (Gemini model), unable to format the answer."})


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print(json.dumps({"error": "Usage: python OCR.py <image_path> <hyperbolic_api_key> <openrouter_api_key>"}))
        sys.exit(1)

    image_file_path = sys.argv[1]
    hyperbolic_api_key = sys.argv[2]
    openRouterApiKey = sys.argv[3]

    # Step 1: Extract the full question using Gemini
    extraction_result = get_question_from_image(image_file_path, openRouterApiKey)
    if "error" in json.loads(extraction_result):
        print(extraction_result)
        sys.exit(1)

    question = json.loads(extraction_result)["question"]

    # Step 2: Answer the question using DeepSeek
    answer_result = get_answer_from_question(question, openRouterApiKey)
    if "error" in json.loads(answer_result):
        print(answer_result)
        sys.exit(1)

    answer = json.loads(answer_result)["answer"]

    # Step 3: Format the answer using Gemini
    formatted_result = format_answer_with_gemini(answer, openRouterApiKey)
    if "error" in json.loads(formatted_result):
        print(formatted_result)
        sys.exit(1)

    formatted_answer = json.loads(formatted_result)["formatted_answer"]
    print(json.dumps({"formatted_answer": formatted_answer}))