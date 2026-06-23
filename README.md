# **Descripción:**

Carga un archivo resultante de un RTPDumpLog de la OSV para analizarlo.
Permite Realizar multiples filtros para localizar errores y exportar los datos filtrados.  

---

# **Instrucciones de uso:**

- Abre un archivo de log (.txt)
- Puedes ocultar los niveles 'clear'
- Usa el panel lateral para filtrar por:
  - Fecha y hora (Filtrar por fecha y hora de inicio y fin).
  - Búsqueda por palabras clave:
    - Multiples palabras con separadores AND u OR.
    - Búsquedas con Expresiones Regulares (Regex).  
  - Por elementos del log:
    - Nivel.
    - Evento.
    - Proceso.
  - Notas (crea notas automáticas en función de palabras clave preestablecidas en fichero **"notes_config.json"**)
  - Puedes marcar manualmente lineas para posteriormente filtrar por ellas.
- Todos los filtros son acumulativos.
- Una vez filtrados todos los datos necesarios, puedes exportarlos.

---

# **Portapapeles:**

- Puedes seleccionar lineas para posteriormente copiarlas al portapapeles de la siguiente manera:
  - Pulsando sobre una linea del Log.
  - Pulsando sobre el botón **+ Multi** e ir pulsando sobre las lineas deseadas o **Ctrl + Clic**.
  - Pulsando sobre el botón **Rango** e introducir el rango de lineas deseadas o **Shift + Clic**.
  - Pulsando sobre el botón **Todo** o **Ctrl+A** para seleccionar todas las lineas visibles en pantalla.
  - Pulsando sobre el botón **Buscar** o **Ctrl+F** para seleccionar lineas por búsqueda de texto en todo el documento.
- Copiar al portapapeles todas las lineas seleccionadas: Pulsando sobre el botón **Copiar** o **Ctrl+C**.

---

# **Marcar Lineas:**

- Puedes marcar cada una de las lineas de log para filtrar posteriormente por ellas. Para marcarlas:
  - Pulsando en la casilla a la izquierda de cada linea del log.
  - Pulsando el botón de marcar todas las lineas seleccionadas.
  - Pulsando la casilla para marcar todas las lineas de la pagina actual.
  - Puedes marcar las líneas desde la ventana contextual.

---

# **Vista contextual:**

- Haciendo doble Clic sobre cualquier linea del Log se abrirá una ventana con la N lineas anteriores y posteriores sin ningún filtro aplicado.
- Puedes modificar el número de lineas a mostrar en la vista contextual en el menu de configuración.
- Puedes marcar lineas dentro de la vista contextual para posteriormente filtrarlas.

---

# **Exportación:**

- El log visible, resultado del filtrado, se puede exportar a archivos con diferentes formatos:
  - CSV
  - TXT
  - Markdown
  - Base de datos SQLITE

---

# **Notas:**

- Puedes crear notas automáticas en función de palabras clave preestablecidas en fichero **"notes_config.json"**

  - El fichero **"notes_config.json"** se encuentra en el directorio de la aplicación. Si no existe, se creará uno por defecto.
  - El fichero **"notes_config.json"** se puede editar con cualquier editor de texto.
  - El fichero **"notes_config.json"** tiene la siguiente estructura:

  ```json
  [
      {
          "keywords": ["keyword1", "keyword2"],
          "text": "text to add"
      }
  ]
  ```

  Donde:
  - **keywords**: Es una lista de palabras clave que se buscarán en el log.
  - **text**: Es el texto que se añadirá al log cuando se encuentren las palabras clave.
  
---

# **Guía de búsqueda y filtrado libre**

Esta guía explica cómo funciona el motor de búsqueda interno de la aplicación y cómo aprovechar las expresiones regulares para encontrar información específica en los logs.

## 1. Búsqueda por Palabras Clave (Regex desactivado)

Cuando la opción de **expresiones regulares** no está marcada, la aplicación procesa tu búsqueda de la siguiente manera:

1. **División por palabras**: El texto que escribes se divide en términos individuales (separados por espacios).
2. **Modo de búsqueda**: Dependiendo del valor de `search_mode` (que suele ser "AND" por defecto):
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

