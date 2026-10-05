# 06 — Autenticación y sesiones

## Estado tras la Fase 1

| Control | Estado | Detalle |
|---|---|---|
| Hash de contraseñas | ✅ Correcto | PBKDF2-HMAC-SHA256, 200.000 iteraciones, sal aleatoria de 16 bytes por usuario, comparación `hmac.compare_digest`. Recomendación futura (no urgente): Argon2id o subir a ≥ 600.000 iteraciones según la guía vigente de OWASP. |
| Longitud de contraseña | ✅ | 8 a 256 caracteres (el tope evita gastar CPU del servidor con claves gigantes). No hay verificación contra contraseñas filtradas (pendiente). |
| Formato del token | ⚠️ Propio | `base64(json{u,t,v}).base64(HMAC-SHA256)`. Firmado correctamente y rechaza manipulación (`AUTH_007`). No es JWT estándar; aceptable mientras no haya SSO. |
| Secreto de firma | ✅ con condición | `PULLEX_SECRET` (Render lo genera). Sin él, se usa `app_secret.key` local — solo desarrollo; ahora se registra una advertencia y el archivo ya no viaja en el paquete. |
| Vida de la sesión | ⚠️ | 14 días fijos, sin renovación deslizante ni vencimiento por inactividad. |
| Revocación | ✅ **Nuevo** | `sesion_version`: cambiar clave, restablecerla o el reset del admin invalidan todas las sesiones anteriores; `POST /api/cerrar-sesiones` cierra todas a pedido del usuario. |
| Rotación tras login | ➖ N/A | No hay identificador de sesión en servidor que rotar; cada login emite un token nuevo. La fijación de sesión no aplica a este diseño. |
| Almacenamiento en el cliente | ✅ | Variable en memoria (no localStorage/sessionStorage, no URL). Contrapartida: recargar la página cierra la sesión. |
| Transporte | ✅ | Cabecera `Authorization`, no cookie → inmune a CSRF clásico. HSTS activo si `PULLEX_APP_URL` es https. |
| Fuerza bruta | ✅ **Mejorado** | Por IP (falsificable) + por cuenta (no falsificable). |
| Verificación de correo | ✅ | Enlace de un solo uso, 24 h. No bloquea el uso (decisión de producto). |
| Recuperación de contraseña | ✅ | Enlace de un solo uso, 1 h, respuesta anti-enumeración, 3 correos/hora por dirección, invalida otros enlaces pendientes y todas las sesiones. |
| MFA | ❌ | No existe. Prioritario para el administrador (Fase 2). |
| Gestión de dispositivos | ❌ | No hay lista de sesiones activas (requiere sesiones en servidor). |
| Roles | ❌ | Solo `es_admin`. Ver propuesta RBAC en 10. |

## Recomendación de arquitectura (Fase 2, no implementada)

Migrar a **sesión en servidor + cookie `HttpOnly; Secure; SameSite=Strict; Path=/`**, con tabla `sesiones(id, usuario_id, creada, ultima_actividad, ip_hash, user_agent, revocada)`. Eso habilita: lista de dispositivos, cierre individual, vencimiento por inactividad y que la sesión sobreviva a recargar la página. **Al hacerlo, la protección CSRF pasa a ser obligatoria** (token sincronizado o doble envío + validación de `Origin`), porque el navegador adjuntará la cookie solo. Se deja para Fase 2 porque toca todas las llamadas `fetch` del frontend y conviene hacerlo junto con RBAC en una sola migración probada.
