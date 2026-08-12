# 07 — SEGURIDAD, PRIVACIDAD Y CUMPLIMIENTO

## Principios
Security first: nunca sacrificar seguridad por velocidad. Menor privilegio. Datos mínimos.

## Implementado en V1
- Contraseñas: PBKDF2-SHA256, 200.000 iteraciones, sal única por usuario. Nunca texto plano.
- Sesiones: tokens HMAC-SHA256 firmados con secreto de entorno, expiración 14 días.
- Autorización por rol: rutas /api/admin/* exigen `es_admin` (403 si no).
- Secretos únicamente en variables de entorno; `.gitignore` blinda archivos sensibles.
- SQL parametrizado en el 100% de las consultas.
- Sanitización del render (DOMPurify) para todo contenido markdown → evita XSS.
- El service worker nunca cachea `/api/*` (no se filtran respuestas entre usuarios).
- Fail-safe: errores de IA no exponen trazas internas al usuario.

## Datos personales (Ley 1581 de 2012 — Habeas Data)
- Se recogen datos mínimos: nombre, correo, contraseña (cifrada), preferencias.
- El campo "memoria" es voluntario y editable/eliminable por el usuario.
- Pendiente V2 (obligatorio antes de escalar): política de tratamiento de datos publicada,
  autorización expresa en el registro, y procedimiento de supresión de cuenta.

## Riesgos conocidos y mitigación
| Riesgo | Mitigación V1 | Plan V2 |
|---|---|---|
| Compartir cuenta entre estudiantes | Límite mensual por cuenta | Sesión única activa |
| Fuerza bruta en login | Contraseña ≥8 | Rate limiting + bloqueo temporal |
| Pérdida de datos (disco efímero free) | Aviso documentado | PostgreSQL gestionado |
| Prompt injection vía adjuntos | System prompt prevalece; sin herramientas peligrosas | Filtro de adjuntos |
| Fuga de API key | Solo en entorno; nunca en código/repos | Rotación periódica |

## Reglas operativas para el administrador (Josep)
- Cambiar `PULLEX_ADMIN_CLAVE` por una fuerte al primer despliegue.
- Nunca compartir la clave `sk-ant-...`; si se filtra, revocarla en console.anthropic.com.
- Revisar consumo en console.anthropic.com semanalmente (control de costos).
- Backups: exportar usuarios/uso antes de cada cambio grande (V1: descargar pullex.db).
