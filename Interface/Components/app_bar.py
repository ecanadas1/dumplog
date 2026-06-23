import flet as ft
from ..Librerias import i18n

class MainAppBar(ft.AppBar):
    """
    Barra de aplicación principal de la ventana.

    Contiene:
      - Botón de menú (hamburguesa) para mostrar/ocultar el sidebar.
      - Título con el nombre de la app y los botones de selección/copia.
      - Menús desplegables de Exportar, Configuración y Ayuda.
    """

    def __init__(self, controller):
        """
        Construye la AppBar con todos sus elementos.

        Args:
            controller (Manager): Controlador principal con acceso al layout,
                la configuración y los métodos de acción.
        """
        super().__init__()
        self.controller = controller
        
        self.bgcolor = ft.Colors.BLACK
        self.leading = ft.IconButton(
            ft.Icons.MENU, 
            on_click=self.controller.layout.toggle_sidebar,
            tooltip=i18n.t("leading.tooltip", default="Mostrar/Ocultar Panel Lateral"), 
            icon_color=ft.Colors.WHITE
        )
        self.title = self._build_title()
        self.center_title = False
        self.actions = self._build_actions()

    def _build_title(self):
        """
        Construye el widget de título de la AppBar.

        Contiene el texto de la aplicación y los botones de modo de
        selección (Multi, Rango) y copia al portapapeles.

        Returns:
            ft.Row: Fila con el título y los botones de acción.
        """
        return ft.Row(
            [
                ft.Text(i18n.t("app.title"), color=ft.Colors.WHITE),
                ft.Row(
                    [
                        self.controller.layout.btn_mode_multi,
                        self.controller.layout.btn_mode_range,
                        self.controller.layout.btn_select_all,
                        self.controller.layout.btn_search_selection,
                        ft.VerticalDivider(width=1, color=ft.Colors.GREY_800),
                        self.controller.layout.btn_mark_selected,
                        self.controller.layout.btn_unmark_selected,
                        ft.Container(width=6),
                        self.controller.layout.btn_copy_selected,
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    expand=True,
                ),
            ],
            expand=True,
        )

    def _build_actions(self):
        """
        Construye la lista de controles de acción de la AppBar.

        Incluye tres elementos:
          1. Menú de exportación (TXT, CSV, Markdown, SQLite).
          2. Menú de configuración (tema, resaltado de sintaxis, nivel de log,
             ayuda, acerca de y salir).

        Las opciones activas se marcan con un ícono de check dinámico.

        Returns:
            list: Lista de widgets a incluir en ``AppBar.actions``.
        """
        current_theme = self.controller.configuracion.app.tema.lower()
        current_log_level = self.controller.configuracion.app.log_level.upper()
        syntax_hl = self.controller.app_state.syntax_highlighting
        current_page_size = self.controller.configuracion.app.page_size_default
        current_context_range = self.controller.app_state.context_range
        current_lang = i18n.current()
        
        def get_check_icon(theme_name):
            return ft.Icon(ft.Icons.CHECK, size=20) if current_theme == theme_name else ft.Container(width=20)

        def get_check_icon_log(level_name):
            return ft.Icon(ft.Icons.CHECK, size=20) if current_log_level == level_name else ft.Container(width=20)

        def get_check_icon_bool(val):
            return ft.Icon(ft.Icons.CHECK, size=20) if val else ft.Container(width=20)

        def get_check_icon_page_size(size_val):
            return ft.Icon(ft.Icons.CHECK, size=20) if current_page_size == size_val else ft.Container(width=20)

        def get_check_icon_context(range_val):
            return ft.Icon(ft.Icons.CHECK, size=20) if current_context_range == range_val else ft.Container(width=20)

        def get_check_icon_lang(lang_code):
            return ft.Icon(ft.Icons.CHECK, size=20) if current_lang == lang_code else ft.Container(width=20)

        menu_style = ft.MenuStyle(bgcolor=ft.Colors.BLACK, elevation=0)

        export_menu_bar = ft.MenuBar(
            style=menu_style,
            controls=[
                ft.SubmenuButton(
                    content=ft.Row([ft.Icon(ft.Icons.SAVE, color=ft.Colors.WHITE, size=20)]),
                    tooltip=i18n.t("menu.export"),
                    controls=[
                        ft.MenuItemButton(
                            content=ft.Row([ft.Icon(ft.Icons.DESCRIPTION, size=20), ft.Text(i18n.t("menu.export.txt"))]),
                            on_click=lambda e: self.controller.page.run_task(self.controller._exportar_datos, e, 'txt')
                        ),
                        ft.MenuItemButton(
                            content=ft.Row([ft.Icon(ft.Icons.GRID_ON, size=20), ft.Text(i18n.t("menu.export.csv"))]),
                            on_click=lambda e: self.controller.page.run_task(self.controller._exportar_datos, e, 'csv')
                        ),
                        ft.MenuItemButton(
                            content=ft.Row([ft.Icon(ft.Icons.TABLE_CHART, size=20), ft.Text(i18n.t("menu.export.md"))]),
                            on_click=lambda e: self.controller.page.run_task(self.controller._exportar_datos, e, 'md')
                        ),
                        ft.MenuItemButton(
                            content=ft.Row([ft.Icon(ft.Icons.DATASET, size=20), ft.Text(i18n.t("menu.export.sqlite"))]),
                            on_click=lambda e: self.controller.page.run_task(self.controller._exportar_datos, e, 'sqlite')
                        )
                    ]
                ),
            ],
            tooltip=i18n.t("menu.export")
        )

        config_menu_bar = ft.MenuBar(
            style=menu_style,
            controls=[
                ft.SubmenuButton(
                    content=ft.Row([ft.Icon(ft.Icons.SETTINGS, color=ft.Colors.WHITE, size=20)]),
                    controls=[
                        ft.SubmenuButton(
                            content=ft.Row([ft.Icon(ft.Icons.LANGUAGE, size=20), ft.Text(i18n.t("menu.language", default="Idioma"))]),
                            controls=[
                                ft.MenuItemButton(
                                    content=ft.Row([ft.Text("Español"), get_check_icon_lang('es')], spacing=10),
                                    on_click=lambda _: self.controller.cambiar_idioma('es')
                                ),
                                ft.MenuItemButton(
                                    content=ft.Row([ft.Text("English"), get_check_icon_lang('en')], spacing=10),
                                    on_click=lambda _: self.controller.cambiar_idioma('en')
                                ),
                            ]
                        ),
                        ft.SubmenuButton(
                            content=ft.Row([ft.Icon(ft.Icons.BRIGHTNESS_6, size=20), ft.Text(i18n.t("menu.theme"))]),
                            controls=[
                                ft.MenuItemButton(
                                    content=ft.Row([ft.Icon(ft.Icons.LIGHT_MODE, size=20), ft.Text(i18n.t("menu.theme.light")), get_check_icon('claro')], spacing=10),
                                    on_click=lambda _: self.controller.cambiar_tema('claro')
                                ),
                                ft.MenuItemButton(
                                    content=ft.Row([ft.Icon(ft.Icons.DARK_MODE, size=20), ft.Text(i18n.t("menu.theme.dark")), get_check_icon('oscuro')], spacing=10),
                                    on_click=lambda _: self.controller.cambiar_tema('oscuro')
                                ),
                                ft.MenuItemButton(
                                    content=ft.Row([ft.Icon(ft.Icons.SETTINGS_SYSTEM_DAYDREAM, size=20), ft.Text(i18n.t("menu.theme.system")), get_check_icon('sistema')], spacing=10),
                                    on_click=lambda _: self.controller.cambiar_tema('sistema')
                                )
                            ]
                        ),
                        ft.MenuItemButton(
                            content=ft.Row([ft.Icon(ft.Icons.COLOR_LENS, size=20), ft.Text(i18n.t("menu.syntax")), get_check_icon_bool(syntax_hl)], spacing=10),
                            on_click=self.controller.toggle_syntax_highlighting,
                            close_on_click=False
                        ),
                        ft.SubmenuButton(
                            content=ft.Row([ft.Icon(ft.Icons.VIEW_AGENDA, size=20), ft.Text(i18n.t("menu.page_size"))]),
                            controls=[
                                ft.MenuItemButton(content=ft.Row([ft.Text("50"),  get_check_icon_page_size(50)],  spacing=10), on_click=lambda _: self.controller.cambiar_page_size_default(50)),
                                ft.MenuItemButton(content=ft.Row([ft.Text("100"), get_check_icon_page_size(100)], spacing=10), on_click=lambda _: self.controller.cambiar_page_size_default(100)),
                                ft.MenuItemButton(content=ft.Row([ft.Text("200"), get_check_icon_page_size(200)], spacing=10), on_click=lambda _: self.controller.cambiar_page_size_default(200)),
                                ft.MenuItemButton(content=ft.Row([ft.Text("500"), get_check_icon_page_size(500)], spacing=10), on_click=lambda _: self.controller.cambiar_page_size_default(500)),
                            ]
                        ),
                        ft.SubmenuButton(
                            content=ft.Row([ft.Icon(ft.Icons.VIEW_QUILT, size=20), ft.Text(i18n.t("menu.context_range"))]),
                            controls=[
                                ft.MenuItemButton(content=ft.Row([ft.Text(f"5 {i18n.t('table.col.line').lower()}s (±5)"),   get_check_icon_context(5)],  spacing=10), on_click=lambda _: self.controller.cambiar_context_range(5)),
                                ft.MenuItemButton(content=ft.Row([ft.Text(f"10 {i18n.t('table.col.line').lower()}s (±10)"), get_check_icon_context(10)], spacing=10), on_click=lambda _: self.controller.cambiar_context_range(10)),
                                ft.MenuItemButton(content=ft.Row([ft.Text(f"15 {i18n.t('table.col.line').lower()}s (±15)"), get_check_icon_context(15)], spacing=10), on_click=lambda _: self.controller.cambiar_context_range(15)),
                                ft.MenuItemButton(content=ft.Row([ft.Text(f"20 {i18n.t('table.col.line').lower()}s (±20)"), get_check_icon_context(20)], spacing=10), on_click=lambda _: self.controller.cambiar_context_range(20)),
                                ft.MenuItemButton(content=ft.Row([ft.Text(f"50 {i18n.t('table.col.line').lower()}s (±50)"), get_check_icon_context(50)], spacing=10), on_click=lambda _: self.controller.cambiar_context_range(50)),
                            ]
                        ),
                        ft.SubmenuButton( # Movido a la última posición
                            content=ft.Row([ft.Icon(ft.Icons.BUG_REPORT, size=20), ft.Text(i18n.t("menu.log_level"))]),
                            controls=[
                                ft.MenuItemButton(content=ft.Row([ft.Text("DEBUG"),    get_check_icon_log('DEBUG')],    spacing=10), on_click=lambda _: self.controller.cambiar_log_level('DEBUG')),
                                ft.MenuItemButton(content=ft.Row([ft.Text("INFO"),     get_check_icon_log('INFO')],     spacing=10), on_click=lambda _: self.controller.cambiar_log_level('INFO')),
                                ft.MenuItemButton(content=ft.Row([ft.Text("WARNING"),  get_check_icon_log('WARNING')],  spacing=10), on_click=lambda _: self.controller.cambiar_log_level('WARNING')),
                                ft.MenuItemButton(content=ft.Row([ft.Text("ERROR"),    get_check_icon_log('ERROR')],    spacing=10), on_click=lambda _: self.controller.cambiar_log_level('ERROR')),
                                ft.MenuItemButton(content=ft.Row([ft.Text("CRITICAL"), get_check_icon_log('CRITICAL')], spacing=10), on_click=lambda _: self.controller.cambiar_log_level('CRITICAL')),
                            ]
                        ),
                    ],
                    tooltip=i18n.t("menu.settings")
                ),
                ft.SubmenuButton(
                    content=ft.Row([ft.Icon(ft.Icons.HELP, color=ft.Colors.WHITE, size=20)]),
                    controls=[
                        ft.MenuItemButton(content=ft.Row([ft.Icon(ft.Icons.HELP_OUTLINE, size=20), ft.Text(i18n.t("menu.help"))]), on_click=self.controller.dialogs.open_help),
                        ft.MenuItemButton(content=ft.Row([ft.Icon(ft.Icons.INFO_OUTLINE, size=20), ft.Text(i18n.t("menu.about"))]), on_click=self.controller.dialogs.open_about)
                    ],
                    tooltip=i18n.t("menu.help")
                ),
                ft.MenuItemButton(
                    content=ft.Row([ft.Icon(ft.Icons.EXIT_TO_APP, color=ft.Colors.RED_400, size=20)]),
                    on_click=self.controller.close_app_handler,
                    tooltip=i18n.t("menu.exit")
                )
            ]
        )

        return [
            export_menu_bar,
            ft.Container(width=20),
            config_menu_bar,
        ]
