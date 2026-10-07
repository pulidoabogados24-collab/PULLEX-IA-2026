"""Prueba de navegador del bloque «Fuentes consultadas».

Uso: con el servidor simulado corriendo (trae un corpus de demostración y una búsqueda web simulada),
    PORT=8771 python demo/servidor_simulado.py
    BASE=http://127.0.0.1:8771 python3 tests/e2e_fuentes.py
Además abre demo/pullex-demo.html (sin servidor) y verifica que la demo muestre las fuentes de ejemplo.
Sale con código 1 si alguna verificación falla. Verifica cero violaciones de CSP y cero errores de consola.
"""
import os
import sys
import tempfile
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = os.getenv("BASE", "http://127.0.0.1:8771")
RAIZ = Path(__file__).resolve().parent.parent
OUT = os.getenv("CAPTURAS") or tempfile.mkdtemp(prefix="pullex-fuentes-")
os.makedirs(OUT, exist_ok=True)
errores, fallos = [], []
VIGILAR_CSP = """window.__csp=[];document.addEventListener('securitypolicyviolation',
  e=>window.__csp.push(e.violatedDirective+' '+(e.blockedURI||'')));"""


def ok(cond, msg):
    (print("OK  ", msg) if cond else (fallos.append(msg), print("FALLO", msg)))


def preparar(ctx, nombre):
    pg = ctx.new_page()
    pg.add_init_script(VIGILAR_CSP)
    pg.on("pageerror", lambda e: errores.append(f"{nombre}: {e}"))
    pg.on("console", lambda m: errores.append(f"{nombre}: {m.text}") if m.type == "error" else None)
    return pg


def preguntar(pg, texto):
    pg.click("#n-chat")
    pg.fill("#txt", texto)
    pg.click("#env")
    pg.wait_for_function("() => !enviando && document.querySelectorAll('.b.ia').length > 0", timeout=30000)


with sync_playwright() as p:
    nav = p.chromium.launch()
    for nombre, vp in (("desk", {"width": 1280, "height": 900}), ("movil", {"width": 390, "height": 844})):
        ctx = nav.new_context(viewport=vp)
        pg = preparar(ctx, nombre)
        pg.goto(BASE + "/")
        pg.click("#t-reg"); pg.fill("#r-nombre", "Valentina Ríos")
        pg.fill("#a-email", f"f{nombre}{int(time.time()*1000)}@demo.local"); pg.fill("#a-clave", "clave-demo-123")
        pg.click("#a-btn"); pg.wait_for_function("() => PERFIL !== null")
        if "on" not in (pg.get_attribute("#chip-web", "class") or ""):
            pg.click("#chip-web")
        preguntar(pg, "¿Cuándo procede la acción de tutela? Explícame la subsidiariedad y la inmediatez.")
        bloque = pg.locator(".b.ia").last.locator("details.fuentes")
        ok(bloque.count() == 1, f"{nombre}: la respuesta trae el bloque «Fuentes consultadas»")
        resumen = bloque.locator("summary").inner_text()
        ok(resumen.startswith("Fuentes consultadas (") and int(resumen.split("(")[1].rstrip(")")) >= 2,
           f"{nombre}: resumen con el número de fuentes ({resumen})")
        ok(not bloque.evaluate("d => d.open"), f"{nombre}: el bloque empieza plegado")
        bloque.locator("summary").focus(); pg.keyboard.press("Enter")
        ok(bloque.evaluate("d => d.open"), f"{nombre}: se despliega con el teclado (Enter)")
        chips = bloque.locator(".fchip").all_inner_texts()
        ok("Oficial · web" in chips, f"{nombre}: chip «Oficial · web» ({chips})")
        ok("Corpus · verificar vigencia" in chips, f"{nombre}: chip «Corpus · verificar vigencia»")
        enlace = bloque.locator("a.ftit").first
        ok(enlace.get_attribute("href").startswith("https://www.corteconstitucional.gov.co/")
           and enlace.get_attribute("rel") == "noopener noreferrer" and enlace.get_attribute("target") == "_blank",
           f"{nombre}: enlace oficial abre en pestaña nueva con rel=noopener")
        ok("citada en la respuesta" in bloque.inner_text(), f"{nombre}: indica si la fuente fue citada")
        ok(bloque.locator(".fnota").count() == 1, f"{nombre}: nota de «verificar vigencia» para el corpus")
        ancho = pg.evaluate("() => document.documentElement.scrollWidth <= window.innerWidth + 1")
        ok(ancho, f"{nombre}: sin desbordamiento horizontal")
        bloque.screenshot(path=f"{OUT}/{nombre}-fuentes.png")
        # tema claro: el bloque sigue legible (el estado está en el texto del chip, no solo en el color)
        pg.evaluate("aplicarTema('claro')")
        bloque.screenshot(path=f"{OUT}/{nombre}-fuentes-claro.png")
        pg.evaluate("aplicarTema('oscuro')")
        # Reabrir la conversación desde el historial: las fuentes se guardaron con el mensaje.
        cid = pg.evaluate("CONV")
        pg.evaluate("nuevaConsulta()")
        pg.evaluate(f"abrirConv({cid})")
        pg.wait_for_function("() => document.querySelectorAll('#hilo .b.ia').length > 0")
        ok(pg.locator("#hilo .b.ia details.fuentes").count() == 1, f"{nombre}: al reabrir la consulta se ven sus fuentes")
        # Sin búsqueda web: solo corpus.
        pg.evaluate("nuevaConsulta()")
        pg.click("#chip-web")
        preguntar(pg, "derecho de petición respuesta de fondo")
        pg.locator(".b.ia").last.locator("details.fuentes summary").click()
        chips2 = pg.locator(".b.ia").last.locator(".fchip").all_inner_texts()
        ok(chips2 and all(c.startswith("Corpus") for c in chips2), f"{nombre}: sin web, solo fuentes del corpus ({chips2})")
        # Una pregunta sin coincidencias en el corpus y sin web no muestra bloque vacío.
        pg.evaluate("nuevaConsulta()")
        preguntar(pg, "hola")
        ok(pg.locator(".b.ia").last.locator("details.fuentes").count() == 0, f"{nombre}: sin fuentes no hay bloque")
        csp = pg.evaluate("window.__csp")
        ok(csp == [], f"{nombre}: cero violaciones de CSP {csp}")
        ctx.close()

    # Demo sin servidor (demo/pullex-demo.html con mock.js): fuentes de ejemplo.
    ctx = nav.new_context(viewport={"width": 1280, "height": 900})
    pg = preparar(ctx, "demo")
    pg.goto((RAIZ / "demo" / "pullex-demo.html").as_uri())
    pg.click("#a-btn"); pg.wait_for_function("() => PERFIL !== null")
    preguntar(pg, "¿Qué es la tutela?")
    bloque = pg.locator(".b.ia").last.locator("details.fuentes")
    bloque.locator("summary").click()
    ok(bloque.count() == 1 and "ejemplo" in bloque.inner_text().lower(), "demo: muestra 2 fuentes de ejemplo rotuladas")
    ok(bloque.locator("summary").inner_text() == "Fuentes consultadas (2)", "demo: exactamente 2 fuentes")
    ctx.close()
    nav.close()

ok(not errores, f"cero errores de consola {errores[:5]}")
print(f"\n{'TODO OK' if not fallos else str(len(fallos)) + ' FALLOS'} · capturas en {OUT}")
sys.exit(1 if fallos else 0)
