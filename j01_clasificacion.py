"""J01 — Clasificación y orientación del asunto.

De los hechos, la pretensión, las fechas y los sujetos saca: materias POSIBLES (con las palabras que lo
sustentan), datos que faltan, rutas CANDIDATAS (con el tipo de escrito del catálogo, si existe) y las preguntas
necesarias. Es determinista: reglas de palabras clave, sin modelo de IA.

Límite: no afirma competencia, procedencia ni vía definitiva. Cada ruta lleva lo que hay que verificar antes de
elegirla. Opcionalmente recibe una función de apoyo (`apoyo_modelo`) cuya salida se adjunta SOLO como propuesta
no verificada: nunca cambia la clasificación determinista.
"""
import re
import unicodedata
from datetime import date

import documentos
import reglas

VERSION = "1.0.0"
PROCEDIMIENTO = "J01"
MAX_TEXTO = 20000
UMBRAL = 2          # puntaje mínimo para proponer una materia

# Cada materia: palabras o frases (sin tildes) con su peso, área del registro de perfiles y rutas candidatas.
MATERIAS = [
    {"id": "tutela", "nombre": "Constitucional: derechos fundamentales y tutela", "area_perfiles": "A07-S01",
     "claves": {"tutela": 3, "derecho fundamental": 3, "derechos fundamentales": 3, "eps": 2, "medicamento": 2,
                "salud": 1, "cirugia": 2, "tratamiento": 1, "vida digna": 2, "minimo vital": 3, "debido proceso": 2,
                "habeas corpus": 3, "desacato": 3, "no me responden": 1},
     "rutas": ["tutela", "tutela_salud", "tutela_peticion", "desacato"]},
    {"id": "peticion", "nombre": "Derecho de petición", "area_perfiles": "A10-S06",
     "claves": {"derecho de peticion": 3, "peticion": 2, "solicite informacion": 2, "no me han respondido": 2,
                "no respondieron": 2, "copia de documentos": 2, "radique": 1, "solicitud": 1, "consulta a la entidad": 2},
     "rutas": ["peticion_general", "peticion_informacion", "tutela_peticion"]},
    {"id": "laboral", "nombre": "Laboral: contrato, salarios, prestaciones y terminación", "area_perfiles": "A09-S01",
     "claves": {"despido": 3, "despidieron": 3, "me echaron": 3, "liquidacion": 2, "prestaciones": 2, "cesantias": 3,
                "prima": 2, "vacaciones": 1, "salario": 2, "empleador": 2, "contrato de trabajo": 3, "renuncia": 2,
                "horas extras": 2, "acoso laboral": 3, "jefe": 1, "trabaje": 1, "indemnizacion por despido": 3,
                "prestacion de servicios": 2, "subordinacion": 2},
     "rutas": ["reclamacion_laboral", "demanda_laboral", "conciliacion_laboral", "queja_acoso_laboral"]},
    {"id": "seguridad_social", "nombre": "Seguridad social: pensiones, salud y riesgos laborales",
     "area_perfiles": "A09-S07",
     "claves": {"pension": 3, "colpensiones": 3, "fondo de pensiones": 3, "semanas cotizadas": 3, "invalidez": 2,
                "perdida de capacidad laboral": 3, "arl": 3, "incapacidad": 2, "sobrevivientes": 2,
                "accidente de trabajo": 3, "historia laboral": 2},
     "rutas": ["solicitud_pension", "reclamacion_administrativa_laboral", "calificacion_pcl"]},
    {"id": "civil_obligaciones", "nombre": "Civil y comercial: contratos, deudas y títulos", "area_perfiles": "A06-S02",
     "claves": {"pagare": 3, "letra de cambio": 3, "deuda": 2, "me deben": 2, "no me paga": 2, "prestamo": 2,
                "cobrar": 2, "incumplimiento": 2, "contrato": 1, "arrendamiento": 2, "arrendatario": 2, "canon": 2,
                "compraventa": 2, "factura": 2, "cheque": 2, "promesa de compraventa": 3, "desalojo": 2},
     "rutas": ["carta_cobro", "demanda_ejecutiva", "demanda_monitorio", "restitucion_inmueble", "resolucion_contrato"]},
    {"id": "responsabilidad", "nombre": "Responsabilidad civil y daños", "area_perfiles": "A06-S03",
     "claves": {"accidente de transito": 3, "choque": 2, "atropello": 3, "lesiones": 1, "danos": 2, "perjuicios": 2,
                "indemnizacion": 1, "negligencia medica": 3, "aseguradora": 2, "poliza": 2, "soat": 2},
     "rutas": ["responsabilidad_extracontractual", "conciliacion_prejudicial"]},
    {"id": "familia", "nombre": "Familia y sucesiones", "area_perfiles": "A06-S04",
     "claves": {"alimentos": 3, "cuota alimentaria": 3, "custodia": 3, "visitas": 2, "divorcio": 3, "separacion": 2,
                "union marital": 3, "hijo": 1, "hija": 1, "menor de edad": 2, "paternidad": 3, "herencia": 3,
                "sucesion": 3, "testamento": 2, "violencia intrafamiliar": 3, "sociedad conyugal": 3,
                "comisaria de familia": 2},
     "rutas": ["demanda_alimentos", "custodia", "divorcio_mutuo_acuerdo", "divorcio_contencioso", "sucesion",
               "violencia_intrafamiliar"]},
    {"id": "comercial_societario", "nombre": "Comercial y societario", "area_perfiles": "A06-S07",
     "claves": {"sociedad": 2, "sas": 2, "socio": 2, "accionista": 3, "asamblea": 2, "junta directiva": 2,
                "estatutos": 3, "representante legal": 2, "camara de comercio": 2, "acciones": 1, "dividendos": 2},
     "rutas": ["estatutos_sas", "acta_asamblea", "impugnacion_asamblea", "derecho_inspeccion"]},
    {"id": "consumidor", "nombre": "Consumidor y habeas data", "area_perfiles": "A06-S08",
     "claves": {"garantia": 2, "producto defectuoso": 3, "devolucion del dinero": 2, "retracto": 3, "compre": 1,
                "superintendencia de industria": 2, "sic": 1, "datacredito": 3, "reporte negativo": 3,
                "central de riesgo": 3, "servicios publicos": 2, "factura de energia": 2, "operador": 1},
     "rutas": ["reclamacion_garantia", "retracto", "demanda_consumidor", "reclamo_habeas_data_financiero",
               "reclamacion_servicios_publicos"]},
    {"id": "penal", "nombre": "Penal y procesal penal", "area_perfiles": "A08-S02",
     "claves": {"denuncia": 3, "delito": 3, "hurto": 3, "robo": 3, "robaron": 3, "estafa": 3, "estafaron": 3,
                "amenaza": 2, "amenazas": 2, "lesiones personales": 3, "fiscalia": 3, "capturado": 3, "captura": 3,
                "detenido": 3, "imputacion": 3, "carcel": 2, "medida de aseguramiento": 3, "victima": 1,
                "violencia sexual": 3, "homicidio": 3, "extorsion": 3},
     "rutas": ["denuncia_penal", "querella", "habeas_corpus", "incidente_reparacion"]},
    {"id": "administrativo", "nombre": "Administrativo y contratación estatal", "area_perfiles": "A07-S02",
     "claves": {"acto administrativo": 3, "resolucion": 2, "sancion": 2, "multa": 2, "alcaldia": 2, "gobernacion": 2,
                "ministerio": 2, "entidad publica": 2, "recurso de reposicion": 2, "recurso de apelacion": 1,
                "nulidad": 2, "reparacion directa": 3, "licitacion": 3, "contrato estatal": 3, "secop": 3,
                "funcionario": 1, "insubsistencia": 3},
     "rutas": ["recurso_administrativo", "revocatoria_directa", "nulidad_restablecimiento", "reparacion_directa",
               "conciliacion_prejudicial"]},
    {"id": "disciplinario", "nombre": "Disciplinario", "area_perfiles": "A07-S04",
     "claves": {"disciplinario": 3, "procuraduria": 3, "personeria": 2, "pliego de cargos": 3, "falta disciplinaria": 3,
                "control interno disciplinario": 3, "queja contra abogado": 3},
     "rutas": ["queja_disciplinaria", "descargos_disciplinarios", "recurso_disciplinario"]},
    {"id": "tributario", "nombre": "Tributario", "area_perfiles": "A07-S06",
     "claves": {"dian": 3, "impuesto": 2, "impuestos": 2, "declaracion de renta": 3, "requerimiento especial": 3,
                "cobro coactivo": 3, "predial": 2, "iva": 2, "retencion en la fuente": 3, "liquidacion oficial": 3},
     "rutas": ["respuesta_requerimiento", "recurso_reconsideracion", "excepciones_cobro_coactivo", "facilidad_pago"]},
    {"id": "policivo_transito", "nombre": "Policivo y tránsito", "area_perfiles": "A07-S02",
     "claves": {"comparendo": 3, "fotomulta": 3, "transito": 2, "inspector de policia": 3, "codigo de policia": 3,
                "medida correctiva": 3, "vecino": 2, "ruido": 2, "perturbacion": 2},
     "rutas": ["impugnacion_comparendo_transito", "fotomulta", "apelacion_medida_correctiva", "querella_policiva"]},
    {"id": "insolvencia", "nombre": "Insolvencia", "area_perfiles": "A06-S06",
     "claves": {"insolvencia": 3, "no puedo pagar": 2, "sobreendeudado": 3, "reorganizacion": 3, "acreedores": 2,
                "liquidacion patrimonial": 3, "negociacion de deudas": 3},
     "rutas": ["negociacion_deudas", "reorganizacion", "liquidacion_patrimonial"]},
    {"id": "propiedad_intelectual", "nombre": "Propiedad intelectual", "area_perfiles": "A06-S10",
     "claves": {"marca": 3, "logo": 2, "derechos de autor": 3, "patente": 3, "plagio": 3, "competencia desleal": 3,
                "registro de marca": 3, "copiaron": 2},
     "rutas": ["solicitud_registro_marca", "oposicion_marca", "cese_desista", "demanda_competencia_desleal"]},
]

# Lo que hay que verificar antes de elegir una ruta. Son preguntas, no afirmaciones de procedencia.
VERIFICAR_RUTA = {
    "tutela": ["¿Existe otro medio de defensa judicial y es eficaz? (subsidiariedad)",
               "¿Cuánto tiempo pasó desde la vulneración? (inmediatez)",
               "¿Quién vulnera el derecho y quién lo reclama? (legitimación)"],
    "tutela_salud": ["¿Hay orden del médico tratante y negativa o demora de la entidad?",
                     "¿Existe riesgo actual para la salud o la vida?"],
    "tutela_peticion": ["¿Hay constancia de radicación de la petición y venció el plazo de respuesta? (use J05)"],
    "desacato": ["¿Hay fallo de tutela con orden concreta y plazo vencido?"],
    "peticion_general": ["¿Ante qué autoridad o particular se presenta y qué se pide exactamente?"],
    "peticion_informacion": ["¿La información es pública o tiene reserva legal?"],
    "demanda_ejecutiva": ["¿El documento cumple los requisitos de un título ejecutivo? (verificar en la norma "
                          "procesal vigente)",
                          "¿Cuándo venció la obligación? (prescripción: verificar la norma aplicable)"],
    "demanda_monitorio": ["¿El caso cumple los requisitos del proceso monitorio? (verificar en la norma procesal "
                          "vigente)"],
    "demanda_laboral": ["¿Se agotó la reclamación al empleador o la reclamación administrativa, si aplica?",
                        "¿Cuándo terminó la relación? (prescripción: verificar la norma aplicable)"],
    "nulidad_restablecimiento": ["¿Cuándo se notificó el acto? (caducidad: use J05 con R-PLAZO-0012)",
                                 "¿Se interpusieron los recursos obligatorios?",
                                 "¿La conciliación extrajudicial es requisito de procedibilidad?"],
    "reparacion_directa": ["¿Cuándo ocurrió o se conoció el daño? (caducidad: use J05 con R-PLAZO-0013)",
                           "¿La conciliación extrajudicial es requisito de procedibilidad?"],
    "recurso_administrativo": ["¿Cuándo y cómo se notificó el acto? (plazo: use J05 con R-PLAZO-0010)",
                               "¿Qué recursos proceden según el propio acto?"],
    "denuncia_penal": ["¿Qué ocurrió, cuándo, dónde y quiénes intervinieron?",
                       "¿El delito exige querella y está en término? (verificar la norma aplicable)"],
    "habeas_corpus": ["¿La persona está privada de la libertad ahora y por orden de quién?"],
}
GENERICO = ["Verifique los requisitos del trámite y la competencia (territorial, funcional y por cuantía) en la "
            "norma vigente antes de elegir esta ruta."]

DATOS = [
    ("hechos", "Los hechos: qué pasó, en orden.", "¿Qué ocurrió exactamente y en qué orden?"),
    ("pretension", "La pretensión: qué se quiere lograr.", "¿Qué resultado concreto busca?"),
    ("fechas", "Las fechas clave (hecho, notificación, vencimiento).",
     "¿En qué fecha ocurrió cada hecho y cuándo le notificaron o respondieron?"),
    ("sujetos", "Quiénes intervienen y en qué calidad.",
     "¿Quién reclama y contra quién (persona, empresa o entidad pública)?"),
    ("lugar", "El lugar de los hechos o del domicilio de las partes.", "¿En qué ciudad o municipio ocurrió?"),
    ("cuantia", "El valor económico del asunto, si lo tiene.", "¿Cuál es el valor aproximado de lo que reclama?"),
    ("documentos", "Los documentos disponibles.", "¿Qué documentos o pruebas tiene a la mano?"),
]
ALERTAS = [
    (("capturado", "captura", "detenido", "privado de la libertad", "carcel"),
     "Posible privación de la libertad: es un asunto urgente que requiere abogado o defensor de inmediato."),
    (("riesgo de muerte", "urgencia vital", "riesgo para la vida", "amenaza de muerte"),
     "Posible riesgo para la vida o la integridad: acuda de inmediato a la autoridad competente."),
    (("violencia intrafamiliar", "violencia sexual", "maltrato"),
     "Posible situación de violencia: existen medidas de protección urgentes ante comisaría de familia, fiscalía "
     "o policía."),
    (("vence manana", "vence hoy", "ya vencio", "termino vencido", "me notificaron"),
     "Hay un plazo corriendo: calcule el término con J05 antes de cualquier otra cosa."),
]


def _norm(texto) -> str:
    t = unicodedata.normalize("NFD", str(texto or "").lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return " " + re.sub(r"[^a-z0-9ñ]+", " ", t).strip() + " "


def _aparece(clave: str, texto_norm: str) -> bool:
    """Frase exacta, o palabra suelta con su plural simple. Siempre por palabras completas («prima» ≠ «primavera»)."""
    if " " in clave:
        return f" {clave} " in texto_norm
    return re.search(r" %s(?:s|es)? " % re.escape(clave), texto_norm) is not None


def _ref_regla(rid, hoy):
    r = reglas.vigente(rid, hoy)
    return reglas.referencia(r) if r else None


def clasificar(entrada: dict, apoyo_modelo=None, hoy: date = None) -> dict:
    """Clasifica por reglas. `apoyo_modelo(entrada, resultado)` es opcional y su salida queda como propuesta."""
    hoy = hoy or date.today()
    entrada = entrada if isinstance(entrada, dict) else {}
    hechos = str(entrada.get("hechos") or "")[:MAX_TEXTO]
    pretension = str(entrada.get("pretension") or "")[:MAX_TEXTO]
    sujetos = entrada.get("sujetos") if isinstance(entrada.get("sujetos"), list) else []
    fechas = entrada.get("fechas") if isinstance(entrada.get("fechas"), (list, dict)) else []
    docs = entrada.get("documentos") if isinstance(entrada.get("documentos"), list) else []
    texto = _norm(" ".join([hechos, pretension, " ".join(str(s) for s in sujetos), " ".join(str(d) for d in docs)]))

    materias = []
    for m in MATERIAS:
        vistos = [(k, p) for k, p in m["claves"].items() if _aparece(k, texto)]
        puntaje = sum(p for _, p in vistos)
        if puntaje >= UMBRAL:
            materias.append({"id": m["id"], "nombre": m["nombre"], "puntaje": puntaje,
                             "coincidencias": sorted(k for k, _ in vistos), "area_perfiles": m["area_perfiles"]})
    materias.sort(key=lambda x: (-x["puntaje"], x["id"]))

    rutas, vistas = [], set()
    for m in materias[:4]:
        definicion = next(x for x in MATERIAS if x["id"] == m["id"])
        for tid in definicion["rutas"]:
            t = documentos.INDICE.get(tid)
            if not t or tid in vistas:
                continue
            vistas.add(tid)
            rutas.append({"id": tid, "nombre": t["nombre"], "area": t["area"], "materia": m["id"],
                          "tipo_de_documento_en_catalogo": tid,
                          "por_que": f"La materia «{m['nombre']}» coincide por: {', '.join(m['coincidencias'])}.",
                          "por_verificar": VERIFICAR_RUTA.get(tid, []) + GENERICO,
                          "estado": "CANDIDATA"})

    faltantes, preguntas = [], []
    presentes = {"hechos": len(hechos.strip()) >= 40, "pretension": len(pretension.strip()) >= 10,
                 "fechas": bool(fechas) or bool(re.search(r"\b(19|20)\d{2}\b", hechos)),
                 "sujetos": bool(sujetos), "lugar": bool(str(entrada.get("lugar") or "").strip()),
                 "cuantia": entrada.get("cuantia") not in (None, ""), "documentos": bool(docs)}
    for clave, descripcion, pregunta in DATOS:
        if not presentes[clave]:
            faltantes.append({"dato": clave, "descripcion": descripcion})
            preguntas.append(pregunta)
    for r in rutas[:3]:
        for q in VERIFICAR_RUTA.get(r["id"], []):
            if q not in preguntas:
                preguntas.append(q)

    alertas = [msg for claves, msg in ALERTAS if any(_aparece(k, texto) for k in claves)]
    normas = []
    ids = {m["id"] for m in materias}
    for rid, cond in (("R-CONST-0001", "tutela" in ids), ("R-CONST-0002", "tutela" in ids),
                      ("R-PET-0001", "peticion" in ids), ("R-PLAZO-0001", "peticion" in ids)):
        if cond:
            ref = _ref_regla(rid, hoy)
            if ref:
                normas.append(ref)

    if not presentes["hechos"]:
        estado = "INSUFICIENTE"
    elif not materias:
        estado = "SIN_COINCIDENCIAS"
    elif len(materias) > 1 and materias[0]["puntaje"] - materias[1]["puntaje"] <= 1:
        estado = "AMBIGUO"
    else:
        estado = "CLASIFICADO"
    salida = {"procedimiento": PROCEDIMIENTO, "version": VERSION, "estado": estado,
              "materias_posibles": materias, "rutas_candidatas": rutas, "datos_faltantes": faltantes,
              "preguntas_necesarias": preguntas[:14], "alertas": alertas, "normas": normas,
              "metodo": "reglas de palabras clave (determinista, sin modelo de IA)",
              "limites": ["La clasificación es una hipótesis de trabajo basada en palabras: puede fallar con "
                          "hechos descritos de otra manera.",
                          "No se afirma competencia ni procedencia: cada ruta candidata trae lo que debe "
                          "verificarse antes de elegirla.",
                          "Las rutas remiten a tipos de escrito del catálogo; que exista un tipo no prueba que "
                          "proceda en el caso."],
              "juicio_profesional": ["Elegir la vía, la jurisdicción y el juez o autoridad competente.",
                                     "Valorar prescripción, caducidad y requisitos de procedibilidad."],
              "propuesta_modelo": None,
              "aviso": "Orientación de apoyo para revisión profesional; no es un concepto jurídico."}
    if estado == "INSUFICIENTE":
        salida["limites"].insert(0, "Los hechos son demasiado breves para clasificar: complete las preguntas.")
    if callable(apoyo_modelo):
        try:
            propuesta = apoyo_modelo(entrada, salida)
        except Exception as e:                                  # el apoyo nunca tumba la clasificación
            propuesta = {"error": type(e).__name__}
        salida["propuesta_modelo"] = {"estado": "PROPUESTA_NO_VERIFICADA", "contenido": propuesta,
                                      "nota": "Generada por un modelo de IA: no modifica la clasificación por "
                                              "reglas y debe revisarla una persona."}
    return salida


def instruccion_apoyo(entrada: dict, resultado: dict) -> str:
    """Texto para pedirle al modelo una segunda lectura (lo usa quien conecte `apoyo_modelo`)."""
    materias = ", ".join(m["nombre"] for m in resultado["materias_posibles"]) or "ninguna"
    return ("Revisa esta clasificación preliminar hecha por reglas. Materias detectadas: " + materias + ". "
            "Con los hechos que vienen como datos, propone: (1) materias que falten o sobren, con la razón; "
            "(2) preguntas adicionales indispensables. No afirmes competencia, no cites artículos ni sentencias "
            "que no estén en los datos y marca cada punto como PROPUESTA.")
