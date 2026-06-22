from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from datetime import datetime
import re
from Model.log_entry import LogEntry

class BaseFormat(ABC):
    @property
    @abstractmethod
    def id(self) -> str:
        """Identificador único del formato: 'rtp_osv', 'syslog'..."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Nombre legible: 'RTP OSV', 'Syslog'..."""

    @property
    def date_format(self) -> str:
        return "%Y-%m-%d %H:%M:%S"

    @abstractmethod
    def parse_line(self, line: str, line_number: int) -> Optional[LogEntry]:
        """Parsea una línea y retorna un LogEntry o None."""

    def get_extra_columns(self) -> List[str]:
        """Columnas adicionales que este formato expone (para la UI)."""
        return []

    def post_load_hook(self, entries: List[LogEntry]) -> List[LogEntry]:
        """Hook opcional para post-procesamiento tras parsear todo el archivo."""
        return entries

    def extract_notes(self, message: str, notes_rules: List[Dict[str, Any]]) -> str:
        """Extrae notas automáticas basadas en las reglas de configuración."""
        if not notes_rules:
            return ""
        detected = []
        msg_lower = message.lower()
        for rule in notes_rules:
            keywords = rule.get("keywords_lower")
            if keywords and all(k in msg_lower for k in keywords):
                text = rule.get("text") or rule.get("note") or ""
                if text:
                    detected.append(text)
        return " | ".join(detected) if detected else ""


class SimpleFormat(BaseFormat):
    def __init__(self, config: Dict[str, Any], notes_rules_loader=None):
        self._id = config.get("id")
        self._name = config.get("name")
        self._regex_str = config.get("regex")
        self._regex = re.compile(self._regex_str)
        self._mapping = config.get("mapping", {})
        self._date_format = config.get("date_format", "%Y-%m-%d %H:%M:%S")
        self._extra_columns = config.get("extra_columns", [])
        self._notes_rules_loader = notes_rules_loader

    @property
    def id(self) -> str:
        return self._id

    @property
    def name(self) -> str:
        return self._name

    @property
    def date_format(self) -> str:
        return self._date_format

    def get_extra_columns(self) -> List[str]:
        return self._extra_columns

    def parse_line(self, line: str, line_number: int) -> Optional[LogEntry]:
        match = self._regex.match(line)
        if not match:
            return None
        
        try:
            # 1. Timestamp
            ts_idx = self._mapping.get("timestamp")
            if isinstance(ts_idx, list):
                ts_str = " ".join(match.group(idx) for idx in ts_idx)
            elif ts_idx is not None:
                ts_str = match.group(ts_idx)
            else:
                ts_str = None
            
            if ts_str:
                if "%Y" not in self._date_format and "%y" not in self._date_format:
                    current_year = datetime.now().year
                    ts_str_clean = re.sub(r'\s+', ' ', ts_str)
                    ts_str = f"{current_year} {ts_str_clean}"
                    date_fmt = f"%Y {self._date_format}"
                else:
                    date_fmt = self._date_format
                timestamp = datetime.strptime(ts_str, date_fmt)
            else:
                timestamp = datetime.now()
                
            # 2. Level (nivel)
            nivel_idx = self._mapping.get("nivel")
            if nivel_idx is not None:
                nivel = match.group(nivel_idx).strip()
                # Normalizar niveles de una sola letra para la UI
                nivel_upper = nivel.upper()
                if nivel_upper == "I":
                    nivel = "INFO"
                elif nivel_upper == "W":
                    nivel = "WARNING"
                elif nivel_upper == "E":
                    nivel = "ERROR"
                elif nivel_upper == "D":
                    nivel = "DEBUG"
            else:
                nivel = "INFO"
                
            # 3. Message (mensaje)
            msg_idx = self._mapping.get("mensaje")
            if msg_idx is not None:
                mensaje = match.group(msg_idx)
            else:
                mensaje = line
                
            # 4. Extras (extra columns)
            extras = {}
            for col in self._extra_columns:
                col_idx = self._mapping.get(col)
                if col_idx is not None:
                    extras[col] = match.group(col_idx)
            
            # Extract notes
            notes_rules = []
            if self._notes_rules_loader:
                notes_rules = self._notes_rules_loader()
            
            notas = self.extract_notes(mensaje, notes_rules)
            
            return LogEntry(
                linea=line_number,
                timestamp=timestamp,
                nivel=nivel,
                mensaje=mensaje,
                notas=notas,
                extras=extras
            )
        except Exception:
            return None
