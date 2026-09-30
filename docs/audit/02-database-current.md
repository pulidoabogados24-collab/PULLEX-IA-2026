# 02 — Base de datos actual

**Motor:** SQLite (`pullex.db`, ruta relativa al directorio de trabajo). Sin ORM, sin migraciones versionadas: el esquema se crea con `CREATE TABLE IF NOT EXISTS` y se amplía con `ALTER TABLE` envuelto en `try/except`.

## Esquema (tras Fase 1)

| Tabla | Columnas | Observaciones |
|---|---|---|
| `usuarios` | `email` PK, `nombre`, `sal`, `hash`, `plan`, `limite`, `usadas`, `periodo`, `activo`, `es_admin`, `email_verificado`, `preferencias` (JSON), `creado`, **`sesion_version`** (nueva) | El correo es la llave primaria y viaja en el token: cambiar de correo es imposible sin migración. |
| `conversaciones` | `id` INTEGER autoincremental, `usuario` (email), `titulo`, `creada` | IDs secuenciales públicos → facilitaban el IDOR (ver 05). Sin FK. |
| `mensajes` | `id`, `conv`, `rol`, `contenido`, `creada` | Solo texto. No guarda fuentes, confianza, modelo, tokens ni latencia (hallazgo C1 del documento de arquitectura 2026, sigue abierto). Sin FK. |
| `boletin` | `fecha` PK, `contenido`, `creado` | — |
| `tokens_accion` | `token` PK, `email`, `tipo`, `creado`, `expira`, `usado` | Un solo uso, con vencimiento. |

**Índices añadidos en Fase 1:** `conversaciones(usuario)`, `mensajes(conv)`, `tokens_accion(email, tipo)`.

## Hallazgos

| ID | Severidad | Hallazgo | Estado |
|---|---|---|---|
| DB-1 | HIGH | Disco efímero de Render free: la base completa (cuentas pagas, historial) puede perderse en un redeploy. No hay backups automáticos. | Abierto — requiere PostgreSQL gestionado o disco persistente (decisión de costo). |
| DB-2 | MEDIUM | Sin claves foráneas ni `ON DELETE`: borrar una conversación dejaba mensajes huérfanos si fallaba a mitad. | Mitigado (borrado en orden dentro de la misma transacción); FKs quedan para la migración. |
| DB-3 | MEDIUM | IDs secuenciales enumerables en `conversaciones`. | Mitigado con autorización por recurso; UUID públicos quedan para Fase 2. |
| DB-4 | MEDIUM | Sin migraciones versionadas. | Abierto (Alembic al pasar a PostgreSQL). |
| DB-5 | LOW | Correo como PK y como identidad en el token. | Abierto (Fase 2: `id` interno + `uuid` público). |
| DB-6 | INFO | 100 % de consultas parametrizadas; no se encontró SQL construido por concatenación. | Correcto. |

## Compatibilidad verificada

`tests/test_regresion.py::test_base_de_datos_anterior_se_migra_sola` crea una base con el esquema viejo y comprueba que la app arranca y agrega `email_verificado` y `sesion_version` sola. Las sesiones abiertas antes del despliegue siguen válidas (`test_sesiones_abiertas_antes_de_la_actualizacion_siguen_validas`).
