# 09 — Riesgos y resultados de pruebas

## Resultados de pruebas (ejecutadas, no simuladas)

**Batería automática** (`pytest tests`, 38 pruebas tras la Fase 1b, doble del modelo de IA, sin llamadas reales):

| Momento | Resultado |
|---|---|
| Contra el código entregado (`pullex-ia-final.zip`) | **21 fallaron**, 14 pasaron (las 2 pruebas de compatibilidad se añadieron después). Los 21 fallos reproducen hallazgos reales: SEC-01…SEC-09, SEC-11, SEC-12, SEC-14, SEC-15, SEC-17, SEC-23, SEC-24 y AI-5 (SEC-13 y SEC-16 se corrigieron por revisión de código, sin prueba que los reproduzca). |
| Tras la Fase 1 | **37 pasaron, 0 fallaron.** |
| Tras la Fase 1b | **38 pasaron, 0 fallaron** (nueva `WEB_006`: ninguna página tiene JavaScript en línea). |

Detalle de la línea base: pasaban `AUTHZ_004` (estudiante no entra a rutas admin), `AUTH_001`, `AUTH_007` (token manipulado rechazado), `INPUT_004` (cupo en secuencia) y las 10 pruebas de regresión funcional. Todo lo demás de seguridad fallaba.

**Navegador real** (`tests/e2e_navegador.py`, Chromium, servidor local, CSP estricta): **30/30 verificaciones OK tras la Fase 1b**. Todo se maneja con clics y teclado reales (no llamando funciones por consola): recuperación de clave, pestañas, registro, sugerencias, interruptores, Enter para enviar, memoria y modo (llegan a la API), herramientas, actualizar boletín, modales, panel admin (ingresar, desactivar, refrescar) y la página de restablecer. Un `<img onerror>` inyectado no se ejecuta y el navegador reporta el bloqueo; el nombre malicioso se ve como texto en el panel admin; cero violaciones de CSP inesperadas en las tres páginas.

**Dependencias:** `pip-audit` sin vulnerabilidades conocidas.

## NOT VERIFIED en esta iteración

- Respuestas reales del modelo (calidad jurídica, alucinaciones, inyección directa, extracción del prompt): requieren clave de API y presupuesto.
- Envío real de correos por Resend.
- Despliegue en Render con estas cabeceras (probado solo en local; la CSP no depende del dominio, pero hay que abrir la app desplegada y revisar la consola una vez).
- Instalación como PWA en iPhone/Android tras el cambio del service worker.
- Accesibilidad (teclado, lector de pantalla, contraste): no auditada.

## Registro de riesgos abiertos

| Riesgo | Prob. | Impacto | Dueño | Mitigación propuesta |
|---|---|---|---|---|
| Pérdida de la base por disco efímero (SEC-10) | Media-alta | Alto | Josep (decisión de costo) | PostgreSQL gestionado con backups diarios o disco persistente de Render (plan de pago). Antes de eso: descargar la base antes de cada deploy. |
| Usar PULLEX con expedientes reales antes de tener base persistente, auditoría, política de datos y revisión de los términos del proveedor de IA | Alta si se abre el modo profesional | Muy alto (secreto profesional, Ley 1581) | Josep | **Puerta dura:** no aceptar expedientes con datos personales hasta cerrar Fase 2 + política publicada. |
| Citas no verificadas leídas como verificadas (AI-2, AI-4) | Media | Alto | Producto | Rotular "Confianza" como autoevaluación del modelo; revisión humana del boletín; Citation Guard en Fase 3-4. |
| Clave de firma filtrada en GitHub (SEC-05) | Baja-media | Alto | Josep | Revisar el repositorio; si `app_secret.key` está, borrarlo del historial. En Render la app usa `PULLEX_SECRET`, así que no hace falta rotar allí salvo que se haya usado el archivo. |
| Operador único (bus factor 1) | Cierta | Alto a mediano plazo | Josep | Runbook de operación; automatizar cobro/activación más adelante. |
| Los correos de verificación y recuperación no llegan a los estudiantes: el remitente configurado por defecto es `onboarding@resend.dev`, que según la documentación de Resend (https://resend.com/docs/knowledge-base/403-error-resend-dev-domain) solo entrega al correo del dueño de la cuenta de Resend | Alta si no se ha verificado un dominio | Medio (un estudiante que olvida la clave depende del admin) | Josep | Verificar un dominio propio en Resend y poner `PULLEX_EMAIL_FROM` con ese dominio. **NOT VERIFIED** en vivo. |
| Enumeración de cuentas por el registro (SEC-19) | Media | Bajo-medio | Producto | Registro con confirmación por correo antes de revelar si existe. |
| Afirmaciones exageradas en entregables anteriores | — | Reputacional | — | Ver sección siguiente. |

## Corrección de entregables anteriores

El documento `RESUMEN-ESTADO-PULLEX.md` entregado el 12-ago-2026 afirmaba cosas que esta auditoría no sostiene: que `app.py` tenía "46,000+ líneas" (tenía 962 líneas; eran ~46.000 *bytes*), que la app cumplía Habeas Data "para datos académicos" (la política de tratamiento de datos y la autorización expresa no existen aún), respondía "Sí" a "¿Es seguro?" y la rotulaba "LISTA PARA PRODUCCIÓN", cuando tenía tres vulnerabilidades críticas (SEC-01, SEC-02, SEC-03). Este informe reemplaza esas afirmaciones.
