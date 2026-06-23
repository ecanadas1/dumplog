# Guía Técnica de Desarrollo - DumpLog

Este documento proporciona una visión profunda de la arquitectura interna de la aplicación, diseñada para facilitar el mantenimiento y la implementación de nuevas funcionalidades.

---

## 1. Arquitectura General

La aplicación sigue un patrón inspirado en **MVC (Modelo-Vista-Controlador)**, adaptado para la naturaleza reactiva de Flet (Flutter para Python).

*   **Modelo (`Model/`)**: Gestión de datos puros. No conoce nada de la interfaz. Usa **Pandas** para procesar grandes volúmenes de logs con alta velocidad.
*   **Vista (`Interface/Components/` y `Interface/app_layout.py`)**: Define la estructura visual. Es mayormente declarativa.
*   **Controlador (`Interface/Manager.py`)**: El eje central. Orquesta la comunicación entre los submódulos.

---

## 2. El "Manager" y la Delegación

Para evitar que `Manager.py` se convierta en un archivo monolítico inmanejable, la lógica se delega en módulos especializados en `Interface/Logic/`:

| Manager | Responsabilidad |
| :--- | :--- |
| `Dialogs` | Diálogos modales (Ayuda, Acerca de, Selección por búsqueda con historial). |
| `FileManager` | Carga de archivos, persistencia de marcas en archivos `.marks`. |
| `FilterManager` | Construcción de máscaras de Pandas (thread-safe). |
| `SelectionManager` | Selección Normal/Multi/Rango, portapapeles, búsqueda Ctrl+F y navegación. |
| `TableRenderer` | Renderizado por Row Pooling y Vista Contextual. |
| `ExportManager` | Generación de archivos de salida (CSV, TXT, MD, SQLite). |
| `UIActionManager` | Manejadores de eventos de la UI con mecanismo Debounce. |
| `SystemManager` | Tema visual, geometría de ventana, nivel de log y cierre limpio. |

---

## 3. Gestión de Estado (`AppState`)

Toda la aplicación comparte una instancia única de `AppState` (`Interface/state.py`). Agrupa:

| Campo | Tipo | Descripción |
| :--- | :--- | :--- |
| `df` | `pd.DataFrame` | DataFrame original completo. **Nunca modificar tras la carga.** |
| `filtered_df` | `pd.DataFrame` | Resultado de aplicar los filtros activos. |
| `marked_lines` | `Set[int]` | Líneas marcadas por el usuario (persisten en `.marks`). |
| `selected_lines` | `Set[int]` | Líneas con resaltado visual (selección temporal). |
| `context_df` | `pd.DataFrame` | Subconjunto de `df` para la Vista Contextual. |
| `context_range` | `int` | Número de líneas antes/después en la Vista Contextual. |
| `search_query` | `str` | Texto de búsqueda libre activo. |
| `current_page` | `int` | Página actual de la paginación. |

> **Regla de oro**: `df` es inmutable tras la carga. Siempre leer de `filtered_df` para la visualización.

---

## 4. Flujos de Trabajo Clave

### A. Carga de un Archivo
1. `FileManager.cargar_fichero_async` llama a `LogParser.parse_file`.
2. `LogParser` usa Regex para extraer campos y devuelve una lista de `LogEntry`.
3. Se convierte a `pd.DataFrame` y se precalculan valores únicos (niveles, eventos, procesos, notas).
4. Se guarda en `AppState.df` y se intenta cargar el archivo `.marks` asociado.
5. Se resetea la UI y se llama a `apply_filters()` para la vista inicial.

### B. Proceso de Filtrado (Debounced + Thread-Safe)
Para evitar bloqueos al escribir, se usa un mecanismo de **Debounce** combinado con ejecución en hilo secundario:

1. El usuario escribe → `UIActionManager` cancela la tarea pendiente y crea `asyncio.sleep(0.4)`.
2. Transcurrido el tiempo, se llama a `Manager.apply_filters()` en el **hilo principal**.
3. `Manager` lanza `_apply_filters_thread_safe` en un **hilo secundario** (`page.run_thread`).
4. `FilterManager` construye la máscara booleana y calcula `new_filtered = df[mask]`.
5. La asignación `app_state.filtered_df = new_filtered` se hace dentro de un `threading.Lock()` → **asignación atómica**.
6. Se llama a `TableRenderer.refresh_table()` para actualizar la vista.

```
UIActionManager (hilo UI)
  └─► debounce 0.4s
        └─► Manager.apply_filters()
              └─► page.run_thread(_apply_filters_thread_safe)
                    └─► FilterManager.apply_filters()
                          └─► Lock → AppState.filtered_df = new_filtered  ← atómico
                    └─► TableRenderer.refresh_table()
```

### C. Vista Contextual (Split Screen)
Al hacer **doble clic** en una fila:
1. `Manager.show_context_view(line_num)` localiza la línea en el `df` original.
2. Extrae un slice de `±context_range` filas → `AppState.context_df`.
3. Muestra el componente `context_table_comp` y llama a `TableRenderer.refresh_context_table()`.
4. El scroll se posiciona automáticamente en la línea central con resaltado especial.

### D. Persistencia de Marcas
*   Al **cargar** un fichero: `FileManager.load_marks(file_path)` busca `<ruta_log>.marks` y carga los números de línea.
*   Al **cerrar** la aplicación: `Manager.close_app_handler` llama a `FileManager.save_marks()` antes de salir.
*   Si no hay marcas, el archivo `.marks` se elimina para no dejar archivos vacíos.

### E. Renderizado Optimizado (Row Pooling)
Flet puede volverse lento si se destruyen y crean miles de controles. `TableRenderer` implementa un **Pool de Filas**:
*   En lugar de `controls.clear()`, recorre los controles existentes actualizando solo sus valores.
*   Solo crea controles nuevos si la página requiere más filas de las que hay en el pool.
*   Solo elimina controles si la página requiere menos.

---

## 5. Guía de Extensibilidad

### ¿Cómo añadir un nuevo filtro?
1. Añadir el campo en `AppState` (e.g. `selected_pids: Set[str]`).
2. Crear el control visual en `AppLayout._init_controls`.
3. Añadir el widget al `Sidebar`.
4. Añadir el manejador en `UIActionManager`.
5. Actualizar `FilterManager.apply_filters` con el nuevo criterio de máscara.

### ¿Cómo añadir una nueva regla de resaltado de sintaxis?
Añadir una entrada en `_MSG_PATTERNS` en `Interface/Logic/table_renderer.py`:
```python
(re.compile(r'TU_PATRON_REGEX'), ft.Colors.TU_COLOR)
```

### ¿Cómo añadir un nuevo formato de exportación?
1. Añadir la opción en el menú de `Interface/Components/app_bar.py`.
2. Implementar la lógica de escritura en `ExportManager.exportar_datos` añadiendo un nuevo `elif formato == 'nuevo':`.

### ¿Cómo añadir una opción al menú de Configuración?
El menú se reconstruye cada vez que se llama a `layout.refresh_appbar()`. Añadir el nuevo `MenuItemButton` dentro del `SubmenuButton` de configuración en `app_bar.py._build_actions()`.

---

## 6. Consejos de Rendimiento

*   Usa operaciones vectorizadas de Pandas siempre que sea posible. Evita los bucles `for` sobre DataFrames.
*   Mantén `item_extent` fijo en `ListView` para que el scroll sea fluido con el motor de layout de Flutter.
*   No llames a `page.update()` más de lo estrictamente necesario; prefiere `control.update()` sobre el control afectado.
*   El cálculo de la máscara en `FilterManager` es la operación más costosa. Si se añaden nuevos filtros, intentar ordenarlos de más a menos restrictivo para que el DataFrame se reduzca cuanto antes.
*   La Vista Contextual solo reconstruye sus filas (no usa Row Pooling) porque el número máximo de filas es pequeño (máx. `2 * context_range + 1`).
