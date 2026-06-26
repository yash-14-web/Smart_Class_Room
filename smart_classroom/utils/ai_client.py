import os
import json
import urllib.request
import urllib.error
import time
from django.conf import settings

# Ordered list of models to try. If the first fails with quota limit, try the next.
FALLBACK_MODELS = [
    'gemini-3.1-flash-lite',
    'gemini-2.5-flash',
    'gemini-2.5-flash-lite'
]

def get_gemini_api_key():
    """Retrieves the Gemini API Key from settings or environment variables."""
    key = getattr(settings, 'GEMINI_API_KEY', os.environ.get('GEMINI_API_KEY', None))
    if key:
        cleaned_key = key.strip('\'" ')
        if cleaned_key and not cleaned_key.lower().startswith('your_') and cleaned_key != 'PLACEHOLDER':
            return cleaned_key
    return None

def call_gemini_api_with_fallback(system_instruction, user_message, response_schema=None):
    """
    Calls the Gemini API using a fallback strategy.
    If a model hits a rate limit (429), it automatically switches to the next model in FALLBACK_MODELS.
    
    Args:
        system_instruction (str): The system prompt.
        user_message (str): The user's query.
        response_schema (dict, optional): JSON schema for structured output.
    
    Returns:
        tuple: (response_text, error_message)
    """
    api_key = get_gemini_api_key()

    if not api_key:
        return None, "⚠️ **AI is not configured.** Please set your `GEMINI_API_KEY` in the `.env` file to enable AI features."

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": f"{system_instruction}\n\nUser message:\n{user_message}"}
                ]
            }
        ]
    }
    
    # Add structured output schema if requested (for AI Auto-Quiz generation)
    if response_schema:
        payload["generationConfig"] = {
            "responseMimeType": "application/json",
            "responseSchema": response_schema
        }

    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": api_key,
    }
    
    data = json.dumps(payload).encode('utf-8')
    
    # Try models in order
    for model_index, model_name in enumerate(FALLBACK_MODELS):
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"
        
        try:
            req = urllib.request.Request(url, data=data, headers=headers, method='POST')
            with urllib.request.urlopen(req, timeout=30) as response:
                response_body = response.read().decode('utf-8')
                data_json = json.loads(response_body)
                return data_json['candidates'][0]['content']['parts'][0]['text'], None
                
        except urllib.error.HTTPError as e:
            # 429 Too Many Requests indicates Quota limit reached
            if e.code == 429:
                print(f"[AI Fallback] Model {model_name} hit quota limit (429). Trying next...")
                # If we have more models to try, wait 1 second and continue to next model
                if model_index < len(FALLBACK_MODELS) - 1:
                    time.sleep(1)
                    continue
                else:
                    return None, "⚠️ **Quota Finished:** All AI models have reached their daily/minute limits. Please wait a few minutes or try again tomorrow."
            
            # For other HTTP errors (e.g., 400 Bad Request), don't fallback, just return error
            error_body = ''
            try:
                error_body = e.read().decode('utf-8', errors='ignore')
                error_json = json.loads(error_body)
                error_msg = error_json.get('error', {}).get('message', str(e))
            except Exception:
                error_msg = error_body[:300] if error_body else str(e)
                
            return None, f"⚠️ **AI Error (HTTP {e.code}):** {error_msg}"
            
        except Exception as e:
            return None, f"⚠️ **Connection Error:** {str(e)}"
            
    return None, "⚠️ **Unknown Error:** Failed to generate response from all available models."
