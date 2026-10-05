# 10 — Plan de migración hacia PULLEX IA 2026

Este plan toma la visión de las cinco capas (Academy, Legal Brain, Professional, Institutional, Secure Core) y la ordena según lo que el código real permite hoy. No propone reescribir: cada fase deja la app funcionando y con pruebas en verde.

## Arquitectura destino

```
Navegador (SPA actual → pantallas por modo: Academia / Profesional / Institucional)
   │  cookie HttpOnly (Fase 2)
   ▼
FastAPI — monolito modular (se parte app.py en paquetes, NO en microservicios)
   ├─ secure_core/   identidad, sesiones, RBAC por recurso, auditoría, límites, cabeceras
   ├─ legal_brain/   orquestador → clasificador de intención → enrutador de dominio
   │                 → skills versionadas → recuperación (RAG) → borrador
   │                 → revisor adversarial ("abogado del diablo") → Citation Guard
   │                 → compositor de respuesta (con fuentes y estado de verificación)
   ├─ academy/       Laboratorio de casos, rúbricas, banco de errores, repaso espaciado, mapa de conceptos
   ├─ professional/  workspaces, expedientes, documentos, cronologías, matriz de pruebas
   └─ institutional/ organizaciones, miembros, roles, aislamiento por organización
   ▼
PostgreSQL gestionado (+ pgvector para el RAG) · almacenamiento de archivos fuera de /static
   ▼
Proveedor(es) de IA detrás de un router de modelos + pasarela de privacidad (PII)
```

**Principio de ingeniería:** un solo proceso y una sola base mientras no haya una razón medible para separar. El "multiagente" es una secuencia de llamadas orquestadas dentro del mismo backend, no una flota de servicios.

## Esquema propuesto (PostgreSQL, núcleo)

```sql
-- Secure Core
usuarios(id bigserial PK, uuid uuid UNIQUE, email citext UNIQUE, password_hash, nombre,
         tipo text CHECK (tipo IN ('STUDENT','LAWYER','PROFESSOR','RESEARCHER',
         'INSTITUTION_MEMBER','ADMIN','SECURITY_ADMIN')), estado, email_verificado_en,
         sesion_version int, creado_en, actualizado_en, ultimo_login_en)
sesiones(id text PK /*aleatorio opaco*/, usuario_id FK, creada, ultima_actividad,
         expira, revocada_en, ip_hash, user_agent)
organizaciones(id, uuid, nombre, tipo, estado, creada)
miembros(organizacion_id FK, usuario_id FK, rol_id FK, estado, unido_en, PK(org,usuario))
roles(id, nombre) · permisos(id, codigo /*case.read, document.upload…*/) · rol_permisos(rol_id, permiso_id)
auditoria(id, cuando, actor_id, organizacion_id, accion, recurso_tipo, recurso_id, ip_hash, meta jsonb)
eventos_seguridad(id, tipo, severidad, usuario_id, organizacion_id, ip_hash, cuando, meta jsonb, estado)
consentimientos(usuario_id, version_politica, categorias jsonb, cuando)

-- Legal Brain
conversaciones(id, uuid, usuario_id FK, workspace_id FK NULL, titulo, creada)
mensajes(id, conversacion_id FK ON DELETE CASCADE, rol, contenido, creado)
respuestas_meta(mensaje_id FK, modelo, prompt_version, skill_versiones jsonb, tokens_in, tokens_out,
                costo_estimado, latencia_ms, busquedas jsonb, estado_verificacion)
fuentes_juridicas(id, tipo /*CONSTITUCION, LEY, DECRETO, SENTENCIA…*/, titulo, autoridad, numero,
                  url_oficial, fecha_publicacion, vigente_desde, vigente_hasta, modificada_por,
                  estado /*VERIFICADO, PARCIAL, PENDIENTE, DEROGADO, SUPERADO*/, verificada_en,
                  hash_contenido)
fragmentos(id, fuente_id FK, texto, embedding vector, articulo, vigente_desde, vigente_hasta)
citas(id, mensaje_id FK, texto_citado, fuente_id FK NULL, estado /*VERIFICADA, PARCIAL,
      SIN_VERIFICAR, NO_ENCONTRADA*/, verificada_en)
skills(id, slug, version, dominio, subdominio, estado /*DRAFT, TESTING, APPROVED, PRODUCTION,
       DEPRECATED*/, prompt, validadores jsonb, ultima_revision_juridica, aprobada_por, UNIQUE(slug,version))
prompts(id, nombre, version, hash, creado_por, aprobado_por, desplegado_en, resultado_eval jsonb)

-- Academy
conceptos(id, nombre, dominio, padre_id FK NULL, dificultad)
concepto_fuente(concepto_id, fuente_id)
casos(id, dominio, dificultad, enunciado, problemas_esperados jsonb, fuentes_esperadas jsonb,
      rubrica_id, origen /*GENERADO, REVISADO_HUMANO*/)
intentos(id, usuario_id, caso_id, respuesta, puntajes jsonb, omisiones jsonb, pistas_usadas int, creado)
errores_aprendizaje(usuario_id, concepto_id, frecuencia, severidad, primera_vez, ultima_vez, resuelto_en)
repaso(usuario_id, concepto_id, estado, ultimo_repaso, proximo_repaso, facilidad)

-- Professional / Institutional
workspaces(id, uuid, organizacion_id FK NULL, dueno_id FK, nombre, tipo, visibilidad)
documentos(id, uuid, workspace_id FK, nombre_original, sha256, mime_real, tamano,
           ruta_interna /*fuera de rutas públicas*/, clasificacion /*NORMAL, CONFIDENCIAL, RESTRINGIDO*/,
           sospecha_inyeccion bool, subido_por, subido_en)
```

Toda consulta de datos de negocio filtra por `usuario_id` o por `organizacion_id` del miembro autenticado; el patrón `conversacion_de()` de la Fase 1 se generaliza a una función de autorización por recurso para cada tabla.

## Fases (orden recomendado)

| Fase | Contenido | Puerta para darla por terminada |
|---|---|---|
| **0 ✅** | Auditoría, línea base, pruebas que reproducen hallazgos | Este paquete |
| **1 ✅** | Críticos y altos corregibles sin romper (ver 05) | 37/37 pruebas, 11/11 navegador |
| **1b ✅** | CSP sin `'unsafe-inline'` en scripts (JS a archivos, despachador `data-click` con lista blanca), rótulo de autoevaluación bajo "Confianza", aviso reforzado del boletín. Registro sin enumeración evaluado y pospuesto hasta tener dominio verificado en Resend (ver SEC-19). | 38/38 pruebas, 30/30 navegador |
| **2** | PostgreSQL gestionado + backups diarios probados con restauración; partir `app.py` en módulos; sesión en servidor con cookie `HttpOnly` + CSRF; tabla de auditoría; MFA para admin; `uuid` públicos; RBAC mínimo (STUDENT, ADMIN) con permisos por recurso; política de tratamiento de datos y autorización en el registro (**revisión jurídica humana**) | Restauración de backup ensayada; pruebas AUTH/AUTHZ/WEB-003 CSRF; política publicada |
| **3** | Legal Brain v1: clasificador de intención + dominio (llamada barata), `respuestas_meta` por respuesta, prompts y skills versionados en base, revisor adversarial en segunda pasada para respuestas jurídicas de fondo, recorte del historial | Registro de modelo/tokens/fuentes en cada respuesta; batería de 50 preguntas doradas revisadas por un abogado |
| **4** | RAG verificable: corpus del Drive (solo `01`–`06`, nunca expedientes de clientes) → `fuentes_juridicas` + `fragmentos` con vigencia; Citation Guard que marca cada cita VERIFICADA / PARCIAL / SIN VERIFICAR / NO ENCONTRADA; "derecho a una fecha" usando `vigente_desde/hasta` | Pruebas anti-alucinación: sentencia inexistente, norma derogada, premisa falsa |
| **5** | Laboratorio de casos v1 (ver recomendación abajo) | Rúbrica calibrada con 20 casos revisados por un docente |
| **6** | Academy completa: banco de errores, repaso espaciado, mapa de conceptos, modo socrático, examinador, oral con cronómetro, "¿qué cambia si…?" | Métricas de aprendizaje sin mecánicas compulsivas |
| **7** | Professional: workspaces, carga segura de documentos (MIME real, SHA-256, fuera de `/static`), pasarela de privacidad (detección y seudonimización de PII), cronologías, matriz de pruebas, Document Studio | **Puerta dura:** ningún expediente real antes de cerrar Fase 2 y revisar los términos de datos del proveedor de IA |
| **8** | Institutional: organizaciones, miembros, roles, aislamiento verificado (pruebas TENANT-001, fugas por búsqueda, vector, caché y exportación) | Pruebas de aislamiento en verde |
| **9** | Security Center, benchmark jurídico propio (cientos de casos), red teaming, rendimiento, accesibilidad | Informe final de seguridad con tabla hallazgo/severidad/estado |

### Recomendación sobre el orden (decisión de Josep)

El plan maestro pone Academia en la fase 6. Mi recomendación es adelantar un **Laboratorio de casos v0 inmediatamente después de la Fase 2**, antes del RAG completo, por tres razones: (1) el mercado que paga hoy son estudiantes, y el Laboratorio de casos es lo que diferencia a PULLEX de "otro chat jurídico"; (2) técnicamente es barato sobre la base actual — un generador de casos, una pantalla de respuesta, una rúbrica y dos tablas (`casos`, `intentos`); (3) valida con usuarios reales si el método pedagógico funciona antes de invertir en el corpus. El riesgo es que la retroalimentación cite normas sin Citation Guard; se mitiga usando casos **revisados por un humano** con `fuentes_esperadas` fijadas de antemano, en lugar de dejar que el modelo invente la solución de referencia.

## Archivos que tocará cada fase (estimado)

Fase 1b: `static/index.html`, `static/admin.html`, nuevos `static/app.js`, `static/admin.js`, `app.py` (CSP). · Fase 2: `app.py` → `pullex/{secure_core,db,api}/…`, `render.yaml` (base de datos), `requirements.txt` (psycopg, alembic), migraciones, `tests/`. · Fases 3-4: `pullex/legal_brain/…`, script de ingesta del corpus, `tests/evals/`. · Fase 5+: `pullex/academy/…`, nuevas pantallas.

## Pruebas que deben crearse en fases siguientes

AUTH-002 fijación de sesión (cuando haya cookie), WEB-003 CSRF, FILE-001…004 (recorrido de rutas, MIME falso, tamaño, nombre malicioso), AI-001 inyección directa y AI-003 extracción de secretos **contra el modelo real**, AI-004 fuga RAG entre usuarios, TENANT-001 aislamiento de organizaciones, prueba de concurrencia del cupo, restauración de backup, y la batería jurídica (norma vigente/modificada/derogada, jurisprudencia falsa o contradictoria, temporalidad, competencia, caducidad vs. prescripción, prueba).
