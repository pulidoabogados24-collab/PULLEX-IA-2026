"""Registro de reglas (reglas/registro.json + reglas.py): esquema, consulta A UNA FECHA y estados."""
import copy
import json
import re
from datetime import date
from pathlib import Path

import pytest

import reglas

RAIZ = Path(__file__).resolve().parent.parent


def test_registro_valido_y_con_campos_obligatorios():
    datos = reglas.registro()
    reglas.validar(datos)                               # no lanza
    for r in datos["reglas"]:
        assert re.fullmatch(r"R-[A-Z]{2,6}-\d{4}", r["id"])
        assert r["estado"] in reglas.ESTADOS
        assert r["ambito"]["materia"] and r["ambito"]["jurisdiccion"]
        assert set(r["soporte"]) >= {"autoridad", "identificador", "articulo"}
        assert set(r["vigencia"]) >= {"desde", "hasta", "desde_comprobado"}
        assert r["procedimientos"] and all(re.fullmatch(r"J0[1-9]", p) for p in r["procedimientos"])
        assert r["enunciado"].strip()


def test_toda_regla_verificada_tiene_enlace_oficial_y_fecha_de_consulta():
    verificadas = [r for r in reglas.todas() if r["estado"] == reglas.VERIFICADA]
    assert len(verificadas) >= 40
    for r in verificadas:
        assert reglas.es_enlace_oficial(r["enlace"]), r["id"]
        assert reglas.a_fecha(r["consultado"]) <= date(2026, 10, 2), r["id"]
        assert r["cita"].strip(), f"{r['id']}: una regla verificada conserva la cita en que se apoya"
        for s in r.get("soportes_adicionales", []):
            assert reglas.es_enlace_oficial(s["enlace"]), (r["id"], s["enlace"])


def test_reglas_no_verificadas_explican_que_falta_y_no_fingen_enlace():
    pendientes = [r for r in reglas.todas() if r["estado"] != reglas.VERIFICADA]
    assert {r["id"] for r in pendientes} >= {"R-TERM-0007", "R-LIQ-0006", "R-LIQ-0007", "R-JUR-0004", "R-INT-0004"}
    for r in pendientes:
        assert len(r["notas"]) > 40, r["id"]


def test_enlace_oficial_no_acepta_dominios_parecidos():
    assert reglas.es_enlace_oficial("http://www.secretariasenado.gov.co/senado/basedoc/ley_1564_2012.html")
    assert reglas.es_enlace_oficial("https://sidn.ramajudicial.gov.co/x.pdf")
    assert not reglas.es_enlace_oficial("https://secretariasenado.gov.co.ejemplo.com/ley")
    assert not reglas.es_enlace_oficial("https://www.ejemplo.com/?u=funcionpublica.gov.co")
    assert not reglas.es_enlace_oficial("")
    assert not reglas.es_enlace_oficial(None)


def test_vigente_exige_fecha_y_no_devuelve_la_mas_reciente_por_defecto():
    with pytest.raises(ValueError):
        reglas.vigente("R-FEST-0001", None)
    with pytest.raises(ValueError):                    # varias versiones: obtener() no adivina la última
        reglas.obtener("R-FEST-0001")
    antes = reglas.vigente("R-FEST-0001", "2026-06-01")
    despues = reglas.vigente("R-FEST-0001", "2026-06-02")
    assert (antes["version"], despues["version"]) == (1, 2)
    assert "Ley 51 de 1983" in antes["soporte"]["identificador"]
    assert "Ley 2578 de 2026" in despues["soporte"]["identificador"]
    nombres_v1 = {f["nombre"] for f in antes["parametros"]["fijos"]}
    nombres_v2 = {f["nombre"] for f in despues["parametros"]["fijos"]}
    assert nombres_v2 - nombres_v1 == {"Nuestra Señora del Rosario de Chiquinquirá"}
    assert reglas.vigente("R-FEST-0001", "1980-01-01") is None      # antes de la Ley 51 de 1983


def test_plazo_de_peticion_tiene_tres_periodos_y_el_de_emergencia_no_esta_verificado():
    v1 = reglas.vigente("R-PLAZO-0001", "2019-05-10")
    v2 = reglas.vigente("R-PLAZO-0001", "2021-03-01")
    v3 = reglas.vigente("R-PLAZO-0001", "2026-10-02")
    assert [v["version"] for v in (v1, v2, v3)] == [1, 2, 3]
    assert v1["parametros"]["cantidad"] == v3["parametros"]["cantidad"] == 15
    assert v2["estado"] == reglas.NO_VERIFICADO and v2["parametros"]["cantidad"] is None
    assert reglas.vigente("R-PLAZO-0001", "2020-03-27")["version"] == 1
    assert reglas.vigente("R-PLAZO-0001", "2020-03-28")["version"] == 2
    assert reglas.vigente("R-PLAZO-0001", "2022-05-17")["version"] == 2
    assert reglas.vigente("R-PLAZO-0001", "2022-05-18")["version"] == 3
    assert reglas.vigente("R-PLAZO-0001", "2015-06-29") is None      # antes de la Ley 1755 de 2015


def test_vigencia_comprobada_distingue_los_tres_casos():
    cgp = reglas.obtener("R-TERM-0001")                 # verificada, sin inicio de vigencia comprobado
    assert reglas.vigencia_comprobada(cgp, "2026-10-02")["comprobada"] is True
    assert reglas.vigencia_comprobada(cgp, "2019-01-15")["motivo"] == "anterior_sin_inicio"
    assert reglas.vigencia_comprobada(cgp, "2027-01-15")["motivo"] == "posterior_a_consulta"
    ley2213 = reglas.obtener("R-TERM-0006")             # con «desde» comprobado
    assert reglas.vigencia_comprobada(ley2213, "2023-02-01")["comprobada"] is True
    assert reglas.vigencia_comprobada(ley2213, "2021-02-01")["motivo"] == "fuera_de_periodo"
    assert reglas.vigente("R-TERM-0006", "2021-02-01") is None
    sabado = reglas.obtener("R-TERM-0007")
    assert reglas.vigencia_comprobada(sabado, "2026-10-02")["motivo"] == "regla_no_verificada"


def test_vigentes_filtra_por_fecha_procedimiento_y_estado():
    j05 = reglas.vigentes("2026-10-02", procedimiento="J05")
    assert all("J05" in r["procedimientos"] for r in j05) and len(j05) >= 20
    ids = [r["id"] for r in reglas.vigentes("2026-10-02")]
    assert len(ids) == len(set(ids)), "a una fecha solo puede aplicar una versión de cada regla"
    assert all(r["estado"] == reglas.NO_VERIFICADO for r in reglas.vigentes("2021-03-01", estado=reglas.NO_VERIFICADO))
    assert "R-PLAZO-0001" in {r["id"] for r in reglas.vigentes("2021-03-01", estado=reglas.NO_VERIFICADO)}


def test_buscar_por_norma_con_siglas_y_articulo():
    assert {r["id"] for r in reglas.buscar_por_norma("CGP art. 118")} == {"R-TERM-0001", "R-TERM-0002", "R-TERM-0003"}
    assert "R-PLAZO-0004" in {r["id"] for r in reglas.buscar_por_norma("Decreto 2591 de 1991, artículo 31")}
    assert "R-LIQ-0004" in {r["id"] for r in reglas.buscar_por_norma("Código Sustantivo del Trabajo art. 306")}
    assert reglas.buscar_por_norma("Ley 9999 de 2031") == []
    assert reglas.buscar_por_norma("") == []


def test_validar_rechaza_un_registro_mal_formado():
    base = copy.deepcopy(reglas.registro())
    malo = copy.deepcopy(base)
    malo["reglas"][0]["enlace"] = "https://blog.ejemplo.com/ley"          # verificada sin fuente oficial
    with pytest.raises(reglas.ErrorRegistro, match="sin enlace de fuente oficial"):
        reglas.validar(malo)
    malo = copy.deepcopy(base)
    v2 = next(r for r in malo["reglas"] if r["id"] == "R-FEST-0001" and r["version"] == 2)
    v2["vigencia"]["desde"] = "2026-01-01"                                 # se solapa con la versión 1
    with pytest.raises(reglas.ErrorRegistro, match="se solapan"):
        reglas.validar(malo)
    malo = copy.deepcopy(base)
    malo["reglas"][0]["estado"] = "APROBADA"
    with pytest.raises(reglas.ErrorRegistro, match="estado desconocido"):
        reglas.validar(malo)
    malo = copy.deepcopy(base)
    pendiente = next(r for r in malo["reglas"] if r["estado"] == reglas.NO_VERIFICADO)
    pendiente["notas"] = ""
    with pytest.raises(reglas.ErrorRegistro, match="debe explicar qué falta"):
        reglas.validar(malo)


def test_fechas_imposibles():
    for mala in ("2026-02-30", "2025-02-29", "30/02/2026", "2026-13-01", "", None, 20260101):
        with pytest.raises((ValueError, TypeError)):
            reglas.a_fecha(mala)
    assert reglas.a_fecha("2024-02-29") == date(2024, 2, 29)


def test_resumen_y_tabla_de_parametros_vacia():
    r = reglas.resumen()
    assert r["total_versiones"] == len(reglas.todas())
    assert sum(r["por_estado"].values()) == r["total_versiones"]
    assert r["verificadas_con_enlace"] == r["por_estado"][reglas.VERIFICADA]
    # Ningún salario mínimo, tasa ni índice se cargó de memoria: la tabla está vacía hasta verificar cada valor.
    tabla = json.loads((RAIZ / "reglas" / "parametros.json").read_text(encoding="utf-8"))
    assert tabla["parametros"] == []


def test_sin_nombres_de_universidades_en_registro_ni_documentacion():
    rutas = [RAIZ / "reglas" / "registro.json", RAIZ / "reglas.py", RAIZ / "evaluacion" / "procedimientos.jsonl"]
    rutas += sorted((RAIZ / "procedimientos").glob("*.py")) + sorted((RAIZ / "docs" / "procedimientos").glob("*.md"))
    for ruta in rutas:
        assert "universidad" not in ruta.read_text(encoding="utf-8").lower(), ruta.name


def test_la_tabla_en_markdown_esta_al_dia_con_el_registro():
    import importlib.util
    spec = importlib.util.spec_from_file_location("tabla_reglas", RAIZ / "scripts" / "tabla_reglas.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    texto = m.generar()
    assert m.SALIDA.read_text(encoding="utf-8") == texto, "ejecute: python scripts/tabla_reglas.py"
    assert all(r["id"] in texto for r in reglas.todas())
