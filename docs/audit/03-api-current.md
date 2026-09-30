# 03 — API actual

Todas las rutas `/api/*` (salvo registro, login, recuperación y restablecimiento) exigen `Authorization: Bearer <token>`. Tras la Fase 1 todas responden con `Cache-Control: no-store` y cabeceras de seguridad.

| Método y ruta | Auth | Autorización | Límite | Notas |
|---|---|---|---|---|
| `GET /` `/admin` `/sw.js` `/manifest.webmanifest` | — | — | — | Sirven HTML/JS estático. `/admin` es solo la página; los datos exigen `es_admin`. |
| `GET /salud` | — | — | — | Expone nombre del modelo (INFO). |
| `POST /api/registro` | — | — | 8/5 min por IP | Fase 1: formato de correo, nombre 2–120, clave 8–256. |
| `POST /api/login` | — | — | 8/5 min por IP + **10/15 min por cuenta** | Fase 1: límite por cuenta (la IP de `X-Forwarded-For` se puede falsificar). |
| `POST /api/cambiar-clave` | sí | propia | 10/15 min por cuenta | Fase 1: revoca las demás sesiones y devuelve un token nuevo. |
| `POST /api/cerrar-sesiones` | sí | propia | — | **Nueva**: cierra sesión en todos los dispositivos. |
| `POST /api/reenviar-verificacion` | sí | propia | 4/10 min por IP | — |
| `GET /verificar-correo?token=` | — | token de un solo uso | — | — |
| `POST /api/recuperar-clave` | — | — | 4/10 min por IP + **3/h por correo** | Respuesta idéntica exista o no la cuenta. |
| `POST /api/restablecer-clave` | — | token de un solo uso | 6/10 min por IP | Fase 1: revoca sesiones y anula otros enlaces pendientes. |
| `POST /api/preferencias` | sí | propia | — | Lista blanca de campos. |
| `GET /api/estado` `GET /api/boletin` | sí | propia | — | — |
| `GET/POST /api/conversaciones` | sí | propia | — | — |
| `DELETE /api/conversaciones/{cid}` | sí | **propietario** (Fase 1) | — | Antes borraba mensajes de cualquier conversación. |
| `GET /api/conversaciones/{cid}/mensajes` | sí | **propietario** (Fase 1) | — | Antes: lectura de cualquier conversación (CRITICAL). |
| `POST /api/chat` | sí | **propietario de `conversacion`** (Fase 1) | cupo del plan (atómico desde Fase 1) | Adjuntos validados: máx. 5, PDF/JPG/PNG/GIF/WEBP, ≤ 10 MB base64 c/u. |
| `GET /api/admin/usuarios` `/metricas` | sí | `es_admin` | — | — |
| `POST /api/admin/actualizar` `/reset-clave` `/boletin/regenerar` | sí | `es_admin` | — | `reset-clave` ahora revoca sesiones y usa 72 bits de azar. |

## Pendiente (no implementado en esta iteración)

Protección CSRF formal no es necesaria mientras la sesión viaje en una cabecera `Authorization` que el navegador no adjunta sola; **pasa a ser obligatoria** en el momento en que se migre a cookie `HttpOnly` (Fase 2). No hay versionado de API (`/api/v1`), ni paginación en `/api/conversaciones` y `/api/admin/usuarios`, ni registro de auditoría de operaciones admin (solo un log con correos enmascarados para `reset-clave`).
