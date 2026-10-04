"""Prueba de navegador de la Academia de escritos (pestañas del Modular Lab: Casos · Taller de escritos · Cómo contestar).

Uso: con el servidor simulado corriendo (modelo SIMULADO: prueba el flujo, no la calidad jurídica),
    rm -f pullex.db && PORT=8785 /home/claude/work/venv/bin/python demo/servidor_simulado.py
    BASE=http://127.0.0.1:8785 python3 tests/e2e_taller.py
Además abre demo/pullex-demo.html (demostración sin servidor). Escritorio (1280 px) y celular (390 px).
Verifica cero violaciones de CSP, cero errores de consola, que un plan Básico no pida /api/taller/* y que no
haya desbordamiento horizontal. Sale con código 1 si alguna verificación falla.
"""
import json
import os
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = os.getenv("BASE", "http://127.0.0.1:8785")
ADMIN = (os.getenv("PULLEX_ADMIN_EMAIL", "admin@demo.local"), os.getenv("PULLEX_ADMIN_CLAVE", "demo-admin-clave-larga"))
RAIZ = Path(__file__).resolve().parent.parent
OUT = os.getenv("CAPTURAS") or tempfile.mkdtemp(prefix="pullex-taller-")
os.makedirs(OUT, exist_ok=True)
errores, fallos = [], []
VIGILAR_CSP = """window.__csp=[];document.addEventListener('securitypolicyviolation',
  e=>window.__csp.push(e.violatedDirective+' '+(e.blockedURI||'')));"""
SELLO = int(time.time())
_ip = {"n": 0}

# Escrito de práctica con las palabras que busca la evaluación simulada (y una muletilla para la revisión de estilo).
ESCRITO = """Señor JUEZ DE LA REPÚBLICA (reparto)
Bogotá, 4 de septiembre de 2026

Marta Lucía Ríos Peña, actuando en nombre propio como accionante, presento acción de tutela en contra de la EPS accionada.

HECHOS
1. El 20 de agosto de 2026 el médico tratante me formuló un medicamento.
2. El 25 de agosto de 2026 la EPS negó la entrega.

DERECHOS FUNDAMENTALES VULNERADOS
La negativa vulnera mi derecho fundamental a la salud. Es importante destacar que la orden médica sigue vigente.

PROCEDENCIA
Se cumple la subsidiariedad porque no hay otro medio eficaz, y la inmediatez porque han pasado pocos días.

FUNDAMENTOS DE DERECHO
Artículo 86 de la Constitución y Decreto 2591 de 1991 (verificar vigencia).

PRETENSIONES
Que se ordene a la EPS entregar el medicamento dentro de las 48 horas siguientes al fallo.

PRUEBAS
Anexo la fórmula médica y la respuesta de la EPS.
"""


def ok(cond, msg):
    (print("OK  ", msg) if cond else (fallos.append(msg), print("FALLO", msg)))


def ip_nueva():
    """El límite de registro/ingreso es de 8 por IP cada 5 minutos: cada actor usa su propia IP de prueba."""
    _ip["n"] += 1
    return f"10.78.{SELLO % 250}.{_ip['n']}"


def api(ruta, cuerpo=None, token=None):
    h = {"content-type": "application/json", "x-forwarded-for": ip_nueva()}
    if token:
        h["Authorization"] = "Bearer " + token
    req = urllib.request.Request(BASE + ruta, data=json.dumps(cuerpo).encode() if cuerpo is not None else None,
                                 headers=h, method="POST" if cuerpo is not None else "GET")
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read())


def cuenta(plan):
    email = f"taller-{plan}-{SELLO}-{_ip['n']}@demo.local"
    api("/api/registro", {"email": email, "nombre": "Valentina Ríos", "clave": "clave-demo-123"})
    if plan != "prueba":
        token = api("/api/login", {"email": ADMIN[0], "clave": ADMIN[1]})["token"]
        api("/api/admin/actualizar", {"email": email, "plan": plan, "activo": True}, token)
    return email


def contexto(nav, vp):
    ctx = nav.new_context(viewport=vp)
    ip = ip_nueva()
    ctx.route(BASE + "/**", lambda r: r.continue_(headers={**r.request.headers, "x-forwarded-for": ip}))
    return ctx


def preparar(ctx, nombre, pedidos):
    pg = ctx.new_page()
    pg.add_init_script(VIGILAR_CSP)
    pg.on("pageerror", lambda e: errores.append(f"{nombre}: {e}"))
    pg.on("console", lambda m: errores.append(f"{nombre}: {m.text}") if m.type == "error" else None)
    pg.on("request", lambda r: pedidos.append(r.url) if "/api/taller" in r.url else None)
    return pg


def sin_desborde(pg, nombre, momento):
    fuera = pg.evaluate("""() => { const w = window.innerWidth + 1;
        const f = [...document.querySelectorAll('#v-modular *')].filter(e => { const r = e.getBoundingClientRect();
            return r.width > 0 && r.right > w });
        return {pagina: document.documentElement.scrollWidth <= w, fuera: f.slice(0, 3).map(e => e.className || e.tagName)} }""")
    ok(fuera["pagina"] and not fuera["fuera"], f"{nombre}: sin desbordamiento horizontal ({momento}) {fuera['fuera'] or ''}")


def entrar(pg, email):
    pg.goto(BASE + "/")
    pg.fill("#a-email", email)
    pg.fill("#a-clave", "clave-demo-123")
    pg.click("#a-btn")
    pg.wait_for_function("() => ESTADO !== null && PERFIL !== null")


def taller(pg, nombre, demo=False):
    """Flujo completo del Taller: elegir, redactar, evaluar, ver el modelo y retomar."""
    ok(pg.locator("nav button").count() == 7, f"{nombre}: la Academia de escritos no agrega botones a la barra (siguen 7)")
    pg.click("#n-modular")
    pg.wait_for_selector("#ml-areas button")
    ok(pg.locator(".tl-tabs [role=tab]").count() == 3 and pg.get_attribute("#tl-tab-casos", "aria-selected") == "true",
       f"{nombre}: tres pestañas y «Casos» seleccionada")
    ok(pg.locator("#tl-taller").is_hidden() and pg.locator("#ml-areas").is_visible(), f"{nombre}: Casos muestra el Modular Lab de siempre")
    sin_desborde(pg, nombre, "pestañas")

    pg.click("#tl-tab-taller")
    pg.wait_for_selector("#tl-tipos .tl-tipo")
    ok(pg.locator("#ml-areas").is_hidden(), f"{nombre}: al abrir el Taller se oculta Casos")
    ok(pg.locator("#tl-tipos .tl-tipo").count() == 14, f"{nombre}: 14 tipos de escrito")
    ok(pg.locator("#tl-niveles button").count() == 3 and pg.locator("#tl-fuentes .tl-fuente").count() == 2, f"{nombre}: 3 niveles y 2 fuentes")
    ok(pg.get_attribute("#tl-tipos .tl-tipo[data-tipo=tutela]", "aria-pressed") == "true", f"{nombre}: tutela elegida por defecto")
    sin_desborde(pg, nombre, "elegir escrito")
    pg.screenshot(path=f"{OUT}/{nombre}-1-elegir.png", full_page=True)

    restantes = pg.evaluate("PERFIL.restantes")
    pg.click("#tl-empezar")
    pg.wait_for_selector("#tl-esc:not(.hidden) #tl-texto")
    ok(pg.evaluate("PERFIL.restantes") == restantes, f"{nombre}: el escenario del banco no gasta consultas")
    meta = pg.inner_text("#tl-esc .ml-meta").lower()
    ok("banco curado" in meta and "pendiente de revisión humana" in meta, f"{nombre}: el escenario dice que es del banco y que falta revisión humana")
    partes = pg.locator("#tl-lista li").count()
    ok(partes >= 8 and len(pg.inner_text("#tl-esc .tl-hechos")) > 200, f"{nombre}: hechos y lista de comprobación ({partes} partes)")
    ok(pg.is_disabled("#tl-btn-modelo"), f"{nombre}: el escrito modelo está cerrado antes de intentar")
    sin_desborde(pg, nombre, "escenario")

    pg.fill("#tl-texto", "Muy corto.")
    pg.click("#tl-btn-eval")
    pg.wait_for_function("() => [...document.querySelectorAll('.toast')].some(t => /mínimo \\d+ caracteres/.test(t.textContent))")
    ok(pg.locator("#tl-eval").is_hidden(), f"{nombre}: un escrito muy corto no se evalúa")

    pg.fill("#tl-texto", ESCRITO)
    pg.dispatch_event("#tl-texto", "input")
    pg.wait_for_function("() => /Borrador guardado/.test(document.getElementById('tl-guardado').textContent)")
    ok("palabras" in pg.inner_text("#tl-cuenta"), f"{nombre}: contador y borrador guardado en el navegador")
    pg.click("#tl-btn-eval")
    pg.wait_for_selector("#tl-eval:not(.hidden) .ev-total")
    total = int(pg.inner_text("#tl-eval .ev-total").split("/")[0].strip())
    ok(0 < total <= 100 and pg.locator("#tl-eval .rub .r").count() == 7, f"{nombre}: evaluación con rúbrica de 7 criterios ({total}/100)")
    ok("SIMULADA" in pg.inner_text("#tl-eval .ev-com"), f"{nombre}: la evaluación dice que es simulada")
    halladas, faltan = pg.locator("#tl-lista li.ok").count(), pg.locator("#tl-lista li.falta").count()
    ok(halladas >= 6 and halladas + faltan == partes, f"{nombre}: la lista marca {halladas} partes halladas y {faltan} faltantes")
    ok(pg.locator("#tl-eval .ev-grid .ev-box").count() == 4 and "orientativa" in pg.inner_text("#tl-eval .nota-ia"),
       f"{nombre}: cuatro cajas de retroalimentación y aviso de IA")
    if not demo:
        ok(pg.evaluate("PERFIL.restantes") == restantes - 1, f"{nombre}: evaluar gasta una consulta")
        estilo = pg.inner_text("#tl-eval .estilo-rev")
        ok("Es importante destacar" in estilo and "No cambia tu puntaje" in estilo, f"{nombre}: revisión de estilo con la muletilla hallada")
    ok(not pg.is_disabled("#tl-btn-modelo"), f"{nombre}: el escrito modelo se abre después del primer intento")
    sin_desborde(pg, nombre, "evaluación")
    pg.screenshot(path=f"{OUT}/{nombre}-2-evaluacion.png", full_page=True)

    pg.click("#tl-btn-modelo")
    pg.wait_for_selector("#tl-modelo:not(.hidden) .tl-modelo-texto")
    ok("ejemplo de la demostración" in pg.inner_text("#tl-modelo").lower() and "verifica la vigencia" in pg.inner_text("#tl-modelo .nota-ia"),
       f"{nombre}: escrito modelo de ejemplo, rotulado")
    if not demo:
        ok(pg.evaluate("PERFIL.restantes") == restantes - 1, f"{nombre}: el escrito modelo no gasta consultas")
    sin_desborde(pg, nombre, "modelo")

    pg.wait_for_selector("#tl-mis-cuerpo .rep")
    ok("1 intento" in pg.inner_text("#tl-mis-cuerpo .rep"), f"{nombre}: «Tus escritos» lista el intento")
    pg.locator("#tl-esc .ml-acc button", has_text="Otro escenario").click()
    ok(pg.locator("#tl-esc").is_hidden(), f"{nombre}: «Otro escenario» vuelve a la configuración")
    pg.locator("#tl-mis-cuerpo .rep button").first.click()
    pg.wait_for_selector("#tl-eval:not(.hidden) #tl-eval-h")
    ok(pg.inner_text("#tl-eval-h") == "Tu última evaluación" and pg.input_value("#tl-texto").startswith("Señor JUEZ"),
       f"{nombre}: al retomar vuelven el borrador y la última evaluación")


def como(pg, nombre):
    """Lecciones de «Cómo contestar»: cinco lecciones con ejercicio y «Practicar ahora»."""
    pg.click("#tl-tab-como")
    pg.wait_for_selector("#tl-como .tl-lec")
    ok(pg.locator("#tl-como .tl-lec").count() == 5 and pg.locator("#tl-taller").is_hidden(), f"{nombre}: cinco lecciones")
    ok(pg.locator(".tl-punto").count() == 8 and "paso 1 de 8" in pg.inner_text("#tl-paso").lower(), f"{nombre}: método en 8 pasos")
    pg.click("#tl-paso-sig")
    ok("paso 2 de 8" in pg.inner_text("#tl-paso").lower() and pg.locator(".tl-punto.on").get_attribute("data-i") == "1", f"{nombre}: «Siguiente» avanza el paso")
    sin_desborde(pg, nombre, "lección método")
    pg.screenshot(path=f"{OUT}/{nombre}-3-como.png", full_page=True)

    pg.click("#tl-lec-hechos")
    pg.locator(".tl-hecho").nth(0).locator("button", has_text="Relevante").click()
    pg.locator(".tl-hecho").nth(1).locator("button", has_text="Relevante").click()
    ok(pg.locator(".tl-hecho.bien").count() == 1 and pg.locator(".tl-hecho.mal").count() == 1
       and "Llevas 1 de 2 bien" in pg.inner_text("#tl-hechos-marcador"), f"{nombre}: ejercicio de hechos con respuesta inmediata")
    sin_desborde(pg, nombre, "lección hechos")

    pg.click("#tl-lec-conectores")
    pg.select_option(".tl-hueco[data-hueco='0']", "porque")
    pg.select_option(".tl-hueco[data-hueco='1']", "además")
    ok(pg.locator(".tl-fb-lista li.bien").count() == 1 and pg.locator(".tl-fb-lista li.mal").count() == 1, f"{nombre}: ejercicio de conectores")
    sin_desborde(pg, nombre, "lección conectores")

    pg.click("#tl-lec-estructura")
    ok(pg.locator("#tl-leccion details.tl-det").count() == 4 and pg.locator("#tl-leccion details[open] .tl-esqueleto li").count() >= 8,
       f"{nombre}: cuatro esqueletos de escritos")
    sin_desborde(pg, nombre, "lección estructura")

    pg.click("#tl-lec-errores")
    pg.locator(".tl-quiz button").nth(1).click()
    ok(pg.locator(".tl-quiz button.bien").count() == 1 and pg.inner_text("#tl-leccion .tl-quiz + .tl-fb").startswith("Correcto"),
       f"{nombre}: pregunta de control")
    sin_desborde(pg, nombre, "lección errores")
    pg.locator("#tl-leccion .tl-practicar button").click()
    pg.wait_for_selector("#tl-taller:not(.hidden) #tl-config")
    ok(pg.get_attribute("#tl-tab-taller", "aria-selected") == "true" and pg.locator("#tl-esc").is_hidden(),
       f"{nombre}: «Practicar ahora» lleva al Taller")


with sync_playwright() as p:
    nav = p.chromium.launch()
    for nombre, vp in (("escritorio", {"width": 1280, "height": 900}), ("celular", {"width": 390, "height": 844})):
        pedidos = []
        ctx = contexto(nav, vp)
        pg = preparar(ctx, nombre, pedidos)
        entrar(pg, cuenta("pro"))
        taller(pg, nombre)
        como(pg, nombre)
        # Volver a Casos y a otra sección: el Modular Lab sigue funcionando.
        pg.click("#tl-tab-casos")
        ok(pg.locator("#ml-areas").is_visible() and pg.locator("#tl-taller").is_hidden(), f"{nombre}: volver a Casos")
        pg.keyboard.press("ArrowRight")
        ok(pg.get_attribute("#tl-tab-taller", "aria-selected") == "true", f"{nombre}: pestañas navegables con flechas")
        csp = pg.evaluate("window.__csp")
        ok(csp == [], f"{nombre}: cero violaciones de CSP {csp or ''}")
        ctx.close()

    # Modo oscuro y otro tema: los colores salen de los tokens (captura para revisión visual).
    ctx = contexto(nav, {"width": 390, "height": 844})
    pg = preparar(ctx, "oscuro", [])
    entrar(pg, cuenta("pro"))
    pg.evaluate("() => { document.documentElement.dataset.esquema = 'oscuro'; document.documentElement.dataset.tema = 'toga' }")
    pg.click("#n-modular")
    pg.click("#tl-tab-como")
    pg.wait_for_selector("#tl-como .tl-lec")
    pg.wait_for_timeout(350)   # termina la transición de color de la pestaña
    colores = pg.evaluate("""() => { const c = getComputedStyle(document.querySelector('.tl-tabs button.on'));
        const r = getComputedStyle(document.documentElement);
        const d = document.createElement('i'); d.style.color = r.getPropertyValue('--accent'); document.body.appendChild(d);
        const acento = getComputedStyle(d).color; d.remove();
        return {fondo: c.backgroundColor, texto: c.color, acento} }""")
    ok(colores["fondo"] == colores["acento"] and colores["texto"] != colores["fondo"], f"oscuro: la pestaña activa usa el acento del tema {colores}")
    pg.screenshot(path=f"{OUT}/celular-4-oscuro.png", full_page=True)
    ctx.close()

    # Plan Básico: pantalla de mejora y ningún pedido a /api/taller/*.
    pedidos = []
    ctx = contexto(nav, {"width": 390, "height": 844})
    pg = preparar(ctx, "basico", pedidos)
    entrar(pg, cuenta("basico"))
    pg.click("#n-modular")
    pg.wait_for_selector("#v-mejora.on .plan-card")
    ok(pg.locator("#v-modular.on").count() == 0 and pg.locator(".tl-tabs").is_hidden(), "básico: Modular Lab y la Academia de escritos muestran la pantalla de mejora")
    pg.click("#n-inicio")
    pg.wait_for_timeout(600)
    ok(pedidos == [], f"básico: la interfaz no pide /api/taller/* {pedidos[:2] or ''}")
    ok(pg.evaluate("window.__csp") == [], "básico: cero violaciones de CSP")
    ctx.close()

    # Demostración sin servidor (un solo archivo): mismo taller.js con el banco real y evaluación simulada.
    for nombre, vp in (("demo-escritorio", {"width": 1280, "height": 900}), ("demo-celular", {"width": 390, "height": 844})):
        ctx = nav.new_context(viewport=vp)
        pg = preparar(ctx, nombre, [])
        pg.goto((RAIZ / "demo" / "pullex-demo.html").as_uri())
        pg.click("#a-btn")
        pg.wait_for_function("() => ESTADO !== null && PERFIL !== null")
        taller(pg, nombre, demo=True)
        como(pg, nombre)
        ok(pg.evaluate("window.__csp") == [], f"{nombre}: cero violaciones de CSP")
        ctx.close()
    nav.close()

ok(not errores, f"cero errores de consola {errores[:5] or ''}")
print(f"\n{'TODO OK' if not fallos else str(len(fallos)) + ' FALLOS'} · capturas en {OUT}")
sys.exit(1 if fallos else 0)
