import os, sys, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from marca2 import LIMA, CIAN, GRAFITO, CARTA, BORDE, TINTA, nombre, lema, fuentes
from lamina3 import emblema, ficha
AQUI = os.path.dirname(os.path.abspath(__file__)); B = os.path.join(AQUI, "build"); O = os.path.join(AQUI, "out", "archivos3")
os.makedirs(O, exist_ok=True)
def pagina(n, w, h, cuerpo):
    css = fuentes("../fonts") + f"html,body{{margin:0;background:transparent}}.p{{width:{w}px;height:{h}px;display:flex;align-items:center;justify-content:center}}"
    r = os.path.join(B, n + ".html")
    open(r, "w", encoding="utf-8").write(f'<!doctype html><html><head><meta charset="utf-8"><style>{css}</style></head><body><div class="p">{cuerpo}</div></body></html>')
    return r
def logo(d, con_lema=True, disco=None, cp=TINTA, cl=LIMA, ci=CIAN, clema="rgba(244,246,249,.62)", cx=LIMA):
    lem = f'<div style="padding-left:{d*0.013:.1f}px">{lema(d*0.032, clema, cx)}</div>' if con_lema else ""
    return (f'<div style="display:flex;align-items:center;gap:{d*0.13:.1f}px">{emblema(d, disco=disco)}'
            f'<div style="display:flex;flex-direction:column;gap:{d*0.055:.1f}px">{nombre(d*0.25, cp, cl, ci)}{lem}</div></div>')
trabajos = [
    ("emblema-para-fondo-oscuro", 1400, 1400, emblema(1200)),
    ("emblema-con-disco-para-cualquier-fondo", 1400, 1400, emblema(1200, disco=GRAFITO)),
    ("emblema-variante-lima", 1400, 1400, emblema(1200, "lima")),
    ("emblema-un-solo-color", 1400, 1400, emblema(1200, "plano", brillo=False)),
    ("icono-app", 1024, 1024, ficha(1024)),
    ("favicon-64", 64, 64, ficha(64)),
    ("logo-horizontal-para-fondo-oscuro", 2400, 760, logo(600)),
    ("logo-horizontal-sin-lema-fondo-oscuro", 2400, 760, logo(600, con_lema=False)),
    ("logo-horizontal-para-fondo-claro", 2400, 760, logo(600, disco=GRAFITO, cp=GRAFITO, cl=GRAFITO, ci=GRAFITO, clema="rgba(16,17,21,.66)", cx=GRAFITO)),
]
for n, w, h, c in trabajos:
    subprocess.run([sys.executable, os.path.join(AQUI, "render.py"), pagina(n, w, h, c), os.path.join(O, n + ".png"), str(w), str(h), "1", "-", "t"], check=True)
    print(n, os.path.getsize(os.path.join(O, n + ".png")))
