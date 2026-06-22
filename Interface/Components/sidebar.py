import flet as ft
from ..Librerias import i18n

class Sidebar(ft.Container):
    """
    Panel lateral deslizable con todos los controles de filtrado.
    Ahora soporta la visualización de filtros generados dinámicamente.
    """

    def __init__(self, controller, layout):
        super().__init__()
        self.controller = controller
        self.layout = layout
        
        self.width = 250
        self.padding = 20
        self.border_radius = 10
        self._init_ui()

    def _init_ui(self):
        """Inicializa o reconstruye el contenido de la UI."""
        self.content = self._build()

    def _build(self):
        """
        Construye y devuelve el contenido completo del Sidebar.
        Ahora incluye el contenedor de filtros dinámicos.
        """
        return ft.Column(
            [
                ft.Column(
                    [
                        ft.Text(i18n.t("sidebar.filters"), size=20, weight=ft.FontWeight.BOLD),
                        ft.Divider(),
                        
                        ft.Text(i18n.t("menu.file"), weight=ft.FontWeight.BOLD),
                        ft.Row([
                            self.layout.btn_abrir,
                            self.layout.btn_reload,
                        ], spacing=4, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                        self.layout.format_dropdown,
                        self.layout.chk_auto_detect,
                        self.layout.progress_bar,
                        self.layout.selected_file_text,
                        self.layout.log_range_text,
                        ft.Divider(),

                        # Filtro de fecha/hora
                        self._build_expansion_tile(i18n.t("sidebar.date_time"), ft.Column([self.layout.start_controls, self.layout.end_controls])),

                        ft.Row([
                            ft.Text(f"{i18n.t('sidebar.filters')}:", weight=ft.FontWeight.BOLD),
                            self.layout.search_loading,
                        ], spacing=10),
                        ft.ElevatedButton(content=ft.Text(i18n.t("sidebar.clear_all")), on_click=self.controller.clear_filters, width=210),
                        
                        self.layout.chk_exclude_clear,
                        self.layout.chk_only_marked,

                        ft.ExpansionTile(
                            title=ft.Row([
                                ft.Icon(ft.Icons.SEARCH, size=18, color=ft.Colors.BLUE_400),
                                ft.Text(i18n.t("sidebar.free_filter"), weight=ft.FontWeight.BOLD),
                            ], spacing=10),
                            controls=[
                                ft.Column([
                                    self.layout.search_field,
                                    self.layout.search_mode_radio,
                                    ft.Row([
                                        self.layout.regex_checkbox,
                                        self.layout.sidebar_history_button
                                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                                ], spacing=8)
                            ],
                            controls_padding=10
                        ),

                        # Contenedor para los filtros dinámicos
                        self.layout.dynamic_filters_column,

                        # Estadísticas
                        self._build_expansion_tile(i18n.t("table.stats_title"), self.layout.stats_column),
                    ],
                    spacing=5,
                    scroll=ft.ScrollMode.AUTO,
                    expand=True
                ),
                ft.Row([self.layout.status_text]),
            ],
            spacing=0
        )

    def _build_expansion_tile(self, title, controls_col):
        """
        Crea un panel desplegable (ExpansionTile) con título y contenido.
        """
        tile = ft.ExpansionTile(
            title=ft.Text(title, weight=ft.FontWeight.BOLD),
            controls=[controls_col],
            controls_padding=10
        )
        return tile

    def refresh_ui(self):
        """
        Actualiza los textos de los elementos estáticos del Sidebar en memoria.
        NO llama a .update() — el caller es responsable del page.update() final.
        """
        try:
            # 1. Textos estáticos del sidebar (título, cabecera de archivo, etc.)
            main_col = self.content.controls[0]
            for ctrl in main_col.controls:
                # Textos directos
                if isinstance(ctrl, ft.Text):
                    if ctrl.size == 20:  # Título "Filtros"
                        ctrl.value = i18n.t("sidebar.filters")
                    elif ctrl.weight == ft.FontWeight.BOLD:  # Cabecera "Archivo"
                        ctrl.value = i18n.t("menu.file")

                # Fila de filtros activos ("Filtros:")
                elif isinstance(ctrl, ft.Row):
                    if ctrl.controls and isinstance(ctrl.controls[0], ft.Text):
                        val_str = str(ctrl.controls[0].value)
                        if "Filtros" in val_str or "Filters" in val_str:
                            ctrl.controls[0].value = f"{i18n.t('sidebar.filters')}:"

                # Botón Limpiar Filtros
                elif isinstance(ctrl, ft.ElevatedButton):
                    if ctrl.on_click == self.controller.clear_filters:
                        if isinstance(ctrl.content, ft.Text):
                            ctrl.content.value = i18n.t("sidebar.clear_all")
                        else:
                            ctrl.content = ft.Text(i18n.t("sidebar.clear_all"))

                # Paneles desplegables (ExpansionTile)
                elif isinstance(ctrl, ft.ExpansionTile):
                    # Fecha y Hora
                    if ctrl.controls and isinstance(ctrl.controls[0], ft.Column) and len(ctrl.controls[0].controls) > 0:
                        inner_ctrl = ctrl.controls[0].controls[0]
                        if inner_ctrl == self.layout.start_controls:
                            ctrl.title.value = i18n.t("sidebar.date_time")

                    # Filtro Libre
                    if isinstance(ctrl.title, ft.Row) and len(ctrl.title.controls) > 1:
                        ctrl.title.controls[1].value = i18n.t("sidebar.free_filter")

                    # Estadísticas
                    if ctrl.controls and ctrl.controls[0] == self.layout.stats_column:
                        ctrl.title.value = i18n.t("table.stats_title")

        except Exception as ex:
            import logging
            logging.getLogger(__name__).error(f"Error al actualizar idioma de la barra lateral: {ex}")