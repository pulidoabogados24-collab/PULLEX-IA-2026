"""Prueba de navegador de las respuestas del chat (PUL-017): respuesta cortada por el límite, continuación automática,
botón «Continuar», aviso al reabrir una conversación y valoración 👍/👎 con motivos.

Uso: con el servidor simulado corriendo (el simulador corta las respuestas cuando el mensaje lleva [[CORTE]] o [[CORTE-SIEMPRE]]),
    rm -f pullex.db && PORT=8774 /home/claude/work/venv/bin/python demo/servidor_simulado.py
    BASE=http://127.0.0.1:8774 python3 tests/e2e_respuestas.py
Escritorio (1280 px) y celular (390 px). Verifica cero violaciones de CSP (sin JavaScript en línea), cero errores de consola,
que el botón «Continuar» complete la respuesta SIN gastar una consulta y que no haya desbordamiento horizontal.
IMPORTANTE: el modelo es simulado; esto prueba la tubería y la interfaz, no la calidad jurídica de la IA real.
Sale con código 1 si alguna verificación falla."""
import json
import os
import sys
import tempfile
import time
import urllib.request

from playwright.sync_api import sync_playwright

BASE = os.getenv("BASE", "http://127.0.0.1:8774")
ADMIN = (os.getenv("PULLEX_ADMIN_EMAIL", "admin@demo.local"), os.getenv("PULLEX_ADMIN_CLAVE", "demo-admin-clave-larga"))
OUT = os.getenv("CAPTURAS") or tempfile.mkdtemp(prefix="pullex-respuestas-")
os.makedirs(OUT, exist_ok=True)
errores, fallos = [], []
VIGILAR_CSP = """window.__csp=[];document.addEventListener('securitypolicyviolation',
  e=>window.__csp.push(e.violatedDirective+' '+(e.blockedURI||'')));"""
SELLO = int(time.time())
_ip = {"n": 0}
CONCLUSION = "Conclusión de la respuesta simulada"


def ok(cond, msg):
    (print("OK  ", msg) if cond else (fallos.append(msg), print("FALLO", msg)))


def ip_nueva():
    _ip["n"] += 1
    return f"10.78.{SELLO % 250}.{_ip['n']}"


def api(ruta, cuerpo=None, token=None):
    h = {"content-type": "application/json", "x-forwarded-for": ip_nueva()}
    if token:
        h["Authorization"] = "Bearer " + token
    req = urllib.request.Request(BASE + ruta, data=json.dumps(cuerpo).encode() if cuerpo is not None else None, headers=h,
                                 method="POST" if cuerpo is not None else "GET")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


ADMIN_TOKEN = api("/api/login", {"email": ADMIN[0], "clave": ADMIN[1]})["token"]


def cuenta(etiqueta):
    email = f"resp-{etiqueta}-{SELLO}@demo.local"
    api("/api/registro", {"email": email, "nombre": "Valentina Ríos", "clave": "clave-demo-123"})
    api("/api/admin/actualizar", {"email": email, "plan": "premium", "activo": True}, ADMIN_TOKEN)
    return email, api("/api/login", {"email": email, "clave": "clave-demo-123"})["token"]


def contexto(nav, vp):
    ctx = nav.new_context(viewport=vp)
    ip = ip_nueva()
    ctx.route(BASE + "/**", lambda r: r.continue_(headers={**r.request.headers, "x-forwarded-for": ip}))
    return ctx


def entrar(pg, email):
    pg.goto(BASE + "/")
    pg.fill("#a-email", email)
    pg.fill("#a-clave", "clave-demo-123")
    pg.click("#a-btn")
    pg.wait_for_function("() => ESTADO !== null && document.querySelectorAll('#capgrid .captarj').length > 0")
    pg.click("#n-chat")


def preguntar(pg, texto):
    pg.fill("#txt", texto)
    pg.click("#env")


def esperar_fin(pg):
    """El envío termina cuando el botón vuelve a estar habilitado."""
    pg.wait_for_function("() => !document.getElementById('env').disabled", timeout=30000)


def ultimo_texto(pg):
    return pg.locator("#hilo .b.ia .md").last.inner_text()


def sin_desborde(pg, nombre):
    r = pg.evaluate("() => document.documentElement.scrollWidth <= window.innerWidth + 1 && "
                    "[...document.querySelectorAll('#hilo *')].every(e => e.getBoundingClientRect().right <= window.innerWidth + 1)")
    ok(r, f"{nombre}: sin desbordamiento horizontal en el hilo")


def usadas(token):
    return api("/api/estado", token=token)["perfil"]["usadas"]


with sync_playwright() as p:
    nav = p.chromium.launch()
    for nombre, vp in (("desk", {"width": 1280, "height": 900}), ("movil", {"width": 390, "height": 844})):
        email, token = cuenta(nombre)
        ctx = contexto(nav, vp)
        pg = ctx.new_page()
        pg.add_init_script(VIGILAR_CSP)
        pg.on("pageerror", lambda e, n=nombre: errores.append(f"{n}: {e}"))
        pg.on("console", lambda m, n=nombre: errores.append(f"{n}: {m.text}") if m.type == "error" else None)
        entrar(pg, email)

        # 1. Respuesta normal: sin aviso, con valoración.
        preguntar(pg, f"¿Qué es la acción de tutela? ({nombre} {SELLO})")
        pg.wait_for_selector("#hilo .b.ia .valorar", timeout=30000)
        esperar_fin(pg)
        ok(pg.locator(".aviso-inc").count() == 0, f"{nombre}: una respuesta normal no muestra el aviso de incompleta")
        ok(pg.locator("#hilo .b.ia .valorar .vl-btn").count() == 2, f"{nombre}: aparecen 👍 y 👎")

        # 2. 👎 con motivos de la lista cerrada.
        pg.locator("#hilo .b.ia .valorar .vl-btn").nth(1).click()
        pg.wait_for_selector("#hilo .b.ia .vl-motivos:not(.hidden)")
        ok(pg.locator("#hilo .b.ia .vl-chip").count() == 5, f"{nombre}: cinco motivos para elegir")
        pg.locator("#hilo .b.ia .vl-chip", has_text="Quedó incompleta").click()
        pg.locator("#hilo .b.ia .vl-chip", has_text="Es demasiado larga").click()
        pg.locator("#hilo .b.ia .vl-enviar").click()
        pg.wait_for_function("() => document.querySelector('#hilo .b.ia .vl-estado').textContent.includes('Gracias')")
        cal = api("/api/admin/calidad?dias=1", token=ADMIN_TOKEN)
        ok(cal["valoraciones"]["abajo"] >= 1 and cal["motivos_abajo"].get("muy_larga", 0) >= 1,
           f"{nombre}: el servidor registró la valoración con sus motivos")
        pg.screenshot(path=f"{OUT}/{nombre}-valoracion.png")

        # 3. Se corta una vez: la continuación automática la completa sin que la persona haga nada.
        preguntar(pg, f"¿Cómo se presenta la tutela? [[CORTE]] {nombre} {SELLO}")
        esperar_fin(pg)
        t = ultimo_texto(pg)
        ok(CONCLUSION in t and "Primer tramo" in t and t.count("Primer tramo") == 1,
           f"{nombre}: la continuación automática completó la respuesta sin duplicar texto")
        ok(pg.locator(".aviso-inc").count() == 0, f"{nombre}: completada sola: no hay aviso de incompleta")

        # 4. Se corta siempre: queda incompleta, se avisa, y «Continuar» la completa sin gastar consulta.
        preguntar(pg, f"¿Y el plazo para impugnar? [[CORTE-SIEMPRE]] {nombre} {SELLO}")
        pg.wait_for_selector(".aviso-inc .btn-continuar", timeout=30000)
        esperar_fin(pg)
        t = ultimo_texto(pg)
        ok(CONCLUSION not in t and "Primer tramo" in t, f"{nombre}: la respuesta cortada NO se presenta como completa")
        ok("incompleta" in pg.inner_text(".aviso-inc").lower(), f"{nombre}: el aviso dice que quedó incompleta")
        sin_desborde(pg, nombre)
        pg.screenshot(path=f"{OUT}/{nombre}-incompleta.png")
        antes = usadas(token)
        pg.click(".aviso-inc .btn-continuar")
        pg.wait_for_function("() => document.querySelectorAll('.aviso-inc').length === 0", timeout=30000)
        esperar_fin(pg)
        t = ultimo_texto(pg)
        ok(CONCLUSION in t and t.count("Primer tramo") == 1, f"{nombre}: «Continuar» completó la misma respuesta")
        ok(usadas(token) == antes, f"{nombre}: «Continuar» no gastó una consulta ({antes} → {usadas(token)})")
        ok(pg.locator("#hilo .b.ia").last.locator(".valorar").count() == 1, f"{nombre}: la respuesta completada se puede valorar")
        pg.screenshot(path=f"{OUT}/{nombre}-continuada.png")

        # 5. Al reabrir la conversación, la respuesta incompleta sigue ofreciendo «Continuar».
        preguntar(pg, f"¿Qué pasa si no responden? [[CORTE-SIEMPRE]] {nombre} {SELLO} reabrir")
        pg.wait_for_selector(".aviso-inc .btn-continuar", timeout=30000)
        esperar_fin(pg)
        entrar(pg, email)       # la sesión no sobrevive a recargar: se vuelve a entrar y se abre la conversación del historial
        cid = api("/api/conversaciones", token=token)[0]["id"]
        pg.evaluate("c => abrirConv(c)", cid)
        pg.wait_for_selector("#hilo .b.ia .aviso-inc .btn-continuar", timeout=15000)
        ok(pg.locator("#hilo .aviso-inc").count() == 1, f"{nombre}: al reabrir, solo la respuesta incompleta ofrece «Continuar»")
        pg.click("#hilo .aviso-inc .btn-continuar")
        pg.wait_for_function("() => document.querySelectorAll('.aviso-inc').length === 0", timeout=30000)
        esperar_fin(pg)
        ok(CONCLUSION in ultimo_texto(pg), f"{nombre}: la respuesta reabierta también se completa")

        ok(pg.evaluate("window.__csp") == [], f"{nombre}: cero violaciones de CSP")
        ctx.close()
    nav.close()

ok(not errores, f"cero errores de consola {errores[:5]}")
print(f"\n{'TODO OK' if not fallos else str(len(fallos)) + ' FALLOS'} · capturas en {OUT}")
sys.exit(1 if fallos else 0)
