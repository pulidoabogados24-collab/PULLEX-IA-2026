# J04 — Análisis jurisprudencial

Módulo: `procedimientos/j04_jurisprudencia.py` · Ruta: `POST /api/procedimientos/jurisprudencia` · Versión 1.0.0 ·
Estado: PROBADO como ficha y validador. **No hay base de sentencias cargada**: el procedimiento no busca ni
propone precedentes.

## Entradas

`problema_juridico` (obligatorio), `hechos` y, opcionalmente, `fichas` diligenciadas por una persona.

## Ficha

| Campo | Contenido |
|---|---|
| `autoridad` | Corporación y sala o sección |
| `tipo_decision` | C, SU, T, casación, unificación, auto… |
| `identificador` | Número o radicado exacto |
| `fecha` | AAAA-MM-DD |
| `problema_juridico` | Lo que resolvió la decisión |
| `fundamento_determinante` | Razón que sostiene la decisión, con cita localizable |
| `diferencias_con_el_caso` | Semejanzas y diferencias de hecho y de derecho |
| `efectos` | A quién obliga y desde cuándo |
| `enlace`, `fecha_consulta` | Fuente en la autoridad que la expidió y fecha de consulta |

## Reglas

Los efectos de cada tipo de decisión solo se afirman con reglas verificadas del registro:

| Tipo | Regla | Norma | Estado |
|---|---|---|---|
| C | R-JUR-0001 | Constitución, art. 243 (cosa juzgada constitucional) | Verificada |
| C | R-JUR-0002 | Ley 270 de 1996, art. 48, num. 1 (erga omnes en la parte resolutiva) | Verificada |
| C | R-JUR-0005 | Ley 270 de 1996, art. 45 (efectos hacia el futuro, salvo decisión contraria) | Verificada |
| T | R-JUR-0003 | Ley 270 de 1996, art. 48, num. 2; Decreto 2591 de 1991, art. 36 | Verificada |
| SU | R-JUR-0004 | sin norma verificada | **No verificado**: no se afirma ningún efecto |

El art. 48 de la Ley 270 de 1996 es condicionalmente exequible; el condicionamiento no se verificó y queda como
juicio profesional.

## Validaciones

- Campos obligatorios → `INCOMPLETA` con la lista.
- El tipo se deduce del identificador (forma de la Corte Constitucional); si no coincide con el tipo declarado, o
  el año del identificador no coincide con la fecha, alerta.
- Si la ficha atribuye efectos generales («erga omnes», «obliga a todos») a una decisión T, SU o de otra
  autoridad, alerta con la regla correspondiente. Si limita a las partes una sentencia C, también.
- Existencia: `NO_VERIFICADA`, salvo enlace a la autoridad y fecha de consulta, en cuyo caso
  `ENLACE_OFICIAL_DECLARADO_NO_ABIERTO_POR_EL_SISTEMA`. El sistema no abre el enlace.

## Salida

Sin fichas: `SIN_BASE_DE_SENTENCIAS`, la ficha vacía, lo que falta y dónde buscar. Con fichas:
`FICHAS_VALIDADAS`, cada una con su validación, y el número de fundamentos distintos (posibles líneas distintas).

## Límites

No inventa sentencias: en el código no hay ninguna. No atribuye efectos generales ni fuerza vinculante sin
comprobarlos. La ratio decidendi, la analogía con el caso y la fuerza del precedente son juicio profesional.

## Pseudocódigo

```
si no hay problema → ABSTENCION
si no hay fichas → SIN_BASE_DE_SENTENCIAS + ficha vacía + faltantes
para cada ficha:
    faltan = campos vacíos
    tipo = forma del identificador (C | SU | T | A | ninguno)
    alertas = tipo declarado ≠ tipo ; año ≠ fecha ; efectos generales sin regla verificada ; enlace no oficial
    efectos afirmables = reglas verificadas del registro para ese tipo, a la fecha de la decisión
```

## Pruebas

`tests/test_procedimientos_otros.py`: ficha vacía sin base; efectos por tipo desde el registro; alerta por efectos
generales en T, SU y otra autoridad; ficha incompleta, incoherente o con enlace no oficial; el código no contiene
sentencias.

## Pendiente con dependencia concreta

Base de sentencias verificada (carpeta «Sentencia y Jurisprudencia» del Drive, tras inventario y clasificación) y
verificación de R-JUR-0004 en la relatoría de la Corte Constitucional.
