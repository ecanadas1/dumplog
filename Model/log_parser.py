import re
import json
import os
from datetime import datetime
import pandas as pd
from typing import List, Optional, Any, Dict, ClassVar
from .log_entry import LogEntry
import logging

logger = logging.getLogger(__name__)


class LogParser:
    """Clase encargada de leer y parsear archivos de log."""

    # Atributo de clase compartido entre todas las instancias (patrón Registry).
    # Se carga una sola vez mediante load_rules() al arranque de la aplicación.
    notes_rules: ClassVar[List] = []

    @classmethod
    def load_rules(cls, config_path="notes_config.json"):
        """Carga las reglas de anotación automática desde un fichero JSON."""
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    rules = json.load(f)
                for rule in rules:
                    if "keywords" in rule:
                        rule["keywords_lower"] = [k.lower() for k in rule["keywords"]]
                cls.notes_rules = rules
                logger.info(f"Reglas de notas cargadas ({len(rules)} reglas) desde {config_path}")
            except Exception as e:
                logger.error(f"Error cargando configuración de notas: {e}")
        else:
            logger.warning(f"No se encontró el archivo de reglas de notas: {config_path}. Creando uno por defecto.")
            default_rules = [
                {"keywords": ["Process", "Killed"], "text": "Process Killed"},
                {"keywords": ["full", "queue"],     "text": "Queue full"},
                {"keywords": ["node", "starting"],  "text": "Node start"},
                {"keywords": ["memory", "utilization"], "text": "Memory Utilization"}
            ]
            try:
                with open(config_path, 'w', encoding='utf-8') as f:
                    json.dump(default_rules, f, indent=4)
                for rule in default_rules:
                    if "keywords" in rule:
                        rule["keywords_lower"] = [k.lower() for k in rule["keywords"]]
                cls.notes_rules = default_rules
                logger.info(f"Archivo de reglas de notas por defecto creado en: {config_path}")
            except Exception as e:
                logger.error(f"Error creando configuración de notas por defecto: {e}")

    def __init__(self, formato = None):
        if formato is None:
            from .formats.rtp_osv import RtpOsvFormat
            formato = RtpOsvFormat()
        self.formato = formato

    @classmethod
    def detect_format(cls, file_path: str) -> Optional[Any]:
        """Lee las primeras líneas de un fichero e intenta detectar qué formato coincide mejor."""
        from .formats import load_all_formats
        available_formats = list(load_all_formats().values())
        matches = {fmt: 0 for fmt in available_formats}
        lines_tested = 0
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as file:
                for line in file:
                    line = line.strip()
                    if not line: continue
                    lines_tested += 1
                    for fmt in available_formats:
                        try:
                            entry = fmt.parse_line(line, lines_tested)
                            if entry is not None: matches[fmt] += 1
                        except Exception: pass
                    if lines_tested >= 50: break
        except Exception as e:
            logger.error(f"Error durante la auto-detección de formato: {e}")
            return None
        if lines_tested == 0: return None
        best_format = None
        max_matches = 0
        for fmt, count in matches.items():
            if count > max_matches:
                max_matches = count
                best_format = fmt
        if best_format and (max_matches / lines_tested) >= 0.2:
            logger.info(f"Formato auto-detectado: {best_format.name} ({max_matches}/{lines_tested} líneas)")
            return best_format
        return None

    def parse_file(self, file_path: str) -> List[LogEntry]:
        """Lee un archivo de log y lo convierte en una lista de objetos LogEntry."""
        entries = []
        invalid_count = 0
        logger.info(f"Iniciando parseo del archivo ({self.formato.name}): {file_path}")
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as file:
                for line_number, line in enumerate(file, start=1):
                    line = line.strip()
                    if not line: continue
                    entry = self.formato.parse_line(line, line_number)
                    if entry: entries.append(entry)
                    else: invalid_count += 1
            entries = self.formato.post_load_hook(entries)
            logger.info(f"Parseo completado: {len(entries)} entradas")
        except Exception as e:
            logger.error(f"Error leyendo archivo '{file_path}': {e}")
        return entries

    @staticmethod
    def to_dataframe(entries: List[LogEntry]) -> pd.DataFrame:
        """Convierte una lista de LogEntry en un DataFrame de pandas dinámico."""
        if not entries: return pd.DataFrame()
        data = {
            'linea': [e.linea for e in entries],
            'timestamp': [e.timestamp for e in entries],
            'nivel': [e.nivel for e in entries],
            'mensaje': [e.mensaje for e in entries],
            'notas': [e.notas for e in entries],
        }
        extra_keys = set()
        for e in entries:
            if e.extras: extra_keys.update(e.extras.keys())
        for key in extra_keys:
            data[key] = [e.extras.get(key, "") for e in entries]
        df = pd.DataFrame(data)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        for col in df.columns:
            if col not in ['linea', 'timestamp', 'mensaje'] and df[col].nunique() < len(df) / 2:
                df[col] = df[col].astype('category')
        return df

    @staticmethod
    def _clean_df_for_export(df: pd.DataFrame) -> pd.DataFrame:
        """Limpia el DataFrame de nulos de forma infalible para exportación."""
        # 1. Crear una copia y manejar timestamps primero
        temp_df = df.copy()
        for col in temp_df.columns:
            if pd.api.types.is_datetime64_any_dtype(temp_df[col]):
                temp_df[col] = temp_df[col].dt.strftime("%Y-%m-%d %H:%M:%S").fillna('')

        # 2. Convertir TODO el DataFrame a tipo string/object de forma segura fila a fila
        # Esto elimina el tipo Categorical que causa el error al intentar insertar cadenas vacías
        temp_df = pd.DataFrame(
            [[str(val) if pd.notna(val) else "" for val in row] for row in temp_df.values],
            columns=temp_df.columns,
            index=temp_df.index
        )
        
        # 3. Limpiar residuos de cadenas 'nan', 'None', etc.
        variants = ['nan', 'NaN', 'None', '<NA>', 'null']
        for v in variants:
            temp_df = temp_df.replace(v, '')
                
        return temp_df

    @staticmethod
    def format_dataframe_to_text(df: pd.DataFrame) -> str:
        """Convierte un DataFrame de logs en texto formateado dinámicamente."""
        if df.empty: return ""
        try:
            temp_df = LogParser._clean_df_for_export(df)
            std_cols = {'linea', 'timestamp', 'nivel', 'mensaje', 'notas'}
            extra_cols = [c for c in temp_df.columns if c not in std_cols]
            
            lines = []
            for _, row in temp_df.iterrows():
                line = f"#{row['linea']} [{row['timestamp']}] [{row['nivel']}] "
                for col in extra_cols:
                    val = str(row.get(col, '')).strip()
                    if val:
                        line += f"{col.capitalize()}: {val}, "
                
                line += f"\"{row['mensaje']}\""
                if str(row['notas']).strip():
                    line += f" | {row['notas']}"
                lines.append(line)

            return "\n".join(lines)
        except Exception as e:
            logger.error(f"Error en formateo dinámico a texto: {e}")
            return ""

    @staticmethod
    def format_dataframe_to_markdown(df: pd.DataFrame) -> str:
        """Genera manualmente una tabla Markdown dinámica."""
        if df.empty: return ""
        try:
            temp_df = LogParser._clean_df_for_export(df)

            # Orden dinámico de columnas
            std_start = ['linea', 'timestamp', 'nivel']
            std_end = ['mensaje', 'notas']
            extras = [c for c in temp_df.columns if c not in std_start and c not in std_end]
            ordered_cols = std_start + extras + std_end
            
            # Escapar el pipe '|' y limpiar saltos de línea
            for col in ordered_cols:
                if col in temp_df.columns:
                    temp_df[col] = temp_df[col].str.replace("|", "\\|", regex=False).str.replace("\n", " ", regex=False)

            headers = [c.capitalize() for c in ordered_cols]
            header_row = "| " + " | ".join(headers) + " |"
            separator_row = "| " + " | ".join([":---"] * len(headers)) + " |"
            
            body_rows = []
            for _, row in temp_df.iterrows():
                vals = [str(row.get(c, '')) for c in ordered_cols]
                body_rows.append("| " + " | ".join(vals) + " |")
            
            return f"{header_row}\n{separator_row}\n" + "\n".join(body_rows)
        except Exception as e:
            logger.error(f"Error en formateo markdown manual: {e}")
            return ""
