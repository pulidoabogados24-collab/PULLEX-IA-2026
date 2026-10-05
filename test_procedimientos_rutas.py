"""Rutas de procedimientos y del registro de reglas: sesión obligatoria, sin gasto de consultas, aislamiento
entre usuarios y evaluación (evaluacion/procedimientos.jsonl)."""
import importlib
import json
import sys
from pathlib import Path

import pytest

from conftest import FakeAnthropic, auth, login_admin, nuevo_usuario

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "evaluacion"))

POST = {
    "/api/procedimientos/terminos": {"regimen": "administrativo", "forma_notificacion": "recepcion",
                                     "termino_id": "R-PLAZO-0001", "fecha_notificacion": "2026-07-01"},
    "/api/procedimientos/liquidacion": {"tipo": "prestaciones", "fecha_inicio": "2026-01-01", "fecha_fin": "2026-06-30",
                                        "salario_mensual": 2000000, "auxilio_transporte_mensual": 0},
    "/api/procedimientos/clasificar": {"hechos": "Me despidieron sin justa causa después de tres años de trabajo."},
    "/api/procedimientos/verificar-escrito": {"texto": "Ana Pérez contra EPS Ejemplo, Ley 1751 de 2015.",
                                              "entradas": {"solicitante": "Ana Pérez", "contraparte": "EPS Ejemplo"}},
    "/api/procedimientos/modelos": {"consulta": "tutela salud"},
    "/api/procedimientos/vigencia": {"disposicion": "CGP art. 118", "fecha_hechos": "2026-10-02", "fecha_analisis": "2026-10-02"},
    "/api/procedimientos/jurisprudencia": {"problema_juridico": "¿Procede la tutela?"},
    "/api/procedimientos/matriz-probatoria": {"hechos": ["Me despidieron."], "elementos": []},
    "/api/procedimientos/impacto": {"tipo": "norma", "identificador": "Ley 1755 de 2015"},
}
GET = ("/api/procedimientos", "/api/reglas")


@pytest.mark.parametrize("ruta", sorted(POST))
def test_rutas_post_exigen_sesion(cliente, ruta):
    assert cliente.post(ruta, json=POST[ruta]).status_code == 401
    assert cliente.post(ruta, json=POST[ruta], headers=auth("token-falso")).status_code == 401


@pytest.mark.parametrize("ruta", GET)
def test_rutas_get_exigen_sesion(cliente, ruta):
    assert cliente.get(ruta).status_code == 401
    assert cliente.get(ruta, headers=auth("token-falso")).status_code == 401


def test_las_rutas_deterministas_no_gastan_consultas_ni_llaman_al_modelo(cliente, modulo):
    email, _, token = nuevo_usuario(cliente)
    antes = modulo.obtener_usuario(email)["usadas"]
    FakeAnthropic.ultima_llamada = None
    FakeAnthropic.ultima_create = None
    for ruta, cuerpo in POST.items():
        if ruta.endswith("/impacto"):
            continue
        r = cliente.post(ruta, json=cuerpo, headers=auth(token))
        assert r.status_code == 200, (ruta, r.text)
        assert r.json()["procedimiento"].startswith("J0")
        assert r.headers["cache-control"] == "no-store"
    for ruta in GET:
        assert cliente.get(ruta, headers=auth(token)).status_code == 200
    assert modulo.obtener_usuario(email)["usadas"] == antes
    assert FakeAnthropic.ultima_llamada is None and FakeAnthropic.ultima_create is None


def test_terminos_y_liquidacion_por_http(cliente):
    _, _, token = nuevo_usuario(cliente)
    r = cliente.post("/api/procedimientos/terminos", json=POST["/api/procedimientos/terminos"], headers=auth(token)).json()
    assert r["estado"] == "CALCULADO" and r["fecha_vencimiento"] == "2026-07-24" and len(r["cronologia"]) == 24
    assert all(n["enlace"] is None or n["enlace"].startswith("http") for n in r["normas"])
    sin = cliente.post("/api/procedimientos/terminos", json={"regimen": "administrativo"}, headers=auth(token)).json()
    assert sin["estado"] == "ABSTENCION" and sin["fecha_vencimiento"] is None
    liq = cliente.post("/api/procedimientos/liquidacion", json=POST["/api/procedimientos/liquidacion"], headers=auth(token)).json()
    assert liq["estado"] == "CALCULADO" and liq["total"] == 2560000 and len(liq["desglose"]) == 4
    malo = cliente.post("/api/procedimientos/liquidacion", json={"tipo": "prestaciones", "fecha_inicio": "2026-02-30"},
                        headers=auth(token)).json()
    assert malo["estado"] == "CONTRADICCION" and malo["total"] is None


def test_cuerpos_mal_formados_devuelven_400_o_413_nunca_500(cliente):
    _, _, token = nuevo_usuario(cliente)
    for ruta in ("/api/procedimientos/terminos", "/api/procedimientos/liquidacion", "/api/procedimientos/clasificar",
                 "/api/procedimientos/verificar-escrito"):
        assert cliente.post(ruta, content=b"{no es json", headers={**auth(token), "content-type": "application/json"}).status_code == 400
        assert cliente.post(ruta, json=[1, 2, 3], headers=auth(token)).status_code == 400
        raros = cliente.post(ruta, json={"regimen": {"a": 1}, "tipo": ["x"], "hechos": 5, "texto": {"x": 1}, "periodos": "no",
                                         "suspensiones": [1, "a", None], "cantidad": {"x": 1}, "fecha_notificacion": 20260101},
                             headers=auth(token))
        assert raros.status_code == 200 and raros.json()["estado"] in ("CONTRADICCION", "ABSTENCION", "INSUFICIENTE",
                                                                     "SIN_HALLAZGOS", "POSIBLES_INVENCIONES"), (ruta, raros.text)
    enorme = cliente.post("/api/procedimientos/clasificar", json={"hechos": "a" * 450_000}, headers=auth(token))
    assert enorme.status_code == 413


def test_catalogo_de_procedimientos_y_opciones_para_la_interfaz(cliente):
    _, _, token = nuevo_usuario(cliente)
    d = cliente.get("/api/procedimientos", headers=auth(token)).json()
    assert [p["id"] for p in d["procedimientos"]] == [f"J0{i}" for i in range(1, 10)]
    assert d["registro"]["por_estado"]["VERIFICADA_EN_FUENTE_OFICIAL"] >= 40
    assert len(d["terminos"]["tabla"]) == 15 and len(d["terminos"]["regimenes"]) == 5
    assert {c["id"] for c in d["liquidacion"]["conceptos"]} == {"cesantias", "intereses_cesantias", "prima", "vacaciones"}
    viejo = cliente.get("/api/procedimientos?fecha=2021-03-01", headers=auth(token)).json()
    assert {t["id"]: t["cantidad"] for t in viejo["terminos"]["tabla"]}["R-PLAZO-0001"] is None
    assert cliente.get("/api/procedimientos?fecha=ayer", headers=auth(token)).status_code == 400


def test_api_reglas_lista_todas_o_a_una_fecha(cliente):
    _, _, token = nuevo_usuario(cliente)
    todas = cliente.get("/api/reglas", headers=auth(token)).json()
    assert todas["n"] == todas["resumen"]["total_versiones"] and todas["a_fecha"] is None
    una = todas["reglas"][0]
    assert {"id", "version", "ambito", "enunciado", "soporte", "enlace", "consultado", "vigencia", "estado", "procedimientos"} <= set(una)
    hoy = cliente.get("/api/reglas?fecha=2026-10-02", headers=auth(token)).json()
    ids = [r["id"] for r in hoy["reglas"]]
    assert len(ids) == len(set(ids)) == todas["resumen"]["reglas_distintas"]
    fest = cliente.get("/api/reglas?fecha=2025-07-01&id=R-FEST-0001", headers=auth(token)).json()
    assert fest["n"] == 1 and fest["reglas"][0]["version"] == 1
    fest = cliente.get("/api/reglas?fecha=2026-07-01&id=r-fest-0001", headers=auth(token)).json()
    assert fest["reglas"][0]["version"] == 2
    nv = cliente.get("/api/reglas?estado=NO_VERIFICADO", headers=auth(token)).json()
    assert nv["n"] >= 5 and all(r["estado"] == "NO_VERIFICADO" for r in nv["reglas"])
    j06 = cliente.get("/api/reglas?procedimiento=J06&fecha=2026-10-02", headers=auth(token)).json()
    assert j06["n"] >= 10 and all("J06" in r["procedimientos"] for r in j06["reglas"])
    assert cliente.get("/api/reglas?estado=INVENTADO", headers=auth(token)).status_code == 400
    assert cliente.get("/api/reglas?fecha=2026-02-30", headers=auth(token)).status_code == 400


def test_impacto_solo_para_administracion(cliente):
    _, _, token = nuevo_usuario(cliente)
    cuerpo = {"tipo": "norma", "identificador": "Ley 1755 de 2015", "comprobado": True, "fecha_consulta": "2026-10-02",
              "fecha_efecto": "2026-11-01", "enlace": "http://www.secretariasenado.gov.co/senado/basedoc/ley_1755_2015.html"}
    assert cliente.post("/api/procedimientos/impacto", json=cuerpo, headers=auth(token)).status_code == 403
    r = cliente.post("/api/procedimientos/impacto", json=cuerpo, headers=auth(login_admin(cliente)))
    assert r.status_code == 200 and r.json()["estado"] == "IMPACTO_CALCULADO" and r.json()["aplicado"] is False


def test_verificar_escrito_de_un_documento_guardado_y_aislamiento_entre_usuarios(cliente, modulo):
    FakeAnthropic.fallar_create = False
    email, _, token = nuevo_usuario(cliente)
    campos = {"solicitante": "Ana Pérez", "ciudad": "Bogotá", "contraparte": "EPS Ejemplo", "derechos": "salud",
              "hechos": "Me negaron un medicamento formulado.", "peticiones": "Que ordene entregarlo.", "urgente": "Sí"}
    g = cliente.post("/api/documentos/generar", json={"tipo": "tutela", "campos": campos}, headers=auth(token))
    assert g.status_code == 200, g.text
    did = g.json()["id"]
    usadas = modulo.obtener_usuario(email)["usadas"]
    r = cliente.post("/api/procedimientos/verificar-escrito", json={"documento_id": did}, headers=auth(token)).json()
    assert r["origen"] == "documento" and r["estado"] in ("PENDIENTES", "SIN_HALLAZGOS", "POSIBLES_INVENCIONES")
    assert any("ciudad de reparto" in p for p in r["pendientes"])
    assert "Decreto 2591 de 1991" not in {h["valor"] for h in r["posibles_invenciones"]}
    assert modulo.obtener_usuario(email)["usadas"] == usadas, "revisar no gasta consultas"
    # Si el texto guardado cambia y aparece un dato que no estaba en el formulario, se detecta.
    e = cliente.put(f"/api/documentos/{did}", json={"texto": "Ana Pérez contra EPS Ejemplo. El doctor Carlos Ramírez firmó el 4 de abril de 2026."},
                    headers=auth(token))
    assert e.status_code == 200, e.text
    r = cliente.post("/api/procedimientos/verificar-escrito", json={"documento_id": did}, headers=auth(token)).json()
    assert {("nombre", "Carlos Ramírez"), ("fecha", "4 de abril de 2026")} <= {(h["categoria"], h["valor"]) for h in r["posibles_invenciones"]}
    # Otro usuario no puede revisar (ni saber que existe) el documento ajeno.
    _, _, intruso = nuevo_usuario(cliente)
    assert cliente.post("/api/procedimientos/verificar-escrito", json={"documento_id": did}, headers=auth(intruso)).status_code == 404
    assert cliente.post("/api/procedimientos/verificar-escrito", json={"documento_id": "abc"}, headers=auth(token)).status_code == 400


def test_limite_de_frecuencia_por_cuenta(cliente):
    _, _, token = nuevo_usuario(cliente)
    cuerpo = POST["/api/procedimientos/clasificar"]
    codigos = [cliente.post("/api/procedimientos/clasificar", json=cuerpo, headers=auth(token)).status_code for _ in range(95)]
    assert codigos[:90] == [200] * 90 and codigos[-1] == 429


def test_rutas_sin_javascript_en_linea_y_vista_herramientas_en_el_html():
    html = (RAIZ / "static" / "index.html").read_text(encoding="utf-8")
    assert 'id="n-herramientas"' in html and 'id="v-herramientas"' in html and "/* ---- Herramientas ---- */" in html
    assert '<script src="/static/herramientas.js"></script>' in html
    js = (RAIZ / "static" / "herramientas.js").read_text(encoding="utf-8")
    assert "innerHTML" not in js and "eval(" not in js and "onclick" not in js
    assert "'herramientas'" in (RAIZ / "static" / "app.js").read_text(encoding="utf-8")
    bloque = html.split("/* ---- Herramientas ---- */")[1].split("</style>")[0]
    import re
    assert not re.search(r"#[0-9a-fA-F]{3,8}\b", bloque), "el bloque de Herramientas solo usa tokens de tema.css"


# ------------------------------------------------------------------------------- evaluación --
def _casos():
    return [json.loads(l) for l in (RAIZ / "evaluacion" / "procedimientos.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]


def test_evaluacion_bien_formada_con_dos_conjuntos_separados():
    casos = _casos()
    assert len(casos) >= 40 and len({c["id"] for c in casos}) == len(casos)
    for c in casos:
        assert set(c) >= {"id", "conjunto", "procedimiento", "categoria", "descripcion", "entrada", "esperado", "calculo_a_mano"}
        assert c["conjunto"] in ("desarrollo", "medicion") and c["procedimiento"] in ("J05", "J06")
        assert c["categoria"] in ("normal", "frontera", "falta_de_datos", "contradiccion")
        assert len(c["calculo_a_mano"]) > 20 and c["esperado"]["estado"] in ("CALCULADO", "ABSTENCION", "CONTRADICCION")
    for conjunto in ("desarrollo", "medicion"):
        for proc in ("J05", "J06"):
            cats = {c["categoria"] for c in casos if c["conjunto"] == conjunto and c["procedimiento"] == proc}
            assert cats == {"normal", "frontera", "falta_de_datos", "contradiccion"}, (conjunto, proc, cats)
    entradas = [json.dumps(c["entrada"], sort_keys=True) for c in casos]
    assert len(set(entradas)) == len(entradas), "ningún caso de medición repite una entrada de desarrollo"
    descripciones = " ".join(c["descripcion"].lower() for c in casos)
    for frontera in ("semana santa", "bisiesto", "cambio de año", "festivo trasladado", "fin de semana"):
        assert frontera in descripciones, frontera


def test_evaluacion_cumple_el_umbral_fijado_antes_de_medir():
    ev = importlib.import_module("evaluar_procedimientos")
    assert ev.UMBRAL == 1.0
    r = ev.evaluar(ev.cargar())
    assert r["errores"] == [], r["errores"]
    assert r["aprobado"] and r["total"]["aciertos"] == r["total"]["total"] == len(_casos())
    assert r["por_conjunto"]["medicion"]["total"] >= 25 and r["por_conjunto"]["desarrollo"]["total"] >= 15
    assert ev.main(["--json"]) == 0


def test_el_evaluador_detecta_un_resultado_errado():
    ev = importlib.import_module("evaluar_procedimientos")
    caso = next(c for c in _casos() if c["id"] == "T-M01")
    malo = json.loads(json.dumps(caso))
    malo["esperado"]["fecha_vencimiento"] = "2026-11-18"
    r = ev.evaluar([malo])
    assert not r["aprobado"] and "fecha" in r["errores"][0]["diferencias"][0]
    # Entregar una fecha cuando había que abstenerse también cuenta como error.
    abst = next(c for c in _casos() if c["id"] == "T-M07")
    assert ev.comparar(abst, {"estado": "ABSTENCION", "fecha_vencimiento": "2026-01-20", "escenarios": [], "faltantes": []})
