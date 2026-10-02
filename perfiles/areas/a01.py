"""A01 — Ingeniería informática. Fuentes: documentación oficial, estándares y el propio repositorio."""
from perfiles.definiciones import S, VERIFICAR

CLAVES_AREA = ["servidor", "infraestructura", "despliegue", "hosting", "alojamiento"]

SUBESPECIALIDADES = [
    S("S01", "cómputo",
      tema="la capacidad de cómputo del servicio (procesador, memoria y procesos del servidor)",
      objeto="Cubre el dimensionamiento de procesador y memoria, el número de procesos e hilos del servidor ASGI "
             "y el efecto de las llamadas bloqueantes al modelo.",
      entradas=["el plan o tipo de instancia contratada", "el comando de arranque con su número de procesos",
                "el volumen esperado de usuarios simultáneos"],
      fuentes=["render.yaml y runtime.txt del repositorio", "documentación oficial de Uvicorn (despliegue y procesos)",
               "documentación oficial de Python (asyncio, hilos y bloqueo global del intérprete)",
               "documentación del proveedor de alojamiento sobre tipos de instancia",
               "docs/01-ENGINEERING-STANDARDS.md"],
      herramientas={"metricas_tecnicas": "F03 F05"},
      entregable="hoja de dimensionamiento con procesos, memoria por proceso, tope de solicitudes simultáneas y "
                 "supuestos de carga",
      riesgos=["Sin métricas de carga toda cifra de capacidad es una estimación y debe decirlo.",
               "Un solo proceso con llamadas bloqueantes al modelo detiene a los demás usuarios."],
      comprobaciones=["Cada cifra de capacidad indica si fue medida o estimada y con qué supuesto de carga.",
                      "El número de procesos propuesto cabe en la memoria de la instancia declarada en render.yaml."],
      extraer="tipo de instancia, comando de arranque, procesos e hilos configurados, rutas con llamadas bloqueantes "
              "y topes de tamaño de solicitud",
      vigencia="la versión de Python fijada en runtime.txt, la de Uvicorn en requirements.txt y los límites actuales "
               "del plan de alojamiento",
      preguntas="¿cuántas solicitudes simultáneas soporta la instancia con la configuración actual?; ¿qué rutas "
                "bloquean el ciclo de eventos mientras responde el modelo?",
      opciones="más procesos en la misma instancia, una instancia mayor o pasar las llamadas largas a un grupo de "
               "hilos o a una cola",
      claves=["cpu$", "procesador", "memoria ram", "ram$", "workers", "uvicorn", "tipo de instancia",
              "capacidad del servidor", "dimensionar", "dimensionamiento", "usuarios simultaneos",
              "se queda sin memoria"]),
    S("S02", "sistemas operativos",
      tema="el sistema operativo y el entorno de ejecución del servidor",
      objeto="Cubre la imagen base, la versión del intérprete, las variables de entorno, los permisos de archivos, "
             "la zona horaria y el sistema de archivos efímero del contenedor.",
      entradas=["el archivo de despliegue y la versión del intérprete",
                "la lista de variables de entorno sin sus valores secretos",
                "el error o comportamiento observado en el servidor"],
      fuentes=["render.yaml, runtime.txt y .env.example del repositorio",
               "documentación oficial de Python para la versión fijada",
               "documentación del proveedor de alojamiento sobre entorno y disco",
               "páginas de manual POSIX (permisos, señales y procesos)"],
      entregable="ficha del entorno de ejecución: sistema, intérprete, variables requeridas, rutas escribibles y qué "
                 "se pierde al reiniciar",
      riesgos=["Dar por persistente un archivo que vive en el disco efímero del contenedor.",
               "Mezclar hora local y UTC al calcular vencimientos o reinicios de cupo."],
      comprobaciones=["La ficha lista cada variable de entorno requerida y qué ocurre si falta.",
                      "Cada ruta de escritura indica si sobrevive a un reinicio o a un redespliegue."],
      extraer="versión del intérprete, variables de entorno leídas por el código, rutas donde se escribe, zona "
              "horaria usada y señales de apagado",
      vigencia="la versión de Python de runtime.txt frente a su calendario de soporte y la imagen que hoy entrega el "
               "proveedor",
      preguntas="¿qué archivos escribe la aplicación y cuáles sobreviven a un redespliegue?; ¿qué variables de "
                "entorno son obligatorias para arrancar?",
      opciones="mantener el entorno nativo del proveedor, fijar una imagen de contenedor propia o mover el estado a "
               "un disco persistente",
      claves=["sistema operativo", "linux", "variables de entorno", "variable de entorno", "permisos de archivo",
              "zona horaria", "disco efimero", "runtime", "version de python", "interprete"]),
    S("S03", "redes",
      tema="la red del servicio (dominio, TLS, cabeceras HTTP y salidas a terceros)",
      objeto="Cubre el dominio y el certificado, el proxy del proveedor, las cabeceras de seguridad, la política de "
             "contenido y las conexiones salientes al modelo, al correo y a la web.",
      entradas=["el dominio y la URL pública del servicio", "las cabeceras de respuesta observadas",
                "la lista de servicios externos que se llaman"],
      fuentes=["middleware de seguridad y política de contenido en app.py",
               "RFC 9110 (semántica de HTTP) y RFC 6797 (HSTS)",
               "especificación Content Security Policy del W3C", "MDN Web Docs (cabeceras HTTP)",
               "documentación del proveedor sobre proxy, TLS y tiempos máximos de respuesta"],
      entregable="mapa de red con entradas, salidas, cabeceras exigidas y tiempo máximo de cada tramo",
      riesgos=["Tomar la IP de X-Forwarded-For como identidad: el cliente puede falsificarla.",
               "Una respuesta larga del modelo puede superar el tiempo máximo del proxy y cortarse."],
      comprobaciones=["Cada conexión saliente indica destino, propósito y qué pasa si no responde.",
                      "Las cabeceras listadas coinciden con las que pone el middleware de app.py."],
      extraer="dominios permitidos por la política de contenido, cabeceras de seguridad, destinos salientes, tiempos "
              "de espera y uso de X-Forwarded-For",
      vigencia="la política de contenido que hoy envía app.py, la versión de TLS del proveedor y las huellas de "
               "integridad de las librerías del CDN",
      preguntas="¿qué tráfico entra y sale del servicio y por dónde?; ¿qué tramo puede cortar una respuesta larga "
                "antes de que termine?",
      opciones="respuestas en flujo con latidos, respuestas diferidas con consulta posterior o tiempos de espera "
               "cortos con reintento",
      claves=["redes", "red$", "dns$", "tls$", "https", "certificado tls", "csp$", "cabecera", "cors$", "proxy",
              "hsts$", "cortafuegos", "tiempo de espera", "politica de contenido"]),
    S("S04", "almacenamiento",
      tema="el almacenamiento de datos del servicio (archivos SQLite, disco y tamaño de lo guardado)",
      objeto="Cubre dónde viven la base de usuarios y el índice del corpus, cuánto crecen, qué se guarda como texto "
             "o como binario y qué ocurre con el disco efímero del proveedor.",
      entradas=["la ruta y el tamaño actual de los archivos de base de datos",
                "el tipo de disco del plan de alojamiento", "el crecimiento esperado de usuarios y documentos"],
      fuentes=["esquema de tablas en app.py, academia.py y fuentes.py",
               "documentación oficial de SQLite (límites, diario WAL y tipos)",
               "documentación del proveedor sobre discos persistentes", "docs/audit/02-database-current.md"],
      entregable="inventario de almacenamiento: qué dato vive dónde, tamaño, crecimiento estimado y si persiste",
      riesgos=["El disco del plan actual es efímero: un redespliegue borra usuarios y conversaciones.",
               "Guardar imágenes como binario sin tope hace crecer la base sin control."],
      comprobaciones=["Cada tabla o archivo indica ubicación, tamaño o tope y si sobrevive a un redespliegue.",
                      "Los topes de tamaño citados coinciden con las constantes del código."],
      extraer="tablas y columnas, tipos de dato, topes de tamaño por campo, archivos de base usados y rutas "
              "configurables por variable de entorno",
      vigencia="el modo de diario de SQLite en uso, los límites de la versión de SQLite del intérprete y las "
               "condiciones actuales del disco del proveedor",
      preguntas="¿qué datos se pierden hoy en un redespliegue?; ¿cuánto crece la base por usuario activo y por "
                "documento indexado?",
      opciones="disco persistente con SQLite, base PostgreSQL gestionada o almacenamiento de objetos para binarios",
      claves=["almacenamiento", "disco", "sqlite", "espacio en disco", "blob$", "archivo de base",
              "disco persistente", "tamano de la base", "donde se guarda"]),
    S("S05", "virtualización",
      tema="el empaquetado y aislamiento del servicio (entornos virtuales, contenedores y ambientes)",
      objeto="Cubre el entorno virtual de Python, la reproducibilidad de la instalación, la separación entre "
             "desarrollo, pruebas y producción y el uso eventual de contenedores.",
      entradas=["los archivos de dependencias y de despliegue", "los pasos actuales para levantar el proyecto",
                "las diferencias observadas entre ambientes"],
      fuentes=["requirements.txt, requirements.lock y render.yaml del repositorio",
               "documentación oficial de Python (venv y pip)",
               "especificación de imágenes de la Open Container Initiative",
               "metodología Twelve-Factor (configuración y paridad de ambientes)"],
      entregable="procedimiento reproducible para levantar el servicio en limpio, con los ambientes separados y sus "
                 "diferencias",
      riesgos=["Sin versiones fijadas cada ambiente instala algo distinto.",
               "Compartir la misma base o las mismas claves entre pruebas y producción."],
      comprobaciones=["El procedimiento levanta el servicio desde cero solo con los archivos del repositorio.",
                      "Cada ambiente declara su base de datos, sus claves y su modelo, sin compartirlos."],
      extraer="versiones fijadas, pasos de instalación, comando de arranque, variables por ambiente y dobles de "
              "prueba usados",
      vigencia="las versiones de requirements.lock frente a las instaladas y la versión de Python de cada ambiente",
      preguntas="¿la instalación es reproducible a partir del repositorio?; ¿qué comparten hoy los ambientes de "
                "prueba y de producción?",
      opciones="entorno virtual con versiones fijadas, imagen de contenedor propia o ambiente de vista previa por "
               "rama",
      claves=["virtualizacion", "entorno virtual", "venv$", "contenedor", "docker", "ambiente de pruebas",
              "ambiente de produccion", "staging", "reproducible", "maquina virtual"]),
    S("S06", "identidad",
      tema="la identidad y el acceso (cuentas, contraseñas, sesiones y permisos)",
      objeto="Cubre el registro y el ingreso, el guardado de contraseñas, los tokens de sesión firmados y su "
             "revocación, la verificación de correo y la autorización por dueño del recurso y por plan.",
      entradas=["el flujo de ingreso o el permiso que se quiere revisar", "las rutas y recursos involucrados",
                "el rol o plan del usuario afectado"],
      fuentes=["funciones de token, sesión y límite de intentos en app.py", "NIST SP 800-63B (autenticación)",
               "OWASP ASVS (autenticación, sesiones y control de acceso)",
               "docs/07-SECURITY-POLICIES.md y docs/audit/06-auth-current.md", "tests/test_seguridad.py"],
      entregable="matriz de acceso (quién puede qué sobre qué recurso) con el control que la hace cumplir y su prueba",
      riesgos=["Autorizar por lo que oculta la interfaz y no por lo que valida el servidor.",
               "Responder 403 en lugar de 404 confirma que existe un recurso ajeno."],
      comprobaciones=["Cada fila de la matriz señala la función del servidor que valida y la prueba que la cubre.",
                      "Ningún recurso con dueño se lee o modifica sin filtrar por el usuario de la sesión."],
      extraer="rutas con sesión obligatoria, validaciones de dueño, duración del token, reglas de contraseña y "
              "límites de intentos",
      vigencia="los parámetros de derivación de clave en uso frente a la recomendación vigente y la duración actual "
               "del token",
      preguntas="¿qué rutas leen o cambian recursos sin comprobar al dueño?; ¿cómo se revoca una sesión "
                "comprometida?",
      opciones="token firmado en cabecera como hoy, cookie HttpOnly con protección CSRF o un proveedor de identidad "
               "externo con segundo factor",
      claves=["identidad", "autenticacion", "autorizacion", "inicio de sesion", "login", "contrasena", "token",
              "sesion", "permisos de usuario", "roles", "mfa$", "segundo factor", "idor$", "control de acceso"]),
    S("S07", "seguridad defensiva",
      tema="la defensa del servicio frente a ataques (entradas, secretos, abuso y exposición de datos)",
      objeto="Cubre la validación de entradas, la protección contra inyección y XSS, el manejo de secretos, los "
             "límites de abuso y de costo y la reducción de datos personales en los registros.",
      entradas=["el componente o la ruta que se quiere endurecer", "el hallazgo o incidente observado",
                "los datos personales que toca el componente"],
      fuentes=["docs/07-SECURITY-POLICIES.md y docs/audit/05-security-current.md", "OWASP Top 10 y OWASP ASVS",
               "especificación Content Security Policy del W3C",
               "Ley 1581 de 2012, protección de datos personales " + VERIFICAR, "tests/test_seguridad.py"],
      entregable="registro de amenazas del componente con control existente, brecha, severidad y prueba que lo "
                 "demuestra",
      riesgos=["Declarar cerrado un hallazgo sin una prueba que falle cuando se quita el control.",
               "Dejar correos, claves o textos de casos en los registros del servidor."],
      comprobaciones=["Cada amenaza tiene control, severidad y una prueba automatizada o el motivo de su ausencia.",
                      "Ningún secreto ni dato personal completo aparece en código, registros o respuestas de error."],
      extraer="entradas sin validar, puntos de salida de HTML, secretos leídos del entorno, límites de tamaño y de "
              "intentos y datos personales registrados",
      vigencia="la edición vigente de la guía OWASP citada y los avisos de seguridad de las versiones instaladas",
      preguntas="¿qué entrada controlada por el usuario llega sin validar a la base, al modelo o al HTML?; ¿qué "
                "abuso encarece el servicio sin límite?",
      opciones="validación con lista blanca en el servidor, límites por cuenta y por costo o aislamiento del "
               "componente expuesto",
      claves=["seguridad", "vulnerabilidad", "xss$", "inyeccion sql", "secretos", "fuerza bruta", "ataque",
              "owasp", "endurecer", "hardening", "fuga de datos", "ciberseguridad"]),
    S("S08", "respaldo",
      tema="las copias de seguridad y la restauración de los datos",
      objeto="Cubre qué se respalda (base de usuarios, índice del corpus, secretos), cada cuánto, dónde queda la "
             "copia, cuánto se puede perder y cómo se prueba la restauración.",
      entradas=["los archivos y bases que deben respaldarse",
                "la pérdida de datos y el tiempo de caída tolerables", "el destino disponible para las copias"],
      fuentes=["documentación oficial de SQLite (API de copia en línea y VACUUM INTO)",
               "docs/audit/09-risks-current.md y docs/coordinacion/PUL-001-estado-del-proyecto.md",
               "documentación del proveedor sobre discos, instantáneas y tareas programadas",
               "ISO/IEC 27001, control de copias de seguridad de la información"],
      entregable="plan de respaldo con alcance, frecuencia, destino, retención, pérdida máxima tolerada y guion de "
                 "restauración ensayado",
      riesgos=["Una copia que nunca se restauró no es un respaldo: es una suposición.",
               "Copiar el archivo SQLite en caliente sin la API de copia puede dejarlo corrupto."],
      comprobaciones=["El plan fija con cifras la pérdida máxima (RPO) y el tiempo de recuperación (RTO).",
                      "Incluye el guion de restauración y la fecha del último ensayo, o declara que no se ha ensayado."],
      extraer="archivos de base de datos con su ubicación y tamaño, secretos que deben conservarse y tareas "
              "programadas existentes",
      vigencia="el método de copia recomendado para la versión de SQLite en uso y las condiciones de retención del "
               "destino",
      preguntas="¿qué se pierde hoy si el contenedor se reinicia?; ¿cuánto tarda la restauración y quién la "
                "ejecuta?",
      opciones="copia programada con la API de SQLite hacia almacenamiento externo, réplica continua o migración a "
               "una base gestionada con copias automáticas",
      claves=["copia de seguridad", "backup", "respaldo", "respaldar", "restaurar", "restauracion",
              "recuperacion ante desastres", "rpo$", "rto$", "perdida de datos"]),
    S("S09", "rendimiento",
      tema="el rendimiento del servicio (latencia, consumo y cuellos de botella)",
      objeto="Cubre el tiempo de respuesta de cada ruta, el primer token del modelo, las consultas a la base, el "
             "peso de lo que recibe el navegador y el costo por consulta.",
      entradas=["la ruta o pantalla que se percibe lenta", "la medición disponible o la forma de reproducir",
                "el objetivo de tiempo o de costo"],
      fuentes=["objetivos de latencia en docs/02-AI-ARCHITECTURE.md",
               "documentación oficial de SQLite (planificador y EXPLAIN QUERY PLAN)",
               "documentación de la API del proveedor del modelo (flujo y caché de instrucciones)",
               "MDN Web Docs (API de rendimiento del navegador)"],
      herramientas={"metricas_tecnicas": "F03 F05"},
      entregable="informe de rendimiento con medición de partida, cuello de botella identificado, cambio propuesto y "
                 "medición esperada",
      riesgos=["Optimizar sin medir antes y después.", "Confundir la latencia del modelo con la del servidor propio."],
      comprobaciones=["Cada cifra indica cómo se midió, cuántas veces y en qué ambiente.",
                      "El cuello de botella señalado se apoya en una medición, no en una intuición."],
      extraer="tiempos por tramo, consultas ejecutadas por solicitud, peso de respuestas y recursos estáticos y "
              "tokens de entrada y de salida",
      vigencia="los precios y límites de tokens del modelo configurado y los objetivos de latencia vigentes en la "
               "documentación del proyecto",
      preguntas="¿en qué tramo se va el tiempo: red, servidor, base o modelo?; ¿qué parte del costo por consulta "
                "es evitable?",
      opciones="índices y menos consultas, caché de instrucciones del modelo, respuestas en flujo o un modelo más "
               "liviano para tareas simples",
      claves=["rendimiento", "latencia", "carga lento", "tarda en cargar", "cuello de botella", "performance",
              "tiempo de respuesta", "costo por consulta", "consumo de tokens", "va lento"]),
    S("S10", "compatibilidad",
      tema="la compatibilidad del servicio con navegadores, dispositivos y versiones",
      objeto="Cubre los navegadores y anchos de pantalla admitidos, la instalación como aplicación web, el "
             "funcionamiento sin las librerías del CDN y la compatibilidad de datos entre versiones.",
      entradas=["el navegador, dispositivo y versión donde falla o debe funcionar",
                "la función de la plataforma afectada", "la captura o el mensaje de error"],
      fuentes=["static/ (HTML, CSS y JavaScript sin compilación) y manifest.webmanifest",
               "MDN Web Docs (tablas de compatibilidad)",
               "especificaciones del W3C y del WHATWG (HTML, CSS, Service Workers)",
               "pruebas de navegador en tests/e2e_*.py"],
      entregable="matriz de compatibilidad (navegador por función) con lo probado, lo no probado y las degradaciones "
                 "previstas",
      riesgos=["Declarar compatible lo que solo se probó en un motor de navegador.",
               "Usar una función reciente de CSS o JavaScript sin respaldo para navegadores anteriores."],
      comprobaciones=["Cada celda de la matriz dice «probado», «no probado» o «no soportado», con la fecha de la prueba.",
                      "Toda función web reciente usada indica su respaldo cuando el navegador no la tiene."],
      extraer="funciones de CSS y JavaScript usadas, anchos de pantalla previstos, dependencias del CDN y "
              "comportamiento cuando faltan",
      vigencia="el soporte actual de cada función web en las tablas de compatibilidad y las versiones de navegador "
               "del público objetivo",
      preguntas="¿en qué navegadores y anchos se probó de verdad?; ¿qué deja de funcionar si no cargan el CDN o el "
                "service worker?",
      opciones="respaldo progresivo de la función, sustitución por una equivalente ampliamente soportada o declarar "
               "el navegador como no admitido",
      claves=["compatibilidad", "navegador", "safari", "firefox", "chrome", "iphone", "android", "pwa$",
              "service worker", "pantalla pequena", "version movil", "no funciona en el celular"]),
]
