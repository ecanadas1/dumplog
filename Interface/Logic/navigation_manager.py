# Interface/Logic/navigation_manager.py
"""
Responsabilidad única: navegación dentro de la tabla de logs.

Gestiona los saltos a líneas concretas y la navegación entre líneas seleccionadas.
No realiza ninguna selección visual ni accede al portapapeles.
"""
import asyncio
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..Manager import Manager

logger = logging.getLogger(__name__)


class NavigationManager:
    """
    Gestiona la navegación de páginas y saltos de línea en la tabla de logs.

    Responsabilidades:
    - Ir a una línea específica introducida por el usuario.
    - Saltar programáticamente a una línea y centrar el scroll.
    - Navegar entre líneas seleccionadas (anterior / siguiente).
    """

    def __init__(self, manager: 'Manager'):
        self.mgr = manager
        self.app_state = manager.app_state
        self.layout = manager.layout

    async def goto_line(self, e):
        """Salta a la línea indicada en el campo goto_line_field."""
        val = self.layout.goto_line_field.value.strip()
        if not val:
            return
        try:
            line_num = int(val)
            df = self.app_state.filtered_df
            if line_num in df['linea'].astype(int).values:
                await self.jump_to_line(line_num)
            else:
                from ..Core import i18n
                self.mgr.selection_mgr._show_snack(i18n.t("msg.line_not_found", n=line_num))
        except (ValueError, TypeError):
            pass
        finally:
            self.layout.goto_line_field.value = ""
            self.layout.goto_line_field.update()

    async def jump_to_line(self, line_num: int):
        """
        Cambia a la página que contiene la línea dada y hace scroll hasta ella.
        """
        df = self.app_state.filtered_df
        lineas = df['linea'].astype(int).tolist()
        try:
            pos = lineas.index(line_num)
            new_page = (pos // self.app_state.page_size) + 1
            self.app_state.current_page = new_page
            self.app_state.last_selected_line = line_num
            self.mgr.refresh_table()
            await asyncio.sleep(0.1)
            pos_in_page = pos % self.app_state.page_size
            if self.layout.log_table:
                res = self.layout.log_table.scroll_to(offset=pos_in_page * 25, duration=300)
                if asyncio.iscoroutine(res):
                    await res
        except (ValueError, Exception):
            pass

    async def navigate_marked(self, direction: int):
        """
        Navega al elemento seleccionado anterior (-1) o siguiente (+1).
        """
        df = self.app_state.filtered_df
        target_set = self.app_state.selected_lines
        if df.empty or not target_set:
            return

        lineas_df = df['linea'].astype(int).tolist()
        current_line = self.app_state.last_selected_line

        if current_line is None:
            idx = (self.app_state.current_page - 1) * self.app_state.page_size
            current_line = lineas_df[idx] if idx < len(lineas_df) else lineas_df[0]

        try:
            curr_pos = lineas_df.index(current_line)
        except ValueError:
            curr_pos = 0

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

        if target_line is not None:
            await self.jump_to_line(target_line)
