import flet as ft
import pandas as pd
import csv
import os
import asyncio
import logging
import sqlite3
from Model.log_parser import LogParser
from ..Librerias import i18n

logger = logging.getLogger(__name__)

class ExportManager:
    """Gestiona la exportación de los registros filtrados a distintos formatos de forma dinámica."""

    def __init__(self, page, app_state, layout, picker):
        self.page = page
        self.app_state = app_state
        self.layout = layout
        self.picker = picker

    async def exportar_datos(self, formato: str):
        """Exporta el DataFrame filtrado al formato indicado de forma no bloqueante."""
        if self.app_state.df.empty:
            self.layout.status_text.value = i18n.t("msg.no_data_to_export")
            self.page.update()
            return

        df_filtered = self.app_state.filtered_df
        if df_filtered.empty:
            self.layout.status_text.value = i18n.t("msg.no_matches_filters")
            self.page.update()
            return

        try:
            # Asegurar sincronización del picker
            if hasattr(self.page, "services") and self.picker not in self.page.services:
                self.page.services.append(self.picker)
                self.page.update()
                await asyncio.sleep(0.5)
            
            self.picker.update()
            await asyncio.sleep(0.2)
            
            file_path = await self.picker.save_file(
                dialog_title=f"{i18n.t('menu.export')} {formato.upper()}",
                file_name=f"export_filtrado.{formato}",
                allowed_extensions=[formato]
            )

            if file_path:
                self.layout.status_text.value = f"{i18n.t('msg.exporting')} ({formato.upper()})..."
                self.page.update()

                def save_to_file():
                    # 1. Crear una copia limpia para exportar (convertir categorías a str para evitar errores)
                    df_export = df_filtered.copy()
                    for col in df_export.columns:
                        if isinstance(df_export[col].dtype, pd.CategoricalDtype):
                            df_export[col] = df_export[col].astype(str)

                    if formato == 'txt':
                        content = LogParser.format_dataframe_to_text(df_export)
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(content)

                    elif formato == 'csv':
                        # Orden dinámico: linea, timestamp, nivel, extras..., mensaje, notas
                        std_start = ['linea', 'timestamp', 'nivel']
                        std_end = ['mensaje', 'notas']
                        extras = [c for c in df_export.columns if c not in std_start and c not in std_end]
                        ordered_cols = std_start + extras + std_end
                        
                        df_export[ordered_cols].to_csv(file_path, sep=';', index=False, quoting=csv.QUOTE_MINIMAL, encoding='utf-8')

                    elif formato == 'md':
                        content = LogParser.format_dataframe_to_markdown(df_export)
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(content)

                    elif formato == 'sqlite':
                        # Añadir columna de marcada
                        df_export['marcada'] = df_export['linea'].isin(self.app_state.marked_lines).astype(int)

                        # Convertir datetime a string ISO para SQLite
                        if pd.api.types.is_datetime64_any_dtype(df_export['timestamp']):
                            df_export['timestamp'] = df_export['timestamp'].astype(str)
                                
                        # Limpiar nulos antes de SQLite
                        for col in df_export.columns:
                            if df_export[col].dtype == 'object':
                                df_export[col] = df_export[col].fillna("").astype(str)
                                    
                        with sqlite3.connect(file_path) as conn:
                            df_export.to_sql('log_entries', conn, if_exists='replace', index=False)
                            conn.commit()

                loop = asyncio.get_running_loop()
                await loop.run_in_executor(None, save_to_file)

                num_registros = len(df_filtered)
                self.layout.status_text.value = i18n.t("msg.export_success", count=num_registros, file=os.path.basename(file_path))
                logger.info(f"{num_registros} registros exportados correctamente a {file_path}")
            else:
                self.layout.status_text.value = i18n.t("msg.export_cancelled")

        except Exception as ex:
            self.layout.status_text.value = f"{i18n.t('msg.error_exporting')}: {ex}"
            logger.error(f"Error al exportar datos: {ex}", exc_info=True)
        finally:
            self.page.update()
