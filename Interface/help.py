"""
Contiene el texto de ayuda en formato Markdown que se muestra en el diálogo de ayuda de la aplicación.
"""

ES_HELP_TEXT = """
# **Descripción:**

Carga un archivo de log (RTP OSV, Syslog o formatos personalizados definidos mediante JSON) para analizarlo.
Permite realizar múltiples filtros para localizar errores y exportar los datos filtrados.  

---

# **Instrucciones de uso:**

- Abre un archivo de log (.txt)
- Puedes ocultar los niveles 'clear'
- Usa el panel lateral para filtrar por: 
  - Fecha y hora (Filtrar por fecha y hora de inicio y fin).
  - Búsqueda por palabras clave: 
    - Múltiples palabras con separadores AND u OR.
    - Búsquedas con Expresiones Regulares (Regex).  
  - Por elementos disponibles en el log:
    - Nivel. 
    - Evento. 
    - Proceso.
    - etc... 
  - Notas (crea notas automáticas en función de palabras clave preestablecidas en fichero **"notes_config.json"**)
  - Puedes marcar manualmente líneas para posteriormente filtrar por ellas.
- Todos los filtros son acumulativos.
- Una vez filtrados todos los datos necesarios, puedes exportarlos.
---

# **Portapapeles:**

- Puedes seleccionar líneas para posteriormente copiarlas al portapapeles de la siguiente manera:
    - Pulsando sobre una línea del Log.
    - Pulsando sobre el botón **+ Multi** e ir pulsando sobre las líneas deseadas o **Ctrl + Clic**.
    - Pulsando sobre el botón **Rango** e introducir el rango de líneas deseadas o **Shift + Clic**.
    - Pulsando sobre el botón **Todo** o **Ctrl+A** para seleccionar todas las líneas visibles en pantalla.
    - Pulsando sobre el botón **Buscar** o **Ctrl+F** para seleccionar líneas por búsqueda de texto en todo el documento.
- Copiar al portapapeles todas las líneas seleccionadas: Pulsando sobre el botón **Copiar** o **Ctrl+C**.
---

# **Marcar Líneas:**

- Puedes marcar cada una de las líneas de log para filtrar posteriormente por ellas. Para marcarlas:
    - Pulsando en la casilla a la izquierda de cada línea del log.
    - Pulsando el botón de marcar todas las líneas seleccionadas.
    - Pulsando la casilla para marcar todas las líneas de la página actual.
    - Puedes marcar las líneas desde la ventana contextual.
 
---

# **Vista contextual:**

- Haciendo doble clic sobre cualquier línea del Log se abrirá una ventana con las N líneas anteriores y posteriores sin ningún filtro aplicado.
- Puedes modificar el número de líneas a mostrar en la vista contextual en el menú de configuración.
- Puedes marcar líneas dentro de la vista contextual para posteriormente filtrarlas.

---

# **Exportación:**

- El log visible, resultado del filtrado, se puede exportar a archivos con diferentes formatos:
    - CSV
    - TXT
    - Markdown
    - Base de datos SQLITE

---

# **Notas y Formatos Personalizados:**

## 1. Notas Automáticas
Puedes crear notas automáticas en función de palabras clave preestablecidas en fichero **"notes_config.json"** con la siguiente estructura:
```json
[
    { "keywords": ["keyword1", "keyword2"], "text": "nota a añadir" }
]
```

## 2. Añadir Nuevos Formatos de Log
Puedes añadir soporte para nuevos tipos de log editando el archivo **"formats_config.json"**. Cada formato requiere:
- **id**: Identificador único.
- **name**: Nombre que aparecerá en la aplicación.
- **regex**: Expresión regular para capturar los campos.
- **mapping**: Diccionario que asocia los grupos del regex con los campos (`timestamp`, `nivel`, `mensaje`, etc.).
- **date_format**: Formato de la fecha para su correcto parseo.
- **extra_columns**: Lista de campos adicionales que deseas que aparezcan como columnas y filtros.

---

# **Guía de búsqueda y filtrado libre**

Esta guía explica cómo funciona el motor de búsqueda interno de la aplicación y cómo aprovechar las expresiones regulares para encontrar información específica en los logs.

## 1. Búsqueda por Palabras Clave (Regex desactivado)

Cuando la opción de **expresiones regulares** no está marcada, la aplicación procesa tu búsqueda de la siguiente manera:

1. **División por palabras**: El texto que escribes se divide en términos individuales (separados por espacios).
2. **Modo de búsqueda**: Dependiendo del valor del modo de búsqueda (que suele ser "AND" por defecto):
   - **Modo AND**: La línea del log debe contener **todas** las palabras que has escrito, sin importar el orden.
     - *Ejemplo*: `SIP INVITE 5060` mostrará líneas que contengan las tres palabras en cualquier posición.
   - **Modo OR**: La línea del log debe contener **al menos una** de las palabras escritas.
     - *Ejemplo*: `ERROR CRITICAL` mostrará cualquier línea que contenga "ERROR" o que contenga "CRITICAL".
3. **Insensibilidad a mayúsculas**: La búsqueda no distingue entre "error", "Error" o "ERROR".

## 2. Búsqueda con Expresiones Regulares (Regex marcado)

Cuando activas **Regex**, el texto se interpreta como un patrón lógico complejo. 
Algunos ejemplos útiles para el análisis de logs:

### Ejemplos Básicos

- **Líneas que comienzan con una fecha**:  
  `^2026-03`

- **Líneas que terminan con la palabra "failed"**:  
  `failed$`

- **Líneas que contienen "SIP" o "HTTP"**:  
  `SIP|HTTP`

- **Busca el número exacto "5060"**:  
  `\\b5060\\b`  
  *(evita coincidencias como "15060")*

### Ejemplos Avanzados para Logs

- **Direcciones IP**:  
  `\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}`  
  *(Busca cualquier dirección IP estándar)*

- **Códigos de Error (Error seguido de números)**:  
  `Error \\d+`  
  *(Coincide con "Error 404", "Error 500", etc.)*

- **Líneas que NO contienen una palabra**:  
  `^((?!DEBUG).)*$`  
  *(Muestra líneas que no tengan la palabra "DEBUG")*

- **Búsqueda de múltiples palabras en un orden específico**:  
  `Sending.*INVITE.*to`  
  *(Busca líneas donde aparezca "Sending", luego "INVITE" y luego "to", con cualquier cosa en medio)*
"""

EN_HELP_TEXT = """
# **Description:**

Loads a log file (RTP OSV, Syslog or custom JSON-defined formats) for analysis.
Allows multiple filters to locate errors and export filtered data.

---

# **Usage Instructions:**

- Open a log file (.txt)
- You can hide 'clear' levels
- Use the sidebar to filter by:
  - Date and time (Filter by start and end date/time).
  - Keyword search:
    - Multiple words with AND or OR separators.
    - Regular Expression (Regex) searches.
  - By log elements:
    - Level, Event, Process, etc.
  - Notes (creates automatic notes based on preset keywords in **"notes_config.json"**)
  - You can manually mark lines to filter by them later.
- All filters are cumulative.
- Once all necessary data is filtered, you can export it.
---

# **Clipboard:**

- You can select lines and copy them to the clipboard using **Ctrl+C**.
- Use **Ctrl+Click** for multi-selection or **Shift+Click** for range selection.
- **Ctrl+A** selects all visible lines, and **Ctrl+F** allows searching and selecting matching lines.

---

# **Context View:**

- Double-clicking on any log line will open a window showing surrounding lines (context).
- You can change the context range in the settings menu.

---

# **Export:**

- Export filtered results to: **CSV, TXT, Markdown, or SQLITE**.

---

# **Notes and Custom Formats:**

## 1. Automatic Notes
Define automatic notes based on keywords in **"notes_config.json"**:
```json
[
    { "keywords": ["keyword1", "keyword2"], "text": "note to add" }
]
```

## 2. Adding New Log Formats
Add support for new log types by editing **"formats_config.json"**. Each entry needs:
- **id**: Unique identifier.
- **name**: Display name in the app.
- **regex**: Regular expression to capture fields.
- **mapping**: Associates regex groups with fields (`timestamp`, `nivel`, `mensaje`, etc.).
- **date_format**: Date format for correct parsing.
- **extra_columns**: List of additional fields to display as columns and filters.

---

# **Search and Free Filtering Guide**

This guide explains how the application's internal search engine works and how to take advantage of regular expressions to find specific information in logs.

## 1. Keyword Search (Regex off)

When the **regular expressions** option is not checked, the application processes your search as follows:

1. **Word splitting**: The text you type is split into individual terms (separated by spaces).
2. **Search mode**: Depending on the search mode value (usually "AND" by default):
   - **Mode AND**: The log line must contain **all** the words you have written, regardless of order.
     - *Example*: `SIP INVITE 5060` will show lines containing all three words in any position.
   - **Mode OR**: The log line must contain **at least one** of the written words.
     - *Example*: `ERROR CRITICAL` will show any line containing "ERROR" or containing "CRITICAL".
3. **Case insensitivity**: The search does not distinguish between "error", "Error", or "ERROR".

## 2. Regular Expression Search (Regex on)

When you activate **Regex**, the text is interpreted as a complex logical pattern.
Some useful examples for log analysis:

### Basic Examples

- **Lines starting with a date**:
  `^2026-03`

- **Lines ending with the word "failed"**:
  `failed$`

- **Lines containing "SIP" or "HTTP"**:
  `SIP|HTTP`

- **Search for exact number "5060"**:
  `\\b5060\\b`
  *(avoids matches like "15060")*

### Advanced Examples for Logs

- **IP Addresses**:
  `\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}`
  *(Searches for any standard IP address)*

- **Error Codes (Error followed by numbers)**:
  `Error \\d+`
  *(Matches "Error 404", "Error 500", etc.)*

- **Lines NOT containing a word**:
  `^((?!DEBUG).)*$`
  *(Shows lines that do not have the word "DEBUG")*

- **Search for multiple words in a specific order**:
  `Sending.*INVITE.*to`
  *(Searches for lines where "Sending" appears, then "INVITE", and then "to", with anything in between)*
"""

def get_help_text(lang: str) -> str:
    """Devuelve el texto de ayuda en el idioma solicitado."""
    if lang == "en":
        return EN_HELP_TEXT
    return ES_HELP_TEXT
