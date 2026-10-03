"""
Proveedores de IA de PULLEX (docs/15-PLANES-Y-PROVEEDORES.md).

Una interfaz común con dos operaciones, usada por el chat, el Modular Lab y el automatizador:

- ``stream(system, messages, max_tokens, tools, web)``: genera eventos ``{"tipo": "texto", "texto": …}``
  y ``{"tipo": "busqueda"}``; acumula en ``web`` los resultados (``web["resultados"]``) y las citas
  (``web["citas"]``) de la búsqueda web, que app.py convierte en el evento SSE ``fuentes``.
- ``crear_texto(system, user, max_tokens)``: una llamada sin streaming que devuelve solo el texto
  (la usan ``llamar_json`` y la generación de documentos).

Los argumentos llegan en el formato de Anthropic (bloques de sistema, mensajes con bloques de texto,
imagen o PDF en base64 y la herramienta ``web_search`` con ``allowed_domains``); OpenAIProveedor los
traduce a la Responses API.

Implementaciones:
- AnthropicProveedor (por defecto): Messages API, igual que antes de este módulo.
- OpenAIProveedor: SDK oficial ``openai`` (versión fijada en requirements.txt), Responses API con
  streaming. Documentación consultada el 1-oct-2026:
  https://developers.openai.com/api/docs/guides/streaming-responses (eventos response.output_text.delta)
  https://developers.openai.com/api/docs/guides/tools-web-search (web_search con filters.allowed_domains)
  NOT VERIFIED contra la API real: no hay clave de OpenAI en este entorno; solo se probó con un doble.

Respaldo: si el proveedor principal falla por error de servidor, saturación o red ANTES de emitir texto,
se intenta una vez el proveedor de respaldo (``PULLEX_RESPALDO``) y se deja constancia en el log sin
datos personales (solo proveedor, tipo de error y código HTTP).
"""
import os
import logging

import anthropic

log = logging.getLogger("pullex.proveedores")

NOMBRES = ("anthropic", "openai")
ETIQUETAS = {"anthropic": "Anthropic (Claude)", "openai": "OpenAI (ChatGPT)"}
# Modelo por defecto de OpenAI: gpt-6.1-sol, que según la página oficial de modelos equilibra capacidad
# y costo (2 USD/M de entrada y 10 USD/M de salida, el mismo rango de Sonnet 5.5). Cámbialo con
# PULLEX_OPENAI_MODELO (p. ej. gpt-6-luna para abaratar o gpt-6-astra para la máxima calidad).
OPENAI_MODELO_DEFECTO = "gpt-6.1-sol"
# Errores HTTP que justifican intentar el respaldo: saturación (429, 529) y fallas del servidor (5xx).
ESTADOS_RECUPERABLES = {408, 409, 429, 500, 502, 503, 504, 529}


class ErrorProveedor(Exception):
    """Falla de un proveedor de IA (la API respondió con error o no respondió).

    app.py la trata igual que ``anthropic.APIError``: modo degradado y reintegro de la consulta."""

    def __init__(self, proveedor: str, tipo: str, estado=None, recuperable: bool = False):
        super().__init__(f"{proveedor}: {tipo}" + (f" ({estado})" if estado else ""))
        self.proveedor, self.tipo, self.estado, self.recuperable = proveedor, tipo, estado, recuperable


def _openai():
    """Importación diferida: la app arranca aunque el paquete openai no esté instalado."""
    import openai
    return openai


def es_error_api(e: Exception) -> bool:
    if isinstance(e, (ErrorProveedor, anthropic.APIError)):
        return True
    try:
        return isinstance(e, _openai().APIError)
    except ImportError:
        return False


def es_recuperable(e: Exception) -> bool:
    """True si la falla es de servidor, saturación o red (vale la pena intentar el respaldo).
    Errores del pedido (400, clave inválida, contenido rechazado) NO activan el respaldo."""
    if isinstance(e, ErrorProveedor):
        return e.recuperable
    if isinstance(e, (anthropic.APIConnectionError, anthropic.APITimeoutError)):
        return True
    if isinstance(e, anthropic.APIStatusError):
        return getattr(e, "status_code", None) in ESTADOS_RECUPERABLES
    try:
        oa = _openai()
    except ImportError:
        return False
    if isinstance(e, (oa.APIConnectionError, oa.APITimeoutError)):
        return True
    if isinstance(e, oa.APIStatusError):
        return getattr(e, "status_code", None) in ESTADOS_RECUPERABLES
    return False


def _texto_sistema(system) -> str:
    if isinstance(system, list):
        return "\n\n".join(b.get("text", "") for b in system if isinstance(b, dict) and b.get("text"))
    return str(system or "")


# ------------------------------------------------------------------------------- Anthropic --
def evento_anthropic(evento, web: dict):
    """Traduce un evento del stream del SDK de Anthropic a un evento para el cliente (o None).

    - Solo se reenvían deltas de TEXTO: los bloques de thinking (thinking_delta, signature_delta)
      nunca llegan al cliente ni se guardan.
    - Resultados de búsqueda (web_search_tool_result) y citas (citations_delta con
      web_search_result_location) se acumulan en `web` para el evento final "fuentes"."""
    tipo = getattr(evento, "type", "")
    if tipo == "content_block_start":
        bloque = getattr(evento, "content_block", None)
        btipo = getattr(bloque, "type", "")
        if btipo == "server_tool_use":
            return {"tipo": "busqueda"}
        if btipo == "web_search_tool_result":
            contenido = getattr(bloque, "content", None)
            if isinstance(contenido, list):
                for r in contenido:
                    url = getattr(r, "url", None)
                    if url and url not in web["resultados"]:
                        web["resultados"][url] = {"titulo": getattr(r, "title", "") or url,
                                                  "fecha": getattr(r, "page_age", None)}
        return None
    if tipo == "content_block_delta":
        delta = getattr(evento, "delta", None)
        dtipo = getattr(delta, "type", "text_delta")
        if dtipo == "text_delta" and isinstance(getattr(delta, "text", None), str):
            return {"tipo": "texto", "texto": delta.text}
        if dtipo == "citations_delta":
            c = getattr(delta, "citation", None)
            if getattr(c, "type", "") == "web_search_result_location" and getattr(c, "url", None):
                web["citas"].setdefault(c.url, getattr(c, "title", None) or c.url)
        return None
    return None


class AnthropicProveedor:
    nombre = "anthropic"

    def __init__(self, api_key: str, modelo: str, opciones: dict = None):
        self.api_key, self.modelo, self.opciones = api_key, modelo, dict(opciones or {})

    @property
    def configurado(self) -> bool:
        return bool(self.api_key)

    def stream(self, system, messages, max_tokens, tools=None, web=None):
        web = web if web is not None else {"resultados": {}, "citas": {}}
        cliente = anthropic.Anthropic(api_key=self.api_key)
        with cliente.messages.stream(model=self.modelo, max_tokens=max_tokens, system=system,
                                     messages=messages, tools=list(tools or []), **self.opciones) as s:
            for evento in s:
                salida = evento_anthropic(evento, web)
                if salida is not None:
                    yield salida

    def crear_texto(self, system, user: str, max_tokens: int) -> str:
        cliente = anthropic.Anthropic(api_key=self.api_key)
        r = cliente.messages.create(model=self.modelo, max_tokens=max_tokens, system=system,
                                    messages=[{"role": "user", "content": user}], **self.opciones)
        return "".join(b.text for b in r.content if getattr(b, "type", "") == "text")


# ---------------------------------------------------------------------------------- OpenAI --
def _contenido_openai(contenido, rol: str):
    """Mensaje en formato Anthropic → contenido de la Responses API (texto, imagen o PDF)."""
    if isinstance(contenido, str):
        return contenido
    partes = []
    for b in contenido or []:
        tipo = b.get("type") if isinstance(b, dict) else None
        src = (b.get("source") or {}) if isinstance(b, dict) else {}
        if tipo == "text":
            partes.append({"type": "input_text" if rol == "user" else "output_text", "text": b.get("text", "")})
        elif tipo == "image" and src.get("type") == "base64":
            partes.append({"type": "input_image", "detail": "auto",
                           "image_url": f"data:{src.get('media_type', 'image/png')};base64,{src.get('data', '')}"})
        elif tipo == "document" and src.get("type") == "base64":
            partes.append({"type": "input_file", "filename": "documento.pdf",
                           "file_data": f"data:{src.get('media_type', 'application/pdf')};base64,{src.get('data', '')}"})
    if rol != "user":  # el historial del asistente siempre se guarda como texto
        return "".join(p.get("text", "") for p in partes)
    return partes


def mensajes_openai(messages: list) -> list:
    return [{"role": m["role"], "content": _contenido_openai(m["content"], m["role"])} for m in messages]


def herramientas_openai(tools) -> tuple:
    """Herramienta web_search de Anthropic → web_search de OpenAI con el mismo filtro de dominios.
    Devuelve (tools, max_tool_calls). Formato de filters.allowed_domains confirmado en la guía oficial
    (dominios sin esquema, subdominios incluidos, hasta 100)."""
    salida, maximo = [], None
    for t in tools or []:
        if not str(t.get("type", "")).startswith("web_search"):
            continue
        h = {"type": "web_search", "user_location": {"type": "approximate", "country": "CO"}}
        if t.get("allowed_domains"):
            h["filters"] = {"allowed_domains": list(t["allowed_domains"])[:100]}
        salida.append(h)
        maximo = t.get("max_uses") or maximo
    return salida, maximo


def _campo(obj, nombre, defecto=None):
    if isinstance(obj, dict):
        return obj.get(nombre, defecto)
    return getattr(obj, nombre, defecto)


def evento_openai(evento, web: dict):
    """Traduce un evento de streaming de la Responses API (o None). Solo texto de salida: el
    razonamiento del modelo nunca llega al cliente."""
    tipo = _campo(evento, "type", "")
    if tipo == "response.output_text.delta":
        delta = _campo(evento, "delta")
        return {"tipo": "texto", "texto": delta} if isinstance(delta, str) else None
    if tipo == "response.web_search_call.in_progress":
        return {"tipo": "busqueda"}
    if tipo == "response.output_text.annotation.added":
        a = _campo(evento, "annotation")
        if _campo(a, "type") == "url_citation" and _campo(a, "url"):
            web["citas"].setdefault(_campo(a, "url"), _campo(a, "title") or _campo(a, "url"))
        return None
    if tipo == "response.output_item.done":
        item = _campo(evento, "item")
        if _campo(item, "type") == "web_search_call":
            for s in _campo(_campo(item, "action"), "sources") or []:
                url = _campo(s, "url")
                if url and url not in web["resultados"]:
                    web["resultados"][url] = {"titulo": url, "fecha": None}
        return None
    if tipo in ("response.failed", "error"):
        err = _campo(_campo(evento, "response"), "error") if tipo == "response.failed" else evento
        codigo = str(_campo(err, "code") or "desconocido")
        raise ErrorProveedor("openai", "evento " + tipo, codigo,
                             recuperable=codigo in ("server_error", "rate_limit_exceeded"))
    return None


class OpenAIProveedor:
    nombre = "openai"

    def __init__(self, api_key: str, modelo: str = OPENAI_MODELO_DEFECTO, esfuerzo: str = ""):
        self.api_key, self.modelo, self.esfuerzo = api_key, modelo or OPENAI_MODELO_DEFECTO, esfuerzo

    @property
    def configurado(self) -> bool:
        return bool(self.api_key)

    def _base(self, system, max_tokens) -> dict:
        # store=False: las conversaciones no quedan guardadas en OpenAI (datos personales, Ley 1581).
        k = {"model": self.modelo, "instructions": _texto_sistema(system), "max_output_tokens": max_tokens,
             "store": False}
        if self.esfuerzo:
            k["reasoning"] = {"effort": self.esfuerzo}
        return k

    def stream(self, system, messages, max_tokens, tools=None, web=None):
        web = web if web is not None else {"resultados": {}, "citas": {}}
        cliente = _openai().OpenAI(api_key=self.api_key)
        k = self._base(system, max_tokens)
        herramientas, maximo = herramientas_openai(tools)
        if herramientas:
            k["tools"] = herramientas
            k["include"] = ["web_search_call.action.sources"]
            if maximo:
                k["max_tool_calls"] = int(maximo)
        for evento in cliente.responses.create(input=mensajes_openai(messages), stream=True, **k):
            salida = evento_openai(evento, web)
            if salida is not None:
                yield salida

    def crear_texto(self, system, user: str, max_tokens: int) -> str:
        cliente = _openai().OpenAI(api_key=self.api_key)
        r = cliente.responses.create(input=[{"role": "user", "content": user}], **self._base(system, max_tokens))
        return getattr(r, "output_text", "") or ""


# ------------------------------------------------------------------ configuración y respaldo --
def _nombre(valor: str, defecto: str = "") -> str:
    v = (valor or "").strip().lower()
    return v if v in NOMBRES else defecto


def ajustes() -> dict:
    """Configuración leída del entorno en cada llamada (así se puede cambiar sin tocar el código)."""
    principal = _nombre(os.getenv("PULLEX_PROVEEDOR", "anthropic"), "anthropic")
    respaldo = _nombre(os.getenv("PULLEX_RESPALDO", ""))
    return {"proveedor": principal, "respaldo": respaldo if respaldo != principal else "",
            "openai_modelo": os.getenv("PULLEX_OPENAI_MODELO", "").strip() or OPENAI_MODELO_DEFECTO,
            "openai_esfuerzo": os.getenv("PULLEX_OPENAI_ESFUERZO", "medium").strip().lower(),
            "openai_key": os.getenv("OPENAI_API_KEY", "")}


def _registrar_respaldo(principal, respaldo, e: Exception):
    estado = getattr(e, "estado", None) or getattr(e, "status_code", None)
    log.warning("respaldo de IA: %s falló (tipo=%s estado=%s); se intenta una vez con %s",
                principal.nombre, type(e).__name__, estado, respaldo.nombre)


def stream_texto(cadena: list, system, messages, max_tokens, tools=None, web=None):
    """Stream con respaldo. `cadena` = [principal] o [principal, respaldo]. El respaldo solo se usa si
    la falla es recuperable y el principal todavía no había emitido texto (nunca se mezclan dos
    respuestas). Un error de API que no se recupera sale como ErrorProveedor."""
    web = web if web is not None else {"resultados": {}, "citas": {}}
    principal, respaldo = cadena[0], (cadena[1] if len(cadena) > 1 else None)
    emitido = False
    try:
        for ev in principal.stream(system, messages, max_tokens, tools, web):
            emitido = emitido or ev.get("tipo") == "texto"
            yield ev
        return
    except Exception as e:
        if emitido or respaldo is None or not respaldo.configurado or not es_recuperable(e):
            if es_error_api(e) and not isinstance(e, ErrorProveedor):
                raise ErrorProveedor(principal.nombre, type(e).__name__, getattr(e, "status_code", None),
                                     es_recuperable(e)) from e
            raise
        _registrar_respaldo(principal, respaldo, e)
    web["resultados"].clear()
    web["citas"].clear()
    try:
        yield from respaldo.stream(system, messages, max_tokens, tools, web)
    except Exception as e:
        if es_error_api(e) and not isinstance(e, ErrorProveedor):
            raise ErrorProveedor(respaldo.nombre, type(e).__name__, getattr(e, "status_code", None)) from e
        raise


def crear_texto(cadena: list, system, user: str, max_tokens: int) -> str:
    """Llamada sin streaming con el mismo respaldo que stream_texto."""
    principal, respaldo = cadena[0], (cadena[1] if len(cadena) > 1 else None)
    try:
        return principal.crear_texto(system, user, max_tokens)
    except Exception as e:
        if respaldo is None or not respaldo.configurado or not es_recuperable(e):
            raise
        _registrar_respaldo(principal, respaldo, e)
    return respaldo.crear_texto(system, user, max_tokens)
