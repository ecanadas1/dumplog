# Interface/Logic/data_service.py
"""
Responsabilidad única: cargar datos de log desde el sistema de ficheros al AppState.

No conoce ningún control Flet. No toca la UI. No abre diálogos.
Es una capa de servicio pura: entrada (ruta de fichero) → salida (AppState poblado).
"""
import asyncio
import os
import gc
import logging
import pandas as pd
from pathlib import Path
from typing import TYPE_CHECKING
from Model.log_parser import LogParser

if TYPE_CHECKING:
    from ..state import AppState

logger = logging.getLogger(__name__)


class DataService:
    """
    Servicio de datos de log.

    Responsabilidades:
    - Detectar el formato del fichero.
    - Parsear el fichero a DataFrame y actualizar AppState.
    - Guardar y cargar las marcas persistentes (.marks).
    """

    def __init__(self, app_state: 'AppState'):
        self.app_state = app_state

    async def load_file(self, file_path: str, file_name: str) -> bool:
        """
        Parsea el fichero e inicializa el AppState con los datos resultantes.

        Returns:
            bool: True si la carga fue exitosa, False en caso de error.
        """
        loop = asyncio.get_running_loop()

        # ── Paso 0: guardar marcas + liberar DataFrames anteriores en un thread ──
        # Se hace todo junto para evitar que el GC del DataFrame viejo (potencialmente
        # cientos de MB de numpy arrays) bloquee el event-loop de Flet durante decenas
        # de segundos cuando el usuario abre un segundo fichero grande.
        old_df          = self.app_state.df
        old_filtered_df = self.app_state.filtered_df
        old_search      = self.app_state.search_source

        # Sustituir por objetos vacíos ANTES de lanzar el executor: así el hilo
        # puede liberar las referencias sin race-conditions con el event-loop.
        self.app_state.df           = pd.DataFrame()
        self.app_state.filtered_df  = pd.DataFrame()
        self.app_state.search_source = pd.Series(dtype='str')

        def _save_and_free():
            self.save_marks()           # I/O en thread, no bloquea UI
            # Dejar que el GC recoja los DataFrames viejos fuera del event-loop
            nonlocal old_df, old_filtered_df, old_search
            del old_df, old_filtered_df, old_search
            gc.collect()

        try:
            await loop.run_in_executor(None, _save_and_free)
        except Exception as ex:
            logger.warning(f"Error en save/free: {ex}")

        try:
            # ── Paso 1: Auto-detección de formato ─────────────────────────────
            if self.app_state.auto_detect_format:
                detected = await loop.run_in_executor(
                    None, lambda: LogParser.detect_format(file_path)
                )
                if detected:
                    self.app_state.active_format = detected

            formato = self.app_state.active_format
            if formato is None:
                from Model.formats.rtp_osv import RtpOsvFormat
                formato = RtpOsvFormat()
                self.app_state.active_format = formato

            # ── Paso 2: Parseo directo a DataFrame ────────────────────────────
            df = await loop.run_in_executor(
                None,
                lambda: LogParser(formato).parse_file_to_dataframe(file_path)
            )

            self.app_state.df           = df
            self.app_state.filtered_df  = df
            self.app_state.last_file_path  = file_path
            self.app_state.last_file_name  = file_name

            self.app_state.marked_lines.clear()
            self.load_marks(file_path)

            if not df.empty:
                # ── Paso 3: valores únicos + search_source en UN SOLO executor ──
                # Así evitamos múltiples round-trips await/executor para DataFrames
                # con pocas columnas de filtro.
                std_excluded = {'linea', 'timestamp', 'mensaje'}
                filter_cols  = [c for c in df.columns if c not in std_excluded]

                def _compute_meta():
                    unique = {}
                    for col in filter_cols:
                        series = df[col]
                        # Las columnas ya vienen como 'category' desde el parser
                        vals = (series.cat.categories.tolist()
                                if series.dtype.name == 'category'
                                else series.dropna().unique().tolist())
                        lst = sorted(str(x) for x in vals if str(x).strip())
                        if lst:
                            unique[col] = lst
                    search = df['mensaje'].astype(str).str.lower()
                    return unique, search

                unique_values, search_source = await loop.run_in_executor(None, _compute_meta)
                self.app_state.unique_values  = unique_values
                self.app_state.search_source  = search_source

            logger.info(f"Fichero cargado: {file_name} ({len(df)} entradas)")
            return True

        except Exception as ex:
            logger.error(f"Error cargando fichero: {ex}", exc_info=True)
            return False

    def save_marks(self) -> None:
        """Persiste las marcas del fichero actual en un archivo .marks."""
        if not self.app_state.last_file_path:
            return
        marks_path = f"{self.app_state.last_file_path}.marks"
        if not self.app_state.marked_lines:
            if os.path.exists(marks_path):
                try:
                    os.remove(marks_path)
                except Exception:
                    pass
            return
        try:
            with open(marks_path, "w", encoding="utf-8") as f:
                f.write("\n".join(map(str, sorted(self.app_state.marked_lines))))
        except Exception as ex:
            logger.warning(f"No se pudieron guardar las marcas: {ex}")

    def load_marks(self, file_path: str) -> None:
        """Carga las marcas del fichero dado desde su archivo .marks."""
        marks_path = f"{file_path}.marks"
        if not os.path.exists(marks_path):
            return
        try:
            with open(marks_path, "r", encoding="utf-8") as f:
                marks = {int(line.strip()) for line in f if line.strip().isdigit()}
                self.app_state.marked_lines = marks
        except Exception as ex:
            logger.warning(f"No se pudieron cargar las marcas: {ex}")
