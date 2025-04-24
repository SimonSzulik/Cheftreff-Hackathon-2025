# main.py

from gemini_chat import GeminiTutor
from Prompts.prompts import Marie_Belle, Van_Claude, Elise

def main():
    # Erstelle die beiden Tutoren
    tutor_math = GeminiTutor(subject="Math", name="Mary-Belle", introduction = Marie_Belle)
    tutor_french = GeminiTutor(subject="French", name="Claude", introduction = Van_Claude)
    tutor_biology = GeminiTutor(subject="Biology", name="Elise", introduction = Elise)

    # Initialisiere den aktuellen Tutor (Standard ist der Mathe-Tutor)
    current_tutor = tutor_math

    print("AI Tutor: Ready to help! Ask me anything or answer my questions.\n")

    while True:
        user_input = input(f"You are currently chatting with {current_tutor.name} ({current_tutor.subject}).\nYou: ")

        # Beenden der Konversation
        if user_input.lower() in ["exit", "quit"]:
            print("Chat ended. Goodbye!")
            break

        # Wechseln des Tutors
        if user_input.lower() in ["/switch_math", "#switch_math", "/sm"]:
            current_tutor = tutor_math
            print(f"Switched to {current_tutor.name} ({current_tutor.subject}).\n")
            continue  # Weiter zum nächsten Input

        elif user_input.lower() in ["/switch_french", "#switch_french", "/sf"]:
            current_tutor = tutor_french
            print(f"Switched to {current_tutor.name} ({current_tutor.subject}).\n")
            continue  # Weiter zum nächsten Input

        elif user_input.lower() in ["/switch_biology", "#switch_biology", "/sf"]:
            current_tutor = tutor_biology
            print(f"Switched to {current_tutor.name} ({current_tutor.subject}).\n")
            continue  # Weiter zum nächsten Input

        # Historie anzeigen
        elif user_input.lower() in ["/history", "#history", "/h"]:
            current_tutor.print_chat_history()
            continue  # Diese Eingabe nicht an den Tutor senden

        # Tutor fragen
        ai_response = current_tutor.ask(user_input)
        print(f"AI Tutor: {ai_response}\n")

if __name__ == "__main__":
    main()
