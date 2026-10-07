# PUL-018: prompt de calidad de respuesta, evaluaciones y skill

Rama: `pul/018-prompt-evals` (desde `pul/integracion @ 00cbb98`). Responsable: Claude. Revisor: Codex.
Estado: **EN REVISIÓN** con una salvedad central: **nada de esto se probó contra el modelo real** (no hay
`ANTHROPIC_API_KEY` en el entorno). Lo entregado se probó como código y como formato; no se midió que PULLEX responda
mejor.

Origen: `docs/coordinacion/ESPECIFICACION-MOTOR-RESPUESTAS.md` (texto literal del dueño). PUL-017 (motor de
respuestas en `app.py`, `motor_respuesta.py`, `static/`) trabaja en paralelo; esta tarea no tocó esos archivos.

## 1. Qué quedó

| Entregable | Archivo | Qué es |
|---|---|---|
| Investigación | `docs/17-CALIDAD-DE-RESPUESTA.md` | 21 fuentes abiertas el 2026-10-04 con URL; hallazgos aplicables separados de las hipótesis (H1 a H8); rúbrica propuesta; observaciones del código actual |
| Bloque de prompt | `prompts/calidad_respuesta.md` v1.0.0 | Contrato de respuesta, intención, respuesta primero, cobertura y profundidad, hechos y vacíos, seguimientos y reparación, no inventar lo jurídico, advertencias con medida, qué hacer si no se puede terminar, comprobación final (unas 1.200 palabras) |
| Prompt maestro | `prompts/PROMPT-MAESTRO-PULLEX.md` v1.0.0 | Identidad, el bloque anterior, modos (rápido, estándar, profundo, investigación, documento, voz), verbos, análisis de casos, voces, reglas jurídicas y límites; usa marcadores para no copiar `estilo_redaccion.py` |
| Cómo se usa y se versiona | `prompts/README.md`, `prompts_calidad.py` | Cargador puro (`cargar_bloque`, `cargar_maestro`) que falla si queda un marcador sin resolver |
| Casos dorados | `evaluacion/calidad_respuesta.jsonl` | 44 casos, 171 partes obligatorias, 65 errores prohibidos; todos con `estado_revision: SIN_REVISAR_POR_ABOGADO` |
| Evaluador | `evaluacion/evaluar_calidad.py` | Funciones puras y CLI (`validar`, `evaluar`); sin red ni modelo |
| Skill | `.claude/skills/pullex-response-intelligence/SKILL.md` | Flujo y reglas de calidad de respuesta |
| Subagentes | `.claude/agents/hermes.md`, `argos.md`, `minerva.md` | Intención, cobertura, crítico y reparación |
| Versionado | `.gitignore` | Se versionan `.claude/skills/` y `.claude/agents/`; `.claude/worktrees/` y los datos locales siguen fuera |

Cobertura de los casos dorados: Tutela 7, Laboral 7, Penal 8, Civil y familia 8, Administrativo 4, Comercial 4,
Transversal 6; 26 de ciudadano y 18 de abogado. Tipos: simples (6), multi-parte (7), caso largo (5), ambiguas
respondibles (3) y crítica (1), seguimientos (4), redacción (4), revisión (1), documento (1), premisa falsa (3),
reparación de intención (1), alto riesgo (2) y riesgo de alucinación (6). Los siete casos de prueba históricos del punto
155 de la especificación tienen representante (cuatro subpreguntas: CR16; caso penal largo: CR15; pregunta simple:
CR08; pregunta sobre documento: CR27; ambigua respondible: CR03 y CR20; sentencia que no se encuentra: CR40; generación
larga: CR10 y CR06 con `min_palabras` alto).

## 2. Evidencia

- `python -m pytest -q`: **807 pasan** (antes del trabajo: 620). Las 187 nuevas son: 23 de `tests/test_prompts_calidad.py`,
  154 de `tests/test_evaluar_calidad.py` y 10 de `tests/test_skill_agentes_calidad.py`.
- `python evaluacion/evaluar_calidad.py validar` sobre los 44 casos: 0 problemas de forma.
- Pruebas que sí demuestran algo:
  - Cada caso es internamente coherente: un texto armado con las pistas cubre todas las partes y no cae en un error
    prohibido (44 pruebas).
  - Un modelo de mentira que repite la consulta, o que no responde, nunca aprueba ninguno de los 44 casos
    (44 pruebas, 88 comprobaciones). En la corrida de línea base con la consulta como respuesta: tasa de aprobación 0,0 y
    `missed_question_rate` 0,71.
  - Respuestas escritas a mano (buenas y malas) para los casos históricos: cuatro subpreguntas con dos omitidas
    no aprueba; apertura con relleno no es directa; respuesta cortada se detecta; sentencia inexistente inventada se
    marca y la honesta aprueba; solo preguntas no aprueba una consulta ambigua respondible; un «explícame más» que
    repite lo anterior se marca.
  - 8 respuestas con forma jurídica correcta (artículo 86, Decreto 2591, Ley 1755…) no se marcan como sospechosas;
    11 con forma imposible sí.
- Archivos de PUL-017 (`app.py`, `proveedores.py`, `static/`, `tests/test_motor_respuesta.py`) sin cambios.

Lo que estas pruebas NO demuestran: que el modelo real obedezca el prompt, que mejore frente al prompt actual, ni que
los umbrales del evaluador sean los adecuados. Las respuestas «buenas» de las pruebas las escribió el mismo autor
del evaluador, así que pasan por construcción; es una prueba del arnés, no del modelo.

## 3. Qué NO está verificado

1. **Todo el efecto sobre el modelo.** No se hizo ninguna llamada a un modelo. No hay antes y después. No se puede
   decir que PULLEX ahora sea «más directo, más completo, más preciso o con menos alucinaciones».
2. **El contenido jurídico de los casos dorados.** Las partes obligatorias, los errores prohibidos y las
   `comportamiento_esperado` los redactó Claude sin revisión de un abogado colombiano. Pueden contener errores o
   exigir cosas discutibles (por ejemplo, el plazo de impugnación o los umbrales del revisor fiscal). Se escribieron
   evitando números de sentencia y fijando solo normas muy conocidas, y los casos con plazos exigen marcar la
   verificación. Aun así: **un abogado debe revisarlos antes de usarlos como verdad**.
3. **Las 21 fuentes se leyeron por medio de un lector que las resume.** Cifras como 17 % a 33 %, 58 % o 49 % salen de ese
   resumen y deben cotejarse con el original. No se abrió el texto completo del Acuerdo PCSJA24-12243 ni de la
   Sentencia T-323 de 2024 más allá de lo que devolvió el lector.
4. **Que `citas_sospechosas` sirva en producción.** Revisa solo la forma. Los topes de artículos por código son
   generosos y aproximados; los de sentencia (C 1500, T 2000, SU 1500) y los de coherencia ley-año son estimaciones. No
   comprueba existencia. Habrá falsos positivos y falsos negativos con texto real.
5. **Que `detectar_truncamiento` detecte todos los cortes.** Detecta síntomas; un corte que cae justo al final de una
   frase completa no se ve. Con `stop_reason` conservado es exacto. El motor actual **no conserva** el motivo de parada
   (ver `docs/17`, sección 6): ese es el arreglo de fondo y es de PUL-017.
6. **El costo del bloque.** Agrega unas 1.200 palabras al prompt fijo; no se midieron tokens ni latencia ni si
   empeora las respuestas simples.
7. **Los subagentes.** Hermes, Argos y Minerva son archivos de definición. No se ejecutaron como subagentes ni se
   probó que su salida JSON sea estable.
8. **El prompt maestro frente al `SYSTEM_PROMPT` actual.** Se reconstruyó conservando las reglas jurídicas y los
   límites (una prueba comprueba que están), pero no se comparó línea por línea ni lo revisó un abogado. Mientras tanto,
   vale el prompt actual.
9. **El juez de modelo.** Está descrito en `docs/17` pero no implementado.

## 4. Cómo integrarlo (para PUL-017 u otra persona)

1. Mínimo: en `app.py`, añadir `prompts_calidad.cargar_bloque()` al `SYSTEM_PROMPT` justo después de la presentación
   (sigue siendo texto fijo, cacheable). `prompts/README.md` explica las dos formas de integrarlo.
2. Leer y guardar el motivo de parada de cada respuesta en `proveedores.py` (Anthropic: `stop_reason` en
   `message_delta`; OpenAI: el estado de la respuesta) y, si es de corte, continuar o avisar. Hasta que eso exista no
   se sabe cuántas respuestas llegan cortadas.
3. Usar `evaluar_calidad.detectar_truncamiento` como red de seguridad y `cobertura_de_partes` en los casos de alto valor.
4. Con clave y presupuesto (PUL-008): correr los 44 casos contra el modelo con el prompt actual y con el nuevo, guardar
   las respuestas en un `.jsonl` (`{id, respuesta, stop_reason}`) y calificarlas con
   `python evaluacion/evaluar_calidad.py evaluar --respuestas …`. Esa es la primera medición real; el resultado va a
   `evaluacion/resultados/` (ignorado por git).

## 5. Siguiente paso recomendado

1. Que un abogado colombiano revise los 44 casos y las reglas del prompt maestro (cambiar `estado_revision` solo
   cuando lo haya hecho).
2. Primera corrida real antes y después (punto 4.4) con las respuestas revisadas a mano en una muestra.
3. Medir el motivo de parada en producción para confirmar o descartar la hipótesis H1 (cortes por el tope de salida).
4. Después, y solo si las medidas lo piden: juez de modelo con la rúbrica de `docs/17` (sección 5) como señal secundaria
   y mejora del índice de fuentes (fragmentos con contexto, mezcla léxica y semántica, reordenamiento).

## 6. Pendientes de coordinación

- `docs/coordinacion/TABLERO.md` no tiene fila de PUL-017 ni de PUL-018; no se editó para evitar conflicto con PUL-017.
  Fila sugerida: `PUL-018 | Prompt de calidad de respuesta, evaluaciones y skill | Claude | Codex | EN REVISIÓN | rama pul/018-prompt-evals; 807 pytest; 44 casos dorados sin revisión de abogado; NADA probado contra el modelo real`.
- El entorno de pruebas no traía `pytest`; se instaló con `pip install -r requirements-dev.txt` (no hay cambios en el repositorio).
