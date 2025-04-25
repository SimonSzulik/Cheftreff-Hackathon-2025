from fastapi import FastAPI, Request
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from gemini_chat import GeminiTutor
from data.prompts import Marie_Belle, Marie_Belle_Intro # Mathe
from data.prompts import Van_Claude, Van_Claude_Intro # French
from data.prompts import Sophia_Lane, Sophia_Lane_Intro # English 
from data.prompts import Maximilian_Koehler, Maximilian_Koehler_Intro # German
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
from collections import defaultdict

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

# Store how many messages the user has sent to each tutor
user_message_counts = defaultdict(int)
achievement_threshold = 5

# Tutor pool
tutors = {
    "marieBelle": GeminiTutor(subject="Math", name="Marie Belle", introduction=Marie_Belle, first_message=Marie_Belle_Intro),
    "vanClaude": GeminiTutor(subject="French", name="Van Claude", introduction=Van_Claude, first_message=Van_Claude_Intro),
    "sophiaLane": GeminiTutor(subject="English", name="Sophia Lane", introduction=Sophia_Lane, first_message=Sophia_Lane_Intro),
    "maximilianKoehler": GeminiTutor(subject="German", name="Maximilian Koehler", introduction=Maximilian_Koehler, first_message=Maximilian_Koehler_Intro),
    "eliseSchmitz": GeminiTutor(subject="Biology", name="Elise Schmitz", introduction=Elise_Schmitz, first_message=Elise_Schmitz_Intro),
    "isabellaReyes": GeminiTutor(subject="Music", name="Isabella Reyes", introduction=Isabella_Reyes, first_message=Isabella_Reyes_Intro),
    "danielHartmann": GeminiTutor(subject="Geography", name="Daniel Hartmann", introduction=Daniel_Hartmann, first_message=Daniel_Hartmann_Intro),
    "lenaFischer": GeminiTutor(subject="Physics", name="Lena Fischer", introduction=Lena_Fischer, first_message=Lena_Fischer_Intro),
    "amiraSolis": GeminiTutor(subject="Chemistry", name="Amira Solis", introduction=Amira_Solis, first_message=Amira_Solis_Intro),
    "liamReyes": GeminiTutor(subject="Computer Science", name="Liam Reyes", introduction=Liam_Reyes, first_message=Liam_Reyes_Intro),
    "annaLuciaBaumann": GeminiTutor(subject="Religion", name="Anna Lucia Baumann", introduction=Anna_Lucia_Baumann, first_message=Anna_Lucia_Baumann_Intro),
    "jordanKeller": GeminiTutor(subject="Sports", name="Jordan Keller", introduction=Jordan_Keller, first_message=Jordan_Keller_Intro),
    "oliviaSchmidt": GeminiTutor(subject="Psychology", name="Olivia Schmidt", introduction=Olivia_Schmidt, first_message=Olivia_Schmidt_Intro),
    "maxWeber": GeminiTutor(subject="Economics", name="Max Weber", introduction=Max_Weber, first_message=Max_Weber_Intro),
    "liamFischer": GeminiTutor(subject="Politics", name="Liam Fischer", introduction=Liam_Fischer, first_message=Liam_Fischer_Intro),
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
    
    # Count the user message
    user_message_counts[request.tutor_id] += 1

    # Check if achievement was unlocked
    count = user_message_counts[request.tutor_id]
    unlocked = count == achievement_threshold

    response = tutor.ask(request.message)
    return {
        "reply": response,
        "achievementUnlocked": unlocked
    }

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

@app.get("/achievements")
def get_achievements():
    return {"achieved": [tid for tid, count in user_message_counts.items() if count >= achievement_threshold]}