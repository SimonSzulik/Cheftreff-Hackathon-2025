# gemini_chat.py

import google.generativeai as genai

class GeminiTutor:
    def __init__(self, subject, name, introduction, first_message):
        self.api_key = "AIzaSyAybCSRKhfg-l69kKgexdBc3_NH6vaGx7g"
        genai.configure(api_key=self.api_key)

        self.model = genai.GenerativeModel("models/gemini-1.5-pro-latest")
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