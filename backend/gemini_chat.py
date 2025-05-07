# gemini_chat.py

import google.generativeai as genai
import os
from dotenv import load_dotenv

class GeminiTutor:
    def __init__(self, subject, name, introduction, first_message):
        # Load environment variables from .env
        load_dotenv()

        # Get API key and model version from environment
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.model_version = os.getenv("GEMINI_MODEL_VERSION", "models/gemini-1.5-pro-latest")

        if not self.api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set")

        genai.configure(api_key=self.api_key)

        self.model = genai.GenerativeModel(self.model_version)
        self.chat = self.model.start_chat(history=[])

        self.subject = subject
        self.name = name
        self.introduction = introduction
        self.first_message = first_message
        self.system_prompt = self._build_prompt()

        # Send the initial system message
        self.chat.send_message(self.system_prompt)

    def _build_prompt(self):
        return self.introduction

    def ask(self, message):
        response = self.chat.send_message(message)
        return response.text
    
    def print_chat_history(self):
        print(f"\nChat History with {self.name} ({self.subject}):\n" + "-"*50)

        for msg in self.chat.history:
            role = msg.role  # use attribute, not ['role']
            text = getattr(msg.parts[0], 'text', '[non-text content]') if msg.parts else ""
            if role == "user":
                print(f"You: {text}")
            elif role == "model":
                print(f"{self.name}: {text}")
        print("-" * 50 + "\n")