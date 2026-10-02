"""J04 — Análisis jurisprudencial: ficha y validaciones.

No hay base de sentencias cargada. Por eso este procedimiento NO busca ni propone sentencias: entrega la ficha
vacía con lo que falta y valida las fichas que una persona (o un proceso de ingesta futuro) diligencie.

Validaciones deterministas:
- campos obligatorios de la ficha;
- el tipo de decisión (C, SU, T) se deduce del identificador, y sus efectos solo se afirman con reglas
  VERIFICADAS del registro (R-JUR-0001 a R-JUR-0005). Para SU no hay regla verificada: no se afirma efecto;
- una ficha no puede atribuir efectos generales (erga omnes, «obliga a todos») a una decisión de tutela;
- la existencia de la sentencia solo consta si hay enlace a la autoridad que la expidió y fecha de consulta; aun
  así el sistema no abrió el enlace: lo dice.

Lo que queda a juicio profesional: la ratio decidendi, la analogía con el caso y la fuerza del precedente.
"""
import re
import unicodedata
from datetime import date

import reglas

VERSION = "1.0.0"
PROCEDIMIENTO = "J04"

CAMPOS = [
    ("autoridad", "Autoridad que profirió la decisión (corporación y sala o sección)."),
    ("tipo_decision", "Tipo de decisión (sentencia C, SU, T; casación; unificación; auto…)."),
    ("identificador", "Número o radicado exacto, tal como aparece en la fuente."),
    ("fecha", "Fecha de la decisión (AAAA-MM-DD)."),
    ("problema_juridico", "Problema jurídico que resolvió la decisión."),
    ("fundamento_determinante", "Razón que sostiene la decisión (ratio decidendi), con cita localizable."),
    ("diferencias_con_el_caso", "Semejanzas y diferencias de hecho y de derecho con el caso analizado."),
    ("efectos", "Alcance de la decisión: a quién obliga y desde cuándo."),
    ("enlace", "Enlace a la autoridad que expidió la decisión."),
    ("fecha_consulta", "Fecha en que se consultó la fuente (AAAA-MM-DD)."),
]
OBLIGATORIOS = tuple(c for c, _ in CAMPOS)
_RE_CC = re.compile(r"^\s*(?:sentencia\s+)?(C|SU|T|A)\s*[-–]?\s*(\d{1,4})[A-Z]?\s*(?:de|/|-)\s*(\d{2,4})\s*$", re.I)
_GENERALES = ("erga omnes", "efectos generales", "obliga a todos", "obligatoria para todos", "vinculante para todos",
              "todas las autoridades", "para todos los casos", "efecto general")
_DOMINIOS_AUTORIDAD = ("corteconstitucional.gov.co", "cortesuprema.gov.co", "consejodeestado.gov.co",
                       "ramajudicial.gov.co")
REGLAS_POR_TIPO = {"C": ("R-JUR-0001", "R-JUR-0002", "R-JUR-0005"), "T": ("R-JUR-0003",), "SU": ("R-JUR-0004",)}


def _norm(texto) -> str:
    t = unicodedata.normalize("NFD", str(texto or "").lower())
    return re.sub(r"\s+", " ", "".join(c for c in t if unicodedata.category(c) != "Mn")).strip()


def ficha_vacia() -> dict:
    return {c: "" for c, _ in CAMPOS}


def tipo_de(identificador: str):
    """C, SU, T o A si el identificador tiene la forma de la Corte Constitucional; None en otro caso.
    Que tenga la forma no prueba que la sentencia exista."""
    m = _RE_CC.match(str(identificador or ""))
    return m.group(1).upper() if m else None


def efectos_verificados(tipo: str, fecha=None) -> dict:
    """Lo que el registro permite afirmar sobre los efectos de un tipo de decisión, y con qué estado."""
    f = reglas.a_fecha(fecha) if fecha else date.today()
    afirmables, sin_verificar = [], []
    for rid in REGLAS_POR_TIPO.get(tipo or "", ()):
        r = reglas.vigente(rid, f)
        if not r:
            continue
        item = {**reglas.referencia(r), "enunciado": r["enunciado"],
                "requiere_juicio_profesional": r.get("requiere_juicio_profesional", "")}
        (afirmables if r["estado"] == reglas.VERIFICADA else sin_verificar).append(item)
    return {"tipo": tipo, "afirmables": afirmables, "sin_verificar": sin_verificar}


def validar_ficha(ficha: dict) -> dict:
    ficha = ficha if isinstance(ficha, dict) else {}
    faltan = [c for c in OBLIGATORIOS if not str(ficha.get(c) or "").strip()]
    alertas, juicio = [], ["La ratio decidendi, la analogía con el caso y la fuerza del precedente las determina "
                           "el profesional leyendo la providencia completa."]
    tipo = tipo_de(ficha.get("identificador"))
    declarado = _norm(ficha.get("tipo_decision"))
    palabras = set(re.split(r"[^a-z]+", declarado))
    declarados = (palabras & {"c", "su", "t", "a"}) | {v for k, v in (("tutela", "t"), ("constitucionalidad", "c"),
                                                                  ("unificacion", "su"), ("auto", "a"))
                                                      if k in palabras}
    if tipo and declarados and tipo.lower() not in declarados:
        alertas.append(f"El identificador tiene forma de decisión {tipo}, pero el tipo declarado es "
                       f"«{ficha.get('tipo_decision')}». Revise cuál es correcto.")
    fecha_txt = str(ficha.get("fecha") or "").strip()
    f = None
    if fecha_txt:
        try:
            f = reglas.a_fecha(fecha_txt)
            if f > date.today():
                alertas.append("La fecha de la decisión es futura.")
        except ValueError:
            alertas.append(f"La fecha {fecha_txt!r} no existe o no es AAAA-MM-DD.")
    m = _RE_CC.match(str(ficha.get("identificador") or ""))
    if m and f:
        anio = int(m.group(3))
        anio = anio + (1900 if anio >= 92 else 2000) if anio < 100 else anio
        if anio != f.year:
            alertas.append(f"El identificador dice año {anio} y la fecha indicada es de {f.year}.")
    efectos_txt = _norm(ficha.get("efectos"))
    verificados = efectos_verificados(tipo, f)
    if any(g in efectos_txt for g in _GENERALES):
        if tipo == "T":
            alertas.append("La ficha atribuye efectos generales a una decisión de tutela. La regla verificada "
                           "dice que obliga únicamente a las partes (R-JUR-0003): no lo afirme sin comprobar en "
                           "el texto que la Corte fijó otro alcance.")
        elif tipo == "SU":
            alertas.append("La ficha atribuye efectos generales a una sentencia SU. El registro no tiene una "
                           "regla verificada sobre su alcance (R-JUR-0004, NO_VERIFICADO): compruébelo en la fuente.")
        elif tipo != "C":
            alertas.append("La ficha atribuye efectos generales a una decisión cuyo tipo no tiene regla "
                           "verificada en el registro: el alcance debe comprobarse en la fuente.")
    if tipo == "C" and "inter partes" in efectos_txt:
        alertas.append("La ficha limita a las partes una sentencia de constitucionalidad; la regla verificada le "
                       "da efecto erga omnes en su parte resolutiva (R-JUR-0002).")
    enlace = str(ficha.get("enlace") or "").strip()
    existencia = "NO_VERIFICADA"
    if enlace:
        host = re.match(r"^https?://([^/:?#]+)", enlace.lower())
        oficial = bool(host) and any(host.group(1) == d or host.group(1).endswith("." + d) for d in _DOMINIOS_AUTORIDAD)
        if not oficial:
            alertas.append("El enlace no pertenece a la autoridad que expide la decisión: la jurisprudencia se "
                           "verifica en la relatoría de la corporación.")
        elif str(ficha.get("fecha_consulta") or "").strip():
            existencia = "ENLACE_OFICIAL_DECLARADO_NO_ABIERTO_POR_EL_SISTEMA"
    estado = "INCOMPLETA" if faltan else ("CON_ALERTAS" if alertas else "COMPLETA_PENDIENTE_DE_REVISION_HUMANA")
    return {"procedimiento": PROCEDIMIENTO, "version": VERSION, "estado": estado, "faltan": faltan,
            "alertas": alertas, "tipo_detectado": tipo, "existencia": existencia,
            "efectos_que_el_registro_permite_afirmar": verificados, "juicio_profesional": juicio,
            "limite": "No se atribuyen efectos generales ni fuerza vinculante sin comprobarlos en la fuente."}


def analizar(problema_juridico: str, hechos: str = "", fichas: list = None) -> dict:
    """Sin base de sentencias: devuelve la ficha vacía y lo que falta. Con fichas: las valida una por una."""
    problema = str(problema_juridico or "").strip()
    base = {"procedimiento": PROCEDIMIENTO, "version": VERSION, "problema_juridico": problema,
            "base_de_sentencias": "NO_CARGADA", "precedentes": [],
            "campos_de_la_ficha": [{"campo": c, "descripcion": d} for c, d in CAMPOS],
            "limite": "El sistema no propone sentencias de memoria: una sentencia que no esté en una ficha con "
                      "enlace oficial y fecha de consulta no se cita.",
            "reglas_de_alcance": {t: efectos_verificados(t) for t in ("C", "SU", "T")}}
    if not problema:
        return {**base, "estado": "ABSTENCION", "faltantes": ["problema_juridico"], "ficha": ficha_vacia()}
    if not fichas:
        return {**base, "estado": "SIN_BASE_DE_SENTENCIAS", "ficha": ficha_vacia(),
                "faltantes": ["Base de sentencias verificada (hoy no hay ninguna cargada).",
                              "Al menos una ficha diligenciada con enlace a la relatoría y fecha de consulta."],
                "donde_buscar": ["https://www.corteconstitucional.gov.co/relatoria/",
                                 "https://www.cortesuprema.gov.co/", "https://www.consejodeestado.gov.co/"]}
    validadas = [{"ficha": f, "validacion": validar_ficha(f)} for f in fichas[:50] if isinstance(f, dict)]
    lineas = {}
    for v in validadas:
        clave = _norm(v["ficha"].get("fundamento_determinante"))[:80]
        if clave:
            lineas.setdefault(clave, []).append(v["ficha"].get("identificador"))
    return {**base, "estado": "FICHAS_VALIDADAS", "precedentes": validadas,
            "posibles_lineas_distintas": len(lineas) if len(lineas) > 1 else 0,
            "juicio_profesional": ["Si hay fundamentos distintos entre las fichas, puede haber líneas "
                                   "contradictorias: debe compararlas un profesional."]}
