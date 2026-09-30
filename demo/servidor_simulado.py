"""Levanta PULLEX IA con un modelo SIMULADO (sin clave de API ni costo) para probar pantallas.

    cd pullex-ia && python demo/servidor_simulado.py      → http://localhost:8000

Usa el backend real (registro, cupos, base de datos, Modular Lab) pero reemplaza las llamadas
a Claude por respuestas de ejemplo tomadas de demo/datos_demo.json. Útil para mostrar la app o
probar la interfaz; NO sirve para evaluar la calidad jurídica del modelo.
"""
import json
import os
import re
import sys
import types
import unicodedata
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DATOS = json.loads((RAIZ / "demo" / "datos_demo.json").read_text(encoding="utf-8"))
os.chdir(RAIZ)
os.environ.setdefault("ANTHROPIC_API_KEY", "simulado")
os.environ.setdefault("PULLEX_ADMIN_EMAIL", "admin@demo.local")
os.environ.setdefault("PULLEX_ADMIN_CLAVE", "demo-admin-clave-larga")
os.environ.setdefault("PULLEX_SECRET", "solo-para-la-demo-local")
sys.path.insert(0, str(RAIZ))
import app as pullex  # noqa: E402


class _B:
    def __init__(self, t):
        self.type, self.text = "text", t


class _Ev:
    def __init__(self, t):
        self.type = "content_block_delta"
        self.delta = types.SimpleNamespace(text=t)


def _trozos(texto, n=28):
    return [texto[i:i + n] for i in range(0, len(texto), n)]


class _Stream:
    def __init__(self, system):
        sis = " ".join(b.get("text", "") for b in system)
        clave = next((k for k, v in {"conmigo": "RESUÉLVELO CONMIGO", "ensename": "ENSÉÑAME",
                                     "examiname": "EXAMÍNAME", "auditar": "AUDITA MI RESPUESTA"}.items()
                      if v in sis), "directo")
        self.texto = DATOS["chat"][clave]

    def __enter__(self):
        return iter(_Ev(t) for t in _trozos(self.texto))

    def __exit__(self, *a):
        return False


def _sin_tildes(texto) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", str(texto or "").lower())
                   if unicodedata.category(c) != "Mn")


# Todos los casos del banco de demostración (casos y variaciones), para reconocerlos por su título.
_TODOS = [(area, tipo, d) for area, par in DATOS["casos"].items() for tipo, d in par.items()]


def _caso_por_titulo(texto: str):
    """Devuelve (área, tipo, datos) del caso cuyo título aparece en el pedido, o None."""
    return next(((a, t, d) for a, t, d in _TODOS if d["titulo"] in texto), None)


# Si piden un área sin caso de demostración, se devuelve un aviso con forma de caso (el backend real
# exige un JSON de caso; así el usuario ve un mensaje claro en vez de un error genérico).
_SIN_CASO = {
    "titulo": "Área sin caso de demostración",
    "enunciado": ("El servidor simulado trae casos de Derecho " + ", ".join(list(DATOS["casos"])[:-1])
                  + " y " + list(DATOS["casos"])[-1] + ". Elige una de esas áreas para ver un caso completo; "
                  "con el modelo real se genera un caso nuevo de cualquier área."),
    "pregunta": "Vuelve a la configuración y elige una de las áreas disponibles en la demostración.",
    "pistas": [], "conceptos": [],
    "solucion": {"problema_juridico": "", "normas": [], "analisis": "", "contraargumento": "",
                 "conclusion": "", "errores_comunes": []}}


def _evaluar(pedido):
    """Evaluación simulada y genérica a partir de las `claves_evaluacion` del caso (misma lógica que demo/mock.js)."""
    antes, _, resto = pedido.partition("<respuesta_estudiante>")
    respuesta = resto.split("</respuesta_estudiante>")[0].strip()
    r = _sin_tildes(respuesta)
    encontrado = _caso_por_titulo(antes)
    k = (encontrado[2] if encontrado else {}).get("claves_evaluacion") or {}
    tiene = lambda ks: any(_sin_tildes(x) in r for x in (ks or []))
    p = {}
    for clave, _nombre, maximo in pullex.RUBRICA:
        if clave == "claridad":
            p[clave] = 9 if len(respuesta) > 250 else 7
            continue
        grupos = (k.get("rubrica_claves") or {}).get(clave) or []
        base = int(maximo * 0.4 + 0.5)
        aciertos = sum(1 for g in grupos if tiene(g))
        p[clave] = base + int((maximo - 1 - base) * aciertos / len(grupos) + 0.5) if grupos else base
    omitio = [o["texto"] for o in k.get("omisiones") or [] if not tiene(o["si_falta"])]
    return {"puntajes": p,
            "identificaste": [a["texto"] for a in k.get("aciertos") or [] if tiene(a["si_hay"])]
            or [k.get("acierto_base") or "Identificaste el tema general del caso."],
            "omitiste": omitio or ["Nada importante: cubriste los puntos principales."],
            "norma_faltante": [n["norma"] for n in k.get("normas_clave") or [] if not tiene(n["si_falta"])],
            "contraargumento": k.get("contraargumento", ""),
            "como_mejorar": k.get("como_mejorar") or [],
            "conceptos_debiles": [c["concepto"] for c in k.get("conceptos_clave") or [] if not tiene(c["si_falta"])],
            "comentario": (k.get("comentario_mejorar") or "Vas bien encaminado.") if len(omitio) > 1
            else (k.get("comentario_bien") or "Muy buena estructura.")}


def _caso_para(pedido: str) -> dict:
    """Elige el caso según el pedido: la variación sale del área del caso original (reconocido por su
    título); un caso nuevo, del área indicada en «Crea un caso de Derecho {área}»."""
    if "VARIACIÓN" in pedido:
        encontrado = _caso_por_titulo(pedido)
        return DATOS["casos"][encontrado[0]]["variacion"] if encontrado else _SIN_CASO
    m = re.search(r"Crea un caso de Derecho (\S+)", pedido)
    par = DATOS["casos"].get(m.group(1)) if m else None
    return par["caso"] if par else _SIN_CASO


class _Modelo:
    def __init__(self, *a, **k):
        self.messages = types.SimpleNamespace(stream=self._stream, create=self._create)

    def _stream(self, model, max_tokens, system, messages, tools):
        s = _Stream(system)
        ultimo = messages[-1]["content"] if messages else ""
        ultimo = ultimo if isinstance(ultimo, str) else " ".join(b.get("text", "") for b in ultimo)
        if ultimo.startswith("SOLICITUD DE REDACCIÓN"):  # Document Studio
            s.texto = DATOS["chat"]["escrito_peticion" if "PETICIÓN" in ultimo.split("\n")[0] else "escrito"]
        return s

    def _create(self, **k):
        pedido = k["messages"][0]["content"]
        if k.get("system") == pullex.MODULAR_SISTEMA:
            if pedido.startswith("Evalúa"):
                cuerpo = _evaluar(pedido)
            else:
                cuerpo = _caso_para(pedido)
            return types.SimpleNamespace(content=[_B(json.dumps(cuerpo, ensure_ascii=False))])
        return types.SimpleNamespace(content=[_B(
            "## Boletín de demostración\n\nEn la app real, aquí aparece el boletín jurídico del día, "
            "generado con búsqueda web en fuentes oficiales.")])


pullex.anthropic.Anthropic = _Modelo

if __name__ == "__main__":
    import uvicorn
    puerto = int(os.getenv("PORT", "8000"))
    print(f"\nPULLEX IA (modelo simulado) → http://localhost:{puerto}   admin: {os.environ['PULLEX_ADMIN_EMAIL']}\n")
    uvicorn.run(pullex.app, host="127.0.0.1", port=puerto)
