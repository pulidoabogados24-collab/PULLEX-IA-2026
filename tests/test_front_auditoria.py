"""Comprobaciones estáticas de las correcciones de frontend de la auditoría 2026-10-13 y de la app instalable (PWA).
Las pruebas de comportamiento en navegador están en tests/e2e_front_auditoria.py y tests/e2e_seguridad_md.py."""
import base64
import hashlib
import json
import re
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
ST = RAIZ / "static"


def leer(nombre):
    return (ST / nombre).read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def csp(modulo):
    return {d.strip().split(" ")[0]: d.strip() for d in modulo.CSP.split(";") if d.strip()}


def test_FRONT_001_script_src_son_los_archivos_exactos_que_carga_la_pagina(csp):
    externos = re.findall(r'<script src="(https://[^"]+)"', leer("index.html"))
    assert externos and csp["script-src"] == "script-src 'self' " + " ".join(externos)
    assert "https://cdnjs.cloudflare.com " not in csp["script-src"] + " "      # nunca todo cdnjs


def test_FRONT_002_estilos_en_linea_solo_por_huella(csp):
    elem = csp["style-src-elem"]
    assert "'unsafe-inline'" not in elem
    for pagina in ("index.html", "admin.html", "restablecer.html"):
        for bloque in re.findall(r"<style[^>]*>(.*?)</style>", leer(pagina), re.S):
            h = "'sha256-" + base64.b64encode(hashlib.sha256(bloque.encode()).digest()).decode() + "'"
            assert h in elem, pagina
    assert csp["style-src-attr"] == "style-src-attr 'unsafe-inline'"


def test_FRONT_003_paginas_nuevas_sin_javascript_en_linea():
    for pagina in ("politica-datos.html", "sin-conexion.html"):
        fuente = leer(pagina)
        assert fuente.startswith("<!doctype html>") and 'name="viewport"' in fuente, pagina
        assert not re.search(r"\son[a-z]+\s*=", fuente) and "javascript:" not in fuente, pagina
        assert not re.search(r"<script(?![^>]*\ssrc=)[^>]*>", fuente), pagina
        assert "<style" not in fuente and "/static/tema.css" in fuente and "/static/paginas.css" in fuente, pagina
    pol = leer("politica-datos.html")
    assert '<main id="politica"' in pol and "Tus derechos" in pol and "Pendiente de revisión jurídica" in pol


def test_FRONT_004_registro_exige_la_politica():
    html, app = leer("index.html"), leer("app.js")
    assert 'id="r-acepto"' in html and "He leído y acepto la <a href=\"/politica-de-datos\" target=\"_blank\"" in html
    assert html.count('href="/politica-de-datos"') >= 3              # casilla, pie del ingreso y Ajustes
    assert "acepto_politica:true" in app and "!$('r-acepto').checked" in app


def test_FRONT_005_service_worker_prudente():
    sw = leer("sw.js")
    assert int(re.search(r'const CACHE = "pullex-v(\d+)"', sw).group(1)) >= 13
    assert '"/static/sin-conexion.html"' in sw and "r.ok" in sw and "no-store" in sw
    assert "Response.error()" in sw                                  # sin red y sin copia: error, no un 200 inventado


def test_FRONT_006_manifiesto_instalable():
    m = json.loads(leer("manifest.webmanifest"))
    assert m["name"] == m["short_name"] == "PULLEX IA"
    assert m["id"] == m["start_url"] == m["scope"] == "/" and m["display"] == "standalone"
    assert m["background_color"] == m["theme_color"] == "#101115" and m.get("orientation")
    Image = pytest.importorskip("PIL.Image")
    propositos = set()
    for ic in m["icons"] + m.get("screenshots", []):
        ruta = RAIZ / ic["src"].lstrip("/")
        assert ruta.is_file(), ic["src"]
        assert Image.open(ruta).size == tuple(int(x) for x in ic["sizes"].split("x")), ic["src"]
        propositos.add((ic["sizes"], ic.get("purpose", "any")))
    assert {("192x192", "any"), ("512x512", "any"), ("192x192", "maskable"), ("512x512", "maskable")} <= propositos
    assert Image.open(ST / "apple-touch-icon.png").size == (180, 180)


def test_FRONT_007_etiquetas_ios_y_android():
    html = leer("index.html")
    for etiqueta in ('name="apple-mobile-web-app-capable" content="yes"', 'name="mobile-web-app-capable" content="yes"',
                     'name="apple-mobile-web-app-status-bar-style"', 'name="apple-mobile-web-app-title" content="PULLEX IA"',
                     'media="(prefers-color-scheme: dark)"', 'media="(prefers-color-scheme: light)"',
                     'rel="apple-touch-icon" sizes="180x180"', "viewport-fit=cover"):
        assert etiqueta in html, etiqueta
    assert "env(safe-area-inset-" in leer("justicia.css") and "display-mode:standalone" in leer("justicia.css")


def test_FRONT_008_sin_token_global_ni_desplazamiento_suave_directo():
    app = leer("app.js")
    assert not re.search(r"\blet TOKEN\b|\bTOKEN=", app)
    for nombre in ("app.js", "documentos.js", "perfiles.js", "taller.js"):
        assert "behavior:'smooth'" not in leer(nombre).replace("behavior:movimientoReducido()?'auto':'smooth'", ""), nombre
