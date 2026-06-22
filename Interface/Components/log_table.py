import flet as ft
from ..Librerias import i18n

class LogTable(ft.Column):
    """
    Componente de visualización de la tabla de logs con cabeceras dinámicas.
    """

    def __init__(self, controller, layout, is_context=False):
        super().__init__()
        self.controller = controller
        self.layout = layout
        self.is_context = is_context
        self.expand = True
        
        self.log_list = None 
        self.header_row = ft.Container(bgcolor="surfaceVariant", padding=ft.Padding(5, 2, 5, 2))
        self.header_checkbox = ft.Checkbox(
            scale=0.8,
            on_change=lambda e: self.controller.toggle_mark_all_on_page(e, is_context=self.is_context),
            tooltip=i18n.t("btn.mark")
        )
        
        self.current_display_columns = []
        
        self._init_controls()
        self.controls = self._build()
        
        self.update_columns(should_update=False)

    def _init_controls(self):
        self.log_list = ft.ListView(
            expand=True,
            spacing=0, 
            item_extent=25, 
        )
        
        if self.is_context:
            self.layout.context_log_table = self.log_list
        else:
            self.layout.log_table = self.log_list 
            self.layout.header_checkbox = self.header_checkbox

        self.page_info = ft.Text(i18n.t("table.pagination", current=1, total=1), size=12)
        self.btn_first = ft.IconButton(ft.Icons.FIRST_PAGE, on_click=lambda e: self.controller.change_page(e, first=True), disabled=True, icon_size=20)
        self.btn_prev = ft.IconButton(ft.Icons.CHEVRON_LEFT, on_click=lambda e: self.controller.change_page(e, delta=-1), disabled=True, icon_size=20)
        self.btn_next = ft.IconButton(ft.Icons.CHEVRON_RIGHT, on_click=lambda e: self.controller.change_page(e, delta=1), disabled=True, icon_size=20)
        self.btn_last = ft.IconButton(ft.Icons.LAST_PAGE, on_click=lambda e: self.controller.change_page(e, last=True), disabled=True, icon_size=20)

        self.btn_prev_marked = ft.IconButton(ft.Icons.KEYBOARD_ARROW_UP, on_click=self.controller.goto_prev_marked, icon_size=24)
        self.btn_next_marked = ft.IconButton(ft.Icons.KEYBOARD_ARROW_DOWN, on_click=self.controller.goto_next_marked, icon_size=24)

        self.page_size_dropdown = ft.Dropdown(
            value=str(self.controller.app_state.page_size),
            options=[ft.dropdown.Option(key=s, text=s) for s in ["50", "100", "200", "500"]],
            width=80, text_size=12, content_padding=5,
        )
        self.page_size_dropdown.on_change = self.controller.on_page_size_change

        self.selection_info = ft.Text("", size=12, italic=True)

        self.btn_mode_multi = ft.IconButton(
            icon=ft.Icons.ADD_BOX_OUTLINED, tooltip=i18n.t("btn.multi_tooltip"), 
            on_click=self.controller.toggle_mode_multi, icon_size=20,
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=5))
        )
        self.btn_mode_range = ft.IconButton(
            icon=ft.Icons.UNFOLD_MORE, tooltip=i18n.t("btn.range_tooltip"), 
            on_click=self.controller.toggle_mode_range, icon_size=20,
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=5))
        )
        self.btn_select_all = ft.IconButton(
            icon=ft.Icons.SELECT_ALL, tooltip=i18n.t("btn.all_tooltip"),
            on_click=self.controller.select_all_on_page, icon_size=20,
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=5))
        )
        self.btn_search_selection = ft.IconButton(
            icon=ft.Icons.SEARCH_SHARP, tooltip=i18n.t("btn.search_tooltip"),
            on_click=self.controller.open_search_selection_dialog, icon_size=20,
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=5))
        )
        self.btn_mark_selected = ft.IconButton(
            icon=ft.Icons.CHECK_BOX, icon_color=ft.Colors.GREEN_400,
            tooltip=i18n.t("btn.mark_selected"), on_click=self.controller.mark_selected, icon_size=20,
        )
        self.btn_unmark_selected = ft.IconButton(
            icon=ft.Icons.CHECK_BOX_OUTLINE_BLANK, icon_color=ft.Colors.RED_400,
            tooltip=i18n.t("btn.unmark_selected"), on_click=self.controller.unmark_selected, icon_size=20,
        )
        self.btn_copy_selected = ft.IconButton(
            icon=ft.Icons.COPY, tooltip=i18n.t("btn.copy_tooltip"),
            on_click=lambda e: self.controller.page.run_task(self.controller.copy_selected_lines), icon_size=20,
        )

        if not self.is_context:
            l = self.layout
            l.page_info, l.btn_first, l.btn_prev, l.btn_next, l.btn_last = self.page_info, self.btn_first, self.btn_prev, self.btn_next, self.btn_last
            l.btn_prev_marked, l.btn_next_marked, l.page_size_dropdown, l.selection_info = self.btn_prev_marked, self.btn_next_marked, self.page_size_dropdown, self.selection_info
            
            l.btn_mode_multi, l.btn_mode_range, l.btn_select_all, l.btn_search_selection = self.btn_mode_multi, self.btn_mode_range, self.btn_select_all, self.btn_search_selection
            l.btn_mark_selected, l.btn_unmark_selected, l.btn_copy_selected = self.btn_mark_selected, self.btn_unmark_selected, self.btn_copy_selected

            self.pagination_row = ft.Row([
                self.btn_first, self.btn_prev, self.page_info, self.btn_next, self.btn_last,
                ft.VerticalDivider(width=10),
                ft.Text(f"{i18n.t('menu.page_size').split(' ')[0]}:", size=12),
                self.page_size_dropdown,
                ft.VerticalDivider(width=10),
                self.layout.goto_line_field,
                ft.VerticalDivider(width=10),
                self.btn_prev_marked, self.btn_next_marked,
                self.selection_info,
            ], alignment=ft.MainAxisAlignment.CENTER, height=40)
        else:
            self.layout.context_title = ft.Text(i18n.t("table.context_title", range=self.controller.app_state.context_range), size=12, weight="bold", italic=True)
            self.pagination_row = ft.Row([
                self.layout.context_title, ft.VerticalDivider(width=10),
                ft.IconButton(ft.Icons.CLOSE, on_click=self.controller.close_context_view, icon_size=20, icon_color=ft.Colors.RED_400, tooltip=i18n.t("btn.close"))
            ], alignment=ft.MainAxisAlignment.CENTER, height=40)

    def update_columns(self, should_update=True):
        df = self.controller.app_state.df
        widths = {"chk": 35, "linea": 55, "timestamp": 135, "nivel": 75, "mensaje": None, "notas": 90}
        
        display_cols = ["chk", "linea", "timestamp", "nivel"]
        std_cols = {"linea", "timestamp", "nivel", "mensaje", "notas"}
        
        extra_cols = []
        if not df.empty:
            extra_cols = [c for c in df.columns if c not in std_cols]
        
        display_cols.extend(extra_cols)
        display_cols.extend(["mensaje", "notas"])
        
        if self.current_display_columns != display_cols:
            self.log_list.controls.clear()
            self.current_display_columns = display_cols
        
        translation_map = {
            "chk": "", "linea": i18n.t("table.col.line"), "timestamp": i18n.t("table.col.time"),
            "nivel": i18n.t("table.col.level"), "mensaje": i18n.t("table.col.message"), "notas": i18n.t("table.col.notes")
        }

        controls = []
        for col in display_cols:
            if col == "chk":
                controls.append(ft.Container(content=self.header_checkbox, width=widths["chk"]))
            else:
                title = translation_map.get(col, col.capitalize())
                width = widths.get(col, 85)
                if col == "mensaje":
                    controls.append(ft.Container(content=ft.Text(title, weight="bold", size=12), expand=True))
                else:
                    controls.append(ft.Container(content=ft.Text(title, weight="bold", size=12), width=width))
        
        self.header_row.content = ft.Row(controls, spacing=5, vertical_alignment=ft.CrossAxisAlignment.CENTER)
        
        if should_update:
            try:
                self.header_row.update()
                self.log_list.update()
            except Exception: pass

    def update_header_text_for_language(self):
        """Actualiza solo el texto de la cabecera sin reconstruir la estructura."""
        self.header_checkbox.tooltip = i18n.t("btn.mark")
        
        translation_map = {
            "chk": "", "linea": i18n.t("table.col.line"), "timestamp": i18n.t("table.col.time"),
            "nivel": i18n.t("table.col.level"), "mensaje": i18n.t("table.col.message"), "notas": i18n.t("table.col.notes")
        }
        
        if self.header_row.content and isinstance(self.header_row.content, ft.Row):
            for i, col_name in enumerate(self.current_display_columns):
                if col_name != "chk":
                    try:
                        text_control = self.header_row.content.controls[i].content
                        if isinstance(text_control, ft.Text):
                            text_control.value = translation_map.get(col_name, col_name.capitalize())
                    except Exception: pass
        
        if self.header_row.page:
            try: self.header_row.update()
            except Exception: pass

    def _build(self):
        return [
            self.header_row,
            ft.Divider(height=1, thickness=1),
            self.log_list,
            ft.Divider(height=1, thickness=1),
            self.layout.empty_message if not self.is_context else ft.Container(),
            self.pagination_row
        ]

    def refresh_ui(self):
        """Actualiza las traducciones de los controles internos de la tabla de forma eficiente."""
        self.update_header_text_for_language()

        if not self.is_context:
            self.page_info.value = i18n.t("table.pagination", current=self.controller.app_state.current_page, total=self.controller.app_state.total_pages)
            if len(self.pagination_row.controls) > 6 and isinstance(self.pagination_row.controls[6], ft.Text):
                self.pagination_row.controls[6].value = f"{i18n.t('menu.page_size').split(' ')[0]}:"
            self.btn_first.tooltip = i18n.t("pagination.first")
            self.btn_prev.tooltip = i18n.t("pagination.prev")
            self.btn_next.tooltip = i18n.t("pagination.next")
            self.btn_last.tooltip = i18n.t("pagination.last")
            self.btn_prev_marked.tooltip = i18n.t("btn.prev_marked")
            self.btn_next_marked.tooltip = i18n.t("btn.next_marked")
        else:
            self.layout.context_title.value = i18n.t("table.context_title", range=self.controller.app_state.context_range)
            if len(self.pagination_row.controls) > 2 and isinstance(self.pagination_row.controls[2], ft.IconButton):
                self.pagination_row.controls[2].tooltip = i18n.t("btn.close")

        self.btn_mode_multi.tooltip = i18n.t("btn.multi_tooltip")
        self.btn_mode_range.tooltip = i18n.t("btn.range_tooltip")
        self.btn_select_all.tooltip = i18n.t("btn.all_tooltip")
        self.btn_search_selection.tooltip = i18n.t("btn.search_tooltip")
        self.btn_mark_selected.tooltip = i18n.t("btn.mark_selected")
        self.btn_unmark_selected.tooltip = i18n.t("btn.unmark_selected")
        self.btn_copy_selected.tooltip = i18n.t("btn.copy_tooltip")
        
        # Eliminamos las llamadas a .update() individuales aquí para que se procesen
        # en la actualización global de la página, evitando latencia.
