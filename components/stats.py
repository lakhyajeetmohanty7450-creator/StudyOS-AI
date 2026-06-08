import flet as ft
from datetime import datetime, timedelta
from theme import *

class StatsPanel:
    def __init__(self, app):
        self.app = app
        
        self.time_toggles = ft.Row([], spacing=10)
        self.chart_title = ft.Text("7-Day Productivity Trend", size=16, weight="bold", color="white")
        
        self.val_streak = ft.Text("0 days", size=24, weight="bold", color="white")
        self.val_time = ft.Text("0h 0m", size=24, weight="bold", color="white")
        self.val_tasks = ft.Text("0", size=24, weight="bold", color="white")
        self.val_break = ft.Text("0h 0m", size=24, weight="bold", color="white") 

        self.grid_cards = ft.Row([
            self.make_stat_card("Streak", self.val_streak, "#ff4757", ft.Icons.LOCAL_FIRE_DEPARTMENT), 
            self.make_stat_card("Focus Time", self.val_time, "#ffa502", ft.Icons.BOLT), 
            self.make_stat_card("Tasks Done", self.val_tasks, "#2ed573", ft.Icons.CHECKLIST), 
            self.make_stat_card("Break Time", self.val_break, "#ff38a2", ft.Icons.COFFEE), 
        ], wrap=True, spacing=10, run_spacing=10, width=370)

        self.chart_row = ft.Row([], alignment=ft.MainAxisAlignment.SPACE_EVENLY, height=150)

        self.container = ft.Container(
            width=460, height=650, bgcolor=GLASS_BG, blur=ft.Blur(32, 32, ft.BlurTileMode.MIRROR),
              border=GLASS_BORDER, shadow=GLASS_SHADOW,
            border_radius=CARD_RADIUS, padding=24, right=30, bottom=100, visible=False,
            content=ft.Column([
                ft.Text("Focus Stats", size=24, weight="bold", color="white"),
                ft.Text("Refine your workflow with insights.", size=12, color=TEXT_SECONDARY),
                self.time_toggles, ft.Container(height=5), self.grid_cards, ft.Container(height=10),
                self.chart_title, 
                ft.Container(content=self.chart_row, height=160, padding=10)
            ], scroll=ft.ScrollMode.AUTO) 
        )

    def on_show(self):
        self.update_ui()

    def set_view_range(self, e, range_name):
        self.app.state["view_range"] = range_name
        self.app.save()
        self.update_ui()

    def make_stat_card(self, title, value_ref, color, icon):
        return ft.Container(
            content=ft.Column([
                ft.Row([ft.Text(title, size=13, color="white", weight="bold"), ft.Icon(icon, color=ACCENT, size=16)], 
                       alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Container(height=5), value_ref
            ]), bgcolor=GLASS_BG_SOFT, border=GLASS_BORDER, shadow=ft.BoxShadow(blur_radius=16, spread_radius=-10, 
                color="#55000000", offset=ft.Offset(0, 8)), border_radius=16, padding=15, width=170, height=100
        )

    def make_bar(self, label, height_pct, is_active=False, width=30):
        bar_color = ACCENT if is_active else ACCENT_PURPLE
        return ft.Column([
            ft.Container(width=width, height=max(5, 120 * height_pct), gradient=ft.LinearGradient(begin=ft.Alignment(0, 1),
             end=ft.Alignment(0, -1), colors=["#F6F2EA", bar_color]), border_radius=8,
               tooltip=f"{int(height_pct*100)}%"),
            ft.Text(label, size=10, color=TEXT_SECONDARY)
        ], alignment=ft.MainAxisAlignment.END, horizontal_alignment=ft.CrossAxisAlignment.CENTER)

    def update_ui(self):
        self.time_toggles.controls.clear()
        for tr in ["Today", "1 Week", "4 Weeks"]:
            bg = ACCENT_PURPLE if self.app.state.get("view_range") == tr else "#22FFFFFF"
            col = "white" if self.app.state.get("view_range") == tr else "white70"
            self.time_toggles.controls.append(
                ft.Container(content=ft.Text(tr, color=col, size=12), bgcolor=bg, padding=10,
                              border=GLASS_BORDER, border_radius=14, 
                             on_click=lambda e, r=tr: self.set_view_range(e, r))
            )

        view = self.app.state.get("view_range", "Today")
        history_by_date = {log.get("date"): log for log in self.app.state.get("history_log", [])}
        days_to_look_back = 0
        if view == "1 Week": days_to_look_back = 6
        elif view == "4 Weeks": days_to_look_back = 27

        aggregated_study = self.app.state["total_study_seconds"]
        aggregated_break = self.app.state.get("total_break_seconds", 0)
        aggregated_tasks = sum(1 for t in self.app.state["tasks"] if t.get("status") == "done")

        if days_to_look_back > 0:
            target_dates = [(datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(1, days_to_look_back + 1)]
            for log in self.app.state.get("history_log", []):
                if log["date"] in target_dates:
                    aggregated_study += log.get("study_seconds", 0)
                    aggregated_break += log.get("break_seconds", 0)
                    aggregated_tasks += log.get("tasks_done", 0)

        h, rem = divmod(aggregated_study, 3600)
        m, _ = divmod(rem, 60)
        bh, brem = divmod(aggregated_break, 3600)
        bm, _ = divmod(brem, 60)
        
        self.val_streak.value = f"{self.app.state.get('streak_days', 0)} day{'s' if self.app.state.get('streak_days', 0) != 1 else ''}"
        self.val_time.value = f"{h}h {m}m"
        self.val_break.value = f"{bh}h {bm}m" 
        self.val_tasks.value = str(aggregated_tasks)

        self.chart_row.controls.clear()
        today_str = datetime.now().strftime("%Y-%m-%d")
        
        if view in ["Today", "1 Week"]:
            if view == "Today":
                self.chart_title.value = "7-Day Productivity Trend"
            else:
                self.chart_title.value = "1-Week Productivity Trend"
                
            last_7_days_data = []
            
            for i in range(6, -1, -1):
                target_date = datetime.now() - timedelta(days=i)
                date_str = target_date.strftime("%Y-%m-%d")
                day_label = target_date.strftime("%a")
                
                if date_str == today_str:
                    sec = self.app.state["total_study_seconds"]
                    is_today = True
                else:
                    sec = history_by_date.get(date_str, {}).get("study_seconds", 0)
                    is_today = False
                    
                last_7_days_data.append({"label": day_label, "sec": sec, "is_active": is_today})

            max_sec = max([d["sec"] for d in last_7_days_data] + [1]) 
            for d in last_7_days_data:
                self.chart_row.controls.append(self.make_bar(d["label"], d["sec"] / max_sec, d["is_active"], width=30))
                
        elif view == "4 Weeks":
            self.chart_title.value = "4-Week Productivity Trend"
            last_4_weeks_data = []
            
            labels = ["This Wk", "1 Wk Ago", "2 Wks Ago", "3 Wks Ago"]
            
            for w in range(3, -1, -1): 
                week_sec = 0
                for d in range(7):
                    days_ago = w * 7 + d
                    target_date = datetime.now() - timedelta(days=days_ago)
                    date_str = target_date.strftime("%Y-%m-%d")
                    
                    if date_str == today_str:
                        week_sec += self.app.state["total_study_seconds"]
                    else:
                        week_sec += history_by_date.get(date_str, {}).get("study_seconds", 0)
                
                last_4_weeks_data.append({"label": labels[w], "sec": week_sec, "is_active": (w == 0)})
                
            max_sec = max([d["sec"] for d in last_4_weeks_data] + [1]) 
            for d in last_4_weeks_data:
                self.chart_row.controls.append(self.make_bar(d["label"], d["sec"] / max_sec, d["is_active"], width=50))
        
        try:
            if self.container.visible:
                self.container.update()
        except Exception: 
            pass
