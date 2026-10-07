# PUL-015 — Banco curado de casos del Laboratorio de casos

Rama: `pul/wip-banco-modular` · Estado: banco completo (180 casos) y conectado a la API; interfaz pendiente.

> **Advertencia — Exactitud jurídica: NOT VERIFIED.**
> Los 180 casos fueron redactados con asistencia de IA y **no han pasado revisión humana**. Antes de
> usarlos con estudiantes, un docente o abogado debe revisar cada caso: hechos, normas citadas, número
> y vigencia de cada artículo, criterios jurisprudenciales y conclusión. El validador y las pruebas
> automáticas revisan **estructura**, no derecho. Ningún texto de este banco debe presentarse como
> material verificado.

## 1. Conteo por área

Conteo real, tomado de `python scripts/validar_banco.py` (cada área: 6 básico, 6 intermedio, 5 avanzado, 3 experto).

| Área | Archivo | Casos | Ids |
|---|---|---|---|
| Constitucional | `academia_banco/constitucional.json` | 20 | `cons-01` … `cons-20` |
| Penal | `academia_banco/penal.json` | 20 | `pen-01` … `pen-20` |
| Civil | `academia_banco/civil.json` | 20 | `civ-01` … `civ-20` |
| Laboral | `academia_banco/laboral.json` | 20 | `lab-01` … `lab-20` |
| Administrativo | `academia_banco/administrativo.json` | 20 | `adm-01` … `adm-20` |
| Comercial | `academia_banco/comercial.json` | 20 | `com-01` … `com-20` |
| Familia | `academia_banco/familia.json` | 20 | `fam-01` … `fam-20` |
| Procesal | `academia_banco/procesal.json` | 20 | `proc-01` … `proc-20` |
| Probatorio | `academia_banco/probatorio.json` | 20 | `prob-01` … `prob-20` |
| **Total** | 9 archivos | **180** | |

Cobertura del Mapa del Derecho (`academia.MAPA`): 61 de 61 conceptos tienen al menos un caso.
Constitucional y Penal venían de commits anteriores de la rama; en esta tarea se escribieron las otras
siete áreas (140 casos) y se cambió el campo `aviso` de los nueve archivos para que diga NOT VERIFIED.

## 2. Esquema de un caso

`id`, `area`, `nivel`, `titulo`, `enunciado` (120–220 palabras, con al menos una fecha), `pregunta`,
`pistas` (2), `conceptos` (2 a 4, cada uno debe emparejar con un nodo del mapa),
`solucion` {`problema_juridico`, `normas` [{`norma`, `para_que`}], `analisis`, `contraargumento`,
`conclusion`, `errores_comunes` (≥ 2)}, `respuesta_modelo` (250–400 palabras, prosa),
`conectores_usados`, `variacion` {`cambio` «¿Qué cambia si…?», `respuesta`}, `distractor`
(obligatorio en avanzado y experto) y `revision_humana: true`.

## 3. Cómo se valida

```
python scripts/validar_banco.py          # informe legible; sale con 1 si hay errores
python scripts/validar_banco.py --json   # el mismo informe en JSON
python -m pytest tests/test_banco.py     # validador + conexión con la API
```

El validador comprueba, por archivo y por caso: 20 casos por área con la distribución 6/6/5/3; campos
obligatorios; longitudes de enunciado y respuesta modelo; fecha en el enunciado; pregunta terminada en
«?»; dos pistas; conceptos que emparejan con el mapa; solución completa; respuesta modelo en prosa (sin
listas) con al menos 6 conectores argumentativos de 4 categorías (`academia.detectar_conectores`);
`conectores_usados` coherente con el texto; variación bien formada; distractor declarado en los niveles
altos; `revision_humana: true`; ids únicos; ninguna sentencia fuera de la lista blanca
(`C-355 de 2006`, `T-760 de 2008`, `SU-214 de 2016`); ningún número de radicado; ninguna mención de
instituciones de educación superior por su nombre.

Última salida (resumen): `Banco curado: 180 casos` · `Conceptos del mapa cubiertos: 61/61` ·
`Conceptos que no emparejan con el mapa: 0` · sentencias citadas: `T-760 de 2008` (2) y
`SU-214 de 2016` (2) · `RESULTADO: VÁLIDO · Exactitud jurídica: NOT VERIFIED (requiere revisión docente)`.

**Lo que el validador no hace:** no comprueba que un artículo exista, que diga lo que el caso afirma, que
esté vigente, ni que la conclusión sea correcta. Tampoco detecta citas de leyes o artículos equivocados.

## 4. Qué está conectado

Cambio mínimo en `app.py` (el módulo `academia.py` ya traía `cargar_banco`, `BANCO`, `BANCO_IDX`,
`conceptos_ids` y `elegir_del_banco`). Los nombres internos de rutas y tablas (`/api/modular/*`,
`modular_casos`) no se tocaron; solo cambia el nombre visible de la sección, que es asunto del frontend.

| Punto | Comportamiento |
|---|---|
| `POST /api/modular/caso` con `{"origen": "banco", "area", "nivel"}` | Sirve un caso curado de esa área y nivel. No llama al modelo ni descuenta consulta. Funciona aunque no haya motor de IA configurado. |
| `POST /api/modular/caso` con `{"origen": "banco", "concepto_id"}` | Sirve un caso que evalúa ese concepto del mapa (prefiere el área del concepto y el nivel más cercano al recomendado). |
| Respuesta de un caso del banco | Campos públicos de siempre más `origen: "banco"`, `banco_id`, `curado: true`, `gasta_consulta: false`, `repetido`, `aviso` (incluye NOT VERIFIED) y `restantes` sin cambio. Nunca incluye solución, pistas, respuesta modelo, variación ni distractor. |
| Sin `origen` u `origen: "modelo"` | Igual que antes: caso generado por el modelo, cuesta 1 consulta; la respuesta ahora trae `origen: "modelo"`. |
| No repetición | Se evita repetir casos ya servidos al mismo estudiante; agotados los candidatos, se repite el que recibió hace más tiempo y se marca `repetido: true`. |
| `GET /api/modular/opciones` | Agrega `banco: {total, por_area, aviso}`. |
| `GET /api/modular/solucion` | Para casos del banco agrega `origen`, `banco_id`, `aviso`, `respuesta_modelo`, `conectores_usados`, `variacion` y `distractor`. |
| `GET /api/modular/caso/{id}` | Incluye `origen` para que la interfaz pueda mostrar la etiqueta al reabrir. |
| Pistas, solución, conceptos | Gratis, como en los casos generados. |
| `POST /api/modular/evaluar` | Sin cambios: la evaluación usa el modelo y cuesta 1 consulta, también para casos del banco; actualiza el mapa del estudiante. |
| `variacion_de` sobre un caso del banco | Sin cambios: genera la variación con el modelo (1 consulta). La variación curada se entrega con la solución. |

Pruebas: `tests/test_banco.py` (17 pruebas). Suite completa: ver el informe de la tarea.

## 5. Qué falta

1. **Revisión humana de los 180 casos** (bloqueante para usarlos con estudiantes). Sugerencia: agregar a
   cada caso un campo `revisado` {quién, fecha, observaciones} y que el validador lo informe; mientras
   no exista, la interfaz debe mostrar el aviso.
2. **Interfaz** (no se tocó `static/`, otra tarea la está cambiando). Pendiente:
   - opción para pedir «caso del banco (no gasta consulta)» además del caso generado, usando
     `opciones.banco` para mostrar disponibilidad;
   - etiqueta visible «Banco curado · sin verificar» y el texto de `aviso` en cada caso del banco;
   - en la solución, mostrar `respuesta_modelo`, la variación curada y el distractor;
   - indicar que evaluar la respuesta sí gasta una consulta.
3. **Conectores argumentativos**: `detectar_conectores`, `segmentar_conectores`, `resumen_conectores` y
   `conectores_publicos` existen en `academia.py` y los usa el validador, pero ningún endpoint los expone
   todavía (panel «Conectores para tu respuesta», línea de conectores en la evaluación y resaltado de la
   respuesta modelo). No hacía parte de esta tarea.
4. Los comentarios internos y el encabezado de `scripts/validar_banco.py` conservan el nombre antiguo de
   la sección; no son texto visible para el usuario.
5. Casos de Constitucional y Penal: no fueron reescritos ni revisados en esta tarea.

## 6. Puntos que un abogado debe revisar primero

Reglas seguidas al redactar: sin radicados, magistrados ni fechas de sentencias; solo dos sentencias con
número (lista blanca); cuando no había certeza del artículo se nombró la institución y se dejó la nota
«verificar». Aun así, estos puntos tienen mayor riesgo de error o de cambio normativo:

**Cambios normativos recientes que cruzan varios casos**
- Ley 2466 de 2025 (reforma laboral): tabla de indemnización del art. 64 del CST, preaviso y prórroga del
  contrato a término fijo (art. 46). Casos `lab-02`, `lab-08`, `lab-09`, `lab-15`, `lab-20`.
- Ley 2452 de 2025 (nuevo código procesal laboral, vigente desde abril de 2026): norma procesal de
  prescripción y reclamo escrito. Casos `lab-05`, `lab-12`, `lab-18`, `lab-19`, `lab-20`, `adm-18`.
- Ley 2442 de 2024 (divorcio por la sola voluntad de cualquiera de los cónyuges) y sus efectos sobre
  alimentos. Casos `fam-05`, `fam-09`.
- Ley 2220 de 2022 (conciliación): artículo exacto sobre suspensión de la caducidad y requisito de
  procedibilidad. Casos `adm-02`, `adm-07`, `proc-06`, `proc-20`.
- Valor del salario mínimo de 2026 y topes de cuantía, casación y salario integral: `proc-01`, `proc-17`,
  `lab-03`.

**Criterios jurisprudenciales afirmados sin número de sentencia (verificar línea vigente)**
- Civil: morigeración del año del art. 94 del CGP (`civ-14`); carga probatoria en responsabilidad médica
  (`civ-15`); concurrencia de actividades peligrosas y responsabilidad directa de la persona jurídica
  frente al art. 2358 del Código Civil (`civ-18`); pertenencia entre coherederos (`civ-19`); efectos de la
  promesa sin época determinada (`civ-17`).
- Laboral: exigibilidad de las cesantías a la terminación y tratamiento de los aportes a pensión
  (`lab-05`, `lab-12`, `lab-19`); umbral de la estabilidad reforzada por salud (`lab-10`); buena fe y
  sanciones moratorias (`lab-06`, `lab-14`); fuero de maternidad en contrato a término fijo y conocimiento
  del empleador (`lab-16`); culpa patronal: carga de la prueba, no descuento de lo pagado por riesgos
  laborales y cómputo de la prescripción (`lab-18`).
- Administrativo: títulos de imputación por armas de dotación (`adm-10`) y daño especial (`adm-14`);
  elección del medio de control según la fuente del daño (`adm-08`); art. 52 del CPACA, decidir y notificar
  dentro del término (`adm-09`, `adm-16`); unificación del Consejo de Estado sobre contrato realidad
  (`adm-18`); decaimiento del acto y cobro coactivo (`adm-19`).
- Comercial: efecto del llenado abusivo del título en blanco (`com-07`); reglamentación de conflictos de
  interés de administradores (`com-03`, `com-14`); facultad de la Superintendencia de Sociedades para
  reconocer la ineficacia (`com-17`).
- Familia: alimentos del hijo mayor que estudia (`fam-06`); imprescriptibilidad de la declaración de la
  unión marital (`fam-08`); extensión del régimen a parejas del mismo sexo y derechos hereditarios
  (`fam-16`); injuria atroz como causa de cesación de alimentos (`fam-17`); cómputo de los 140 días
  (`fam-18`); efectos de la separación de hecho sobre la sociedad conyugal y sociedad de hecho entre
  compañeros (`fam-20`).
- Procesal: unificación sobre fueros privativos concurrentes (`proc-14`); sustentación de la apelación
  ante el superior, precedente en disputa (`proc-18`); condicionamiento constitucional del art. 121 del
  CGP (`proc-19`).
- Probatorio: cadena de custodia como asunto de autenticidad y no de legalidad (`prob-03`, `prob-09`,
  `prob-14`); grabación hecha por la víctima interlocutora (`prob-08`); excepciones a la prueba derivada
  (`prob-10`, `prob-13`, `prob-18`); autonomía del lavado de activos y uso de la carga dinámica en
  materia penal (`prob-20`).

**Artículos citados con número cuya exactitud conviene confirmar**
- Código de Comercio: arts. 982, 1003, 993 y 1006 (`civ-20`); 718, 729, 730 y 731 (`com-10`); 29, 164,
  641 y 901 (`com-20`); 61 y 67 (`prob-16`); 186, 190, 191 y 897 (`com-17`); 660 y 624 (`com-19`).
- Ley 1116 de 2006, arts. 74 y 82 (`com-18`); Ley 1258 de 2008, arts. 7, 20, 42 y 43; Ley 222 de 1995,
  arts. 22 a 25; Ley 1563 de 2012, art. 21 (`proc-11`); Ley 2213 de 2022, arts. 8 y 12.
- Ley 142 de 1994, art. 158 (`adm-06`); Ley 270 de 1996, arts. 65 a 69 (`adm-15`); CPACA, arts. 52, 91,
  92, 97, 168 y 229 a 231.
- Ley 1098 de 2006, arts. 110, 111, 112 y 129; Ley 294 de 1996, arts. 4 y 5; Ley 1257 de 2008, art. 8;
  Convenio de La Haya de 1980 (Ley 173 de 1994), artículos sobre el plazo de un año y las excepciones
  (`fam-19`).
- CGP: arts. 228, 256, 272, 317, 372, 382 y 384; Código Civil: arts. 1744, 1747, 2346 a 2348, 2358, 2530
  a 2532; Ley 906 de 2004: arts. 23, 232, 235, 237, 254, 277, 381, 437, 438 y 455.
- CST: arts. 34, 35, 46, 62 (parágrafo), 64, 65, 67 a 69, 127, 128, 132, 216, 239 a 241, 488 y 489;
  Ley 361 de 1997, art. 26; Ley 1429 de 2010, art. 63.

**Cómputos de términos incluidos en los casos**
Varios casos calculan vencimientos (caducidad de cuatro meses y de dos años, traslados, prescripción,
140 días, suspensión por conciliación). Se dejaron márgenes para evitar casos de borde, pero deben
recalcularse con calendario oficial, festivos y vacancia judicial antes de darlos por buenos:
`adm-02`, `adm-07`, `adm-08`, `adm-11`, `civ-07`, `civ-14`, `fam-08`, `fam-18`, `proc-04`, `proc-06`,
`proc-08`, `proc-09`, `proc-12`.

## 7. Datos y nombres

Personas y empresas son ficticias; no hay documentos de identidad ni direcciones. Las ciudades son
reales. Las entidades demandadas llevan nombres inventados (municipios de Monteluna, Villa del Rosal,
Valle Claro y Puerto Sereno; departamento de Los Andes). Si algún nombre comercial coincide con una
empresa real, es casual y debe cambiarse.
