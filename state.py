import json
import os
import tempfile
import random
import logging
from datetime import datetime

logger = logging.getLogger("studyflow")

DATA_FILE = "studyflow_data.json"

def load_data():
    default_state = {
        "tasks": [],
        "total_study_seconds": 0,
        "total_break_seconds": 0, 
        "current_mode": "focus",  
        "subject_stats": {"Math": 0, "Python": 0, "Study": 0, "Personal": 0},
        "streak_days": 0,
        "today_streak_claimed": False, 
        "last_login_date": datetime.now().strftime("%Y-%m-%d"),
        "kanban_board": {"To-Do": [], "In Progress": [], "Done": []},
        "timer_mode": "Pomodoro",
        "history_log": [],      
        "view_range": "Today",
        "username": f"Student_{random.randint(1000, 9999)}"
    }
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                for key, value in default_state.items():
                    if key not in loaded:
                        loaded[key] = value
                
                for t in loaded["tasks"]:
                    if "status" not in t:
                        t["status"] = "done" if t.get("done", False) else "pending"
                return loaded
        except Exception:
            logger.exception("Unable to load local data; starting with default state")
    return default_state

def save_data(state):
    data_dir = os.path.dirname(os.path.abspath(DATA_FILE)) or "."
    fd, tmp_path = tempfile.mkstemp(prefix="studyflow_", suffix=".json", dir=data_dir, text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=4, ensure_ascii=False)
        os.replace(tmp_path, DATA_FILE)
    except Exception:
        try:
            os.remove(tmp_path)
        except OSError:
            pass
        logger.exception("Unable to save local data")

def check_daily_reset(app_state):
    today_str = datetime.now().strftime("%Y-%m-%d")
    last_login = app_state.get("last_login_date", today_str)
    
    if last_login != today_str:
        app_state["history_log"].append({
            "date": last_login,
            "study_seconds": app_state.get("total_study_seconds", 0),
            "break_seconds": app_state.get("total_break_seconds", 0),
            "tasks_done": sum(1 for t in app_state.get("tasks", []) if t.get("status") == "done")
        })
        
        app_state["history_log"] = app_state["history_log"][-30:]
        
        try:
            days_missed = (datetime.now().date() - datetime.strptime(last_login, "%Y-%m-%d").date()).days
            if days_missed > 1 or not app_state.get("today_streak_claimed", False):
                if len(app_state.get("tasks", [])) > 0 or days_missed > 1:
                    app_state["streak_days"] = 0 
        except Exception:
            app_state["streak_days"] = 0

        app_state["tasks"] = [] 
        app_state["total_study_seconds"] = 0
        app_state["total_break_seconds"] = 0
        app_state["today_streak_claimed"] = False
        app_state["last_login_date"] = today_str
        save_data(app_state)
        return True 
    return False
