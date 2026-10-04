# PUL-001 — Estado real del proyecto PULLEX IA

Fecha: 2026-10-02 · Responsable: Claude · Revisión: Codex (pendiente) · Rama base: `academia` @ `34afb99`

PULLEX IA es una aplicación real con backend, base de datos y pruebas; no es un prototipo visual. Lo que
sí es simulado es el modelo de IA durante las pruebas: nada se ha ejecutado contra las API reales de
Anthropic u OpenAI desde este entorno.

## 1. Ubicación

| Qué | Dónde | Estado |
|---|---|---|
| Repositorio GitHub | `pulidoabogados24-collab/pullex-ia-2026`, rama `main` @ `4d54f17` | Es la versión v4 (antes de Academia). **Desactualizado.** |
| Rama integrada | `academia` @ `34afb99` (9 commits sobre `main`) | Solo local. **No se pudo subir**: la sesión no tiene permiso de escritura sobre el repositorio (403 del proxy de git). |
| Ramas de la ronda 2 | `pul/planes-y-proveedores`, `pul/wip-banco-modular`, `pul/wip-estilo-humano`, `pul/wip-taller-escritos` | Locales, sin fusionar. Ver sección 5. |
| Exportación | `pullex-ia-export-2026-10-02.zip` (código de `academia`) y `pullex-ia-todas-las-ramas.bundle` (historial completo) | Entregados en el chat. |
| Demo sin servidor | `demo/pullex-demo.html` (un solo archivo, datos de ejemplo) | Publicada como artifact "PULLEX IA Demo" (versión de Academia; no incluye rediseño ni Documentos). |
| Despliegue | Render (`render.yaml`) | **NOT VERIFIED**: no sé qué versión está desplegada ni desde qué repositorio. |

## 2. Tecnologías y ejecución

- Backend: Python 3.11, FastAPI 0.142.1, Uvicorn, SQLite (archivo `pullex.db`), SDK Anthropic 1.9.0, python-docx 1.2.0.
- Frontend: HTML + CSS + JavaScript sin framework ni paso de compilación (`static/`). Fuentes autohospedadas.
- IA: `claude-sonnet-5-5` por defecto (`PULLEX_MODELO`), con búsqueda web restringida a dominios oficiales.
- Correo: Resend (verificación y recuperación de clave).

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env            # completar ANTHROPIC_API_KEY, PULLEX_ADMIN_EMAIL, PULLEX_ADMIN_CLAVE, PULLEX_SECRET
uvicorn app:app --reload        # http://localhost:8000

python demo/servidor_simulado.py   # backend real con modelo simulado, sin clave de API
pytest tests                       # 147 pruebas
```

## 3. Funciones operativas y funciones simuladas

Operativas en código y probadas con el modelo simulado (rama `academia`):

- Cuentas: registro, ingreso, verificación de correo, recuperación de clave, cierre de sesiones, panel de administración, cupo de consultas por plan.
- Chat jurídico con streaming, historial de conversaciones, adjuntos, cinco formas de respuesta, bloque "Fuentes consultadas".
- Academia: Laboratorio de casos (caso, pistas, evaluación con rúbrica, solución, variación), Mi mapa del Derecho (61 conceptos), banco de errores, repasos espaciados, tablero de estudio.
- Motor de fuentes: índice de texto completo SQLite FTS5, script de ingesta, web limitada a sitios oficiales, evento de fuentes por respuesta.
- Automatizador: catálogo de 203 tipos de escrito en 15 áreas, generación, exportación a Word, 7 flujos, asistente de pasos encadenados.
- Apariencia personalizable por usuario: 6 temas, acento, tipografía, densidad, imagen de fondo, avatar y logo.

Simulado o no verificado:

- **Todas las llamadas al modelo** en pruebas usan un doble (`FakeAnthropic`). Calidad jurídica real, costos y tiempos: NOT VERIFIED.
- El **corpus está vacío**: el motor de fuentes funciona, pero no hay documentos cargados. Hoy las respuestas dependen del modelo y de la búsqueda web.
- La demo (`pullex-demo.html`) es 100 % simulada en el navegador.
- Envío real de correos, despliegue en Render y benchmark jurídico (`evaluacion/benchmark.py`): NOT VERIFIED.
- Flujos programados (periódicos): no implementados.

## 4. Drive, búsqueda, autenticación y almacenamiento

| Componente | Estado |
|---|---|
| Google Drive | **No conectado a la app.** El corpus del dueño existe en Drive (`LEXCOL_CORPUS` y bibliotecas compartidas por terceros). El script `scripts/ingesta_corpus.py` puede leer una carpeta local o Drive con cuenta de servicio; nunca se ha corrido contra el Drive real. El inventario y la clasificación (manifiesto, vigencia) **no se hicieron**: el agente asignado no llegó a ejecutarse. |
| Búsqueda | FTS5 con BM25 implementada y probada con documentos de prueba. Sin corpus real. Búsqueda web del modelo restringida por `allowed_domains`: NOT VERIFIED contra la API real. |
| Autenticación | Propia: contraseña con hash y sal, token firmado HMAC en `Authorization: Bearer`, versión de sesión para revocar. El token vive en memoria del navegador, no en cookie HttpOnly. Sin MFA. Sin CSRF (no aplica a Bearer). |
| Autorización | Por dueño del recurso en cada ruta (pruebas IDOR). El control por plan está en la rama `pul/planes-y-proveedores`, aún sin fusionar. |
| Almacenamiento | SQLite en el disco de Render, que es **efímero**: un redespliegue borra usuarios, conversaciones y progreso. Es el riesgo operativo más alto. Supabase está disponible en la cuenta del dueño, pero no se ha migrado nada. |

## 5. Archivos y ramas en modificación

| Rama | Contenido | Estado | Pruebas |
|---|---|---|---|
| `academia` (`34afb99`) | Todo lo de la sección 3 | Integrada | 147 pytest; e2e navegador 30/30, academia, fuentes y documentos sin fallos (2026-10-02) |
| `pul/planes-y-proveedores` (`89290bb`) | Acceso por plan (Básico: chat; Pro: + Academia; Premium: + Automatizador), `proveedores.py` con OpenAI como alterno y respaldo | Terminada, **sin fusionar ni revisar** | 174 pytest; e2e planes según informe del agente |
| `pul/wip-banco-modular` (`b4cc164`) | `academia_banco/` con 40 de 180 casos (Constitucional y Penal), validador, conectores | **Incompleta**; banco no conectado a la app | 147 pytest (no agrega integración) |
| `pul/wip-estilo-humano` (`a3be4b4`) | `estilo_redaccion.py`, detector de rasgos de IA, cambios en prompts | **Incompleta**; 1 prueba falla (`test_pulir_negritas…`) | 185 pasan, 1 falla |
| `pul/wip-taller-escritos` (`c053782`) | `taller.py` (backend y 42 escenarios) completo; `static/taller.js` a medias | **Incompleta**; frontend sin probar | 166 pytest; sin e2e |

Archivos compartidos con riesgo de conflicto al fusionar: `app.py`, `static/app.js`, `static/index.html`, `demo/mock.js`, `tests/conftest.py`, `documentos.py`.

## 6. Pruebas realizadas y errores pendientes

Evidencia del 2026-10-02 sobre `academia` @ `34afb99`:

- `pytest tests`: 147 pasan.
- `tests/e2e_navegador.py`: 30/30. `e2e_academia.py`, `e2e_fuentes.py`, `e2e_documentos.py`: sin fallos, cero violaciones de CSP, cero errores de consola (Chromium, 1280 y 390 px).
- Búsqueda de secretos en el árbol: solo marcadores de ejemplo en `.env.example`.

Pendientes conocidos:

1. Nada probado con modelo real (Anthropic u OpenAI).
2. Base de datos efímera en Render.
3. Corpus sin cargar; códigos del Drive con fecha de febrero de 2024 (vigencia sin revisar).
4. Margen: Sonnet con búsqueda web puede costar más por consulta de lo que cobra el plan Básico (estimación, no medición).
5. Contenido jurídico generado por IA sin revisión humana: 61 descripciones del mapa, 203 tipos de escrito, 40 casos del banco, 42 escenarios del taller, 30 preguntas del benchmark.
6. Solo probado en Chromium.
7. La barra de navegación móvil tiene 6 botones tras sumar "Documentos": revisar en dispositivos reales.
8. Derechos de autor: plantillas y doctrina de terceros en el Drive no deben mostrarse como texto a usuarios de pago sin revisión legal.

## 7. Próxima tarea propuesta: PUL-002 — Fusionar control de acceso por plan

Alcance: fusionar `pul/planes-y-proveedores` en `academia`, resolviendo conflictos, sin cambios funcionales adicionales.

Criterios de aceptación:

- `pytest tests` pasa completo (se esperan 174).
- Matriz plan × ruta: Básico recibe 403 en `/api/modular/*`, `/api/academia/*`, `/api/documentos/*`, `/api/flujos/*`, `/api/asistente/*`; Pro 200 en Academia y 403 en Automatizador; Premium 200 en todo.
- `tests/e2e_planes.py`, `e2e_navegador.py`, `e2e_academia.py`, `e2e_fuentes.py` y `e2e_documentos.py` pasan con cero violaciones de CSP.
- Con `PULLEX_PROVEEDOR` sin definir, el comportamiento es idéntico al actual (Anthropic).
- Revisión de Codex del diff antes de fusionar.

Decisión que necesita el dueño antes de PUL-002: qué funciones tiene el plan de prueba gratis (hoy: todas, limitadas por 10 consultas).
