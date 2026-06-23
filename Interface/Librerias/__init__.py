# Interface/Librerias/__init__.py
# Shim de compatibilidad — re-exporta todo desde Interface.Core
# Mantiene funcionando todos los imports existentes sin modificarlos.
from Interface.Core.app_settings import AppSettings, SeccionAPP, Version, DatosConfig
from Interface.Core.config_manager import ConfigManager
from Interface.Core import i18n

__all__ = ["AppSettings", "SeccionAPP", "Version", "DatosConfig", "ConfigManager", "i18n"]
