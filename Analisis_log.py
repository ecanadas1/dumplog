"""
Carga un archivo resultante de un RTPDumpLog de la OSV para analizarlo.
Permite Realizar multiples filtros para localizar errores y exportar los datos filtrados.
"""

from Interface.Manager import Manager
from Interface.Librerias.app_settings import Version
from Interface.Librerias.config_manager import ConfigManager
import sys
import os
from pathlib import Path
import flet as ft
import logging
from logging.handlers import TimedRotatingFileHandler
import asyncio

__author__ = 'Eduardo Cañadas'
__title__ = 'Visor de ficheros de Log'
__date__ = '09/06/2026'
__version__ = '0.8.0'

def setup_global_logging(log_name: str, config_log_level_str: str = 'INFO', log_dir: str = "logs_app"):
    """
    Configura el sistema de logging global de la aplicación.

    Crea el directorio de logs si no existe, establece el nivel de severidad
    y registra dos handlers: uno para la consola (stdout) y otro de rotación
    diaria de ficheros (TimedRotatingFileHandler con retención de 7 días).

    Args:
        log_name (str): Nombre base del fichero de log (sin extensión).
        config_log_level_str (str): Nivel de log como cadena ('DEBUG', 'INFO',
            'WARNING', 'ERROR', 'CRITICAL'). Por defecto 'INFO'.
        log_dir (str): Directorio donde se guardarán los ficheros de log.
            Por defecto 'logs_app' relativo al directorio de trabajo.
    """
    log_path = Path(log_dir)
    log_path.mkdir(exist_ok=True)
    
    log_file_path = log_path / f"{log_name}.log"

    numeric_level = getattr(logging, config_log_level_str.upper(), None)
    if not isinstance(numeric_level, int):
        logging.warning(f"Nivel de log no válido '{config_log_level_str}'. Usando INFO por defecto.")
        numeric_level = logging.INFO

    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    log_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(module)s.%(funcName)s:%(lineno)d - %(message)s'
    )

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_formatter)

    file_rotating_handler = TimedRotatingFileHandler(
        filename=log_file_path,
        when='midnight',
        interval=1,
        backupCount=7,
        encoding='utf-8',
        utc=False
    )
    file_rotating_handler.setFormatter(log_formatter)

    if root_logger.hasHandlers():
        root_logger.handlers.clear()

    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_rotating_handler)


def silent_loop_exception_handler(handler_loop, context):
    """
    Manejador de excepciones del event-loop que silencia errores específicos de conexión.

    Silencia el error WinError 10054 (ConnectionResetError) y BrokenPipeError que pueden
    ocurrir al cerrar la aplicación o cuando el navegador se desconecta inesperadamente
    del servidor de Flet.

    Args:
        handler_loop: El event loop donde ocurrió la excepción.
        context: Diccionario que contiene información sobre la excepción.
    """
    exception = context.get("exception")
    if isinstance(exception, (ConnectionResetError, BrokenPipeError)):
        return
    handler_loop.default_exception_handler(context)


async def main(page: ft.Page):
    """
    Punto de entrada principal de la aplicación Flet.

    Realiza la secuencia de arranque completa:
      1. Instala el manejador silencioso para WinError 10054.
      2. Construye los metadatos de versión (autor, título, fecha, versión, ayuda).
      3. Determina la ruta del ejecutable (compatible con PyInstaller).
      4. Inicializa el ConfigManager y carga la configuración desde el .ini.
      5. Configura el sistema de logging con el nivel indicado en la config.
      6. Instancia el Manager, que construye toda la interfaz gráfica.

    Args:
        page (ft.Page): Objeto de página proporcionado por el framework Flet.
    """
    # Silenciar errores de conexión reseteada al cerrar (WinError 10054)
    try:
        loop = asyncio.get_running_loop()
        loop.set_exception_handler(silent_loop_exception_handler)
    except RuntimeError as e:
        print(f"[WARN] No se pudo configurar el manejador de errores del loop: {e}")

    # Configuración de la versión
    metadata = Version(
        author=__author__,
        title=__title__,
        date=__date__,
        version=__version__,
        help="",  # Se maneja dinámicamente en dialogs.py mediante get_help_text
    )

    # Determina el nombre base de la aplicación y rutas
    if getattr(sys, 'frozen', False):
        app_path = Path(sys.executable)
    else:
        app_path = Path(sys.argv[0])
    
    app_dir = app_path.parent
    app_name = app_path.stem 
    config_file = f"{app_name}.ini"

    # Inicializa la configuración desde el fichero .ini
    config_manager = ConfigManager(config_file)
    my_settings = config_manager.cargar()

    # Configura el logging pasando el nombre de la aplicación
    setup_global_logging(app_name, my_settings.app.log_level)
    logger = logging.getLogger(__name__)

    logger.info(f"Lectura del fichero de configuración '{config_file}' correcta.")
    logger.info("Iniciando la aplicación.")

    Manager(page, config_manager, my_settings, metadata)

if __name__ == "__main__":
    try:
        # Usamos ft.run con assets_dir para evitar avisos de deprecación
        ft.run(main, assets_dir="assets")
    except SystemExit:
        pass
    except Exception as e:
        print(f"Error al cerrar la aplicación: {e}")
    finally:
        # Aseguramos que el proceso muera incluso si ft.run() no termina limpiamente
        os._exit(0)
