"""Ingesta del corpus: formatos .rtf y .doc (el 72 % del inventario de Drive), archivos que no se
pueden leer (nada se omite en silencio) y convivencia con lo que ya indexó la biblioteca.
Ninguna prueba llama a Google Drive: se usa un servicio de mentira."""
import sys
import types
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "scripts"))
import biblioteca_recorrido as biblioteca  # noqa: E402
import fuentes  # noqa: E402
import ingesta_corpus as ing  # noqa: E402

ns = types.SimpleNamespace
RTF = (rb"{\rtf1\ansi\ansicpg1252{\fonttbl{\f0 Arial;}}{\colortbl;\red0\green0\blue0;}{\*\generator Prueba;}"
       rb"\f0\fs24 LEY 9999 DE 2001\par Art\'edculo 1. La petici\'f3n se resuelve en quince d\'edas del a\u241?o.\par"
       rb"{\pict\wmetafile8 0102030405}Texto \{entre llaves\} y \\barra\line Fin\par}")


def test_rtf_a_texto_conserva_tildes_y_descarta_tablas_e_imagenes():
    t = ing.rtf_a_texto(RTF)
    assert t == ("LEY 9999 DE 2001\nArtículo 1. La petición se resuelve en quince días del año.\n"
                 "Texto {entre llaves} y \\barra\nFin")
    assert "Arial" not in t and "0102030405" not in t and "Prueba" not in t
    assert ing.extraer("LEY 9999 DE 2001.rtf", RTF) == [("", t)]
    assert ing.rtf_a_texto(b"") == ""


def test_doc_usa_el_conversor_instalado(monkeypatch):
    llamadas = []

    def correr(orden, **k):
        llamadas.append(orden[0])
        return ns(returncode=0, stdout="Texto del documento con petición".encode("utf-8"), stderr=b"")

    monkeypatch.setattr(ing.shutil, "which", lambda x: "/usr/bin/antiword" if x == "antiword" else None)
    monkeypatch.setattr(ing.subprocess, "run", correr)
    assert ing.extraer("Minuta.doc", b"\xd0\xcf\x11\xe0contenido") == [("", "Texto del documento con petición")]
    assert llamadas == ["antiword"]


def test_doc_con_libreoffice_lee_el_archivo_convertido(monkeypatch):
    def correr(orden, **k):
        salida = Path(orden[orden.index("--outdir") + 1]) / "entrada.txt"
        salida.write_text("\ufeffLEY 9999 DE 2001\nARTICULO 1o. Petición.", encoding="utf-8")
        return ns(returncode=0, stdout=b"", stderr=b"")

    monkeypatch.setattr(ing.shutil, "which", lambda x: "/usr/bin/soffice" if x == "soffice" else None)
    monkeypatch.setattr(ing.subprocess, "run", correr)
    assert ing.extraer_doc(b"x") == [("", "LEY 9999 DE 2001\nARTICULO 1o. Petición.")]


def test_doc_sin_conversor_falla_con_un_mensaje_claro_y_queda_en_el_reporte(monkeypatch, tmp_path):
    monkeypatch.setattr(ing.shutil, "which", lambda x: None)
    with pytest.raises(RuntimeError, match="antiword, catdoc o LibreOffice"):
        ing.extraer_doc(b"x")
    base = tmp_path / "corpus"
    base.mkdir()
    (base / "LEY 1 DE 2000.doc").write_bytes(b"\xd0\xcf\x11\xe0")
    (base / "LEY 2 DE 2000.rtf").write_bytes(RTF)
    rep = ing.ingerir(ing.recorrer_carpeta(base), str(tmp_path / "c.db"), patrones=[])
    assert [x["ruta"] for x in rep["indexados"]] == ["LEY 2 DE 2000.rtf"]
    assert rep["errores"][0]["ruta"] == "LEY 1 DE 2000.doc" and "instala un conversor" in rep["errores"][0]["error"]


def _servicio(arbol, contenidos):
    class Files:
        def list(self, q, **k):
            return ns(execute=lambda: {"files": arbol[q.split("'")[1]]})

        def get_media(self, fileId, **k):
            return ns(execute=lambda: contenidos[fileId])

    return ns(files=lambda: Files())


def test_drive_lee_doc_y_rtf_da_el_enlace_y_reporta_lo_que_no_puede_leer(monkeypatch, capsys):
    f = lambda i, nombre, mime: {"id": i, "name": nombre, "mimeType": mime, "modifiedTime": "2026-07-21T00:00:00Z"}
    arbol = {"raiz": [f("d1", "LEY 1 DE 2000.doc", "application/msword"), f("r1", "LEY 2 DE 2000.rtf", "application/rtf"),
                      f("x1", "Tabla.xlsm", "application/vnd.ms-excel.sheet.macroenabled.12"),
                      f("s1", "Plantillas", "application/vnd.google-apps.shortcut"), f("t1", "~WRL0001.tmp", "application/octet-stream")]}
    rep = {"excluidos": []}
    items = list(ing.recorrer_drive(_servicio(arbol, {"r1": RTF}), "raiz", "", [], rep))
    assert [(i[0], i[4], i[5]) for i in items] == [
        ("LEY 1 DE 2000.doc", "drive:d1", "https://drive.google.com/file/d/d1/view"),
        ("LEY 2 DE 2000.rtf", "drive:r1", "https://drive.google.com/file/d/r1/view")]
    assert {o["ruta"]: o["motivo"].split(":")[0].split(" (")[0] for o in rep["omitidos"]} == {
        "Tabla.xlsm": "formato no admitido", "Plantillas": "acceso directo", "~WRL0001.tmp": "formato no admitido"}
    assert "petición" in ing.extraer(items[1][0], items[1][2]())[0][1]
    ing.imprimir_reporte({"indexados": [], "excluidos": [], "errores": [], **rep})
    assert "Omitidos (no se pueden leer): 3" in capsys.readouterr().out


def test_la_ingesta_no_duplica_lo_que_ya_indexo_la_biblioteca(tmp_path):
    db = str(tmp_path / "c.db")
    con = fuentes.abrir(db)
    biblioteca.indexar_modelo(con, drive_id="r1", titulo="LEY 2 DE 2000.rtf", texto=ing.rtf_a_texto(RTF), tipo_fuente="ley",
                              url="https://drive.google.com/file/d/r1/view", propietario="propio")
    con.close()
    f = lambda i, nombre: {"id": i, "name": nombre, "mimeType": "application/rtf", "modifiedTime": "2026-07-21T00:00:00Z"}
    arbol = {"raiz": [f("r1", "LEY 2 DE 2000.rtf"), f("r2", "LEY 3 DE 2000.rtf")]}
    rep = {"excluidos": []}
    rep = ing.ingerir(ing.recorrer_drive(_servicio(arbol, {"r1": RTF, "r2": RTF}), "raiz", "", [], rep), db, patrones=[], reporte=rep)
    assert rep["ya_en_biblioteca"] == 1 and [x["ruta"] for x in rep["indexados"]] == ["LEY 3 DE 2000.rtf"]
    con = fuentes.abrir(db)
    assert sorted(o[0] for o in con.execute("SELECT origen FROM fuentes")) == ["drive:r2", "r1"]
    assert con.execute("SELECT url FROM fuentes WHERE origen='drive:r2'").fetchone()[0] == "https://drive.google.com/file/d/r2/view"
    con.close()


def test_ingesta_privada_de_una_coleccion_de_terceros_no_llega_al_chat(tmp_path):
    base = tmp_path / "PACK"
    (base / "MODELOS Y MINUTAS" / "CIVIL").mkdir(parents=True)
    (base / "MODELOS Y MINUTAS" / "CIVIL" / "Minuta de arrendamiento.rtf").write_bytes(
        rb"{\rtf1\ansi Minuta de contrato de arrendamiento de vivienda urbana entre arrendador y arrendatario.\par}")
    db = str(tmp_path / "c.db")
    assert ing.main(["--carpeta", str(base), "--db", db, "--privada"]) == 0
    pregunta = "contrato de arrendamiento de vivienda"
    assert fuentes.buscar(pregunta, ruta=db) == []                                # el chat general no lo ve
    r = biblioteca.buscar_modelos(pregunta, ruta=db, tipos=None)
    assert len(r) == 1 and r[0]["visibilidad"] == "privada" and r[0]["derechos"] == biblioteca.AVISO_DERECHOS
    assert r[0]["area"] == "civil" and r[0]["tipo_documental"] == "plantilla/minuta"
    assert ing.main(["--carpeta", str(base), "--db", db, "--privada"]) == 0       # repetir no falla ni duplica
    con = fuentes.abrir(db)
    assert con.execute("SELECT COUNT(*) FROM biblioteca_fichas").fetchone()[0] == 1
    con.close()
    db2 = str(tmp_path / "general.db")
    ing.main(["--carpeta", str(base), "--db", db2])                               # sin --privada sí es general
    assert len(fuentes.buscar(pregunta, ruta=db2)) == 1
