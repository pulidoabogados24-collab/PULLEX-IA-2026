# Prompts de PULLEX IA

Estado: borrador de PUL-018. **Ningún prompt de esta carpeta se ha probado contra el modelo real** (no hay clave de
API en el entorno donde se escribieron). Se probó que se cargan y se ensamblan (`tests/test_prompts_calidad.py`),
no que mejoren las respuestas.

## Qué hay

| Archivo | Qué es | Quién lo carga |
|---|---|---|
| `calidad_respuesta.md` | Bloque de calidad de respuesta: contrato de respuesta, intención, cobertura, profundidad, seguimientos, no inventar lo jurídico, incertidumbre y cómo continuar | `prompts_calidad.cargar_bloque()` |
| `PROMPT-MAESTRO-PULLEX.md` | Prompt maestro integrado: identidad, el bloque anterior, modos, verbos, análisis de casos, voces, reglas jurídicas y límites | `prompts_calidad.cargar_maestro({...})` |

Reglas de formato de cada archivo:
- Metadato en comentarios HTML al principio: `<!-- version: X.Y.Z | fecha: AAAA-MM-DD | estado: … -->`.
- El texto que se carga va entre `<!-- INICIO -->` y `<!-- FIN -->`; lo que está fuera no llega al modelo.
- En el prompt maestro, `{{CALIDAD_RESPUESTA}}`, `{{GUIA_ESCRITURA}}`, `{{VOZ_ESTUDIANTE}}`, `{{VOZ_ABOGADO}}` y
  `{{VOZ_CIUDADANO}}` se sustituyen al cargar. Las cuatro últimas son las constantes de `estilo_redaccion.py`, para
  no copiar texto que ya existe y que se desfasaría. Si falta un valor, `cargar_maestro` lanza `ErrorPrompt`:
  es mejor no arrancar que enviar un marcador sin resolver al modelo.

## Cómo lo usa el backend

```python
import prompts_calidad as pc
import estilo_redaccion as redaccion

maestro = pc.cargar_maestro({
    "GUIA_ESCRITURA": redaccion.GUIA_ESCRITURA,
    "VOZ_ESTUDIANTE": redaccion.VOZ_ESTUDIANTE,
    "VOZ_ABOGADO": redaccion.VOZ_ABOGADO,
    "VOZ_CIUDADANO": redaccion.VOZ_CIUDADANO,
})
```

Dos formas de integrarlo, a decidir por quien toque `app.py` (PUL-017):
1. **Mínima:** dejar el `SYSTEM_PROMPT` actual y añadir `pc.cargar_bloque()` justo después de la presentación.
   El texto es fijo, así que sigue siendo cacheable (`cache_control`) como el resto del bloque estático.
2. **Completa:** reemplazar el `SYSTEM_PROMPT` por `cargar_maestro(...)`. El maestro conserva las reglas jurídicas y
   los límites del actual; si hay diferencias de fondo, vale el actual hasta que un abogado revise el maestro.

Lo que cambia por consulta (fecha, nombre, memoria, fragmentos del corpus, modo elegido) va en el bloque dinámico
sin caché, como hoy. Los modos RÁPIDO, ESTÁNDAR, PROFUNDO, etc. del maestro son criterio del modelo; la decisión
dura de presupuesto de tokens y de modelo es del enrutador del backend, no del prompt.

## Cómo se versiona

- Versión semántica en el metadato: **patch** para corregir una errata o precisar una frase sin cambiar la conducta;
  **minor** para añadir una regla o un modo; **major** para cambiar una prioridad o quitar una regla.
- Todo cambio de conducta (minor o major) se acompaña de: la nota en este README (tabla de abajo), una corrida de
  `python evaluacion/evaluar_calidad.py` sobre respuestas guardadas y, cuando haya clave, una corrida contra el
  modelo con el conjunto `evaluacion/calidad_respuesta.jsonl`. Sin la corrida real, el cambio queda como
  «NOT VERIFIED» en la nota.
- Los archivos se versionan en git; no hay copias con fecha en el nombre.

| Versión | Fecha | Cambio | Medido contra el modelo real |
|---|---|---|---|
| 1.0.0 | 2026-10-04 | Primera redacción del bloque y del maestro a partir de la especificación del dueño (`docs/coordinacion/ESPECIFICACION-MOTOR-RESPUESTAS.md`) y de `docs/17-CALIDAD-DE-RESPUESTA.md` | No |

## Qué prueba y qué no

`tests/test_prompts_calidad.py` comprueba formato (marcadores, versión, cuerpo no vacío), que el bloque menciona
cada obligación clave y que no contiene emojis ni nombres de universidades. No comprueba que el modelo obedezca.

## Qué falta

- Medir antes y después con el modelo real y el conjunto de evaluación (PUL-008 lo bloquea hasta que haya clave).
- Que un abogado revise las reglas jurídicas del maestro.
- Medir cuántos tokens agrega el bloque (hoy son unas 1.200 palabras; no se midió el costo).
