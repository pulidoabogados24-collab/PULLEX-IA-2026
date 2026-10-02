"""Mapa de carpetas de la biblioteca: área y tipo documental por regla, con confianza.
Nombres de carpetas tomados de la especificación del dueño; títulos de archivos ficticios."""
import json
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "scripts"))
import biblioteca  # noqa: E402
import mapa_biblioteca  # noqa: E402

PC = biblioteca.POR_CLASIFICAR


@pytest.mark.parametrize("titulo,ancestros,tipo,area", [
    ("MODELOS Y MINUTAS - 2026", ["PACK JURIDICO 1"], "plantilla/minuta", "general (varias áreas)"),
    ("CIVIL", ["Carpeta #2", "MODELOS Y MINUTAS - 2026", "PACK JURIDICO 1"], "plantilla/minuta", "civil"),
    ("MINUTAS Y MODELOS PARA FUNCIONARIOS", ["FAMILIA", "Carpeta #2", "MODELOS Y MINUTAS - 2026"], "plantilla/minuta", "familia"),
    ("MODELOS INFANCIA", ["MINUTAS Y MODELOS PARA LITIGANTES", "FAMILIA"], "plantilla/minuta", "familia"),
    ("DERECHOS DE PETICION - 2026", ["PACK JURIDICO 1"], "plantilla/minuta", "derecho de petición"),
    ("ACCIONES DE TUTELA", ["PACK JURIDICO 1"], "plantilla/minuta", "constitucional (tutela)"),
    ("MEDIDAS CAUTELARES - 2026", ["PACK JURIDICO 1"], "plantilla/minuta", "procesal (medidas cautelares)"),
    ("CODIGOS COLOMBIANOS", ["PACK JURIDICO 1"], "norma", "general (varias áreas)"),
    ("LEYES 1.992 -2.025", ["PACK JURIDICO 1"], "norma", "general (varias áreas)"),
    ("1996", ["1992 A 2025", "02_LEYES", "LEXCOL_CORPUS"], "norma", "general (varias áreas)"),
    ("Sentencia y Jurisprudencia", ["PACK JURIDICO 1"], "jurisprudencia", "general (varias áreas)"),
    ("2022-2023", ["SALA LABORAL", "03_JURISPRUDENCIA", "LEXCOL_CORPUS"], "jurisprudencia", "laboral y seguridad social"),
    ("Libros Juridicos", ["PACK JURIDICO 1"], "doctrina", "general (varias áreas)"),
    ("CONCURSO FISCALIA", ["PACK JURIDICO 1"], "material de estudio", "penal"),
    ("MATERIAL DE ESTUDIO CONCURSO DIAN", ["PACK JURIDICO 1"], "material de estudio", "tributario y aduanero"),
    ("TABLAS LIQUIDADORAS - 2026", ["PACK JURIDICO 1"], "tabla de liquidación", PC),
    ("CONALBOS", ["PACK JURIDICO 1"], "otro", "gestión profesional (honorarios)"),
    ("INDICE LEYES", ["1992 A 2025", "02_LEYES"], "otro", "general (varias áreas)"),
    ("PACK JURIDICO 1", [], "otro", "general (varias áreas)"),
])
def test_reglas_por_nombre(titulo, ancestros, tipo, area):
    r = biblioteca.clasificar_carpeta(titulo, ancestros)
    assert (r["tipo_documental"], r["area"]) == (tipo, area)
    assert r["tipo_documental"] in biblioteca.TIPOS_DOCUMENTALES


@pytest.mark.parametrize("titulo,ancestros", [
    ("ESTATUTOS", ["PACK JURIDICO 1"]),                    # ¿normas o minutas de estatutos sociales?
    ("FUNCION PUBLICA", ["PACK JURIDICO 1"]),
    ("DERECHO PROCESAL INFORMATICO", ["PACK JURIDICO 1"]),
    ("07_EJEMPLOS_MODELOS_CASOS", ["LEXCOL_CORPUS"]),       # didácticos o reales: lo decide una persona
    ("ley", ["Sentencia y Jurisprudencia", "PACK JURIDICO 1"]),   # el nombre contradice a la carpeta que lo contiene
    ("COSAS VARIAS", []),
])
def test_lo_dudoso_queda_por_clasificar_con_confianza_baja(titulo, ancestros):
    r = biblioteca.clasificar_carpeta(titulo, ancestros)
    assert r["tipo_documental"] == PC and r["confianza"] == "baja"


def test_lo_heredado_tiene_menos_confianza_que_lo_que_dice_el_propio_nombre():
    propio = biblioteca.clasificar_carpeta("SALA PENAL", ["03_JURISPRUDENCIA"])
    heredado = biblioteca.clasificar_carpeta("2022-2023", ["SALA PENAL", "03_JURISPRUDENCIA"])
    assert propio["confianza"] == "alta" and heredado["confianza"] == "media"
    assert heredado["regla_tipo"] == "T09 (heredada)" and heredado["regla_area"] == "A04 (heredada)"


def test_la_evidencia_de_los_archivos_corrige_una_carpeta_mal_ubicada():
    # una carpeta "ESTATUTOS" dentro de "PLANTILLAS" cuyos archivos son normas, no minutas
    normas = ["Estatuto del Consumidor.docx", "Estatuto Tributario.docx", "Estatuto Aduanero.docx"]
    r = biblioteca.clasificar_carpeta("ESTATUTOS", ["04_PLANTILLAS", "LEXCOL_CORPUS"], normas)
    assert r["tipo_documental"] == "norma" and r["confianza_tipo"] == "media" and r["notas"]
    sociales = ["Estatutos sociales de una S.A.S.docx", "Estatuto de una sociedad limitada.docx"]
    assert biblioteca.clasificar_carpeta("ESTATUTOS", ["04_PLANTILLAS"], sociales)["tipo_documental"] == PC


def test_la_evidencia_sube_o_baja_la_confianza():
    leyes = [f"LEY {n} DE 1996.doc" for n in range(250, 260)]
    assert biblioteca.clasificar_carpeta("1996", ["02_LEYES"], leyes)["confianza_tipo"] == "alta"
    assert biblioteca.clasificar_carpeta("1996", ["02_LEYES"])["confianza_tipo"] == "media"
    r = biblioteca.clasificar_carpeta("MINUTAS", [], ["LEY 1 DE 2000.doc", "LEY 2 DE 2000.doc", "Codigo civil.pdf"])
    assert r["tipo_documental"] == PC and "parecen normas" in r["notas"][0]


def test_prefijos_de_otra_sala_dejan_una_nota():
    titulos = [f"AC{n}-2022.docx" for n in range(100, 180)] + [f"AP{n}-2022.docx" for n in range(100, 120)]
    r = biblioteca.clasificar_carpeta("SENTENCIAS 2022-2023", ["SALA CIVIL"], titulos)
    assert r["area"] == "civil" and r["evidencia"]["salas"] == {"civil": 80, "penal": 20}
    assert "prefijo de otra sala" in r["notas"][0] and r["confianza_area"] == "media"


def test_mapa_desde_el_inventario_con_reservados_y_correccion_manual(tmp_path):
    carpeta = lambda i, t, ruta: {"drive_id": i, "titulo": t, "ruta": ruta, "propietario": "propio", "listado": "COMPLETO"}
    inv = {"carpetas": [carpeta("R", "BIBLIOTECA", ""), carpeta("C1", "MINUTAS", "BIBLIOTECA"),
                        carpeta("C2", "[título reservado]", "BIBLIOTECA"), carpeta("C3", "COSAS", "BIBLIOTECA")],
           "elementos": [{"drive_id": "F1", "titulo": "Modelo de poder.docx", "mime": "x/docx", "carpeta_id": "C1"},
                         {"drive_id": "F2", "titulo": "~WRL0001.tmp", "mime": "x/tmp", "carpeta_id": "C1",
                          "no_procesable": "archivo temporal de Word"}]}
    mapa = mapa_biblioteca.construir(inv, {"C3": {"tipo_documental": "doctrina", "area": "civil", "motivo": "revisada por el dueño"}})
    por_id = {f["drive_id"]: f for f in mapa["carpetas"]}
    assert por_id["C1"]["tipo_documental"] == "plantilla/minuta" and por_id["C1"]["evidencia"]["archivos_visibles"] == 1
    assert por_id["C2"]["tipo_documental"] == PC and "dato personal" in por_id["C2"]["notas"][0]
    assert por_id["C3"]["confianza"] == "humana" and por_id["C3"]["tipo_documental"] == "doctrina"
    assert mapa["resumen"]["carpetas"] == 4 and mapa["resumen"]["por_clasificar"] >= 1
    assert {r["id"] for r in mapa["reglas"]} >= {"T01", "T08", "A04", "A15"}
    inv_ruta, salida = tmp_path / "inv.json", tmp_path / "mapa.json"
    inv_ruta.write_text(json.dumps(inv), encoding="utf-8")
    mapa_biblioteca.main(["--inventario", str(inv_ruta), "--salida", str(salida), "--correcciones", str(tmp_path / "no-existe.json")])
    assert len(json.loads(salida.read_text(encoding="utf-8"))["carpetas"]) == 4


def test_el_mapa_del_repositorio_cubre_todas_las_carpetas_del_inventario():
    inv = json.loads((RAIZ / "biblioteca" / "inventario.json").read_text(encoding="utf-8"))
    mapa = json.loads((RAIZ / "biblioteca" / "mapa_carpetas.json").read_text(encoding="utf-8"))
    assert {c["drive_id"] for c in inv["carpetas"]} == {c["drive_id"] for c in mapa["carpetas"]}
    for c in mapa["carpetas"]:
        assert c["tipo_documental"] in biblioteca.TIPOS_DOCUMENTALES
        assert c["confianza"] in ("alta", "media", "baja", "humana")
        assert c["regla_tipo"] or c["tipo_documental"] == PC
