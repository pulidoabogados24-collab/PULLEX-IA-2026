"""Otros generadores frente al corte por límite de longitud (PUL-017, ítem 5): JSON del Laboratorio y del Taller,
documentos, pasos de un flujo, escrito modelo del Taller, boletín y perfiles del coordinador.
Antes de este cambio ninguno miraba el motivo de parada: una salida cortada se guardaba y se mostraba como terminada.
El modelo es un doble: estas pruebas verifican que se detecta el corte y se actúa, no la calidad de lo que escribiría la IA real."""
import json

import pytest

from conftest import FakeAnthropic, auth, nuevo_usuario
from test_documentos import CAMPOS_DESPIDO, CAMPOS_TUTELA, eventos_sse, generar


@pytest.fixture(autouse=True)
def limpio():
    FakeAnthropic.guion_create, FakeAnthropic.llamadas_create = [], []
    FakeAnthropic.guion, FakeAnthropic.llamadas_stream = [], []
    FakeAnthropic.fallar_create = False
    yield
    FakeAnthropic.guion_create, FakeAnthropic.guion = [], []


CASO = json.dumps(FakeAnthropic.CASO, ensure_ascii=False)


def test_json_cortado_por_limite_se_reintenta_con_mas_espacio(modulo):
    FakeAnthropic.guion_create = [(CASO[:60], "max_tokens"), (CASO, "end_turn")]
    caso = modulo.llamar_json("Crea un caso de Derecho Penal.", max_tokens=2500)
    assert caso["titulo"] == FakeAnthropic.CASO["titulo"]
    primero, segundo = (k["max_tokens"] for k in FakeAnthropic.llamadas_create)
    assert segundo == 2 * primero


def test_json_cortado_siempre_falla_con_error_claro_y_con_tope(modulo):
    FakeAnthropic.guion_create = [(CASO[:60], "max_tokens")] * 3
    with pytest.raises(ValueError):
        modulo.llamar_json("Crea un caso de Derecho Penal.", max_tokens=2500)
    assert all(k["max_tokens"] <= modulo.MAX_TOKENS_JSON_TOPE for k in FakeAnthropic.llamadas_create)


def test_json_malformado_sin_corte_se_reintenta_igual_que_antes(modulo):
    FakeAnthropic.guion_create = [("esto no es json", "end_turn"), (CASO, "end_turn")]
    assert modulo.llamar_json("Crea un caso.")["titulo"] == FakeAnthropic.CASO["titulo"]
    a, b = (k["max_tokens"] for k in FakeAnthropic.llamadas_create)
    assert a == b


# ---------------------------------------------------------------------------------- documentos
def test_documento_cortado_se_continua_y_queda_completo(cliente, modulo):
    _, _, t = nuevo_usuario(cliente)
    FakeAnthropic.guion_create = [("# ACCIÓN DE TUTELA\n\nSeñor juez [COMPLETAR: ciudad]. Hechos de la solicitud y un argumento que se", "max_tokens"),
                                  ("un argumento que se completa aquí. Pretensiones y firma.", "end_turn")]
    r = generar(cliente, t)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["incompleto"] is False and "se completa aquí" in d["texto"] and d["texto"].count("un argumento que se") == 1
    assert "INCOMPLETO" not in " ".join(d["advertencias"])
    assert "se cortó" in FakeAnthropic.llamadas_create[1]["messages"][-1]["content"]


def test_documento_que_sigue_cortado_se_marca_incompleto_y_visible(cliente, modulo):
    _, _, t = nuevo_usuario(cliente)
    FakeAnthropic.guion_create = [("# ACCIÓN DE TUTELA\n\nSeñor juez [COMPLETAR: ciudad]. Primer tramo " + str(i), "max_tokens") for i in range(5)]
    d = generar(cliente, t).json()
    assert d["incompleto"] is True
    assert d["advertencias"][0].startswith("Este borrador quedó INCOMPLETO") and "quedó incompleto" in d["texto"]
    guardado = cliente.get(f"/api/documentos/{d['id']}", headers=auth(t)).json()
    assert "quedó incompleto" in guardado["texto"]


def test_documento_normal_no_cambia(cliente):
    _, _, t = nuevo_usuario(cliente)
    d = generar(cliente, t).json()
    assert d["incompleto"] is False and not any("INCOMPLETO" in a for a in d["advertencias"])


# ------------------------------------------------------------------------------------- flujos
def test_paso_de_flujo_cortado_se_continua_solo(cliente, modulo):
    _, _, t = nuevo_usuario(cliente)
    FakeAnthropic.guion = [("Liquidación orientativa: el salario base es de dos millones y el tiempo laborado de dos años, de modo que", "max_tokens"),
                           ("dos años, de modo que la indemnización se calcula con los días completos.", "end_turn")]
    r = cliente.post("/api/flujos/ejecutar", headers=auth(t), json={"flujo": "despido", "campos": CAMPOS_DESPIDO})
    ev = eventos_sse(r)
    assert ev[-1]["completo"] is True and not any(e["tipo"] == "paso_incompleto" for e in ev)
    paso1 = "".join(e["texto"] for e in ev if e["tipo"] == "texto" and e["n"] == 1)
    assert "se calcula con los días completos" in paso1 and paso1.count("de modo que") == 1


def test_paso_de_flujo_que_sigue_cortado_se_marca_y_el_flujo_queda_incompleto(cliente, modulo):
    email, _, t = nuevo_usuario(cliente)
    FakeAnthropic.guion = [("Tramo sin terminar del primer paso del flujo número " + str(i), "max_tokens") for i in range(modulo.motor.MAX_CONTINUACIONES + 1)]
    r = cliente.post("/api/flujos/ejecutar", headers=auth(t), json={"flujo": "despido", "campos": CAMPOS_DESPIDO})
    ev = eventos_sse(r)
    inc = [e for e in ev if e["tipo"] == "paso_incompleto"]
    assert len(inc) == 1 and inc[0]["n"] == 1
    assert ev[-1]["tipo"] == "fin" and ev[-1]["completo"] is False
    doc = next(e for e in ev if e["tipo"] == "documento")
    assert "(incompleto)" in doc["titulo"]
    guardado = cliente.get(f"/api/documentos/{doc['id']}", headers=auth(t)).json()
    assert "quedó incompleto" in guardado["texto"]


# ------------------------------------------------------------------------------------- taller
def _escenario_evaluado(cliente, t, **k):
    from test_taller import _escenario, _evaluar
    eid = _escenario(cliente, t, **k).json()["id"]
    _evaluar(cliente, t, eid)
    return eid


def test_escrito_modelo_cortado_no_se_guarda_en_cache_y_avisa(cliente):
    _, _, t = nuevo_usuario(cliente)
    eid = _escenario_evaluado(cliente, t, fuente="ia")   # escenario propio: no toca la caché compartida de modelos curados
    FakeAnthropic.guion_create = [("# DERECHO DE PETICIÓN\n\n" + "Texto del escrito modelo que no termina. " * 12, "max_tokens")] * 3
    r = cliente.post("/api/taller/modelo", headers=auth(t), json={"escenario_id": eid}).json()
    assert r["incompleto"] is True and "quedó incompleto" in r["texto"]
    assert not cliente.get(f"/api/taller/escenario/{eid}", headers=auth(t)).json()["tiene_modelo"]
    # el siguiente intento lo genera completo y esa versión sí queda guardada
    r2 = cliente.post("/api/taller/modelo", headers=auth(t), json={"escenario_id": eid}).json()
    assert r2["nuevo"] and not r2.get("incompleto")
    assert cliente.get(f"/api/taller/escenario/{eid}", headers=auth(t)).json()["tiene_modelo"]


# ------------------------------------------------------------------------------------ boletín
def test_boletin_cortado_lleva_aviso_y_mas_espacio(modulo):
    FakeAnthropic.guion_create = [("## Noticias jurídicas\n\nUna noticia que se corta", "max_tokens")]
    texto = modulo.generar_boletin_texto()
    assert "quedó incompleto" in texto
    assert FakeAnthropic.llamadas_create[0]["max_tokens"] == modulo.MAX_TOKENS_BOLETIN > 1800


def test_boletin_completo_no_lleva_aviso(modulo):
    FakeAnthropic.guion_create = [("## Noticias jurídicas\n\nTodo bien.", "end_turn")]
    assert "incompleto" not in modulo.generar_boletin_texto()


# ------------------------------------------------------------------------------------ perfiles
def test_perfil_cortado_lleva_aviso_en_su_resultado(cliente):
    from test_perfiles import DESPIDO
    _, _, t = nuevo_usuario(cliente)
    FakeAnthropic.guion_create = [("Sección 1. Análisis del despido que se interrumpe porque se acabó el espacio", "max_tokens")]
    r = cliente.post("/api/coordinador/ejecutar", headers=auth(t), json={"tarea": DESPIDO})
    assert r.status_code == 200, r.text
    primero = r.json()["perfiles"][0]
    assert "se cortó por límite de longitud" in primero["resultado"]
