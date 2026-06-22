import flet as ft
import logging
from .Components.sidebar import Sidebar
from .Components.log_table import LogTable
from .Components.app_bar import MainAppBar
from .Librerias import i18n

logger = logging.getLogger(__name__)

class AppLayout:
    """
    Construye y gestiona la disposición visual principal de la aplicación.
    Soporta la creación dinámica de paneles de filtro.
    """

    def __init__(self, controller):
        self.controller = controller
        self.controller.layout = self
        self.page = controller.page
        
        self._init_controls()
        
        self.sidebar_comp = Sidebar(controller, self)
        self.table_comp = LogTable(controller, self)
        self.context_table_comp = LogTable(controller, self, is_context=True)
        self.context_table_comp.visible = False
        
        self.main_content_area = ft.Column(
            [
                self.table_comp,
                self.context_table_comp
            ],
            expand=True,
            spacing=0
        )
        
        self.refresh_appbar()

    def _init_controls(self):
        # State texts
        self.selected_file_text = ft.Text(i18n.t("sidebar.no_file"), size=12)
        self.log_range_text = ft.Text("", size=12)
        self.status_text = ft.Text("", size=12)

        # Progress bars
        self.progress_bar = ft.ProgressBar(visible=False, width=210)
        self.search_loading = ft.ProgressRing(width=20, height=20, visible=False)

        # Search field principal (Sidebar)
        self.search_field = ft.TextField(
            label=i18n.t("sidebar.search_placeholder"),
            on_submit=self.controller.on_search_submit,
            height=40, width=210, 
            text_size=12, 
            label_style=ft.TextStyle(size=12),
            content_padding=10, 
            filled=True,
            prefix_icon=ft.Icons.SEARCH,
        )

        self.regex_checkbox = ft.Checkbox(
            label=i18n.t("sidebar.regex"),
            on_change=self.controller.on_regex_change
        )

        self.search_mode_radio = ft.RadioGroup(
            content=ft.Row([
                ft.Radio(value="AND", label=i18n.t("sidebar.mode.and")),
                ft.Radio(value="OR", label=i18n.t("sidebar.mode.or")),
            ], spacing=20),
            value="AND",
            on_change=self.controller.on_search_mode_change,
        )

        self.chk_exclude_clear = ft.Checkbox(
            label=i18n.t("sidebar.exclude_clear"),
            value=True,
            on_change=self.controller.on_exclude_clear_change
        )

        self.chk_only_marked = ft.Checkbox(
            label=i18n.t("sidebar.marked_only"),
            on_change=self.controller.on_only_marked_change
        )

        # CONTENEDOR DE FILTROS DINÁMICOS
        self.dynamic_filters_column = ft.Column(spacing=0)

        # Date/Time Pickers
        self.date_picker_start = ft.DatePicker(on_change=self.controller.on_date_change_start)
        self.date_picker_end = ft.DatePicker(on_change=self.controller.on_date_change_end)
        self.time_picker_start = ft.TimePicker(on_change=self.controller.on_time_change_start)
        self.time_picker_end = ft.TimePicker(on_change=self.controller.on_time_change_end)
        self.page.overlay.extend([self.date_picker_start, self.date_picker_end, self.time_picker_start, self.time_picker_end])

        # Date/Time Labels
        self.start_date_label = ft.Text(i18n.t("sidebar.no_filter"), size=10, italic=True, color=ft.Colors.GREY_600)
        self.end_date_label = ft.Text(i18n.t("sidebar.no_filter"), size=10, italic=True, color=ft.Colors.GREY_600)

        def open_dp(dp):
            dp.open = True
            self.page.update()

        self.btn_date_start = ft.IconButton(icon=ft.Icons.DATE_RANGE, on_click=lambda _: open_dp(self.date_picker_start))
        self.btn_time_start = ft.IconButton(icon=ft.Icons.ACCESS_TIME, on_click=lambda _: open_dp(self.time_picker_start))
        self.btn_date_end = ft.IconButton(icon=ft.Icons.DATE_RANGE, on_click=lambda _: open_dp(self.date_picker_end))
        self.btn_time_end = ft.IconButton(icon=ft.Icons.ACCESS_TIME, on_click=lambda _: open_dp(self.time_picker_end))

        self.start_controls = ft.Column([
            ft.Row([ft.Text(f"{i18n.t('sidebar.start')}:", weight="bold", size=12, width=50), self.btn_date_start, self.btn_time_start]),
            self.start_date_label
        ], spacing=0)

        self.end_controls = ft.Column([
            ft.Row([ft.Text(f"{i18n.t('sidebar.end')}:", weight="bold", size=12, width=50), self.btn_date_end, self.btn_time_end]),
            self.end_date_label
        ], spacing=0)

        self.stats_column = ft.Column(spacing=5, tight=True)

        from Model.formats import load_all_formats
        available_formats = load_all_formats()
        options = [ft.dropdown.Option(key=fmt.id, text=fmt.name) for fmt in available_formats.values()]
        
        self.format_dropdown = ft.Dropdown(
            label=i18n.t("menu.log_format"), width=210, options=options, value="rtp_osv",
            height=46, text_size=11, content_padding=5,
        )
        self.format_dropdown.on_change = self.controller.on_format_change
        
        self.chk_auto_detect = ft.Checkbox(label=i18n.t("menu.auto_detect"), value=True)
        self.chk_auto_detect.on_change = self.controller.on_auto_detect_change

        # Inicialización de botones de archivo
        self._init_file_buttons()

        self.empty_message = ft.Text(i18n.t("msg.no_matches_filters"), size=14, italic=True, color=ft.Colors.GREY_500, visible=False, text_align=ft.TextAlign.CENTER)

        self.goto_line_field = ft.TextField(
            label=i18n.t("dialog.goto.title"), width=90, height=30, text_size=12, content_padding=5,
            on_submit=self.controller.goto_line, keyboard_type=ft.KeyboardType.NUMBER,
            input_filter=ft.InputFilter(allow=True, regex_string=r"^[0-9]*$", replacement_string=""),
        )
        self.sidebar_history_button = ft.PopupMenuButton(icon=ft.Icons.HISTORY, visible=True, width=40)
        
        # Cache de controles de filtro dinámica: {col_name: {label: Checkbox}}
        self.filter_controls = {}

    def _init_file_buttons(self):
        """Inicializa o actualiza los botones de abrir y recargar archivo."""
        if hasattr(self, 'btn_abrir') and self.btn_abrir:
            if isinstance(self.btn_abrir.content, ft.Text):
                self.btn_abrir.content.value = i18n.t("menu.open")
            else:
                self.btn_abrir.content = ft.Text(i18n.t("menu.open"))
            self.btn_reload.tooltip = i18n.t("menu.reload")
            try:
                self.btn_abrir.update()
                self.btn_reload.update()
            except Exception: pass
        else:
            self.btn_abrir = ft.ElevatedButton(content=ft.Text(i18n.t("menu.open")), icon=ft.Icons.FOLDER_OPEN, on_click=self.controller.open_file_dialog, width=162)
            self.btn_reload = ft.IconButton(icon=ft.Icons.REFRESH, tooltip=i18n.t("menu.reload"), on_click=self.controller.reload_file, disabled=True, icon_color=ft.Colors.BLUE_400)

    def refresh_appbar(self, do_update: bool = True):
        self.page.appbar = MainAppBar(self.controller)
        if do_update:
            self.page.update()

    def refresh_sidebar(self):
        """Actualiza los textos del sidebar sin hacer update propio; el caller debe hacer page.update()."""
        self.sidebar_comp.refresh_ui()

    def toggle_sidebar(self, e=None):
        """Alterna la visibilidad del panel lateral (Sidebar)."""
        self.sidebar_comp.visible = not self.sidebar_comp.visible
        self.sidebar_comp.update()

    def refresh_controls(self):
        self.selected_file_text.value = f"{i18n.t('menu.file')}: {self.controller.app_state.last_file_name}" if self.controller.app_state.last_file_name else i18n.t("sidebar.no_file")
        self.search_field.label = i18n.t("sidebar.search_placeholder")
        self.regex_checkbox.label = i18n.t("sidebar.regex")
        self.search_mode_radio.content.controls[0].label = i18n.t("sidebar.mode.and")
        self.search_mode_radio.content.controls[1].label = i18n.t("sidebar.mode.or")
        self.chk_exclude_clear.label = i18n.t("sidebar.exclude_clear")
        self.chk_only_marked.label = i18n.t("sidebar.marked_only")
        
        self.start_date_label.value = i18n.t("sidebar.no_filter") if not self.controller.app_state.start_date else self.start_date_label.value
        self.end_date_label.value = i18n.t("sidebar.no_filter") if not self.controller.app_state.end_date else self.end_date_label.value
        self.start_controls.controls[0].controls[0].value = f"{i18n.t('sidebar.start')}:"
        self.end_controls.controls[0].controls[0].value = f"{i18n.t('sidebar.end')}:"
        
        self.btn_abrir.text = i18n.t("menu.open")
        self.btn_reload.tooltip = i18n.t("menu.reload")
        try:
            self.btn_abrir.update()
            self.btn_reload.update()
        except Exception: pass
        
        # Forzar la actualización del contenedor padre para que los nuevos botones se muestren
        if self.sidebar_comp.page: # Asegurarse de que el sidebar ya está montado
            self.sidebar_comp.update()
        
        self.empty_message.value = i18n.t("msg.no_matches_filters")
        self.goto_line_field.label = i18n.t("dialog.goto.title")
        self.format_dropdown.label = i18n.t("menu.log_format")
        self.chk_auto_detect.label = i18n.t("menu.auto_detect")
        
        # Eliminar el argumento 'should_update' de la llamada a refresh_ui
        self.table_comp.refresh_ui()
        self.context_table_comp.refresh_ui()
        
        # En vez de actualizar toda la tabla (que recrea o actualiza todos los controles visuales pesados),
        # solo actualizamos los encabezados y la paginación. Las filas de datos actuales no cambian su contenido
        # de texto dinámico de traducción ya que son líneas de logs del archivo.
        self.controller.dialogs.refresh_ui()
        self.page.update()

    def build(self):
        return ft.Row([self.sidebar_comp, self.main_content_area], expand=True, vertical_alignment=ft.CrossAxisAlignment.STRETCH)

    def update_stats(self, stats):
        self.stats_column.controls.clear()
        self.stats_column.controls.append(ft.Text(i18n.t("table.stats", total=stats.get('total', 0), filtered=stats.get('filtered', 0)), size=12, weight="bold"))
        self.stats_column.controls.append(ft.Divider(height=10))
        
        levels = stats.get('by_level', {})
        total_filtered = stats.get('filtered', 0)
        sorted_levels = sorted(levels.items(), key=lambda x: x[1], reverse=True)
        
        for level, count in sorted_levels:
            if count == 0: continue
            color = self._get_level_color(level)
            percentage = (count / total_filtered * 100) if total_filtered > 0 else 0
            self.stats_column.controls.append(ft.Row([ft.Container(bgcolor=color, width=10, height=10, border_radius=5), ft.Text(f"{level}: {count} ({percentage:.1f}%)", size=11, expand=True)]))
            self.stats_column.controls.append(ft.ProgressBar(value=percentage/100, color=color, bgcolor=ft.Colors.GREY_300, height=4, border_radius=2))
        self.stats_column.update()

    def _get_level_color(self, level):
        lvl = str(level).upper()
        if any(x in lvl for x in ["CRIT", "EMERG", "FATAL"]): return ft.Colors.RED_900
        if any(x in lvl for x in ["ERROR", "FAIL", "MAJOR", "MAYOR"]): return ft.Colors.RED_500
        if any(x in lvl for x in ["WARN", "MINOR", "MENOR"]): return ft.Colors.AMBER_600
        if "INFO" in lvl: return ft.Colors.BLUE_500
        if "DEBUG" in lvl: return ft.Colors.PURPLE_400
        if "CLEAR" in lvl: return ft.Colors.GREY_500
        return ft.Colors.GREEN_500

    def crear_filtros_iniciales(self, unique_data: dict):
        """
        Crea dinámicamente los paneles de filtro basándose en los datos únicos del log.
        """
        self.filter_controls = {}
        self.dynamic_filters_column.controls.clear()
        
        translation_map = {
            "nivel": i18n.t("sidebar.levels"),
            "evento": i18n.t("sidebar.events"),
            "proceso": i18n.t("sidebar.processes"),
            "notas": i18n.t("sidebar.notes")
        }

        for col_name, values in unique_data.items():
            if not values: continue
            
            self.filter_controls[col_name] = {
                str(v): ft.Checkbox(label=str(v), value=False, data=col_name, on_change=self.controller.ui_actions.on_dynamic_filter_change)
                for v in values
            }
            
            col_checkboxes = ft.Column(list(self.filter_controls[col_name].values()), scroll=ft.ScrollMode.AUTO)
            
            # Campo de búsqueda interno de cada panel de filtro
            search_field = ft.TextField(
                label=f"{i18n.t('btn.search')} {col_name}...", 
                height=40, 
                text_size=12,
                label_style=ft.TextStyle(size=12),
                content_padding=10,
                filled=True,
                on_change=self.controller.ui_actions.on_dynamic_filter_search_change, 
                data=col_name
            )
            
            title = translation_map.get(col_name, col_name.capitalize())
            panel = ft.ExpansionTile(
                title=ft.Text(title, weight=ft.FontWeight.BOLD),
                controls=[ft.Column([search_field, ft.Container(col_checkboxes, height=200)])],
                controls_padding=10
            )
            self.dynamic_filters_column.controls.append(panel)
        
        self.dynamic_filters_column.update()

    def regenerar_checkboxes(self, col_name=None, query=""):
        if col_name not in self.filter_controls: return

        q = query.lower()
        for label, cb in self.filter_controls[col_name].items():
            cb.visible = q in label.lower()
        
        self.dynamic_filters_column.update()
