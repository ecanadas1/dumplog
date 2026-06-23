import pandas as pd
import logging
import threading
from typing import Dict, Any
import re
import datetime

logger = logging.getLogger(__name__)
_state_lock = threading.Lock()

class FilterManager:
    """
    Aplica los filtros definidos por el usuario al DataFrame completo.
    Soporta filtros dinámicos basados en cualquier columna del DataFrame.
    """

    def __init__(self, app_state):
        self.app_state = app_state

    def apply_filters(self, exclude_clear: bool):
        """
        Calcula el DataFrame filtrado y lo guarda en el estado global.
        """
        logger.info("Aplicando filtros...")
        df = self.app_state.df
        if df.empty:
            self.app_state.filtered_df = df
            return

        mask = pd.Series(True, index=df.index)

        logger.debug(f"DF columns: {df.columns.tolist()}")
        logger.debug(f"Selected filters: {self.app_state.selected_filters}")

        # 1. Filtro de fecha/hora
        start_dt = self.app_state.start_date
        if start_dt:
            if hasattr(start_dt, "tzinfo") and start_dt.tzinfo is not None:
                start_dt = start_dt.astimezone(None)
            
            y, m, d = start_dt.year, start_dt.month, start_dt.day
            if self.app_state.start_time:
                t = self.app_state.start_time
                start_ts = pd.Timestamp(year=y, month=m, day=d, hour=t.hour, minute=t.minute, second=t.second)
            else:
                start_ts = pd.Timestamp(year=y, month=m, day=d)
            mask &= (df['timestamp'] >= start_ts)

        end_dt = self.app_state.end_date
        if end_dt:
            if hasattr(end_dt, "tzinfo") and end_dt.tzinfo is not None:
                end_dt = end_dt.astimezone(None)
                
            y, m, d = end_dt.year, end_dt.month, end_dt.day
            if self.app_state.end_time:
                t = self.app_state.end_time
                end_ts = pd.Timestamp(year=y, month=m, day=d, hour=t.hour, minute=t.minute, second=t.second)
            else:
                end_ts = pd.Timestamp(year=y, month=m, day=d, hour=23, minute=59, second=59, microsecond=999999)
            mask &= (df['timestamp'] <= end_ts)

        # 2. Filtro de nivel 'clear' (opcional)
        if exclude_clear and 'nivel' in df.columns:
            mask &= (df['nivel'] != 'clear')

        # 3. FILTROS DINÁMICOS (Iterar sobre todas las selecciones, incluyendo las "estándar")
        for col_name, selected_values in self.app_state.selected_filters.items():
            logger.debug(f"Checking filter for column: {col_name}, selected values: {selected_values}")
            if selected_values: # Solo aplicar si hay valores seleccionados para esta columna
                if col_name in df.columns: # Y si la columna existe en el DataFrame actual
                    logger.debug(f"Applying filter for {col_name}")
                    mask &= (df[col_name].isin(selected_values))
                else:
                    logger.warning(f"Filter for column '{col_name}' has selected values but column does not exist in DataFrame. Skipping orphan filter.")
                    # Si la columna no existe (p.ej. cambio de formato), ignoramos
                    # este filtro huérfano en lugar de vaciar toda la tabla.

        # 4. Filtro de líneas marcadas
        if self.app_state.show_only_marked:
            marked = [int(x) for x in self.app_state.marked_lines]
            mask &= (df['linea'].astype(int).isin(marked))

        # 5. Filtro de búsqueda libre (todas las columnas de texto relevantes)
        search_query = self.app_state.search_query
        if search_query:
            # Calcular search_source directamente desde el DF para evitar
            # inconsistencias del caché cuando el DataFrame cambia de tamaño.
            search_cols = [col for col in df.columns if col not in ['linea', 'timestamp']]
            if search_cols:
                search_source = df[search_cols].astype(str).agg(' '.join, axis=1).str.lower()
            else:
                search_source = pd.Series("", index=df.index)

            if self.app_state.use_regex:
                try:
                    mask &= search_source.str.contains(search_query, case=False, regex=True, na=False)
                    self.app_state.regex_error = False
                except re.error:
                    logger.warning(f"Regex inválida: {search_query}")
                    self.app_state.regex_error = True
            else:
                search_query = search_query.lower()
                terms = search_query.split()
                search_mask = pd.Series(self.app_state.search_mode == "AND", index=df.index)

                for term in terms:
                    term_mask = search_source.str.contains(term, case=False, regex=False, na=False)
                    if self.app_state.search_mode == "AND":
                        search_mask &= term_mask
                    else:
                        search_mask |= term_mask
                mask &= search_mask

        logger.info("Filtros aplicados")

        new_filtered = df[mask]
        with _state_lock:
            self.app_state.filtered_df = new_filtered

    def calculate_statistics(self) -> Dict[str, Any]:
        """Calcula las estadísticas de los logs basándose en el estado actual."""
        df_all = self.app_state.df
        df_filtered = self.app_state.filtered_df
        
        if df_all.empty:
            return {'total': 0, 'filtered': 0, 'by_level': {}}
            
        by_level = {}
        if 'nivel' in df_filtered.columns:
            by_level = df_filtered['nivel'].value_counts().to_dict()
        
        stats = {
            'total': len(df_all),
            'filtered': len(df_filtered),
            'by_level': by_level
        }
        self.app_state.stats = stats
        return stats
