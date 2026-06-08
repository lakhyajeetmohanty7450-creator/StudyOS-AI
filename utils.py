import re

# Pre-compile regex for performance
TIMETABLE_PATTERN = re.compile(r"^\s*(.*?(?:AM|PM))\s+(.*)$", re.IGNORECASE)
TIME_CATEGORIZE_PATTERN = re.compile(r'(\d{1,2}):?(\d{2})?\s*(AM|PM)', re.IGNORECASE)

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
    parsed_tasks = []
    for line in raw_text.strip().split("\n"):
        line = line.strip()
        if not line: continue
        match = TIMETABLE_PATTERN.match(line)
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

def categorize_time(time_string):
    if not time_string: return "Unscheduled"
    try:
        match = TIME_CATEGORIZE_PATTERN.search(time_string)
        if match:
            hr = int(match.group(1))
            meridiem = match.group(3).upper()
            if meridiem == "PM" and hr != 12: hr += 12
            if meridiem == "AM" and hr == 12: hr = 0
            if 5 <= hr < 12: return "Morning"
            elif 12 <= hr < 17: return "Afternoon"
            elif 17 <= hr < 21: return "Evening"
            else: return "Night"
    except Exception:
        pass
    return "Unscheduled"
