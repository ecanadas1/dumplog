import flet as ft
import pandas as pd
import logging
import re
import time
import asyncio
from Model.log_entry import LogEntry
from ..Librerias import i18n

logger = logging.getLogger(__name__)

class TableRenderer:
    """
    Renderiza y actualiza la tabla de registros de log de forma eficiente.
    Soporta columnas dinámicas.
    """

    _MSG_PATTERNS = [
        (re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b'), ft.Colors.BLUE_400),          # Direcciones IP
        (re.compile(r'(?<=:)\d{4,5}\b'), ft.Colors.AMBER_600),                      # Puerto tras ':'
        (re.compile(r'\bport\s+(\d{4,5})\b', re.IGNORECASE), ft.Colors.AMBER_600), # Palabra 'port NNN'
        (re.compile(r'\b(ERROR|FAIL|FAILED|restart|CRITICAL|FAILURE|shutdown|reboot|UP)\b', re.IGNORECASE), ft.Colors.RED_500),
        (re.compile(r'\b(SUCCESSFULLY|SUCCESS|OK|DONE|COMPLETED|DOWN)\b', re.IGNORECASE), ft.Colors.GREEN_500),
        (re.compile(r'\b0x[0-9a-fA-F]+\b'), ft.Colors.PURPLE_400),                 # Valores hexadecimales
    ]

    MAX_DISPLAY_LEN = 500

    def __init__(self, page, app_state, layout, on_row_click, controller):
        self.page = page
        self.app_state = app_state
        self.layout = layout
        self.on_row_click = on_row_click
        self.controller = controller
        
        # Definición de anchos ajustados (debe coincidir con log_table.py)
        self.col_widths = {
            "chk": 35, 
            "linea": 55, 
            "timestamp": 135, 
            "nivel": 75,
            "mensaje": None, # Expandible
            "notas": 90
        }

    def _handle_row_click(self, e):
        if e.control.data is not None:
            self.on_row_click(e, e.control.data)

    def _handle_row_double_click(self, e):
        if e.control.data is not None:
            self.controller.show_context_view(e.control.data)

    def _handle_checkbox_change(self, e):
        if e.control.data is not None:
            self.controller.toggle_mark(e, e.control.data)

    def _get_display_value(self, value):
        """Convierte un valor a string y reemplaza 'nan' o 'None' por cadena vacía."""
        s_val = str(value)
        if s_val.lower() in ['nan', 'none', '<na>']:
            return ""
        return s_val

    def _build_cell(self, col_name: str, col_val: str, line_num: int, is_marked: bool = False, is_target_line: bool = False) -> ft.Control:
        if col_name == "chk":
            return ft.Container(
                content=ft.Checkbox(
                    value=is_marked,
                    on_change=self._handle_checkbox_change,
                    data=line_num,
                    scale=0.8
                ),
                width=self.col_widths["chk"],
                alignment=ft.alignment.Alignment(-1, 0)
            )
        elif col_name == "mensaje":
            raw_msg = col_val
            if len(raw_msg) > self.MAX_DISPLAY_LEN:
                display_msg = raw_msg[:self.MAX_DISPLAY_LEN] + "..."
                tooltip_msg = raw_msg[:1000]
            else:
                display_msg = raw_msg
                tooltip_msg = None
            msg_val, msg_spans = self._calculate_message_content(display_msg)
            return ft.Container(
                content=ft.Text(value=msg_val, spans=msg_spans, size=11, selectable=True, tooltip=tooltip_msg, no_wrap=True, overflow=ft.TextOverflow.ELLIPSIS, max_lines=1, text_align=ft.TextAlign.LEFT),
                expand=True,
                padding=ft.Padding.only(right=10),
                alignment=ft.alignment.Alignment(-1, 0)
            )
        elif col_name == "nivel":
            level_color = self.layout._get_level_color(col_val) if self.app_state.syntax_highlighting else None
            level_weight = ft.FontWeight.BOLD if (self.app_state.syntax_highlighting or is_target_line) else None
            return ft.Container(
                content=ft.Text(col_val, size=11, color=level_color, weight=level_weight, no_wrap=True, overflow=ft.TextOverflow.ELLIPSIS, max_lines=1, text_align=ft.TextAlign.LEFT),
                width=self.col_widths.get(col_name, 85),
                alignment=ft.alignment.Alignment(-1, 0)
            )
        else:
            width = self.col_widths.get(col_name, 85)
            weight = ft.FontWeight.BOLD if is_target_line else None
            return ft.Container(
                content=ft.Text(col_val, size=11, weight=weight, no_wrap=True, overflow=ft.TextOverflow.ELLIPSIS, max_lines=1, text_align=ft.TextAlign.LEFT, tooltip=col_val if col_val else None),
                width=width,
                alignment=ft.alignment.Alignment(-1, 0)
            )

    def update_row_colors(self):
        selected_lines = self.app_state.selected_lines
        selected_color = ft.Colors.with_opacity(0.25, ft.Colors.BLUE)
        
        rows = self.layout.log_table.controls
        if not rows: return

        for row_gesture in rows:
            if not row_gesture.visible: continue
            line_num = row_gesture.data
            is_selected = line_num in selected_lines
            new_color = selected_color if is_selected else None
            container = row_gesture.content
            if container.bgcolor != new_color:
                container.bgcolor = new_color
        self.page.update()
        self.update_status_bar()

    def refresh_table(self):
        with self.controller._ui_lock:
            df = self.app_state.filtered_df
            total_items = len(df)
            
            self.app_state.total_pages = max(1, (total_items + self.app_state.page_size - 1) // self.app_state.page_size)
            if self.app_state.current_page > self.app_state.total_pages:
                self.app_state.current_page = self.app_state.total_pages
            if self.app_state.current_page < 1:
                self.app_state.current_page = 1

            if df.empty:
                self.layout.log_table.controls.clear()
                self.layout.empty_message.visible = True
                self.update_pagination_ui()
                self.update_status_bar()
                self.page.update()
                return
            
            self.layout.empty_message.visible = False

            start_idx = (self.app_state.current_page - 1) * self.app_state.page_size
            end_idx = start_idx + self.app_state.page_size
            page_df = df.iloc[start_idx:end_idx]
            
            current_rows_count = len(page_df)

            page_line_nums = set(page_df['linea'].astype(int))
            all_marked = page_line_nums.issubset(self.app_state.marked_lines) if page_line_nums else False
            self.layout.header_checkbox.value = all_marked
            try: self.layout.header_checkbox.update()
            except Exception: pass

            marked_lines = self.app_state.marked_lines
            selected_lines = self.app_state.selected_lines
            selected_color = ft.Colors.with_opacity(0.25, ft.Colors.BLUE)

            existing_rows = self.layout.log_table.controls
            rows_needed = current_rows_count
            rows_available = len(existing_rows)
            
            # Obtener el orden de las columnas a mostrar desde LogTable
            display_columns_order = self.layout.table_comp.current_display_columns

            # --- FUNCIÓN HELPER PARA CREAR UNA FILA ---
            def create_row_controls(line_num, row_data, is_context_row=False):
                is_marked = line_num in marked_lines
                
                cells = []
                for col_name in display_columns_order:
                    col_val = self._get_display_value(getattr(row_data, col_name, '')) if col_name != "chk" else ""
                    cells.append(self._build_cell(col_name, col_val, line_num, is_marked=is_marked))
                
                row_content = ft.Row(controls=cells, spacing=5, vertical_alignment=ft.CrossAxisAlignment.CENTER)
                
                bgcolor = selected_color if line_num in selected_lines else None
                if is_context_row and line_num == self.app_state.context_line:
                    bgcolor = ft.Colors.with_opacity(0.3, ft.Colors.AMBER) # Resaltar línea central en contexto

                container = ft.Container(
                    content=row_content,
                    bgcolor=bgcolor,
                    padding=ft.Padding.symmetric(horizontal=5, vertical=0),
                    border=ft.Border.only(bottom=ft.BorderSide(0.5, "outlineVariant")),
                    height=25 
                )

                return ft.GestureDetector(
                    content=container,
                    on_tap=self._handle_row_click,
                    on_double_tap=self._handle_row_double_click,
                    data=line_num
                )

            # --- ESTRATEGIA DE POOL ---
            for i, row_data in enumerate(page_df.itertuples(index=False)):
                line_num = int(row_data.linea)
                
                if i < rows_available:
                    # RECICLAR
                    gesture_row = existing_rows[i]
                    gesture_row.data = line_num
                    
                    container_row = gesture_row.content
                    container_row.bgcolor = selected_color if line_num in selected_lines else None
                    
                    inner_row = container_row.content
                    cells = inner_row.controls
                    
                    # Actualizar celdas dinámicamente
                    cell_idx = 0
                    for col_name in display_columns_order:
                        if col_name == "chk":
                            is_marked = int(line_num) in marked_lines
                            if cells[cell_idx].content.value != is_marked:
                                cells[cell_idx].content.value = is_marked
                                try: cells[cell_idx].content.update()
                                except Exception: pass
                            cells[cell_idx].content.data = int(line_num)
                        else:
                            col_val = self._get_display_value(getattr(row_data, col_name, ''))
                            if col_name == "mensaje":
                                raw_msg = col_val
                                if len(raw_msg) > self.MAX_DISPLAY_LEN:
                                    display_msg = raw_msg[:self.MAX_DISPLAY_LEN] + "..."
                                    tooltip_msg = raw_msg[:1000]
                                else:
                                    display_msg = raw_msg
                                    tooltip_msg = None
                                msg_val, msg_spans = self._calculate_message_content(display_msg)
                                
                                msg_control = cells[cell_idx].content
                                if msg_control.value != msg_val: msg_control.value = msg_val
                                msg_control.spans = msg_spans 
                                msg_control.tooltip = tooltip_msg
                            elif col_name == "nivel":
                                cells[cell_idx].content.value = col_val
                                cells[cell_idx].content.color = self.layout._get_level_color(col_val) if self.app_state.syntax_highlighting else None
                                cells[cell_idx].content.weight = ft.FontWeight.BOLD if self.app_state.syntax_highlighting else None
                            else:
                                cells[cell_idx].content.value = col_val
                                cells[cell_idx].content.tooltip = col_val if col_val else None
                        cell_idx += 1
                else:
                    # CREAR
                    self.layout.log_table.controls.append(create_row_controls(line_num, row_data))

            # Podar excedentes
            if rows_available > rows_needed:
                del self.layout.log_table.controls[rows_needed:]

            self.update_pagination_ui()
            self.update_status_bar()
            self.layout.log_table.update()
            self.page.update()

    def refresh_context_table(self, auto_scroll=True):
        with self.controller._ui_lock:
            df = self.app_state.context_df
            if df.empty or not self.layout.context_log_table: return

            marked_lines = self.app_state.marked_lines
            selected_lines = self.app_state.selected_lines
            
            target_line = self.app_state.context_line
            
            context_line_nums = set(df['linea'].astype(int))
            all_marked = context_line_nums.issubset(marked_lines) if context_line_nums else False
            if self.layout.context_table_comp:
                self.layout.context_table_comp.header_checkbox.value = all_marked
                self.layout.context_table_comp.header_checkbox.update()
            
            # Obtener el orden de las columnas a mostrar desde LogTable
            display_columns_order = self.layout.table_comp.current_display_columns # Usar las mismas columnas que la tabla principal

            # Reconstrucción simple para el contexto (solo son 21 líneas máx)
            self.layout.context_log_table.controls = [
                self._create_context_row_controls(int(row.linea), row, display_columns_order, marked_lines, selected_lines) 
                for row in df.itertuples(index=False)
            ]
            try: self.layout.context_log_table.update()
            except Exception: pass
            
            if auto_scroll:
                async def perform_scroll():
                    target_idx = 0
                    lineas_contexto = df['linea'].astype(int).tolist()
                    if target_line in lineas_contexto:
                        target_idx = lineas_contexto.index(target_line)
                    res = self.layout.context_log_table.scroll_to(offset=target_idx * 25, duration=0)
                    if asyncio.iscoroutine(res): await res
                self.page.run_task(perform_scroll)
            self.page.update()

    def _create_context_row_controls(self, line_num, row_data, display_columns_order, marked_lines, selected_lines):
        is_marked = line_num in marked_lines
        target_line = self.app_state.context_line
        selected_color = ft.Colors.with_opacity(0.25, ft.Colors.BLUE)
        highlight_color = ft.Colors.with_opacity(0.3, ft.Colors.AMBER) # Color para la línea central

        cells = []
        is_target = line_num == target_line
        for col_name in display_columns_order:
            col_val = self._get_display_value(getattr(row_data, col_name, '')) if col_name != "chk" else ""
            cells.append(self._build_cell(col_name, col_val, line_num, is_marked=is_marked, is_target_line=is_target))
        
        row_content = ft.Row(controls=cells, spacing=5, vertical_alignment=ft.CrossAxisAlignment.CENTER)
        
        bgcolor = selected_color if line_num in selected_lines else None
        if line_num == target_line:
            bgcolor = highlight_color

        return ft.Container(
            content=row_content,
            bgcolor=bgcolor,
            on_click=self._handle_row_click,
            data=line_num,
            key=str(line_num),
            padding=ft.Padding.symmetric(horizontal=5, vertical=0),
            border=ft.Border.only(bottom=ft.BorderSide(0.5, "outlineVariant")),
            height=25
        )

    def update_pagination_ui(self):
        cp = self.app_state.current_page
        tp = self.app_state.total_pages
        self.layout.page_info.value = i18n.t("table.pagination", current=cp, total=tp)
        self.layout.btn_first.disabled = cp == 1
        self.layout.btn_prev.disabled = cp == 1
        self.layout.btn_next.disabled = cp == tp
        self.layout.btn_last.disabled = cp == tp

    def update_status_bar(self):
        msg = i18n.t("table.records", filtered=len(self.app_state.filtered_df), total=len(self.app_state.df))
        if self.app_state.search_query: msg += f" | {i18n.t('btn.search')}: '{self.app_state.search_query}'"
        self.layout.status_text.value = msg
        self.layout.status_text.update()

    def _calculate_message_content(self, text):
        if not text: return "", None
        if not self.app_state.syntax_highlighting: return text, None
        if len(text) < 150 and not any(c in text for c in "0123456789"): return text, None

        search_text = text[:self.MAX_DISPLAY_LEN]
        matches = []
        has_matches = False
        for compiled, color in self._MSG_PATTERNS:
            for m in compiled.finditer(search_text):
                has_matches = True
                start, end = m.span(1) if m.lastindex else m.span()
                matches.append((start, end, color))
        
        if not has_matches: return text, None

        matches.sort(key=lambda x: x[0])
        
        filtered_matches = []
        current_pos = 0
        for start, end, color in matches:
            if start >= current_pos:
                filtered_matches.append((start, end, color))
                current_pos = end

        spans = []
        last_idx = 0
        for start, end, color in filtered_matches:
            if start > last_idx:
                spans.append(ft.TextSpan(text[last_idx:start]))
            spans.append(ft.TextSpan(text[start:end], style=ft.TextStyle(color=color, weight=ft.FontWeight.BOLD)))
            last_idx = end
        
        if last_idx < len(text):
            spans.append(ft.TextSpan(text[last_idx:]))
            
        return None, spans

    def toggle_mark_all_on_page(self, e, is_context=False):
        is_checked = e.control.value
        if is_context:
            page_df = self.app_state.context_df
        else:
            df = self.app_state.filtered_df
            if df.empty: return
            start_idx = (self.app_state.current_page - 1) * self.app_state.page_size
            end_idx = start_idx + self.app_state.page_size
            page_df = df.iloc[start_idx:end_idx]
            
        if page_df.empty: return
        
        lines_to_modify = set(page_df['linea'].astype(int))
        
        if is_checked: self.app_state.marked_lines.update(lines_to_modify)
        else: self.app_state.marked_lines.difference_update(lines_to_modify)
        
        self.controller.refresh_table()
