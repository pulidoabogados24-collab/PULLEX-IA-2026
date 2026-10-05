# J05 — Cómputo de términos

Módulos: `procedimientos/j05_terminos.py` y `procedimientos/calendario.py` · Ruta: `POST /api/procedimientos/terminos`
· Versión 1.0.0 · Estado: PROBADO (no OPERATIVO: falta revisión de un abogado).

Calculadora determinista y reproducible. La misma entrada produce siempre la misma salida y la misma `huella`.
No usa el modelo de IA.

## Entradas

| Campo | Obligatorio | Descripción |
|---|---|---|
| `regimen` | sí | `cgp`, `contencioso`, `tutela`, `administrativo` u `otro` |
| `termino_id` | uno de los dos | Término de la tabla verificada (`R-PLAZO-0001` … `R-PLAZO-0015`) |
| `cantidad`, `unidad` | uno de los dos | Número y `dias`, `meses` o `anios` cuando el término no está en la tabla |
| `tipo_dias` | si son días y la tabla no lo fija | `habiles` o `calendario` |
| `fecha_notificacion` | sí | Día en que quedó surtida la notificación, la recepción o el hecho |
| `forma_notificacion` | sí | `estado`, `personal`, `mensaje_datos`, `aviso`, `conducta_concluyente`, `recepcion`, `comunicacion`, `hecho`, `audiencia`, `otra` |
| `acuse_constatado` | con `mensaje_datos` | `true` si hay acuse de recibo o acceso constatado |
| `vacancia_judicial` | no | `true`, `false` o sin indicar: ¿el despacho tuvo vacancia colectiva del 20 de diciembre al 10 de enero? |
| `semana_santa_judicial` | no | `true`, `false` o sin indicar: ¿no atendió lunes a miércoles santos? |
| `sabado_habil` | no | `true` si el despacho o la entidad atiende los sábados |
| `suspensiones` | no | Lista de `{desde, hasta, motivo}` |
| `dias_no_habiles` | no | Cierres del despacho o de la entidad: `{fecha, motivo}` |
| `fecha_providencia` | no | Para detectar una notificación anterior a la decisión |

## Reglas y fuentes

Todas en `reglas/registro.json`; el detalle y los enlaces están en [REGISTRO-DE-REGLAS.md](REGISTRO-DE-REGLAS.md).

| Qué | Regla | Norma | Estado |
|---|---|---|---|
| El término corre desde el día siguiente a la notificación | R-TERM-0001 | CGP, art. 118 | Verificada |
| Meses y años: mismo día; si no existe, último del mes; si es inhábil, primer hábil | R-TERM-0002 | CGP, art. 118, inc. 7 | Verificada |
| En términos de días no cuentan vacancia ni días con el juzgado cerrado | R-TERM-0003 | CGP, art. 118, inc. final | Verificada |
| Plazos legales de días: se suprimen feriados y vacantes | R-TERM-0004 | Ley 4 de 1913, art. 62 | Verificada |
| Los plazos terminan a medianoche del último día | R-TERM-0005 | Ley 4 de 1913, arts. 59 y 60 | Verificada |
| Notificación por mensaje de datos: dos días hábiles tras el envío | R-TERM-0006 | Ley 2213 de 2022, art. 8 | Verificada (desde 2022-06-13) |
| Sábado no hábil | R-TERM-0007 | sin norma verificada | **No verificado** (supuesto visible y modificable) |
| Festivos y traslado al lunes | R-FEST-0001, R-FEST-0002 | Ley 51 de 1983; Ley 2578 de 2026 | Verificadas (dos versiones) |
| Festivos que dependen de la Pascua | R-FEST-0003 | fechas del Banco de la República | Verificada |
| Vacancia del 20 de diciembre al 10 de enero | R-VAC-0001 | Ley 31 de 1971, art. 1, lit. b | Verificada |
| Semana Santa como vacancia judicial | R-VAC-0002 | Ley 31 de 1971, art. 1, lit. a | Verificada |
| Despachos sin vacaciones colectivas | R-VAC-0003 | Ley 270 de 1996, art. 146 | Verificada |
| Tabla de términos frecuentes | R-PLAZO-0001 a 0015 | Ley 1755 de 2015, Decreto 2591 de 1991, CGP, CPACA | Verificadas, salvo la versión 2 de 0001–0003 |

El calendario no tiene fechas escritas a mano: cada festivo sale de la versión de R-FEST-0001 vigente ese día.
El 9 de julio solo es festivo desde el 2 de junio de 2026.

## Excepciones y abstenciones

- Falta `regimen`, `forma_notificacion`, `fecha_notificacion`, la cantidad o la clase de días → `ABSTENCION`.
- `forma_notificacion = audiencia` → `ABSTENCION`: el art. 118 dice que el término corre «a partir de su
  otorgamiento» y eso se deja a juicio profesional.
- `mensaje_datos` sin acuse constatado, o anterior al 13 de junio de 2022 → `ABSTENCION`.
- No se sabe si hubo vacancia o cierre en Semana Santa **y el dato cambia la fecha** → `ABSTENCION` con los
  escenarios. Si el dato no cambia nada, se calcula y se dice.
- Petición radicada entre el 28 de marzo de 2020 y el 17 de mayo de 2022 → `ABSTENCION`: el plazo ampliado no
  está verificado. El usuario puede indicar el número y el resultado lo declara como dato suyo.
- Fecha inexistente, suspensión que termina antes de empezar, notificación anterior a la providencia, estado en
  día inhábil, régimen distinto al del término, cantidad distinta a la de la regla → `CONTRADICCION`.
- Días calendario que vencen en día inhábil: no se extienden (la extensión solo está verificada para meses y años)
  y se advierte.

## Salida

`estado`, `fecha_vencimiento` y su texto, `inicio_computo`, `termino`, `cronologia` (fecha, día, número de cuenta
o motivo por el que no cuenta), `escenarios`, `normas`, `supuestos`, `advertencias`, `juicio_profesional`,
`faltantes`, `contradicciones`, `entrada` normalizada, `huella` y `aviso`.

## Límites

- No decide cuándo se surtió la notificación, si el recurso procede, ni si hubo suspensión: usa lo que se le dice.
- La regla de inicio para mensaje de datos admite otra lectura que empieza un día después; se usa la que da la
  fecha más temprana y se advierte.
- En términos de meses o años con suspensión se corre el vencimiento los días suspendidos (método declarado).
- Fuera del CGP, aplicar el art. 118 por analogía es una decisión profesional (se señala).
- Años admitidos: 1984 a 2069.

## Pseudocódigo

```
validar entrada → faltantes, contradicciones
si hay termino_id: regla = reglas.vigente(termino_id, fecha_notificacion)      # a la fecha, no la de hoy
    si la regla no está verificada o no fija número → falta "número de días aplicable"
si hay contradicciones → CONTRADICCION ; si hay faltantes → ABSTENCION

para cada combinación desconocida de (vacancia, semana santa):               # 1, 2 o 4 escenarios
    calendario = fines de semana + festivos(regla vigente cada día) + vacancia + semana santa + suspensiones + cierres
    inicio = día siguiente a la notificación        (mensaje de datos: tras dos días hábiles desde el envío)
    si unidad = días:  avanzar día a día contando los que el calendario admite hasta llegar a la cantidad
    si meses o años:   mismo día del mes o año; + días suspendidos; si es inhábil → siguiente hábil
si los escenarios dan fechas distintas → ABSTENCION con escenarios
si no → CALCULADO con cronología, normas, supuestos, advertencias y juicio profesional
```

## Pruebas

- `tests/test_procedimientos_terminos.py`: festivos calculados contra 19 fechas publicadas por el Banco de la
  República y el Consejo Superior de la Judicatura (`reglas/festivos_oficiales.json`, con enlace cada una); Pascua
  2024–2027; traslado al lunes; dos festivos el mismo día; vacancia; meses y bisiestos; abstenciones;
  contradicciones; escenarios; regla a la fecha; reproducibilidad.
- `evaluacion/procedimientos.jsonl`: 26 casos de J05 calculados a mano (11 de desarrollo, 15 de medición) —
  normales, de frontera (fin de semana, festivo trasladado, Semana Santa, bisiesto, cambio de año), de falta de
  datos y de contradicción. Resultado: 26/26.

De los 19 festivos de 2026, 13 se contrastaron con una página oficial; los otros 6 salen de la regla.
