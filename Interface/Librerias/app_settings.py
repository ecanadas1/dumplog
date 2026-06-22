# Librerias/app_settings.py
"""
Crea todas las clases de datos de la aplicación
"""

from dataclasses import dataclass, field
from typing import Dict, Any
from pathlib import Path

@dataclass
class SeccionAPP:
    ventana: str = ''
    dir_ini: Path = field(default_factory=Path.cwd)
    tema: str = 'sistema'
    log_level: str = 'ERROR'
    resaltado_sintaxis: bool = True
    page_size_default: int = 50 
    context_range: int = 10     
    idioma: str = 'es'          # Nuevo: Idioma de la aplicación ('es', 'en')
    historial_busqueda: list = field(default_factory=list)

@dataclass
class AppSettings:
    """Contiene toda la configuración de la aplicación."""
    app: SeccionAPP = field(default_factory=SeccionAPP)

@dataclass
class  Version:
    author: str = ""
    title: str = ""
    date: str = ""
    version: str = ""
    help: str = ""

@dataclass
class DatosConfig:
    """
    Esta Clase la utilizamos para almacenar todos los datos de configuración globales
    para usarlos desde cualquier parte de la aplicación.
    """
    config: AppSettings
    version: Version = field(default_factory=Version)
    path_fichero: str = ""
    n_fichero: str = ""
