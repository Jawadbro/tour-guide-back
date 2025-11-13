import os
import requests

def get_gemini_response(prompt: str):
    """Calls Gemini API (or fallback logic if offline)."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return "Gemini API key not configured. Please set GEMINI_API_KEY in .env."

    try:
        response = requests.post(
            "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent",
            headers={"Content-Type": "application/json"},
            params={"key": api_key},
            json={"contents": [{"parts": [{"text": prompt}]}]}
        )
        data = response.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        return f"(AI Fallback) Could not reach Gemini API. Error: {str(e)}"
