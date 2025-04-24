from fastapi import FastAPI, Request
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from gemini_chat import GeminiTutor
from data.prompts import Marie_Belle, Van_Claude, Elise, Marie_Belle_Intro, Van_Claude_Intro

app = FastAPI()

# CORS for local frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In dev only. Restrict in prod.
    allow_methods=["*"],
    allow_headers=["*"]
)

# Tutor pool
tutors = {
    "alice": GeminiTutor(subject="Math", name="Marie Belle", introduction=Marie_Belle, first_message=Marie_Belle_Intro),
    "bob": GeminiTutor(subject="French", name="Van Claude", introduction=Van_Claude, first_message=Van_Claude_Intro),
}

class ChatRequest(BaseModel):
    tutor_id: str
    message: str

@app.post("/chat")
def chat(request: ChatRequest):
    tutor = tutors.get(request.tutor_id)
    if not tutor:
        return {"error": "Tutor not found"}

    response = tutor.ask(request.message)
    return {"reply": response}

@app.get("/history/{tutor_id}")
def get_history(tutor_id: str):
    tutor = tutors.get(tutor_id)
    if not tutor:
        return {"error": "Tutor not found"}

    history = []
    for msg in tutor.chat.history:
        if len(history) == 2:
            text = tutor.first_message
            role = "mentor"
            history.append({"sender": role, "text": text})
        text = getattr(msg.parts[0], 'text', '') if msg.parts else ''
        role = "mentor" if msg.role == "model" else "me"
        history.append({"sender": role, "text": text})

    if len(history) == 2:
        text = tutor.first_message
        role = "mentor"
        history.append({"sender": role, "text": text})

    return {"messages": history[2:]}