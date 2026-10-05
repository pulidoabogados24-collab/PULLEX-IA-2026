"""Prueba de navegador del acceso por plan (candados, pantalla de mejora y tabla comparativa).

Uso: con el servidor simulado corriendo,
    rm -f pullex.db && PORT=8774 /home/claude/work/venv/bin/python demo/servidor_simulado.py
    BASE=http://127.0.0.1:8774 python3 tests/e2e_planes.py
(admin por defecto del servidor simulado: admin@demo.local / demo-admin-clave-larga; se cambian con
PULLEX_ADMIN_EMAIL y PULLEX_ADMIN_CLAVE). Además abre demo/pullex-demo.html con ?plan=basico|pro|premium.
Escritorio (1280 px) y celular (390 px). Verifica cero violaciones de CSP, cero errores de consola, que la
interfaz no pida rutas que el plan no incluye y que no haya desbordamiento horizontal.
Sale con código 1 si alguna verificación falla.
"""
import json
import os
import sys
import tempfile
import time
import urllib.request
from pathlib import Path
from urllib.parse import unquote

from playwright.sync_api import sync_playwright

BASE = os.getenv("BASE", "http://127.0.0.1:8774")
ADMIN = (os.getenv("PULLEX_ADMIN_EMAIL", "admin@demo.local"), os.getenv("PULLEX_ADMIN_CLAVE", "demo-admin-clave-larga"))
RAIZ = Path(__file__).resolve().parent.parent
OUT = os.getenv("CAPTURAS") or tempfile.mkdtemp(prefix="pullex-planes-")
os.makedirs(OUT, exist_ok=True)
errores, fallos = [], []
VIGILAR_CSP = """window.__csp=[];document.addEventListener('securitypolicyviolation',
  e=>window.__csp.push(e.violatedDirective+' '+(e.blockedURI||'')));"""
SELLO = int(time.time())
_ip = {"n": 0}


def ok(cond, msg):
    (print("OK  ", msg) if cond else (fallos.append(msg), print("FALLO", msg)))


def ip_nueva():
    """El límite de registro/ingreso es de 8 por IP cada 5 minutos: cada actor usa su propia IP de prueba."""
    _ip["n"] += 1
    return f"10.77.{SELLO % 250}.{_ip['n']}"


def api(ruta, cuerpo=None, token=None, metodo=None):
    h = {"content-type": "application/json", "x-forwarded-for": ip_nueva()}
    if token:
        h["Authorization"] = "Bearer " + token
    req = urllib.request.Request(BASE + ruta, data=json.dumps(cuerpo).encode() if cuerpo is not None else None,
                                 headers=h, method=metodo or ("POST" if cuerpo is not None else "GET"))
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read())


ADMIN_TOKEN = api("/api/login", {"email": ADMIN[0], "clave": ADMIN[1]})["token"]


def cuenta(plan):
    email = f"plan-{plan}-{SELLO}-{_ip['n']}@demo.local"
    api("/api/registro", {"email": email, "nombre": "Valentina Ríos", "clave": "clave-demo-123"})
    if plan != "prueba":
        api("/api/admin/actualizar", {"email": email, "plan": plan, "activo": True}, ADMIN_TOKEN)
    return email


def contexto(nav, vp):
    """Contexto con su propia IP de prueba solo hacia el servidor (no hacia el CDN, que rechazaría la cabecera)."""
    ctx = nav.new_context(viewport=vp)
    ip = ip_nueva()
    ctx.route(BASE + "/**", lambda r: r.continue_(headers={**r.request.headers, "x-forwarded-for": ip}))
    return ctx


def preparar(ctx, nombre, bloqueadas):
    pg = ctx.new_page()
    pg.add_init_script(VIGILAR_CSP)
    pg.on("pageerror", lambda e: errores.append(f"{nombre}: {e}"))
    pg.on("console", lambda m: errores.append(f"{nombre}: {m.text}") if m.type == "error" else None)
    pg.on("response", lambda r: bloqueadas.append(r.url) if r.status == 403 else None)
    return pg


def sin_desborde(pg, nombre, sel):
    ancho = pg.evaluate("s => document.documentElement.scrollWidth <= window.innerWidth + 1 && "
                        "[...document.querySelectorAll(s + ' *')].every(e => e.getBoundingClientRect().right <= window.innerWidth + 1)",
                        sel)
    ok(ancho, f"{nombre}: sin desbordamiento horizontal en {sel}")


def entrar(pg, email):
    pg.goto(BASE + "/")
    pg.fill("#a-email", email)
    pg.fill("#a-clave", "clave-demo-123")
    pg.click("#a-btn")
    pg.wait_for_function("() => ESTADO !== null && document.querySelectorAll('#capgrid .captarj').length > 0")


ESPERA = {  # plan → (vistas con candado, n.º de botones «Mejorar» en Ajustes)
    "basico": ({"modular", "mapa", "documentos"}, 2),
    "pro": ({"documentos"}, 1),
    "premium": (set(), 0),
    "prueba": (set(), 3),
}


def revisar_plan(pg, nombre, plan):
    candados, n_mejorar = ESPERA[plan]
    tienen = {v for v in ("inicio", "modular", "mapa", "chat", "documentos", "config")
              if pg.locator(f"#n-{v} .nav-candado").count()}
    ok(tienen == candados, f"{nombre}/{plan}: candados en la navegación {sorted(tienen)}")
    # Inicio (camino «aprender»): la tarjeta del Laboratorio de casos indica el plan si está bloqueada.
    pg.click("#cam-aprender")
    tarj = pg.locator("#capgrid .captarj", has_text="Resolver un caso")
    tag = tarj.locator(".plan-tag").count()
    ok(tag == (1 if "modular" in candados else 0), f"{nombre}/{plan}: Inicio indica el plan en «Resolver un caso»")
    if "modular" in candados:
        pg.wait_for_selector("#tablero .mejora-tc")
        ok("Pro" in pg.inner_text("#tablero .mejora-tc"), f"{nombre}/{plan}: tablero invita al plan Pro sin llamar a la API")
    pg.click("#cam-trabajar")
    tarj = pg.locator("#capgrid .captarj", has_text="Documentos y flujos")
    ok(tarj.locator(".plan-tag").count() == (1 if "documentos" in candados else 0),
       f"{nombre}/{plan}: Inicio indica el plan en «Documentos y flujos»")
    pg.click("#cam-aprender")

    for vista, funcion in (("modular", "academia"), ("documentos", "automatizador")):
        pg.click(f"#n-{vista}")
        if vista in candados:
            pg.wait_for_selector("#v-mejora.on .plan-card")
            ok(pg.is_visible("#v-mejora") and not pg.is_visible(f"#v-{vista}"),
               f"{nombre}/{plan}: {vista} muestra la pantalla de mejora")
            ok("on" in pg.get_attribute(f"#n-{vista}", "class"), f"{nombre}/{plan}: la pestaña {vista} queda marcada")
            req = "pro" if funcion == "academia" else "premium"
            cards = pg.locator("#mejora-raiz .plan-card")
            ok(cards.count() == (2 if req == "pro" else 1), f"{nombre}/{plan}: planes ofrecidos para {funcion}")
            rec = pg.locator("#mejora-raiz .plan-card.rec")
            ok(rec.get_attribute("data-plan") == req and ("45.000" if req == "pro" else "60.000") in rec.inner_text(),
               f"{nombre}/{plan}: recomienda {req} con su precio en COP")
            href = rec.locator("a.pc-cta").get_attribute("href")
            txt = unquote(href)
            ok(href.startswith("mailto:") and "Pulidoabogados24@gmail.com" in href and req.capitalize() in txt
               and "Nequi" in txt and "@demo.local" in txt,
               f"{nombre}/{plan}: «Mejorar a {req.capitalize()}» abre el correo de activación ya escrito")
            ok(pg.locator("#mejora-raiz .mejora-ben li").count() == 4, f"{nombre}/{plan}: beneficios concretos")
            sin_desborde(pg, f"{nombre}/{plan}", "#v-mejora")
            pg.wait_for_timeout(400)  # fin de la animación de entrada de la vista
            pg.screenshot(path=f"{OUT}/{nombre}-{plan}-mejora-{vista}.png", full_page=True)
        else:
            ok(pg.is_visible(f"#v-{vista}") and not pg.is_visible("#v-mejora"), f"{nombre}/{plan}: {vista} abre normal")
            if vista == "documentos":
                pg.wait_for_selector("#doc-grid .doc-card")
            else:
                pg.wait_for_selector("#ml-areas button")

    if candados:
        pg.click("#n-modular" if "modular" in candados else "#n-documentos")
        pg.click("#mejora-raiz >> text=Seguir en Consultar")
        ok(pg.is_visible("#v-chat"), f"{nombre}/{plan}: «Seguir en Consultar» lleva al chat")

    pg.click("#n-config")
    pg.wait_for_selector("#planes .planes-tabla")
    ok(pg.locator("#planes th.actual .pt-tu").count() == (0 if plan == "prueba" else 1),
       f"{nombre}/{plan}: la tabla marca «Tu plan»")
    ok(pg.locator("#planes .planes-tabla tbody tr").count() == 4, f"{nombre}/{plan}: tabla con consultas y 3 funciones")
    ok(pg.locator("#planes a.pt-cta").count() == n_mejorar, f"{nombre}/{plan}: {n_mejorar} botones «Mejorar»")
    sin_desborde(pg, f"{nombre}/{plan}", "#planes")
    ok(pg.evaluate("() => [...document.querySelectorAll('#planes th, #planes td')].every(c => c.scrollWidth <= c.clientWidth + 1)"),
       f"{nombre}/{plan}: ninguna celda de la tabla de planes se desborda")
    pg.locator("#planes").scroll_into_view_if_needed()
    pg.wait_for_timeout(400)
    pg.screenshot(path=f"{OUT}/{nombre}-{plan}-ajustes.png")
    pg.click("#n-inicio")


with sync_playwright() as p:
    nav = p.chromium.launch()
    for nombre, vp in (("desk", {"width": 1280, "height": 900}), ("movil", {"width": 390, "height": 844})):
        for plan in ("basico", "pro", "premium", "prueba"):
            bloqueadas = []
            ctx = contexto(nav, vp)
            pg = preparar(ctx, f"{nombre}/{plan}", bloqueadas)
            entrar(pg, cuenta(plan))
            if plan == "basico":
                pg.wait_for_timeout(600)
                pg.screenshot(path=f"{OUT}/{nombre}-basico-inicio.png")
            revisar_plan(pg, nombre, plan)
            ok(bloqueadas == [], f"{nombre}/{plan}: la interfaz no pidió rutas fuera del plan {bloqueadas[:3]}")
            ok(pg.evaluate("window.__csp") == [], f"{nombre}/{plan}: cero violaciones de CSP")
            ctx.close()

    # El administrador baja el plan con la app abierta: el 403 del servidor lleva a la pantalla de mejora.
    bloqueadas = []
    ctx = contexto(nav, {"width": 1280, "height": 900})
    pg = ctx.new_page()
    pg.add_init_script(VIGILAR_CSP)
    consola = []
    pg.on("console", lambda m: consola.append(m.text) if m.type == "error" else None)
    pg.on("pageerror", lambda e: errores.append(f"degradado: {e}"))
    email = cuenta("pro")
    entrar(pg, email)
    api("/api/admin/actualizar", {"email": email, "plan": "basico", "activo": True}, ADMIN_TOKEN)
    pg.click("#n-mapa")
    pg.wait_for_selector("#v-mejora.on .plan-card", timeout=10000)
    ok(pg.locator("#n-mapa .nav-candado").count() == 1 and pg.locator("#n-modular .nav-candado").count() == 1,
       "degradado: tras el 403 «plan_insuficiente» aparecen los candados y la pantalla de mejora")
    # El navegador registra el 403 como «Failed to load resource»: es esperado aquí y solo aquí.
    ok(all("403" in m for m in consola), f"degradado: solo el 403 esperado en consola {consola[:3]}")
    ok(pg.evaluate("window.__csp") == [], "degradado: cero violaciones de CSP")
    ctx.close()

    # Panel de administración: muestra el proveedor de IA y el modelo activos.
    ctx = contexto(nav, {"width": 1280, "height": 900})
    pg = preparar(ctx, "admin", [])
    pg.goto(BASE + "/admin")
    pg.fill("#e", ADMIN[0])
    pg.fill("#c", ADMIN[1])
    pg.click("#login button")
    pg.wait_for_selector("#ia-activa")
    txt = pg.inner_text("#ia-activa")
    ok("Anthropic (Claude)" in txt and "claude-sonnet-5-5" in txt and "respaldo" in txt.lower(),
       f"admin: el panel muestra proveedor y modelo activos ({txt!r})")
    ok(pg.evaluate("window.__csp") == [], "admin: cero violaciones de CSP")
    pg.screenshot(path=f"{OUT}/admin-ia.png")
    ctx.close()

    # Demo sin servidor: Premium por defecto; ?plan=basico|pro muestran los bloqueos.
    for plan, candados in (("", set()), ("basico", {"modular", "mapa", "documentos"}), ("pro", {"documentos"})):
        for nombre, vp in (("demo-desk", {"width": 1280, "height": 900}), ("demo-movil", {"width": 390, "height": 844})):
            bloqueadas = []
            ctx = nav.new_context(viewport=vp)
            pg = preparar(ctx, f"{nombre}{plan and '-' + plan}", bloqueadas)
            pg.goto((RAIZ / "demo" / "pullex-demo.html").as_uri() + (f"?plan={plan}" if plan else ""))
            pg.click("#a-btn")
            pg.wait_for_function("() => ESTADO !== null && document.querySelectorAll('#capgrid .captarj').length > 0")
            etiqueta = plan or "premium"
            ok(pg.evaluate("PERFIL.plan") == etiqueta, f"{nombre}: perfil de demo en plan {etiqueta}")
            tienen = {v for v in ("modular", "mapa", "documentos") if pg.locator(f"#n-{v} .nav-candado").count()}
            ok(tienen == candados, f"{nombre}/{etiqueta}: candados {sorted(tienen)}")
            pg.click("#n-documentos")
            if "documentos" in candados:
                pg.wait_for_selector("#v-mejora.on .plan-card")
                sin_desborde(pg, f"{nombre}/{etiqueta}", "#v-mejora")
                pg.screenshot(path=f"{OUT}/{nombre}-{etiqueta}-mejora.png", full_page=True)
            else:
                pg.wait_for_selector("#doc-grid .doc-card")
                ok(True, f"{nombre}/{etiqueta}: Documentos abre normal")
            ok(bloqueadas == [], f"{nombre}/{etiqueta}: sin pedidos fuera del plan")
            ok(pg.evaluate("window.__csp") == [], f"{nombre}/{etiqueta}: cero violaciones de CSP")
            ctx.close()
    nav.close()

ok(not errores, f"cero errores de consola {errores[:5]}")
print(f"\n{'TODO OK' if not fallos else str(len(fallos)) + ' FALLOS'} · capturas en {OUT}")
sys.exit(1 if fallos else 0)
