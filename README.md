# 🚀 StudyOS AI 

An elite, AI-powered study command center and productivity dashboard designed to replace fragmented study apps with one unified execution engine. 

Built originally to manage the rigorous demands and massive syllabi of competitive engineering entrance exams (like JEE), this application leverages generative AI to break down complex study goals into actionable daily blueprints.

![StudyOS AI Interface](app-hero.jpg)

## ✨ Core Features

*   **🧠 Gemini AI Architect:** Feed the engine your syllabus gaps or backlog, and it generates a logically sequenced, bite-sized daily execution plan using the Google Gemini 2.5 Flash model.
*   **⏱️ Immersive Focus Hub:** A high-precision visual timer featuring multiple execution frameworks including Pomodoro, 52/17, and Animedoro.
*   **🌐 Live Study Hall (Multiplayer):** A real-time cloud leaderboard powered by Supabase. See who is currently in deep work and track competitive study hours.
*   **📋 Automated Project Kanban:** AI-generated tasks automatically route to a Kanban board (To-Do → In Progress → Done) for seamless project management.
*   **📊 Analytics Engine:** Tracks 7-day and 4-week productivity intelligence, visualizing focus time, break time, and task completion streaks.

## 🛠️ Tech Stack

*   **Frontend & Desktop GUI:** [Flet](https://flet.dev/) (Python-based Flutter framework)
*   **Backend Logic:** Python 3.x, `asyncio` for non-blocking UI and timer loops
*   **Artificial Intelligence:** Google Generative AI (Gemini Pro/Flash API)
*   **Cloud Database:** Supabase (PostgreSQL) for live leaderboard syncing
*   **Audio Engine:** Pygame (for alarm and notification handling)

## ⚙️ Local Setup & Installation

To run StudyOS AI on your local machine, follow these steps:

### 1. Clone the repository
```bash
git clone https://github.com/lakhyajeetmohanty7450-creator/StudyOS-AI.git
cd StudyOS-AI