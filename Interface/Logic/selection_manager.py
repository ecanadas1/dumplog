# Interface/Logic/selection_manager.py
"""
Responsabilidad única: selección visual de filas en la tabla de logs.

Gestiona los modos Normal / Multi / Rango, la detección de modificadores de teclado
(Ctrl, Shift) y la selección de todas las filas de la página.

La navegación está en NavigationManager.
El portapapeles y el historial están en ClipboardService.
"""
import flet as ft
import numpy as np
import logging
import time
import sys
import ctypes
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..Manager import Manager

# Constantes de Windows para códigos de teclas virtuales
VK_SHIFT = 0x10
VK_CONTROL = 0x11

logger = logging.getLogger(__name__)


class SelectionManager:
    """
    Gestiona la selección visual de filas.

    Responsabilidades:
    - Modos de selección: Normal, Multi (Ctrl+Clic) y Rango (Shift+Clic).
    - Selección de toda la página (Ctrl+A).
    - Marcado y desmarcado de filas seleccionadas.
    - Registro de eventos de teclado (Ctrl/Shift como modificadores).
    """

    def __init__(self, page: ft.Page, app_state, layout, manager: 'Manager'):
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

    # ── Eventos de teclado ───────────────────────────────────────────────────
    def _on_keyboard_event(self, e: ft.KeyboardEvent):
        """Registra modificadores y despacha atajos de teclado globales."""
        self.ctrl_pressed = e.ctrl
        self.shift_pressed = e.shift

        if e.key == "C" and e.ctrl and not e.shift and not e.alt:
            self.page.run_task(self.manager.copy_selected_lines)
        elif e.key == "A" and e.ctrl and not e.shift and not e.alt:
            self.select_all_on_page()
        elif e.key == "F" and e.ctrl and not e.shift and not e.alt:
            self.manager.open_search_selection_dialog()

    # ── Modos de selección ───────────────────────────────────────────────────
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
        self.set_mode(multi=not self.mode_multi, rango=False)

    def toggle_mode_range(self, e=None):
        self.set_mode(multi=False, rango=not self.mode_range)

    # ── Click en fila ────────────────────────────────────────────────────────
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

    # ── Selección de página ──────────────────────────────────────────────────
    def select_all_on_page(self, e=None):
        """Selecciona todas las líneas de la página visible."""
        df = self.app_state.filtered_df
        if df.empty:
            return
        start_idx = (self.app_state.current_page - 1) * self.app_state.page_size
        end_idx = start_idx + self.app_state.page_size
        page_df = df.iloc[start_idx:end_idx]
        page_lines = set(page_df['linea'].astype(int))
        self.app_state.selected_lines.update(page_lines)
        if not page_df.empty:
            self.app_state.last_selected_line = int(page_df.iloc[-1]['linea'])
        self.manager.refresh_selection_visuals()

    # ── Marcado ──────────────────────────────────────────────────────────────
    def mark_selected_lines(self, mark: bool):
        if mark:
            self.app_state.marked_lines.update(self.app_state.selected_lines)
        else:
            self.app_state.marked_lines.difference_update(self.app_state.selected_lines)

        n = len(self.app_state.selected_lines)
        from ..Core import i18n
        msg_key = "msg.marked" if mark else "msg.unmarked"
        self._show_snack(i18n.t(msg_key, n=n, s='s' if n != 1 else ''))

        if self.app_state.show_only_marked:
            self.manager.apply_filters()
        else:
            self.manager.refresh_table()

    # ── Snack bar ────────────────────────────────────────────────────────────
    def _show_snack(self, message: str):
        snack = ft.SnackBar(content=ft.Text(message), open=True)
        self.page.overlay[:] = [c for c in self.page.overlay if not isinstance(c, ft.SnackBar)]
        self.page.overlay.append(snack)
        self.page.snack_bar = snack
        self.page.update()

    # ── Compatibilidad con código existente que llama _add_to_history ────────
    def _add_to_history(self, query: str):
        """Delegado a ClipboardService para mantener compatibilidad."""
        self.manager.clipboard_svc.add_to_history(query)
