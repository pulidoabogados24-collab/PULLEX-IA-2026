---
name: pullex-response-intelligence
description: PULLEX RESPONSE INTELLIGENCE. Úsala SIEMPRE que se trabaje en la calidad de las respuestas de PULLEX IA o LEXCOL (prompt, enrutador, motor de respuestas, evaluaciones) o cuando una respuesta salga corta, incompleta, desviada, que omita preguntas, que no profundice, que se corte a la mitad, o que cite normas o sentencias dudosas. Cubre detección de intención, descomposición de preguntas, cobertura, profundidad, completitud, control de truncamiento, reparación de la respuesta y evaluaciones. No la uses para estilo de redacción (eso es estilo_redaccion.py).
---

# PULLEX Response Intelligence

Objetivo del producto: que la persona piense «eso era exactamente lo que estaba preguntando» y, en consultas complejas, «respondió todo, me explicó por qué y puedo verificarlo». Prioridad del dueño: entender correctamente, responder completo, verificar lo jurídico, seguridad y privacidad, velocidad, presentación. Una respuesta bonita que contesta otra cosa no sirve.

Estado honesto: lo de este directorio es borrador. Nada se ha medido contra el modelo real (no hay clave de API en el entorno de PUL-018). No afirmes que algo mejoró sin una corrida que lo demuestre.

## Dónde está cada cosa

| Qué | Dónde |
|---|---|
| Especificación del dueño (175 puntos, literal) | `docs/coordinacion/ESPECIFICACION-MOTOR-RESPUESTAS.md` |
| Investigación con fuentes y qué es hipótesis | `docs/17-CALIDAD-DE-RESPUESTA.md` |
| Bloque de prompt (contrato, intención, cobertura, no inventar…) | `prompts/calidad_respuesta.md` |
| Prompt maestro integrado y cómo se versiona | `prompts/PROMPT-MAESTRO-PULLEX.md`, `prompts/README.md`, cargador `prompts_calidad.py` |
| Casos dorados (44) | `evaluacion/calidad_respuesta.jsonl` |
| Evaluador determinista (sin modelo) | `evaluacion/evaluar_calidad.py`, pruebas `tests/test_evaluar_calidad.py` |
| Subagentes | `.claude/agents/hermes.md` (intención), `argos.md` (cobertura), `minerva.md` (crítico y reparación) |
| Estado y pendientes de PUL-018 | `docs/coordinacion/PUL-018-prompt-y-evaluaciones.md` |

## Flujo de trabajo

Usa el nivel de profundidad mínimo que la consulta justifica. «Hola» o una definición no pasan por el flujo completo (punto 152 de la especificación).

1. **Intención (Hermes).** Fija la intención principal (pregunta, investigación, análisis, redacción, comparación, extracción, resumen, acción, documento, voz), el formato pedido, la jurisdicción y si es un seguimiento. Verbo manda: «dime» no es ensayo; «redáctame» es un documento completo; «revisa» es leer el texto entregado. Prefiere reglas deterministas a una llamada de modelo.
2. **Descomposición.** Cuenta las preguntas (`evaluar_calidad.contar_preguntas`) y escribe una parte por entregable. En un caso con hechos, separa hechos dados de inferencias.
3. **Profundidad.** BRIEF, NORMAL, DEEP o EXPERT según número de preguntas, hechos, normas, fechas, riesgo y tipo de entregable. No uses el mismo tope de tokens para todo.
4. **Redacción.** Respuesta primero; luego el porqué, la aplicación a los hechos, el contraargumento y la conclusión con siguiente paso. Sin advertencias repetidas.
5. **Cobertura (Argos).** Contrasta la respuesta con las partes: `cobertura_de_partes`. Si falta una, complétala antes de enviar.
6. **Truncamiento.** Lee el motivo de parada del proveedor (`max_tokens`, `length`, `model_context_window_exceeded`, `incomplete`) y, si no se conserva, usa `detectar_truncamiento`. Si está cortada: continúa sin duplicar (`continuacion_duplicada`) o avísalo; nunca la presentes como completa.
7. **Crítico y reparación (Minerva).** Solo en casos de alto valor (jurídico complejo, riesgo alto, investigación, documentos, contratos). Detecta omisiones, contradicciones, afirmaciones sin soporte, falsa certeza y relleno. Repara y entrega la versión corregida, no el borrador.
8. **Citas.** `citas_sospechosas` revisa solo la forma (número imposible, año fuera de rango, radicado o ponente que la persona no dio, cita textual atribuida). No prueba que la sentencia exista: eso exige la relatoría.

## Reglas que no se negocian

- No inventes normas, artículos, sentencias, radicados, ponentes, fechas ni cifras. Es mejor «No pude verificar esa sentencia en una fuente oficial» que un dato falso.
- Si falta contexto no crítico, responde con mejor esfuerzo («Con los hechos que indicas…») y di qué dato cambiaría la conclusión. Pregunta antes de responder solo si algo impide responder, y una sola pregunta.
- La longitud no mide calidad. Sirve para detectar respuestas demasiado cortas, nunca para premiar las largas.
- El juez de modelo, si se usa, es señal secundaria y nunca la única verificación jurídica.
- Los casos dorados y sus pistas no han pasado por un abogado: son material de prueba, no verdad jurídica.

## Comandos

```bash
python evaluacion/evaluar_calidad.py validar                       # forma de los casos
python evaluacion/evaluar_calidad.py evaluar --respuestas r.jsonl  # califica respuestas guardadas, sin modelo
python -m pytest -q tests/test_evaluar_calidad.py tests/test_prompts_calidad.py
```

`r.jsonl`: una línea por caso, `{"id": "CR01", "respuesta": "…", "stop_reason": "end_turn"}`.

## Cuando una respuesta salga mala

Antes de tocar el prompt, descarta las causas técnicas: tope de salida (el razonamiento cuenta dentro del tope), motivo de parada ignorado, flujo cerrado antes de tiempo, tiempo de espera de la función o del proxy, truncamiento del contexto, modelo demasiado pequeño para la consulta. Registra el motivo de parada de cada respuesta: sin ese dato no se sabe si el problema es el prompt o el corte.
