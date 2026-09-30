# 01 — Arquitectura actual (inspeccionada, no supuesta)

**Fecha de auditoría:** 30-sep-2026 · **Código auditado:** `pullex-ia-final.zip` (entregado el 12-ago-2026), recuperado de la carpeta Descargas del fundador. Línea base guardada como commit `baseline` en el repositorio local de trabajo.

## Qué es hoy PULLEX IA, en una frase

Un monolito FastAPI de un solo archivo (`app.py`, 962 líneas en la línea base, 1.194 tras la Fase 1) con SQLite local, que sirve una SPA en HTML/JS sin framework, llama a la API de Claude (Haiku 4.5 por defecto) con búsqueda web opcional y se despliega en Render (plan gratuito) mediante `render.yaml`.

## Mapa de componentes

| Capa | Qué hay | Evidencia |
|---|---|---|
| Frontend | 3 páginas HTML estáticas con JS en línea, sin build ni framework: `static/index.html` (app del estudiante, 739 líneas), `static/admin.html` (panel admin, 136), `static/restablecer.html` (100). Markdown renderizado con `marked` 12.0.2 + `DOMPurify` (CDN cdnjs). | `static/*.html` |
| PWA | `manifest.webmanifest` + `sw.js` (red primero, caché de respaldo, nunca `/api/`). | `static/sw.js` |
| Backend | FastAPI (0.142.1 probada) + Uvicorn. Sin routers, sin ORM, sin capas: todo en `app.py`. | `app.py` |
| Base de datos | SQLite (`pullex.db`) con `sqlite3` estándar, consultas parametrizadas. Tablas: `usuarios`, `conversaciones`, `mensajes`, `boletin`, `tokens_accion`. | `app.py` bloque `executescript` |
| Autenticación | Correo + contraseña (PBKDF2-SHA256, 200.000 iteraciones, sal por usuario). Sesión = token propio `base64(json).base64(HMAC-SHA256)` con 14 días de vida, enviado en `Authorization: Bearer`. | `emitir_token`, `validar_token` |
| Autorización | Booleano `es_admin` para `/api/admin/*`. No hay roles, permisos ni organizaciones. Antes de la Fase 1 no había verificación de propiedad en conversaciones (ver 05). | `admin_actual` |
| Almacén del token en el cliente | Variable JS en memoria (`let TOKEN`), **no** localStorage. Al recargar la página se pierde la sesión. | `static/index.html` l. 423 |
| Cookies | Ninguna (ver 07). | inspección de respuestas |
| IA | SDK `anthropic` (1.9.0). Un único `messages.stream` por consulta. Prompt de sistema fijo con caché + bloque dinámico (agentes por palabra clave, modo, nombre, áreas, memoria, corpus). Herramienta de servidor `web_search_20250305` opcional. | `chat()` |
| "Agentes" | Enrutador por palabras clave (`AGENTES`): añade hasta 3 párrafos de instrucción por área. No hay clasificador, orquestador ni segunda pasada. | `enrutar_agentes` |
| RAG | Código opcional para ChromaDB + `voyage-law-2`, **inactivo**: las dependencias están comentadas y no existe `bd_vectorial/`. | `buscar_corpus`, `requirements.txt` |
| Correo | Resend vía HTTP (`urllib`), opcional. Verificación de correo (24 h) y restablecimiento (1 h) con tokens de un solo uso. | `enviar_correo`, `tokens_accion` |
| Boletín | Generado 1 vez al día con búsqueda web, cacheado en la tabla `boletin`. | `obtener_boletin` |
| Adjuntos | PDF/imagen en base64 dentro del JSON del chat; se reenvían al modelo, no se guardan en disco. | `chat()` |
| Rate limiting | Diccionario en memoria por IP (tomada de `X-Forwarded-For`), se pierde en cada reinicio. | `limitar` |
| Logs | `print()` a stdout (antes de Fase 1), sin estructura. | — |
| Jobs / colas / caché | No existen. | — |
| Observabilidad | Solo `/salud`. | — |
| Despliegue | Render free: disco efímero (la base SQLite puede perderse en un redeploy), *cold start* tras 15 min. | `render.yaml` |

## Flujo de una consulta (tal como funciona hoy)

Navegador → `POST /api/chat` (token Bearer) → valida token → verifica cupo → guarda el mensaje → arma historial de la conversación → prompt de sistema + agentes por palabra clave → Claude Haiku (con búsqueda web si está activa) → *streaming* SSE al navegador → guarda la respuesta.

No hay: clasificación de intención, recuperación verificable, verificación de citas, segunda revisión adversarial ni registro de fuentes. Todo el rigor depende de las instrucciones del prompt.

## Otros sistemas encontrados (fragmentación)

En la carpeta Descargas conviven al menos: `pullex-ia-app/` (versión anterior de 603 líneas), `pullex-ia-actualizado/` (mismo `app.py` que la final), `lexcol-app/` (x2), cinco variantes de `PULLEX_IA_2026*.html` / `PULLEX_IA_APP.html` (páginas sueltas) y un `PULLEX-respaldo.json` del 29-sep-2026 con estructura de otra aplicación (tareas/agenda). **HUMAN REVIEW REQUIRED:** confirmar que `pullex-ia-final` es la única fuente de verdad y archivar el resto.

## Qué conservar

El monolito modular, SQL parametrizado, PBKDF2, el modelo configurable por variable de entorno, el control de cupo por plan, el modo degradado cuando falla la IA, el token en memoria (no en localStorage), el flujo de correo con anti-enumeración y la disciplina anti-alucinación del prompt. Nada de esto se reemplaza; se construye encima.
