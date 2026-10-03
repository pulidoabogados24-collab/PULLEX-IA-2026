"""Prueba de navegador de Perfiles (registro, matriz, filtros, ficha, coordinador y resumen auditable).

Uso: con el servidor simulado corriendo (modelo simulado: prueba el flujo, no la calidad),
    rm -f pullex.db && PORT=8782 /home/claude/work/venv/bin/python demo/servidor_simulado.py
    BASE=http://127.0.0.1:8782 python3 tests/e2e_perfiles.py
Escritorio (1280 px) y celular (390 px). Verifica cero violaciones de CSP, cero errores de consola y que no
haya desbordamiento horizontal. Sale con código 1 si alguna verificación falla.
"""
import os
import re
import sys
import tempfile
import time

from playwright.sync_api import sync_playwright

BASE = os.getenv("BASE", "http://127.0.0.1:8782")
OUT = os.getenv("CAPTURAS") or tempfile.mkdtemp(prefix="pullex-perfiles-")
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
    # La matriz puede desplazarse dentro de su propia caja; nada más puede salirse de la pantalla.
    dato = pg.evaluate("""() => { const w = window.innerWidth + 1;
        const fuera = [...document.querySelectorAll('#v-perfiles *')].filter(e => { const r = e.getBoundingClientRect();
            return r.width > 0 && r.right > w && !e.closest('.per-matriz-caja,.per-salida table,.per-oculto') });
        return {pagina: document.documentElement.scrollWidth <= w, fuera: fuera.slice(0, 3).map(e => e.className || e.tagName),
                matriz: (() => { const c = document.querySelector('.per-matriz-caja'); return !c || c.scrollWidth <= c.clientWidth + 1 })()} }""")
    ok(dato["pagina"] and not dato["fuera"], f"{nombre}: sin desbordamiento horizontal ({momento}) {dato['fuera'] or ''}")
    ok(dato["matriz"], f"{nombre}: la matriz cabe completa sin desplazamiento ({momento})")


def entrar(pg, nombre):
    pg.goto(BASE + "/")
    pg.click("#t-reg")
    pg.fill("#r-nombre", "Persona " + nombre)
    pg.fill("#a-email", f"p{nombre}{int(time.time() * 1000)}@demo.local")
    pg.fill("#a-clave", "clave-demo-123")
    pg.click("#a-btn")
    pg.wait_for_selector("#app:not(.hidden)")


def registro(pg, nombre):
    ok(pg.locator("nav button").count() == 6, f"{nombre}: la barra de navegación sigue con 6 botones")
    pg.click("#n-config")
    pg.wait_for_selector("#panel-perfiles")
    pg.click("#abrir-perfiles")
    pg.wait_for_selector(".per-matriz .per-celda")
    ok(pg.locator("#v-perfiles.on").count() == 1 and pg.locator("#v-config.on").count() == 0, f"{nombre}: se abre la vista Perfiles")
    ok(pg.get_attribute("#n-config", "aria-current") == "page", f"{nombre}: Ajustes sigue marcado en la navegación")
    ok(pg.locator(".per-matriz .per-celda").count() == 100, f"{nombre}: matriz de 10 áreas × 10 funciones")
    ok(pg.locator(".per-matriz tbody tr").count() == 10 and pg.locator(".per-matriz thead th").count() == 11, f"{nombre}: encabezados de la matriz")
    textos = pg.locator(".per-estado-t").all_inner_texts()
    ok(len(textos) == 5 and "Definido" in textos[0] and "Conectado a herramientas" in textos[1] and "Ejecutado" in textos[2],
       f"{nombre}: los cinco estados con su nombre")
    numeros = [int(re.search(r"\d+", t).group()) for t in textos]
    ok(sum(numeros) == 1000 and numeros[2] == 0 and numeros[3] == 0 and numeros[4] == 0,
       f"{nombre}: 1.000 perfiles, ninguno ejecutado, evaluado ni aprobado ({numeros})")
    ok("Ningún perfil se ha ejecutado contra el modelo real" in pg.inner_text("#per-panel-registro"), f"{nombre}: lo dice con texto")
    ok(pg.inner_text("#per-n").strip() == "1000 perfiles" and pg.locator("#per-resultados .per-item").count() == 20,
       f"{nombre}: lista paginada (20 de 1000)")
    ok(pg.get_attribute(".per-celda[data-area=A07][data-funcion=F09]", "aria-label").startswith("A07 Derecho público colombiano, F09 revisión crítica"),
       f"{nombre}: cada celda tiene nombre accesible")
    sin_desborde(pg, nombre, "registro")
    pg.screenshot(path=f"{OUT}/{nombre}-registro.png", full_page=True)
    # Celda de la matriz → filtra por área y función.
    pg.click(".per-celda[data-area=A07][data-funcion=F09]")
    pg.wait_for_function("() => document.querySelectorAll('#per-resultados .per-item').length === 10")
    ids = pg.evaluate("() => [...document.querySelectorAll('#per-resultados .per-item')].map(e => e.dataset.perfil)")
    ok(all(i.startswith("A07-") and i.endswith("-F09") for i in ids), f"{nombre}: la celda A07×F09 muestra sus 10 perfiles")
    ok(pg.input_value("#per-f-area") == "A07" and pg.input_value("#per-f-funcion") == "F09", f"{nombre}: los filtros reflejan la celda")
    # Subespecialidad depende del área.
    pg.select_option("#per-f-sub", "S04")
    pg.wait_for_function("() => document.querySelectorAll('#per-resultados .per-item').length === 1")
    ok(pg.get_attribute("#per-resultados .per-item", "data-perfil") == "A07-S04-F09", f"{nombre}: filtro por subespecialidad")
    # Ficha con todos los campos y el estado real con texto.
    pg.click("#per-resultados .per-item")
    pg.wait_for_selector("#per-ficha:not(.hidden) #per-ficha-t")
    ficha = pg.inner_text("#per-ficha")
    for titulo in ("Estado real:", "Propósito", "Entradas", "Herramientas permitidas", "Fuentes", "Salida estructurada", "Límites",
                   "Pruebas de aceptación", "Presupuesto", "Condición de activación", "Instrucciones"):
        ok(titulo.upper() in ficha.upper(), f"{nombre}: la ficha muestra «{titulo}»")
    ok("A07-S04-F09" in ficha and "disciplinario" in ficha, f"{nombre}: ficha del perfil correcto")
    ok("Conectado a herramientas: se puede ejecutar, pero nadie ha medido" in pg.inner_text("#per-ficha-estado"), f"{nombre}: estado real escrito con palabras")
    ok("verificar vigencia" in ficha and "PERFIL PULLEX A07-S04-F09" in ficha, f"{nombre}: fuentes con «verificar vigencia» e instrucciones")
    sin_desborde(pg, nombre, "ficha")
    pg.screenshot(path=f"{OUT}/{nombre}-ficha.png", full_page=True)
    pg.click("#per-ficha .per-volver")
    pg.wait_for_selector("#per-ficha.hidden", state="attached")
    # Buscador (sin tildes) y filtro por estado.
    pg.click("#per-limpiar")
    pg.wait_for_function("() => document.getElementById('per-n').textContent.trim() === '1000 perfiles'")
    pg.fill("#per-q", "pagare")
    pg.wait_for_function("() => /^\\d+ de 1000/.test(document.getElementById('per-n').textContent)")
    ok(pg.locator("#per-resultados .per-item[data-perfil^=A06-S06]").count() >= 1, f"{nombre}: el buscador encuentra «pagaré» sin tilde")
    pg.fill("#per-q", "")
    pg.wait_for_function("() => document.getElementById('per-n').textContent.trim() === '1000 perfiles'")
    pg.click(".per-estado-t[data-estado=DEFINIDO]")
    pg.wait_for_function("() => /^\\d+ de 1000/.test(document.getElementById('per-n').textContent)")
    ok(pg.evaluate("() => [...document.querySelectorAll('#per-resultados .per-est')].every(e => e.textContent === 'Definido')"),
       f"{nombre}: filtro por estado «Definido»")
    ok(pg.evaluate("() => getComputedStyle(document.querySelector('.per-pag')).position") == "static",
       f"{nombre}: la paginación no hereda la posición fija de la barra principal")
    pg.click("#per-pag-sig")
    pg.wait_for_function("() => document.getElementById('per-pag-n').textContent.startsWith('Página 2')")
    ok(True, f"{nombre}: paginación")
    # Un perfil con herramienta propuesta lo dice.
    pg.click("#per-limpiar")
    pg.fill("#per-q", "A10-S02-F05")
    pg.wait_for_selector("#per-resultados .per-item[data-perfil=A10-S02-F05]")
    pg.click("#per-resultados .per-item[data-perfil=A10-S02-F05]")
    pg.wait_for_selector("#per-ficha:not(.hidden) #per-usar")
    ok("Propuesta: aún no existe" in pg.inner_text("#per-ficha") and pg.is_disabled("#per-usar"),
       f"{nombre}: un perfil solo definido muestra la herramienta propuesta y no se puede ejecutar")
    pg.click("#per-ficha .per-volver")


def coordinador(pg, nombre):
    pg.click("#per-tab-coordinador")
    pg.wait_for_selector("#per-tarea")
    ok(pg.get_attribute("#per-tab-coordinador", "aria-selected") == "true", f"{nombre}: pestaña Coordinador")
    # Tarea ambigua → pide datos y no ofrece ejecutar.
    pg.fill("#per-tarea", "necesito ayuda con un problema")
    pg.click("#per-ver-plan")
    pg.wait_for_selector("#per-plan-caja[data-estado=FALTAN_DATOS]")
    ok(pg.locator("#per-plan .per-preguntas li").count() >= 2 and pg.locator("#per-ejecutar").count() == 0,
       f"{nombre}: la tarea ambigua pide los datos que faltan")
    antes = pg.evaluate("PERFIL.restantes")
    # Tarea clara → plan con perfiles del área laboral, sin gastar consultas.
    pg.fill("#per-tarea", "Me despidieron sin justa causa después de tres años.")
    pg.click("#per-ver-plan")
    pg.wait_for_selector("#per-plan-caja[data-estado=LISTO] #per-ejecutar")
    ids = pg.evaluate("() => [...document.querySelectorAll('.per-plan-paso')].map(e => e.dataset.perfil)")
    ok(ids == ["A09-S04-F01", "A09-S04-F05", "A09-S04-F06"], f"{nombre}: el plan elige tres perfiles de A09 ({ids})")
    ok(pg.evaluate("PERFIL.restantes") == antes, f"{nombre}: ver el plan no gasta consultas")
    ok("3 consultas" in pg.inner_text("#per-costo") and "modelo simulado" in pg.inner_text("#per-plan"), f"{nombre}: costo y aviso de motor simulado")
    sin_desborde(pg, nombre, "plan")
    pg.click("#per-ejecutar")
    pg.wait_for_selector("#per-resumen")
    ok(pg.get_attribute("#per-resumen", "data-estado") == "completada", f"{nombre}: ejecución completada")
    ok("EJECUCIÓN SIMULADA" in pg.inner_text("#per-simulada"), f"{nombre}: el resumen dice que la ejecución fue simulada")
    ok(pg.locator("#per-resumen .per-paso").count() == 3, f"{nombre}: tres perfiles en el resumen auditable")
    ok(pg.evaluate("PERFIL.restantes") == antes - 3 and pg.inner_text("#c-rest").strip() == str(antes - 3),
       f"{nombre}: se descontaron 3 consultas (1 por perfil)")
    resumen = pg.inner_text("#per-resumen")
    ok("Secuencial" in resumen and "3 llamadas al modelo" in resumen and "Pasa" in resumen, f"{nombre}: modo, recursos y comprobaciones")
    sin_desborde(pg, nombre, "resumen")
    pg.screenshot(path=f"{OUT}/{nombre}-resumen.png", full_page=True)
    # El estado del perfil NO sube a Ejecutado por una ejecución simulada.
    pg.click("#per-tab-registro")
    pg.fill("#per-q", "A09-S04-F05")
    pg.wait_for_selector("#per-resultados .per-item[data-perfil=A09-S04-F05]")
    ok(pg.inner_text("#per-resultados .per-item[data-perfil=A09-S04-F05] .per-est") == "CONECTADO A HERRAMIENTAS"
       or pg.inner_text("#per-resultados .per-item[data-perfil=A09-S04-F05] .per-est").lower() == "conectado a herramientas",
       f"{nombre}: tras la ejecución simulada el perfil sigue «Conectado a herramientas»")
    pg.click("#per-resultados .per-item[data-perfil=A09-S04-F05]")
    pg.wait_for_selector("#per-ficha:not(.hidden) #per-usar")
    ok("no cuentan como ejecución real" in pg.inner_text("#per-ficha-estado"), f"{nombre}: la ficha aclara que la simulada no cuenta")
    # Elegir el perfil a mano → va al coordinador.
    pg.click("#per-usar")
    pg.wait_for_selector("#per-elegidos .per-chip")
    ok("A09-S04-F05" in pg.inner_text("#per-elegidos"), f"{nombre}: perfil elegido a mano desde la ficha")
    # Mis ejecuciones.
    pg.click("#per-tab-ejecuciones")
    pg.wait_for_selector("#per-ejec-lista .per-item")
    ok(pg.locator("#per-ejec-lista .per-item").count() == 1 and "Simulada" in pg.inner_text("#per-ejec-lista"), f"{nombre}: la ejecución quedó guardada y rotulada")
    pg.click("#per-ejec-lista .per-item")
    pg.wait_for_selector("#per-ejec-abierta #per-resumen")
    ok(pg.locator("#per-ejec-abierta .per-paso").count() == 3, f"{nombre}: el resumen guardado se puede volver a abrir")
    # Teclado: flechas entre pestañas.
    pg.focus("#per-tab-ejecuciones")
    pg.keyboard.press("ArrowLeft")
    ok(pg.get_attribute("#per-tab-coordinador", "aria-selected") == "true", f"{nombre}: pestañas navegables con flechas")
    # Volver a Ajustes.
    pg.click(".per-cab .per-volver")
    ok(pg.locator("#v-config.on").count() == 1 and pg.locator("#v-perfiles.on").count() == 0, f"{nombre}: «Volver a Ajustes» funciona")
    pg.click("#n-inicio")
    ok(pg.locator("#v-inicio.on").count() == 1 and pg.locator("#v-perfiles.on").count() == 0, f"{nombre}: al cambiar de sección Perfiles se oculta")


with sync_playwright() as p:
    nav = p.chromium.launch()
    for nombre, ancho, alto in (("escritorio", 1280, 900), ("celular", 390, 844)):
        ctx = nav.new_context(viewport={"width": ancho, "height": alto})
        pg = preparar(ctx, nombre)
        entrar(pg, nombre)
        registro(pg, nombre)
        coordinador(pg, nombre)
        csp = pg.evaluate("window.__csp")
        ok(csp == [], f"{nombre}: cero violaciones de CSP {csp or ''}")
        ctx.close()
    nav.close()

ok(not errores, f"cero errores de consola {errores[:5] or ''}")
print(f"\nCapturas: {OUT}")
print(f"{'TODO BIEN' if not fallos else str(len(fallos)) + ' FALLOS'}")
sys.exit(1 if fallos else 0)
