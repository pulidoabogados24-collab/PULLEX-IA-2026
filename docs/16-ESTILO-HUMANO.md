# Estilo humano: que PULLEX escriba como un estudiante de Derecho y como un abogado colombiano

Estado: implementado y probado con el modelo **simulado** (pytest y navegador). **NOT VERIFIED** con la API real:
no se ha medido cuánto cambian las respuestas reales de Claude con las nuevas guías de voz, ni cuántos rasgos de
IA sobreviven en la práctica.

Archivos: `estilo_redaccion.py` (guías, detector y `pulir`), `SYSTEM_PROMPT` en `app.py`, `SISTEMA_BASE` y
`voz_documento` en `documentos.py`, `evaluacion/estilo.jsonl` (+ `evaluacion/construir_estilo.py`),
`tests/test_estilo.py`.

---

## 1. Investigación

Páginas abiertas y leídas para este trabajo (no se copió texto: se resumen ideas y los ejemplos de este documento
son propios).

### 1.1 Lenguaje claro en el Estado y en la Rama Judicial de Colombia

| Fuente (abierta) | Lo que aporta |
|---|---|
| Guía de lenguaje claro para servidores públicos de Colombia, DNP, 2015 (copia publicada en <https://www.portaltributariodecolombia.com/wp-content/uploads/2015/07/portaltributariodecolombia_guia-de-lenguaje-claro-para-servidores-publicos.pdf>) | Un texto es claro si el lector puede encontrar, entender y usar lo que necesita. Oraciones cortas, orden sujeto–verbo–complemento, voz activa, verbos en lugar de sustantivos ("decidir", no "tomar la decisión"), eliminar redundancias, encabezados informativos, viñetas solo si el orden no importa y numeración si importa. |
| Guía de lenguaje claro para textos e información legislativa, Senado de la República, 2020: <https://www.senado.gov.co/images/Unidad_de_Atenci%C3%B3n_Ciudadana/guia_lenguaje_claro_1.pdf> | Tope orientativo de 20 palabras por oración y 9 líneas por párrafo, una idea por párrafo, cambiar "de conformidad con" por "según", "a fin de" por "para", "debido a que" por "porque"; definir tecnicismos y siglas; evitar arcaísmos y latinismos innecesarios. |
| Guía de Lenguaje Claro 2024, Colombia Compra Eficiente: <https://colombiacompra.gov.co/wp-content/uploads/2025/05/cce-rec-gi-01_guia_lenguaje_claro_v2_31-12-2024-1.pdf> | Misma línea (20 palabras, voz activa), con ejemplos de reordenar la oración para que el sujeto vaya primero y una tabla de sustituciones ("problemática" → "problema", "habida cuenta de que" → "como"). Negrita para encabezados e información clave, no para todo. |
| Consejo Superior de la Judicatura, noticia del 10 de noviembre de 2025 sobre estandarización de providencias: <https://www.ramajudicial.gov.co/web/consejo-superior-de-la-judicatura/-/lenguaje-claro-y-decisiones-comprensibles-consejo-superior-de-la-judicatura-lidera-estandarizaci%C3%B3n-de-providencias-judiciales> | La Rama trabaja en modelos de estructura de providencias "más comprensibles y accesibles a la ciudadanía" sin uniformar el razonamiento; meta de modelos por jurisdicción en 2026. |
| Instituto Colombiano de Derecho Procesal, "El lenguaje claro de las providencias judiciales": <https://icdp.org.co/el-lenguaje-claro-de-las-providencias-judiciales/> | Problemas típicos del escrito judicial colombiano: arcaísmos ("trabarse la litis", "opugnador"), latinismos innecesarios, frases densas; el ciudadano no sabe si ganó o perdió. Menciona la Sentencia T-607 de 2019 como paso hacia el lenguaje claro y el art. 285 del CGP (aclaración) (ambas referencias tomadas del artículo, pendientes de verificación en la fuente oficial). |
| RAE, Crónica de la lengua española 2021, "Lenguaje jurídico claro: nuevos desafíos para las academias": <https://www.rae.es/recursos-academicos-de-apoyo-para-el-lenguaje-claro/cronica-de-la-lengua-espanola-2021/lenguaje> | Rasgos del lenguaje jurídico oscuro: gerundios en cadena, pasivas, oraciones de un párrafo entero, léxico arcaico tenido por "prestigioso", redundancias ("dar cumplimiento" por "cumplir"). Propone sintaxis sucinta y léxico comprensible sin perder precisión. |

### 1.2 Cómo se contestan y califican los casos en un examen de Derecho

| Fuente (abierta) | Lo que aporta |
|---|---|
| ICFES, Guía de orientación Saber Pro, módulo Comunicación Jurídica 2025-2: <https://www.icfes.gov.co/wp-content/uploads/2025/09/comunicacion-juridica-saber-pro-2025-2.pdf> | Lo que el Estado evalúa en el egresado de Derecho: comunicar soluciones jurídicas con estructuras argumentativas coherentes; manejar el lenguaje jurídico y los métodos de interpretación (40 %); evaluar textos con los principios de la argumentación jurídica, la pertinencia de las fuentes y las características de cada género (sentencia, memorial, concepto, ley) (60 %). |
| Ediciones Rodio, "Casos prácticos: estructura y pasos para resolverlos": <https://www.edicionesrodio.com/blog/consejos-para-oposiciones/casos-practicos-estructura-y-pasos-para-resolverlos/> | Estructura esperada: leer y subrayar lo que se pregunta, identificar el problema, invocar la norma, desarrollar la solución aplicada a los hechos y cerrar con una conclusión breve. Errores que se castigan: desorden, no contestar lo preguntado, no fundamentar en norma, extenderse sin foco y dejar la respuesta sin conclusión. Es una fuente española (oposiciones), útil por el método. |

Para Colombia se suma la rúbrica que PULLEX ya usa en Laboratorio de casos (problema 20, normas 20, argumentación 20,
aplicación 20, conclusión 10, claridad 10). **NOT VERIFIED**: no se consultaron rúbricas internas de facultades de
Derecho colombianas (no son públicas o no se encontraron); la voz de estudiante se apoya en el marco del ICFES,
en el método general de casos y en la rúbrica propia.

### 1.3 Cómo se cita en Colombia

| Fuente (abierta) | Lo que aporta |
|---|---|
| Relatoría de la Corte Constitucional, Sentencia T-760/08: <https://www.corteconstitucional.gov.co/relatoria/2008/t-760-08.htm> | La propia Corte identifica sus fallos como "Sentencia T-760/08", con fecha (31 de julio de 2008), magistrado ponente y sala. En la prosa forense colombiana se escribe "Corte Constitucional, Sentencia T-760 de 2008" la primera vez y "la T-760 de 2008" después. |

Convenciones adoptadas (uso forense corriente; no hay una norma oficial única de citación): "artículo 86 de la
Constitución Política" completo la primera vez y "art. 86 C.P." después; "Ley 1755 de 2015"; "Decreto 2591 de
1991"; "Corte Suprema de Justicia, Sala de Casación Laboral"; "Consejo de Estado, Sección Tercera". Lo que no se
puede verificar no se cita con número: se describe la regla y se marca "(pendiente de verificación)", como ya
exigía el `SYSTEM_PROMPT`.

### 1.4 Rasgos que delatan un texto generado por IA en español

| Fuente (abierta) | Lo que aporta |
|---|---|
| <https://traductorinterprete.es/detectar-textos-escritos-con-ia/> | Conectores y fórmulas repetidas ("en conclusión", "es importante destacar", "por otro lado", "en resumen"), viñetas en lugar de párrafos, respuestas más completas de lo pedido, negritas como organizador, español "neutro" sin rasgos regionales y calcos del inglés. |
| <https://www.culturamas.es/2026/03/18/como-saber-si-un-texto-ha-sido-escrito-por-una-ia-indicios-y-ejemplos-reales/> | Arranques "Es importante señalar", "Cabe destacar"; clichés ("En el mundo actual", "desempeña un papel clave", "enfoque integral"); palabras parásitas ("profundizar", "innovador", "sin precedentes"); estructuras rígidas, monotonía en la longitud de las frases y abuso de guiones y dos puntos. |
| <https://www.moncloa.com/2025/12/12/senales-texto-creado-inteligencia-artificial-3347072/> | Frases que "marchan al mismo paso", plantillas estructurales, formalidad sin matices, emociones con frases estándar y ausencia de detalles concretos del caso. |

Rasgos añadidos por observación propia y por la regla ortotipográfica del español: la raya de inciso va pegada
al texto (—así—); el guion largo con espacios usado como pausa es un hábito del inglés y de la IA. Los títulos
con Mayúscula En Cada Palabra son norma del inglés, no del español. También son típicos: el paralelismo "no
solo…, sino también…" de adorno, las tríadas por costumbre, las preguntas retóricas que el texto se responde
("¿La clave? …"), el entusiasmo artificial, los emojis y los cierres serviles ("Espero que esta información te sea
útil", "Si tienes más preguntas, no dudes en escribirme").

---

## 2. Qué se construyó

### 2.1 Voces (`estilo_redaccion.py`)
- **`VOZ_ESTUDIANTE`** (examen, parcial, modular): prosa continua; método problema → norma → aplicación de cada
  requisito a los hechos → contraargumento → conclusión que responde lo preguntado; conectores con función;
  primera persona moderada solo al tomar posición; citas a la colombiana; lista de errores que un docente
  castiga.
- **`VOZ_ABOGADO`** (concepto, memorial, demanda, recurso, correo): sobrio, voz activa, una idea por oración,
  numerales donde el género los pide, fórmulas forenses con mesura ("respetuosamente", "en mérito de lo
  expuesto" en su sitio), latinismo técnico solo si no tiene equivalente cómodo, negrita solo en rótulos, sin
  cierres de cortesía.
- **`VOZ_CIUDADANO`**: respuesta primero ("Sí", "No", "Depende de…"), frases de menos de 25 palabras, cada
  tecnicismo explicado en la misma oración, cálido sin exclamaciones, pasos numerados con entidad y plazo.
- **`GUIA_ESCRITURA`**: reglas comunes contra los rasgos de máquina. **`CONECTORES`**: por función lógica.

### 2.2 Detector (`rasgos_ia`, `revisar`)
Devuelve cada rasgo con nombre legible, explicación, sugerencia, número de apariciones, peso, ejemplos y
posiciones. No analiza citas textuales («…», "…"), código, enlaces ni marcas [F#]. `revisar()` suma los pesos
(cada rasgo aporta como máximo 2) y marca `parece_ia` desde 2 puntos.

| Peso | Rasgos |
|---|---|
| 2 | apertura de asistente ("¡Excelente pregunta!"), cierre servil, emojis, "Como inteligencia artificial…" |
| 1 | "Es importante destacar", "Cabe destacar/resaltar", "Vale la pena señalar", "Juega un papel fundamental", "Es fundamental que…", "En el mundo actual", anuncios ("A continuación te explico"), "Profundicemos/Exploremos", "no solo…, sino también…", preguntas retóricas, viñetas cortas en lugar de prosa, títulos con Mayúscula En Cada Palabra, muchos títulos en un texto corto, cierre "En conclusión" que repite |
| 0,5 a 1 | rayas con espacios usadas como pausa, negritas dentro de párrafos (desde 3), tríadas repetidas (desde 3), exclamaciones (desde 2) |
| 0,5 | "En el ámbito de" (no "ámbito de aplicación"), "un amplio abanico", adjetivos de énfasis ("crucial", "fascinante"), "enfoque integral", "sin lugar a dudas", "En ese orden de ideas" (muletilla forense gastada, también humana), "Quedo atento a cualquier inquietud" |

Falsos positivos evitados a propósito: "derechos fundamentales", "reparación integral", "Sistema de Seguridad
Social Integral", "ámbito de aplicación", títulos con nombres propios ("Código General del Proceso"), términos
definidos en mayúsculas y negrita ("**EL ARRENDADOR**"), rótulos al inicio de línea ("**Hechos.**"), la raya
pegada al inciso y las casillas ☐ de los formularios.

Es una **ayuda de estilo, no una prueba de autoría**: una persona puede escribir "Cabe destacar" y una IA bien
guiada puede no dejar rastros. La interfaz lo dice debajo de cada revisión.

### 2.3 `pulir(texto)`: correcciones deterministas y seguras
Quita emojis (respeta ✓ ✗ ☐ ☑), aperturas serviles al comienzo, cierres serviles al final (aunque después venga
la advertencia legal obligatoria), "Es importante destacar que / Cabe destacar que / Vale la pena señalar que"
al comienzo de una oración (no si la oración coordina "que… y que…", porque se rompería la gramática), negritas
dentro de los párrafos cuando hay cuatro o más, y rayas con espacios usadas como pausa (pareja → comas; sola →
coma) solo en líneas de prosa.

Nunca toca: bloques y fragmentos de código, tablas, títulos, citas textuales, enlaces y URLs, [F#],
[COMPLETAR: …], "(pendiente de verificación)", "(verificar vigencia)", el rótulo de borrador del funcionario ni
nada de lo que sigue a `<<<VERIFICAR>>>`. No quita "En conclusión" (en un examen es legítimo), ni "Quedo atento"
(fórmula humana frecuente), ni los saludos. Es idempotente y se probó con 600 combinaciones aleatorias en pytest
(y 20.000 en una corrida manual con cinco semillas).

### 2.4 Integración
- **Chat.** La sección de estilo del `SYSTEM_PROMPT` se reescribió con `GUIA_ESCRITURA` y las tres voces ("CÓMO
  SUENAS"); se conservaron sin cambios las secciones "CUANDO EL TEMA ES JURÍDICO" y "LÍMITES" (fuentes, [F#],
  "(pendiente de verificación)", datos personales, fraude, culpabilidad, datos como no instrucciones). El texto
  sigue siendo fijo, así que conserva el prompt caching. La preferencia "Escribe como" va en el bloque dinámico.
- **`pulir` y el streaming.** No se aplica a los trozos que se transmiten: sus reglas dependen del texto completo
  (el cierre, cuántas negritas hay, si una raya tiene pareja) y lo ya enviado no se puede retirar. Se aplica una
  vez al terminar: se guarda el texto pulido y el servidor envía el evento SSE `pulido` (antes de `fuentes`) para
  que el cliente reemplace lo mostrado. El mensaje de fallo del proveedor no se pule.
- **Ajustes → Personalización → "Escribe como"**: Automático, Estudiante, Abogado, Lenguaje sencillo. Clave
  `escritura` en las preferencias con lista blanca (valor desconocido: 400; valor guardado inválido: se lee como
  "auto").
- **Documentos.** `SISTEMA_BASE` (escritos, flujos y asistente) incluye `VOZ_ABOGADO` y la lista de rasgos a evitar.
  Si el escrito es del área "Consultorio jurídico" y la persona escribe como estudiante (o en automático y en el
  camino "Estoy aprendiendo Derecho"), se suma `VOZ_ESTUDIANTE` en el bloque dinámico del sistema. La salida
  pasa por `documentos.procesar_salida` (separa la lista a verificar y pule el escrito); en flujos y asistente se
  pule lo que se guarda y lo que recibe el paso siguiente.
- **Herramienta "Revisar estilo".** `POST /api/estilo/revisar {texto}`: requiere sesión, máximo 20.000 caracteres
  (413), 60 revisiones cada 5 minutos por cuenta (429), no llama al modelo y no cuesta consultas. Botón "Revisar
  estilo" en las acciones de cada respuesta del chat y en la vista del borrador (Documentos y Mis documentos); el
  resultado se pinta con `textContent`, sin JavaScript en línea.

---

## 3. Antes y después (ejemplos propios)

**Respuesta de examen (estudiante).**

> Antes: «¡Excelente pregunta! Es importante destacar que la tutela es un mecanismo fundamental en el ámbito del
> derecho colombiano. A continuación, te explico los requisitos: • Subsidiariedad • Inmediatez • Legitimación.
> En conclusión, la tutela procede. ¡Espero que te sirva! 😊»

> Después: «El problema es si Pedro puede usar la tutela para que la EPS le autorice la cirugía, aunque existe un
> trámite ante la Superintendencia de Salud. La tutela procede, porque ese trámite no protege a tiempo a quien
> tiene una cirugía urgente ordenada por su médico: la subsidiariedad cede ante un medio que no es eficaz para
> el caso. La inmediatez se cumple, pues la negativa es de hace un mes. La EPS dirá que Pedro debió acudir
> primero a la Superintendencia; ese argumento sí prosperaría si la cirugía no fuera urgente. Por tanto, el
> juez debe conceder el amparo.»

**Concepto (abogado).**

> Antes: «En el mundo actual, los contratos de arrendamiento juegan un papel crucial. **Cabe resaltar** que
> usted **no** puede terminar el contrato — salvo que exista justa causa — sin pagar la **indemnización**.»

> Después: «Usted no puede terminar el contrato antes del vencimiento sin pagar la cláusula penal, salvo que el
> arrendador haya incumplido. Las reparaciones que usted reportó se hicieron dentro del mes siguiente al aviso,
> de modo que no hay incumplimiento que alegar.»

**Memorial.**

> Antes: «Señor juez, me permito muy respetuosamente, con el debido respeto, solicitar de manera atenta el
> aplazamiento de la diligencia — por motivos de fuerza mayor —. Quedo atento a cualquier inquietud.»

> Después: «Señora jueza: como apoderado de la parte demandante, solicito aplazar la audiencia inicial del 15 de
> marzo de 2026, porque ese día debo asistir a un juicio oral en Tunja programado antes, según la constancia
> adjunta. Pido fijar nueva fecha a partir del 1 de abril.»

**Orientación a un ciudadano.**

> Antes: «¡Claro que sí! 🙌 Profundicemos en tus derechos como consumidor. ¿La clave? La garantía legal.»

> Después: «Sí puedes reclamar. El celular falló a las dos semanas, así que está dentro de la garantía legal:
> pídele por escrito a la tienda que lo cambie o te devuelva el dinero, y guarda la copia con el sello de
> recibido. Si se niega, presenta una queja gratuita ante la Superintendencia de Industria y Comercio.»

---

## 4. Evaluación del detector

`evaluacion/estilo.jsonl`: 20 textos escritos para esta prueba (10 con rasgos de IA de distinta intensidad y 10
humanos bien escritos: respuestas de examen, conceptos, hechos de tutela, memorial, correo, orientación
ciudadana). Se regenera con `python evaluacion/construir_estilo.py`. Resultado
(`tests/test_estilo.py::test_precision_y_exhaustividad_del_detector`):

| Métrica | Resultado | Meta |
|---|---|---|
| Precisión (textos marcados como IA que sí lo eran) | 10/10 = **100 %** | ≥ 90 % |
| Exhaustividad (textos de IA que se marcaron) | 10/10 = **100 %** | ≥ 90 % |
| Rasgos esperados encontrados | 36/36 = **100 %** | — |
| `pulir` deja intactos los 10 textos humanos | 10/10 | — |
| `pulir` baja el puntaje de los textos de IA | 10/10 | ≥ 8 |

**Advertencia sobre estas cifras:** el conjunto es pequeño y lo escribió el mismo autor del detector, con los
rasgos de la investigación en mente; el detector se ajustó mirando estos textos (por ejemplo, la regla de
tríadas y la de "quedo atento"). Las cifras muestran que el detector hace lo que promete sobre ejemplos claros,
**no** su desempeño sobre textos reales de estudiantes o de modelos (NOT VERIFIED). Para medirlo de verdad hace
falta un conjunto ciego: respuestas reales del modelo con y sin las nuevas guías y escritos de estudiantes con
su autorización.

---

## 5. Pendiente y límites (NOT VERIFIED)
- Efecto real de las voces sobre Claude Sonnet 5.5 (no hay clave de API en el entorno de desarrollo).
- El reemplazo del texto al final del streaming (evento `pulido`) puede notarse si el modelo usa muchos emojis o
  cierres; con las guías nuevas debería ser raro.
- Un abogado o docente debe revisar las voces: las fórmulas forenses y el método de examen se apoyan en fuentes
  generales y en la rúbrica propia, no en rúbricas de facultades.
- La demo de un solo archivo (`demo/pullex-demo.html`) no calcula la revisión de estilo (corre en el servidor): el
  botón avisa que no está disponible. La caja «Revisión de estilo» tiene estilos desde PUL-014 (`static/escritura.css`).
