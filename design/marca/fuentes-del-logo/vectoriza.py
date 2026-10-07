"""Versión vectorial (SVG) del emblema de Temis: traza cada capa del estarcido con potrace."""
import os, sys
import numpy as np
import potrace
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import estarcido as E

HEX = lambda c: "#%02x%02x%02x" % tuple(int(round(v)) for v in c)
CX, CY, RC = 268, 286, 270          # círculo de recorte, en coordenadas del recorte (antes de ampliar)

def traza(mask, color, turd=40):
    bm = potrace.Bitmap(~mask.astype(bool))   # la biblioteca toma True como papel en blanco
    plist = bm.trace(turdsize=turd, alphamax=1.0, opttolerance=0.4)
    partes = []
    s = 1.0 / E.ESC
    f = lambda p: f"{p.x * s:.2f} {p.y * s:.2f}"
    for curve in plist:
        partes.append(f"M {f(curve.start_point)}")
        for seg in curve.segments:
            if seg.is_corner:
                partes.append(f"L {f(seg.c)} L {f(seg.end_point)}")
            else:
                partes.append(f"C {f(seg.c1)} {f(seg.c2)} {f(seg.end_point)}")
        partes.append("Z")
    return f'<path fill="{color}" fill-rule="evenodd" d="{" ".join(partes)}"/>'

def capas_color(esq):
    hi, mid, cy, ro, venda = E.capas()
    G, L, C, R, T = E.GRAF, E.LIMA, E.CIAN, E.ROSA, E.TINTA
    if esq == "venda":
        banda = E.suaviza(E.suaviza(venda, 7) & ~hi, 4)
        return [(mid & ~banda, HEX(C * 0.36 + G * 0.64)), (hi & ~banda, HEX(T)), (banda & ~mid, HEX(L)), (banda & mid, HEX(L * 0.72 + G * 0.28)),
                (cy & ~venda, HEX(C)), (ro & ~venda, HEX(R))]
    if esq == "lima":
        return [(mid, HEX(L * 0.42 + G * 0.58)), (hi, HEX(L)), (cy, HEX(C)), (ro, HEX(R))]
    return [(hi, HEX(L))]

def svg(esq, con_aro=True, disco=False):
    paths = "".join(traza(m, col) for m, col in capas_color(esq))
    r_aro = RC * 1.0787       # el aro va un poco por fuera del busto (96 / 89)
    vb = f"{CX - r_aro - 8:.1f} {CY - r_aro - 8:.1f} {2 * (r_aro + 8):.1f} {2 * (r_aro + 8):.1f}"
    fondo = f'<circle cx="{CX}" cy="{CY}" r="{r_aro:.1f}" fill="#101115"/>' if disco else ""
    aro = f'<circle cx="{CX}" cy="{CY}" r="{r_aro:.1f}" fill="none" stroke="#d9ff68" stroke-width="4.6"/>' if con_aro else ""
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{vb}" role="img" aria-label="PULLEX IA: el rostro de Temis">'
            f'<defs><clipPath id="c"><circle cx="{CX}" cy="{CY}" r="{RC}"/></clipPath></defs>{fondo}'
            f'<g clip-path="url(#c)">{paths}</g>{aro}</svg>')

if __name__ == "__main__":
    out = os.path.join(E.OUT, "archivos3")
    for esq, nombre, disco in (("venda", "emblema-vector.svg", False), ("venda", "emblema-vector-con-disco.svg", True), ("plano", "emblema-vector-un-solo-color.svg", False)):
        s = svg(esq, disco=disco)
        open(os.path.join(out, nombre), "w", encoding="utf-8").write(s)
        print(nombre, len(s))
