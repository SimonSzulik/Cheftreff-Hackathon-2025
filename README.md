# ChefTreff AI-Hackathon 2025: AI-Powered Learning Platform

## Project Overview

This project was developed within 24 hours during the **AI-Hackathon of ChefTreff 2025**.

The Challange was presented by **Knowunity** (https://knowunity.de/).

**Goal:** Build an AI-powered solution that creates personalized learning experiences, supports adaptive content delivery, provides actionable insights to educators, and improves student engagement and performance.

---

## Contents

- [Challenge Description](#challenge-description)
- [Solution Description](#solution-description)
- [Installation](#installation)
- [Contributors](#contributors)

---

## Challenge Description

The following is the short description of the Challange.

*Goal: Build an AI-powered solution that creates personalized learning experiences, supports adaptive content delivery, provides actionable insights to educators, and improves student engagement and performance.*

*Use Cases (Examples):*
- Adaptive Learning Pathways: AI analyzes students’ progress, strengths, and weaknesses to create personalized learning journeys. The system adjusts the pace, difficulty, and type of content dynamically to ensure each student is learning in the most effective way possible.
- Smart Tutoring Assistant: An AI-powered assistant that provides real-time help to students. It can answer questions, provide hints, explain concepts in different ways, and suggest additional resources based on the student’s learning style and progress.
- Educator Insights Dashboard: AI aggregates data on student performance, providing educators with real-time insights into individual and class-wide progress. This tool helps teachers identify students at risk, track learning trends, and adjust their teaching methods accordingly.
- Behavioral Analytics for Student Engagement: AI analyzes students’ interactions with learning materials (videos, quizzes, discussions) to predict and monitor engagement. The system provides recommendations to both students and educators on how to increase engagement and retention.
- AI-Powered Feedback Generator: AI analyzes student submissions (essays, assignments) and provides personalized, actionable feedback. It can identify common mistakes, suggest improvements, and help students better understand their areas for growth.

---

## Solution Description

To address the challenge, we developed a multi-part AI-powered learning platform that creates engaging, personalized learning experiences for students. At the heart of the system are **personalized AI tutors**, each designed to represent a specific subject (e.g., math, science, history). These tutors are not just functional — they also have personalized pictures and conversational styles to simulate the presence of a real human tutor, making the interaction more relatable and motivating for students.

The **frontend** was designed to resemble a familiar and appealing interface similar to WhatsApp Desktop, where each subject has its own dedicated chat. This allows students to seamlessly switch between subjects and tutors, creating an intuitive and organized learning environment.

A key feature of the system is the **real-time observation of student behavior** using the device’s **camera**, allowing the platform to monitor whether the student is paying attention to the screen. This data is combined with the concept of **“time on task”** — measuring how long a student stays engaged with a learning activity. If the system detects that the student has looked away from the screen for too long, appears distracted, or takes unusually long pauses, the AI tutor automatically intervenes with supportive prompts, encouragement, or adaptive changes to the task difficulty. This proactive approach helps keep students focused, ensures tasks are appropriately challenging, and prevents frustration or disengagement.

A key goal was to enhance **“flow”** — the psychological state where learners are fully immersed and enjoying the activity. By matching the difficulty of tasks to the student’s current skill level and monitoring time on task, the system dynamically adapts content to keep the student challenged but not overwhelmed, maintaining focus and maximizing learning impact.

To boost engagement even further, we integrated **gamification elements**, including an **achievement system** that rewards students for milestones and progress. This not only keeps motivation high but also gives students a sense of accomplishment as they advance through their personalized learning journey.

On the technical side, the backend is powered by Python with the Gemini API for the AI tutors, while the frontend is built with Vue.js for a responsive and user-friendly experience. Together, these components form a cohesive solution that personalizes learning, increases engagement, and empowers both students and educators.

---

## Installation

### Setup Project (Python 3.10.17 recommended)

1. **Create virtual environment**
   ```bash
   python3.10 -m venv venv
   source venv/bin/activate  # macOS/Linux
   venv\Scripts\activate     # Windows
   ```

2. **Install Python dependencies**
    ```bash
    pip install -r requirements.txt
    ```

3. **Set up environment variables**
    - Create a `.env` file in the project root:
        ```
        GEMINI_API_KEY=your_api_key_here
        GEMINI_MODEL_VERSION=models/your-prefered-gemini-model
        ```
        The application was tested with Gemini models 1.5 Flash (gemini-1.5-flash-latest) aswell as 1.5 Pro (gemini-1.5-pro-latest).

    - Test if the set model is supported with the given API Key
        ```bash
        python backend/check_gemini_model.py
        ```

### Setup frontend and run application

1. **Navigate to frontend folder**
    ```bash
    cd frontend
    ```

2. **Install Node dependencies (force required)**
    ```bash
    npm install --force
    ```

3. **Running the Project**
    ```bash
    npm run dev

    # for isolated camera service
    python ../backend/camera_service.py
    ```
    After starting the application is accessible via `http://localhost:8080/`.\
    The Camera Service takes some time to start and is required for the service to run, so have some patience after startup.

---

## Contributors

- **Mehdy Shinwari**   
    E-Mail: mehdyshinwari@gmail.com  
    GitHub: [@MehdyShinwari] (https://github.com/MehdyShinwari)

- **Fabian Sponholz**  
    E-Mail: s4faspon@uni-trier.de  
    GitHub: [@K3BAP] (https://github.com/K3BAP)

- **Simon Szulik**   
    E-Mail: simonszulik18@gmail.com  
    GitHub: [@SimonSzulik] (https://github.com/SimonSzulik)

- **Patrick Weil**  
    E-Mail: p.weil94@gmail.com  
    GitHub: [@s4paweil] (https://github.com/s4paweil)