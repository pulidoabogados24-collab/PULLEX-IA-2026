"""PULLEX IA — símbolo «P de la Justicia».

La P es el fiel (el asta) y la cabeza de la figura (el ojo de la P). La viga de la balanza cruza la
cabeza como la venda de Temis, y de sus extremos cuelgan los dos platillos.

Coordenadas con el asta en x = 0 y la viga en y = 0.
"""
LIMA, CIAN, ROSA = "#d9ff68", "#68e4f4", "#ff73b1"
GRAFITO, CARTA, BORDE, TINTA, GRIS = "#101115", "#17191e", "#2e3037", "#f4f6f9", "#979da7"

SW = 22          # grosor de la P
R = 30           # radio del ojo de la P
VIGA = 86        # media longitud de la viga
SV = 13          # grosor de la viga
HILO = 7         # grosor de los hilos
PLATO = 24       # radio de los platillos
CAIDA = 46       # altura a la que cuelgan los platillos
PIE = 112        # altura del pie
GAP = 5          # separación entre viga y P

# caja que contiene el símbolo con un pequeño aire
X0, Y0 = -(VIGA + PLATO) - 4, -(R + SW / 2) - 4
ANCHO, ALTO = 2 * (VIGA + PLATO) + 8, (R + SW / 2) + PIE + SW / 2 + 8
VB = f"{X0:g} {Y0:g} {ANCHO:g} {ALTO:g}"


def simbolo(p=LIMA, b=CIAN, fondo=GRAFITO):
    """Fragmento SVG. p = color de la P, b = color de la balanza, fondo = color sobre el que se pinta."""
    cx = R + 2
    return (
        f'<g fill="none" stroke-linecap="round">'
        # ojo de la P (la cabeza)
        f'<circle cx="{cx}" cy="0" r="{R}" stroke="{p}" stroke-width="{SW}"/>'
        # viga = venda: pasa por delante de la cabeza
        f'<line x1="{-VIGA}" y1="0" x2="{VIGA}" y2="0" stroke="{fondo}" stroke-width="{SV + 2 * GAP}"/>'
        f'<line x1="{-VIGA}" y1="0" x2="{VIGA}" y2="0" stroke="{b}" stroke-width="{SV}"/>'
        f'<line x1="{-VIGA}" y1="0" x2="{-VIGA}" y2="{CAIDA}" stroke="{b}" stroke-width="{HILO}"/>'
        f'<line x1="{VIGA}" y1="0" x2="{VIGA}" y2="{CAIDA}" stroke="{b}" stroke-width="{HILO}"/>'
        # asta de la P = columna: pasa por delante de la viga
        f'<line x1="0" y1="{-SV / 2 - GAP}" x2="0" y2="{SV / 2 + GAP}" stroke="{fondo}" stroke-width="{SW + 2 * GAP}" stroke-linecap="butt"/>'
        f'<line x1="0" y1="{-R}" x2="0" y2="{PIE}" stroke="{p}" stroke-width="{SW}"/>'
        f'<line x1="-30" y1="{PIE}" x2="30" y2="{PIE}" stroke="{p}" stroke-width="{SW}"/>'
        f'</g>'
        f'<path d="M {-VIGA - PLATO} {CAIDA} A {PLATO} {PLATO} 0 0 0 {-VIGA + PLATO} {CAIDA} Z" fill="{b}"/>'
        f'<path d="M {VIGA - PLATO} {CAIDA} A {PLATO} {PLATO} 0 0 0 {VIGA + PLATO} {CAIDA} Z" fill="{b}"/>'
    )


def svg(alto, p=LIMA, b=CIAN, fondo=GRAFITO, extra=""):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{VB}" width="{alto * ANCHO / ALTO:.2f}" height="{alto}" {extra}>'
            f'{simbolo(p, b, fondo)}</svg>')


def nombre(alto, c_pul=TINTA, c_lex=LIMA, c_ia=CIAN):
    """«PUL» + «LEX» resaltado + «IA» fina. alto = tamaño de letra en px."""
    return (f'<span style="font-family:Syne;font-weight:800;font-size:{alto}px;line-height:1;letter-spacing:.005em;white-space:nowrap;color:{c_pul}">'
            f'PUL<span style="color:{c_lex}">LEX</span><span style="font-weight:400;color:{c_ia};margin-left:.22em">IA</span></span>')


def lema(tam, color="rgba(244,246,249,.62)", cx=LIMA):
    return (f'<span style="font-family:GeistMono;font-size:{tam}px;letter-spacing:.46em;color:{color};text-transform:uppercase;white-space:nowrap">'
            f'Justicia <span style="color:{cx}">×</span> Inteligencia</span>')


def ficha(lado, fondo, p, b, borde=None, escala=0.56):
    sombra = f"box-shadow:inset 0 0 0 {max(1, lado / 512):.2f}px {borde};" if borde else ""
    alto = lado * escala
    return (f'<div style="width:{lado}px;height:{lado}px;border-radius:{lado * 0.225:.1f}px;background:{fondo};{sombra}'
            f'display:grid;place-items:center;flex:none">{svg(alto, p, b, fondo)}</div>')


FUENTES = """
@font-face{font-family:Syne;src:url(%(f)s/syne-var.woff2) format("woff2");font-weight:400 800}
@font-face{font-family:Jakarta;src:url(%(f)s/plus-jakarta-sans-var.woff2) format("woff2");font-weight:200 800}
@font-face{font-family:GeistMono;src:url(%(f)s/GeistMono-Regular.ttf);font-weight:400}
"""


def fuentes(ruta="../fonts"):
    return FUENTES % {"f": ruta}
