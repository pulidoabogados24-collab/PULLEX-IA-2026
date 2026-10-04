# Calidad de respuesta: entender, cubrir, no truncar, no inventar y poder medirlo

Estado: investigación y diseño de prompt y evaluaciones (PUL-018). **NOT VERIFIED** contra el modelo real: no hay
clave de API en este entorno, así que ninguna recomendación de este documento se ha medido sobre PULLEX. Lo que
está respaldado por una fuente se marca como tal; lo demás es hipótesis y está en la sección 4.

Especificación que origina el trabajo: `docs/coordinacion/ESPECIFICACION-MOTOR-RESPUESTAS.md` (texto literal del
dueño, 175 puntos). Prioridad del dueño: entender correctamente → responder completamente → verificar
jurídicamente → seguridad y privacidad → velocidad → presentación.

Archivos que salen de este trabajo: `prompts/calidad_respuesta.md`, `prompts/PROMPT-MAESTRO-PULLEX.md`,
`prompts/README.md`, `evaluacion/calidad_respuesta.jsonl`, `evaluacion/evaluar_calidad.py`,
`tests/test_evaluar_calidad.py`, `.claude/skills/pullex-response-intelligence/SKILL.md`,
`.claude/agents/{hermes,argos,minerva}.md`.

---

## 1. Resumen en cinco líneas

1. La respuesta incompleta tiene causas técnicas además de las del prompt: tope de salida, razonamiento que
   consume ese tope, cierre del flujo antes de tiempo y ausencia de lectura del motivo de parada.
2. Las herramientas jurídicas con búsqueda y recuperación siguen inventando entre el 17 % y el 33 % de las veces
   en un estudio revisado; un modelo general sin recuperación fue mucho peor. La citación se comprueba, no se
   presupone.
3. Pedirle al modelo que diga «no sé», que cite lo que afirma y que retire lo que no puede respaldar reduce las
   invenciones, pero no las elimina (lo dice la propia documentación del proveedor).
4. Para medir calidad conviene combinar comprobaciones deterministas (rápidas, repetibles) con un juez de modelo
   como señal secundaria, sabiendo que el juez tiene sesgos conocidos, entre ellos preferir lo más largo.
5. Más capas no son mejores por sí mismas: la guía de Anthropic recomienda añadir complejidad solo cuando
   demuestra mejorar el resultado. Por eso el diseño propuesto prefiere lógica determinista y un crítico solo en
   los casos de alto valor.

---

## 2. Fuentes consultadas

Todas se abrieron el **2026-10-04** con las herramientas de búsqueda y lectura web de la sesión. Aviso de método:
el contenido de cada página lo devolvió un lector automático que la resume, así que las cifras y citas breves de
este documento deben cotejarse con el original antes de citarlas en un escrito (HUMAN REVIEW REQUIRED). Las
direcciones de `docs.claude.com` redirigen a `platform.claude.com`; se anota la dirección final.

| # | Fuente | URL | Qué se tomó |
|---|---|---|---|
| F1 | Anthropic, «Prompting best practices» (Claude Platform Docs) | https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices | Instrucciones claras y explícitas; explicar el motivo de cada regla; documentos largos arriba y la pregunta al final (hasta 30 % de mejora en sus pruebas); citar primero los fragmentos relevantes; «investigar antes de responder»; verificación previa a terminar; 3 a 5 ejemplos; estilo más conciso en los modelos recientes |
| F2 | Anthropic, «Reduce hallucinations» | https://platform.claude.com/docs/en/test-and-evaluate/strengthen-guardrails/reduce-hallucinations | Permitir decir «no sé»; extraer citas literales primero en documentos largos; verificar con citas y retirar la afirmación sin cita; verificación en cadena; mejor-de-N; refinamiento iterativo; restringir al material entregado; advertencia de que no eliminan el problema |
| F3 | Anthropic, «Handling stop reasons» | https://platform.claude.com/docs/en/build-with-claude/handling-stop-reasons | `stop_reason: max_tokens` significa respuesta truncada por el tope; hay que revisarlo siempre; opciones: subir el tope o continuar; `model_context_window_exceeded` también es truncamiento; `pause_turn` y `refusal` tienen su propio manejo |
| F4 | Anthropic, «Streaming Messages» | https://platform.claude.com/docs/en/build-with-claude/streaming | El motivo de parada llega en el evento `message_delta`; pueden llegar eventos de error a mitad del flujo (por ejemplo `overloaded_error`); para reanudar un flujo cortado se hace una nueva petición con el texto parcial y la orden de continuar; bloques de razonamiento y herramientas no se recuperan parcialmente |
| F5 | Anthropic, «Adaptive thinking» | https://platform.claude.com/docs/en/build-with-claude/adaptive-thinking | El razonamiento cuenta dentro de `max_tokens`; un tope calculado para una respuesta sin razonamiento suele quedar corto; con esfuerzo alto es más probable agotar el presupuesto; remedios: subir el tope o bajar el esfuerzo |
| F6 | Anthropic, «Define success criteria and build evaluations» | https://platform.claude.com/docs/en/test-and-evaluate/develop-tests | Criterios específicos y medibles; evaluaciones que reflejen la tarea real incluidos los casos límite; automatizar; «más preguntas con calificación automática de señal algo menor es mejor que pocas calificadas a mano»; calificación por código, humana o por modelo; rúbricas detalladas y modelo juez distinto del generador |
| F7 | Anthropic, «Building effective agents» | https://www.anthropic.com/engineering/building-effective-agents | Patrones de enrutamiento, cadena con puertas de control y evaluador-optimizador (útil «cuando hay criterios claros de evaluación»); empezar simple y añadir complejidad solo si demuestra mejorar |
| F8 | Anthropic, «Citations» | https://platform.claude.com/docs/en/build-with-claude/citations | La función de citas devuelve punteros válidos a los documentos entregados; el texto citado no cuenta como tokens de salida; es más confiable que pedir citas por prompt; no es compatible con salidas estructuradas |
| F9 | Anthropic, «Introducing Contextual Retrieval» | https://www.anthropic.com/news/contextual-retrieval | Los fragmentos sin contexto se recuperan mal; añadir contexto por fragmento más BM25 redujo los fallos de recuperación 49 % (5,7 % a 2,9 %) y con reordenamiento 67 % (a 1,9 %); recomienda traer unos 20 fragmentos |
| F10 | Magesh et al., «Hallucination-Free? Assessing the Reliability of Leading AI Legal Research Tools» (J. Empirical Legal Studies, 2025) | https://arxiv.org/abs/2405.20362 | Tres herramientas comerciales de investigación jurídica con recuperación alucinaron entre 17 % y 33 %, menos que un modelo general pero muy por encima de lo que prometían los proveedores; la verificación humana sigue siendo necesaria |
| F11 | Dahl, Magesh, Suzgun y Ho, «Large Legal Fictions» (2024) | https://arxiv.org/abs/2401.01301 | Sobre preguntas verificables de casos federales de EE. UU., GPT-4 alucinó 58 % y Llama 2 88 %; los modelos no corrigen premisas jurídicas falsas del usuario («sesgo contrafactual») y no siempre saben cuándo alucinan |
| F12 | Dhuliawala et al., «Chain-of-Verification Reduces Hallucination in LLMs» (2023) | https://arxiv.org/abs/2309.11495 | Borrador, preguntas de verificación, respuestas independientes a esas preguntas y respuesta final corregida; reduce alucinaciones en varias tareas |
| F13 | Zheng et al., «Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena» (2023) | https://arxiv.org/abs/2306.05685 | Un juez fuerte coincide con las preferencias humanas en más del 80 %, pero tiene sesgo de posición, de verbosidad, de autopreferencia y razonamiento limitado |
| F14 | Liu et al., «Lost in the Middle» (2023) | https://arxiv.org/abs/2307.03172 | El rendimiento es mejor cuando lo relevante está al principio o al final del contexto y cae cuando está en medio |
| F15 | Lewis et al., «Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks» (2020) | https://arxiv.org/abs/2005.11401 | La recuperación aporta procedencia de la decisión y facilita actualizar el conocimiento; produce lenguaje más específico y factual que el modelo solo |
| F16 | «HealthBench» (OpenAI, 2025) | https://arxiv.org/abs/2505.08775 | Evaluación por rúbricas específicas de cada conversación (48.562 criterios, 262 médicos, 5.000 conversaciones) que cubre exactitud, seguimiento de instrucciones y comunicación; modelo para una evaluación jurídica por rúbricas |
| F17 | «Modeling Future Conversation Turns to Teach LLMs to Ask Clarifying Questions» (ICLR 2025) | https://arxiv.org/abs/2410.13788 | Los modelos suelen suponer una sola interpretación de una petición ambigua en lugar de aclarar |
| F18 | Su y Cardie, «Knowing but Not Showing: LLMs Recognize Ambiguity but Rarely Ask Clarifying Questions» (arXiv, mayo de 2026) | https://arxiv.org/abs/2605.25284 | Los modelos identifican la ambigüedad si se les pregunta, pero en la práctica responden directo; el contexto recuperado empeora esa conducta. Es un preprint reciente |
| F19 | Wikipedia, «Mata v. Avianca, Inc.» (fuente secundaria) | https://en.wikipedia.org/wiki/Mata_v._Avianca,_Inc. | Tribunal federal de Nueva York, sanción de 5.000 dólares el 22 de junio de 2023 por citar casos que no existían y que un asistente de IA había generado. Se cita como ejemplo del costo real de una cita inventada; confirmar en la providencia |
| F20 | Corte Constitucional, Sentencia T-323 de 2024 (relatoría) | https://www.corteconstitucional.gov.co/relatoria/2024/t-323-24.htm | Fija criterios para el uso de IA generativa por jueces: transparencia, responsabilidad y verificación de lo que entrega la herramienta, privacidad, no sustitución de la racionalidad humana, prevención de riesgos como alucinaciones y sesgos, control humano. La fecha (2 de agosto de 2024) salió del resumen del lector; confirmar en la relatoría |
| F21 | Consejo Superior de la Judicatura, Acuerdo PCSJA24-12243 del 16 de diciembre de 2024 (noticia institucional) | https://www.ramajudicial.gov.co/web/consejo-superior-de-la-judicatura/-/consejo-superior-de-la-judicatura-expidi%C3%B3-lineamientos-para-el-uso-responsable-y-seguro-de-la-ia-generativa-en-la-rama-judicial | Lineamientos de uso responsable de IA generativa en la Rama Judicial: verificación de los resultados antes de usarlos, supervisión humana y registro del uso. Se leyó la noticia, no el texto completo del acuerdo |

Fuentes que se intentaron y no se usaron: ninguna página fue rechazada; la búsqueda del Acuerdo PCSJA24-12243 también
devolvió el PDF oficial (`actosadministrativos.ramajudicial.gov.co`), que **no** se abrió.

---

## 3. Hallazgos sustentados y cómo se aplican a PULLEX

Cada hallazgo remite a su fuente. «Aplicación» es lo que se decidió en este trabajo; no está demostrado que
funcione en PULLEX (ver sección 4).

### 3.1 Truncamiento: revisar siempre el motivo de parada
- **Qué dice la fuente.** `max_tokens` es un tope duro; si se alcanza, la respuesta queda cortada y el motivo de
  parada lo indica; hay que revisarlo siempre y, o subir el tope, o continuar la respuesta (F3). El motivo llega
  en `message_delta` durante el flujo (F4). Un flujo interrumpido se reanuda con una petición nueva que lleva el
  texto parcial y pide continuar (F4). El razonamiento cuenta dentro del tope y un tope pensado para respuestas
  sin razonamiento suele quedar corto; con esfuerzo alto es más probable agotarlo (F5).
- **Aplicación.** El contrato del backend debe leer el motivo de parada, tratar `max_tokens` y
  `model_context_window_exceeded` como truncamiento, continuar sin duplicar y, si no puede, avisar en lugar de
  presentar la respuesta como completa (puntos 13 y 14 de la especificación). `evaluar_calidad.py` incluye
  `detectar_truncamiento` para detectar en el texto los síntomas que quedan cuando el motivo de parada no se
  conserva (frase cortada, lista numerada a medias, bloque de código sin cerrar, encabezado final sin cuerpo).
  Es una red de seguridad, no un sustituto de leer el motivo de parada.

### 3.2 Entender la intención y no responder una pregunta vecina
- **Qué dice la fuente.** Las instrucciones claras y explícitas producen mejores resultados; si un colega sin
  contexto se confundiría con el prompt, el modelo también (F1). Explicar el motivo de cada regla ayuda a
  generalizarla (F1). En los modelos recientes el estilo es más conciso y directo, por lo que hay que pedir
  explícitamente la profundidad deseada (F1).
- **Aplicación.** El bloque de prompt define un contrato de respuesta (intención principal, preguntas
  explícitas, formato, nivel de profundidad) y explica el porqué de cada regla. El enrutador de intención
  (agente Hermes) clasifica verbo y formato (`pregunta, investigación, análisis, redacción, comparación,
  extracción, resumen, acción, documento, voz`) con reglas deterministas primero.

### 3.3 Cobertura de preguntas múltiples
- **Qué dice la fuente.** Lo que hay en la bibliografía revisada sobre medir cobertura es indirecto: la
  documentación de evaluación recomienda criterios específicos y medibles y rúbricas detalladas (F6), y HealthBench
  evalúa con criterios propios de cada conversación, no con una respuesta única (F16).
- **Aplicación.** Cada caso dorado declara `partes_obligatorias`; `evaluar_calidad.cobertura_de_partes` mide
  cuántas aparecen en la respuesta (por palabras clave con alternativas, igual que `benchmark.py`). La métrica
  `missed_question_rate` del punto 159 se calcula como `1 - cobertura`. El agente Argos hace esa verificación en
  la ejecución real.
- **Límite.** Que una palabra clave aparezca no prueba que la parte esté bien respondida. Es un piso, no un techo.

### 3.4 No inventar normas ni sentencias
- **Qué dice la fuente.** Un modelo general sin recuperación inventó más de la mitad de las veces en preguntas
  verificables sobre casos (F11); las herramientas jurídicas con recuperación siguen entre el 17 % y el 33 % (F10);
  los modelos no corrigen premisas jurídicas falsas del usuario (F11) y no siempre saben cuándo alucinan (F11).
  La documentación del proveedor recomienda permitir «no sé», pedir citas literales, y retirar la afirmación que
  no tenga cita (F2). La verificación en cadena reduce alucinaciones en varias tareas (F12). La función de citas
  de la API da punteros válidos a los documentos entregados (F8). Un caso real de sanción por citas inexistentes
  generadas por un asistente muestra el costo (F19). En Colombia, la Corte Constitucional exige a los jueces
  verificar lo que entrega la IA y prevenir alucinaciones (F20), y el Consejo Superior pide verificación y
  supervisión humana (F21).
- **Aplicación.**
  1. El prompt autoriza expresamente a decir «no pude verificar esto», describe qué hacer cuando no se está seguro
     y exige corregir la premisa falsa de entrada (coherente con el `SYSTEM_PROMPT` actual).
  2. `evaluar_calidad.citas_sospechosas` es una revisión determinista de forma: extrae las referencias a
     sentencias y normas del texto y marca las que tienen formato imposible o riesgoso. Por ejemplo, una
     sentencia de tutela sin número, una sentencia con un año fuera de rango (la Corte Constitucional empezó en 1992),
     un artículo cuyo número no existe en el código citado, un radicado con formato impropio, o una cita
     textual atribuida a una sentencia sin su número. **No verifica que la sentencia exista**: eso exige consultar
     la relatoría (punto 40 de la especificación), y esa consulta no se hizo aquí.
  3. Se prefiere la recuperación sobre la memoria del modelo y que las citas del corpus se marquen `[F#]` como ya
     hace PULLEX.

### 3.5 Recuperación de fuentes (RAG jurídico)
- **Qué dice la fuente.** La recuperación da procedencia y actualizabilidad (F15). Los fragmentos sin contexto se
  recuperan peor; añadir contexto a cada fragmento, combinar con BM25 y reordenar redujo los fallos hasta 67 %
  (F9). El rendimiento cae cuando lo relevante queda en el medio de un contexto largo (F14); poner los
  documentos largos al inicio y la pregunta al final mejoró hasta 30 % en las pruebas de Anthropic (F1). Pedir
  que se citen primero los fragmentos relevantes ayuda en documentos largos (F1, F2).
- **Aplicación al prompt.** Material recuperado y documentos adjuntos antes de la pregunta, cada uno con su fuente;
  cuando se responda sobre un documento, citar primero lo que el documento dice y luego lo adicional. La parte de
  construir mejor el índice (fragmentos con contexto, mezcla léxica y semántica, reordenamiento) queda como
  recomendación para el motor de fuentes; no se tocó código.
- **Advertencia de F10.** La recuperación reduce pero no elimina las invenciones; no basta con tener RAG.

### 3.6 Preguntar o responder cuando algo es ambiguo
- **Qué dice la fuente.** Los modelos tienden a elegir una sola interpretación de una petición ambigua (F17) y, ya
  recuperado contexto, a responder directo en lugar de preguntar (F18, preprint de mayo de 2026). Es decir,
  la bibliografía describe el problema contrario al que menciona el dueño (demasiadas preguntas aclaratorias).
- **Aplicación.** La regla es la de la especificación (puntos 19 a 21): responder con mejor esfuerzo declarando el
  supuesto y qué dato lo cambiaría; preguntar solo si falta algo que impide responder materialmente. Para que
  el diseño no caiga en el extremo contrario, hay casos dorados de los dos tipos: ambiguos respondibles
  (no deben terminar en pregunta) y ambiguos no respondibles (una sola pregunta concreta).

### 3.7 Cómo medir
- **Qué dice la fuente.** Criterios específicos y medibles; evaluación que refleje la tarea real y sus casos límite;
  automatizar; preferir más casos con calificación automática a pocos calificados a mano; elegir el método más
  rápido y confiable: código para lo que es regla, humano para lo que exige criterio, modelo para lo intermedio;
  juez de modelo con rúbrica detallada, salida acotada y modelo distinto del generador (F6). Un juez de modelo
  coincide con humanos en más del 80 % pero prefiere respuestas largas, depende del orden y se favorece a sí
  mismo (F13). La evaluación por rúbricas específicas de cada caso es un patrón probado en medicina (F16).
- **Aplicación.**
  - Capa 1, determinista (`evaluar_calidad.py`): cobertura de partes, errores prohibidos, truncamiento, citas
    sospechosas, directitud de la apertura, exceso de advertencias, longitud respecto del mínimo orientativo,
    pregunta aclaratoria innecesaria, falta de conclusión. Sin red, sin modelo.
  - Capa 2, juez de modelo (no implementada): puntuar con la rúbrica de la sección 5, con un modelo distinto del
    generador, mezclando el orden y **sin premiar la longitud**. Señal secundaria (punto 107).
  - Capa 3, revisión humana por un abogado: obligatoria para cualquier cifra que se publique. Los casos dorados
    son material de prueba, no verdad jurídica.
  - Longitud: se usa solo como piso orientativo para detectar respuestas demasiado cortas. Premiar la longitud
    sería caer en el sesgo de verbosidad (F13) y contradice el punto 109 de la especificación.

### 3.8 Cuántas capas
- **Qué dice la fuente.** Los patrones de enrutamiento, de cadena con puertas de control y de evaluador-optimizador
  son los adecuados cuando hay criterios claros, pero Anthropic recomienda empezar con lo más simple y añadir
  complejidad solo si mejora el resultado de forma demostrable (F7). La verificación previa a terminar («antes de
  terminar, comprueba tu respuesta contra estos criterios») es una instrucción barata que la documentación señala
  como eficaz (F1).
- **Aplicación.** Hermes y Argos son, primero, funciones deterministas (el punto 167 prefiere lógica determinista
  a llamadas de modelo). Minerva, el crítico, solo se invoca en casos de alto valor (puntos 55 y 56) y solo
  reescribe si encuentra un defecto. La verificación de último paso va también dentro del prompt principal como
  una comprobación breve.

---

## 4. Hipótesis (no sustentadas en una fuente leída, no medidas en PULLEX)

H1. Una parte de las respuestas cortas que ha visto el dueño viene del tope de salida con razonamiento, no del
prompt. Se infiere de F5 y de que `MAX_TOKENS_CHAT` vale 8.000 con razonamiento adaptativo; no se midió.
Para saberlo hay que registrar el motivo de parada de cada respuesta (punto 100) y contar cuántas terminan en
`max_tokens`.

H2. El bloque de calidad añade unas 1.200 palabras (unos 7.400 caracteres) al prompt fijo. Es texto cacheable como el resto, pero
el costo y la latencia de ese aumento no se midieron, ni se sabe si mejora o empeora las respuestas simples.

H3. La instrucción «responde primero, sin avisos repetidos» reducirá las advertencias redundantes. Es plausible por
F1 (instrucciones explícitas con su porqué), pero el `SYSTEM_PROMPT` ya la pedía en parte.

H4. Las expresiones regulares de `citas_sospechosas` capturan los formatos colombianos más frecuentes (T-, C-, SU-,
Ley, Decreto, artículo, radicado), pero no se probaron contra respuestas reales del modelo. Habrá falsos positivos
y falsos negativos. Los intervalos de años y de números por código son aproximaciones y deben revisarse.

H5. Los umbrales de longitud mínima de cada caso dorado son estimaciones del autor, no medidas sobre respuestas de
abogados. Por eso son «orientativos».

H6. Un juez de modelo con la rúbrica de la sección 5 detectará omisiones mejor que las palabras clave. No se probó.

H7. La parte de mejora del índice de fuentes (fragmentos con contexto, BM25, reordenamiento) transferirá a un corpus
jurídico colombiano la mejora que Anthropic mide en sus propios conjuntos de datos (F9). No hay medida en este
repositorio.

H8. Escalar de un modelo rápido a otro superior (puntos 61 a 63) mejora la calidad jurídica en preguntas difíciles
lo suficiente para justificar el costo. No se leyó ninguna fuente sobre esto ni se midió.

---

## 5. Rúbrica propuesta de calidad (para el juez y para la revisión humana)

Escala de 0 a 2 por dimensión. Primero se evalúan las dimensiones de contenido; la forma solo desempata. Pesos
siguiendo la prioridad del dueño.

| Dimensión | Peso | 0 | 1 | 2 |
|---|---|---|---|---|
| Intención | 3 | Responde otra cosa | Responde la pregunta pero desvía parte | Responde exactamente lo preguntado |
| Cobertura | 3 | Omite más de una parte | Omite una parte | Cubre todas las partes |
| Apoyo jurídico | 3 | Hay una norma o sentencia inventada o mal atribuida | Citas correctas pero incompletas o sin marcar lo incierto | Fundamento verificable y la incertidumbre marcada |
| Aplicación a los hechos | 2 | Solo teoría | Aplicación parcial | Subsume los hechos y da contraargumento |
| Conclusión y siguiente paso | 2 | Sin conclusión | Conclusión vaga | Conclusión clara y paso concreto |
| Honestidad sobre incertidumbre | 2 | Falsa certeza | Incertidumbre genérica | Dice qué no pudo verificar y qué dato cambiaría la respuesta |
| Proporción | 1 | Relleno o demasiado corta | Algo desbalanceada | Tan corta como se pueda y tan larga como haga falta |
| Forma | 1 | Plantilla rígida o advertencias repetidas | Aceptable | Natural, estructura según la pregunta |

Reglas de decisión sugeridas (a validar con abogados): cualquier 0 en Intención, Cobertura o Apoyo jurídico es
reprobado sin importar el total; sobre el resto, un puntaje ponderado de al menos el 80 % pasa.

---

## 6. Observaciones sobre el código actual (solo lectura; sin cambios)

Es lectura de `app.py` y `proveedores.py` en `pul/integracion @ 00cbb98`. La auditoría completa y las
correcciones del motor son de PUL-017, que trabaja en esos archivos; aquí solo se anota lo útil para el prompt
y las evaluaciones.

- `MAX_TOKENS_CHAT` toma 8.000 por defecto (`PULLEX_MAX_TOKENS`) y es el mismo para todas las consultas (el punto
  11 pide presupuesto dinámico). El comentario del propio código reconoce que el razonamiento adaptativo cuenta
  dentro del tope (coherente con F5).
- Una búsqueda de `stop_reason`, `finish_reason` y `incomplete` en `app.py` y `proveedores.py` no encontró ninguna
  lectura del motivo de parada: el flujo transmite el texto y termina sin saber si el modelo acabó o fue cortado.
  Esto es consistente con la hipótesis H1, no la prueba.
- El `SYSTEM_PROMPT` ya contiene: respuesta primero, pregunta única solo si cambia la respuesta, jerarquía de
  fuentes, «(pendiente de verificación)», corrección de premisas falsas y límites. Lo que no tiene: contrato de
  respuesta, cobertura de preguntas múltiples, profundidad según complejidad, seguimientos cortos, modo reparación
  de intención («eso no fue lo que pregunté»), verbos y formato pedido. El bloque nuevo cubre eso sin duplicar lo
  que ya existe.
- `evaluacion/benchmark.py` y `golden.jsonl` miden palabras que deben o no aparecer (30 preguntas). El conjunto
  nuevo es complementario: añade partes obligatorias, errores prohibidos específicos y longitud mínima.

---

## 7. Qué NO se hizo

- No se llamó a ningún modelo. No hay medición antes y después. Ninguna afirmación de que PULLEX «responde mejor»
  está respaldada.
- No se abrieron los textos completos de F10, F11, F12, F13 y F16; se usaron los resúmenes de la página del
  resumen (abstract) obtenida por el lector. No se abrió el PDF del Acuerdo PCSJA24-12243.
- No se consultó ninguna relatoría para verificar que las sentencias mencionadas en los casos dorados existan o
  digan lo que se les atribuye. Por eso los casos dorados evitan exigir números de sentencia concretos y, cuando
  mencionan alguna norma, se trata de normas básicas y conocidas que deben revisarse igualmente.
- No se evaluó cuánto cuesta en tokens el bloque nuevo.
