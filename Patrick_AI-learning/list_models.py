# list_models.py

import google.generativeai as genai

# Replace with your actual API key (or better: use environment variables)
API_KEY = "AIzaSyAybCSRKhfg-l69kKgexdBc3_NH6vaGx7g"

def list_available_models():
    genai.configure(api_key=API_KEY)

    print("📦 Available Gemini Models:\n")
    models = genai.list_models()

    for model in models:
        print(f"✅ Name: {model.name}")
        print(f"   - Description: {model.description}")
        print(f"   - Input Token Limit: {model.input_token_limit}")
        print(f"   - Output Token Limit: {model.output_token_limit}")
        print(f"   - Supported Generation Methods: {model.supported_generation_methods}\n")

if __name__ == "__main__":
    list_available_models()