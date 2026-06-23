from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

@dataclass
class LogEntry:
    """
    Representa una entrada individual estructurada de un archivo de log.

    Contiene campos base (línea, timestamp, nivel, mensaje, notas) y un
    diccionario 'extras' para almacenar campos específicos de formatos dinámicos.
    """
    linea: int
    timestamp: datetime
    nivel: str
    mensaje: str
    notas: str = ""
    extras: dict = field(default_factory=dict)

    # Propiedades de compatibilidad con el código existente
    @property
    def evento(self) -> str:
        return self.extras.get("evento", "")

    @property
    def proceso(self) -> str:
        return self.extras.get("proceso", "")

    @property
    def pid(self) -> Optional[str]:
        return self.extras.get("pid")

    def __str__(self) -> str:
        """Formato legible para imprimir en consola y exportar."""
        formatted_timestamp = self.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        
        # Handle PID: display "PID: XXXX" or "PID: -" if empty
        pid_display = f"PID: {self.pid}" if self.pid else "PID: -"
        
        # Construct the string based on the desired format
        return (f"#{self.linea} "
                f"[{formatted_timestamp}] "
                f"[{self.nivel}] "
                f"[{self.proceso}] "
                f"Evento: {self.evento}, "
                f"{pid_display}, "
                f"Mensaje: \"{self.mensaje}\", "
                f"notas: {self.notas}")
