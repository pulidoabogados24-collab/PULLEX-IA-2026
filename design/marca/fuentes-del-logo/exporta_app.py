"""Iconos y emblema para la app (static/)."""
import os, sys, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from marca2 import GRAFITO, CARTA, BORDE, LIMA
from lamina3 import emblema
AQUI = os.path.dirname(os.path.abspath(__file__)); B = os.path.join(AQUI, "build"); O = os.path.join(AQUI, "out", "app")
os.makedirs(O, exist_ok=True)
def cuadro(lado, radio=0.0, x=4, y=7, t=96, fondo=CARTA):
    return (f'<div style="position:relative;width:{lado}px;height:{lado}px;border-radius:{lado*radio:.1f}px;background:{fondo};overflow:hidden">'
            f'<img src="../out/temis-venda-cuadro.png" style="position:absolute;left:{x}%;top:{y}%;width:{t}%;height:{t}%"></div>')
def pagina(n, w, cuerpo):
    r = os.path.join(B, "app-" + n + ".html")
    open(r, "w", encoding="utf-8").write(f'<!doctype html><html><head><meta charset="utf-8"><style>html,body{{margin:0;background:transparent}}</style></head><body>{cuerpo}</body></html>')
    return r
trabajos = [
    ("emblema-192", 96, 2, emblema(96, disco=GRAFITO, brillo=False), True),
    ("favicon", 96, 1, cuadro(96, radio=0.225), True),
    ("apple-touch-icon", 180, 1, cuadro(180), False),
    ("icon-192", 192, 1, cuadro(192, radio=0.225), True),
    ("icon-512", 512, 1, cuadro(512, radio=0.225), True),
    ("icon-maskable", 512, 1, cuadro(512, x=14, y=17, t=74), False),
]
for n, lado, esc, cuerpo, transp in trabajos:
    args = [sys.executable, os.path.join(AQUI, "render.py"), pagina(n, lado, cuerpo), os.path.join(O, n + ".png"), str(lado), str(lado), str(esc), "-"]
    if transp: args.append("t")
    subprocess.run(args, check=True)
    print(n, os.path.getsize(os.path.join(O, n + ".png")))
