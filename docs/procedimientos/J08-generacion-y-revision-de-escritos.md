# J08 — Generación y revisión de escritos

Módulo: `procedimientos/j08_escritos.py` (envuelve el generador de `documentos.py`) · Ruta:
`POST /api/procedimientos/verificar-escrito` · Versión 1.0.0 · Estado: verificador PROBADO; `preparar()`
IMPLEMENTADO y probado como función, **aún no conectado** a `/api/documentos/generar`.

## Dos piezas deterministas

### 1. `preparar(entrada)` — antes de generar

Exige:

- `tipo`: un modelo seleccionado del catálogo (use J02 para encontrarlo);
- `campos`: datos válidos según el formulario del tipo;
- `hechos_confirmados: true`: confirmación expresa del usuario;
- `fuentes`: lista de fuentes aplicables, o `sin_fuentes: true` para un borrador que no cite normas ni sentencias
  con número.

Si falta algo → `ABSTENCION`. Si todo está → `LISTO`, con el pedido para el generador, los anexos requeridos, los
campos opcionales sin diligenciar y las reglas de generación. No llama al modelo.

### 2. `verificar_escrito(texto, entradas, fuentes, tipo_id)` — después de generar

Busca en el borrador datos que **no estaban** en las entradas del usuario ni en las fuentes:

| Categoría | Qué reconoce | Se compara contra |
|---|---|---|
| `sentencia` | C-, T-, SU- y radicados de la Corte Suprema (SL, SC, SP, STC…) | fuentes y notas del modelo |
| `norma` | Ley, Decreto, Resolución, Acuerdo o Circular con número y año | fuentes y notas del modelo |
| `articulo` | «artículo 86», «arts. 13 y 29» | fuentes y notas del modelo |
| `radicado` | 23 dígitos o lo que sigue a «radicado», «expediente» | entradas y fuentes |
| `identificacion` | C.C., NIT, T.I., C.E., T.P. con número | entradas y fuentes |
| `fecha` | «3 de marzo de 2026», 03/03/2026, 2026-03-03 | entradas, fuentes y la fecha de hoy |
| `valor` | importes con signo $ | números de las entradas y fuentes |
| `contacto` | correos y celulares | entradas y fuentes |
| `nombre` | dos o más palabras con mayúscula inicial que no son vocabulario jurídico | palabras de las entradas y fuentes |

También reúne los pendientes: el bloque `<<<VERIFICAR>>>` y cada `[COMPLETAR: …]`. Una fecha que no existe en el
calendario se marca aunque estuviera en las entradas.

Por HTTP admite `documento_id`: revisa un documento guardado del propio usuario contra los datos de su formulario
y sus fuentes (404 si el documento es de otra persona).

## Salida del verificador

`estado` (`POSIBLES_INVENCIONES`, `PENDIENTES`, `SIN_HALLAZGOS`, `ABSTENCION`), `posibles_invenciones` (categoría,
valor, motivo, confianza y contexto), `por_categoria`, `pendientes`, `citas_respaldadas`, `advertencias`,
`limites` y `juicio_profesional`.

## Límites

- Trabaja por patrones: «posible» no significa falso, y un dato inventado con otra redacción puede no detectarse.
  No se ha medido su precisión ni su cobertura con borradores reales del modelo.
- Que una cita esté en las fuentes no prueba que la fuente diga lo que el borrador le atribuye.
- Los nombres se comparan palabra por palabra; no se valida que correspondan a la misma persona.
- No inventa ni corrige: solo señala. Presentar el escrito es decisión del profesional.

## Pseudocódigo

```
preparar:
    faltan = modelo, campos válidos, hechos confirmados, fuentes (o sin_fuentes)
    si faltan → ABSTENCION ; si no → LISTO + pedido + anexos + reglas de generación

verificar_escrito:
    cuerpo, pendientes = separar el bloque <<<VERIFICAR>>> y los [COMPLETAR: …]
    base_datos = entradas + fuentes ; base_citas = base_datos + notas del modelo elegido
    para cada categoría: extraer del cuerpo ; normalizar ; si no está en la base → posible invención
    estado = POSIBLES_INVENCIONES | PENDIENTES | SIN_HALLAZGOS
```

## Pruebas

`tests/test_procedimientos_otros.py` y `tests/test_procedimientos_rutas.py`: borrador limpio (solo pendientes);
borrador con diez datos inventados (nombre, radicado, fechas, sentencia, norma, artículo, valor, correo, celular,
NIT) y lo que sí estaba no se marca; las fuentes respaldan citas; la fecha de hoy no es invención; requisitos de
`preparar`; revisión de un documento guardado y aislamiento entre usuarios.

## Pendiente con dependencia concreta

Conectar `preparar()` y el verificador al flujo de `/api/documentos/generar` y mostrar los hallazgos en la vista
Documentos. Depende de coordinar el cambio en `app.py` y `static/documentos.js` con quien mantiene el automatizador.
