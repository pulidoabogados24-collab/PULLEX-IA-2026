"""Genera biblioteca/mapa_carpetas.json: a cada carpeta del inventario le asigna un área jurídica y
un tipo documental, con la regla que lo decidió y el nivel de confianza. Lo dudoso queda
"por clasificar". No lee el contenido de ningún archivo: usa nombres de carpetas y de archivos.

    python scripts/mapa_biblioteca.py [--inventario biblioteca/inventario.json] [--salida biblioteca/mapa_carpetas.json]

Las reglas están en biblioteca.py (REGLAS_TIPO y REGLAS_AREA). Para corregir una carpeta a mano,
agrégala en biblioteca/mapa_correcciones.json: {"<drive_id>": {"area": "...", "tipo_documental": "...",
"motivo": "..."}}. Una corrección manual queda marcada como tal y con confianza "humana".
"""
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
import biblioteca  # noqa: E402

CARPETA = "application/vnd.google-apps.folder"
ATAJO = "application/vnd.google-apps.shortcut"
RESERVADO = "[título reservado]"


def construir(inv, correcciones=None):
    correcciones = correcciones or {}
    archivos = defaultdict(list)
    for e in inv["elementos"]:
        if e["mime"] not in (CARPETA, ATAJO) and e["titulo"] != RESERVADO and not e.get("no_procesable", "").startswith("archivo temporal"):
            archivos[e["carpeta_id"]].append(e["titulo"])
    filas = []
    for c in inv["carpetas"]:
        ancestros = [x for x in reversed(c["ruta"].split("/")) if x]
        if c["titulo"] == RESERVADO or RESERVADO in ancestros:
            fila = {"area": biblioteca.POR_CLASIFICAR, "area_perfiles": biblioteca.POR_CLASIFICAR,
                    "tipo_documental": biblioteca.POR_CLASIFICAR, "regla_tipo": None, "regla_area": None,
                    "confianza_tipo": "baja", "confianza_area": "baja", "confianza": "baja",
                    "evidencia": {"archivos_visibles": 0, "por_nombre": {}, "salas": {}},
                    "notas": ["posible dato personal: no se clasifica hasta que una persona decida"]}
        else:
            fila = biblioteca.clasificar_carpeta(c["titulo"], ancestros, archivos.get(c["drive_id"], []))
        fila = {"drive_id": c["drive_id"], "ruta": (c["ruta"] + "/" if c["ruta"] else "") + c["titulo"],
                "propietario": c["propietario"], "listado": c["listado"], **fila}
        m = correcciones.get(c["drive_id"])
        if m:
            fila.update({k: m[k] for k in ("area", "area_perfiles", "tipo_documental") if k in m})
            fila.update(confianza="humana", correccion_manual=m.get("motivo", "sin motivo registrado"))
        filas.append(fila)
    filas.sort(key=lambda f: f["ruta"])
    reglas = ([{"id": r[0], "patron": r[1], "tipo_documental": r[2], "confianza": r[3], "motivo": r[4]} for r in biblioteca.REGLAS_TIPO]
              + [{"id": r[0], "patron": r[1], "area": r[2], "area_perfiles": r[3], "confianza": r[4]}
                 for r in biblioteca.REGLAS_AREA + (biblioteca.REGLA_AREA_GENERAL,)])
    return {
        "nota": ("Clasificación por nombre de carpeta y de archivos; no se leyó el contenido. La regla del propio "
                 "nombre manda; si no hay, se hereda la de la carpeta que la contiene (confianza menor). "
                 "«por clasificar» = requiere decisión humana."),
        "resumen": {"carpetas": len(filas),
                    "por_tipo_documental": dict(Counter(f["tipo_documental"] for f in filas).most_common()),
                    "por_area": dict(Counter(f["area"] for f in filas).most_common()),
                    "por_confianza": dict(Counter(f["confianza"] for f in filas).most_common()),
                    "por_clasificar": sum(1 for f in filas if biblioteca.POR_CLASIFICAR in (f["tipo_documental"], f["area"]))},
        "reglas": reglas, "carpetas": filas}


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    op = lambda n, d: argv[argv.index(n) + 1] if n in argv else d
    inv = json.loads(Path(op("--inventario", RAIZ / "biblioteca" / "inventario.json")).read_text(encoding="utf-8"))
    rc = Path(op("--correcciones", RAIZ / "biblioteca" / "mapa_correcciones.json"))
    mapa = construir(inv, json.loads(rc.read_text(encoding="utf-8")) if rc.is_file() else None)
    cab = {k: v for k, v in mapa.items() if k != "carpetas"}
    texto = json.dumps(cab, ensure_ascii=False, indent=1)[:-2] + ',\n "carpetas": [\n'
    texto += ",\n".join("  " + json.dumps(f, ensure_ascii=False) for f in mapa["carpetas"]) + "\n ]\n}\n"
    Path(op("--salida", RAIZ / "biblioteca" / "mapa_carpetas.json")).write_text(texto, encoding="utf-8")
    print(json.dumps(mapa["resumen"], ensure_ascii=False, indent=1))
    for f in mapa["carpetas"]:
        print(f"{f['tipo_documental']:<20} {f['area']:<30} {f['confianza']:<6} {f['regla_tipo'] or '-':<16} {f['ruta'][-70:]}"
              + ("  ⚠ " + "; ".join(f["notas"]) if f["notas"] else ""))


if __name__ == "__main__":
    main()
