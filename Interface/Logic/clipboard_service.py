# Interface/Logic/clipboard_service.py
"""
Responsabilidad única: acceso al portapapeles y búsqueda de selección por texto.

Gestiona la copia de líneas al portapapeles y la búsqueda de líneas por texto (Ctrl+F),
incluyendo el historial de búsqueda de selección.
No gestiona la selección visual de filas (eso es responsabilidad de SelectionManager).
"""
import flet as ft
import pandas as pd
import logging
import re
from typing import TYPE_CHECKING
from Model.log_parser import LogParser
from ..Core import i18n

if TYPE_CHECKING:
    from ..Manager import Manager

logger = logging.getLogger(__name__)


class ClipboardService:
    """
    Servicio de portapapeles y búsqueda de selección.

    Responsabilidades:
    - Copiar líneas seleccionadas al portapapeles en formato texto.
    - Buscar y seleccionar líneas que coincidan con un texto/regex (Ctrl+F).
    - Gestionar el historial de búsquedas de selección.
    """

    def __init__(self, manager: 'Manager'):
        self.mgr = manager
        self.app_state = manager.app_state
        self.page = manager.page

    async def copy_selected_lines(self, e=None):
        """Copia las líneas seleccionadas al portapapeles en formato texto."""
        if not self.app_state.selected_lines:
            return

        df = self.app_state.filtered_df
        selected_rows = df[df['linea'].astype(int).isin(self.app_state.selected_lines)]
        n = len(selected_rows)

        if n > 10000:
            self._show_snack(i18n.t("msg.selecting"))

        text_to_copy = LogParser.format_dataframe_to_text(selected_rows)

        try:
            import pyperclip
            pyperclip.copy(text_to_copy)
        except Exception:
            await ft.Clipboard().set(text_to_copy)

        self._show_snack(i18n.t("msg.copied", n=n, s='s' if n != 1 else ''))

    async def select_by_search(self, query: str):
        """
        Selecciona todas las líneas del DataFrame filtrado que coincidan con query.
        Soporta modos AND / OR y Regex.
        """
        df = self.app_state.filtered_df
        if df.empty or not query:
            return

        self.add_to_history(query)

        search_cols = [col for col in df.columns if col not in ['linea', 'timestamp']]
        if not search_cols:
            self._show_snack(i18n.t("msg.no_search_cols"))
            return

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
            await self.mgr._jump_to_line(first_line)
        else:
            self._show_snack(i18n.t("msg.no_matches", query=query))

        self.mgr.refresh_selection_visuals()

    # ── Historial ────────────────────────────────────────────────────────────
    def add_to_history(self, query: str) -> None:
        """Añade una consulta al historial de búsqueda de selección (máx. 20 entradas)."""
        if not query:
            return
        history = self.mgr.configuracion.app.historial_busqueda
        if query in history:
            history.remove(query)
        history.insert(0, query)
        self.mgr.configuracion.app.historial_busqueda = history[:20]
        self.mgr.config_manager.guardar(self.mgr.configuracion)

    # ── Snack bar ────────────────────────────────────────────────────────────
    def _show_snack(self, message: str):
        snack = ft.SnackBar(content=ft.Text(message), open=True)
        self.page.overlay[:] = [c for c in self.page.overlay if not isinstance(c, ft.SnackBar)]
        self.page.overlay.append(snack)
        self.page.snack_bar = snack
        self.page.update()
