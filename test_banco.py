"""Banco curado de casos del Laboratorio de casos: archivos, validador y conexión con la API.

Estas pruebas revisan la ESTRUCTURA del banco y cómo se sirve. No verifican la exactitud jurídica
de los casos, que sigue marcada como NOT VERIFIED y exige revisión de un docente o abogado.
"""
import json
import sys
from pathlib import Path

import pytest
from conftest import FakeAnthropic, auth, nuevo_usuario

RAIZ = Path(__file__).resolve().parent.parent
BANCO_DIR = RAIZ / "academia_banco"
AREAS = ["Constitucional", "Penal", "Civil", "Laboral", "Administrativo", "Comercial",
         "Familia", "Procesal", "Probatorio"]
POR_NIVEL = {"basico": 6, "intermedio": 6, "avanzado": 5, "experto": 3}
RESPUESTA = ("En primer lugar, el problema jurídico es si procede la pretensión. En efecto, la norma "
             "aplicable exige probar el hecho; por consiguiente, la demanda debe prosperar.")


@pytest.fixture(scope="module")
def validador():
    sys.path.insert(0, str(RAIZ / "scripts"))
    import validar_banco
    return validar_banco


def _banco(cliente, t, **k):
    return cliente.post("/api/modular/caso", headers=auth(t), json={"origen": "banco", **k})


def _restantes(cliente, t):
    return cliente.get("/api/estado", headers=auth(t)).json()["perfil"]["restantes"]


# ------------------------------------------------------------------ archivos y validador --
def test_validador_del_banco_sin_errores(validador):
    r = validador.validar()
    assert r["errores"] == [] and r["conceptos_sin_emparejar"] == [] and r["ok"]
    assert r["total"] == 180
    assert list(r["por_area_nivel"]) == AREAS
    for area in AREAS:
        assert r["por_area_nivel"][area] == POR_NIVEL, area
    # Los únicos conceptos del mapa sin caso en el banco son los de redacción de escritos, que agregó el
    # Taller de escritos y se practican allí (integración PUL-014 + PUL-015).
    import academia
    import taller
    escritura = set().union(*(t["conceptos"] for t in taller.TIPOS))
    escritura |= {c for t in taller.TIPOS for cs in t["criterio_conceptos"].values() for c in cs}
    escritura |= {c for cs in taller.CRITERIO_CONCEPTOS_BASE.values() for c in cs}
    ids_escritura = {academia.emparejar(n) for n in escritura} | set(taller._CONCEPTO_A_TIPO)
    assert set(r["cobertura_mapa"]["sin_cubrir"]) <= ids_escritura, r["cobertura_mapa"]["sin_cubrir"]


def test_validador_detecta_un_caso_roto(validador, tmp_path):
    for f in BANCO_DIR.glob("*.json"):
        (tmp_path / f.name).write_text(f.read_text(encoding="utf-8"), encoding="utf-8")
    datos = json.loads((tmp_path / "civil.json").read_text(encoding="utf-8"))
    datos["casos"][0]["respuesta_modelo"] = "- Una lista\n- en lugar de prosa"
    datos["casos"][1]["conceptos"] = ["concepto que no existe en el mapa", "posesión"]
    (tmp_path / "civil.json").write_text(json.dumps(datos, ensure_ascii=False), encoding="utf-8")
    r = validador.validar(tmp_path)
    assert not r["ok"]
    assert any(e.startswith("civ-01:") for e in r["errores"])
    assert any(x.startswith("civ-02:") for x in r["conceptos_sin_emparejar"])


def test_cada_archivo_declara_not_verified_y_revision_humana():
    archivos = sorted(f for f in BANCO_DIR.glob("*.json") if f.name != "escritos.json")   # escritos.json es del Taller
    assert len(archivos) == 9
    for f in archivos:
        datos = json.loads(f.read_text(encoding="utf-8"))
        assert "NOT VERIFIED" in datos["aviso"] and "revisión humana" in datos["aviso"], f.name
        assert all(c["revision_humana"] is True for c in datos["casos"]), f.name
        texto = f.read_text(encoding="utf-8").lower()
        assert "modular lab" not in texto and "universidad" not in texto, f.name


def test_banco_cargado_en_academia(modulo):
    academia = modulo.academia
    assert len(academia.BANCO) == 180 and len(academia.BANCO_IDX) == 180
    for c in academia.BANCO:
        assert academia.conceptos_ids(c), c["id"]  # todo caso evalúa al menos un concepto del mapa
        usados = {x["frase"] for x in academia.detectar_conectores(c["respuesta_modelo"])}
        assert set(c["conectores_usados"]) <= usados, c["id"]


# ------------------------------------------------------------------------- API: servir --
def test_caso_del_banco_no_gasta_consulta_ni_llama_al_modelo(cliente):
    _, _, t = nuevo_usuario(cliente)
    antes = len(FakeAnthropic.llamadas_json)
    r = _banco(cliente, t, area="Civil", nivel="basico")
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["origen"] == "banco" and d["curado"] is True and d["gasta_consulta"] is False
    assert d["area"] == "Civil" and d["nivel"] == "basico" and d["banco_id"].startswith("civ-")
    assert d["titulo"] and d["enunciado"] and d["pregunta"].endswith("?") and d["n_pistas"] == 2
    assert "NOT VERIFIED" in d["aviso"] and "no gasta consulta" in d["aviso"]
    assert d["restantes"] == 10 and _restantes(cliente, t) == 10
    assert len(FakeAnthropic.llamadas_json) == antes


def test_caso_del_banco_no_revela_la_solucion(cliente):
    _, _, t = nuevo_usuario(cliente)
    d = _banco(cliente, t, area="Penal", nivel="experto").json()
    for clave in ("solucion", "pistas", "respuesta_modelo", "variacion", "distractor", "conectores_usados"):
        assert clave not in d
    reabierto = cliente.get(f"/api/modular/caso/{d['id']}", headers=auth(t)).json()
    assert reabierto["origen"] == "banco" and "solucion" not in reabierto and "respuesta_modelo" not in reabierto


def test_banco_cubre_todas_las_areas_y_niveles(cliente):
    _, _, t = nuevo_usuario(cliente)
    for area in AREAS:
        for nivel in POR_NIVEL:
            d = _banco(cliente, t, area=area, nivel=nivel).json()
            assert d["origen"] == "banco" and d["area"] == area and d["nivel"] == nivel
    assert _restantes(cliente, t) == 10


def test_banco_no_repite_hasta_agotar_los_candidatos(cliente):
    _, _, t = nuevo_usuario(cliente)
    vistos = []
    for _ in range(POR_NIVEL["experto"]):
        d = _banco(cliente, t, area="Familia", nivel="experto").json()
        assert d["repetido"] is False
        vistos.append(d["banco_id"])
    assert len(set(vistos)) == POR_NIVEL["experto"]
    otra_vez = _banco(cliente, t, area="Familia", nivel="experto").json()
    assert otra_vez["repetido"] is True and otra_vez["banco_id"] == vistos[0]


def test_banco_por_concepto_del_mapa(cliente, modulo):
    _, _, t = nuevo_usuario(cliente)
    r = _banco(cliente, t, concepto_id="cadena-custodia")
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["origen"] == "banco" and d["foco"] == "Cadena de custodia" and d["area"] == "Probatorio"
    caso = modulo.academia.BANCO_IDX[d["banco_id"]]
    assert "cadena-custodia" in modulo.academia.conceptos_ids(caso)
    assert _banco(cliente, t, concepto_id="no-existe").status_code == 404


def test_pistas_y_solucion_de_un_caso_del_banco(cliente, modulo):
    _, _, t = nuevo_usuario(cliente)
    d = _banco(cliente, t, area="Laboral", nivel="avanzado").json()
    original = modulo.academia.BANCO_IDX[d["banco_id"]]
    p0 = cliente.post("/api/modular/pista", headers=auth(t), json={"caso_id": d["id"], "n": 0}).json()
    assert p0["pista"] == original["pistas"][0] and p0["quedan"] == 1
    sol = cliente.get(f"/api/modular/solucion?caso_id={d['id']}", headers=auth(t)).json()
    assert sol["conclusion"] == original["solucion"]["conclusion"] and len(sol["errores_comunes"]) >= 2
    assert sol["origen"] == "banco" and sol["banco_id"] == d["banco_id"] and "NOT VERIFIED" in sol["aviso"]
    assert sol["respuesta_modelo"] == original["respuesta_modelo"]
    assert sol["variacion"]["cambio"].startswith("¿Qué cambia si") and sol["distractor"]
    assert len(sol["conectores_usados"]) >= 6
    assert _restantes(cliente, t) == 10  # pistas y solución siguen siendo gratis


def test_evaluar_un_caso_del_banco_si_gasta_consulta(cliente):
    _, _, t = nuevo_usuario(cliente)
    d = _banco(cliente, t, area="Procesal", nivel="basico").json()
    r = cliente.post("/api/modular/evaluar", headers=auth(t), json={"caso_id": d["id"], "respuesta": RESPUESTA})
    assert r.status_code == 200, r.text
    ev = r.json()
    assert ev["restantes"] == 9 and ev["total"] > 0 and ev["conocimiento"]
    assert d["titulo"] in FakeAnthropic.llamadas_json[-1]  # el modelo evalúa contra el caso curado
    p = cliente.get("/api/modular/progreso", headers=auth(t)).json()
    assert p["resueltos"] == 1 and p["por_area"][0]["area"] == "Procesal"


def test_banco_funciona_sin_motor_de_ia(cliente, modulo, monkeypatch):
    _, _, t = nuevo_usuario(cliente)
    monkeypatch.setattr(modulo, "ANTHROPIC_API_KEY", "")
    assert _banco(cliente, t, area="Comercial", nivel="intermedio").status_code == 200
    generado = cliente.post("/api/modular/caso", headers=auth(t), json={"area": "Comercial", "nivel": "intermedio"})
    assert generado.status_code == 503


def test_caso_generado_por_el_modelo_sigue_igual(cliente):
    _, _, t = nuevo_usuario(cliente)
    d = cliente.post("/api/modular/caso", headers=auth(t), json={"area": "Constitucional", "nivel": "basico"}).json()
    assert d["origen"] == "modelo" and d["restantes"] == 9 and "banco_id" not in d
    sol = cliente.get(f"/api/modular/solucion?caso_id={d['id']}", headers=auth(t)).json()
    assert "respuesta_modelo" not in sol and "origen" not in sol


def test_banco_valida_area_nivel_y_origen(cliente):
    _, _, t = nuevo_usuario(cliente)
    assert _banco(cliente, t, area="Astrología", nivel="basico").status_code == 400
    assert _banco(cliente, t, area="Civil", nivel="imposible").status_code == 400
    r = cliente.post("/api/modular/caso", headers=auth(t), json={"area": "Civil", "nivel": "basico", "origen": "otro"})
    assert r.status_code == 400
    assert _restantes(cliente, t) == 10
    assert cliente.post("/api/modular/caso", json={"area": "Civil", "nivel": "basico", "origen": "banco"}).status_code == 401


def test_caso_del_banco_de_otro_estudiante_no_es_accesible(cliente):
    _, _, a = nuevo_usuario(cliente)
    _, _, b = nuevo_usuario(cliente)
    cid = _banco(cliente, a, area="Administrativo", nivel="basico").json()["id"]
    assert cliente.get(f"/api/modular/solucion?caso_id={cid}", headers=auth(b)).status_code == 404
    assert cliente.get(f"/api/modular/caso/{cid}", headers=auth(b)).status_code == 404


def test_opciones_informa_el_banco(cliente):
    _, _, t = nuevo_usuario(cliente)
    banco = cliente.get("/api/modular/opciones", headers=auth(t)).json()["banco"]
    assert banco["total"] == 180 and "NOT VERIFIED" in banco["aviso"]
    assert banco["por_area"]["Probatorio"] == POR_NIVEL and set(banco["por_area"]) == set(AREAS)


def test_documento_de_coordinacion_existe_y_advierte():
    doc = (RAIZ / "docs" / "coordinacion" / "PUL-015-banco-de-casos.md").read_text(encoding="utf-8")
    assert "NOT VERIFIED" in doc and "revisión humana" in doc and "180" in doc
