"""J06 — Liquidaciones: fórmulas, aritmética decimal reproducible, abstenciones y contradicciones."""
import inspect
import json
import re
from datetime import date
from decimal import Decimal

import pytest

import reglas
from procedimientos import j06_liquidaciones as j6

PREST = {"tipo": "prestaciones", "fecha_inicio": "2026-01-01", "fecha_fin": "2026-06-30",
         "salario_mensual": 2000000, "auxilio_transporte_mensual": 0}


def valores(r):
    return {d["concepto"]: d["valor"] for d in r["desglose"]}


# ------------------------------------------------------------------------------- días 30/360 --
@pytest.mark.parametrize("desde,hasta,dias", [
    ("2026-01-01", "2026-12-31", 360), ("2026-01-01", "2026-06-30", 180), ("2026-03-16", "2026-09-15", 180),
    ("2026-02-01", "2026-02-28", 30), ("2024-02-01", "2024-02-29", 30), ("2026-01-31", "2026-02-28", 31),
    ("2026-07-01", "2026-09-15", 75), ("2026-05-31", "2026-05-31", 1), ("2026-05-15", "2026-05-15", 1),
    ("2024-07-01", "2026-06-30", 720), ("2025-12-16", "2026-01-15", 30),
])
def test_dias_360(desde, hasta, dias):
    assert j6.dias_360(reglas.a_fecha(desde), reglas.a_fecha(hasta)) == dias


# ------------------------------------------------------------------------------ prestaciones --
def test_prestaciones_semestre_con_desglose_formula_parametros_redondeo_y_fuentes():
    r = j6.liquidar(PREST)
    assert r["estado"] == "CALCULADO" and r["total"] == 2560000
    assert valores(r) == {"cesantias": 1000000, "intereses_cesantias": 60000, "prima": 1000000, "vacaciones": 500000}
    ces = r["desglose"][0]
    assert ces["formula"] == "cesantias = base_mensual × dias / base_dias_anio"
    assert ces["formula_valores"] == "2000000 × 180 / 360" and ces["dias"] == "180" and ces["regla"] == "R-LIQ-0001"
    assert r["desglose"][1]["tasa_anual"] == "0.12"
    assert r["parametros"]["base_dias_anio"] == "360" and r["parametros"]["fuente_de_los_valores"] == "indicados por el usuario"
    assert r["redondeo"]["modo"] == "ROUND_HALF_UP" and r["redondeo"]["decimales"] == 0
    ids = {n["id"]: n for n in r["normas"]}
    assert {"R-LIQ-0001", "R-LIQ-0002", "R-LIQ-0003", "R-LIQ-0004", "R-LIQ-0005", "R-LIQ-0007"} <= set(ids)
    assert ids["R-LIQ-0001"]["estado"] == reglas.VERIFICADA and ids["R-LIQ-0001"]["enlace"].startswith("http")
    assert ids["R-LIQ-0007"]["estado"] == reglas.NO_VERIFICADO
    assert any("R-LIQ-0007" in a for a in r["advertencias"]), "el supuesto no verificado se advierte"
    assert any("360" in s for s in r["supuestos"]) and r["juicio_profesional"] and r["aviso"]


def test_redondeo_mitad_hacia_arriba_y_valor_exacto():
    r = j6.liquidar({**PREST, "fecha_inicio": "2026-01-31", "fecha_fin": "2026-02-28", "salario_mensual": 1500000})
    assert valores(r) == {"cesantias": 129167, "intereses_cesantias": 1335, "prima": 129167, "vacaciones": 64583}
    assert r["total"] == 324252 == sum(valores(r).values())
    assert r["desglose"][0]["valor_exacto"] == "129166.666667"
    assert j6.pesos(Decimal("0.5")) == 1 and j6.pesos(Decimal("1.5")) == 2 and j6.pesos(Decimal("2.4999")) == 2


def test_aritmetica_decimal_sin_errores_binarios():
    # 0,1 + 0,2 en binario no da 0,3; con decimales el resultado es exacto.
    r = j6.liquidar({"tipo": "indexacion", "valor_historico": "0.3", "ipc_inicial": "0.1", "ipc_final": "0.2", "fuente_ipc": "x"})
    assert r["desglose"][0]["valor_exacto"] == "0.6" and r["desglose"][0]["factor"] == "2"
    fuente = inspect.getsource(j6)
    assert "float(" not in fuente.replace('float("inf")', "").replace('float("-inf")', "")
    # Mismo resultado con número, texto con puntos de miles o texto simple.
    for salario in (2000000, "2000000", "2.000.000", "$ 2.000.000", "2000000,00", 2000000.0):
        assert j6.liquidar({**PREST, "salario_mensual": salario})["total"] == 2560000


def test_reproducible_misma_huella():
    a, b = j6.liquidar(PREST), j6.liquidar(dict(PREST))
    assert a == b and len(a["huella"]) == 16
    assert j6.liquidar({**PREST, "salario_mensual": 2000001})["huella"] != a["huella"]


def test_auxilio_de_transporte_lo_decide_el_usuario_porque_la_regla_no_esta_verificada():
    base = {**PREST, "fecha_inicio": "2026-03-16", "fecha_fin": "2026-09-15", "salario_mensual": 1800000,
            "auxilio_transporte_mensual": 200000}
    sin_decidir = j6.liquidar(base)
    assert sin_decidir["estado"] == "ABSTENCION" and sin_decidir["total"] is None
    assert any(f.startswith("auxilio_en_base_prestaciones") for f in sin_decidir["faltantes"])
    con = j6.liquidar({**base, "auxilio_en_base_prestaciones": True})
    sin = j6.liquidar({**base, "auxilio_en_base_prestaciones": False})
    assert valores(con) == {"cesantias": 1000000, "intereses_cesantias": 60000, "prima": 416667, "vacaciones": 450000}
    assert valores(sin) == {"cesantias": 900000, "intereses_cesantias": 54000, "prima": 375000, "vacaciones": 450000}
    assert valores(con)["vacaciones"] == valores(sin)["vacaciones"], "el auxilio nunca entra en vacaciones"
    assert "R-LIQ-0006" in {n["id"] for n in con["normas"]}
    assert any("SE INCLUYÓ" in s for s in con["supuestos"]) and any("NO se incluyó" in s for s in sin["supuestos"])


def test_periodos_por_defecto_y_avisos():
    r = j6.liquidar({**PREST, "fecha_inicio": "2024-07-01", "fecha_fin": "2026-09-15"})
    p = {d["concepto"]: d["periodo"] for d in r["desglose"]}
    assert p["cesantias"] == {"desde": "2026-01-01", "hasta": "2026-09-15"}      # solo el año en curso
    assert p["prima"] == {"desde": "2026-07-01", "hasta": "2026-09-15"}          # solo el semestre en curso
    assert p["vacaciones"] == {"desde": "2024-07-01", "hasta": "2026-09-15"}     # todo el tiempo
    assert any("solo por el año 2026" in a for a in r["advertencias"])
    assert any("No incluye salarios pendientes" in a for a in r["advertencias"])
    propio = j6.liquidar({**PREST, "fecha_inicio": "2024-07-01", "fecha_fin": "2026-09-15", "conceptos": ["prima"],
                          "periodos": {"prima": {"desde": "2026-01-01", "hasta": "2026-06-30"}}})
    assert valores(propio) == {"prima": 1000000}
    dias = j6.liquidar({**PREST, "conceptos": ["cesantias"], "dias": {"cesantias": 90}})
    assert valores(dias) == {"cesantias": 500000} and dias["desglose"][0]["origen_dias"] == "indicados por el usuario"


def test_vacaciones_con_dias_tomados():
    base = {**PREST, "fecha_inicio": "2024-07-01", "fecha_fin": "2026-06-30", "salario_mensual": 2400000, "conceptos": ["vacaciones"]}
    r = j6.liquidar({**base, "vacaciones_dias_tomados": 15})
    assert r["total"] == 1200000 and r["desglose"][0]["dias_vacaciones_pendientes"] == "15"
    demasiados = j6.liquidar({**base, "vacaciones_dias_tomados": 40})
    assert demasiados["estado"] == "CONTRADICCION" and "superan los causados" in demasiados["contradicciones"][0]


@pytest.mark.parametrize("cambio,falta", [
    ({"salario_mensual": None}, "salario_mensual"), ({"auxilio_transporte_mensual": None}, "auxilio_transporte_mensual"),
    ({"fecha_inicio": ""}, "fecha_inicio"), ({"fecha_fin": None}, "fecha_fin"),
])
def test_prestaciones_se_abstiene_sin_datos_esenciales(cambio, falta):
    r = j6.liquidar({**PREST, **cambio})
    assert r["estado"] == "ABSTENCION" and r["total"] is None and r["desglose"] == []
    assert falta in r["faltantes"]


@pytest.mark.parametrize("cambio,texto", [
    ({"fecha_fin": "2025-12-31"}, "anterior a la inicial"), ({"fecha_fin": "2026-02-30"}, "no existe"),
    ({"salario_mensual": -5}, "no puede ser menor"), ({"salario_mensual": "dos millones"}, "no es un número"),
    ({"salario_mensual": True}, "no es un número"), ({"conceptos": ["bonificacion"]}, "solo admite"),
    ({"conceptos": ["intereses_cesantias"]}, "incluya ambos"), ({"salario_mensual": "1e30"}, "no es un número"),
    ({"salario_mensual": 10 ** 16}, "demasiado grande"),
])
def test_prestaciones_contradicciones(cambio, texto):
    r = j6.liquidar({**PREST, **cambio})
    assert r["estado"] == "CONTRADICCION" and r["total"] is None
    assert texto in " ".join(r["contradicciones"]), r["contradicciones"]


# --------------------------------------------------------------------------------- intereses --
def test_interes_legal_civil_usa_la_tasa_de_la_regla_verificada():
    r = j6.liquidar({"tipo": "intereses_mora", "capital": 10000000, "clase": "legal_civil", "base_dias": 360,
                     "periodos": [{"desde": "2026-01-01", "hasta": "2026-06-30"}]})
    assert r["total"] == 301667 and r["total_con_capital"] == 10301667
    d = r["desglose"][0]
    assert d["dias"] == "181" and d["tasa_aplicada_anual_pct"] == "6" and d["formula_valores"] == "10000000 × 0.06 × 181 / 360"
    assert {"R-INT-0001", "R-INT-0003"} <= {n["id"] for n in r["normas"]}
    assert reglas.obtener("R-INT-0001")["parametros"]["tasa_anual"] == "0.06"


def test_moratorio_comercial_multiplica_por_uno_y_medio_y_exige_fuente():
    base = {"tipo": "intereses_mora", "capital": 5000000, "clase": "comercial_moratorio", "metodo": "simple",
            "base_dias": 365, "periodos": [{"desde": "2026-01-01", "hasta": "2026-01-31", "tasa_pct": 20}]}
    sin_fuente = j6.liquidar(base)
    assert sin_fuente["estado"] == "ABSTENCION" and any(f.startswith("fuente_tasas") for f in sin_fuente["faltantes"])
    r = j6.liquidar({**base, "fuente_tasas": "tasa de ejemplo"})
    assert r["total"] == 127397 and r["desglose"][0]["tasa_aplicada_anual_pct"] == "30"
    assert r["parametros"]["factor"] == "1.5" and "tasa de ejemplo" in " ".join(r["supuestos"])
    eq = j6.liquidar({**base, "fuente_tasas": "tasa de ejemplo", "metodo": "equivalente_diaria", "capital": 10000000})
    assert eq["total"] == 222910 and eq["desglose"][0]["tasa_diaria"].startswith("0.000719064")
    assert "R-INT-0004" in {n["id"] for n in eq["normas"]}
    assert any("R-INT-0004" in a for a in eq["advertencias"]), "el método pendiente de revisión humana se advierte"


def test_intereses_no_tienen_tasas_ni_bases_por_defecto():
    base = {"tipo": "intereses_mora", "capital": 1000000, "clase": "tasa_indicada", "metodo": "simple", "base_dias": 365,
            "fuente_tasas": "contrato", "periodos": [{"desde": "2026-01-01", "hasta": "2026-01-31", "tasa_pct": 18}]}
    assert j6.liquidar(base)["estado"] == "CALCULADO"
    for quitar, falta in (("base_dias", "base_dias"), ("metodo", "metodo"), ("periodos", "periodos"), ("clase", "clase"),
                          ("capital", "capital")):
        r = j6.liquidar({k: v for k, v in base.items() if k != quitar})
        assert r["estado"] == "ABSTENCION" and any(f.startswith(falta) for f in r["faltantes"]), (quitar, r["faltantes"])
    sin_tasa = j6.liquidar({**base, "periodos": [{"desde": "2026-01-01", "hasta": "2026-01-31"}]})
    assert sin_tasa["estado"] == "ABSTENCION" and "periodos[1].tasa_pct" in sin_tasa["faltantes"]
    # El módulo no trae ninguna tasa de interés bancario corriente ni salario mínimo escritos en el código.
    assert j6.parametro("interes_bancario_corriente_ea", "2026-10-02") is None
    assert j6.parametro("salario_minimo_mensual", "2026-10-02") is None
    assert not re.search(r"\b1[.,]?[34]\d{2}[.,]?\d{3}\b", inspect.getsource(j6)), "no hay salarios mínimos en el código"


@pytest.mark.parametrize("cambio,texto", [
    ({"periodos": [{"desde": "2026-01-01", "hasta": "2026-03-31"}, {"desde": "2026-03-15", "hasta": "2026-04-30"}]}, "se solapan"),
    ({"periodos": [{"desde": "2026-03-31", "hasta": "2026-01-01"}]}, "antes de empezar"),
    ({"base_dias": 300}, "360 o 365"), ({"metodo": "equivalente_diaria"}, "interés simple"),
    ({"periodos": [{"desde": "2026-01-01", "hasta": "2026-03-31", "tasa_pct": 30}]}, "no admite otra tasa"),
    ({"clase": "usura"}, "debe ser"), ({"capital": 0}, "no puede ser menor"),
])
def test_intereses_contradicciones(cambio, texto):
    base = {"tipo": "intereses_mora", "capital": 1000000, "clase": "legal_civil", "base_dias": 360,
            "periodos": [{"desde": "2026-01-01", "hasta": "2026-03-31"}]}
    r = j6.liquidar({**base, **cambio})
    assert r["estado"] == "CONTRADICCION" and r["total"] is None
    assert texto in " ".join(r["contradicciones"]), r["contradicciones"]


def test_periodos_separados_se_ordenan_y_redondean_por_separado():
    r = j6.liquidar({"tipo": "intereses_mora", "capital": 1000000, "clase": "legal_civil", "base_dias": 365,
                     "periodos": [{"desde": "2026-07-01", "hasta": "2026-07-31"}, {"desde": "2026-01-01", "hasta": "2026-03-31"}]})
    assert [d["periodo"]["desde"] for d in r["desglose"]] == ["2026-01-01", "2026-07-01"]
    assert [d["valor"] for d in r["desglose"]] == [14795, 5096] and r["total"] == 19891


# -------------------------------------------------------------------------------- indexación --
def test_indexacion_formula_fuente_y_entradas_obligatorias():
    r = j6.liquidar({"tipo": "indexacion", "valor_historico": 2500000, "ipc_inicial": "105,48", "ipc_final": "151,36",
                     "fuente_ipc": "índices de ejemplo", "periodo_inicial": "2019-01", "periodo_final": "2026-08"})
    assert r["total"] == 3587410 and r["desglose"][0]["diferencia"] == 1087410
    assert r["desglose"][0]["formula"] == "valor_actualizado = valor_historico × ipc_final / ipc_inicial"
    n = r["normas"][0]
    assert n["id"] == "R-IDX-0001" and "corteconstitucional.gov.co" in n["enlace"]
    for quitar in ("ipc_inicial", "ipc_final", "fuente_ipc", "valor_historico"):
        e = {"tipo": "indexacion", "valor_historico": 1, "ipc_inicial": 1, "ipc_final": 2, "fuente_ipc": "x"}
        e.pop(quitar)
        a = j6.liquidar(e)
        assert a["estado"] == "ABSTENCION" and any(f.startswith(quitar) for f in a["faltantes"])
    cero = j6.liquidar({"tipo": "indexacion", "valor_historico": 1000, "ipc_inicial": 0, "ipc_final": 2, "fuente_ipc": "x"})
    assert cero["estado"] == "CONTRADICCION"
    invertidos = j6.liquidar({"tipo": "indexacion", "valor_historico": 1000, "ipc_inicial": 150, "ipc_final": 100, "fuente_ipc": "x"})
    assert invertidos["total"] == 667 and any("menor que el inicial" in a for a in invertidos["advertencias"])


def test_tipo_desconocido_o_ausente():
    assert j6.liquidar({})["estado"] == "ABSTENCION"
    assert j6.liquidar({"tipo": "honorarios"})["estado"] == "CONTRADICCION"
    assert j6.liquidar("x")["estado"] == "CONTRADICCION"


def test_tabla_de_parametros_solo_acepta_valores_con_enlace_oficial(tmp_path, monkeypatch):
    tabla = {"parametros": [
        {"nombre": "ipc", "valor": "1", "desde": "2026-01-01", "hasta": "2026-01-31", "enlace": "https://blog.ejemplo.com/ipc"},
        {"nombre": "ipc", "valor": "2", "desde": "2026-02-01", "hasta": "2026-02-28",
         "enlace": "https://www.dane.gov.co/ipc", "consultado": "2026-10-02"}]}
    ruta = tmp_path / "parametros.json"
    ruta.write_text(json.dumps(tabla), encoding="utf-8")
    monkeypatch.setattr(j6, "RUTA_PARAMETROS", ruta)
    assert j6.parametro("ipc", "2026-01-15") is None, "un valor sin fuente oficial no se usa"
    assert j6.parametro("ipc", "2026-02-15")["valor"] == "2"
    assert j6.parametro("ipc", date(2026, 3, 1)) is None, "fuera del período no hay valor"
