import re
from datetime import datetime, date
from typing import Optional, List
from Model.log_entry import LogEntry
from .base_format import BaseFormat

# Mapa de severidad RFC 5424 (prival % 8) -> nivel legible
_RFC5424_SEVERITY = {
    0: "EMERGENCY",
    1: "ALERT",
    2: "CRITICAL",
    3: "ERROR",
    4: "WARNING",
    5: "NOTICE",
    6: "INFO",
    7: "DEBUG",
}

class SyslogFormat(BaseFormat):
    # Patrón 1 - RFC 5424: <PRIVAL>VERSION TIMESTAMP HOSTNAME APP-NAME PROCID MSGID SD MSG
    # Ejemplo: <34>1 2003-10-11T22:14:15.003Z mymachine.example.com su - ID47 - mensaje
    LOG_PATTERN_5424 = re.compile(
        r'^<(\d{1,3})>(\d+)\s+'                      # <prival>version
        r'(\S+)\s+'                                   # timestamp (ISO-8601 o "-")
        r'(\S+)\s+'                                   # hostname
        r'(\S+)\s+'                                   # app-name
        r'(\S+)\s+'                                   # procid
        r'(\S+)\s+'                                   # msgid
        r'(?:(\[.*?\](?:\s*\[.*?\])*)|(-))(?:\s|$)' # structured-data
        r'(.*)$'                                      # mensaje
    )

    # Patrón 2 - Syslog RFC 3164 estándar: "Jan  3 10:05:01 host proc[pid]: msg"
    LOG_PATTERN_RFC = re.compile(
        r'^([A-Z][a-z]{2}\s+\d+\s+\d{2}:\d{2}:\d{2})\s+(\S+)\s+([^:\[\s]+)(?:\[(\d+)\])?:?\s*(.*)$'
    )
    # Patrón 3 - Variante numérica: " 17 8:1:1 host proc[pid]: msg"
    LOG_PATTERN_NUM = re.compile(
        r'^\s*(\d{1,2})\s+(\d{1,2}):(\d{1,2}):(\d{1,2})\s+(\S+)\s+([^:\[\s]+)(?:\[(\d+)\])?:?\s*(.*)$'
    )

    @property
    def id(self) -> str:
        return "syslog"

    @property
    def name(self) -> str:
        return "Syslog Standard"

    def get_extra_columns(self) -> List[str]:
        return ["host", "proceso", "pid"]

    def parse_line(self, line: str, line_number: int) -> Optional[LogEntry]:
        # --- Intentar patrón RFC 5424 primero ---
        match = self.LOG_PATTERN_5424.match(line)
        if match:
            try:
                prival = int(match.group(1))
                severity = prival % 8
                nivel = _RFC5424_SEVERITY.get(severity, "INFO")

                ts_raw = match.group(3)
                if ts_raw == "-":
                    timestamp = datetime.now()
                else:
                    # Intentar parsear ISO 8601
                    ts_norm = ts_raw.replace("Z", "+00:00")
                    try:
                        timestamp = datetime.fromisoformat(ts_norm)
                        # Quitar tzinfo para consistencia
                        timestamp = timestamp.replace(tzinfo=None)
                    except Exception:
                        timestamp = datetime.strptime(ts_norm[:19], "%Y-%m-%dT%H:%M:%S")

                host = match.group(4) if match.group(4) != "-" else ""
                proceso = match.group(5) if match.group(5) != "-" else ""
                pid = match.group(6) if match.group(6) != "-" else None
                mensaje = match.group(9).strip()

                return self._make_entry(line_number, timestamp, host, proceso, pid, mensaje, nivel_override=nivel)
            except Exception:
                pass

        # --- Intentar patrón RFC 3164 ---
        match = self.LOG_PATTERN_RFC.match(line)
        if match:
            try:
                timestamp_str = re.sub(r'\s+', ' ', match.group(1))
                current_year = datetime.now().year
                timestamp = datetime.strptime(f"{current_year} {timestamp_str}", "%Y %b %d %H:%M:%S")
                host    = match.group(2)
                proceso = match.group(3)
                pid     = match.group(4) if match.group(4) else None
                mensaje = match.group(5)
                return self._make_entry(line_number, timestamp, host, proceso, pid, mensaje)
            except Exception:
                pass

        # --- Intentar patrón numérico: " DD H:M:S host proc[pid]: msg" ---
        match = self.LOG_PATTERN_NUM.match(line)
        if match:
            try:
                today = date.today()
                day  = int(match.group(1))
                hour = int(match.group(2))
                minu = int(match.group(3))
                sec  = int(match.group(4))
                timestamp = datetime(today.year, today.month, day, hour, minu, sec)
                host    = match.group(5)
                proceso = match.group(6)
                pid     = match.group(7) if match.group(7) else None
                mensaje = match.group(8)
                return self._make_entry(line_number, timestamp, host, proceso, pid, mensaje)
            except Exception:
                pass

        return None

    def _make_entry(self, line_number, timestamp, host, proceso, pid, mensaje, nivel_override: str = None) -> LogEntry:
        """Construye un LogEntry determinando el nivel por palabras clave o override."""
        if nivel_override:
            nivel = nivel_override
        else:
            msg_lower = mensaje.lower()
            if any(w in msg_lower for w in ["error", "fail", "critical", "pam: auth"]):
                nivel = "ERROR"
            elif any(w in msg_lower for w in ["warning", "warn", "alert"]):
                nivel = "WARNING"
            elif "debug" in msg_lower:
                nivel = "DEBUG"
            else:
                nivel = "INFO"

        from Model.log_parser import LogParser
        notas = self.extract_notes(mensaje, LogParser.notes_rules)

        extras = {
            "evento":  host,
            "host":    host,
            "proceso": proceso,
            "pid":     pid,
        }

        return LogEntry(
            linea=line_number,
            timestamp=timestamp,
            nivel=nivel,
            mensaje=mensaje,
            notas=notas,
            extras=extras,
        )


