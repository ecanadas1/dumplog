import flet as ft
import asyncio
import os
import logging
import threading
from typing import Optional
from .state import AppState
from .app_layout import AppLayout
from .Logic.filter_manager import FilterManager
from .Logic.export_manager import ExportManager
from .Logic.dialogs import Dialogs
from .Logic.selection_manager import SelectionManager
from .Logic.table_renderer import TableRenderer
from .Logic.file_manager import FileManager
from .Logic.system_manager import SystemManager
from .Logic.ui_action_manager import UIActionManager
from .Librerias.config_manager import ConfigManager
from .Librerias.app_settings import AppSettings, Version
from .Librerias import i18n
from Model.log_parser import LogParser

logger = logging.getLogger(__name__)

class Manager:
    """Controlador principal de la aplicación (patrón MVC)."""

    def __init__(self, page: ft.Page, config_manager: ConfigManager, configuracion: AppSettings, metadata: Version):
        self.page = page
        self.config_manager = config_manager
        self.configuracion = configuracion
        self.metadata = metadata
        
        i18n.load(self.configuracion.app.idioma)
        
        self.page.title = metadata.title
        icon_path = self._get_resource_path("assets/icon.ico")
        if os.path.exists(icon_path):
            self.page.window.icon = icon_path
            self.page.icon = "icon.ico" 
        
        self.page.window.min_width, self.page.window.min_height = 900, 750
        self.page.locale_configuration = ft.LocaleConfiguration(
            current_locale=ft.Locale(self.configuracion.app.idioma, "US" if self.configuracion.app.idioma == 'en' else "ES"),
            supported_locales=[ft.Locale("es", "ES"), ft.Locale("en", "US")],
        )

        self.app_state = AppState()
        from Model.formats import load_all_formats
        self._formatos_disponibles = load_all_formats()
        self.app_state.active_format = self._formatos_disponibles.get("rtp_osv")

        self.app_state.syntax_highlighting = self.configuracion.app.resaltado_sintaxis
        self.app_state.page_size = self.configuracion.app.page_size_default
        self.app_state.context_range = self.configuracion.app.context_range

        self._debounce_task = None
        self._filter_controls_debounce_task = None
        self._current_filter_field = None 
        self._is_filtering = False
        self._needs_refilter = False
        self._ui_lock = threading.RLock() 

        # Managers
        from .Logic.navigation_manager import NavigationManager
        from .Logic.clipboard_service import ClipboardService
        
        self.dialogs = Dialogs(self)
        self.layout = AppLayout(self)
        self.table_renderer = TableRenderer(self.page, self.app_state, self.layout, self.on_row_click, self)
        self.selection_mgr = SelectionManager(self.page, self.app_state, self.layout, self)
        self.navigation_mgr = NavigationManager(self)
        self.clipboard_svc = ClipboardService(self)
        
        self.picker = ft.FilePicker()
        if hasattr(self.page, "services") and self.picker not in self.page.services:
            self.page.services.append(self.picker)
        elif self.picker not in self.page.overlay:
            self.page.overlay.append(self.picker)
        
        self.file_mgr = FileManager(page, self.app_state, self.layout, configuracion, config_manager, self.picker, self)
        self.system_mgr = SystemManager(page, configuracion, config_manager, self.layout)
        self.export_mgr = ExportManager(page, self.app_state, self.layout, self.picker)
        self.filter_mgr = FilterManager(self.app_state)
        self.ui_actions = UIActionManager(self)

        self.system_mgr.apply_geometry()
        self.system_mgr.apply_theme()
        
        self.page.add(self.layout.build())
        self.page.window.prevent_close = True
        self.page.on_window_event = self.on_window_event
        self.page.update()
        LogParser.load_rules()
        self.refresh_history_ui()

    def _get_resource_path(self, relative_path: str) -> str:
        import sys
        if hasattr(sys, '_MEIPASS'):
            return os.path.join(sys._MEIPASS, relative_path)
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(base_path, relative_path)

    def cambiar_tema(self, mode): self.system_mgr.cambiar_tema(mode)
    def cambiar_log_level(self, level): self.system_mgr.cambiar_log_level(level)

    async def close_app_handler(self, e):
        self.file_mgr.save_marks()
        await self.system_mgr.close_app_handler(e)
    
    async def on_window_event(self, e):
        if e.data == "close": await self.close_app_handler(None)

    def cambiar_page_size_default(self, size: int):
        self.configuracion.app.page_size_default = size
        self.config_manager.guardar(self.configuracion)
        self.app_state.page_size = size
        self.app_state.current_page = 1
        if self.layout and self.layout.page_size_dropdown:
            self.layout.page_size_dropdown.value = str(size)
            self.layout.page_size_dropdown.update()
        self.refresh_table()
        self.layout.refresh_appbar()

    def cambiar_context_range(self, range_val: int):
        """Cambia el rango de líneas de la vista de contexto y lo guarda."""
        self.configuracion.app.context_range = range_val
        self.config_manager.guardar(self.configuracion)
        self.app_state.context_range = range_val
        
        if hasattr(self.layout, 'context_title') and self.layout.context_title:
            self.layout.context_title.value = i18n.t("table.context_title", range=range_val)
            self.layout.context_title.update()

        # Si la vista de contexto está abierta, refrescarla para aplicar el nuevo rango
        if self.app_state.context_mode and self.app_state.context_line is not None:
            self.show_context_view(self.app_state.context_line)
        self.layout.refresh_appbar()

    def cambiar_idioma(self, lang: str):
        """Cambia el idioma de la interfaz de forma eficiente, sin recargar datos de la tabla."""
        async def _cambiar_idioma_async():
            try:
                i18n.load(lang)
                self.configuracion.app.idioma = lang
                self.config_manager.guardar(self.configuracion)
                self.page.locale_configuration.current_locale = ft.Locale(lang, "US" if lang == 'en' else "ES")

                # 1. Reconstruir AppBar + actualizar todos los textos en un único page.update()
                self.layout.refresh_appbar(do_update=False)

                # 2. Actualizar solo los textos del sidebar y controles de la UI,
                #    SIN tocar los datos de la tabla para evitar congelamientos.
                self._refresh_ui_texts_only()

            except Exception as ex:
                logger.error(f"Error al cambiar idioma: {ex}")

        self.page.run_task(_cambiar_idioma_async)

    def _refresh_ui_texts_only(self):
        """
        Actualiza los textos de la interfaz sin regenerar ni tocar los datos de la tabla.
        Un único page.update() al final para evitar parpadeos y congelamientos.
        """
        l = self.layout

        # Botones de archivo (los problemáticos)
        new_text = i18n.t("menu.open")
        logger.debug(f"[IDIOMA] btn_abrir.page={l.btn_abrir.page is not None}, text_antes='{l.btn_abrir.content.value if isinstance(l.btn_abrir.content, ft.Text) else l.btn_abrir.content}', text_nuevo='{new_text}'")
        if isinstance(l.btn_abrir.content, ft.Text):
            l.btn_abrir.content.value = new_text
        else:
            l.btn_abrir.content = ft.Text(new_text)
        l.btn_reload.tooltip = i18n.t("menu.reload")

        # Controles del sidebar
        l.search_field.label = i18n.t("sidebar.search_placeholder")
        l.regex_checkbox.label = i18n.t("sidebar.regex")
        l.search_mode_radio.content.controls[0].label = i18n.t("sidebar.mode.and")
        l.search_mode_radio.content.controls[1].label = i18n.t("sidebar.mode.or")
        l.chk_exclude_clear.label = i18n.t("sidebar.exclude_clear")
        l.chk_only_marked.label = i18n.t("sidebar.marked_only")
        l.chk_auto_detect.label = i18n.t("menu.auto_detect")
        l.format_dropdown.label = i18n.t("menu.log_format")
        l.empty_message.value = i18n.t("msg.no_matches_filters")
        l.goto_line_field.label = i18n.t("dialog.goto.title")

        # Etiquetas de fecha/hora
        if not self.app_state.start_date:
            l.start_date_label.value = i18n.t("sidebar.no_filter")
        if not self.app_state.end_date:
            l.end_date_label.value = i18n.t("sidebar.no_filter")
        l.start_label.value = f"{i18n.t('sidebar.start')}:"
        l.end_label.value   = f"{i18n.t('sidebar.end')}:"

        # Texto del archivo seleccionado
        l.selected_file_text.value = (
            f"{i18n.t('menu.file')}: {self.app_state.last_file_name}"
            if self.app_state.last_file_name else i18n.t("sidebar.no_file")
        )

        # Textos estáticos dentro del sidebar (título "Filtros", cabecera "Archivo", etc.)
        l.refresh_sidebar()

        # Encabezados de la tabla (solo textos, sin recargar filas)
        l.table_comp.update_header_text_for_language()
        l.context_table_comp.update_header_text_for_language()

        # Paginación y tooltips de la tabla principal
        l.table_comp.refresh_ui()
        l.context_table_comp.refresh_ui()

        # Filtros dinámicos (solo títulos de paneles)
        translation_map = {
            "nivel": i18n.t("sidebar.levels"),
            "evento": i18n.t("sidebar.events"),
            "proceso": i18n.t("sidebar.processes"),
            "notas": i18n.t("sidebar.notes")
        }
        for col_name, title_text in l.filter_panel_title_texts.items():
            title_text.value = translation_map.get(col_name, col_name.capitalize())
        for col_name, search_field in l.filter_search_fields.items():
            search_field.label = f"{i18n.t('btn.search')} {col_name}..."

        # Diálogos
        self.dialogs.refresh_ui()
        self.refresh_history_ui()

        # Update global + forzar update individual de los botones problemáticos
        self.page.update()
        try:
            l.btn_abrir.update()
            l.btn_reload.update()
            logger.debug(f"[IDIOMA] btn_abrir.update() OK, text='{l.btn_abrir.content.value if isinstance(l.btn_abrir.content, ft.Text) else l.btn_abrir.content}'")
        except Exception as ex:
            logger.error(f"[IDIOMA] Error en btn_abrir.update(): {ex}")

    async def open_file_dialog(self, e): await self.file_mgr.open_file_dialog(e)
    async def reload_file(self, e): await self.file_mgr.reload_file(e)

    def on_format_change(self, e):
        fmt_id = self.layout.format_dropdown.value
        formato = self._formatos_disponibles.get(fmt_id)
        if formato:
            self.app_state.active_format = formato
            logger.info(f"Formato activo cambiado a: {formato.name}")

    def on_auto_detect_change(self, e):
        self.app_state.auto_detect_format = self.layout.chk_auto_detect.value

    def _reset_ui_after_load(self):
        """Restablece la interfaz tras cargar un nuevo fichero con datos DINÁMICOS."""
        self._reset_filters_ui()
        self._reset_date_filters_ui()
        self.layout.refresh_appbar()
        self.layout.crear_filtros_iniciales(self.app_state.unique_values)
        if hasattr(self.layout.table_comp, "update_columns"):
            self.layout.table_comp.update_columns()
        if hasattr(self.layout.context_table_comp, "update_columns"):
            self.layout.context_table_comp.update_columns()
        self.apply_filters()

    async def _exportar_datos(self, e, formato: str):
        await self.export_mgr.exportar_datos(formato)

    def refresh_table(self): 
        self.table_renderer.refresh_table()
        if self.app_state.context_mode:
            self.refresh_context_table(auto_scroll=False)
        self.update_selection_info()

    def refresh_context_table(self, auto_scroll=True):
        self.table_renderer.refresh_context_table(auto_scroll=auto_scroll)

    def show_context_view(self, line_num):
        df = self.app_state.df
        if df.empty: return
        try:
            idx = df[df['linea'].astype(int) == int(line_num)].index[0]
            ctx_range = self.app_state.context_range
            start_idx = max(0, idx - ctx_range)
            end_idx = min(len(df), idx + ctx_range + 1)
            self.app_state.context_df = df.iloc[start_idx:end_idx]
            self.app_state.context_line = int(line_num)
            self.app_state.context_mode = True
            self.layout.context_table_comp.visible = True
            self.layout.main_content_area.update()
            self.refresh_context_table()
        except Exception as e:
            logger.error(f"Error al mostrar contexto: {e}")

    def close_context_view(self, e=None):
        self.app_state.context_mode = False
        self.app_state.context_line = None
        self.app_state.context_df = self.app_state.df.iloc[0:0]
        self.layout.context_table_comp.visible = False
        self.layout.main_content_area.update()

    def update_selection_info(self):
        if not self.layout.selection_info: return
        selected = self.app_state.selected_lines
        if not selected:
            self.layout.selection_info.value = ""
        else:
            try:
                df = self.app_state.filtered_df
                all_selected = df[df['linea'].astype(int).isin(selected)]['linea'].tolist()
                total_in_view = len(all_selected)
                if self.app_state.last_selected_line in all_selected:
                    idx = all_selected.index(self.app_state.last_selected_line) + 1
                    self.layout.selection_info.value = i18n.t("table.selection_info", idx=idx, total=total_in_view)
                else:
                    self.layout.selection_info.value = i18n.t("table.selection_info_total", total=total_in_view)
            except Exception:
                self.layout.selection_info.value = i18n.t("table.selection_info_total", total=len(selected))
        try: self.layout.selection_info.update()
        except Exception: pass

    def refresh_selection_visuals(self): 
        self.table_renderer.update_row_colors()
        self.update_selection_info()

    def toggle_mark_all_on_page(self, e, is_context=False):
        self.table_renderer.toggle_mark_all_on_page(e, is_context)

    def update_filter_controls(self, target_filter: Optional[str] = None):
        if not target_filter: return
        query = self.app_state.internal_search_queries.get(target_filter, "")
        self.layout.regenerar_checkboxes(target_filter, query)

    def toggle_mode_multi(self, e): self.selection_mgr.toggle_mode_multi(e)
    def toggle_mode_range(self, e): self.selection_mgr.toggle_mode_range(e)
    def on_row_click(self, e, line_num): self.selection_mgr.on_row_click(e, line_num)
    async def copy_selected_lines(self, e=None): await self.clipboard_svc.copy_selected_lines(e)
    def select_all_on_page(self, e=None): self.selection_mgr.select_all_on_page(e)
    def open_search_selection_dialog(self, e=None): self.dialogs.open_search_selection(e)
    async def select_by_search(self, query: str): await self.clipboard_svc.select_by_search(query)
    def mark_selected(self, e=None): self.selection_mgr.mark_selected_lines(True)
    def unmark_selected(self, e=None): self.selection_mgr.mark_selected_lines(False)

    def apply_filters(self):
        if self._is_filtering:
            self._needs_refilter = True
            return
        self._is_filtering = True
        self._needs_refilter = False
        if not self.layout.search_loading.visible:
            self.layout.search_loading.visible = True
            self.layout.search_loading.update()
        self.app_state.current_page = 1
        self.app_state.selected_lines.clear()
        self.app_state.last_selected_line = None
        self.selection_mgr.set_mode(multi=False, rango=False)
        self.page.run_thread(self._apply_filters_thread_safe)

    def _apply_filters_thread_safe(self):
        """
        Ejecuta únicamente el cómputo puro (filtrado pandas) en el hilo secundario.

        Toda actualización de UI se despacha al event-loop de Flet mediante
        page.run_task() para garantizar thread-safety. De este modo:
          - El hilo secundario nunca toca controles de Flet directamente.
          - El flag _is_filtering y la comprobación de _needs_refilter ocurren
            DENTRO del callback async, una vez la UI ya ha sido actualizada.
        """
        stats = None
        error_occurred = False
        try:
            self.filter_mgr.apply_filters(self.layout.chk_exclude_clear.value)
            stats = self.filter_mgr.calculate_statistics()
        except Exception as e:
            logger.error(f"Error filtrando: {e}")
            error_occurred = True

        # Capturar en closure — evita race conditions si el estado cambia antes
        # de que el event-loop ejecute el callback.
        _stats = stats
        _error = error_occurred

        async def _post_filter_ui_update():
            """Todas las actualizaciones de UI en el event-loop de Flet."""
            try:
                if not _error:
                    try:
                        if self.app_state.use_regex:
                            self.layout.search_field.error_text = (
                                "Regex inválida" if self.app_state.regex_error else None
                            )
                            self.layout.search_field.update()
                    except Exception:
                        pass
                    if _stats is not None:
                        self.layout.update_stats(_stats)
                self.layout.search_loading.visible = False
                self.refresh_table()
            finally:
                # Resetear el flag y relanzar si se solicitó un nuevo filtrado
                # mientras este estaba en curso.
                self._is_filtering = False
                if self._needs_refilter:
                    self.page.run_thread(self.apply_filters)

        self.page.run_task(_post_filter_ui_update)


    def _reset_filters_ui(self):
        self.app_state.reset_filters()
        l = self.layout
        l.search_field.value = ""
        l.search_mode_radio.value = "AND"
        l.regex_checkbox.value = False
        l.chk_only_marked.value = False
        
        if hasattr(l, 'filter_controls'):
            for col_controls in l.filter_controls.values():
                for cb in col_controls.values():
                    cb.value = False
                    cb.visible = True
            try: l.dynamic_filters_column.update()
            except Exception: pass

        self._update_date_labels_ui()

    def _reset_date_filters_ui(self):
        self.app_state.start_date = self.app_state.end_date = None
        self.app_state.start_time = self.app_state.end_time = None
        self.layout.date_picker_start.value = self.layout.date_picker_end.value = None
        self.layout.time_picker_start.value = self.layout.time_picker_end.value = None
        self._update_date_labels_ui()

    def _trigger_debounced_filter(self, reason: str):
        self.ui_actions.trigger_debounced_filter(reason)

    def _update_date_labels_ui(self):
        def fmt(d): 
            if not d: return i18n.t("sidebar.no_filter")
            if hasattr(d, "tzinfo") and d.tzinfo is not None: d = d.astimezone(None)
            return d.strftime('%Y-%m-%d')
        def fmt_t(t): return t.strftime('%H:%M') if t else ""
        self.layout.start_date_label.value = f"{fmt(self.app_state.start_date)} {fmt_t(self.app_state.start_time)}"
        self.layout.end_date_label.value = f"{fmt(self.app_state.end_date)} {fmt_t(self.app_state.end_time)}"
        self.page.update()

    def on_search_submit(self, e): self.ui_actions.on_search_submit(e)
    def _on_sidebar_history_click(self, e): self.ui_actions._on_sidebar_history_click(e)
    def change_page(self, e, delta=0, first=False, last=False): self.ui_actions.change_page(e, delta, first, last)
    def on_page_size_change(self, e): self.ui_actions.on_page_size_change(e)
    def on_level_change(self, e): self.ui_actions.on_level_change(e)
    def on_event_change(self, e): self.ui_actions.on_event_change(e)
    def on_process_change(self, e): self.ui_actions.on_process_change(e)
    def on_note_change(self, e): self.ui_actions.on_note_change(e)
    def on_exclude_clear_change(self, e): self.ui_actions.on_exclude_clear_change(e)
    def on_only_marked_change(self, e): self.ui_actions.on_only_marked_change(e)
    def on_search_mode_change(self, e): self.ui_actions.on_search_mode_change(e)
    def on_filter_search_change(self, e): self.ui_actions.on_filter_search_change(e)
    def on_date_change_start(self, e): self.ui_actions.on_date_change_start(e)
    def on_date_change_end(self, e): self.ui_actions.on_date_change_end(e)
    def on_time_change_start(self, e): self.ui_actions.on_time_change_start(e)
    def on_time_change_end(self, e): self.ui_actions.on_time_change_end(e)
    def on_search_change(self, e): self.ui_actions.on_search_change(e)
    def on_regex_change(self, e): self.ui_actions.on_regex_change(e)
    def on_clear_filters(self, e): self.ui_actions.on_clear_filters(e)

    async def _debounce_update_filter_controls(self):
        try:
            await asyncio.sleep(0.3)
            self.update_filter_controls(target_filter=self._current_filter_field)
            self._current_filter_field = None
        except asyncio.CancelledError: pass

    def toggle_mark(self, e, line_num):
        ln = int(line_num)
        if ln in self.app_state.marked_lines: self.app_state.marked_lines.discard(ln)
        else: self.app_state.marked_lines.add(ln)
        if self.app_state.show_only_marked: self._trigger_debounced_filter("toggle_mark")
        else: self.refresh_table()
        self.page.update()

    def toggle_syntax_highlighting(self, e):
        self.app_state.syntax_highlighting = not self.app_state.syntax_highlighting
        self.configuracion.app.resaltado_sintaxis = self.app_state.syntax_highlighting
        self.config_manager.guardar(self.configuracion)
        self.refresh_table()
        self.layout.refresh_appbar()

    def clear_filters(self):
        self._reset_filters_ui()
        self.apply_filters()
    
    async def goto_line(self, e): await self.navigation_mgr.goto_line(e)
    async def goto_next_marked(self, e): await self.navigation_mgr.navigate_marked(1)
    async def goto_prev_marked(self, e): await self.navigation_mgr.navigate_marked(-1)
    async def _jump_to_line(self, line_num: int): await self.navigation_mgr.jump_to_line(line_num)

    def refresh_history_ui(self):
        history = self.configuracion.app.historial_busqueda
        if history:
            items = [ft.PopupMenuItem(content=ft.Text(h), data=h, on_click=self._on_sidebar_history_click) for h in history]
            self.layout.sidebar_history_button.items = items
        else:
            self.layout.sidebar_history_button.items = [ft.PopupMenuItem(content=ft.Text(i18n.t("sidebar.no_history", default="Sin historial...")))]
        try: self.layout.sidebar_history_button.update()
        except Exception: pass
