import re
from datetime import datetime
from typing import Optional, List
from Model.log_entry import LogEntry
from .base_format import BaseFormat

class RtpOsvFormat(BaseFormat):
    LOG_PATTERN = re.compile(r'^(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2}:\d{2})\s+(\S+)\s+(\S+)\s+"(.*)"\s*(.*)$')
    PID_PATTERN = re.compile(r'\(pid[:\s]+(\d{2,5})[),]', re.IGNORECASE)
    PROCESS_OVERRIDE_PATTERN = re.compile(r': Process\s+(\S+)')

    @property
    def id(self) -> str:
        return "rtp_osv"

    @property
    def name(self) -> str:
        return "RTP OSV"

    def get_extra_columns(self) -> List[str]:
        return ["evento", "proceso", "pid"]

    def parse_line(self, line: str, line_number: int) -> Optional[LogEntry]:
        match = self.LOG_PATTERN.match(line)
        if not match:
            return None

        try:
            timestamp_str = f"{match.group(1)} {match.group(2)}"
            timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
            
            raw_message = match.group(5)
            
            # 1. Extraer Proceso: Desde el inicio hasta el primer ':'
            parts = raw_message.split(':', 1)
            proceso = parts[0].strip() if len(parts) > 1 else ""
            
            # 1.1 Excepción: Si aparece ": Process", la siguiente palabra es el proceso real
            proc_override_match = self.PROCESS_OVERRIDE_PATTERN.search(raw_message)
            if proc_override_match and proceso == "RTP":
                proceso = proc_override_match.group(1)
            
            # 2. Extraer PID: Buscar patrón (pid xxxx)
            pid_match = self.PID_PATTERN.search(raw_message)
            pid = pid_match.group(1) if pid_match else None
            
            # 3. Extraer Notas
            from Model.log_parser import LogParser
            notes_rules = LogParser.notes_rules
            notas = self.extract_notes(raw_message, notes_rules)

            extras = {
                "evento": match.group(3),
                "proceso": proceso,
                "pid": pid
            }

            return LogEntry(
                linea=line_number,
                timestamp=timestamp,
                nivel=match.group(4),
                mensaje=raw_message,
                notas=notas,
                extras=extras
            )
        except Exception:
            return None
