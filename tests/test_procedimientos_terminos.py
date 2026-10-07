"""J05 — Cómputo de términos: calendario por regla, conteo, abstenciones y contradicciones."""
import json
from datetime import date, timedelta
from pathlib import Path

import pytest

import reglas
from procedimientos import calendario as cal
from procedimientos import j05_terminos as j5

RAIZ = Path(__file__).resolve().parent.parent
OFICIALES = json.loads((RAIZ / "reglas" / "festivos_oficiales.json").read_text(encoding="utf-8"))
ADM = {"regimen": "administrativo", "forma_notificacion": "recepcion"}


# ------------------------------------------------------------------------------ calendario --
def test_festivos_calculados_coinciden_con_las_fechas_publicadas_por_la_autoridad():
    """Fuente: páginas de feriados del Banco de la República y circulares citadas en
    reglas/festivos_oficiales.json (consultadas el 2026-10-02)."""
    publicadas = OFICIALES["festivos"]
    assert len(publicadas) >= 18
    for f in publicadas:
        assert reglas.es_enlace_oficial(f["enlace"]), f["enlace"]
        d = reglas.a_fecha(f["fecha"])
        assert d in cal.festivos(d.year), f"{f['fecha']} ({f['nombre']}) publicado por {f['autoridad']} y no calculado"
    de_2026 = {reglas.a_fecha(f["fecha"]) for f in publicadas if f["fecha"].startswith("2026")}
    assert len(de_2026) == 13 and de_2026 <= set(cal.festivos(2026))


def test_calendario_2026_completo_por_regla():
    esperado = ["01-01", "01-12", "03-23", "04-02", "04-03", "05-01", "05-18", "06-08", "06-15", "06-29", "07-13",
                "07-20", "08-07", "08-17", "10-12", "11-02", "11-16", "12-08", "12-25"]
    assert [d.isoformat()[5:] for d in cal.festivos(2026)] == esperado
    assert all(d.weekday() < 5 for d in cal.festivos(2026)), "en 2026 ningún festivo cae en fin de semana"


def test_el_9_de_julio_solo_es_festivo_desde_la_ley_2578_de_2026():
    assert date(2025, 7, 14) not in cal.festivos(2025)
    assert date(2025, 7, 9) not in cal.festivos(2025)
    assert cal.festivos(2026)[date(2026, 7, 13)]["version"] == 2
    assert cal.festivos(2026)[date(2026, 1, 12)]["version"] == 1          # antes del 2 de junio rige la versión 1
    assert date(2027, 7, 12) in cal.festivos(2027)                         # 9 de julio de 2027 es viernes → lunes 12
    assert len(cal.festivos(2024)) == 18 and len(cal.festivos(2027)) == 19


def test_pascua_y_festivos_que_dependen_de_ella():
    assert cal.pascua(2024) == date(2024, 3, 31)
    assert cal.pascua(2025) == date(2025, 4, 20)
    assert cal.pascua(2026) == date(2026, 4, 5)
    assert cal.pascua(2027) == date(2027, 3, 28)
    f = cal.festivos(2026)
    p = cal.pascua(2026)
    assert f[p - timedelta(days=3)]["nombre"] == "Jueves Santo" and f[p - timedelta(days=2)]["nombre"] == "Viernes Santo"
    for dias, nombre in ((43, "Ascensión del Señor"), (64, "Corpus Christi"), (71, "Sagrado Corazón de Jesús")):
        d = p + timedelta(days=dias)
        assert d.weekday() == 0 and f[d]["nombre"] == nombre


def test_traslado_al_lunes_y_dos_festivos_el_mismo_dia():
    assert cal.al_lunes(date(2026, 1, 6)) == date(2026, 1, 12)      # martes → lunes siguiente
    assert cal.al_lunes(date(2025, 1, 6)) == date(2025, 1, 6)       # ya es lunes
    assert cal.al_lunes(date(2025, 6, 29)) == date(2025, 6, 30)     # domingo → lunes
    # 2025: San Pedro (29 de junio, domingo) y Sagrado Corazón caen el mismo lunes 30 de junio.
    junto = cal.festivos(2025)[date(2025, 6, 30)]["nombre"]
    assert "San Pedro" in junto and "Sagrado Corazón" in junto
    assert len(cal.festivos(2025)) == 17
    # Los festivos de fecha fija no se trasladan aunque caigan en domingo.
    assert date(2025, 7, 20) in cal.festivos(2025) and date(2025, 7, 21) not in cal.festivos(2025)


def test_vacancia_y_semana_santa_judicial():
    for v in OFICIALES["vacancia_judicial_publicada"]:
        ini, fin = reglas.a_fecha(v["desde"]), reglas.a_fecha(v["hasta"])
        assert cal.en_vacancia_fin_de_anio(ini) and cal.en_vacancia_fin_de_anio(fin)
        assert not cal.en_vacancia_fin_de_anio(ini - timedelta(days=1))
        assert not cal.en_vacancia_fin_de_anio(fin + timedelta(days=1))
    assert cal.semana_santa_judicial(2026) == [date(2026, 3, 30), date(2026, 3, 31), date(2026, 4, 1)]
    c = cal.Calendario(vacancia_judicial=True, semana_santa_judicial=True)
    assert "vacancia" in c.motivo_inhabil(date(2026, 1, 5)) and "Semana Santa" in c.motivo_inhabil(date(2026, 3, 31))
    assert cal.Calendario().es_habil(date(2026, 1, 5)) and cal.Calendario().es_habil(date(2026, 3, 31))


def test_sumar_meses_respeta_fin_de_mes_y_bisiestos():
    assert cal.sumar_meses(date(2023, 10, 31), 4) == date(2024, 2, 29)
    assert cal.sumar_meses(date(2025, 10, 31), 4) == date(2026, 2, 28)
    assert cal.sumar_meses(date(2026, 11, 15), 2) == date(2027, 1, 15)
    assert cal.sumar_meses(date(2024, 2, 29), 24) == date(2026, 2, 28)


def test_anio_fuera_de_rango():
    with pytest.raises(ValueError):
        cal.festivos(1970)


# ---------------------------------------------------------------------------------- cómputo --
def test_peticion_quince_dias_con_festivos_trasladados():
    r = j5.calcular({**ADM, "termino_id": "R-PLAZO-0001", "fecha_notificacion": "2026-07-01"})
    assert r["estado"] == "CALCULADO" and r["fecha_vencimiento"] == "2026-07-24"
    assert r["inicio_computo"] == "2026-07-02"
    contados = [c for c in r["cronologia"] if c["cuenta"]]
    assert len(contados) == 15 and contados[-1]["fecha"] == "2026-07-24"
    motivos = {c["fecha"]: c["motivo"] for c in r["cronologia"] if c["motivo"]}
    assert "Chiquinquirá" in motivos["2026-07-13"] and motivos["2026-07-04"] == "sábado"
    assert r["cronologia"][0]["cuenta"] is None            # el día de la recepción no se cuenta
    ids = {n["id"] for n in r["normas"]}
    assert {"R-PLAZO-0001", "R-TERM-0004", "R-FEST-0001", "R-TERM-0007"} <= ids
    assert any("sábado" in s.lower() and "no verificado" in s for s in r["supuestos"])
    assert any("R-TERM-0007" in a for a in r["advertencias"])
    assert r["aviso"] and r["juicio_profesional"]


def test_el_calculo_es_reproducible():
    e = {**ADM, "termino_id": "R-PLAZO-0003", "fecha_notificacion": "2026-10-01"}
    a, b = j5.calcular(e), j5.calcular(dict(e))
    assert a == b and a["huella"] == b["huella"] and len(a["huella"]) == 16
    assert j5.calcular({**e, "fecha_notificacion": "2026-10-02"})["huella"] != a["huella"]


def test_usa_la_regla_vigente_a_la_fecha_no_la_de_hoy():
    hoy = j5.calcular({**ADM, "termino_id": "R-PLAZO-0001", "fecha_notificacion": "2026-08-03"})
    emergencia = j5.calcular({**ADM, "termino_id": "R-PLAZO-0001", "fecha_notificacion": "2021-03-01"})
    assert hoy["normas"][0]["version"] == 3 and hoy["estado"] == "CALCULADO"
    assert emergencia["estado"] == "ABSTENCION" and emergencia["fecha_vencimiento"] is None
    assert emergencia["normas"][0]["version"] == 2 and "Decreto Legislativo 491 de 2020" in " ".join(emergencia["faltantes"])
    # Si el usuario verifica el plazo y lo indica, se calcula y queda dicho que el número es suyo.
    con_dato = j5.calcular({**ADM, "termino_id": "R-PLAZO-0001", "fecha_notificacion": "2021-03-01", "cantidad": 30})
    assert con_dato["estado"] == "CALCULADO" and any("indicó el usuario" in s for s in con_dato["supuestos"])
    antes = j5.calcular({**ADM, "termino_id": "R-PLAZO-0001", "fecha_notificacion": "2014-03-03"})
    assert antes["estado"] == "ABSTENCION" and "no tiene versión registrada" in " ".join(antes["faltantes"])


@pytest.mark.parametrize("entrada,falta", [
    ({"termino_id": "R-PLAZO-0001", "fecha_notificacion": "2026-08-03", "forma_notificacion": "recepcion"}, "regimen"),
    ({"regimen": "administrativo", "termino_id": "R-PLAZO-0001", "fecha_notificacion": "2026-08-03"}, "forma_notificacion"),
    ({**ADM, "termino_id": "R-PLAZO-0001"}, "fecha_notificacion"),
    ({**ADM, "fecha_notificacion": "2026-08-03"}, "cantidad"),
    ({**ADM, "fecha_notificacion": "2026-08-03", "cantidad": 5, "unidad": "dias"}, "tipo_dias"),
    ({**ADM, "fecha_notificacion": "2026-08-03", "cantidad": 5}, "unidad"),
])
def test_se_abstiene_si_falta_un_dato_esencial(entrada, falta):
    r = j5.calcular(entrada)
    assert r["estado"] == "ABSTENCION" and r["fecha_vencimiento"] is None and r["cronologia"] == []
    assert any(f.startswith(falta) for f in r["faltantes"]), r["faltantes"]


def test_se_abstiene_cuando_un_dato_desconocido_cambia_el_resultado():
    base = {"regimen": "cgp", "forma_notificacion": "estado", "termino_id": "R-PLAZO-0008", "fecha_notificacion": "2025-12-15"}
    r = j5.calcular(base)
    assert r["estado"] == "ABSTENCION" and r["fecha_vencimiento"] is None
    assert {(e["vacancia_judicial"], e["fecha_vencimiento"]) for e in r["escenarios"]} == {(True, "2026-01-20"), (False, "2025-12-30")}
    assert any(f.startswith("vacancia_judicial") for f in r["faltantes"])
    assert "R-VAC-0001" in {n["id"] for n in r["normas"]}
    assert j5.calcular({**base, "vacancia_judicial": True})["fecha_vencimiento"] == "2026-01-20"
    assert j5.calcular({**base, "vacancia_judicial": False})["fecha_vencimiento"] == "2025-12-30"
    # El mismo dato desconocido NO impide calcular cuando no cambia nada.
    lejos = j5.calcular({**base, "fecha_notificacion": "2026-08-10"})
    assert lejos["estado"] == "CALCULADO" and any("mismo en cualquiera" in s for s in lejos["supuestos"])


def test_semana_santa_judicial_desconocida_muestra_escenarios():
    base = {"regimen": "cgp", "forma_notificacion": "estado", "termino_id": "R-PLAZO-0005", "fecha_notificacion": "2026-03-27"}
    r = j5.calcular(base)
    assert r["estado"] == "ABSTENCION"
    assert {(e["semana_santa_judicial"], e["fecha_vencimiento"]) for e in r["escenarios"]} == {(True, "2026-04-08"), (False, "2026-04-01")}
    assert all("vacancia_judicial" not in e for e in r["escenarios"]), "solo se muestra el dato que cambia el resultado"


def test_audiencia_y_mensaje_de_datos_sin_acuse_quedan_a_juicio_profesional():
    r = j5.calcular({"regimen": "cgp", "forma_notificacion": "audiencia", "termino_id": "R-PLAZO-0005", "fecha_notificacion": "2026-08-10"})
    assert r["estado"] == "ABSTENCION" and any("audiencia" in f for f in r["faltantes"]) and r["juicio_profesional"]
    base = {"regimen": "cgp", "forma_notificacion": "mensaje_datos", "termino_id": "R-PLAZO-0009", "fecha_notificacion": "2026-10-08"}
    assert j5.calcular(base)["estado"] == "ABSTENCION"
    ok = j5.calcular({**base, "acuse_constatado": True})
    assert ok["fecha_vencimiento"] == "2026-10-27" and ok["inicio_computo"] == "2026-10-14"
    assert "R-TERM-0006" in {n["id"] for n in ok["normas"]} and len(ok["juicio_profesional"]) >= 2
    viejo = j5.calcular({**base, "fecha_notificacion": "2021-10-07", "acuse_constatado": True, "vacancia_judicial": False,
                         "semana_santa_judicial": False})
    assert viejo["estado"] == "ABSTENCION", "antes de la Ley 2213 de 2022 no hay regla registrada"


@pytest.mark.parametrize("entrada,texto", [
    ({**ADM, "termino_id": "R-PLAZO-0001", "fecha_notificacion": "2026-02-30"}, "no existe"),
    ({**ADM, "termino_id": "R-PLAZO-0001", "fecha_notificacion": "2025-02-29"}, "no existe"),
    ({**ADM, "termino_id": "R-PLAZO-0001", "fecha_notificacion": "2026-08-03",
      "suspensiones": [{"desde": "2026-08-10", "hasta": "2026-08-05"}]}, "antes de empezar"),
    ({"regimen": "cgp", "forma_notificacion": "estado", "termino_id": "R-PLAZO-0005", "fecha_notificacion": "2026-05-05",
      "fecha_providencia": "2026-05-10"}, "anterior a la providencia"),
    ({"regimen": "cgp", "forma_notificacion": "estado", "termino_id": "R-PLAZO-0005", "fecha_notificacion": "2026-08-09"}, "día inhábil"),
    ({"regimen": "cgp", "forma_notificacion": "estado", "termino_id": "R-PLAZO-0005", "fecha_notificacion": "2026-07-13"}, "día inhábil"),
    ({"regimen": "cgp", "forma_notificacion": "recepcion", "termino_id": "R-PLAZO-0001", "fecha_notificacion": "2026-08-03"}, "régimen"),
    ({**ADM, "termino_id": "R-PLAZO-0001", "fecha_notificacion": "2026-08-03", "cantidad": 20}, "fija 15"),
    ({**ADM, "termino_id": "R-PLAZO-9999", "fecha_notificacion": "2026-08-03"}, "no está en la tabla"),
    ({**ADM, "fecha_notificacion": "2026-08-03", "cantidad": 0, "unidad": "dias", "tipo_dias": "habiles"}, "entre 1 y"),
    ({**ADM, "fecha_notificacion": "2026-08-03", "cantidad": "cinco", "unidad": "dias", "tipo_dias": "habiles"}, "número entero"),
])
def test_contradicciones_no_producen_fecha(entrada, texto):
    r = j5.calcular(entrada)
    assert r["estado"] == "CONTRADICCION" and r["fecha_vencimiento"] is None
    assert texto in " ".join(r["contradicciones"]), r["contradicciones"]


def test_meses_y_anios_con_extension_al_primer_dia_habil():
    base = {"regimen": "contencioso", "forma_notificacion": "comunicacion", "termino_id": "R-PLAZO-0012"}
    assert j5.calcular({**base, "fecha_notificacion": "2023-10-30"})["fecha_vencimiento"] == "2024-02-29"
    r = j5.calcular({**base, "fecha_notificacion": "2025-10-30"})
    assert r["fecha_vencimiento"] == "2026-03-02" and r["inicio_computo"] == "2025-10-31"
    assert any("R-TERM-0002" == n["id"] for n in r["normas"]) and len(r["juicio_profesional"]) >= 2
    # Vence en plena vacancia judicial: sin saber si el despacho la tuvo, no hay fecha definitiva.
    r = j5.calcular({**base, "fecha_notificacion": "2025-08-27"})          # 28 de agosto + 4 meses = 28 de diciembre
    assert r["estado"] == "ABSTENCION"
    assert {e["fecha_vencimiento"] for e in r["escenarios"]} == {"2025-12-29", "2026-01-13"}
    # Suspensión informada en un término de meses: corre el vencimiento los días suspendidos.
    r = j5.calcular({**base, "fecha_notificacion": "2026-03-02", "vacancia_judicial": False, "semana_santa_judicial": False,
                     "suspensiones": [{"desde": "2026-05-04", "hasta": "2026-05-13", "motivo": "conciliación"}]})
    assert r["fecha_vencimiento"] == "2026-07-14"          # 3 de julio + 10 días = 13 de julio (festivo) → 14
    assert any("suspensiones" in j.lower() for j in r["juicio_profesional"])


def test_dias_calendario_no_se_extienden_y_lo_advierte():
    r = j5.calcular({"regimen": "otro", "forma_notificacion": "otra", "cantidad": 10, "unidad": "dias",
                     "tipo_dias": "calendario", "fecha_notificacion": "2026-06-10"})
    assert r["fecha_vencimiento"] == "2026-06-20" and any("inhábil" in a for a in r["advertencias"])
    assert len([c for c in r["cronologia"] if c["cuenta"]]) == 10


def test_tabla_de_terminos_a_una_fecha_solo_trae_reglas_del_registro():
    hoy = j5.tabla_terminos("2026-10-02")
    assert len(hoy) == 15 and all(t["estado"] == reglas.VERIFICADA for t in hoy)
    assert {t["id"]: t["cantidad"] for t in hoy}["R-PLAZO-0001"] == 15
    emergencia = {t["id"]: t for t in j5.tabla_terminos("2021-03-01")}
    assert emergencia["R-PLAZO-0001"]["estado"] == reglas.NO_VERIFICADO and emergencia["R-PLAZO-0001"]["cantidad"] is None
    op = j5.opciones("2026-10-02")
    assert {r["id"] for r in op["regimenes"]} == set(j5.REGIMENES) and len(op["formas_notificacion"]) == len(j5.FORMAS)


def test_plazo_sin_clase_de_dias_verificada_exige_que_el_usuario_la_indique():
    base = {"regimen": "tutela", "forma_notificacion": "otra", "termino_id": "R-PLAZO-0014", "fecha_notificacion": "2026-10-01"}
    r = j5.calcular(base)
    assert r["estado"] == "ABSTENCION" and any(f.startswith("tipo_dias") for f in r["faltantes"])
    assert j5.calcular({**base, "tipo_dias": "calendario"})["fecha_vencimiento"] == "2026-10-11"
    assert j5.calcular({**base, "tipo_dias": "habiles"})["fecha_vencimiento"] == "2026-10-16"


def test_entrada_que_no_es_objeto():
    assert j5.calcular(None)["estado"] == "CONTRADICCION"
    assert j5.calcular([1, 2])["estado"] == "CONTRADICCION"
