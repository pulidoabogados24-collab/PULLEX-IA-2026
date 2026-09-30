"""Genera demo/pullex-demo.html: la app completa en un solo archivo, sin servidor, con datos de
ejemplo (demo/datos_demo.json + demo/mock.js). Sirve para mostrar PULLEX IA desde cualquier
navegador o publicarla como página.

    python demo/construir_demo.py
"""
import base64
import json
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
ST = RAIZ / "static"


def data_uri(ruta: Path, mime: str) -> str:
    return f"data:{mime};base64," + base64.b64encode(ruta.read_bytes()).decode()


html = (ST / "index.html").read_text(encoding="utf-8")
app_js = (ST / "app.js").read_text(encoding="utf-8")
mock = (RAIZ / "demo" / "mock.js").read_text(encoding="utf-8")
datos = json.loads((RAIZ / "demo" / "datos_demo.json").read_text(encoding="utf-8"))

html = html.replace("<title>PULLEX IA — Asistente Jurídico Colombiano</title>", "<title>PULLEX IA Demo</title>")
html = html.replace('<link rel="manifest" href="/manifest.webmanifest">', "")
html = html.replace('href="/static/apple-touch-icon.png"', f'href="{data_uri(ST / "apple-touch-icon.png", "image/png")}"')
html = html.replace('href="/static/favicon.png"', f'href="{data_uri(ST / "favicon.png", "image/png")}"')

cinta = """
<style>
body{display:flex;flex-direction:column}
.demo-cinta{flex:none;height:30px;line-height:30px;padding:0 12px;box-sizing:content-box;
  padding-top:env(safe-area-inset-top,0px);background:#FFC93C;color:#20170a;
  font:600 12.5px/30px 'Segoe UI',system-ui,sans-serif;text-align:center;white-space:nowrap;
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

salida = RAIZ / "demo" / "pullex-demo.html"
salida.write_text(html, encoding="utf-8")
print(f"{salida} ({len(html) // 1024} KB)")
