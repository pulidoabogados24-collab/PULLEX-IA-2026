"""Prueba de navegador de PULLEX Academia (tablero, Modular Lab → Mi mapa, repasos).

Uso: con `python demo/servidor_simulado.py` corriendo (modelo simulado, sin clave de API),
    BASE=http://127.0.0.1:8000 python3 tests/e2e_academia.py
Recorre el flujo en escritorio (1280 px) y móvil (390 px) y guarda capturas en CAPTURAS
(por defecto, un directorio temporal). Sale con código 1 si alguna verificación falla.
"""
import os, sys, tempfile, time
from playwright.sync_api import sync_playwright
BASE = os.getenv("BASE", "http://127.0.0.1:8000")
OUT = os.getenv("CAPTURAS") or tempfile.mkdtemp(prefix="pullex-academia-")
os.makedirs(OUT, exist_ok=True)
RESP = ("El problema jurídico es si Andrés actuó en legítima defensa. La agresión era actual e injusta porque "
        "el otro lo atacó con una botella rota; la defensa fue necesaria. Concluyo que no es responsable.")
errores, fallos = [], []

def ok(cond, msg):
    (print("OK  ", msg) if cond else (fallos.append(msg), print("FALLO", msg)))

with sync_playwright() as p:
    nav = p.chromium.launch()
    for nombre, vp in (("desk", {"width": 1280, "height": 900}), ("movil", {"width": 390, "height": 844})):
        ctx = nav.new_context(viewport=vp)
        pg = ctx.new_page()
        pg.on("pageerror", lambda e: errores.append(str(e)))
        pg.on("console", lambda m: errores.append(m.text) if m.type == "error" else None)
        pg.goto(BASE + "/")
        pg.click("#t-reg"); pg.fill("#r-nombre", "Valentina Ríos")
        pg.fill("#a-email", f"{nombre}{int(time.time()*1000)}@demo.local"); pg.fill("#a-clave", "clave-demo-123")
        pg.click("#a-btn"); pg.wait_for_function("() => PERFIL !== null")
        pg.wait_for_selector("#tablero .tcard")
        ok(pg.locator("#tablero .tcard.rec").count() == 1, f"{nombre}: tablero muestra caso recomendado a usuario nuevo")
        pg.screenshot(path=f"{OUT}/{nombre}-1-inicio-nuevo.png")
        # Modular Lab: Penal
        pg.click("#n-modular"); pg.wait_for_selector("#ml-areas button")
        pg.locator("#ml-areas button", has_text="Penal").click()
        pg.click("#ml-generar"); pg.wait_for_selector("#ml-caso:not(.hidden)")
        pg.click("#ml-btn-pista"); pg.wait_for_selector(".pista")
        pg.click("#ml-btn-pista"); pg.wait_for_function("() => document.querySelectorAll('.pista').length===2")
        ok(pg.inner_text("#ml-btn-pista") == "Explícame el concepto", f"{nombre}: tras las pistas aparece «Explícame el concepto»")
        pg.fill("#ml-resp", RESP); pg.dispatch_event("#ml-resp", "input")
        pg.click("#ml-btn-eval"); pg.wait_for_selector("#ml-eval:not(.hidden)")
        pg.wait_for_selector("#ml-eval .aprendido")
        ok("tu mapa se actualizó" in pg.inner_text("#ml-eval .aprendido").lower(), f"{nombre}: la evaluación informa el cambio en el mapa")
        pg.locator("#ml-eval .aprendido").screenshot(path=f"{OUT}/{nombre}-2-mapa-actualizado.png")
        # Mi mapa
        pg.locator("#ml-eval .aprendido button").click()
        pg.wait_for_selector("#mapa-temas .nodo")
        time.sleep(0.4)
        ok(pg.locator("#mapa-err-cuerpo .rep").count() >= 1, f"{nombre}: banco de errores con al menos un concepto")
        ok(pg.locator("#mapa-areas button.on").inner_text().startswith("Penal"), f"{nombre}: el mapa abre en el área con conceptos débiles")
        pg.screenshot(path=f"{OUT}/{nombre}-3-mi-mapa.png", full_page=True)
        pg.locator("#mapa-temas .nodo.debil").first.click()
        pg.wait_for_selector(".nodo-det")
        pg.locator(".nodo-det").screenshot(path=f"{OUT}/{nombre}-4-detalle-concepto.png")
        # practicar desde el nodo
        pg.locator(".nodo-det button", has_text="Practicar este concepto").click()
        pg.wait_for_function("() => document.querySelector('#ml-meta') && document.querySelector('#ml-meta').textContent.includes('Repaso:')", timeout=15000)
        ok(True, f"{nombre}: «Practicar este concepto» genera un caso de repaso")
        # Inicio con tablero
        pg.click("#n-inicio"); pg.wait_for_function("() => document.querySelectorAll('#tablero .tcard').length>=3")
        time.sleep(0.3)
        txt = pg.inner_text("#tablero").lower()
        ok("continuar estudiando" in txt and "caso recomendado" in txt, f"{nombre}: tablero con continuar y recomendado")
        pg.screenshot(path=f"{OUT}/{nombre}-5-inicio-tablero.png")
        pg.locator("#tablero button", has_text="Retomar caso").click()
        pg.wait_for_selector("#v-modular.on #ml-caso:not(.hidden)")
        ok("repaso:" in pg.inner_text("#ml-meta").lower(), f"{nombre}: «Retomar caso» reabre el caso pendiente")
        # explicame del mapa abre el chat en modo enséñame
        pg.click("#n-mapa"); pg.wait_for_selector("#mapa-err-cuerpo .rep")
        pg.locator("#mapa-err-cuerpo button", has_text="Explícamelo").first.click()
        pg.wait_for_selector("#v-chat.on")
        ok(pg.input_value("#estilo") == "ensename", f"{nombre}: «Explícamelo» abre el chat en modo Enséñame")
        ok(pg.locator("html").evaluate("() => document.documentElement.scrollWidth <= window.innerWidth + 1"), f"{nombre}: sin scroll horizontal")
        ctx.close()
    nav.close()
csp = [e for e in errores if "Content Security Policy" in e]
print("errores consola:", errores[:8])
print("violaciones CSP:", len(csp), "| fallos:", fallos, "| capturas:", OUT)
sys.exit(1 if fallos or csp or errores else 0)
