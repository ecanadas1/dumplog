# Model/notes_registry.py
import os
import json
import logging
from typing import List

logger = logging.getLogger(__name__)

notes_rules: List = []

def load_rules(config_path="notes_config.json") -> List:
    """Carga las reglas de anotación automática desde un fichero JSON."""
    global notes_rules
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                rules = json.load(f)
            for rule in rules:
                if "keywords" in rule:
                    rule["keywords_lower"] = [k.lower() for k in rule["keywords"]]
            notes_rules.clear()
            notes_rules.extend(rules)
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
            notes_rules.clear()
            notes_rules.extend(default_rules)
            logger.info(f"Archivo de reglas de notas por defecto creado en: {config_path}")
        except Exception as e:
            logger.error(f"Error creando configuración de notas por defecto: {e}")
    return notes_rules
