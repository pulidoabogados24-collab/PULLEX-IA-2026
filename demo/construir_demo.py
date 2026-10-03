"""Genera demo/pullex-demo.html: la app completa en un solo archivo, sin servidor, con datos de
ejemplo (demo/datos_demo.json + demo/mock.js). Sirve para mostrar PULLEX IA desde cualquier
navegador o publicarla como página.

    python demo/construir_demo.py
"""
import base64
import json
import os
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
ST = RAIZ / "static"


def data_uri(ruta: Path, mime: str) -> str:
    return f"data:{mime};base64," + base64.b64encode(ruta.read_bytes()).decode()


html = (ST / "index.html").read_text(encoding="utf-8")
app_js = (ST / "app.js").read_text(encoding="utf-8")
# Sistema de diseño: tema.css (con las fuentes incrustadas como data URI) y el motor de apariencia,
# en línea, para que la demo siga siendo un solo archivo que abre sin servidor.
tema_css = (ST / "tema.css").read_text(encoding="utf-8")
tema_css = re.sub(r'url\("fonts/([a-z0-9-]+\.woff2)"\)',
                  lambda m: 'url("' + data_uri(ST / "fonts" / m.group(1), "font/woff2") + '")', tema_css)
assert "fonts/" not in tema_css
apariencia_js = (ST / "apariencia.js").read_text(encoding="utf-8")
# La demo es un solo archivo: no registra el service worker (no existe /sw.js fuera del servidor).
app_js = app_js.replace("'serviceWorker' in navigator", "false&&'serviceWorker' in navigator")
mock = (RAIZ / "demo" / "mock.js").read_text(encoding="utf-8")
datos = json.loads((RAIZ / "demo" / "datos_demo.json").read_text(encoding="utf-8"))
sys.path.insert(0, str(RAIZ))
import academia  # noqa: E402  — el Mapa del Derecho es el mismo de la app real
import documentos  # noqa: E402  — el catálogo del automatizador también es el real
datos["mapa"] = academia.MAPA
datos["automatizador"] = {
    "catalogo": documentos.CATALOGO, "areas": documentos.AREAS, "para": list(documentos.PARA_QUIEN),
    "flujos": documentos.flujos_publicos(), "max_pasos": documentos.MAX_PASOS,
    "aviso_general": documentos.AVISO_GENERAL, "aviso_funcionario": documentos.AVISO_FUNCIONARIO,
    "borrador": documentos.BORRADOR_FUNCIONARIO,
    "demo": json.loads((RAIZ / "demo" / "documentos_demo.json").read_text(encoding="utf-8"))}
docs_js = (ST / "documentos.js").read_text(encoding="utf-8")
bib_js = (ST / "biblioteca.js").read_text(encoding="utf-8")


def biblioteca_de_ejemplo() -> dict:
    """Catálogo FICTICIO de la Biblioteca (demo/biblioteca_demo.json) pasado por el backend real: lo que vería
    un usuario que no es administrador. demo/mock.js solo busca, filtra y compara sobre estas fichas."""
    from contextlib import closing

    import biblioteca
    import fuentes
    sys.path.insert(0, str(RAIZ / "demo"))
    import biblioteca_demo
    previas = {k: v for k, v in os.environ.items() if k.startswith("PULLEX_BIBLIOTECA_")}
    biblioteca_demo.montar()
    try:
        with closing(biblioteca.conexion()) as con:
            filas = con.execute(f"SELECT m.* FROM biblioteca_modelos m WHERE {biblioteca.predicado(False)} ORDER BY m.catalogo_id").fetchall()
            fichas, busq, estructura, copias = {}, {}, {}, {}
            for f in filas:
                cid = f["catalogo_id"]
                fichas[cid] = biblioteca.ficha(con, f)
                texto = biblioteca._texto_de(con, f["id"])
                visible = texto if (texto and biblioteca.puede_ver_texto(f)) else None
                busq[cid] = {"t": f["busq_titulo"], "m": f["busq_meta"], "sin_texto": texto is None,
                             "x": fuentes.sin_tildes(visible).lower() if visible else "", "o": visible or ""}
                if visible:
                    estructura[cid] = {"titulos": biblioteca.estructura_de(visible), "longitud": len(visible)}
                if biblioteca.copiable(f):
                    copias[cid] = biblioteca.copia_de_trabajo(con, f)
            resumen = biblioteca.facetas(con)
        generador = {t: {"tipo": g["id"], "nombre": g["nombre"], "area": g["area"]}
                     for t in biblioteca.GENERADOR_POR_TIPO for g in [biblioteca._generador(t)] if g}
        return {"resumen": resumen, "fichas": fichas, "orden": list(fichas), "busq": busq, "estructura": estructura, "copias": copias,
                "sinonimos": [list(g) for g in biblioteca.SINONIMOS],
                "tramites": [{"nombre": t["nombre"], "tipos": t["tipos"], "senales": t["senales"]} for t in biblioteca.TRAMITES],
                "campos_comparar": [list(c) for c in biblioteca.CAMPOS_COMPARAR], "generador": generador,
                "vacias": sorted(fuentes._VACIAS)}
    finally:
        for k in [k for k in os.environ if k.startswith("PULLEX_BIBLIOTECA_")]:
            del os.environ[k]
        os.environ.update(previas)


datos["biblioteca"] = biblioteca_de_ejemplo()

html = html.replace("<title>PULLEX IA — Asistente Jurídico Colombiano</title>", "<title>PULLEX IA Demo</title>")
html = html.replace('<link rel="manifest" href="/manifest.webmanifest">', "")
html = html.replace('href="/static/apple-touch-icon.png"', f'href="{data_uri(ST / "apple-touch-icon.png", "image/png")}"')
html = html.replace('href="/static/favicon.png"', f'href="{data_uri(ST / "favicon.png", "image/png")}"')
html = re.sub(r'<link rel="preload" href="/static/fonts/[^>]+>\n', "", html)
assert html.count('<link rel="stylesheet" href="/static/tema.css">') == 1
html = html.replace('<link rel="stylesheet" href="/static/tema.css">', "<style>\n" + tema_css + "\n</style>")
assert html.count('<script src="/static/apariencia.js"></script>') == 1
html = html.replace('<script src="/static/apariencia.js"></script>', "<script>\n" + apariencia_js + "\n</script>")

cinta = """
<style>
body{display:flex;flex-direction:column}
.demo-cinta{flex:none;height:30px;line-height:30px;padding:0 12px;box-sizing:content-box;
  padding-top:env(safe-area-inset-top,0px);background:var(--text);color:var(--bg);
  font:600 12.5px/30px var(--font-ui);text-align:center;white-space:nowrap;
  overflow:hidden;text-overflow:ellipsis}
.demo-cinta b{font-weight:800}
#app{flex:1;min-height:0;height:auto}
#auth{top:calc(30px + env(safe-area-inset-top,0px))}
</style>
<div class="demo-cinta"><b>Demostración</b> · datos de ejemplo</div>
"""
html = re.sub(r"(<body[^>]*>)", r"\1" + cinta.replace("\\", "\\\\"), html, count=1)

prellenar = """
document.addEventListener('DOMContentLoaded',()=>{});
(function(){const e=document.getElementById('a-email'),c=document.getElementById('a-clave');
  if(e&&!e.value)e.value='demo@pullex.co';if(c&&!c.value)c.value='demostracion';})();
// En la demostración no se pueden descargar archivos ni imprimir: se avisa en vez de no hacer nada.
(function(){const aviso=()=>toast('En la app real esto descarga el archivo; la demostración no guarda archivos.');
  descargar=aviso;imprimirPDF=aviso;exportarExcel=aviso;
  ACCIONES.imprimirPDF=aviso;ACCIONES.exportarExcel=aviso;})();
"""
bloque = ("<script>window.__DEMO_DATOS__=" + json.dumps(datos, ensure_ascii=False).replace("</", "<\\/") +
          ";</script>\n<script>" + mock + "</script>\n<script>" + app_js + prellenar + "</script>")
assert html.count('<script src="/static/app.js"></script>') == 1
html = html.replace('<script src="/static/app.js"></script>', bloque)
# Automatizador: mismo documentos.js; la descarga en Word muestra un aviso (la demo no genera archivos).
aviso_word = ("\ndocDescargarWord=function(){toast('En la app real esto descarga el borrador en Word (.docx); "
              "la demostración no genera archivos.')};\n")
assert html.count('<script src="/static/documentos.js"></script>') == 1
html = html.replace('<script src="/static/documentos.js"></script>',
                    "<script>" + docs_js.replace("</script", "<\\/script") + aviso_word + "</script>")
# Biblioteca: mismo biblioteca.js; sus datos son el catálogo ficticio que sirve demo/mock.js.
assert html.count('<script src="/static/biblioteca.js"></script>') == 1
html = html.replace('<script src="/static/biblioteca.js"></script>', "<script>" + bib_js.replace("</script", "<\\/script") + "</script>")

# Herramientas (términos y liquidación): los cálculos corren en el servidor (procedimientos/), así que en la
# demostración la vista carga y avisa que no está disponible (mock.js responde 404 a /api/procedimientos).
herr_js = (ST / "herramientas.js").read_text(encoding="utf-8")
assert html.count('<script src="/static/herramientas.js"></script>') == 1
html = html.replace('<script src="/static/herramientas.js"></script>',
                    "<script>" + herr_js.replace("</script", "<\\/script") + "</script>")

# Perfiles y coordinador: la demostración sin servidor no trae el registro (1.000 fichas). Se retiran la entrada
# de Ajustes y el script; la vista vacía queda oculta porque nadie la abre.
assert html.count('<script src="/static/perfiles.js"></script>') == 1
html = html.replace('<script src="/static/perfiles.js"></script>\n', "")
html, n = re.subn(r"\s*<!-- perfiles:inicio.*?<!-- perfiles:fin -->", "", html, flags=re.S)
assert n == 1

salida = RAIZ / "demo" / "pullex-demo.html"
salida.write_text(html, encoding="utf-8")
print(f"{salida} ({len(html.encode('utf-8')) // 1024} KB)")
