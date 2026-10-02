"""Arnés de pruebas de PULLEX IA.

app.py inicializa la base y la cuenta admin al importarse, con rutas relativas al directorio
actual. Por eso cada sesión de pruebas corre en un directorio temporal limpio (con un enlace a
static/) y con variables de entorno de prueba — nunca toca pullex.db ni app_secret.key reales.
El modelo de IA se reemplaza por un doble (FakeAnthropic): ninguna prueba llama a la API real.
"""
import importlib
import json
import os
import sys
import types
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent

ADMIN_EMAIL = "admin@pruebas.local"
ADMIN_CLAVE = "Clave-Admin-De-Prueba-9f3!"


class _Bloque:
    def __init__(self, texto):
        self.type = "text"
        self.text = texto


class _Evento:
    def __init__(self, texto):
        self.type = "content_block_delta"
        self.delta = types.SimpleNamespace(type="text_delta", text=texto)


class _Stream:
    """Devuelve como respuesta el historial que recibió el modelo. Así una prueba puede
    demostrar si mensajes de OTRO usuario llegaron al modelo (fuga entre usuarios)."""

    def __init__(self, messages, system, extra=None):
        self.messages = messages
        self.system = system
        self.extra = extra or {}

    def __enter__(self):
        FakeAnthropic.ultima_llamada = {"messages": self.messages, "system": self.system, **self.extra}
        partes = []
        for m in self.messages:
            c = m["content"]
            partes.append(c if isinstance(c, str) else json.dumps(c)[:200])
        # Una prueba puede inyectar eventos crudos del SDK (thinking, búsqueda web, citas).
        previos = list(FakeAnthropic.eventos_extra)
        return iter(previos + [_Evento("ECO:" + " || ".join(partes))] + list(FakeAnthropic.eventos_final))

    def __exit__(self, *a):
        return False


class FakeAnthropic:
    ultima_llamada = None
    eventos_extra = []   # eventos del SDK antes de la respuesta (p. ej. thinking, búsqueda web)
    eventos_final = []   # eventos después (p. ej. una cita)

    def __init__(self, *a, **k):
        self.messages = types.SimpleNamespace(stream=self._stream, create=self._create)

    # Automatizador: una prueba puede hacer fallar la llamada n-ésima a stream (1 = la primera desde que
    # se reinició el contador) o cualquier create del automatizador.
    n_stream = 0
    fallar_stream_en = None
    fallar_create = False
    PLAN = {"titulo": "Tarea de prueba", "pasos": [
        {"titulo": "Investigar", "instruccion": "Identifica normas aplicables."},
        {"titulo": "Analizar", "instruccion": "Analiza el caso con el resultado anterior."},
        {"titulo": "Redactar", "instruccion": "Redacta el borrador final."}]}
    DOCUMENTO = ("# ACCIÓN DE TUTELA\n\nSeñor juez [COMPLETAR: ciudad de reparto].\n\n## Hechos\n\n1. Hecho de prueba.\n\n"
                 "Firma\n\n" + "<<<VERIFICAR>>>" + "\n- Verificar la vigencia del Decreto 2591 de 1991\n- Número de cédula")
    llamadas_documento = []

    def _stream(self, model, max_tokens, system, messages, tools, **k):
        FakeAnthropic.n_stream += 1
        if FakeAnthropic.fallar_stream_en == FakeAnthropic.n_stream:
            raise RuntimeError("fallo simulado del proveedor")
        return _Stream(messages, system, {"model": model, "max_tokens": max_tokens, "tools": tools, **k})

    CASO = {"titulo": "La EPS que no entrega", "enunciado": "Hechos de prueba del caso.",
            "pregunta": "¿Procede la tutela?", "pistas": ["Piensa en la procedencia.", "Revisa la Ley 1751 de 2015."],
            "conceptos": ["subsidiariedad", "derecho a la salud"],
            "solucion": {"problema_juridico": "PJ", "normas": [{"norma": "Art. 86 C.P.", "para_que": "tutela"}],
                         "analisis": "A", "contraargumento": "C", "conclusion": "CONCLUSION-SECRETA",
                         "errores_comunes": ["confundir subsidiariedad con inmediatez"]}}
    EVAL = {"puntajes": {"problema": 18, "normas": 25, "argumentacion": 12, "aplicacion": 14,
                         "conclusion": 8, "claridad": 9},
            "identificaste": ["la procedencia"], "omitiste": ["inmediatez"], "norma_faltante": ["Ley 1751 de 2015"],
            "contraargumento": "Superintendencia de Salud", "como_mejorar": ["aplica cada requisito"],
            "conceptos_debiles": ["inmediatez"], "comentario": "Buen inicio."}
    llamadas_json = []

    def _create(self, **k):
        FakeAnthropic.ultima_create = k
        sistema = k.get("system") or ""
        if isinstance(sistema, list):
            sistema = " ".join(b.get("text", "") for b in sistema)
        if "PLANIFICADOR" in sistema or "PULLEX DOCUMENTOS" in sistema:
            if FakeAnthropic.fallar_create:
                raise RuntimeError("fallo simulado del proveedor")
            if "PLANIFICADOR" in sistema:
                return types.SimpleNamespace(content=[_Bloque(json.dumps(FakeAnthropic.PLAN, ensure_ascii=False))])
            FakeAnthropic.llamadas_documento.append(k["messages"][0]["content"])
            return types.SimpleNamespace(content=[_Bloque(FakeAnthropic.DOCUMENTO)])
        if isinstance(sistema, str) and "banco de casos" in sistema:
            pedido = k["messages"][0]["content"]
            FakeAnthropic.llamadas_json.append(pedido)
            if pedido.startswith("Evalúa"):
                cuerpo = dict(self.EVAL)
            elif "VARIACIÓN" in pedido:
                cuerpo = dict(self.CASO, cambio="¿Qué cambia si pasaron dos años?")
            else:
                cuerpo = dict(self.CASO)
            return types.SimpleNamespace(content=[_Bloque("Aquí va:\n" + json.dumps(cuerpo, ensure_ascii=False))])
        return types.SimpleNamespace(content=[_Bloque("Boletín de prueba")])


@pytest.fixture(scope="session")
def modulo(tmp_path_factory):
    trabajo = tmp_path_factory.mktemp("pullex")
    (trabajo / "static").symlink_to(RAIZ / "static")
    os.chdir(trabajo)
    os.environ.update({
        "ANTHROPIC_API_KEY": "sk-ant-prueba-no-real",
        "PULLEX_ADMIN_EMAIL": ADMIN_EMAIL,
        "PULLEX_ADMIN_CLAVE": ADMIN_CLAVE,
        "PULLEX_SECRET": "secreto-de-pruebas-no-usar-en-produccion",
        "RESEND_API_KEY": "",
        "PULLEX_APP_URL": "https://pullex.pruebas",
    })
    sys.path.insert(0, str(RAIZ))
    if "app" in sys.modules:
        del sys.modules["app"]
    m = importlib.import_module("app")
    m.anthropic.Anthropic = FakeAnthropic
    return m


@pytest.fixture(autouse=True)
def limpiar_limites(modulo):
    for nombre in ("_intentos", "_intentos_cuenta"):
        d = getattr(modulo, nombre, None)
        if isinstance(d, dict):
            d.clear()
    yield


@pytest.fixture
def cliente(modulo):
    from fastapi.testclient import TestClient
    return TestClient(modulo.app)


_contador = {"n": 0}


def nuevo_usuario(cliente, nombre="Estudiante Prueba", clave="clave-segura-123"):
    _contador["n"] += 1
    email = f"u{_contador['n']}_{os.getpid()}@pruebas.local"
    r = cliente.post("/api/registro", json={"email": email, "nombre": nombre, "clave": clave})
    assert r.status_code == 200, r.text
    return email, clave, r.json()["token"]


def auth(token):
    return {"Authorization": "Bearer " + token}


def login_admin(cliente):
    r = cliente.post("/api/login", json={"email": ADMIN_EMAIL, "clave": ADMIN_CLAVE})
    assert r.status_code == 200, r.text
    return r.json()["token"]


def chat(cliente, token, cid, mensaje="hola"):
    r = cliente.post("/api/chat", headers=auth(token),
                     json={"conversacion": cid, "mensaje": mensaje, "web": False})
    return r


class FakeOpenAI:
    """Doble del cliente oficial de OpenAI (Responses API). Ninguna prueba llama a la API real.
    Con stream=True devuelve eventos con la forma de la documentación (response.output_text.delta…);
    sin stream, un objeto con output_text. `error` hace fallar la llamada; `eventos_extra` agrega eventos
    (búsqueda web, citas) antes del texto."""
    ultima_llamada = None
    llamadas = 0
    texto = "RESPUESTA-DESDE-OPENAI"
    error = None
    eventos_extra = []

    def __init__(self, *a, **k):
        FakeOpenAI.api_key = k.get("api_key")
        self.responses = types.SimpleNamespace(create=self._create)

    @classmethod
    def reiniciar(cls):
        cls.ultima_llamada, cls.llamadas, cls.error = None, 0, None
        cls.texto, cls.eventos_extra = "RESPUESTA-DESDE-OPENAI", []

    def _create(self, **k):
        FakeOpenAI.ultima_llamada = k
        FakeOpenAI.llamadas += 1
        if FakeOpenAI.error is not None:
            raise FakeOpenAI.error
        ns = types.SimpleNamespace
        if k.get("stream"):
            t = FakeOpenAI.texto
            trozos = [ns(type="response.output_text.delta", delta=t[i:i + 7]) for i in range(0, len(t), 7)]
            return iter([ns(type="response.created")] + list(FakeOpenAI.eventos_extra) + trozos
                        + [ns(type="response.completed")])
        return ns(output_text=FakeOpenAI.texto)
