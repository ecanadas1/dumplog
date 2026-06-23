# Documentación del Proyecto DumpLog

Bienvenido a la documentación técnica de **DumpLog**, una herramienta de visualización y análisis de logs RTP construida con Flet y Pandas.

## Mapa de Documentación

Si eres un desarrollador que desea actualizar o mantener esta aplicación, te recomendamos seguir este orden:

1.  **[Estructura del Proyecto](project_structure.md)**: Una visión general de dónde se encuentra cada archivo y de qué es responsable.
2.  **[Guía Técnica de Arquitectura](guia_tecnica.md)**: Explicación detallada de cómo fluyen los datos, el patrón de diseño y las optimizaciones de rendimiento (imprescindible para tocar el código).
3.  **[Explicación del Motor de Búsqueda](explicacion_busqueda.md)**: Detalles sobre cómo funcionan los modos AND/OR y las expresiones regulares.
4.  **[Manual de Usuario](manual.md)**: Guía sobre el uso de la interfaz desde el punto de vista del usuario final.

## Resumen de la Estructura de Funciones

La aplicación está organizada para que el **Manager** (`Interface/Manager.py`) centralice las llamadas, pero la ejecución real reside en submódulos:

*   **Filtrado**: `FilterManager.apply_filters()`
*   **Renderizado**: `TableRenderer.refresh_table()`
*   **Carga de Datos**: `LogParser.parse_file()` -> `LogParser.to_dataframe()`
*   **Interacción UI**: `UIActionManager` (contiene todos los `on_click`, `on_change`, etc.)
*   **Selección y Copia**: `SelectionManager.on_row_click()` y `SelectionManager.copy_selected_lines()`

## Tecnologías Principales
*   **Flet (0.84.0+)**: Framework de UI basado en Flutter.
*   **Pandas**: Motor de procesamiento de datos para el filtrado y análisis.
*   **Nuitka**: Utilizado para compilar la aplicación a un ejecutable (.exe) de alto rendimiento.
