import flet as ft
import pandas as pd
import logging
import time
import re
import sys
import ctypes
import numpy as np
from Model.log_parser import LogParser
from ..Librerias import i18n

# Constantes de Windows para códigos de teclas virtuales
VK_SHIFT = 0x10
VK_CONTROL = 0x11

logger = logging.getLogger(__name__)

class SelectionManager:
    """
    Gestiona la selección visual de filas y la copia al portapapeles.
    """

    def __init__(self, page, app_state, layout, manager):
        self.page = page
        self.app_state = app_state
        self.layout = layout
        self.manager = manager
        
        self.mode_multi = False
        self.mode_range = False
        self._last_click_key = (-1, 0.0, False)
        
        self.ctrl_pressed = False
        self.shift_pressed = False
        
        self.page.on_keyboard_event = self._on_keyboard_event

    def _on_keyboard_event(self, e: ft.KeyboardEvent):
        # Mantiene el estado de modificadores para uso como fallback en non-Windows.
        # En Windows, on_row_click usa GetAsyncKeyState para mayor fiabilidad,
        # ya que los eventos de teclado de Flet no detectan la tecla suelta.
        self.ctrl_pressed = e.ctrl
        self.shift_pressed = e.shift

        if e.key == "C" and e.ctrl and not e.shift and not e.alt:
            self.page.run_task(self.copy_selected_lines)
        elif e.key == "A" and e.ctrl and not e.shift and not e.alt:
            self.select_all_on_page()
        elif e.key == "F" and e.ctrl and not e.shift and not e.alt:
            self.manager.open_search_selection_dialog()

    def set_mode(self, multi: bool, rango: bool):
        self.mode_multi = multi
        self.mode_range = rango
        
        self.layout.btn_mode_multi.icon_color = ft.Colors.BLUE_400 if multi else ft.Colors.WHITE
        self.layout.btn_mode_range.icon_color = ft.Colors.BLUE_400 if rango else ft.Colors.WHITE
        
        self.layout.btn_mode_multi.bgcolor = ft.Colors.with_opacity(0.2, ft.Colors.BLUE) if multi else None
        self.layout.btn_mode_range.bgcolor = ft.Colors.with_opacity(0.2, ft.Colors.BLUE) if rango else None

        self.layout.btn_mode_multi.update()
        self.layout.btn_mode_range.update()

    def toggle_mode_multi(self, e=None):
        new_val = not self.mode_multi
        self.set_mode(multi=new_val, rango=False)

    def toggle_mode_range(self, e=None):
        new_val = not self.mode_range
        self.set_mode(multi=False, rango=new_val)

    def on_row_click(self, e, line_num: int):
        now = time.monotonic()
        is_selected_event = e.control.selected if hasattr(e.control, 'selected') else True
        
        last_line, last_ts, last_was_selected = self._last_click_key
        
        if line_num == last_line and (now - last_ts) < 0.05:
            if last_was_selected and not is_selected_event:
                return

        self._last_click_key = (line_num, now, is_selected_event)
        df = self.app_state.filtered_df

        is_ctrl = (ctypes.windll.user32.GetAsyncKeyState(VK_CONTROL) & 0x8000) != 0 \
            if sys.platform == "win32" else self.ctrl_pressed
        is_shift = (ctypes.windll.user32.GetAsyncKeyState(VK_SHIFT) & 0x8000) != 0 \
            if sys.platform == "win32" else self.shift_pressed

        is_multi = is_ctrl or self.mode_multi
        is_range = is_shift or self.mode_range

        if is_multi:
            if line_num in self.app_state.selected_lines:
                self.app_state.selected_lines.discard(line_num)
            else:
                self.app_state.selected_lines.add(line_num)
            self.app_state.last_selected_line = line_num

        elif is_range:
            anchor = self.app_state.last_selected_line
            if anchor is not None:
                lineas_arr = df['linea'].values.astype(int)
                anchor_pos = np.where(lineas_arr == anchor)[0]
                current_pos = np.where(lineas_arr == line_num)[0]
                if anchor_pos.size > 0 and current_pos.size > 0:
                    lo = min(anchor_pos[0], current_pos[0])
                    hi = max(anchor_pos[0], current_pos[0])
                    self.app_state.selected_lines = set(lineas_arr[lo:hi + 1].tolist())
                else:
                    self.app_state.selected_lines = {line_num}
                    self.app_state.last_selected_line = line_num
            else:
                self.app_state.selected_lines = {line_num}
                self.app_state.last_selected_line = line_num
        else:
            self.app_state.selected_lines = {line_num}
            self.app_state.last_selected_line = line_num

        self.manager.refresh_selection_visuals()

    async def copy_selected_lines(self, e=None):
        if not self.app_state.selected_lines: return

        df = self.app_state.filtered_df
        selected_rows = df[df['linea'].astype(int).isin(self.app_state.selected_lines)]
        n = len(selected_rows)

        if n > 10000: self._show_snack(i18n.t("msg.selecting"))

        text_to_copy = LogParser.format_dataframe_to_text(selected_rows)

        try:
            import pyperclip
            pyperclip.copy(text_to_copy)
        except Exception:
            await ft.Clipboard().set(text_to_copy)
            
        self._show_snack(i18n.t("msg.copied", n=n, s='s' if n != 1 else ''))

    def select_all_on_page(self, e=None):
        df = self.app_state.filtered_df
        if df.empty: return

        start_idx = (self.app_state.current_page - 1) * self.app_state.page_size
        end_idx = start_idx + self.app_state.page_size
        page_df = df.iloc[start_idx:end_idx]
        
        page_lines = set(page_df['linea'].astype(int))
        self.app_state.selected_lines.update(page_lines)
        
        if not page_df.empty:
            self.app_state.last_selected_line = int(page_df.iloc[-1]['linea'])

        self.manager.refresh_selection_visuals()

    async def select_by_search(self, query: str):
        df = self.app_state.filtered_df
        if df.empty or not query: return

        self._add_to_history(query)

        # 1. Identificar columnas presentes
        potential_search_cols = ['nivel', 'evento', 'proceso', 'mensaje', 'notas', 'pid']
        search_cols = [col for col in potential_search_cols if col in df.columns]

        if not search_cols:
            self._show_snack(i18n.t("msg.no_search_cols"))
            return

        # 2. Crear una serie de búsqueda limpia para evitar errores de tipo float/Categorical
        # Convertimos cada celda a str individualmente para asegurar compatibilidad total con ' '.join
        def row_to_str(row):
            return ' '.join(str(val) if pd.notna(val) else "" for val in row)

        search_source = df[search_cols].apply(row_to_str, axis=1)

        if self.app_state.selection_use_regex:
            try:
                mask = search_source.str.contains(query, case=False, regex=True, na=False)
            except Exception:
                self._show_snack(i18n.t("msg.regex_invalid"))
                return
        else:
            query_lower = query.lower()
            terms = query_lower.split()
            search_mask = pd.Series(self.app_state.selection_search_mode == "AND", index=df.index)

            for term in terms:
                term_mask = search_source.str.contains(term, case=False, regex=False, na=False)
                if self.app_state.selection_search_mode == "AND":
                    search_mask &= term_mask
                else:
                    search_mask |= term_mask
            mask = search_mask

        matched_lines = set(df[mask]['linea'].astype(int))
        self.app_state.selected_lines.clear()

        if matched_lines:
            self.app_state.selected_lines.update(matched_lines)
            self._show_snack(i18n.t("msg.selected", n=len(matched_lines)))
            
            first_line = int(df[mask].iloc[0]['linea'])
            await self.manager._jump_to_line(first_line)
        else:
            self._show_snack(i18n.t("msg.no_matches", query=query))
            
        self.manager.refresh_selection_visuals()

    def mark_selected_lines(self, mark: bool):
        if mark:
            self.app_state.marked_lines.update(self.app_state.selected_lines)
        else:
            self.app_state.marked_lines.difference_update(self.app_state.selected_lines)
        
        n = len(self.app_state.selected_lines)
        msg_key = "msg.marked" if mark else "msg.unmarked"
        self._show_snack(i18n.t(msg_key, n=n, s='s' if n != 1 else ''))
        
        if self.app_state.show_only_marked:
            self.manager.apply_filters()
        else:
            self.manager.refresh_table()

    def _add_to_history(self, query: str):
        if not query: return
        history = self.manager.configuracion.app.historial_busqueda
        if query in history: history.remove(query)
        history.insert(0, query)
        self.manager.configuracion.app.historial_busqueda = history[:20]
        self.manager.config_manager.guardar(self.manager.configuracion)

    def _show_snack(self, message: str):
        snack = ft.SnackBar(content=ft.Text(message), open=True)
        self.page.overlay[:] = [c for c in self.page.overlay if not isinstance(c, ft.SnackBar)]
        self.page.overlay.append(snack)
        self.page.snack_bar = snack
        self.page.update()

    async def goto_line(self, e):
        val = self.layout.goto_line_field.value.strip()
        if not val: return
        try:
            line_num = int(val)
            df = self.app_state.filtered_df
            if line_num in df['linea'].astype(int).values:
                await self.jump_to_line(line_num)
            else:
                self._show_snack(i18n.t("msg.line_not_found", n=line_num))
        except (ValueError, TypeError): pass
        finally:
            self.layout.goto_line_field.value = ""
            self.layout.goto_line_field.update()

    async def jump_to_line(self, line_num: int):
        df = self.app_state.filtered_df
        lineas = df['linea'].astype(int).tolist()
        try:
            pos = lineas.index(line_num)
            new_page = (pos // self.app_state.page_size) + 1
            self.app_state.current_page = new_page
            self.app_state.last_selected_line = line_num
            self.manager.refresh_table()
            import asyncio
            await asyncio.sleep(0.1)
            pos_in_page = pos % self.app_state.page_size
            if self.layout.log_table:
                res = self.layout.log_table.scroll_to(offset=pos_in_page * 25, duration=300)
                if asyncio.iscoroutine(res): await res
        except (ValueError, Exception): pass

    async def navigate_marked(self, direction: int):
        df = self.app_state.filtered_df
        target_set = self.app_state.selected_lines
        if df.empty or not target_set: return
        lineas_df = df['linea'].astype(int).tolist()
        current_line = self.app_state.last_selected_line
        if current_line is None:
            idx = (self.app_state.current_page - 1) * self.app_state.page_size
            current_line = lineas_df[idx] if idx < len(lineas_df) else lineas_df[0]
        try: curr_pos = lineas_df.index(current_line)
        except ValueError: curr_pos = 0
        target_line = None
        if direction == 1:
            for line in lineas_df[curr_pos + 1:]:
                if line in target_set:
                    target_line = line
                    break
            if target_line is None:
                for line in lineas_df:
                    if line in target_set:
                        target_line = line
                        break
        else:
            for line in reversed(lineas_df[:curr_pos]):
                if line in target_set:
                    target_line = line
                    break
            if target_line is None:
                for line in reversed(lineas_df):
                    if line in target_set:
                        target_line = line
                        break
        if target_line is not None: await self.jump_to_line(target_line)
