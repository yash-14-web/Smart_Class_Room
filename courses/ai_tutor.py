from smart_classroom.utils.ai_client import call_gemini_api_with_fallback, get_gemini_api_key

def generate_ai_response(user_role, action, topic, context=None):
    """
    Simple chatbot: sends the user's message to Gemini and returns the response.
    Now uses the centralized ai_client which has automatic multi-model fallback.
    """
    # Simple system instruction based on role
    if user_role == 'teacher':
        system_instruction = (
            "You are an AI Teaching Assistant for the Smart Classroom platform. "
            "Help teachers with course content, assignment ideas, grading feedback, "
            "syllabus planning, and any educational queries. "
            "Use clear Markdown formatting with headings and bullet points."
        )
    else:
        system_instruction = (
            "You are an AI Study Companion for the Smart Classroom platform. "
            "Help students understand concepts, solve problems, prepare for exams, "
            "and learn effectively. Explain things clearly with examples and code snippets when relevant. "
            "Use Markdown formatting."
        )

    # Build the user message
    user_message = topic
    if context:
        user_message = f"{topic}\n\nAdditional context:\n{context}"

    response_text, error_msg = call_gemini_api_with_fallback(system_instruction, user_message)
    
    if error_msg:
        return error_msg
        
    return response_text

