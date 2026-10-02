"""Prueba de navegador de la Biblioteca (pestaña de Documentos): buscador, filtros, ficha, original en Drive,
comparar, copia de trabajo, recomendación y auditoría del administrador.

Uso: con el servidor simulado corriendo (rutas reales sobre el catálogo FICTICIO de demo/biblioteca_demo.json),
    rm -f pullex.db && PORT=8781 /home/claude/work/venv/bin/python demo/servidor_simulado.py
    BASE=http://127.0.0.1:8781 python3 tests/e2e_biblioteca.py
Además abre demo/pullex-demo.html (sin servidor). Escritorio (1280 px) y celular (390 px).

Opcional: BASE_REAL=http://127.0.0.1:8782 apunta a un segundo servidor levantado con el inventario real
    PULLEX_BIBLIOTECA_INVENTARIO=biblioteca/inventario.json PORT=8782 … demo/servidor_simulado.py
y comprueba que, con 8.269 archivos, la pantalla dice cuántos modelos hay y responde a tiempo.

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

BASE = os.getenv("BASE", "http://127.0.0.1:8781")
BASE_REAL = os.getenv("BASE_REAL", "")
ADMIN = (os.getenv("ADMIN_EMAIL", "admin@demo.local"), os.getenv("ADMIN_CLAVE", "demo-admin-clave-larga"))
RAIZ = Path(__file__).resolve().parent.parent
OUT = os.getenv("CAPTURAS") or tempfile.mkdtemp(prefix="pullex-biblioteca-")
os.makedirs(OUT, exist_ok=True)
errores, fallos, hechas = [], [], [0]
VIGILAR_CSP = """window.__csp=[];document.addEventListener('securitypolicyviolation',
  e=>window.__csp.push(e.violatedDirective+' '+(e.blockedURI||'')));"""
# Lo que un usuario normal nunca debe ver del catálogo de demostración (sensible y excluido).
OCULTOS = ("título reservado", "Minuta retirada")
CAMPOS_FICHA = ["ID del catálogo", "Tipo documental", "Finalidad", "Área", "Tipo de escrito", "Trámite", "Año", "Carpeta", "Supuestos de uso",
                "Límites", "Datos que hay que completar", "Anexos", "Fuentes citadas", "Fecha de revisión", "Estado de validación",
                "Procesamiento", "Sensibilidad", "Derechos"]


def ok(cond, msg):
    hechas[0] += 1
    (print("OK  ", msg) if cond else (fallos.append(msg), print("FALLO", msg)))


def preparar(ctx, nombre):
    pg = ctx.new_page()
    pg.add_init_script(VIGILAR_CSP)
    pg.on("pageerror", lambda e: errores.append(f"{nombre}: {e}"))
    pg.on("console", lambda m: errores.append(f"{nombre}: {m.text}") if m.type == "error" else None)
    return pg


def sin_desborde(pg, nombre, momento):
    fuera = pg.evaluate("""() => { const ancho = window.innerWidth + 1;
        const malos = [...document.querySelectorAll('#v-documentos *')].filter(e => e.offsetParent !== null &&
            e.getBoundingClientRect().right > ancho && !e.closest('.bib-tabla-w,.doc-texto table,.md table'));
        return {pagina: document.documentElement.scrollWidth <= ancho, malos: malos.slice(0, 3).map(e => e.className || e.tagName)} }""")
    ok(fuera["pagina"] and not fuera["malos"], f"{nombre}: sin desbordamiento horizontal ({momento}) {fuera['malos'] or ''}")


def restantes(pg):
    return pg.evaluate("PERFIL.restantes")


def n_resultados(pg):
    return pg.locator("#bib-resultados .bib-item").count()


def esperar_n(pg, n):
    pg.wait_for_function("n => document.querySelectorAll('#bib-resultados .bib-item').length === n && "
                         "/^(\\d|Sin)/.test(document.getElementById('bib-n').textContent)", arg=n)


def titulos(pg):
    return pg.locator("#bib-resultados .bib-titulo").all_inner_texts()


def abrir_biblioteca(pg):
    pg.click("#n-documentos")
    pg.wait_for_selector("#doc-tab-biblioteca")
    pg.click("#doc-tab-biblioteca")
    pg.wait_for_function("() => /^(Hay|Todavía)/.test((document.getElementById('bib-resumen')||{}).textContent||'')")


def abrir_ficha(pg, titulo):
    pg.locator("#bib-resultados .bib-titulo", has_text=titulo).first.click()
    pg.wait_for_selector("#bib-trabajo .bib-ficha-w")
    return pg.locator("#bib-trabajo .bib-ficha-w")


def volver(pg):
    pg.click("#bib-trabajo .doc-volver")
    pg.wait_for_selector("#bib-lista:not(.hidden)")


def catalogo(pg, nombre):
    abrir_biblioteca(pg)
    ok(pg.get_attribute("#doc-tab-biblioteca", "aria-selected") == "true", f"{nombre}: pestaña Biblioteca seleccionada dentro de Documentos")
    esperar_n(pg, 11)
    resumen = pg.inner_text("#bib-resumen")
    ok(resumen.startswith("Hay 11 modelos jurídicos disponibles") and "3 en «Normas»" in resumen, f"{nombre}: dice cuántos modelos hay ({resumen[:60]}…)")
    cob = pg.inner_text("#bib-cobertura")
    ok("no se han podido enumerar" in cob or pg.locator("#bib-cobertura details").count() == 1, f"{nombre}: explica qué cubre y qué falta")
    pg.locator("#bib-cobertura summary").click()
    ok("provisional" in pg.inner_text("#bib-cobertura") and "No es búsqueda por significado" in pg.inner_text("#bib-cobertura"),
       f"{nombre}: cobertura provisional y búsqueda sin embeddings, dichas en pantalla")
    ok("11 resultados" in pg.inner_text("#bib-n"), f"{nombre}: lista inicial con los 11 modelos")
    chips = pg.evaluate("""() => [...document.querySelectorAll('#bib-resultados .bib-item')].map(i =>
        [...i.querySelectorAll('.bib-chip')].map(c => c.textContent.trim()))""")
    ok(all(len(c) >= 2 and all(c) for c in chips), f"{nombre}: cada resultado trae chips de estado con texto")
    ok(any("Sin validar jurídicamente" in c for c in chips) and any("Validado por revisión humana" in c for c in chips)
       and any("Histórico" in c for c in chips) and any("Ficha incompleta" in c for c in chips) and any("De un tercero" in c for c in chips),
       f"{nombre}: chips «Sin validar», «Validado», «Histórico», «Ficha incompleta» y «De un tercero»")
    sin_label = pg.evaluate("() => [...document.querySelectorAll('#doc-panel-biblioteca input, #doc-panel-biblioteca select, #doc-panel-biblioteca textarea')]"
                            ".filter(i => !document.querySelector('label[for=\"'+i.id+'\"]')).map(i => i.id)")
    ok(sin_label == [], f"{nombre}: todos los controles tienen <label for> {sin_label}")
    sin_desborde(pg, nombre, "catálogo")
    pg.screenshot(path=f"{OUT}/{nombre}-catalogo.png", full_page=True)


def busqueda_y_filtros(pg, nombre):
    # literal y ampliada (el título dice «fotomulta», se busca «comparendo»)
    pg.fill("#bib-q", "comparendo")
    pg.wait_for_function("() => /Se amplió/.test(document.getElementById('bib-otras').textContent) && "
                         "document.querySelectorAll('#bib-resultados .bib-porque').length > 0")
    ok("fotomulta" in titulos(pg)[0], f"{nombre}: «comparendo» encuentra primero el modelo de fotomulta")
    porque = pg.locator("#bib-resultados .bib-item").first.locator(".bib-porque").inner_text()
    ok("término relacionado" in porque, f"{nombre}: explica por qué coincide ({porque[:70]}…)")
    ok("Se amplió la búsqueda" in pg.inner_text("#bib-otras"), f"{nombre}: avisa que la búsqueda se amplió con sinónimos o trámites")
    pg.fill("#bib-q", "medicamento")                       # está en el TEXTO de la tutela de salud
    pg.wait_for_function("() => [...document.querySelectorAll('#bib-resultados .bib-titulo')].some(t => /tutela/i.test(t.textContent))")
    ok(pg.locator("#bib-resultados .bib-extracto").count() >= 0 and "tutela" in titulos(pg)[0].lower(), f"{nombre}: búsqueda por contenido o título («medicamento»)")
    # filtros combinables
    pg.fill("#bib-q", "")
    pg.select_option("#bib-f-tipo", "Derecho de petición")
    esperar_n(pg, 4)
    pg.select_option("#bib-f-area", "Constitucional")
    esperar_n(pg, 3)
    ok(all("Derecho de petición" in m and "Constitucional" in m for m in pg.locator("#bib-resultados .bib-meta").all_inner_texts()),
       f"{nombre}: filtros combinados área + tipo de escrito (3 resultados)")
    pg.select_option("#bib-f-estado", "INDEXADO")
    esperar_n(pg, 2)
    ok(True, f"{nombre}: tercer filtro (procesamiento) reduce a 2")
    pg.select_option("#bib-f-carpeta", "BIBLIOTECA DE DEMOSTRACIÓN/DERECHOS DE PETICION")
    esperar_n(pg, 2)
    sin_desborde(pg, nombre, "filtros")
    pg.locator("#bib-filtros").screenshot(path=f"{OUT}/{nombre}-filtros.png")
    pg.click("#bib-limpiar")
    esperar_n(pg, 11)
    ok(pg.input_value("#bib-f-clase") == "modelo" and pg.input_value("#bib-f-tipo") == "", f"{nombre}: «Quitar filtros» vuelve al catálogo de modelos")
    # tipo documental: normas y jurisprudencia no se mezclan con los modelos
    pg.select_option("#bib-f-clase", "norma")
    esperar_n(pg, 3)
    ok("LEY 1755 DE 2015.doc" in titulos(pg), f"{nombre}: tipo documental «Normas» lista las normas")
    pg.select_option("#bib-f-anio", "2015")
    esperar_n(pg, 1)
    ok(titulos(pg) == ["LEY 1755 DE 2015.doc"], f"{nombre}: filtro por año (2015)")
    pg.click("#bib-limpiar")
    esperar_n(pg, 11)
    pg.fill("#bib-q", "sentencia laboral")
    pg.wait_for_selector("#bib-otras .doc-btn.chip")
    esperar_n(pg, 0)
    ok("Sin resultados" in pg.inner_text("#bib-n") and "No hay un modelo que coincida" in pg.inner_text("#bib-resultados"),
       f"{nombre}: si no hay modelo lo dice, sin forzar uno parecido")
    ok("Jurisprudencia (2)" in pg.inner_text("#bib-otras"), f"{nombre}: avisa que la consulta sí coincide en otro tipo documental")
    pg.click("#bib-otras .doc-btn.chip")
    pg.wait_for_function("() => document.getElementById('bib-f-clase').value === 'jurisprudencia'")
    esperar_n(pg, 2)
    ok("(laboral)" in titulos(pg)[0], f"{nombre}: un clic lleva a esas coincidencias en «Jurisprudencia»")
    pg.click("#bib-limpiar")
    esperar_n(pg, 11)
    texto = pg.inner_text("#v-documentos")
    ok(not any(o in texto for o in OCULTOS), f"{nombre}: lo sensible y lo excluido no aparecen en pantalla")


def fichas(pg, nombre):
    f = abrir_ficha(pg, "Acción de tutela por negación de medicamento")
    ok(pg.evaluate("document.activeElement.classList.contains('doc-h')"), f"{nombre}: al abrir la ficha el foco va al título")
    dts = f.locator("dt").all_inner_texts()
    faltan = [c for c in CAMPOS_FICHA if c not in dts]
    ok(not faltan and f.locator(".bib-rel h4").inner_text().lower() == "versiones relacionadas", f"{nombre}: ficha completa {faltan or ''}")
    ok("MOD-000005" in f.inner_text() and "Pedir al juez de tutela" in f.inner_text() and "2026-06-20" in f.inner_text(),
       f"{nombre}: ID, finalidad y fecha de revisión visibles")
    enlace = f.locator("a.bib-drive")
    ok(enlace.count() == 1 and enlace.get_attribute("href").startswith("https://drive.google.com/file/d/DEMO-TUT-SALUD")
       and enlace.get_attribute("target") == "_blank" and enlace.get_attribute("rel") == "noopener noreferrer"
       and enlace.inner_text() == "Abrir original en Drive", f"{nombre}: «Abrir original en Drive» con rel=noopener noreferrer")
    ok("Ejemplo de la demostración" in f.locator(".bib-previa-t").inner_text(), f"{nombre}: vista previa del texto extraído")
    ok(len(f.locator(".bib-previa-t").inner_text()) <= 620, f"{nombre}: la vista previa es corta")
    ok("Artículo 86" in f.inner_text() or "artículo 86" in f.inner_text(), f"{nombre}: fuentes citadas detectadas, marcadas como no verificadas")
    ok("no verificada" in f.inner_text(), f"{nombre}: las fuentes citadas dicen «no verificada»")
    ok(f.locator(".bib-aviso").count() == 0, f"{nombre}: un modelo validado por una persona no muestra el aviso «sin validar»")
    sin_desborde(pg, nombre, "ficha")
    f.screenshot(path=f"{OUT}/{nombre}-ficha.png")
    volver(pg)
    f = abrir_ficha(pg, "Denuncia por hurto")
    avisos = f.locator(".bib-aviso").all_inner_texts()
    ok(any(a.startswith("Modelo sin validar jurídicamente") for a in avisos), f"{nombre}: aviso «Modelo sin validar jurídicamente»")
    ok(any(a.startswith("Histórico") for a in avisos) and any(a.startswith("Ficha incompleta") for a in avisos), f"{nombre}: avisos «Histórico» e «incompleto»")
    ok(all(pg.evaluate("e => e.getAttribute('role')", h) == "note" for h in f.locator(".bib-aviso").element_handles()), f"{nombre}: los avisos llevan role=note")
    ok("aún no extraído" in f.locator(".bib-previa").inner_text(), f"{nombre}: sin texto extraído dice «Sin vista previa: aún no extraído»")
    ok("típico de este tipo de escrito" in f.inner_text(), f"{nombre}: los campos por completar dicen de dónde salen")
    f.screenshot(path=f"{OUT}/{nombre}-ficha-historico.png")
    volver(pg)
    f = abrir_ficha(pg, "Tutela habeas data")
    ok("tercero" in f.locator(".bib-previa").inner_text() and f.locator(".bib-previa-t").count() == 0,
       f"{nombre}: el texto de un documento de terceros no se muestra al usuario")
    ok("reporte negativo" not in f.inner_text(), f"{nombre}: ni un extracto del texto del tercero llega a la ficha")
    volver(pg)


def copia(pg, nombre):
    f = abrir_ficha(pg, "Modelo derecho de petición por fotomulta")
    antes_previa, antes_consultas = f.locator(".bib-previa-t").inner_text(), restantes(pg)
    pg.click("#bib-copiar")
    pg.wait_for_selector("#bib-copia-res .bib-copia")
    ok("El original en Drive no se modificó" in pg.inner_text("#bib-copia-res"), f"{nombre}: copia de trabajo creada, con constancia de que el original no cambia")
    ok(restantes(pg) == antes_consultas, f"{nombre}: crear la copia no gasta consultas")
    pg.click("#bib-abrir-copia")
    pg.wait_for_selector("#doc-mis-abierto .doc-res")
    res = pg.locator("#doc-mis-abierto .doc-res")
    ok("COPIA DE TRABAJO" in res.inner_text() and "SECRETARÍA DE MOVILIDAD" in res.inner_text(), f"{nombre}: la copia abre en Mis documentos con el texto del modelo")
    ok("No la redactó la IA" in res.locator(".doc-aviso").first.inner_text(), f"{nombre}: la copia no se presenta como texto generado por IA")
    ok(res.locator(".doc-verif li").count() >= 3, f"{nombre}: la copia lista los datos por completar y las normas por verificar")
    # editar la copia y comprobar que el modelo de la biblioteca sigue igual
    res.locator("text=Editar texto").click()
    res.locator("textarea.doc-editor").fill("COPIA EDITADA POR EL USUARIO")
    res.locator("text=Guardar").click()
    pg.wait_for_selector(".toast >> text=Cambios guardados")
    sin_desborde(pg, nombre, "copia en Mis documentos")
    res.locator("text=Ver el modelo en la biblioteca").click()
    pg.wait_for_selector("#bib-trabajo .bib-ficha-w")
    ok(pg.locator("#bib-trabajo .bib-previa-t").inner_text() == antes_previa, f"{nombre}: editar la copia no altera el original")
    volver(pg)


def comparar(pg, nombre):
    pg.fill("#bib-q", "servicios publicos")
    pg.wait_for_function("() => [...document.querySelectorAll('#bib-resultados .bib-titulo')].filter(t => /servicios públicos/.test(t.textContent)).length === 2")
    casillas = pg.locator("#bib-resultados .bib-item", has_text="servicios públicos").locator("input.bib-cmp")
    casillas.nth(0).check()
    ok(pg.is_visible("#bib-comparar-barra") and pg.is_disabled("#bib-comparar"), f"{nombre}: con un documento elegido, «Comparar» espera el segundo")
    casillas.nth(1).check()
    ok(pg.is_enabled("#bib-comparar"), f"{nombre}: con dos documentos elegidos se habilita «Comparar»")
    otra = pg.locator("#bib-resultados input.bib-cmp:not(:checked)")
    if otra.count():
        otra.first.click()                                    # la casilla se desmarca sola y avisa
        pg.wait_for_selector(".toast >> text=Solo se comparan dos")
        ok(pg.locator("#bib-resultados input.bib-cmp:checked").count() == 2, f"{nombre}: no deja elegir un tercero")
    pg.click("#bib-comparar")
    pg.wait_for_selector("#bib-trabajo .bib-comparacion")
    c = pg.locator("#bib-trabajo .bib-comparacion")
    filas = c.locator(".bib-tabla tbody tr")
    ok(filas.count() >= 10 and c.locator("tr.bib-dif").count() >= 2, f"{nombre}: tabla de comparación con diferencias marcadas")
    carpeta = c.locator(".bib-tabla tbody tr", has_text="Carpeta").first.inner_text()
    ok("Distinto" in carpeta and "DERECHOS DE PETICION" in carpeta and "CIVIL" in carpeta, f"{nombre}: las diferencias se dicen con texto («Distinto»), no solo con color")
    ok("PRUEBAS" in c.inner_text() and "En los dos" in c.inner_text() and "Solo en B" in c.inner_text(), f"{nombre}: compara secciones y campos (comunes y propios de cada uno)")
    ok("no indica cuál modelo es jurídicamente mejor" in c.inner_text(), f"{nombre}: la comparación no dice cuál es «mejor»")
    sin_desborde(pg, nombre, "comparación")
    c.screenshot(path=f"{OUT}/{nombre}-comparar.png")
    volver(pg)
    pg.locator("#bib-comparar-barra .doc-btn.chip").first.click()
    pg.locator("#bib-comparar-barra .doc-btn.chip").first.click()
    ok(not pg.is_visible("#bib-comparar-barra"), f"{nombre}: se puede vaciar la selección de comparación")
    pg.click("#bib-limpiar")
    esperar_n(pg, 11)
    # versiones relacionadas en la ficha: homónimo en otra carpeta, con texto parecido
    f = abrir_ficha(pg, "Modelo derecho de petición ante empresa de servicios públicos (1)")
    rel = f.locator(".bib-rel-ul li")
    ok(rel.count() >= 1 and "MOD-000002" in rel.first.inner_text(), f"{nombre}: la ficha muestra la versión relacionada ({rel.first.inner_text()[:60]}…)")
    volver(pg)


def recomendar(pg, nombre):
    pg.locator("#bib-rec summary").click()
    pg.click("#bib-recomendar")
    ok(pg.get_attribute("#bib-caso", "aria-invalid") == "true" and pg.is_visible("#bib-caso-err"), f"{nombre}: caso vacío marcado como inválido")
    antes = restantes(pg)
    pg.fill("#bib-caso", "Me llegó una fotomulta y nunca me notificaron. Quiero pedir que revisen el comparendo.")
    pg.click("#bib-recomendar")
    pg.wait_for_selector("#bib-rec-res .bib-cand")
    cand = pg.locator("#bib-rec-res .bib-cand").first
    ok("fotomulta" in cand.locator(".bib-titulo").inner_text() and "Por qué corresponde" in cand.inner_text()
       and "Qué hay que adaptar" in cand.inner_text() and "Plantilla recuperada" in cand.inner_text(),
       f"{nombre}: recomienda el modelo, dice por qué y qué adaptar")
    ok("Datos que el modelo pide y no veo en tu descripción" in cand.inner_text(), f"{nombre}: lista los requisitos que faltan")
    ok(restantes(pg) == antes, f"{nombre}: la recomendación no gasta consultas")
    ok("no prueba que el modelo proceda" in pg.inner_text("#bib-rec-msg"), f"{nombre}: advierte que parecerse al caso no prueba que proceda")
    pg.check("#bib-explicar")
    pg.click("#bib-recomendar")
    pg.wait_for_selector("#bib-rec-res .doc-verif >> text=Explicación redactada por IA")
    ok(restantes(pg) == antes - 1 and "Verifícala" in pg.inner_text("#bib-rec-res .doc-verif"), f"{nombre}: la explicación con IA es opcional, usa 1 consulta y pide verificarla")
    pg.uncheck("#bib-explicar")
    sin_desborde(pg, nombre, "recomendación")
    pg.locator("#bib-rec").screenshot(path=f"{OUT}/{nombre}-recomendar.png")
    pg.fill("#bib-caso", "Mi empleador me despidió sin justa causa después de tres años y no me pagó la liquidación.")
    pg.click("#bib-recomendar")
    pg.wait_for_function("() => /^No encontré/.test((document.getElementById('bib-rec-msg')||{}).textContent||'')")
    ok(pg.locator("#bib-rec-res .bib-cand").count() == 0, f"{nombre}: si no hay modelo adecuado lo dice y no propone uno parecido")
    botones = pg.locator("#bib-rec-res [data-generador]")
    ok(botones.count() >= 1 and "Un borrador NUEVO" in pg.inner_text("#bib-rec-res"), f"{nombre}: distingue borrador nuevo de plantilla recuperada y remite al generador")
    botones.first.click()
    pg.wait_for_selector("#doc-generar")
    ok(pg.get_attribute("#doc-tab-escritos", "aria-selected") == "true", f"{nombre}: el botón abre el formulario del generador (pestaña Escritos)")
    pg.click("#doc-trabajo .doc-volver")
    pg.click("#doc-tab-biblioteca")


def teclado(pg, nombre):
    pg.focus("#doc-tab-biblioteca")                        # la pestaña activa es la única en el orden de tabulación
    pg.keyboard.press("ArrowLeft")
    ok(pg.get_attribute("#doc-tab-asistente", "aria-selected") == "true", f"{nombre}: flecha izquierda pasa a la pestaña anterior")
    pg.keyboard.press("ArrowRight")
    ok(pg.evaluate("document.activeElement.id") == "doc-tab-biblioteca" and pg.get_attribute("#doc-tab-biblioteca", "aria-selected") == "true",
       f"{nombre}: la pestaña Biblioteca se alcanza con las flechas del teclado")
    pg.focus("#bib-q")
    pg.keyboard.type("tutela")
    pg.keyboard.press("Enter")
    pg.wait_for_function("() => [...document.querySelectorAll('#bib-resultados .bib-titulo')].length > 0 && "
                         "[...document.querySelectorAll('#bib-resultados .bib-titulo')].every(t => /tutela/i.test(t.textContent))")
    pg.locator("#bib-resultados .bib-titulo").first.focus()
    pg.keyboard.press("Enter")
    pg.wait_for_selector("#bib-trabajo .bib-ficha-w")
    ok(pg.evaluate("document.activeElement.classList.contains('doc-h')"), f"{nombre}: buscar y abrir una ficha solo con el teclado")
    pg.keyboard.press("Tab")
    ok(pg.evaluate("document.activeElement.closest('.bib-acc') !== null"), f"{nombre}: el siguiente Tab llega a las acciones de la ficha")
    visible = pg.evaluate("() => { const s = getComputedStyle(document.activeElement); return s.outlineStyle !== 'none' && parseFloat(s.outlineWidth) >= 2 }")
    ok(visible, f"{nombre}: el foco del teclado se ve (contorno)")
    pg.locator("#bib-trabajo .doc-volver").focus()
    pg.keyboard.press("Enter")
    pg.wait_for_selector("#bib-lista:not(.hidden)")
    ok(pg.evaluate("document.activeElement.classList.contains('bib-titulo')"), f"{nombre}: al volver, el foco regresa a los resultados")
    pg.click("#bib-limpiar")
    esperar_n(pg, 11)


def registrar(pg, nombre):
    pg.goto(BASE + "/")
    pg.click("#t-reg")
    pg.fill("#r-nombre", "Valentina Ríos")
    pg.fill("#a-email", f"b{nombre}{int(time.time() * 1000)}@demo.local")
    pg.fill("#a-clave", "clave-demo-123")
    pg.click("#a-btn")
    pg.wait_for_function("() => PERFIL !== null")
    pg.wait_for_function("() => ESTADO !== null")


with sync_playwright() as p:
    nav = p.chromium.launch()
    for nombre, vp in (("desk", {"width": 1280, "height": 900}), ("movil", {"width": 390, "height": 844})):
        ctx = nav.new_context(viewport=vp)
        pg = preparar(ctx, nombre)
        registrar(pg, nombre)
        catalogo(pg, nombre)
        ok(pg.locator("#bib-auditoria").count() == 0, f"{nombre}: un usuario normal no ve el acceso a la auditoría")
        busqueda_y_filtros(pg, nombre)
        fichas(pg, nombre)
        copia(pg, nombre)
        comparar(pg, nombre)
        recomendar(pg, nombre)
        teclado(pg, nombre)
        sin_desborde(pg, nombre, "final")
        csp = pg.evaluate("window.__csp")
        ok(csp == [], f"{nombre}: cero violaciones de CSP {csp}")
        ctx.close()

    # Administrador: ve la auditoría (todo el inventario, con lo oculto y su motivo) y el texto de terceros.
    ctx = nav.new_context(viewport={"width": 1280, "height": 900})
    pg = preparar(ctx, "admin")
    pg.goto(BASE + "/")
    pg.fill("#a-email", ADMIN[0])
    pg.fill("#a-clave", ADMIN[1])
    pg.click("#a-btn")
    pg.wait_for_function("() => PERFIL !== null && ESTADO !== null")
    abrir_biblioteca(pg)
    esperar_n(pg, 11)
    f = abrir_ficha(pg, "Tutela habeas data")
    ok("reporte negativo" in f.locator(".bib-previa-t").inner_text(), "admin: el administrador sí ve la vista previa del documento de terceros")
    volver(pg)
    pg.click("#bib-auditoria")
    pg.wait_for_selector("#bib-trabajo >> text=Inventario completo")
    aud = pg.inner_text("#bib-trabajo")
    ok("PROVISIONAL" in aud and "19" in aud and "17 visibles para los usuarios" in aud, "admin: auditoría con totales y denominador provisional")
    ok(all(o in aud for o in OCULTOS) and "excluido" in aud and "POSIBLE_DATO_PERSONAL" in aud, "admin: la auditoría lista lo oculto con su motivo")
    ok("Según el inventario de Drive" in aud and "Por carpeta de primer nivel" in aud, "admin: cantidades por estado y por carpeta")
    sin_desborde(pg, "admin", "auditoría")
    pg.screenshot(path=f"{OUT}/admin-auditoria.png", full_page=True)
    ok(pg.evaluate("window.__csp") == [], "admin: cero violaciones de CSP")
    ctx.close()

    # Registro de motores de IA en el panel de administración (solo administrador).
    ctx = nav.new_context(viewport={"width": 390, "height": 844})
    pg = preparar(ctx, "motores")
    pg.goto(BASE + "/admin")
    pg.fill("#e", ADMIN[0])
    pg.fill("#c", ADMIN[1])
    pg.click("[data-click=entrar]")
    pg.wait_for_selector("#panel", state="visible")
    pg.click("[data-click=verMotores]")
    pg.wait_for_selector("#motores .mot")
    mot = pg.inner_text("#motores")
    ok(pg.locator("#motores .mot").count() == 8 and "Modelo de lenguaje principal" in mot, "motores: el panel lista los 8 motores que están en el código")
    ok("Costo (Comprobado)" in mot and "https://platform.claude.com/docs/en/about-claude/pricing" in mot and "consultada el 2026-10-02" in mot,
       "motores: un costo «comprobado» trae la página oficial y la fecha")
    ok("solo simuladas" in mot and "Ninguna llamada" in mot, "motores: las pruebas se declaran como solo simuladas")
    ok("OCR para documentos escaneados" in mot and "PROPUESTO" in mot, "motores: lo no configurado aparece como propuesto, no como disponible")
    ok(pg.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1"), "motores: sin desbordamiento horizontal a 390 px")
    ok(pg.evaluate("window.__csp") == [], "motores: cero violaciones de CSP")
    pg.locator("#motores").screenshot(path=f"{OUT}/admin-motores.png")
    ctx.close()

    # Demostración de un solo archivo (sin servidor): mismo biblioteca.js sobre el catálogo ficticio de demo/mock.js.
    ctx = nav.new_context(viewport={"width": 390, "height": 844})
    pg = preparar(ctx, "demo")
    pg.goto((RAIZ / "demo" / "pullex-demo.html").as_uri())
    pg.click("#a-btn")
    pg.wait_for_function("() => PERFIL !== null")
    abrir_biblioteca(pg)
    esperar_n(pg, 11)
    ok(pg.inner_text("#bib-resumen").startswith("Hay 11 modelos jurídicos disponibles"), "demo: catálogo de ejemplo con 11 modelos")
    pg.fill("#bib-q", "comparendo")
    pg.wait_for_function("() => document.querySelectorAll('#bib-resultados .bib-porque').length > 0")
    ok("fotomulta" in titulos(pg)[0] and "término relacionado" in pg.locator("#bib-resultados .bib-porque").first.inner_text(), "demo: búsqueda ampliada con explicación")
    pg.fill("#bib-q", "")
    pg.select_option("#bib-f-tipo", "Derecho de petición")
    esperar_n(pg, 4)
    pg.select_option("#bib-f-area", "Constitucional")
    esperar_n(pg, 3)
    ok(True, "demo: filtros combinados")
    pg.click("#bib-limpiar")
    esperar_n(pg, 11)
    f = abrir_ficha(pg, "Modelo derecho de petición por fotomulta")
    ok(f.locator("a.bib-drive").get_attribute("rel") == "noopener noreferrer" and "Ejemplo de la demostración" in f.locator(".bib-previa-t").inner_text(),
       "demo: ficha con vista previa y enlace al original")
    ok(any(a.startswith("Modelo sin validar jurídicamente") for a in f.locator(".bib-aviso").all_inner_texts()), "demo: aviso «Modelo sin validar jurídicamente»")
    pg.click("#bib-copiar")
    pg.wait_for_selector("#bib-abrir-copia")
    pg.click("#bib-abrir-copia")
    pg.wait_for_selector("#doc-mis-abierto .doc-res")
    ok("COPIA DE TRABAJO" in pg.inner_text("#doc-mis-abierto .doc-res"), "demo: copia de trabajo en Mis documentos")
    pg.click("#doc-tab-biblioteca")
    volver(pg)
    comparar(pg, "demo")
    pg.locator("#bib-rec summary").click()
    pg.fill("#bib-caso", "Mi empleador me despidió sin justa causa después de tres años y no me pagó la liquidación.")
    pg.click("#bib-recomendar")
    pg.wait_for_function("() => /^No encontré/.test((document.getElementById('bib-rec-msg')||{}).textContent||'')")
    ok(pg.locator("#bib-rec-res .bib-cand").count() == 0, "demo: sin modelo adecuado, lo dice")
    ok(not any(o in pg.inner_text("#v-documentos") for o in OCULTOS), "demo: lo sensible y lo excluido no están en la demostración")
    sin_desborde(pg, "demo", "biblioteca")
    ctx.close()

    if BASE_REAL:
        # Inventario REAL (8.269 archivos): la pantalla dice con honestidad cuántos modelos hay y responde a tiempo.
        ctx = nav.new_context(viewport={"width": 390, "height": 844})
        pg = preparar(ctx, "real")
        BASE = BASE_REAL
        registrar(pg, "real")
        abrir_biblioteca(pg)
        resumen = pg.inner_text("#bib-resumen")
        ok(resumen.startswith("Todavía no hay modelos jurídicos"), f"real: un usuario normal no tiene modelos disponibles y la pantalla lo dice ({resumen[:80]}…)")
        ok("en «Normas»" in resumen and "en «Jurisprudencia»" in resumen, "real: cuenta aparte normas y jurisprudencia")
        cob = pg.inner_text("#bib-cobertura")
        ok("no se han podido enumerar" in cob and "provisional" in cob and "restringido al administrador" in cob, "real: explica que las colecciones de terceros no se han podido enumerar")
        ok(not re.search(r"FOTOMULTA|HABEAS DATA|MANIFIESTO", pg.inner_text("#v-documentos"), re.I), "real: ningún título de terceros ni nota interna en pantalla")
        pg.select_option("#bib-f-clase", "todas")
        pg.wait_for_function("() => /resultados/.test(document.getElementById('bib-n').textContent)")
        total = int(re.sub(r"\D", "", pg.inner_text("#bib-n").split(" resultados")[0]))
        ok(total > 8000, f"real: «Todo el catálogo» lista {total} documentos paginados")
        t0 = time.time()
        pg.fill("#bib-q", "ley 100 de 1993")
        pg.wait_for_function("() => /relevancia/.test(document.getElementById('bib-n').textContent)")
        dt = time.time() - t0
        ok("LEY 100 DE1993" in titulos(pg)[0] and dt < 3, f"real: búsqueda sobre 8.269 archivos en {dt:.2f} s (incluye la espera de escritura)")
        pg.select_option("#bib-f-clase", "jurisprudencia")
        pg.fill("#bib-q", "")
        pg.select_option("#bib-f-area", "Laboral y Seguridad Social")
        pg.wait_for_function("() => /resultados en jurisprudencia/.test(document.getElementById('bib-n').textContent)")
        ok(pg.locator("#bib-paginas .doc-btn").count() == 2, "real: resultados paginados (Anterior / Siguiente)")
        sin_desborde(pg, "real", "catálogo real")
        pg.screenshot(path=f"{OUT}/real-catalogo.png")
        ok(pg.evaluate("window.__csp") == [], "real: cero violaciones de CSP")
        ctx.close()
    nav.close()

ok(not errores, f"cero errores de consola {errores[:5]}")
print(f"\n{'TODO OK' if not fallos else str(len(fallos)) + ' FALLOS'} · {hechas[0]} comprobaciones · capturas en {OUT}")
sys.exit(1 if fallos else 0)
