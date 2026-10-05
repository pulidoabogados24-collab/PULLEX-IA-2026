"""J03 — Verificación normativa temporal.

Dada una disposición, la fecha de los hechos y la fecha del análisis, devuelve la regla del registro aplicable
A LA FECHA DE LOS HECHOS (no la más reciente) y la vigente a la fecha del análisis, y dice si entre las dos hubo
un cambio registrado. Si la disposición no está en el registro, o el inicio de su vigencia no está comprobado,
responde «vigencia pendiente de comprobar» con la lista de qué verificar y dónde.

No abre la red ni consulta al modelo: solo razona sobre reglas/registro.json. La transición entre normas y la
retroactividad quedan señaladas como juicio profesional.
"""
from datetime import date

import reglas

VERSION = "1.0.0"
PROCEDIMIENTO = "J03"
PENDIENTE = "VIGENCIA_PENDIENTE_DE_COMPROBAR"

DONDE = [
    {"fuente": "SUIN-Juriscol (Ministerio de Justicia)", "enlace": "https://www.suin-juriscol.gov.co/",
     "para": "texto original, modificaciones y derogatorias con sus fechas"},
    {"fuente": "Secretaría del Senado", "enlace": "http://www.secretariasenado.gov.co/senado/basedoc/",
     "para": "texto vigente con notas de vigencia y sentencias de constitucionalidad"},
    {"fuente": "Corte Constitucional — Relatoría", "enlace": "https://www.corteconstitucional.gov.co/relatoria/",
     "para": "sentencias que declararon la norma exequible, inexequible o condicionada, y desde cuándo"},
    {"fuente": "Gestor Normativo de Función Pública", "enlace": "https://www.funcionpublica.gov.co/eva/gestornormativo/",
     "para": "normas anteriores a 1992 y conceptos"},
    {"fuente": "Diario Oficial (Imprenta Nacional)", "enlace": "https://www.imprenta.gov.co/",
     "para": "fecha exacta de publicación (promulgación)"},
]
QUE_VERIFICAR = [
    "Texto de la disposición tal como estaba el día de los hechos.",
    "Modificaciones, sustituciones o adiciones posteriores y la fecha desde la que rigen.",
    "Derogatorias expresas o tácitas.",
    "Sentencias de constitucionalidad o de nulidad sobre la disposición y sus efectos en el tiempo.",
    "Régimen de transición: qué norma rige las situaciones iniciadas antes del cambio.",
]


def _estado_version(regla, f: date) -> dict:
    if regla is None:
        return None
    c = reglas.vigencia_comprobada(regla, f)
    d = reglas.referencia(regla)
    d.update(enunciado=regla["enunciado"], vigencia=regla["vigencia"], cita=regla.get("cita", ""),
             vigencia_comprobada_a_la_fecha=c["comprobada"], motivo=c["motivo"], detalle=c["detalle"],
             notas=regla.get("notas", ""))
    return d


def verificar(disposicion: str, fecha_hechos, fecha_analisis=None) -> dict:
    faltantes, contradicciones = [], []
    disposicion = str(disposicion or "").strip()[:300]
    if not disposicion:
        faltantes.append("disposicion (por ejemplo «Ley 1755 de 2015, art. 14»)")
    fh = fa = None
    if fecha_hechos in (None, ""):
        faltantes.append("fecha_hechos")
    else:
        try:
            fh = reglas.a_fecha(fecha_hechos)
        except (ValueError, TypeError):
            contradicciones.append(f"La fecha de los hechos {fecha_hechos!r} no existe o no es AAAA-MM-DD.")
    try:
        fa = reglas.a_fecha(fecha_analisis) if fecha_analisis not in (None, "") else date.today()
    except (ValueError, TypeError):
        contradicciones.append(f"La fecha de análisis {fecha_analisis!r} no existe o no es AAAA-MM-DD.")
    if fh and fa and fa < fh:
        contradicciones.append("La fecha de análisis es anterior a la de los hechos.")
    base = {"procedimiento": PROCEDIMIENTO, "version": VERSION, "disposicion": disposicion,
            "fecha_hechos": fh.isoformat() if fh else None, "fecha_analisis": fa.isoformat() if fa else None,
            "reglas": [], "por_verificar": [], "donde_verificar": [], "advertencias": [],
            "limite": "La norma más reciente no es automáticamente la aplicable a hechos anteriores.",
            "juicio_profesional": ["Determinar si la situación se rige por la norma vigente al momento de los "
                                   "hechos o por una posterior (transición, retroactividad, favorabilidad)."]}
    if contradicciones:
        return {**base, "estado": "CONTRADICCION", "contradicciones": contradicciones, "faltantes": faltantes}
    if faltantes:
        return {**base, "estado": "ABSTENCION", "faltantes": faltantes}

    encontradas = reglas.buscar_por_norma(disposicion)
    ids = []
    for r in encontradas:
        if r["id"] not in ids:
            ids.append(r["id"])
    if not ids:
        return {**base, "estado": PENDIENTE, "por_verificar": QUE_VERIFICAR, "donde_verificar": DONDE,
                "advertencias": ["La disposición no está en el registro de reglas: el sistema no puede afirmar "
                                 "su vigencia ni su contenido. No se asume que el texto actual aplique a la "
                                 "fecha de los hechos."]}
    salida, hubo_cambio, todo_comprobado = [], False, True
    for rid in ids:
        vh, va = reglas.vigente(rid, fh), reglas.vigente(rid, fa)
        cambio = (vh["version"] if vh else None) != (va["version"] if va else None)
        hubo_cambio = hubo_cambio or cambio
        eh, ea = _estado_version(vh, fh), _estado_version(va, fa)
        if not eh or not eh["vigencia_comprobada_a_la_fecha"]:
            todo_comprobado = False
        salida.append({"id": rid, "aplicable_a_la_fecha_de_los_hechos": eh, "vigente_a_la_fecha_del_analisis": ea,
                       "cambio_entre_las_dos_fechas": cambio,
                       "versiones_registradas": [{"version": v["version"], "desde": v["vigencia"]["desde"],
                                                  "hasta": v["vigencia"]["hasta"], "estado": v["estado"],
                                                  "norma": reglas.referencia(v)["norma"]}
                                                 for v in reglas.versiones(rid)]})
    base["reglas"] = salida
    if hubo_cambio:
        base["advertencias"].append("Entre la fecha de los hechos y la del análisis cambió al menos una regla "
                                    "registrada: se muestra la versión aplicable a los hechos, no la última.")
    if todo_comprobado:
        estado = "REGLA_APLICABLE_COMPROBADA"
    else:
        estado = PENDIENTE
        base["por_verificar"] = QUE_VERIFICAR
        base["donde_verificar"] = DONDE
        base["advertencias"].append("Para al menos una regla no está comprobado que rigiera en la fecha de los "
                                    "hechos (ver «motivo» y «detalle» de cada una).")
    base["advertencias"].append("El registro solo conoce las reglas y versiones que tiene cargadas: puede haber "
                                "modificaciones no registradas.")
    return {**base, "estado": estado}
