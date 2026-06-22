import asyncio
import logging
import flet as ft
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..Manager import Manager

logger = logging.getLogger(__name__)

class UIActionManager:
    """
    Gestiona los eventos y acciones de la interfaz de usuario de forma dinámica.
    """

    def __init__(self, manager: 'Manager'):
        self.mgr = manager
        self.app_state = manager.app_state
        self.layout = manager.layout

    # --- Pagination ---
    def change_page(self, e, delta=0, first=False, last=False):
        """Cambia la página actual de la tabla."""
        if first: self.app_state.current_page = 1
        elif last: self.app_state.current_page = self.app_state.total_pages
        else: self.app_state.current_page = max(1, min(self.app_state.total_pages, self.app_state.current_page + delta))
        self.mgr.refresh_table()

    def on_page_size_change(self, e):
        """Maneja el cambio de tamaño de página."""
        raw = e.data if e.data else (e.control.value if hasattr(e.control, 'value') else None)
        if not raw: return
        self.app_state.page_size = int(raw)
        self.app_state.current_page = 1
        self.mgr.refresh_table()

    # --- Sidebar Filters ---
    def on_dynamic_filter_change(self, e):
        """Maneja el cambio en cualquier checkbox de filtro dinámico."""
        col_name = e.control.data  # Almacenamos el nombre de la columna en 'data'
        val = e.control.label
        
        if col_name not in self.app_state.selected_filters:
            self.app_state.selected_filters[col_name] = set()
            
        if e.control.value:
            self.app_state.selected_filters[col_name].add(val)
        else:
            self.app_state.selected_filters[col_name].discard(val)
            
        self.trigger_debounced_filter(f"filter_change_{col_name}")

    def on_dynamic_filter_search_change(self, e):
        """Maneja la búsqueda interna en los paneles de filtros dinámicos."""
        val, col_name = e.control.value, e.control.data
        self.app_state.internal_search_queries[col_name] = val
        self.mgr._current_filter_field = col_name
        
        if self.mgr._filter_controls_debounce_task and not self.mgr._filter_controls_debounce_task.done():
            self.mgr._filter_controls_debounce_task.cancel()
        self.mgr._filter_controls_debounce_task = asyncio.create_task(self.mgr._debounce_update_filter_controls())

    # --- Compatibilidad (mapeados a los nuevos métodos genéricos) ---
    def on_level_change(self, e): e.control.data = "nivel"; self.on_dynamic_filter_change(e)
    def on_event_change(self, e): e.control.data = "evento"; self.on_dynamic_filter_change(e)
    def on_process_change(self, e): e.control.data = "proceso"; self.on_dynamic_filter_change(e)
    def on_note_change(self, e): e.control.data = "notas"; self.on_dynamic_filter_change(e)

    def on_exclude_clear_change(self, e):
        """Maneja el cambio en el filtro de exclusión de niveles 'clear'."""
        self.trigger_debounced_filter("exclude")
    
    def on_only_marked_change(self, e):
        """Maneja el cambio en el filtro de mostrar solo líneas marcadas."""
        self.app_state.show_only_marked = e.control.value
        self.trigger_debounced_filter("marked")

    def on_search_mode_change(self, e):
        """Cambia entre modo AND y OR."""
        self.app_state.search_mode = e.control.value
        self.trigger_debounced_filter("mode")

    def on_filter_search_change(self, e):
        """Mapeo de compatibilidad para búsquedas internas."""
        self.on_dynamic_filter_search_change(e)

    # --- Date/Time Filters ---
    def on_date_change_start(self, e):
        if e.control.value:
            self.app_state.start_date = e.control.value
            self.mgr._update_date_labels_ui()
            self.trigger_debounced_filter("date_start")

    def on_date_change_end(self, e):
        if e.control.value:
            self.app_state.end_date = e.control.value
            self.mgr._update_date_labels_ui()
            self.trigger_debounced_filter("date_end")

    def on_time_change_start(self, e):
        if e.control.value:
            self.app_state.start_time = e.control.value
            self.mgr._update_date_labels_ui()
            self.trigger_debounced_filter("time_start")

    def on_time_change_end(self, e):
        if e.control.value:
            self.app_state.end_time = e.control.value
            self.mgr._update_date_labels_ui()
            self.trigger_debounced_filter("time_end")

    # --- Search Bar ---
    def on_search_change(self, e):
        self.app_state.search_query = e.control.value
        self.trigger_debounced_filter("search")

    def on_regex_change(self, e):
        """Activa/Desactiva el uso de Regex en la búsqueda y actualiza la visibilidad del radio group."""
        self.app_state.use_regex = e.control.value
        self.layout.search_mode_radio.visible = not e.control.value # <-- Aquí se actualiza la visibilidad
        self.layout.search_mode_radio.update() # Forzar la actualización de la UI
        self.trigger_debounced_filter("regex")

    def on_clear_filters(self, e):
        self.mgr.clear_filters()

    def on_search_submit(self, e):
        query = self.layout.search_field.value.strip()
        self.app_state.search_query = query
        self.mgr.selection_mgr._add_to_history(query)
        self.mgr.refresh_history_ui()
        self.mgr.apply_filters()

    def _on_sidebar_history_click(self, e):
        query = e.control.data
        self.layout.search_field.value = query
        self.app_state.search_query = query
        self.mgr.apply_filters()
        self.layout.search_field.update()

    # --- Debounce Logic ---
    def trigger_debounced_filter(self, reason: str):
        """Activa el filtrado con debounce."""
        if self.layout and self.layout.search_loading:
            if not self.layout.search_loading.visible:
                self.layout.search_loading.visible = True
                self.layout.search_loading.update()
        
        if self.mgr._debounce_task and not self.mgr._debounce_task.done():
            self.mgr._debounce_task.cancel()
        self.mgr._debounce_task = asyncio.create_task(self._debounce_refresh())

    async def _debounce_refresh(self):
        try:
            await asyncio.sleep(0.4)
            self.mgr.apply_filters()
        except asyncio.CancelledError: pass
