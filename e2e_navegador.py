"""Regresión en navegador real (Chromium) con la CSP estricta activa.

Uso: con el servidor corriendo en BASE, `python3 tests/e2e_navegador.py`
(variables PULLEX_ADMIN_EMAIL y PULLEX_ADMIN_CLAVE del servidor).

Todo se maneja con clics y teclado reales, no llamando funciones por consola: así se prueba
que cada botón sigue funcionando sin JavaScript en línea (despachador data-click). También
comprueba que un XSS con atributo onerror NO se ejecuta aunque llegue al HTML.
"""
import os
import sys
import time

from playwright.sync_api import sync_playwright

BASE = os.getenv("BASE", "http://127.0.0.1:8765")
ADMIN_EMAIL = os.environ["PULLEX_ADMIN_EMAIL"]
ADMIN_CLAVE = os.environ["PULLEX_ADMIN_CLAVE"]
CARGA = '<img src=x onerror="window.__xss=1">Mala'
OBSERVADOR = """document.addEventListener('securitypolicyviolation',
    e => (window.__csp = (window.__csp||[])).push(e.violatedDirective + ' ' + e.blockedURI));"""
resultados = []


def ok(nombre, cond, detalle=""):
    resultados.append((nombre, bool(cond), detalle))
    print(("PASS " if cond else "FAIL ") + nombre + (f" — {detalle}" if detalle else ""))


with sync_playwright() as p:
    nav = p.chromium.launch()
    ctx = nav.new_context()
    pag = ctx.new_page()
    pag.add_init_script(OBSERVADOR)
    pag.goto(BASE + "/")
    ok("librerías marked/DOMPurify cargan con SRI", pag.evaluate("LIBS_OK") is True)

    # enlace con preventDefault + modal
    pag.click("text=¿Olvidaste tu contraseña?")
    ok("abre recuperación (enlace sin navegar a #)",
       pag.is_visible("#m-recuperar") and not pag.url.endswith("#"))
    pag.locator("#m-recuperar [data-click=cerrarRecuperar]").click()
    ok("cierra recuperación", not pag.is_visible("#m-recuperar"))

    # registro con nombre malicioso
    email = f"e2e{int(time.time())}@pruebas.local"
    pag.click("#t-reg")
    ok("pestaña Crear cuenta (data-arg)", pag.is_visible("#r-nombre"))
    pag.fill("#r-nombre", CARGA)
    pag.fill("#a-email", email)
    pag.fill("#a-clave", "clave-e2e-segura-1")
    pag.click("#a-btn")
    pag.wait_for_function("() => PERFIL !== null", timeout=10000)
    ok("registro por la interfaz", pag.evaluate("PERFIL.email") == email)
    ok("banner de verificación visible", pag.is_visible("#banner-verif"))

    # chat: sugerencia (pasa this), escritura (input), Enter (keydown con event)
    pag.click("#n-chat")
    pag.locator("#sugs button").first.click()
    ok("sugerencia llena el cuadro (data-pasa=this)", len(pag.input_value("#txt")) > 10)
    web_antes = "on" in (pag.get_attribute("#chip-web", "class") or "")
    pag.click("#chip-web")
    ok("interruptor de búsqueda web", ("on" in (pag.get_attribute("#chip-web", "class") or "")) != web_antes)
    pag.fill("#txt", "")
    pag.click("#txt")
    pag.keyboard.type("¿Qué es una acción de tutela?")
    pag.keyboard.press("Enter")
    pag.wait_for_function("() => document.querySelectorAll('.md').length >= 2 && !enviando", timeout=60000)
    burbujas = pag.locator(".md").all_inner_texts()
    ok("Enter envía y el chat responde (modelo real o modo degradado)",
       any(len(b) > 20 for b in burbujas), (burbujas[-1][:80] if burbujas else "sin burbujas"))
    ok("sin XSS en la app del estudiante", pag.evaluate("window.__xss") is None)
    n = pag.evaluate("""() => { const t='Respuesta de prueba.\\n\\n---\\n**Confianza:** Alta — por prueba.';
        const b=burbuja('ia',t); accionesResp(b,t); return b.querySelectorAll('.nota-ia').length; }""")
    ok("respuesta con 'Confianza' lleva el rótulo de autoevaluación", n == 1)

    # configuración: tema (pasa this) y modal de clave
    pag.click("#n-config")
    tema_antes = "on" in (pag.get_attribute("#cf-tema", "class") or "")
    pag.click("#cf-tema")
    ok("interruptor de tema", ("on" in (pag.get_attribute("#cf-tema", "class") or "")) != tema_antes)
    pag.click("text=Cambiar contraseña")
    ok("abre modal de contraseña", pag.is_visible("#m-clave"))
    pag.locator("#m-clave [data-click=cerrarClave]").click()
    ok("cierra modal de contraseña", not pag.is_visible("#m-clave"))

    # memoria (click) y modo por defecto (change) llegan al servidor
    pag.fill("#cf-memoria", "Estudio sexto semestre")
    with pag.expect_response(lambda r: "/api/preferencias" in r.url) as resp:
        pag.click("text=Guardar memoria")
    ok("guardar memoria (click → API)", resp.value.status == 200)
    with pag.expect_response(lambda r: "/api/preferencias" in r.url) as resp:
        pag.select_option("#cf-modo", "profesional")
    ok("modo por defecto (change → API)", resp.value.status == 200)

    # herramientas del chat y boletín
    pag.click("#n-chat")
    pag.click("[data-click=abrirTools]")
    ok("abre herramientas", pag.is_visible("#m-tools"))
    pag.locator("#m-tools [data-click=cerrarTools]").click()
    ok("cierra herramientas", not pag.is_visible("#m-tools"))
    pag.click("#n-inicio")
    with pag.expect_response(lambda r: "/api/boletin" in r.url) as resp:
        pag.click("text=Actualizar boletín")
    ok("actualizar boletín (data-arg=true)", resp.value.status == 200)

    # prueba de la barrera: un atributo onerror inyectado no debe ejecutarse
    pag.evaluate("""() => { const d=document.createElement('div');
        d.innerHTML='<img src=x onerror="window.__xss2=1">'; document.body.appendChild(d); }""")
    time.sleep(0.5)
    ok("CSP bloquea un onerror inyectado (script-src-attr 'none')", pag.evaluate("window.__xss2") is None)
    todas = pag.evaluate("window.__csp || []")
    ok("el navegador reporta el bloqueo del onerror", any(v.startswith("script-src-attr") for v in todas))
    viol_app = [v for v in todas if not v.startswith("script-src-attr")]

    # panel admin: todo con clics
    admin = ctx.new_page()
    admin.add_init_script(OBSERVADOR)
    admin.goto(BASE + "/admin")
    admin.fill("#e", ADMIN_EMAIL)
    admin.fill("#c", ADMIN_CLAVE)
    admin.click("text=Ingresar")
    admin.wait_for_selector("#tb tr", timeout=10000)
    time.sleep(0.5)
    ok("admin: ingresar con clic", admin.is_visible("#panel"))
    ok("XSS almacenado NO se ejecuta en el panel admin", admin.evaluate("window.__xss") is None)
    fila = admin.locator("#tb tr", has_text=email)
    ok("nombre malicioso se muestra como texto", CARGA in fila.inner_text())
    fila.get_by_role("button", name="Desactivar").click()
    admin.wait_for_function(f"""() => [...document.querySelectorAll('#tb tr')].some(tr =>
        tr.innerText.includes('{email}') && tr.innerText.includes('Inactivo'))""", timeout=10000)
    ok("admin: Desactivar", True)
    admin.click("text=Refrescar")
    admin.wait_for_selector("#tb tr", timeout=10000)
    ok("admin: Refrescar", admin.locator("#tb tr").count() >= 2)
    viol_admin = admin.evaluate("window.__csp || []")

    # página de restablecer con token inválido
    rp = ctx.new_page()
    rp.add_init_script(OBSERVADOR)
    rp.goto(BASE + "/static/restablecer.html?token=token-invalido-de-prueba")
    rp.fill("#clave1", "nueva-clave-segura-1")
    rp.fill("#clave2", "nueva-clave-segura-1")
    rp.click("#btn")
    rp.wait_for_function("() => document.getElementById('msg').textContent.length > 0", timeout=10000)
    ok("restablecer: botón responde (enlace inválido rechazado)",
       any(k in rp.inner_text("#msg") for k in ("válido", "venció", "Demasiados intentos")),
       rp.inner_text("#msg")[:80])
    viol_rp = rp.evaluate("window.__csp || []")

    for nombre, v in (("app", viol_app), ("admin", viol_admin), ("restablecer", viol_rp)):
        ok(f"sin violaciones de CSP inesperadas ({nombre})", not v, "; ".join(v)[:200])
    nav.close()

fallos = [r for r in resultados if not r[1]]
print(f"\n{len(resultados) - len(fallos)}/{len(resultados)} verificaciones de navegador OK")
sys.exit(1 if fallos else 0)
