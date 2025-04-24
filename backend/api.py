from fastapi import FastAPI, Request
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from gemini_chat import GeminiTutor
from data.prompts import Marie_Belle, Marie_Belle_Intro # Mathe
from data.prompts import Van_Claude, Van_Claude_Intro # French
from data.prompts import Sophia_Lane, Sophia_Lane_Intro # English 
from data.prompts import Maximilian_Koehler, Maximilian_Koehler # German
from data.prompts import Elise_Schmitz, Elise_Schmitz_Intro # Biologie
from data.prompts import Isabella_Reyes, Isabella_Reyes_Intro # Musik
from data.prompts import Daniel_Hartmann, Daniel_Hartmann_Intro # Geographie
from data.prompts import Lena_Fischer, Lena_Fischer_Intro # Physics
from data.prompts import Amira_Solis, Amira_Solis_Intro # Chemistry
from data.prompts import Liam_Reyes, Liam_Reyes_Intro # Computer Science
from data.prompts import Anna_Lucia_Baumann, Anna_Lucia_Baumann_Intro # Religion
from data.prompts import Jordan_Keller, Jordan_Keller_Intro # Sports
from data.prompts import Olivia_Schmidt, Olivia_Schmidt_Intro # Psychologie
from data.prompts import Max_Weber, Max_Weber_Intro # Economics
from data.prompts import Liam_Fischer, Liam_Fischer_Intro # Politics
from camera_service import CameraService
import requests

motivation_prompt = "The student seems to be distracted. Send him a nice message to motivate him. Maybe adjust the difficulty of the current task."
motivate_allowed = True

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
    

@app.get("/motivate/{tutor_id}")
async def motivate(tutor_id: str):
    tutor = tutors.get(tutor_id)
    if not tutor:
        return {"error": "Tutor not found"}

    response = tutor.ask(motivation_prompt)
    return {"reply": response}


@app.get("/tracking/{tutor_id}")
async def tracking(tutor_id: str):
    global motivate_allowed
    tutor = tutors.get(tutor_id)
    if not tutor:
        return {"error": "Tutor not found"}

    try:
        parameters = cameraService.get_current_parameters()
        if parameters["looking_state"] == "away" and parameters["looking_duration"] > 10.0 and motivate_allowed:
            print(parameters["looking_state"] + " should motivate")
            motivate_allowed = False
            return {"reply": "motivate"}
        else:
            print(parameters["looking_state"] + " everythings fine")
            return {"reply": "fine"} # Return empty reply when not distracted
    except Exception as e:
        return {"error": f"Camera service error: {str(e)}"}

@app.post("/chat")
def chat(request: ChatRequest):
    global motivate_allowed
    motivate_allowed = True
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
        if not text == motivation_prompt:
            history.append({"sender": role, "text": text})

    if len(history) == 2:
        text = tutor.first_message
        role = "mentor"
        history.append({"sender": role, "text": text})

    return {"messages": history[2:]}