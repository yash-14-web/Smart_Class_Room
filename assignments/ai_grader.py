import os
import json
import urllib.request
import urllib.error
from django.conf import settings

def get_gemini_api_key():
    """Retrieves the Gemini API Key from settings or environment variables."""
    key = getattr(settings, 'GEMINI_API_KEY', os.environ.get('GEMINI_API_KEY', None))
    if key:
        cleaned_key = key.strip('\'" ')
        if cleaned_key and not cleaned_key.lower().startswith('your_') and cleaned_key != 'PLACEHOLDER':
            # Validate key format — Gemini API keys always start with 'AIza'
            if not cleaned_key.startswith('AIza'):
                print(f"[AI Grader WARNING] API key appears invalid (starts with '{cleaned_key[:6]}...'). Valid Gemini keys start with 'AIza'. Get one from https://aistudio.google.com/apikey")
                return None
            return cleaned_key
    return None

def extract_submission_content(submission):
    """
    Tries to read the contents of the submitted file if it's text-based.
    Returns the text content or a descriptive fallback.
    """
    content = ""
    if submission.file:
        file_path = submission.file.path
        ext = os.path.splitext(file_path)[1].lower()
        # Only read text-based code or notes files to prevent binary parser crashes
        text_extensions = {'.py', '.txt', '.js', '.java', '.cpp', '.c', '.html', '.css', '.json', '.md', '.sql'}
        if ext in text_extensions:
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read(25000)  # Read up to 25k chars
            except Exception as e:
                content = f"[Could not read file contents: {str(e)}]"
        else:
            content = f"[Submitted binary file: {os.path.basename(file_path)} (Download to view)]"
            
    if submission.github_link:
        if content:
            content += f"\n\nGitHub Link: {submission.github_link}"
        else:
            content = f"GitHub Link: {submission.github_link}"
            
    return content or "[No file contents or GitHub links provided]"

def get_local_grading_fallback(assignment_title, label, total_marks, student_name, student_content):
    """Generates a smart local fallback grade and feedback when Gemini API is unavailable."""
    # Compute a mock grade (e.g. around 85% of total marks, offset based on length of content)
    base_percentage = 80
    if len(student_content) > 100:
        base_percentage += 8
    if "github" in student_content.lower():
        base_percentage += 4
    
    # Cap percentage at 98%
    base_percentage = min(base_percentage, 98)
    suggested_grade = int((base_percentage / 100) * total_marks)
    
    # Custom feedback matter based on topic keywords
    title_lower = assignment_title.lower()
    
    if "python" in title_lower or "loop" in title_lower or "list" in title_lower:
        feedback = (
            f"### 🤖 AI Evaluation Summary (Local Demo Mode)\n\n"
            f"**Student**: {student_name}\n"
            f"**Assignment**: {assignment_title} ({label.capitalize()})\n\n"
            f"#### 🌟 Strengths\n"
            f"- Effective implementation of standard Python scripting conventions.\n"
            f"- Variable bindings are named descriptively (e.g., matching PEP 8 rules).\n"
            f"- Logical control flow resolves the primary problem statement successfully.\n\n"
            f"#### 🛠️ Areas for Improvement\n"
            f"- **Complexity**: Consider optimizing loop lookups. If searching collections, use Python dictionaries or sets for O(1) average lookup speed.\n"
            f"- **Error Handling**: Wrap input parsing operations in a `try...except ValueError` block to fail gracefully on invalid values.\n\n"
            f"**Recommended Score: {suggested_grade} / {total_marks}**"
        )
    elif "java" in title_lower or "oop" in title_lower or "class" in title_lower:
        feedback = (
            f"### 🤖 AI Evaluation Summary (Local Demo Mode)\n\n"
            f"**Student**: {student_name}\n"
            f"**Assignment**: {assignment_title} ({label.capitalize()})\n\n"
            f"#### 🌟 Strengths\n"
            f"- Object-oriented encapsulation principles are followed correctly (appropriate use of private fields and getters/setters).\n"
            f"- Classes have a clear separation of concerns.\n\n"
            f"#### 🛠️ Areas for Improvement\n"
            f"- **Resource Management**: Make sure stream objects (e.g., Scanner or FileWriter) are closed inside a `finally` block or using a try-with-resources statement.\n"
            f"- **Code Modularity**: Extract repeating calculations into static helper utility methods to enhance readability.\n\n"
            f"**Recommended Score: {suggested_grade} / {total_marks}**"
        )
    else:
        feedback = (
            f"### 🤖 AI Evaluation Summary (Local Demo Mode)\n\n"
            f"**Student**: {student_name}\n"
            f"**Assignment**: {assignment_title} ({label.capitalize()})\n\n"
            f"#### 🌟 Strengths\n"
            f"- Core features of the assignment are addressed correctly.\n"
            f"- Code structure is clean, making it highly readable for reviews.\n\n"
            f"#### 🛠️ Areas for Improvement\n"
            f"- **Input Constraints**: Verify boundary limits (e.g., negative values, null pointers, empty data streams) to prevent runtime exceptions.\n"
            f"- **Documentation**: Add inline comments explaining non-trivial sections of your execution algorithm.\n\n"
            f"**Recommended Score: {suggested_grade} / {total_marks}**"
        )
        
    return {
        "grade": suggested_grade,
        "feedback": feedback,
        "is_demo": True
    }

def run_ai_grading(submission):
    """
    Sends the submission to Gemini 2.5 Flash for grading and feedback analysis.
    If the API call fails or is blocked, falls back gracefully to local mockup grading.
    """
    assignment = submission.assignment
    student = submission.student
    student_name = student.get_full_name() or student.username
    student_content = extract_submission_content(submission)
    
    api_key = get_gemini_api_key()
    
    if not api_key:
        return get_local_grading_fallback(
            assignment.title, assignment.label, assignment.total_marks, student_name, student_content
        )
        
    # Formulate grading instructions
    system_prompt = (
        "You are an expert academic tutor and instructor. "
        "Your task is to grade the student's submission based on the assignment title, description, and total marks. "
        "Analyze any code or text provided for syntax errors, logical correctness, efficiency, and styling. "
        "You MUST return a JSON response containing exactly two fields:\n"
        "1. 'grade': An integer representing the recommended score out of total marks.\n"
        "2. 'feedback': A detailed feedback string formatted in clean Markdown (including sections like Strengths, Improvement areas, and a conclusion).\n"
        "Do NOT wrap the response in markdown code blocks or return any text other than the raw JSON string."
    )
    
    user_prompt = (
        f"Assignment Title: {assignment.title}\n"
        f"Assignment Description: {assignment.description}\n"
        f"Label: {assignment.get_label_display()}\n"
        f"Total Marks Available: {assignment.total_marks}\n\n"
        f"Student Name: {student_name}\n"
        f"Student Submission Content:\n"
        f"----------------------------------------\n"
        f"{student_content}\n"
        f"----------------------------------------\n"
    )
    
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": api_key,
    }
    
    # We request the output to be JSON formatted
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": f"{system_prompt}\n\nUser Submission:\n{user_prompt}"}
                ]
            }
        ],
        "generationConfig": {
            "responseMimeType": "application/json"
        }
    }
    
    try:
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(url, data=data, headers=headers, method='POST')
        
        with urllib.request.urlopen(req, timeout=30) as response:
            status_code = response.getcode()
            response_body = response.read().decode('utf-8')
            
            if status_code == 200:
                result = json.loads(response_body)
                response_text = result['candidates'][0]['content']['parts'][0]['text'].strip()
                parsed_json = json.loads(response_text)
                
                # Verify grade is bounded within total marks
                grade = int(parsed_json.get('grade', 0))
                grade = max(0, min(grade, assignment.total_marks))
                
                return {
                    "grade": grade,
                    "feedback": parsed_json.get('feedback', 'No feedback provided.'),
                    "is_demo": False
                }
            
    except urllib.error.HTTPError as e:
        # Read the actual error body for diagnostics
        error_body = ''
        try:
            error_body = e.read().decode('utf-8', errors='ignore')
            error_json = json.loads(error_body)
            error_msg = error_json.get('error', {}).get('message', str(e))
        except Exception:
            error_msg = error_body[:300] if error_body else str(e)
        print(f"[AI Grader ERROR] Gemini API HTTP {e.code}: {error_msg}")
    except Exception as e:
        # Graceful connection/parsing failover to local fallback
        print(f"[AI Grader ERROR] Connection failed: {str(e)}")
        
    return get_local_grading_fallback(
        assignment.title, assignment.label, assignment.total_marks, student_name, student_content
    )
