"""Proveedor de IA alterno (OpenAI) y respaldo automático (proveedores.py).

Todo con dobles: FakeAnthropic y FakeOpenAI. La integración con la API real de OpenAI queda
NOT VERIFIED (no hay clave en este entorno)."""
import json
import logging
import types

import anthropic
import httpx2
import openai
import pytest

import proveedores
from conftest import FakeAnthropic, FakeOpenAI, auth, login_admin, nuevo_usuario


@pytest.fixture(autouse=True)
def openai_falso(monkeypatch):
    monkeypatch.setattr(openai, "OpenAI", FakeOpenAI)
    for v in ("PULLEX_PROVEEDOR", "PULLEX_RESPALDO", "PULLEX_OPENAI_MODELO", "OPENAI_API_KEY",
              "PULLEX_OPENAI_ESFUERZO"):
        monkeypatch.delenv(v, raising=False)
    FakeOpenAI.reiniciar()
    FakeAnthropic.ultima_llamada = None
    FakeAnthropic.eventos_extra, FakeAnthropic.eventos_final = [], []
    yield
    FakeOpenAI.reiniciar()


def _conv(cliente, t):
    return cliente.post("/api/conversaciones", headers=auth(t)).json()["id"]


def _sse(r):
    return [json.loads(l[6:]) for l in r.text.split("\n\n") if l.startswith("data: ")]


def _texto(eventos):
    return "".join(e["texto"] for e in eventos if e["tipo"] == "texto")


def _error_anthropic(cls, estado):
    resp = httpx2.Response(estado, request=httpx2.Request("POST", "https://api.anthropic.com/v1/messages"))
    return cls("simulado", response=resp, body=None)


def _usar_openai(monkeypatch, clave="sk-openai-prueba-no-real"):
    monkeypatch.setenv("PULLEX_PROVEEDOR", "openai")
    if clave:
        monkeypatch.setenv("OPENAI_API_KEY", clave)


# ------------------------------------------------------------------ selección de proveedor --
def test_por_defecto_anthropic_sin_respaldo(modulo):
    ia = modulo.ia_activa()
    assert ia["principal"] == {"proveedor": "anthropic", "nombre": "Anthropic (Claude)",
                               "modelo": "claude-sonnet-5-5", "configurado": True}
    assert ia["respaldo"] is None


def test_valores_invalidos_vuelven_al_defecto(monkeypatch):
    monkeypatch.setenv("PULLEX_PROVEEDOR", "gemini")
    monkeypatch.setenv("PULLEX_RESPALDO", "anthropic")  # igual al principal: se ignora
    aj = proveedores.ajustes()
    assert aj["proveedor"] == "anthropic" and aj["respaldo"] == ""
    assert aj["openai_modelo"] == proveedores.OPENAI_MODELO_DEFECTO == "gpt-6.1-sol"


def test_chat_con_openai_entrega_el_texto_por_sse(cliente, modulo, monkeypatch):
    _usar_openai(monkeypatch)
    monkeypatch.setenv("PULLEX_OPENAI_MODELO", "gpt-6-luna")
    _, _, t = nuevo_usuario(cliente)
    r = cliente.post("/api/chat", headers=auth(t), json={"conversacion": _conv(cliente, t), "mensaje": "hola",
                                                         "web": False})
    assert r.status_code == 200
    ev = _sse(r)
    assert [e["tipo"] for e in ev][0] == "restantes" and ev[-1]["tipo"] == "fin"
    assert _texto(ev) == "RESPUESTA-DESDE-OPENAI"
    assert any(e["tipo"] == "fuentes" for e in ev)
    assert FakeAnthropic.ultima_llamada is None            # Anthropic no se llamó
    k = FakeOpenAI.ultima_llamada
    assert k["model"] == "gpt-6-luna" and k["stream"] is True and k["store"] is False
    assert "PULLEX IA" in k["instructions"] and "tools" not in k
    assert k["reasoning"] == {"effort": "medium"}
    assert k["input"][-1] == {"role": "user", "content": "hola"}
    assert modulo.ia_activa()["principal"]["modelo"] == "gpt-6-luna"


def test_openai_sin_clave_responde_503_y_estado_lo_indica(cliente, monkeypatch):
    _usar_openai(monkeypatch, clave=None)
    _, _, t = nuevo_usuario(cliente)
    assert cliente.get("/api/estado", headers=auth(t)).json()["api"] is False
    r = cliente.post("/api/chat", headers=auth(t), json={"conversacion": _conv(cliente, t), "mensaje": "hola"})
    assert r.status_code == 503
    assert FakeOpenAI.llamadas == 0


def test_openai_con_web_usa_los_mismos_dominios_oficiales_y_llena_fuentes(cliente, modulo, monkeypatch):
    _usar_openai(monkeypatch)
    ns = types.SimpleNamespace
    url = "https://www.corteconstitucional.gov.co/relatoria/2020/T-100-20.htm"
    otra = "https://www.suin-juriscol.gov.co/viewDocument.asp?id=1"
    FakeOpenAI.eventos_extra = [
        ns(type="response.web_search_call.in_progress"),
        ns(type="response.output_item.done", item=ns(type="web_search_call", action=ns(
            type="search", sources=[ns(type="url", url=url), ns(type="url", url=otra)]))),
        ns(type="response.output_text.annotation.added", annotation=ns(
            type="url_citation", url=url, title="T-100 de 2020", start_index=0, end_index=5)),
    ]
    _, _, t = nuevo_usuario(cliente)
    ev = _sse(cliente.post("/api/chat", headers=auth(t), json={"conversacion": _conv(cliente, t),
                                                               "mensaje": "tutela", "web": True}))
    k = FakeOpenAI.ultima_llamada
    h = k["tools"][0]
    assert h["type"] == "web_search" and h["filters"]["allowed_domains"] == modulo.herramienta_web()["allowed_domains"]
    assert k["include"] == ["web_search_call.action.sources"] and k["max_tool_calls"] == modulo.WEB_MAX_USOS
    assert any(e["tipo"] == "busqueda" for e in ev)
    fu = next(e for e in ev if e["tipo"] == "fuentes")["fuentes"]
    assert fu[0] == {"origen": "web", "titulo": "T-100 de 2020", "url": url, "oficial": True, "citado": True}
    assert fu[1]["url"] == otra and fu[1]["citado"] is False


def test_mensajes_con_adjuntos_se_traducen_a_la_responses_api():
    msgs = [{"role": "user", "content": "antes"}, {"role": "assistant", "content": "respuesta"},
            {"role": "user", "content": [
                {"type": "text", "text": "analiza"},
                {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": "QUJD"}},
                {"type": "document", "source": {"type": "base64", "media_type": "application/pdf", "data": "UERG"}}]}]
    out = proveedores.mensajes_openai(msgs)
    assert out[0] == {"role": "user", "content": "antes"} and out[1] == {"role": "assistant", "content": "respuesta"}
    assert out[2]["content"] == [
        {"type": "input_text", "text": "analiza"},
        {"type": "input_image", "detail": "auto", "image_url": "data:image/png;base64,QUJD"},
        {"type": "input_file", "filename": "documento.pdf", "file_data": "data:application/pdf;base64,UERG"}]


def test_llamar_json_con_openai(modulo, monkeypatch):
    _usar_openai(monkeypatch)
    FakeOpenAI.texto = "Aquí va: " + json.dumps(FakeAnthropic.CASO, ensure_ascii=False)
    caso = modulo.llamar_json("Crea un caso de Derecho Penal.", max_tokens=2500)
    assert caso["pregunta"] == FakeAnthropic.CASO["pregunta"]
    k = FakeOpenAI.ultima_llamada
    assert "stream" not in k and k["max_output_tokens"] == 2500 + modulo.MARGEN_THINKING
    assert k["instructions"] == modulo.MODULAR_SISTEMA


# ------------------------------------------------------------------------------- respaldo --
def test_respaldo_ante_saturacion_de_anthropic(cliente, monkeypatch, caplog):
    monkeypatch.setenv("PULLEX_RESPALDO", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-openai-prueba-no-real")

    def saturado(self, **k):
        raise _error_anthropic(anthropic.OverloadedError, 529)
    monkeypatch.setattr(FakeAnthropic, "_stream", saturado)
    email, _, t = nuevo_usuario(cliente)
    antes = cliente.get("/api/estado", headers=auth(t)).json()["perfil"]["usadas"]
    with caplog.at_level(logging.WARNING, logger="pullex.proveedores"):
        r = cliente.post("/api/chat", headers=auth(t), json={"conversacion": _conv(cliente, t),
                                                             "mensaje": "hola", "web": False})
    assert _texto(_sse(r)) == "RESPUESTA-DESDE-OPENAI" and FakeOpenAI.llamadas == 1
    assert cliente.get("/api/estado", headers=auth(t)).json()["perfil"]["usadas"] == antes + 1
    registros = [x.getMessage() for x in caplog.records if x.name == "pullex.proveedores"]
    assert any("respaldo de IA" in m and "OverloadedError" in m and "openai" in m for m in registros)
    assert not any(email in m or email.split("@")[0] in m for m in registros)   # sin datos personales


def test_sin_respaldo_ante_error_del_pedido(cliente, monkeypatch):
    """Un 400 no es saturación: no se intenta OpenAI y el usuario recibe el modo degradado sin cobro."""
    monkeypatch.setenv("PULLEX_RESPALDO", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-openai-prueba-no-real")

    def malo(self, **k):
        raise _error_anthropic(anthropic.BadRequestError, 400)
    monkeypatch.setattr(FakeAnthropic, "_stream", malo)
    _, _, t = nuevo_usuario(cliente)
    antes = cliente.get("/api/estado", headers=auth(t)).json()["perfil"]["usadas"]
    ev = _sse(cliente.post("/api/chat", headers=auth(t), json={"conversacion": _conv(cliente, t), "mensaje": "x"}))
    assert FakeOpenAI.llamadas == 0 and "no está disponible" in _texto(ev)
    assert cliente.get("/api/estado", headers=auth(t)).json()["perfil"]["usadas"] == antes


def test_respaldo_sin_clave_no_se_intenta(cliente, monkeypatch):
    monkeypatch.setenv("PULLEX_RESPALDO", "openai")   # sin OPENAI_API_KEY

    def caido(self, **k):
        raise _error_anthropic(anthropic.InternalServerError, 500)
    monkeypatch.setattr(FakeAnthropic, "_stream", caido)
    _, _, t = nuevo_usuario(cliente)
    ev = _sse(cliente.post("/api/chat", headers=auth(t), json={"conversacion": _conv(cliente, t), "mensaje": "x"}))
    assert FakeOpenAI.llamadas == 0 and "no está disponible" in _texto(ev)


def test_respaldo_en_llamar_json(modulo, monkeypatch):
    monkeypatch.setenv("PULLEX_RESPALDO", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-openai-prueba-no-real")

    def caido(self, **k):
        raise _error_anthropic(anthropic.InternalServerError, 503)
    monkeypatch.setattr(FakeAnthropic, "_create", caido)
    FakeOpenAI.texto = json.dumps(FakeAnthropic.CASO, ensure_ascii=False)
    assert modulo.llamar_json("Crea un caso de Derecho Civil.")["titulo"] == FakeAnthropic.CASO["titulo"]


def test_openai_principal_con_anthropic_de_respaldo(cliente, monkeypatch):
    _usar_openai(monkeypatch)
    monkeypatch.setenv("PULLEX_RESPALDO", "anthropic")
    req = httpx2.Request("POST", "https://api.openai.com/v1/responses")
    FakeOpenAI.error = openai.InternalServerError("simulado", response=httpx2.Response(500, request=req), body=None)
    _, _, t = nuevo_usuario(cliente)
    ev = _sse(cliente.post("/api/chat", headers=auth(t), json={"conversacion": _conv(cliente, t),
                                                               "mensaje": "MENSAJE-X", "web": False}))
    assert _texto(ev).startswith("ECO:") and "MENSAJE-X" in _texto(ev)   # respondió el doble de Anthropic


def test_no_se_mezclan_respuestas_si_el_principal_ya_emitio_texto():
    class Principal:
        nombre, configurado = "anthropic", True

        def stream(self, *a):
            yield {"tipo": "texto", "texto": "parcial"}
            raise _error_anthropic(anthropic.OverloadedError, 529)

    class Respaldo:
        nombre, configurado, usado = "openai", True, False

        def stream(self, *a):
            Respaldo.usado = True
            yield {"tipo": "texto", "texto": "otra"}

    recibidos = []
    with pytest.raises(proveedores.ErrorProveedor):
        for e in proveedores.stream_texto([Principal(), Respaldo()], "s", [], 10):
            recibidos.append(e)
    assert recibidos == [{"tipo": "texto", "texto": "parcial"}] and not Respaldo.usado


def test_evento_de_falla_de_openai_es_error_de_proveedor():
    ev = types.SimpleNamespace(type="response.failed", response=types.SimpleNamespace(
        error=types.SimpleNamespace(code="server_error", message="x")))
    with pytest.raises(proveedores.ErrorProveedor) as e:
        proveedores.evento_openai(ev, {"resultados": {}, "citas": {}})
    assert e.value.recuperable is True


def test_admin_ve_proveedor_y_modelo_activos(cliente, monkeypatch):
    monkeypatch.setenv("PULLEX_RESPALDO", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-openai-prueba-no-real")
    m = cliente.get("/api/admin/metricas", headers=auth(login_admin(cliente))).json()
    assert m["ia"]["principal"]["proveedor"] == "anthropic" and m["ia"]["principal"]["modelo"] == "claude-sonnet-5-5"
    assert m["ia"]["respaldo"] == {"proveedor": "openai", "nombre": "OpenAI (ChatGPT)", "modelo": "gpt-6.1-sol",
                                   "configurado": True}
    assert "sk-openai" not in json.dumps(m)                                  # nunca la clave
    assert cliente.get("/salud").json()["proveedor"] == "anthropic"
