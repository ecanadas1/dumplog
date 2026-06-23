# Model/formats/__init__.py
import os
import json
from .base_format import BaseFormat, SimpleFormat
from .rtp_osv import RtpOsvFormat
from .syslog import SyslogFormat

from functools import lru_cache

@lru_cache(maxsize=1)
def load_all_formats(config_path="formats_config.json") -> dict:
    """Carga todos los formatos disponibles, tanto estáticos (Python) como dinámicos (JSON)."""
    formats = {}
    
    # 1. Formatos estáticos Python
    rtp = RtpOsvFormat()
    syslog = SyslogFormat()
    formats[rtp.id] = rtp
    formats[syslog.id] = syslog
    
    # 2. Formatos dinámicos desde JSON
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config_list = json.load(f)
            for item in config_list:
                # Evitar sobreescribir si ya existe un formato con ese ID
                fmt_id = item.get("id")
                if fmt_id and fmt_id not in formats:
                    # Cargador diferido para las reglas de notas
                    def get_notes_rules():
                        from Model.notes_registry import notes_rules
                        return notes_rules
                    
                    simple = SimpleFormat(item, notes_rules_loader=get_notes_rules)
                    formats[simple.id] = simple
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Error cargando formatos desde JSON: {e}")
            
    return formats
