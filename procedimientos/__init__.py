"""PULLEX IA — Procedimientos jurídicos J01–J09 (docs/procedimientos/).

Cada módulo separa lo DETERMINISTA (cálculo y validación, reproducible y sin modelo de IA) de lo que requiere
JUICIO PROFESIONAL (lo señala en la salida y no lo decide). Las reglas jurídicas viven en reglas/registro.json
y se consultan siempre a una fecha (reglas.py).

Estados (docs/coordinacion/ESPECIFICACION-LEXCOL.md): PROPUESTO → CONFIGURADO → IMPLEMENTADO → PROBADO → OPERATIVO.
«PROBADO» significa pruebas automáticas y evaluación propias; ninguno está OPERATIVO: falta revisión de un
profesional del derecho y uso real.
"""

CATALOGO = [
    {"id": "J01", "nombre": "Clasificación y orientación del asunto", "modulo": "j01_clasificacion",
     "determinista": "reglas de palabras clave, datos faltantes y preguntas",
     "juicio_profesional": "competencia, procedencia y elección de la vía", "estado": "PROBADO"},
    {"id": "J02", "nombre": "Recuperación de modelos", "modulo": "j02_modelos",
     "determinista": "búsqueda en el catálogo, razones y requisitos",
     "juicio_profesional": "si el modelo procede jurídicamente para el caso", "estado": "PROBADO"},
    {"id": "J03", "nombre": "Verificación normativa temporal", "modulo": "j03_vigencia",
     "determinista": "regla del registro aplicable a la fecha de los hechos",
     "juicio_profesional": "transición, retroactividad y normas no registradas", "estado": "PROBADO"},
    {"id": "J04", "nombre": "Análisis jurisprudencial", "modulo": "j04_jurisprudencia",
     "determinista": "estructura de la ficha y validaciones de alcance",
     "juicio_profesional": "ratio decidendi, analogía con el caso y fuerza del precedente", "estado": "PROBADO"},
    {"id": "J05", "nombre": "Cómputo de términos", "modulo": "j05_terminos",
     "determinista": "calendario, festivos por regla y conteo día por día",
     "juicio_profesional": "fecha en que se surtió la notificación, suspensiones y vacancia del despacho",
     "estado": "PROBADO"},
    {"id": "J06", "nombre": "Liquidaciones", "modulo": "j06_liquidaciones",
     "determinista": "fórmulas versionadas con aritmética decimal",
     "juicio_profesional": "qué es salario, tasas e índices aplicables y método de intereses", "estado": "PROBADO"},
    {"id": "J07", "nombre": "Matriz probatoria", "modulo": "j07_matriz_probatoria",
     "determinista": "relación hecho–elemento, vacíos y contradicciones declaradas",
     "juicio_profesional": "valor probatorio, pertinencia y conducencia", "estado": "PROBADO"},
    {"id": "J08", "nombre": "Generación y revisión de escritos", "modulo": "j08_escritos",
     "determinista": "requisitos previos y detector de datos que no estaban en las entradas",
     "juicio_profesional": "contenido jurídico del escrito y decisión de presentarlo", "estado": "PROBADO"},
    {"id": "J09", "nombre": "Actualización e impacto", "modulo": "j09_impacto",
     "determinista": "reglas, tipos de documento y perfiles que mencionan la norma cambiada",
     "juicio_profesional": "alcance real del cambio y texto de la nueva versión", "estado": "PROBADO"},
]


def catalogo() -> list:
    return [dict(p) for p in CATALOGO]
