# Estructura del Proyecto: DumpLog

Este documento describe la organización de archivos y carpetas de la aplicación, detallando la responsabilidad de cada componente.

---

## Directorio Raíz

| Archivo | Descripción |
| :--- | :--- |
| `DumpLog.py` | Punto de entrada principal. Configura el sistema de logging rotativo, carga los ajustes del `.ini` y arranca la aplicación Flet. |
| `DumpLog.ini` | Configuración persistente: geometría de ventana, último directorio, tema, tamaño de página, nivel de log, historial de búsqueda, etc. |
| `notes_config.json` | Reglas JSON para la generación automática de **Notas** basadas en palabras clave encontradas en los mensajes del log. |
| `Compilar.cmd` | Script para automatizar la creación del ejecutable con Nuitka. |

---

## 📁 `Interface/` (Capa de Presentación)

Contiene todo lo relacionado con la interfaz gráfica y la coordinación entre la vista y la lógica.

| Archivo | Descripción |
| :--- | :--- |
| `Manager.py` | **Controlador central (MVC)**. Orquesta todos los submódulos, delega eventos de UI y coordina el flujo de datos. |
| `app_layout.py` | Construye la disposición visual de la app (Sidebar + Área principal + Vista contextual). Gestiona los checkboxes de filtro con caché. |
| `state.py` | Define `AppState`, el almacén centralizado de estado: DataFrames, filtros activos, selección, paginación, marcas y vista contextual. |
| `help.py` | Texto de ayuda en formato Markdown que se muestra en el diálogo de Ayuda. |

### 📁 `Interface/Components/` (Widgets UI)

Componentes visuales de la interfaz:

| Archivo | Descripción |
| :--- | :--- |
| `app_bar.py` | Barra superior con botones de selección/copia, menú de exportación (TXT, CSV, MD, SQLite) y menú de configuración (tema, resaltado, filas/página, rango contextual, nivel de log). |
| `log_table.py` | Tabla principal y tabla de **Vista Contextual**. Usa `ListView` con `item_extent` fijo para alto rendimiento con miles de filas. |
| `sidebar.py` | Panel lateral con filtros por fecha/hora, búsqueda libre (AND/OR/Regex), checkboxes de nivel/evento/proceso/nota y controles de navegación de selección. |

### 📁 `Interface/Logic/` (Controladores de Funcionalidad)

Módulos especializados que ejecutan la lógica de negocio sin acoplarse directamente a la UI:

| Archivo | Descripción |
| :--- | :--- |
| `dialogs.py` | Gestiona los diálogos modales: "Acerca de", "Ayuda" y "Selección por búsqueda" (Ctrl+F) con historial persistente y soporte AND/OR/Regex. |
| `export_manager.py` | Exporta el `filtered_df` a TXT, CSV, Markdown y SQLite. La escritura se ejecuta en un executor para no bloquear la UI. |
| `file_manager.py` | Abre y parsea ficheros de log de forma asíncrona. Gestiona la persistencia de marcas en archivos `.marks` junto al log original. |
| `filter_manager.py` | Construye máscaras booleanas de Pandas combinando todos los criterios activos. La asignación final a `AppState` es **thread-safe** (lock atómico). |
| `selection_manager.py` | Selección de filas (Normal / Multi / Rango con Ctrl+Clic / Shift+Clic), búsqueda por texto (Ctrl+F), copia al portapapeles y navegación entre líneas seleccionadas. |
| `system_manager.py` | Gestión del tema visual, geometría de ventana, nivel de log global y cierre limpio de la aplicación. |
| `table_renderer.py` | Renderizado eficiente mediante **Row Pooling** (reutilización de controles). Aplica resaltado de sintaxis con regex precompilados (IPs, puertos, errores, hex). Gestiona también la Vista Contextual. |
| `ui_action_manager.py` | Centraliza todos los manejadores de eventos de la UI (filtros, paginación, búsqueda, fechas). Implementa el mecanismo de **Debounce** (0.4 s) para agrupar cambios rápidos y evitar refiltrados innecesarios. |

### 📁 `Interface/Librerias/` (Utilidades)

| Archivo | Descripción |
| :--- | :--- |
| `app_settings.py` | Dataclasses de configuración: `AppSettings` (ajustes de app) y `Version` (metadatos de versión/autor). |
| `config_manager.py` | Lógica de bajo nivel para leer y escribir el archivo `DumpLog.ini`. |

---

## 📁 `Model/` (Capa de Datos)

Define la estructura de los datos y cómo se transforman desde el formato de texto original.

| Archivo | Descripción |
| :--- | :--- |
| `log_entry.py` | Dataclass `LogEntry` que representa una única línea del log con sus campos: `linea`, `timestamp`, `nivel`, `proceso`, `evento`, `pid`, `mensaje`, `notas`. |
| `log_parser.py` | Motor de parseo. Aplica Regex al fichero línea a línea, extrae objetos `LogEntry` y los convierte a `pd.DataFrame` optimizado (columnas categóricas para menor uso de memoria). Carga las reglas de `notes_config.json`. |

---

## 📁 Otros Directorios

| Directorio | Descripción |
| :--- | :--- |
| `Documentacion/` | Manuales de usuario (`manual.md`), guía técnica de desarrollo (`guia_tecnica.md`), este documento y otros. |
| `Ejemplos/` | Archivos de log de muestra (`.txt`) y ejemplos de exportaciones generadas. |
| `dist/` | Directorio de salida del ejecutable compilado con Nuitka. |
| `logs_app/` | Logs internos de depuración de la propia aplicación (rotación diaria, 7 días de retención). |

---

## Flujo de Datos Resumido

```
DumpLog.py
  └─► Manager.__init__()
        ├─► FileManager.cargar_fichero_async()
        │     └─► LogParser.parse_file() → LogParser.to_dataframe()
        │           └─► AppState.df
        ├─► UIActionManager (eventos) → Manager._trigger_debounced_filter()
        │     └─► FilterManager.apply_filters() [hilo separado, thread-safe]
        │           └─► AppState.filtered_df  (asignación atómica)
        └─► TableRenderer.refresh_table() [Row Pooling]
              └─► AppLayout.log_table (ListView)
```
