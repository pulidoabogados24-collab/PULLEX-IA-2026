"""Indexa en el índice de búsqueda (corpus/corpus.db, el de fuentes.py) los documentos de Drive ya
extraídos que son aptos, y deja constancia en biblioteca/extraccion.json.

    python scripts/indexar_biblioteca.py            # indexa lo apto
    python scripts/indexar_biblioteca.py --listar   # muestra el catálogo indexado, con enlaces

Reglas:
- Solo entra lo que el registro marca `apto_indice` (texto suficiente, sin datos personales aparentes,
  no escaneado) y cuyo texto guardado coincide con la huella registrada.
- `origen` = id de Drive, `url` = enlace para abrir el original, vigencia PENDIENTE_VERIFICAR.
- Lo que es de terceros queda con visibilidad "privada": lo encuentra la biblioteca del dueño, no el
  chat general. Cada ficha dice "derechos de redistribución por confirmar".
- Si un documento deja de ser apto (por ejemplo, una persona lo marca con datos personales), se
  retira del índice.
- INDEXADO solo se escribe después de comprobar que el documento quedó en la base y se puede buscar.
"""
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
import biblioteca_recorrido as biblioteca  # noqa: E402
import fuentes  # noqa: E402


def retirar(con, drive_id):
    f = con.execute("SELECT id FROM fuentes WHERE origen=?", (drive_id,)).fetchone()
    if f is None:
        return False
    con.execute("DELETE FROM fragmentos WHERE fuente_id=?", (f["id"],))
    con.execute("DELETE FROM fuentes WHERE id=?", (f["id"],))
    con.executescript(biblioteca.ESQUEMA_FICHAS)
    con.execute("DELETE FROM biblioteca_fichas WHERE origen=?", (drive_id,))
    con.commit()
    return True


def indexar(registro, inventario, carpeta_textos, db_ruta):
    docs = registro["documentos"]
    fechas = {e["drive_id"]: e.get("modificado") for e in inventario.get("elementos", [])}
    con = fuentes.abrir(db_ruta)
    informe = {"indexados": [], "sin_cambios": [], "retirados": [], "no_aptos": [], "errores": []}
    try:
        for i, d in sorted(docs.items()):
            archivo = Path(carpeta_textos) / f"{i}.txt"
            if not d.get("apto_indice"):
                if retirar(con, i):
                    informe["retirados"].append(i)
                    d.pop("indexado", None)
                    if d.get("estado") == "INDEXADO":
                        d["estado"] = "EXTRAÍDO"
                informe["no_aptos"].append(i)
                continue
            if not archivo.is_file():
                informe["errores"].append({"id": i, "error": "no está el texto extraído (corpus/extraidos)"})
                continue
            texto = archivo.read_text(encoding="utf-8")
            if biblioteca.huella(texto) != d.get("sha256_texto"):
                informe["errores"].append({"id": i, "error": "el texto guardado no coincide con la huella del registro"})
                continue
            if biblioteca.datos_personales(texto)["aparentes"]:        # segunda barrera, por si el registro es viejo
                informe["errores"].append({"id": i, "error": "datos personales aparentes: no se indexa"})
                continue
            r = biblioteca.indexar_modelo(
                con, drive_id=i, titulo=d["titulo"], texto=texto, tipo_fuente=d.get("tipo_fuente", "otro"),
                url=d.get("enlace"), ruta=d.get("ruta", ""), tipo_documental=d.get("tipo_documental"),
                area=d.get("area"), propietario=d.get("propietario", "tercero"), fecha_archivo=fechas.get(i),
                versiones_relacionadas=[biblioteca.id_catalogo(v["id"]) for v in d.get("version_similar_de", [])])
            # comprobación: está en la base, con su enlace, y tiene fragmentos
            fila = con.execute("SELECT id, url, estado_vigencia FROM fuentes WHERE origen=?", (i,)).fetchone()
            if not fila or r["fragmentos"] < 1 or fila["url"] != d.get("enlace"):
                informe["errores"].append({"id": i, "error": "no quedó en el índice como se esperaba"})
                continue
            d.update(estado="INDEXADO", indexado={"fuente_id": fila["id"], "fragmentos": r["fragmentos"],
                                                  "id_catalogo": r["id_catalogo"], "vigencia": fila["estado_vigencia"],
                                                  "visibilidad": "privada" if d.get("propietario") != "propio" else "general",
                                                  "derechos": biblioteca.AVISO_DERECHOS})
            informe["sin_cambios" if r["accion"] == "sin_cambios" else "indexados"].append(i)
    finally:
        con.close()
    return informe


def listar(db_ruta):
    con = fuentes._abrir_lectura(db_ruta)
    if con is None:
        print("No hay índice en", db_ruta)
        return []
    with biblioteca.closing(con):
        filas = con.execute("SELECT s.titulo, s.tipo, s.url, s.estado_vigencia, b.id_catalogo, b.area, b.visibilidad, b.derechos, "
                            "(SELECT COUNT(*) FROM fragmentos WHERE fuente_id=s.id) n FROM fuentes s "
                            "JOIN biblioteca_fichas b ON b.origen=s.origen ORDER BY s.tipo, s.titulo").fetchall()
    for f in filas:
        print(f"[{f['tipo']:<9}] {f['titulo'][:60]:<60} {f['n']:>2} frag. · {f['estado_vigencia']} · {f['visibilidad']} · "
              f"{f['derechos']}\n            {f['url']}")
    return filas


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    op = lambda n, d: argv[argv.index(n) + 1] if n in argv else str(d)
    db_ruta = op("--db", fuentes.ruta_db())
    if "--listar" in argv:
        return listar(db_ruta)
    ruta_reg = Path(op("--registro", RAIZ / "biblioteca" / "extraccion.json"))
    ruta_inv = Path(op("--inventario", RAIZ / "biblioteca" / "inventario.json"))
    registro = json.loads(ruta_reg.read_text(encoding="utf-8"))
    inventario = json.loads(ruta_inv.read_text(encoding="utf-8")) if ruta_inv.is_file() else {}
    informe = indexar(registro, inventario, op("--textos", RAIZ / "corpus" / "extraidos"), db_ruta)
    ruta_reg.write_text(json.dumps(registro, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: (len(v) if k != "errores" else v) for k, v in informe.items()}, ensure_ascii=False, indent=1))
    print("Índice:", db_ruta)
    return informe


if __name__ == "__main__":
    main()
