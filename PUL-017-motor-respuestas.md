# PUL-017. Motor de respuestas del chat

Rama `pul/017-motor-respuestas` (desde `pul/integracion` en `00cbb98`). Responsable: Claude. Revisor: Codex.
Especificación del dueño: `docs/coordinacion/ESPECIFICACION-MOTOR-RESPUESTAS.md`. Auditoría con evidencia de código:
`docs/audit/AI_RESPONSE_QUALITY_AUDIT.md`.

## Estado

**EN REVISIÓN, con una salvedad grande**: todo se probó con un modelo SIMULADO. No hay `ANTHROPIC_API_KEY` en este
entorno. La tubería (qué se manda, qué se hace con lo que vuelve, qué ve la persona) está verificada; la calidad de las
respuestas del modelo real y su calidad jurídica **no se midieron**.

## Qué se hizo (y está probado)

1. **Causa técnica del corte.** El motivo de parada del modelo se descartaba y el tope de salida era fijo en 8000 con el
   razonamiento incluido. Ahora se lee el motivo (`end_turn`, `max_tokens`, `pause_turn`…), el tope depende de la consulta
   (de 2700 a 15000 tokens con Sonnet; máximo `PULLEX_MAX_TOKENS`, por defecto 16000) y, si se corta, el servidor pide
   la continuación hasta 3 veces y empalma sin duplicar. Si sigue cortada **nunca se presenta como completa**.
2. **`motor_respuesta.py`** (funciones puras): HERMES (intención, partes, entregable, profundidad, riesgo, seguimiento y
   «candado de intención»), presupuesto de tokens, ARGOS (cobertura determinista), MINERVA (una sola reparación), recorte
   de contexto, latido, carga de la guía de calidad.
3. **`/api/chat`**: contrato inyectado en el bloque dinámico del `system`; evento SSE `incompleta`; latido `: latido` cada
   15 s; límite de inactividad de 150 s; lo generado se guarda como incompleto si se cierra la conexión; cabeceras
   anti-buffering; recuperación y agentes usan la pregunta anterior en los seguimientos.
4. **Botón «Continuar»** (`POST /api/chat` con `{continuar:true}`, no gasta consulta) y **aviso de respuesta incompleta**,
   también al reabrir una conversación. Sin JavaScript en línea (CSP estricta intacta).
5. **Telemetría local** (`telemetria_respuestas.py`, tabla `calidad_respuestas`): solo etiquetas y conteos; **no** guarda el
   texto de la pregunta ni de la respuesta ni el correo (el usuario es un código HMAC irreversible). Se borra con la
   conversación. **Valoración** 👍/👎 con motivos de lista cerrada (incompleta, no respondió lo pedido, error jurídico, muy
   larga, otro) en `POST /api/feedback`; tablero para el administrador en `GET /api/admin/calidad`.
6. **Otros generadores**: JSON del Laboratorio/Taller/Documentos (reintento con más espacio), documentos, pasos de flujos,
   escrito modelo del Taller (no se guarda cortado), boletín y perfiles. Detalle en la auditoría, sección 6.

## Evidencia (comandos y resultados reales)

```
python -m pytest -q                                  → 766 passed   (620 al empezar)
python -m pytest -q tests/test_motor_respuesta.py    → 110 passed   (24 casos dorados de intención + dorados de ARGOS/MINERVA)
python -m pytest -q tests/test_chat_motor.py         → 24 passed
python -m pytest -q tests/test_generadores_truncados.py → 12 passed
rm -f pullex.db && PORT=8774 python demo/servidor_simulado.py &
BASE=http://127.0.0.1:8774 python tests/e2e_respuestas.py → 31 comprobaciones OK, TODO OK
```

El e2e (Playwright, 1280 px y 390 px) comprueba: respuesta normal sin aviso; 👍/👎 y los cinco motivos llegan al servidor;
una respuesta cortada una vez se completa sola sin duplicar texto; una cortada siempre queda marcada incompleta y NO se
presenta como completa; «Continuar» la completa sin gastar consulta; al reabrir la conversación el botón sigue ahí; sin
desbordamiento horizontal; cero violaciones de CSP; cero errores de consola. Para simular el corte, el simulador
(`demo/servidor_simulado.py`) reconoce las marcas `[[CORTE]]` y `[[CORTE-SIEMPRE]]` dentro del mensaje.

## NO verificado

- Todo lo que depende del modelo real: cuánto razonamiento consume Sonnet 5.5 y si los presupuestos nuevos alcanzan; que
  el contrato mejore la respuesta; que el modelo repita las últimas palabras al continuar como se le pide (el empalme
  funciona igual si no lo hace, pero con un modelo real puede producir repeticiones parciales que no se probaron).
- Comportamiento real de `stop_reason`, `pause_turn` con búsqueda web y de la ruta OpenAI (`response.incomplete`).
- Que el hosting (Render) tolere el stream y que 15 s de latido basten.
- ARGOS es léxico: sus falsos positivos y negativos con respuestas reales no se midieron.
- La calidad jurídica de cualquier respuesta. Nada de esta tarea la evalúa; sigue pendiente PUL-008 (modelo real y
  benchmark jurídico).
- Los datos de telemetría viven en el mismo SQLite efímero del hosting actual (PUL-003).

## Limitaciones conocidas

- Los adjuntos no se guardan entre turnos (no se cambió): en un seguimiento el modelo ya no ve el archivo.
- MINERVA no corrige antes de mostrar (el texto ya se transmitió): agrega lo que falta al final.
- La guía de calidad `prompts/calidad_respuesta.md` es de PUL-018: aquí se carga si existe y, si no, se usa una constante
  de respaldo. Al fusionar ambas ramas, revisar que no se duplique la guía.

## Variables de entorno nuevas (todas opcionales)

`PULLEX_MAX_TOKENS` (16000), `PULLEX_MAX_CONTINUACIONES` (3), `PULLEX_MINERVA` (1), `PULLEX_LATIDO_S` (15),
`PULLEX_INACTIVIDAD_S` (150), `PULLEX_CONTEXTO_MAX_CARACTERES` (150000), `PULLEX_PROMPT_CALIDAD` (ruta),
`PULLEX_MAX_TOKENS_JSON_TOPE` (16000), `PULLEX_MAX_TOKENS_BOLETIN` (4000), `PULLEX_TELEMETRIA_DIAS` (180).

## Próximo paso

1. Con `ANTHROPIC_API_KEY`: ejecutar 20 a 30 consultas reales (incluidas las de varias partes y las muy largas), mirar
   `GET /api/admin/calidad` (tasa de truncadas, de pregunta omitida, latencia) y ajustar los presupuestos de
   `presupuesto_tokens` con datos.
2. Revisión humana de ARGOS contra respuestas reales.
3. Fusionar con PUL-018 y decidir la redacción final de la guía de calidad.
4. Confirmar la retención de la telemetría: hoy 180 días (`PULLEX_TELEMETRIA_DIAS`), purgada al iniciar la aplicación; no hay tarea programada.
