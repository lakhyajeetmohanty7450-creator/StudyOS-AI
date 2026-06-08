import flet as ft
import json
import asyncio
import logging
import google.generativeai as genai
import os
from theme import *

logger = logging.getLogger("studyflow")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

async def ai_generate_schedule(api_key, user_prompt):
    if not api_key or api_key == "YOUR_GEMINI_API_KEY_HERE":
        raise ValueError("Gemini API key is missing. Set GEMINI_API_KEY in your environment.")
        
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.5-flash")
    
    system_instruction = """
    You are the core AI Scheduling engine for 'StudyOS AI', an elite productivity dashboard for Engineering, Medical, Law, PG, and University students.
    Your job is to generate a comprehensive, highly structured day plan optimized for deep study, thesis writing, and heavy syllabus revision.
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


class GeminiPanel:
    def __init__(self, app):
        self.app = app
        
        self.gemini_prompt_input = ft.TextField(
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
        
        self.ai_status_indicator = ft.Text("", size=11, color="white60", italic=True)

        self.container = ft.Container(
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
                self.gemini_prompt_input,
                self.ai_status_indicator,
                ft.Button("Compile Blueprint ✨", on_click=self.process_ai_schedule, bgcolor=ACCENT_PURPLE, color="white", width=400)
            ])
        )

    def on_show(self):
        pass

    async def process_ai_schedule_async(self):
        prompt = self.gemini_prompt_input.value.strip()
        key = GEMINI_API_KEY
        
        if not key:
            self.ai_status_indicator.value = "⚠️ Error: Set GEMINI_API_KEY in your environment."
            self.ai_status_indicator.color = "#ff4757"
            self.app.page.update()
            return
            
        if not prompt:
            self.ai_status_indicator.value = "⚠️ Error: Please enter a directive for the LLM."
            self.ai_status_indicator.color = "#ff4757"
            self.app.page.update()
            return
            
        self.ai_status_indicator.value = "⚡ Directing Gemini Pro Engine... Building blueprint..."
        self.ai_status_indicator.color = "#ffa502"
        self.app.page.update()
        
        try:
            generated_tasks = await ai_generate_schedule(key, prompt)
            
            self.app.state["tasks"].extend(generated_tasks)
            for t in generated_tasks:
                if self.app.kanban_panel:
                    self.app.kanban_panel.auto_route_to_kanban(t["task"], t["subject"])
                
            self.gemini_prompt_input.value = ""
            self.ai_status_indicator.value = f"✨ Injected {len(generated_tasks)} optimization steps into your framework!"
            self.ai_status_indicator.color = "#2ed573"
            
            self.app.save()
            if self.app.tasks_panel:
                self.app.tasks_panel.update_ui()
            if self.app.kanban_panel:
                self.app.kanban_panel.update_ui()
        except Exception as err:
            logger.exception("Unable to generate AI schedule")
            self.ai_status_indicator.value = f"❌ Parsing Error: {str(err)[:50]}..."
            self.ai_status_indicator.color = "#ff4757"
            self.app.page.update()

    def process_ai_schedule(self, e):
        self.app.page.run_task(self.process_ai_schedule_async)
