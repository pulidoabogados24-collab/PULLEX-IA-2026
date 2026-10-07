"""Movimiento de la interfaz (static/movimiento.css y static/movimiento.js): reglas que no deben romperse.

No prueban cómo se ve una animación (eso se revisa en el navegador); cuidan los límites acordados en
docs/12-DISENO-Y-APARIENCIA.md: tokens con nombre, apagado con movimiento reducido, nada que quede oculto si
JavaScript no carga, solo propiedades baratas de animar y el cascarón al día en el service worker.
"""
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
ST = RAIZ / "static"


def leer(nombre):
    return (ST / nombre).read_text(encoding="utf-8")


def sin_comentarios(css):
    return re.sub(r"/\*.*?\*/", "", css, flags=re.S)


def test_MOV_001_tokens_de_movimiento_en_el_tema():
    tema = leer("tema.css")
    for token in ("--mv-instante", "--mv-rapida", "--mv-media", "--mv-lenta", "--mv-escena",
                  "--mv-entra", "--mv-sale", "--mv-enfasis", "--mv-paso", "--mv-giro", "--mv-pulso", "--mv-respira"):
        assert re.search(re.escape(token) + r":\s*[^;]+;", tema), token
    # Tres curvas DISTINTAS: una sola curva para todo es justo lo que se quiere evitar.
    curvas = {re.search(rf"--mv-{n}:\s*(cubic-bezier\([^)]*\))", tema).group(1) for n in ("entra", "sale", "enfasis")}
    assert len(curvas) == 3
    # Los nombres anteriores siguen existiendo (hay hojas que los usan).
    for alias in ("--t-rapida", "--t-media", "--curva"):
        assert alias + ":" in tema, alias


def test_MOV_002_la_pagina_carga_el_movimiento_y_antes_que_app_js():
    html = leer("index.html")
    assert html.count('<link rel="stylesheet" href="/static/movimiento.css">') == 1
    assert html.count('<script src="/static/movimiento.js"></script>') == 1
    # app.js usa window.MV si existe: movimiento.js tiene que ir antes.
    assert html.index("/static/movimiento.js") < html.index('<script src="/static/app.js">')
    # y después de justicia.css, para poder ajustar sus piezas
    assert html.index("/static/justicia.css") < html.index("/static/movimiento.css")


def test_MOV_003_el_cascaron_del_service_worker_esta_al_dia():
    sw = leer("sw.js")
    version = re.search(r'const CACHE = "pullex-v(\d+)"', sw)
    assert version and int(version.group(1)) >= 7
    shell = re.findall(r'"(/static/[^"]+)"', sw)
    for ruta in ("/static/movimiento.css", "/static/movimiento.js", "/static/img/justicia-luz.webp"):
        assert ruta in shell, ruta
    for ruta in shell:                       # nada de la lista puede faltar en disco: addAll() fallaría entero
        assert (RAIZ / ruta.lstrip("/")).is_file(), ruta


def test_MOV_004_todo_el_movimiento_se_apaga_con_movimiento_reducido():
    css = sin_comentarios(leer("movimiento.css"))
    # 1) El interruptor de Ajustes apaga igual que la preferencia del sistema.
    assert re.search(r':root\[data-movimiento="reducido"\] \*[^{]*\{[^}]*animation-duration:\.001ms!important', css)
    # 2) Toda regla que anima vive dentro del bloque de movimiento completo… salvo las transiciones de opacidad
    #    de piezas que cambian de estado (aro, borde de luz) y la transición entre secciones, que movimiento.js
    #    no dispara con movimiento reducido.
    ini = css.index("@media (prefers-reduced-motion:no-preference)")
    fin = css.index(":root.mv-vt main")
    fuera = css[:ini] + css[fin:]
    fuera = re.sub(r"@keyframes[^{]+\{(?:[^{}]*\{[^{}]*\})*[^{}]*\}", "", fuera)
    fuera = re.sub(r"::view-transition-[^{]+\{[^}]*\}", "", fuera)
    for regla in re.findall(r"[^{}]+\{[^{}]*\}", fuera):
        if "!important" in regla:
            continue
        regla = regla.replace("animation:none", "")           # quitar una animación no es animar
        assert "animation:" not in regla and "animation-name" not in regla, regla.strip()[:120]
        for t in re.findall(r"transition:([^;}]+)", regla):
            assert re.fullmatch(r"\s*opacity var\(--mv-\w+\) ease\s*", t), regla.strip()[:120]
    assert ':root:not([data-movimiento="reducido"]){' in css[ini:fin]
    # 3) movimiento.js consulta las dos fuentes de la preferencia antes de mover nada.
    js = leer("movimiento.js")
    assert "prefers-reduced-motion: reduce" in js and "data-movimiento" in js


def test_MOV_005_duraciones_y_curvas_solo_con_tokens():
    css = sin_comentarios(leer("movimiento.css"))
    literales = []
    for decl in re.findall(r"(?:animation|transition)(?:-duration|-delay)?:([^;}]+)", css):
        if "!important" in decl:                            # apagado global
            continue
        if "mv-visible" in decl:                             # salvavidas: garantiza que nada se quede oculto
            continue
        sin_vars = re.sub(r"var\(--[\w-]+(?:,[^()]*)?\)", "", decl)
        if re.search(r"\d(?:\.\d+)?m?s\b", sin_vars):
            literales.append(decl.strip())
    assert not literales, literales
    assert "cubic-bezier" not in css                         # las curvas viven en tema.css


def test_MOV_010_ningun_giro_dura_mas_de_cinco_segundos():
    """Lo único que puede moverse indefinidamente es opacidad. Un giro (mv-gira) siempre lleva un número finito de
    vueltas que, con los periodos de tema.css, suma menos de cinco segundos."""
    tema, css = leer("tema.css"), sin_comentarios(leer("movimiento.css"))
    giro = float(re.search(r"--mv-giro:\s*([\d.]+)s", tema).group(1))
    usos = re.findall(r"mv-gira ([^,;}]+)", css)
    assert usos
    for uso in usos:
        assert "infinite" not in uso, uso
        factor = re.search(r"calc\(var\(--mv-giro\) \* ([\d.]+)\)", uso)
        vueltas = int(re.search(r"linear (\d+)", uso).group(1))
        assert giro * (float(factor.group(1)) if factor else 1) * vueltas < 5, uso
    kf = dict(re.findall(r"@keyframes ([\w-]+)\{((?:[^{}]*\{[^{}]*\})*)", css))
    for nombre in re.findall(r"animation:[^;}]*?(mv-[\w-]+)[^,;}]*infinite", css):
        assert set(re.findall(r"([a-z-]+):", kf[nombre])) == {"opacity"}, nombre


def test_MOV_006_solo_se_animan_propiedades_baratas():
    css = sin_comentarios(leer("movimiento.css"))
    permitidas = {"opacity", "transform", "clip-path", "outline-offset", "outline-color"}
    for nombre, cuerpo in re.findall(r"@keyframes ([\w-]+)\{((?:[^{}]*\{[^{}]*\})*)", css):
        for prop in re.findall(r"([a-z-]+):", cuerpo):
            assert prop in permitidas, f"{nombre} anima «{prop}»"
    assert "will-change" not in css
    for t in re.findall(r"transition:([^;}]+)", css):
        for parte in t.split(","):
            prop = parte.strip().split(" ")[0]
            assert prop in {"transform", "opacity", "background-color", "border-color", "box-shadow", "color"}, t


def test_MOV_007_nada_queda_oculto_esperando_a_javascript():
    """Los estados de partida ocultos solo pueden vivir dentro de una animación (fill backwards) o en clases que pone
    el propio movimiento.js y que llevan salvavidas en CSS."""
    css = sin_comentarios(leer("movimiento.css"))
    sin_kf = re.sub(r"@keyframes[^{]+\{(?:[^{}]*\{[^{}]*\})*[^{}]*\}", "", css)
    for selector, cuerpo in re.findall(r"([^{}]+)\{([^{}]*)\}", sin_kf):
        if not re.search(r"(?:^|;)\s*opacity:0(?:;|$)", cuerpo):
            continue
        # piezas de estado (aros, borde de luz, indicador) y el ícono que cede su lugar al aro del botón ocupado
        estado = any(x in selector for x in ("::before", "::after", ".oculto", ".env.ocupado svg"))
        salvavidas = "mv-visible" in cuerpo
        assert estado or salvavidas, selector.strip()
    js = leer("movimiento.js")
    for clase in ("mv-prep", "mv-espera"):                   # las únicas que ocultan, y solo las pone el script
        assert clase in js and clase in css
    assert "visibility:hidden" not in sin_kf.replace(".herr-dia.hueco{border:0;visibility:hidden}", "")


def test_MOV_008_los_estados_de_trabajo_salen_de_app_js():
    app = leer("app.js")
    js = leer("movimiento.js")
    # El atributo que enciende aros, latido y onda solo se escribe desde la función trabajo() de app.js…
    assert app.count("setAttribute('data-trabajo'") == 1 and "function trabajo(e)" in app
    js = "\n".join(l for l in js.splitlines() if not l.lstrip().startswith("//"))
    assert "data-trabajo" not in js                          # …y movimiento.js nunca lo toca: no simula estados
    for evento, estado in (("'busqueda'", "'fuentes'"), ("'texto'", "'escribe'")):
        linea = next(l for l in app.splitlines() if "ev.tipo===" + evento in l)
        assert "estado(" + estado in linea, evento
    assert "setInterval" not in js                           # sin temporizadores periódicos


def test_MOV_009_sin_librerias_ni_scripts_en_linea():
    html = leer("index.html")
    externos = re.findall(r'<script src="(https://[^"]+)"', html)
    assert all(u.startswith("https://cdnjs.cloudflare.com/") for u in externos) and len(externos) == 2
    assert "fonts.googleapis" not in html and "fonts.gstatic" not in html
    for nombre in ("movimiento.js", "movimiento.css"):
        fuente = leer(nombre)
        assert "http://" not in fuente and "https://" not in fuente, nombre
    assert "eval(" not in leer("movimiento.js") and "innerHTML" not in leer("movimiento.js")
