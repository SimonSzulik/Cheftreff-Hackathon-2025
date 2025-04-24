# main.py

from gemini_chat import GeminiTutor

def main():
    tutor = GeminiTutor(subject="Math", name="Mary-Belle")

    print("AI Tutor: Ready to help! Ask me anything or answer my questions.\n")

    while True:
        user_input = input("You: ")
        if user_input.lower() in ["exit", "quit"]:
            print("Chat ended. Goodbye!")
            break

        if user_input.lower() in ["/history", "#history", "/h"]:
            tutor.print_chat_history()
            continue  # don't send this to the AI
        
        ai_response = tutor.ask(user_input)
        print(f"AI Tutor: {ai_response}\n")

if __name__ == "__main__":
    main()