import os
from dotenv import load_dotenv
import google.generativeai as genai

def check_model_availability():
    # Load environment variables
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    target_model = os.getenv("GEMINI_MODEL_VERSION")

    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable not set")
    if not target_model:
        raise ValueError("GEMINI_MODEL_VERSION environment variable not set")

    # Configure Gemini API
    genai.configure(api_key=api_key)

    print(f"🔍 Checking availability of model: {target_model}")

    try:
        # Try a harmless dry-run request
        model = genai.GenerativeModel(target_model)
        response = model.generate_content("Hello!")
        if response and response.text:
            print(f"Model '{target_model}' is available and working!")
        else:
            print(f"Model '{target_model}' did not return a usable response.")
    except Exception as e:
        print(f"Model '{target_model}' is NOT available. Reason: {e}")

if __name__ == "__main__":
    check_model_availability()