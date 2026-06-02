import flet as ft
import pygame  
import json
import re
import asyncio
import os
import logging
import tempfile
import random 
from datetime import datetime, timedelta
import google.generativeai as genai  
from supabase import create_client, Client 
from dotenv import load_dotenv


load_dotenv() 

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("studyflow")


try:
    pygame.mixer.init()
except Exception:
    logger.exception("Unable to initialize pygame audio mixer")

DATA_FILE = "studyflow_data.json"

def glass_border(color="#30FFFFFF", width=1):
    side = ft.BorderSide(width, color)
    return ft.Border(
        left=side,
        top=side,
        right=side,
        bottom=side
    )



BG_PRIMARY = "#0F172A"
BG_SECONDARY = "#111827"
BG_TERTIARY = "#1E293B"

ACCENT = "#3B82F6"          
ACCENT_PURPLE = "#8B5CF6"   
ACCENT_GREEN = "#10B981"    

TEXT_PRIMARY = "#FFFFFF"
TEXT_SECONDARY = "#CBD5E1"

MUTED = "#94A3B8"

GLASS_BG = "#14FFFFFF"
GLASS_BG_SOFT = "#0BFFFFFF"

GLASS_BORDER = glass_border("#30FFFFFF")

GLASS_SHADOW = ft.BoxShadow(
    blur_radius=50,
    spread_radius=-12,
    color="#40000000",
    offset=ft.Offset(0, 24)
)

CARD_RADIUS = 36 

QUOTES = [
    "Great results require great ambitions",
    "The pain you feel today will be the strength you feel tomorrow",
    "Focus on the process, not the outcome",
    "One day, or day one. You decide.",
    "Discipline is choosing between what you want now and what you want most.",
    "Push yourself, because no one else is going to do it for you.",
    "Success is the sum of small efforts, repeated day in and day out.",
    "Don't stop until you're proud."
]


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
        except:
            app_state["streak_days"] = 0

        app_state["tasks"] = [] 
        app_state["total_study_seconds"] = 0
        app_state["total_break_seconds"] = 0
        app_state["today_streak_claimed"] = False
        app_state["last_login_date"] = today_str
        save_data(app_state)
        return True 
    return False




def get_emoji_and_subject(task_string):
    t = task_string.lower()
    if any(word in t for word in ["math", "jee", "coordinate", "parabola", "algebra", "calculus"]): return "📐", "Math"
    if any(word in t for word in ["python", "code", "sql", "leetcode", "dsa", "c++", "java"]): return "💻", "Python"
    if any(word in t for word in ["physics", "chem", "study", "mock", "paper", "revision", "read"]): return "📚", "Study"
    
    if any(word in t for word in ["history", "polity", "geography", "upsc", "current affairs"]): return "🌍", "General Studies"
    if any(word in t for word in ["reasoning", "quant", "aptitude", "ssc", "puzzle"]): return "🧠", "Aptitude"
    
    if any(word in t for word in ["edit", "video", "premiere", "after effects", "capcut", "thumbnail"]): return "🎬", "Video Editing"
    if any(word in t for word in ["office", "work", "meeting", "client", "email", "report"]): return "💼", "Office Work"
    if any(word in t for word in ["lunch", "dinner", "breakfast", "meal", "food"]): return "🍽️", "Personal"
    if any(word in t for word in ["sleep", "rest", "wake", "nap"]): return "🌙", "Personal"
    if any(word in t for word in ["break", "exercise", "gym", "walk", "chore", "clean"]): return "🏃‍♂️", "Personal"
    return "📝", "General"




def parse_timetable(raw_text):
    pattern = re.compile(r"^\s*(.*?(?:AM|PM))\s+(.*)$", re.IGNORECASE)
    parsed_tasks = []
    for line in raw_text.strip().split("\n"):
        line = line.strip()
        if not line: continue
        match = pattern.match(line)
        if match:
            time_string = match.group(1).strip().replace("–", "-")
            task_string = match.group(2).strip()
            start_time = time_string.split("-")[0].strip() if "-" in time_string else time_string
            emoji, subject = get_emoji_and_subject(task_string)
            parsed_tasks.append({
                "start_time": start_time, 
                "task": task_string, 
                "emoji": emoji,
                "subject": subject,
                "status": "pending",
                "is_now": False
            })
    return parsed_tasks





async def ai_generate_schedule(api_key, user_prompt):
    if not api_key or api_key == "YOUR_GEMINI_API_KEY_HERE":
        raise ValueError("Gemini API key is missing. Set GEMINI_API_KEY in your environment.")
        
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.5-flash")
    
    system_instruction = """
    You are the core AI Scheduling engine for 'StudyOS AI', an elite productivity dashboard for Engineering, Medical, Law, PG, and University students.
    Your job is to generate a comprehensive, highly structured day plan optimized for deep study, thesis writing, and heavy syllabus revision.
    
    Your job is to generate a comprehensive, highly structured day plan optimized for deep study.
    Break down broad topics into specific, bite-sized logical execution steps.
    
    You MUST respond with a valid, raw JSON array of objects. Do not include markdown code block wrappers.
    Each task object must contain exactly these fields:
    - "start_time": A clean time string or slot indicator (e.g., "08:00 AM", "10:30 AM", "04:00 PM")
    - "task": The specific descriptive study action or personal chore
    - "emoji": One highly accurate matching emoji
    - "subject": Must be exactly one of these categories: "Math", "Python", "Study", "Personal", "General"
    - "status": "pending"
    - "is_now": false
    """
    
    loop = asyncio.get_running_loop()
    response = await loop.run_in_executor(
        None, 
        lambda: model.generate_content(system_instruction + "\nUser Input Goal: " + user_prompt)
    )
    
    cleaned_text = response.text.strip()
    if cleaned_text.startswith("```json"):
        cleaned_text = cleaned_text[7:]
    if cleaned_text.endswith("```"):
        cleaned_text = cleaned_text[:-3]
        
    return json.loads(cleaned_text.strip())





def categorize_time(time_string):
    if not time_string: return "Unscheduled"
    try:
        match = re.search(r'(\d{1,2}):?(\d{2})?\s*(AM|PM)', time_string, re.IGNORECASE)
        if match:
            hr = int(match.group(1))
            meridiem = match.group(3).upper()
            if meridiem == "PM" and hr != 12: hr += 12
            if meridiem == "AM" and hr == 12: hr = 0
            if 5 <= hr < 12: return "Morning"
            elif 12 <= hr < 17: return "Afternoon"
            elif 17 <= hr < 21: return "Evening"
            else: return "Night"
    except: pass
    return "Unscheduled"





def main(page: ft.Page):
    
    page.title = "StudyOS AI"
    page.padding = 0  
    
    page.window_width = 1440
    page.window_height = 900
    page.window_maximized = True
    page.theme_mode = ft.ThemeMode.DARK

    app_state = load_data()
    app_state["timer_running"] = False
    app_state["focus_seconds"] = 25 * 60

    check_daily_reset(app_state)

    # Initialize Supabase 
    supabase_client = None

    def get_supabase():
        nonlocal supabase_client
        if supabase_client:
            return supabase_client
        if SUPABASE_URL and SUPABASE_KEY:
            try:
                supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
                return supabase_client
            except Exception:
                logger.exception("Unable to initialize Supabase client")
        return None



    async def run_blocking(func):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, func)

    


    def sync_cloud_status(is_studying):
        async def _sync():
            sb = get_supabase()
            if not sb:
                return
            try:
                await run_blocking(lambda: sb.table("study_hall").upsert({
                    "username": app_state["username"],
                    "total_minutes": app_state.get("total_study_seconds", 0) // 60,
                    "is_studying": is_studying,
                    "last_active": datetime.now().isoformat()
                }).execute())
            except Exception:
                logger.exception("Unable to sync study status")

        page.run_task(_sync)

   
    bg_gradient = ft.Container(
        expand=True,
        gradient=ft.LinearGradient(
            begin=ft.Alignment(-1, -1), end=ft.Alignment(1, 1),
            colors=[
                "#0F172A",
                "#111827",
                "#1E293B"
            ],
        ),
    )


    greeting_text = ft.Text(random.choice(QUOTES), size=18, weight="w500", color=MUTED, text_align=ft.TextAlign.CENTER, italic=True)
    
    
    focus_text = ft.Text(
        "25:00",
        size=140,
        weight=ft.FontWeight.W_700,
        color="white"
    )
    
    live_time_text = ft.Text("00:00", size=18, color="white", weight="bold")
    live_date_text = ft.Text("00-00-0000", size=13, color=MUTED)
    
    time_date_container = ft.Column([live_time_text, live_date_text], 
                      alignment=ft.MainAxisAlignment.CENTER,
                     horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=2)


    timer_circle = ft.Container(
        width=420,
        height=420,
        border_radius=210,
        bgcolor="#08FFFFFF",
        border=glass_border("#20FFFFFF"),
        content=ft.Column([
            focus_text,
            time_date_container
        ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
    )




    def update_timer_display():
        mins, secs = divmod(app_state["focus_seconds"], 60)
        if app_state["timer_mode"] == "Stopwatch (Count-Up)" or app_state["focus_seconds"] >= 3600:
            hours, mins = divmod(mins, 60)
            focus_text.value = f"{hours:02d}:{mins:02d}:{secs:02d}"
            # Shrink text size to fit the 8-character format inside the circle
            focus_text.size = 90 
        else:
            focus_text.value = f"{mins:02d}:{secs:02d}"
            # Restore to your premium large size for the 5-character format
            focus_text.size = 140




    async def clock_loop():
        while True:
            now = datetime.now()
            live_time_text.value = now.strftime("%H:%M")
            live_date_text.value = now.strftime("%d-%m-%Y")
            try: 
                live_time_text.update()
                live_date_text.update()
            except: pass
            
            if check_daily_reset(app_state):
                update_records_ui()
                render_tasks()

            await asyncio.sleep(1) 



    async def quote_rotator():
        while True:
            await asyncio.sleep(300) 
            if app_state.get("current_mode") != "break":
                greeting_text.value = random.choice(QUOTES)
                try: greeting_text.update()
                except: pass




    async def timer_loop():
        while app_state["timer_running"]:
            await asyncio.sleep(1)
            if not app_state["timer_running"]: break
            
            is_stopwatch = app_state["timer_mode"] == "Stopwatch (Count-Up)"
            
            if is_stopwatch:
                app_state["focus_seconds"] += 1
            else:
                if app_state["focus_seconds"] > 0:
                    app_state["focus_seconds"] -= 1
                else:
                    break
            
            if app_state.get("current_mode") == "break":
                app_state["total_break_seconds"] = app_state.get("total_break_seconds", 0) + 1
            else:
                app_state["total_study_seconds"] += 1
            
            update_timer_display()
            try:
                focus_text.update()
            except Exception:
                logger.exception("Unable to update timer display")
            
            
            if app_state["focus_seconds"] > 0 and app_state["focus_seconds"] % 60 == 0:
                save_data(app_state)
                update_records_ui()
                if app_state.get("current_mode") == "focus":
                    sync_cloud_status(is_studying=True)
                
        if not is_stopwatch and app_state["focus_seconds"] <= 0:
            app_state["timer_running"] = False
            start_btn.text = "Start"
            start_btn.bgcolor = ACCENT
            sync_cloud_status(is_studying=False)
            
            try:
                base_dir = os.path.dirname(os.path.abspath(__file__))
                alarm_path = os.path.join(base_dir, "assets", "alarm.mp3")
                pygame.mixer.music.load(alarm_path)
                pygame.mixer.music.play()
            except Exception as e:
                pass
            
            page.update()




    def toggle_timer(e):
        is_valid_start = app_state["timer_mode"] == "Stopwatch (Count-Up)" or app_state["focus_seconds"] > 0

        if not app_state["timer_running"] and is_valid_start:
            app_state["timer_running"] = True
            start_btn.text = "Pause"
            start_btn.bgcolor = "#FF6B6B" 
            if app_state.get("current_mode") == "focus":
                sync_cloud_status(is_studying=True)
            page.update()
            page.run_task(timer_loop)
        elif app_state["timer_running"]:
            app_state["timer_running"] = False
            start_btn.text = "Resume"
            start_btn.bgcolor = ACCENT 
            sync_cloud_status(is_studying=False)
            page.update()
            save_data(app_state)




    def reset_timer(mins, is_break=False):
        app_state["timer_running"] = False
        app_state["focus_seconds"] = mins * 60
        app_state["current_mode"] = "break" if is_break else "focus"
        
        sync_cloud_status(is_studying=False)
        update_timer_display()
        start_btn.text = "Start"
        start_btn.bgcolor = ACCENT
        
        if is_break:
            greeting_text.value = "Time to recharge"
        else:
            greeting_text.value = random.choice(QUOTES)
        page.update()


    custom_hour_input = ft.TextField(width=60, height=35, content_padding=5,
                                      text_align="center", hint_text="hr", bgcolor="#10FFFFFF", 
                                      border_color="#55FFFFFF", color="white", border_radius=18)
    custom_min_input = ft.TextField(width=60, height=35, content_padding=5,
                                     text_align="center", hint_text="min", bgcolor="#10FFFFFF", 
                                     border_color="#55FFFFFF", color="white", border_radius=18)
    



    def set_custom(e):
        try:
            h_val = custom_hour_input.value.strip()
            m_val = custom_min_input.value.strip()
            
            h = int(h_val) if h_val else 0
            m = int(m_val) if m_val else 0
            
            total_mins = (h * 60) + m
            if total_mins > 0:
                reset_timer(total_mins)
            
            custom_hour_input.value = ""
            custom_min_input.value = ""
        except: pass




    def handle_reset(e):
        mode = app_state.get("timer_mode", "Pomodoro")
        if mode == "Pomodoro":
            reset_timer(25)
        elif mode == "52/17":
            reset_timer(52)
        elif mode == "Animedoro":
            reset_timer(45)
        elif mode in ["Countdown", "Stopwatch (Count-Up)"]:
            reset_timer(0)
            
        start_btn.text = "Start"
        start_btn.bgcolor = ACCENT
        page.update()

    
    start_btn = ft.Button("Start", width=132, height=46, color="white", bgcolor=ACCENT, 
                          style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=20), elevation=0),
                          on_click=toggle_timer)
    reset_btn = ft.Button("Reset", width=132, height=46, color="white", bgcolor="#FF6B6B", 
                          style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=20), elevation=0),
                            on_click=handle_reset)
    
    timer_controls = ft.Row([start_btn, reset_btn], alignment=ft.MainAxisAlignment.CENTER, spacing=15)
    
    preset_row = ft.Row([], alignment=ft.MainAxisAlignment.CENTER)




    def change_timer_mode(e):
        new_mode = e.control.value if e else app_state.get("timer_mode", "Pomodoro")
        app_state["timer_mode"] = new_mode
        
        app_state["timer_running"] = False
        start_btn.text = "Start"
        start_btn.bgcolor = ACCENT
        
        preset_row.controls.clear()
        
        if new_mode == "Pomodoro":
            app_state["focus_seconds"] = 25 * 60
            preset_row.controls.extend([
                ft.TextButton("25m", on_click=lambda e: reset_timer(25), 
                              icon_color=TEXT_SECONDARY),
                ft.TextButton("50m", on_click=lambda e: reset_timer(50), 
                              icon_color=TEXT_SECONDARY),
                ft.TextButton("Break 5m", on_click=lambda e: reset_timer(5, is_break=True), 
                              icon_color=TEXT_SECONDARY),
                ft.Container(width=1, height=20, bgcolor="white24"), 
                custom_hour_input,
                ft.Text(":", color=TEXT_SECONDARY, size=14, weight="bold"),
                custom_min_input,
                ft.IconButton(ft.Icons.PLAY_ARROW, on_click=set_custom,
                               icon_color=TEXT_SECONDARY, icon_size=18)
            ])
        elif new_mode == "52/17":
            app_state["focus_seconds"] = 52 * 60
            preset_row.controls.extend([
                ft.TextButton("52m Focus", on_click=lambda e: reset_timer(52), icon_color=TEXT_SECONDARY),
                ft.TextButton("17m Break", on_click=lambda e: reset_timer(17, is_break=True),
                               icon_color=TEXT_SECONDARY),
            ])
        elif new_mode == "Animedoro":
            app_state["focus_seconds"] = 45 * 60
            preset_row.controls.extend([
                ft.TextButton("45m Study", on_click=lambda e: reset_timer(45), icon_color=TEXT_SECONDARY),
                ft.TextButton("20m Episode", on_click=lambda e: reset_timer(20, is_break=True),
                               icon_color=TEXT_SECONDARY),

            ])
        elif new_mode == "Countdown":
            app_state["focus_seconds"] = 0
            preset_row.controls.extend([
                ft.Text("Custom:", color=TEXT_SECONDARY, size=14),
                custom_hour_input,
                ft.Text(":", color=TEXT_SECONDARY, size=14, weight="bold"),
                custom_min_input,
                ft.IconButton(ft.Icons.PLAY_ARROW, on_click=set_custom, icon_color=TEXT_SECONDARY, icon_size=18)
            ])
        elif new_mode == "Stopwatch (Count-Up)":
            app_state["focus_seconds"] = 0
            preset_row.controls.extend([
                ft.TextButton("Reset", on_click=lambda e: reset_timer(0), icon_color=TEXT_SECONDARY)
            ])
            
        update_timer_display()
        if page:
            try: page.update()
            except: pass

    mode_dropdown = ft.Dropdown(
        value=app_state.get("timer_mode", "Pomodoro"),
        width=200,
        dense=True,
        options=[
            ft.DropdownOption("Pomodoro"),
            ft.DropdownOption("52/17"),
            ft.DropdownOption("Animedoro"),
            ft.DropdownOption("Countdown"),
            ft.DropdownOption("Stopwatch (Count-Up)"),
        ],
        color="white",
        bgcolor="#35FFFFFF",
        border_color="#66FFFFFF",
        border_radius=18,
        on_select=change_timer_mode
    )
    
    top_right_controls = ft.Container(
        content=ft.Column([
            ft.Text("Timer Mode", color=TEXT_SECONDARY, size=12, weight="bold"),
            mode_dropdown
        ], spacing=2),
        top=40,
        right=80
    )
    
    change_timer_mode(None)


    center_hub = ft.Container(
        content=ft.Column([
            greeting_text,
            ft.Container(height=20),
            timer_circle,
            ft.Container(height=20),
            timer_controls,
            preset_row,
            ft.Container(height=80) # <-- Foolproof invisible spacer prevents overlap!
        ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER,
          scroll=ft.ScrollMode.AUTO),
        alignment=ft.Alignment(0, 0), expand=True
    )




    def toggle_panel(panel_container):
        for p in [tasks_panel, records_panel, kanban_panel, gemini_panel, multiplayer_panel]:
            if p != panel_container: p.visible = False
        panel_container.visible = not panel_container.visible
        
        if panel_container == records_panel and panel_container.visible: update_records_ui()
        elif panel_container == kanban_panel and panel_container.visible: render_kanban()
        elif panel_container == multiplayer_panel and panel_container.visible: page.run_task(fetch_lb_now)
        page.update()


    progress_bar = ft.ProgressBar(width=360, value=0.0, color=ACCENT, bgcolor="#35FFFFFF")
    progress_text = ft.Text("0% Completed", color=TEXT_SECONDARY, size=12)
    task_list_ui = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True, spacing=5)
    
    manual_time_input = ft.TextField(hint_text="Time (e.g. 10 AM)", width=130,
                                      border_color="#66FFFFFF", bgcolor="#10FFFFFF", 
                                      color="white", text_size=12, content_padding=10, border_radius=18)
    manual_input = ft.TextField(hint_text="Type your priority...", expand=True, 
                                border_color="#66FFFFFF", bgcolor="#10FFFFFF", 
                                color="white", content_padding=10, border_radius=18)
    
    sched_input = ft.TextField(
        hint_text="Paste timetable here...", 
        multiline=True, 
        min_lines=3, 
        max_lines=5, 
        border_color="#66FFFFFF", 
        bgcolor="#10FFFFFF",
        color="white", 
        text_size=12,
        border_radius=18
    )




    def update_progress():
        if not app_state["tasks"]:
            progress_bar.value = 0.0
            progress_text.value = "0% Completed"
        else:
            total = len(app_state["tasks"])
            completed = sum(1 for t in app_state["tasks"] if t.get("status") == "done")
            pct = completed / total
            progress_bar.value = pct
            progress_text.value = f"{int(pct * 100)}% Completed ({completed}/{total})"

            if pct == 1.0 and not app_state.get("today_streak_claimed", False):
                app_state["streak_days"] = app_state.get("streak_days", 0) + 1
                app_state["today_streak_claimed"] = True
                save_data(app_state)
                update_records_ui()
            elif pct < 1.0 and app_state.get("today_streak_claimed", False):
                app_state["streak_days"] = max(0, app_state.get("streak_days", 0) - 1)
                app_state["today_streak_claimed"] = False
                save_data(app_state)
                update_records_ui()

        try:
            progress_bar.update()
            progress_text.update()
        except: pass




    def handle_checkbox(e, idx):
        app_state["tasks"][idx]["status"] = "done" if e.control.value else "pending"
        save_data(app_state)
        update_progress()
        render_tasks()




    def delete_task(idx):
        app_state["tasks"].pop(idx)
        save_data(app_state)
        update_progress()
        render_tasks()




    def render_tasks():
        task_list_ui.controls.clear()
        groups = {"Morning": [], "Afternoon": [], "Evening": [], "Night": [], "Unscheduled": []}
        for i, task in enumerate(app_state["tasks"]):
            cat = categorize_time(task.get("start_time", ""))
            if cat == "Morning": groups["Morning"].append((i, task))
            elif cat == "Afternoon": groups["Afternoon"].append((i, task))
            elif cat == "Evening": groups["Evening"].append((i, task))
            elif cat == "Night": groups["Night"].append((i, task))
            else: groups["Unscheduled"].append((i, task))

        for group_name, tasks_in_group in groups.items():
            if tasks_in_group:
                task_list_ui.controls.append(ft.Container(height=5))
                task_list_ui.controls.append(ft.Text(group_name, size=14, weight="bold", color=ACCENT))
                for idx, task in tasks_in_group:
                    display = f"{task['emoji']} {task['start_time']} -> {task['task']}" if task['start_time'] else f"{task['emoji']} {task['task']}"
                    
                    task_text_ui = ft.Text(display, size=13, expand=True, overflow=ft.TextOverflow.ELLIPSIS, max_lines=2)
                    
                    is_done = task.get("status") == "done"
                    task_text_ui.color = "white54" if is_done else "white"
                    task_text_ui.style = ft.TextStyle(decoration=ft.TextDecoration.LINE_THROUGH) if is_done else None
                    cb = ft.Checkbox(value=is_done, fill_color=ACCENT, check_color="#25302D", 
                                     on_change=lambda e, i=idx: handle_checkbox(e, i))
                        
                    del_btn = ft.IconButton(icon=ft.Icons.DELETE_OUTLINE, icon_color="white54",
                                             icon_size=18, on_click=lambda e, i=idx: delete_task(i))
                    
                    task_list_ui.controls.append(ft.Row([cb, task_text_ui, del_btn],
                                                         alignment=ft.MainAxisAlignment.SPACE_BETWEEN))
                    
        update_progress()
        try: page.update()
        except: pass




    def auto_route_to_kanban(task_text, subject):
        if subject == "Personal":
            return
            
        formatted_task = f"[{subject}] {task_text}"
        
        all_board_tasks = app_state["kanban_board"]["To-Do"] 
        + app_state["kanban_board"]["In Progress"] + app_state["kanban_board"]["Done"]
        if formatted_task not in all_board_tasks:
            app_state["kanban_board"]["To-Do"].append(formatted_task)




    def add_manual(e):
        if manual_input.value.strip():
            emoji, subject = get_emoji_and_subject(manual_input.value)
            task_text = manual_input.value
            time_text = manual_time_input.value.strip() 
            
            app_state["tasks"].append({
                "start_time": time_text, 
                "task": task_text, 
                "emoji": emoji, 
                "subject": subject, 
                "status": "pending", 
                "is_now": False
            })
            auto_route_to_kanban(task_text, subject)
            
            manual_input.value = ""
            manual_time_input.value = "" 
            save_data(app_state)
            render_tasks()
            render_kanban() 




    def sync_data(e):
        if sched_input.value.strip():
            new_tasks = parse_timetable(sched_input.value)
            app_state["tasks"].extend(new_tasks)
            
            for t in new_tasks:
                auto_route_to_kanban(t["task"], t["subject"])
                
            sched_input.value = ""
            save_data(app_state)
            render_tasks()
            render_kanban() 

    tasks_panel = ft.Container(
        width=400, height=650,
        bgcolor=GLASS_BG, blur=ft.Blur(32, 32, ft.BlurTileMode.MIRROR), 
        border=GLASS_BORDER, shadow=GLASS_SHADOW, border_radius=CARD_RADIUS, padding=24, 
        left=30, bottom=100, visible=False,
        content=ft.Column([
            ft.Text("Daily Agenda", size=20, weight="bold", color="white"),
            progress_bar, progress_text,
            ft.Divider(color="white24"),
            ft.Container(content=task_list_ui, expand=True),
            ft.Row([manual_time_input, manual_input, ft.IconButton(ft.Icons.ADD_CIRCLE, 
                                                                   icon_color=ACCENT, on_click=add_manual)]),
            ft.Divider(color="white24"),
            ft.Text("🤖 AI Import", size=14, weight="bold", color="white"),
            sched_input,
            ft.Button("Auto-Parse ✨", on_click=sync_data, bgcolor="#00b894", color="white", width=400)
        ])
    )


    gemini_prompt_input = ft.TextField(
        hint_text="Tell AI your blueprint goals...", 
        multiline=True, 
        min_lines=4, 
        max_lines=6, 
        border_color="#66FFFFFF", 
        bgcolor="#10FFFFFF",
        color="white", 
        text_size=12,
        border_radius=18
    )
    
    ai_status_indicator = ft.Text("", size=11, color="white60", italic=True)




    async def process_ai_schedule(e):
        prompt = gemini_prompt_input.value.strip()
        key = GEMINI_API_KEY
        
        if not key:
            ai_status_indicator.value = "⚠️ Error: Set GEMINI_API_KEY in your environment."
            ai_status_indicator.color = "#ff4757"
            page.update()
            return
            
        if not prompt:
            ai_status_indicator.value = "⚠️ Error: Please enter a directive for the LLM."
            ai_status_indicator.color = "#ff4757"
            page.update()
            return
            
        ai_status_indicator.value = "⚡ Directing Gemini Pro Engine... Building blueprint..."
        ai_status_indicator.color = "#ffa502"
        page.update()
        
        try:
            generated_tasks = await ai_generate_schedule(key, prompt)
            
            app_state["tasks"].extend(generated_tasks)
            for t in generated_tasks:
                auto_route_to_kanban(t["task"], t["subject"])
                
            gemini_prompt_input.value = ""
            ai_status_indicator.value = f"✨ Injected {len(generated_tasks)} optimization steps into your framework!"
            ai_status_indicator.color = "#2ed573"
            
            save_data(app_state)
            render_tasks()
            render_kanban()
        except Exception as err:
            logger.exception("Unable to generate AI schedule")
            ai_status_indicator.value = f"❌ Parsing Error: {str(err)[:50]}..."
            ai_status_indicator.color = "#ff4757"
            page.update()

    gemini_panel = ft.Container(
        width=400, height=350,
        bgcolor=GLASS_BG, blur=ft.Blur(32, 32, ft.BlurTileMode.MIRROR), 
        border=GLASS_BORDER, shadow=GLASS_SHADOW, border_radius=CARD_RADIUS, padding=24, left=30, bottom=100, 
        visible=False,
        content=ft.Column([
            ft.Row([ft.Icon(ft.Icons.PSYCHOLOGY, color="white"), ft.Text("Gemini AI Architect", size=20,
                                                                          weight="bold", color="white")]),
            ft.Text("Create contextual syllabus splits on the fly.", size=12, color=TEXT_SECONDARY),
            ft.Divider(color="white24"),
            ft.Text("Define Blueprint Scope", size=12, weight="bold", color="white54"),
            gemini_prompt_input,
            ai_status_indicator,
            ft.Button("Compile Blueprint ✨", on_click=process_ai_schedule, bgcolor=ACCENT_PURPLE, color="white", width=400)
        ])
    )

    #  MULTIPLAYER  PANEL 
    username_input = ft.TextField(value=app_state.get("username", ""), 
                        hint_text="Your Study Alias", border_color="white24", color="white", 
                        text_size=11, height=38, content_padding=10, bgcolor="#10FFFFFF", border_radius=18)
    leaderboard_list = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True, spacing=10)





    async def fetch_lb_now():
        sb = get_supabase()
        if not sb:
            return
        try:
            response = await run_blocking(
                lambda: sb.table("study_hall").select("*").order("total_minutes", desc=True).limit(10).execute()
            )
            leaderboard_list.controls.clear()
            for row in response.data:
                status_icon = "Online" if row.get("is_studying") else "Idle"
                user_text = f"{status_icon} - {row.get('username')}"
                mins = row.get('total_minutes', 0)
                h, m = divmod(mins, 60)
                time_text = f"{h}h {m}m"
                leaderboard_list.controls.append(
                    ft.Container(
                        content=ft.Row([ft.Text(user_text, color="white", weight="bold", size=14),
                                         ft.Text(time_text, color="#00b894", weight="bold", size=14)],
                                           alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        bgcolor=GLASS_BG_SOFT, border=GLASS_BORDER, padding=15, border_radius=16
                    )
                )
            leaderboard_list.update()
        except Exception:
            logger.exception("Unable to fetch leaderboard")




    def save_multiplayer_settings(e):
        app_state["username"] = username_input.value.strip()
        save_data(app_state)
        page.run_task(fetch_lb_now)




    async def poll_leaderboard():
        while True:
            await asyncio.sleep(10)
            if multiplayer_panel.visible:
                page.run_task(fetch_lb_now)

    multiplayer_panel = ft.Container(
        width=400, height=650, bgcolor=GLASS_BG, blur=ft.Blur(32, 32, ft.BlurTileMode.MIRROR),
          border=GLASS_BORDER, shadow=GLASS_SHADOW,
        border_radius=CARD_RADIUS, padding=24, left=238, bottom=112, visible=False,
        content=ft.Column([
            ft.Row([ft.Icon(ft.Icons.GROUPS, color="white"), ft.Text("Live Study Hall", 
                                                                     size=20, weight="bold", color="white")]),
            ft.Text("See who is currently grinding.", size=12, color=TEXT_SECONDARY),
            ft.Divider(color="white24"),
            username_input, 
            ft.Button("Connect to Cloud 🌐", on_click=save_multiplayer_settings, 
                      bgcolor=ACCENT_PURPLE, color="white", width=400),
            ft.Divider(color="white24"),
            leaderboard_list
        ], expand=True)
    )

    # todo
    todo_list = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True, spacing=10)
    in_progress_list = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True, spacing=10)
    done_list = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True, spacing=10)
    kanban_input = ft.TextField(hint_text="Add a new project task...", expand=True, 
                                border_color="white24", color="white", bgcolor="#10FFFFFF", border_radius=18)




    def drag_accept(e):
        src_data = page.get_control(e.src_id).data
        task_text, source_col = src_data["text"], src_data["source_col"]
        dest_col = e.control.data 
        if source_col != dest_col:
            app_state["kanban_board"][source_col].pop(src_data["idx"])
            app_state["kanban_board"][dest_col].append(task_text)
            save_data(app_state)
            render_kanban()




    def delete_kanban_task(col_name, idx):
        app_state["kanban_board"][col_name].pop(idx)
        save_data(app_state)
        render_kanban()

    
    app_state["kanban_filter"] = "All"




    def set_kanban_filter(e, filter_val):
        app_state["kanban_filter"] = filter_val
        render_kanban()

    filter_row = ft.Row([
        ft.Text("Filter Column view:", color=TEXT_SECONDARY, size=12),
        ft.TextButton("All", on_click=lambda e: set_kanban_filter(e, "All")),
        ft.TextButton("📐 Math", on_click=lambda e: set_kanban_filter(e, "Math")),
        ft.TextButton("💻 Python", on_click=lambda e: set_kanban_filter(e, "Python")),
        ft.TextButton("📚 Study", on_click=lambda e: set_kanban_filter(e, "Study")),
        ft.TextButton("📝 General", on_click=lambda e: set_kanban_filter(e, "General")),
    ], spacing=10, alignment=ft.MainAxisAlignment.START)




    def render_kanban():
        for lst in [todo_list, in_progress_list, done_list]: 
            lst.controls.clear()
            
        current_filter = app_state.get("kanban_filter", "All")




        def create_draggable(task_text, col_name, idx):
            if current_filter != "All" and not task_text.startswith(f"[{current_filter}]"):
                return None

            card_ui = ft.Container(
                content=ft.Row([
                    ft.Text(task_text, color="white", size=13, expand=True), 
                    ft.IconButton(ft.Icons.DELETE_OUTLINE, icon_color="white54", 
                                  icon_size=16, on_click=lambda e: delete_kanban_task(col_name, idx))
                ]), 
                bgcolor=GLASS_BG_SOFT, border=GLASS_BORDER, padding=15, border_radius=16
            )
            dragging_ui = ft.Container(content=ft.Text(task_text, color="white", size=13, weight="bold"), 
                                       bgcolor=ACCENT_PURPLE, padding=15, border_radius=16, width=220, opacity=0.8)
            return ft.Draggable(group="kanban", data={"text": task_text, "source_col": col_name, "idx": idx}, 
                                content=card_ui, content_feedback=dragging_ui)

        for i, t in enumerate(app_state["kanban_board"]["To-Do"]): 
            item = create_draggable(t, "To-Do", i)
            if item: todo_list.controls.append(item)
            
        for i, t in enumerate(app_state["kanban_board"]["In Progress"]): 
            item = create_draggable(t, "In Progress", i)
            if item: in_progress_list.controls.append(item)
            
        for i, t in enumerate(app_state["kanban_board"]["Done"]): 
            item = create_draggable(t, "Done", i)
            if item: done_list.controls.append(item)
            
        try: 
            todo_list.update()
            in_progress_list.update()
            done_list.update()
        except: 
            pass




    def make_kanban_col(title, item_list, col_name, accent_color):
        return ft.DragTarget(
            group="kanban", data=col_name, on_accept=drag_accept,
            content=ft.Container(
                content=ft.Column([
                    ft.Container(content=ft.Text(title, weight="bold", color="white", size=14),
                                  bgcolor=accent_color, padding=10, border_radius=15),
                    ft.Container(height=5), item_list
                ]), bgcolor=GLASS_BG_SOFT, border=GLASS_BORDER, border_radius=22, padding=15, width=250, expand=True
            )
        )

    kanban_columns = ft.Row([
        make_kanban_col("To-Do", todo_list, "To-Do", "#ff4757"), 
        make_kanban_col("In Progress", in_progress_list, "In Progress", "#ffa502"), 
        make_kanban_col("Done", done_list, "Done", "#2ed573"), 
    ], expand=True, spacing=15, alignment=ft.MainAxisAlignment.CENTER)




    def add_kanban(e):
        if kanban_input.value.strip():
            app_state["kanban_board"]["To-Do"].append(kanban_input.value.strip())
            kanban_input.value = ""
            save_data(app_state)
            render_kanban()

    kanban_panel = ft.Container(
        width=860, height=650, bgcolor=GLASS_BG, blur=ft.Blur(32, 32, ft.BlurTileMode.MIRROR), border=GLASS_BORDER,
          shadow=GLASS_SHADOW,
        border_radius=CARD_RADIUS, padding=24, left=238, bottom=112, visible=False,
        content=ft.Column([
            ft.Row([ft.Icon(ft.Icons.VIEW_KANBAN, color="white"), ft.Text("Project Board", size=24, weight="bold", 
                                                                          color="white")]),
            ft.Text("Tasks from your Daily Agenda are automatically routed here.", size=12, color=TEXT_SECONDARY),
            ft.Container(height=5),
            ft.Row([kanban_input, ft.IconButton(ft.Icons.ADD_CIRCLE, icon_color=ACCENT, on_click=add_kanban)]),
            ft.Divider(color="white24"), 
            filter_row,
            ft.Container(height=5),
            kanban_columns
        ], expand=True)
    )

    

    
    def set_view_range(e, range_name):
        app_state["view_range"] = range_name
        save_data(app_state)
        update_records_ui()

    time_toggles = ft.Row([], spacing=10)
    chart_title = ft.Text("7-Day Productivity Trend", size=16, weight="bold", color="white")



    def make_stat_card(title, value_ref, color, icon):
        return ft.Container(
            content=ft.Column([
                ft.Row([ft.Text(title, size=13, color="white", weight="bold"), ft.Icon(icon, color=ACCENT, size=16)], 
                       alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Container(height=5), value_ref
            ]), bgcolor=GLASS_BG_SOFT, border=GLASS_BORDER, shadow=ft.BoxShadow(blur_radius=16, spread_radius=-10, 
                color="#55000000", offset=ft.Offset(0, 8)), border_radius=16, padding=15, width=170, height=100
        )

    val_streak = ft.Text("0 days", size=24, weight="bold", color="white")
    val_time = ft.Text("0h 0m", size=24, weight="bold", color="white")
    val_tasks = ft.Text("0", size=24, weight="bold", color="white")
    val_break = ft.Text("0h 0m", size=24, weight="bold", color="white") 

    grid_cards = ft.Row([
        make_stat_card("Streak", val_streak, "#ff4757", ft.Icons.LOCAL_FIRE_DEPARTMENT), 
        make_stat_card("Focus Time", val_time, "#ffa502", ft.Icons.BOLT), 
        make_stat_card("Tasks Done", val_tasks, "#2ed573", ft.Icons.CHECKLIST), 
        make_stat_card("Break Time", val_break, "#ff38a2", ft.Icons.COFFEE), 
    ], wrap=True, spacing=10, run_spacing=10, width=370)



    def make_bar(label, height_pct, is_active=False, width=30):
        bar_color = ACCENT if is_active else ACCENT_PURPLE
        return ft.Column([
            ft.Container(width=width, height=max(5, 120 * height_pct), gradient=ft.LinearGradient(begin=ft.Alignment(0, 1),
             end=ft.Alignment(0, -1), colors=["#F6F2EA", bar_color]), border_radius=8,
               tooltip=f"{int(height_pct*100)}%"),
            ft.Text(label, size=10, color=TEXT_SECONDARY)
        ], alignment=ft.MainAxisAlignment.END, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
    
    chart_row = ft.Row([], alignment=ft.MainAxisAlignment.SPACE_EVENLY, height=150)



    def update_records_ui():
        time_toggles.controls.clear()
        for tr in ["Today", "1 Week", "4 Weeks"]:
            bg = ACCENT_PURPLE if app_state.get("view_range") == tr else "#22FFFFFF"
            col = "white" if app_state.get("view_range") == tr else "white70"
            time_toggles.controls.append(
                ft.Container(content=ft.Text(tr, color=col, size=12), bgcolor=bg, padding=10,
                              border=GLASS_BORDER, border_radius=14, 
                             on_click=lambda e, r=tr: set_view_range(e, r))
            )

        view = app_state.get("view_range", "Today")
        history_by_date = {log.get("date"): log for log in app_state.get("history_log", [])}
        days_to_look_back = 0
        if view == "1 Week": days_to_look_back = 6
        elif view == "4 Weeks": days_to_look_back = 27

        aggregated_study = app_state["total_study_seconds"]
        aggregated_break = app_state.get("total_break_seconds", 0)
        aggregated_tasks = sum(1 for t in app_state["tasks"] if t.get("status") == "done")

        if days_to_look_back > 0:
            target_dates = [(datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(1, days_to_look_back + 1)]
            for log in app_state.get("history_log", []):
                if log["date"] in target_dates:
                    aggregated_study += log.get("study_seconds", 0)
                    aggregated_break += log.get("break_seconds", 0)
                    aggregated_tasks += log.get("tasks_done", 0)

        h, rem = divmod(aggregated_study, 3600)
        m, _ = divmod(rem, 60)
        bh, brem = divmod(aggregated_break, 3600)
        bm, _ = divmod(brem, 60)
        
        val_streak.value = f"{app_state.get('streak_days', 0)} day{'s' if app_state.get('streak_days', 0) != 1 else ''}"
        val_time.value = f"{h}h {m}m"
        val_break.value = f"{bh}h {bm}m" 
        val_tasks.value = str(aggregated_tasks)

    
        chart_row.controls.clear()
        today_str = datetime.now().strftime("%Y-%m-%d")
        
        if view in ["Today", "1 Week"]:
            if view == "Today":
                chart_title.value = "7-Day Productivity Trend"
            else:
                chart_title.value = "1-Week Productivity Trend"
                
            last_7_days_data = []
            
            for i in range(6, -1, -1):
                target_date = datetime.now() - timedelta(days=i)
                date_str = target_date.strftime("%Y-%m-%d")
                day_label = target_date.strftime("%a")
                
                if date_str == today_str:
                    sec = app_state["total_study_seconds"]
                    is_today = True
                else:
                    sec = history_by_date.get(date_str, {}).get("study_seconds", 0)
                    is_today = False
                    
                last_7_days_data.append({"label": day_label, "sec": sec, "is_active": is_today})

            max_sec = max([d["sec"] for d in last_7_days_data] + [1]) 
            for d in last_7_days_data:
                chart_row.controls.append(make_bar(d["label"], d["sec"] / max_sec, d["is_active"], width=30))
                
        elif view == "4 Weeks":
            chart_title.value = "4-Week Productivity Trend"
            last_4_weeks_data = []
            
            labels = ["This Wk", "1 Wk Ago", "2 Wks Ago", "3 Wks Ago"]
            
            for w in range(3, -1, -1): 
                week_sec = 0
                for d in range(7):
                    days_ago = w * 7 + d
                    target_date = datetime.now() - timedelta(days=days_ago)
                    date_str = target_date.strftime("%Y-%m-%d")
                    
                    if date_str == today_str:
                        week_sec += app_state["total_study_seconds"]
                    else:
                        week_sec += history_by_date.get(date_str, {}).get("study_seconds", 0)
                
                last_4_weeks_data.append({"label": labels[w], "sec": week_sec, "is_active": (w == 0)})
                
            max_sec = max([d["sec"] for d in last_4_weeks_data] + [1]) 
            for d in last_4_weeks_data:
                chart_row.controls.append(make_bar(d["label"], d["sec"] / max_sec, d["is_active"], width=50))
        
        try: records_panel.update()
        except: pass

    records_panel = ft.Container(
        width=460, height=650, bgcolor=GLASS_BG, blur=ft.Blur(32, 32, ft.BlurTileMode.MIRROR),
          border=GLASS_BORDER, shadow=GLASS_SHADOW,
        border_radius=CARD_RADIUS, padding=24, right=30, bottom=100, visible=False,
        content=ft.Column([
            ft.Text("Focus Stats", size=24, weight="bold", color="white"),
            ft.Text("Refine your workflow with insights.", size=12, color=TEXT_SECONDARY),
            time_toggles, ft.Container(height=5), grid_cards, ft.Container(height=10),
            chart_title, 
            ft.Container(content=chart_row, height=160, padding=10)
        ], scroll=ft.ScrollMode.AUTO) 
    )




    def toggle_fullscreen(e):
        try: page.window_full_screen = not page.window_full_screen
        except: page.window.full_screen = not page.window.full_screen
        page.update()




    def dock_btn(icon, click_action, tooltip):
       
        return ft.Container(
            content=ft.IconButton(icon, icon_color="white", icon_size=24,
                                   on_click=click_action, tooltip=tooltip),
            bgcolor="#18FFFFFF", border=GLASS_BORDER, border_radius=22,
            shadow=ft.BoxShadow(blur_radius=16, spread_radius=-10, color="#44000000",
                                 offset=ft.Offset(0, 6)),
        )

    left_dock = ft.Row([
        dock_btn(ft.Icons.CHECK_BOX, lambda e: toggle_panel(tasks_panel), "Daily Tasks"),
        dock_btn(ft.Icons.AUTO_AWESOME, lambda e: toggle_panel(gemini_panel), "Gemini AI Architect"),
        dock_btn(ft.Icons.GROUPS, lambda e: toggle_panel(multiplayer_panel), "Live Study Hall"), 
        dock_btn(ft.Icons.VIEW_KANBAN_OUTLINED, lambda e: toggle_panel(kanban_panel), "Project Board"), 
    ], spacing=10)

    right_dock = ft.Row([
        dock_btn(ft.Icons.LOCAL_FIRE_DEPARTMENT, lambda e: toggle_panel(records_panel), "Stats & Records"),
        dock_btn(ft.Icons.FULLSCREEN, toggle_fullscreen, "Focus Mode"),
    ], spacing=10)

     
    left_nav_container = ft.Container(content=left_dock, bottom=30, left=40)
    right_nav_container = ft.Container(content=right_dock, bottom=30, right=40)


    main_stack = ft.Stack([
        bg_gradient, center_hub, top_right_controls, tasks_panel, gemini_panel, 
        kanban_panel, records_panel, multiplayer_panel, left_nav_container, right_nav_container
    ], expand=True)

    page.add(main_stack)
    
    # Initialize UI
    render_tasks()
    render_kanban()
    update_records_ui()
    
    # Start tasks
    page.run_task(clock_loop)    
    page.run_task(quote_rotator) 
    page.run_task(poll_leaderboard) 

if __name__ == "__main__":
    ft.app(target=main, assets_dir="assets")