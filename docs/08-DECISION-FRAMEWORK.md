# 08 — MARCO DE DECISIONES Y TRADE-OFFS

## Método obligatorio para toda decisión técnica
1. Definir el problema (sin proponer solución aún).
2. Generar ≥3 alternativas reales.
3. Matriz: costo · escalabilidad · rendimiento · seguridad · mantenibilidad · complejidad ·
   velocidad de desarrollo · UX · facilidad de IA.
4. Elegir UNA, justificar, y documentar por qué se descartaron las otras.
5. Auditoría de la propia solución (errores, contradicciones, riesgos) antes de entregar.

## Decisiones ya tomadas (registro)

### D-001 · Arquitectura: Monolito Modular (vs Microservicios vs Serverless)
| Criterio | Monolito Modular | Microservicios | Serverless |
|---|---|---|---|
| Costo | ★★★ (gratis en Render) | ★ (múltiples servicios) | ★★ (por invocación) |
| Complejidad para 1 persona | ★★★ | ★ | ★★ |
| Velocidad de desarrollo | ★★★ | ★ | ★★ |
| Escala hasta ~5k usuarios | ★★★ | ★★★ | ★★★ |
**Elegido:** Monolito Modular. Microservicios se reevalúa a ~5.000 usuarios activos.

### D-002 · Modelo IA: Haiku 4.5 (vs Sonnet vs Opus)
Haiku: 1/5 USD por M tokens → consulta ≈ 40–50 COP → margen sano con plan de $30.000.
Sonnet/Opus quedan para plan Profesional (V3) donde el precio lo soporte.
**Actualización oct-2026:** el modelo por defecto pasa a Sonnet 5.5 (precisión y fuentes verificables). El
impacto en el margen del plan Básico está pendiente de decisión (docs/11, sección de costos).

### D-003 · Base de datos: SQLite (vs PostgreSQL)
SQLite: cero configuración y suficiente en V1. **Deuda técnica aceptada y documentada:**
en Render free el disco es efímero → migrar a PostgreSQL al llegar a ~20 clientes pagos.

### D-004 · Frontend sin framework (vs React/Next)
Una sola página HTML/JS: carga rápida, sin build, mantenible por el fundador. React se
justificaría con equipo o con UI mucho más compleja (V3).

### D-005 · Cobro manual por Nequi (vs pasarela)
Manual: cero comisión, cero integración, validación del negocio primero. Pasarela (Wompi/
MercadoPago) en V2 con ~20 pagos/mes, cuando el tiempo del admin valga más que la comisión.

### D-006 · Agentes: enrutador ligero (vs multi-agente real)
Instrucciones especializadas activadas por detección de área: 90% del beneficio con 1% del
costo/latencia. Multi-agente con herramientas: V3.

### D-007 · Nombre: PULLEX IA
Pulido + Lex. Búsqueda preliminar sin conflictos relevantes en LegalTech Colombia.
Pendiente: búsqueda formal de antecedentes y registro ante la SIC (el fundador es abogado).

## Ficha para nuevas funcionalidades (obligatoria)
Valor usuario · Valor negocio · Complejidad · Riesgo · Dependencias · Prioridad ·
Impacto esperado · Tiempo estimado. Sin ficha, no entra al roadmap.
