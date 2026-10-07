# J01 — Clasificación y orientación del asunto

Módulo: `procedimientos/j01_clasificacion.py` · Ruta: `POST /api/procedimientos/clasificar` · Versión 1.0.0 ·
Estado: PROBADO (reglas de palabras; sin validación con casos reales).

## Entradas

`hechos` (texto), `pretension`, `fechas` (lista o mapa), `sujetos` (lista), `documentos` (lista), `lugar`, `cuantia`.
Solo `hechos` es indispensable; con menos de 40 caracteres responde `INSUFICIENTE`.

## Reglas

- 16 materias (`MATERIAS`), cada una con palabras o frases y su peso, un área del registro de perfiles
  (`A06-S02`, `A09-S01`…) y entre dos y seis rutas candidatas, que son tipos del catálogo de `documentos.py`.
- Coincidencia por palabras completas y sin tildes («prima» no coincide con «primavera»); una materia se propone
  con puntaje de 2 o más.
- `VERIFICAR_RUTA`: preguntas que deben resolverse antes de elegir cada ruta (subsidiariedad, caducidad,
  requisitos de procedibilidad…). Son preguntas, no afirmaciones de procedencia.
- Normas citadas solo desde el registro: R-CONST-0001, R-CONST-0002, R-PET-0001 y R-PLAZO-0001.

## Excepciones

- Hechos muy breves → `INSUFICIENTE`, con las preguntas necesarias.
- Ninguna materia alcanza el umbral → `SIN_COINCIDENCIAS`, sin rutas.
- Dos materias con puntajes a un punto de distancia → `AMBIGUO`: se muestran ambas.
- Palabras de urgencia (privación de la libertad, riesgo para la vida, violencia, plazo corriendo) → `alertas`.

## Salida

`estado`, `materias_posibles` (con puntaje y coincidencias), `rutas_candidatas` (tipo del catálogo, por qué y qué
verificar), `datos_faltantes`, `preguntas_necesarias`, `alertas`, `normas`, `limites`, `juicio_profesional` y
`propuesta_modelo`.

## Límites

No afirma competencia, procedencia ni vía definitiva. Es una hipótesis basada en palabras: hechos descritos de
otra forma pueden quedar sin clasificar o mal clasificados. La precisión no se ha medido con casos reales.

## Apoyo del modelo (opcional)

`clasificar(entrada, apoyo_modelo=funcion)` adjunta la salida de la función en `propuesta_modelo` con estado
`PROPUESTA_NO_VERIFICADA`. No cambia materias ni rutas, y si la función falla la clasificación sigue igual.
La ruta HTTP no lo usa (no gasta consultas). `instruccion_apoyo()` da el texto para pedirle la segunda lectura.

## Pseudocódigo

```
texto = normalizar(hechos + pretensión + sujetos + documentos)
para cada materia: puntaje = suma de pesos de las claves presentes ; conservar si puntaje ≥ 2
ordenar por puntaje ; rutas = tipos del catálogo de las cuatro primeras materias, con sus preguntas
datos_faltantes = hechos, pretensión, fechas, sujetos, lugar, cuantía, documentos que no vinieron
alertas = palabras de urgencia presentes
estado = INSUFICIENTE | SIN_COINCIDENCIAS | AMBIGUO | CLASIFICADO
si hay apoyo_modelo: adjuntar su salida como propuesta, sin tocar lo anterior
```

## Pruebas

`tests/test_procedimientos_otros.py`: clasificación con razones y rutas existentes en el catálogo real; siete
materias por palabras completas; insuficiente, ambiguo y sin coincidencias; alertas; el apoyo del modelo no altera
el resultado ni lo tumba si falla. No hay conjunto de evaluación con casos reales: es el pendiente principal.
