"""Construye biblioteca/inventario.json a partir de los listados de Google Drive hechos con el
conector de Drive durante una sesión de trabajo (se leen de la transcripción de la sesión).

Por qué así: el conector de Drive solo se puede usar desde el asistente, no desde un script. Este
script convierte esos listados en un inventario verificable y REANUDABLE: dice qué carpetas faltan
por listar y qué páginas quedaron a medias, para continuar sin repetir trabajo.

    python scripts/cosechar_inventario_drive.py <transcripcion.jsonl> [más.jsonl …] [--raices id1,id2,...]

No lee el contenido de ningún archivo: solo metadatos (id, título, carpeta, tipo, tamaño, fechas,
propietario). Estado de cada elemento: ENCONTRADO. Leer, extraer, indexar y validar son pasos aparte.
"""
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SALIDA = RAIZ / "biblioteca" / "inventario.json"
CARPETA = "application/vnd.google-apps.folder"
ATAJO = "application/vnd.google-apps.shortcut"
PROPIO = "pulidoabogados24@gmail.com"

# Nombre de persona en mayúsculas seguido de un tipo de escrito, o palabras de expediente: se
# trata como posible dato personal hasta que un humano lo clasifique.
PATRON_PERSONA = re.compile(
    r"^(?:[A-ZÁÉÍÓÚÑ]{3,}\s+){2,4}[A-ZÁÉÍÓÚÑ]{3,}\s*,?\s+(?:DERECHO|TUTELA|DEMANDA|PODER|QUERELLA|DENUNCIA|CONTRATO|PROCESO)")
PATRON_EXPEDIENTE = re.compile(r"\b(CLIENTE|EXPEDIENTE|HISTORIA CL[IÍ]NICA|C[ÉE]DULA)\b", re.I)


def _texto(contenido):
    if isinstance(contenido, str):
        return contenido
    if isinstance(contenido, list):
        return "".join(b.get("text", "") for b in contenido if isinstance(b, dict))
    return ""


def leer_listados(ruta):
    """Devuelve [(consulta, pageToken_usado, resultado_json)] de cada búsqueda de Drive."""
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
            if b.get("type") == "tool_use" and b.get("name", "").endswith("Google_Drive__search_files"):
                usos[b["id"]] = b.get("input") or {}
            elif b.get("type") == "tool_result" and b.get("tool_use_id") in usos:
                try:
                    r = json.loads(_texto(b.get("content")))
                except json.JSONDecodeError:
                    continue
                ent = usos[b["tool_use_id"]]
                salida.append((ent.get("query", ""), ent.get("pageToken"), r))
    return salida


def sensibilidad(titulo):
    if PATRON_PERSONA.search(titulo) or PATRON_EXPEDIENTE.search(titulo):
        return "POSIBLE_DATO_PERSONAL"
    return "SIN_INDICIOS"


def construir(rutas, raices):
    elementos, listadas, a_medias, exploradas = {}, set(), {}, set()
    listados = [x for ruta in rutas for x in leer_listados(ruta)]
    for consulta, token, r in listados:
        padres = re.findall(r"parentId\s*=\s*'([^']+)'", consulta)
        solo_padres = bool(padres) and not re.search(r"title|fullText|mimeType|owner|sharedWithMe", consulta)
        solo_carpetas = bool(padres) and "mimeType = 'application/vnd.google-apps.folder'" in consulta and not re.search(r"title|fullText|owner|sharedWithMe", consulta)
        for f in r.get("files", []):
            e = elementos.setdefault(f["id"], {})
            e.update({
                "drive_id": f["id"], "titulo": f.get("title", ""), "mime": f.get("mimeType", ""),
                "carpeta_id": f.get("parentId"), "tamano": int(f["fileSize"]) if f.get("fileSize") else None,
                "modificado": f.get("modifiedTime"), "creado": f.get("createdTime"),
                "propietario": "propio" if f.get("owner") == PROPIO else "tercero",
                "enlace": f.get("viewUrl"), "extension": f.get("fileExtension"),
                "estado": "ENCONTRADO"})
        if solo_padres:
            clave = tuple(sorted(padres))
            if r.get("nextPageToken"):
                a_medias[clave] = {"consulta": consulta, "pageToken": r["nextPageToken"]}
            else:
                a_medias.pop(clave, None)
                listadas.update(padres)
        elif solo_carpetas and not r.get("nextPageToken"):
            exploradas.update(padres)
    # rutas y clasificación de sensibilidad
    def ruta_de(e, visto=()):
        p = e.get("carpeta_id")
        if not p or p not in elementos or p in visto:
            return ""
        padre = elementos[p]
        return (ruta_de(padre, visto + (p,)) + "/" + padre["titulo"]).strip("/")
    for e in elementos.values():
        e["ruta"] = ruta_de(e)
        e["sensibilidad"] = sensibilidad(e["titulo"])
        if any(sensibilidad(x) != "SIN_INDICIOS" for x in e["ruta"].split("/") if x):
            e["sensibilidad"] = "POSIBLE_DATO_PERSONAL"
        if e["sensibilidad"] != "SIN_INDICIOS":
            e["estado"] = "PENDIENTE"
            e["motivo"] = "posible dato personal: requiere clasificación humana antes de leer o indexar"
            e["titulo"] = "[título reservado]"
    carpetas = {i for i, e in elementos.items() if e["mime"] == CARPETA}
    alcanzables = set(raices)
    cambio = True
    while cambio:
        cambio = False
        for i in carpetas:
            if i not in alcanzables and elementos[i].get("carpeta_id") in alcanzables:
                alcanzables.add(i)
                cambio = True
    ok = lambda i: i in raices or elementos.get(i, {}).get("sensibilidad") == "SIN_INDICIOS"
    pendientes = sorted(i for i in alcanzables if i not in listadas and ok(i))
    sin_explorar = sorted(i for i in alcanzables if i not in listadas and i not in exploradas and ok(i))
    return elementos, listadas, a_medias, pendientes, alcanzables, sin_explorar


def main():
    rutas = [a for a in sys.argv[1:] if a.endswith(".jsonl")]
    raices = []
    if "--raices" in sys.argv:
        raices = sys.argv[sys.argv.index("--raices") + 1].split(",")
    elementos, listadas, a_medias, pendientes, alcanzables, sin_explorar = construir(rutas, raices)
    en_alcance = {i: e for i, e in elementos.items() if e.get("carpeta_id") in alcanzables or i in alcanzables}
    archivos = [e for e in en_alcance.values() if e["mime"] not in (CARPETA,)]
    resumen = {
        "raices": raices,
        "elementos_en_alcance": len(en_alcance),
        "carpetas": sum(1 for e in en_alcance.values() if e["mime"] == CARPETA),
        "atajos": sum(1 for e in en_alcance.values() if e["mime"] == ATAJO),
        "archivos": sum(1 for e in archivos if e["mime"] != ATAJO),
        "carpetas_listadas_completas": len(listadas & alcanzables),
        "carpetas_pendientes_de_listar": len(pendientes),
        "carpetas_sin_explorar_subcarpetas": len(sin_explorar),
        "listados_a_medias": len(a_medias),
        "denominador": "PROVISIONAL" if (pendientes or a_medias) else "COMPLETO para las raíces indicadas",
        "por_estado": dict(Counter(e["estado"] for e in archivos)),
        "por_propietario": dict(Counter(e["propietario"] for e in archivos)),
        "por_tipo_de_archivo": dict(Counter((e.get("extension") or e["mime"].split(".")[-1].split("/")[-1])
                                            for e in archivos).most_common(12)),
    }
    SALIDA.parent.mkdir(exist_ok=True)
    SALIDA.write_text(json.dumps({"resumen": resumen, "pendientes": pendientes, "sin_explorar": sin_explorar,
                                  "a_medias": list(a_medias.values()),
                                  "elementos": sorted(en_alcance.values(), key=lambda e: (e["ruta"], e["titulo"]))},
                                 ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(resumen, ensure_ascii=False, indent=1))
    por_carpeta = defaultdict(int)
    for e in archivos:
        por_carpeta[e["ruta"].split("/")[0] if e["ruta"] else "(raíz)"] += 1
    print("archivos por carpeta de primer nivel:", dict(sorted(por_carpeta.items(), key=lambda x: -x[1])[:25]))
    print("PENDIENTES (hasta 40):", " ".join(pendientes[:40]))
    for a in list(a_medias.values())[:5]:
        print("A MEDIAS:", a["consulta"][:80], "token:", a["pageToken"][:20], "…")


if __name__ == "__main__":
    main()
