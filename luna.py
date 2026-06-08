import flet as ft
import logging

from core import StudyOSApp
from theme import *
from components.timer import TimerHub
from components.tasks import TasksPanel
from components.kanban import KanbanPanel
from components.stats import StatsPanel
from components.gemini import GeminiPanel
from components.multiplayer import MultiplayerPanel

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("studyflow")

def main(page: ft.Page):
    page.title = "StudyOS AI"
    page.padding = 0  
    
    page.window_width = 1440
    page.window_height = 900
    page.window_maximized = True
    page.theme_mode = ft.ThemeMode.DARK

    app = StudyOSApp(page)

    app.timer_hub = TimerHub(app)
    app.tasks_panel = TasksPanel(app)
    app.kanban_panel = KanbanPanel(app)
    app.stats_panel = StatsPanel(app)
    app.gemini_panel = GeminiPanel(app)
    app.multiplayer_panel = MultiplayerPanel(app)

    bg_gradient = ft.Container(
        expand=True,
        gradient=ft.LinearGradient(
            begin=ft.Alignment(-1, -1), end=ft.Alignment(1, 1),
            colors=[BG_PRIMARY, BG_SECONDARY, BG_TERTIARY],
        ),
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
        dock_btn(ft.Icons.CHECK_BOX, lambda e: app.toggle_panel(app.tasks_panel), "Daily Tasks"),
        dock_btn(ft.Icons.AUTO_AWESOME, lambda e: app.toggle_panel(app.gemini_panel), "Gemini AI Architect"),
        dock_btn(ft.Icons.GROUPS, lambda e: app.toggle_panel(app.multiplayer_panel), "Live Study Hall"), 
        dock_btn(ft.Icons.VIEW_KANBAN_OUTLINED, lambda e: app.toggle_panel(app.kanban_panel), "Project Board"), 
    ], spacing=10)

    right_dock = ft.Row([
        dock_btn(ft.Icons.LOCAL_FIRE_DEPARTMENT, lambda e: app.toggle_panel(app.stats_panel), "Stats & Records"),
        dock_btn(ft.Icons.FULLSCREEN, toggle_fullscreen, "Focus Mode"),
    ], spacing=10)
     
    left_nav_container = ft.Container(content=left_dock, bottom=30, left=40)
    right_nav_container = ft.Container(content=right_dock, bottom=30, right=40)

    main_stack = ft.Stack([
        bg_gradient, 
        app.timer_hub.container, 
        app.timer_hub.top_right_controls, 
        app.tasks_panel.container, 
        app.gemini_panel.container, 
        app.kanban_panel.container, 
        app.stats_panel.container, 
        app.multiplayer_panel.container, 
        left_nav_container, 
        right_nav_container
    ], expand=True)

    page.add(main_stack)
    
    app.tasks_panel.update_ui()
    app.kanban_panel.update_ui()
    app.stats_panel.update_ui()
    
    page.run_task(app.timer_hub.clock_loop)    
    page.run_task(app.timer_hub.quote_rotator) 
    page.run_task(app.multiplayer_panel.poll_leaderboard) 

if __name__ == "__main__":
    ft.app(target=main, assets_dir="assets")


