import flet as ft
import asyncio
import os
import logging
import pandas as pd
from pathlib import Path
from Model.log_parser import LogParser
from ..Librerias import i18n

logger = logging.getLogger(__name__)

class FileManager:
    """Gestiona la apertura, carga y recarga de ficheros de log."""

    def __init__(self, page: ft.Page, app_state, layout, configuracion, config_manager, picker, controller):
        self.page = page
        self.app_state = app_state
        self.layout = layout
        self.configuracion = configuracion
        self.config_manager = config_manager
        self.picker = picker
        self.controller = controller

    async def open_file_dialog(self, e=None):
        initial_directory = str(self.configuracion.app.dir_ini)
        result = await self.picker.pick_files(
            allowed_extensions=["txt", "log"],
            dialog_title=i18n.t("menu.open"),
            initial_directory=initial_directory
        )
        if result:
            if await self.cargar_fichero_async(result[0].path, result[0].name):
                self.controller._reset_ui_after_load()

    async def reload_file(self, e=None):
        if self.app_state.last_file_path:
            if await self.cargar_fichero_async(self.app_state.last_file_path, self.app_state.last_file_name):
                self.controller._reset_ui_after_load()

    async def cargar_fichero_async(self, file_path: str, file_name: str):
        """Carga y parsea un fichero de log de forma asíncrona y dinámica."""
        try:
            self.layout.progress_bar.visible = True
            self.page.update()
            
            loop = asyncio.get_running_loop()
            
            # 1. Auto-detección de formato
            detected = None
            if self.app_state.auto_detect_format:
                detected = await loop.run_in_executor(None, lambda: LogParser.detect_format(file_path))
                if detected:
                    self.app_state.active_format = detected
                    if hasattr(self.layout, "format_dropdown") and self.layout.format_dropdown:
                        self.layout.format_dropdown.value = detected.id
                        try: self.layout.format_dropdown.update()
                        except Exception: pass

            formato = self.app_state.active_format
            if formato is None:
                from Model.formats.rtp_osv import RtpOsvFormat
                formato = RtpOsvFormat()
                self.app_state.active_format = formato

            det_suffix = " (Auto-detectado)" if detected else ""
            self.layout.status_text.value = f"Formato: {formato.name}{det_suffix}"
            try: self.layout.status_text.update()
            except Exception: pass

            # 2. Parseo
            entries = await loop.run_in_executor(None, lambda: LogParser(formato).parse_file(file_path))
            df = await loop.run_in_executor(None, lambda: LogParser.to_dataframe(entries))
            
            self.app_state.entries = [] 
            self.app_state.df = df
            self.app_state.filtered_df = df
            self.app_state.last_file_path = file_path
            self.app_state.last_file_name = file_name
            
            self.app_state.marked_lines.clear()
            self.load_marks(file_path)
            
            if not df.empty:
                # 3. Precalcular valores únicos de forma DINÁMICA
                self.app_state.unique_values.clear()
                
                # Identificar columnas candidatas a filtros (categóricas o con pocos valores)
                # Excluimos línea, timestamp y mensaje
                std_excluded = {'linea', 'timestamp', 'mensaje'}
                filter_cols = [c for c in df.columns if c not in std_excluded]
                
                for col in filter_cols:
                    unique_list = await loop.run_in_executor(None, lambda c=col: sorted([str(x) for x in df[c].unique().tolist() if pd.notna(x) and str(x).strip()]))
                    if unique_list:
                        self.app_state.unique_values[col] = unique_list

                self.app_state.search_source = await loop.run_in_executor(None, lambda: df['mensaje'].str.lower())
                ts = df['timestamp']
                self.layout.log_range_text.value = f"{i18n.t('sidebar.start')}: {ts.iloc[0]}\n{i18n.t('sidebar.end')}:    {ts.iloc[-1]}"
            
            self.configuracion.app.dir_ini = Path(os.path.dirname(file_path))
            self.config_manager.guardar(self.configuracion)
            
            self.layout.selected_file_text.value = f"{i18n.t('menu.file')}: {file_name}"
            self.layout.btn_reload.disabled = False
            
            return True 
        except Exception as ex:
            self.layout.status_text.value = f"{i18n.t('msg.error')}: {ex}"
            logger.error(f"Error cargando fichero: {ex}", exc_info=True)
            return False
        finally:
            self.layout.progress_bar.visible = False
            self.page.update()

    def save_marks(self):
        if not self.app_state.last_file_path: return
        marks_path = f"{self.app_state.last_file_path}.marks"
        if not self.app_state.marked_lines:
            if os.path.exists(marks_path):
                try: os.remove(marks_path)
                except Exception: pass
            return
        try:
            with open(marks_path, "w", encoding="utf-8") as f:
                f.write("\n".join(map(str, sorted(self.app_state.marked_lines))))
        except Exception: pass

    def load_marks(self, file_path: str):
        marks_path = f"{file_path}.marks"
        if not os.path.exists(marks_path): return
        try:
            with open(marks_path, "r", encoding="utf-8") as f:
                marks = {int(line.strip()) for line in f if line.strip().isdigit()}
                self.app_state.marked_lines = marks
        except Exception: pass
