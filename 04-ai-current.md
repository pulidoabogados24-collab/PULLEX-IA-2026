# 04 — Auditoría de IA

## Cómo funciona realmente

- **Proveedor y modelo:** Anthropic, `claude-haiku-4-5` por defecto (`PULLEX_MODELO`). El boletín puede usar otro (`PULLEX_MODELO_BOLETIN`). Acoplado a un solo proveedor, pero el modelo ya es configurable.
- **Llamadas:** una sola llamada `messages.stream` por consulta, `max_tokens=4000`, historial completo de la conversación en cada turno (sin recorte: una conversación larga encarece cada mensaje sin límite).
- **Prompt de sistema:** fijo y cacheado (`cache_control: ephemeral`), con modo dual, regla de cero alucinaciones, jerarquía de fuentes y bloque final de "Confianza / Fuentes".
- **Bloque dinámico:** agentes por palabra clave (6 áreas), modo elegido, nombre del usuario, áreas de interés, "memoria" escrita por el usuario (≤ 1.500 caracteres) y, si existiera, el corpus recuperado.
- **Herramientas:** solo `web_search` del servidor de Anthropic (máx. 5 usos). No hay herramientas propias ni ejecución de código.
- **Adjuntos:** PDF e imágenes se envían como bloques `document`/`image` en el turno del usuario; no se guardan.

## Hallazgos

| ID | Severidad | Hallazgo | Estado |
|---|---|---|---|
| AI-1 | **CRITICAL** | Fuga de datos entre usuarios a través del modelo: `POST /api/chat` aceptaba cualquier `conversacion`; el servidor cargaba el historial de la víctima y se lo enviaba al modelo en nombre del atacante ("repite lo anterior"). Además dejaba el mensaje del atacante dentro de la conversación ajena. | **Corregido** (autorización por recurso). Prueba: `AUTHZ_002`. |
| AI-2 | HIGH | La "Confianza: Alta/Media/Baja" y las "Fuentes" las declara el propio modelo; nada las verifica. Un usuario puede leerlas como verificación. | Mitigado (Fase 1b): cada respuesta que trae ese bloque muestra debajo un rótulo fijo que aclara que es una autoevaluación de la IA, no verificada por PULLEX. La verificación real sigue abierta — Fase 3/4 (Citation Guard). |
| AI-3 | HIGH | Sin RAG en producción: todo depende de la memoria del modelo + búsqueda web genérica. Las citas no se contrastan contra una base propia. | Abierto — Fase 4. |
| AI-4 | MEDIUM | El boletín diario se publica a todos los usuarios tal como lo genera el modelo, con la sección "Jurisprudencia reciente", sin verificación. Riesgo de sentencias inexistentes presentadas como noticia. | Mitigado (Fase 1b): el aviso bajo el boletín ahora dice que lo genera la IA sin revisión humana y que una sentencia o norma citada puede estar mal. **HUMAN REVIEW REQUIRED:** decidir si alguien lo revisa antes de publicarse. |
| AI-5 | MEDIUM | Inyección indirecta: el texto recuperado del corpus se pegaba en el prompt de sistema sin delimitar. | **Corregido** para el corpus: se envuelve en `<documentos_recuperados>` con instrucción explícita de tratarlo como datos y se neutraliza el cierre del delimitador. Prueba: `AI_002`. PDFs adjuntos y resultados web siguen sin capa propia (van en el turno del usuario / los gestiona Anthropic). |
| AI-6 | LOW | El nombre del usuario y su "memoria" se insertan en el prompt de sistema. Solo permiten auto-inyección (el usuario manipula su propia sesión), no afectan a otros. | Aceptado; mover a un bloque de "datos del usuario" en Fase 3. |
| AI-7 | MEDIUM | Costo sin techo por consulta: historial completo sin recorte + adjuntos de hasta ~7 MB cuentan como 1 consulta. | Parcial: validación de tamaño/cantidad/tipo de adjuntos (Fase 1). Recorte de historial y registro de tokens por consulta pendientes. |
| AI-8 | MEDIUM | No se registra modelo, tokens, latencia, fuentes ni búsquedas por respuesta: imposible auditar una respuesta después. | Abierto — Fase 3 (tabla `respuestas_meta`). |
| AI-9 | LOW | Los errores del proveedor se mostraban al usuario con el texto técnico de la excepción. | **Corregido**: mensaje genérico + código de error; detalle solo en el log. |
| AI-10 | INFO | No existe batería de evaluación ("preguntas doradas") ni benchmark jurídico. | Abierto — Fase 13; ver 10-migration-plan. |

## Lo que NO se verificó en esta iteración

- **NOT VERIFIED:** comportamiento real del modelo ante inyección directa, extracción del prompt de sistema, premisas falsas, sentencias inexistentes o normas derogadas. Las pruebas automáticas usan un doble del modelo (no llaman a la API real, por costo y porque no hay clave disponible en este entorno). Requiere la batería AI-001…AI-004 contra el modelo real con presupuesto aprobado.
- **NOT VERIFIED:** política de retención y uso de datos del proveedor de IA para esta cuenta. **HUMAN REVIEW REQUIRED** antes de admitir expedientes con datos personales o reservados.
- **NOT VERIFIED:** que el nombre de herramienta `web_search_20250305` siga siendo el vigente en la API; el boletín y el chat lo usan.
