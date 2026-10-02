"""A05 — Ingeniería de inteligencia artificial. Fuentes: documentación oficial, estándares y el repositorio."""
from perfiles.definiciones import S, VERIFICAR

CLAVES_AREA = ["inteligencia artificial", "modelo de lenguaje", "llm$", "ia generativa", "el motor de ia"]

SUBESPECIALIDADES = [
    S("S01", "ingesta",
      tema="la ingesta de documentos al corpus (lectura, troceo e indexación con procedencia)",
      objeto="Cubre el recorrido de carpetas, la lectura de PDF, DOCX y texto, las exclusiones de material de "
             "clientes, el troceo en fragmentos y el registro de origen, fecha y estado de cada fuente.",
      entradas=["la carpeta o colección que se quiere cargar", "los formatos y el volumen aproximado de archivos",
                "las reglas de exclusión que deben respetarse"],
      fuentes=["scripts/ingesta_corpus.py y fuentes.py del repositorio", "docs/11-MOTOR-DE-FUENTES.md",
               "biblioteca/inventario.json y scripts/cosechar_inventario_drive.py",
               "documentación oficial de SQLite FTS5",
               "documentación oficial de la API de Google Drive (listado, paginación y exportación)"],
      herramientas={"conector_drive": "F03 F07"},
      entregable="plan de ingesta por lotes con cantidades por estado (encontrado, leído, extraído, indexado, "
                 "excluido) y motivo de cada exclusión",
      riesgos=["Contar como indexado un archivo que solo fue encontrado o leído a medias.",
               "Indexar un escrito con datos de una persona real porque el nombre del archivo no lo delataba."],
      comprobaciones=["Las cantidades se dan por estado y el denominador se declara provisional si el universo no "
                      "está enumerado.",
                      "Cada archivo excluido o fallido conserva su motivo y sigue visible en el inventario."],
      extraer="archivos por formato, tamaño y fecha, exclusiones con su motivo, fragmentos generados por documento "
              "y errores de lectura",
      vigencia="la versión del índice y del troceo con que se cargó cada fuente y la fecha del archivo frente a la "
               "de la última ingesta",
      preguntas="¿qué parte del universo documental quedó realmente indexada?; ¿qué archivos se excluyeron y por "
                "qué regla?",
      opciones="carga completa por carpetas, carga incremental solo de lo cambiado o una muestra representativa "
               "antes de ampliar",
      claves=["ingesta", "cargar el corpus", "indexar documentos", "indexacion", "troceo", "fragmentos del corpus",
              "subir documentos al indice", "cargar la biblioteca", "ingestar"]),
    S("S02", "OCR",
      tema="el reconocimiento de texto en documentos escaneados (OCR) y la calidad de lo extraído",
      objeto="Cubre la detección de PDF sin capa de texto, la elección de un motor de OCR, la medición de la "
             "calidad del resultado y el registro de las incertidumbres por página.",
      entradas=["los documentos escaneados o una muestra de ellos", "el idioma y el tipo de documento",
                "el uso que tendrá el texto (búsqueda, cita literal o cálculo)"],
      fuentes=["extracción de PDF en scripts/ingesta_corpus.py", "docs/11-MOTOR-DE-FUENTES.md",
               "documentación oficial del motor de OCR que se evalúe (p. ej. Tesseract)",
               "documentación oficial de la API del proveedor del modelo sobre lectura de PDF e imágenes",
               "especificación ISO 32000 (PDF) sobre capas de texto"],
      herramientas={"ocr": "*"},
      entregable="protocolo de OCR con criterio para detectar escaneos, motor propuesto, medida de calidad por "
                 "página y tratamiento de las páginas dudosas",
      riesgos=["Citar literalmente un texto reconocido con errores como si fuera el original.",
               "Confundir cifras, fechas o números de artículo mal reconocidos con datos ciertos."],
      comprobaciones=["Cada página lleva una medida de calidad y las dudosas quedan marcadas para revisión humana.",
                      "Ninguna cifra, fecha o número de norma salido de OCR se usa sin cotejo con la imagen."],
      extraer="páginas sin capa de texto, idioma, resolución, zonas ilegibles, tablas y sellos, y la confianza "
              "reportada por el motor",
      vigencia="la versión del motor de OCR y de sus datos de idioma con que se procesó cada documento",
      preguntas="¿qué documentos del corpus son escaneos sin texto?; ¿la calidad alcanza para cita literal o solo "
                "para búsqueda?",
      opciones="motor de OCR local, lectura directa del PDF por el modelo o transcripción humana de los documentos "
               "críticos",
      claves=["ocr$", "escaneado", "escaneo", "reconocimiento de texto", "pdf sin texto", "imagen a texto",
              "tesseract", "documento escaneado", "digitalizar"]),
    S("S03", "clasificación",
      tema="la clasificación de documentos y consultas (tipo documental, área jurídica y sensibilidad)",
      objeto="Cubre las reglas y modelos que asignan tipo, área, autoridad y año a un documento, que detectan "
             "datos personales y que enrutan una consulta al especialista adecuado.",
      entradas=["los documentos o consultas por clasificar", "la taxonomía de tipos y áreas vigente",
                "ejemplos ya clasificados y revisados"],
      fuentes=["clasificar_nombre, parece_de_persona y es_excluido en fuentes.py", "enrutar_agentes en app.py",
               "perfiles/definiciones.py (intenciones y claves del coordinador)", "docs/03-LEGAL-STANDARDS.md",
               "Ley 1581 de 2012, protección de datos personales " + VERIFICAR],
      entregable="esquema de clasificación con categorías, regla o señal de cada una, casos dudosos y medida de "
                 "acierto sobre una muestra revisada",
      riesgos=["Tomar el nombre del archivo o el año del título como prueba del contenido o de la vigencia.",
               "Clasificar como ejemplo didáctico un escrito con datos reales, o al revés, sin comprobarlo."],
      comprobaciones=["Cada categoría tiene una regla explícita y un caso límite documentado.",
                      "El acierto se mide sobre una muestra revisada por una persona e indica su tamaño."],
      extraer="categorías asignadas, señal que las activó, documentos sin categoría, homónimos, duplicados y "
              "casos marcados como sensibles",
      vigencia="la versión de la taxonomía y de las reglas con que se clasificó cada elemento",
      preguntas="¿qué documentos quedan mal clasificados y por qué señal?; ¿qué casos dudosos deben quedar fuera "
                "del índice general?",
      opciones="reglas deterministas por nombre y carpeta, clasificación por el modelo con revisión de muestra o "
               "un esquema mixto con cola de dudosos",
      claves=["clasificacion de documentos", "clasificar documentos", "taxonomia", "etiquetar", "enrutar",
              "enrutamiento", "tipo documental", "detectar datos personales", "clasificador"]),
    S("S04", "búsqueda semántica",
      tema="la búsqueda semántica sobre el corpus (representaciones vectoriales y búsqueda híbrida)",
      objeto="Cubre la elección del modelo de representaciones, el almacén de vectores, la combinación con la "
             "búsqueda literal y el camino antiguo (ChromaDB y Voyage) que quedó sin configurar.",
      entradas=["las consultas que hoy no encuentran lo que deberían", "el tamaño del corpus y su crecimiento",
                "el presupuesto de costo y de latencia por consulta"],
      fuentes=["buscar_corpus en app.py y buscar en fuentes.py", "docs/02-AI-ARCHITECTURE.md y "
               "docs/11-MOTOR-DE-FUENTES.md",
               "documentación oficial del proveedor de representaciones que se evalúe",
               "documentación oficial de SQLite FTS5 (función bm25)",
               "evaluacion/golden.jsonl como conjunto de consultas de prueba"],
      herramientas={"busqueda_semantica": "*"},
      entregable="diseño de búsqueda híbrida con modelo de representaciones, almacén, fusión de resultados y "
                 "medición de recuperación frente a la búsqueda literal",
      riesgos=["Dar por pertinente un fragmento solo porque es parecido: similitud no es procedencia jurídica.",
               "Enviar texto de asuntos reales a un proveedor externo de representaciones sin revisar el "
               "tratamiento de datos."],
      comprobaciones=["La mejora se mide con consultas de prueba contra la búsqueda literal y reporta el tamaño de "
                      "la muestra.",
                      "El diseño indica qué datos salen hacia terceros y bajo qué condiciones."],
      extraer="consultas sin resultado, términos que fallan por sinónimos, tamaño de fragmentos, modelo y dimensión "
              "de los vectores y costo por documento",
      vigencia="la versión del modelo de representaciones con que se generó cada vector frente a la que hoy "
               "ofrece el proveedor",
      preguntas="¿qué consultas falla la búsqueda literal que una semántica sí resolvería?; ¿cuánto cuesta y "
                "cuánto tarda indexar y consultar?",
      opciones="seguir solo con texto completo, búsqueda híbrida con reordenamiento o expansión de la consulta "
               "con sinónimos jurídicos",
      claves=["busqueda semantica", "embeddings", "vectorial", "vectores", "chromadb", "voyage", "similitud",
              "busqueda hibrida", "reordenamiento", "base vectorial"]),
    S("S05", "recuperación con fuentes",
      tema="la recuperación con fuentes (fragmentos entregados al modelo, citas y bloque de fuentes consultadas)",
      objeto="Cubre cómo se eligen los fragmentos, cómo se entregan al modelo como datos, cómo se marcan las citas "
             "y cómo llega al usuario la lista de fuentes con su estado de vigencia.",
      entradas=["la pregunta y la respuesta que se quieren examinar", "los fragmentos que recibió el modelo",
                "la lista de fuentes mostrada al usuario"],
      fuentes=["buscar, formatear_para_modelo y para_cliente en fuentes.py",
               "bloque_corpus, envolver_como_datos y fuentes_de_respuesta en app.py", "docs/11-MOTOR-DE-FUENTES.md",
               "tests/test_fuentes.py",
               "documentación oficial de la API del proveedor del modelo (citas y resultados de búsqueda)"],
      entregable="traza de recuperación de una respuesta: fragmentos recuperados, usados y citados, afirmaciones "
                 "sin soporte y ajustes propuestos",
      riesgos=["Una cita con marca que el fragmento no respalda es peor que una afirmación sin cita.",
               "Mostrar al usuario enlaces o identificadores del Drive privado del corpus."],
      comprobaciones=["Cada marca de cita de la respuesta corresponde a un fragmento realmente entregado.",
                      "Toda afirmación material sin fragmento ni fuente oficial aparece como pendiente de "
                      "verificación."],
      extraer="fragmentos recuperados con puntaje, marcas usadas en la respuesta, afirmaciones sin marca y estado "
              "de vigencia de cada fuente",
      vigencia="el estado de vigencia registrado de cada fuente citada y la fecha de su última verificación",
      preguntas="¿qué afirmaciones de la respuesta tienen soporte en los fragmentos?; ¿se recuperó el fragmento "
                "que contenía la respuesta?",
      opciones="ajustar el umbral de términos coincidentes, cambiar el tamaño del fragmento o exigir abstención "
               "cuando no hay soporte",
      claves=["rag$", "recuperacion con fuentes", "fuentes consultadas", "citas de la respuesta", "grounding",
              "fragmentos recuperados", "sin soporte", "alucinacion", "alucina"]),
    S("S06", "selección de motores",
      tema="la selección de motores de IA (qué modelo atiende cada tarea, con qué costo y qué respaldo)",
      objeto="Cubre el registro de los motores realmente configurados, sus límites, su costo comprobado o "
             "desconocido, el tratamiento de datos y la alternativa cuando uno falla.",
      entradas=["la tarea que debe atender el motor", "los motores hoy configurados y sus variables",
                "el presupuesto por consulta y la latencia tolerable"],
      fuentes=["MODELO, opciones_modelo y los topes de tokens en app.py", ".env.example y render.yaml",
               "docs/02-AI-ARCHITECTURE.md y docs/audit/04-ai-current.md",
               "documentación oficial y lista de precios vigente del proveedor del modelo",
               "docs/coordinacion/PUL-001-estado-del-proyecto.md"],
      entregable="registro de motores con función, versión, límites, tratamiento de datos, costo comprobado o "
                 "desconocido, pruebas hechas y alternativa de fallo",
      riesgos=["Anotar un precio o una capacidad de memoria sin verificar la documentación vigente.",
               "Tratar una carpeta de minutas como si fuera un catálogo de motores de IA."],
      comprobaciones=["Cada motor indica si su costo y su latencia fueron medidos o son una estimación.",
                      "Ningún motor figura como disponible sin una variable de entorno o un código que lo use."],
      extraer="modelos nombrados en el código, variables que los cambian, topes de tokens, parámetros por modelo y "
              "lugares donde se llama a cada uno",
      vigencia="el identificador y los precios vigentes de cada modelo en la documentación del proveedor frente a "
               "los escritos en el código",
      preguntas="¿qué motor atiende hoy cada función y qué pasa si falla?; ¿qué parte del costo por consulta es "
                "medida y cuál supuesta?",
      opciones="un solo motor para todo, un motor liviano para tareas simples y otro para análisis o un proveedor "
               "alterno de respaldo",
      claves=["seleccion de modelo", "que modelo usar", "motor de ia", "sonnet", "haiku", "opus", "proveedor de ia",
              "cambiar de modelo", "costo del modelo", "modelo de respaldo"]),
    S("S07", "instrucciones",
      tema="las instrucciones de sistema de la plataforma (qué se le ordena al modelo y en qué versión)",
      objeto="Cubre la redacción, el versionado y la prueba de los mensajes de sistema del chat, del Modular Lab, "
             "del automatizador y de los perfiles, y la separación entre instrucciones y datos.",
      entradas=["la instrucción que se quiere escribir o cambiar", "el comportamiento observado y el esperado",
                "los casos de prueba que debe seguir cumpliendo"],
      fuentes=["SYSTEM_PROMPT, AGENTES y ESTILOS en app.py", "SISTEMA_BASE y SISTEMA_PLAN en documentos.py",
               "perfiles/definiciones.py (reglas de los perfiles)", "docs/03-LEGAL-STANDARDS.md",
               "documentación oficial del proveedor del modelo sobre redacción de instrucciones"],
      entregable="instrucción versionada con propósito, reglas, formato de salida, casos de prueba y comparación "
                 "contra la versión anterior",
      riesgos=["Cambiar una instrucción sin medir contra la versión anterior y empeorar sin saberlo.",
               "Meter en la instrucción un dato que cambia (fechas, cifras, vigencias) como si fuera fijo."],
      comprobaciones=["La instrucción nueva se compara con la anterior sobre los mismos casos y reporta el "
                      "resultado.",
                      "Las reglas de fuentes y de «No verificado» siguen presentes y sin contradicciones."],
      extraer="reglas vigentes, formato de salida exigido, datos variables incrustados, contradicciones entre "
              "mensajes y longitud de cada instrucción",
      vigencia="la versión de cada instrucción en el repositorio y el modelo contra el que se probó por última vez",
      preguntas="¿qué regla de la instrucción produce el comportamiento observado?; ¿qué casos de prueba deja de "
                "cumplir el cambio propuesto?",
      opciones="ajustar la regla existente, añadir un ejemplo o mover el dato variable fuera de la instrucción",
      claves=["prompt", "mensaje de sistema", "instrucciones del modelo", "system prompt", "instruccion de sistema",
              "redactar la instruccion", "versionar instrucciones", "prompt maestro"]),
    S("S08", "coordinación de agentes",
      tema="la coordinación de perfiles especializados (selección, orden de ejecución, límites y resumen auditable)",
      objeto="Cubre las reglas con que el coordinador elige pocos perfiles, el modo de ejecución declarado, los "
             "topes de llamadas, tiempo y costo, el tratamiento de discrepancias y el registro de cada ejecución.",
      entradas=["la tarea y el plan que propuso el coordinador", "el resumen auditable de la ejecución",
                "el límite de consultas y de tiempo disponible"],
      fuentes=["coordinador.py y perfiles/registro.json", "docs/16-PERFILES-Y-COORDINADOR.md",
               "docs/coordinacion/ESPECIFICACION-LEXCOL.md (secciones 6 y 7)", "tests/test_perfiles.py",
               "documentación oficial del proveedor del modelo sobre uso de herramientas"],
      entregable="revisión de un plan del coordinador: perfiles elegidos y descartados con su regla, límites "
                 "aplicados y puntos donde debe intervenir una persona",
      riesgos=["Presentar una conversación simulada entre agentes como evidencia de trabajo real.",
               "Resolver una discrepancia por mayoría en lugar de comparar hechos, fuentes y supuestos."],
      comprobaciones=["Cada perfil elegido tiene la regla que lo activó y su estado real.",
                      "El resumen declara el modo de ejecución, los recursos consumidos y si el motor fue "
                      "simulado."],
      extraer="perfiles seleccionados, regla de activación, herramientas usadas, llamadas al modelo, duración, "
              "errores y discrepancias registradas",
      vigencia="la versión del registro de perfiles y de las reglas del coordinador con que se armó el plan",
      preguntas="¿los perfiles elegidos son los mínimos útiles para la tarea?; ¿qué límite detuvo o debió detener "
                "la ejecución?",
      opciones="ejecución secuencial como hoy, paralelismo acotado con tope de concurrencia o un solo perfil con "
               "más contexto",
      claves=["coordinador", "orquestador", "multiagente", "agentes", "perfiles especializados",
              "coordinacion de agentes", "orquestacion", "subagentes", "seleccion de perfiles"]),
    S("S09", "evaluaciones",
      tema="la evaluación de calidad de la IA (conjuntos de prueba, criterios, umbrales y regresiones)",
      objeto="Cubre el conjunto de preguntas con criterios esperados, la separación entre ejemplos de mejora y "
             "de medición, las métricas, los umbrales fijados antes de medir y la comparación entre versiones.",
      entradas=["la capacidad que se quiere medir", "el conjunto de casos y sus criterios revisados",
                "el umbral de aceptación acordado"],
      fuentes=["evaluacion/benchmark.py y evaluacion/golden.jsonl", "docs/09-QUALITY-CHECKLIST.md",
               "docs/coordinacion/ESPECIFICACION-LEXCOL.md (sección 12)", "tests/test_benchmark.py",
               "NIST AI Risk Management Framework (función de medición)"],
      herramientas={"evaluador_benchmark": "F03 F05 F07"},
      entregable="informe de evaluación con métrica medida, tamaño de muestra, umbral fijado de antemano, errores "
                 "encontrados y comparación con la versión anterior",
      riesgos=["Calificar por palabras clave y presentar el resultado como calidad jurídica comprobada.",
               "Usar el número de perfiles o de agentes como si fuera una medida de calidad."],
      comprobaciones=["Cada métrica indica tamaño de muestra, motor evaluado y si el motor fue real o simulado.",
                      "El umbral de aceptación quedó escrito antes de correr la medición."],
      extraer="casos del conjunto, criterios por caso, casos trampa, resultados por criterio, fallas revisadas a "
              "mano y motor usado",
      vigencia="la versión del conjunto de evaluación, de las instrucciones y del modelo de cada corrida comparada",
      preguntas="¿qué mide de verdad la calificación automática?; ¿el cambio propuesto mejora o empeora frente a "
                "la versión anterior?",
      opciones="calificación automática por criterios, revisión humana de una muestra o un juez de IA calibrado "
               "contra revisión humana",
      claves=["evaluacion de calidad", "benchmark", "golden", "metricas de calidad", "umbral de aceptacion",
              "regresion", "medir la calidad", "conjunto de evaluacion", "evals$"]),
    S("S10", "protección frente a instrucciones maliciosas",
      tema="la protección frente a instrucciones maliciosas en documentos, páginas y mensajes",
      objeto="Cubre la inyección de instrucciones por contenido recuperado o adjunto, la separación entre datos "
             "y órdenes, la fuga del mensaje de sistema o de datos de otros usuarios y el abuso de herramientas.",
      entradas=["el punto por donde entra contenido no confiable", "el texto o documento sospechoso",
                "las herramientas y datos a los que el modelo tiene acceso en ese flujo"],
      fuentes=["envolver_como_datos y las reglas de seguridad de SYSTEM_PROMPT en app.py",
               "tests/test_seguridad.py y tests/test_fuentes.py", "docs/07-SECURITY-POLICIES.md",
               "OWASP Top 10 para aplicaciones con modelos de lenguaje",
               "docs/coordinacion/ESPECIFICACION-LEXCOL.md (sección 11)"],
      entregable="mapa de entradas no confiables con ataque posible, defensa existente, prueba que la demuestra y "
                 "brecha pendiente",
      riesgos=["Confiar en que el modelo «sabrá ignorar» la orden incrustada sin una prueba que lo muestre.",
               "Dar al flujo una herramienta con efectos (enviar, borrar, pagar) que un documento pueda accionar."],
      comprobaciones=["Cada entrada no confiable llega al modelo delimitada como datos y hay una prueba que lo "
                      "verifica.",
                      "Ningún flujo que lee contenido externo tiene una herramienta con efectos irreversibles."],
      extraer="puntos de entrada de contenido externo, delimitadores usados, herramientas disponibles en cada "
              "flujo, datos sensibles alcanzables y pruebas existentes",
      vigencia="la edición vigente de la guía OWASP citada y las recomendaciones actuales del proveedor del modelo",
      preguntas="¿por dónde puede entrar una orden ajena y qué podría lograr?; ¿qué prueba demuestra que la "
                "defensa funciona?",
      opciones="delimitar y neutralizar el contenido, reducir las herramientas del flujo o exigir confirmación "
               "humana antes de cualquier efecto",
      claves=["inyeccion de instrucciones", "prompt injection", "instrucciones maliciosas", "jailbreak",
              "documento malicioso", "fuga del prompt", "ignora las instrucciones", "contenido no confiable"]),
]
