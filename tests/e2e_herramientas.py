"""Prueba de navegador de la vista Herramientas (Calculadora de términos y Liquidación).

Uso: con el servidor simulado corriendo,
    PORT=8783 /home/claude/work/venv/bin/python demo/servidor_simulado.py
    BASE=http://127.0.0.1:8783 python3 tests/e2e_herramientas.py
Escritorio (1280 px) y celular (390 px). Verifica cero violaciones de CSP, cero errores de consola, que no haya
desbordamiento horizontal, etiquetas en todos los controles y que los cálculos no gasten consultas.
Sale con código 1 si alguna verificación falla.
"""
import os
import sys
import tempfile
import time

from playwright.sync_api import sync_playwright

BASE = os.getenv("BASE", "http://127.0.0.1:8783")
OUT = os.getenv("CAPTURAS") or tempfile.mkdtemp(prefix="pullex-herramientas-")
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


def sin_desborde(pg, nombre, momento):
    bien = pg.evaluate("() => document.documentElement.scrollWidth <= window.innerWidth + 1 && "
                       "[...document.querySelectorAll('#v-herramientas *')].every(e => "
                       "e.getBoundingClientRect().right <= window.innerWidth + 1 || e.closest('.herr-scroll'))")
    ok(bien, f"{nombre}: sin desbordamiento horizontal ({momento})")


def etiquetas(pg, nombre, panel):
    sin = pg.evaluate("p => [...document.querySelectorAll(p + ' input, ' + p + ' select, ' + p + ' textarea')]"
                      ".filter(i => i.offsetParent !== null && !document.querySelector('label[for=\"' + i.id + '\"]')).map(i => i.id)", panel)
    ok(sin == [], f"{nombre}: todos los controles visibles de {panel} tienen <label for> {sin}")


def ir(pg, vista):
    """Abre una sección desde la navegación. En celular, Mi mapa, Herramientas y Ajustes están dentro de «Más»."""
    if not pg.is_visible("#n-" + vista):
        pg.click("#n-mas")
    pg.click("#n-" + vista)
    # El cambio de sección puede pasar por una transición (View Transitions): se espera a que la vista esté puesta.
    pg.wait_for_selector("#v-" + vista + ".on, #v-mejora.on")


def terminos(pg, nombre):
    ir(pg, "herramientas")
    pg.wait_for_selector("#herr-t-regimen")
    ok(pg.is_visible("#v-herramientas") and pg.get_attribute("#n-herramientas", "aria-current") == "page",
       f"{nombre}: la vista Herramientas abre y el botón queda marcado")
    ok(pg.get_attribute("#herr-tab-terminos", "aria-selected") == "true", f"{nombre}: pestaña Términos seleccionada")
    etiquetas(pg, nombre, "#herr-panel-terminos")
    sin_desborde(pg, nombre, "formulario de términos")
    antes = pg.evaluate("PERFIL.restantes")

    # 1. Formulario vacío: el servidor se abstiene y la interfaz marca lo que falta.
    pg.click("#herr-t-calcular")
    pg.wait_for_selector("#herr-t-res .herr-caja")
    ok("Sin fecha definitiva" in pg.inner_text("#herr-t-res .herr-h"), f"{nombre}: sin datos no hay fecha (abstención)")
    ok(pg.locator("#herr-t-res .herr-bloque.falta li").count() >= 3, f"{nombre}: lista lo que falta")
    ok(pg.locator("#herr-panel-terminos [aria-invalid=true]").count() >= 2, f"{nombre}: marca los campos que faltan")
    ok(pg.locator("#herr-t-vence").count() == 0, f"{nombre}: no muestra fecha de vencimiento al abstenerse")

    # 2. Petición general recibida el 1 de julio de 2026 → vence el 24 de julio.
    pg.select_option("#herr-t-regimen", "administrativo")
    opciones = pg.locator("#herr-t-termino_id option").count()
    ok(4 <= opciones <= 7, f"{nombre}: la tabla se filtra por régimen ({opciones} opciones)")
    pg.select_option("#herr-t-termino_id", "R-PLAZO-0001")
    ok("Ley 1437 de 2011" in pg.inner_text("#herr-t-nota"), f"{nombre}: muestra la norma del término elegido")
    pg.fill("#herr-t-fecha_notificacion", "2026-07-01")
    pg.select_option("#herr-t-forma_notificacion", "recepcion")
    pg.click("#herr-t-calcular")
    pg.wait_for_selector("#herr-t-vence")
    ok("viernes 24 de julio de 2026" in pg.inner_text("#herr-t-vence"), f"{nombre}: vence el viernes 24 de julio de 2026")
    ok(pg.locator("#herr-t-res .herr-tabla tbody tr").count() == 24, f"{nombre}: cronología día por día (24 filas)")
    ok("Chiquinquirá" in pg.inner_text("#herr-t-res .herr-tabla"), f"{nombre}: la cronología explica el festivo del 13 de julio")
    ok(pg.locator("#herr-t-res .herr-normas li").count() >= 6 and pg.locator("#herr-t-res .herr-normas a[href^=http]").count() >= 5,
       f"{nombre}: normas con enlace a la fuente")
    ok(pg.locator("#herr-t-res .herr-chip.pend").count() >= 1, f"{nombre}: la regla no verificada se distingue")
    ok("sábado" in pg.inner_text("#herr-t-res").lower() and "profesional" in pg.inner_text("#herr-t-res"),
       f"{nombre}: muestra supuestos y lo que decide un profesional")
    ok(pg.evaluate("document.activeElement.classList.contains('herr-h')"), f"{nombre}: el foco pasa al resultado")
    pg.click("#herr-t-copiar")
    pg.wait_for_selector(".toast")
    copiado = pg.evaluate("navigator.clipboard.readText()")
    ok("2026-07-24" in copiado and "R-PLAZO-0001" in copiado and "Huella" in copiado, f"{nombre}: «Copiar resultado» copia fecha, normas y huella")
    sin_desborde(pg, nombre, "resultado de términos")
    pg.screenshot(path=f"{OUT}/{nombre}-terminos.png", full_page=True)

    # 3. Dato desconocido que cambia el resultado: dos escenarios, sin fecha definitiva.
    pg.select_option("#herr-t-regimen", "cgp")
    ok(pg.is_visible("#herr-t-vacancia_judicial"), f"{nombre}: en régimen judicial pregunta por la vacancia")
    pg.select_option("#herr-t-termino_id", "R-PLAZO-0008")
    pg.fill("#herr-t-fecha_notificacion", "2025-12-15")
    pg.select_option("#herr-t-forma_notificacion", "estado")
    pg.click("#herr-t-calcular")
    pg.wait_for_selector("#herr-t-escenarios li")
    esc = pg.inner_text("#herr-t-escenarios")
    ok(pg.locator("#herr-t-escenarios li").count() == 2 and "30 de diciembre de 2025" in esc and "20 de enero de 2026" in esc,
       f"{nombre}: muestra los dos escenarios (con y sin vacancia)")
    ok(pg.locator("#herr-t-vence").count() == 0, f"{nombre}: con escenarios no afirma una fecha")
    pg.select_option("#herr-t-vacancia_judicial", "si")
    pg.click("#herr-t-calcular")
    pg.wait_for_selector("#herr-t-vence")
    ok("20 de enero de 2026" in pg.inner_text("#herr-t-vence"), f"{nombre}: con vacancia indicada, vence el 20 de enero")

    # 4. Término propio con suspensión.
    pg.select_option("#herr-t-regimen", "administrativo")
    pg.select_option("#herr-t-termino_id", "otro")
    ok(pg.is_visible("#herr-t-cantidad"), f"{nombre}: «otro término» pide número, unidad y clase de días")
    pg.fill("#herr-t-cantidad", "5")
    pg.select_option("#herr-t-tipo_dias", "habiles")
    pg.fill("#herr-t-fecha_notificacion", "2026-09-07")
    pg.select_option("#herr-t-forma_notificacion", "recepcion")
    pg.click("text=Agregar suspensión")
    pg.fill("#herr-t-s1-d", "2026-09-09")
    pg.fill("#herr-t-s1-h", "2026-09-10")
    pg.fill("#herr-t-s1-m", "cierre")
    pg.click("#herr-t-calcular")
    pg.wait_for_function("() => (document.querySelector('#herr-t-vence')||{}).textContent?.includes('16 de septiembre')")
    ok(True, f"{nombre}: término propio con suspensión vence el 16 de septiembre de 2026")
    etiquetas(pg, nombre, "#herr-panel-terminos")
    ok(pg.evaluate("PERFIL.restantes") == antes, f"{nombre}: calcular términos no gasta consultas")


def liquidacion(pg, nombre):
    antes = pg.evaluate("PERFIL.restantes")
    pg.click("#herr-tab-liquidacion")
    pg.wait_for_selector("#herr-l-salario_mensual")
    etiquetas(pg, nombre, "#herr-panel-liquidacion")
    sin_desborde(pg, nombre, "formulario de liquidación")
    # Sin salario → abstención.
    pg.fill("#herr-l-fecha_inicio", "2026-01-01")
    pg.fill("#herr-l-fecha_fin", "2026-06-30")
    pg.click("#herr-l-calcular")
    pg.wait_for_selector("#herr-l-res .herr-caja")
    ok("Sin liquidación" in pg.inner_text("#herr-l-res .herr-h") and pg.locator("#herr-l-total").count() == 0,
       f"{nombre}: sin salario no liquida (abstención)")
    ok(pg.get_attribute("#herr-l-salario_mensual", "aria-invalid") == "true", f"{nombre}: marca el salario como dato faltante")
    # Semestre completo.
    pg.fill("#herr-l-salario_mensual", "2.000.000")
    pg.fill("#herr-l-auxilio_transporte_mensual", "0")
    pg.click("#herr-l-calcular")
    pg.wait_for_selector("#herr-l-total")
    ok("2.560.000" in pg.inner_text("#herr-l-total"), f"{nombre}: total de prestaciones $ 2.560.000")
    filas = pg.locator("#herr-l-res .herr-tabla tbody tr")
    ok(filas.count() == 4 and "2000000 × 180 / 360" in pg.inner_text("#herr-l-res .herr-tabla"),
       f"{nombre}: desglose con la fórmula y sus valores")
    texto = pg.inner_text("#herr-l-res")
    ok("Redondeo" in texto and "base dias anio: 360" in texto and "R-LIQ-0007" in texto,
       f"{nombre}: muestra parámetros, redondeo y el supuesto no verificado")
    pg.click("#herr-l-copiar")
    pg.wait_for_selector(".toast")
    ok("2.560.000" in pg.evaluate("navigator.clipboard.readText()"), f"{nombre}: «Copiar resultado» copia la liquidación")
    sin_desborde(pg, nombre, "resultado de liquidación")
    pg.screenshot(path=f"{OUT}/{nombre}-liquidacion.png", full_page=True)
    # Intereses de mora: sin tasas por defecto.
    pg.select_option("#herr-l-tipo", "intereses_mora")
    pg.wait_for_selector("#herr-l-p1-d")
    etiquetas(pg, nombre, "#herr-panel-liquidacion")
    pg.fill("#herr-l-capital", "10000000")
    pg.select_option("#herr-l-clase", "comercial_moratorio")
    pg.fill("#herr-l-p1-d", "2026-01-01")
    pg.fill("#herr-l-p1-h", "2026-01-31")
    pg.click("#herr-l-calcular")
    pg.wait_for_selector("#herr-l-res .herr-bloque.falta li")
    faltan = pg.inner_text("#herr-l-res .herr-bloque.falta")
    ok("base_dias" in faltan and "fuente_tasas" in faltan and "tasa_pct" in faltan and pg.locator("#herr-l-total").count() == 0,
       f"{nombre}: intereses sin tasa, base ni fuente → no liquida")
    pg.fill("#herr-l-p1-t", "20")
    pg.select_option("#herr-l-metodo", "equivalente_diaria")
    pg.select_option("#herr-l-base_dias", "365")
    pg.fill("#herr-l-fuente_tasas", "tasa de ejemplo")
    pg.click("#herr-l-calcular")
    pg.wait_for_selector("#herr-l-total")
    ok("222.910" in pg.inner_text("#herr-l-total"), f"{nombre}: intereses con tasa indicada $ 222.910")
    # Indexación.
    pg.select_option("#herr-l-tipo", "indexacion")
    pg.fill("#herr-l-valor_historico", "1000000")
    pg.fill("#herr-l-ipc_inicial", "100")
    pg.fill("#herr-l-ipc_final", "125,5")
    pg.fill("#herr-l-fuente_ipc", "índices de ejemplo")
    pg.click("#herr-l-calcular")
    pg.wait_for_function("() => (document.querySelector('#herr-l-total')||{}).textContent?.includes('1.255.000')")
    ok(True, f"{nombre}: indexación $ 1.255.000")
    ok("corteconstitucional.gov.co" in (pg.get_attribute("#herr-l-res .herr-normas a", "href") or ""),
       f"{nombre}: la fórmula de indexación enlaza su fuente")
    sin_desborde(pg, nombre, "indexación")
    ok(pg.evaluate("PERFIL.restantes") == antes, f"{nombre}: liquidar no gasta consultas")
    # Pestañas con teclado.
    pg.focus("#herr-tab-liquidacion")
    pg.keyboard.press("ArrowLeft")
    ok(pg.evaluate("document.activeElement.id") == "herr-tab-terminos" and
       pg.get_attribute("#herr-tab-terminos", "aria-selected") == "true", f"{nombre}: pestañas navegables con teclado")


with sync_playwright() as p:
    nav = p.chromium.launch()
    for nombre, vp in (("desk", {"width": 1280, "height": 900}), ("movil", {"width": 390, "height": 844})):
        ctx = nav.new_context(viewport=vp, permissions=["clipboard-read", "clipboard-write"])
        pg = preparar(ctx, nombre)
        pg.goto(BASE + "/")
        pg.click("#t-reg")
        pg.fill("#r-nombre", "Valentina Ríos")
        pg.fill("#a-email", f"h{nombre}{int(time.time() * 1000)}@demo.local")
        pg.fill("#a-clave", "clave-demo-123")
        pg.click("#a-btn")
        pg.wait_for_function("() => PERFIL !== null")
        pg.wait_for_function("() => ESTADO !== null")
        # Escritorio: barra lateral con las 7 secciones. Celular: 4 destinos y «Más» (el resto se despliega encima).
        botones = pg.evaluate("() => [...document.querySelectorAll('nav button')].filter(b => b.offsetParent !== null).length")
        ancho_nav = pg.evaluate("() => [...document.querySelectorAll('nav button')].filter(b => b.offsetParent !== null)"
                                ".every(b => b.getBoundingClientRect().right <= window.innerWidth + 1 && b.getBoundingClientRect().width >= 40)")
        ok(botones in (5, 7) and ancho_nav, f"{nombre}: la navegación visible ({botones} botones) cabe en pantalla")
        terminos(pg, nombre)
        liquidacion(pg, nombre)
        # Las demás vistas siguen funcionando al volver.
        ir(pg, "documentos")
        pg.wait_for_selector("#doc-grid .doc-card")
        ir(pg, "inicio")
        ok(pg.is_visible("#v-inicio") and not pg.is_visible("#v-herramientas"), f"{nombre}: cambiar de vista oculta Herramientas")
        csp = pg.evaluate("window.__csp")
        ok(csp == [], f"{nombre}: cero violaciones de CSP {csp}")
        ctx.close()
    # Sin sesión, la API responde 401.
    ctx = nav.new_context()
    r = ctx.request.post(BASE + "/api/procedimientos/terminos", data={"regimen": "cgp"})
    ok(r.status == 401, "sin sesión: /api/procedimientos/terminos responde 401")
    ok(ctx.request.get(BASE + "/api/reglas").status == 401, "sin sesión: /api/reglas responde 401")
    ctx.close()
    nav.close()

ok(not errores, f"cero errores de consola {errores[:5]}")
print(f"\n{'TODO OK' if not fallos else str(len(fallos)) + ' FALLOS'} · capturas en {OUT}")
sys.exit(1 if fallos else 0)
