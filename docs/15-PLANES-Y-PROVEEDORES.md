# 15 — Planes (acceso por función) y proveedores de IA

Dos cosas independientes viven aquí: **qué puede usar cada plan** y **qué motor de IA responde**.

## 1. Acceso por plan

Decisión del dueño (1-oct-2026):

| Plan | Precio/mes (COP) | Consultas/mes | Consultar (chat) | Academia: Modular Lab, Mi mapa, Taller de escritos | Automatizador: Documentos, Flujos, Asistente |
|---|---:|---:|:---:|:---:|:---:|
| Prueba gratis | $0 | 10 (no se renuevan) | Sí | Sí | Sí |
| Básico | $30.000 | 200 | Sí | No | No |
| Pro | $45.000 | 500 | Sí | Sí | No |
| Premium | $60.000 | 1.000 | Sí | Sí | Sí |
| Administrador | — | — | Sí | Sí | Sí |

- **Prueba** tiene acceso a todo para que el usuario conozca el producto; lo limita su cupo de 10 consultas.
  Se cambia en **una sola constante** de `app.py`: `FUNCIONES_PLAN_PRUEBA` (por ejemplo `("chat",)` para
  dejar la prueba solo con el chat).
- Precios y cupos siguen en `PLANES`; las funciones de cada plan, en `PLAN_FUNCIONES`.

### Cómo se aplica en el servidor

- `PLAN_FUNCIONES` (plan → funciones) y `PREFIJOS_FUNCION` (prefijo de ruta → función):

  | Prefijo | Función |
  |---|---|
  | `/api/modular`, `/api/academia`, `/api/taller` | `academia` |
  | `/api/documentos`, `/api/flujos`, `/api/asistente` | `automatizador` |

- El middleware `control_plan` aplica `exigir_funcion(u, funcion)` a **toda** ruta bajo esos prefijos
  (la ruta exacta y sus subrutas). Una ruta nueva bajo `/api/taller/…` queda protegida sin tocar nada.
  Para proteger otro prefijo se agrega una línea a `PREFIJOS_FUNCION`.
- Sin sesión válida la ruta responde `401` como siempre. Con sesión y plan insuficiente:

  ```json
  HTTP 403
  {"detail": "Modular Lab y Mi mapa está disponible desde el plan Pro. Mejora tu plan para usarlo.",
   "codigo": "plan_insuficiente", "funcion": "academia", "plan_requerido": "pro"}
  ```

  `plan_requerido` es el plan pago más barato que incluye la función. El 403 sale antes de la lógica de
  la ruta: no gasta consultas ni llama al modelo, y lleva las mismas cabeceras de seguridad (CSP incluida).
- `GET /api/estado` devuelve `funciones` (las del usuario), `plan_funciones` (la tabla completa),
  `plan_requerido` y `contacto_planes`. `perfil.funciones` también viene en el ingreso y el registro.
- Cambiar el plan desde `/admin` cambia el acceso en la siguiente petición (no hay caché).
- El chat (`/api/chat`) está en todos los planes, incluidas sus formas «Enséñame», «Resuélvelo conmigo»,
  «Examíname» y el formulario «Redactar un escrito» de Herramientas.

### Cómo se ve (static/planes.js, static/planes.css)

- **Navegación:** candado sutil en las secciones que el plan no incluye.
- **Pantalla de mejora:** al entrar a una sección bloqueada se muestra qué incluye, los planes que la
  traen con su precio en COP (leído de `/api/estado`) y el botón «Mejorar a Pro/Premium».
- **Flujo de pago (el que ya existía):** pagar por Nequi y escribirle al administrador, que asigna el plan
  en `/admin`. El botón abre un correo ya escrito (plan, precio y correo de la cuenta) dirigido a
  `PULLEX_CONTACTO_PLANES` (por defecto, el correo de soporte que ya mostraba Ajustes). No hay pasarela de
  pagos: sigue siendo activación manual.
- **Ajustes → Planes:** tabla comparativa con «Tu plan» y botones «Mejorar» solo hacia planes superiores.
- **Inicio:** las tarjetas que llevan a una función bloqueada lo indican («Plan Pro» / «Plan Premium») y
  el tablero de estudio no consulta rutas bloqueadas.
- Si el administrador baja el plan con la app abierta, el 403 del servidor actualiza los candados y lleva a
  la pantalla de mejora.

### Demo

`demo/pullex-demo.html` entra como **Premium**. Selector oculto en la URL para mostrar los bloqueos:
`pullex-demo.html?plan=basico`, `?plan=pro`, `?plan=premium` (también `?plan=prueba`). Regenerar con
`python demo/construir_demo.py`.

## 2. Proveedores de IA (`proveedores.py`)

Interfaz común con dos operaciones: `stream(...)` (chat y pasos de los flujos; emite eventos de texto y de
búsqueda, y acumula las fuentes web) y `crear_texto(...)` (llamadas que esperan un JSON o un documento).
La usan el chat, `llamar_json` (Modular Lab y plan del asistente), la generación de documentos y los
pasos de flujos y asistente. El evento SSE `fuentes` no cambia.

| Proveedor | Implementación | Modelo por defecto | Clave |
|---|---|---|---|
| `anthropic` (por defecto) | Messages API, SDK `anthropic` | `claude-sonnet-5-5` (`PULLEX_MODELO`) | `ANTHROPIC_API_KEY` |
| `openai` | Responses API con streaming, SDK oficial `openai==3.22.1` | `gpt-6.1-sol` (`PULLEX_OPENAI_MODELO`) | `OPENAI_API_KEY` |

### Cómo cambiar el proveedor

Variables de entorno (en `.env` o en Render) y reiniciar:

```bash
PULLEX_PROVEEDOR=anthropic      # anthropic | openai  (principal)
PULLEX_RESPALDO=openai          # opcional: se usa si el principal está saturado o caído
OPENAI_API_KEY=sk-...           # necesaria si openai es principal o respaldo
PULLEX_OPENAI_MODELO=gpt-6.1-sol
PULLEX_OPENAI_ESFUERZO=medium   # reasoning.effort; vacío = no enviarlo
```

- Un valor desconocido en `PULLEX_PROVEEDOR` vuelve a `anthropic`. Un respaldo igual al principal se ignora.
- Si el proveedor **principal** no tiene clave, las rutas de IA responden 503 y `/api/estado` da `"api": false`.
- El panel `/admin` muestra el proveedor y el modelo activos y el respaldo (nunca las claves); `/salud`
  también informa `proveedor` y `modelo`.

### Respaldo automático

Con `PULLEX_RESPALDO` definido, si el principal falla **por saturación o error de servidor** (HTTP 408,
409, 429, 5xx, 529, errores de conexión o de tiempo de espera) y todavía no había enviado texto, se intenta
**una vez** con el proveedor de respaldo. En el log queda una línea como:

```
WARNING pullex.proveedores respaldo de IA: anthropic falló (tipo=OverloadedError estado=529); se intenta una vez con openai
```

Sin correo, nombre ni contenido de la consulta. No hay respaldo cuando:
- el error es del pedido (400, clave inválida, contenido rechazado): cambiar de proveedor no lo arregla;
- el principal ya había empezado a responder (no se mezclan dos respuestas);
- el respaldo no tiene clave.

En esos casos el chat entra en el modo degradado de siempre (mensaje con fuentes oficiales y reintegro de la
consulta). Una consulta atendida por el respaldo se cobra una sola vez.

### Qué se envía a OpenAI y cómo

Documentación oficial consultada el 1-oct-2026:
- Streaming de la Responses API (eventos `response.output_text.delta`):
  https://developers.openai.com/api/docs/guides/streaming-responses
- Modelos vigentes (`gpt-6-astra`, `gpt-6.1-sol`, `gpt-6-luna`): https://developers.openai.com/api/docs/models
- Búsqueda web con filtro de dominios: https://developers.openai.com/api/docs/guides/tools-web-search
- Referencia de la Responses API: https://developers.openai.com/api/reference/resources/responses

Detalles:
- `client.responses.create(model, instructions, input, max_output_tokens, stream=True, store=False)`.
  `store=False` para que las conversaciones no queden guardadas en OpenAI (datos personales, Ley 1581 de 2012).
- El mensaje de sistema viaja en `instructions`; los adjuntos se traducen a `input_image` e `input_file`.
- **Búsqueda web restringida:** OpenAI sí ofrece el equivalente. La herramienta `web_search` acepta
  `filters.allowed_domains` (dominios sin `https://`, subdominios incluidos, hasta 100), así que se envía la
  misma lista de dominios oficiales que usa Anthropic (`fuentes.dominios_web()`), con `max_tool_calls` igual a
  `PULLEX_WEB_MAX_USOS` e `include=["web_search_call.action.sources"]` para listar lo consultado. Las citas
  (`url_citation`) y las fuentes consultadas llegan al mismo bloque «Fuentes consultadas».
- El boletín diario sigue usando Anthropic (necesita `ANTHROPIC_API_KEY`).

### Costos aproximados (verificar antes de decidir)

Precios leídos el 1-oct-2026 en las páginas oficiales; cambian sin aviso.

| Modelo | Entrada (USD/M tokens) | Salida (USD/M tokens) | Búsqueda web |
|---|---:|---:|---|
| Claude Sonnet 5.5 | 2 | 10 | 10 USD por 1.000 búsquedas |
| Claude Haiku 4.5 | 1 | 5 | 10 USD por 1.000 búsquedas |
| GPT-6 Astra | 10 | 50 | 10 USD por 1.000 llamadas + tokens del contenido |
| GPT-6.1 Sol | 2 | 10 | 10 USD por 1.000 llamadas + tokens del contenido |
| GPT-6 Luna | 0,10 | 0,50 | 10 USD por 1.000 llamadas + tokens del contenido |

Fuentes: https://platform.claude.com/docs/en/about-claude/pricing y
https://developers.openai.com/api/docs/pricing

`gpt-6.1-sol` es el modelo por defecto porque cuesta lo mismo que Sonnet 5.5 por token: el respaldo no cambia
el costo estimado por consulta (`PULLEX_COSTO_CONSULTA_COP`). El costo real por consulta con OpenAI no está
medido: **verificar** en el panel de uso de OpenAI con tráfico real.

## 3. Pruebas

- `tests/test_planes.py`: matriz plan × ruta, las 23 rutas protegidas (leídas de `app.routes`) contra un plan sin
  acceso, forma del 403, prefijo `/api/taller`, cambio de plan desde admin y la constante de la prueba.
- `tests/test_proveedores.py`: selección de proveedor, texto por SSE con OpenAI, búsqueda web con los mismos
  dominios, adjuntos, `llamar_json`, respaldo ante 529/5xx, sin respaldo ante 400 o sin clave, sin mezcla de
  respuestas y panel de administración. Usa los dobles `FakeAnthropic` y `FakeOpenAI` de `tests/conftest.py`.
- `tests/e2e_planes.py`: candados, pantalla de mejora y tabla en 1280 y 390 px, panel de administración y la
  demo con `?plan=`; exige cero violaciones de CSP, cero errores de consola y que la interfaz no pida rutas
  fuera del plan.

## 4. NOT VERIFIED

- **OpenAI contra la API real:** no hay `OPENAI_API_KEY` en este entorno. Todo lo de OpenAI (streaming,
  `instructions`, adjuntos, `web_search` con `filters.allowed_domains`, `max_tool_calls`, `store=False`,
  `reasoning.effort` en `gpt-6.1-sol`, forma exacta de los eventos de error) está construido según la
  documentación y los tipos del SDK 3.22.1, y probado solo con un doble.
- **Respaldo con fallas reales:** probado con errores simulados (529, 500, 503, 400), no con una caída real.
- **Calidad jurídica de las respuestas con OpenAI:** no evaluada (el benchmark de `evaluacion/` solo corre
  con Anthropic o simulado).
- **Costo por consulta con OpenAI:** estimado por precio de lista, no medido.
- **Correo de «Mejorar»:** se verificó el enlace `mailto:` que arma la app, no la entrega del correo ni la
  activación manual posterior.
