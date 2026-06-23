# Interface/Core/i18n.py
"""
Responsabilidad única: internacionalización (i18n) de la aplicación.
Carga archivos de traducción JSON y provee la función t() para traducir claves.
No conoce la UI ni el estado de la aplicación.
"""
import json
import os
import logging

logger = logging.getLogger(__name__)

_translations = {}
_current_lang = "es"

def load(lang: str, locales_dir: str = "locales"):
    """
    Carga el archivo de traducciones para el idioma especificado.

    Args:
        lang (str): Código del idioma (ej: 'es', 'en').
        locales_dir (str): Directorio donde se encuentran los archivos .json.
    """
    global _translations, _current_lang
    import sys
    if hasattr(sys, '_MEIPASS'):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    full_locales_dir = os.path.join(base_path, locales_dir)
    path = os.path.join(full_locales_dir, f"{lang}.json")

    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                _translations = json.load(f)
            _current_lang = lang
            logger.info(f"Traducciones cargadas para: {lang}")
        else:
            logger.warning(f"No se encontró el archivo de traducción: {path}")
            if lang != "es":
                load("es", locales_dir)
    except Exception as e:
        logger.error(f"Error cargando traducciones: {e}")

def t(key: str, default: str = None, **kwargs) -> str:
    """
    Traduce una clave al idioma actual. Soporta interpolación.

    Args:
        key (str): Clave de la traducción (ej: 'app.title').
        default (str): Texto de fallback si la clave no existe.
        **kwargs: Valores para interpolar en el texto.

    Returns:
        str: Texto traducido o el valor de default (o la clave) si no se encuentra.
    """
    fallback = default if default is not None else key
    text = _translations.get(key, fallback)
    try:
        if kwargs:
            return text.format(**kwargs)
        return text
    except Exception as e:
        logger.error(f"Error formateando traducción '{key}': {e}")
        return text

def current() -> str:
    """Devuelve el código del idioma actual."""
    return _current_lang
