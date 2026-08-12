# 02 — ARQUITECTURA DE IA

## Modelo
- **V1:** Claude Haiku 4.5 (1 USD/M entrada, 5 USD/M salida — verificado jul-2026).
  Razón: mejor relación costo/calidad para consultas de estudiantes; margen del negocio sano.
- El modelo es configurable por variable de entorno (`PULLEX_MODELO`): cambiarlo no toca código.
- Boletín diario puede usar modelo distinto (`PULLEX_MODELO_BOLETIN`), se genera 1 vez/día.

## Orquestación de agentes (V1: enrutador ligero)
Un orquestador decide qué "agente" (instrucción especializada) se activa según el texto:
Penal, Laboral, Constitucional/Tutela, Civil/Familia, Administrativo, Comercial/Marcas.
Máximo 3 agentes simultáneos para no diluir el foco. V2: clasificador con el propio modelo;
V3: agentes con herramientas propias (citación, jurisprudencia, redacción, calidad).

## Anti-alucinación (defensa en capas)
1. System prompt con regla de oro (nunca inventar; declarar incertidumbre).
2. Jerarquía de fuentes explícita e inviolable.
3. Búsqueda web activada por defecto para verificar en fuentes oficiales.
4. Bloque final obligatorio en respuestas jurídicas: **Confianza** (Alta/Media/Baja con razón)
   y **Fuentes** utilizadas → explicabilidad (XAI) y auditoría por el usuario.
5. RAG opcional con corpus propio (lexcol-rag: voyage-law-2 + ChromaDB) que cita fragmentos.

## Memoria (separación)
- **Conversacional:** historial del hilo (SQLite, por conversación).
- **Del usuario:** campo "memoria" editable por el estudiante (se inyecta al system prompt).
- **Jurídica:** corpus RAG versionable (V2: versionado normativo con fechas de vigencia).
- **Empresarial:** preferencias y planes en DB.

## Evaluación de la IA (V2)
- Batería de preguntas doradas (respuesta conocida) para medir precisión y alucinación.
- Registro de respuestas con confianza Baja para revisión humana.
- Métrica objetivo: % de respuestas con fuentes verificables.

## Costos
- Consulta típica ≈ 5–12k tokens ≈ 40–50 COP con Haiku.
- Límite por plan = techo de gasto por usuario. Prompt caching en V2 para bajar aún más.

## Latencia
- Objetivo: primer token < 3 s; respuesta completa < 30 s. Streaming SSE siempre.
