# Interface/Logic/file_manager.py
"""
Responsabilidad única: gestionar el diálogo de selección de ficheros y actualizar
la UI durante y después de la carga.

La lógica de carga de datos pura está en DataService.
"""
import flet as ft
import logging
from ..Core import i18n
from .data_service import DataService

logger = logging.getLogger(__name__)


class FileManager:
    """
    Gestiona el diálogo de apertura/recarga de ficheros y la retroalimentación visual.

    Responsabilidades:
    - Abrir el FilePicker y recoger la ruta seleccionada.
    - Mostrar progreso y mensajes de estado en la UI.
    - Actualizar los controles de UI tras una carga exitosa.
    - Delegar la carga real de datos a DataService.
    """

    def __init__(self, page: ft.Page, app_state, layout, configuracion, config_manager, picker, controller):
        self.page = page
        self.app_state = app_state
        self.layout = layout
        self.configuracion = configuracion
        self.config_manager = config_manager
        self.picker = picker
        self.controller = controller
        self._data_service = DataService(app_state)

    # ── Compatibilidad: delega operaciones de marcas al DataService ──────────
    def save_marks(self) -> None:
        self._data_service.save_marks()

    def load_marks(self, file_path: str) -> None:
        self._data_service.load_marks(file_path)

    # ── Diálogos de fichero ──────────────────────────────────────────────────
    async def open_file_dialog(self, e=None):
        """Abre el diálogo de selección de fichero y carga el seleccionado."""
        initial_directory = str(self.configuracion.app.dir_ini)
        result = await self.picker.pick_files(
            allowed_extensions=["txt", "log"],
            dialog_title=i18n.t("menu.open"),
            initial_directory=initial_directory
        )
        if result:
            await self._cargar_con_ui(result[0].path, result[0].name)

    async def reload_file(self, e=None):
        """Recarga el último fichero abierto."""
        if self.app_state.last_file_path:
            await self._cargar_con_ui(
                self.app_state.last_file_path,
                self.app_state.last_file_name
            )

    # ── Carga con feedback de UI ─────────────────────────────────────────────
    async def _cargar_con_ui(self, file_path: str, file_name: str):
        """Orquesta la carga mostrando progreso y actualizando la UI al terminar."""
        from pathlib import Path
        import os
        try:
            self.layout.progress_bar.visible = True
            self.page.update()

            ok = await self._data_service.load_file(file_path, file_name)

            if ok:
                formato = self.app_state.active_format
                det_suffix = " (Auto-detectado)" if self.app_state.auto_detect_format else ""
                self.layout.status_text.value = f"Formato: {formato.name}{det_suffix}"

                # Sincronizar el desplegable de formato en la UI
                if hasattr(self.layout, "format_dropdown") and self.layout.format_dropdown:
                    self.layout.format_dropdown.value = formato.id
                    try:
                        self.layout.format_dropdown.update()
                    except Exception:
                        pass

                # Actualizar rango temporal si hay datos
                if not self.app_state.df.empty:
                    ts = self.app_state.df['timestamp']
                    self.layout.log_range_text.value = (
                        f"{i18n.t('sidebar.start')}: {ts.iloc[0]}\n"
                        f"{i18n.t('sidebar.end')}:    {ts.iloc[-1]}"
                    )

                self.configuracion.app.dir_ini = Path(os.path.dirname(file_path))
                self.config_manager.guardar(self.configuracion)

                self.layout.selected_file_text.value = f"{i18n.t('menu.file')}: {file_name}"
                self.layout.btn_reload.disabled = False

                self.controller._reset_ui_after_load()
            else:
                self.layout.status_text.value = i18n.t("msg.error")

        except Exception as ex:
            self.layout.status_text.value = f"{i18n.t('msg.error')}: {ex}"
            logger.error(f"Error en _cargar_con_ui: {ex}", exc_info=True)
        finally:
            self.layout.progress_bar.visible = False
            try:
                self.layout.status_text.update()
            except Exception:
                pass
            self.page.update()
