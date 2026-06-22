from dataclasses import dataclass, field
from datetime import datetime, time
from typing import List, Set, Optional, Dict, Any
import pandas as pd
from Model.log_entry import LogEntry
from Model.formats.base_format import BaseFormat

@dataclass
class AppState:
    """
    Gestiona el estado global de la aplicación de forma centralizada y tipada.
    Soporta columnas y filtros dinámicos.
    """
    active_format: Optional[BaseFormat] = None
    auto_detect_format: bool = True

    entries: List[LogEntry] = field(default_factory=list)
    df: pd.DataFrame = field(default_factory=pd.DataFrame)
    filtered_df: pd.DataFrame = field(default_factory=pd.DataFrame)
    search_source: pd.Series = field(default_factory=lambda: pd.Series(dtype='str'))
    
    # Valores únicos por columna (para los checkboxes de la UI)
    unique_values: Dict[str, List[str]] = field(default_factory=dict)
    
    # Filtros temporales
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    
    # Filtros de selección dinámicos
    selected_filters: Dict[str, Set[str]] = field(default_factory=dict)
    
    # Búsqueda y Paginación
    search_query: str = ""
    search_mode: str = "AND"
    use_regex: bool = False  

    # Búsqueda de Selección (Ctrl+F)
    selection_search_mode: str = "AND"
    selection_use_regex: bool = False

    # Búsquedas internas de los paneles de filtro (UI)
    internal_search_queries: Dict[str, str] = field(default_factory=dict)

    current_page: int = 1
    page_size: int = 50
    total_pages: int = 1
    stats: Dict[str, Any] = field(default_factory=dict)
    regex_error: bool = False

    # Configuración de visualización
    syntax_highlighting: bool = True

    # Fichero cargado
    last_file_path: Optional[str] = None
    last_file_name: Optional[str] = None

    # Marcación de líneas (checkboxes)
    marked_lines: Set[int] = field(default_factory=set)
    show_only_marked: bool = False

    # Selección visual de filas (resaltado con click/shift/ctrl)
    selected_lines: Set[int] = field(default_factory=set)
    last_selected_line: Optional[int] = None

    # Context View
    context_mode: bool = False
    context_line: Optional[int] = None
    context_df: pd.DataFrame = field(default_factory=pd.DataFrame)
    context_range: int = 10

    # Propiedades de compatibilidad para evitar romper todo de golpe
    @property
    def unique_levels(self): return self.unique_values.get("nivel", [])
    @property
    def unique_events(self): return self.unique_values.get("evento", [])
    @property
    def unique_processes(self): return self.unique_values.get("proceso", [])
    @property
    def unique_notes(self): return self.unique_values.get("notas", [])

    @property
    def selected_levels(self): return self.selected_filters.get("nivel", set())
    @property
    def selected_events(self): return self.selected_filters.get("evento", set())
    @property
    def selected_processes(self): return self.selected_filters.get("proceso", set())
    @property
    def selected_notes(self): return self.selected_filters.get("notas", set())

    def reset_filters(self):
        """Reinicia los filtros de selección y búsqueda."""
        self.current_page = 1
        self.search_query = ""
        self.internal_search_queries.clear()
        self.selected_filters.clear()
        self.use_regex = False
        self.show_only_marked = False
        self.selected_lines.clear()
        self.last_selected_line = None
        self.filtered_df = self.df
