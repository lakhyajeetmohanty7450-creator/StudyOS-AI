import flet as ft
import asyncio
import logging
from theme import *

logger = logging.getLogger("studyflow")

class MultiplayerPanel:
    def __init__(self, app):
        self.app = app
        
        self.username_input = ft.TextField(value=self.app.state.get("username", ""), 
                            hint_text="Your Study Alias", border_color="white24", color="white", 
                            text_size=11, height=38, content_padding=10, bgcolor="#10FFFFFF", border_radius=18)
        
        self.leaderboard_list = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True, spacing=10)

        self.container = ft.Container(
            width=400, height=650, bgcolor=GLASS_BG, blur=ft.Blur(32, 32, ft.BlurTileMode.MIRROR),
              border=GLASS_BORDER, shadow=GLASS_SHADOW,
            border_radius=CARD_RADIUS, padding=24, left=238, bottom=112, visible=False,
            content=ft.Column([
                ft.Row([ft.Icon(ft.Icons.GROUPS, color="white"), ft.Text("Live Study Hall", 
                                                                         size=20, weight="bold", color="white")]),
                ft.Text("See who is currently grinding.", size=12, color=TEXT_SECONDARY),
                ft.Divider(color="white24"),
                self.username_input, 
                ft.Button("Connect to Cloud 🌐", on_click=self.save_multiplayer_settings, 
                          bgcolor=ACCENT_PURPLE, color="white", width=400),
                ft.Divider(color="white24"),
                self.leaderboard_list
            ], expand=True)
        )

    def on_show(self):
        self.app.page.run_task(self.fetch_lb_now)

    async def fetch_lb_now(self):
        sb = self.app.supabase_client
        if not sb:
            return
        try:
            loop = asyncio.get_running_loop()
            response = await loop.run_in_executor(
                None,
                lambda: sb.table("study_hall").select("*").order("total_minutes", desc=True).limit(10).execute()
            )
            self.leaderboard_list.controls.clear()
            for row in response.data:
                status_icon = "Online" if row.get("is_studying") else "Idle"
                user_text = f"{status_icon} - {row.get('username')}"
                mins = row.get('total_minutes', 0)
                h, m = divmod(mins, 60)
                time_text = f"{h}h {m}m"
                self.leaderboard_list.controls.append(
                    ft.Container(
                        content=ft.Row([ft.Text(user_text, color="white", weight="bold", size=14),
                                         ft.Text(time_text, color="#00b894", weight="bold", size=14)],
                                           alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        bgcolor=GLASS_BG_SOFT, border=GLASS_BORDER, padding=15, border_radius=16
                    )
                )
            self.leaderboard_list.update()
        except Exception:
            logger.exception("Unable to fetch leaderboard")

    def save_multiplayer_settings(self, e):
        self.app.state["username"] = self.username_input.value.strip()
        self.app.save()
        self.app.page.run_task(self.fetch_lb_now)

    async def poll_leaderboard(self):
        while True:
            await asyncio.sleep(10)
            if self.container.visible:
                self.app.page.run_task(self.fetch_lb_now)
