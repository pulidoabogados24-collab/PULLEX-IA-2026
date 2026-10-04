# J07 — Matriz probatoria

Módulo: `procedimientos/j07_matriz_probatoria.py` · Ruta: `POST /api/procedimientos/matriz-probatoria` ·
Versión 1.0.0 · Estado: PROBADO sobre la estructura que recibe; no lee documentos.

## Entradas

- `hechos`: lista de `{id, texto, fecha}` (o solo el texto; el identificador se asigna: H1, H2…).
- `elementos`: lista de `{id, tipo, descripcion, aportado, hechos, sentido, directo}`.
  - `tipo` documental: documento, contrato, certificado, acto_administrativo, providencia, comunicacion, factura,
    historia_clinica, registro_civil, escritura, titulo_valor. No documental: testimonio, declaracion_de_parte,
    dictamen_pericial, inspeccion, fotografia, audio_video, mensaje_de_datos, indicio, otro.
  - `aportado`: `true` si el usuario lo entregó; `false` si solo lo menciona. Obligatorio.
  - `sentido`: `apoya` (por defecto) o `contradice`. `directo`: `false` si solo respalda el hecho indirectamente.
- `pretensiones`: lista de `{id, texto, hechos}`.
- `propuestas_modelo`: sugerencias de un modelo de IA; se guardan aparte.

## Reglas

| Nivel | Condición |
|---|---|
| `ACREDITADO_POR_DOCUMENTO` | Al menos un elemento documental, aportado y directo apoya el hecho |
| `INDICIO` | Hay elementos que lo apoyan, pero no aportados, no documentales o indirectos |
| `AFIRMACION_DEL_USUARIO` | Ningún elemento lo respalda |

Además: un hecho con algún elemento en sentido `contradice` queda `controvertido`, aunque esté acreditado.
No hay reglas jurídicas del registro en este procedimiento: es una clasificación operativa, no una tarifa legal.

## Salida

`matriz` (hecho, nivel, razón, elementos que apoyan y contradicen), `pretensiones` (hechos sin acreditar o
controvertidos), `vacios`, `contradicciones_probatorias`, `elementos_sin_hecho`, `necesidades_de_verificacion`,
`conteo` por nivel y `propuestas` (cada una `PROPUESTA_NO_VERIFICADA`).

## Excepciones

Sin hechos → `ABSTENCION`. Elemento con tipo desconocido, sin `aportado`, o que remite a un hecho inexistente;
identificadores repetidos; pretensión que remite a un hecho inexistente → `CONTRADICCION` (la matriz se entrega
con lo válido y la lista de problemas).

## Límites

«Acreditado por documento» solo dice que hay un documento aportado que respalda el hecho. No valora
autenticidad, pertinencia, conducencia ni suficiencia, ni define la carga de la prueba. La matriz no lee los
documentos: usa la relación hecho–elemento que recibe. Las propuestas del modelo no cambian ningún nivel.

## Pseudocódigo

```
para cada elemento válido: anotarlo en cada hecho que cita, como «apoya» o «contradice»
para cada hecho:
    si hay apoyo documental + aportado + directo → ACREDITADO_POR_DOCUMENTO
    si hay otro apoyo                            → INDICIO (con el motivo)
    si no                                        → AFIRMACION_DEL_USUARIO (vacío)
    si algún elemento contradice                 → controvertido + contradicción probatoria
para cada pretensión: listar sus hechos no acreditados o controvertidos
```

## Pruebas

`tests/test_procedimientos_otros.py`: los tres niveles; documento no aportado y testimonio aportado no acreditan;
contradicción probatoria; pretensión sin hechos; entradas incoherentes; la propuesta del modelo no altera la matriz.
