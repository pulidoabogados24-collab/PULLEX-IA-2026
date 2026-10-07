"""Prueba de navegador del automatizador (Documentos: Escritos, Flujos, Asistente, Mis documentos).

Uso: con el servidor simulado corriendo (modelo simulado con textos de ejemplo),
    PORT=8773 /home/claude/work/venv/bin/python demo/servidor_simulado.py
    BASE=http://127.0.0.1:8773 python3 tests/e2e_documentos.py
Además abre demo/pullex-demo.html (sin servidor). Escritorio (1280 px) y celular (390 px).
Verifica cero violaciones de CSP, cero errores de consola y que no haya desbordamiento horizontal.
Sale con código 1 si alguna verificación falla.
"""
import os
import re
import sys
import tempfile
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = os.getenv("BASE", "http://127.0.0.1:8773")
RAIZ = Path(__file__).resolve().parent.parent
OUT = os.getenv("CAPTURAS") or tempfile.mkdtemp(prefix="pullex-documentos-")
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
    ancho = pg.evaluate("() => document.documentElement.scrollWidth <= window.innerWidth + 1 && "
                        "[...document.querySelectorAll('#v-documentos *')].every(e => e.getBoundingClientRect().right <= window.innerWidth + 1 || e.closest('.doc-texto table,.md table,.doc-salida table'))")
    ok(ancho, f"{nombre}: sin desbordamiento horizontal ({momento})")


def restantes(pg):
    return pg.evaluate("PERFIL.restantes")


def escritos(pg, nombre):
    pg.click("#n-documentos")
    pg.wait_for_selector("#doc-grid .doc-card")
    total = int(re.search(r"\d+", pg.inner_text("#doc-n")).group())
    ok(total >= 120 and pg.locator("#doc-grid .doc-card").count() == total, f"{nombre}: catálogo con {total} tipos")
    ok(pg.get_attribute("#doc-tab-escritos", "aria-selected") == "true", f"{nombre}: pestaña Escritos seleccionada")
    sin_desborde(pg, nombre, "catálogo")
    pg.screenshot(path=f"{OUT}/{nombre}-catalogo.png")
    # Búsqueda y filtro por área
    pg.fill("#doc-q", "pagare")
    pg.wait_for_function("() => document.querySelectorAll('#doc-grid .doc-card').length < 20")
    ok(pg.locator("#doc-grid .doc-card[data-tipo=pagare]").count() == 1, f"{nombre}: la búsqueda «pagare» encuentra el pagaré (sin tilde)")
    pg.fill("#doc-q", "")
    pg.select_option("#doc-area", "Tributario")
    pg.wait_for_function("() => [...document.querySelectorAll('#doc-grid .doc-card-area')].every(e => e.textContent.startsWith('Tributario'))")
    n_trib = pg.locator("#doc-grid .doc-card").count()
    ok(0 < n_trib < 20, f"{nombre}: filtro por área ({n_trib} tributarios)")
    pg.select_option("#doc-area", "")
    pg.select_option("#doc-para", "funcionario")
    pg.wait_for_function("() => { const c=[...document.querySelectorAll('#doc-grid .doc-card')]; return c.length > 0 && "
                         "c.every(x => [...x.querySelectorAll('.doc-chip')].some(ch => ch.textContent === 'Funcionario')) }")
    time.sleep(0.5)   # una respuesta tardía de la búsqueda anterior no debe sobrescribir el filtro
    n_func = pg.locator("#doc-grid .doc-card").count()
    ok(n_func < 40 and pg.locator("#doc-grid .doc-chip.proy").count() >= 10,
       f"{nombre}: filtro «funcionario» muestra proyectos para despacho ({n_func})")
    pg.select_option("#doc-para", "")
    pg.fill("#doc-q", "informacion copias")
    pg.wait_for_selector("#doc-grid .doc-card[data-tipo=peticion_informacion]")
    pg.click("#doc-grid .doc-card[data-tipo=peticion_informacion]")
    pg.wait_for_selector("#doc-generar")
    # Accesibilidad del formulario: cada control tiene su etiqueta.
    sin_label = pg.evaluate("() => [...document.querySelectorAll('#doc-trabajo .doc-campo .doc-inp')].filter(i => !document.querySelector('label[for=\"'+i.id+'\"]')).length")
    ok(sin_label == 0, f"{nombre}: todos los campos tienen <label for>")
    pg.click("#doc-generar")
    invalidos = pg.locator("#doc-trabajo [aria-invalid=true]").count()
    ok(invalidos >= 4, f"{nombre}: validación marca {invalidos} campos obligatorios con aria-invalid")
    foco = pg.evaluate("document.activeElement.id")
    ok(foco == "doc-f-solicitante", f"{nombre}: el foco va al primer campo con error ({foco})")
    describe = pg.get_attribute("#doc-f-solicitante", "aria-describedby") or ""
    ok("doc-f-solicitante-err" in describe and pg.is_visible("#doc-f-solicitante-err"), f"{nombre}: el error se anuncia con aria-describedby")
    ok(pg.is_visible("#doc-trabajo .doc-resumen"), f"{nombre}: resumen de errores visible (role=alert)")
    antes = restantes(pg)
    pg.fill("#doc-f-solicitante", "Valentina Ríos")
    ok(pg.get_attribute("#doc-f-solicitante", "aria-invalid") is None, f"{nombre}: el error se limpia al escribir")
    pg.fill("#doc-f-ciudad", "Bogotá")
    pg.fill("#doc-f-contraparte", "Secretaría de Movilidad")
    pg.fill("#doc-f-documentos", "Copia del expediente del comparendo.")
    pg.click("#doc-generar")
    pg.wait_for_selector("#doc-trabajo .doc-res", timeout=20000)
    res = pg.locator("#doc-trabajo .doc-res")
    ok("Ejemplo de la demostración" in res.inner_text(), f"{nombre}: muestra el borrador generado")
    ok(res.locator(".doc-texto h2").count() >= 3, f"{nombre}: el Markdown se renderiza (títulos)")
    ok(res.locator(".doc-verif li").count() >= 3, f"{nombre}: lista «datos que debes completar o verificar»")
    ok(res.locator(".doc-adv li").count() >= 1, f"{nombre}: advertencias del tipo")
    ok(restantes(pg) == antes - 1, f"{nombre}: generar usó 1 consulta")
    sin_desborde(pg, nombre, "borrador")
    res.screenshot(path=f"{OUT}/{nombre}-borrador.png")
    # Editar texto y guardar
    pg.click("#doc-trabajo .doc-res >> text=Editar texto")
    editor = res.locator("textarea.doc-editor")
    ok(editor.is_visible(), f"{nombre}: modo edición")
    editor.fill(editor.input_value() + "\n\nTEXTO-EDITADO-E2E")
    pg.click("#doc-trabajo .doc-res >> text=Guardar")
    pg.wait_for_selector(".toast >> text=Cambios guardados")
    pg.click("#doc-trabajo .doc-res >> text=Ver vista previa")
    ok("TEXTO-EDITADO-E2E" in res.locator(".doc-texto").inner_text(), f"{nombre}: la vista previa refleja la edición guardada")
    # Descargar Word (archivo .docx real desde el servidor)
    with pg.expect_download() as info:
        pg.click("#doc-trabajo .doc-res >> text=Descargar Word")
    destino = Path(OUT) / f"{nombre}.docx"
    info.value.save_as(str(destino))
    datos = destino.read_bytes()
    ok(datos[:2] == b"PK" and len(datos) > 5000 and info.value.suggested_filename.endswith(".docx"),
       f"{nombre}: descarga un .docx válido ({info.value.suggested_filename}, {len(datos)} bytes)")
    # Editar y regenerar: vuelve al formulario con los datos
    pg.click("#doc-trabajo .doc-res >> text=Editar y regenerar")
    pg.wait_for_selector("#doc-f-solicitante")
    ok(pg.input_value("#doc-f-solicitante") == "Valentina Ríos", f"{nombre}: «Editar y regenerar» precarga el formulario")
    pg.click("#doc-trabajo .doc-volver")
    ok(pg.is_visible("#doc-grid"), f"{nombre}: volver al catálogo")


def flujos(pg, nombre):
    pg.click("#doc-tab-flujos")
    pg.wait_for_selector("#doc-flujos .doc-card[data-flujo=despido]")
    ok(pg.locator("#doc-flujos .doc-card").count() >= 6, f"{nombre}: al menos 6 flujos")
    pg.click("#doc-flujos .doc-card[data-flujo=despido]")
    pg.fill("#doc-fl-solicitante", "Luis Pardo")
    pg.fill("#doc-fl-empleador", "Comercial Ejemplo S.A.S.")
    pg.fill("#doc-fl-salario", "2.000.000")
    pg.fill("#doc-fl-inicio", "2023-02-01")
    pg.fill("#doc-fl-fin", "2026-06-30")
    pg.select_option("#doc-fl-contrato", "Indefinido")
    pg.select_option("#doc-fl-motivo", "Despido sin justa causa")
    pg.select_option("#doc-fl-auxilio", "Sí")
    pg.fill("#doc-fl-ciudad", "Medellín")
    antes = restantes(pg)
    pg.click("#doc-flujo-ejecutar")
    pg.wait_for_function("() => (document.querySelector('#doc-flujo-progreso .doc-estado')||{}).textContent?.startsWith('Listo')", timeout=30000)
    ok(pg.locator("#doc-flujo-progreso .doc-paso.ok").count() == 3, f"{nombre}: flujo con 3 pasos terminados")
    ok(pg.locator("#doc-flujo-progreso .doc-salida").count() == 3, f"{nombre}: muestra la salida de cada paso")
    ok(pg.locator("#doc-flujo-progreso .doc-salida table").count() >= 1, f"{nombre}: la liquidación se ve como tabla")
    ok(restantes(pg) == antes - 3, f"{nombre}: el flujo usó 1 consulta por paso")
    sin_desborde(pg, nombre, "flujo")
    pg.locator("#doc-flujo-progreso .doc-progreso").screenshot(path=f"{OUT}/{nombre}-flujo.png")
    pg.click("#doc-flujo-progreso >> text=Abrir en Mis documentos")
    pg.wait_for_selector("#doc-mis-abierto .doc-res")
    ok("Paso 3." in pg.inner_text("#doc-mis-abierto .doc-res"), f"{nombre}: el resultado del flujo quedó en Mis documentos")


def asistente(pg, nombre):
    pg.click("#doc-tab-asistente")
    pg.click("#doc-proponer")
    ok(pg.get_attribute("#doc-tarea", "aria-invalid") == "true", f"{nombre}: tarea vacía marcada como inválida")
    pg.fill("#doc-tarea", "Prepara una tutela contra mi EPS porque no me entrega un medicamento formulado hace dos meses.")
    antes = restantes(pg)
    pg.click("#doc-proponer")
    pg.wait_for_selector("#doc-plan .doc-plan-paso")
    n = pg.locator("#doc-plan .doc-plan-paso").count()
    ok(3 <= n <= 6, f"{nombre}: plan propuesto con {n} pasos (sin ejecutar todavía)")
    ok(restantes(pg) == antes - 1 and pg.locator("#doc-asist-progreso .doc-paso").count() == 0, f"{nombre}: proponer el plan usó 1 consulta")
    pg.locator("#doc-plan .doc-plan-t").first.fill("Ordenar hechos (editado)")
    pg.locator("#doc-plan .doc-plan-quitar").last.click()
    ok(pg.locator("#doc-plan .doc-plan-paso").count() == n - 1, f"{nombre}: se puede quitar un paso")
    ok(f"{n - 1} consultas" in pg.inner_text("#doc-plan .doc-costo"), f"{nombre}: el costo se actualiza al editar el plan")
    sin_desborde(pg, nombre, "plan")
    pg.locator("#doc-plan").screenshot(path=f"{OUT}/{nombre}-plan.png")
    pg.click("#doc-ejecutar-plan")
    pg.wait_for_function("() => (document.querySelector('#doc-asist-progreso .doc-estado')||{}).textContent?.startsWith('Listo')", timeout=30000)
    titulos = pg.locator("#doc-asist-progreso .doc-salida h4").all_inner_texts()
    ok(len(titulos) == n - 1 and "editado" in titulos[0], f"{nombre}: se ejecutó el plan editado ({titulos[:1]})")


def mis_documentos(pg, nombre):
    pg.click("#doc-tab-mis")
    pg.wait_for_selector("#doc-mis-lista .doc-mis-f")
    # La lista puede estar pintada desde antes (dos documentos): se espera a que llegue la actualizada.
    try:
        pg.wait_for_function("() => document.querySelectorAll('#doc-mis-lista .doc-mis-f').length === 3", timeout=5000)
    except Exception:
        pass
    filas = pg.locator("#doc-mis-lista .doc-mis-f").count()
    ok(filas == 3, f"{nombre}: Mis documentos lista escrito, flujo y asistente ({filas})")
    pg.locator("#doc-mis-lista .doc-mis-f").last.locator("text=Borrar").click()
    pg.locator("#doc-mis-lista .doc-conf >> text=Sí, borrar").click()
    pg.wait_for_function("() => document.querySelectorAll('#doc-mis-lista .doc-mis-f').length === 2")
    ok(True, f"{nombre}: borrar con confirmación")
    # Navegación por teclado en las pestañas
    pg.focus("#doc-tab-mis")
    pg.keyboard.press("Home")
    ok(pg.evaluate("document.activeElement.id") == "doc-tab-escritos" and
       pg.get_attribute("#doc-tab-escritos", "aria-selected") == "true", f"{nombre}: pestañas navegables con teclado")
    sin_desborde(pg, nombre, "mis documentos")


with sync_playwright() as p:
    nav = p.chromium.launch()
    for nombre, vp in (("desk", {"width": 1280, "height": 900}), ("movil", {"width": 390, "height": 844})):
        ctx = nav.new_context(viewport=vp, accept_downloads=True)
        pg = preparar(ctx, nombre)
        pg.goto(BASE + "/")
        pg.click("#t-reg"); pg.fill("#r-nombre", "Valentina Ríos")
        pg.fill("#a-email", f"d{nombre}{int(time.time() * 1000)}@demo.local"); pg.fill("#a-clave", "clave-demo-123")
        pg.click("#a-btn"); pg.wait_for_function("() => PERFIL !== null")
        # El inicio «Estoy trabajando» lleva a la nueva vista (se espera a que iniciar() termine de pintar).
        pg.wait_for_function("() => ESTADO !== null && document.querySelectorAll('#capgrid .captarj').length > 0")
        pg.click("#cam-trabajar")
        pg.locator("#capgrid .captarj", has_text="Documentos y flujos").click()
        ok(pg.is_visible("#v-documentos") and "on" in pg.get_attribute("#n-documentos", "class"),
           f"{nombre}: «Documentos y flujos» del inicio abre la vista Documentos")
        escritos(pg, nombre)
        flujos(pg, nombre)
        asistente(pg, nombre)
        mis_documentos(pg, nombre)
        csp = pg.evaluate("window.__csp")
        ok(csp == [], f"{nombre}: cero violaciones de CSP {csp}")
        ctx.close()

    # Demo sin servidor: catálogo real, ejemplos rotulados y aviso al descargar Word.
    ctx = nav.new_context(viewport={"width": 390, "height": 844})
    pg = preparar(ctx, "demo")
    pg.goto((RAIZ / "demo" / "pullex-demo.html").as_uri())
    pg.click("#a-btn"); pg.wait_for_function("() => PERFIL !== null")
    pg.click("#n-documentos")
    pg.wait_for_selector("#doc-grid .doc-card")
    ok(pg.locator("#doc-grid .doc-card").count() >= 120, "demo: catálogo real completo")
    pg.fill("#doc-q", "eps")
    pg.wait_for_selector("#doc-grid .doc-card[data-tipo=tutela_salud]")
    pg.click("#doc-grid .doc-card[data-tipo=tutela_salud]")
    pg.fill("#doc-f-solicitante", "Carlos Méndez"); pg.fill("#doc-f-ciudad", "Cali")
    pg.fill("#doc-f-contraparte", "EPS Ejemplo"); pg.fill("#doc-f-servicio", "Medicamento")
    pg.select_option("#doc-f-orden_medica", "Sí"); pg.fill("#doc-f-hechos", "No me entregan el medicamento.")
    pg.fill("#doc-f-peticiones", "Que lo entreguen."); pg.select_option("#doc-f-urgente", "Sí")
    pg.click("#doc-generar")
    pg.wait_for_selector("#doc-trabajo .doc-res", timeout=20000)
    txt = pg.inner_text("#doc-trabajo .doc-res")
    ok("Ejemplo de la demostración" in txt and "Procedencia" in txt, "demo: borrador de ejemplo de tutela, rotulado")
    pg.click("#doc-trabajo .doc-res >> text=Descargar Word")
    pg.wait_for_selector(".toast >> text=demostración no genera archivos")
    ok(True, "demo: «Descargar Word» muestra un aviso")
    pg.click("#doc-tab-flujos")
    pg.click("#doc-flujos .doc-card[data-flujo=revisar_contrato]")
    pg.fill("#doc-fl-contrato", "Contrato de ejemplo con cláusulas."); pg.fill("#doc-fl-parte", "Arrendatario")
    pg.click("#doc-flujo-ejecutar")
    pg.wait_for_function("() => (document.querySelector('#doc-flujo-progreso .doc-estado')||{}).textContent?.startsWith('Listo')", timeout=30000)
    ok(pg.locator("#doc-flujo-progreso .doc-paso.ok").count() == 3, "demo: flujo simulado completo")
    sin_desborde(pg, "demo", "flujo")
    ctx.close()
    nav.close()

ok(not errores, f"cero errores de consola {errores[:5]}")
print(f"\n{'TODO OK' if not fallos else str(len(fallos)) + ' FALLOS'} · capturas en {OUT}")
sys.exit(1 if fallos else 0)
