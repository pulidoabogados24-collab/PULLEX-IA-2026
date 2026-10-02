"""Genera el registro de 1.000 perfiles de PULLEX a partir de los datos escritos a mano.

    python -m perfiles.generar              # escribe perfiles/registro.json y perfiles/REGISTRO.md
    python -m perfiles.generar --comprobar  # no escribe: falla si lo que hay en disco no coincide

Es determinista: no usa fechas, azar ni el orden de un diccionario sin ordenar; dos corridas sobre el mismo
código producen exactamente los mismos bytes (lo comprueba tests/test_perfiles.py).

Un perfil es una ficha (instrucciones + contrato de entrada y salida), no un agente en ejecución. Aquí solo se
asignan dos estados: DEFINIDO y CONECTADO_A_HERRAMIENTAS. Este último exige que TODAS las herramientas del
perfil existan hoy en el código, y eso se comprueba buscando la evidencia declarada en cada archivo. Los
estados EJECUTADO, EVALUADO y APROBADO no se pueden asignar desde aquí: dependen de ejecuciones reales
registradas en la base de datos (ver docs/16-PERFILES-Y-COORDINADOR.md).
"""
import hashlib
import json
import re
import sys
import unicodedata
from pathlib import Path

from perfiles import definiciones as D

RAIZ = Path(__file__).resolve().parent.parent
SALIDA_JSON = RAIZ / "perfiles" / "registro.json"
SALIDA_MD = RAIZ / "perfiles" / "REGISTRO.md"
ESPECIFICACION = RAIZ / "docs" / "coordinacion" / "ESPECIFICACION-LEXCOL.md"
VERSION = "1.0.0"
ESQUEMA = "pullex-perfiles/1"

MAX_INSTRUCCIONES = 1200
MAX_FUENTE_CORTA = 70   # en el propósito de F02 cada fuente va abreviada; completa queda en «fuentes»
MIN_PROPOSITO = 120
# Umbrales de similitud entre propósitos de la MISMA función (Jaccard sobre el conjunto de palabras del texto
# completo, plantilla incluida). Se fijaron antes de medir; el generador falla si se superan.
UMBRAL_SIMILITUD_MAX = 0.60
UMBRAL_SIMILITUD_MEDIA = 0.35

RE_ID = re.compile(r"^A(0[1-9]|10)-S(0[1-9]|10)-F(0[1-9]|10)$")
# Instituciones de educación superior: ningún perfil las nombra.
RE_UNIVERSIDAD = re.compile(r"universidad|\buniv\.|uniandes|javeriana|externado|\bunal\b|politecnico|"
                            r"institucion universitaria|alma mater", re.I)
# Identificadores de providencias: ningún perfil los trae (ni reales ni inventados).
RE_PROVIDENCIA = re.compile(
    r"\b(?:C|T|SU|A)\s?-\s?\d{2,4}(?:\s+de\s+\d{4}|\s*/\s*\d{2,4})?\b|"
    r"\b(?:SL|SC|SP|STC|STL|STP|AL|AC|AP)\s?\d{2,6}\s?-\s?\d{4}\b|"
    r"\bsentencia\s+(?:n[°ºo.]*\s*)?\d|\bradicad[oa]\s+(?:n[°ºo.]*\s*)?\d", re.I)
# Toda norma citada con número en la lista de fuentes debe llevar «(verificar vigencia)».
RE_NORMA = re.compile(r"\b(?:Ley|Decreto(?: Ley)?|Decisión(?: Andina)?|Acto Legislativo|Resolución)\s+\d{1,5}\s+de\s+\d{4}")
RE_RUTA = re.compile(r"(?<![\w/.*-])((?:docs|tests|static|scripts|perfiles|evaluacion|biblioteca|demo)/[\w.*/-]*[\w/]|"
                     r"[\w-]+\.(?:py|md|txt|yaml|lock|json|webmanifest)|\.env\.example)(?![\w/*-])")
_CARPETAS = ("", "static", "docs", "tests", "scripts", "perfiles", "evaluacion", "demo", "biblioteca")


def existe_ruta(ruta: str) -> bool:
    """¿La ruta citada en una fuente existe en el repositorio? Admite comodines y nombres sin carpeta."""
    if "*" in ruta:
        return any(RAIZ.glob(ruta))
    if "/" in ruta:
        return (RAIZ / ruta).exists()
    return any((RAIZ / c / ruta).exists() for c in _CARPETAS)


# ------------------------------------------------------------------------------ texto --
def sin_tildes(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", str(texto)) if unicodedata.category(c) != "Mn")


def palabras(texto: str) -> frozenset:
    return frozenset(p for p in re.findall(r"[a-z0-9ñ]+", sin_tildes(texto).lower()) if len(p) >= 3)


def jaccard(a: frozenset, b: frozenset) -> float:
    return len(a & b) / len(a | b) if (a or b) else 0.0


def _capital(texto: str) -> str:
    return texto[0].upper() + texto[1:]


def _fuente_corta(fuente: str) -> str:
    """La fuente sin paréntesis ni coletilla de verificación: en el propósito va una sola advertencia al final
    y el texto completo queda en el campo «fuentes» del perfil."""
    corta = re.sub(r"\s+", " ", re.sub(r"\s*\([^)]*\)", "", fuente)).strip(" ,;")
    if len(corta) > MAX_FUENTE_CORTA:
        cortes = [m.start() for m in re.finditer(r"[,;] ", corta)]
        dentro = [c for c in cortes if c <= MAX_FUENTE_CORTA]
        if cortes:
            corta = corta[:dentro[-1] if dentro else cortes[0]]
    return corta


# ---------------------------------------------------------------------- herramientas --
def verificar_herramientas() -> dict:
    """Para cada herramienta: si existe HOY (declarada EXISTE y con toda su evidencia en el código)."""
    salida = {}
    for hid, h in D.HERRAMIENTAS.items():
        faltantes = []
        if h["estado"] == "EXISTE":
            for archivo, texto in h["evidencia"]:
                ruta = RAIZ / archivo
                if not ruta.is_file() or texto not in ruta.read_text(encoding="utf-8"):
                    faltantes.append(f"{archivo}: «{texto}»")
        salida[hid] = {"existe": h["estado"] == "EXISTE" and bool(h["evidencia"]) and not faltantes,
                       "faltantes": faltantes}
    return salida


# --------------------------------------------------------------------------- perfiles --
def _herramientas_de(funcion: dict, sub: dict, tipo: str) -> list:
    ids = list(funcion["herramientas"][tipo])
    for hid, funciones in sorted(sub["herramientas"].items()):
        if funciones == "*" or funcion["id"] in funciones.split():
            if hid not in ids:
                ids.append(hid)
    return ids


def _proposito(funcion: dict, sub: dict, tipo: str) -> str:
    plantilla = funcion.get("proposito_" + tipo) or funcion["proposito"]
    fuentes = "; ".join(_fuente_corta(f) for f in sub["fuentes"])
    if tipo == "derecho":
        fuentes += " (toda norma: verificar vigencia)"
    texto = plantilla.format(
        tema=sub["tema"], entradas="; ".join(sub["entradas"]), fuentes=fuentes, extraer=sub["extraer"],
        vigencia=sub["vigencia"], preguntas=sub["preguntas"], opciones=sub["opciones"],
        entregable=sub["entregable"], comprobacion_1=sub["comprobaciones"][0],
        comprobacion_2=sub["comprobaciones"][1], riesgos=" ".join(sub["riesgos"]), objeto=sub["objeto"])
    return texto.replace(" de el ", " del ").replace(" a el ", " al ")


def _salida(funcion: dict, sub: dict) -> dict:
    secciones = []
    for sid, titulo in funcion["salida"]:
        descripcion = D.DESCRIPCIONES_SALIDA[sid]
        if funcion["id"] == "F07" and sid == "entregable":
            descripcion = f"El entregable de la subespecialidad ({sub['entregable']}), con lo pendiente entre corchetes."
        if funcion["id"] == "F08" and sid == "comprobaciones":
            descripcion += " Incluye las dos comprobaciones propias de la subespecialidad."
        secciones.append({"id": sid, "titulo": titulo, "obligatorio": True, "descripcion": descripcion})
    secciones += [dict(s) for s in D.COMUNES_SALIDA]
    return {"formato": "Markdown: un encabezado «## » por sección, en este orden y con estos títulos.",
            "secciones": secciones,
            "cierre": ("Última línea: «Sentido: favorable», «Sentido: desfavorable», «Sentido: condicionado» o "
                       "«Sentido: indeterminado».") if funcion["emite_posicion"] else None}


def _instrucciones(pid: str, funcion: dict, sub: dict, area: dict, proposito: str, salida: dict) -> str:
    titulos = "; ".join(s["titulo"] for s in salida["secciones"])
    cierre = " Última línea: «Sentido: favorable», «desfavorable», «condicionado» o «indeterminado»." \
        if funcion["emite_posicion"] else ""
    return (f"PERFIL PULLEX {pid} · {funcion['nombre']}.\n"
            f"MISIÓN: {proposito}\n{D.REGLAS[area['tipo']]}\n"
            f"SALIDA (secciones con «## », en este orden): {titulos}.{cierre}")


def _activacion(funcion: dict, sub: dict, area: dict, solo_admin: bool) -> dict:
    intenciones = [i for i in D.INTENCIONES if funcion["id"] in i["cadena"]]
    piden = " o ".join(i["nombre"] for i in intenciones)
    return {
        "descripcion": (f"El coordinador lo elige cuando la tarea trata de {sub['nombre']} "
                        f"({area['nombre']}) y pide {piden}. También puede pedirse por su identificador."),
        "intenciones": [i["id"] for i in intenciones],
        "claves_subespecialidad": list(sub["claves"]),
        "claves_area": list(area["claves"]),
        "estado_minimo_para_ejecutar": D.ESTADO_MINIMO_EJECUTABLE,
        "solo_administracion": solo_admin,
    }


def _perfil(area: dict, sub: dict, funcion: dict, existencia: dict) -> dict:
    pid = f"{area['id']}-{sub['id']}-{funcion['id']}"
    tipo = area["tipo"]
    hids = _herramientas_de(funcion, sub, tipo)
    herramientas = [{"id": h, "nombre": D.HERRAMIENTAS[h]["nombre"],
                     "estado": "EXISTE" if existencia[h]["existe"] else "PROPUESTA",
                     "modo": D.HERRAMIENTAS[h]["modo"]} for h in hids]
    faltan = [h["nombre"] for h in herramientas if h["estado"] != "EXISTE"]
    solo_admin = any(D.HERRAMIENTAS[h]["solo_admin"] for h in hids)
    if faltan:
        estado = "DEFINIDO"
        motivo = "Todavía no se puede ejecutar: depende de una herramienta que es una propuesta (" + "; ".join(faltan) + ")."
    else:
        estado = "CONECTADO_A_HERRAMIENTAS"
        motivo = ("Todas sus herramientas existen hoy en el código y el coordinador puede entregárselas. No tiene "
                  "ninguna ejecución con el modelo real: nadie ha medido cómo responde.")
    proposito = _proposito(funcion, sub, tipo)
    salida = _salida(funcion, sub)
    limites = list(funcion["limites"]) + ["Riesgo que debe evitar: " + r for r in sub["riesgos"]] + [D.LIMITES_TIPO[tipo]]
    if area["id"] in D.LIMITES_AREA:
        limites.append(D.LIMITES_AREA[area["id"]])
    presupuesto = {**D.PRESUPUESTO_BASE, **funcion["presupuesto"]}
    return {
        "id": pid,
        "nombre": f"{_capital(funcion['nombre'])} — {sub['nombre']} ({area['id']} {area['nombre']})",
        "area": {"id": area["id"], "nombre": area["nombre"]},
        "subespecialidad": {"id": sub["id"], "nombre": sub["nombre"]},
        "funcion": {"id": funcion["id"], "nombre": funcion["nombre"]},
        "tipo": tipo,
        "proposito": proposito,
        "entradas": list(funcion["entradas"]) + list(sub["entradas"]),
        "herramientas_permitidas": herramientas,
        "fuentes": list(sub["fuentes"]),
        "salida_estructurada": salida,
        "limites": limites,
        "pruebas_de_aceptacion": list(funcion["pruebas"]) + list(sub["comprobaciones"]),
        "presupuesto": presupuesto,
        "condicion_de_activacion": _activacion(funcion, sub, area, solo_admin),
        "estado_real": estado,
        "estado_motivo": motivo,
        "solo_administracion": solo_admin,
        "emite_posicion": funcion["emite_posicion"],
        "instrucciones": _instrucciones(pid, funcion, sub, area, proposito, salida),
    }


# -------------------------------------------------------------------------- similitud --
def medir_similitud(perfiles: list) -> dict:
    """Similitud de Jaccard (conjunto de palabras de 3 o más letras, sin tildes) entre propósitos."""
    bolsa = {p["id"]: palabras(p["proposito"]) for p in perfiles}
    por_funcion = {}
    for f in D.FUNCIONES_IDS:
        ids = [p["id"] for p in perfiles if p["funcion"]["id"] == f]
        total, n, maximo, par = 0.0, 0, 0.0, None
        for i, a in enumerate(ids):
            for b in ids[i + 1:]:
                j = jaccard(bolsa[a], bolsa[b])
                total += j
                n += 1
                if j > maximo:
                    maximo, par = j, [a, b]
        por_funcion[f] = {"pares": n, "media": round(total / n, 4), "maxima": round(maximo, 4), "par_mas_parecido": par}
    # Vecino más parecido de cada perfil en todo el registro (cualquier área y función).
    ids = [p["id"] for p in perfiles]
    maximo, par, suma_vecino = 0.0, None, 0.0
    mejor = dict.fromkeys(ids, 0.0)
    for i, a in enumerate(ids):
        ba = bolsa[a]
        for b in ids[i + 1:]:
            j = jaccard(ba, bolsa[b])
            if j > mejor[a]:
                mejor[a] = j
            if j > mejor[b]:
                mejor[b] = j
            if j > maximo:
                maximo, par = j, [a, b]
    suma_vecino = sum(mejor.values())
    medias = [v["media"] for v in por_funcion.values()]
    return {
        "metrica": "Jaccard sobre el conjunto de palabras (3 o más letras, sin tildes) del propósito completo, "
                   "plantilla de la función incluida. 0 = sin palabras comunes; 1 = las mismas palabras.",
        "umbral_maxima_misma_funcion": UMBRAL_SIMILITUD_MAX,
        "umbral_media_misma_funcion": UMBRAL_SIMILITUD_MEDIA,
        "misma_funcion": por_funcion,
        "misma_funcion_media_global": round(sum(medias) / len(medias), 4),
        "misma_funcion_maxima_global": max(v["maxima"] for v in por_funcion.values()),
        "todo_el_registro_maxima": round(maximo, 4),
        "todo_el_registro_par_mas_parecido": par,
        "todo_el_registro_media_del_vecino_mas_parecido": round(suma_vecino / len(ids), 4),
        "propositos_distintos": len({p["proposito"] for p in perfiles}),
    }


# ---------------------------------------------------------------------------- registro --
def construir() -> dict:
    areas = D.cargar_areas()
    existencia = verificar_herramientas()
    perfiles = [_perfil(a, s, f, existencia) for a in areas for s in a["subespecialidades"] for f in D.FUNCIONES]
    por_area, por_estado, por_area_estado, matriz = {}, {e: 0 for e in D.ESTADOS_IDS}, {}, {}
    for p in perfiles:
        a, f, e = p["area"]["id"], p["funcion"]["id"], p["estado_real"]
        por_area[a] = por_area.get(a, 0) + 1
        por_estado[e] += 1
        por_area_estado.setdefault(a, {x: 0 for x in D.ESTADOS_IDS})[e] += 1
        celda = matriz.setdefault(a, {}).setdefault(f, {"total": 0, "conectados": 0})
        celda["total"] += 1
        celda["conectados"] += e == "CONECTADO_A_HERRAMIENTAS"
    herramientas = {}
    for hid, h in D.HERRAMIENTAS.items():
        herramientas[hid] = {
            "nombre": h["nombre"], "estado": "EXISTE" if existencia[hid]["existe"] else "PROPUESTA",
            "modo": h["modo"], "solo_administracion": h["solo_admin"], "nota": h["nota"],
            "evidencia": [f"{a}: {t}" for a, t in h["evidencia"]],
            "perfiles_que_la_usan": sum(1 for p in perfiles if any(x["id"] == hid for x in p["herramientas_permitidas"])),
        }
    huella = hashlib.sha256(json.dumps(perfiles, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()
    return {
        "esquema": ESQUEMA,
        "version": VERSION,
        "huella": huella,
        "generado_por": "perfiles/generar.py a partir de perfiles/definiciones.py y perfiles/areas/",
        "nota": ("Un perfil es una ficha con instrucciones y contrato de entrada y salida. No es un agente en "
                 "ejecución. Ningún perfil de este archivo tiene ejecuciones con el modelo real; las ejecuciones se "
                 "registran en la base de datos, no aquí."),
        "estados": [dict(e) for e in D.ESTADOS],
        "funciones": [{"id": f["id"], "nombre": f["nombre"], "emite_posicion": f["emite_posicion"]} for f in D.FUNCIONES],
        "areas": [{"id": a["id"], "nombre": a["nombre"], "tipo": a["tipo"], "claves": list(a["claves"]),
                   "subespecialidades": [{"id": s["id"], "nombre": s["nombre"], "tema": s["tema"], "objeto": s["objeto"],
                                          "entregable": s["entregable"], "entradas": list(s["entradas"]),
                                          "claves": list(s["claves"])}
                                         for s in a["subespecialidades"]]} for a in areas],
        "intenciones": [{"id": i["id"], "nombre": i["nombre"], "cadena": list(i["cadena"]), "claves": list(i["claves"])}
                        for i in D.INTENCIONES],
        "neutralizar": list(D.NEUTRALIZAR),
        "herramientas": herramientas,
        "resumen": {"total": len(perfiles), "por_area": por_area, "por_estado": por_estado,
                    "por_area_y_estado": por_area_estado, "matriz_area_funcion": matriz,
                    "similitud_de_propositos": medir_similitud(perfiles)},
        "perfiles": perfiles,
    }


def serializar(registro: dict) -> str:
    return json.dumps(registro, ensure_ascii=False, indent=1) + "\n"


# ------------------------------------------------------------------------ validaciones --
def areas_de_la_especificacion() -> list:
    """[(id, nombre, [subespecialidades])] leídas de la sección 6 de la especificación."""
    texto = ESPECIFICACION.read_text(encoding="utf-8")
    salida = []
    for m in re.finditer(r"^(A\d\d) — (.+?)\.\nSubespecialidades: (.+?)\.$", texto, re.M):
        subs = [s.strip() for s in re.split(r",| y (?=[^,]*$)", m.group(3)) if s.strip()]
        salida.append((m.group(1), m.group(2), subs))
    return salida


def validar(registro: dict) -> list:
    """Devuelve la lista de errores (vacía si el registro es válido)."""
    e = []
    perfiles = registro["perfiles"]
    ids = [p["id"] for p in perfiles]
    if len(perfiles) != 1000:
        e.append(f"hay {len(perfiles)} perfiles, no 1.000")
    if len(set(ids)) != len(ids):
        e.append("hay identificadores repetidos")
    e += [f"identificador mal formado: {i}" for i in ids if not RE_ID.match(i)]
    for a in D.AREAS_META:
        n = sum(1 for p in perfiles if p["area"]["id"] == a[0])
        if n != 100:
            e.append(f"{a[0]} tiene {n} perfiles, no 100")
    for f in D.FUNCIONES_IDS:
        n = sum(1 for p in perfiles if p["funcion"]["id"] == f)
        if n != 100:
            e.append(f"{f} tiene {n} perfiles, no 100")

    # Áreas, subespecialidades y funciones: las de la especificación, en su orden.
    if ESPECIFICACION.is_file():
        esperado = areas_de_la_especificacion()
        real = [(a["id"], a["nombre"], [s["nombre"] for s in a["subespecialidades"]]) for a in registro["areas"]]
        if esperado != real:
            e.append("las áreas o subespecialidades no coinciden con la sección 6 de la especificación")
        texto = ESPECIFICACION.read_text(encoding="utf-8")
        for f in registro["funciones"]:
            if f"{f['id']}: {f['nombre']}." not in texto:
                e.append(f"la función {f['id']} no coincide con la especificación")
    for a in registro["areas"]:
        if [s["id"] for s in a["subespecialidades"]] != [f"S{n:02d}" for n in range(1, 11)]:
            e.append(f"{a['id']}: las subespecialidades no son S01…S10 en orden")

    obligatorios = ("id", "nombre", "area", "subespecialidad", "funcion", "proposito", "entradas",
                    "herramientas_permitidas", "fuentes", "salida_estructurada", "limites", "pruebas_de_aceptacion",
                    "presupuesto", "condicion_de_activacion", "estado_real", "instrucciones")
    existencia = verificar_herramientas()
    for hid, v in existencia.items():
        if D.HERRAMIENTAS[hid]["estado"] == "EXISTE" and not v["existe"]:
            e.append(f"la herramienta «{hid}» se declara EXISTE pero falta su evidencia: {'; '.join(v['faltantes']) or 'ninguna declarada'}")
    for p in perfiles:
        pid = p["id"]
        for c in obligatorios:
            if c not in p or p[c] in (None, "", [], {}):
                e.append(f"{pid}: falta «{c}»")
        if len(p["proposito"]) < MIN_PROPOSITO:
            e.append(f"{pid}: propósito demasiado corto ({len(p['proposito'])})")
        if not 300 <= len(p["instrucciones"]) <= MAX_INSTRUCCIONES:
            e.append(f"{pid}: instrucciones de {len(p['instrucciones'])} caracteres (deben tener entre 300 y {MAX_INSTRUCCIONES})")
        if "No verificado" not in p["instrucciones"] or "no órdenes" not in p["instrucciones"]:
            e.append(f"{pid}: las instrucciones no traen las reglas de fuentes y de «No verificado»")
        if p["tipo"] == "derecho" and "verificar vigencia" not in p["instrucciones"]:
            e.append(f"{pid}: las instrucciones no exigen «verificar vigencia»")
        if len(p["entradas"]) < 3 or len(p["fuentes"]) < 4 or len(p["limites"]) < 4 or len(p["pruebas_de_aceptacion"]) < 4:
            e.append(f"{pid}: entradas, fuentes, límites o pruebas por debajo del mínimo")
        if any(len(x) < 12 for x in p["entradas"] + p["fuentes"] + p["limites"] + p["pruebas_de_aceptacion"]):
            e.append(f"{pid}: hay un elemento de lista demasiado corto")
        secciones = [s["id"] for s in p["salida_estructurada"]["secciones"]]
        if "no_verificado" not in secciones or "fuentes_usadas" not in secciones or len(secciones) < 6:
            e.append(f"{pid}: la salida estructurada no tiene las secciones obligatorias")
        pr = p["presupuesto"]
        if pr.get("max_llamadas_modelo") != 1 or not 0 < pr.get("max_tokens_salida", 0) <= 3000 \
                or not 0 < pr.get("tiempo_max_s", 0) <= 90 or pr.get("max_busquedas_web", 99) > 2:
            e.append(f"{pid}: presupuesto fuera de los topes conservadores")
        if not p["herramientas_permitidas"]:
            e.append(f"{pid}: sin herramientas")
        for h in p["herramientas_permitidas"]:
            if h["id"] not in D.HERRAMIENTAS:
                e.append(f"{pid}: herramienta desconocida {h['id']}")
        todas = all(existencia[h["id"]]["existe"] for h in p["herramientas_permitidas"] if h["id"] in existencia)
        if p["estado_real"] not in ("DEFINIDO", "CONECTADO_A_HERRAMIENTAS"):
            e.append(f"{pid}: estado «{p['estado_real']}» no permitido (no hay ejecuciones reales)")
        elif (p["estado_real"] == "CONECTADO_A_HERRAMIENTAS") != todas:
            e.append(f"{pid}: el estado no corresponde a la existencia de sus herramientas")
        for f in p["fuentes"]:
            if RE_NORMA.search(f) and D.VERIFICAR not in f:
                e.append(f"{pid}: norma con número sin «verificar vigencia»: {f}")
            for ruta in RE_RUTA.findall(f):
                if not existe_ruta(ruta) and ruta != "perfiles/registro.json":
                    e.append(f"{pid}: la fuente cita una ruta que no existe en el repositorio: {ruta}")
    for campo in ("proposito", "nombre", "instrucciones"):
        if len({p[campo] for p in perfiles}) != len(perfiles):
            e.append(f"hay «{campo}» repetidos")

    sim = registro["resumen"]["similitud_de_propositos"]
    for f, v in sim["misma_funcion"].items():
        if v["maxima"] > UMBRAL_SIMILITUD_MAX:
            e.append(f"{f}: similitud máxima {v['maxima']} entre {v['par_mas_parecido']} (umbral {UMBRAL_SIMILITUD_MAX})")
        if v["media"] > UMBRAL_SIMILITUD_MEDIA:
            e.append(f"{f}: similitud media {v['media']} (umbral {UMBRAL_SIMILITUD_MEDIA})")

    texto = serializar(registro)
    for m in RE_UNIVERSIDAD.finditer(texto):
        e.append(f"se nombra una institución de educación superior: «{texto[max(0, m.start() - 30):m.end() + 30]}»")
    for m in RE_PROVIDENCIA.finditer(texto):
        e.append(f"aparece un identificador de providencia: «{texto[max(0, m.start() - 30):m.end() + 30]}»")
    return e


# -------------------------------------------------------------------------- REGISTRO.md --
_NOMBRE_ESTADO = {x["id"]: x["nombre"] for x in D.ESTADOS}


def a_markdown(registro: dict) -> str:
    r = registro["resumen"]
    sim = r["similitud_de_propositos"]
    L = ["# Registro de perfiles de PULLEX", "",
         f"Versión {registro['version']} · esquema `{registro['esquema']}` · huella `{registro['huella'][:16]}`", "",
         "Archivo generado por `python -m perfiles.generar`. **No se edita a mano**: los datos fuente están en "
         "`perfiles/definiciones.py` y `perfiles/areas/`. La versión completa y legible por máquina es "
         "`perfiles/registro.json`; el diseño está en `docs/16-PERFILES-Y-COORDINADOR.md`.", "",
         "Un perfil es una **ficha** (instrucciones más contrato de entrada y salida). No es un agente en "
         "ejecución. Ningún perfil de este registro se ha ejecutado contra el modelo real.", "",
         "## Estado real", "", "| Estado | Qué significa | Perfiles |", "|---|---|---|"]
    for est in registro["estados"]:
        L.append(f"| {est['nombre']} (`{est['id']}`) | {est['significado']} | {r['por_estado'][est['id']]} |")
    L += ["", "## Perfiles por área y estado", "", "| Área | Total | Definido | Conectado a herramientas | Ejecutado | Evaluado | Aprobado |",
          "|---|---|---|---|---|---|---|"]
    for a in registro["areas"]:
        c = r["por_area_y_estado"][a["id"]]
        L.append(f"| {a['id']} {a['nombre']} | {r['por_area'][a['id']]} | {c['DEFINIDO']} | {c['CONECTADO_A_HERRAMIENTAS']} | "
                 f"{c['EJECUTADO']} | {c['EVALUADO']} | {c['APROBADO']} |")
    L += ["", "## Matriz área × función (perfiles conectados a herramientas, de 10)", "",
          "| Área | " + " | ".join(f["id"] for f in registro["funciones"]) + " |", "|---|" + "---|" * 10]
    for a in registro["areas"]:
        L.append(f"| {a['id']} | " + " | ".join(str(r["matriz_area_funcion"][a["id"]][f["id"]]["conectados"])
                                               for f in registro["funciones"]) + " |")
    L += ["", "Funciones: " + "; ".join(f"{f['id']} {f['nombre']}" for f in registro["funciones"]) + ".", "",
          "## Herramientas", "", "| Herramienta | Estado | Modo | Perfiles | Nota |", "|---|---|---|---|---|"]
    for hid, h in registro["herramientas"].items():
        L.append(f"| {h['nombre']} (`{hid}`) | {h['estado']} | {h['modo']} | {h['perfiles_que_la_usan']} | {h['nota']} |")
    L += ["", "## Similitud entre propósitos", "", sim["metrica"], "",
          f"- Propósitos distintos: {sim['propositos_distintos']} de {r['total']}.",
          f"- Misma función: media {sim['misma_funcion_media_global']} (umbral {sim['umbral_media_misma_funcion']}), "
          f"máxima {sim['misma_funcion_maxima_global']} (umbral {sim['umbral_maxima_misma_funcion']}).",
          f"- Todo el registro: par más parecido {' y '.join(sim['todo_el_registro_par_mas_parecido'])} con "
          f"{sim['todo_el_registro_maxima']}; media del vecino más parecido {sim['todo_el_registro_media_del_vecino_mas_parecido']}.",
          "", "| Función | Media | Máxima | Par más parecido |", "|---|---|---|---|"]
    for f, v in sim["misma_funcion"].items():
        L.append(f"| {f} | {v['media']} | {v['maxima']} | {' · '.join(v['par_mas_parecido'])} |")
    por_sub = {}
    for p in registro["perfiles"]:
        por_sub.setdefault((p["area"]["id"], p["subespecialidad"]["id"]), []).append(p)
    for a in registro["areas"]:
        L += ["", f"## {a['id']} — {a['nombre']}"]
        for s in a["subespecialidades"]:
            lista = por_sub[(a["id"], s["id"])]
            L += ["", f"### {a['id']}-{s['id']} · {s['nombre']}", "", s["objeto"], "",
                  "Fuentes: " + "; ".join(lista[0]["fuentes"]) + ".", ""]
            for p in lista:
                L.append(f"- **{p['id']}** · {p['funcion']['nombre']} · {_NOMBRE_ESTADO[p['estado_real']]} — {p['proposito']}")
    return "\n".join(L) + "\n"


# -------------------------------------------------------------------------------- main --
def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    registro = construir()
    errores = validar(registro)
    if serializar(construir()) != serializar(registro):
        errores.append("dos corridas seguidas no producen el mismo registro")
    r = registro["resumen"]
    sim = r["similitud_de_propositos"]
    print(f"Perfiles: {r['total']} · por estado: " + ", ".join(f"{k}={v}" for k, v in r["por_estado"].items()))
    print("Por área: " + ", ".join(f"{a}={n}" for a, n in r["por_area"].items()))
    print(f"Similitud (misma función): media {sim['misma_funcion_media_global']}, máxima {sim['misma_funcion_maxima_global']}; "
          f"todo el registro: máxima {sim['todo_el_registro_maxima']} {sim['todo_el_registro_par_mas_parecido']}")
    if errores:
        print(f"\n{len(errores)} errores de validación:")
        for x in errores[:60]:
            print(" -", x)
        return 1
    texto, md = serializar(registro), a_markdown(registro)
    if "--comprobar" in argv:
        ok = SALIDA_JSON.is_file() and SALIDA_JSON.read_text(encoding="utf-8") == texto \
            and SALIDA_MD.is_file() and SALIDA_MD.read_text(encoding="utf-8") == md
        print("El registro en disco coincide con los datos fuente." if ok else
              "El registro en disco NO coincide: ejecuta `python -m perfiles.generar`.")
        return 0 if ok else 1
    SALIDA_JSON.write_text(texto, encoding="utf-8")
    SALIDA_MD.write_text(md, encoding="utf-8")
    print(f"Escrito {SALIDA_JSON.relative_to(RAIZ)} ({len(texto.encode('utf-8')) // 1024} KB) y {SALIDA_MD.relative_to(RAIZ)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
