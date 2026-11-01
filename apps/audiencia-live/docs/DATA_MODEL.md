# Modelo de dominio y contratos (propuesto)
**Case**: id, tenantId, radicado, delito, despacho, rol, etapa, isDemo, createdAt.
**Declarant**: id, caseId, displayName, role, validatedIdentity.
**SourceDocument**: id, caseId, declarantId, filename, mime, documentDate, sha256, retentionClass, ingestStatus, authorization.
**SourceFragment**: id, documentId, caseId, declarantId, page?, paragraph?, quoteExact, createdAt.
**HearingSession**: id, caseId, startedAt, endedAt?, consentBasis, recordingPolicy.
**Utterance**: id, sessionId, caseId, speakerId?, speakerVerified, startMs, endMs, text, transcriptStatus, sourceChannel.
**Finding**: id, caseId, utteranceId, fragmentId?, category, currentQuoteExact, priorQuoteExact?, sourceLabel?, reason, confidenceLabel, ruleVersion, reviewStatus, reviewedBy?, reviewedAt?.
**Question**: id, caseId, findingId?, text, type, author, createdAt.
**AuditEvent**: id, tenantId, caseId, actorId, action, targetId, at, metadataSansSecrets.

Todos los ID deben ser únicos; el motor no debe usar una declaración anterior de otro declarante. Mantener snapshots para que se sepa qué información vio el abogado al validar. Las correcciones de transcripción deben registrar un nuevo evento, no reescribir silenciosamente un hallazgo histórico.

## Futura política RLS (invariante)
Una consulta o mutación únicamente puede afectar `tenant_id` y `case_id` asociados al usuario autenticado y autorizado. Servicio de procesamiento opera con privilegios mínimos por tarea, credenciales jamás en el frontend y comprobaciones dentro de servidor. Tests con dos tenants comprueban que ninguno lee al otro.
