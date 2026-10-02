"""
PULLEX IA — Biblioteca de modelos (Google Drive → catálogo → búsqueda → borrador trazable)
==========================================================================================
Funciones puras, sin red ni claves, que usan los scripts de la biblioteca y sus pruebas:

- clasificar_carpeta():  área jurídica y tipo documental de una carpeta, con la regla y la confianza.
- desescapar(), calidad_texto(), campos_por_completar(), datos_personales():  qué se sacó de un
  documento, si parece escaneado, qué espacios hay que llenar y si aparenta tener datos de personas.
- indexar_modelo(), buscar_modelos(), ficha():  catálogo sobre el índice de fuentes.py.
- borrador_trazable(), comprobar_borrador():  borrador que cita el modelo usado y no inventa datos.

Estados de un documento: ENCONTRADO → LEÍDO → EXTRAÍDO → INDEXADO → VALIDADO (o PENDIENTE).
VALIDADO solo lo asigna una persona. Detalle en docs/14-BIBLIOTECA-DRIVE.md.
"""
import hashlib
import re
from collections import Counter

import fuentes

TIPOS_DOCUMENTALES = ("plantilla/minuta", "norma", "jurisprudencia", "doctrina", "material de estudio",
                      "tabla de liquidación", "otro", "por clasificar")
POR_CLASIFICAR = "por clasificar"
AVISO_DERECHOS = "derechos de redistribución por confirmar"

# --------------------------------------------------------------- mapa de carpetas --
# (id, patrón sobre el nombre sin tildes y en minúsculas, resultado, confianza, por qué)
REGLAS_TIPO = (
    ("T00", r"ejemplos?.*casos", POR_CLASIFICAR, "baja",
     "ejemplos de casos: hay que decidir antes si son didácticos o reales (OBS-04)"),
    ("T01", r"\b(modelos?|minutas?|plantillas?|formatos?)\b", "plantilla/minuta", "alta",
     "el nombre dice modelos, minutas, plantillas o formatos"),
    ("T02", r"\bderechos? de peticion\b", "plantilla/minuta", "media", "el nombre es un tipo de escrito"),
    ("T03", r"\bacciones? de tutela\b", "plantilla/minuta", "media", "el nombre es un tipo de escrito"),
    ("T04", r"\bmedidas? cautelares?\b", "plantilla/minuta", "media", "el nombre es un tipo de escrito"),
    ("T05", r"\bcontratos?\b", "plantilla/minuta", "media", "el nombre es un tipo de escrito"),
    ("T18", r"^lexcol corpus$|^pack juridico\b", "otro", "alta", "carpeta contenedora: agrupa colecciones de varios tipos"),
    ("T16", r"\bindice\b|\bcuadros\b|^fuentes$", "otro", "media", "índices y cuadros de apoyo"),
    ("T06", r"\bcodigos?\b", "norma", "alta", "el nombre dice códigos"),
    ("T07", r"\bleyes\b|^ley\b|\bdecretos?\b", "norma", "alta", "el nombre dice leyes o decretos"),
    ("T08", r"\bestatutos?\b", POR_CLASIFICAR, "baja",
     "«estatutos» puede ser una norma (Estatuto Tributario) o una minuta (estatutos de una sociedad)"),
    ("T09", r"\bjurisprudencia\b|\bsentencias?\b|\bsala (civil|laboral|penal)\b|\bcorte\b", "jurisprudencia", "alta",
     "el nombre dice jurisprudencia, sentencias, sala o corte"),
    ("T10", r"\blibros?\b|\bdoctrina\b", "doctrina", "alta", "el nombre dice libros o doctrina"),
    ("T11", r"\bmaterial de estudio\b|\bconcursos?\b|\bexamenes\b|\bpreparatorios\b|\bcursos?\b|\btaller(es)?\b|\bmemorando\b",
     "material de estudio", "alta", "el nombre dice material de estudio, concurso, exámenes, cursos o taller"),
    ("T12", r"\btablas? liquidadoras?\b|\bliquidacion(es)?\b", "tabla de liquidación", "alta", "el nombre dice tablas liquidadoras"),
    ("T13", r"\bregimen(es)?\b", "norma", "media", "«regímenes» suele ser una compilación de normas por materia"),
    ("T14", r"\bfuncion publica\b", POR_CLASIFICAR, "baja", "puede ser norma, concepto o material de estudio"),
    ("T15", r"\bconalbos\b", "otro", "media", "tarifas de honorarios de un gremio: ni norma ni minuta"),
    ("T17", r"^sic$|\bprocesal informatico\b", POR_CLASIFICAR, "baja", "el nombre no dice qué clase de documento contiene"),
)
# (id, patrón, área, área del registro de perfiles de la especificación, confianza)
REGLAS_AREA = (
    ("A01", r"\bfamilia\b|\binfancia\b", "familia", "A06", "alta"),
    ("A02", r"\bcomercial\b", "comercial", "A06", "alta"),
    ("A03", r"\bcivil\b", "civil", "A06", "alta"),
    ("A04", r"\bpenal\b|\bfiscalia\b", "penal", "A08", "alta"),
    ("A05", r"\blaboral\b", "laboral y seguridad social", "A09", "alta"),
    ("A06", r"\btutela\b", "constitucional (tutela)", "A10", "alta"),
    ("A07", r"\bpeticion\b", "derecho de petición", "A10", "alta"),
    ("A08", r"\bcautelares?\b", "procesal (medidas cautelares)", "A10", "alta"),
    ("A09", r"\bdisciplinario\b", "disciplinario", "A07", "alta"),
    ("A10", r"\bfuncion publica\b", "empleo público", "A07", "media"),
    ("A11", r"\bdian\b", "tributario y aduanero", "A07", "media"),
    ("A12", r"\bnotarial\b", "notarial y registro", POR_CLASIFICAR, "media"),
    ("A13", r"\bprocesal informatico\b", "procesal informático", "A10", "alta"),
    ("A14", r"\bconalbos\b", "gestión profesional (honorarios)", "A10", "media"),
)
# colecciones que por naturaleza cubren varias áreas: solo se usa si ninguna regla anterior aplica
REGLA_AREA_GENERAL = (
    "A15", r"\bcodigos?\b|\bleyes\b|\blibros?\b|\bjurisprudencia\b|\bdoctrina\b|\bregimen(es)?\b|\bestatutos?\b|"
           r"\bplantillas?\b|\bmodelos?\b|\bminutas?\b|\brama judicial\b|\bexamenes\b|\bpreparatorios\b|"
           r"^lexcol corpus$|^pack juridico\b",
    "general (varias áreas)", "A06–A10", "alta")
_RE_CONTENEDOR = re.compile(r"^lexcol corpus$|^pack juridico\b")      # su área no se hereda hacia abajo
# prefijos de providencias de la Corte Suprema → sala
PREFIJOS_SALA = {"SL": "laboral y seguridad social", "AL": "laboral y seguridad social", "STL": "laboral y seguridad social",
                 "SC": "civil", "AC": "civil", "STC": "civil", "ATC": "civil",
                 "SP": "penal", "AP": "penal", "STP": "penal", "AHP": "penal", "AEP": "penal", "SEP": "penal", "CP": "penal"}
_RE_PREFIJO = re.compile(r"^([A-Z]{2,3})\s?\d{2,6}\s?-\s?\d{4}")
_NIVEL = {"alta": 3, "media": 2, "baja": 1}


def _n(texto):
    return re.sub(r"[\s_]+", " ", fuentes.sin_tildes(texto or "").lower()).strip()


def _primera(reglas, nombre):
    for r in reglas:
        if re.search(r[1], nombre):
            return r
    return None


def clasificar_carpeta(titulo, ancestros=(), titulos_archivos=()):
    """Área y tipo documental de una carpeta.

    `ancestros`: nombres de las carpetas que la contienen, de la más cercana a la más lejana.
    `titulos_archivos`: títulos de los archivos que se ven directamente dentro (evidencia).
    Lo que no se puede decidir con confianza media o alta queda "por clasificar"."""
    propio, cadena = _n(titulo), [_n(a) for a in ancestros]
    notas = []

    rt = _primera(REGLAS_TIPO, propio)
    heredado_tipo = False
    if rt is None:
        for a in cadena:
            rt = _primera(REGLAS_TIPO, a)
            if rt:
                heredado_tipo = True
                break
    tipo, conf_tipo, regla_tipo = (rt[2], rt[3], rt[0]) if rt else (POR_CLASIFICAR, "baja", None)
    if rt and not heredado_tipo and rt[2] != POR_CLASIFICAR:
        # el nombre propio manda, pero si la carpeta que la contiene dice otra cosa, se duda
        for a in cadena:
            ra = _primera(REGLAS_TIPO, a)
            if ra and ra[2] not in (POR_CLASIFICAR, rt[2], "otro") and rt[2] != "otro":
                notas.append(f"el nombre sugiere «{rt[2]}» pero está dentro de una carpeta de «{ra[2]}» (regla {ra[0]})")
                tipo, conf_tipo = POR_CLASIFICAR, "baja"
            if ra:
                break
    if heredado_tipo and conf_tipo == "alta":
        conf_tipo = "media"          # lo heredado nunca es tan seguro como lo que dice el propio nombre

    # evidencia: cómo se llaman los archivos que se ven dentro
    por_nombre = Counter(fuentes.clasificar_nombre(t)["tipo"] for t in titulos_archivos)
    salas = Counter(PREFIJOS_SALA[m.group(1)] for t in titulos_archivos
                    for m in [_RE_PREFIJO.match(t.strip().upper())] if m and m.group(1) in PREFIJOS_SALA)
    n = len(titulos_archivos)
    if regla_tipo == "T08" and n and all(_n(t).startswith("estatuto ") for t in titulos_archivos) \
            and not any(re.search(r"\bsocial(es)?\b|\bsociedad\b|\bs\.?a\.?s\b|\bltda\b", _n(t)) for t in titulos_archivos):
        tipo, conf_tipo = "norma", "media"
        notas.append("los archivos se llaman «Estatuto de…» (normas), no son minutas de estatutos sociales")
    elif tipo == "norma" and n and (por_nombre["ley"] + por_nombre["decreto"] + por_nombre["codigo"]) / n >= 0.6:
        conf_tipo = "alta"
    elif tipo == "plantilla/minuta" and n and por_nombre["plantilla"] / n >= 0.5 and conf_tipo == "media":
        conf_tipo = "alta"
    if tipo == "plantilla/minuta" and n and (por_nombre["ley"] + por_nombre["codigo"] + por_nombre["sentencia"]) / n >= 0.6:
        notas.append("los nombres de los archivos parecen normas o sentencias, no minutas")
        tipo, conf_tipo = POR_CLASIFICAR, "baja"

    # área: gana la regla específica más cercana (el propio nombre y luego las carpetas que la contienen);
    # si ninguna aplica, vale la regla de colección general
    ra, heredado_area = None, False
    for k, nombre in enumerate([propio] + cadena):
        ra = _primera(REGLAS_AREA, nombre)
        if ra:
            heredado_area = k > 0
            break
    if ra is None:
        for k, nombre in enumerate([propio] + cadena):
            if re.search(REGLA_AREA_GENERAL[1], nombre) and not (k > 0 and _RE_CONTENEDOR.search(nombre)):
                ra, heredado_area = REGLA_AREA_GENERAL, False     # heredar "varias áreas" no resta confianza
                break
    area, perfiles, conf_area, regla_area = (ra[2], ra[3], ra[4], ra[0]) if ra else (POR_CLASIFICAR, POR_CLASIFICAR, "baja", None)
    if heredado_area and conf_area == "alta":
        conf_area = "media"
    if salas and area in set(PREFIJOS_SALA.values()):
        otras = sum(v for k, v in salas.items() if k != area)
        if otras / sum(salas.values()) > 0.1:
            notas.append(f"{otras} de {sum(salas.values())} providencias tienen prefijo de otra sala: {dict(salas)}")
            conf_area = "media" if conf_area == "alta" else conf_area

    confianza = min(conf_tipo, conf_area, key=_NIVEL.get) if POR_CLASIFICAR not in (tipo, area) else "baja"
    return {"area": area, "area_perfiles": perfiles, "tipo_documental": tipo,
            "regla_tipo": regla_tipo and (regla_tipo + (" (heredada)" if heredado_tipo else "")),
            "regla_area": regla_area and (regla_area + (" (heredada)" if heredado_area else "")),
            "confianza_tipo": conf_tipo, "confianza_area": conf_area, "confianza": confianza,
            "evidencia": {"archivos_visibles": n, "por_nombre": dict(por_nombre), "salas": dict(salas)},
            "notas": notas}
