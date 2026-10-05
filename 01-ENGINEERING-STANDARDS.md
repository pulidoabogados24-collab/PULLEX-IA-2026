# 01 — ESTÁNDARES DE INGENIERÍA

## Arquitectura vigente (V1): Monolito Modular
Decisión de comité (ver 08): FastAPI + SQLite en Render. Un solo servicio, módulos internos
separados por responsabilidad: `auth`, `planes`, `chat`, `boletin`, `admin`, `corpus`.

**Por qué NO microservicios hoy:** un operador, <1.000 usuarios, presupuesto mínimo. Los
microservicios multiplican costo operativo y complejidad sin beneficio a esta escala
(KISS, YAGNI). Se reevalúa al superar ~5.000 usuarios activos o al necesitar equipos paralelos.

## Principios de diseño obligatorios
- **Única responsabilidad** por componente; módulos independientes (el módulo Penal no
  depende del Laboral: los "agentes" son instrucciones especializadas independientes).
- SOLID, DRY, KISS, YAGNI. Nada de tecnología por moda (toda adopción pasa por 08).
- Diseñar para: mantener, probar, escalar, documentar, reemplazar, extender, auditar, migrar.

## Evolución planificada (arquitectura evolutiva)
| Si ocurre… | Cambio previsto | Impacto contenido porque… |
|---|---|---|
| 100× usuarios | SQLite → PostgreSQL; Render → contenedores | La capa de datos está aislada en funciones `db()` |
| Cambia el modelo de IA | Cambiar `PULLEX_MODELO` (variable de entorno) | El modelo nunca está quemado en el código |
| Nuevas fuentes oficiales | Actualizar módulo boletín/corpus | Fuentes en un solo lugar |
| Se agrega pasarela de pagos | Módulo `pagos` nuevo | Los planes ya existen como datos, no como código |

## Backend
- Python 3.11+, FastAPI, SQLite (V1) → PostgreSQL (V2).
- Secretos SIEMPRE en variables de entorno; jamás en el código (lección aprendida: el
  incidente `ANTHROPIC_API_KEY=sk-ant...` pegado en `app.py` rompió el despliegue).
- Toda ruta autenticada valida token firmado (HMAC-SHA256); contraseñas con PBKDF2 (200k iter).

## Frontend
- HTML/CSS/JS sin framework (V1): carga rápida, cero build, mantenible por una persona.
- Streaming SSE con render por `requestAnimationFrame` (fluidez sin recargar).
- PWA instalable (manifest + service worker; el SW nunca cachea `/api/*`).

## Observabilidad (V1 mínima viable)
- Endpoint `/salud` (health check: servicio, DB, IA configurada).
- Logs de Render como fuente primaria de diagnóstico.
- V2: métricas de uso por endpoint, alertas, tracing.

## Fail-safe (obligatorio)
Si la IA falla: modo degradado con enlaces a fuentes oficiales, la consulta NO se cobra,
y el usuario nunca queda sin respuesta.
