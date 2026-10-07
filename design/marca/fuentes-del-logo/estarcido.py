"""Emblema de PULLEX IA: el rostro de Temis en estarcido de neón, a partir de la imagen del usuario."""
import sys, os
import numpy as np
from PIL import Image, ImageFilter, ImageDraw
from scipy import ndimage as ndi

SRC = "/root/.claude/uploads/91b0dc1b-d87e-575a-a080-831ddc6e0fa9/6cd25f13-image.png"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
X0, Y0, LADO, ESC = 20, 0, 560, 4           # recorte en la imagen original y factor de ampliación
N = LADO * ESC
GRAF = np.array([16, 17, 21]); LIMA = np.array([217, 255, 104]); CIAN = np.array([104, 228, 244])
ROSA = np.array([255, 115, 177]); TINTA = np.array([244, 246, 249])

def suaviza(m, s, u=0.5):
    return ndi.gaussian_filter(m.astype(np.float32), s) > u

def limpia(m, minimo):
    lab, n = ndi.label(m)
    if n == 0: return m
    tam = ndi.sum(m, lab, range(1, n + 1))
    keep = np.zeros(n + 1, bool); keep[1:] = tam >= minimo
    return keep[lab]

def capas():
    im = Image.open(SRC).convert("RGB").crop((X0, Y0, X0 + LADO, Y0 + LADO)).resize((N, N), Image.LANCZOS)
    a = np.asarray(im).astype(np.float32) / 255
    lum = 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]
    yy, xx = np.mgrid[0:N, 0:N]
    # fuera la balanza y la mano (derecha de la imagen)
    fuera = (xx > (474 - X0) * ESC) | ((xx > (428 - X0) * ESC) & (yy > (402 - Y0) * ESC))
    g = ndi.gaussian_filter(lum, 5.0); g[fuera] = 0
    hi = limpia(suaviza(g > 0.50, 3), 900)
    mid = limpia(suaviza((g > 0.29), 3), 2500) & ~hi
    mx, mn = a.max(-1), a.min(-1); sat = (mx - mn) / (mx + 1e-6)
    cy = (a[..., 2] > a[..., 0] + 0.13) & (sat > 0.28) & (lum > 0.30) & ~fuera
    ro = (a[..., 0] > a[..., 1] + 0.11) & (a[..., 0] > a[..., 2] - 0.02) & (sat > 0.24) & (lum > 0.34) & ~fuera
    cy = limpia(suaviza(cy, 2.5, 0.45), 500); ro = limpia(suaviza(ro, 2.5, 0.45), 500)
    # venda: polígono en coordenadas del recorte anterior (800 px = radio 200 alrededor de (335,238))
    P800 = [(108,266),(205,228),(300,205),(400,202),(500,211),(548,230),(560,300),(550,400),(508,412),(488,345),(452,302),(400,293),(350,300),(300,320),(205,350),(120,380),(100,330)]
    pol = [(((x / 2 + 135) - X0) * ESC, ((y / 2 + 38) - Y0) * ESC) for x, y in P800]
    mv = Image.new("L", (N, N), 0); ImageDraw.Draw(mv).polygon(pol, fill=255)
    venda = np.asarray(mv) > 0
    return hi, mid, cy, ro, venda

def compone(esquema, hi, mid, cy, ro, venda):
    rgb = np.zeros((N, N, 3), np.float32); alfa = np.zeros((N, N), np.float32)
    def pinta(m, col, a=1.0):
        rgb[m] = col; alfa[m] = a
    if esquema == "lima":
        pinta(mid, LIMA * 0.42 + GRAF * 0.58); pinta(hi, LIMA)
    elif esquema == "plano":
        pinta(hi, LIMA)
    else:  # rostro claro y venda en lima
        pinta(mid, CIAN * 0.36 + GRAF * 0.64); pinta(hi, TINTA)
        banda = suaviza(suaviza(venda, 7) & ~hi, 4)
        pinta(banda, LIMA); pinta(banda & mid, LIMA * 0.72 + GRAF * 0.28)
    if esquema != "plano":
        v = venda if esquema == "venda" else np.zeros_like(venda)
        pinta(cy & ~v, CIAN); pinta(ro & ~v, ROSA)
    return rgb, alfa

def circulo(rgb, alfa, cx, cy, r, salida, px=1400):
    yy, xx = np.mgrid[0:N, 0:N]
    d = np.sqrt((xx - cx * ESC) ** 2 + (yy - cy * ESC) ** 2)
    borde = np.clip((r * ESC - d) / 3.0, 0, 1)
    out = np.dstack([rgb, alfa * borde * 255]).astype(np.uint8)
    im = Image.fromarray(out, "RGBA")
    caja = (int((cx - r) * ESC), int((cy - r) * ESC), int((cx + r) * ESC), int((cy + r) * ESC))
    im = im.crop(caja).resize((px, px), Image.LANCZOS)
    im.save(salida)

def cuadro(rgb, alfa, cx, cy, r, salida, px=1200):
    out = np.dstack([rgb, alfa * 255]).astype(np.uint8)
    im = Image.fromarray(out, "RGBA")
    caja = (int((cx - r) * ESC), int((cy - r) * ESC), int((cx + r) * ESC), int((cy + r) * ESC))
    im.crop(caja).resize((px, px), Image.LANCZOS).save(salida)


if __name__ == "__main__":
    hi, mid, cy, ro, venda = capas()
    for esq in ("venda", "lima", "plano"):
        rgb, alfa = compone(esq, hi, mid, cy, ro, venda)
        circulo(rgb, alfa, 268, 286, 270, os.path.join(OUT, f"temis-{esq}.png"), px=1600)
        cuadro(rgb, alfa, 264, 250, 215, os.path.join(OUT, f"temis-{esq}-cuadro.png"), px=1200)
        print(esq)
