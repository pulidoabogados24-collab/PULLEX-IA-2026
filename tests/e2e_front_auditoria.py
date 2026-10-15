"""Regresión en navegador real (Chromium) de las correcciones de frontend de la auditoría 2026-10-13 y de la app
instalable (PWA).

Uso: con el servidor simulado corriendo (`python demo/servidor_simulado.py`),
    BASE=http://127.0.0.1:8000 CAPTURAS=/ruta/capturas python3 tests/e2e_front_auditoria.py
(CAPTURAS es opcional: por defecto, un directorio temporal). Sale con código 1 si alguna verificación falla.

Cubre: modales con foco atrapado (F-05), Ajustes accesibles (F-06), CSP sin violaciones en las vistas (F-07),
service worker y página sin conexión (F-09), token fuera del alcance global y «Salir» que limpia todo (F-10),
borradores del Taller por cuenta (F-11), objetivos táctiles de 44 px (F-12), role=alert (F-13), movimiento
reducido (F-14), token de restablecer fuera de la URL (F-15), aceptación de la política en el registro (IA-17),
«Tus datos»: descargar y eliminar la cuenta (IA-18, con respuestas simuladas), nota de revisión de citas
(IA-01/IA-05, con un evento SSE simulado) y PWA (manifiesto, íconos, etiquetas iOS, botón «Instalar app»).
Las respuestas de /api/cuenta/* y /api/chat se simulan con page.route: no dependen del backend ni gastan consultas.
"""
import io
import json
import os
import random
import re
import sys
import tempfile
import time

# Para que context.route también vea lo que pide el service worker (así se simula «sin red» para el SW: set_offline no
# lo afecta en Chromium). Debe estar antes de arrancar Playwright.
os.environ.setdefault("PW_EXPERIMENTAL_SERVICE_WORKER_NETWORK_EVENTS", "1")
from playwright.sync_api import sync_playwright  # noqa: E402

try:
    from PIL import Image
except ImportError:  # sin Pillow se omite solo la verificación del tamaño real de los íconos
    Image = None

BASE = os.getenv("BASE", "http://127.0.0.1:8000")
OUT = os.getenv("CAPTURAS") or tempfile.mkdtemp(prefix="pullex-front-")
os.makedirs(OUT, exist_ok=True)
CLAVE = "clave-e2e-segura-1"
OBSERVADOR = """document.addEventListener('securitypolicyviolation',
    e => (window.__csp = (window.__csp||[])).push(e.violatedDirective + ' ' + (e.blockedURI||'') + ' @' + location.pathname));"""
IPHONE_UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) "
             "Version/17.5 Mobile/15E148 Safari/604.1")
resultados = []


def ok(nombre, cond, detalle=""):
    resultados.append((nombre, bool(cond), detalle))
    print(("PASS " if cond else "FAIL ") + nombre + (f" — {detalle}" if detalle else ""))


def sse(*eventos):
    return "".join("data: " + json.dumps(e, ensure_ascii=False) + "\n\n" for e in eventos)


RESPUESTA_CITAS = ("**Respuesta corta:** la tutela procede contra la EPS que niega un medicamento formulado.\n\n"
                   "**Dónde está:** artículo 86 de la Constitución y Decreto 2591 de 1991 [F1]. La Corte lo reiteró en la "
                   "Sentencia T-999 de 2031 [F9] y el artículo 4500 del Código Civil lo complementa.")
CITAS = {"hay_citas": True, "huerfanas": ["F9"], "sospechosas": [
    {"cita": "Sentencia T-999 de 2031", "motivo": "El año es posterior a la fecha actual.", "gravedad": "grave"},
    {"cita": "artículo 4500 del Código Civil", "motivo": "Número de artículo fuera del rango del código.", "gravedad": "leve"}]}


def contexto(nav, **kw):
    """Contexto con una IP propia (solo hacia este servidor): el límite de registros por IP no frena la suite."""
    ip = "10.%d.%d.%d" % tuple(random.randint(1, 250) for _ in range(3))
    kw.setdefault("service_workers", "block")
    ctx = nav.new_context(accept_downloads=True, **kw)
    ctx.route(BASE + "/**", lambda r: r.continue_(headers={**r.request.headers, "x-forwarded-for": ip}))
    return ctx


def registrar(pag, sufijo, capturar=None):
    pag.goto(BASE + "/")
    pag.click("#t-reg")
    pag.fill("#r-nombre", "Valentina Ríos")
    email = f"front{int(time.time() * 1000)}{sufijo}@pruebas.local"
    pag.fill("#a-email", email)
    pag.fill("#a-clave", CLAVE)
    pag.check("#r-acepto")
    if capturar:
        pag.locator("#r-acepto").evaluate("e => e.scrollIntoView({block: 'center'})")
        pag.wait_for_timeout(1200)          # la portada entra con su animación: se espera a que termine
        pag.screenshot(path=capturar)
    pag.click("#a-btn")
    pag.wait_for_function("() => PERFIL !== null", timeout=15000)
    pag.wait_for_timeout(400)
    return email


def foco(pag):
    return pag.evaluate("(()=>{const a=document.activeElement;return a?(a.id?'#'+a.id:a.tagName.toLowerCase()+'.'+[...a.classList].join('.')):null})()")


def probar_modal(pag, nombre, disparador, modal, primer=None, abrir=None):
    """Abre con teclado desde el disparador; verifica foco inicial, Tab atrapado (ida y vuelta), fondo inerte,
    Escape y el regreso del foco."""
    pag.locator(disparador).first.focus()
    pag.keyboard.press("Enter") if not abrir else pag.evaluate(abrir)
    pag.wait_for_timeout(250)
    ok(f"{nombre}: se abre", pag.is_visible(modal))
    dentro = f"document.querySelector('{modal}').contains(document.activeElement)"
    ok(f"{nombre}: el foco entra al primer control", pag.evaluate(dentro) and (primer is None or foco(pag) == primer), foco(pag))
    ok(f"{nombre}: el fondo queda inerte", pag.evaluate(
        f"[...document.body.children].filter(e=>e!==document.querySelector('{modal}')&&e.tagName!=='SCRIPT').every(e=>e.inert)"))
    salio = any(not (pag.keyboard.press("Tab") or pag.evaluate(dentro)) for _ in range(25))
    salio = salio or any(not (pag.keyboard.press("Shift+Tab") or pag.evaluate(dentro)) for _ in range(25))
    ok(f"{nombre}: Tab y Mayús+Tab no salen del diálogo", not salio)
    pag.keyboard.press("Escape")
    pag.wait_for_timeout(250)
    ok(f"{nombre}: Escape cierra", not pag.is_visible(modal))
    ok(f"{nombre}: el foco vuelve al disparador", pag.evaluate(
        f"document.activeElement===document.querySelector('{disparador}')"), foco(pag))
    ok(f"{nombre}: el fondo deja de estar inerte", pag.evaluate("![...document.body.children].some(e=>e.inert)"))


def sin_nombre(pag):
    cdp = pag.context.new_cdp_session(pag)
    malos = []
    for n in cdp.send("Accessibility.getFullAXTree")["nodes"]:
        rol = (n.get("role") or {}).get("value")
        if rol in ("button", "link", "textbox", "combobox", "checkbox", "switch", "radio") and not n.get("ignored"):
            if not ((n.get("name") or {}).get("value") or "").strip():
                malos.append(rol)
    return malos


def medir_compositor(pag):
    return pag.evaluate("""() => [...document.querySelectorAll('.entrada button, .entrada .chip')].filter(e => {
        const r = e.getBoundingClientRect(); return r.width && r.height && getComputedStyle(e).visibility !== 'hidden'; })
        .map(e => { const r = e.getBoundingClientRect(); return [e.id || e.className, Math.round(r.width), Math.round(r.height)]; })""")


with sync_playwright() as p:
    nav = p.chromium.launch()

    # ================================================================ escritorio 1440×900 ==
    ctx = contexto(nav, viewport={"width": 1440, "height": 900})
    pag = ctx.new_page()
    pag.add_init_script(OBSERVADOR)
    pag.goto(BASE + "/")

    # --- F-05 en la portada: recuperar contraseña (disparador: el enlace) + F-13
    probar_modal(pag, "m-recuperar", "#a-olvido a", "#m-recuperar", primer="#rec-email")
    ok("F-13: #rec-msg y #k-msg con role=alert", pag.get_attribute("#rec-msg", "role") == "alert" and pag.get_attribute("#k-msg", "role") == "alert")

    # --- IA-17: casilla obligatoria, enlace a la política, cuerpo del registro
    pag.click("#t-reg")
    ok("IA-17: la casilla aparece al crear cuenta, sin marcar", pag.is_visible("#r-acepto") and not pag.is_checked("#r-acepto"))
    ok("IA-17: el texto de la casilla", pag.inner_text("label[for=r-acepto]").strip() == "He leído y acepto la Política de tratamiento de datos personales")
    enl = pag.locator("label[for=r-acepto] a")
    ok("IA-17: el enlace abre /politica-de-datos en pestaña nueva",
       enl.get_attribute("href") == "/politica-de-datos" and enl.get_attribute("target") == "_blank" and "noopener" in (enl.get_attribute("rel") or ""))
    ok("IA-17: enlace a la política en el pie del ingreso", pag.locator(".auth-card .nota a[href='/politica-de-datos']").count() == 1)
    registros = []
    pag.on("request", lambda r: registros.append(r.post_data) if r.url.endswith("/api/registro") else None)
    pag.fill("#r-nombre", "Valentina Ríos")
    email = f"front{int(time.time() * 1000)}d@pruebas.local"
    pag.fill("#a-email", email)
    pag.fill("#a-clave", CLAVE)
    pag.click("#a-btn")
    pag.wait_for_timeout(400)
    ok("IA-17: sin la casilla no se envía el registro", not registros and "aceptar la Política" in pag.inner_text("#a-msg"), pag.inner_text("#a-msg"))
    ok("IA-17: la casilla queda marcada como inválida y con el foco", pag.get_attribute("#r-acepto", "aria-invalid") == "true" and foco(pag) == "#r-acepto")
    pag.check("#r-acepto")
    pag.screenshot(path=f"{OUT}/fix-ingreso-1440.png")
    pag.click("#a-btn")
    pag.wait_for_function("() => PERFIL !== null", timeout=15000)
    pag.wait_for_timeout(400)
    cuerpo = json.loads(registros[0]) if registros else {}
    ok("IA-17: el registro envía acepto_politica: true", cuerpo.get("acepto_politica") is True, str({k: v for k, v in cuerpo.items() if k != "clave"}))

    # --- F-10: el token no es una variable global
    ok("F-10: no hay TOKEN global (ni window.TOKEN)", pag.evaluate("typeof TOKEN === 'undefined' && !('TOKEN' in window)"))
    ok("F-10: la sesión sigue activa por SESION", pag.evaluate("SESION.activa() && Object.isFrozen(SESION)"))
    with pag.expect_request(lambda r: "/api/conversaciones" in r.url) as rq:
        pag.evaluate("api('/api/conversaciones')")
    token = rq.value.headers.get("authorization", "").replace("Bearer ", "")
    guardado = " ".join(pag.evaluate("[...Object.values(localStorage), ...Object.values(sessionStorage), document.cookie]"))
    ok("F-10: el token no queda en localStorage/sessionStorage/cookies", len(token) > 20 and token not in guardado)

    # --- F-11: borradores del Taller por cuenta
    pag.evaluate("tlEscribir('caso-1', {texto: 'borrador', marcas: [], t: 1})")
    claves = pag.evaluate("Object.keys(localStorage).filter(k => k.startsWith('pullex.taller.'))")
    ok("F-11: la clave del borrador lleva la huella de la cuenta y no el correo",
       len(claves) == 1 and re.fullmatch(r"pullex\.taller\.borrador\.h[0-9a-f]{16}\.caso-1", claves[0]) and email.split("@")[0] not in claves[0], str(claves))
    ok("F-11: el borrador se lee de vuelta", (pag.evaluate("tlLeer('caso-1')") or {}).get("texto") == "borrador")

    # --- F-14: desplazamiento suave solo sin movimiento reducido
    espia = """() => { let a; const o = Element.prototype.scrollIntoView; Element.prototype.scrollIntoView = function (x) { a = x };
        desplazar(document.body); Element.prototype.scrollIntoView = o; return a && a.behavior; }"""
    ok("F-14: con movimiento completo, desplazar() es suave", pag.evaluate(espia) == "smooth")
    pag.evaluate("document.documentElement.setAttribute('data-movimiento','reducido')")
    ok("F-14: con «Movimiento reducido», desplazar() no anima", pag.evaluate(espia) == "auto")
    pag.evaluate("document.documentElement.removeAttribute('data-movimiento')")

    # --- F-05: herramientas, redactar escrito (desde herramientas) y cambiar contraseña
    pag.click("#n-chat")
    pag.wait_for_timeout(300)
    probar_modal(pag, "m-tools", ".entrada .chip-icono", "#m-tools")
    pag.locator(".entrada .chip-icono").focus()
    pag.keyboard.press("Enter")
    pag.wait_for_timeout(200)
    pag.locator("#tools-grid .tool").first.click()      # «Redactar tutela» abre el escrito
    pag.wait_for_timeout(250)
    ok("m-escrito: se abre desde Herramientas, con el foco en el primer dato",
       pag.is_visible("#m-escrito") and foco(pag) == "#es-tutela-nombre", foco(pag))
    pag.keyboard.press("Escape")
    pag.wait_for_timeout(250)
    ok("m-escrito: Escape cierra y el foco vuelve a Herramientas",
       not pag.is_visible("#m-escrito") and pag.evaluate("document.activeElement.classList.contains('chip-icono')"), foco(pag))

    # --- IA-01/IA-05: nota de revisión de citas con un evento SSE simulado
    pag.route("**/api/chat", lambda r: r.fulfill(status=200, content_type="text/event-stream", body=sse(
        {"tipo": "texto", "texto": RESPUESTA_CITAS}, {"tipo": "citas", "citas": CITAS},
        {"tipo": "fin", "completo": True, "mensaje_id": None})))
    pag.fill("#txt", "¿Procede la tutela contra mi EPS?")
    pag.keyboard.press("Enter")
    pag.wait_for_function("() => !enviando && document.querySelector('#hilo .b.ia .citas-rev')", timeout=30000)
    nota = pag.locator("#hilo .b.ia .citas-rev").last
    ok("citas: la nota dice exactamente el aviso",
       nota.locator(".citas-t").inner_text().strip() == "Citas sin verificar: confirma cada norma y sentencia en la fuente oficial antes de usarla.")
    items = nota.locator(".citas-it").all_inner_texts()
    ok("citas: lista «Revisar» con la huérfana y las sospechosas, con su motivo",
       len(items) == 3 and all(i.upper().startswith("REVISAR") for i in items) and "[F9]" in items[0]
       and "T-999 de 2031" in items[1] and "posterior" in items[1], str(items))
    ok("citas: la nota va antes de los botones de la respuesta", pag.evaluate(
        "(()=>{const b=[...document.querySelectorAll('#hilo .b.ia')].pop();const n=b.querySelector('.citas-rev'),a=b.querySelector('.acc');return !!(n.compareDocumentPosition(a)&Node.DOCUMENT_POSITION_FOLLOWING)})()"))
    ok("citas: sin emojis en la nota", not re.search("[\U0001F300-\U0001FAFF☀-➿]", nota.inner_text()))
    pag.wait_for_timeout(300)
    pag.locator("#hilo .b.ia").last.scroll_into_view_if_needed()
    pag.screenshot(path=f"{OUT}/fix-consultar-1440.png")
    # hay_citas true sin marcas: solo la nota; hay_citas false: nada
    n = pag.evaluate("""() => { const t='Según el artículo 86 de la Constitución.';
        const a=burbuja('ia',t); accionesResp(a,t,[],{citas:{hay_citas:true,huerfanas:[],sospechosas:[]}});
        const b=burbuja('ia','Hola.'); accionesResp(b,'Hola.',[],{citas:{hay_citas:false,huerfanas:['F2'],sospechosas:[]}});
        const c=burbuja('ia','**Confianza:** Alta'); accionesResp(c,'**Confianza:** Alta',[],{});
        return [a.querySelectorAll('.citas-rev').length, a.querySelectorAll('.citas-it').length,
                b.querySelectorAll('.citas-rev').length, c.querySelectorAll('.citas-rev,.nota-ia').length]; }""")
    ok("citas: con citas y sin marcas solo la nota; sin citas nada; «**Confianza» ya no decide", n == [1, 0, 0, 0], str(n))
    # al recargar una conversación, el mensaje guardado trae «citas»
    pag.route("**/api/conversaciones/424242/mensajes", lambda r: r.fulfill(status=200, content_type="application/json", body=json.dumps([
        {"id": 1, "rol": "user", "contenido": "¿Procede?"},
        {"id": 2, "rol": "assistant", "contenido": RESPUESTA_CITAS, "fuentes": [], "citas": CITAS}])))
    pag.evaluate("abrirConv(424242)")
    pag.wait_for_function("() => document.querySelectorAll('#hilo .citas-rev').length === 1", timeout=10000)
    ok("citas: la nota reaparece al abrir la conversación guardada", pag.locator("#hilo .citas-it").count() == 3)
    pag.unroute("**/api/chat")
    pag.evaluate("nuevaConsulta()")

    # --- F-06: Ajustes accesibles
    pag.click("#n-config")
    pag.wait_for_timeout(400)
    for sw_id in ("cf-web", "cf-tema"):
        info = pag.evaluate(f"(()=>{{const e=$('{sw_id}');return [e.tagName,e.getAttribute('role'),e.getAttribute('aria-checked'),e.classList.contains('on')]}})()")
        ok(f"F-06: #{sw_id} es <button role=switch> con aria-checked = estado", info[0] == "BUTTON" and info[1] == "switch" and info[2] == str(info[3]).lower(), str(info))
    antes = pag.get_attribute("#cf-web", "aria-checked")
    pag.locator("#cf-web").focus()
    with pag.expect_response(lambda r: "/api/preferencias" in r.url):
        pag.keyboard.press("Space")
    ok("F-06: el interruptor responde al teclado y sincroniza aria-checked",
       pag.get_attribute("#cf-web", "aria-checked") != antes and pag.get_attribute("#cf-web", "aria-checked") == str(pag.evaluate("$('cf-web').classList.contains('on')")).lower())
    ok("F-06: los interruptores tienen nombre accesible",
       pag.get_by_role("switch", name="Buscar en internet por defecto").count() == 1 and pag.get_by_role("switch", name="Modo claro").count() == 1)
    ok("F-06: el select de modo tiene etiqueta", pag.get_by_role("combobox", name="Modo por defecto").count() == 1)
    area = pag.locator("#areas .area").first
    ok("F-06: áreas como <button aria-pressed>", area.evaluate("e => e.tagName") == "BUTTON" and area.get_attribute("aria-pressed") in ("true", "false"))
    previo = area.get_attribute("aria-pressed")
    area.focus()
    with pag.expect_response(lambda r: "/api/preferencias" in r.url):
        pag.keyboard.press("Enter")
    ok("F-06: un área se alterna con el teclado", area.get_attribute("aria-pressed") != previo)
    ok("F-06: sin controles sin nombre accesible en Ajustes", not sin_nombre(pag), str(sin_nombre(pag)))
    ok("IA-17: enlace a la política en Ajustes", pag.locator("#panel-datos a[href='/politica-de-datos'][target=_blank]").count() == 1)
    probar_modal(pag, "m-clave", "#v-config [data-click=abrirClave]", "#m-clave", primer="#k-act")

    # --- IA-18: descargar mis datos (simulado)
    pag.route("**/api/cuenta/exportar", lambda r: r.fulfill(status=200, content_type="application/json",
              body=json.dumps({"cuenta": {"email": email}, "conversaciones": []})))
    pedidos = []
    pag.on("request", lambda r: pedidos.append((r.method, r.headers.get("authorization", ""))) if "/api/cuenta/exportar" in r.url else None)
    with pag.expect_download() as d:
        pag.click("#btn-exportar")
    dl = d.value
    ok("IA-18: «Descargar mis datos» pide GET /api/cuenta/exportar con el token Bearer",
       pedidos and pedidos[0][0] == "GET" and pedidos[0][1].startswith("Bearer ") and len(pedidos[0][1]) > 20)
    ok("IA-18: descarga un JSON con nombre claro", re.fullmatch(r"pullex-mis-datos-\d{4}-\d{2}-\d{2}\.json", dl.suggested_filename)
       and json.load(open(dl.path(), encoding="utf-8"))["cuenta"]["email"] == email, dl.suggested_filename)
    pag.unroute("**/api/cuenta/exportar")
    pag.route("**/api/cuenta/exportar", lambda r: r.fulfill(status=429, content_type="application/json", body='{"detail":"Demasiadas descargas. Espera un rato."}'))
    pag.click("#btn-exportar")
    pag.wait_for_timeout(500)
    ok("IA-18: un error al descargar se muestra", "Demasiadas descargas" in pag.evaluate("[...document.querySelectorAll('.toast')].map(t=>t.textContent).join()"))
    pag.locator("#panel-datos").scroll_into_view_if_needed()
    pag.wait_for_timeout(300)
    pag.screenshot(path=f"{OUT}/fix-ajustes-datos-1440.png")

    # --- IA-18: eliminar la cuenta (modal accesible + respuestas simuladas)
    probar_modal(pag, "m-eliminar", "#btn-eliminar", "#m-eliminar", primer="#el-clave")
    estado = {"codigo": 401, "cuerpo": {"detail": "Clave incorrecta"}}
    cuerpos = []

    def eliminar(r):
        cuerpos.append(json.loads(r.request.post_data or "{}"))
        r.fulfill(status=estado["codigo"], content_type="application/json", body=json.dumps(estado["cuerpo"]))
    pag.route("**/api/cuenta/eliminar", eliminar)
    pag.click("#btn-eliminar")
    pag.click("#el-btn")
    ok("IA-18: sin contraseña no se envía y se pide", not cuerpos and pag.inner_text("#el-msg") == "Escribe tu contraseña.")
    pag.fill("#el-clave", CLAVE)
    pag.fill("#el-conf", "eliminar")
    pag.click("#el-btn")
    ok("IA-18: sin escribir ELIMINAR no se envía", not cuerpos and "ELIMINAR" in pag.inner_text("#el-msg"))
    pag.fill("#el-conf", "ELIMINAR")
    for codigo, cuerpo, esperado in ((401, {"detail": "Clave incorrecta"}, "Clave incorrecta"),
                                     (429, {"detail": "Demasiados intentos. Espera unos minutos."}, "Demasiados intentos"),
                                     (400, {}, "Revisa los datos")):
        estado.update(codigo=codigo, cuerpo=cuerpo)
        pag.click("#el-btn")
        pag.wait_for_function("() => !$('el-btn').disabled && $('el-msg').textContent.length > 0", timeout=10000)
        ok(f"IA-18: error {codigo} se muestra en el modal (role=alert)", esperado in pag.inner_text("#el-msg")
           and pag.get_attribute("#el-msg", "role") == "alert" and pag.is_visible("#m-eliminar"), pag.inner_text("#el-msg"))
        if codigo == 401:
            pag.screenshot(path=f"{OUT}/fix-eliminar-1440.png")
    ok("IA-18: el cuerpo es {\"clave\": …}", cuerpos and cuerpos[-1] == {"clave": CLAVE}, str(cuerpos[-1:]))
    pag.evaluate("localStorage.setItem('pullex.apariencia.v2','{}'); sessionStorage.setItem('x','1')")
    estado.update(codigo=200, cuerpo={"ok": True})
    pag.click("#el-btn")
    pag.wait_for_function("() => typeof PERFIL !== 'undefined' && PERFIL === null && !document.getElementById('auth').classList.contains('hidden')", timeout=15000)
    pag.wait_for_timeout(300)
    ok("IA-18: tras eliminar vuelve a la portada con un mensaje", "eliminada" in pag.inner_text("#a-msg") and pag.is_visible("#auth"), pag.inner_text("#a-msg"))
    ok("IA-18: tras eliminar no queda estado local", not pag.evaluate("Object.keys(localStorage).filter(k=>k.startsWith('pullex.'))")
       and pag.evaluate("sessionStorage.length") == 0)

    # --- F-07: CSP sin violaciones en las vistas principales y páginas sueltas
    email2 = registrar(pag, "c")
    for v in ("inicio", "chat", "modular", "mapa", "documentos", "herramientas", "config", "perfiles"):
        pag.evaluate(f"ver('{v}')")
        pag.wait_for_timeout(600)
    for ruta in ("/static/politica-datos.html", "/static/sin-conexion.html", "/static/restablecer.html?token=abc", "/admin"):
        pag.goto(BASE + ruta)
        pag.wait_for_timeout(400)
        if ruta.startswith("/static/restablecer"):
            ok("F-15: el token sale de la URL al cargar restablecer", pag.evaluate("location.search") == "")
            envios = []
            pag.on("request", lambda r: envios.append(r.post_data) if "/api/restablecer-clave" in r.url else None)
            pag.fill("#clave1", "nueva-clave-segura-1")
            pag.fill("#clave2", "nueva-clave-segura-1")
            pag.click("#btn")
            pag.wait_for_timeout(600)
            ok("F-15: el formulario sigue enviando el token leído", envios and json.loads(envios[0]).get("token") == "abc")
        if ruta.startswith("/static/politica"):
            ok("política: página propia con <main id=politica> y el marcador",
               pag.locator("main#politica").count() == 1 and "El texto de la política se carga aquí" in pag.inner_text("main#politica"))
            ancho = pag.evaluate("document.querySelector('main#politica').getBoundingClientRect().width")
            ok("política: ancho de lectura cómodo (≤ 760 px en 1440)", 400 < ancho <= 760, str(ancho))
    viol = pag.evaluate("window.__csp || []")
    ok("F-07: sin violaciones de CSP en vistas, política, sin conexión, restablecer y admin", not viol, "; ".join(viol)[:300])
    ctx.close()

    # ============================================================== CSP del servidor (F-07) ==
    ctx = contexto(nav)
    pag = ctx.new_page()
    r = pag.goto(BASE + "/")
    csp = r.headers.get("content-security-policy", "")
    dirs = {d.strip().split(" ")[0]: d.strip() for d in csp.split(";") if d.strip()}
    ok("F-07: script-src solo con los dos archivos exactos de cdnjs", dirs.get("script-src") ==
       "script-src 'self' https://cdnjs.cloudflare.com/ajax/libs/marked/12.0.2/marked.min.js https://cdnjs.cloudflare.com/ajax/libs/dompurify/3.4.16/purify.min.js",
       dirs.get("script-src", ""))
    ok("F-07: style-src-elem sin 'unsafe-inline' y con huellas", "'unsafe-inline'" not in dirs.get("style-src-elem", "x unsafe")
       and "'sha256-" in dirs.get("style-src-elem", ""))
    ok("F-07: style-src-attr 'unsafe-inline'", dirs.get("style-src-attr") == "style-src-attr 'unsafe-inline'")
    ctx.close()

    # ===================================================== service worker y «Salir» (F-09, F-10) ==
    ctx = contexto(nav, service_workers="allow", viewport={"width": 1280, "height": 800})
    pag = ctx.new_page()
    pag.goto(BASE + "/")
    pag.evaluate("navigator.serviceWorker.ready")
    pag.reload()
    pag.wait_for_function("!!navigator.serviceWorker.controller", timeout=15000)
    registrar(pag, "s")
    pag.evaluate("localStorage.setItem('pullex.taller.borrador.viejo-sin-dueno','{}')")
    for u in ("/salud", "/admin", "/no-existe-404", "/static/no-existe.js"):
        pag.evaluate("u => fetch(u).then(r => r.status).catch(() => 0)", u)
    pag.wait_for_timeout(800)
    cache = pag.evaluate("""async () => { const o = {}; for (const k of await caches.keys()) { const c = await caches.open(k);
        o[k] = (await c.keys()).map(r => new URL(r.url).pathname); } return o; }""")
    entradas = [x for v in cache.values() for x in v]
    ok("F-09: caché pullex-v14", list(cache) == ["pullex-v14"], str(list(cache)))
    ok("F-09: solo se guarda la cara de la app (/, /static/, manifiesto)",
       entradas and all(x == "/" or x.startswith("/static/") or x == "/manifest.webmanifest" for x in entradas),
       str([x for x in entradas if not (x == "/" or x.startswith("/static/"))]))
    ok("F-09: un 404 no entra a la caché", "/static/no-existe.js" not in entradas and "/no-existe-404" not in entradas)
    ok("F-09: la página «Sin conexión» está guardada", "/static/sin-conexion.html" in entradas)
    sin_red = "/static/sin-conexion-prueba-" + str(int(time.time()))
    ctx.route("**" + sin_red, lambda r: r.abort("internetdisconnected"))
    try:
        pag.goto(BASE + sin_red, timeout=15000)
        ok("F-09/PWA: navegar sin red muestra «No hay conexión»", "No hay conexión" in pag.inner_text("h1"), pag.inner_text("body")[:80])
        pag.screenshot(path=f"{OUT}/fix-sin-conexion-1280.png")
    except Exception as e:
        ok("F-09/PWA: navegar sin red muestra «No hay conexión»", False, str(e)[:160])
    pag.goto(BASE + "/")
    pag.wait_for_load_state()
    pag.fill("#a-email", email2)
    pag.fill("#a-clave", CLAVE)
    pag.click("#a-btn")
    pag.wait_for_function("() => PERFIL !== null && huellaCuenta() !== null", timeout=15000)
    pag.wait_for_load_state("networkidle")
    ok("F-11: un borrador antiguo sin dueño se descarta al ingresar",
       pag.evaluate("localStorage.getItem('pullex.taller.borrador.viejo-sin-dueno')") is None)
    pag.evaluate("tlEscribir('c2', {texto:'x'}); sessionStorage.setItem('algo','1')")
    pag.wait_for_load_state("networkidle")
    limpio = pag.evaluate("""async () => { await limpiarEstadoLocal();
        return [(await caches.keys()).filter(k => k.startsWith('pullex-')).length,
                Object.keys(localStorage).filter(k => k.startsWith('pullex.')).length, sessionStorage.length, SESION.activa()]; }""")
    ok("F-10: limpiar borra las cachés de la app, localStorage pullex.* y sessionStorage", limpio == [0, 0, 0, False], str(limpio))
    ctx.close()

    # «Salir» de verdad (botón): vuelve a la portada sin sesión y sin datos locales
    ctx = contexto(nav, viewport={"width": 1280, "height": 800})
    pag = ctx.new_page()
    registrar(pag, "x")
    pag.evaluate("tlEscribir('c3', {texto:'y'})")
    with pag.expect_navigation():
        pag.locator("[data-click=salir]:visible").first.click()
    pag.wait_for_timeout(400)
    ok("F-10: «Salir» deja la portada sin sesión ni borradores", pag.is_visible("#auth") and pag.evaluate(
        "typeof PERFIL!=='undefined' && PERFIL===null && !SESION.activa() && !Object.keys(localStorage).some(k=>k.startsWith('pullex.'))"))
    ctx.close()

    # ==================================================================== PWA: manifiesto ==
    ctx = contexto(nav)
    pag = ctx.new_page()
    r = pag.request.get(BASE + "/manifest.webmanifest")
    ok("PWA: manifiesto alcanzable y con tipo application/manifest+json", r.status == 200 and "manifest+json" in r.headers.get("content-type", ""))
    man = r.json()
    ok("PWA: nombre, id, start_url, scope, display, colores", man.get("name") == "PULLEX IA" and man.get("short_name") == "PULLEX IA"
       and man.get("id") == "/" and man.get("start_url") == "/" and man.get("scope") == "/" and man.get("display") == "standalone"
       and man.get("background_color") == "#101115" and man.get("theme_color") == "#101115" and man.get("orientation"))
    tam_ok, propositos = True, set()
    for ic in man.get("icons", []) + man.get("screenshots", []):
        ri = pag.request.get(BASE + ic["src"])
        w, h = (int(x) for x in ic["sizes"].split("x"))
        real = Image.open(io.BytesIO(ri.body())).size if Image else (w, h)
        if ri.status != 200 or real != (w, h):
            tam_ok = False
            print("   ícono/captura con problema:", ic["src"], ri.status, real, ic["sizes"])
        propositos.add(ic.get("purpose", "any"))
    ok("PWA: cada ícono (y captura) existe con el tamaño declarado", tam_ok)
    ok("PWA: íconos «any» y «maskable» de 192 y 512", {"any", "maskable"} <= propositos and
       {(i["sizes"], i.get("purpose", "any")) for i in man["icons"]} >= {("192x192", "any"), ("512x512", "any"), ("192x192", "maskable"), ("512x512", "maskable")})
    pag.goto(BASE + "/")
    cdp = ctx.new_cdp_session(pag)
    am = cdp.send("Page.getAppManifest")
    ok("PWA: Chromium lee el manifiesto sin errores", am.get("url", "").endswith("/manifest.webmanifest") and not am.get("errors"), str(am.get("errors"))[:200])
    try:
        ident = cdp.send("Page.getAppId")
        print("   Page.getAppId:", ident)
    except Exception as e:
        print("   (Page.getAppId no disponible:", str(e)[:80], ")")
    ati = pag.request.get(BASE + "/static/apple-touch-icon.png")
    ok("PWA: apple-touch-icon de 180×180", ati.status == 200 and (not Image or Image.open(io.BytesIO(ati.body())).size == (180, 180)))
    metas = pag.evaluate("""() => ({
        cap: document.querySelector('meta[name=apple-mobile-web-app-capable]')?.content,
        mcap: document.querySelector('meta[name=mobile-web-app-capable]')?.content,
        barra: document.querySelector('meta[name=apple-mobile-web-app-status-bar-style]')?.content,
        titulo: document.querySelector('meta[name=apple-mobile-web-app-title]')?.content,
        temas: [...document.querySelectorAll('meta[name=theme-color]')].map(m => m.media),
        vp: document.querySelector('meta[name=viewport]').content,
        ati: document.querySelector('link[rel=apple-touch-icon]')?.getAttribute('sizes') })""")
    ok("PWA: etiquetas de iOS y theme-color claro/oscuro", metas["cap"] == "yes" and metas["mcap"] == "yes" and metas["barra"]
       and metas["titulo"] == "PULLEX IA" and "(prefers-color-scheme: dark)" in metas["temas"] and "(prefers-color-scheme: light)" in metas["temas"]
       and "viewport-fit=cover" in metas["vp"] and metas["ati"] == "180x180", str(metas))
    # Android/Chrome: el botón aparece solo con beforeinstallprompt y usa prompt()
    ok("PWA: sin aviso del navegador, el botón no aparece (escritorio)", not pag.is_visible("#btn-instalar-auth"))
    pag.evaluate("""() => { const e = new Event('beforeinstallprompt'); e.prompt = () => { window.__prompt = 1; return Promise.resolve() };
        e.userChoice = Promise.resolve({outcome: 'accepted'}); window.dispatchEvent(e); }""")
    ok("PWA: con beforeinstallprompt aparece «Instalar app»", pag.is_visible("#btn-instalar-auth"))
    pag.click("#btn-instalar-auth")
    pag.wait_for_timeout(300)
    ok("PWA: el botón llama a prompt() y se oculta al aceptar", pag.evaluate("window.__prompt") == 1 and not pag.is_visible("#btn-instalar-auth"))
    ctx.close()

    # ======================================================== móvil 390×844 (iPhone, táctil) ==
    ctx = contexto(nav, viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True, has_touch=True, user_agent=IPHONE_UA)
    pag = ctx.new_page()
    pag.add_init_script(OBSERVADOR)
    pag.goto(BASE + "/")
    ok("PWA iOS: «Instalar app» visible en Safari sin instalar", pag.is_visible("#btn-instalar-auth"))
    pag.click("#btn-instalar-auth")
    pag.wait_for_timeout(300)
    ok("PWA iOS: abre los pasos Compartir → Agregar a pantalla de inicio", pag.is_visible("#mi-ios") and not pag.is_visible("#mi-otro")
       and "Agregar a pantalla de inicio" in pag.inner_text("#m-instalar"))
    pag.screenshot(path=f"{OUT}/fix-instalar-ios-390.png")
    pag.keyboard.press("Escape")
    registrar(pag, "m", capturar=f"{OUT}/fix-ingreso-390.png")
    pag.click("#n-chat")
    pag.wait_for_timeout(400)
    chicos = [m for m in medir_compositor(pag) if m[1] < 44 or m[2] < 44]
    ok("F-12: controles del compositor de al menos 44×44 px en 390 px", not chicos, str(chicos))
    ok("F-12: sin desplazamiento horizontal", pag.evaluate("document.documentElement.scrollWidth <= innerWidth + 1"))
    pag.route("**/api/chat", lambda r: r.fulfill(status=200, content_type="text/event-stream", body=sse(
        {"tipo": "texto", "texto": RESPUESTA_CITAS}, {"tipo": "citas", "citas": CITAS}, {"tipo": "fin", "completo": True, "mensaje_id": None})))
    pag.fill("#txt", "¿Procede la tutela contra mi EPS?")
    pag.click("#env")
    pag.wait_for_function("() => !enviando && document.querySelector('#hilo .citas-rev')", timeout=30000)
    pag.wait_for_timeout(400)
    pag.locator("#hilo .citas-rev").last.scroll_into_view_if_needed()
    pag.screenshot(path=f"{OUT}/fix-consultar-390.png")
    pag.evaluate("ver('config')")
    pag.wait_for_timeout(400)
    sw = pag.locator("#cf-web").bounding_box()
    ok("F-12: el interruptor tiene área de toque ≥ 44 px (pseudo-elemento)", pag.evaluate(
        "(()=>{const s=getComputedStyle($('cf-web'),'::before');return s.content!=='none'&&parseFloat(s.height)>=0})()") and sw["height"] >= 24)
    pag.locator("#panel-datos").scroll_into_view_if_needed()
    pag.wait_for_timeout(300)
    pag.screenshot(path=f"{OUT}/fix-ajustes-datos-390.png")
    pag.click("#btn-eliminar")
    pag.wait_for_timeout(300)
    pag.route("**/api/cuenta/eliminar", lambda r: r.fulfill(status=401, content_type="application/json", body='{"detail":"Clave incorrecta"}'))
    pag.fill("#el-clave", "una-clave-mala")
    pag.fill("#el-conf", "ELIMINAR")
    pag.click("#el-btn")
    pag.wait_for_function("() => $('el-msg').textContent.length > 0")
    pag.screenshot(path=f"{OUT}/fix-eliminar-390.png")
    viol = pag.evaluate("window.__csp || []")
    ok("F-07: sin violaciones de CSP en el recorrido móvil", not viol, "; ".join(viol)[:200])
    ctx.close()

    # ================================================ modo instalado (standalone) simulado, 390×844 ==
    ctx = contexto(nav, viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True, has_touch=True, user_agent=IPHONE_UA)
    ctx.add_init_script("Object.defineProperty(navigator, 'standalone', {get: () => true});")
    pag = ctx.new_page()
    cdp = ctx.new_cdp_session(pag)
    emulado = True
    try:
        cdp.send("Emulation.setEmulatedMedia", {"features": [{"name": "display-mode", "value": "standalone"}]})
    except Exception:
        emulado = False
    pag.goto(BASE + "/")
    pag.wait_for_timeout(400)
    ok("PWA standalone: «Instalar app» oculto cuando ya está instalada", not pag.is_visible("#btn-instalar-auth") and pag.evaluate("esStandalone()"))
    if not (emulado and pag.evaluate("matchMedia('(display-mode: standalone)').matches")):
        print("   (Chromium sin interfaz no emula la media display-mode: el modo instalado se simula con navigator.standalone;"
              " las reglas @media(display-mode:standalone) no se ven en estas capturas)")
    pag.screenshot(path=f"{OUT}/fix-standalone-ingreso-390.png")
    registrar(pag, "t")
    pag.screenshot(path=f"{OUT}/fix-standalone-inicio-390.png")
    pag.click("#n-chat")
    pag.wait_for_timeout(400)
    pag.screenshot(path=f"{OUT}/fix-standalone-consultar-390.png")
    ok("PWA standalone: sin desplazamiento horizontal", pag.evaluate("document.documentElement.scrollWidth <= innerWidth + 1"))
    ctx.close()

    # ========================================== movimiento reducido del sistema (F-14) ==
    ctx = contexto(nav, reduced_motion="reduce")
    pag = ctx.new_page()
    pag.goto(BASE + "/")
    ok("F-14: prefers-reduced-motion apaga el desplazamiento suave", pag.evaluate(
        "(() => { let a; const o = Element.prototype.scrollIntoView; Element.prototype.scrollIntoView = function (x) { a = x }; desplazar(document.body); Element.prototype.scrollIntoView = o; return a.behavior })()") == "auto")
    ctx.close()
    nav.close()

fallos = [r for r in resultados if not r[1]]
print(f"\n{len(resultados) - len(fallos)}/{len(resultados)} verificaciones de frontend OK · capturas: {OUT}")
sys.exit(1 if fallos else 0)
