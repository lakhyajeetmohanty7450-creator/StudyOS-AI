import flet as ft
from theme import *
from utils import get_emoji_and_subject, parse_timetable, categorize_time

class TasksPanel:
    def __init__(self, app):
        self.app = app
        
        self.progress_bar = ft.ProgressBar(width=360, value=0.0, color=ACCENT, bgcolor="#35FFFFFF")
        self.progress_text = ft.Text("0% Completed", color=TEXT_SECONDARY, size=12)
        self.task_list_ui = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True, spacing=5)
        
        self.manual_time_input = ft.TextField(hint_text="Time (e.g. 10 AM)", width=130,
                                          border_color="#66FFFFFF", bgcolor="#10FFFFFF", 
                                          color="white", text_size=12, content_padding=10, border_radius=18)
        self.manual_input = ft.TextField(hint_text="Type your priority...", expand=True, 
                                    border_color="#66FFFFFF", bgcolor="#10FFFFFF", 
                                    color="white", content_padding=10, border_radius=18)
        
        self.sched_input = ft.TextField(
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

        self.container = ft.Container(
            width=400, height=650,
            bgcolor=GLASS_BG, blur=ft.Blur(32, 32, ft.BlurTileMode.MIRROR), 
            border=GLASS_BORDER, shadow=GLASS_SHADOW, border_radius=CARD_RADIUS, padding=24, 
            left=30, bottom=100, visible=False,
            content=ft.Column([
                ft.Text("Daily Agenda", size=20, weight="bold", color="white"),
                self.progress_bar, self.progress_text,
                ft.Divider(color="white24"),
                ft.Container(content=self.task_list_ui, expand=True),
                ft.Row([self.manual_time_input, self.manual_input, ft.IconButton(ft.Icons.ADD_CIRCLE, 
                                                                       icon_color=ACCENT, on_click=self.add_manual)]),
                ft.Divider(color="white24"),
                ft.Text("🤖 AI Import", size=14, weight="bold", color="white"),
                self.sched_input,
                ft.Button("Auto-Parse ✨", on_click=self.sync_data, bgcolor="#00b894", color="white", width=400)
            ])
        )

    def on_show(self):
        pass

    def update_progress(self):
        if not self.app.state["tasks"]:
            self.progress_bar.value = 0.0
            self.progress_text.value = "0% Completed"
        else:
            total = len(self.app.state["tasks"])
            completed = sum(1 for t in self.app.state["tasks"] if t.get("status") == "done")
            pct = completed / total
            self.progress_bar.value = pct
            self.progress_text.value = f"{int(pct * 100)}% Completed ({completed}/{total})"

            if pct == 1.0 and not self.app.state.get("today_streak_claimed", False):
                self.app.state["streak_days"] = self.app.state.get("streak_days", 0) + 1
                self.app.state["today_streak_claimed"] = True
                self.app.save()
                if self.app.stats_panel:
                    self.app.stats_panel.update_ui()
            elif pct < 1.0 and self.app.state.get("today_streak_claimed", False):
                self.app.state["streak_days"] = max(0, self.app.state.get("streak_days", 0) - 1)
                self.app.state["today_streak_claimed"] = False
                self.app.save()
                if self.app.stats_panel:
                    self.app.stats_panel.update_ui()

        try:
            self.progress_bar.update()
            self.progress_text.update()
        except Exception:
            pass

    def handle_checkbox(self, e, idx):
        self.app.state["tasks"][idx]["status"] = "done" if e.control.value else "pending"
        self.app.save()
        self.update_progress()
        self.update_ui()

    def delete_task(self, idx):
        self.app.state["tasks"].pop(idx)
        self.app.save()
        self.update_progress()
        self.update_ui()

    def update_ui(self):
        self.task_list_ui.controls.clear()
        groups = {"Morning": [], "Afternoon": [], "Evening": [], "Night": [], "Unscheduled": []}
        for i, task in enumerate(self.app.state["tasks"]):
            cat = categorize_time(task.get("start_time", ""))
            if cat in groups:
                groups[cat].append((i, task))
            else:
                groups["Unscheduled"].append((i, task))

        for group_name, tasks_in_group in groups.items():
            if tasks_in_group:
                self.task_list_ui.controls.append(ft.Container(height=5))
                self.task_list_ui.controls.append(ft.Text(group_name, size=14, weight="bold", color=ACCENT))
                for idx, task in tasks_in_group:
                    display = f"{task['emoji']} {task['start_time']} -> {task['task']}" if task['start_time'] else f"{task['emoji']} {task['task']}"
                    
                    task_text_ui = ft.Text(display, size=13, expand=True, overflow=ft.TextOverflow.ELLIPSIS, max_lines=2)
                    
                    is_done = task.get("status") == "done"
                    task_text_ui.color = "white54" if is_done else "white"
                    task_text_ui.style = ft.TextStyle(decoration=ft.TextDecoration.LINE_THROUGH) if is_done else None
                    cb = ft.Checkbox(value=is_done, fill_color=ACCENT, check_color="#25302D", 
                                     on_change=lambda e, i=idx: self.handle_checkbox(e, i))
                        
                    del_btn = ft.IconButton(icon=ft.Icons.DELETE_OUTLINE, icon_color="white54",
                                             icon_size=18, on_click=lambda e, i=idx: self.delete_task(i))
                    
                    self.task_list_ui.controls.append(ft.Row([cb, task_text_ui, del_btn],
                                                         alignment=ft.MainAxisAlignment.SPACE_BETWEEN))
                    
        self.update_progress()
        try:
            if self.container.visible:
                self.container.update()
        except Exception:
            pass

    def add_manual(self, e):
        if self.manual_input.value.strip():
            emoji, subject = get_emoji_and_subject(self.manual_input.value)
            task_text = self.manual_input.value
            time_text = self.manual_time_input.value.strip() 
            
            self.app.state["tasks"].append({
                "start_time": time_text, 
                "task": task_text, 
                "emoji": emoji, 
                "subject": subject, 
                "status": "pending", 
                "is_now": False
            })
            if self.app.kanban_panel:
                self.app.kanban_panel.auto_route_to_kanban(task_text, subject)
            
            self.manual_input.value = ""
            self.manual_time_input.value = "" 
            self.app.save()
            self.update_ui()
            if self.app.kanban_panel:
                self.app.kanban_panel.update_ui()

    def sync_data(self, e):
        if self.sched_input.value.strip():
            new_tasks = parse_timetable(self.sched_input.value)
            self.app.state["tasks"].extend(new_tasks)
            
            for t in new_tasks:
                if self.app.kanban_panel:
                    self.app.kanban_panel.auto_route_to_kanban(t["task"], t["subject"])
                
            self.sched_input.value = ""
            self.app.save()
            self.update_ui()
            if self.app.kanban_panel:
                self.app.kanban_panel.update_ui()
