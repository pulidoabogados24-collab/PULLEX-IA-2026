"""Evaluación DETERMINISTA de la calidad de una respuesta de PULLEX IA (PUL-018).

No llama a ningún modelo ni a la red. Son funciones puras que reciben texto y devuelven datos: sirven para
(1) calificar respuestas guardadas contra `evaluacion/calidad_respuesta.jsonl`, (2) probar el arnés en pytest
y (3) que el backend reutilice las mismas comprobaciones (truncamiento, cobertura, citas sospechosas) antes de
mostrar una respuesta.

Qué mide (y qué NO):
- Cobertura de partes obligatorias por palabras clave (como `benchmark.py`): es un PISO. Que una palabra aparezca
  no prueba que la parte esté bien respondida.
- Truncamiento por síntomas en el texto (o por `stop_reason` si se conserva). Es una red de seguridad; la
  defensa real es leer el motivo de parada del proveedor.
- Citas sospechosas por FORMA (formato imposible, número improbable, radicado o ponente que el usuario no dio,
  cita textual atribuida). NO verifica que una sentencia exista: eso exige consultar la relatoría.
- Directitud de la apertura, exceso de advertencias, preguntas aclaratorias, conclusión, longitud mínima.
  La longitud NUNCA suma puntos: solo detecta respuestas demasiado cortas o demasiado largas (un juez que premia
  lo largo cae en el sesgo de verbosidad).

HUMAN REVIEW REQUIRED: los casos dorados son material de prueba redactado sin revisión de un abogado. Una
respuesta que aprueba aquí no es por eso jurídicamente correcta.

Uso:
    python evaluacion/evaluar_calidad.py validar
    python evaluacion/evaluar_calidad.py evaluar --respuestas respuestas.jsonl [--salida resultado.json]

`respuestas.jsonl`: una línea por caso, {"id": "CR01", "respuesta": "…", "stop_reason": "end_turn"} (el
último campo es opcional).
"""
import argparse
import json
import re
import sys
import unicodedata
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
CASOS = RAIZ / "evaluacion" / "calidad_respuesta.jsonl"

AVISO_REVISION = ("AVISO: los casos y las pistas de esta evaluación son borradores sin revisión de un abogado "
                  "colombiano. Una aprobación automática no demuestra corrección jurídica.")

AREAS = ("Tutela", "Laboral", "Penal", "Civil y familia", "Administrativo", "Comercial", "Transversal")
PERFILES = ("abogado", "ciudadano")
TIPOS = ("simple", "multi_parte", "caso_largo", "ambigua_respondible", "ambigua_critica", "seguimiento",
         "redaccion", "revision", "riesgo_alucinacion", "premisa_falsa", "reparacion_intencion", "documento",
         "alto_riesgo")
INTENCIONES = ("pregunta", "investigacion", "analisis", "redaccion", "comparacion", "extraccion", "resumen",
               "accion", "documento", "voz")
PROFUNDIDADES = ("brief", "normal", "deep", "expert")
GRAVEDADES = ("critica", "mayor", "menor")
MOTIVOS_DE_CORTE = ("max_tokens", "length", "model_context_window_exceeded", "incomplete", "max_output_tokens")

ANIO_ACTUAL = date.today().year
ANIO_PRIMERA_SENTENCIA_CC = 1992


# ------------------------------------------------------------------------------------ texto básico --
def normalizar(texto: str) -> str:
    """Minúsculas, sin tildes y con espacios simples."""
    t = "".join(c for c in unicodedata.normalize("NFD", str(texto or "")) if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", t.lower())


def aparece(item: str, respuesta_norm: str) -> bool:
    """¿Aparece el ítem en el texto ya normalizado? `item` admite alternativas separadas por «|». Se compara
    desde el inicio de una palabra (no dentro de otra)."""
    for alt in (a.strip() for a in str(item).split("|")):
        if not alt:
            continue
        a = normalizar(alt)
        patron = (r"(?<![a-z0-9])" if a[:1].isalnum() else "") + re.escape(a)
        if re.search(patron, respuesta_norm):
            return True
    return False


def contar_palabras(texto: str) -> int:
    return len(re.findall(r"[\wÁÉÍÓÚÜÑáéíóúüñ]+(?:[-'][\wÁÉÍÓÚÜÑáéíóúüñ]+)*", texto or ""))


def _oraciones(texto: str) -> list:
    """Oraciones aproximadas: corta en . ? ! y en saltos de línea; ignora líneas vacías."""
    partes = re.split(r"(?<=[.?!])\s+|\n+", texto or "")
    return [p.strip() for p in partes if p and p.strip()]


def primera_frase(texto: str) -> str:
    for linea in (texto or "").splitlines():
        l = linea.strip()
        if not l or re.fullmatch(r"[#>*\-_\s]+", l):
            continue
        l = re.sub(r"^[#>\s]+", "", l)
        m = re.match(r"(.+?[.?!:])(?:\s|$)", l)
        return (m.group(1) if m else l).strip()
    return ""


_RE_SUBPREGUNTA = re.compile(
    r"(?:,|;|\by\b|\bo\b)\s*(?:qu[eé]|cu[aá]l(?:es)?|c[oó]mo|cu[aá]ndo|d[oó]nde|qui[eé]n(?:es)?|cu[aá]nt[oa]s?|"
    r"por qu[eé]|para qu[eé]|hay|existe|puede|podr[ií]a|procede)\b", re.I)


def contar_preguntas(texto: str) -> int:
    """Cantidad de preguntas distintas de un mensaje (detector de preguntas múltiples). Cuenta cada segmento
    entre signos de interrogación y, dentro de uno, las subpreguntas encadenadas con coma o «y» que traen su
    propia palabra interrogativa («¿Qué delito es, qué artículo aplica y hay dolo?» son tres)."""
    t = texto or ""
    segmentos = re.findall(r"¿[^?¿]*\?", t)
    if not segmentos:
        return t.count("?")
    return sum(1 + len(_RE_SUBPREGUNTA.findall(seg)) for seg in segmentos)


# ------------------------------------------------------------------------------------- cobertura --
def cobertura_de_partes(respuesta: str, partes: list) -> dict:
    """Cobertura de las partes obligatorias. Cada parte es {"parte": descripción, "pistas": [ítems]}; se da por
    cubierta si aparece AL MENOS UNA de sus pistas (cada pista admite alternativas con «|»). `missed_question_rate`
    de la especificación (punto 159) es 1 - cobertura."""
    rn = normalizar(respuesta)
    cubiertas, faltantes = [], []
    for p in partes or []:
        pistas = p.get("pistas") or []
        (cubiertas if any(aparece(x, rn) for x in pistas) else faltantes).append(p.get("parte", ""))
    total = len(partes or [])
    return {"total": total, "cubiertas": cubiertas, "faltantes": faltantes,
            "cobertura": (len(cubiertas) / total) if total else 1.0}


def errores_prohibidos(respuesta: str, errores: list) -> list:
    """Errores prohibidos del caso: cada uno es {"error": descripción, "pistas": [ítems]}. Se marca si aparece
    CUALQUIERA de sus pistas. Devuelve la lista de descripciones marcadas."""
    rn = normalizar(respuesta)
    return [e.get("error", "") for e in errores or [] if any(aparece(x, rn) for x in e.get("pistas") or [])]


# ---------------------------------------------------------------------------------- truncamiento --
_PALABRAS_ABIERTAS = frozenset(
    "de del la las el los lo un una unos unas en y e o u ni que con por para a al se su sus como entre sobre "
    "ante bajo desde hasta hacia según segun sin cuando donde si pero aunque porque pues también tambien más mas "
    "muy es son fue ser está esta están estan hay ha han puede pueden debe deben tiene tienen".split())


def detectar_truncamiento(texto: str, stop_reason: str = None) -> dict:
    """¿La respuesta parece cortada? Devuelve {"truncada": bool, "senales": [..], "fuertes": n, "moderadas": n}.
    Con `stop_reason` de corte (max_tokens, length, model_context_window_exceeded…) es truncada sin más.
    Sin él, se buscan síntomas: frase que termina en una palabra que pide continuación, bloque de código sin
    cerrar, encabezado o introducción («:») sin contenido, paréntesis o comillas abiertos, prosa larga sin punto."""
    senales, fuertes, moderadas = [], 0, 0
    t = (texto or "").rstrip()
    if stop_reason and str(stop_reason).lower() in MOTIVOS_DE_CORTE:
        return {"truncada": True, "senales": [f"stop_reason={stop_reason}"], "fuertes": 1, "moderadas": 0}
    if not t.strip():
        return {"truncada": True, "senales": ["respuesta vacía"], "fuertes": 1, "moderadas": 0}
    if t.count("```") % 2 == 1:
        senales.append("bloque de código sin cerrar")
        fuertes += 1
    lineas = [l for l in t.splitlines() if l.strip()]
    ultima = lineas[-1].strip()
    cuerpo = re.sub(r"^(?:[-*•+]\s+|\d+[.)]\s+|>\s*|#{1,6}\s+)", "", ultima).rstrip()
    if re.match(r"^#{1,6}\s+\S", ultima) and len(lineas) >= 2:
        senales.append("termina en un encabezado sin contenido")
        fuertes += 1
    elif ultima.endswith(":") or re.fullmatch(r"\*\*[^*]+:\*\*", ultima):
        senales.append("termina en una introducción con dos puntos, sin lo que anuncia")
        fuertes += 1
    elif ultima.startswith("|"):
        if not ultima.rstrip().endswith("|"):
            senales.append("fila de tabla incompleta")
            fuertes += 1
    elif ultima.endswith(("…", "...")):
        senales.append("termina en puntos suspensivos")
        moderadas += 1
    else:
        sin_cierre = re.sub(r"[*_`]+$", "", cuerpo).rstrip()
        fin = sin_cierre[-1:] if sin_cierre else ""
        if fin and fin not in ".?!:;)]»\"'”":
            palabras = re.findall(r"[\wáéíóúüñÁÉÍÓÚÜÑ]+", sin_cierre)
            ultima_palabra = normalizar(palabras[-1]) if palabras else ""
            es_item = bool(re.match(r"^(?:[-*•+]\s+|\d+[.)]\s+)", ultima))
            if ultima_palabra in _PALABRAS_ABIERTAS:
                senales.append(f"termina en «{ultima_palabra}», una palabra que pide continuación")
                fuertes += 1
            elif not es_item and contar_palabras(sin_cierre) >= 8:
                senales.append("el último párrafo de prosa no termina en punto")
                moderadas += 1
    ultimo_parrafo = re.split(r"\n\s*\n", t)[-1]
    if ultimo_parrafo.count("(") > ultimo_parrafo.count(")") or ultimo_parrafo.count("«") > ultimo_parrafo.count("»"):
        senales.append("paréntesis o comillas angulares sin cerrar en el último párrafo")
        moderadas += 1
    if ultimo_parrafo.count('"') % 2 == 1:
        senales.append("comillas sin cerrar en el último párrafo")
        moderadas += 1
    if t.count("**") % 2 == 1:
        senales.append("negrita sin cerrar")
        moderadas += 1
    return {"truncada": fuertes >= 1 or moderadas >= 2, "senales": senales, "fuertes": fuertes,
            "moderadas": moderadas}


def continuacion_duplicada(parcial: str, continuacion: str, minimo_palabras: int = 6) -> int:
    """Al unir una respuesta cortada con su continuación, ¿cuántas palabras iniciales de la continuación ya
    estaban al final de lo parcial? (0 = no hay solapamiento). Sirve para recortar el duplicado."""
    def fichas(t):
        return [x for x in (re.sub(r"^\W+|\W+$", "", normalizar(w)) for w in re.findall(r"\S+", t or "")) if x]
    a, b = fichas(parcial), fichas(continuacion)
    for n in range(min(len(a), len(b), 80), minimo_palabras - 1, -1):
        if a[-n:] == b[:n]:
            return n
    return 0


# ----------------------------------------------------------------------------------- citas jurídicas --
# Topes GENEROSOS por texto legal: no son el número exacto de artículos, solo sirven para marcar lo absurdo
# (por ejemplo «artículo 9999 del Código Penal»). Revisar con un abogado antes de endurecerlos.
_TOPE_ARTICULOS = (
    (r"constituci[oó]n", 380, "Constitución Política"),
    (r"c[oó]digo penal|ley 599", 700, "Código Penal"),
    (r"c[oó]digo de procedimiento penal|ley 906", 800, "Código de Procedimiento Penal"),
    (r"c[oó]digo general del proceso|\bcgp\b|ley 1564", 800, "Código General del Proceso"),
    (r"c[oó]digo sustantivo del trabajo|\bcst\b", 600, "Código Sustantivo del Trabajo"),
    (r"c[oó]digo civil|ley 57", 3000, "Código Civil"),
    (r"c[oó]digo de comercio", 3000, "Código de Comercio"),
    (r"cpaca|ley 1437", 450, "CPACA"),
    (r"decreto 2591", 62, "Decreto 2591 de 1991"),
)
_RE_SENTENCIA = re.compile(
    r"\b(?:sentencia\s+)?(?P<tipo>SU|C|T)\s?-\s?(?P<num>\d{1,6})(?P<resto>(?:\s*(?:de|del|/)\s*(?:a[ñn]o\s+)?(?P<anio>\d{4}|\d{2}))?)",
    re.I)
_TOPE_SENTENCIA = {"C": 1500, "T": 2000, "SU": 1500}
_RE_ARTICULO = re.compile(r"\b(?:art[íi]culo|art\.)\s*(?P<num>\d{1,6})(?P<letra>[A-Za-z]?)\b(?P<cola>[^.;,\n]{0,60})", re.I)
_RE_LEY = re.compile(r"\bLey\s+(?P<num>\d{1,4})\s+de\s+(?P<anio>\d{4})\b")
_RE_DECRETO = re.compile(r"\bDecreto(?:\s+Ley|\s+Legislativo)?\s+(?P<num>\d{1,5})\s+de\s+(?P<anio>\d{4})\b", re.I)
_RE_RADICADO = re.compile(r"\b\d{5}-?\d{2}-?\d{2}-?\d{3}-?\d{4}-?\d{5}-?\d{2}\b|\b(?:radicado|rad\.?)\s*(?:n[.º°o]*\s*)?[\dA-Z][\dA-Z\-./]{6,}", re.I)
_RE_PONENTE = re.compile(r"\b(?:M\.\s?P\.|magistrad[oa]\s+ponente)\s*:?\s*(?:Dr\.?|Dra\.?)?\s*[A-ZÁÉÍÓÚ][\wáéíóúñ]+", re.I)
_RE_CITA_TEXTUAL_INVERSA = re.compile(
    r"(?:dijo|dice|señal[oó]|afirm[oó]|sostuvo|indic[oó]|expres[oó]|consider[oó])\s+(?:la corte|el consejo de estado|la sala|el tribunal)[^.\n]{0,40}?[:,]?\s*[«\"“]([^»\"”]{60,})[»\"”]",
    re.I)
_RE_CITA_TEXTUAL = re.compile(
    r"(?:la corte|el consejo de estado|la sala|el tribunal|la sentencia)[^.\n]{0,80}?(?:dijo|dice|señal[oó]|afirm[oó]|sostuvo|indic[oó]|expres[oó]|consider[oó])[^.\n]{0,40}?[:,]?\s*[«\"“]([^»\"”]{60,})[»\"”]",
    re.I)


def _anio_completo(a: str) -> int:
    n = int(a)
    if n < 100:
        return 1900 + n if n >= 90 else 2000 + n
    return n


def _extraer_citas(texto: str) -> list:
    """Lista de dicts {"cita", "tipo", ...} con lo que parece una cita jurídica del texto."""
    citas = []
    for m in _RE_SENTENCIA.finditer(texto or ""):
        anio = _anio_completo(m.group("anio")) if m.group("anio") else None
        citas.append({"tipo": "sentencia", "cita": m.group(0).strip(), "alta": m.group("tipo").upper(),
                      "numero": int(m.group("num")), "anio": anio})
    for m in _RE_ARTICULO.finditer(texto or ""):
        citas.append({"tipo": "articulo", "cita": (m.group(0).split("\n")[0]).strip(), "numero": int(m.group("num")),
                      "cola": m.group("cola") or ""})
    for m in _RE_LEY.finditer(texto or ""):
        citas.append({"tipo": "ley", "cita": m.group(0), "numero": int(m.group("num")), "anio": int(m.group("anio"))})
    for m in _RE_DECRETO.finditer(texto or ""):
        citas.append({"tipo": "decreto", "cita": m.group(0), "numero": int(m.group("num")), "anio": int(m.group("anio"))})
    for m in _RE_RADICADO.finditer(texto or ""):
        citas.append({"tipo": "radicado", "cita": m.group(0).strip()})
    for m in _RE_PONENTE.finditer(texto or ""):
        citas.append({"tipo": "ponente", "cita": m.group(0).strip()})
    for rx in (_RE_CITA_TEXTUAL, _RE_CITA_TEXTUAL_INVERSA):
        for m in rx.finditer(texto or ""):
            citas.append({"tipo": "cita_textual", "cita": m.group(1)[:80] + "…"})
    return citas


def _tope_de_articulo(cola: str):
    c = normalizar(cola)
    for patron, tope, nombre in _TOPE_ARTICULOS:
        if re.search(patron, c):
            return tope, nombre
    if re.search(r"\bc\.?\s?p\.?\b", c):  # «C.P.» es a la vez Constitución y Código Penal: se usa el tope mayor
        return 700, "C.P. (Constitución o Código Penal)"
    return None, None


def citas_sospechosas(texto: str, permitidas: str = "") -> list:
    """Revisa por FORMA las citas jurídicas del texto. `permitidas` es el texto que la persona ya dio (consulta,
    documento adjunto): lo que ya estaba ahí no se marca. Cada hallazgo: {"cita", "tipo", "motivo",
    "severidad"} con severidad «grave» (formato o número imposible) o «aviso» (hay que verificarlo en la fuente
    oficial: radicado, ponente, cita textual, sentencia sin año). NO comprueba que la sentencia exista."""
    previas = normalizar(permitidas)
    hallazgos = []

    def anotar(c, motivo, severidad):
        hallazgos.append({"cita": c["cita"], "tipo": c["tipo"], "motivo": motivo, "severidad": severidad})

    for c in _extraer_citas(texto):
        if previas and normalizar(c["cita"]) in previas:
            continue
        t = c["tipo"]
        if t == "sentencia":
            tope = _TOPE_SENTENCIA.get(c["alta"], 2000)
            if c["numero"] == 0 or c["numero"] > tope:
                anotar(c, f"número improbable para una sentencia {c['alta']} (más de {tope} o cero)", "grave")
            elif c["anio"] is None:
                anotar(c, "sentencia sin año: no se puede ubicar en la relatoría", "aviso")
            elif c["anio"] < ANIO_PRIMERA_SENTENCIA_CC or c["anio"] > ANIO_ACTUAL:
                anotar(c, f"año {c['anio']} fuera del rango posible de la Corte Constitucional "
                          f"({ANIO_PRIMERA_SENTENCIA_CC}-{ANIO_ACTUAL})", "grave")
        elif t == "articulo":
            tope, nombre = _tope_de_articulo(c["cola"])
            if c["numero"] == 0:
                anotar(c, "artículo cero no existe", "grave")
            elif tope and c["numero"] > tope:
                anotar(c, f"número muy por encima de los artículos de {nombre} (tope orientativo {tope})", "grave")
        elif t == "ley":
            n, a = c["numero"], c["anio"]
            if a > ANIO_ACTUAL or a < 1800:
                anotar(c, f"año {a} imposible", "grave")
            elif n == 0 or n > 3000:
                anotar(c, "número de ley improbable", "grave")
            elif a >= 2006 and n < 1000:
                anotar(c, "número de ley incoherente con el año (desde 2006 las leyes pasan de 1000)", "grave")
            elif 1992 <= a <= 2004 and n >= 1000:
                anotar(c, "número de ley incoherente con el año (hasta 2004 no llegaban a 1000)", "grave")
            elif a <= 2018 and n >= 2000:
                anotar(c, "número de ley incoherente con el año (las leyes 2000 en adelante son de 2019 o después)", "grave")
        elif t == "decreto":
            if c["anio"] > ANIO_ACTUAL or c["anio"] < 1800:
                anotar(c, f"año {c['anio']} imposible", "grave")
            elif c["numero"] == 0:
                anotar(c, "decreto número cero", "grave")
        elif t == "radicado":
            anotar(c, "radicado que la persona no dio: verificar en la Rama Judicial; un radicado no se debe inventar",
                   "aviso")
        elif t == "ponente":
            anotar(c, "magistrado ponente: verificar en la relatoría; un ponente no se debe inventar", "aviso")
        elif t == "cita_textual":
            anotar(c, "cita textual atribuida a una providencia: verificar la literalidad en la fuente oficial",
                   "aviso")
    return hallazgos


# ------------------------------------------------------------------------- forma de la respuesta --
_APERTURAS_NO_DIRECTAS = re.compile(
    r"^(?:claro|por supuesto|con gusto|entiendo|comprendo|gracias por|excelente|buena pregunta|muy buena|"
    r"antes de (?:responder|empezar|contestar)|para (?:responder|contestar|resolver|entender) (?:esta|tu|su|bien)|"
    r"a continuaci[oó]n|veamos|lo primero es|es importante (?:aclarar|se[ñn]alar|destacar|recordar|mencionar)|"
    r"cabe (?:aclarar|destacar|se[ñn]alar|resaltar)|esto no es asesor[ií]a|no soy abogado|como (?:inteligencia artificial|ia\b)|"
    r"me preguntas|tu pregunta es|seg[uú]n entiendo|es una (?:pregunta|situaci[oó]n|consulta) (?:muy |bastante )?(?:com[uú]n|frecuente|interesante|compleja))",
    re.I)
_PREGUNTA_SI_NO = re.compile(
    r"^\W*¿\s*(?:puedo|puede|pueden|podr[ií]a|es|son|ser[ií]a|se puede|se pueden|tengo|tiene|tienen|debo|debe|deben|"
    r"procede|proceden|hay|existe|aplica|aplican|cabe|vale|sirve|corresponde|me toca|toca|est[aá]|estoy|fue|ha|han|caduca|prescribe)\b",
    re.I)
_MARCAS_DE_RESPUESTA = re.compile(
    r"\b(?:s[ií]|no|depende|probablemente|lo m[aá]s probable|es posible|podr[ií]a|puedes|puede|procede|no procede|"
    r"correcto|incorrecto|en principio|tienes derecho|no tienes|s[ií] puede|no puede|debes|no debes|cabe|no cabe|"
    r"claro que|as[ií] es|exacto|ya prescribi|todav[ií]a|aun no|a[uú]n no)\b", re.I)


def apertura_directa(respuesta: str, consulta: str = "") -> dict:
    """Prueba de la primera frase. No es directa si arranca con relleno de asistente, advertencia legal o
    repite la pregunta. Si la consulta es de sí o no, además debe aparecer una marca de respuesta («Sí», «No»,
    «Depende…», «Lo más probable…») en los primeros 220 caracteres."""
    p = primera_frase(respuesta)
    pn = normalizar(p)
    if not p:
        return {"directa": False, "motivo": "respuesta vacía", "primera_frase": p}
    if _APERTURAS_NO_DIRECTAS.search(pn):
        return {"directa": False, "motivo": "arranca con relleno o advertencia antes de responder", "primera_frase": p}
    if _PREGUNTA_SI_NO.search((consulta or "").strip()):
        if not _MARCAS_DE_RESPUESTA.search(normalizar(respuesta)[:220]):
            return {"directa": False, "motivo": "la consulta es de sí o no y la apertura no contesta sí, no o depende",
                    "primera_frase": p}
    return {"directa": True, "motivo": "", "primera_frase": p}


_RE_ADVERTENCIA = re.compile(
    r"no (?:es|constituye|sustituye|reemplaza)[^.]{0,40}asesor[ií]a|orientaci[oó]n general|"
    r"(?:consulta|consultar|acude|acudir|busca|buscar|habla|hablar)[^.]{0,25}(?:con )?(?:un|una|tu|su) abogad|"
    r"recomiend[oa][^.]{0,40}abogad|te sugiero[^.]{0,40}abogad|no soy (?:un )?abogad|"
    r"soy (?:una )?(?:ia|inteligencia artificial)[^.]{0,40}(?:no|pero)", re.I)


def advertencias(respuesta: str) -> dict:
    """Cuenta las advertencias del tipo «consulta a un abogado / esto no es asesoría». `solo_advertencia` es
    verdadero si la respuesta casi no tiene más que eso (la advertencia usada como respuesta)."""
    oraciones = _oraciones(respuesta)
    marcadas = [o for o in oraciones if _RE_ADVERTENCIA.search(normalizar(o))]
    palabras_utiles = sum(contar_palabras(o) for o in oraciones if o not in marcadas)
    return {"cantidad": len(marcadas), "ejemplos": marcadas[:3], "palabras_utiles": palabras_utiles,
            "solo_advertencia": bool(marcadas) and palabras_utiles < 40}


def preguntas_en_respuesta(respuesta: str) -> dict:
    """Cuántas preguntas hace la respuesta, qué fracción del texto son preguntas y si termina en pregunta."""
    oraciones = _oraciones(respuesta)
    preg = [o for o in oraciones if o.endswith("?")]
    pal_p = sum(contar_palabras(o) for o in preg)
    pal_t = max(1, contar_palabras(respuesta))
    return {"cantidad": len(preg), "fraccion": pal_p / pal_t, "termina_en_pregunta": bool(oraciones) and oraciones[-1].endswith("?"),
            "ejemplos": preg[:3]}


_RE_CONCLUSION = re.compile(
    r"\b(?:en conclusi[oó]n|conclusi[oó]n|en s[ií]ntesis|en resumen|por (?:lo )?tanto|entonces|as[ií] que|"
    r"en definitiva|lo recomendable|lo (?:que )?(?:sigue|siguiente)|te recomiendo|recomiendo|siguiente paso|"
    r"qu[eé] hacer|qu[eé] puedes hacer|puedes (?:presentar|solicitar|radicar|acudir|pedir)|debes (?:presentar|solicitar|radicar|acudir)|"
    r"lo (?:m[aá]s )?probable es|en tu caso|en su caso|para (?:resumir|cerrar))\b", re.I)


def tiene_conclusion(respuesta: str) -> bool:
    """Heurística débil: ¿hay una conclusión o un siguiente paso en el último tercio del texto? Las respuestas
    de menos de 80 palabras no la necesitan (la respuesta misma es la conclusión)."""
    if contar_palabras(respuesta) < 80:
        return True
    t = respuesta or ""
    cola = t[int(len(t) * 0.55):]
    return bool(_RE_CONCLUSION.search(cola)) or bool(re.search(r"(?mi)^#{0,6}\s*\**conclusi[oó]n", t))


_RE_MARCADOR_VERIFICACION = re.compile(
    r"pendiente de verificaci[oó]n|verific[ao][^.]{0,50}(?:fuente|oficial|relator[ií]a|vigencia|suin|senado|diario)|"
    r"no pude verificar|no (?:he|pude|puedo) (?:podido )?(?:verificar|confirmar|encontrar|ubicar)|"
    r"no (?:tengo|cuento con) (?:registro|certeza|informaci[oó]n)|no (?:conozco|identifico|encuentro)|"
    r"conviene (?:confirmar|verificar)|debes (?:confirmar|verificar)|confirma(?:r|lo)? (?:en|con)|"
    r"no (?:existe|figura|aparece) (?:una|ese|esa|tal)|sin (?:poder )?verificar|consulta(?:r)? (?:la|el) (?:relator[ií]a|suin|texto oficial)",
    re.I)


def marcador_de_verificacion(respuesta: str) -> bool:
    """¿La respuesta marca lo que no pudo verificar o remite a la fuente oficial?"""
    return bool(_RE_MARCADOR_VERIFICACION.search(respuesta or ""))


def repeticion_de_previo(respuesta: str, previo: str, n: int = 8) -> float:
    """Fracción de las secuencias de `n` palabras de la respuesta que ya estaban en el texto previo del asistente.
    Detecta el «explícame más» contestado con las mismas palabras (punto 135). 0 = nada repetido."""
    def gramas(t):
        w = normalizar(t).split()
        return {" ".join(w[i:i + n]) for i in range(0, max(0, len(w) - n + 1))}
    a, b = gramas(respuesta), gramas(previo)
    return (len(a & b) / len(a)) if a else 0.0


def longitud(respuesta: str, minimo: int = None, maximo: int = None) -> dict:
    n = contar_palabras(respuesta)
    return {"palabras": n, "corta": bool(minimo) and n < minimo, "larga": bool(maximo) and n > maximo}


# --------------------------------------------------------------------------------- evaluación total --
def _chk(nombre, ok, gravedad, detalle=""):
    return {"nombre": nombre, "ok": bool(ok), "gravedad": gravedad, "detalle": detalle}


def evaluar_respuesta(caso: dict, respuesta: str, stop_reason: str = None) -> dict:
    """Aplica todas las comprobaciones del caso a una respuesta. `aprobado` exige cero fallas críticas y cero
    mayores; las menores se informan. El resultado NO es una nota jurídica."""
    contexto = " ".join([caso.get("consulta", "")] + [m.get("texto", "") for m in caso.get("contexto_previo", [])])
    checks = []

    trunc = detectar_truncamiento(respuesta, stop_reason)
    checks.append(_chk("sin_truncamiento", not trunc["truncada"], "critica", "; ".join(trunc["senales"])))

    cov = cobertura_de_partes(respuesta, caso.get("partes_obligatorias", []))
    if cov["total"]:
        gravedad = "critica" if cov["cobertura"] < 0.5 else "mayor"
        checks.append(_chk("cobertura_completa", cov["cobertura"] == 1.0, gravedad,
                           "faltan: " + " | ".join(cov["faltantes"]) if cov["faltantes"] else ""))

    prohibidos = errores_prohibidos(respuesta, caso.get("errores_prohibidos", []))
    checks.append(_chk("sin_errores_prohibidos", not prohibidos, "critica", " | ".join(prohibidos)))

    citas = citas_sospechosas(respuesta, permitidas=contexto)
    graves = [c for c in citas if c["severidad"] == "grave"]
    avisos = [c for c in citas if c["severidad"] == "aviso"]
    checks.append(_chk("citas_sin_formato_imposible", not graves, "critica",
                       "; ".join(f"{c['cita']} ({c['motivo']})" for c in graves)))
    checks.append(_chk("citas_sin_datos_no_verificables", not avisos, "menor",
                       "; ".join(f"{c['cita']} ({c['motivo']})" for c in avisos)))

    adv = advertencias(respuesta)
    checks.append(_chk("advertencia_no_sustituye_respuesta", not adv["solo_advertencia"], "critica",
                       "casi todo es advertencia" if adv["solo_advertencia"] else ""))
    maximo_adv = caso.get("max_advertencias", 1)
    checks.append(_chk("sin_exceso_de_advertencias", adv["cantidad"] <= maximo_adv, "menor",
                       f"{adv['cantidad']} advertencias (máximo {maximo_adv})"))
    if caso.get("perfil") == "abogado" and re.search(r"no es asesor|orientaci[oó]n general", normalizar(respuesta)):
        checks.append(_chk("sin_advertencia_de_ciudadano_a_abogado", False, "menor",
                           "advertencia de «orientación general» dirigida a un abogado"))

    if caso.get("exige_apertura_directa", True):
        ap = apertura_directa(respuesta, caso.get("consulta", ""))
        checks.append(_chk("apertura_directa", ap["directa"], "mayor", ap["motivo"]))

    if caso.get("prohibe_radicado_y_ponente"):
        inventables = [c for c in avisos if c["tipo"] in ("radicado", "ponente")]
        checks.append(_chk("sin_radicado_ni_ponente_no_dados", not inventables, "critica",
                           "; ".join(f"{c['cita']}" for c in inventables)))

    previos = " ".join(m.get("texto", "") for m in caso.get("contexto_previo", []) if m.get("rol") == "asistente")
    if previos:
        rep = repeticion_de_previo(respuesta, previos)
        checks.append(_chk("no_repite_lo_anterior", rep <= 0.35, "mayor", f"{rep:.0%} de la respuesta ya estaba dicho"))

    pr = preguntas_en_respuesta(respuesta)
    max_p = caso.get("max_preguntas", 2)
    min_p = caso.get("min_preguntas", 0)
    checks.append(_chk("no_pregunta_de_mas", pr["cantidad"] <= max_p, "mayor", f"{pr['cantidad']} preguntas (máximo {max_p})"))
    if min_p:
        checks.append(_chk("hace_la_pregunta_necesaria", pr["cantidad"] >= min_p, "mayor", "no hizo la pregunta que falta"))
    elif caso.get("tipo") not in ("ambigua_critica",):
        checks.append(_chk("responde_en_vez_de_preguntar", pr["fraccion"] < 0.5, "critica",
                           f"{pr['fraccion']:.0%} del texto son preguntas"))
    if caso.get("no_debe_terminar_en_pregunta"):
        checks.append(_chk("no_termina_en_pregunta", not pr["termina_en_pregunta"], "menor", ""))

    if caso.get("exige_marcador_verificacion"):
        checks.append(_chk("marca_lo_no_verificado", marcador_de_verificacion(respuesta), "critica",
                           "no dice que no pudo verificar ni remite a la fuente oficial"))

    lon = longitud(respuesta, caso.get("min_palabras"), caso.get("max_palabras"))
    checks.append(_chk("longitud_minima", not lon["corta"], "mayor", f"{lon['palabras']} palabras, mínimo orientativo {caso.get('min_palabras')}"))
    if caso.get("max_palabras"):
        checks.append(_chk("no_excede_longitud", not lon["larga"], "menor", f"{lon['palabras']} palabras, máximo orientativo {caso['max_palabras']}"))

    if caso.get("exige_conclusion", False):
        checks.append(_chk("tiene_conclusion", tiene_conclusion(respuesta), "menor", "no se ve conclusión ni siguiente paso"))

    fallas = [c for c in checks if not c["ok"]]
    return {"id": caso.get("id"), "area": caso.get("area"), "tipo": caso.get("tipo"), "perfil": caso.get("perfil"),
            "aprobado": not any(c["gravedad"] in ("critica", "mayor") for c in fallas),
            "cobertura": cov["cobertura"], "palabras": lon["palabras"], "truncada": trunc["truncada"],
            "citas_graves": len(graves), "citas_aviso": len(avisos), "fallas": fallas, "checks": checks}


def evaluar_lote(casos: list, respuestas: dict) -> dict:
    """`respuestas`: {id: texto} o {id: {"respuesta": texto, "stop_reason": …}}. Los casos sin respuesta se
    cuentan aparte (no se evalúan como fallas)."""
    resultados, sin_respuesta = [], []
    for c in casos:
        r = respuestas.get(c["id"])
        if r is None:
            sin_respuesta.append(c["id"])
            continue
        texto, motivo = (r.get("respuesta", ""), r.get("stop_reason")) if isinstance(r, dict) else (r, None)
        resultados.append(evaluar_respuesta(c, texto, motivo))
    return {"resultados": resultados, "sin_respuesta": sin_respuesta, "resumen": resumir(resultados)}


def resumir(resultados: list) -> dict:
    """Métricas agregadas (punto 106 y 159 de la especificación). Nada de porcentajes de confianza: son
    proporciones sobre los casos evaluados."""
    n = len(resultados)
    if not n:
        return {"casos": 0}

    def prop(f):
        return round(sum(1 for r in resultados if f(r)) / n, 4)

    por_area = {}
    for r in resultados:
        a = por_area.setdefault(r["area"], {"casos": 0, "aprobados": 0})
        a["casos"] += 1
        a["aprobados"] += 1 if r["aprobado"] else 0
    return {"casos": n, "tasa_aprobacion": prop(lambda r: r["aprobado"]),
            "missed_question_rate": round(sum(1 - r["cobertura"] for r in resultados) / n, 4),
            "truncation_rate": prop(lambda r: r["truncada"]),
            "citas_graves_rate": prop(lambda r: r["citas_graves"] > 0),
            "falla_apertura_rate": prop(lambda r: any(f["nombre"] == "apertura_directa" for f in r["fallas"])),
            "por_area": por_area}


# ----------------------------------------------------------------------------------------- casos --
def cargar_casos(ruta: Path = CASOS) -> list:
    return [json.loads(l) for l in Path(ruta).read_text(encoding="utf-8").splitlines() if l.strip()]


def validar_caso(c: dict) -> list:
    """Problemas de forma de un caso dorado (lista vacía = bien formado)."""
    p = []
    for k in ("id", "consulta", "area", "perfil", "tipo", "intencion_esperada", "profundidad_esperada",
              "partes_obligatorias", "errores_prohibidos", "min_palabras", "estado_revision", "comportamiento_esperado"):
        if k not in c:
            p.append(f"falta «{k}»")
    if p:
        return p
    if c["area"] not in AREAS:
        p.append(f"área desconocida: {c['area']}")
    if c["perfil"] not in PERFILES:
        p.append(f"perfil desconocido: {c['perfil']}")
    if c["tipo"] not in TIPOS:
        p.append(f"tipo desconocido: {c['tipo']}")
    if c["intencion_esperada"] not in INTENCIONES:
        p.append(f"intención desconocida: {c['intencion_esperada']}")
    if c["profundidad_esperada"] not in PROFUNDIDADES:
        p.append(f"profundidad desconocida: {c['profundidad_esperada']}")
    if not str(c["estado_revision"]).startswith("SIN_REVISAR"):
        p.append("estado_revision debe empezar por SIN_REVISAR mientras un abogado no lo revise")
    if not isinstance(c["min_palabras"], int) or c["min_palabras"] < 0:
        p.append("min_palabras debe ser un entero >= 0")
    if c.get("max_palabras") is not None and c["max_palabras"] < c["min_palabras"]:
        p.append("max_palabras menor que min_palabras")
    if not c["partes_obligatorias"]:
        p.append("sin partes obligatorias")
    for i, parte in enumerate(c["partes_obligatorias"]):
        if not parte.get("parte") or not parte.get("pistas"):
            p.append(f"parte {i + 1} sin descripción o sin pistas")
    for i, e in enumerate(c["errores_prohibidos"]):
        if not e.get("error") or not e.get("pistas"):
            p.append(f"error prohibido {i + 1} sin descripción o sin pistas")
    n_preg = contar_preguntas(c["consulta"])
    if c["tipo"] == "multi_parte" and len(c["partes_obligatorias"]) < max(2, n_preg):
        p.append(f"la consulta trae {n_preg} preguntas y el caso declara {len(c['partes_obligatorias'])} partes")
    if c["tipo"] == "riesgo_alucinacion" and not c.get("exige_marcador_verificacion"):
        p.append("un caso de riesgo de alucinación debe exigir marcador de verificación")
    if c["tipo"] == "seguimiento" and not c.get("contexto_previo"):
        p.append("un seguimiento necesita contexto_previo")
    return p


def validar_casos(casos: list) -> dict:
    ids = [c.get("id") for c in casos]
    problemas = {c.get("id", f"#{i}"): validar_caso(c) for i, c in enumerate(casos)}
    problemas = {k: v for k, v in problemas.items() if v}
    if len(set(ids)) != len(ids):
        problemas["_ids"] = ["hay ids repetidos"]
    return problemas


# ------------------------------------------------------------------------------------------ CLI --
def _cli(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="orden", required=True)
    sub.add_parser("validar", help="valida la forma de los casos dorados")
    ev = sub.add_parser("evaluar", help="califica respuestas guardadas (sin llamar a ningún modelo)")
    ev.add_argument("--respuestas", required=True, help="JSONL con {id, respuesta[, stop_reason]}")
    ev.add_argument("--casos", default=str(CASOS))
    ev.add_argument("--salida", help="escribe el detalle en este archivo JSON (por ejemplo bajo evaluacion/resultados/)")
    a = ap.parse_args(argv)
    casos = cargar_casos(Path(getattr(a, "casos", CASOS)))
    print(AVISO_REVISION)
    if a.orden == "validar":
        prob = validar_casos(casos)
        print(f"{len(casos)} casos; {len(prob)} con problemas")
        for k, v in prob.items():
            print(f"  {k}: " + "; ".join(v))
        return 1 if prob else 0
    respuestas = {}
    for l in Path(a.respuestas).read_text(encoding="utf-8").splitlines():
        if l.strip():
            d = json.loads(l)
            respuestas[d["id"]] = d
    rep = evaluar_lote(casos, respuestas)
    print(json.dumps(rep["resumen"], ensure_ascii=False, indent=2))
    for r in rep["resultados"]:
        if not r["aprobado"]:
            print(f"- {r['id']} ({r['area']}): " + "; ".join(f"{f['nombre']} [{f['gravedad']}] {f['detalle']}".strip() for f in r["fallas"]))
    if rep["sin_respuesta"]:
        print("sin respuesta:", ", ".join(rep["sin_respuesta"]))
    if a.salida:
        Path(a.salida).parent.mkdir(parents=True, exist_ok=True)
        Path(a.salida).write_text(json.dumps(rep, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(_cli())
