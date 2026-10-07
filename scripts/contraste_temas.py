"""Mide el contraste (WCAG 2.x) de cada tema de static/tema.css, en claro y en oscuro.

    python scripts/contraste_temas.py            # tabla legible
    python scripts/contraste_temas.py --md       # tabla Markdown (para docs/12-DISENO-Y-APARIENCIA.md)

Sale con código 1 si algún par de texto queda por debajo de AA (4,5:1) o algún borde de control
(inputs) por debajo de 3:1. Los valores se leen del CSS real, no de una copia.
"""
import re
import sys
from pathlib import Path

CSS = (Path(__file__).resolve().parent.parent / "static" / "tema.css").read_text(encoding="utf-8")
TEMAS = ["justicia", "pullex", "notario", "bogota", "caribe", "toga", "jardin"]
# (frente, fondo, mínimo, descripción)
PARES = [
    ("text", "bg", 4.5, "texto / fondo"),
    ("text", "surface-2", 4.5, "texto / superficie 2"),
    ("text-2", "bg", 4.5, "texto secundario / fondo"),
    ("text-2", "surface", 4.5, "texto secundario / superficie"),
    ("text-2", "surface-2", 4.5, "texto secundario / superficie 2"),
    ("accent-ink", "accent", 4.5, "texto sobre acento (botón)"),
    ("accent-text", "surface", 4.5, "acento como texto / superficie"),
    ("accent-text", "bg", 4.5, "acento como texto / fondo"),
    ("accent-text", "accent-soft", 4.5, "acento como texto / acento suave"),
    ("ok", "surface", 4.5, "verde estado / superficie"),
    ("warn", "surface", 4.5, "ámbar estado / superficie"),
    ("danger", "surface", 4.5, "rojo estado / superficie"),
    ("border-strong", "surface", 3.0, "borde de campo / superficie"),
]


def bloque(selector: str) -> dict:
    out = {}
    for m in re.finditer(re.escape(selector) + r"\s*\{([^}]*)\}", CSS):
        for k, v in re.findall(r"--([a-z0-9-]+)\s*:\s*(#[0-9a-fA-F]{6})", m.group(1)):
            out[k] = v
    return out


def tokens(tema: str, esquema: str) -> dict:
    t = dict(bloque(":root"))
    if esquema == "oscuro":
        t.update(bloque(':root[data-esquema="oscuro"]'))
    if tema != "pullex":
        t.update(bloque(f':root[data-tema="{tema}"]'))
        if esquema == "oscuro":
            t.update(bloque(f':root[data-tema="{tema}"][data-esquema="oscuro"]'))
    return t


def lum(h: str) -> float:
    c = [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    c = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def contraste(a: str, b: str) -> float:
    la, lb = sorted((lum(a), lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def main():
    md = "--md" in sys.argv
    fallos = []
    filas = []
    for tema in TEMAS:
        for esq in ("claro", "oscuro"):
            t = tokens(tema, esq)
            valores = []
            for fr, fo, minimo, desc in PARES:
                r = contraste(t[fr], t[fo])
                valores.append(r)
                if r < minimo:
                    fallos.append(f"{tema}/{esq}: {desc} = {r:.2f} (< {minimo})")
            filas.append((tema, esq, valores))
    if md:
        cab = ["Tema", "Modo"] + [d for *_, d in PARES]
        print("| " + " | ".join(cab) + " |")
        print("|" + "---|" * len(cab))
        for tema, esq, v in filas:
            print(f"| {tema} | {esq} | " + " | ".join(f"{x:.2f}" for x in v) + " |")
    else:
        for i, (_, _, minimo, desc) in enumerate(PARES):
            print(f"[{i:2}] {desc} (mín. {minimo})")
        for tema, esq, v in filas:
            print(f"{tema:8} {esq:6} " + " ".join(f"{x:5.2f}" for x in v))
        peor = min(x for *_, v in filas for x in v[:-1])
        print(f"\nPeor par de texto: {peor:.2f}:1")
    if fallos:
        print("\nFALLAN:\n  " + "\n  ".join(fallos))
        sys.exit(1)


if __name__ == "__main__":
    main()
