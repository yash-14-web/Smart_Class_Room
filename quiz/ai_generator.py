import json
from smart_classroom.utils.ai_client import call_gemini_api_with_fallback

def generate_quiz_questions(topic, num_questions=5, difficulty="medium"):
    """
    Calls the Gemini API to generate a list of quiz questions on a given topic.
    Returns a list of dictionaries with questions and choices.
    """
    system_instruction = (
        "You are an expert educational content creator. Your task is to generate high-quality "
        "multiple-choice questions for a quiz. The questions should be clear, accurate, and engaging."
    )
    
    user_message = (
        f"Generate {num_questions} multiple-choice questions about '{topic}' at a {difficulty} difficulty level. "
        "Ensure there are exactly 4 choices for each question, and only 1 choice is correct. "
        "Return the output as a valid JSON array, where each item in the array has the following structure:\n"
        "{\n"
        "  \"text\": \"The question text\",\n"
        "  \"marks\": 1,\n"
        "  \"choices\": [\n"
        "    {\"text\": \"Choice A\", \"is_correct\": false},\n"
        "    {\"text\": \"Choice B\", \"is_correct\": true},\n"
        "    {\"text\": \"Choice C\", \"is_correct\": false},\n"
        "    {\"text\": \"Choice D\", \"is_correct\": false}\n"
        "  ]\n"
        "}"
    )

    # We use response_schema to force Gemini to return exactly what we want in JSON
    schema = {
        "type": "ARRAY",
        "items": {
            "type": "OBJECT",
            "properties": {
                "text": {"type": "STRING"},
                "marks": {"type": "INTEGER"},
                "choices": {
                    "type": "ARRAY",
                    "items": {
                        "type": "OBJECT",
                        "properties": {
                            "text": {"type": "STRING"},
                            "is_correct": {"type": "BOOLEAN"}
                        },
                        "required": ["text", "is_correct"]
                    }
                }
            },
            "required": ["text", "marks", "choices"]
        }
    }

    response_text, error_msg = call_gemini_api_with_fallback(system_instruction, user_message, response_schema=schema)
    
    if error_msg:
        return None, error_msg
        
    try:
        # Gemini with responseSchema returns the JSON string directly
        questions = json.loads(response_text)
        return questions, None
    except json.JSONDecodeError as e:
        return None, f"Failed to parse AI response: {str(e)}\nRaw Response: {response_text}"
