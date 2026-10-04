"""PULLEX Academia — modelo individual del conocimiento jurídico del estudiante.

Tres piezas, sin dependencias externas:

* MAPA: el Mapa del Derecho (área → tema → concepto). Las descripciones son deliberadamente
  generales y casi no citan números de artículo: el mapa orienta el estudio, no reemplaza la
  fuente oficial. Donde se nombra una norma, el estudiante debe verificar su vigencia.
* Emparejamiento: los conceptos que devuelve el modelo ("confundió la inmediatez") se
  convierten en un nodo del mapa por palabras clave; si no encaja, queda como concepto libre
  del área, para no perder el dato.
* Repetición espaciada tipo Leitner: cada concepto está en una "caja" 0-5. Un error lo manda a
  la caja 1 (repaso mañana); un acierto lo sube una caja y aleja el próximo repaso
  (1, 3, 7, 15 y 30 días).

Los indicadores son orientativos para el propio estudiante; no deben usarse para decisiones
académicas oficiales sin intervención humana.
"""
import json
import random
import re
import time
import unicodedata
from pathlib import Path

DIA = 86400
INTERVALOS = {0: 1, 1: 1, 2: 3, 3: 7, 4: 15, 5: 30}  # días hasta el próximo repaso según la caja
CAJA_DOMINADO = 4
UMBRAL_ACIERTO = 60  # puntaje total (0-100) desde el que un concepto no señalado cuenta como acierto


def normalizar(texto: str) -> str:
    t = unicodedata.normalize("NFD", str(texto or "").lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9ñ]+", " ", t).strip()


# (id, nombre, descripción, palabras clave globales, palabras clave válidas solo dentro del área)
def _c(cid, nombre, desc, kw=(), kwa=()):
    return {"id": cid, "nombre": nombre, "desc": desc, "kw": list(kw), "kwa": list(kwa)}


MAPA = [
    {"area": "Constitucional", "temas": [
        {"tema": "Acción de tutela", "conceptos": [
            _c("tutela-procedencia", "Requisitos de procedencia",
               "Antes del fondo, el juez verifica legitimación, inmediatez y subsidiariedad. Analízalos por separado y con los hechos del caso.",
               ["procedencia de la tutela", "requisitos de procedencia", "procedibilidad"], ["procedencia"]),
            _c("tutela-legitimacion", "Legitimación en la tutela",
               "Quién puede presentar la tutela (el titular, un apoderado, un agente oficioso) y contra quién procede (autoridades y, en ciertos casos, particulares).",
               ["legitimacion por activa", "legitimacion por pasiva", "agencia oficiosa", "agente oficioso"], ["legitimacion"]),
            _c("tutela-inmediatez", "Inmediatez",
               "La tutela debe presentarse en un plazo razonable desde la vulneración; no hay un término fijo, se analiza caso a caso.",
               ["inmediatez", "plazo razonable"]),
            _c("tutela-subsidiariedad", "Subsidiariedad",
               "Procede si no hay otro medio de defensa judicial idóneo y eficaz, o como mecanismo transitorio para evitar un perjuicio irremediable.",
               ["subsidiariedad", "otro medio de defensa", "mecanismo transitorio", "residual"]),
            _c("tutela-perjuicio", "Perjuicio irremediable",
               "Daño inminente, grave, que exige medidas urgentes e impostergables; habilita la tutela transitoria aunque exista otro medio.",
               ["perjuicio irremediable"]),
            _c("tutela-carencia", "Carencia actual de objeto",
               "Hecho superado (se satisfizo la pretensión) o daño consumado: el juez ya no puede dar la orden pedida.",
               ["hecho superado", "carencia actual", "dano consumado"]),
            _c("tutela-providencias", "Tutela contra providencias judiciales",
               "Procede excepcionalmente: requisitos generales de procedencia y al menos un defecto específico (fáctico, sustantivo, procedimental, orgánico, desconocimiento del precedente, entre otros).",
               ["contra providencia", "defecto factico", "defecto sustantivo", "defecto procedimental", "defecto organico"]),
            _c("tutela-desacato", "Cumplimiento del fallo y desacato",
               "Si la orden de tutela no se cumple, se pide el cumplimiento y se abre el incidente de desacato; la sanción exige probar la responsabilidad personal de quien debía cumplir.",
               ["desacato", "incidente de desacato", "cumplimiento del fallo", "cumplimiento del fallo y desacato"]),
        ]},
        {"tema": "Derechos fundamentales", "conceptos": [
            _c("derecho-salud", "Derecho fundamental a la salud",
               "Derecho fundamental autónomo, desarrollado por la Ley Estatutaria de Salud (Ley 1751 de 2015 — verificar vigencia). Peso de la orden del médico tratante.",
               ["derecho a la salud", "salud", "medico tratante", "eps"]),
            _c("derecho-peticion", "Derecho de petición",
               "Derecho a presentar solicitudes respetuosas y a recibir respuesta de fondo, clara y oportuna dentro del término legal.",
               ["derecho de peticion", "peticion"]),
            _c("debido-proceso", "Debido proceso",
               "Garantías en toda actuación judicial y administrativa: juez natural, defensa, contradicción, legalidad, doble instancia, entre otras.",
               ["debido proceso", "derecho de defensa", "contradiccion"]),
            _c("minimo-vital", "Mínimo vital",
               "Condiciones materiales mínimas para una existencia digna; relevante en tutelas por salarios o pensiones.",
               ["minimo vital"]),
        ]},
    ]},
    {"area": "Penal", "temas": [
        {"tema": "Teoría del delito", "conceptos": [
            _c("conducta", "Conducta", "Acción u omisión humana, voluntaria, penalmente relevante. Incluye la posición de garante en la omisión impropia.",
               ["conducta", "accion u omision", "posicion de garante", "omision impropia", "comision por omision"]),
            _c("tipicidad", "Tipicidad", "Adecuación de la conducta a la descripción legal del tipo penal (elementos objetivos y subjetivos).",
               ["tipicidad", "tipo penal", "atipic*", "conducta atipica"]),
            _c("imputacion-objetiva", "Imputación objetiva", "Creación de un riesgo jurídicamente desaprobado que se realiza en el resultado; riesgo permitido, autopuesta en peligro.",
               ["imputacion objetiva", "riesgo permitido", "riesgo desaprobado", "nexo causal", "causalidad"]),
            _c("dolo", "Dolo", "Conocimiento de los hechos constitutivos de la infracción y voluntad de realizarlos (incluye el dolo eventual).",
               ["dolo", "doloso", "dolosa", "dolo eventual"]),
            _c("culpa", "Culpa", "Infracción al deber objetivo de cuidado con un resultado previsible; solo es punible cuando la ley lo prevé.",
               ["culpa", "culposo", "deber objetivo de cuidado", "imprudencia"]),
            _c("antijuridicidad", "Antijuridicidad", "Lesión o puesta en peligro efectiva, sin justa causa, del bien jurídico tutelado.",
               ["antijuridicidad", "bien juridico"]),
            _c("legitima-defensa", "Legítima defensa", "Causal de ausencia de responsabilidad: agresión actual o inminente e injusta, defensa necesaria y proporcionada.",
               ["legitima defensa", "defensa propia", "agresion actual", "agresion injusta", "actualidad de la agresion", "proporcionalidad de la defensa"]),
            _c("culpabilidad", "Culpabilidad", "Reproche personal: imputabilidad, conocimiento de la antijuridicidad y exigibilidad de otra conducta.",
               ["culpabilidad", "inimputab*", "error de prohibicion", "exigibilidad"]),
            _c("ira-intenso-dolor", "Ira o intenso dolor", "Disminuye la pena cuando se actúa en ese estado, provocado por un comportamiento ajeno grave e injustificado.",
               ["ira", "intenso dolor", "estado de ira"]),
        ]},
        {"tema": "Proceso penal acusatorio", "conceptos": [
            _c("captura-flagrancia", "Captura en flagrancia", "Aprehensión sin orden judicial en las hipótesis legales de flagrancia; se somete a control de legalidad.",
               ["flagrancia", "captura", "control de legalidad"]),
            _c("imputacion", "Formulación de imputación", "Acto de comunicación de la Fiscalía que vincula formalmente al indiciado al proceso.",
               ["formulacion de imputacion"], ["imputacion"]),
            _c("medida-aseguramiento", "Medida de aseguramiento", "Restricción cautelar de la libertad o de otros derechos: requisitos de inferencia razonable, necesidad y proporcionalidad.",
               ["medida de aseguramiento", "detencion preventiva"]),
            _c("preacuerdos", "Preacuerdos", "Negociación entre Fiscalía e imputado o acusado que termina anticipadamente el proceso, con límites legales.",
               ["preacuerdo", "aceptacion de cargos", "allanamiento"]),
            _c("principio-oportunidad", "Principio de oportunidad", "Facultad reglada de la Fiscalía de suspender, interrumpir o renunciar a la persecución penal, con control judicial.",
               ["principio de oportunidad"]),
            _c("denuncia-querella", "Denuncia y querella", "La noticia criminal se pone en conocimiento de la Fiscalía bajo juramento; en los delitos querellables solo actúa la víctima y se exige intentar la conciliación antes.",
               ["denuncia", "denuncia penal", "querella", "querellable", "noticia criminal", "denuncia y querella"]),
        ]},
    ]},
    {"area": "Laboral", "temas": [
        {"tema": "Contrato de trabajo", "conceptos": [
            _c("elementos-contrato", "Elementos del contrato de trabajo", "Prestación personal del servicio, continuada subordinación y salario; reunidos, hay contrato aunque se le dé otro nombre.",
               ["elementos del contrato", "elementos esenciales", "prestacion personal", "remuneracion", "salario"]),
            _c("subordinacion", "Subordinación", "Facultad del empleador de dar órdenes e imponer reglamentos durante todo el contrato; el rasgo que distingue del contrato de prestación de servicios.",
               ["subordinacion", "dependencia", "autonomia tecnica"]),
            _c("primacia-realidad", "Primacía de la realidad", "Prevalecen los hechos sobre las formas: un contrato de prestación de servicios puede ser, en realidad, un contrato de trabajo (contrato realidad).",
               ["primacia de la realidad", "contrato realidad", "prestacion de servicios", "presuncion del contrato", "presuncion de contrato"]),
        ]},
        {"tema": "Terminación y protección", "conceptos": [
            _c("despido-sin-justa-causa", "Despido sin justa causa", "Terminación unilateral sin una causa legal; genera la indemnización tarifada según el tipo de contrato.",
               ["despido", "justa causa", "indemnizacion por despido"]),
            _c("indemnizacion-moratoria", "Indemnización moratoria", "Sanción por no pagar salarios y prestaciones al terminar el contrato; se analiza la buena o mala fe del empleador.",
               ["moratoria", "sancion moratoria", "buena fe"]),
            _c("estabilidad-reforzada", "Estabilidad laboral reforzada", "Protección frente al despido de personas en situación de debilidad (salud, embarazo, fuero); exige autorización o justa causa.",
               ["estabilidad laboral reforzada", "estabilidad reforzada", "fuero", "embarazo", "debilidad manifiesta"]),
        ]},
        {"tema": "Prestaciones y reclamación", "conceptos": [
            _c("prestaciones-sociales", "Prestaciones sociales", "Cesantías, intereses sobre cesantías y prima de servicios, entre otras; se liquidan con el salario base.",
               ["prestaciones", "cesantias", "prima de servicios"]),
            _c("prescripcion-laboral", "Prescripción laboral", "Regla general de tres años desde que la obligación se hizo exigible; el reclamo escrito la interrumpe por una sola vez (verificar).",
               ["prescripcion laboral"], ["prescripcion"]),
        ]},
    ]},
    {"area": "Civil", "temas": [
        {"tema": "Extinción de acciones", "conceptos": [
            _c("prescripcion-extintiva", "Prescripción extintiva", "Modo de extinguir acciones y derechos por no ejercerlos durante el tiempo legal; se interrumpe y se renuncia; debe alegarse.",
               ["prescripcion extintiva", "prescripcion de la accion"], ["prescripcion"]),
            _c("caducidad", "Caducidad", "Término perentorio para acudir a la jurisdicción; no se interrumpe como la prescripción y el juez la declara de oficio. Diferénciala bien de la prescripción.",
               ["caducidad", "prescripcion y caducidad", "prescripcion vs caducidad"]),
        ]},
        {"tema": "Responsabilidad y contratos", "conceptos": [
            _c("responsabilidad-contractual", "Responsabilidad contractual", "Incumplimiento de una obligación nacida del contrato: incumplimiento, daño, nexo causal; resolución o cumplimiento más perjuicios.",
               ["responsabilidad contractual", "incumplimiento", "resolucion del contrato", "condicion resolutoria"]),
            _c("responsabilidad-extracontractual", "Responsabilidad extracontractual", "Daño causado sin vínculo contractual previo: hecho, daño, nexo causal y culpa (o régimen objetivo en actividades peligrosas).",
               ["extracontractual", "actividades peligrosas", "responsabilidad civil"]),
            _c("nulidad-contrato", "Nulidad del contrato", "Absoluta (objeto o causa ilícita, incapacidad absoluta, falta de solemnidades) o relativa (vicios del consentimiento, incapacidad relativa).",
               ["nulidad absoluta", "nulidad relativa", "vicios del consentimiento", "error fuerza dolo"]),
            _c("arrendamiento-vivienda", "Arrendamiento de vivienda urbana", "Régimen especial de protección al arrendatario de vivienda: reajuste del canon con tope legal, garantías permitidas, preavisos y causales de terminación (verificar en la ley vigente).",
               ["arrendamiento de vivienda", "arrendamiento de vivienda urbana", "reajuste del canon", "canon de arrendamiento", "contrato de arrendamiento"]),
        ]},
        {"tema": "Bienes", "conceptos": [
            _c("posesion", "Posesión", "Tenencia de una cosa con ánimo de señor y dueño; distinta de la mera tenencia.",
               ["posesion", "animo de senor", "mera tenencia"]),
            _c("prescripcion-adquisitiva", "Prescripción adquisitiva", "Modo de adquirir el dominio por la posesión durante el tiempo legal (ordinaria o extraordinaria).",
               ["prescripcion adquisitiva", "usucapion", "pertenencia"]),
        ]},
    ]},
    {"area": "Administrativo", "temas": [
        {"tema": "Medios de control", "conceptos": [
            _c("nulidad-simple", "Nulidad", "Control objetivo de legalidad de un acto administrativo general, en interés de la legalidad.",
               ["nulidad simple", "medio de control de nulidad"]),
            _c("nulidad-restablecimiento", "Nulidad y restablecimiento del derecho", "Para quien se cree lesionado en un derecho por un acto administrativo particular; tiene término de caducidad.",
               ["restablecimiento del derecho"]),
            _c("reparacion-directa", "Reparación directa", "Indemnización por daños antijurídicos causados por hechos, omisiones u operaciones de la administración.",
               ["reparacion directa", "dano antijuridico", "falla del servicio"]),
            _c("caducidad-medio-control", "Caducidad del medio de control", "Cada medio de control tiene un término distinto; su conteo y la suspensión por conciliación prejudicial son errores frecuentes.",
               ["caducidad del medio", "conciliacion prejudicial"], ["caducidad"]),
        ]},
        {"tema": "Actuación administrativa", "conceptos": [
            _c("recursos-administrativos", "Recursos en sede administrativa", "Reposición, apelación y queja; cuándo son obligatorios para acudir a la jurisdicción.",
               ["recurso de reposicion", "recurso de apelacion", "recursos administrativos", "via gubernativa"]),
            _c("silencio-administrativo", "Silencio administrativo", "Efecto de que la administración no responda a tiempo: negativo como regla, positivo solo cuando la ley lo dispone.",
               ["silencio administrativo", "silencio negativo", "silencio positivo"]),
        ]},
    ]},
    {"area": "Familia", "temas": [
        {"tema": "Niños, niñas y adolescentes", "conceptos": [
            _c("interes-superior", "Interés superior del menor", "Criterio que orienta toda decisión que afecte a niños, niñas y adolescentes; sus derechos prevalecen.",
               ["interes superior", "prevalencia de los derechos"]),
            _c("alimentos", "Alimentos", "Obligación de proveer lo necesario para la subsistencia de quien tiene derecho; se fija según necesidad del alimentario y capacidad del alimentante.",
               ["alimentos", "cuota alimentaria"]),
            _c("custodia", "Custodia y visitas", "Cuidado personal del hijo y régimen de visitas del otro progenitor; se decide por el interés superior.",
               ["custodia", "cuidado personal", "visitas"]),
        ]},
        {"tema": "Pareja", "conceptos": [
            _c("union-marital", "Unión marital de hecho", "Comunidad de vida permanente y singular; la sociedad patrimonial exige requisitos y tiempo adicionales.",
               ["union marital", "sociedad patrimonial", "companeros permanentes"]),
            _c("divorcio", "Divorcio", "Por mutuo acuerdo (incluso ante notario) o contencioso por causales legales ante el juez de familia.",
               ["divorcio", "cesacion de efectos civiles"]),
        ]},
    ]},
    {"area": "Comercial", "temas": [
        {"tema": "Derecho societario y títulos", "conceptos": [
            _c("sas", "Sociedad por acciones simplificada", "Tipo societario flexible; responsabilidad de los accionistas limitada al monto de sus aportes, con excepciones.",
               ["sas", "sociedad por acciones simplificada"]),
            _c("titulos-valores", "Títulos valores", "Documentos necesarios para legitimar el ejercicio del derecho literal y autónomo que incorporan (letra, pagaré, cheque).",
               ["titulo valor", "titulos valores", "pagare", "letra de cambio", "cheque", "literalidad", "autonomia"]),
            _c("responsabilidad-administradores", "Deberes de los administradores", "Buena fe, lealtad y diligencia de un buen hombre de negocios; responden por los perjuicios causados con dolo o culpa.",
               ["administradores", "deber de lealtad", "buen hombre de negocios"]),
        ]},
    ]},
    {"area": "Procesal", "temas": [
        {"tema": "Presupuestos del proceso", "conceptos": [
            _c("competencia", "Competencia", "Factores objetivo, subjetivo, territorial, funcional y de conexión; distingue competencia de jurisdicción.",
               ["competencia", "factor territorial", "cuantia", "jurisdiccion"]),
            _c("legitimacion-causa", "Legitimación en la causa", "Relación entre las partes y la relación sustancial discutida; su falta lleva a sentencia desfavorable, no a nulidad.",
               ["legitimacion en la causa"], ["legitimacion"]),
            _c("notificacion", "Notificación", "Forma de poner en conocimiento las providencias; la notificación indebida puede generar nulidad.",
               ["notificacion", "notificar", "emplazamiento"]),
            _c("recursos-judiciales", "Recursos judiciales", "Reposición, apelación, queja, súplica, casación y revisión: procedencia, términos y efectos.",
               ["recurso", "recursos", "apelacion", "reposicion", "casacion"]),
        ]},
        {"tema": "Escritos y actuaciones", "conceptos": [
            _c("requisitos-demanda", "Requisitos formales de la demanda", "Designación del juez, partes, pretensiones, hechos, fundamentos, pruebas, cuantía, anexos y notificaciones; su falta lleva a la inadmisión.",
               ["requisitos formales de la demanda", "requisitos de la demanda", "requisitos formales", "inadmision", "juramento estimatorio", "anexos de la demanda"]),
            _c("narracion-hechos", "Narración de hechos", "Hechos determinados, numerados, en orden cronológico, uno por numeral y con su prueba; sin calificaciones jurídicas ni hechos que no sirven.",
               ["narracion de hechos", "narracion de los hechos", "hechos numerados", "hechos relevantes", "hechos distractores"]),
            _c("pretensiones", "Pretensiones y peticiones", "Lo que se pide debe ser concreto, claro y congruente con los hechos; se separan principales, subsidiarias y consecuenciales.",
               ["pretensiones y peticiones", "pretensiones", "pretension principal", "pretensiones subsidiarias", "peticiones concretas", "petitum"]),
            _c("contestacion-excepciones", "Contestación y excepciones", "Pronunciamiento expreso sobre pretensiones y cada hecho; excepciones de mérito en la contestación y previas en escrito separado.",
               ["contestacion y excepciones", "excepciones de merito", "excepcion de merito", "excepciones previas", "excepcion previa", "contestacion de la demanda"]),
            _c("poder-postulacion", "Poder y derecho de postulación", "Quién puede actuar sin abogado; el poder especial determina el asunto y las facultades, y las de disposición deben otorgarse expresamente.",
               ["poder y derecho de postulacion", "derecho de postulacion", "poder especial", "facultades del apoderado", "otorgamiento del poder"]),
            _c("sustentacion-recursos", "Sustentación de recursos", "Un recurso se interpone a tiempo y se sustenta con razones concretas contra la decisión; en la apelación de sentencias, los reparos delimitan lo que revisa el superior.",
               ["sustentacion de recursos", "sustentacion del recurso", "reparos concretos", "sustentar el recurso", "carga de sustentacion"]),
            _c("impulso-procesal", "Impulso procesal", "Cómo pedir con respeto y precisión que el despacho actúe, y qué herramientas existen frente a la mora judicial.",
               ["impulso procesal", "mora judicial", "duracion del proceso", "vigilancia judicial"]),
        ]},
    ]},
    {"area": "Probatorio", "temas": [
        {"tema": "Prueba", "conceptos": [
            _c("carga-prueba", "Carga de la prueba", "A quién corresponde probar los hechos que alega; el juez puede distribuirla en ciertos casos.",
               ["carga de la prueba", "carga dinamica", "onus probandi"]),
            _c("cadena-custodia", "Cadena de custodia", "Procedimiento que garantiza la autenticidad (mismidad) de los elementos materiales probatorios.",
               ["cadena de custodia", "mismidad"]),
            _c("prueba-ilicita", "Prueba ilícita", "Obtenida con violación de derechos fundamentales; es nula de pleno derecho y debe excluirse.",
               ["prueba ilicita", "prueba ilegal", "exclusion de la prueba", "regla de exclusion"]),
        ]},
    ]},
]

INDICE = {}
for _a in MAPA:
    for _t in _a["temas"]:
        for _c_ in _t["conceptos"]:
            INDICE[_c_["id"]] = {**_c_, "area": _a["area"], "tema": _t["tema"]}


def emparejar(texto: str, area: str | None = None) -> str | None:
    """Devuelve el id del concepto del mapa que mejor corresponde al texto, o None."""
    t = " " + normalizar(texto) + " "
    if not t.strip():
        return None
    mejor, largo = None, 0
    for cid, c in INDICE.items():
        claves = c["kw"] + (c["kwa"] if c["area"] == area else [])
        for k in claves:
            # palabra completa, salvo que la clave termine en "*" (prefijo: "atipic*" → atípica, atípico)
            patron = " " + k[:-1] if k.endswith("*") else " " + k + " "
            puntaje = len(k) + (0.5 if c["area"] == area else 0)
            if patron in t and puntaje > largo:
                mejor, largo = cid, puntaje
    return mejor


def id_libre(texto: str) -> str:
    return "libre:" + normalizar(texto)[:60].replace(" ", "-")


def estado_de(fila) -> str:
    if fila is None:
        return "sin_evaluar"
    if fila["caja"] >= CAJA_DOMINADO:
        return "dominado"
    if fila["fallos"] and fila["caja"] <= 1:
        return "debil"
    return "en_progreso"


def nivel_recomendado(promedio) -> str:
    if promedio is None or promedio < 55:
        return "basico"
    if promedio < 75:
        return "intermedio"
    if promedio < 88:
        return "avanzado"
    return "experto"


UTC_OFFSET_COLOMBIA = -5 * 3600  # Colombia no tiene horario de verano


def fin_del_dia(ahora: float) -> float:
    """Medianoche siguiente en hora de Colombia (los «repasos de hoy» vencen a esa hora)."""
    local = ahora + UTC_OFFSET_COLOMBIA
    return ahora + DIA - (local % DIA)


def cuando(ts: float, ahora: float | None = None) -> str:
    ahora = ahora or time.time()
    dias = int((ts - ahora) // DIA) + 1 if ts > ahora else 0
    return "hoy" if dias <= 0 else "mañana" if dias == 1 else f"en {dias} días"


def crear_tabla(con):
    con.executescript("""
    CREATE TABLE IF NOT EXISTS conocimiento(
        usuario TEXT NOT NULL, concepto_id TEXT NOT NULL, nombre TEXT NOT NULL, area TEXT,
        aciertos INTEGER DEFAULT 0, fallos INTEGER DEFAULT 0, caja INTEGER DEFAULT 0,
        proximo REAL, primer_visto REAL, ultimo_visto REAL, ultimo_fallo REAL, resuelto REAL,
        PRIMARY KEY(usuario, concepto_id));
    CREATE INDEX IF NOT EXISTS ix_conoc_proximo ON conocimiento(usuario, proximo);
    """)


def _actualizar(con, email, cid, nombre, area, resultado, ahora):
    f = con.execute("SELECT * FROM conocimiento WHERE usuario=? AND concepto_id=?", (email, cid)).fetchone()
    if f is None:
        con.execute("INSERT INTO conocimiento(usuario,concepto_id,nombre,area,caja,proximo,primer_visto,ultimo_visto) "
                    "VALUES(?,?,?,?,0,?,?,?)", (email, cid, nombre[:80], area, ahora + DIA, ahora, ahora))
        f = con.execute("SELECT * FROM conocimiento WHERE usuario=? AND concepto_id=?", (email, cid)).fetchone()
    if resultado == "fallo":
        con.execute("UPDATE conocimiento SET fallos=fallos+1, caja=1, proximo=?, ultimo_fallo=?, ultimo_visto=?, "
                    "resuelto=NULL WHERE usuario=? AND concepto_id=?",
                    (ahora + INTERVALOS[1] * DIA, ahora, ahora, email, cid))
    elif resultado == "acierto":
        caja = min(5, f["caja"] + 1)
        resuelto = f["resuelto"]
        if caja >= CAJA_DOMINADO and f["fallos"] and not resuelto:
            resuelto = ahora
        con.execute("UPDATE conocimiento SET aciertos=aciertos+1, caja=?, proximo=?, ultimo_visto=?, resuelto=? "
                    "WHERE usuario=? AND concepto_id=?",
                    (caja, ahora + INTERVALOS[caja] * DIA, ahora, resuelto, email, cid))
    else:
        con.execute("UPDATE conocimiento SET ultimo_visto=? WHERE usuario=? AND concepto_id=?", (ahora, email, cid))


def registrar_resultado(con, email: str, area: str, conceptos_caso, conceptos_debiles, total: int,
                        foco: str | None = None, ahora: float | None = None,
                        foco_nombre: str | None = None) -> list:
    """Actualiza el modelo del estudiante tras una evaluación. Devuelve los cambios aplicados."""
    ahora = ahora or time.time()

    def resolver(texto):
        cid = emparejar(texto, area)
        if cid:
            return cid, INDICE[cid]["nombre"], INDICE[cid]["area"]
        nombre = str(texto).strip()[:80]
        return (id_libre(nombre), nombre, area) if normalizar(nombre) else (None, None, None)

    debiles = {}
    for t in conceptos_debiles or []:
        cid, nombre, a = resolver(t)
        if cid:
            debiles[cid] = (nombre, a)
    evaluados = {}
    for t in conceptos_caso or []:
        cid, nombre, a = resolver(t)
        if cid:
            evaluados[cid] = (nombre, a)
    if foco and foco in INDICE:
        evaluados.setdefault(foco, (INDICE[foco]["nombre"], INDICE[foco]["area"]))
    elif foco and foco.startswith("libre:") and foco_nombre:
        evaluados.setdefault(foco, (str(foco_nombre)[:80], area))
    cambios = []
    for cid, (nombre, a) in debiles.items():
        _actualizar(con, email, cid, nombre, a, "fallo", ahora)
        cambios.append({"id": cid, "nombre": nombre, "resultado": "fallo"})
    for cid, (nombre, a) in evaluados.items():
        if cid in debiles:
            continue
        res = "acierto" if total >= UMBRAL_ACIERTO else "visto"
        _actualizar(con, email, cid, nombre, a, res, ahora)
        cambios.append({"id": cid, "nombre": nombre, "resultado": res})
    return cambios


def fila_publica(f, ahora=None) -> dict:
    return {"id": f["concepto_id"], "nombre": f["nombre"], "area": f["area"], "estado": estado_de(f),
            "aciertos": f["aciertos"], "fallos": f["fallos"], "caja": f["caja"],
            "proximo": f["proximo"], "proximo_texto": cuando(f["proximo"], ahora) if f["proximo"] else None,
            "tema": INDICE.get(f["concepto_id"], {}).get("tema")}


def severidad(f) -> str:
    if f["fallos"] >= 3 or (f["fallos"] >= 2 and f["aciertos"] == 0):
        return "alta"
    if f["fallos"] >= 2 or f["aciertos"] == 0:
        return "media"
    return "baja"


# ------------------------------------------------------------ Conectores argumentativos --
# Detección determinista (sin IA) de los conectores que unen el razonamiento de una respuesta de
# examen. La comparación ignora mayúsculas y tildes y exige palabra completa. Cada frase pertenece a
# una sola categoría; el orden de las categorías es el del panel «Conectores para tu respuesta».
CATEGORIAS_CONECTORES = [
    ("orden", "Orden", "Para ordenar los pasos del análisis",
     ["en primer lugar", "en segundo lugar", "en tercer lugar", "para empezar", "por un lado", "por otro lado",
      "de un lado", "de otro lado", "a continuación", "acto seguido", "finalmente", "por último"]),
    ("adicion", "Adición", "Para sumar un argumento o un requisito más",
     ["además", "asimismo", "igualmente", "de igual modo", "de igual manera", "del mismo modo", "por otra parte",
      "a su vez", "aunado a lo anterior", "sumado a ello", "incluso"]),
    ("contraste", "Contraste", "Para introducir el contraargumento, una excepción o un límite",
     ["sin embargo", "no obstante", "ahora bien", "en cambio", "por el contrario", "aun así", "pese a",
      "a pesar de", "si bien", "con todo", "aunque"]),
    ("causa", "Causa", "Para fundamentar: la razón jurídica o fáctica",
     ["porque", "puesto que", "ya que", "dado que", "toda vez que", "en virtud de", "debido a",
      "habida cuenta de", "comoquiera que", "como quiera que", "en razón de"]),
    ("consecuencia", "Consecuencia", "Para derivar la consecuencia jurídica de lo anterior",
     ["por consiguiente", "en consecuencia", "por lo tanto", "por tanto", "de ahí que", "así pues", "por ende",
      "de modo que", "de manera que", "por esa razón", "por esta razón", "de suerte que", "con lo cual"]),
    ("conclusion", "Conclusión", "Para cerrar con una respuesta defendible",
     ["en conclusión", "en síntesis", "en suma", "en definitiva", "para concluir", "en resumen", "así las cosas",
      "en ese orden de ideas", "en este orden de ideas"]),
    ("ejemplificacion", "Ejemplificación", "Para aclarar, confirmar o ilustrar con los hechos",
     ["en efecto", "por ejemplo", "es decir", "esto es", "a saber", "en otras palabras", "verbigracia",
      "tal es el caso de", "como ocurre con"]),
]
NOMBRE_CATEGORIA = {c: n for c, n, _, _ in CATEGORIAS_CONECTORES}
# Orden en que se sugieren las categorías que faltan (las que más pesan en un caso, primero).
PRIORIDAD_SUGERENCIA = ["contraste", "consecuencia", "conclusion", "orden", "causa", "adicion", "ejemplificacion"]

_FRASE_A_CATEGORIA = {}
for _cat, _n, _u, _frases in CATEGORIAS_CONECTORES:
    for _f in _frases:
        _FRASE_A_CATEGORIA[normalizar(_f)] = (_cat, _f)

_VOCALES = {"a": "[aáà]", "e": "[eéè]", "i": "[iíì]", "o": "[oóò]", "u": "[uúüù]"}
_LETRA = "0-9A-Za-zÁÉÍÓÚÜÑáéíóúüñàèìòù"


def _patron_frase(frase_normalizada: str) -> str:
    return "".join(r"\s+" if ch == " " else _VOCALES.get(ch, re.escape(ch)) for ch in frase_normalizada)


_RX_CONECTORES = re.compile(
    "(?<![" + _LETRA + "])(?:" + "|".join(_patron_frase(f) for f in sorted(_FRASE_A_CATEGORIA, key=len, reverse=True))
    + ")(?![" + _LETRA + "])", re.IGNORECASE)


def detectar_conectores(texto: str) -> list:
    """Conectores encontrados en orden de aparición: [{frase, categoria, inicio, fin}]."""
    encontrados = []
    for m in _RX_CONECTORES.finditer(str(texto or "")):
        cat, frase = _FRASE_A_CATEGORIA.get(normalizar(m.group(0)), (None, None))
        if cat:
            encontrados.append({"frase": frase, "categoria": cat, "inicio": m.start(), "fin": m.end()})
    return encontrados


def segmentar_conectores(texto: str) -> list:
    """Parte el texto en tramos [{t, c}] donde c es la categoría del conector o None. El cliente
    pinta cada tramo con textContent (sin innerHTML), así el resaltado no abre una vía de inyección."""
    texto = str(texto or "")
    tramos, pos = [], 0
    for d in detectar_conectores(texto):
        if d["inicio"] > pos:
            tramos.append({"t": texto[pos:d["inicio"]], "c": None})
        tramos.append({"t": texto[d["inicio"]:d["fin"]], "c": d["categoria"]})
        pos = d["fin"]
    if pos < len(texto):
        tramos.append({"t": texto[pos:], "c": None})
    return tramos


def _lista_frases(frases: list) -> str:
    q = ["«" + f + "»" for f in frases]
    return q[0] if len(q) == 1 else ", ".join(q[:-1]) + " y " + q[-1]


def resumen_conectores(texto: str) -> dict:
    """Resumen determinista para la evaluación: usados, categorías cubiertas, sugerencias y la línea
    «Conectores: usaste X; prueba con Y»."""
    det = detectar_conectores(texto)
    usados, por_cat = [], {}
    for d in det:
        if d["frase"] not in usados:
            usados.append(d["frase"])
        por_cat.setdefault(d["categoria"], [])
        if d["frase"] not in por_cat[d["categoria"]]:
            por_cat[d["categoria"]].append(d["frase"])
    faltan = [c for c in PRIORIDAD_SUGERENCIA if c not in por_cat]
    frases_de = {c: fs for c, _, _, fs in CATEGORIAS_CONECTORES}
    if faltan:
        sugeridos = [{"frase": frases_de[c][0], "categoria": c} for c in faltan[:2 if usados else 3]]
    else:  # todas las categorías cubiertas: propone variar con uno que no usó
        alternativa = next((f for c in ("contraste", "consecuencia", "conclusion") for f in frases_de[c]
                            if f not in usados), None)
        sugeridos = [{"frase": alternativa, "categoria": "variedad"}] if alternativa else []
    partes = ["«" + s["frase"] + "»" + (" (" + NOMBRE_CATEGORIA[s["categoria"]].lower() + ")"
                                         if s["categoria"] in NOMBRE_CATEGORIA else "") for s in sugeridos]
    sug_txt = partes[0] if len(partes) == 1 else ", ".join(partes[:-1]) + " y " + partes[-1] if partes else ""
    if not usados:
        linea = "Conectores: no encontré conectores argumentativos en tu respuesta; prueba con " + sug_txt + "."
    else:
        extra = f" (y {len(usados) - 5} más)" if len(usados) > 5 else ""
        linea = "Conectores: usaste " + _lista_frases(usados[:5]) + extra
        if not faltan:
            linea += "; buen repertorio" + ("; para variar, prueba con " + sug_txt if sugeridos else "") + "."
        else:
            linea += "; prueba con " + sug_txt + "."
    return {"usados": usados, "total": len(det),
            "categorias": [{"id": c, "nombre": NOMBRE_CATEGORIA[c], "frases": por_cat[c]}
                           for c, _, _, _ in CATEGORIAS_CONECTORES if c in por_cat],
            "faltan": [{"id": c, "nombre": NOMBRE_CATEGORIA[c]} for c in faltan],
            "sugeridos": sugeridos, "linea": linea}


def conectores_publicos() -> list:
    """Lo que muestra el panel plegable «Conectores para tu respuesta»."""
    return [{"id": c, "nombre": n, "uso": u, "ejemplos": fs[:6]} for c, n, u, fs in CATEGORIAS_CONECTORES]


# ------------------------------------------------------------------- Banco curado de casos --
# 180 casos tipo examen escritos con criterio docente (academia_banco/*.json, uno por área).
# Se sirven sin llamar al modelo y sin consumir consultas. Todos llevan revision_humana: true: su
# exactitud jurídica debe revisarla un docente antes de usarlos como material oficial.
BANCO_DIR = Path(__file__).resolve().parent / "academia_banco"
NIVELES_ORDEN = ["basico", "intermedio", "avanzado", "experto"]


def cargar_banco(directorio=None) -> list:
    casos = []
    d = Path(directorio) if directorio else BANCO_DIR
    if not d.is_dir():
        return casos
    for ruta in sorted(d.glob("*.json")):
        datos = json.loads(ruta.read_text(encoding="utf-8"))
        for c in datos.get("casos", []):
            casos.append({**c, "area": c.get("area") or datos.get("area")})
    return casos


BANCO = cargar_banco()
BANCO_IDX = {c["id"]: c for c in BANCO}


def conceptos_ids(caso: dict) -> set:
    """Ids del mapa que evalúa un caso del banco (sus «conceptos» emparejados en su área)."""
    return {cid for cid in (emparejar(t, caso.get("area")) for t in caso.get("conceptos") or []) if cid}


_IDS_POR_CASO = {c["id"]: conceptos_ids(c) for c in BANCO}


def elegir_del_banco(area, nivel, servidos: dict, concepto_id=None, azar=None):
    """Elige un caso del banco evitando los que el estudiante ya recibió.

    `servidos` = {banco_id: último momento en que se le sirvió}. Con `concepto_id` se prefieren los
    casos que evalúan ese concepto (primero los de su propia área y luego los más cercanos al nivel
    pedido). Si ya recibió todos los candidatos, repite el que recibió hace más tiempo.
    Devuelve (caso, repetido) o (None, False) si el banco no tiene candidatos."""
    azar = azar or random
    if concepto_id:
        area_c = INDICE.get(concepto_id, {}).get("area")
        pool = [c for c in BANCO if concepto_id in _IDS_POR_CASO.get(c["id"], ())]
    else:
        area_c = area
        pool = [c for c in BANCO if c["area"] == area and c["nivel"] == nivel]
    if not pool:
        return None, False
    nuevos = [c for c in pool if c["id"] not in servidos]
    if not nuevos:
        return min(pool, key=lambda c: (servidos.get(c["id"], 0), c["id"])), True

    def preferencia(c):
        dist = (abs(NIVELES_ORDEN.index(nivel) - NIVELES_ORDEN.index(c["nivel"]))
                if nivel in NIVELES_ORDEN and c["nivel"] in NIVELES_ORDEN else 0)
        return (c["area"] != area_c, dist)

    mejor = min(preferencia(c) for c in nuevos)
    return azar.choice([c for c in nuevos if preferencia(c) == mejor]), False
