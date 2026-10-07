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


def test_MOV_011_al_navegar_gana_el_ultimo_cambio():
    """La transición entre secciones aplica el cambio un cuadro después del clic. Si entre tanto hubo otra navegación
    (otro clic, o un ver() interno), el cambio viejo no puede pisarla: se descarta."""
    app = leer("app.js")
    cuerpo_ver = app[app.index("function ver(v){"):app.index("function pintarUbicacion")]
    assert "TURNO_VER++" in cuerpo_ver                       # todo cambio de sección cuenta, venga de donde venga
    cuerpo_nav = app[app.index("function verNav(v){"):app.index("ACCIONES.ver=verNav")]
    assert "const turno=TURNO_VER" in cuerpo_nav and "if(turno===TURNO_VER)ver(v)" in cuerpo_nav
    assert "MV.transicion(()=>ver(v))" not in app            # nunca un cambio diferido sin comprobar el turno


def test_MOV_012_el_interruptor_de_movimiento_vale_en_todas_las_paginas():
    """admin.html y restablecer.html cargan tema.css y apariencia.js, pero no movimiento.css: la regla que apaga el
    movimiento con Ajustes → Movimiento: reducido tiene que estar también en tema.css."""
    tema = sin_comentarios(leer("tema.css"))
    assert re.search(r':root\[data-movimiento="reducido"\] \*[^{]*\{[^}]*animation-duration:\.001ms!important[^}]*'
                     r'transition-duration:\.001ms!important', tema)
    assert "raiz.setAttribute('data-movimiento'" in leer("apariencia.js")
    for pagina in ("admin.html", "restablecer.html"):
        html = leer(pagina)
        assert "/static/tema.css" in html and "/static/apariencia.js" in html, pagina


def test_MOV_013_el_calendario_rotula_cada_dia_por_su_motivo():
    """El calendario del término es un apoyo de un cálculo jurídico: el rótulo corto de cada casilla sale del motivo
    que dio el servidor, no de la posición del día. Un sábado entre la notificación y el día 1 no es «notif.»."""
    js = leer("herramientas.js")
    assert "previo?'notif.'" not in js
    assert "text:herrMotivoCorto(c.motivo)" in js
    # El resumen cuenta lo que no contó desde el inicio del cómputo y lo contrasta con la cifra del servidor.
    assert "c.fecha<r.inicio_computo" in js and "r.dias_inhabiles_descontados!==noCuentan)return null" in js
    corto = js[js.index("function herrMotivoCorto"):js.index("function herrCalendario")]
    servidor = (RAIZ / "procedimientos" / "j05_terminos.py").read_text(encoding="utf-8")
    calendario = (RAIZ / "procedimientos" / "calendario.py").read_text(encoding="utf-8")
    # Cada motivo que el servidor puede dar a un día no contado tiene su rótulo (si cambia el texto allá, se nota aquí).
    for inicio_motivo, fuente in (("día de la notificación", servidor), ("envío", servidor), ("día hábil siguiente", servidor),
                                  ("domingo", calendario), ("sábado", calendario), ("festivo", calendario),
                                  ("vacancia", calendario), ("suspensión", calendario), ("día sin atención", calendario)):
        assert "startsWith('" + inicio_motivo + "')" in corto, inicio_motivo
        assert '"' + inicio_motivo in fuente, inicio_motivo


def test_MOV_014_una_respuesta_cortada_se_pinta_con_lo_recuperado():
    """Si la conexión se cae a mitad, lo que se recupera del servidor (o el aviso de conexión interrumpida) tiene que
    quedar a la vista en la burbuja, no solo en la variable que usan «Copiar» y «Continuar»."""
    app = leer("app.js")
    enviar = app[app.index("async function enviar(opc){"):app.index("async function continuarResp")]
    bloque = enviar[enviar.index("if(res.error==='conexion'&&!res.fin){"):enviar.index("cerrarResp(bIA,res,cid)")]
    assert "se interrumpió la conexión" in bloque and "innerHTML=md(res.buffer)" in bloque
    continuar = app[app.index("async function continuarResp"):app.index("function quitarAcciones")]
    assert "res.buffer=rec.texto;res.id=rec.id;bIA.querySelector('.md').innerHTML=md(res.buffer)" in continuar


def test_MOV_015_el_cascaron_incluye_todo_lo_que_la_pagina_enlaza():
    """Si la página enlaza una hoja o un script de este sitio que el service worker no guarda al instalarse, la
    primera vez que se abra sin señal la app carga a medias (sin planes, documentos, herramientas…)."""
    html, sw = leer("index.html"), leer("sw.js")
    shell = set(re.findall(r'"(/static/[^"]+)"', sw))
    enlazados = set(re.findall(r'<script src="(/static/[^"]+)"', html)) | set(re.findall(r'<link rel="stylesheet" href="(/static/[^"]+)"', html))
    assert len(enlazados) >= 15
    assert not (enlazados - shell), sorted(enlazados - shell)
    assert int(re.search(r'const CACHE = "pullex-v(\d+)"', sw).group(1)) >= 9


def test_MOV_016_el_envio_nunca_queda_ocupado_si_algo_falla():
    """«Ocupado» (botón girando, chat que no admite otro mensaje) se suelta en un finally, y cada envío suelta solo lo
    suyo. Un fallo del intérprete de markdown no tumba el pintado: la respuesta sale como texto plano seguro."""
    app = leer("app.js")
    for inicio, fin in (("async function enviar(opc){", "async function continuarResp"), ("async function continuarResp", "function quitarAcciones")):
        cuerpo = app[app.index(inicio):app.index(fin)]
        assert "ocupado(true);" in cuerpo and "}finally{soltar()}" in cuerpo, inicio
        assert cuerpo.count("ocupado(false)") == 1 and "suelto=true;ocupado(false)" in cuerpo, inicio
    linea_md = next(l for l in app.splitlines() if l.startswith("function md(t){"))
    assert "try{return DOMPurify.sanitize(marked.parse(t||''))}catch(e){}" in linea_md and "esc(t)" in linea_md
    assert "DOMPurify.sanitize" in linea_md.split("catch")[0]            # lo que sale de marked siempre pasa por DOMPurify


def test_MOV_017_un_aviso_de_conexion_no_se_presenta_como_respuesta():
    """Si la conexión se cae sin que llegue ni quede guardado nada, se muestra el aviso y ya: sin «Copiar», sin
    «Continuar» (no hay de dónde continuar) y sin sumar una consulta usada."""
    app = leer("app.js")
    enviar = app[app.index("async function enviar(opc){"):app.index("async function continuarResp")]
    aviso = enviar[enviar.index("if(!res.buffer.trim()){"):enviar.index("cerrarResp(bIA,res,cid)")]
    assert "se interrumpió la conexión" in aviso and "soltar();cargarConvs();return}" in aviso
    assert enviar.index("cerrarResp(bIA,res,cid)") < enviar.index("PERFIL.usadas++")
    assert "res.buffer='**Aviso:**" not in app                           # el aviso no se guarda como texto de la respuesta


def test_MOV_018_los_avisos_duran_lo_que_toma_leerlos():
    """Un aviso corto dura lo de siempre; uno largo (los errores del servidor pasan de 100 caracteres) dura más. Se
    retira por tiempo, sin depender de que una animación termine."""
    app = leer("app.js")
    toast = app[app.index("function toast(m){"):app.index("function trabajo(e)")]
    m = re.search(r"Math\.min\((\d+),Math\.max\((\d+),(\d+)\+String\(m\|\|''\)\.length\*(\d+)\)\)", toast)
    tope, minimo, base, por_caracter = map(int, m.groups())
    def dura(n):
        return min(tope, max(minimo, base + n * por_caracter))
    assert dura(8) >= 2600                                               # «Copiado»
    assert dura(105) >= 105 / 17 * 1000                                  # error típico del servidor, a 17 caracteres por segundo
    assert dura(150) >= 9000 and tope <= 10000
    assert "animationend" not in toast.split("\n", 2)[2] and "setTimeout" in toast


def test_MOV_019_el_boton_de_ingreso_dice_lo_del_modo_a_la_vista():
    app = leer("app.js")
    ingreso = app[app.index("async function enviarAuth(){"):app.index("const CAPACIDADES")]
    assert "b.textContent=modoActual==='registrar'?'Crear cuenta':'Ingresar';trabajo(null)" in ingreso
    assert "b.textContent=rotulo" not in ingreso


def test_MOV_020_has_no_arrastra_reglas_que_no_lo_necesitan():
    """Un navegador sin :has() descarta la regla completa. Fuera del bloque de movimiento completo (que ya exige un
    navegador reciente), ninguna regla mezcla :has() con otro selector en la misma lista."""
    css = sin_comentarios(leer("movimiento.css"))
    quietas = css[:css.index("@media (prefers-reduced-motion:no-preference)")]
    for selector in re.findall(r"([^{}]+)\{[^{}]*\}", quietas):
        if ":has(" in selector:
            assert "," not in re.sub(r"\([^()]*\)", "", selector), selector.strip()
