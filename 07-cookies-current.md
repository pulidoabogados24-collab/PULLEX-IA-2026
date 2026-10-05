# 07 — Auditoría de cookies

## Inventario (COOKIE_REGISTRY)

Se inspeccionaron todas las respuestas del servidor (`Set-Cookie`) y todo el JavaScript de las tres páginas (`document.cookie`, `localStorage`, `sessionStorage`, IndexedDB).

| Cookie | Propósito | Quién la crea | Contenido | HttpOnly | Secure | SameSite | Duración | Necesaria | Riesgo | Recomendación |
|---|---|---|---|---|---|---|---|---|---|---|
| — | — | — | — | — | — | — | — | — | — | — |

**Resultado: PULLEX IA no crea ninguna cookie** ni usa almacenamiento del navegador para datos de sesión. El único almacenamiento del lado del cliente es la **Cache Storage del service worker** (`pullex-v2`), que guarda la "cáscara" pública de la app (HTML, íconos) y, desde la Fase 1, excluye explícitamente la API, otros dominios y cualquier URL con `?token=`.

Terceros: las librerías `marked` y `DOMPurify` se cargan desde cdnjs con `crossorigin="anonymous"` y `referrerpolicy="no-referrer"`, por lo que el navegador no envía cookies ni la URL de la página a ese dominio. No hay analítica, píxeles ni publicidad.

## Consecuencia para el banner de consentimiento

Mientras no existan cookies no esenciales ni analítica, **no hace falta un banner de cookies**; mostrar uno sería ruido. Sí hace falta, por Ley 1581 de 2012, la política de tratamiento de datos y la autorización expresa en el registro (SEC-22) — eso es independiente de las cookies.

## Cuándo cambia esto

1. **Fase 2 — sesión con cookie HttpOnly:** aparecerá una cookie estrictamente necesaria. Configuración objetivo: `__Host-pullex_sesion`, `HttpOnly`, `Secure`, `SameSite=Strict`, `Path=/`, sin `Domain`, `Max-Age` ≤ 14 días, valor = identificador aleatorio opaco (nunca datos del usuario), rotación en login y cambio de privilegios, invalidación en logout. No requiere consentimiento (necesaria), sí debe figurar en la política.
2. **Si algún día se agrega analítica:** crear el Centro de Privacidad (aceptar / rechazar opcionales / configurar / revocar), guardar `consent_version`, fecha y categorías, y **no cargar el script de analítica antes del consentimiento**. Marketing: apagado por defecto.
