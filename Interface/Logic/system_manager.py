import flet as ft
import asyncio
import logging
import os
import sys

logger = logging.getLogger(__name__)

class SystemManager:
    """
    Gestiona la configuración del sistema de la aplicación.

    Centraliza las operaciones de bajo nivel relacionadas con la ventana
    y la configuración persistente: tema visual, geometría de la ventana,
    nivel de log y cierre limpio de la aplicación.
    """

    def __init__(self, page: ft.Page, configuracion, config_manager, layout):
        """
        Inicializa el SystemManager.

        Args:
            page (ft.Page): Página Flet activa.
            configuracion (AppSettings): Configuración actual de la aplicación.
            config_manager (ConfigManager): Gestor de persistencia del .ini.
            layout (AppLayout): Referencia al layout para refrescar la barra de app.
        """
        self.page = page
        self.configuracion = configuracion
        self.config_manager = config_manager
        self.layout = layout

    def apply_theme(self):
        """
        Aplica el tema visual (claro/oscuro/sistema) al iniciar la aplicación.

        Lee el tema almacenado en la configuración y establece el
        ``page.theme_mode`` junto con los temas Material 3 con semilla BLUE.
        """
        tema = self.configuracion.app.tema.lower()
        self.page.theme_mode = ft.ThemeMode.LIGHT if tema == 'claro' else \
                               ft.ThemeMode.DARK if tema == 'oscuro' else \
                               ft.ThemeMode.SYSTEM
        self.page.theme = ft.Theme(color_scheme_seed=ft.Colors.BLUE, use_material3=True)
        self.page.dark_theme = ft.Theme(color_scheme_seed=ft.Colors.BLUE, use_material3=True)

    def cambiar_tema(self, mode):
        """
        Cambia el tema visual en tiempo de ejecución y lo persiste.

        Actualiza ``page.theme_mode``, guarda el nuevo valor en el .ini
        y refresca la barra de aplicación para reflejar el cambio de icono.

        Args:
            mode (str): Nombre del tema: 'claro', 'oscuro' o 'sistema'.
        """
        self.page.theme_mode = ft.ThemeMode.LIGHT if mode == 'claro' else \
                               ft.ThemeMode.DARK if mode == 'oscuro' else \
                               ft.ThemeMode.SYSTEM
        self.configuracion.app.tema = mode
        self.config_manager.guardar(self.configuracion)
        self.layout.refresh_appbar()

    def apply_geometry(self):
        """
        Restaura la posición y tamaño de la ventana guardados en la configuración.

        Espera una cadena con formato ``'ANCHOxALTO+IZQ+ARR'`` en
        ``configuracion.app.ventana``. Si el formato no es válido o la cadena
        está vacía, no hace nada.
        """
        geometria = self.configuracion.app.ventana
        if geometria:
            try:
                parts = geometria.replace('+', 'x').split('x')
                if len(parts) == 4:
                    w, h, l, t = map(lambda x: int(float(x)), parts)
                    self.page.window.width, self.page.window.height = w, h
                    self.page.window.left, self.page.window.top = l, t
            except Exception as e:
                logger.error(f"Error al aplicar la geometría: {e}")

    def cambiar_log_level(self, level):
        """
        Cambia el nivel de log global en tiempo de ejecución y lo persiste.

        Actualiza el logger raíz, guarda el nivel en el .ini y refresca
        la barra de aplicación.

        Args:
            level (str): Nivel de log: 'DEBUG', 'INFO', 'WARNING', 'ERROR' o 'CRITICAL'.
        """
        logging.getLogger().setLevel(getattr(logging, level))
        self.configuracion.app.log_level = level
        self.config_manager.guardar(self.configuracion)
        self.layout.refresh_appbar()

    async def close_app_handler(self, e=None):
        """
        Manejador asíncrono del cierre de la aplicación.

        Guarda la geometría actual de la ventana (posición y tamaño) en el
        fichero .ini, oculta la ventana, espera 200 ms para que Flet procese
        la ocultación y cierra el proceso limpiamente.

        Los errores durante el cierre se registran como DEBUG y se ignoran
        para no interrumpir la secuencia de salida.

        Args:
            e: Evento Flet (opcional, ignorado).
        """
        try:
            # Intentar guardar la geometría de la ventana
            try:
                w = int(self.page.window.width)
                h = int(self.page.window.height)
                l = int(self.page.window.left)
                t = int(self.page.window.top)
                self.configuracion.app.ventana = f"{w}x{h}+{l}+{t}"
                self.config_manager.guardar(self.configuracion)
            except Exception:
                pass

            # Ocultar ventana para feedback inmediato
            self.page.window.visible = False
            self.page.update()
            
            # Intentar cierre suave. 
            # IMPORTANTE: destroy() es una corrutina y necesita await.
            if hasattr(self.page.window, "destroy"):
                await self.page.window.destroy()
            else:
                await self.page.window.close()
                
        except Exception as ex:
            logger.debug(f"Error durante la secuencia de cierre: {ex}")
        finally:
            # Asegurar que el proceso muere SIEMPRE
            os._exit(0)
