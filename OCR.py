import requests
import base64
from PIL import Image
import io
import os
from dotenv import load_dotenv
import json
import sys
import time
import re
from uuid import uuid4

load_dotenv()
sys.stdout.reconfigure(encoding='utf-8')

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
DEEPSEEK_MODEL_NAME = "deepseek/deepseek-chat"
GEMINI_MODEL_NAME = "google/gemini-flash-1.5-8b"

def get_question_and_options(image_path, api_key, max_retries=3, base_delay=2):
    """
    Extracts the question, diagram information, options, option type and question type from an image using google/gemini-flash-1.5-8b model.
    """

    if not os.path.exists(image_path):
        return "Error: Image file does not exist."

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
                                    **Objective:** Analyze the provided image and extract the question, diagram information, answer options, options type, and question type with high accuracy.

                                    **Instructions:**

                                    **1. Question Identification and Extraction:**
                                        * Identify the core question. Preserve any original formatting (bold, italics, etc.).
                                        * If no question is found, state "Question: No question found."
                                         * **Matrix Match Extraction:**
                                                * If the question is a matrix-match, output the question as a list of two lists, list 1 representing the first column and list 2 the second column. For example:
                                                 ```
                                                 [['A', 'B', 'C'], ['1', '2', '3']]
                                                ```
                                                 * Preserve any original formatting, including bolding, italics, and special characters, within the list.
                                         *   **Paragraph Question Extraction:**
                                                * If the question is a paragraph question, extract the paragraph followed by each of the questions that are associated with the paragraph.
                                                *  Output the paragraph as a single string and the questions as a list.
                                                *   Preserve any original formatting within the paragraph and the questions.
                                    **2. Diagram Description (If Present):**
                                        * Identify the type of diagram (bar, pie, flowchart, etc.).
                                        * Provide a detailed description using Markdown (axes, labels, shapes, etc.).
                                         * If no diagram is present, state "Diagram: No diagram found."
                                    **3. Option Extraction (If Present):**
                                        * Extract each option, including letter and text. Preserve original formatting.
                                        * Format the options using Markdown with bullet points.
                                        * If no options are present state "Options: No options found."
                                    **4. Option Type:**
                                        * Determine if the question is single-select or multi-select.
                                         * If no options are present return `Options Type: No options`.
                                        * If the option type is multi select, explicitly state `"Options Type: Multi-select"`.
                                        * If the option type is single select, explicitly state `"Options Type: Single-select"`.
                                    **5. Question Type Extraction:**
                                        * Based on the question identify the type of question. Possible question types include:
                                               - Multiple Choice Question
                                               - Numerical Question
                                               - Open Ended Question
                                               - Diagram Question
                                               - Matrix Match Question
                                               - Paragraph Question
                                        * If no question is found return **"Question Type: No question"**

                                    **Output Format:**
                                        *   Start with: **Question Extraction:**
                                        *   Follow with the extracted question in Markdown format or "Question: No question found."
                                        *   Start a new line with **Diagram Description:**
                                        *   Follow with a detailed diagram description in Markdown format or "Diagram: No diagram found."
                                        *   Start a new line with **Option Extraction:**
                                        *   Follow with the extracted options in Markdown format or "Options: No options found.".
                                        *   Start a new line with **Option Type:**
                                        *   Follow with the options type.
                                        *    Start a new line with **Question Type:**
                                        *    Follow with the question type.
                                        *   Do not include any additional introductory or concluding remarks.
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
                "max_tokens": 8000
            }

            response = requests.post(OPENROUTER_API_URL, headers=headers, json=payload, timeout=30)

            if response.status_code == 200:
                json_response = response.json()
                if json_response and 'choices' in json_response and json_response['choices']:
                    extracted_content = json_response['choices'][0]['message']['content']
                    parts = extracted_content.split("Diagram Description:")
                    if len(parts) > 1:
                        question_and_options = parts[0].strip()
                        diagram_and_options = parts[1].strip()
                        parts2 = diagram_and_options.split("Option Extraction:")
                        if len(parts2) > 1:
                            diagram = parts2[0].strip()
                            options_and_type = parts2[1].strip()
                            parts3 = options_and_type.split("Option Type:")
                            if len(parts3) > 1:
                                options = parts3[0].strip()
                                options_and_question = parts3[1].strip()
                                parts4 = options_and_question.split("Question Type:")
                                if len(parts4) > 1:
                                    options_type = parts4[0].strip()
                                    question_type = parts4[1].strip()
                                    return {"question": question_and_options, "diagram": diagram, "options": options, "options_type": options_type, "question_type": question_type}
                                else:
                                   options_type = parts4[0].strip()
                                   return {"question": question_and_options, "diagram": diagram, "options": options, "options_type": options_type, "question_type": ""}
                            else:
                                options = parts3[0].strip()
                                return {"question": question_and_options, "diagram": diagram, "options": options, "options_type": "", "question_type": ""}
                        else:
                            diagram = parts2[0].strip()
                            return {"question": question_and_options, "diagram": diagram, "options": "", "options_type": "", "question_type": ""}
                    else:
                        question_and_options = parts[0].strip()
                        return {"question": question_and_options, "diagram": "", "options": "", "options_type": "", "question_type": ""}
                else:
                  print("Error: No valid response from Gemini model")
                  return "Error: No valid response from Gemini model"
            else:
              print(f"Error: HTTP Request failed (Gemini model): {response.status_code}")
              return f"Error: HTTP Request failed (Gemini model): {response.status_code}"


        except requests.exceptions.RequestException as e:
            if response and response.status_code == 429:
                wait_time = base_delay * (2**attempt)
                print(f"Rate limited (google/gemini-flash-1.5-8b model). Retrying in {wait_time} seconds (attempt {attempt + 1}/{max_retries})...")
                time.sleep(wait_time)
                continue
            print(f"Error: HTTP Request failed (google/gemini-flash-1.5-8b model): {e}")
            return f"Error: HTTP Request failed (google/gemini-flash-1.5-8b model): {e}"
        except Exception as e:
            print(f"Error: An unexpected error occurred (google/gemini-flash-1.5-8b model): {e}")
            return f"Error: An unexpected error occurred (google/gemini-flash-1.5-8b model): {e}"
    
    print("Error: Max retries reached (google/gemini-flash-1.5-8b model), unable to get a response.")
    return "Error: Max retries reached (google/gemini-flash-1.5-8b model), unable to get a response."


def get_answer_from_question(question, diagram, options, options_type, question_type, api_key, max_retries=3, base_delay=2):
    """
    Answers the extracted question using deepseek/deepseek-chat model and reformats the response using google/gemini-flash-1.5-8b model.
    """
    for attempt in range(max_retries):
        try:
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }

            deepseek_payload = {
                "model": DEEPSEEK_MODEL_NAME,
                "messages": [
                    {
                        "role": "user",
                        "content": (
                            "Solve the following problem step-by-step. Provide a detailed explanation of each step, including all necessary equations (if applicable).\n\n"
                            "**Context:**\n"
                            f"* Consider this diagram information when solving the question:\n"
                            f"    {diagram}\n"
                            f"* These are the possible answer options:\n"
                            f"    {options}\n"
                            f"* This is the option type for this question:\n"
                            f"    {options_type}\n"
                            f"* This is the question type:\n"
                            f"    {question_type}\n\n"
                            "**Format Instructions:**\n\n"
                            "*   **Equations:** Enclose all mathematical equations using the delimiter `$$...$$`. For example: $$E=mc^2$$\n"
                            "*   **Reasoning Step:** Before each step, clearly state the reasoning behind it, starting with 'Reasoning Step:'.\n"
                            "*  **Paragraph Question Logic:** If the question type is \"Paragraph Question\" use the following logic:\n"
                            "      * First extract the paragraph and questions from the question string, if this fails assume the question is the paragraph and there are no questions.\n"
                            "      * If extraction is successful:\n"
                            "        *  Try to extract the paragraph, if this fails assume the paragraph is an empty string\n"
                            "        *  Try to extract the questions, if this fails assume there are no questions.\n"
                            f"        * The paragraph is: {question.split('Paragraph:')[1].split('Questions:')[0].strip() if 'Paragraph:' in question and 'Questions:' in question else ''}\n"
                            f"        * The questions are: {question.split('Questions:')[1].strip() if 'Questions:' in question else ''}\n"
                            "       * For each question, use the paragraph for context.\n"
                            "        * Answer each question individually, using the paragraph to provide a response.\n"
                            "      * If extraction is unsuccessful:\n"
                            "        * Assume the question is the paragraph and there are no questions.\n\n"
                            "*   **Matrix Match Logic:** If the question type is \"Matrix Match Question\" use the following logic:\n"
                            "        *   Use a step-by-step approach, matching each item from the first list with the corresponding item from the second list.\n"
                            "        *  State your reasoning behind each match.\n"
                            "        *   Format your answer as a list of tuples, showing the matches. For example: `[('A', '1'), ('B', '2'), ('C', '3')]`\n"
                            "*   **Step-by-step:** Use a numbered list to structure the explanation of your solution process.\n"
                            "*   **Option Analysis:** If options (A, B, C, D) are provided:\n"
                            "    * For **single-select** questions, rigorously analyze each option using your calculations or reasoning. Clearly state whether each option is correct or incorrect and explain why. Select only one option.\n"
                            "    * For **multi-select** questions, analyze each option and explicitly state if it's correct or incorrect, explaining the reasoning. Select all correct options.\n"
                            "*   **Final Answer:**\n"
                            "    * For single select questions, when options are available, select one of the provided options as the final answer based on your analysis. State your answer using the format: 'The correct answer is: [option letter]'.\n"
                            "    * For multi select questions, list all of the correct options. State the answer using the format: 'The correct answers are: [option letters]'.\n"
                            "    * For matrix match questions, provide your answer as list of tuples.\n"
                            "    * For paragraph questions, answer each question individually.\n"
                            "    * For numerical questions provide the numerical answer along with the correct units.\n"
                            "    * For open ended questions, answer in a paragraph.\n\n"
                            "**Example Output Structure:**\n"
                            "**Assumptions:** [Assumptions made to solve the problem]\n"
                            "For Paragraph Questions:\n"
                            "    **Paragraph:** [Extracted paragraph]\n"
                            "    **Question 1:** [Answer to Question 1]\n"
                            "    **Question 2:** [Answer to Question 2]\n"
                            "    ...\n\n"
                            "For Matrix Match Questions:\n"
                            "    **Reasoning Step:** [Reasoning]\n"
                            "    **Steps:**\n"
                            "      1. [Explanation of Step 1]\n"
                            "      2. [Explanation of Step 2]\n"
                            "    **Final Answer:** [List of tuples]\n\n"
                            "For other questions:\n"
                            "    **Reasoning Step:** [Reasoning]\n"
                            "    **Steps:**\n"
                            "    1. [Explanation of Step 1 including equations or reasoning]\n\n"
                            "    **Reasoning Step:** [Reasoning]\n"
                            "    2. [Explanation of Step 2 including equations or reasoning]\n"
                            "    ...\n\n"
                            "    **Option Analysis Example:**\n"
                            "    A: [Correct or Incorrect, Explanation]\n"
                            "    B: [Correct or Incorrect, Explanation]\n"
                            "    C: [Correct or Incorrect, Explanation]\n"
                            "    D: [Correct or Incorrect, Explanation]\n\n"
                            "**Final Answer Example:**\n"
                            "   * Single Select Question: The correct answer is: [option letter]\n"
                            "   * Multi Select Question: The correct answers are: [option letters]\n"
                            "    * Matrix Match Question: [List of tuples]\n"
                            "    * Paragraph Question:  [Answer to each question]\n"
                            "   * Numerical Question: [Numerical Answer]\n"
                            "   * Open Ended Question: [Answer paragraph]\n\n"
                            "**Constraints:**\n"
                            "* Do not include any introductory or concluding remarks. Start directly with the solution.\n"
                            "* If multiple options are given always choose one or more of the given options.\n"
                            "* If no options are given, just solve the question without selecting an option.\n"
                            "* For Paragraph questions only use the given paragraph to answer each of the given questions.\n\n"
                            f"**Question:** {question}"
                        )
                    }
                ],
                "max_tokens": 8000
            }

            response = requests.post(OPENROUTER_API_URL, headers=headers, json=deepseek_payload, timeout=30)
            if response.status_code == 200:
                json_response = response.json()
                if json_response and 'choices' in json_response and json_response['choices']:
                    deepseek_answer = ""
                    for i in range(len(json_response['choices'])):
                        deepseek_answer += json_response['choices'][i]['message']['content'] + "\n"
                    deepseek_answer = re.sub(r'\\\((.*?)\\\)', r'\1', deepseek_answer)
                else:
                    print("Error: No valid response from Deepseek model")
                    return "Error: No valid response from Deepseek model"
            else:
                print(f"Error: HTTP Request failed (Deepseek model): {response.status_code}")
                return f"Error: HTTP Request failed (Deepseek model): {response.status_code}"
            
            gemini_payload = {
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
                            Here is the text to format: {deepseek_answer}
                        """
                    }
                ],
                "max_tokens": 8000
            }

            gemini_response = requests.post(OPENROUTER_API_URL, headers=headers, json=gemini_payload, timeout=30)
            if gemini_response.status_code == 200:
                gemini_json_response = gemini_response.json()
                if gemini_json_response and 'choices' in gemini_json_response and gemini_json_response['choices']:
                    corrected_answer = gemini_json_response['choices'][0]['message']['content']
                    corrected_answer = re.sub(r'(?<!\$)\$([^$]+?)\$(?!\$)', r' $\1$ ', corrected_answer)
                    corrected_answer = re.sub(r'\$\$([^$]+?)\$\$', r'$$\1$$', corrected_answer)
                    corrected_answer = re.sub(r'  +', ' ', corrected_answer)
                    corrected_answer = re.sub(r'\$\$\s*([^$]+?)\s*\$\$', r'$$\1$$', corrected_answer)
                    corrected_answer = re.sub(r'\\begin\{([^}]+)\}(.*?)\\end\{\1\}', r'\\begin{\1}\2\\end{\1}', corrected_answer, flags=re.DOTALL)
                    
                    return corrected_answer
                else:
                    print("Error: No valid response from Gemini model")
                    return "Error: No valid response from Gemini model"
            else:
                print(f"Error: HTTP Request failed (Gemini model): {gemini_response.status_code}")
                return f"Error: HTTP Request failed (Gemini model): {gemini_response.status_code}"

        except requests.exceptions.RequestException as e:
            if response and response.status_code == 429:
                wait_time = base_delay * (2**attempt)
                print(f"Rate limited (Deepseek model). Retrying in {wait_time} seconds (attempt {attempt + 1}/{max_retries})...")
                time.sleep(wait_time)
                continue
            print(f"Error: HTTP Request failed (Deepseek model): {e}")
            return f"Error: HTTP Request failed (Deepseek model): {e}"
        except Exception as e:
            print(f"Error: An unexpected error occurred (Deepseek model): {e}")
            return f"Error: An unexpected error occurred (Deepseek model): {e}"

    print("Error: Max retries reached (Deepseek model), unable to get an answer.")
    return "Error: Max retries reached (Deepseek model), unable to get an answer."


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python OCR.py <image_path> <hyperbolic_api_key> <openrouter_api_key>")
        sys.exit(1)

    image_file_path = sys.argv[1]
    hyperbolic_api_key = sys.argv[2]
    openRouterApiKey = sys.argv[3]

    question_and_options = get_question_and_options(image_file_path, openRouterApiKey)
    if "Error:" in question_and_options:
        print(question_and_options)
    else:
        if isinstance(question_and_options, dict):
                question_string = question_and_options.get("question", "").strip()
                diagram_string = question_and_options.get("diagram", "").strip()
                options_string = question_and_options.get("options", "").strip()
                options_type = question_and_options.get("options_type", "").strip()
                question_type = question_and_options.get("question_type", "").strip()
                
                answer = get_answer_from_question(question_string, diagram_string, options_string, options_type, question_type, openRouterApiKey)
                if "Error:" in answer:
                    print(answer)
                else:
                    print(f"{diagram_string}\n\n{answer}")
        else:
            print(question_and_options)