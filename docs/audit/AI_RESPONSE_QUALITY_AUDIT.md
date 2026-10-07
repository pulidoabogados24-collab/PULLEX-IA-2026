# Auditoría de la calidad de las respuestas de la IA (PUL-017)

Fecha: 2026-10-04. Rama `pul/017-motor-respuestas`, sobre `pul/integracion` en `00cbb98` («base»).
Las líneas con «base» son del commit `00cbb98` (`git show 00cbb98:archivo`); las demás son del estado actual de la rama.

**Alcance y honestidad.** No hay `ANTHROPIC_API_KEY` en este entorno: ninguna conclusión de esta auditoría se probó contra el
modelo real. Lo que sí se verificó es la tubería (qué se envía al modelo, qué se hace con lo que devuelve, qué ve la
persona) con modelos simulados. Cada sección separa **hecho verificado** de **hipótesis por confirmar con el modelo real**.
La calidad jurídica de las respuestas NO se midió aquí.

Orden de prioridad aplicado (el del dueño): entender bien lo pedido → responder completo → verificar jurídicamente →
seguridad y privacidad → velocidad → presentación. Se auditaron primero las causas técnicas y luego los prompts.

---

## 1. Arquitectura actual (antes del cambio)

Ruta del chat: `POST /api/chat` (base `app.py:1467`) → recupera fragmentos del corpus con el texto crudo del mensaje
(base `app.py:1441`) → arma `system` = `SYSTEM_PROMPT` (cacheado) + un bloque dinámico (fecha, agentes, estilo, memoria,
corpus) → `proveedores.stream_texto(...)` con `MAX_TOKENS_CHAT` fijo (base `app.py:87`, `app.py:1578`) → reenvía cada evento
como SSE → pule el texto (`redaccion.pulir`) → guarda → emite `fuentes` y `fin` (base `app.py:1626-1627`).
El navegador (`static/app.js`, base `enviar`, línea 247) pinta el stream y, si la lectura falla, agrega «se interrumpió la
conexión» (base `static/app.js:278`).

Proveedores: Anthropic (principal) y OpenAI (respaldo) detrás de `proveedores.py`. El modelo por defecto es Sonnet 5.5 con
razonamiento adaptativo (base `app.py:74`, `app.py:93`: no se envía `thinking`; el razonamiento cuenta dentro de `max_tokens`).

## 2. Modos de falla históricos (lo que la persona percibía)

Descripción del dueño: respuestas que se cortaban a mitad, que no contestaban lo que se preguntó, o que contestaban
solo una parte de una pregunta con varias partes. Mapa hacia las causas (sección 3):

| Síntoma | Causa técnica probable | Evidencia |
|---|---|---|
| La respuesta se corta a mitad de frase o de lista | C1 y C2 | base `app.py:87`, `proveedores.py:97-150` |
| Parece terminada pero falta la conclusión o una parte | C1 (el razonamiento consumió el cupo) + C2 | ídem |
| Contesta otra cosa o ignora una sub-pregunta | C5 (no hay comprobación de qué se pidió) y C6 (seguimientos sin contexto) | base `app.py:1441`, `app.py:1528` |
| La pantalla se queda «pensando» y luego nada | C3 (sin latido ni límite de inactividad) | base `app.py:1573-1583` |
| Se pierde lo ya escrito si se cierra la pestaña | C4 | base `app.py:1613-1625` |
| Conversaciones largas se degradan o fallan | C7 (historial completo, sin recorte) | base `app.py:1522-1528` |

## 3. Causas raíz

### C1. Tope de salida fijo (8000) con el razonamiento adentro
Base `app.py:87`: `MAX_TOKENS_CHAT = 8000` para todo: un saludo y una demanda. Con razonamiento adaptativo, lo que el modelo
«piensa» se descuenta de ese cupo antes de escribir (`app.py:93` base). **Hecho verificado en el código**: no existía ningún
cálculo por tipo de consulta. **Hipótesis por confirmar**: cuánto razonamiento consume Sonnet 5.5 en consultas largas; si
fueran 5000 tokens, quedarían unos 3000 de texto visible (unas 2000 palabras como máximo, menos en español con citas).

### C2. El motivo de parada se descartaba
La API de Anthropic informa por qué terminó (`stop_reason`: `end_turn`, `max_tokens`, `pause_turn`, `refusal`…) en el evento
`message_delta`. Base `proveedores.py:97-150` (`evento_anthropic`) no lo leía, y `AnthropicProveedor.stream` (base línea 142)
solo reenviaba texto. Resultado: una respuesta cortada por `max_tokens` se guardaba y se mostraba como terminada, sin aviso,
sin «Continuar» y sin ninguna señal para telemetría. Es la causa principal de «se corta». **Hecho verificado** por lectura de
código y por la prueba nueva que reproduce el corte con el doble de prueba (sección 7).

### C3. Sin latido ni límite de inactividad
Base `app.py:1573-1583`: el generador solo emitía cuando llegaba un evento del modelo. Con razonamiento largo o búsqueda
web no salía nada durante decenas de segundos; un proxy o balanceador puede cerrar una conexión inactiva, y el navegador no
distingue «pensando» de «muerta». Tampoco había límite de inactividad: un proveedor colgado dejaba la petición abierta.
**Por confirmar**: el tiempo de inactividad que tolera el hosting real (Render); no se probó.

### C4. Lo generado se perdía al cortarse la conexión
Base `app.py:1613-1625`: el mensaje se guardaba solo al final. Si la persona cerraba la pestaña o se caía la red, no
quedaba nada guardado y la consulta ya estaba descontada.

### C5. Nadie comprobaba que se respondió lo pedido
No existía representación de «qué pidió la persona» (partes, entregable, profundidad, riesgo) ni verificación posterior. Las
instrucciones de calidad estaban solo en el prompt largo, que el modelo puede o no cumplir. Una pregunta con cuatro partes
no producía ninguna señal si se contestaban dos.

### C6. Los seguimientos perdían contexto en la recuperación
Base `app.py:1441`: `fuentes.buscar(texto)` con el mensaje crudo. Para «¿y el dolo?» o «amplía eso» el corpus se consultaba
sin el tema de la conversación, y el enrutador de agentes (`enrutar_agentes(texto)`, base `app.py:347`) tampoco veía el tema.

### C7. Historial sin recorte
Base `app.py:1522-1528`: se enviaba todo el historial de la conversación. Una conversación muy larga puede exceder la
ventana de contexto (error del proveedor) o diluir la pregunta actual.

### Otras observaciones
- El texto pulido (`redaccion.pulir`) se aplicaba también a respuestas cortadas, lo que dificulta continuarlas.
- Otros generadores (documentos, flujos, escrito modelo del Taller, boletín, JSON del Laboratorio, perfiles) tenían el mismo
  riesgo: ninguno miraba el motivo de parada (sección 6).

## 4. Problemas por capa (resumen)

- **Prompt**: la guía de calidad no existía como bloque separado; `prompts/calidad_respuesta.md` pertenece a PUL-018 y puede no
  existir cuando se despliega esta rama. Se resolvió con carga opcional y una constante de respaldo.
- **Modelo**: razonamiento adaptativo dentro de `max_tokens` (C1). El comportamiento real de `pause_turn` con búsqueda web
  no se probó.
- **RAG**: consulta cruda (C6). No se cambió el ranking ni el corpus.
- **Streaming**: C2, C3, C4. Además faltaban las cabeceras `no-transform` y `X-Accel-Buffering: no` para que los
  intermediarios no acumulen el stream.
- **Límite de tokens**: C1.
- **Contexto**: C7.

## 5. Correcciones recomendadas (en el orden en que se aplicaron)

1. Leer y normalizar el motivo de parada de ambos proveedores; nunca presentar como completa una respuesta cortada.
2. Presupuesto de tokens por consulta (texto + margen de razonamiento) en vez de un número fijo.
3. Continuación automática cuando se corta (limitada), con empalme sin duplicar texto, y botón «Continuar» si no alcanza.
4. Latido SSE, límite de inactividad y cabeceras anti-buffering.
5. Guardar lo parcial si se cierra la conexión, marcado como incompleto y continuable.
6. Contrato de respuesta (HERMES): qué se pidió, partes, entregable, profundidad, riesgo; inyectado en el `system`.
7. Comprobación determinista de cobertura (ARGOS) y una sola reparación (MINERVA) cuando falta una parte.
8. Recorte de historial que conserva la pregunta actual, los primeros hechos y las cifras.
9. Telemetría local sin texto sensible y valoración 👍/👎 con motivos de lista cerrada.
10. Aplicar lo mismo a los demás generadores.
11. (PUL-018, fuera de esta rama) prompt de calidad, investigación y evaluaciones con modelo real.

## 6. Correcciones implementadas

| # | Cambio | Dónde | Antes → después |
|---|---|---|---|
| 1 | Motivo de parada normalizado | `proveedores.py` `motivo_anthropic` (110), `evento_anthropic` (117), `completar_texto` (419), `crear_con_parada` (407) | Descartado → evento `{"tipo":"parada","motivo","tokens_salida"}`; también en OpenAI (`response.incomplete`), **no probado contra la API real** |
| 2 | Presupuesto de tokens | `motor_respuesta.presupuesto_tokens` (603); `app.py:92` | 8000 fijo → 2700 (saludo), 6000 (pregunta normal), 11000 (4 sub-preguntas), 14000 (un escrito), 15000 (investigación) con Sonnet; tope `PULLEX_MAX_TOKENS`, por defecto 16000 |
| 3 | Continuación automática | `motor_respuesta.generar` (1026) | Cortaba → hasta 3 continuaciones (`PULLEX_MAX_CONTINUACIONES`), texto empalmado sin duplicar |
| 4 | Respuesta incompleta visible | `app.py` `_flujo_chat` (1547): evento `incompleta` + `fin.completo`; `static/app.js` `avisoIncompleta` (365) | Se veía como terminada → aviso claro y botón «Continuar» |
| 5 | «Continuar» | `app.py` `_chat_continuar` (1771); `static/app.js` `continuarResp` (325) | No existía → completa el mismo mensaje, no gasta consulta, límite de ritmo 30/10 min |
| 6 | Latido e inactividad | `motor_respuesta.con_latido` (1146); `app.py:94-95` | Sin señales → comentario `: latido` cada 15 s y corte a los 150 s sin eventos (modo degradado si no había texto; incompleta y continuable si ya lo había) |
| 7 | Parcial guardado | `app.py` `_flujo_chat`, bloque `finally` | Se perdía → se guarda como incompleto y es continuable |
| 8 | Contrato (HERMES) | `motor_respuesta.clasificar` (488), `contrato_a_instruccion` (832); `app.py` `_armar_system` (1514) | Sin contrato → contrato en el bloque dinámico del `system` |
| 9 | ARGOS | `verificar_cobertura` (705) | Sin comprobación → cobertura léxica, orden de la respuesta directa, conclusión, longitud |
| 10 | MINERVA | `decidir_reparacion` (767), dentro de `generar` | Sin reparación → UNA reparación si falta una parte; nunca sobre respuestas cortadas |
| 11 | Seguimientos | `clasificar` (`consulta_recuperacion`) | Recuperación con «¿y el dolo?» → recuperación y agentes con la pregunta anterior |
| 12 | Contexto | `recortar_historial` (1253) | Historial completo → recorte con resumen de fechas, cifras, normas y radicados |
| 13 | Guía de calidad | `cargar_calidad` (907) | No existía → lee `prompts/calidad_respuesta.md` si existe (o `PULLEX_PROMPT_CALIDAD`), si no usa una constante |
| 14 | Telemetría | `telemetria_respuestas.py`; `app.py` `_registrar_calidad` | Nada → tabla `calidad_respuestas` (solo etiquetas y conteos) |
| 15 | Valoración | `POST /api/feedback` (1810), `GET /api/admin/calidad` (1833); `static/app.js` `panelValorar` (375) | Nada → 👍/👎 con cinco motivos de lista cerrada |
| 16 | Cabeceras SSE | `app.py` `CABECERAS_SSE` (1768) | Sin ellas → `no-cache, no-transform`, `X-Accel-Buffering: no` |
| 17 | Otros generadores | `llamar_json`, `documentos_generar`, `_ejecutar_pasos`, `taller.py` (modelo), `generar_boletin_texto`, `perfiles/rutas.py` | Ver abajo |

Detalle del punto 17 (todos con prueba en `tests/test_generadores_truncados.py`):

- `llamar_json` (Laboratorio de casos, Taller, Documentos y Biblioteca): si el JSON sale cortado por el límite se reintenta
  con el doble de `max_tokens` (tope `PULLEX_MAX_TOKENS_JSON_TOPE`, 16000). Antes reintentaba con el mismo límite y fallaba igual.
- Borrador de documento: se continúa; si sigue cortado se marca INCOMPLETO en el texto, en las advertencias y en el campo
  `incompleto` de la respuesta (la consulta no se reintegra porque se entregó un borrador).
- Pasos de un flujo: cada paso usa la generación con continuación; si sigue cortado se agrega un aviso visible, el evento
  `paso_incompleto` (la interfaz lo marca «Incompleto») y el flujo se guarda con «(incompleto)» en el título.
- Escrito modelo del Taller: se continúa; si queda cortado se avisa y **no** se guarda en la caché compartida de modelos curados.
- Boletín: `max_tokens` de 1800 a 4000 y aviso si se corta (antes se guardaba el cortado todo el día).
- Perfiles del coordinador: si la salida se corta se agrega un aviso a su resultado y se informa `cortada`.

## 7. Resultados de las pruebas

Comandos y resultados reales (todos ejecutados en este entorno, con el modelo SIMULADO):

| Comando | Resultado |
|---|---|
| `python -m pytest -q` (suite completa) | 766 pasan (620 al empezar la tarea) |
| `python -m pytest -q tests/test_motor_respuesta.py` | 110 pasan (24 casos dorados de intención/profundidad/áreas, más dorados de riesgo, entregables, seguimiento, órdenes cortas, ARGOS y MINERVA) |
| `python -m pytest -q tests/test_chat_motor.py` | 24 pasan (integración con `/api/chat`: contrato, tokens, continuación, nunca fingir, Continuar, caídas, latido, MINERVA, contexto, telemetría, valoración, aislamiento) |
| `python -m pytest -q tests/test_generadores_truncados.py` | 12 pasan |
| `PORT=8774 python demo/servidor_simulado.py` + `BASE=http://127.0.0.1:8774 python tests/e2e_respuestas.py` | 31 verificaciones OK a 1280 y 390 px; cero violaciones de CSP y cero errores de consola |

**No verificado** (necesita el modelo real o el hosting real):
- Cuántos tokens consume el razonamiento y si el presupuesto nuevo basta en consultas largas.
- El comportamiento real de `stop_reason`, de `pause_turn` con búsqueda web y de la ruta de OpenAI.
- Si Render u otro intermediario cierra conexiones y si el latido de 15 s es suficiente.
- Que ARGOS (léxico) detecte las omisiones reales de un modelo; sus falsos positivos y negativos no se midieron con respuestas reales.
- Que la guía de calidad y el contrato mejoren la calidad percibida (se necesita una evaluación con el modelo real, ver PUL-008/PUL-018).
- La calidad jurídica de cualquier respuesta: nada de esto la mide.

## 8. Limitaciones conocidas

- Los adjuntos no se guardan entre turnos: en un seguimiento el modelo ya no ve el PDF o la imagen original (no se cambió).
- MINERVA no puede «arreglar antes de mostrar» porque el texto ya se transmitió; la reparación se agrega al final.
- ARGOS es una comprobación por palabras: puede dar por cubierta una parte que se nombra sin responderse.
- Sobre `pause_turn`: la continuación devuelve el contenido del asistente tal cual; sin la API real no se confirmó el formato.
- La telemetría vive en el mismo SQLite que el resto (efímero en el hosting actual: ver PUL-003).
