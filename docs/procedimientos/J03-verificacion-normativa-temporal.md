# J03 — Verificación normativa temporal

Módulo: `procedimientos/j03_vigencia.py` (sobre `reglas.py`) · Ruta: `POST /api/procedimientos/vigencia` ·
Versión 1.0.0 · Estado: PROBADO para las normas que están en el registro.

## Entradas

`disposicion` («Ley 1437 de 2011, art. 14», «CGP art. 118», «Decreto 2591 de 1991, artículo 31»), `fecha_hechos`
y `fecha_analisis` (por defecto, hoy).

## Reglas

- La disposición se busca en el soporte principal y en los soportes adicionales de cada regla del registro.
  Reconoce las siglas CGP, CPACA, CST, C.P. y los nombres de los códigos.
- Para cada regla hallada se toma la versión cuyo período contiene la **fecha de los hechos** y, aparte, la que
  contiene la fecha del análisis. Si son distintas, se informa el cambio y se muestra la aplicable a los hechos.
- `reglas.vigencia_comprobada(regla, fecha)` distingue: en período comprobado; fecha anterior a la consulta sin
  inicio de vigencia verificado; fecha posterior a la consulta; regla no verificada.

## Salida

`estado`:

- `REGLA_APLICABLE_COMPROBADA`: hay regla y su vigencia en la fecha de los hechos está comprobada.
- `VIGENCIA_PENDIENTE_DE_COMPROBAR`: la disposición no está en el registro, o no está comprobado que rigiera en
  esa fecha. Trae `por_verificar` (texto de la época, modificaciones, derogatorias, sentencias, transición) y
  `donde_verificar` (SUIN-Juriscol, Secretaría del Senado, relatoría de la Corte Constitucional, Gestor Normativo,
  Diario Oficial).
- `ABSTENCION` o `CONTRADICCION` si faltan datos, la fecha no existe o el análisis es anterior a los hechos.

Por regla: versión aplicable a los hechos, versión vigente al análisis, si hubo cambio y todas las versiones
registradas con sus períodos.

## Límites

- Solo conoce las reglas y versiones cargadas (57 versiones): puede haber modificaciones no registradas.
- No abre la red: no comprueba nada nuevo, razona sobre lo ya comprobado.
- La transición entre normas, la retroactividad y la favorabilidad son juicio profesional.
- La norma más reciente no es automáticamente la aplicable a hechos anteriores.

## Pseudocódigo

```
validar disposición y fechas
reglas = buscar_por_norma(disposición)
si no hay → VIGENCIA_PENDIENTE_DE_COMPROBAR + qué verificar y dónde
para cada regla:
    vh = vigente(regla, fecha_hechos) ; va = vigente(regla, fecha_analisis)
    cambio = vh.version ≠ va.version
    comprobada = vigencia_comprobada(vh, fecha_hechos)
estado = COMPROBADA si todas lo están ; si no, PENDIENTE + qué verificar y dónde
```

## Pruebas

`tests/test_procedimientos_otros.py` y `tests/test_reglas.py`: petición de 2019 (versión 1) frente a análisis de
2026 (versión 3); petición de 2021 (versión no verificada → pendiente); CGP en 2019 (inicio sin comprobar →
pendiente); norma inexistente; fechas imposibles; consulta a una fecha sin devolver «la última».
