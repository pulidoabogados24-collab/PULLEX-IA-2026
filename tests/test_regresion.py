"""Regresión funcional: lo que ya funcionaba debe seguir funcionando."""
from conftest import auth, chat, login_admin, nuevo_usuario


def test_salud(cliente):
    r = cliente.get("/salud")
    assert r.status_code == 200 and r.json()["db"] is True


def test_paginas_publicas(cliente):
    for ruta in ("/", "/admin", "/sw.js", "/manifest.webmanifest", "/static/restablecer.html"):
        assert cliente.get(ruta).status_code == 200, ruta


def test_registro_login_estado(cliente):
    email, clave, t = nuevo_usuario(cliente)
    r = cliente.post("/api/login", json={"email": email, "clave": clave})
    assert r.status_code == 200
    e = cliente.get("/api/estado", headers=auth(r.json()["token"])).json()
    assert e["perfil"]["email"] == email and e["perfil"]["email_verificado"] is False


def test_verificacion_de_correo(cliente, modulo):
    email, _, t = nuevo_usuario(cliente)
    tok = modulo.generar_token_accion(email, "verificar_correo", horas_validez=24)
    assert cliente.get(f"/verificar-correo?token={tok}").status_code == 200
    assert cliente.get("/api/estado", headers=auth(t)).json()["perfil"]["email_verificado"] is True
    # un solo uso
    assert "no es válido" in cliente.get(f"/verificar-correo?token={tok}").text


def test_recuperar_clave_misma_respuesta_exista_o_no(cliente):
    email, _, _ = nuevo_usuario(cliente)
    a = cliente.post("/api/recuperar-clave", json={"email": email})
    b = cliente.post("/api/recuperar-clave", json={"email": "nadie@pruebas.local"})
    assert a.status_code == b.status_code == 200 and a.json() == b.json()


def test_chat_propio_y_historial(cliente):
    _, _, t = nuevo_usuario(cliente)
    cid = cliente.post("/api/conversaciones", headers=auth(t)).json()["id"]
    r = chat(cliente, t, cid, "¿Qué es una tutela?")
    assert r.status_code == 200 and "ECO:" in r.text and '"fin"' in r.text
    msgs = cliente.get(f"/api/conversaciones/{cid}/mensajes", headers=auth(t)).json()
    assert [m["rol"] for m in msgs] == ["user", "assistant"]
    lista = cliente.get("/api/conversaciones", headers=auth(t)).json()
    assert lista[0]["titulo"].startswith("¿Qué es una tutela?")
    assert cliente.delete(f"/api/conversaciones/{cid}", headers=auth(t)).status_code == 200
    assert cliente.get("/api/conversaciones", headers=auth(t)).json() == []


def test_chat_con_adjunto_pdf_valido(cliente):
    _, _, t = nuevo_usuario(cliente)
    cid = cliente.post("/api/conversaciones", headers=auth(t)).json()["id"]
    r = cliente.post("/api/chat", headers=auth(t), json={
        "conversacion": cid, "mensaje": "resume", "web": False,
        "adjuntos": [{"tipo": "document", "media_type": "application/pdf",
                      "datos": "JVBERi0xLjQK", "nombre": "sentencia.pdf"}]})
    assert r.status_code == 200


def test_preferencias(cliente):
    _, _, t = nuevo_usuario(cliente)
    r = cliente.post("/api/preferencias", headers=auth(t),
                     json={"modo": "profesional", "tema": "claro", "areas": ["Penal", "Inventada"]})
    assert r.status_code == 200 and r.json()["preferencias"]["areas"] == ["Penal"]


def test_admin_flujo_completo(cliente):
    email, _, _ = nuevo_usuario(cliente)
    t = login_admin(cliente)
    us = cliente.get("/api/admin/usuarios", headers=auth(t)).json()["usuarios"]
    assert any(u["email"] == email for u in us)
    r = cliente.post("/api/admin/actualizar", headers=auth(t),
                     json={"email": email, "plan": "pro", "activo": True, "reiniciar": True})
    assert r.status_code == 200 and r.json()["perfil"]["limite"] == 500
    assert cliente.get("/api/admin/metricas", headers=auth(t)).status_code == 200
    temporal = cliente.post("/api/admin/reset-clave", headers=auth(t), json={"email": email}).json()["temporal"]
    assert cliente.post("/api/login", json={"email": email, "clave": temporal}).status_code == 200


def test_boletin(cliente):
    _, _, t = nuevo_usuario(cliente)
    r = cliente.get("/api/boletin", headers=auth(t))
    assert r.status_code == 200 and r.json()["contenido"]


def test_sesiones_abiertas_antes_de_la_actualizacion_siguen_validas(cliente, modulo):
    """Tokens emitidos por la versión anterior (sin campo "v") no deben cerrar la sesión de
    los estudiantes al desplegar esta versión."""
    import base64, hashlib, hmac, json, time
    email, _, _ = nuevo_usuario(cliente)
    cuerpo = json.dumps({"u": email, "t": int(time.time())}).encode()
    firma = hmac.new(modulo.SECRET, cuerpo, hashlib.sha256).digest()
    legado = base64.urlsafe_b64encode(cuerpo).decode() + "." + base64.urlsafe_b64encode(firma).decode()
    assert cliente.get("/api/estado", headers=auth(legado)).status_code == 200


def test_base_de_datos_anterior_se_migra_sola(tmp_path, monkeypatch):
    """Una pullex.db creada por la versión entregada (sin sesion_version) arranca y migra."""
    import importlib, sqlite3, sys
    from pathlib import Path
    raiz = Path(__file__).resolve().parent.parent
    con = sqlite3.connect(tmp_path / "pullex.db")
    con.executescript("""CREATE TABLE usuarios(email TEXT PRIMARY KEY, nombre TEXT, sal TEXT, hash TEXT,
        plan TEXT DEFAULT 'prueba', limite INTEGER DEFAULT 10, usadas INTEGER DEFAULT 0, periodo TEXT,
        activo INTEGER DEFAULT 1, es_admin INTEGER DEFAULT 0, preferencias TEXT DEFAULT '{}', creado REAL);""")
    con.commit(); con.close()
    (tmp_path / "static").symlink_to(raiz / "static")
    monkeypatch.chdir(tmp_path)
    spec = importlib.util.spec_from_file_location("app_migracion", raiz / "app.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    cols = [r[1] for r in sqlite3.connect(tmp_path / "pullex.db").execute("PRAGMA table_info(usuarios)")]
    assert "email_verificado" in cols and "sesion_version" in cols
