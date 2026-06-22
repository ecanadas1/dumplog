# Librerias/config_manager.py
import configparser
from pathlib import Path
from .app_settings import AppSettings, SeccionAPP  # Importamos el modelo
import logging

logger = logging.getLogger(__name__)

DEFAULT_TEMA = 'sistema'
DEFAULT_LOG_LEVEL = 'ERROR'
DEFAULT_DIR = str(Path.cwd())
DEFAULT_PAGE_SIZE = 50 # Nuevo valor por defecto

class ConfigManager:
    """Gestiona la carga y guardado de la configuración desde/hacia un archivo .ini."""

    def __init__(self, file_ini: str):
        self.path_ini = Path(file_ini)
        self._parser = configparser.ConfigParser()

    def cargar(self) -> AppSettings:
        """Lee el .ini y devuelve un objeto AppSettings."""
        if not self.path_ini.exists():
            # Si no existe, creamos uno por defecto y lo guardamos
            logger.info(f"Archivo de configuración no encontrado. Creando uno nuevo en: {self.path_ini}")
            settings = AppSettings()
            self.guardar(settings)
            return settings

        try:
            self._parser.read(self.path_ini, encoding='utf-8')

            # Se cargan los valores leídos, si falta alguno, se carga el valor por defecto
            app_data = SeccionAPP(
                ventana=self._parser.get('APP', 'ventana', fallback=''),
                dir_ini=Path(self._parser.get('APP', 'dir_ini', fallback=DEFAULT_DIR)),
                tema=self._parser.get('APP', 'tema', fallback=DEFAULT_TEMA),
                log_level = self._parser.get('APP', 'log_level', fallback=DEFAULT_LOG_LEVEL),
                resaltado_sintaxis = self._parser.getboolean('APP', 'resaltado_sintaxis', fallback=True),
                page_size_default = self._parser.getint('APP', 'page_size_default', fallback=DEFAULT_PAGE_SIZE),
                context_range = self._parser.getint('APP', 'context_range', fallback=10),
                idioma = self._parser.get('APP', 'idioma', fallback='es'),
                historial_busqueda = self._parser.get('APP', 'historial_busqueda', fallback='').split('|||') if self._parser.get('APP', 'historial_busqueda', fallback='') else []
            )

            # Valída los directorios de entrada, si no existen busca el directorio padre
            app_data.dir_ini = self._validar_directorio(app_data.dir_ini)

            # Valida el tema
            app_data.tema = self._validar_tema(app_data.tema)
            app_data.log_level = self._validar_log_level(app_data.log_level)
            app_data.page_size_default = self._validar_page_size(app_data.page_size_default)
            app_data.idioma = self._validar_idioma(app_data.idioma)
            # Limpiar entradas vacías del historial por si acaso
            app_data.historial_busqueda = [h for h in app_data.historial_busqueda if h.strip()]

            return AppSettings(app=app_data)
        except Exception as e:
            logger.error(f"Error al cargar la configuración desde {self.path_ini}: {e}")
            # En caso de error crítico, devolvemos una configuración por defecto
            return AppSettings()

    def guardar(self, settings: AppSettings) -> None:
        """Guarda el objeto AppSettings en el archivo .ini."""
        try:
            self._parser['APP'] = {
                'ventana': settings.app.ventana,
                'dir_ini': str(settings.app.dir_ini),
                'tema': settings.app.tema,
                'log_level': settings.app.log_level,
                'resaltado_sintaxis': str(settings.app.resaltado_sintaxis),
                'page_size_default': str(settings.app.page_size_default),
                'context_range': str(settings.app.context_range),
                'idioma': settings.app.idioma,
                'historial_busqueda': '|||'.join(settings.app.historial_busqueda)
            }

            with open(self.path_ini, 'w', encoding='utf-8') as configfile:
                self._parser.write(configfile)
            logger.info(f"Configuración guardada exitosamente en {self.path_ini}")
        except Exception as e:
            logger.error(f"Error al guardar la configuración en {self.path_ini}: {e}")


    @staticmethod
    def _validar_directorio(directorio: Path) -> Path:
        """
        Valída el directorio de entrada, si no existe busca el directorio padre.
        """
        original_dir = directorio
        while not directorio.is_dir():
            if directorio.parent == directorio:
                # Se ha llegado a la raíz (ej. 'C:\\') y no existe, usar directorio actual.
                logger.warning(f"Directorio configurado '{original_dir}' no válido. Usando directorio actual.")
                return Path.cwd()
            directorio = directorio.parent
        
        if original_dir != directorio:
            logger.warning(f"Directorio configurado '{original_dir}' no existe. Usando padre válido: '{directorio}'")

        return directorio

    @staticmethod
    def _validar_tema(tema: str)-> str:
        temas_validos = ['claro', 'oscuro', 'sistema']
        if tema.lower() not in temas_validos:
            logger.warning(f"Tema configurado '{tema}' no válido. Usando '{DEFAULT_TEMA}'.")
            tema = DEFAULT_TEMA
        return tema

    @staticmethod
    def _validar_log_level(log_level: str)-> str:
        log_level_validos = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if log_level.upper() not in log_level_validos:
            logger.warning(f"Nivel de log configurado '{log_level}' no válido. Usando '{DEFAULT_LOG_LEVEL}'.")
            log_level = DEFAULT_LOG_LEVEL
        return log_level

    @staticmethod
    def _validar_page_size(page_size: int) -> int:
        sizes_validos = [50, 100, 200, 500]
        if page_size not in sizes_validos:
            logger.warning(f"Tamaño de página configurado '{page_size}' no válido. Usando '{DEFAULT_PAGE_SIZE}'.")
            page_size = DEFAULT_PAGE_SIZE
        return page_size

    @staticmethod
    def _validar_idioma(idioma: str) -> str:
        idiomas_validos = ['es', 'en']
        if idioma.lower() not in idiomas_validos:
            logger.warning(f"Idioma configurado '{idioma}' no válido. Usando 'es'.")
            idioma = 'es'
        return idioma
