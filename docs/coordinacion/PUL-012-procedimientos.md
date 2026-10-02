# PUL-012 — Procedimientos jurídicos J01–J09 y registro de reglas

Fecha: 2026-10-02 · Responsable: Claude · Revisión: pendiente (Codex y un profesional del derecho) ·
Rama: `pul/012-procedimientos`, sobre `pul/010-biblioteca` @ `5b59df2`. Sin push.

Entregable 8 de `ESPECIFICACION-LEXCOL.md` (secciones 9, 10 y 12). Detalle por procedimiento en
[`docs/procedimientos/`](../procedimientos/README.md).

## Qué quedó hecho

| Pieza | Dónde | Estado |
|---|---|---|
| Registro de reglas con consulta a una fecha | `reglas/registro.json`, `reglas.py`, `GET /api/reglas` | PROBADO |
| J01–J09, un módulo por procedimiento | `procedimientos/` | PROBADO (ver alcance abajo) |
| Rutas autenticadas, sin gasto de consultas | `procedimientos/rutas.py`; bloque de dos líneas en `app.py` | PROBADO |
| Vista Herramientas: términos y liquidación | `static/herramientas.js`, bloque CSS en `index.html` | PROBADO en Chromium (1280 y 390 px) |
| Evaluación con dos conjuntos | `evaluacion/procedimientos.jsonl`, `evaluar_procedimientos.py` | 45/45 |
| Documentación | `docs/procedimientos/` (README, J01–J09, registro) | Escrita |

Nada está OPERATIVO: ningún abogado ha revisado las reglas ni las fórmulas y no hay uso con casos reales.

## Registro de reglas

57 versiones de 50 reglas: **49 verificadas** en fuente oficial con enlace y fecha de consulta (2026-10-02),
**7 no verificadas** y **1 pendiente de revisión humana**. Tabla completa: [`REGISTRO-DE-REGLAS.md`](../procedimientos/REGISTRO-DE-REGLAS.md).

No verificadas (el cálculo que depende de ellas lo advierte o se abstiene):

| Regla | Qué | Por qué |
|---|---|---|
| R-TERM-0007 | Sábado no hábil | No se halló norma general en fuente oficial; es un supuesto visible y modificable |
| R-PLAZO-0001/0002/0003 v2 | Plazos de petición ampliados (28-03-2020 a 17-05-2022) | El texto derogado del Decreto 491 de 2020 no se muestra en la fuente consultada: la calculadora se abstiene |
| R-LIQ-0006 | Auxilio de transporte en la base de prestaciones | `suin-juriscol.gov.co` y `mintrabajo.gov.co` no fueron accesibles: el usuario debe decidirlo |
| R-LIQ-0007 | Año de 360 días y meses de 30 | Convención sin fuente oficial consultada; parámetro visible |
| R-JUR-0004 | Alcance de las sentencias SU | Sin norma verificada: J04 no afirma ningún efecto para SU |
| R-INT-0004 (revisión humana) | Método de tasa diaria equivalente | Método financiero declarado; lo elige el usuario |

## Estado real de cada procedimiento

| Id | Estado | Alcance real |
|---|---|---|
| J01 | PROBADO | Reglas de palabras clave; precisión sin medir con casos reales |
| J02 | PROBADO | Solo catálogo interno (203 tipos); la biblioteca de Drive no está conectada (hay punto de extensión) |
| J03 | PROBADO | Solo normas del registro; para el resto responde «vigencia pendiente de comprobar» |
| J04 | PROBADO | Ficha y validación; no hay base de sentencias y no propone ninguna |
| J05 | PROBADO | 26/26 casos calculados a mano; festivos contrastados con 19 fechas publicadas |
| J06 | PROBADO | 19/19 casos calculados a mano; tabla de valores oficiales vacía (todo valor es entrada del usuario) |
| J07 | PROBADO | Sobre la estructura recibida; no lee documentos |
| J08 | PROBADO el verificador; IMPLEMENTADO `preparar()` | El verificador no está integrado a la vista Documentos ni a `/api/documentos/generar` |
| J09 | PROBADO | Propone y nunca aplica; perfiles por esquema, sin el registro real de perfiles |

## Evidencia

- `python -m pytest -q tests`: **298 pasan** (147 anteriores + 151 nuevas).
- `python evaluacion/evaluar_procedimientos.py`: **45/45**. Desarrollo 18/18 (J05 11, J06 7); medición 27/27
  (J05 15, J06 12). Por categoría: normal 13/13, frontera 16/16, falta de datos 8/8, contradicción 8/8.
  Umbral (100 %) y resultados esperados quedaron en un commit anterior a la primera ejecución (`60481c8`).
- Navegador (`tests/e2e_herramientas.py`, servidor simulado en el puerto 8783, base limpia): todas las
  verificaciones pasan en 1280 y 390 px; cero violaciones de CSP; cero errores de consola; los cálculos no gastan
  consultas; sin sesión la API responde 401. Regresión: `e2e_navegador` 30/30, `e2e_documentos`, `e2e_academia` y
  `e2e_fuentes` sin fallos.

Límite de la evidencia: los casos «a mano» los calculó la misma sesión que escribió el código. Miden que el
programa aplica la regla registrada, no que la regla esté bien interpretada.

## Cambios en archivos compartidos

- `app.py`: un bloque marcado de ocho líneas (importa y registra las rutas), antes de las rutas de administración.
- `static/index.html`: botón de navegación, sección `v-herramientas`, etiqueta de script y bloque CSS
  `/* ---- Herramientas ---- */`.
- `static/app.js`: `ver()` conoce la vista `herramientas` (dos líneas).
- `demo/construir_demo.py` y `demo/pullex-demo.html` (regenerado): la demostración sin servidor incluye la vista,
  que avisa que los cálculos no están disponibles allí.

La barra de navegación queda con 7 botones; en 390 px caben (probado), pero conviene revisarla en un teléfono real.

## Pendientes con dependencia concreta

1. **Revisión jurídica** de las 57 versiones del registro y de las fórmulas de J06. Depende de un abogado (y de
   un contador para liquidaciones).
2. **Tabla de valores oficiales** (`reglas/parametros.json`): salario mínimo, auxilio de transporte, interés
   bancario corriente, IPC. Depende de acceso a `mintrabajo.gov.co`, `superfinanciera.gov.co` y `dane.gov.co`
   (los dos primeros no respondieron desde este entorno) o de carga manual verificada.
3. **Reglas por verificar**: R-LIQ-0006, R-LIQ-0007, R-TERM-0007, R-JUR-0004 y los plazos del Decreto 491 de 2020.
   Depende de acceso a `suin-juriscol.gov.co`.
4. **Inicio de vigencia** de las reglas del CGP, del CST y de la Ley 4 de 1913: hoy solo están verificadas a la
   fecha de consulta y la calculadora lo advierte para otras fechas.
5. **Conectar J02 a la biblioteca**: depende de `/api/biblioteca/buscar` con permisos por usuario.
6. **Integrar J08 al automatizador** (exigir `preparar()` y mostrar el verificador en Documentos): depende de
   coordinar cambios en `app.py` y `static/documentos.js`.
7. **Base de sentencias para J04**: depende del inventario y clasificación de la carpeta de jurisprudencia.
8. **Conjunto de evaluación independiente** para J05 y J06, calculado por un profesional, y casos reales para J01.
9. Acceso por plan: las rutas nuevas exigen sesión pero no plan; al fusionar `pul/planes-y-proveedores` hay que
   decidir en qué plan quedan las herramientas.
