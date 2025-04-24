from fastapi import FastAPI, Request
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from gemini_chat import GeminiTutor
from data.prompts import Marie_Belle, Van_Claude, Elise, Marie_Belle_Intro, Van_Claude_Intro
from camera_service import CameraService
import requests

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

cameraService = CameraService()

@app.on_event("startup")
async def startup_event():
    cameraService.start()

@app.on_event("shutdown")
async def shutdown_event():
    cameraService.stop()

class ChatRequest(BaseModel):
    tutor_id: str
    message: str
    
@app.get("/tracking/{tutor_id}")
async def tracking(tutor_id: str):
    tutor = tutors.get(tutor_id)
    if not tutor:
        return {"error": "Tutor not found"}

    try:
        parameters = cameraService.get_current_parameters()
        if parameters["looking_state"] == "away" and parameters["looking_duration"] > 10.0:
            print(parameters["looking_state"] + " should motivate")
            return {"reply": "motivate"}
        else:
            print(parameters["looking_state"] + " everythings fine")
            return {"reply": "fine"} # Return empty reply when not distracted
    except Exception as e:
        return {"error": f"Camera service error: {str(e)}"}

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