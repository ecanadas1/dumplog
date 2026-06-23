# Análisis Técnico: Visor de ficheros RTPDumpLogs

Este documento proporciona un análisis detallado de la arquitectura, tecnologías y rendimiento de la aplicación **DumpLog**.

---

## Arquitectura y Diseño

La aplicación emplea una arquitectura modular basada en el patrón **MVC**, facilitada por el framework **Flet** y el uso de **Pandas** para la gestión de datos.

### Componentes Principales

*   **Entrada de Datos (`Model/log_parser.py`)**: Utiliza expresiones regulares (Regex) para transformar archivos de texto raw en estructuras de datos tipadas (`LogEntry`). La conversión a `pandas.DataFrame` con tipos categóricos permite una manipulación extremadamente rápida y eficiente en memoria.
*   **Núcleo de Control (`Interface/Manager.py`)**: Orquestador central que gestiona el estado de la aplicación (`AppState`) y coordina las acciones entre la UI y los managers de lógica especializados.
*   **Gestión de Interfaz (`Interface/app_layout.py`)**: Estructura la aplicación en una barra de herramientas superior, un panel lateral de filtros, una tabla de visualización paginada y una **Vista Contextual** en pantalla dividida.
*   **Manejadores de Lógica (`Interface/Logic/`)**: Módulos especializados que encapsulan funcionalidades específicas:
    *   `filter_manager.py`: Filtrado avanzado mediante indexación booleana de Pandas con asignación **thread-safe**.
    *   `export_manager.py`: Exportación multiformato (TXT, CSV, MD, SQLite) en executor asíncrono.
    *   `file_manager.py`: Carga asíncrona de archivos y persistencia de marcas en archivos `.marks`.
    *   `selection_manager.py`: Selección multi-fila (Normal/Multi/Rango), búsqueda Ctrl+F con motor AND/OR/Regex e historial persistente.
    *   `table_renderer.py`: Renderizado optimizado mediante **Row Pooling** y resaltado de sintaxis.
    *   `ui_action_manager.py`: Centralización de eventos de UI con mecanismo de **Debounce**.
    *   `dialogs.py`: Diálogos modales con historial de búsqueda persistente.

---

## Tecnologías Clave

| Tecnología | Propósito |
| :--- | :--- |
| **Flet** | Framework de UI para crear aplicaciones nativas con Python (basado en Flutter). |
| **Pandas** | Motor de procesamiento de datos para filtrado y estadísticas de alto rendimiento. |
| **Asyncio** | Gestión de tareas asíncronas para mantener la interfaz fluida durante operaciones pesadas. |
| **Threading** | Ejecución de filtrado en hilo secundario con asignación atómica (thread-safe) al estado. |
| **SQLite** | Soporte para exportación de datos estructurados para análisis externo. |
| **Nuitka** | Compilación a ejecutable nativo de alto rendimiento para distribución. |

---

## Puntos de Interés y Optimizaciones

### 🚀 Rendimiento con Grandes Volúmenes
La aplicación está optimizada para manejar logs de más de 250.000 líneas:
*   **Paginación Real**: Solo se renderizan las filas visibles (50–500 por página), evitando la sobrecarga del sistema de layout.
*   **Row Pooling**: `TableRenderer` reutiliza los controles existentes actualizando solo sus propiedades, en lugar de destruir y crear objetos en cada cambio de página.
*   **Tipado Categórico**: Columnas repetitivas (Nivel, Evento, Proceso) se almacenan como tipos categóricos en Pandas, reduciendo el uso de memoria hasta un 80%.
*   **Búsqueda Debounced**: Los filtros se activan tras 400 ms sin escritura, evitando cálculos innecesarios por cada pulsación.
*   **Thread-Safe Filtering**: El filtrado ocurre en un hilo secundario; la asignación final a `filtered_df` es atómica mediante `threading.Lock()`.

### 🔍 Capacidades de Filtrado
*   Soporte completo para **Expresiones Regulares (Regex)** con detección y feedback visual de errores.
*   Lógica booleana (**AND/OR**) para términos de búsqueda múltiples.
*   Filtrado temporal preciso por fecha y hora de inicio y fin.
*   Filtros por **Nivel, Evento, Proceso y Notas** con búsqueda interna en cada categoría.
*   **Reglas de Notas Dinámicas**: Anotaciones automáticas basadas en `notes_config.json`.

### 🖱️ Selección e Interacción
*   **Modo Normal**: Clic simple selecciona una sola fila.
*   **Modo Multi** (botón o Ctrl+Clic): Acumula filas en la selección.
*   **Modo Rango** (botón o Shift+Clic): Selecciona todas las filas entre el ancla y la fila pulsada.
*   **Ctrl+A**: Selecciona todas las líneas de la página visible.
*   **Ctrl+F**: Abre el diálogo de selección por texto (AND/OR/Regex) con historial persistente.
*   **Ctrl+C**: Copia las líneas seleccionadas al portapapeles en formato texto.

### 🔎 Vista Contextual (Split Screen)
*   **Doble clic** en cualquier fila abre la Vista Contextual.
*   Muestra ±N líneas alrededor de la línea seleccionada sin ningún filtro aplicado.
*   El número de líneas de contexto es configurable desde el menú de Configuración (5, 10, 15, 20 o 50 líneas).
*   Se pueden marcar líneas dentro de la Vista Contextual para filtrarlas posteriormente.

### 📌 Persistencia de Marcas
*   Las líneas marcadas se guardan automáticamente en un archivo `<nombre_log>.marks` junto al archivo de log.
*   Se cargan automáticamente al abrir el mismo archivo en sesiones posteriores.
*   Si no hay marcas, el archivo `.marks` se elimina para no dejar archivos huérfanos.

### 📦 Robustez y Despliegue
*   Compilación con **Nuitka** para distribución como ejecutable independiente en Windows.
*   Configuración persistente mediante archivo `.ini` (tema, geometría, historial, tamaño de página, etc.).
*   Sistema de **logs interno rotativo** con retención de 7 días para depuración.
*   Nivel de log configurable en tiempo de ejecución desde el menú de la aplicación.

---

## Conclusión

DumpLog es una herramienta profesional de análisis de logs que equilibra una interfaz de usuario rica con un motor de procesamiento de datos de alto rendimiento. La separación de responsabilidades en managers especializados, la gestión thread-safe del estado compartido y las optimizaciones de renderizado la convierten en una aplicación robusta, escalable y fácil de mantener.
