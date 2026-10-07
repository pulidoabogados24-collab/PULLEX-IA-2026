# J06 — Liquidaciones

Módulo: `procedimientos/j06_liquidaciones.py` · Ruta: `POST /api/procedimientos/liquidacion` · Versión 1.0.0 ·
Estado: PROBADO (no OPERATIVO: falta revisión de un abogado o contador).

Fórmulas versionadas y aritmética decimal (`Decimal`, 34 dígitos, sin números binarios). No usa el modelo de IA.

**Regla de oro.** El procedimiento no trae de memoria tasas, índices, salarios mínimos ni auxilios. Son entradas
obligatorias del usuario, con su fuente, o salen de `reglas/parametros.json` cuando un valor oficial esté cargado
con enlace y fecha. **Hoy esa tabla está vacía.** Las únicas cifras propias son las que fija una norma verificada:
12 % de intereses sobre cesantías, 6 % de interés legal civil y el factor 1,5 del moratorio comercial.

## Tres liquidaciones (`tipo`)

### `prestaciones`

| Campo | Obligatorio | Descripción |
|---|---|---|
| `fecha_inicio`, `fecha_fin` | sí | Inicio del contrato y fecha final o de corte (incluida) |
| `salario_mensual` | sí | Base salarial ya definida por el usuario |
| `auxilio_transporte_mensual` | sí | Valor; `0` si no aplica |
| `auxilio_en_base_prestaciones` | si el auxilio es mayor que 0 | `true` o `false`: ¿entra en la base de cesantías y prima? |
| `conceptos` | no | `cesantias`, `intereses_cesantias`, `prima`, `vacaciones` (por defecto, los cuatro) |
| `vacaciones_dias_tomados` | no | Días de vacaciones ya disfrutados o pagados |
| `periodos`, `dias`, `base_dias_anio` | no | Para cambiar los períodos por defecto, los días o la base de 360 |

| Concepto | Fórmula (versión 1.0) | Regla | Norma | Estado |
|---|---|---|---|---|
| Cesantías | base × días / 360 | R-LIQ-0001, R-LIQ-0002 | CST, arts. 249 y 253 | Verificadas |
| Intereses sobre cesantías | cesantías × 0,12 × días / 360 | R-LIQ-0003 | Decreto 116 de 1976, arts. 1 y 2; Ley 50 de 1990, art. 99 | Verificada |
| Prima de servicios | base × días del semestre / 360 | R-LIQ-0004 | CST, art. 306 (Ley 1788 de 2016) | Verificada (desde 2016-07-07) |
| Vacaciones | salario / 30 × (días × 15 / 360 − días tomados) | R-LIQ-0005 | CST, arts. 186, 189 y 192; Ley 995 de 2005 | Verificada |
| Auxilio de transporte en la base | lo decide el usuario | R-LIQ-0006 | Ley 1 de 1963, art. 7 | **No verificado** |
| Año de 360 días, meses de 30 | parámetro | R-LIQ-0007 | sin norma verificada | **No verificado** |

Períodos por defecto: cesantías e intereses, del 1 de enero del año de la fecha final (o del inicio, si es
posterior) a la fecha final; prima, el semestre en curso; vacaciones, todo el tiempo trabajado menos los días
tomados. La salida lo advierte y permite cambiarlo.

Días 30/360: `(año2 − año1) × 360 + (mes2 − mes1) × 30 + (día2 − día1) + 1`, donde el día 31 cuenta como 30 y el
último día de febrero, cuando es la fecha final, también.

### `intereses_mora`

| Campo | Obligatorio | Descripción |
|---|---|---|
| `capital` | sí | |
| `clase` | sí | `legal_civil` (6 %), `comercial_moratorio` (1,5 × bancario corriente) o `tasa_indicada` |
| `periodos` | sí | `{desde, hasta, tasa_pct}`; en `legal_civil` no se indica tasa |
| `base_dias` | sí | 360 o 365; no hay valor por defecto |
| `metodo` | salvo `legal_civil` | `simple` o `equivalente_diaria` |
| `fuente_tasas` | salvo `legal_civil` | De dónde salió cada tasa (certificación, contrato, decisión) |

| Qué | Regla | Norma | Estado |
|---|---|---|---|
| Interés legal del 6 % anual | R-INT-0001 | Código Civil, art. 1617 | Verificada |
| Moratorio comercial = 1,5 × bancario corriente | R-INT-0002 | Código de Comercio, art. 884 | Verificada |
| Los intereses atrasados no producen interés | R-INT-0003 | Código Civil, art. 1617; Código de Comercio, art. 886 | Verificada |
| Tasa diaria equivalente = (1 + EA)^(1/base) − 1, sin capitalizar | R-INT-0004 | método financiero | **Revisión humana pendiente** |

Días de cada período: calendario, con ambas fechas incluidas. Cada período se redondea por separado.

### `indexacion`

`valor_historico`, `ipc_inicial`, `ipc_final` y `fuente_ipc` son obligatorios; `periodo_inicial` y `periodo_final`
son recomendados. Fórmula: valor histórico × IPC final / IPC inicial (R-IDX-0001: Corte Constitucional, sentencias
SU-637 de 2016 y T-1055 de 2007, que la aplican a la indexación de mesadas pensionales).

## Excepciones y abstenciones

- Falta salario, auxilio, fechas, capital, clase, base de días, método, períodos, tasa de un período, fuente de
  tasas, índices o fuente de los índices → `ABSTENCION`. Nunca se rellena con un valor supuesto.
- Auxilio mayor que 0 sin decir si entra en la base → `ABSTENCION`.
- Fecha final anterior a la inicial, fecha inexistente, números negativos o no numéricos, intereses sobre
  cesantías sin cesantías, períodos solapados, base distinta de 360 o 365, índice igual a cero, más días de
  vacaciones tomados que causados → `CONTRADICCION`.

## Salida

`estado`, `total`, `desglose` (por concepto: período, días, base, fórmula, fórmula con valores, valor exacto con
seis decimales y valor redondeado), `parametros`, `redondeo`, `normas`, `supuestos`, `advertencias`,
`juicio_profesional`, `faltantes`, `contradicciones`, `huella` y `aviso`.

Redondeo: cada concepto al peso más cercano, mitad hacia arriba; los cálculos intermedios usan el valor sin
redondear (los intereses sobre cesantías se calculan sobre la cesantía exacta).

## Límites

- No decide qué pagos son salario, si el salario varió, qué tasa o índice corresponde, ni el método de intereses.
- No incluye salarios pendientes, indemnizaciones, sanciones moratorias ni aportes.
- Las reglas del CST se verificaron con el texto vigente el 2026-10-02; para períodos anteriores se advierte que la
  vigencia en esa fecha no está comprobada.
- La fórmula de indexación está verificada para mesadas pensionales; su uso en otras obligaciones lo justifica el
  profesional.

## Pseudocódigo

```
según tipo:
  prestaciones:
    validar; si auxilio > 0 y no se indicó si entra en la base → ABSTENCION
    base = salario + (auxilio si el usuario dijo que entra)
    para cada concepto: período por defecto o indicado → días 30/360 (o los indicados)
      cesantías  = base × días / 360
      intereses  = cesantías_exactas × 0,12 × días / 360
      prima      = base × días / 360
      vacaciones = salario / 30 × (días × 15 / 360 − tomados)
      redondear al peso (mitad hacia arriba)
  intereses_mora:
    validar clase, base, método, fuente y períodos sin solape
    tasa = 6 % (civil) | tasa del período × 1,5 (comercial) | tasa del período (indicada)
    simple:              capital × tasa × días / base
    equivalente_diaria:  capital × ((1 + tasa)^(1/base) − 1) × días
  indexacion:
    valor × ipc_final / ipc_inicial
total = suma de los valores redondeados
```

## Pruebas

- `tests/test_procedimientos_liquidaciones.py`: días 30/360 (11 casos), cada fórmula, redondeo, exactitud decimal
  (0,3 × 0,2 / 0,1 = 0,6), misma huella en dos ejecuciones, auxilio decidido por el usuario, abstenciones,
  contradicciones, que el código no contiene salarios mínimos ni tasas, y que la tabla de parámetros solo acepta
  valores con enlace oficial.
- `evaluacion/procedimientos.jsonl`: 19 casos de J06 calculados a mano (7 de desarrollo, 12 de medición).
  Resultado: 19/19. Las tasas e índices de esos casos son de ejemplo y lo dicen.

## Pendiente con dependencia concreta

- Cargar en `reglas/parametros.json` el salario mínimo, el auxilio de transporte, el interés bancario corriente y
  el IPC con su norma, enlace y fecha. Depende de acceso a `mintrabajo.gov.co`, `superfinanciera.gov.co` y
  `dane.gov.co` o de que una persona los verifique.
- Verificar R-LIQ-0006 (Ley 1 de 1963, art. 7) y R-LIQ-0007 (año de 360 días) en fuente oficial.
- Revisión de R-INT-0004 por un profesional.
