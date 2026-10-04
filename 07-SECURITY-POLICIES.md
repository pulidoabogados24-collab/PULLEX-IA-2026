# 07 — SEGURIDAD, PRIVACIDAD Y CUMPLIMIENTO

## Principios
Security first: nunca sacrificar seguridad por velocidad. Menor privilegio. Datos mínimos.

> **Actualizado 30-sep-2026:** la auditoría de `docs/audit/` encontró que varias afirmaciones de
> esta sección no se cumplían (autorización por recurso, XSS en el panel admin, errores que sí
> exponían detalles). El estado verificado, con pruebas, está en `docs/audit/05-security-current.md`.

## Implementado en V1
- Contraseñas: PBKDF2-SHA256, 200.000 iteraciones, sal única por usuario. Nunca texto plano.
- Sesiones: tokens HMAC-SHA256 firmados con secreto de entorno, expiración 14 días.
- Autorización por rol: rutas /api/admin/* exigen `es_admin` (403 si no).
- Autorización por recurso (desde Fase 1): cada conversación solo la ve, escribe o borra su dueño.
- Revocación de sesiones al cambiar/restablecer la clave y "cerrar sesión en todos los dispositivos".
- Límite de intentos por IP y por cuenta; cabeceras de seguridad y CSP; SRI en scripts de CDN.
- Secretos únicamente en variables de entorno; `.gitignore` blinda archivos sensibles.
- SQL parametrizado en el 100% de las consultas.
- Sanitización del render (DOMPurify 3.4.16) para el markdown del modelo; el panel admin construye
  sus filas con `textContent` (antes interpolaba HTML: XSS almacenado, corregido en Fase 1).
- El service worker nunca cachea `/api/*` (no se filtran respuestas entre usuarios).
- Fail-safe: errores de IA muestran un mensaje genérico con código; el detalle va solo al log
  (antes se mostraba el texto de la excepción, corregido en Fase 1).

## Datos personales (Ley 1581 de 2012 — Habeas Data)
- Se recogen datos mínimos: nombre, correo, contraseña (cifrada), preferencias.
- El campo "memoria" es voluntario y editable/eliminable por el usuario.
- Pendiente V2 (obligatorio antes de escalar): política de tratamiento de datos publicada,
  autorización expresa en el registro, y procedimiento de supresión de cuenta.

## Riesgos conocidos y mitigación
| Riesgo | Mitigación V1 | Plan V2 |
|---|---|---|
| Compartir cuenta entre estudiantes | Límite mensual por cuenta | Sesión única activa |
| Fuerza bruta en login | Límite por IP + por cuenta (Fase 1) | MFA admin, verificación contra claves filtradas |
| Pérdida de datos (disco efímero free) | Aviso documentado | PostgreSQL gestionado |
| Prompt injection vía adjuntos | System prompt prevalece; sin herramientas peligrosas | Filtro de adjuntos |
| Fuga de API key | Solo en entorno; nunca en código/repos | Rotación periódica |

## Reglas operativas para el administrador (Josep)
- Cambiar `PULLEX_ADMIN_CLAVE` por una fuerte al primer despliegue.
- Nunca compartir la clave `sk-ant-...`; si se filtra, revocarla en console.anthropic.com.
- Revisar consumo en console.anthropic.com semanalmente (control de costos).
- Backups: exportar usuarios/uso antes de cada cambio grande (V1: descargar pullex.db).
