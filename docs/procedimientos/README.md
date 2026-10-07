# Procedimientos jurídicos J01–J09 y registro de reglas

Sección 9 de `docs/coordinacion/ESPECIFICACION-LEXCOL.md`. Código en `procedimientos/` y `reglas.py`; datos en
`reglas/`. Fecha de esta versión: 2026-10-02.

## Qué hay

| Id | Procedimiento | Módulo | Ruta HTTP | Estado real |
|---|---|---|---|---|
| J01 | [Clasificación y orientación](J01-clasificacion-y-orientacion.md) | `j01_clasificacion.py` | `POST /api/procedimientos/clasificar` | PROBADO |
| J02 | [Recuperación de modelos](J02-recuperacion-de-modelos.md) | `j02_modelos.py` | `POST /api/procedimientos/modelos` | PROBADO (solo catálogo interno) |
| J03 | [Verificación normativa temporal](J03-verificacion-normativa-temporal.md) | `j03_vigencia.py` | `POST /api/procedimientos/vigencia` | PROBADO |
| J04 | [Análisis jurisprudencial](J04-analisis-jurisprudencial.md) | `j04_jurisprudencia.py` | `POST /api/procedimientos/jurisprudencia` | PROBADO (ficha y validación; sin base de sentencias) |
| J05 | [Cómputo de términos](J05-computo-de-terminos.md) | `j05_terminos.py`, `calendario.py` | `POST /api/procedimientos/terminos` | PROBADO |
| J06 | [Liquidaciones](J06-liquidaciones.md) | `j06_liquidaciones.py` | `POST /api/procedimientos/liquidacion` | PROBADO |
| J07 | [Matriz probatoria](J07-matriz-probatoria.md) | `j07_matriz_probatoria.py` | `POST /api/procedimientos/matriz-probatoria` | PROBADO |
| J08 | [Generación y revisión de escritos](J08-generacion-y-revision-de-escritos.md) | `j08_escritos.py` | `POST /api/procedimientos/verificar-escrito` | PROBADO (verificador); generación sin integrar al flujo |
| J09 | [Actualización e impacto](J09-actualizacion-e-impacto.md) | `j09_impacto.py` | `POST /api/procedimientos/impacto` (administración) | PROBADO |

«PROBADO» = pruebas automáticas propias y, en J05 y J06, evaluación con casos calculados a mano. Ninguno está
OPERATIVO: falta la revisión de un profesional del derecho y uso con casos reales. Además: `GET /api/procedimientos`
(catálogo y opciones de la interfaz) y `GET /api/reglas` ([registro de reglas](REGISTRO-DE-REGLAS.md)).

Todas las rutas exigen sesión, no llaman al modelo de IA y no descuentan consultas. Límite: 90 llamadas por minuto
por cuenta.

## Lo determinista y lo que queda a juicio profesional

Cada salida separa cuatro listas:

- `normas`: reglas del registro usadas, con identificador, versión, estado y enlace de la fuente.
- `supuestos`: lo que el cálculo dio por cierto (por ejemplo, «el sábado no se contó como día hábil»).
- `advertencias`: reglas no verificadas usadas y reglas cuya vigencia a la fecha del cálculo no está comprobada.
- `juicio_profesional`: lo que el procedimiento no decide.

Estados comunes: `CALCULADO` (o el propio de cada procedimiento), `ABSTENCION` (falta un dato esencial: no hay
resultado) y `CONTRADICCION` (los datos son imposibles o incoherentes: tampoco hay resultado).

## Disciplina de fuentes (sección 10)

Cada regla jurídica material se comprobó el 2026-10-02 en una fuente oficial y quedó en `reglas/registro.json` con
enlace, fecha de consulta y cita. Cómo se consultó:

- Secretaría del Senado (`secretariasenado.gov.co`): texto descargado y leído literalmente.
- Gestor Normativo de Función Pública, Banco de la República, Rama Judicial y Corte Constitucional: lectura con
  la herramienta de consulta web, pidiendo cita literal. El registro lo indica en `metodo_verificacion`.
- **No accesibles desde el entorno de trabajo**: `suin-juriscol.gov.co` y `mintrabajo.gov.co`. Lo que dependía de
  ellas quedó `NO_VERIFICADO` (ver «Lo que falta verificar» en el registro).

Hallazgos de la verificación que cambiaron el código respecto de lo que se habría escrito de memoria:

1. **Ley 2578 de 2026** (1 de junio): el 9 de julio es festivo nacional y se traslada al lunes. Confirmado en la
   Secretaría del Senado, en la Carta Circular GE-0203 de 2026 del Banco de la República y en la Circular
   PCSJC26-26 del Consejo Superior de la Judicatura. Por eso la regla de festivos tiene dos versiones.
2. El art. 177 del Código Sustantivo del Trabajo publicado por la Secretaría del Senado omite el «once de
   noviembre» entre los festivos trasladables; el texto de Función Pública lo incluye y el Banco de la República
   publica ese festivo en lunes. Queda anotada la discrepancia.
3. El art. 14 del CPACA tuvo una ampliación temporal (Decreto Legislativo 491 de 2020, art. 5, derogado por la
   Ley 2207 de 2022). El número de días ampliados no se pudo leer en la fuente: esa versión está `NO_VERIFICADO`
   y la calculadora se abstiene para peticiones de ese período.

## Evaluación (sección 12)

`evaluacion/procedimientos.jsonl` y `evaluacion/evaluar_procedimientos.py`. 45 casos de J05 y J06 con resultado
esperado calculado a mano y explicado, en dos conjuntos: desarrollo (18) y medición (27). Umbral fijado antes de
medir: 100 %. Resultado de la primera ejecución (2026-10-02): 45/45; medición 27/27.

Límite de esta evaluación: los resultados esperados los calculó la misma sesión que escribió el código, con las
mismas reglas. Mide que el programa hace lo que la regla registrada dice, no que la regla esté bien interpretada.
Falta un conjunto calculado por un abogado o contador independiente.

```bash
python evaluacion/evaluar_procedimientos.py            # tabla y código de salida
python -m pytest -q tests/test_reglas.py tests/test_procedimientos_*.py
python scripts/tabla_reglas.py                         # regenera REGISTRO-DE-REGLAS.md
```

## Mantenimiento del registro

1. Verificar la norma en la fuente oficial y anotar enlace, fecha y cita.
2. Si cambia una regla existente: cerrar la versión actual (`vigencia.hasta` = día anterior al cambio) y agregar
   la versión siguiente con su `vigencia.desde`. No se edita una versión ya publicada. `J09` propone este cambio.
3. Correr `python -m pytest -q tests/test_reglas.py` (valida esquema, enlaces oficiales y que las versiones no se
   solapen) y `python scripts/tabla_reglas.py`.
4. Revertir es quitar la versión nueva y reabrir la anterior: el historial de git conserva ambas.
