"""Levanta PULLEX IA con un modelo SIMULADO (sin clave de API ni costo) para probar pantallas.

    cd pullex-ia && python demo/servidor_simulado.py      → http://localhost:8000

Usa el backend real (registro, cupos, base de datos, Modular Lab) pero reemplaza las llamadas
a Claude por respuestas de ejemplo tomadas de demo/datos_demo.json. La Biblioteca usa un catálogo
ficticio (demo/biblioteca_demo.json), no el inventario real del Drive. Útil para mostrar la app o
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
# Biblioteca de DEMOSTRACIÓN (demo/biblioteca_demo.json): catálogo ficticio servido por las rutas reales
# /api/biblioteca/*. Se monta ANTES de importar la aplicación para que su arranque no cargue el inventario real.
# Con PULLEX_BIBLIOTECA_INVENTARIO definido se respeta ese inventario (p. ej. biblioteca/inventario.json).
if "PULLEX_BIBLIOTECA_INVENTARIO" not in os.environ:
    sys.path.insert(0, str(RAIZ / "demo"))
    import biblioteca_demo  # noqa: E402
    biblioteca_demo.montar()
import app as pullex  # noqa: E402
import documentos  # noqa: E402
import fuentes  # noqa: E402
from perfiles.muestra_simulada import texto_simulado  # noqa: E402  — texto de ejemplo para los perfiles

# Textos de ejemplo del automatizador (Documentos, Flujos, Asistente), rotulados como demostración.
DOCS_DEMO = json.loads((RAIZ / "demo" / "documentos_demo.json").read_text(encoding="utf-8"))

# Corpus de DEMOSTRACIÓN (si no se indicó otro con PULLEX_CORPUS_DB): dos textos de ejemplo,
# rotulados como tales, para ver el motor de fuentes funcionando. No son texto normativo.
_CORPUS_DEMO = [
    ("Ejemplo de demostración - guía sobre la acción de tutela.txt", "05_DOCTRINA",
     "Texto de ejemplo de la demostración de PULLEX (no es texto normativo). La acción de tutela "
     "protege derechos fundamentales cuando son vulnerados o amenazados por una autoridad o, en "
     "ciertos casos, por particulares. Al estudiar su procedencia se revisan la legitimación, la "
     "subsidiariedad (que no exista otro medio de defensa eficaz) y la inmediatez (que se presente "
     "en un tiempo razonable). Verifica siempre la norma y la jurisprudencia en la fuente oficial."),
    ("Ejemplo de demostración - guía sobre el derecho de petición.txt", "05_DOCTRINA",
     "Texto de ejemplo de la demostración de PULLEX (no es texto normativo). El derecho de petición "
     "permite presentar solicitudes respetuosas a las autoridades y obtener una respuesta de fondo, "
     "clara y oportuna. Los plazos de respuesta dependen del tipo de petición; confírmalos en la ley "
     "vigente antes de calcular un término."),
]
if "PULLEX_CORPUS_DB" not in os.environ:
    os.environ["PULLEX_CORPUS_DB"] = str(RAIZ / "demo" / "corpus_demo.db")
    with fuentes.abrir(os.environ["PULLEX_CORPUS_DB"]) as _con:
        for _nombre, _carpeta, _texto in _CORPUS_DEMO:
            fuentes.indexar(_con, origen="demo:" + _nombre, nombre=_nombre, paginas=[("", _texto)],
                            carpeta=_carpeta, fecha_archivo="2026-01-15T00:00:00+00:00")


class _B:
    def __init__(self, t):
        self.type, self.text = "text", t


class _Ev:
    def __init__(self, t):
        self.type = "content_block_delta"
        self.delta = types.SimpleNamespace(type="text_delta", text=t)


# Búsqueda web SIMULADA (solo cuando el usuario tiene la búsqueda activada): un resultado y una cita
# con forma de evento del SDK, para ver el bloque «Fuentes consultadas». No es una búsqueda real.
_URL_DEMO = "https://www.corteconstitucional.gov.co/relatoria/"
_TITULO_DEMO = "Relatoría de la Corte Constitucional (resultado simulado de la demostración)"


def _eventos_web():
    ns = types.SimpleNamespace
    return [ns(type="content_block_start", content_block=ns(type="server_tool_use")),
            ns(type="content_block_start", content_block=ns(
                type="web_search_tool_result",
                content=[ns(type="web_search_result", url=_URL_DEMO, title=_TITULO_DEMO, page_age=None)]))]


def _evento_cita():
    ns = types.SimpleNamespace
    return ns(type="content_block_delta", delta=ns(type="citations_delta", citation=ns(
        type="web_search_result_location", url=_URL_DEMO, title=_TITULO_DEMO, cited_text="")))


def _trozos(texto, n=28):
    return [texto[i:i + n] for i in range(0, len(texto), n)]


class _Stream:
    def __init__(self, system, web=False):
        self.web = web
        sis = " ".join(b.get("text", "") for b in system)
        clave = next((k for k, v in {"conmigo": "RESUÉLVELO CONMIGO", "ensename": "ENSÉÑAME",
                                     "examiname": "EXAMÍNAME", "auditar": "AUDITA MI RESPUESTA"}.items()
                      if v in sis), "directo")
        self.texto = DATOS["chat"][clave]

    def __enter__(self):
        eventos = [_Ev(t) for t in _trozos(self.texto)]
        if self.web:
            eventos = _eventos_web() + eventos + [_evento_cita()]
        return iter(eventos)

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


def _documento_ejemplo(pedido: str) -> str:
    """Automatizador: texto de ejemplo para el tipo pedido (3 ejemplos completos y uno genérico)."""
    m = re.match(r"Redacta el borrador completo de este documento: (.+?)\.\n", pedido)
    tipo = next((t for t in documentos.CATALOGO if m and t["nombre"] == m.group(1)), None)
    if tipo and tipo["id"] in DOCS_DEMO["documentos"]:
        return DOCS_DEMO["documentos"][tipo["id"]]
    nombre = tipo["nombre"] if tipo else "el documento"
    secciones = "\n".join(f"{i}. {s}" for i, s in enumerate(tipo["estructura"] if tipo else [], 1))
    texto = DOCS_DEMO["generico"].replace("{nombre}", nombre).replace("{secciones}", secciones)
    return documentos.asegurar_rotulo(tipo, texto) if tipo else texto


def _paso_ejemplo(pedido: str) -> str:
    """Automatizador: resultado de ejemplo del paso n de un flujo (o genérico para el asistente)."""
    nombre = re.search(r"^FLUJO: (.+)$", pedido, re.M)
    paso = re.search(r"^PASO (\d+) DE \d+: (.+)$", pedido, re.M)
    n, titulo = (int(paso.group(1)), paso.group(2)) if paso else (1, "paso")
    flujo = next((f for f in documentos.FLUJOS if nombre and f["nombre"] == nombre.group(1)), None)
    textos = DOCS_DEMO["pasos"].get(flujo["id"]) if flujo else None
    if textos and n <= len(textos):
        return textos[n - 1]
    return DOCS_DEMO["paso_generico"].replace("{titulo}", titulo)


class _StreamTexto:
    def __init__(self, texto):
        self.texto = texto

    def __enter__(self):
        return iter([_Ev(t) for t in _trozos(self.texto, 40)])

    def __exit__(self, *a):
        return False


class _Modelo:
    def __init__(self, *a, **k):
        self.messages = types.SimpleNamespace(stream=self._stream, create=self._create)

    def _stream(self, model, max_tokens, system, messages, tools, **k):
        ultimo = messages[-1]["content"] if messages else ""
        ultimo = ultimo if isinstance(ultimo, str) else " ".join(b.get("text", "") for b in ultimo)
        sis = " ".join(b.get("text", "") for b in system) if isinstance(system, list) else str(system)
        if "PULLEX DOCUMENTOS" in sis:  # Automatizador: un paso de un flujo o del asistente
            return _StreamTexto(_paso_ejemplo(ultimo))
        s = _Stream(system, web=bool(tools))
        if ultimo.startswith("SOLICITUD DE REDACCIÓN"):  # Document Studio
            s.texto = DATOS["chat"]["escrito_peticion" if "PETICIÓN" in ultimo.split("\n")[0] else "escrito"]
        return s

    def _create(self, **k):
        pedido = k["messages"][0]["content"]
        sistema = k.get("system")
        sis = " ".join(b.get("text", "") for b in sistema) if isinstance(sistema, list) else str(sistema or "")
        if sis.startswith("PERFIL PULLEX "):   # coordinador de perfiles: salida con la forma del contrato
            return types.SimpleNamespace(content=[_B(texto_simulado(sis))])
        if sistema == documentos.SISTEMA_PLAN:
            return types.SimpleNamespace(content=[_B(json.dumps(DOCS_DEMO["plan"], ensure_ascii=False))])
        if "PULLEX DOCUMENTOS" in sis:
            return types.SimpleNamespace(content=[_B(_documento_ejemplo(pedido))])
        if "BIBLIOTECARIO" in sis:   # Biblioteca: explicación opcional de una recomendación (solo usa las fichas)
            ids = re.findall(r'"id": "(MOD-\d{6})"', pedido)
            return types.SimpleNamespace(content=[_B(json.dumps({"sin_modelo_adecuado": not ids, "candidatos": [
                {"id": i, "por_que": "Ejemplo de la demostración: explicación simulada a partir de la ficha del modelo.",
                 "requisitos_faltantes": ["Los datos que la ficha marca como faltantes."],
                 "adaptacion": ["Los hechos y el destinatario de tu caso."]} for i in ids[:3]],
                "nota": "Texto de ejemplo: con el modelo real, aquí va una explicación redactada para tu caso."}, ensure_ascii=False))])
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
