"""A04 — Programación y experiencia de usuario. Fuentes: documentación oficial, estándares y el repositorio."""
from perfiles.definiciones import S, VERIFICAR

CLAVES_AREA = ["programacion", "programar", "javascript", "python", "experiencia de usuario", "ux$"]

SUBESPECIALIDADES = [
    S("S01", "interfaz",
      tema="la interfaz de la aplicación (vistas, navegación y componentes en HTML, CSS y JavaScript sin compilación)",
      objeto="Cubre la estructura de vistas, la navegación en escritorio y celular, los componentes reutilizables, "
             "los tokens de diseño de tema.css y la regla de no usar JavaScript en línea.",
      entradas=["la pantalla o el componente que se quiere crear o cambiar",
                "el ancho de pantalla y el tema donde debe verse", "el comportamiento esperado al interactuar"],
      fuentes=["static/index.html, static/app.js y static/tema.css",
               "docs/04-UX-UI-GUIDELINES.md y docs/12-DISENO-Y-APARIENCIA.md", "MDN Web Docs (HTML, CSS y DOM)",
               "especificación Content Security Policy del W3C"],
      entregable="especificación de la vista con estructura, estados (vacío, cargando, error y con datos), "
                 "comportamiento a 390 px y tokens usados",
      riesgos=["Un manejador en línea o un color fuera de los tokens rompe la política de contenido o el tema.",
               "Diseñar solo el estado con datos y olvidar vacío, cargando y error."],
      comprobaciones=["La vista define sus estados vacío, cargando, error y con datos.",
                      "No hay desbordamiento horizontal a 390 px ni JavaScript en línea."],
      extraer="vistas y botones de navegación, clases y tokens usados, acciones registradas en el despachador y "
              "textos visibles",
      vigencia="los tokens semánticos vigentes en tema.css y las reglas de la política de contenido que hoy envía el "
               "servidor",
      preguntas="¿qué ve el usuario en cada estado de la vista?; ¿cabe y se entiende en un celular de 390 px?",
      opciones="vista propia en la navegación, sección dentro de una vista existente o ventana modal para una tarea "
               "corta",
      claves=["interfaz", "vista nueva", "boton", "barra de navegacion", "css$", "html$", "tema.css",
              "componente visual", "frontend", "diseno de la pantalla", "ui$"]),
    S("S02", "servicios",
      tema="los servicios del servidor (funciones que atienden cada ruta y su lógica)",
      objeto="Cubre la implementación de las funciones del servidor: validar la entrada, comprobar sesión y cupo, "
             "llamar al modelo o a la base, manejar el fallo y responder.",
      entradas=["el comportamiento que debe implementarse", "la ruta y los datos que recibe",
                "las reglas de cupo, plan y dueño que aplican"],
      fuentes=["funciones de ruta en app.py", "documentación oficial de FastAPI y Starlette",
               "documentación oficial de Python (excepciones, contextlib y tipos)", "docs/06-CODING-STANDARDS.md"],
      entregable="implementación descrita paso a paso: validación, autorización, operación, tratamiento del fallo, "
                 "reintegro y respuesta",
      riesgos=["Descontar la consulta y no reintegrarla cuando el modelo falla.",
               "Bloquear el ciclo de eventos con una llamada larga dentro de una función asíncrona."],
      comprobaciones=["Cada camino de error devuelve un código definido y deja el cupo como estaba.",
                      "La función comprueba sesión y dueño antes de leer o escribir."],
      extraer="orden de validaciones, llamadas al modelo y a la base, bloques de excepción, reintegros y datos que "
              "devuelve",
      vigencia="la firma vigente de las funciones auxiliares que reutiliza y el comportamiento de la versión de "
               "FastAPI instalada",
      preguntas="¿qué ocurre en cada punto donde la operación puede fallar?; ¿qué función existente ya hace parte "
                "del trabajo?",
      opciones="reutilizar una función auxiliar existente, escribir una nueva con sus pruebas o dividir la ruta en "
               "dos pasos",
      claves=["servicio del servidor", "logica del servidor", "funcion del backend", "implementar la ruta",
              "fastapi", "manejo de errores", "reintegro", "cupo de consultas"]),
    S("S03", "conectores",
      tema="los conectores de la plataforma hacia fuentes externas de contenido (Drive, sitios oficiales, correo)",
      objeto="Cubre el código que trae contenido de fuera: listado y descarga desde Drive, búsqueda web "
             "restringida y envío de correo, con paginación, reanudación y permisos.",
      entradas=["la fuente externa que se quiere conectar",
                "el tipo de acceso disponible (cuenta de servicio, clave o conector del asistente)",
                "el volumen y los formatos esperados"],
      fuentes=["scripts/ingesta_corpus.py y scripts/cosechar_inventario_drive.py",
               "herramienta web y lista de dominios en app.py y fuentes.py",
               "documentación oficial de la API de Google Drive (archivos, paginación y accesos directos)",
               "documentación de la herramienta de búsqueda web del proveedor del modelo"],
      herramientas={"conector_drive": "F03"},
      entregable="diseño del conector con permisos mínimos, paginación completa, reanudación, registro de errores y "
                 "elementos excluidos con su motivo",
      riesgos=["Afirmar que se recorrió todo cuando el listado quedó a medias por paginación.",
               "Seguir accesos directos sin control y entrar en ciclos."],
      comprobaciones=["El conector registra por carpeta si el listado está completo o a medias.",
                      "Cada elemento no procesado queda en el inventario con su motivo."],
      extraer="identificadores estables, rutas, tipos de archivo, tamaños, fechas, permisos, páginas pendientes y "
              "errores por elemento",
      vigencia="la versión de la API de Drive en uso, los alcances de permiso concedidos y la lista vigente de "
               "dominios oficiales",
      preguntas="¿qué parte de la fuente quedó sin recorrer y por qué?; ¿qué permiso mínimo necesita el conector?",
      opciones="cuenta de servicio con solo lectura, sincronización manual de una carpeta local o cosecha por "
               "sesiones reanudables",
      claves=["conector", "google drive", "drive$", "sincronizar carpeta", "cuenta de servicio", "ingesta desde",
              "descargar archivos", "inventario de drive"]),
    S("S04", "tareas asíncronas",
      tema="las tareas asíncronas y de larga duración (flujos por pasos, eventos en vivo y trabajos programados)",
      objeto="Cubre la ejecución por pasos con eventos enviados por el servidor, las llamadas largas al modelo, los "
             "trabajos periódicos y qué ocurre si el usuario cierra la página a mitad.",
      entradas=["la tarea larga o periódica que se necesita", "cuánto tarda y qué pasa si se interrumpe",
                "si el resultado debe verse en vivo"],
      fuentes=["ejecución de flujos por pasos en app.py",
               "documentación oficial de Python (asyncio y concurrent.futures)",
               "documentación de Starlette (respuestas en flujo y tareas en segundo plano)",
               "estándar HTML, eventos enviados por el servidor", "docs/13-AUTOMATIZADOR.md"],
      entregable="diseño de la tarea con pasos, estado guardado tras cada paso, comportamiento ante corte, reintegro "
                 "de cupo y reanudación",
      riesgos=["Perder el resultado parcial si la conexión se corta antes del final.",
               "Ejecutar dos veces la misma tarea por un doble clic o un reintento."],
      comprobaciones=["Tras cada paso queda guardado lo producido y el cupo consumido coincide con los pasos terminados.",
                      "Una tarea ya ejecutada no vuelve a ejecutarse con la misma orden."],
      extraer="pasos, eventos emitidos, puntos de guardado, consumo de cupo por paso, tratamiento del corte y "
              "estados de la tarea",
      vigencia="el comportamiento de las respuestas en flujo en la versión de Starlette instalada y el tiempo máximo "
               "que permite el proxy",
      preguntas="¿qué queda guardado si la tarea se corta en el tercer paso?; ¿puede ejecutarse dos veces la misma "
                "orden?",
      opciones="flujo de eventos en la misma solicitud, trabajo en segundo plano con consulta de estado o tarea "
               "programada externa",
      claves=["asincron", "tarea larga", "segundo plano", "background", "cola de tareas", "tarea programada",
              "cron$", "flujo por pasos", "streaming", "eventos en vivo"]),
    S("S05", "formularios",
      tema="los formularios de la aplicación (campos, validación y mensajes de error)",
      objeto="Cubre los formularios generados desde el catálogo de escritos y los de cuenta: tipos de campo, "
             "obligatoriedad, validación en navegador y en servidor y mensajes accesibles.",
      entradas=["el formulario o campo que se quiere crear o corregir", "las reglas de validación del dato",
                "el error que hoy ve el usuario"],
      fuentes=["definición de campos y validación en documentos.py",
               "formularios dinámicos en static/documentos.js", "MDN Web Docs (formularios y validación)",
               "WCAG 2.2, criterios de identificación y sugerencia de errores"],
      entregable="especificación del formulario con campos, tipo, obligatoriedad, regla de validación en servidor y "
                 "mensaje de error de cada uno",
      riesgos=["Validar solo en el navegador: el servidor recibe cualquier cosa.",
               "Mensajes de error que no dicen qué campo corregir ni cómo."],
      comprobaciones=["Cada campo tiene etiqueta visible, regla de validación en servidor y mensaje de error propio.",
                      "El error se anuncia al lector de pantalla y lleva el foco al primer campo inválido."],
      extraer="campos, tipos, topes de longitud, obligatorios, reglas de validación en cliente y servidor y textos "
              "de ayuda y de error",
      vigencia="los tipos de campo y topes vigentes en documentos.py y los atributos de validación que soportan los "
               "navegadores objetivo",
      preguntas="¿qué dato inválido acepta hoy el servidor?; ¿entiende el usuario qué debe corregir?",
      opciones="validación compartida entre cliente y servidor, campo guiado con opciones cerradas o dato opcional "
               "marcado para completar después",
      claves=["formulario", "campo obligatorio", "validacion de campos", "mensaje de error del campo", "input$",
              "campos del formulario"]),
    S("S06", "generación documental",
      tema="la generación de documentos (del formulario al borrador y a Word)",
      objeto="Cubre el recorrido del automatizador: instrucciones por tipo de escrito, datos del formulario "
             "tratados como datos, marcas de campos pendientes, lista de verificación y exportación a Word.",
      entradas=["el tipo de escrito o la plantilla involucrada", "los datos del formulario de ejemplo",
                "el defecto observado en el borrador o en el archivo Word"],
      fuentes=["documentos.py (catálogo, instrucciones, separación de la respuesta y exportación)",
               "docs/13-AUTOMATIZADOR.md", "documentación oficial de python-docx", "ECMA-376 (Office Open XML)"],
      entregable="especificación de generación de un tipo de escrito: estructura, campos, marcas de pendiente, "
                 "advertencias y resultado esperado en Word",
      riesgos=["Que el modelo complete con datos inventados lo que el formulario dejó vacío.",
               "Que el archivo Word pierda numeración, tablas o el rótulo de borrador."],
      comprobaciones=["Todo dato ausente en el formulario aparece entre corchetes y en la lista de verificación.",
                      "El archivo Word conserva títulos, listas y el rótulo de borrador cuando aplica."],
      extraer="estructura del tipo de escrito, campos y su uso en las instrucciones, marcas de pendiente, "
              "advertencias y elementos que convierte la exportación",
      vigencia="la versión de python-docx instalada y las notas de forma vigentes del tipo de escrito en el catálogo",
      preguntas="¿qué parte del borrador sale de los datos y cuál del modelo?; ¿qué se pierde al pasar de Markdown "
                "a Word?",
      opciones="plantilla fija con variables, redacción por el modelo con estructura obligatoria o combinación con "
               "secciones bloqueadas",
      claves=["generacion documental", "generador de escritos", "automatizador", "exportar a word", "docx",
              "python-docx", "plantilla del documento", "borrador en word"]),
    S("S07", "búsqueda",
      tema="la búsqueda dentro de la aplicación (catálogo, corpus y biblioteca)",
      objeto="Cubre la búsqueda por texto en el catálogo de escritos y en el corpus: normalización sin tildes, "
             "términos y raíces, orden por relevancia, filtros y qué mostrar cuando no hay resultados.",
      entradas=["la consulta que no encuentra lo esperado",
                "el conjunto donde se busca (catálogo, corpus o biblioteca)",
                "el resultado que debería aparecer primero"],
      fuentes=["búsqueda del catálogo en documentos.py y del corpus en fuentes.py",
               "documentación oficial de SQLite FTS5 (consultas, bm25 y tokenizadores)",
               "docs/11-MOTOR-DE-FUENTES.md", "anexo de Unicode sobre formas de normalización"],
      entregable="especificación de búsqueda con normalización, campos consultados, orden, filtros, respuesta sin "
                 "resultados y consultas de prueba con su resultado esperado",
      riesgos=["Una coincidencia literal no prueba que el documento sea pertinente.",
               "Devolver nombres o extractos de documentos a los que el usuario no tiene acceso."],
      comprobaciones=["Cada consulta de prueba indica el resultado esperado en primer lugar y el obtenido.",
                      "La búsqueda aplica los permisos antes de devolver nombres o fragmentos."],
      extraer="campos indexados, reglas de normalización, palabras vacías, fórmula de orden, filtros disponibles y "
              "consultas sin resultado",
      vigencia="el tokenizador y las opciones de FTS5 disponibles en la versión de SQLite del intérprete",
      preguntas="¿por qué esta consulta no devuelve el documento esperado?; ¿qué ve el usuario cuando no hay "
                "resultados?",
      opciones="ajustar normalización y raíces, añadir sinónimos jurídicos o combinar texto completo con búsqueda "
               "semántica",
      claves=["busqueda en la app", "buscador", "no encuentra resultados", "resultados de busqueda", "relevancia",
              "bm25", "filtros de busqueda", "tokenizador"]),
    S("S08", "accesibilidad",
      tema="la accesibilidad de la interfaz (teclado, lector de pantalla, contraste y texto)",
      objeto="Cubre el uso solo con teclado, los nombres accesibles y roles, el orden de foco, el contraste de cada "
             "tema, el tamaño de texto y que el estado no dependa solo del color.",
      entradas=["la pantalla o el componente por evaluar", "el tema y el tamaño de texto en uso",
                "la dificultad reportada por un usuario"],
      fuentes=["WCAG 2.2 del W3C", "WAI-ARIA y guía de prácticas de autoría del W3C",
               "static/index.html y static/tema.css", "scripts/contraste_temas.py y docs/12-DISENO-Y-APARIENCIA.md",
               "Ley 1618 de 2013, derechos de las personas con discapacidad " + VERIFICAR],
      entregable="informe de accesibilidad con criterio incumplido, elemento, efecto para la persona y corrección "
                 "propuesta",
      riesgos=["Comunicar un estado solo con color.",
               "Declarar accesible una pantalla sin recorrerla con teclado y lector de pantalla."],
      comprobaciones=["Cada hallazgo cita el criterio de WCAG, el elemento y cómo reproducirlo.",
                      "Todo control tiene nombre accesible y se alcanza y activa con el teclado."],
      extraer="controles sin etiqueta, roles y atributos ARIA, orden de foco, pares de color con su contraste y "
              "estados comunicados solo con color",
      vigencia="la versión de WCAG tomada como referencia y los ratios de contraste medidos de cada tema",
      preguntas="¿puede completarse la tarea solo con teclado?; ¿qué información se pierde sin ver los colores?",
      opciones="corregir el marcado y las etiquetas, añadir texto junto al color o rediseñar el componente con un "
               "patrón accesible conocido",
      claves=["accesibilidad", "lector de pantalla", "navegar con teclado", "contraste", "wcag", "aria$",
              "orden de foco", "discapacidad visual", "accesible"]),
    S("S09", "diagnóstico de errores",
      tema="el diagnóstico de errores de la aplicación (reproducir, aislar y explicar la causa)",
      objeto="Cubre los errores del navegador y del servidor: cómo reproducirlos, qué registro o código los "
             "identifica, cuál es la causa raíz y qué prueba evita que vuelvan.",
      entradas=["el mensaje o código de error y cuándo aparece", "los pasos para reproducirlo",
                "el navegador, la cuenta de prueba y la versión del código"],
      fuentes=["manejo de errores y códigos de error en app.py",
               "consola y red de las herramientas de desarrollo del navegador",
               "documentación oficial de Python (trazas y excepciones)", "pruebas existentes en tests/"],
      herramientas={"registro_logs": "F03 F05"},
      entregable="informe de diagnóstico con pasos de reproducción, causa raíz, alcance, corrección propuesta y "
                 "prueba de regresión",
      riesgos=["Corregir el síntoma sin haber reproducido el error.",
               "Atribuir la causa sin una evidencia que la distinga de las alternativas."],
      comprobaciones=["El informe incluye pasos que reproducen el error en un ambiente limpio.",
                      "La causa señalada explica todos los síntomas observados y descarta las alternativas."],
      extraer="mensaje exacto, código de error, ruta y solicitud implicadas, traza, pasos de reproducción y cambios "
              "recientes relacionados",
      vigencia="la versión del código y de las dependencias donde ocurre el error y si ya fue corregido en otra rama",
      preguntas="¿se reproduce siempre y con qué pasos mínimos?; ¿qué cambio lo introdujo?",
      opciones="corrección puntual con prueba de regresión, reversa del cambio que lo introdujo o mitigación "
               "temporal con aviso",
      claves=["error en la app", "bug", "no funciona la", "se rompe", "traza", "excepcion no controlada",
              "error 500", "depurar", "pantalla en blanco", "error de consola", "causa raiz"]),
    S("S10", "optimización",
      tema="la optimización del código y de los recursos (hacer lo mismo con menos tiempo, tokens o datos)",
      objeto="Cubre la reducción de trabajo repetido: consultas, llamadas al modelo, tamaño de instrucciones, "
             "recursos estáticos y cálculo en el navegador, sin cambiar el resultado.",
      entradas=["la operación costosa que se quiere reducir", "su medición actual (tiempo, tokens o peso)",
                "lo que no puede cambiar en el resultado"],
      fuentes=["código de la operación en el repositorio",
               "documentación de la API del proveedor del modelo (caché de instrucciones y conteo de tokens)",
               "documentación oficial de Python (perfilado con cProfile)",
               "MDN Web Docs (carga y caché de recursos)"],
      entregable="propuesta de optimización con medición de partida, cambio, ahorro esperado y prueba de que el "
                 "resultado no cambia",
      riesgos=["Optimizar lo que no es el cuello de botella.",
               "Ganar velocidad cambiando el resultado sin advertirlo."],
      comprobaciones=["La propuesta trae la medición antes del cambio y la forma de medir después.",
                      "Una prueba demuestra que el resultado es el mismo con y sin la optimización."],
      extraer="operaciones repetidas, tamaño de las instrucciones enviadas al modelo, consultas por solicitud, "
              "recursos sin caché y cálculos redundantes",
      vigencia="las condiciones vigentes de la caché de instrucciones del proveedor y los precios por token del "
               "modelo configurado",
      preguntas="¿qué trabajo se repite sin necesidad?; ¿cuánto se ahorra y qué riesgo introduce el cambio?",
      opciones="guardar en caché el resultado, reducir lo que se envía al modelo o precalcular fuera de la solicitud",
      claves=["optimizacion", "optimizar", "reducir tokens", "reducir costo", "cache$", "mas rapido",
              "perfilado", "aligerar"]),
]
