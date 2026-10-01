"""
PULLEX IA — Motor de fuentes (corpus propio con SQLite FTS5 / BM25)
====================================================================
Índice local de códigos, leyes, decretos, sentencias, plantillas y doctrina, sin claves externas.
Lo usa el chat para entregar al modelo fragmentos numerados [F1]..[F6] con su título, tipo, fecha
y estado de vigencia, y para mostrar al usuario las "Fuentes consultadas" de cada respuesta.

- Base: archivo SQLite en PULLEX_CORPUS_DB (por defecto corpus/corpus.db). Si no existe, el chat
  funciona igual (sin fragmentos) y se intenta el corpus vectorial antiguo (chromadb + voyage).
- Tablas: `fuentes` (metadatos por documento) y `fragmentos` (FTS5 con remove_diacritics, así
  "peticion" encuentra "petición").
- Nada aquí depende de la API de IA. La ingesta está en scripts/ingesta_corpus.py.

Reglas de vigencia (docs/11-MOTOR-DE-FUENTES.md):
- Todo documento entra como PENDIENTE_VERIFICAR. Solo una persona lo marca VIGENTE_VERIFICADA
  (scripts/ingesta_corpus.py --verificar ID) después de confirmarlo en la fuente oficial.
- Una verificación de hace más de 12 meses vuelve a contar como PENDIENTE_VERIFICAR.
"""
import fnmatch
import hashlib
import os
import re
import sqlite3
import unicodedata
from contextlib import closing
from datetime import datetime, timezone, timedelta

TIPOS = ("codigo", "ley", "decreto", "sentencia", "plantilla", "doctrina", "otro")
ESTADOS = ("VIGENTE_VERIFICADA", "PENDIENTE_VERIFICAR", "DESACTUALIZADA", "DEROGADA")
VIGENCIA_DIAS = 365          # "más de 12 meses" → pendiente de verificar
TAM_FRAGMENTO = 1200
SOLAPE = 200
MAX_FRAGMENTOS = 6
MAX_POR_FUENTE = 3

ESQUEMA = f"""
CREATE TABLE IF NOT EXISTS fuentes(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    titulo TEXT NOT NULL,
    tipo TEXT NOT NULL CHECK (tipo IN ({",".join(repr(t) for t in TIPOS)})),
    autoridad TEXT,
    numero TEXT,
    anio INTEGER,
    fecha_archivo TEXT,
    origen TEXT NOT NULL UNIQUE,
    url TEXT,
    estado_vigencia TEXT NOT NULL DEFAULT 'PENDIENTE_VERIFICAR'
        CHECK (estado_vigencia IN ({",".join(repr(e) for e in ESTADOS)})),
    verificado_en TEXT,
    sha256 TEXT,
    indexado_en TEXT);
CREATE VIRTUAL TABLE IF NOT EXISTS fragmentos USING fts5(
    texto, fuente_id UNINDEXED, ubicacion UNINDEXED,
    tokenize = 'unicode61 remove_diacritics 2');
"""


def ruta_db() -> str:
    return os.getenv("PULLEX_CORPUS_DB", os.path.join("corpus", "corpus.db"))


def abrir(ruta: str = None, crear: bool = True) -> sqlite3.Connection:
    """Conexión de escritura (ingesta). Crea el esquema si no existe."""
    ruta = ruta or ruta_db()
    if crear:
        os.makedirs(os.path.dirname(os.path.abspath(ruta)), exist_ok=True)
    con = sqlite3.connect(ruta)
    con.row_factory = sqlite3.Row
    con.executescript(ESQUEMA)
    return con


def _abrir_lectura(ruta: str):
    """Solo lectura: el chat nunca modifica el corpus. None si el archivo no existe."""
    if not ruta or not os.path.isfile(ruta):
        return None
    con = sqlite3.connect(f"file:{os.path.abspath(ruta)}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    return con


def disponible(ruta: str = None) -> bool:
    con = _abrir_lectura(ruta or ruta_db())
    if con is None:
        return False
    with closing(con):
        try:
            return con.execute("SELECT 1 FROM fragmentos LIMIT 1").fetchone() is not None
        except sqlite3.DatabaseError:
            return False


# ------------------------------------------------------------- normalización --
def sin_tildes(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", str(texto or ""))
                   if unicodedata.category(c) != "Mn")


def _norm(texto: str) -> str:
    return sin_tildes(texto).lower()


# --------------------------------------------- clasificación por nombre --
_RE_SENTENCIA_CC = re.compile(
    r"(?<![A-Z0-9])(SU|C|T|A)\s*[-–_ ]\s*(\d{1,4})\s*(?:[-–_/ ]\s*|\s+DE(?:L)?\s+)(\d{4}|\d{2})(?!\d)", re.I)
_RE_SENTENCIA_CSJ = re.compile(r"(?<![A-Z0-9])(SL|SC|SP|STC|STL|STP|AL|AC|AP)\s*[-–_ ]?\s*(\d{1,6})\s*[-–_/ ]\s*(\d{4})(?!\d)", re.I)
_RE_LEY = re.compile(r"\bley(?:\s+estatutaria|\s+org[aá]nica)?\s*(?:n[°º.o]*\s*)?(\d{1,5})\s*(?:de(?:l)?\s+|[-–_/ ]\s*)(\d{4})\b", re.I)
_RE_DECRETO = re.compile(r"\bdecreto(?:\s*[-–]?\s*ley)?\s*(?:n[°º.o]*\s*)?(\d{1,5})\s*(?:de(?:l)?\s+|[-–_/ ]\s*)(\d{4})\b", re.I)
_RE_ANIO = re.compile(r"(?<!\d)(19[0-9]{2}|20[0-9]{2})(?!\d)")

# Carpetas del corpus del usuario (LEXCOL_CORPUS en Google Drive) → tipo por defecto.
TIPO_POR_CARPETA = (
    ("codigo", "codigo"), ("ley", "ley"), ("decreto", "decreto"), ("jurisprudencia", "sentencia"),
    ("sentencia", "sentencia"), ("plantilla", "plantilla"), ("modelo", "plantilla"),
    ("doctrina", "doctrina"), ("regimen", "otro"),
)


def _anio(texto: str):
    try:
        n = int(texto)
    except (TypeError, ValueError):
        return None
    if n < 100:  # T-760-08 → 2008; C-355-06 → 2006
        n += 2000 if n <= (datetime.now().year % 100) else 1900
    return n


def _limpiar_titulo(nombre: str) -> str:
    base = os.path.splitext(os.path.basename(nombre))[0]
    base = re.sub(r"[_]+", " ", base)
    return re.sub(r"\s+", " ", base).strip()[:200] or "Documento"


def clasificar_nombre(nombre: str, carpeta: str = "") -> dict:
    """Clasifica un archivo por su nombre (y, si no basta, por su carpeta).

    >>> clasificar_nombre("SENTENCIA C-420 DE 2020.pdf")["numero"]
    'C-420'
    """
    titulo = _limpiar_titulo(nombre)
    t = titulo
    tn = _norm(t)
    r = {"titulo": titulo, "tipo": "otro", "autoridad": None, "numero": None, "anio": None}

    m = _RE_SENTENCIA_CC.search(t)
    if m and ("sentencia" in tn or "auto" in tn or "corte" in tn or re.match(r"\s*(SU|C|T|A)\s*[-–_ ]\s*\d", t, re.I)):
        pref = m.group(1).upper()
        r.update(tipo="sentencia", autoridad="Corte Constitucional",
                 numero=f"{pref}-{int(m.group(2)):03d}" if pref != "SU" else f"SU-{int(m.group(2)):03d}",
                 anio=_anio(m.group(3)))
        # 3 dígitos es la convención de la Corte (T-025, C-355); si el número tiene más, se respeta.
        if len(m.group(2)) > 3:
            r["numero"] = f"{pref}-{m.group(2)}"
        return r
    m = _RE_SENTENCIA_CSJ.search(t)
    if m:
        r.update(tipo="sentencia", autoridad="Corte Suprema de Justicia",
                 numero=f"{m.group(1).upper()}{m.group(2)}-{m.group(3)}", anio=_anio(m.group(3)))
        return r
    if "consejo de estado" in tn and ("sentencia" in tn or "radicado" in tn or "auto" in tn):
        r.update(tipo="sentencia", autoridad="Consejo de Estado")
        a = _RE_ANIO.search(t)
        r["anio"] = int(a.group(1)) if a else None
        return r
    m = _RE_DECRETO.search(t)
    if m:
        r.update(tipo="decreto", autoridad="Gobierno Nacional", numero=m.group(1), anio=int(m.group(2)))
        return r
    m = _RE_LEY.search(t)
    if m:
        r.update(tipo="ley", autoridad="Congreso de la República", numero=m.group(1), anio=int(m.group(2)))
        return r
    if re.search(r"\bcodigo\b", tn):
        r["tipo"] = "codigo"
    elif "constitucion politica" in tn or tn.startswith("constitucion"):
        r.update(tipo="otro", autoridad="Asamblea Nacional Constituyente", anio=1991)
        return r
    elif re.search(r"\b(plantilla|modelo|formato|minuta)\b", tn):
        r["tipo"] = "plantilla"
    elif re.search(r"\b(doctrina|tratado|manual|libro|ensayo)\b", tn):
        r["tipo"] = "doctrina"
    elif re.search(r"\bsentencia\b", tn):
        r["tipo"] = "sentencia"
    else:
        cn = _norm(carpeta)
        for clave, tipo in TIPO_POR_CARPETA:
            if clave in cn:
                r["tipo"] = tipo
                break
    a = _RE_ANIO.search(t)
    if a and r["tipo"] in ("codigo", "sentencia", "doctrina"):
        r["anio"] = int(a.group(1))
    return r


# -------------------------------------------- exclusión de datos de personas --
# El corpus es material de consulta general. Nunca se indexan expedientes ni escritos de
# clientes: el texto indexado se muestra a TODOS los usuarios como fragmento de fuente.
_PALABRAS_CLIENTE = ("cliente", "expediente")
_TIPOS_ESCRITO = (
    r"TUTELA|ACCI[OÓ]N\s+DE\s+TUTELA|DEMANDA|DERECHO\s+DE\s+PETICI[OÓ]N|PETICI[OÓ]N|DENUNCIA|CONTRATO|"
    r"PODER|RECURSO|CONTESTACI[OÓ]N|QUERELLA|SOLICITUD|DESACATO|ACCI[OÓ]N|MEMORIAL|IMPUGNACI[OÓ]N|"
    r"APELACI[OÓ]N|REPOSICI[OÓ]N|INCIDENTE|ALEGATOS?|CONCILIACI[OÓ]N|LIQUIDACI[OÓ]N|DESCARGOS|"
    r"QUEJA|RECLAMACI[OÓ]N|RECLAMO|HABEAS\s+CORPUS|CONCEPTO|AUDIENCIA|ESCRITO")
# Palabras que NO son nombres de persona aunque estén en mayúsculas ("MODELO DE TUTELA").
_GENERICAS = {
    "MODELO", "MODELOS", "PLANTILLA", "PLANTILLAS", "FORMATO", "FORMATOS", "EJEMPLO", "EJEMPLOS", "MINUTA",
    "GUIA", "MANUAL", "CODIGO", "LEY", "DECRETO", "SENTENCIA", "SENTENCIAS", "JURISPRUDENCIA", "DOCTRINA",
    "REGIMEN", "REGIMENES", "CASO", "CASOS", "NUEVO", "NUEVA", "BORRADOR", "FINAL", "COPIA", "ANEXO",
    "CORTE", "CONSEJO", "ESTADO", "CONSTITUCIONAL", "SUPREMA", "JUZGADO", "TRIBUNAL", "FISCALIA",
    "PENAL", "CIVIL", "LABORAL", "FAMILIA", "ADMINISTRATIVO", "COMERCIAL", "PROCESAL", "GENERAL",
    "CONTRA", "PARA", "POR", "SOBRE", "CON", "SIN", "TIPO", "BASICO", "COMPLETO", "ESTRUCTURA",
    "ACCION", "DERECHO", "DERECHOS", "PRINCIPIO", "INCIDENTE", "TUTELA", "DEMANDA", "PETICION",
    "RECURSO", "CONTRATO", "PODER", "SOLICITUD", "DENUNCIA", "EPS", "SAS", "LTDA", "COLOMBIA",
    "TITULOS", "VALORES", "SEGURIDAD", "SOCIAL", "PROPIEDAD", "INTELECTUAL", "MARCAS", "CONSUMIDOR",
    "TRIBUTARIO", "PENSIONES", "SALUD", "NORMAS", "LEYES", "DECRETOS", "CODIGOS", "CORPUS", "LEXCOL",
    "PULLEX", "RESPONSABILIDAD", "EXTRACONTRACTUAL", "CONTRACTUAL", "PRUEBAS", "PROBATORIO",
    "SUCESIONES", "INSOLVENCIA", "AMBIENTAL", "AGRARIO", "INTERNACIONAL", "PUBLICO", "PRIVADO",
    "NOTARIAL", "DISCIPLINARIO", "POLICIA", "TRANSITO", "ARRENDAMIENTO", "COMPRAVENTA", "SOCIEDADES",
    "OTROS", "VARIOS", "ARCHIVO", "ARCHIVOS", "DOCUMENTOS", "CONTRATACION", "ESTATAL", "PROCESO",
}
_CONECTORES = {"DE", "DEL", "LA", "LAS", "LOS", "Y"}
_PALABRA_MAY = r"[A-ZÁÉÍÓÚÑÜ][A-ZÁÉÍÓÚÑÜ]+"
_RE_NOMBRE_ESCRITO = re.compile(
    r"^\s*(?P<nombre>" + _PALABRA_MAY + r"(?:\s+" + _PALABRA_MAY + r"){1,5})\s*[-–_.,:]*\s*(?:" + _TIPOS_ESCRITO + r")\b")
_PALABRA_TIT = r"[A-ZÁÉÍÓÚÑ][a-záéíóúñü]+"
_RE_NOMBRE_TITULO_ESCRITO = re.compile(
    r"^\s*(?P<nombre>" + _PALABRA_TIT + r"(?:\s+(?:de|del|la|las|los|y)?\s*" + _PALABRA_TIT + r"){1,4})\s*[-–_]+\s*(?:"
    + _TIPOS_ESCRITO + r")\b", re.I)


def _parece_nombre(palabras) -> bool:
    utiles = [p for p in palabras if sin_tildes(p).upper() not in _CONECTORES]
    if len(utiles) < 2:
        return False
    return not any(sin_tildes(p).upper() in _GENERICAS for p in utiles)


_RE_SOLO_NOMBRE = re.compile(r"^" + _PALABRA_MAY + r"(?:\s+" + _PALABRA_MAY + r"){1,4}$")


def tiene_palabra_cliente(componente: str) -> bool:
    bn = _norm(re.sub(r"[_]+", " ", componente))
    return any(re.search(r"\b" + p, bn) for p in _PALABRAS_CLIENTE)


def parece_de_persona(componente: str, es_carpeta: bool = False) -> bool:
    """True si un nombre de carpeta o archivo parece de un cliente o una persona real."""
    base = os.path.splitext(componente)[0] if "." in componente[-6:] else componente
    base = re.sub(r"[_]+", " ", base).strip()
    if tiene_palabra_cliente(base):
        return True
    # Carpeta cuyo nombre es solo un nombre propio en mayúsculas ("CARLOS ANDRES ROJAS"): en un
    # archivo de abogado casi siempre es la carpeta de un cliente. Prefiere excluir de más.
    if es_carpeta and _RE_SOLO_NOMBRE.match(base) and _parece_nombre(base.split()):
        return True
    m = _RE_NOMBRE_ESCRITO.match(base)
    if m and _parece_nombre(m.group("nombre").split()):
        return True
    m = _RE_NOMBRE_TITULO_ESCRITO.match(base)
    if m and not base.isupper():
        palabras = [p for p in m.group("nombre").split() if p[:1].isupper()]
        if _parece_nombre(palabras):
            return True
    return False


def patrones_exclusion(extra=None) -> list:
    """Lista configurable: PULLEX_CORPUS_EXCLUIR (separada por comas) y corpus/excluir.txt
    (un patrón por línea; '#' para comentarios). Patrones glob sin distinguir mayúsculas,
    comparados contra la ruta relativa completa y contra cada carpeta o archivo."""
    pats = [p.strip() for p in os.getenv("PULLEX_CORPUS_EXCLUIR", "").split(",") if p.strip()]
    archivo = os.getenv("PULLEX_CORPUS_EXCLUIR_ARCHIVO", os.path.join("corpus", "excluir.txt"))
    if os.path.isfile(archivo):
        with open(archivo, encoding="utf-8") as f:
            pats += [l.strip() for l in f if l.strip() and not l.lstrip().startswith("#")]
    return pats + list(extra or [])


def _coincide(pat: str, rel: str, partes) -> bool:
    pn = _norm(pat)
    return (fnmatch.fnmatch(_norm(rel), pn) or any(fnmatch.fnmatch(_norm(p), pn) for p in partes)
            or ("*" not in pn and "?" not in pn and pn in _norm(rel)))


def es_excluido(ruta_relativa: str, patrones=None):
    """Devuelve el motivo (str) si la ruta NO debe indexarse; None si se puede indexar.

    Orden: (1) "CLIENTE"/"EXPEDIENTE" en cualquier carpeta o archivo → siempre excluido;
    (2) patrones de la lista de exclusión; (3) patrones "!..." de la lista = permitir (solo
    anulan la heurística de nombres, nunca la regla 1); (4) heurística de nombres de persona."""
    partes = [p for p in re.split(r"[\\/]+", ruta_relativa) if p]
    rel = "/".join(partes)
    if any(tiene_palabra_cliente(p) for p in partes):
        return "carpeta o archivo de cliente/expediente"
    patrones = list(patrones or [])
    for pat in (p for p in patrones if not p.startswith("!")):
        if _coincide(pat, rel, partes):
            return f"lista de exclusión ({pat})"
    if any(_coincide(p[1:], rel, partes) for p in patrones if p.startswith("!") and len(p) > 1):
        return None
    for i, p in enumerate(partes):
        if parece_de_persona(p, es_carpeta=i < len(partes) - 1):
            return "parece de un cliente o una persona real"
    return None


# --------------------------------------------------------- vigencia --
def _fecha(texto):
    if not texto:
        return None
    try:
        d = datetime.fromisoformat(str(texto).replace("Z", "+00:00"))
    except ValueError:
        return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def estado_efectivo(estado: str, verificado_en: str = None, ahora: datetime = None) -> str:
    """Una verificación vencida (más de 12 meses) o ausente no cuenta como vigente."""
    ahora = ahora or datetime.now(timezone.utc)
    if estado == "VIGENTE_VERIFICADA":
        v = _fecha(verificado_en)
        if not v or ahora - v > timedelta(days=VIGENCIA_DIAS):
            return "PENDIENTE_VERIFICAR"
    return estado if estado in ESTADOS else "PENDIENTE_VERIFICAR"


def estado_inicial(fecha_archivo: str = None, verificado_en: str = None, ahora: datetime = None) -> str:
    """Estado al indexar. Sin verificación humana reciente → PENDIENTE_VERIFICAR (también si el
    archivo tiene más de 12 meses, como varios códigos del Drive de febrero de 2024)."""
    ahora = ahora or datetime.now(timezone.utc)
    fa = _fecha(fecha_archivo)
    if fa and ahora - fa > timedelta(days=VIGENCIA_DIAS):
        return "PENDIENTE_VERIFICAR"
    return estado_efectivo("VIGENTE_VERIFICADA", verificado_en, ahora) if verificado_en else "PENDIENTE_VERIFICAR"


# ---------------------------------------------------------- troceo --
def trocear(texto: str, tam: int = TAM_FRAGMENTO, solape: int = SOLAPE) -> list:
    """Fragmentos de ~tam caracteres con solape, cortando en espacios cuando se puede."""
    texto = re.sub(r"[ \t\r\f\v]+", " ", texto or "")
    texto = re.sub(r"\n\s*\n+", "\n\n", texto).strip()
    if not texto:
        return []
    if len(texto) <= tam:
        return [texto]
    trozos, i = [], 0
    while i < len(texto):
        fin = min(len(texto), i + tam)
        if fin < len(texto):
            corte = max(texto.rfind("\n", i + tam // 2, fin), texto.rfind(" ", i + tam // 2, fin))
            if corte > i:
                fin = corte
        trozo = texto[i:fin].strip()
        if trozo:
            trozos.append(trozo)
        if fin >= len(texto):
            break
        sig = fin - solape
        if sig > i:
            ini_palabra = texto.find(" ", sig, fin)
            sig = ini_palabra + 1 if ini_palabra != -1 else sig
        i = max(sig, i + 1)
    return trozos


# --------------------------------------------------------- indexación --
def indexar(con, *, origen: str, nombre: str, paginas, carpeta: str = "", fecha_archivo: str = None,
            url: str = None, sha256: str = None, meta: dict = None) -> dict:
    """Indexa un documento ya extraído. `paginas`: lista de (ubicacion, texto).
    Idempotente por `origen`: mismo contenido → no hace nada; contenido nuevo → reemplaza los
    fragmentos y vuelve a PENDIENTE_VERIFICAR (cambió el texto, hay que verificar otra vez)."""
    paginas = [(u, t) for u, t in paginas if (t or "").strip()]
    if sha256 is None:
        h = hashlib.sha256()
        for u, t in paginas:
            h.update(((u or "") + "\x00" + t).encode("utf-8"))
        sha256 = h.hexdigest()
    clas = {**clasificar_nombre(nombre, carpeta), **(meta or {})}
    if clas.get("tipo") not in TIPOS:
        clas["tipo"] = "otro"
    previa = con.execute("SELECT id, sha256 FROM fuentes WHERE origen=?", (origen,)).fetchone()
    if previa and previa["sha256"] == sha256:
        return {"id": previa["id"], "accion": "sin_cambios", "fragmentos": 0}
    ahora = datetime.now(timezone.utc).isoformat(timespec="seconds")
    estado = estado_inicial(fecha_archivo)
    campos = (clas["titulo"], clas["tipo"], clas.get("autoridad"), clas.get("numero"), clas.get("anio"),
              fecha_archivo, url, estado, sha256, ahora)
    if previa:
        fid = previa["id"]
        con.execute("DELETE FROM fragmentos WHERE fuente_id=?", (fid,))
        con.execute("UPDATE fuentes SET titulo=?, tipo=?, autoridad=?, numero=?, anio=?, fecha_archivo=?, url=?, "
                    "estado_vigencia=?, verificado_en=NULL, sha256=?, indexado_en=? WHERE id=?", campos + (fid,))
        accion = "actualizado"
    else:
        cur = con.execute("INSERT INTO fuentes(titulo,tipo,autoridad,numero,anio,fecha_archivo,url,estado_vigencia,"
                          "sha256,indexado_en,origen) VALUES(?,?,?,?,?,?,?,?,?,?,?)", campos + (origen,))
        fid = cur.lastrowid
        accion = "nuevo"
    n = 0
    for ubicacion, texto in paginas:
        for trozo in trocear(texto):
            con.execute("INSERT INTO fragmentos(texto,fuente_id,ubicacion) VALUES(?,?,?)", (trozo, fid, ubicacion or ""))
            n += 1
    con.commit()
    return {"id": fid, "accion": accion, "fragmentos": n, "tipo": clas["tipo"], "estado": estado}


def marcar_estado(con, fuente_id: int, estado: str, verificado_en: str = None):
    if estado not in ESTADOS:
        raise ValueError(f"estado inválido: {estado}")
    if estado == "VIGENTE_VERIFICADA" and not verificado_en:
        verificado_en = datetime.now(timezone.utc).date().isoformat()
    cur = con.execute("UPDATE fuentes SET estado_vigencia=?, verificado_en=? WHERE id=?",
                      (estado, verificado_en, int(fuente_id)))
    con.commit()
    return cur.rowcount == 1


# ----------------------------------------------------------- búsqueda --
_VACIAS = set("""
a al algo algun alguna algunas alguno algunos ante antes aqui asi aun cada cual cuales cuando como con
contra cual de del desde donde dos el ella ellas ello ellos en entre era es esa esas ese eso esos esta
estan estas este esto estos fue fueron ha hace hacer han hasta hay la las le les lo los mas me mi mis
muy mucho nada ni no nos o otra otro para pero poco por porque puede pueden puedo que quien se segun
ser si sin sobre son su sus tal tambien tan tanto te tener tengo ti tiene tienen todo todos tu tus un
una uno unos unas y ya yo usted ustedes hola gracias favor quiero quisiera saber necesito ayuda dime
explicame explica dice dicen decir cual cuales cuanto cuantos cuanta cuantas debo deberia hacer pasa pasaria caso tema
""".split())


def terminos(pregunta: str, maximo: int = 12) -> list:
    """Términos de búsqueda sin tildes ni palabras vacías (en orden de aparición, sin repetir)."""
    vistos, salida = set(), []
    for tok in re.findall(r"\w+", _norm(pregunta)):
        if tok in _VACIAS or tok in vistos:
            continue
        if tok.isdigit():
            if len(tok) < 2:
                continue
        elif len(tok) < 3:
            continue
        vistos.add(tok)
        salida.append(tok)
    return salida[:maximo]


def _raiz(tok: str) -> str:
    """Raíz mínima para plural/singular: 'tutelas'→'tutela', 'peticiones'→'peticion'."""
    if tok.isdigit() or len(tok) <= 4:
        return tok
    if tok.endswith("ones") and len(tok) > 6:
        return tok[:-2]
    if tok.endswith("es") and len(tok) > 5 and tok[-3] in "lrnzd":
        return tok[:-2]
    if tok.endswith("s"):
        return tok[:-1]
    return tok


def _consulta_fts(terms) -> str:
    partes = []
    for t in terms:
        r = _raiz(t)
        partes.append(f'"{r}"*' if not r.isdigit() and len(r) >= 4 else f'"{r}"')
    return " OR ".join(partes)


def buscar(pregunta: str, limite: int = MAX_FRAGMENTOS, ruta: str = None) -> list:
    """Busca en el corpus propio (BM25). Devuelve fragmentos con los metadatos de su fuente.

    Para no traer ruido en preguntas que no son del corpus, un fragmento solo se acepta si
    contiene al menos 2 términos distintos de la pregunta (o el único término, si solo hay uno).
    Nunca lanza excepción: si algo falla, devuelve [] y el chat sigue sin fragmentos."""
    terms = terminos(pregunta)
    if not terms:
        return []
    con = _abrir_lectura(ruta or ruta_db())
    if con is None:
        return []
    raices = [_raiz(t) for t in terms]
    minimo = 1 if len(raices) == 1 else 2
    try:
        with closing(con):
            filas = con.execute(
                "SELECT f.rowid AS frag_id, f.texto, f.ubicacion, bm25(fragmentos) AS puntaje, s.* "
                "FROM fragmentos f JOIN fuentes s ON s.id = f.fuente_id "
                "WHERE fragmentos MATCH ? ORDER BY puntaje LIMIT 40",
                (_consulta_fts(terms),)).fetchall()
    except sqlite3.Error:
        return []
    ahora = datetime.now(timezone.utc)
    salida, por_fuente = [], {}
    for f in filas:
        tn = _norm(f["texto"])
        cubiertos = sum(1 for r in raices if re.search(r"\b" + re.escape(r), tn))
        if cubiertos < minimo:
            continue
        if por_fuente.get(f["id"], 0) >= MAX_POR_FUENTE:
            continue
        por_fuente[f["id"]] = por_fuente.get(f["id"], 0) + 1
        salida.append({
            "fuente_id": f["id"], "fragmento_id": f["frag_id"], "titulo": f["titulo"], "tipo": f["tipo"],
            "autoridad": f["autoridad"], "numero": f["numero"], "anio": f["anio"],
            "fecha_archivo": f["fecha_archivo"], "url": f["url"], "ubicacion": f["ubicacion"] or "",
            "estado_vigencia": estado_efectivo(f["estado_vigencia"], f["verificado_en"], ahora),
            "verificado_en": f["verificado_en"], "texto": f["texto"], "puntaje": f["puntaje"],
        })
        if len(salida) >= limite:
            break
    for i, s in enumerate(salida, 1):
        s["ref"] = f"F{i}"
    return salida


# ------------------------------------------------ entrega al modelo --
_LEYENDA_ESTADO = {
    "VIGENTE_VERIFICADA": "vigencia verificada",
    "PENDIENTE_VERIFICAR": "PENDIENTE_VERIFICAR (vigencia sin confirmar)",
    "DESACTUALIZADA": "DESACTUALIZADA (puede haber reformas posteriores)",
    "DEROGADA": "DEROGADA (no la cites como vigente)",
}

INSTRUCCION_CITAS = """

CÓMO USAR LOS FRAGMENTOS [F1]…[Fn] DEL CORPUS:
- Toda afirmación que tomes de un fragmento lleva su marca al final de la frase, por ejemplo [F2]. No uses marcas que no aparezcan arriba ni atribuyas a un fragmento algo que no dice.
- Si un dato no está en los fragmentos ni en una fuente oficial consultada con la búsqueda web, márcalo "(pendiente de verificación)".
- Si citas un fragmento con vigencia PENDIENTE_VERIFICAR, DESACTUALIZADA o DEROGADA, adviértelo en la misma frase (por ejemplo: "según el texto del corpus, cuya vigencia está pendiente de confirmar [F1]").
- Si los fragmentos no sirven para la pregunta, ignóralos y no los menciones."""


def _limpiar_meta(texto) -> str:
    return re.sub(r"[\r\n\[\]<>]+", " ", str(texto or "")).strip()[:160]


def formatear_para_modelo(frags: list, max_chars: int = 1500) -> str:
    bloques = []
    for s in frags:
        cab = [f"[{s['ref']}] {_limpiar_meta(s['titulo'])}", f"tipo: {s['tipo']}"]
        if s.get("autoridad"):
            cab.append(f"autoridad: {_limpiar_meta(s['autoridad'])}")
        if s.get("fecha_archivo"):
            cab.append(f"fecha del archivo: {str(s['fecha_archivo'])[:10]}")
        cab.append("vigencia: " + _LEYENDA_ESTADO.get(s["estado_vigencia"], s["estado_vigencia"]))
        if s.get("ubicacion"):
            cab.append(f"ubicación: {_limpiar_meta(s['ubicacion'])}")
        texto = s["texto"] if len(s["texto"]) <= max_chars else s["texto"][:max_chars] + "…"
        bloques.append(" · ".join(cab) + "\n" + texto)
    return "\n\n".join(bloques)


def para_cliente(frags: list, respuesta: str = "") -> list:
    """Lo que ve el usuario en "Fuentes consultadas": sin el texto completo del fragmento.
    `citado` indica si la respuesta usa la marca [F#] de ese fragmento."""
    salida = []
    for s in frags:
        url = s.get("url") or ""
        if not (url.startswith("https://") and "drive.google.com" not in url and "docs.google.com" not in url):
            url = None  # nunca exponer enlaces o ids del Drive privado del corpus
        salida.append({
            "origen": "corpus", "ref": s["ref"], "titulo": s["titulo"], "tipo": s["tipo"],
            "estado_vigencia": s["estado_vigencia"], "ubicacion": s.get("ubicacion") or "",
            "fecha_archivo": (s.get("fecha_archivo") or "")[:10] or None, "url": url,
            "citado": bool(re.search(r"\[\s*" + re.escape(s["ref"]) + r"\s*\]", respuesta or "")),
        })
    return salida


# --------------------------------------------------- dominios web oficiales --
DOMINIOS_OFICIALES = (
    "corteconstitucional.gov.co", "cortesuprema.gov.co", "consejodeestado.gov.co", "ramajudicial.gov.co",
    "secretariasenado.gov.co", "suin-juriscol.gov.co", "funcionpublica.gov.co", "imprenta.gov.co",
    "minjusticia.gov.co", "dian.gov.co", "sic.gov.co", "supersociedades.gov.co", "procuraduria.gov.co",
    "fiscalia.gov.co", "mintrabajo.gov.co", "minsalud.gov.co", "colombiacompra.gov.co", "defensoria.gov.co",
    "camara.gov.co", "senado.gov.co", "presidencia.gov.co", "cnsc.gov.co", "supersalud.gov.co",
    "registraduria.gov.co",
)
_RE_DOMINIO = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,62}[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]{0,62}[a-z0-9])?)+(?:/[\x21-\x7e]*)?$")


def dominios_web():
    """Lista para `allowed_domains` del tool web_search. Formato de la documentación oficial:
    dominio sin esquema (los subdominios quedan incluidos), ASCII. PULLEX_WEB_DOMINIOS="*" quita
    la restricción (devuelve None)."""
    crudo = os.getenv("PULLEX_WEB_DOMINIOS")
    if crudo is not None and crudo.strip() == "*":
        return None
    lista = [d for d in (crudo.split(",") if crudo and crudo.strip() else DOMINIOS_OFICIALES)]
    salida = []
    for d in lista:
        d = re.sub(r"^https?://", "", d.strip().lower()).rstrip("/")
        if d.startswith("www."):
            d = d[4:]
        if d and _RE_DOMINIO.match(d) and d not in salida:
            salida.append(d)
    return salida or list(DOMINIOS_OFICIALES)


def es_oficial(url: str, dominios=None) -> bool:
    dominios = dominios if dominios is not None else (dominios_web() or DOMINIOS_OFICIALES)
    m = re.match(r"^https?://([^/:?#]+)", str(url or "").lower())
    if not m:
        return False
    host = m.group(1)
    for d in dominios:
        base = d.split("/", 1)[0]
        if host == base or host.endswith("." + base):
            return True
    return False
