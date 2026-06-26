import json
from smart_classroom.utils.ai_client import call_gemini_api_with_fallback

def generate_test_questions(topic, question_type="mixed", num_questions=3, difficulty="medium"):
    """
    Calls the Gemini API to generate a list of coding and/or MCQ questions on a given topic for a Test.
    """
    system_instruction = (
        "You are an expert computer science instructor and educational content creator. Your task is to "
        "generate high-quality assessment questions for coding and programming tests. These questions can be "
        "either multiple-choice quiz questions (MCQs) or coding questions with structured automated test cases."
    )
    
    # Restrict Gemini prompt based on selected question type
    strict_type_instruction = ""
    if question_type == "mcq":
        strict_type_instruction = "IMPORTANT: You MUST generate ONLY MCQ questions (question_type must be 'mcq'). DO NOT generate any coding questions."
    elif question_type == "coding":
        strict_type_instruction = "IMPORTANT: You MUST generate ONLY coding questions (question_type must be 'coding'). DO NOT generate any multiple choice / MCQ questions."
    else:
        strict_type_instruction = "You can generate a mix of MCQ (question_type: 'mcq') and Coding (question_type: 'coding') questions."

    user_message = (
        f"Generate {num_questions} questions about '{topic}' at a {difficulty} difficulty level.\n"
        f"{strict_type_instruction}\n\n"
        "CRITICAL FORMAT RULES:\n"
        "1. For MCQ (question_type: 'mcq') questions:\n"
        "   - You MUST fill option1, option2, option3, option4 with the answer choices.\n"
        "   - You MUST set correct_answer to exactly one of 'option1', 'option2', 'option3', or 'option4' representing the correct choice. Do NOT leave it empty.\n"
        "   - Set expected_function_name, starter_code, reference_solution to \"none\" and test_cases to [].\n"
        "2. For Coding (question_type: 'coding') questions:\n"
        "   - Provide a clear description in question_text. You MUST also append 1 or 2 concrete examples of expected input and expected output directly to the end of the question_text description (e.g. 'Example 1:\\nInput: num = 5\\nOutput: 10\\n\\nExample 2:\\nInput: num = -1\\nOutput: -2') so that students can understand the specifications clearly.\n"
        "   - Set expected_function_name to the Python function students must implement.\n"
        "   - Set starter_code to a clean Python template with signature and placeholder pass.\n"
        "   - You MUST set reference_solution to a fully complete, correct, and working Python implementation of the function (e.g. actually compute and return the result). Never leave it empty or set to pass. This is strictly MANDATORY.\n"
        "   - Set option1, option2, option3, option4 to \"none\", and correct_answer to \"none\".\n"
        "   - Provide at least 4 test cases (minimum 2 sample, 2 hidden) in the test_cases list.\n"
        "     * input_data: MUST be a JSON array string representing arguments. E.g. '[5]' or '[[1, 2, 3], 4]'\n"
        "     * expected_output: MUST be a JSON representation of the output value. E.g. '12' or '\"hello\"' or 'true' or '[1, 4, 9]'\n"
        "     * is_sample: boolean (true for student practice visible, false for grading)\n"
        "     * weight: integer (grading weight, e.g. 1)\n"
        "     * explanation: short string detailing the test case logic.\n\n"
        "Return the output as a valid JSON array matching the requested response schema."
    )

    type_enum = ["mcq", "coding"]
    if question_type in ["mcq", "coding"]:
        type_enum = [question_type]

    # Make all fields required in the schema so Gemini is forced to output them.
    # We will instruct the model to use empty/placeholder values ("none" or []) for fields not applicable to the question type.
    required_fields = [
        "question_type", "question_text", "marks",
        "option1", "option2", "option3", "option4", "correct_answer",
        "expected_function_name", "starter_code", "reference_solution", "test_cases"
    ]

    schema = {
        "type": "ARRAY",
        "items": {
            "type": "OBJECT",
            "properties": {
                "question_type": {"type": "STRING", "enum": type_enum},
                "question_text": {"type": "STRING"},
                "marks": {"type": "INTEGER"},
                # MCQ fields
                "option1": {"type": "STRING"},
                "option2": {"type": "STRING"},
                "option3": {"type": "STRING"},
                "option4": {"type": "STRING"},
                "correct_answer": {"type": "STRING", "enum": ["option1", "option2", "option3", "option4", "none"]},
                # Coding fields
                "expected_function_name": {"type": "STRING"},
                "starter_code": {"type": "STRING"},
                "reference_solution": {"type": "STRING"},
                "test_cases": {
                    "type": "ARRAY",
                    "items": {
                        "type": "OBJECT",
                        "properties": {
                            "input_data": {"type": "STRING"},
                            "expected_output": {"type": "STRING"},
                            "is_sample": {"type": "BOOLEAN"},
                            "weight": {"type": "INTEGER"},
                            "explanation": {"type": "STRING"}
                        },
                        "required": ["input_data", "expected_output", "is_sample", "weight"]
                    }
                }
            },
            "required": required_fields
        }
    }

    response_text, error_msg = call_gemini_api_with_fallback(system_instruction, user_message, response_schema=schema)
    
    if error_msg:
        return None, error_msg
        
    try:
        questions = json.loads(response_text)
        return questions, None
    except json.JSONDecodeError as e:
        return None, f"Failed to parse AI response: {str(e)}\nRaw Response: {response_text}"
