"""A03 — Ingeniería de software. Fuentes: documentación oficial, estándares y el propio repositorio."""
from perfiles.definiciones import S

CLAVES_AREA = ["codigo", "software", "repositorio", "backend"]

SUBESPECIALIDADES = [
    S("S01", "arquitectura de aplicación",
      tema="la arquitectura de la aplicación (módulos del servidor, capas y dependencias entre ellos)",
      objeto="Cubre cómo se reparte el código entre app.py y los módulos (academia, documentos, fuentes, perfiles), "
             "qué depende de qué y dónde poner una función nueva sin acoplarla.",
      entradas=["la función o el módulo que se quiere agregar o mover", "los módulos actuales implicados",
                "la restricción de no romper las pruebas existentes"],
      fuentes=["app.py y los módulos del repositorio",
               "docs/audit/01-architecture-current.md y docs/06-CODING-STANDARDS.md",
               "documentación oficial de FastAPI (aplicaciones grandes y enrutadores)",
               "modelo C4 para describir arquitectura de software", "ISO/IEC/IEEE 42010"],
      entregable="propuesta de estructura con módulos, responsabilidad de cada uno, dependencias permitidas y cambio "
                 "mínimo en app.py",
      riesgos=["Un archivo único que crece sin límite y donde todo cambio genera conflictos.",
               "Importaciones circulares al separar módulos que comparten la base y la sesión."],
      comprobaciones=["Cada módulo propuesto tiene una responsabilidad y la lista de lo que puede importar.",
                      "La propuesta indica qué líneas de app.py cambian y por qué son las mínimas."],
      extraer="módulos, funciones públicas de cada uno, importaciones entre módulos, estado global compartido y "
              "puntos de extensión",
      vigencia="el patrón de enrutadores de la versión de FastAPI instalada y la estructura actual de la rama "
               "integrada",
      preguntas="¿dónde debe vivir la función nueva para no acoplarse al resto?; ¿qué dependencias entre módulos "
                "sobran?",
      opciones="un bloque marcado en app.py, un enrutador en módulo propio con dependencias inyectadas o un paquete "
               "con contrato público",
      claves=["arquitectura de aplicacion", "arquitectura del codigo", "modulos", "estructura del proyecto",
              "acoplamiento", "router", "enrutador", "monolito", "refactorizar la estructura"]),
    S("S02", "dominio",
      tema="el modelo de dominio de la plataforma (conceptos del negocio jurídico y sus reglas)",
      objeto="Cubre las entidades y reglas propias: usuario y plan, consulta y cupo, conversación, caso de estudio, "
             "concepto del mapa, tipo de escrito, documento generado, fuente y vigencia.",
      entradas=["la regla de negocio o el concepto que se quiere modelar",
                "cómo lo nombra el dueño y cómo lo nombra el código", "los casos límite conocidos"],
      fuentes=["constantes y tablas de app.py, academia.py, documentos.py y fuentes.py",
               "docs/03-LEGAL-STANDARDS.md y docs/10-ACADEMIA.md", "docs/coordinacion/ESPECIFICACION-LEXCOL.md",
               "literatura de diseño guiado por el dominio (lenguaje ubicuo y agregados)"],
      entregable="glosario del dominio con entidades, atributos, reglas invariantes y estados por los que pasa cada "
                 "una",
      riesgos=["Usar la misma palabra para dos cosas: modelo jurídico (minuta) y modelo de IA (motor).",
               "Reglas de negocio repartidas entre la interfaz y el servidor con resultados distintos."],
      comprobaciones=["Cada término del glosario tiene una sola definición y el nombre que usa el código.",
                      "Cada regla invariante señala la función del servidor que la hace cumplir."],
      extraer="entidades, estados posibles, reglas de cupo y de plan, nombres usados en código y en pantalla y "
              "sinónimos conflictivos",
      vigencia="los planes, límites y estados vigentes en el código frente a los que describe la documentación",
      preguntas="¿qué reglas debe cumplir siempre esta entidad?; ¿qué términos se usan con dos sentidos?",
      opciones="unificar el término en código y pantalla, separar dos conceptos hoy mezclados o documentar la "
               "excepción",
      claves=["modelo de dominio", "reglas de negocio", "regla de negocio", "entidades del sistema", "glosario",
              "lenguaje ubicuo", "invariante"]),
    S("S03", "API",
      tema="la API HTTP de la plataforma (rutas, contratos, códigos de estado y errores)",
      objeto="Cubre el diseño de rutas, la validación del cuerpo, los códigos de estado, la paginación, el formato "
             "de error, los flujos de eventos y la compatibilidad con la interfaz y la demo.",
      entradas=["la ruta nueva o el cambio de contrato", "quién la consume (interfaz, demo, pruebas)",
                "los casos de error que debe cubrir"],
      fuentes=["rutas de app.py y docs/audit/03-api-current.md", "documentación oficial de FastAPI",
               "RFC 9110 (semántica de HTTP) y RFC 9457 (detalles de problema)", "especificación OpenAPI",
               "estándar HTML, eventos enviados por el servidor"],
      entregable="contrato de la ruta con método, entrada validada, respuesta, códigos de estado, errores y un "
                 "ejemplo de solicitud y respuesta",
      riesgos=["Cambiar un contrato sin actualizar la interfaz, la demo y las pruebas que lo consumen.",
               "Devolver 500 ante una entrada mal formada en lugar de 400."],
      comprobaciones=["Cada ruta documenta cuándo responde 400, 401, 402, 403 y 404.",
                      "Toda entrada del cuerpo se valida en el servidor con tipo y tope de tamaño."],
      extraer="rutas, métodos, campos del cuerpo, validaciones, códigos de estado devueltos, formato de error y "
              "consumidores de cada ruta",
      vigencia="el contrato vigente de cada ruta frente a lo que consumen la interfaz, la demo y las pruebas",
      preguntas="¿qué entradas inválidas puede recibir y qué responde a cada una?; ¿a quién rompe este cambio de "
                "contrato?",
      opciones="ruta nueva sin tocar las existentes, campo opcional compatible hacia atrás o versión nueva de la ruta",
      claves=["api$", "endpoint", "ruta http", "rutas de la api", "codigo de estado", "paginacion",
              "contrato de la api", "rest$", "sse$", "json de respuesta"]),
    S("S04", "persistencia",
      tema="la persistencia de datos de la aplicación (esquema, consultas e integridad)",
      objeto="Cubre el diseño de tablas e índices, las consultas parametrizadas, las operaciones atómicas, la "
             "pertenencia de cada fila a su dueño y el índice de texto completo.",
      entradas=["la tabla o consulta que se quiere crear o cambiar", "los datos que guarda y quién es su dueño",
                "el volumen y la frecuencia de acceso"],
      fuentes=["esquema y consultas en app.py, academia.py y fuentes.py",
               "documentación oficial de SQLite (transacciones, índices y FTS5)",
               "documentación oficial de Python (módulo sqlite3)", "docs/audit/02-database-current.md"],
      entregable="diseño de tabla o consulta con columnas, índices, dueño de cada fila, operación atómica y prueba de "
                 "aislamiento",
      riesgos=["Leer y luego escribir en dos pasos donde debe haber una sola operación atómica (cupo, estado).",
               "Construir SQL concatenando texto del usuario."],
      comprobaciones=["Toda consulta sobre datos con dueño filtra por el usuario de la sesión.",
                      "Cada descuento o cambio de estado se hace en una sola sentencia condicionada."],
      extraer="tablas, columnas, índices, consultas con parámetros, sentencias que cambian estado y columnas sin "
              "índice usadas en filtros",
      vigencia="las funciones de SQLite disponibles en la versión del intérprete y el esquema vigente tras las "
               "migraciones al arrancar",
      preguntas="¿qué consulta puede devolver filas de otro usuario?; ¿qué operación deja datos inconsistentes si "
                "se interrumpe a la mitad?",
      opciones="sentencia única condicionada, transaccion explícita o tabla aparte con clave del dueño",
      claves=["persistencia", "base de datos", "tabla nueva", "esquema de la base", "consulta sql", "sql$",
              "indice de la tabla", "transaccion sql", "transacciones de la base", "fts5"]),
    S("S05", "pruebas",
      tema="las pruebas automatizadas del proyecto (unitarias, de API y de navegador)",
      objeto="Cubre qué se prueba y con qué doble del modelo, las pruebas de seguridad y aislamiento, las de "
             "navegador con política de contenido estricta y lo que queda sin cubrir.",
      entradas=["la función o el cambio que debe probarse", "las pruebas existentes relacionadas",
                "los casos límite y de error conocidos"],
      fuentes=["tests/conftest.py y tests/test_*.py", "tests/e2e_*.py (pruebas de navegador)",
               "documentación oficial de pytest", "documentación oficial de Playwright para Python",
               "docs/09-QUALITY-CHECKLIST.md"],
      herramientas={"ejecutor_pruebas": "F05"},
      entregable="plan de pruebas con casos normales, de frontera, de error y de aislamiento, y el archivo donde vive "
                 "cada uno",
      riesgos=["Una prueba que pasa con el doble del modelo no dice nada de la calidad del modelo real.",
               "Pruebas que comparten estado y pasan o fallan según el orden."],
      comprobaciones=["Cada caso indica entrada, resultado esperado y el archivo de prueba que lo cubre.",
                      "El plan incluye un caso sin sesión, uno de recurso ajeno y uno de fallo del modelo."],
      extraer="pruebas existentes por módulo, dobles usados, casos sin cubrir, pruebas dependientes del orden y "
              "tiempos de ejecución",
      vigencia="las versiones de pytest y Playwright fijadas y el número de pruebas que pasa en la rama base",
      preguntas="¿qué comportamiento importante no tiene prueba?; ¿qué prueba pasa hoy sin comprobar lo que dice "
                "comprobar?",
      opciones="prueba de API con el doble del modelo, prueba de navegador de extremo a extremo o prueba de "
               "propiedad sobre datos generados",
      claves=["pruebas automatizadas", "pruebas unitarias", "pytest", "tests$", "cobertura de pruebas",
              "playwright", "prueba unitaria", "e2e$", "doble de prueba", "caso de prueba", "plan de pruebas"]),
    S("S06", "mantenibilidad",
      tema="la mantenibilidad del código (legibilidad, duplicación, tamaño y deuda técnica)",
      objeto="Cubre la complejidad de funciones y archivos, el código duplicado, los nombres, los comentarios que "
             "explican el porqué y la deuda técnica anotada con su costo.",
      entradas=["el archivo o la función que cuesta cambiar", "el cambio reciente que resultó difícil",
                "los estándares de código del proyecto"],
      fuentes=["docs/06-CODING-STANDARDS.md", "código del repositorio (app.py, documentos.py, static/app.js)",
               "ISO/IEC 25010, característica de mantenibilidad", "PEP 8 y PEP 257 (estilo y cadenas de documentación)"],
      entregable="informe de deuda técnica con el punto débil, su efecto, el cambio propuesto, el riesgo de tocarlo y "
                 "su prioridad",
      riesgos=["Reescribir por gusto algo que funciona y está probado.",
               "Refactorizar sin pruebas que protejan el comportamiento actual."],
      comprobaciones=["Cada punto de deuda indica archivo, líneas, efecto concreto y la prueba que protege el cambio.",
                      "Ningún cambio propuesto altera el comportamiento sin decirlo."],
      extraer="funciones largas, bloques duplicados, constantes repetidas, nombres inconsistentes y comentarios "
              "desactualizados",
      vigencia="los estándares de código vigentes del proyecto y las convenciones de la versión de Python en uso",
      preguntas="¿qué parte del código encarece cada cambio?; ¿qué refactorización es segura con las pruebas "
                "actuales?",
      opciones="extraer a un módulo con pruebas, dejar una nota de deuda con fecha o no tocar por falta de protección",
      claves=["mantenibilidad", "deuda tecnica", "refactor", "codigo duplicado", "legibilidad", "codigo limpio",
              "complejidad del codigo", "pep 8", "estilo de codigo"]),
    S("S07", "versiones",
      tema="el control de versiones y las entregas (ramas, commits, fusiones y numeración)",
      objeto="Cubre la estrategia de ramas, el contenido de cada commit, la resolución de conflictos en archivos "
             "compartidos, la numeración de entregas y el registro de cambios.",
      entradas=["las ramas o cambios que deben integrarse", "los archivos compartidos con riesgo de conflicto",
                "el estado de las pruebas en cada rama"],
      fuentes=["historial de git del repositorio y docs/coordinacion/PUL-001-estado-del-proyecto.md",
               "documentación oficial de Git", "especificación de Versionado Semántico",
               "convención Keep a Changelog"],
      entregable="plan de integración con orden de fusión, conflictos previstos, pruebas por correr tras cada fusión y "
                 "punto de retorno",
      riesgos=["Fusionar una rama incompleta porque sus pruebas unitarias pasan.",
               "Resolver un conflicto conservando un lado y perdiendo el cambio del otro."],
      comprobaciones=["El plan fija el orden de fusión y la batería que debe pasar tras cada paso.",
                      "Cada rama indica su commit, su estado (terminada o incompleta) y quién la revisó."],
      extraer="ramas existentes, commit de cada una, archivos modificados en común y pruebas que pasan y fallan por "
              "rama",
      vigencia="el commit actual de la rama base y qué ramas siguen sin fusionar según el informe de estado",
      preguntas="¿en qué orden conviene fusionar para reducir conflictos?; ¿qué rama no debe fusionarse todavía y "
                "por qué?",
      opciones="fusión por orden de dependencia, rebase de la rama corta sobre la base o integración parcial detrás "
               "de un interruptor",
      claves=["control de versiones", "git$", "rama de git", "ramas sin fusionar", "branch", "commit", "merge",
              "fusionar ramas", "conflicto de fusion", "versionado", "changelog", "pull request"]),
    S("S08", "migraciones",
      tema="las migraciones de esquema y de datos (cambiar la base sin perder información)",
      objeto="Cubre los cambios de esquema sobre una base con datos, las migraciones al arrancar, el paso de SQLite "
             "a una base gestionada y la verificación de que nada se perdió.",
      entradas=["el cambio de esquema o de motor que se necesita",
                "el volumen y la sensibilidad de los datos existentes", "la ventana de mantenimiento disponible"],
      fuentes=["migraciones al arrancar en app.py", "docs/audit/10-migration-plan.md",
               "documentación oficial de SQLite (ALTER TABLE y sus límites)",
               "documentación oficial de PostgreSQL (tipos y carga de datos)"],
      entregable="guion de migración con respaldo previo, pasos, verificación por conteos y sumas de control y "
                 "procedimiento de reversa",
      riesgos=["Migrar sin copia previa ni forma de volver atrás.",
               "Diferencias de tipos y fechas entre SQLite y el motor de destino que cambian datos en silencio."],
      comprobaciones=["El guion compara conteos por tabla y una suma de control antes y después.",
                      "Existe un paso de reversa ensayado o la declaración de que no lo hay."],
      extraer="tablas y columnas afectadas, migraciones ya aplicadas al arrancar, datos nulos o inconsistentes y "
              "partes del código que dependen del esquema",
      vigencia="el esquema efectivo de la base en producción frente al que crea el código y los límites de ALTER "
               "TABLE en la versión de SQLite",
      preguntas="¿qué datos pueden perderse o cambiar en la migración?; ¿cómo se comprueba que el resultado está "
                "completo?",
      opciones="migración al arrancar, guion único con ventana de mantenimiento o escritura doble temporal con corte "
               "posterior",
      claves=["migracion de datos", "migracion de esquema", "migrar la base", "migraciones de la base", "alter table", "cambio de esquema", "postgres",
              "supabase", "pasar de sqlite"]),
    S("S09", "dependencias",
      tema="las dependencias externas del proyecto (librerías, versiones fijadas y licencias)",
      objeto="Cubre las librerías de Python y las del navegador servidas por CDN, las versiones fijadas, las "
             "huellas de integridad, las vulnerabilidades conocidas y las licencias.",
      entradas=["la librería que se quiere agregar, actualizar o quitar", "los archivos de dependencias actuales",
                "el motivo del cambio (función, seguridad o soporte)"],
      fuentes=["requirements.txt, requirements.lock y requirements-dev.txt",
               "etiquetas de script con integridad en static/index.html", "docs/audit/08-dependencies-current.md",
               "índice oficial de paquetes de Python y notas de versión de cada librería",
               "especificación Subresource Integrity del W3C"],
      herramientas={"escaner_dependencias": "F04 F05"},
      entregable="ficha de dependencia con versión actual y propuesta, cambios incompatibles, licencia, avisos de "
                 "seguridad y prueba de regresión",
      riesgos=["Subir una versión mayor sin leer sus cambios incompatibles.",
               "Cargar una librería del CDN sin huella de integridad."],
      comprobaciones=["Cada dependencia indica versión fijada, licencia y fecha de la última revisión de avisos.",
                      "Toda librería del navegador cargada de terceros lleva huella de integridad."],
      extraer="paquetes y versiones fijadas, dependencias transitivas, librerías del CDN con su huella y "
              "dependencias opcionales comentadas",
      vigencia="la última versión estable de cada librería, su calendario de soporte y los avisos de seguridad "
               "publicados",
      preguntas="¿qué dependencia está sin soporte o con avisos abiertos?; ¿qué se rompe al actualizarla?",
      opciones="actualizar con pruebas de regresión, fijar la versión actual con aviso documentado o reemplazar la "
               "librería",
      claves=["dependencias del proyecto", "libreria", "requirements", "pip$", "actualizar version", "paquete de python",
              "cdn$", "licencia de software", "vulnerabilidad conocida"]),
    S("S10", "documentación",
      tema="la documentación técnica del proyecto (qué existe, para quién y si dice la verdad)",
      objeto="Cubre el README, los documentos numerados de docs/, las guías de uso y mantenimiento y la "
             "correspondencia entre lo que dicen y lo que el código hace.",
      entradas=["el documento que se quiere escribir o corregir", "el público (dueño, desarrollador u operador)",
                "el código o la función que describe"],
      fuentes=["README.md y docs/ del repositorio", "docs/coordinacion/ (estado, tablero y especificación)",
               "marco Diátaxis para organizar documentación técnica", "especificación CommonMark"],
      entregable="documento técnico con propósito, público, pasos reproducibles, límites declarados y estado real de "
                 "cada función",
      riesgos=["Documentar como terminada una función futura.",
               "Instrucciones que nadie ejecutó tal como están escritas."],
      comprobaciones=["Cada comando o ruta citada existe en el repositorio tal como se escribe.",
                      "Cada función descrita lleva su estado real y lo no verificado se marca como tal."],
      extraer="documentos existentes, afirmaciones sobre el estado de cada función, comandos citados y secciones "
              "desactualizadas frente al código",
      vigencia="la fecha y el commit sobre los que se escribió cada documento frente al estado actual del código",
      preguntas="¿qué afirma la documentación que el código no hace?; ¿qué necesita saber el lector y no encuentra?",
      opciones="corregir el documento existente, escribir una guía nueva por público o retirar el documento "
               "desactualizado",
      claves=["documentacion tecnica", "readme", "guia de uso", "manual tecnico", "documentar el",
              "guia de mantenimiento", "instructivo", "documentacion del proyecto"]),
]
