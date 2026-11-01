# Arquitectura técnica — PULLEX IA | Audiencia Live
Versión: 0.1 · Estado: MVP experimental aislado.

## 1. Principios
- Copiloto del abogado, NO sistema que decide credibilidad o prueba judicial.
- Contraste auditable: cada diferencia se explica con citas textuales y contexto.
- Ingesta controlada: autorización de audio, aislamiento por expediente, mínimo dato.
- Diseño offline/local para demo. Producción requiere backend, aislamiento, secreto y legalidad comprobados.
- No alterar la aplicación PULLEX IA existente sin una aprobación separada.

## 2. Flujo de eventos
```text
[Micrófono autorizado] --(Web Speech API en navegadores compatibles)--> [Transcripción provisional/final]
[Entrada manual] -----------------------------------------------------> [Turno final]
[Entrevistas TXT / fragmentos documentales] --> [Normalización e índice por expediente+declarante]
[Turno final] + [Fragmentos anteriores del MISMO declarante]
                  |
                  v
       [Extracción: hora, color, acción, objeto]
                  |
                  v
         [Recuperación de contexto]
                  |
                  v
      [Clasificador explicable, NO veredicto]
                  |
                  v
 [Alerta con fuente literal + razón + nivel de certeza]
                  |
                  v
  [Revisión humana -> pregunta -> exportación]
```

## 3. Componentes del MVP
| Capa | Contrato | Limitación |
|---|---|---|
| Captura | Micrófono con consentimiento y bandera de grabación visible | Web Speech API depende del navegador y puede procesar audio con proveedores del navegador |
| Transcripción | Texto final / provisional / marca temporal / hablante elegido | Sin diarización automática |
| Ingesta documental | Fragmentos TXT y pegado manual | PDF, DOCX y OCR pasan a la siguiente fase |
| Índice | Fragmentos estructurados en memoria por expediente y declarante | Sin motor vectorial |
| Contraste | Función pura `compareStatement` con reglas interpretables | Solo soporta fenómenos limitados, no razonamiento jurídico integral |
| Alertas | Clasificación, citas exactas, selección y revisión | No sustituye confrontación procesal |
| Persistencia | localStorage por dispositivo | No cifrada, no apta para documentos reservados |
| Exportación | JSON e impresión navegador | No representa expediente oficial |

## 4. Futuro diseño de producción
- Frontend React/Next.js TypeScript; accesibilidad WCAG 2.2 AA.
- API autenticada (FastAPI o NestJS), RBAC y MFA.
- PostgreSQL con RLS por `tenant_id` y `case_id`; transacciones auditables, migraciones.
- Almacenamiento privado de archivos, objetos versionados, hash SHA-256, antivirus y extracción asíncrona; cadena de custodia documentada pero nunca simulada.
- Adaptadores STT con streaming y diarización, consentimiento; buffers cifrados, tiempos de retención definidos.
- Recuperación híbrida FTS + embeddings solo en material autorizado y filtrado por `tenant_id/case_id/declarant_id`.
- Motor de hipótesis y clasificación con esquema JSON estricto, verificaciones deterministas y abstención cuando no existe contexto.
- Cola de eventos con idempotencia, secuencias y trazabilidad; métricas de latencia y porcentaje de alertas erróneas.
- Respuesta degradada segura: si falla STT u OCR, mostrar error y no inventar fragmentos.
- Aislamiento fuerte de casos, no reutilizar fragmentos entre clientes. Probar RLS con roles adversariales.

## 5. Modelo de datos y relaciones
Ver `docs/DATA_MODEL.md`. Todas las referencias se limitan a un expediente y declarante.
`Finding` guarda referencias a los IDs de `SourceFragment` y `Utterance`, y también el texto citado exacto al tiempo del análisis (snapshot), nivel de certeza, regla, estado de revisión, actor y momento de cambio.
`AuditEvent` solo se añade; no debe almacenar audio ni contenido completo sensible innecesario.

## 6. Estados del motor
- `possible-contradiction`: valores incompatibles respecto al mismo evento, requiere comprobar que contexto y momento realmente coinciden.
- `coincides`: afirmaciones compatibles.
- `expansion`: relato agrega detalle sin negar lo anterior.
- `not-found`: antecedente no localizado; no es mentira ni omisión acreditada.
- `inconclusive`: fuente ambigua, otro hablante, mala calidad o datos insuficientes.
Ningún resultado se anuncia como sentencia o conclusión judicial.

## 7. Seguridad y cumplimiento
Antes de usar expedientes reales: evaluación de autorización de captación de audio; régimen de reserva; Ley 1581 de 2012; definición de encargado/responsable de tratamiento; residencia y transferencia internacional; DPIA; MFA; autorización por caso; encriptación, RLS y pruebas de penetración. Prohibido usar proveedor de STT por navegador para casos reales sin evaluación de transmisión/retención. No capturar audio del sistema mediante evasión de permisos.

## 8. SLO y pruebas
Objetivo exploratorio: alerta útil dentro de 3 segundos desde turno final (no garantizado). Medir p50/p95, falsos positivos, fragmentos no atribuibles, citas inventadas (objetivo: cero) y errores por identidad. Pruebas unitarias del motor, integración y evaluación con transcripciones ficticias de múltiples hablantes.

## 9. Integración con PULLEX IA principal
Se propone integración futura como módulo enlazado con SSO y API interna autorizada, no acceso directo a las tablas existentes. Hasta entonces `apps/audiencia-live` no modifica `app.py`, `biblioteca.py`, base de datos ni despliegue principal.
