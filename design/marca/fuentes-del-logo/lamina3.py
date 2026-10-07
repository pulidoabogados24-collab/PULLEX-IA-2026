"""Lámina del logo «Temis en neón» (1600 x 1240 px CSS)."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from marca2 import LIMA, CIAN, ROSA, GRAFITO, CARTA, BORDE, TINTA, nombre, lema, fuentes
AQUI = os.path.dirname(os.path.abspath(__file__)); B = os.path.join(AQUI, "build"); os.makedirs(B, exist_ok=True)
W, H, M = 1600, 1240, 72

def emblema(d, esq="venda", aro=LIMA, brillo=True, disco=None):
    """Busto dentro de un aro de luz. d = diámetro total en px."""
    r_busto = d * 0.445
    glow = (f'<img src="../out/temis-{esq}.png" style="position:absolute;left:50%;top:50%;width:{2*r_busto:.1f}px;height:{2*r_busto:.1f}px;transform:translate(-50%,-50%);filter:blur({d*0.035:.1f}px) saturate(1.5);opacity:.55">') if brillo else ""
    fondo = f'<div style="position:absolute;inset:0;border-radius:50%;background:{disco}"></div>' if disco else ""
    sombra = f"filter:drop-shadow(0 0 {d*0.012:.1f}px {aro}) drop-shadow(0 0 {d*0.05:.1f}px {aro}88);" if brillo else ""
    return (f'<div style="position:relative;width:{d}px;height:{d}px;flex:none">{fondo}{glow}'
            f'<img src="../out/temis-{esq}.png" style="position:absolute;left:50%;top:50%;width:{2*r_busto:.1f}px;height:{2*r_busto:.1f}px;transform:translate(-50%,-50%)">'
            f'<svg viewBox="0 0 200 200" style="position:absolute;inset:0;width:100%;height:100%;overflow:visible;{sombra}"><circle cx="100" cy="100" r="96" fill="none" stroke="{aro}" stroke-width="{max(1.6, 320/d):.2f}"/></svg></div>')

def ficha(lado, esq="venda", fondo=CARTA, borde=BORDE):
    b = f"box-shadow:inset 0 0 0 {max(1, lado/400):.2f}px {borde};" if borde else ""
    return (f'<div style="position:relative;width:{lado}px;height:{lado}px;border-radius:{lado*0.225:.1f}px;background:{fondo};{b}overflow:hidden;flex:none">'
            f'<img src="../out/temis-{esq}-cuadro.png" style="position:absolute;left:4%;top:7%;width:96%;height:96%"></div>')

def html():
    css = fuentes("../fonts") + f"""
html,body{{margin:0;background:{GRAFITO}}}
.l{{position:relative;width:{W}px;height:{H}px;background:{GRAFITO};color:{TINTA};overflow:hidden}}
.m{{font-family:GeistMono;font-size:12px;letter-spacing:.2em;color:rgba(244,246,249,.62);text-transform:uppercase;white-space:nowrap}}
.abs{{position:absolute}}
.r{{position:absolute;left:{M}px;right:{M}px;height:1px;background:rgba(244,246,249,.16)}}
.v{{position:absolute;width:1px;background:rgba(244,246,249,.16)}}
"""
    cuerpo = f"""
<div class="l">
  <div class="abs m" style="left:{M}px;top:56px;color:{TINTA}">PULLEX IA</div>
  <div class="abs m" style="right:{M}px;top:56px">Logo · propuesta 3 · el rostro de Temis</div>
  <div class="r" style="top:90px"></div>

  <div class="abs" style="left:0;right:0;top:90px;height:640px;display:flex;align-items:center;justify-content:center;gap:64px">
    {emblema(470)}
    <div style="display:flex;flex-direction:column;gap:26px">
      {nombre(118)}
      <div style="padding-left:6px">{lema(15)}</div>
    </div>
  </div>

  <div class="r" style="top:730px"></div>

  <div class="abs m" style="left:{M}px;top:760px">Icono de la app</div>
  <div class="abs" style="left:{M}px;top:804px;display:flex;align-items:flex-end;gap:22px">
    {ficha(170)}{ficha(96)}{ficha(48)}{ficha(28)}
  </div>

  <div class="v" style="left:{M + 440}px;top:760px;height:216px"></div>
  <div class="abs m" style="left:{M + 476}px;top:760px">Sello</div>
  <div class="abs" style="left:{M + 476}px;top:796px;display:flex;align-items:center;gap:26px">
    {emblema(180)}{emblema(110)}{emblema(64, brillo=False)}
  </div>

  <div class="v" style="left:{M + 940}px;top:760px;height:216px"></div>
  <div class="abs m" style="left:{M + 976}px;top:760px">Variantes</div>
  <div class="abs" style="left:{M + 976}px;top:796px;display:flex;align-items:center;gap:26px">
    <div style="display:flex;flex-direction:column;align-items:center;gap:10px">{emblema(150, "lima")}<span class="m" style="font-size:10px">Toda en lima</span></div>
    <div style="display:flex;flex-direction:column;align-items:center;gap:10px">{emblema(150, "plano", brillo=False)}<span class="m" style="font-size:10px">Un solo color</span></div>
  </div>

  <div class="r" style="top:1012px"></div>
  <div class="abs" style="left:{M}px;top:1046px;right:{M}px;display:grid;grid-template-columns:repeat(3,1fr);gap:40px">
    <div style="display:flex;gap:16px;align-items:flex-start"><span style="flex:none;width:12px;height:12px;border-radius:50%;background:{TINTA};margin-top:6px"></span><div style="font-family:Jakarta;font-size:19px;line-height:1.45;color:{TINTA}"><b style="font-weight:700">El rostro es Temis.</b><br><span style="color:rgba(244,246,249,.7)">Sale de tu propia imagen, llevada a formas planas.</span></div></div>
    <div style="display:flex;gap:16px;align-items:flex-start"><span style="flex:none;width:12px;height:12px;border-radius:50%;background:{LIMA};margin-top:6px"></span><div style="font-family:Jakarta;font-size:19px;line-height:1.45;color:{TINTA}"><b style="font-weight:700">La venda va en lima.</b><br><span style="color:rgba(244,246,249,.7)">El mismo color de LEX, la ley, dentro de tu nombre.</span></div></div>
    <div style="display:flex;gap:16px;align-items:flex-start"><span style="flex:none;width:12px;height:12px;border-radius:50%;background:linear-gradient(90deg,{CIAN} 50%,{ROSA} 50%);margin-top:6px"></span><div style="font-family:Jakarta;font-size:19px;line-height:1.45;color:{TINTA}"><b style="font-weight:700">Las vetas son la inteligencia.</b><br><span style="color:rgba(244,246,249,.7)">Luz cian y rosa que recorre el mármol.</span></div></div>
  </div>
</div>"""
    return f'<!doctype html><html lang="es"><head><meta charset="utf-8"><style>{css}</style></head><body>{cuerpo}</body></html>'

if __name__ == "__main__":
    open(os.path.join(B, "lamina3.html"), "w", encoding="utf-8").write(html()); print("ok")
