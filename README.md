# PULLEX IA — Asistente Jurídico Colombiano (multiusuario)

Aplicación web para **vender por suscripción a estudiantes de Derecho**.
Cada estudiante tiene su cuenta con un **plan y un límite de consultas**; tú, como
administrador, activas las cuentas cuando te pagan (por Nequi u otro medio).
Motor **Claude Haiku** (económico) vía la API oficial de Anthropic, con búsqueda
web, boletín jurídico diario, adjuntar PDF/fotos, memoria y exportar a PDF/Excel.

## Requisitos

- **Python 3.10 o superior**.
- Una **clave de la API de Claude**: console.anthropic.com → *API Keys* (se paga por uso).

## Instalación local (5 minutos)

```bash
cd pullex-ia
python -m venv venv
source venv/bin/activate            # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                # Windows: copy .env.example .env
#   Abre .env y pega tu ANTHROPIC_API_KEY y define el correo/clave del admin
python app.py
```

- App para estudiantes: **http://localhost:8000**
- Panel de administrador: **http://localhost:8000/admin**

## Cómo funciona el negocio

1. El estudiante entra a la app y **crea su cuenta** → recibe **10 consultas gratis** (plan Prueba).
2. Cuando quiere más, **paga por Nequi** y te avisa.
3. Tú entras a **/admin**, buscas su correo, le asignas el plan (Básico/Pro/Premium) y **activas** la cuenta.
4. El límite de consultas por plan **protege tu costo de API**: nunca gastas más de lo que cobras.

### Planes (editables en `app.py` → `PLANES`)

| Plan     | Precio/mes | Consultas/mes |
|----------|-----------:|--------------:|
| Prueba   |         $0 |            10 |
| Básico   |    $30.000 |           200 |
| Pro      |    $45.000 |           500 |
| Premium  |    $60.000 |         1.000 |

## Administrador

Se crea solo al arrancar, con las variables `PULLEX_ADMIN_EMAIL` y `PULLEX_ADMIN_CLAVE`.
**Cambia esa clave por una segura.** Con esa cuenta entras a `/admin` para gestionar estudiantes
y regenerar el boletín.

## Novedades (PULLEX Academia)

- **Inicio con dos caminos:** "Estoy aprendiendo Derecho" y "Estoy trabajando en un asunto". Cada uno
  muestra sus propias herramientas; la elección se recuerda en la cuenta.
- **Modular Lab:** eliges área y nivel, PULLEX genera un caso tipo examen **sin mostrar la solución**,
  respondes, pides hasta 2 pistas, y recibes una evaluación con rúbrica (problema 20, normas 20,
  argumentación 20, aplicación 20, conclusión 10, claridad 10) con lo que identificaste, lo que omitiste,
  la norma que faltó, el argumento contrario y cómo mejorar. Luego puedes ver la solución de referencia
  o pedir una variación "¿Qué cambia si…?". Generar un caso y evaluar cuestan 1 consulta cada uno;
  pistas y solución son gratis.
- **Progreso:** casos evaluados, promedio por área y conceptos a reforzar (con acceso directo a
  "Enséñame" sobre ese concepto).
- **Mi mapa del Derecho (modelo individual del conocimiento):** 61 conceptos en 9 áreas (área → tema →
  concepto). Cada evaluación de un modular actualiza el estado de los conceptos del caso para ese
  estudiante: *Dominado*, *En progreso*, *Débil* o *Sin evaluar*. Dos estudiantes que usan PULLEX
  reciben entrenamientos distintos según lo que cada uno confunde.
- **Banco de errores:** los conceptos que confundiste, cuántas veces, severidad y si ya los superaste.
  Desde ahí: "Explícamelo" (chat en modo Enséñame) o "Practicar" (caso nuevo centrado en ese concepto).
- **Repasos espaciados:** un error lleva el concepto a repaso al día siguiente; cada acierto aleja el
  próximo repaso (1, 3, 7, 15 y 30 días). "Hoy" se calcula en hora de Colombia.
- **Tablero de estudio en el inicio:** caso recomendado (con nivel sugerido según tu promedio en el
  área), continuar el último caso sin responder, próximo repaso, tema débil y último modular.
- **Escalera de ayuda en Modular Lab:** Pista 1 → Pista 2 → Explícame el concepto → Ver solución.
  Detalle técnico en `docs/10-ACADEMIA.md`.
- **Forma de respuesta en el chat:** Respuesta directa, Enséñame, Resuélvelo conmigo (tutor
  socrático), Examíname (simulacro oral) y Audita mi respuesta.
- **Demo sin servidor:** `python demo/construir_demo.py` genera `demo/pullex-demo.html`, la app completa
  con datos de ejemplo para mostrarla. `python demo/servidor_simulado.py` levanta el backend real con
  un modelo simulado (sin clave de API) en http://localhost:8000.

## Funciones

- **Inicio dinámico**: boletín jurídico del día (noticias, jurisprudencia y novedades
  normativas) generado con búsqueda web y **cacheado 1 vez al día** (no gasta las consultas
  del estudiante).
- **Chat fluido** con streaming, trato humano y capaz de responder también temas no jurídicos.
- **Adjuntar** PDF, fotos o documentos para analizarlos.
- **Memoria**: cada estudiante escribe lo que quiere que PULLEX recuerde de él.
- **Personalización**: áreas de interés, modo (Automático/Técnico/Sencillo), tema claro/oscuro,
  búsqueda web por defecto.
- **Exportar**: imprimir/guardar en **PDF**, descargar respuesta, y exportar tablas
  (liquidaciones) a **Excel/CSV**.
- **Cada estudiante tiene su propia cuenta** (correo + contraseña que crea él mismo), con
  **verificación de correo** y **recuperación de contraseña** por correo (ver abajo).

## Verificación de correo y recuperación de contraseña

Cada estudiante se registra con su propio correo y contraseña. Al crear la cuenta, PULLEX IA
le envía un correo de confirmación (enlace de un solo uso, vence en 24 horas); mientras no lo
confirme, ve un aviso en la app con un botón para reenviarlo. Si olvida su contraseña, desde
"¿Olvidaste tu contraseña?" en la pantalla de ingreso recibe un enlace (vence en 1 hora) para
elegir una nueva — por seguridad, la respuesta es idéntica exista o no esa cuenta, para que
nadie pueda usar ese formulario y averiguar qué correos están registrados.

**Para que estos correos salgan de verdad**, consigue una clave gratis en
[resend.com](https://resend.com) (capa gratuita: 3.000 correos/mes) y ponla en la variable
`RESEND_API_KEY` (en tu `.env` local o en Render). Sin esa clave, la app funciona igual —
solo que esos correos no se envían y queda un aviso en el log del servidor. También define
`PULLEX_APP_URL` con la URL pública real de tu app (en Render, la que te asigna tu servicio),
para que los enlaces de los correos apunten al lugar correcto.

## Desplegar en internet (Render.com, gratis)

El archivo `render.yaml` ya deja todo listo. En Render creas un *Blueprint* apuntando a tu
repositorio, y defines en **Environment**:

- `ANTHROPIC_API_KEY` → tu clave real.
- `PULLEX_ADMIN_EMAIL` y `PULLEX_ADMIN_CLAVE` → tu correo y una clave segura de admin.
- `RESEND_API_KEY` (opcional) → para que salgan los correos de verificación/recuperación.
- `PULLEX_APP_URL` → tu URL real de Render, tras el primer despliegue.

## Seguridad

- Contraseñas cifradas (PBKDF2-SHA256, 200.000 iteraciones, sal por usuario).
- Sesiones con tokens firmados (HMAC), 14 días, **revocables**: cambiar o restablecer la contraseña
  cierra las demás sesiones, y hay "Cerrar sesión en todos los dispositivos" en Configuración.
- Cada conversación solo la puede ver, escribir o borrar su dueño (autorización por recurso).
- Límite de intentos por IP **y por cuenta** en ingreso, recuperación y cambio de contraseña.
- Cabeceras de seguridad y Content-Security-Policy estricta: ningún JavaScript en línea (los botones usan
  `data-click` y un despachador con lista blanca en `static/app.js`); scripts de CDN con SRI.
  **Regla para quien edite el frontend:** no agregar `onclick="..."` ni `<script>` en línea; la CSP los
  bloquea y `tests/test_seguridad.py::test_WEB_006` falla si aparecen.
- Enlaces de verificación/recuperación de un solo uso y con vencimiento (24h / 1h).
- Historial en SQLite (`pullex.db`). **Ojo:** en el plan gratuito de Render el disco es efímero;
  descarga la base antes de cada despliegue hasta migrar a una base gestionada.
- Estado verificado, hallazgos abiertos y plan: `docs/audit/` (empieza por `09-risks-current.md`).

## Pruebas

```bash
pip install -r requirements-dev.txt
pytest tests                  # 68 pruebas: seguridad, regresión, Modular Lab y Academia (no llaman a la API real)
pip-audit -r requirements.txt # vulnerabilidades conocidas en dependencias
```

Con el servidor corriendo, `tests/e2e_navegador.py` repite las verificaciones en un navegador real
(requiere Playwright y las variables `PULLEX_ADMIN_EMAIL` / `PULLEX_ADMIN_CLAVE`).

## Advertencia

PULLEX IA es una herramienta de **apoyo y estudio**. Ninguna norma o sentencia debe usarse en un
escrito judicial sin confirmarla en la fuente oficial. No sustituye a un abogado ni garantiza
resultados. Trata los datos personales conforme a la Ley 1581 de 2012.
