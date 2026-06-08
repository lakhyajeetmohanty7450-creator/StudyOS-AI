import os
import asyncio
import logging
from datetime import datetime
from supabase import create_client
from dotenv import load_dotenv

from state import load_data, save_data, check_daily_reset

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

logger = logging.getLogger("studyflow")

class StudyOSApp:
    def __init__(self, page):
        self.page = page
        self.state = load_data()
        self.state["timer_running"] = False
        self.state["focus_seconds"] = 25 * 60
        check_daily_reset(self.state)

        self.supabase_client = None
        if SUPABASE_URL and SUPABASE_KEY:
            try:
                self.supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
            except Exception:
                logger.exception("Unable to initialize Supabase client")

        self.timer_hub = None
        self.tasks_panel = None
        self.kanban_panel = None
        self.stats_panel = None
        self.multiplayer_panel = None
        self.gemini_panel = None

    def save(self):
        save_data(self.state)

    def check_reset(self):
        if check_daily_reset(self.state):
            if self.stats_panel:
                self.stats_panel.update_ui()
            if self.tasks_panel:
                self.tasks_panel.update_ui()

    def sync_cloud_status(self, is_studying):
        async def _sync():
            if not self.supabase_client:
                return
            try:
                loop = asyncio.get_running_loop()
                await loop.run_in_executor(None, lambda: self.supabase_client.table("study_hall").upsert({
                    "username": self.state["username"],
                    "total_minutes": self.state.get("total_study_seconds", 0) // 60,
                    "is_studying": is_studying,
                    "last_active": datetime.now().isoformat()
                }).execute())
            except Exception:
                logger.exception("Unable to sync study status")

        self.page.run_task(_sync)

    def toggle_panel(self, target_panel):
        panels = [
            self.tasks_panel, 
            self.stats_panel, 
            self.kanban_panel, 
            self.gemini_panel, 
            self.multiplayer_panel
        ]
        
        for p in panels:
            if p and p != target_panel:
                p.container.visible = False
                
        if target_panel:
            target_panel.container.visible = not target_panel.container.visible
            target_panel.on_show()

        self.page.update()
