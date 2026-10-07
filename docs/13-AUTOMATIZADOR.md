# PULLEX Documentos — el automatizador

Estado: implementado y probado con el modelo **simulado** (pytest y navegador). **NOT VERIFIED** con la API
real de Anthropic: la calidad jurídica de los borradores, el cumplimiento del formato `<<<VERIFICAR>>>`, la
duración real de cada paso y el costo real por documento no se han medido con el modelo real.

Todo lo que produce el automatizador es un **borrador generado por IA para revisión humana**. No envía correos,
no radica, no paga ni contacta a nadie.

---

## Para quien lo usa (sin tecnicismos)

Entra a **Documentos** en la barra superior (o, en el Inicio, "Estoy trabajando en un asunto" → **Documentos y
flujos**). Hay cinco pestañas; la quinta, **Biblioteca**, está descrita en `docs/15-BIBLIOTECA.md`:

### 1. Escritos
1. Busca el documento ("tutela", "pagaré", "despido", "mandamiento de pago"…). Puedes filtrar por **área** y por
   **para quién** es (abogado, ciudadano, funcionario, estudiante). La búsqueda no distingue tildes.
2. Toca la tarjeta. Verás qué secciones tendrá el escrito, los requisitos de forma y las advertencias
   (términos, competencia, cuantía).
3. Llena el formulario. Los campos con `*` son obligatorios. Si no tienes un dato, déjalo en blanco: el
   borrador lo marcará como **[COMPLETAR: …]**.
4. **Generar borrador** (usa 1 consulta; si falla, no se descuenta).
5. Recibes el borrador, la lista **"Datos que debes completar o verificar"** y las advertencias. Botones:
   - **Copiar**, **Descargar Word** (.docx con márgenes, Arial 12, lugar y fecha, bloque de firma),
   - **Editar texto** (cambias el texto aquí mismo) y **Guardar**,
   - **Editar y regenerar** (vuelve al formulario con tus datos para generar otra versión; cuesta otra consulta).

Los **proyectos de autos y providencias** (área "Despachos judiciales y funcionarios") salen siempre con el rótulo
**BORRADOR — PROYECTO PARA REVISIÓN DEL FUNCIONARIO** y sin firma. Solo el funcionario decide y firma.

### 2. Flujos (recetas de varios pasos)
Llenas un formulario una sola vez y PULLEX ejecuta los pasos en orden; cada paso recibe lo que produjo el anterior.
Ves el avance paso a paso. Cada paso usa 1 consulta (el número aparece antes de empezar).

| Flujo | Pasos |
|---|---|
| De los hechos a la tutela | entrevista guiada (hechos ordenados y datos que faltan) → análisis de procedencia → borrador de tutela |
| Responder una demanda | resumen → excepciones posibles → borrador de contestación |
| Preparar una audiencia | cronología → teoría del caso → preguntas y lista de verificación |
| Cobrar una deuda | requisitos del título ejecutivo → liquidación orientativa → demanda ejecutiva |
| Despido | liquidación orientativa → reclamación al empleador → solicitud de conciliación |
| Revisar un contrato | riesgos → cláusulas a renegociar → versión mejorada |
| Recurrir una decisión administrativa | análisis de la decisión → recursos y términos → borrador del recurso |

La "entrevista guiada" no es un chat: las preguntas están en el formulario inicial y el primer paso ordena tus
respuestas y te dice qué datos faltan. Si un paso falla, ese paso no se cobra, el flujo se detiene y lo que ya se
produjo queda guardado.

### 3. Asistente (le das una tarea y él encadena los pasos)
1. Escribe la tarea completa ("Prepara una tutela contra mi EPS porque…").
2. **Proponer un plan** (1 consulta): PULLEX propone de 3 a 6 pasos.
3. Revisa el plan: cambia títulos o instrucciones, quita pasos o agrega hasta 6. **Nada se ejecuta todavía.**
4. **Confirmar y ejecutar**: cada paso usa 1 consulta. Un plan se ejecuta una sola vez (para repetir, pide otro plan).

### 4. Mis documentos
Todo lo generado (escritos, flujos, tareas del asistente y copias de trabajo de la Biblioteca) queda aquí: abrir, descargar en Word, editar, guardar
o borrar (con confirmación). Nadie más puede ver tus documentos.

---

## Para quien lo mantiene (técnico)

### Archivos
| Archivo | Qué contiene |
|---|---|
| `documentos.py` | Catálogo (`CATALOGO`, 203 tipos), `FLUJOS` (7), validación (`validar_campos`), mensajes de sistema (`SISTEMA_DOCUMENTO`, `SISTEMA_FLUJO`, `SISTEMA_PLAN`), lectura de la lista a verificar (`separar_respuesta`), exportación `a_docx`. No llama al modelo ni a la base. |
| `app.py` (sección "AUTOMATIZADOR") | Rutas, tablas `documentos_generados` y `asistente_tareas`, cobro/reintegro, SSE. |
| `static/documentos.js` | Vista "Documentos" (pestañas, buscador, formulario dinámico accesible, borrador, flujos, plan editable). |
| `static/index.html` | Botón de navegación, `<section id="v-documentos">`, `<script src="/static/documentos.js">` y bloque CSS `/* ---- Documentos ---- */` (solo variables semánticas con respaldo). |
| `demo/documentos_demo.json` | Textos de ejemplo (3 escritos completos, pasos de 2 flujos, plan) rotulados como demostración. |
| `tests/test_documentos.py`, `tests/e2e_documentos.py` | Pruebas. |

### Catálogo por área (203 tipos)
Constitucional 17 · Civil y Familia 55 (procesal civil, familia, infancia, contratos, poderes, memoriales y
solicitudes, medidas cautelares) · Comercial y Societario 13 · Laboral y Seguridad Social 16 · Penal y Procesal
Penal 16 (víctima, defensa, ejecución de penas) · Administrativo y Contratación Estatal 11 · Disciplinario 6 ·
Tributario 7 · Consumidor 8 · Propiedad Intelectual 7 · Policivo 6 · Notarial 9 · Insolvencia 6 · Despachos
judiciales y funcionarios 20 · Consultorio jurídico 6.

Cada tipo: `id, nombre, area, subarea, para_quien, descripcion, campos[{id, etiqueta, tipo
(texto|textarea|fecha|select|numero), requerido, ayuda, opciones, max}], estructura, notas_de_forma,
advertencias, borrador_funcionario`. Regla editorial: solo se nombran artículos de uso corriente y siempre con
"(verificar vigencia)"; si hay duda, se nombra la norma sin número. **Sin números de sentencias. Sin nombres de
universidades.** Los textos son originales (no se copió texto de los modelos del Drive). Las pruebas verifican
≥120 tipos, ids únicos, tipos de campo válidos, ausencia de números de sentencias y de universidades.

**Pendiente (revisión humana):** un abogado debe revisar notas y advertencias del catálogo; las referencias
normativas se marcaron para verificar, pero no se confirmaron una por una en SUIN-Juriscol (NOT VERIFIED).

### Rutas
| Método y ruta | Costo | Notas |
|---|---|---|
| `GET /api/documentos/catalogo?q=&area=&para=&detalle=0` | 0 | Resumen por defecto; `detalle=1` incluye campos. 400 si área o filtro no existen. |
| `GET /api/documentos/catalogo/{tipo}` | 0 | Tipo completo para el formulario. |
| `POST /api/documentos/generar` `{tipo, campos}` | 1 consulta | Valida contra el catálogo (400 con `errores` por campo, sin cobrar). Campos desconocidos se ignoran. Datos envueltos con `envolver_como_datos(..., encabezado=...)`. Usa `fuentes.buscar` (corpus FTS5) si existe. Reintegra y responde 503 si el modelo falla. Responde `texto`, `verificar`, `advertencias`, `fuentes`, `id`. |
| `GET /api/documentos/mis` | 0 | Últimos 100 del usuario. |
| `GET/PUT/DELETE /api/documentos/{id}` | 0 | Solo el dueño (404 para ajenos). PUT: `{texto ≤ 60.000, titulo}`. |
| `GET /api/documentos/{id}/docx` | 0 | Solo el dueño. Carta, márgenes 3 cm izquierda y 2,5 cm resto, Arial 12, justificado, encabezado de borrador, número de página; agrega lugar y fecha y bloque de firma si el texto no los trae. |
| `GET /api/flujos` | 0 | |
| `POST /api/flujos/ejecutar` `{flujo, campos}` | 1 por paso | SSE. Si no alcanzan las consultas para todos los pasos: 402 antes de empezar. |
| `POST /api/asistente/tarea` `{tarea}` | 1 | 15 a 4.000 caracteres. Plan JSON con 3 a 6 pasos (más de 6 se recorta; menos de 3 = 503 y reintegro). |
| `POST /api/asistente/ejecutar` `{id, pasos?}` | 1 por paso | 1 a 6 pasos (editados por el usuario). Una sola ejecución por plan (409). Plan ajeno: 404. |

Eventos SSE: `inicio {titulo,total,pasos}`, `restantes`, `paso {n,titulo}`, `texto {n,texto}`, `paso_fin {n}`,
`error {n,mensaje}`, `documento {id,titulo,verificar}`, `fin {completo,pasos_completados}`.

### Límites y costos
- **Tope por tarea del asistente:** 1 (plan) + 6 (pasos) = 7 consultas. Flujos: 3 pasos cada uno (máx. 6).
- `PULLEX_MAX_TOKENS_DOCUMENTO` (7.000) y `PULLEX_MAX_TOKENS_PASO` (4.000), más `PULLEX_MARGEN_THINKING` en modelos
  que no son Haiku. Cada paso recibe como máximo ~24.000 caracteres de resultados anteriores.
- Sin herramientas: ni búsqueda web ni acciones externas (`tools=[]`).
- Costo estimado (NOT VERIFIED, sin medición real): un documento con Sonnet 5.5 ronda varias veces una consulta
  de chat corta por la salida larga; ajusta `PULLEX_COSTO_CONSULTA_COP` con la consola de Anthropic.
- Si el usuario cierra la página en mitad de un paso, la consulta de ese paso ya se cobró (el modelo sí trabajó).

### Seguridad
- Todas las rutas exigen sesión (401). Documentos y planes filtrados por dueño en cada consulta (pruebas IDOR).
- Los campos del formulario, la tarea y los resultados previos van envueltos como **datos**; un intento de cerrar el
  delimitador se neutraliza. Nada del servidor se inserta como HTML salvo el borrador, que pasa por DOMPurify.
- La interfaz no tiene JavaScript en línea (CSP intacta; la prueba de navegador verifica 0 violaciones).

### Programar flujos periódicos (no implementado)
"Correr este flujo cada lunes" **no está implementado**: requiere un trabajador en segundo plano (cola o cron) que
ejecute sin un usuario conectado, y eso **no funciona en el plan gratis de Render** (los servicios gratuitos se
duermen y no admiten trabajadores en segundo plano). Si se implementa, debe respetar el mismo cobro por paso y el
tope de consultas del plan.

### Cómo probar
```bash
/home/claude/work/venv/bin/python -m pytest tests -q
PORT=8773 /home/claude/work/venv/bin/python demo/servidor_simulado.py    # otra terminal
BASE=http://127.0.0.1:8773 python3 tests/e2e_documentos.py
python demo/construir_demo.py                                             # regenera demo/pullex-demo.html
```
El servidor simulado responde con los textos de `demo/documentos_demo.json`. La demo de un solo archivo usa el
catálogo real y muestra un aviso al pulsar "Descargar Word". El limitador de intentos por IP (8 registros cada 5
minutos) puede hacer fallar varias pruebas de navegador seguidas contra el mismo servidor: reinícialo entre suites.
