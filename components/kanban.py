import flet as ft
from theme import *

class KanbanPanel:
    def __init__(self, app):
        self.app = app
        
        self.todo_list = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True, spacing=10)
        self.in_progress_list = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True, spacing=10)
        self.done_list = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True, spacing=10)
        
        self.kanban_input = ft.TextField(hint_text="Add a new project task...", expand=True, 
                                    border_color="white24", color="white", bgcolor="#10FFFFFF", border_radius=18)

        self.kanban_columns = ft.Row([
            self.make_kanban_col("To-Do", self.todo_list, "To-Do", "#ff4757"), 
            self.make_kanban_col("In Progress", self.in_progress_list, "In Progress", "#ffa502"), 
            self.make_kanban_col("Done", self.done_list, "Done", "#2ed573"), 
        ], expand=True, spacing=15, alignment=ft.MainAxisAlignment.CENTER)

        self.container = ft.Container(
            width=860, height=650, bgcolor=GLASS_BG, blur=ft.Blur(32, 32, ft.BlurTileMode.MIRROR), border=GLASS_BORDER,
              shadow=GLASS_SHADOW,
            border_radius=CARD_RADIUS, padding=24, left=238, bottom=112, visible=False,
            content=ft.Column([
                ft.Row([ft.Icon(ft.Icons.VIEW_KANBAN, color="white"), ft.Text("Project Board", size=24, weight="bold", 
                                                                              color="white")]),
                ft.Text("Tasks from your Daily Agenda are automatically routed here.", size=12, color=TEXT_SECONDARY),
                ft.Container(height=5),
                ft.Row([self.kanban_input, ft.IconButton(ft.Icons.ADD_CIRCLE, icon_color=ACCENT, on_click=self.add_kanban)]),
                ft.Divider(color="white24"), 
                ft.Container(height=5),
                self.kanban_columns
            ], expand=True)
        )

    def on_show(self):
        self.update_ui()

    def auto_route_to_kanban(self, task_text, subject):
        if subject == "Personal":
            return
            
        formatted_task = f"[{subject}] {task_text}"
        
        all_board_tasks = self.app.state["kanban_board"]["To-Do"] + \
                          self.app.state["kanban_board"]["In Progress"] + \
                          self.app.state["kanban_board"]["Done"]
                          
        if formatted_task not in all_board_tasks:
            self.app.state["kanban_board"]["To-Do"].append(formatted_task)

    def drag_accept(self, e):
        src_data = self.app.page.get_control(e.src_id).data
        task_text, source_col = src_data["text"], src_data["source_col"]
        dest_col = e.control.data 
        if source_col != dest_col:
            self.app.state["kanban_board"][source_col].pop(src_data["idx"])
            self.app.state["kanban_board"][dest_col].append(task_text)
            self.app.save()
            self.update_ui()

    def delete_kanban_task(self, col_name, idx):
        self.app.state["kanban_board"][col_name].pop(idx)
        self.app.save()
        self.update_ui()

    def update_ui(self):
        for lst in [self.todo_list, self.in_progress_list, self.done_list]: 
            lst.controls.clear()
            
        def create_draggable(task_text, col_name, idx):
            card_ui = ft.Container(
                content=ft.Row([
                    ft.Text(task_text, color="white", size=13, expand=True), 
                    ft.IconButton(ft.Icons.DELETE_OUTLINE, icon_color="white54", 
                                  icon_size=16, on_click=lambda e: self.delete_kanban_task(col_name, idx))
                ]), 
                bgcolor=GLASS_BG_SOFT, border=GLASS_BORDER, padding=15, border_radius=16
            )
            dragging_ui = ft.Container(content=ft.Text(task_text, color="white", size=13, weight="bold"), 
                                       bgcolor=ACCENT_PURPLE, padding=15, border_radius=16, width=220, opacity=0.8)
            return ft.Draggable(group="kanban", data={"text": task_text, "source_col": col_name, "idx": idx}, 
                                content=card_ui, content_feedback=dragging_ui)

        for i, t in enumerate(self.app.state["kanban_board"]["To-Do"]): 
            item = create_draggable(t, "To-Do", i)
            if item: self.todo_list.controls.append(item)
            
        for i, t in enumerate(self.app.state["kanban_board"]["In Progress"]): 
            item = create_draggable(t, "In Progress", i)
            if item: self.in_progress_list.controls.append(item)
            
        for i, t in enumerate(self.app.state["kanban_board"]["Done"]): 
            item = create_draggable(t, "Done", i)
            if item: self.done_list.controls.append(item)
            
        try: 
            self.todo_list.update()
            self.in_progress_list.update()
            self.done_list.update()
        except Exception: 
            pass

    def make_kanban_col(self, title, item_list, col_name, accent_color):
        return ft.DragTarget(
            group="kanban", data=col_name, on_accept=self.drag_accept,
            content=ft.Container(
                content=ft.Column([
                    ft.Container(content=ft.Text(title, weight="bold", color="white", size=14),
                                  bgcolor=accent_color, padding=10, border_radius=15),
                    ft.Container(height=5), item_list
                ]), bgcolor=GLASS_BG_SOFT, border=GLASS_BORDER, border_radius=22, padding=15, width=250, expand=True
            )
        )

    def add_kanban(self, e):
        if self.kanban_input.value.strip():
            self.app.state["kanban_board"]["To-Do"].append(self.kanban_input.value.strip())
            self.kanban_input.value = ""
            self.app.save()
            self.update_ui()
