# 07 — SEGURIDAD, PRIVACIDAD Y CUMPLIMIENTO

## Principios
Security first: nunca sacrificar seguridad por velocidad. Menor privilegio. Datos mínimos.

> **Actualizado 30-sep-2026:** la auditoría de `docs/audit/` encontró que varias afirmaciones de
> esta sección no se cumplían (autorización por recurso, XSS en el panel admin, errores que sí
> exponían detalles). El estado verificado, con pruebas, está en `docs/audit/05-security-current.md`.

## Implementado en V1
- Contraseñas: PBKDF2-SHA256, 600.000 iteraciones (desde 13-oct-2026; antes 200.000), sal única por
  usuario, guardadas como `p600000$<hex>`. Los hashes viejos se rehacen solos en el siguiente ingreso.
- Sesiones: tokens HMAC-SHA256 firmados con `PULLEX_SECRET`, expiración 14 días. En Vercel o Render la
  app NO arranca sin `PULLEX_SECRET`; en local usa `app_secret.key` creado con permisos 0600.
- Autorización por rol: rutas /api/admin/* exigen `es_admin` (403 si no).
- Autorización por recurso (desde Fase 1): cada conversación solo la ve, escribe o borra su dueño.
- Revocación de sesiones al cambiar/restablecer la clave y "cerrar sesión en todos los dispositivos".
- Límite de intentos por IP y por cuenta; cabeceras de seguridad y CSP; SRI en scripts de CDN.

## Cambios de la auditoría del 13-oct-2026 (área autenticación, sesiones y límites)
Pruebas de regresión: `tests/test_seguridad_auth.py` (una por hallazgo).
- **AUTH-01** Una cuenta desactivada recibe 403 en toda ruta con sesión (también el panel admin) y en el
  login con la clave correcta (con clave errada, 401). Desactivar cierra sus sesiones; el admin no puede
  desactivarse a sí mismo.
- **AUTH-02** `PULLEX_EXIGIR_VERIFICACION=1` exige correo verificado para lo que gasta consultas (admins
  exentos). Por defecto NO se exige: la entrega real del correo no está comprobada. Reenviar la verificación:
  máx. 3 por hora por cuenta. Restablecer la clave por correo marca el correo como verificado.
- **AUTH-03 / AUTH-13** Los tokens de los enlaces (verificar correo, restablecer clave) se gastan con un
  UPDATE condicional en la misma transacción que la acción: un enlace sirve una sola vez aunque lleguen
  varias peticiones a la vez. En la base se guarda su huella SHA-256, no el token; los vencidos hace más de
  un día se purgan. Los enlaces pendientes al desplegar este cambio dejan de valer (se pide otro).
- **AUTH-04** La IP se toma del último proxy confiable (`PULLEX_PROXIES_CONFIABLES`; por defecto 1 en
  Vercel/Render, 0 en local). El límite por cuenta vive en la tabla `limites` (compartido entre instancias;
  si la base falla, cae a memoria). La poda en memoria ya no vacía el diccionario.
- **AUTH-05** El tope de 26 MB se aplica a los bytes realmente leídos (también cuerpos «chunked»): 413 con
  las cabeceras de seguridad.
- **AUTH-07** Login con cuenta inexistente hace el mismo PBKDF2 (el tiempo no revela cuentas). El registro
  sigue respondiendo 409 si el correo ya existe (pendiente de decisión).
- **AUTH-08 / AUTH-09 / AUTH-10** «Continuar» una respuesta: máx. 3 por mensaje. Escrito modelo del taller:
  máx. 6 generaciones por hora por cuenta. El reinicio mensual del cupo es condicional (no borra consumos).
- **AUTH-12** `/docs`, `/redoc` y `/openapi.json` apagados salvo `PULLEX_DOCS=1`. `/salud` (pública) solo dice
  estado, base, si hay secreto y si hay IA; el modelo y el proveedor los ve el admin en métricas.
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
- Autorización expresa en el registro (IA-17, servidor): `/api/registro` exige `acepto_politica: true` y guarda
  la versión aceptada (`POLITICA_VERSION`, hoy `2026-10-13`) y la fecha. La política se sirve en
  `/politica-de-datos` (`static/politica-datos.html`; su texto lo redacta y revisa un abogado). Al cambiar el
  texto, sube `POLITICA_VERSION` en `app.py`.
- Pendiente (obligatorio antes de escalar): procedimiento de supresión de cuenta.

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
- Copias de seguridad: copia diaria cifrada del esquema `pullex` con `scripts/respaldar_bd.sh` (conexión directa, puerto 5432) y siempre una copia manual antes de cada cambio grande; restauración con `scripts/restaurar_bd.sh` y prueba de restauración cada trimestre (docs/18-BASE-DE-DATOS.md, «Copias de seguridad y restauración»). La base ya no es un archivo `pullex.db`: no se descarga nada del servidor.
