"""Apariencia personalizable por usuario: validación estricta, imágenes y aislamiento entre cuentas."""
import base64
import struct
import zlib

from conftest import auth, nuevo_usuario


def _png(ancho=4, alto=4) -> bytes:
    """PNG real y mínimo (escala de grises) con las dimensiones pedidas."""
    def bloque(tipo, datos):
        return struct.pack(">I", len(datos)) + tipo + datos + struct.pack(">I", zlib.crc32(tipo + datos))
    filas = b"".join(b"\x00" + b"\x80" * ancho for _ in range(alto))
    return (b"\x89PNG\r\n\x1a\n" + bloque(b"IHDR", struct.pack(">IIBBBBB", ancho, alto, 8, 0, 0, 0, 0))
            + bloque(b"IDAT", zlib.compress(filas)) + bloque(b"IEND", b""))


def _jpeg(ancho=8, alto=8, relleno=0) -> bytes:
    """Cabecera JPEG suficiente para leer dimensiones (SOI, APP0, SOF0) + relleno + EOI."""
    app0 = b"\xff\xe0" + struct.pack(">H", 16) + b"JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
    sof0 = b"\xff\xc0" + struct.pack(">HBHHB", 11, 8, alto, ancho, 1) + b"\x01\x11\x00"
    return b"\xff\xd8" + app0 + sof0 + b"\x00" * relleno + b"\xff\xd9"


def _url(mime, datos):
    return f"data:{mime};base64," + base64.b64encode(datos).decode()


def _guardar(cliente, token, apariencia):
    return cliente.post("/api/preferencias", headers=auth(token), json={"apariencia": apariencia})


def test_apariencia_por_defecto_en_el_perfil(cliente):
    _, _, t = nuevo_usuario(cliente)
    a = cliente.get("/api/estado", headers=auth(t)).json()["perfil"]["preferencias"]["apariencia"]
    assert a["tema"] == "pullex" and a["modo"] == "claro" and a["acento"] is None
    assert a["imagenes"] == {"fondo": 0, "avatar": 0, "logo": 0}


def test_guardar_apariencia_valida(cliente):
    _, _, t = nuevo_usuario(cliente)
    r = _guardar(cliente, t, {"modo": "oscuro", "tema": "caribe", "acento": "#0B7A75", "fuente": "clasica",
                              "tamano": "grande", "densidad": "compacta", "radio": "recto"})
    assert r.status_code == 200, r.text
    a = r.json()["preferencias"]["apariencia"]
    assert (a["modo"], a["tema"], a["acento"], a["fuente"], a["tamano"], a["densidad"], a["radio"]) == \
        ("oscuro", "caribe", "#0b7a75", "clasica", "grande", "compacta", "recto")
    assert r.json()["preferencias"]["tema"] == "oscuro"  # el interruptor rápido queda sincronizado
    # cambio parcial: lo demás se conserva
    a2 = _guardar(cliente, t, {"tema": "toga"}).json()["preferencias"]["apariencia"]
    assert a2["tema"] == "toga" and a2["fuente"] == "clasica" and a2["acento"] == "#0b7a75"
    # quitar el acento propio
    assert _guardar(cliente, t, {"acento": None}).json()["preferencias"]["apariencia"]["acento"] is None


def test_color_invalido_se_rechaza(cliente):
    _, _, t = nuevo_usuario(cliente)
    for malo in ("red", "#fff", "#12345g", "#1234567", "url(javascript:alert(1))", 123, "#0b7a75;x:y"):
        r = _guardar(cliente, t, {"acento": malo})
        assert r.status_code == 400, malo
    assert cliente.get("/api/estado", headers=auth(t)).json()["perfil"]["preferencias"]["apariencia"]["acento"] is None


def test_valor_fuera_de_lista_blanca_se_rechaza(cliente):
    _, _, t = nuevo_usuario(cliente)
    for clave, malo in (("tema", "neon"), ("modo", "rosa"), ("fuente", "Comic Sans"), ("radio", 3)):
        assert _guardar(cliente, t, {clave: malo}).status_code == 400, clave
    assert cliente.post("/api/preferencias", headers=auth(t), json={"apariencia": "oscuro"}).status_code == 400


def test_clave_desconocida_se_ignora(cliente):
    _, _, t = nuevo_usuario(cliente)
    r = _guardar(cliente, t, {"tema": "jardin", "css": "body{display:none}", "__proto__": {"x": 1},
                              "imagenes": {"fondo": 999}})
    assert r.status_code == 200
    a = r.json()["preferencias"]["apariencia"]
    assert a["tema"] == "jardin" and "css" not in a and "__proto__" not in a
    assert a["imagenes"]["fondo"] == 0  # las versiones de imagen solo las pone el servidor


def test_imagen_svg_y_otros_formatos_rechazados(cliente):
    _, _, t = nuevo_usuario(cliente)
    svg = b'<svg xmlns="http://www.w3.org/2000/svg" onload="alert(1)"/>'
    malos = [
        _url("image/svg+xml", svg),
        "data:image/svg+xml;utf8,<svg onload=alert(1)>",
        _url("image/gif", b"GIF89a" + b"\x00" * 20),
        _url("image/webp", b"RIFF\x00\x00\x00\x00WEBP"),
        _url("image/png", svg),            # prefijo PNG pero el contenido es SVG
        _url("image/jpeg", _png()),        # prefijo y contenido no coinciden
        "https://ejemplo.com/foto.jpg",
        "data:text/html;base64,PGgxPmhvbGE8L2gxPg==",
    ]
    for tipo in ("fondo", "avatar", "logo"):
        for malo in malos:
            r = _guardar(cliente, t, {tipo: malo})
            assert r.status_code == 400, (tipo, malo[:40])
    assert cliente.get("/api/apariencia/imagen/fondo", headers=auth(t)).status_code == 404


def test_imagen_demasiado_grande_rechazada(cliente):
    _, _, t = nuevo_usuario(cliente)
    pesada = _jpeg(800, 600, relleno=360 * 1024)
    r = _guardar(cliente, t, {"fondo": _url("image/jpeg", pesada)})
    assert r.status_code == 400 and "pesa demasiado" in r.json()["detail"]
    r = _guardar(cliente, t, {"avatar": _url("image/jpeg", _jpeg(256, 256, relleno=130 * 1024))})
    assert r.status_code == 400
    # dimensiones por encima del tope (aunque pese poco)
    r = _guardar(cliente, t, {"fondo": _url("image/png", _png(1700, 10))})
    assert r.status_code == 400 and "px" in r.json()["detail"]
    r = _guardar(cliente, t, {"avatar": _url("image/png", _png(600, 600))})
    assert r.status_code == 400


def test_imagen_valida_se_guarda_sirve_y_borra(cliente):
    _, _, t = nuevo_usuario(cliente)
    png = _png(256, 256)
    r = _guardar(cliente, t, {"avatar": _url("image/png", png), "fondo": _url("image/jpeg", _jpeg(1600, 900, 2000))})
    assert r.status_code == 200, r.text
    imgs = r.json()["preferencias"]["apariencia"]["imagenes"]
    assert imgs["avatar"] > 0 and imgs["fondo"] > 0 and imgs["logo"] == 0
    g = cliente.get("/api/apariencia/imagen/avatar", headers=auth(t))
    assert g.status_code == 200 and g.content == png and g.headers["content-type"] == "image/png"
    assert g.headers["x-content-type-options"] == "nosniff"
    assert cliente.get("/api/apariencia/imagen/fondo", headers=auth(t)).headers["content-type"] == "image/jpeg"
    # el perfil no carga los bytes de la imagen (solo su versión)
    assert "base64" not in cliente.get("/api/estado", headers=auth(t)).text
    # borrar
    r = _guardar(cliente, t, {"avatar": None})
    assert r.json()["preferencias"]["apariencia"]["imagenes"]["avatar"] == 0
    assert cliente.get("/api/apariencia/imagen/avatar", headers=auth(t)).status_code == 404
    assert cliente.get("/api/apariencia/imagen/fondo", headers=auth(t)).status_code == 200


def test_imagen_requiere_sesion_y_tipo_conocido(cliente):
    _, _, t = nuevo_usuario(cliente)
    assert cliente.get("/api/apariencia/imagen/avatar").status_code == 401
    assert cliente.get("/api/apariencia/imagen/../../usuarios", headers=auth(t)).status_code == 404
    assert cliente.get("/api/apariencia/imagen/secreto", headers=auth(t)).status_code == 404


def test_aislamiento_entre_usuarios(cliente):
    _, _, ta = nuevo_usuario(cliente, nombre="Ana")
    _, _, tb = nuevo_usuario(cliente, nombre="Beto")
    assert _guardar(cliente, ta, {"tema": "toga", "acento": "#7b1e34",
                                  "avatar": _url("image/png", _png(64, 64))}).status_code == 200
    pb = cliente.get("/api/estado", headers=auth(tb)).json()["perfil"]["preferencias"]["apariencia"]
    assert pb["tema"] == "pullex" and pb["acento"] is None and pb["imagenes"]["avatar"] == 0
    assert cliente.get("/api/apariencia/imagen/avatar", headers=auth(tb)).status_code == 404
    assert cliente.get("/api/apariencia/imagen/avatar", headers=auth(ta)).status_code == 200
    # B guarda lo suyo y no toca lo de A
    _guardar(cliente, tb, {"avatar": _url("image/png", _png(32, 32))})
    a = cliente.get("/api/apariencia/imagen/avatar", headers=auth(ta)).content
    b = cliente.get("/api/apariencia/imagen/avatar", headers=auth(tb)).content
    assert a != b and a == _png(64, 64)


def test_interruptor_de_tema_sincroniza_el_modo(cliente):
    _, _, t = nuevo_usuario(cliente)
    p = cliente.post("/api/preferencias", headers=auth(t), json={"tema": "oscuro"}).json()["preferencias"]
    assert p["apariencia"]["modo"] == "oscuro"
    p = _guardar(cliente, t, {"modo": "auto"}).json()["preferencias"]
    assert p["apariencia"]["modo"] == "auto" and p["tema"] == "oscuro"
