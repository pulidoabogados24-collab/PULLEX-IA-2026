"""Construye biblioteca/inventario.json (y biblioteca/INVENTARIO.md) a partir de los listados de
Google Drive hechos con el conector de Drive durante una sesión de trabajo. Los listados se leen de
la transcripción de la sesión.

Por qué así: el conector de Drive solo se puede usar desde el asistente, no desde un script. Este
script convierte esos listados en un inventario verificable y REANUDABLE: dice qué carpetas faltan
por listar y qué páginas quedaron a medias, para continuar sin repetir trabajo.

    python scripts/cosechar_inventario_drive.py <transcripcion.jsonl> [más.jsonl …] [--raices id1,id2,...]
           [--extraccion biblioteca/extraccion.json] [--observaciones biblioteca/observaciones.json]
           [--salida biblioteca/inventario.json] [--md biblioteca/INVENTARIO.md]

No lee el contenido de ningún archivo: solo metadatos (id, título, carpeta, tipo, tamaño, fechas,
propietario). Estados de cada archivo (el más avanzado que se haya COMPROBADO):

    ENCONTRADO  apareció en un listado (solo metadatos).
    LEÍDO       el conector devolvió su contenido.
    EXTRAÍDO    el texto quedó guardado fuera de git (corpus/extraidos/<id>.txt) con huella y calidad.
    INDEXADO    está en el índice de búsqueda (corpus/corpus.db).
    VALIDADO    una persona lo revisó jurídicamente (este script nunca lo asigna).
    PENDIENTE   no se procesa hasta que una persona decida (posible dato personal u otro motivo).

LEÍDO, EXTRAÍDO e INDEXADO no los decide este script: los toma del registro de extracción
(biblioteca/extraccion.json) que escriben scripts/extraer_muestra_drive.py y scripts/indexar_biblioteca.py.

Formatos de consulta que reconoce como listado de carpetas:
    parentId = 'ID'                       (o varias unidas con "or")  → lista todo lo que hay dentro
    mimeType = 'application/vnd.google-apps.folder' and (parentId = 'A' or parentId = 'B' …)  → solo subcarpetas
"""
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
import fuentes  # noqa: E402

SALIDA = RAIZ / "biblioteca" / "inventario.json"
SALIDA_MD = RAIZ / "biblioteca" / "INVENTARIO.md"
EXTRACCION = RAIZ / "biblioteca" / "extraccion.json"
OBSERVACIONES = RAIZ / "biblioteca" / "observaciones.json"
CARPETA = "application/vnd.google-apps.folder"
ATAJO = "application/vnd.google-apps.shortcut"
PROPIO = "pulidoabogados24@gmail.com"
RESERVADO = "[título reservado]"
TOPE_CONECTOR = 2000      # a partir de ~2.000 resultados por consulta el conector solo repite elementos
ESTADOS = ("ENCONTRADO", "LEÍDO", "EXTRAÍDO", "INDEXADO", "VALIDADO", "PENDIENTE")

# Palabras de expediente o de documento de identidad en el título: posible dato personal.
PATRON_EXPEDIENTE = re.compile(r"\b(CLIENTES?|EXPEDIENTES?|HISTORIA CL[IÍ]NICA|C[ÉE]DULA)\b", re.I)
RE_GUARDADO = re.compile(r"Output has been saved to (\S+?\.txt)")
RE_PADRE = re.compile(r"parentId\s*=\s*'([^']+)'")
RE_OTROS_FILTROS = re.compile(r"title|fullText|owner|sharedWithMe|modifiedTime|createdTime|viewedByMeTime")


def _texto(contenido):
    if isinstance(contenido, str):
        return contenido
    if isinstance(contenido, list):
        return "".join(b.get("text", "") for b in contenido if isinstance(b, dict))
    return ""


def _resultado(texto):
    """JSON del resultado de una herramienta. Cuando el resultado era demasiado grande, la sesión lo
    guarda en un archivo y deja en la transcripción solo la ruta: se lee de ahí."""
    try:
        return json.loads(texto)
    except (json.JSONDecodeError, TypeError):
        pass
    m = RE_GUARDADO.search(texto or "")
    if m and Path(m.group(1)).is_file():
        try:
            return json.loads(Path(m.group(1)).read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None
    return None


def leer_llamadas(ruta):
    """Llamadas al conector de Drive, en orden: [{tipo, consulta, token, resultado, fecha}].
    tipo = "listado" (search_files) o "metadatos" (get_file_metadata)."""
    usos, salida = {}, []
    for linea in open(ruta, encoding="utf-8"):
        try:
            d = json.loads(linea)
        except json.JSONDecodeError:
            continue
        contenido = (d.get("message") or {}).get("content")
        if not isinstance(contenido, list):
            continue
        for b in contenido:
            if not isinstance(b, dict):
                continue
            nombre = b.get("name", "")
            if b.get("type") == "tool_use" and nombre.endswith(("Google_Drive__search_files", "Google_Drive__get_file_metadata")):
                usos[b["id"]] = ("listado" if nombre.endswith("search_files") else "metadatos", b.get("input") or {})
            elif b.get("type") == "tool_result" and b.get("tool_use_id") in usos:
                tipo, ent = usos[b["tool_use_id"]]
                r = _resultado(_texto(b.get("content")))
                if not isinstance(r, dict):
                    continue
                if tipo == "metadatos":
                    r = {"files": [r]} if r.get("id") else {"files": []}
                salida.append({"tipo": tipo, "consulta": ent.get("query", ""), "token": ent.get("pageToken"),
                               "resultado": r, "fecha": d.get("timestamp")})
    return salida


def leer_listados(ruta):
    """Compatibilidad: [(consulta, pageToken_usado, resultado_json)] de cada búsqueda de Drive."""
    return [(x["consulta"], x["token"], x["resultado"]) for x in leer_llamadas(ruta) if x["tipo"] == "listado"]


def sensibilidad(titulo, es_carpeta=False):
    """POSIBLE_DATO_PERSONAL si el título parece de una persona o de un expediente. Usa la misma
    heurística que la ingesta (fuentes.py): nombre propio + tipo de escrito, o "CLIENTE"/"EXPEDIENTE".
    Prefiere reservar de más: lo dudoso lo decide una persona."""
    if PATRON_EXPEDIENTE.search(titulo or "") or fuentes.tiene_palabra_cliente(titulo or ""):
        return "POSIBLE_DATO_PERSONAL"
    if fuentes.parece_de_persona(titulo or "", es_carpeta=es_carpeta):
        return "POSIBLE_DATO_PERSONAL"
    return "SIN_INDICIOS"


# Lo que el conector puede leer (lista de su propia documentación) y lo que no.
LEGIBLES_CONECTOR = {
    "application/vnd.google-apps.document", "application/vnd.google-apps.presentation",
    "application/vnd.google-apps.spreadsheet", "application/pdf", "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "application/vnd.oasis.opendocument.spreadsheet", "application/vnd.oasis.opendocument.presentation",
    "application/x-vnd.oasis.opendocument.text", "image/png", "image/jpeg", "image/jpg"}


def no_procesable(e):
    """Motivo por el que un archivo no se puede leer con el conector, y cómo recuperarlo. None si se puede."""
    if e["mime"] in (CARPETA, ATAJO):
        return None
    if (e.get("extension") or "") == "tmp" or e["titulo"].startswith("~"):
        return "archivo temporal de Word, no es un documento: se puede borrar del Drive (decisión del dueño)"
    if "macroenabled" in e["mime"].lower():
        return "hoja de cálculo con macros: no se ejecutan macros; exportarla a .xlsx sin macros para leerla"
    if e["mime"] not in LEGIBLES_CONECTOR:
        return ("formato que el conector no lee (" + (e.get("extension") or e["mime"]) + "): descargarlo y "
                "convertirlo a .docx o texto, o ingerirlo con scripts/ingesta_corpus.py")
    return None


def titulo_normalizado(titulo):
    """Para comparar homónimos: sin extensión, sin "(1)" ni "copia de", sin tildes ni mayúsculas."""
    t = re.sub(r"\.[A-Za-z0-9]{2,5}$", "", titulo or "")
    t = re.sub(r"\s*\(\d+\)\s*$", "", t)
    t = re.sub(r"^\s*copia de\s+", "", t, flags=re.I)
    return re.sub(r"[\s_]+", " ", fuentes.sin_tildes(t).lower()).strip()


def _ref_propietario(correo):
    """No se guardan correos de terceros: una referencia corta y estable basta para distinguir cuentas."""
    if not correo:
        return "desconocido"
    if correo == PROPIO:
        return "propio"
    return "tercero-" + hashlib.sha256(correo.encode("utf-8")).hexdigest()[:8]


def _enlace(url):
    return re.sub(r"[?&](usp=drivesdk|ouid=\d+)", "", url or "").rstrip("?&") or None


def construir(rutas, raices, extraccion=None):
    """Devuelve el inventario completo (dict). `extraccion`: registro {drive_id: {...}} opcional."""
    raices = [r for r in raices if r]
    crudos, corridas, completas, exploradas = {}, defaultdict(list), set(), set()
    # en orden cronológico entre todas las transcripciones: la última corrida de cada consulta manda
    llamadas = [ll for ruta in rutas for ll in leer_llamadas(ruta)]
    llamadas.sort(key=lambda ll: ll["fecha"] or "")
    for ll in llamadas:
        r, consulta = ll["resultado"], ll["consulta"]
        for f in r.get("files", []):
            if not f.get("id"):
                continue
            e = crudos.setdefault(f["id"], {})
            e.update({k: v for k, v in f.items() if v is not None})
            e["_fecha"] = ll["fecha"] or e.get("_fecha")
        if ll["tipo"] != "listado":
            continue
        padres = RE_PADRE.findall(consulta)
        otros = RE_OTROS_FILTROS.search(consulta)
        con_mime = "mimeType" in consulta
        if padres and not otros and not con_mime:
            # listado completo de lo que hay dentro de esas carpetas; una consulta sin token
            # empieza una corrida nueva (reinicio de la paginación)
            if ll["token"] is None or not corridas[consulta]:
                corridas[consulta].append({"padres": padres, "ids": [], "token": None})
            c = corridas[consulta][-1]
            c["ids"] += [f["id"] for f in r.get("files", []) if f.get("id")]
            c["token"] = r.get("nextPageToken")
        elif (padres and not otros and "mimeType = 'application/vnd.google-apps.folder'" in consulta
              and not r.get("nextPageToken")):
            exploradas.update(padres)

    paginacion, a_medias, truncadas, omisiones = [], [], [], []
    hijos_conocidos = defaultdict(set)
    for i, f in crudos.items():
        hijos_conocidos[f.get("parentId")].add(i)
    for consulta, cs in corridas.items():
        for c in cs:
            if c["token"] is not None:
                continue
            unicos_c = set(c["ids"])
            if len(unicos_c) >= TOPE_CONECTOR:
                # el conector deja de entregar resultados nuevos hacia los 2.000: no es el total
                truncadas.append({"consulta": consulta, "padres": sorted(set(c["padres"])), "unicos": len(unicos_c)})
                continue
            completas.update(c["padres"])
            for p in set(c["padres"]):
                faltaron = hijos_conocidos.get(p, set()) - unicos_c
                if faltaron:     # otro listado vio elementos que este, "completo", no trajo
                    omisiones.append({"carpeta_id": p, "consulta": consulta, "omitidos": len(faltaron)})
        ultima = cs[-1]
        unicos = len(set(ultima["ids"]))
        if len(ultima["ids"]) != unicos:
            paginacion.append({"consulta": consulta, "devueltos": len(ultima["ids"]), "unicos": unicos,
                               "repetidos": len(ultima["ids"]) - unicos})
    for consulta, cs in corridas.items():
        ultima = cs[-1]
        if ultima["token"] and not set(ultima["padres"]) <= completas:
            a_medias.append({"consulta": consulta, "pageToken": ultima["token"],
                             "faltan": sorted(set(ultima["padres"]) - completas)})
    truncadas = [t for t in truncadas if not set(t["padres"]) <= completas]
    ids_truncadas = {p for t in truncadas for p in t["padres"]} - completas
    con_omisiones = {o["carpeta_id"] for o in omisiones}
    exploradas |= completas

    elementos = {}
    for i, f in crudos.items():
        elementos[i] = {
            "drive_id": i, "titulo": f.get("title", ""), "mime": f.get("mimeType", ""),
            "carpeta_id": f.get("parentId"), "tamano": int(f["fileSize"]) if f.get("fileSize") else None,
            "modificado": f.get("modifiedTime"), "creado": f.get("createdTime"),
            "propietario": "propio" if f.get("owner") == PROPIO else "tercero",
            "propietario_ref": _ref_propietario(f.get("owner")),
            "visto_por_el_usuario": bool(f.get("viewedByMeTime")),
            "compartido_directamente": bool(f.get("sharedWithMeTime")),
            "enlace": _enlace(f.get("viewUrl")), "extension": (f.get("fileExtension") or "").lower() or None,
            "ultima_comprobacion": f.get("_fecha"), "estado": "ENCONTRADO"}

    for e in elementos.values():
        motivo = no_procesable(e)
        if motivo:
            e["no_procesable"] = motivo

    def ruta_de(e, visto=()):
        p = e.get("carpeta_id")
        if not p or p not in elementos or p in visto:      # `visto` corta cualquier ciclo de carpetas
            return ""
        padre = elementos[p]
        return (ruta_de(padre, visto + (p,)) + "/" + padre["titulo"]).strip("/")

    for e in elementos.values():
        e["ruta"] = ruta_de(e)
    for e in elementos.values():
        e["sensibilidad"] = sensibilidad(e["titulo"], es_carpeta=e["mime"] == CARPETA)
        partes = [x for x in e["ruta"].split("/") if x]
        if any(sensibilidad(x, es_carpeta=True) != "SIN_INDICIOS" for x in partes):
            e["sensibilidad"] = "POSIBLE_DATO_PERSONAL"
    for e in elementos.values():
        if e["sensibilidad"] != "SIN_INDICIOS":
            e["estado"] = "PENDIENTE"
            e["motivo"] = "posible dato personal: requiere clasificación humana antes de leer o indexar"
    reservados = {i for i, e in elementos.items() if e["sensibilidad"] != "SIN_INDICIOS"}

    carpetas = {i for i, e in elementos.items() if e["mime"] == CARPETA}
    alcanzables, cambio = set(raices), True
    while cambio:
        cambio = False
        for i in carpetas:
            if i not in alcanzables and elementos[i].get("carpeta_id") in alcanzables:
                alcanzables.add(i)
                cambio = True
    limpia = lambda i: i in raices or i not in reservados
    # la cola de trabajo solo incluye lo que está dentro de las raíces autorizadas
    a_medias_fuera = [a for a in a_medias if not set(a["faltan"]) & alcanzables]
    a_medias = [a for a in a_medias if set(a["faltan"]) & alcanzables]
    pendientes = sorted(i for i in alcanzables if i not in completas and i not in ids_truncadas and limpia(i))
    sin_explorar = sorted(i for i in alcanzables if i not in exploradas and limpia(i))
    en_alcance = {i: e for i, e in elementos.items() if e.get("carpeta_id") in alcanzables or i in alcanzables}

    # registro de extracción / indexación (lo escriben otros scripts; aquí solo se refleja)
    for i, x in (extraccion or {}).items():
        e = en_alcance.get(i)
        if not e or e["estado"] == "PENDIENTE":
            continue
        if x.get("estado") in ESTADOS:
            e["estado"] = x["estado"]
        for k in ("calidad", "sha256_texto", "campos_por_completar", "datos_personales", "apto_indice",
                  "motivo_no_apto", "indexado", "leido_en", "error"):
            if x.get(k) is not None:
                e[k] = x[k]
        if x.get("motivo"):
            e["motivo"] = x["motivo"]

    archivos = [e for e in en_alcance.values() if e["mime"] not in (CARPETA, ATAJO)]

    # homónimos (mismo título) y posibles duplicados (mismo título y mismo tamaño)
    por_titulo = defaultdict(list)
    for e in archivos:
        if e["drive_id"] not in reservados:
            por_titulo[titulo_normalizado(e["titulo"])].append(e)
    duplicados, homonimos = [], []
    for t, grupo in sorted(por_titulo.items()):
        if len(grupo) < 2 or not t:
            continue
        por_tam = defaultdict(list)
        for e in grupo:
            por_tam[e["tamano"]].append(e)
        hubo_dup = False
        for tam, g in por_tam.items():
            if tam is not None and len(g) > 1:
                hubo_dup = True
                gid = "D%04d" % (len(duplicados) + 1)
                duplicados.append({"grupo": gid, "titulo": t, "tamano": tam, "ids": sorted(x["drive_id"] for x in g),
                                   "propio_y_tercero": len({x["propietario"] for x in g}) > 1})
                for x in g:
                    x["posible_duplicado"] = gid
        if len(por_tam) > 1 or not hubo_dup:
            homonimos.append({"titulo": t, "ids": sorted(x["drive_id"] for x in grupo),
                              "tamanos": sorted({x["tamano"] for x in grupo if x["tamano"] is not None})})

    # atajos (accesos directos): el conector no dice a dónde apuntan; se dejan candidatos por nombre
    atajos = []
    for e in elementos.values():
        if e["mime"] != ATAJO:
            continue
        t = titulo_normalizado(e["titulo"])
        cand = sorted(i for i in carpetas if titulo_normalizado(elementos[i]["titulo"]) == t)
        atajos.append({"drive_id": e["drive_id"], "titulo": e["titulo"], "carpeta_id": e["carpeta_id"],
                       "ruta": e["ruta"], "en_alcance": e["drive_id"] in en_alcance, "resuelto": False,
                       "destino": None, "candidatos_por_nombre": cand,
                       "motivo": "el conector no expone el destino del acceso directo; el candidato por "
                                 "nombre NO está comprobado"})
    atajos.sort(key=lambda a: (a["titulo"], a["drive_id"]))

    # carpetas vistas fuera de las raíces autorizadas (solo de las mismas cuentas: propia o de las colecciones)
    cuentas = {e["propietario_ref"] for e in en_alcance.values()} | {"propio"}
    hijos_fuera = Counter(e["carpeta_id"] for i, e in elementos.items() if i not in en_alcance and e["mime"] != CARPETA)
    fuera = [{"drive_id": i, "titulo": RESERVADO if i in reservados else e["titulo"], "ruta": e["ruta"],
              "propietario": e["propietario"], "propietario_ref": e["propietario_ref"],
              "archivos_vistos_dentro": hijos_fuera.get(i, 0),
              "estado": "PENDIENTE" if i in reservados else "FUERA_DE_ALCANCE",
              "motivo": ("posible dato personal: no se lee" if i in reservados
                         else "no está dentro de las raíces autorizadas: no se recorre ni se lee")}
             for i, e in elementos.items()
             if i in carpetas and i not in en_alcance and e["propietario_ref"] in cuentas]
    fuera.sort(key=lambda x: (x["ruta"], x["titulo"]))

    # cobertura por carpeta
    directos = defaultdict(list)
    for e in archivos:
        directos[e["carpeta_id"]].append(e)

    def dueno(i):
        """Propietario de una carpeta. Si nunca se pidieron sus metadatos (una raíz), se deduce de lo
        que contiene solo cuando todo es propio; ante la duda cuenta como ajena (lo prudente)."""
        if i in elementos:
            return elementos[i]["propietario"]
        hijos = {e["propietario"] for e in en_alcance.values() if e.get("carpeta_id") == i}
        return "propio" if hijos == {"propio"} else "desconocido"
    tabla = []
    for i in sorted(alcanzables, key=lambda i: ((elementos.get(i, {}).get("ruta") or "") + "/" +
                                                 elementos.get(i, {}).get("titulo", i))):
        e = elementos.get(i, {})
        if i in reservados and i not in raices:
            listado = "NO_SE_LISTA (posible dato personal)"
        elif i in ids_truncadas:
            listado = "TRUNCADO_POR_EL_CONECTOR"
        elif i in completas and dueno(i) != "propio":
            listado = "SEGUN_CONECTOR"
        elif i in completas:
            listado = "COMPLETO_CON_OMISIONES" if i in con_omisiones else "COMPLETO"
        elif any(i in a["faltan"] for a in a_medias):
            listado = "A_MEDIAS"
        else:
            listado = "PENDIENTE_DE_LISTAR"
        fs = directos.get(i, [])
        tabla.append({"drive_id": i, "titulo": RESERVADO if i in reservados else e.get("titulo", "(raíz sin metadatos)"),
                      "ruta": e.get("ruta", ""), "propietario": dueno(i), "listado": listado,
                      "archivos": len(fs), "bytes": sum(x["tamano"] or 0 for x in fs),
                      "por_estado": dict(Counter(x["estado"] for x in fs))})

    for i in reservados:
        elementos[i]["titulo"] = RESERVADO
    for e in elementos.values():      # las rutas tampoco deben revelar un título reservado
        partes, p, vistos = [], e.get("carpeta_id"), set()
        while p and p in elementos and p not in vistos:
            vistos.add(p)
            partes.append(elementos[p]["titulo"])
            p = elementos[p].get("carpeta_id")
        e["ruta"] = "/".join(reversed(partes))

    terceros = [e for e in en_alcance.values() if e["propietario"] == "tercero" and e["drive_id"] not in raices]
    hay_terceros = any(t["propietario"] != "propio" for t in tabla)
    resumen = {
        "raices": raices,
        "elementos_en_alcance": len(en_alcance),
        "carpetas": sum(1 for e in en_alcance.values() if e["mime"] == CARPETA),
        "atajos_en_alcance": sum(1 for e in en_alcance.values() if e["mime"] == ATAJO),
        "archivos": len(archivos),
        "bytes": sum(e["tamano"] or 0 for e in archivos),
        "carpetas_listadas_completas": len(completas & alcanzables),
        "carpetas_pendientes_de_listar": len(pendientes),
        "carpetas_sin_explorar_subcarpetas": len(sin_explorar),
        "listados_a_medias": len(a_medias),
        "carpetas_truncadas_por_el_conector": len(ids_truncadas & alcanzables),
        "denominador": ("PROVISIONAL" if (pendientes or a_medias or hay_terceros or ids_truncadas & alcanzables)
                        else "COMPLETO para las raíces indicadas"),
        "denominador_detalle": {
            "carpetas_propias": ("PROVISIONAL (faltan carpetas por listar o el conector las truncó)"
                                 if (pendientes or a_medias or ids_truncadas & alcanzables)
                                 else "COMPLETO según el conector"),
            "carpetas_de_terceros": ("DESCONOCIDO: el conector solo devuelve lo que el usuario ya abrió; "
                                     "lo listado es un mínimo, no el total" if hay_terceros else "no hay"),
        },
        "evidencia_limite_terceros": {
            "elementos_de_terceros_en_alcance": len(terceros),
            "con_fecha_de_visto_por_el_usuario": sum(1 for e in terceros if e["visto_por_el_usuario"]),
            "sin_fecha_de_visto": sum(1 for e in terceros if not e["visto_por_el_usuario"]),
        },
        "por_estado": {s: n for s, n in ((s, sum(1 for e in archivos if e["estado"] == s)) for s in ESTADOS) if n or s in ("ENCONTRADO", "VALIDADO")},
        "por_propietario": dict(Counter(e["propietario"] for e in archivos)),
        "por_tipo_de_archivo": dict(Counter((e.get("extension") or e["mime"].split(".")[-1].split("/")[-1])
                                            for e in archivos).most_common(15)),
        "posibles_duplicados_grupos": len(duplicados),
        "homonimos_grupos": len(homonimos),
        "posible_dato_personal": sum(1 for e in en_alcance.values() if e["sensibilidad"] != "SIN_INDICIOS"),
        "no_procesables_con_el_conector": dict(Counter(
            (e.get("extension") or e["mime"].split("/")[-1]) for e in archivos if e.get("no_procesable"))),
    }
    for e in en_alcance.values():      # compacto: no se escriben los valores por defecto
        for k, defecto in (("tamano", None), ("extension", None), ("compartido_directamente", False),
                           ("sensibilidad", "SIN_INDICIOS"), ("creado", e.get("creado"))):
            if e.get(k) == defecto:
                e.pop(k, None)
    return {"resumen": resumen, "pendientes": pendientes, "sin_explorar": sin_explorar, "a_medias": a_medias,
            "a_medias_fuera_de_alcance": [a["consulta"] for a in a_medias_fuera],
            "truncadas": [t for t in truncadas if set(t["padres"]) & alcanzables],
            "omisiones_detectadas": [o for o in omisiones if o["carpeta_id"] in alcanzables],
            "paginacion_con_repetidos": paginacion, "carpetas": tabla, "atajos": atajos,
            "fuera_de_alcance": fuera, "posibles_duplicados": duplicados, "homonimos": homonimos,
            "elementos": sorted(en_alcance.values(), key=lambda e: (e["ruta"], e["titulo"], e["drive_id"]))}


# ------------------------------------------------------------------ salida --
def _mb(n):
    return f"{n / 1048576:.1f} MB" if n >= 1048576 else f"{n / 1024:.0f} KB"


def informe_md(inv):
    r = inv["resumen"]
    L = ["# Inventario de la biblioteca de Drive", "",
         "Generado por `scripts/cosechar_inventario_drive.py` a partir de los listados del conector de Drive. "
         "No lo edites a mano: vuelve a ejecutar el script.", "",
         f"**Denominador: {r['denominador']}.** Carpetas propias: {r['denominador_detalle']['carpetas_propias']}. "
         f"Carpetas de terceros: {r['denominador_detalle']['carpetas_de_terceros']}.", "",
         "## Totales", "",
         f"- Carpetas en alcance: {r['carpetas']} · Archivos: {r['archivos']} ({_mb(r['bytes'])}) · "
         f"Accesos directos en alcance: {r['atajos_en_alcance']}",
         f"- Carpetas listadas hasta el final: {r['carpetas_listadas_completas']} · pendientes de listar: "
         f"{r['carpetas_pendientes_de_listar']} · listados a medias: {r['listados_a_medias']}",
         f"- Por propietario: {r['por_propietario']}",
         f"- Posible dato personal (título reservado, no se lee): {r['posible_dato_personal']}",
         f"- Grupos de posibles duplicados (mismo título y tamaño): {r['posibles_duplicados_grupos']} · "
         f"grupos de homónimos (mismo título, distinto tamaño): {r['homonimos_grupos']}", "",
         "## Archivos por estado", "", "| Estado | Archivos |", "|---|---:|"]
    for s in ESTADOS:
        L.append(f"| {s} | {r['por_estado'].get(s, 0)} |")
    if r.get("no_procesables_con_el_conector"):
        L += ["", f"Archivos que el conector no puede leer, por tipo: {r['no_procesables_con_el_conector']} "
              "(el motivo y la vía de recuperación están en cada elemento, campo `no_procesable`)."]
    L += ["", "Un archivo cuenta una sola vez, en el estado más avanzado que se comprobó. VALIDADO exige revisión "
          "jurídica humana: ningún proceso automático lo asigna.", "",
          "## Tipos de archivo", "", "| Tipo | Archivos |", "|---|---:|"]
    for t, n in r["por_tipo_de_archivo"].items():
        L.append(f"| {t} | {n} |")
    L += ["", "## Por carpeta", "",
          "`COMPLETO`: carpeta propia listada hasta la última página. `SEGUN_CONECTOR`: carpeta de un tercero; el "
          "conector solo devuelve lo que el usuario ya abrió, así que el número es un mínimo. `A_MEDIAS` y "
          "`PENDIENTE_DE_LISTAR`: falta recorrerlas.", "",
          "| Carpeta | Propietario | Listado | Archivos | Tamaño | Estados |", "|---|---|---|---:|---:|---|"]
    for c in inv["carpetas"]:
        ruta = (c["ruta"] + "/" if c["ruta"] else "") + c["titulo"]
        est = ", ".join(f"{k} {v}" for k, v in sorted(c["por_estado"].items())) or "—"
        L.append(f"| {ruta} | {c['propietario']} | {c['listado']} | {c['archivos']} | {_mb(c['bytes'])} | {est} |")
    L += ["", "## Accesos directos", ""]
    if inv["atajos"]:
        L += ["El conector no dice a dónde apunta un acceso directo. Los candidatos son carpetas con el mismo nombre: "
              "**no están comprobados**.", "", "| Acceso directo | Id | Ubicación | Candidatos por nombre |", "|---|---|---|---|"]
        for a in inv["atajos"]:
            L.append(f"| {a['titulo']} | `{a['drive_id']}` | {a['ruta'] or 'carpeta `' + str(a['carpeta_id']) + '` (no listada)'} | "
                     f"{', '.join('`' + c + '`' for c in a['candidatos_por_nombre']) or 'ninguno'} |")
    else:
        L.append("Ninguno.")
    L += ["", "## Carpetas vistas fuera de las raíces autorizadas", ""]
    if inv["fuera_de_alcance"]:
        L += ["Aparecieron en búsquedas por nombre. No se recorren ni se leen.", "",
              "| Carpeta | Id | Propietario | Estado | Motivo |", "|---|---|---|---|---|"]
        for f in inv["fuera_de_alcance"]:
            L.append(f"| {(f['ruta'] + '/' if f['ruta'] else '') + f['titulo']} | `{f['drive_id']}` | {f['propietario']} | "
                     f"{f['estado']} | {f['motivo']} |")
    else:
        L.append("Ninguna.")
    L += ["", "## Paginación con elementos repetidos", ""]
    if inv["paginacion_con_repetidos"]:
        L += ["En carpetas grandes el conector repite elementos entre páginas. Los únicos son los que cuentan; no se "
              "puede descartar que también omita alguno.", "", "| Carpeta(s) | Devueltos | Únicos | Repetidos |", "|---|---:|---:|---:|"]
        for p in inv["paginacion_con_repetidos"]:
            ids = RE_PADRE.findall(p["consulta"])
            L.append(f"| {', '.join('`' + i + '`' for i in ids[:3])}{' …' if len(ids) > 3 else ''} | {p['devueltos']} | "
                     f"{p['unicos']} | {p['repetidos']} |")
    else:
        L.append("No se observó.")
    L += ["", "## Carpetas que el conector no entrega completas", ""]
    if inv["truncadas"] or inv["omisiones_detectadas"]:
        L += ["Al llegar a unos 2.000 resultados por consulta el conector deja de traer elementos nuevos. El número "
              "listado es un mínimo.", ""]
        for t in inv["truncadas"]:
            L.append(f"- Truncada: {', '.join('`' + p + '`' for p in t['padres'])} — {t['unicos']} elementos únicos vistos.")
        for o in inv["omisiones_detectadas"]:
            L.append(f"- Omisión comprobada: carpeta `{o['carpeta_id']}`: un listado que terminó sin más páginas dejó "
                     f"fuera {o['omitidos']} elemento(s) que otro listado sí vio.")
    else:
        L.append("No se observó.")
    L += ["", "## Posibles duplicados y homónimos", "",
          f"{len(inv['posibles_duplicados'])} grupos con el mismo título y el mismo tamaño "
          f"({sum(1 for d in inv['posibles_duplicados'] if d['propio_y_tercero'])} entre la copia propia y la de un tercero). "
          f"{len(inv['homonimos'])} grupos con el mismo título y distinto tamaño. Detalle en `inventario.json` "
          "(`posibles_duplicados`, `homonimos`). No se compara el contenido: es un indicio, no una prueba. "
          "No se borra ningún original.", "",
          "## Cola de trabajo", ""]
    for t in inv["truncadas"]:
        L.append(f"- Truncada por el conector: {', '.join('`' + p + '`' for p in t['padres'])}. Para completarla hay que "
                 "listarla con la API de Drive (cuenta de servicio) o partir la consulta por fecha de creación.")
    if inv["pendientes"] or inv["a_medias"]:
        L.append(f"- Carpetas pendientes de listar ({len(inv['pendientes'])}): " + ", ".join(f"`{i}`" for i in inv["pendientes"][:60]))
        for a in inv["a_medias"]:
            L.append(f"- A medias: `{a['consulta'][:120]}` (token en `inventario.json` → `a_medias`)")
    else:
        L.append("No quedan carpetas por listar con el conector." if not inv["truncadas"] else
                 "No quedan más carpetas por listar con el conector, salvo las truncadas.")
    obs = inv.get("observaciones") or []
    if obs:
        L += ["", "## Observaciones", "", "Registradas a mano en `biblioteca/observaciones.json`.", ""]
        for o in obs:
            L += [f"### {o['id']} — {o['tema']}", "", f"- Estado: **{o['estado']}**", f"- Comprobado: {o['comprobado']}"]
            for clave, rotulo in (("interpretacion", "Interpretación"), ("consecuencia", "Consecuencia")):
                if o.get(clave):
                    L.append(f"- {rotulo}: {o[clave]}")
            L.append("")
    return "\n".join(L).rstrip("\n") + "\n"


def escribir_json(inv, ruta):
    """Un elemento por línea: el archivo es grande y así los cambios se pueden revisar."""
    cab = {k: v for k, v in inv.items() if k != "elementos"}
    texto = json.dumps(cab, ensure_ascii=False, indent=1)[:-2] + ',\n "elementos": [\n'
    texto += ",\n".join("  " + json.dumps(e, ensure_ascii=False, sort_keys=True) for e in inv["elementos"])
    texto += "\n ]\n}\n"
    Path(ruta).parent.mkdir(exist_ok=True)
    Path(ruta).write_text(texto, encoding="utf-8")


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)

    def opcion(nombre, defecto=None):
        return argv[argv.index(nombre) + 1] if nombre in argv else defecto

    rutas = [a for a in argv if a.endswith(".jsonl")]
    raices = (opcion("--raices") or "").split(",")
    ruta_ext = Path(opcion("--extraccion", str(EXTRACCION)))
    extraccion = json.loads(ruta_ext.read_text(encoding="utf-8")) if ruta_ext.is_file() else {}
    inv = construir(rutas, raices, extraccion.get("documentos", extraccion))
    ruta_obs = Path(opcion("--observaciones", str(OBSERVACIONES)))
    if ruta_obs.is_file():
        inv["observaciones"] = json.loads(ruta_obs.read_text(encoding="utf-8")).get("observaciones", [])
    escribir_json(inv, opcion("--salida", str(SALIDA)))
    Path(opcion("--md", str(SALIDA_MD))).write_text(informe_md(inv), encoding="utf-8")
    print(json.dumps(inv["resumen"], ensure_ascii=False, indent=1))
    por_carpeta = Counter()
    for e in inv["elementos"]:
        if e["mime"] not in (CARPETA, ATAJO):
            por_carpeta["/".join(e["ruta"].split("/")[:2]) if e["ruta"] else "(raíz)"] += 1
    print("archivos por carpeta (dos primeros niveles):", dict(por_carpeta.most_common(30)))
    print("PENDIENTES (hasta 40):", " ".join(inv["pendientes"][:40]))
    for a in inv["a_medias"][:8]:
        print("A MEDIAS:", a["consulta"][:80], "token:", a["pageToken"][:20], "…")
    for t in inv["truncadas"]:
        print("TRUNCADA:", t["padres"], t["unicos"], "únicos (el conector no entrega más)")
    for o in inv["omisiones_detectadas"]:
        print("OMISIÓN:", o["carpeta_id"], o["omitidos"])
    for p in inv["paginacion_con_repetidos"]:
        print("REPETIDOS:", p["consulta"][:60], p["devueltos"], "devueltos,", p["unicos"], "únicos")


if __name__ == "__main__":
    main()
