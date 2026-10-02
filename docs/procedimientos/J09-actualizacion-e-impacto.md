# J09 — Actualización e impacto

Módulo: `procedimientos/j09_impacto.py` · Ruta: `POST /api/procedimientos/impacto` (solo administración) ·
Versión 1.0.0 · Estado: PROBADO. Nunca aplica cambios.

## Entradas

| Campo | Obligatorio | Descripción |
|---|---|---|
| `tipo` | sí | `norma`, `sentencia` o `documento` |
| `identificador` | sí | «Ley 2578 de 2026», «C-123 de 2026»… |
| `articulo` | no | Para acotar la búsqueda en el registro |
| `descripcion` | no | Qué cambió |
| `enlace` | sí | Fuente donde se comprobó; oficial si es norma o sentencia |
| `fecha_consulta` | sí | Cuándo se consultó |
| `fecha_efecto` | sí | Desde cuándo rige o produce efectos |
| `comprobado` | sí | `true`: una persona comprobó el cambio en la fuente |

## Reglas

- Sin `comprobado: true`, enlace (oficial para norma o sentencia) y fechas → `ABSTENCION`: no hay impacto ni
  propuesta sobre un cambio sin comprobar.
- Reglas afectadas: las que se apoyan en la norma (soporte principal o adicional, con artículo si se indicó) y
  las que la nombran en su enunciado o notas. Se indica cuál es la versión vigente en la fecha de efecto.
- Tipos de documento y flujos afectados: los del catálogo de `documentos.py` que nombran la norma en notas de
  forma, advertencias, estructura o descripción. La norma se busca con sus formas usuales («Ley 1564 de 2012» y
  «Código General del Proceso»).
- Perfiles afectados: subespecialidades ligadas a la materia de cada regla y al área de cada tipo de documento,
  en las funciones F04, F08 y F09. Son identificadores `Axx-Syy-Fzz` por construcción; el registro de perfiles lo
  mantiene otro componente y no se consulta.

## Salida

`estado`, `aplicado: false`, `reglas_afectadas`, `tipos_de_documento_afectados`, `flujos_afectados`,
`perfiles_afectados`, `propuesta`, `advertencias`, `limite` y `juicio_profesional`.

Propuesta versionada, por cada regla vigente afectada: cerrar la versión actual el día anterior a la fecha de
efecto y crear la siguiente con `estado = REVISIÓN_HUMANA_PENDIENTE`, el enlace y la fecha de consulta, y el
enunciado por redactar. Por cada tipo de documento: revisar las partes donde aparece la norma y publicar una
revisión del catálogo. Si la norma no está en el registro: valorar una regla nueva.

## Límites

- **No modifica nada en silencio**: no escribe en `reglas/registro.json`, ni en el catálogo, ni en los documentos
  guardados de los usuarios. Los borradores ya generados conservan su texto; se sugiere mostrar un aviso al
  abrirlos.
- La búsqueda es textual: un efecto indirecto (una regla que depende de la norma sin nombrarla) no aparece.
- No cuenta ni lee documentos de usuarios.
- El alcance real del cambio y el texto de la nueva versión son juicio profesional.

## Pseudocódigo

```
validar ; si el cambio no está comprobado → ABSTENCION
claves = formas de escribir la norma
reglas    = buscar_por_norma(identificador, artículo) ∪ reglas cuyo texto contiene una clave
tipos     = tipos del catálogo cuyo texto contiene una clave ; flujos igual
perfiles  = subespecialidades de las materias y áreas halladas × {F04, F08, F09}
propuesta = por regla vigente: cerrar versión N, crear N+1 pendiente de revisión
            por tipo: revisar y publicar revisión ; documentos de usuarios: no se tocan
devolver con aplicado = false
```

## Pruebas

`tests/test_procedimientos_otros.py` y `tests/test_procedimientos_rutas.py`: impacto de un cambio en la Ley 1755
de 2015 (reglas, tipos, perfiles y propuesta de versión 4); los archivos del registro y del catálogo tienen la
misma huella antes y después; abstención sin comprobación; norma ausente del registro; búsqueda por código;
la ruta responde 403 a quien no es administrador.

## Pendiente con dependencia concreta

Cruzar con el registro real de 1.000 perfiles y con el índice de la biblioteca cuando existan, y definir el aviso
a usuarios en la vista Documentos.
