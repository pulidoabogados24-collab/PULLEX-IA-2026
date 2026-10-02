"""A02 — Ingeniería de sistemas. Fuentes: documentación oficial, estándares y el propio repositorio."""
from perfiles.definiciones import S, VERIFICAR

CLAVES_AREA = ["ingenieria de sistemas", "plataforma", "el sistema completo"]

SUBESPECIALIDADES = [
    S("S01", "requisitos",
      tema="los requisitos de una función de la plataforma (qué debe hacer, para quién y cómo se acepta)",
      objeto="Cubre la captura de la necesidad, los requisitos funcionales y de calidad, los criterios de "
             "aceptación verificables y la trazabilidad con la especificación del dueño.",
      entradas=["la solicitud del dueño o del usuario en sus palabras", "la función existente con la que se relaciona",
                "las restricciones de plazo, costo o plan"],
      fuentes=["docs/coordinacion/ESPECIFICACION-LEXCOL.md", "docs/05-PRODUCT-ROADMAP.md y docs/00-CONSTITUTION.md",
               "ISO/IEC/IEEE 29148 (ingeniería de requisitos)", "ISO/IEC 25010 (modelo de calidad del producto)"],
      entregable="ficha de requisito con necesidad, alcance, criterios de aceptación verificables, exclusiones y "
                 "fuente de cada exigencia",
      riesgos=["Convertir una frase ambigua en requisito sin confirmarla con quien la pidió.",
               "Criterios de aceptación que no se pueden comprobar con una prueba."],
      comprobaciones=["Cada requisito cita el párrafo de la especificación o la solicitud de donde sale.",
                      "Cada criterio de aceptación se puede comprobar con una prueba o una medición concreta."],
      extraer="exigencias explícitas, restricciones, actores, criterios de aceptación mencionados y puntos "
              "contradictorios o ambiguos",
      vigencia="la versión vigente de la especificación del dueño y si una decisión posterior del tablero la cambió",
      preguntas="¿qué necesidad resuelve y para qué usuario?; ¿qué criterio verificable dirá que está terminado?",
      opciones="entregar un recorrido mínimo completo, dividir en incrementos o aplazar con la dependencia "
               "identificada",
      claves=["requisito", "requerimiento", "criterios de aceptacion", "historia de usuario",
              "alcance de la funcion", "especificacion", "que debe hacer", "necesidad del usuario"]),
    S("S02", "procesos",
      tema="los procesos de trabajo del equipo y de la plataforma (del encargo a la entrega)",
      objeto="Cubre el recorrido de una tarea desde que se pide hasta que se integra: responsable, revisor, "
             "evidencia, estados del tablero y puntos de control.",
      entradas=["el proceso o la tarea que se quiere ordenar", "quién participa y con qué herramientas",
                "los fallos o demoras observados"],
      fuentes=["docs/coordinacion/TABLERO.md y docs/08-DECISION-FRAMEWORK.md", "docs/09-QUALITY-CHECKLIST.md",
               "ISO/IEC/IEEE 12207 (procesos del ciclo de vida del software)",
               "BPMN 2.0 del Object Management Group (notación de procesos)"],
      entregable="descripción del proceso paso a paso con responsable, entrada, salida, evidencia exigida y punto de "
                 "control",
      riesgos=["Marcar una tarea como hecha sin evidencia reproducible.",
               "Un proceso que depende de la memoria de una persona y no de un registro."],
      comprobaciones=["Cada paso tiene responsable, entrada, salida y la evidencia que lo da por cumplido.",
                      "Los estados usados son los del tablero: pendiente, en curso, en revisión, hecho o bloqueada."],
      extraer="pasos, responsables, revisores, estados, evidencias exigidas, bloqueos y dependencias externas",
      vigencia="la versión actual del tablero de coordinación y de la lista de control de calidad",
      preguntas="¿en qué paso se pierde o se retrasa el trabajo?; ¿qué evidencia falta para cerrar cada tarea?",
      opciones="lista de control por tarea, revisión cruzada obligatoria o automatización del paso repetitivo",
      claves=["proceso de trabajo", "flujo de trabajo", "tablero", "responsable y revisor", "procedimiento interno",
              "bpmn$", "punto de control", "como nos organizamos"]),
    S("S03", "arquitectura empresarial",
      tema="la arquitectura de conjunto de la plataforma (capacidades, sistemas y su relación con el negocio)",
      objeto="Cubre el mapa de capacidades (consulta, academia, automatizador, biblioteca, perfiles), los sistemas "
             "que las soportan, sus dueños y la ruta de evolución.",
      entradas=["la capacidad de negocio que se quiere agregar o cambiar",
                "los sistemas y proveedores que hoy participan", "el horizonte y el presupuesto"],
      fuentes=["docs/audit/01-architecture-current.md y docs/audit/10-migration-plan.md",
               "docs/05-PRODUCT-ROADMAP.md", "estándar TOGAF de The Open Group",
               "lenguaje ArchiMate de The Open Group", "ISO/IEC/IEEE 42010 (descripción de arquitecturas)"],
      entregable="mapa de capacidades y sistemas con el estado de cada uno (propuesto, implementado, probado u "
                 "operativo) y su brecha",
      riesgos=["Dibujar como existente una capacidad que solo está propuesta.",
               "Añadir un sistema nuevo cuando uno existente ya cubre la necesidad."],
      comprobaciones=["Cada capacidad del mapa lleva su estado real y el archivo o la ruta que la implementa.",
                      "Toda brecha indica la dependencia concreta que la cierra."],
      extraer="capacidades, módulos que las implementan, proveedores externos, datos que cruzan entre módulos y "
              "decisiones pendientes del dueño",
      vigencia="el estado real de cada módulo según el último informe de estado del proyecto y las ramas sin fusionar",
      preguntas="¿qué capacidad falta y qué sistema debería asumirla?; ¿qué parte del mapa es propuesta y no "
                "implementación?",
      opciones="ampliar un módulo existente, crear un módulo nuevo con contrato claro o contratar un servicio externo",
      claves=["arquitectura empresarial", "mapa de capacidades", "arquitectura general", "togaf", "archimate",
              "vision de conjunto", "hoja de ruta tecnica", "roadmap"]),
    S("S04", "integración",
      tema="la integración de la plataforma con servicios externos (modelo, correo, Drive, base gestionada)",
      objeto="Cubre el contrato con cada servicio externo: autenticación, límites, errores, reintentos, costos y "
             "qué hace la plataforma cuando el servicio no responde.",
      entradas=["el servicio externo que se integra o que falla", "las credenciales disponibles, sin sus valores",
                "el comportamiento esperado ante errores"],
      fuentes=["llamadas al modelo y al correo en app.py", "documentación oficial de la API del proveedor del modelo",
               "documentación oficial de la API de Google Drive",
               "documentación oficial del servicio de correo transaccional", "docs/11-MOTOR-DE-FUENTES.md"],
      entregable="ficha de integración con contrato, credencial requerida, límites, tratamiento de errores, "
                 "reintegro de cupo y prueba con doble",
      riesgos=["Afirmar que una integración funciona cuando solo se probó con un doble.",
               "Reintentar sin tope una llamada que se cobra por uso."],
      comprobaciones=["La ficha distingue lo probado con doble de lo probado contra el servicio real.",
                      "Cada fallo del servicio externo tiene respuesta definida y no descuenta cupo al usuario."],
      extraer="puntos de llamada, parámetros enviados, tiempos de espera, tratamiento de excepciones, reintegros y "
              "variables de configuración",
      vigencia="la versión de la API y del SDK en uso frente a la documentación vigente del proveedor",
      preguntas="¿qué pasa con el cupo y con el usuario cuando el servicio externo falla?; ¿qué parte de la "
                "integración nunca se probó contra el servicio real?",
      opciones="llamada directa con reintegro, proveedor alterno de respaldo o cola con reintento diferido",
      claves=["integracion", "integrar con", "api externa", "proveedor externo", "sdk$", "webhook", "resend",
              "servicio externo", "credenciales"]),
    S("S05", "flujos de datos",
      tema="los flujos de datos de la plataforma (qué dato entra, por dónde pasa y dónde queda)",
      objeto="Cubre el recorrido de los datos del usuario y de los documentos: captura, envío al modelo, guardado, "
             "exposición en respuestas y eliminación.",
      entradas=["el dato o documento cuyo recorrido se quiere trazar", "las pantallas y rutas que lo tocan",
                "los terceros que lo reciben"],
      fuentes=["rutas y tablas en app.py, documentos.py y fuentes.py", "docs/audit/03-api-current.md",
               "Ley 1581 de 2012, protección de datos personales " + VERIFICAR,
               "ISO/IEC 27701 (gestión de información de privacidad)"],
      entregable="diagrama de flujo de datos con origen, tránsito, destino, tercero receptor, retención y dato "
                 "personal marcado",
      riesgos=["Enviar al modelo o a un tercero más datos de los necesarios para la tarea.",
               "Que la memoria de un caso alimente otro caso por defecto."],
      comprobaciones=["Cada dato personal del diagrama indica dónde se guarda, quién lo recibe y cuándo se borra.",
                      "Ningún flujo cruza información entre usuarios o entre asuntos sin una regla explícita."],
      extraer="campos capturados, lo que se envía al modelo, lo que se guarda en cada tabla, lo que vuelve al "
              "navegador y lo que queda en registros",
      vigencia="las condiciones vigentes de tratamiento de datos del proveedor del modelo y la política de datos "
               "publicada por la plataforma",
      preguntas="¿qué datos personales salen hacia terceros y con qué finalidad?; ¿dónde podría mezclarse "
                "información de dos usuarios o de dos asuntos?",
      opciones="minimizar lo que se envía, separar por asunto con identificador propio o anonimizar antes de salir",
      claves=["flujo de datos", "recorrido del dato", "a donde van los datos", "que se envia al modelo",
              "trazabilidad de datos", "retencion de datos", "minimizacion de datos"]),
    S("S06", "interoperabilidad",
      tema="la interoperabilidad de la plataforma (formatos e intercambio con otras herramientas)",
      objeto="Cubre los formatos de entrada y salida (Word, PDF, Markdown, JSON, hojas de cálculo), las "
             "codificaciones y los contratos para que otros sistemas lean lo que la plataforma produce.",
      entradas=["el formato o sistema con el que se debe intercambiar", "un archivo de ejemplo",
                "lo que se pierde o se daña en el intercambio"],
      fuentes=["exportación a Word en documentos.py y lectura de formatos en scripts/ingesta_corpus.py",
               "ECMA-376 e ISO/IEC 29500 (Office Open XML)", "ISO 32000 (PDF)",
               "RFC 8259 (JSON) y especificación CommonMark", "especificación OpenAPI"],
      entregable="tabla de formatos admitidos con lo que se conserva, lo que se pierde y la prueba de ida y vuelta",
      riesgos=["Dar por conservadas tablas, numeración o notas que el conversor descarta.",
               "Daños de codificación en tildes y eñes al pasar entre sistemas."],
      comprobaciones=["Cada formato indica qué elementos se conservan y cuáles no, con un archivo de prueba.",
                      "Un texto con tildes, eñes y comillas vuelve idéntico tras la ida y vuelta."],
      extraer="formatos leídos y escritos, librería usada en cada uno, elementos no soportados y codificación asumida",
      vigencia="la versión instalada de la librería de conversión y la edición del estándar de formato que implementa",
      preguntas="¿qué se pierde al exportar o importar en este formato?; ¿qué contrato necesita el otro sistema "
                "para leerlo sin intervención?",
      opciones="exportar a un formato abierto intermedio, ofrecer un contrato JSON documentado o limitar el formato "
               "a lo que se conserva sin pérdida",
      claves=["interoperabilidad", "formato docx", "exportar a", "importar desde", "csv$", "codificacion",
              "utf-8", "openapi", "intercambio de archivos", "formato de archivo"]),
    S("S07", "disponibilidad",
      tema="la disponibilidad del servicio (que esté en línea y responda)",
      objeto="Cubre el objetivo de disponibilidad, los puntos únicos de fallo, la comprobación de salud, el "
             "arranque en frío del plan de alojamiento y la degradación cuando falla el modelo.",
      entradas=["la caída o intermitencia observada", "el objetivo de disponibilidad esperado",
                "el plan de alojamiento y sus condiciones"],
      fuentes=["ruta /salud y manejo de errores en app.py",
               "documentación del proveedor sobre comprobaciones de salud, suspensión y reinicios",
               "página de estado del proveedor del modelo", "ISO/IEC 25010, característica de fiabilidad"],
      entregable="análisis de disponibilidad con objetivo, puntos únicos de fallo, comportamiento degradado y forma "
                 "de detectar la caída",
      riesgos=["Prometer un porcentaje de disponibilidad que nadie mide.",
               "Depender de un único proveedor de modelo sin respuesta alterna."],
      comprobaciones=["Cada punto único de fallo indica su efecto para el usuario y la mitigación propuesta.",
                      "El objetivo de disponibilidad va con la forma de medirlo y la ventana de medición."],
      extraer="dependencias sin las que el servicio no responde, comprobaciones de salud, mensajes al usuario ante "
              "fallo y tiempos de arranque",
      vigencia="las condiciones actuales del plan sobre suspensión por inactividad y los compromisos de servicio "
               "publicados por cada proveedor",
      preguntas="¿qué componente, al fallar, deja sin servicio a todos?; ¿qué ve el usuario cuando el modelo no "
                "responde?",
      opciones="plan sin suspensión con comprobación de salud, proveedor alterno del modelo o modo degradado sin "
               "funciones de IA",
      claves=["disponibilidad", "caida del servicio", "se cayo", "fuera de linea", "uptime",
              "punto unico de fallo", "alta disponibilidad", "el servicio no responde"]),
    S("S08", "observabilidad",
      tema="la observabilidad del servicio (registros, métricas y alertas para saber qué pasa)",
      objeto="Cubre qué se registra y con qué identificador, las métricas mínimas (errores, latencia, costo), las "
             "alertas y la protección de datos personales en los registros.",
      entradas=["el incidente o la pregunta que hoy no se puede responder",
                "los registros o códigos de error disponibles", "las métricas que ya se guardan"],
      fuentes=["configuración de registro, códigos de error y /api/admin/metricas en app.py",
               "especificación OpenTelemetry (trazas, métricas y registros)",
               "documentación oficial de Python (módulo logging)", "docs/01-ENGINEERING-STANDARDS.md"],
      herramientas={"registro_logs": "F03 F05"},
      entregable="plan de observabilidad con eventos por registrar, campos, métricas, umbrales de alerta y datos que "
                 "no deben registrarse",
      riesgos=["Registrar correos completos o texto de los casos: es dato personal.",
               "Registros que no permiten unir un error con la solicitud que lo causó."],
      comprobaciones=["Cada evento registrado define sus campos y ninguno contiene datos personales completos.",
                      "Cada alerta tiene umbral, ventana y destinatario."],
      extraer="mensajes de registro existentes, códigos de error, métricas calculadas, datos personales que aparecen "
              "y huecos sin registro",
      vigencia="la convención semántica vigente de OpenTelemetry y la retención de registros que hoy ofrece el "
               "proveedor",
      preguntas="¿qué pregunta sobre el servicio no se puede responder con lo que hoy se registra?; ¿se puede "
                "seguir un error desde el usuario hasta su causa?",
      opciones="registros estructurados con identificador de solicitud, métricas agregadas en la base o un servicio "
               "externo de monitoreo",
      claves=["observabilidad", "logs$", "registros del servidor", "metricas", "alertas", "monitoreo", "trazas",
              "telemetria", "codigo de error"]),
    S("S09", "continuidad",
      tema="la continuidad del servicio ante una interrupción grave (pérdida de datos, proveedor caído, cuenta "
           "bloqueada)",
      objeto="Cubre los escenarios de interrupción, el impacto en usuarios de pago, las funciones mínimas que deben "
             "seguir, los responsables y el guion de recuperación.",
      entradas=["el escenario de interrupción que preocupa", "las funciones que no pueden parar",
                "los contactos y accesos de emergencia disponibles"],
      fuentes=["ISO 22301 (continuidad del negocio)",
               "docs/audit/09-risks-current.md y docs/coordinacion/PUL-001-estado-del-proyecto.md",
               "documentación del proveedor de alojamiento sobre recuperación",
               "condiciones de servicio del proveedor del modelo"],
      entregable="plan de continuidad por escenario con impacto, función mínima, responsable, pasos de recuperación "
                 "y comunicación a usuarios",
      riesgos=["Un plan que depende de una sola persona con todas las claves.",
               "No haber ensayado nunca la recuperación del escenario más probable."],
      comprobaciones=["Cada escenario tiene responsable, pasos numerados y tiempo objetivo de recuperación.",
                      "El plan indica qué accesos se necesitan y dónde están resguardados, sin revelarlos."],
      extraer="escenarios ya identificados como riesgo, dependencias críticas, accesos de emergencia y obligaciones "
              "con usuarios de pago",
      vigencia="los riesgos abiertos en el último informe de estado y las condiciones vigentes de cada proveedor "
               "crítico",
      preguntas="¿qué escenario dejaría sin servicio más de un día y qué se haría?; ¿qué función mínima debe "
                "mantenerse para los usuarios de pago?",
      opciones="proveedor alterno preparado, procedimiento manual temporal o suspensión ordenada con aviso y "
               "compensación",
      claves=["continuidad", "plan de contingencia", "contingencia", "interrupcion grave", "desastre", "bcp$",
              "plan de recuperacion", "que pasa si se cae todo"]),
    S("S10", "gobierno técnico",
      tema="el gobierno técnico del proyecto (decisiones, estándares, revisiones y estados de avance)",
      objeto="Cubre cómo se toman y registran las decisiones técnicas, qué estándares obligan, quién revisa y cómo "
             "se distingue lo propuesto de lo implementado, probado y operativo.",
      entradas=["la decisión o el cambio que debe gobernarse", "los documentos de estándares aplicables",
                "quién propone y quién revisa"],
      fuentes=["docs/00-CONSTITUTION.md, docs/08-DECISION-FRAMEWORK.md y docs/09-QUALITY-CHECKLIST.md",
               "docs/coordinacion/TABLERO.md", "ISO/IEC 38500 (gobierno de tecnologías de la información)",
               "práctica de registros de decisión de arquitectura (ADR)"],
      entregable="registro de decisión con contexto, opciones consideradas, decisión, consecuencias, responsable, "
                 "revisor y estado",
      riesgos=["Presentar como operativo lo que solo está configurado o propuesto.",
               "Decisiones tomadas en una conversación que no quedan en el repositorio."],
      comprobaciones=["El registro usa la escala propuesto, configurado, implementado, probado y operativo, con evidencia.",
                      "Toda decisión tiene responsable, revisor y fecha, y queda en un archivo del repositorio."],
      extraer="decisiones ya registradas, estándares obligatorios, excepciones concedidas, tareas sin revisor y "
              "afirmaciones sin evidencia",
      vigencia="la versión vigente de los documentos de estándares y si una decisión posterior los reemplazó",
      preguntas="¿quién puede aprobar este cambio y con qué evidencia?; ¿qué estándar del proyecto se está "
                "incumpliendo?",
      opciones="aprobar con evidencia completa, aprobar con excepción registrada y fecha de cierre o devolver por "
               "falta de evidencia",
      claves=["gobierno tecnico", "gobernanza", "decision tecnica", "adr$", "estandares del proyecto",
              "quien aprueba", "constitucion de ingenieria", "politica tecnica"]),
]
