"""Revisión de FORMA de las citas jurídicas de una respuesta (auditoría 2026-10-13: IA-01, IA-03, IA-07).

Lo usan el chat (``app._flujo_chat`` emite el evento SSE ``citas`` antes de ``fin``) y el evaluador fuera de línea
(``evaluacion/evaluar_calidad.py`` reexporta ``citas_sospechosas``). No llama a ningún modelo ni a la red; solo lee,
en modo lectura, el corpus propio (``corpus/corpus.db``) para derivar límites.

QUÉ HACE Y QUÉ NO (léase antes de mostrar nada al usuario):
- Es una revisión de FORMA. Que una cita no salga marcada NO significa que exista, que esté vigente ni que diga lo
  que la respuesta afirma. Nada de lo que devuelve este módulo debe presentarse como «verificado». La verificación
  de existencia exige la relatoría oficial y no está implementada.
- ``hay_citas``: la respuesta menciona leyes, decretos, artículos, códigos o providencias (C-/T-/SU-, radicados,
  autos, providencias de la Corte Suprema). Sirve para mostrar SIEMPRE el aviso «confírmalas en la fuente oficial».
- ``huerfanas``: marcas [F#] que no corresponden a ningún fragmento entregado al modelo (IA-03).
- ``sospechosas``: reglas deterministas, cada una con su motivo:
    * GRAVE  sentencia C-/T-/SU- con año posterior al año en curso o anterior a 1992 (la Corte Constitucional se
             instaló en 1992; regla que ya usaba el evaluador) o con número 0 o mayor que un tope orientativo.
    * GRAVE  providencia de la Corte Suprema (SL, SC, SP, STC, STL, STP, AL, AC, AP) con año futuro.
    * GRAVE  artículo mayor que el último artículo del código en el corpus, cuando el código está en corpus.db y su
             numeración en el corpus es fiable (ver ``limites_corpus``); si no, un tope orientativo y generoso
             (heredado del evaluador). Artículo 0.
    * GRAVE  ley con año futuro o anterior a 1800, número 0 o mayor que 3000, o número incoherente con su año según
             la numeración consecutiva de las leyes desde 1992 (reglas heredadas del evaluador y, además, contraste
             con las leyes «número + año» que aparecen en el texto del corpus: si el corpus trae la Ley N' de un año
             posterior con N' < N, una Ley N no puede ser de un año anterior; y al revés).
    * LEVE   ley de un año posterior a la última ley que aparece en el corpus cuyo número supera lo esperable
             (doble del ritmo medio anual observado en el corpus). Es una estimación: solo pide verificar.
    * LEVE   sentencia sin año, radicado, magistrado ponente o cita textual atribuida a una providencia que la
             persona no dio: hay que verificarlos en la fuente oficial.
  Una cita que la persona escribió (en esta conversación) nunca se marca: se informa en ``mencionada_por_usuario``.

LÍMITES CONOCIDOS (no se resuelven sin datos nuevos; ver docs/11-MOTOR-DE-FUENTES.md):
- No hay forma de saber, sin la relatoría, si una sentencia con número y año plausibles existe. «SU-1234 de 2015»
  no se marca: el corpus no trae sentencias (0) y no hay una tabla oficial del número máximo de sentencias SU por
  año. Una regla inventada sería peor que ninguna.
- «Ley 2999 de 2023» solo se marca como LEVE por la regla de ritmo (el corpus solo llega a leyes de 2021). Si el
  corpus incorpora leyes recientes, la regla de numeración consecutiva la volverá GRAVE sin tocar el código.
- La numeración consecutiva de las leyes desde 1992 es un supuesto, coherente con las ~170 leyes «número + año» del
  corpus actual (solo 4 observaciones discordantes, que se descartan como erratas de extracción).
- El corpus tiene vigencia PENDIENTE_VERIFICAR: un artículo agregado por una reforma posterior al texto del corpus
  podría salir marcado.
"""
from __future__ import annotations

import os
import re
import sqlite3
import unicodedata
from collections import defaultdict
from datetime import date

ANIO_PRIMERA_SENTENCIA_CC = 1992      # la Corte Constitucional empezó a fallar en 1992 (regla previa del evaluador)
ANIO_INICIO_NUMERACION_LEYES = 1992   # supuesto documentado arriba: desde 1992 las leyes se numeran en orden
FACTOR_RITMO_LEYES = 2.0              # margen sobre el ritmo medio anual de leyes observado en el corpus
SALTO_MAXIMO_ARTICULOS = 50           # un salto mayor en la numeración de un código se trata como ruido de extracción
COBERTURA_MINIMA_ARTICULOS = 0.9      # fracción de 1..N presente para confiar en el máximo del corpus
MINIMO_ARTICULOS = 20

GRAVE, LEVE = "grave", "leve"


# ------------------------------------------------------------------------------------------- texto --
def normalizar(texto: str) -> str:
    """Minúsculas, sin tildes y con espacios simples."""
    t = "".join(c for c in unicodedata.normalize("NFD", str(texto or "")) if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", t.lower())


def _plano(texto: str) -> str:
    """Minúsculas y sin tildes, carácter por carácter (conserva las posiciones para recortar la cita mostrada)."""
    return "".join(normalizar(ch) if not ch.isspace() else ch for ch in str(texto or ""))


def _anio_completo(a: str) -> int:
    n = int(a)
    if n < 100:
        return 1900 + n if n >= 90 else 2000 + n
    return n


# --------------------------------------------------------------------------------------- patrones --
_RE_SENTENCIA = re.compile(
    r"\b(?:sentencia\s+)?(?P<tipo>SU|C|T)\s?-\s?(?P<num>\d{1,6})(?P<resto>(?:\s*(?:de|del|/)\s*(?:a[ñn]o\s+)?(?P<anio>\d{4}|\d{2}))?)",
    re.I)
_RE_CSJ = re.compile(r"(?<![A-Za-z0-9])(?P<sala>SL|SC|SP|STC|STL|STP|AL|AC|AP)\s?-?\s?(?P<num>\d{1,6})\s?[-/]\s?(?P<anio>\d{4})(?!\d)")
_TOPE_SENTENCIA = {"C": 1500, "T": 2000, "SU": 1500}
_RE_ARTICULO = re.compile(r"\b(?:art[íi]culo|art\.)\s*(?P<num>\d{1,6})(?P<letra>[A-Za-z]?)\b(?P<cola>[^.;,\n]{0,60})", re.I)
_RE_LEY = re.compile(r"\bLey(?:\s+estatutaria|\s+org[áa]nica)?\s+(?:n[.º°o]*\s*)?(?P<num>\d{1,4})\s+de\s+(?P<anio>\d{4})\b", re.I)
_RE_DECRETO = re.compile(r"\bDecreto(?:\s*-?\s*Ley|\s+Legislativo)?\s+(?:n[.º°o]*\s*)?(?P<num>\d{1,5})\s+de\s+(?P<anio>\d{4})\b",
                         re.I)
_RE_ANTES_DECRETO = re.compile(r"decreto\s*-?\s*$", re.I)
_RE_RADICADO = re.compile(r"\b\d{5}-?\d{2}-?\d{2}-?\d{3}-?\d{4}-?\d{5}-?\d{2}\b|\b(?:radicado|rad\.?)\s*(?:n[.º°o]*\s*)?[\dA-Z][\dA-Z\-./]{6,}", re.I)
_RE_PONENTE = re.compile(r"\b(?:M\.\s?P\.|magistrad[oa]\s+ponente)\s*:?\s*(?:Dr\.?|Dra\.?)?\s*[A-ZÁÉÍÓÚ][\wáéíóúñ]+", re.I)
_RE_CITA_TEXTUAL_INVERSA = re.compile(
    r"(?:dijo|dice|señal[oó]|afirm[oó]|sostuvo|indic[oó]|expres[oó]|consider[oó])\s+(?:la corte|el consejo de estado|la sala|el tribunal)[^.\n]{0,40}?[:,]?\s*[«\"“]([^»\"”]{60,})[»\"”]",
    re.I)
_RE_CITA_TEXTUAL = re.compile(
    r"(?:la corte|el consejo de estado|la sala|el tribunal|la sentencia)[^.\n]{0,80}?(?:dijo|dice|señal[oó]|afirm[oó]|sostuvo|indic[oó]|expres[oó]|consider[oó])[^.\n]{0,40}?[:,]?\s*[«\"“]([^»\"”]{60,})[»\"”]",
    re.I)

# ¿La respuesta menciona normas o providencias? (para el aviso «confírmalas en la fuente oficial»)
_RE_HAY_CITAS = re.compile(
    r"\b(?:ley(?:\s+estatutaria|\s+org[áa]nica)?|decreto(?:\s*-?\s*ley)?|resoluci[óo]n|acuerdo|circular)\s+(?:n[.º°o]*\s*)?\d"
    r"|\b(?:art[íi]culos?|arts?\.)\s*\d"
    r"|\bc[óo]digo\s+(?:civil|penal|general|sustantivo|procesal|disciplinario|nacional|de\s+(?:comercio|procedimiento|la\s+infancia|infancia|minas|polic[íi]a|tr[áa]nsito))"
    r"|\b(?:CGP|CST|CPACA|C\.\s?P\.|C\.\s?C\.|E\.\s?T\.)(?![A-Za-z])|\bestatuto\s+tributario|\bconstituci[óo]n\s+pol[íi]tica"
    r"|\b(?:sentencia\s+)?(?:SU|C|T)\s?-\s?\d"
    r"|(?<![A-Za-z0-9])(?:SL|SC|SP|STC|STL|STP|AL|AC|AP)\s?-?\s?\d{1,6}\s?[-/]\s?\d{4}(?!\d)"
    r"|\bsentencia\s+(?:de\s+(?:unificaci[óo]n|tutela|casaci[óo]n|constitucionalidad)|del?\s+\d)"
    r"|\bauto\s+(?:n[.º°o]*\s*)?\d|\bauto\s+del?\s+\d"
    r"|\bradicad[oa]\s*(?:n[.º°o]*\s*)?[:\s]\s*\d|\brad\.\s*\d|\b\d{5}-?\d{2}-?\d{2}-?\d{3}-?\d{4}-?\d{5}-?\d{2}\b",
    re.I)

_RE_GRUPO_MARCAS = re.compile(r"\[([^\[\]\n]{1,60})\]")
_RE_SOLO_MARCAS = re.compile(r"^\s*F\s*\d+(?:\s*(?:,|;|y|-|–)\s*F\s*\d+)*\s*$", re.I)
_RE_MARCA = re.compile(r"F\s*(\d+)", re.I)


# ----------------------------------------------------------------------------- códigos y su corpus --
# (clave, nombre, patrón de la referencia tras «del…», patrón del título en corpus.db, tope orientativo o None)
# Los topes orientativos son los GENEROSOS que ya usaba el evaluador: solo marcan lo absurdo y se usan cuando el
# código no está en el corpus o su numeración allí no es fiable.
_CODIGOS = (
    ("constitucion", "la Constitución Política", r"(?:la\s+)?constituci[oó]n(?:\s+pol[ií]tica)?(?:\s+de\s+(?:colombia|1991))?\b|carta\s+pol[ií]tica",
     r"cons?titucion", 380),
    ("cpp", "el Código de Procedimiento Penal", r"c[oó]digo\s+de\s+procedimiento\s+penal|ley\s+906\b|c\.\s?p\.\s?p\.", None, 800),
    ("penal", "el Código Penal", r"c[oó]digo\s+penal\b(?!\s+militar)|ley\s+599\b", r"codigo penal", 700),
    ("cgp", "el Código General del Proceso", r"c[oó]digo\s+general\s+del\s+proceso|cgp\b|c\.\s?g\.\s?p\.?|ley\s+1564\b",
     r"codigo general del proceso", 800),
    ("cpt", "el Código Procesal del Trabajo", r"c[oó]digo\s+procesal\s+(?:del\s+trabajo|laboral)|c\.\s?p\.\s?t\.?(?:\s?y\s?(?:de\s+la\s+)?s\.\s?s\.?)?|cptss\b",
     r"procesal laboral|procesal del trabajo", None),
    ("cst", "el Código Sustantivo del Trabajo", r"c[oó]digo\s+sustantivo\s+del\s+trabajo|cst\b|c\.\s?s\.\s?t\.?",
     r"sustantivo del trabajo", 600),
    ("civil", "el Código Civil", r"c[oó]digo\s+civil\b|c\.\s?c\.(?!\s?[a-z]\.)|ley\s+57\s+de\s+1887", r"codigo civil", 3000),
    ("comercio", "el Código de Comercio", r"c[oó]digo\s+de\s+comercio|c\.\s?co\.?|decreto\s+410\s+de\s+1971", r"codigo de comercio", 3000),
    ("cpaca", "el CPACA", r"cpaca\b|c[oó]digo\s+de\s+procedimiento\s+administrativo|ley\s+1437\b", r"cpaca|procedimiento administrativo", 450),
    ("infancia", "el Código de la Infancia y la Adolescencia", r"c[oó]digo\s+de\s+(?:la\s+)?infancia\s+y\s+(?:la\s+)?adolescencia|ley\s+1098\b",
     r"infancia y adolescencia", None),
    ("minas", "el Código de Minas", r"c[oó]digo\s+de\s+minas|ley\s+685\b", r"codigo de minas", None),
    ("et", "el Estatuto Tributario", r"estatuto\s+tributario|e\.\s?t\.?(?![a-z])|decreto\s+624\s+de\s+1989", r"estatuto tributario", None),
    ("d2591", "el Decreto 2591 de 1991", r"decreto\s+2591\b", None, 62),
)
_RE_PREFIJO_COLA = re.compile(
    r"^\s*(?:[,(]?\s*(?:inciso|numeral|par[aá]grafo|literal|ordinal)\s+[\w°º]+\s*[,)]?\s*)*(?:,\s*)?(?:del|de\s+la|de\s+el|de)\s+",
    re.I)


def _codigo_de_cola(cola: str):
    """(clave, nombre, tope orientativo, fin) del código que sigue inmediatamente a «artículo N» (``fin``: dónde
    termina su nombre dentro de ``cola``); None si no se nombra un código conocido justo después (así «artículo 5 de la
    Ley 1755 de 2015 y el Código Civil» no se cruza)."""
    c = _plano(cola)
    m = _RE_PREFIJO_COLA.match(c)
    # Sin «del…» también vale el código escrito justo después: «art. 86 C.P.», «artículo 64 CST».
    resto = c[m.end():] if m else c.lstrip()
    base = len(c) - len(resto)
    m2 = re.match(r"^c\.\s?p\.(?![a-z]|\s?[a-z]\.)", resto)
    if m2:
        return ("cp_ambigua", "la C.P. (Constitución o Código Penal)", 700, base + m2.end())
    for clave, nombre, patron, _t, tope in _CODIGOS:
        m2 = re.match(r"^(?:" + patron + r")", resto)
        if m2:
            return (clave, nombre, tope, base + m2.end())
    return None


# ------------------------------------------------------------------------------- límites del corpus --
_RE_ENCABEZADO_ARTICULO = re.compile(r"(?:^|\n)\s*ART[IÍ]CULO\s+(\d{1,5})\s*(?:[A-Z]\b|-\d+)?\s*[°º.:o]", re.I)
_cache_corpus = {}


def _ruta_corpus(ruta: str = None) -> str:
    return ruta or os.getenv("PULLEX_CORPUS_DB", os.path.join("corpus", "corpus.db"))


def _max_fiable(numeros: set):
    """Último artículo de una numeración densa: se corta en el primer salto grande (ruido de extracción) y solo se
    acepta si 1..N está casi completo."""
    if len(numeros) < MINIMO_ARTICULOS:
        return None
    orden = sorted(n for n in numeros if n > 0)
    ultimo = orden[0]
    for n in orden[1:]:
        if n - ultimo > SALTO_MAXIMO_ARTICULOS:
            break
        ultimo = n
    presentes = sum(1 for n in orden if n <= ultimo)
    return ultimo if ultimo and presentes / ultimo >= COBERTURA_MINIMA_ARTICULOS else None


def leyes_en_texto(texto: str):
    """(número, año) de cada «Ley N de AAAA» del texto, sin contar «Decreto Ley N de AAAA»."""
    for m in _RE_LEY.finditer(texto or ""):
        if _RE_ANTES_DECRETO.search(texto[max(0, m.start() - 14):m.start()]):
            continue
        yield int(m.group("num")), int(m.group("anio"))


def _anclas_coherentes(pares) -> list:
    """Quita, de una en una, la observación con más contradicciones de orden (erratas de extracción) hasta que la
    numeración quede coherente: a mayor año, mayor número."""
    ps = sorted(set(p for p in pares if p[1] >= ANIO_INICIO_NUMERACION_LEYES and p[0] > 0))

    def choques(p, lista):
        return sum(1 for q in lista if (q[1] < p[1] and q[0] > p[0]) or (q[1] > p[1] and q[0] < p[0]))

    while ps:
        peor = max(ps, key=lambda p: choques(p, ps))
        if not choques(peor, ps):
            break
        ps.remove(peor)
    return ps


def limites_corpus(ruta: str = None) -> dict:
    """Límites derivados del texto del corpus (solo lectura, en memoria por archivo y fecha de modificación):
    ``articulos``: {clave de código: (último artículo, título de la fuente)} solo para numeraciones fiables;
    ``leyes``: anclas (número, año) coherentes; ``ritmo``: leyes por año (media observada). Vacío si no hay corpus."""
    ruta = _ruta_corpus(ruta)
    vacio = {"articulos": {}, "leyes": [], "ritmo": None}
    try:
        st = os.stat(ruta)
    except OSError:
        return vacio
    clave_cache = (os.path.abspath(ruta), st.st_mtime_ns, st.st_size)
    if clave_cache in _cache_corpus:
        return _cache_corpus[clave_cache]
    try:
        con = sqlite3.connect(f"file:{os.path.abspath(ruta)}?mode=ro", uri=True)
    except sqlite3.Error:
        return vacio
    articulos, pares = {}, []
    try:
        fuentes_codigo = con.execute("SELECT id, titulo FROM fuentes").fetchall()
        for fid, titulo in fuentes_codigo:
            tn = normalizar(titulo)
            clave = next((k for k, _n, _p, pt, _t in _CODIGOS if pt and re.search(pt, tn)), None)
            numeros = set()
            for (texto,) in con.execute("SELECT texto FROM fragmentos WHERE fuente_id=?", (fid,)):
                if clave:
                    numeros.update(int(x) for x in _RE_ENCABEZADO_ARTICULO.findall(texto or ""))
                pares.extend(leyes_en_texto(texto or ""))
            maximo = _max_fiable(numeros) if clave else None
            if maximo and clave not in articulos:
                articulos[clave] = (maximo, titulo)
    except sqlite3.Error:
        return vacio
    finally:
        con.close()
    anclas = _anclas_coherentes(pares)
    ritmo = None
    if len(anclas) >= 2 and anclas[-1][1] > anclas[0][1]:
        ritmo = (anclas[-1][0] - anclas[0][0]) / (anclas[-1][1] - anclas[0][1])
    salida = {"articulos": articulos, "leyes": anclas, "ritmo": ritmo}
    _cache_corpus.clear()
    _cache_corpus[clave_cache] = salida
    return salida


# ------------------------------------------------------------------------------------- extracción --
def extraer_citas(texto: str) -> list:
    """Lista de dicts {"cita", "tipo", ...} con lo que parece una cita jurídica del texto."""
    texto = texto or ""
    citas = []
    for m in _RE_SENTENCIA.finditer(texto):
        anio = _anio_completo(m.group("anio")) if m.group("anio") else None
        citas.append({"tipo": "sentencia", "cita": m.group(0).strip(), "alta": m.group("tipo").upper(),
                      "numero": int(m.group("num")), "anio": anio})
    for m in _RE_CSJ.finditer(texto):
        citas.append({"tipo": "providencia_csj", "cita": m.group(0).strip(), "alta": m.group("sala").upper(),
                      "numero": int(m.group("num")), "anio": int(m.group("anio"))})
    for m in _RE_ARTICULO.finditer(texto):
        cola = m.group("cola") or ""
        codigo = _codigo_de_cola(cola)
        mostrada = m.group(0)[:len(m.group(0)) - len(cola)] + (cola[:codigo[3]] if codigo else "")
        citas.append({"tipo": "articulo", "cita": mostrada.strip(), "numero": int(m.group("num")),
                      "cola": cola, "codigo": codigo})
    for m in _RE_LEY.finditer(texto):
        if _RE_ANTES_DECRETO.search(texto[max(0, m.start() - 14):m.start()]):
            continue            # «Decreto Ley 2150 de 1995» es un decreto, no la Ley 2150
        citas.append({"tipo": "ley", "cita": m.group(0), "numero": int(m.group("num")), "anio": int(m.group("anio"))})
    for m in _RE_DECRETO.finditer(texto):
        citas.append({"tipo": "decreto", "cita": m.group(0), "numero": int(m.group("num")), "anio": int(m.group("anio"))})
    for m in _RE_RADICADO.finditer(texto):
        citas.append({"tipo": "radicado", "cita": m.group(0).strip()})
    for m in _RE_PONENTE.finditer(texto):
        citas.append({"tipo": "ponente", "cita": m.group(0).strip()})
    for rx in (_RE_CITA_TEXTUAL, _RE_CITA_TEXTUAL_INVERSA):
        for m in rx.finditer(texto):
            citas.append({"tipo": "cita_textual", "cita": m.group(1)[:80] + "…", "literal": m.group(1)})
    return citas


def clave_de(c: dict) -> tuple:
    """Clave canónica para comparar la misma cita escrita de formas distintas («T-760/08» = «T-760 de 2008»)."""
    t = c["tipo"]
    if t in ("sentencia", "providencia_csj"):
        return (t, c["alta"], c["numero"], c.get("anio"))
    if t == "articulo":
        return (t, c["numero"], (c.get("codigo") or (None,))[0])
    if t in ("ley", "decreto"):
        return (t, c["numero"], c["anio"])
    if t == "radicado":
        return (t, re.sub(r"\D", "", c["cita"]))
    if t == "cita_textual":
        return (t, normalizar(c.get("literal", c["cita"]))[:60])
    return (t, normalizar(c["cita"]))


def _ya_dada(c: dict, claves: set, texto_norm: str) -> bool:
    if not claves and not texto_norm:
        return False
    k = clave_de(c)
    if k in claves:
        return True
    if c["tipo"] == "articulo" and (c["tipo"], c["numero"], None) in claves:
        return True         # la persona escribió «artículo 4500» sin decir de qué código
    return bool(texto_norm) and normalizar(c["cita"]) in texto_norm


# ---------------------------------------------------------------------------------------- reglas --
def _reglas(c: dict, anio_actual: int, lim: dict):
    """(motivo, gravedad) o None. ``gravedad``: GRAVE (forma o número imposible) o LEVE (verificar)."""
    t = c["tipo"]
    if t == "sentencia":
        tope = _TOPE_SENTENCIA.get(c["alta"], 2000)
        if c["numero"] == 0 or c["numero"] > tope:
            return f"número improbable para una sentencia {c['alta']} (más de {tope} o cero)", GRAVE
        if c["anio"] is None:
            return "sentencia sin año: no se puede ubicar en la relatoría", LEVE
        if c["anio"] > anio_actual:
            return f"año {c['anio']} posterior al año en curso ({anio_actual}): esa sentencia no puede existir", GRAVE
        if c["anio"] < ANIO_PRIMERA_SENTENCIA_CC:
            return (f"año {c['anio']} anterior a {ANIO_PRIMERA_SENTENCIA_CC}, cuando la Corte Constitucional empezó a "
                    "fallar"), GRAVE
        return None
    if t == "providencia_csj":
        if c["anio"] > anio_actual:
            return f"año {c['anio']} posterior al año en curso ({anio_actual})", GRAVE
        if c["numero"] == 0:
            return "providencia número cero", GRAVE
        return None
    if t == "articulo":
        if c["numero"] == 0:
            return "artículo cero no existe", GRAVE
        cod = c.get("codigo")
        if not cod:
            return None
        clave, nombre, tope, _fin = cod
        if clave in lim["articulos"]:
            maximo, _titulo = lim["articulos"][clave]
            if c["numero"] > maximo:
                return (f"en el corpus de PULLEX, {nombre} llega hasta el artículo {maximo} "
                        "(texto con vigencia pendiente de verificar)"), GRAVE
            return None
        if tope and c["numero"] > tope:
            return f"número muy por encima de lo que tiene {nombre} (tope orientativo {tope})", GRAVE
        return None
    if t == "ley":
        n, a = c["numero"], c["anio"]
        if a > anio_actual:
            return f"año {a} posterior al año en curso ({anio_actual})", GRAVE
        if a < 1800:
            return f"año {a} imposible", GRAVE
        if n == 0 or n > 3000:
            return "número de ley improbable", GRAVE
        if a >= 2006 and n < 1000:
            return "número de ley incoherente con el año (desde 2006 las leyes pasan de 1000)", GRAVE
        if 1992 <= a <= 2004 and n >= 1000:
            return "número de ley incoherente con el año (hasta 2004 no llegaban a 1000)", GRAVE
        if a <= 2018 and n >= 2000:
            return "número de ley incoherente con el año (las leyes 2000 en adelante son de 2019 o después)", GRAVE
        if a >= ANIO_INICIO_NUMERACION_LEYES and lim["leyes"]:
            posteriores = [p for p in lim["leyes"] if p[1] > a and p[0] < n]
            if posteriores:
                p = min(posteriores)
                return (f"número incoherente con el año: el corpus cita la Ley {p[0]} de {p[1]} y las leyes se numeran "
                        f"en orden, así que una ley de {a} no puede llevar el número {n}"), GRAVE
            anteriores = [p for p in lim["leyes"] if p[1] < a and p[0] > n]
            if anteriores:
                p = max(anteriores)
                return (f"número incoherente con el año: el corpus cita la Ley {p[0]} de {p[1]} y las leyes se numeran "
                        f"en orden, así que la Ley {n} no puede ser de {a}"), GRAVE
            ultimo = max(lim["leyes"], key=lambda p: (p[1], p[0]))
            if lim["ritmo"] and a > ultimo[1]:
                tope = ultimo[0] + FACTOR_RITMO_LEYES * lim["ritmo"] * (a - ultimo[1] + 1)
                if n > tope:
                    return (f"número muy alto para {a}: la ley más reciente del corpus es la {ultimo[0]} de {ultimo[1]} "
                            f"y el ritmo observado no llega a {int(tope)} en {a}; verifica que exista"), LEVE
        return None
    if t == "decreto":
        if c["anio"] > anio_actual:
            return f"año {c['anio']} posterior al año en curso ({anio_actual})", GRAVE
        if c["anio"] < 1800:
            return f"año {c['anio']} imposible", GRAVE
        if c["numero"] == 0:
            return "decreto número cero", GRAVE
        return None
    if t == "radicado":
        return "radicado que la persona no dio: verifícalo en la Rama Judicial; un radicado no se debe inventar", LEVE
    if t == "ponente":
        return "magistrado ponente: verifícalo en la relatoría; un ponente no se debe inventar", LEVE
    if t == "cita_textual":
        return "cita textual atribuida a una providencia: verifica la literalidad en la fuente oficial", LEVE
    return None


def _evaluar(texto: str, permitidas: str, hoy: date = None, ruta_corpus: str = None, material: str = ""):
    anio_actual = (hoy or date.today()).year
    lim = limites_corpus(ruta_corpus)
    dadas = extraer_citas(permitidas or "")
    claves_usuario = {clave_de(c) for c in dadas}
    usuario_norm = normalizar(permitidas)
    claves_material = {clave_de(c) for c in extraer_citas(material)} if material else set()
    hallazgos, del_usuario, vistos = [], [], set()
    for c in extraer_citas(texto):
        if _ya_dada(c, claves_usuario, usuario_norm):
            if c["cita"] not in del_usuario:
                del_usuario.append(c["cita"])
            continue
        r = _reglas(c, anio_actual, lim)
        if not r:
            continue
        motivo, gravedad = r
        if gravedad == LEVE and clave_de(c) in claves_material:
            continue            # el dato está en el material recuperado: se ve en «Fuentes consultadas»
        k = (c["tipo"], normalizar(c["cita"]))
        if k in vistos:
            continue
        vistos.add(k)
        hallazgos.append({"cita": c["cita"], "tipo": c["tipo"], "motivo": motivo, "gravedad": gravedad})
    return hallazgos, del_usuario


def citas_sospechosas(texto: str, permitidas: str = "", hoy: date = None, ruta_corpus: str = None) -> list:
    """API del evaluador (evaluacion/evaluar_calidad.py). Cada hallazgo: {"cita", "tipo", "motivo", "severidad"} con
    severidad «grave» o «aviso». ``permitidas`` es lo que la persona ya dio: eso no se marca. NO comprueba que la
    sentencia exista."""
    hallazgos, _ = _evaluar(texto, permitidas, hoy, ruta_corpus)
    return [{"cita": h["cita"], "tipo": h["tipo"], "motivo": h["motivo"],
             "severidad": "grave" if h["gravedad"] == GRAVE else "aviso"} for h in hallazgos]


def marcas_huerfanas(respuesta: str, frags) -> list:
    """Marcas [F#] de la respuesta que no corresponden a ningún fragmento entregado al modelo, en orden de aparición."""
    validas = {str(f.get("ref") or "").upper() for f in (frags or [])}
    salida = []
    for g in _RE_GRUPO_MARCAS.finditer(respuesta or ""):
        if not _RE_SOLO_MARCAS.match(g.group(1)):
            continue
        for n in _RE_MARCA.findall(g.group(1)):
            ref = f"F{int(n)}"
            if ref not in validas and ref not in salida:
                salida.append(ref)
    return salida


def hay_citas(respuesta: str) -> bool:
    return bool(_RE_HAY_CITAS.search(respuesta or ""))


def revisar(respuesta: str, frags=None, texto_usuario: str = "", *, hoy: date = None, ruta_corpus: str = None) -> dict:
    """Revisión de forma para el chat. Contrato del evento SSE ``citas``:
    {"hay_citas": bool, "huerfanas": ["F9"], "sospechosas": [{"cita", "motivo", "gravedad": "grave"|"leve"}],
     "mencionada_por_usuario": ["…"]}. Nada de esto es una verificación de existencia ni de vigencia."""
    frags = list(frags or [])
    material = "\n".join(str(f.get("texto") or "") + "\n" + str(f.get("titulo") or "") for f in frags)
    hallazgos, del_usuario = _evaluar(respuesta, texto_usuario, hoy, ruta_corpus, material)
    huerfanas = marcas_huerfanas(respuesta, frags)
    sospechosas = [{"cita": h["cita"], "motivo": h["motivo"], "gravedad": h["gravedad"]} for h in hallazgos]
    return {"hay_citas": bool(hay_citas(respuesta) or huerfanas or sospechosas or del_usuario),
            "huerfanas": huerfanas, "sospechosas": sospechosas, "mencionada_por_usuario": del_usuario}
