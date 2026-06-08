import flet as ft
import asyncio
from datetime import datetime
import random
import os
import pygame
import logging

from theme import *

logger = logging.getLogger("studyflow")

try:
    pygame.mixer.init()
except Exception:
    logger.exception("Unable to initialize pygame audio mixer")

class TimerHub:
    def __init__(self, app):
        self.app = app
        self.greeting_text = ft.Text(random.choice(QUOTES), size=18, weight="w500", color=MUTED, text_align=ft.TextAlign.CENTER, italic=True)
        
        self.focus_text = ft.Text("25:00", size=140, weight=ft.FontWeight.W_700, color="white")
        self.live_time_text = ft.Text("00:00", size=18, color="white", weight="bold")
        self.live_date_text = ft.Text("00-00-0000", size=13, color=MUTED)
        
        self.time_date_container = ft.Column([self.live_time_text, self.live_date_text], 
                          alignment=ft.MainAxisAlignment.CENTER,
                         horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=2)

        self.timer_circle = ft.Container(
            width=420,
            height=420,
            border_radius=210,
            bgcolor="#08FFFFFF",
            border=GLASS_BORDER,
            content=ft.Column([
                self.focus_text,
                self.time_date_container
            ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
        )

        self.start_btn = ft.Button("Start", width=132, height=46, color="white", bgcolor=ACCENT, 
                              style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=20), elevation=0),
                              on_click=self.toggle_timer)
        self.reset_btn = ft.Button("Reset", width=132, height=46, color="white", bgcolor="#FF6B6B", 
                              style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=20), elevation=0),
                                on_click=self.handle_reset)
        
        self.timer_controls = ft.Row([self.start_btn, self.reset_btn], alignment=ft.MainAxisAlignment.CENTER, spacing=15)
        self.preset_row = ft.Row([], alignment=ft.MainAxisAlignment.CENTER)

        self.custom_hour_input = ft.TextField(width=60, height=35, content_padding=5,
                                          text_align="center", hint_text="hr", bgcolor="#10FFFFFF", 
                                          border_color="#55FFFFFF", color="white", border_radius=18)
        self.custom_min_input = ft.TextField(width=60, height=35, content_padding=5,
                                         text_align="center", hint_text="min", bgcolor="#10FFFFFF", 
                                         border_color="#55FFFFFF", color="white", border_radius=18)

        self.mode_dropdown = ft.Dropdown(
            value=self.app.state.get("timer_mode", "Pomodoro"),
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
            on_select=self.change_timer_mode
        )

        self.top_right_controls = ft.Container(
            content=ft.Column([
                ft.Text("Timer Mode", color=TEXT_SECONDARY, size=12, weight="bold"),
                self.mode_dropdown
            ], spacing=2),
            top=40,
            right=80
        )

        self.container = ft.Container(
            content=ft.Column([
                self.greeting_text,
                ft.Container(height=20),
                self.timer_circle,
                ft.Container(height=20),
                self.timer_controls,
                self.preset_row,
                ft.Container(height=80) 
            ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER,
              scroll=ft.ScrollMode.AUTO),
            alignment=ft.Alignment(0, 0), expand=True
        )

        self.change_timer_mode(None)

    def update_timer_display(self):
        mins, secs = divmod(self.app.state["focus_seconds"], 60)
        if self.app.state["timer_mode"] == "Stopwatch (Count-Up)" or self.app.state["focus_seconds"] >= 3600:
            hours, mins = divmod(mins, 60)
            self.focus_text.value = f"{hours:02d}:{mins:02d}:{secs:02d}"
            self.focus_text.size = 90 
        else:
            self.focus_text.value = f"{mins:02d}:{secs:02d}"
            self.focus_text.size = 140
        try:
            self.focus_text.update()
        except: pass

    async def clock_loop(self):
        while True:
            now = datetime.now()
            self.live_time_text.value = now.strftime("%H:%M")
            self.live_date_text.value = now.strftime("%d-%m-%Y")
            try: 
                self.live_time_text.update()
                self.live_date_text.update()
            except: pass
            
            self.app.check_reset()
            await asyncio.sleep(1) 

    async def quote_rotator(self):
        while True:
            await asyncio.sleep(300) 
            if self.app.state.get("current_mode") != "break":
                self.greeting_text.value = random.choice(QUOTES)
                try: self.greeting_text.update()
                except: pass

    async def timer_loop(self):
        while self.app.state["timer_running"]:
            await asyncio.sleep(1)
            if not self.app.state["timer_running"]: break
            
            is_stopwatch = self.app.state["timer_mode"] == "Stopwatch (Count-Up)"
            
            if is_stopwatch:
                self.app.state["focus_seconds"] += 1
            else:
                if self.app.state["focus_seconds"] > 0:
                    self.app.state["focus_seconds"] -= 1
                else:
                    break
            
            if self.app.state.get("current_mode") == "break":
                self.app.state["total_break_seconds"] = self.app.state.get("total_break_seconds", 0) + 1
            else:
                self.app.state["total_study_seconds"] += 1
            
            self.update_timer_display()
            
            if self.app.state["focus_seconds"] > 0 and self.app.state["focus_seconds"] % 60 == 0:
                self.app.save()
                if self.app.stats_panel:
                    self.app.stats_panel.update_ui()
                if self.app.state.get("current_mode") == "focus":
                    self.app.sync_cloud_status(is_studying=True)
                
        if not is_stopwatch and self.app.state["focus_seconds"] <= 0:
            self.app.state["timer_running"] = False
            self.start_btn.text = "Start"
            self.start_btn.bgcolor = ACCENT
            self.app.sync_cloud_status(is_studying=False)
            
            try:
                base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                alarm_path = os.path.join(base_dir, "assets", "alarm.mp3")
                pygame.mixer.music.load(alarm_path)
                pygame.mixer.music.play()
            except Exception:
                pass
            
            self.app.page.update()

    def toggle_timer(self, e):
        is_valid_start = self.app.state["timer_mode"] == "Stopwatch (Count-Up)" or self.app.state["focus_seconds"] > 0

        if not self.app.state["timer_running"] and is_valid_start:
            self.app.state["timer_running"] = True
            self.start_btn.text = "Pause"
            self.start_btn.bgcolor = "#FF6B6B" 
            if self.app.state.get("current_mode") == "focus":
                self.app.sync_cloud_status(is_studying=True)
            self.app.page.update()
            self.app.page.run_task(self.timer_loop)
        elif self.app.state["timer_running"]:
            self.app.state["timer_running"] = False
            self.start_btn.text = "Resume"
            self.start_btn.bgcolor = ACCENT 
            self.app.sync_cloud_status(is_studying=False)
            self.app.page.update()
            self.app.save()

    def reset_timer(self, mins, is_break=False):
        self.app.state["timer_running"] = False
        self.app.state["focus_seconds"] = mins * 60
        self.app.state["current_mode"] = "break" if is_break else "focus"
        
        self.app.sync_cloud_status(is_studying=False)
        self.update_timer_display()
        self.start_btn.text = "Start"
        self.start_btn.bgcolor = ACCENT
        
        if is_break:
            self.greeting_text.value = "Time to recharge"
        else:
            self.greeting_text.value = random.choice(QUOTES)
        self.app.page.update()

    def set_custom(self, e):
        try:
            h_val = self.custom_hour_input.value.strip()
            m_val = self.custom_min_input.value.strip()
            
            h = int(h_val) if h_val else 0
            m = int(m_val) if m_val else 0
            
            total_mins = (h * 60) + m
            if total_mins > 0:
                self.reset_timer(total_mins)
            
            self.custom_hour_input.value = ""
            self.custom_min_input.value = ""
        except Exception:
            pass

    def handle_reset(self, e):
        mode = self.app.state.get("timer_mode", "Pomodoro")
        if mode == "Pomodoro":
            self.reset_timer(25)
        elif mode == "52/17":
            self.reset_timer(52)
        elif mode == "Animedoro":
            self.reset_timer(45)
        elif mode in ["Countdown", "Stopwatch (Count-Up)"]:
            self.reset_timer(0)
            
        self.start_btn.text = "Start"
        self.start_btn.bgcolor = ACCENT
        self.app.page.update()

    def change_timer_mode(self, e):
        new_mode = self.mode_dropdown.value
        self.app.state["timer_mode"] = new_mode
        
        self.app.state["timer_running"] = False
        self.start_btn.text = "Start"
        self.start_btn.bgcolor = ACCENT
        
        self.preset_row.controls.clear()
        
        if new_mode == "Pomodoro":
            self.app.state["focus_seconds"] = 25 * 60
            self.preset_row.controls.extend([
                ft.TextButton("25m", on_click=lambda e: self.reset_timer(25), icon_color=TEXT_SECONDARY),
                ft.TextButton("50m", on_click=lambda e: self.reset_timer(50), icon_color=TEXT_SECONDARY),
                ft.TextButton("Break 5m", on_click=lambda e: self.reset_timer(5, is_break=True), icon_color=TEXT_SECONDARY),
                ft.Container(width=1, height=20, bgcolor="white24"), 
                self.custom_hour_input,
                ft.Text(":", color=TEXT_SECONDARY, size=14, weight="bold"),
                self.custom_min_input,
                ft.IconButton(ft.Icons.PLAY_ARROW, on_click=self.set_custom, icon_color=TEXT_SECONDARY, icon_size=18)
            ])
        elif new_mode == "52/17":
            self.app.state["focus_seconds"] = 52 * 60
            self.preset_row.controls.extend([
                ft.TextButton("52m Focus", on_click=lambda e: self.reset_timer(52), icon_color=TEXT_SECONDARY),
                ft.TextButton("17m Break", on_click=lambda e: self.reset_timer(17, is_break=True), icon_color=TEXT_SECONDARY),
            ])
        elif new_mode == "Animedoro":
            self.app.state["focus_seconds"] = 45 * 60
            self.preset_row.controls.extend([
                ft.TextButton("45m Study", on_click=lambda e: self.reset_timer(45), icon_color=TEXT_SECONDARY),
                ft.TextButton("20m Episode", on_click=lambda e: self.reset_timer(20, is_break=True), icon_color=TEXT_SECONDARY),
            ])
        elif new_mode == "Countdown":
            self.app.state["focus_seconds"] = 0
            self.preset_row.controls.extend([
                ft.Text("Custom:", color=TEXT_SECONDARY, size=14),
                self.custom_hour_input,
                ft.Text(":", color=TEXT_SECONDARY, size=14, weight="bold"),
                self.custom_min_input,
                ft.IconButton(ft.Icons.PLAY_ARROW, on_click=self.set_custom, icon_color=TEXT_SECONDARY, icon_size=18)
            ])
        elif new_mode == "Stopwatch (Count-Up)":
            self.app.state["focus_seconds"] = 0
            self.preset_row.controls.extend([
                ft.TextButton("Reset", on_click=lambda e: self.reset_timer(0), icon_color=TEXT_SECONDARY)
            ])
            
        self.update_timer_display()
        if self.app.page:
            try: self.app.page.update()
            except: pass
