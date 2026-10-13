"""Pruebas de regresión del área AUTENTICACIÓN, SESIONES Y LÍMITES (auditoría del 13-oct-2026, secciones C y F).

Cada prueba lleva el identificador del hallazgo (AUTH-01 … AUTH-13, IA-17). Salen de los guiones de reproducción del
auditor (p02_desactivada, p01_p03, p04_carrera, p05_instancia, idor_cuota, info): se escribieron contra el código
de pul/base-datos (64d8322), donde fallan, y pasan con las correcciones de la rama fix/auth.
"""
from contextlib import closing

from conftest import ADMIN_EMAIL, FakeAnthropic, auth, login_admin, nuevo_usuario

MENSAJE_INACTIVA = "Tu cuenta está inactiva"


def _conv(cliente, token):
    r = cliente.post("/api/conversaciones", headers=auth(token))
    assert r.status_code == 200, r.text
    return r.json()["id"]


def _sql(modulo, sentencia, parametros=()):
    with closing(modulo.db()) as con:
        cur = con.execute(sentencia, parametros)
        con.commit()
        return cur.rowcount


def _usuario(modulo, email):
    return modulo.obtener_usuario(email)


# --------------------------------------------------------------------------------------------- AUTH-01 --
# Rutas que una cuenta desactivada no debe poder usar (todas pasan por usuario_actual).
RUTAS_PROTEGIDAS = [
    ("GET", "/api/estado", None), ("GET", "/api/conversaciones", None), ("POST", "/api/conversaciones", {}),
    ("POST", "/api/preferencias", {"memoria": "escrita estando desactivada"}),
    ("GET", "/api/documentos/mis", None), ("GET", "/api/documentos/catalogo", None),
    ("GET", "/api/biblioteca/resumen", None), ("GET", "/api/academia/mapa", None), ("GET", "/api/modular/progreso", None),
    ("GET", "/api/taller/mis", None), ("POST", "/api/taller/escenario", {"tipo": "tutela", "nivel": "basico", "fuente": "banco"}),
    ("GET", "/api/perfiles", None), ("POST", "/api/estilo/revisar", {"texto": "hola mundo"}), ("GET", "/api/boletin", None),
    ("POST", "/api/cerrar-sesiones", {}),
]


def test_AUTH01_cuenta_inactiva_recibe_403_en_todas_las_rutas(cliente, modulo):
    """activo=0 puesto directamente en la base (sin cerrar sesiones): usuario_actual debe rechazarla igual."""
    email, _, t = nuevo_usuario(cliente)
    cid = _conv(cliente, t)
    _sql(modulo, "UPDATE usuarios SET activo=0 WHERE email=?", (email,))
    for metodo, ruta, cuerpo in RUTAS_PROTEGIDAS + [("GET", f"/api/conversaciones/{cid}/mensajes", None)]:
        r = cliente.request(metodo, ruta, headers=auth(t), json=cuerpo)
        assert r.status_code == 403, (ruta, r.status_code, r.text[:200])
        assert MENSAJE_INACTIVA in r.json()["detail"], ruta
    assert "escrita estando desactivada" not in (_usuario(modulo, email)["preferencias"] or "")


def test_AUTH01_desactivar_cierra_las_sesiones_y_el_login_da_403(cliente, modulo):
    email, clave, t = nuevo_usuario(cliente)
    admin = login_admin(cliente)
    version = int(_usuario(modulo, email)["sesion_version"] or 0)
    r = cliente.post("/api/admin/actualizar", headers=auth(admin), json={"email": email, "activo": False})
    assert r.status_code == 200 and r.json()["perfil"]["activo"] is False
    assert int(_usuario(modulo, email)["sesion_version"] or 0) == version + 1     # desactivar = cerrar todas sus sesiones
    for metodo, ruta, cuerpo in RUTAS_PROTEGIDAS:
        assert cliente.request(metodo, ruta, headers=auth(t), json=cuerpo).status_code in (401, 403), ruta
    # login nuevo: con la clave correcta, 403 claro; con la clave errada, el 401 de siempre (no revela el estado)
    r = cliente.post("/api/login", json={"email": email, "clave": clave})
    assert r.status_code == 403 and MENSAJE_INACTIVA in r.json()["detail"] and "token" not in r.json()
    assert cliente.post("/api/login", json={"email": email, "clave": "clave-equivocada-1"}).status_code == 401
    # reactivar devuelve el acceso
    assert cliente.post("/api/admin/actualizar", headers=auth(admin), json={"email": email, "activo": True}).status_code == 200
    r = cliente.post("/api/login", json={"email": email, "clave": clave})
    assert r.status_code == 200
    assert cliente.get("/api/estado", headers=auth(r.json()["token"])).status_code == 200


def test_AUTH01_taller_modelo_no_llama_al_modelo_con_cuenta_inactiva(cliente, modulo):
    email, _, t = nuevo_usuario(cliente)
    esc = cliente.post("/api/taller/escenario", headers=auth(t), json={"tipo": "tutela", "nivel": "basico", "fuente": "banco"})
    assert esc.status_code == 200, esc.text
    eid = esc.json()["id"]
    _sql(modulo, "INSERT INTO taller_intentos(escenario_id,usuario,texto,evaluacion,puntaje,creado) VALUES(?,?,?,?,?,0)",
         (eid, email, "t", "{}", 50))
    _sql(modulo, "UPDATE usuarios SET activo=0 WHERE email=?", (email,))
    antes = len(FakeAnthropic.llamadas_taller)
    r = cliente.post("/api/taller/modelo", headers=auth(t), json={"escenario_id": eid})
    assert r.status_code == 403 and len(FakeAnthropic.llamadas_taller) == antes


def test_AUTH01_admin_desactivado_pierde_el_acceso_de_admin(cliente, modulo):
    email, clave, t = nuevo_usuario(cliente)
    _sql(modulo, "UPDATE usuarios SET es_admin=1 WHERE email=?", (email,))
    assert cliente.get("/api/admin/usuarios", headers=auth(t)).status_code == 200
    _sql(modulo, "UPDATE usuarios SET activo=0 WHERE email=?", (email,))
    for ruta in ("/api/admin/usuarios", "/api/admin/metricas", "/api/admin/motores"):
        assert cliente.get(ruta, headers=auth(t)).status_code == 403, ruta
    assert cliente.post("/api/admin/actualizar", headers=auth(t), json={"email": email, "activo": True}).status_code == 403
    assert cliente.post("/api/login", json={"email": email, "clave": clave}).status_code == 403


def test_AUTH01_el_admin_no_puede_desactivarse_a_si_mismo(cliente, modulo):
    admin = login_admin(cliente)
    r = cliente.post("/api/admin/actualizar", headers=auth(admin), json={"email": ADMIN_EMAIL, "activo": False})
    assert r.status_code == 400 and "propia cuenta" in r.json()["detail"]
    assert _usuario(modulo, ADMIN_EMAIL)["activo"]
    assert cliente.get("/api/admin/usuarios", headers=auth(admin)).status_code == 200
    # cambiar su propio plan sigue permitido
    assert cliente.post("/api/admin/actualizar", headers=auth(admin), json={"email": ADMIN_EMAIL, "plan": "premium"}).status_code == 200


# ------------------------------------------------------------------------------------ AUTH-03 y AUTH-13 --
import hashlib  # noqa: E402
import threading  # noqa: E402
import time  # noqa: E402


def _en_paralelo(n, funcion):
    """Lanza n hilos que arrancan a la vez (barrera) y devuelve los resultados en orden de hilo."""
    barrera = threading.Barrier(n)
    resultados = [None] * n

    def hilo(i):
        barrera.wait()
        resultados[i] = funcion(i)

    hilos = [threading.Thread(target=hilo, args=(i,)) for i in range(n)]
    [h.start() for h in hilos]
    [h.join(60) for h in hilos]
    return resultados


def _con_latencia(monkeypatch, modulo, segundos=0.03):
    """Cada conexión nueva tarda un poco (como la red hasta PostgreSQL): agranda la ventana entre validar y marcar
    el token si esos dos pasos van en conexiones distintas (el defecto de AUTH-03)."""
    original = modulo.db

    def db_lenta():
        time.sleep(segundos)
        return original()
    monkeypatch.setattr(modulo, "db", db_lenta)


def test_AUTH03_token_de_restablecimiento_se_usa_una_sola_vez_aunque_lleguen_a_la_vez(cliente, modulo, monkeypatch):
    from fastapi.testclient import TestClient
    email, _, _ = nuevo_usuario(cliente)
    token = modulo.generar_token_accion(email, "restablecer_clave", 1)
    _con_latencia(monkeypatch, modulo)

    def intentar(i):
        return TestClient(modulo.app).post("/api/restablecer-clave", json={"token": token, "clave": f"nueva-clave-{i:02d}"}).status_code
    codigos = _en_paralelo(5, intentar)
    monkeypatch.undo()
    assert sorted(codigos) == [200, 400, 400, 400, 400], codigos
    ganadora = codigos.index(200)
    modulo._intentos.clear()                # el límite por IP de esta prueba no es lo que se mide
    for i in range(5):
        r = cliente.post("/api/login", json={"email": email, "clave": f"nueva-clave-{i:02d}"})
        assert r.status_code == (200 if i == ganadora else 401), i


def test_AUTH03_enlace_de_verificacion_se_usa_una_sola_vez_aunque_lleguen_a_la_vez(cliente, modulo, monkeypatch):
    from fastapi.testclient import TestClient
    email, _, _ = nuevo_usuario(cliente)
    token = modulo.generar_token_accion(email, "verificar_correo", 24)
    _con_latencia(monkeypatch, modulo)
    textos = _en_paralelo(4, lambda i: TestClient(modulo.app).get(f"/verificar-correo?token={token}").text)
    monkeypatch.undo()
    assert sum("Correo verificado" in t for t in textos) == 1, textos
    assert _usuario(modulo, email)["email_verificado"]


def test_AUTH13_los_tokens_de_accion_se_guardan_como_huella(cliente, modulo):
    email, _, _ = nuevo_usuario(cliente)
    token = modulo.generar_token_accion(email, "restablecer_clave", 1)
    huella = hashlib.sha256(token.encode()).hexdigest()
    with closing(modulo.db()) as con:
        assert con.execute("SELECT COUNT(*) c FROM tokens_accion WHERE token=?", (token,)).fetchone()["c"] == 0
        assert con.execute("SELECT email FROM tokens_accion WHERE token=?", (huella,)).fetchone()["email"] == email
    # quien lea la base (copia filtrada) y mande la huella como si fuera el enlace, no entra
    assert cliente.post("/api/restablecer-clave", json={"token": huella, "clave": "clave-del-atacante"}).status_code == 400
    assert cliente.post("/api/restablecer-clave", json={"token": token, "clave": "clave-legitima-1"}).status_code == 200


def test_AUTH13_purga_los_tokens_vencidos_hace_mas_de_un_dia(cliente, modulo):
    email, _, _ = nuevo_usuario(cliente)
    ahora = time.time()
    _sql(modulo, "INSERT INTO tokens_accion(token,email,tipo,creado,expira,usado) VALUES(?,?,?,?,?,0)",
         ("viejo-" + email, email, "verificar_correo", ahora - 4 * 86400, ahora - 3 * 86400))
    _sql(modulo, "INSERT INTO tokens_accion(token,email,tipo,creado,expira,usado) VALUES(?,?,?,?,?,0)",
         ("reciente-" + email, email, "verificar_correo", ahora - 7200, ahora - 3600))
    modulo.generar_token_accion(email, "verificar_correo", 24)
    with closing(modulo.db()) as con:
        quedan = {f["token"] for f in con.execute("SELECT token FROM tokens_accion WHERE email=?", (email,)).fetchall()}
    assert "viejo-" + email not in quedan and "reciente-" + email in quedan


def test_AUTH13_token_vencido_o_de_otro_tipo_no_sirve(cliente, modulo):
    email, _, _ = nuevo_usuario(cliente)
    token = modulo.generar_token_accion(email, "verificar_correo", 24)
    assert cliente.post("/api/restablecer-clave", json={"token": token, "clave": "otra-clave-123"}).status_code == 400
    vencido = modulo.generar_token_accion(email, "restablecer_clave", -1)
    assert cliente.post("/api/restablecer-clave", json={"token": vencido, "clave": "otra-clave-123"}).status_code == 400
    assert "Correo verificado" in cliente.get(f"/verificar-correo?token={token}").text


# --------------------------------------------------------------------------------------------- AUTH-02 --
def test_AUTH02_por_defecto_no_se_exige_verificar_el_correo(cliente, modulo, monkeypatch):
    monkeypatch.delenv("PULLEX_EXIGIR_VERIFICACION", raising=False)
    email, _, t = nuevo_usuario(cliente)
    assert not _usuario(modulo, email)["email_verificado"]
    r = cliente.post("/api/chat", headers=auth(t), json={"conversacion": _conv(cliente, t), "mensaje": "hola", "web": False})
    assert r.status_code == 200


def test_AUTH02_con_la_variable_las_consultas_exigen_correo_verificado(cliente, modulo, monkeypatch):
    import pytest
    from fastapi import HTTPException
    monkeypatch.setenv("PULLEX_EXIGIR_VERIFICACION", "1")
    email, _, t = nuevo_usuario(cliente)
    cid = _conv(cliente, t)
    r = cliente.post("/api/chat", headers=auth(t), json={"conversacion": cid, "mensaje": "hola", "web": False})
    assert r.status_code == 403 and "Confirma tu correo" in r.json()["detail"]
    assert cliente.post("/api/chat", headers=auth(t), json={"conversacion": cid, "continuar": True}).status_code == 403
    u = _usuario(modulo, email)
    with pytest.raises(HTTPException) as e:
        modulo.consumir_consulta(u)
    assert e.value.status_code == 403
    with pytest.raises(HTTPException) as e:
        modulo._verificar_cupo(u, 1)
    assert e.value.status_code == 403
    assert _usuario(modulo, email)["usadas"] == 0                     # no se cobró nada
    # el resto de la app (sin costo) sigue disponible para que pueda pedir el enlace
    assert cliente.get("/api/estado", headers=auth(t)).status_code == 200
    # al verificar, puede consultar
    token = modulo.generar_token_accion(email, "verificar_correo", 24)
    assert "Correo verificado" in cliente.get(f"/verificar-correo?token={token}").text
    r = cliente.post("/api/chat", headers=auth(t), json={"conversacion": cid, "mensaje": "hola", "web": False})
    assert r.status_code == 200
    # el administrador queda exento
    admin = login_admin(cliente)
    _sql(modulo, "UPDATE usuarios SET email_verificado=0 WHERE email=?", (ADMIN_EMAIL,))
    try:
        r = cliente.post("/api/chat", headers=auth(admin), json={"conversacion": _conv(cliente, admin), "mensaje": "hola", "web": False})
        assert r.status_code == 200
    finally:
        _sql(modulo, "UPDATE usuarios SET email_verificado=1 WHERE email=?", (ADMIN_EMAIL,))


def test_AUTH02_reenviar_verificacion_tiene_tope_por_cuenta(cliente, modulo, monkeypatch):
    enviados = []
    monkeypatch.setattr(modulo, "enviar_correo", lambda a, asunto, html: enviados.append(a) or True)
    email, _, t = nuevo_usuario(cliente)
    enviados.clear()
    codigos = []
    for _ in range(5):
        modulo._intentos.clear()                       # como si cada intento llegara desde otra IP
        codigos.append(cliente.post("/api/reenviar-verificacion", headers=auth(t)).status_code)
    assert codigos == [200, 200, 200, 429, 429] and len(enviados) == 3


def test_AUTH02_restablecer_la_clave_por_correo_verifica_el_correo(cliente, modulo):
    email, _, _ = nuevo_usuario(cliente)
    assert not _usuario(modulo, email)["email_verificado"]
    token = modulo.generar_token_accion(email, "restablecer_clave", 1)
    assert cliente.post("/api/restablecer-clave", json={"token": token, "clave": "nueva-clave-456"}).status_code == 200
    assert _usuario(modulo, email)["email_verificado"]


# --------------------------------------------------------------------------------------------- AUTH-04 --
def _peticion(xff=None, cliente_ip="203.0.113.9"):
    from starlette.requests import Request
    cabeceras = [(b"x-forwarded-for", xff.encode())] if xff is not None else []
    return Request({"type": "http", "method": "GET", "path": "/", "headers": cabeceras, "client": (cliente_ip, 1234)})


def test_AUTH04_ip_de_solo_cree_al_ultimo_proxy_confiable(modulo, monkeypatch):
    for n in ("VERCEL", "RENDER", "PULLEX_PROXIES_CONFIABLES"):
        monkeypatch.delenv(n, raising=False)
    # en local (sin proxy) la cabecera la escribe el cliente: no se le cree
    assert modulo.ip_de(_peticion("1.1.1.1")) == "203.0.113.9"
    monkeypatch.setenv("RENDER", "true")             # Render: un proxy que AGREGA la IP real al final
    assert modulo.ip_de(_peticion("6.6.6.6, 198.51.100.7")) == "198.51.100.7"
    monkeypatch.delenv("RENDER")
    monkeypatch.setenv("VERCEL", "1")
    assert modulo.ip_de(_peticion("198.51.100.8")) == "198.51.100.8"
    assert modulo.ip_de(_peticion(None)) == "203.0.113.9"
    monkeypatch.setenv("PULLEX_PROXIES_CONFIABLES", "2")
    assert modulo.ip_de(_peticion("6.6.6.6, 198.51.100.7, 10.0.0.1")) == "198.51.100.7"
    assert modulo.ip_de(_peticion("198.51.100.7")) == "198.51.100.7"         # menos saltos de los esperados
    monkeypatch.setenv("PULLEX_PROXIES_CONFIABLES", "0")
    assert modulo.ip_de(_peticion("6.6.6.6")) == "203.0.113.9"


def test_AUTH04_rotar_x_forwarded_for_no_evade_el_limite_por_ip(cliente, monkeypatch):
    for n in ("VERCEL", "RENDER", "PULLEX_PROXIES_CONFIABLES"):
        monkeypatch.delenv(n, raising=False)
    codigos = [cliente.post("/api/registro", headers={"X-Forwarded-For": f"10.0.{i // 250}.{i % 250}"},
                            json={"email": f"rotar{i}_{time.time_ns()}@pruebas.local", "nombre": "Bot",
                                  "clave": "clave-segura-123", "acepto_politica": True}).status_code for i in range(12)]
    assert codigos[:8] == [200] * 8 and set(codigos[8:]) == {429}, codigos


def test_AUTH04_podar_nunca_vacia_el_diccionario_y_conserva_a_los_bloqueados(modulo, monkeypatch):
    monkeypatch.setattr(modulo, "_MAX_CLAVES_LIMITE", 50)
    d = {}
    ahora = time.time()
    d["login:victima@x.co"] = [ahora - 30 + i for i in range(10)]          # la víctima: bloqueada, intentos algo viejos
    for i in range(60):
        d[f"login:relleno{i}@x.co"] = [ahora]                               # relleno del atacante, más reciente
    modulo._podar(d, ahora, 900)
    assert 0 < len(d) <= 50 and "login:victima@x.co" in d


def test_AUTH04_el_correo_del_login_se_recorta_antes_de_usarlo_como_clave(cliente, modulo):
    enorme = "a" * 100_000 + "@x.co"
    assert cliente.post("/api/login", json={"email": enorme, "clave": "x"}).status_code == 401
    claves = list(modulo._intentos_cuenta)
    with closing(modulo.db()) as con:
        claves += [f["clave"] for f in con.execute("SELECT clave FROM limites").fetchall()]
    assert claves and max(len(c) for c in claves) <= 300


def test_AUTH04_el_limite_por_cuenta_se_comparte_entre_instancias(cliente, modulo):
    """Diez intentos fallidos contra una cuenta; luego «otra instancia» (memoria vacía) sigue bloqueando."""
    email, clave, _ = nuevo_usuario(cliente)
    for i in range(10):
        modulo._intentos.clear()
        assert cliente.post("/api/login", json={"email": email, "clave": f"mala-{i}"}).status_code == 401
    modulo._intentos.clear()
    modulo._intentos_cuenta.clear()                 # otra instancia de Vercel: no tiene nada en memoria
    assert cliente.post("/api/login", json={"email": email, "clave": clave}).status_code == 429
    with closing(modulo.db()) as con:
        assert con.execute("SELECT n FROM limites WHERE clave=?", ("login:" + email,)).fetchone()["n"] >= 11


def test_AUTH04_si_la_base_falla_el_limite_sigue_en_memoria(modulo, monkeypatch):
    import pytest
    from fastapi import HTTPException

    def sin_base():
        raise modulo.base_datos.ErrorConexion("simulado")
    monkeypatch.setattr(modulo, "db", sin_base)
    clave = f"prueba-memoria:{time.time_ns()}"
    modulo.limitar_cuenta(clave, 2, 60)
    modulo.limitar_cuenta(clave, 2, 60)
    with pytest.raises(HTTPException) as e:
        modulo.limitar_cuenta(clave, 2, 60)
    assert e.value.status_code == 429


# --------------------------------------------------------------------------------------------- AUTH-05 --
def _trozos(total, trozo=64 * 1024):
    yield b'{"email":"a@b.co","clave":"'
    enviado = 0
    while enviado < total:
        yield b"A" * trozo
        enviado += trozo
    yield b'"}'


def test_AUTH05_cuerpo_sin_content_length_que_supera_el_tope_da_413_con_cabeceras(cliente, modulo, monkeypatch):
    monkeypatch.setattr(modulo, "MAX_CUERPO", 256 * 1024)
    r = cliente.post("/api/login", content=_trozos(512 * 1024), headers={"Content-Type": "application/json"})
    assert r.status_code == 413 and "demasiado grande" in r.json()["detail"]
    assert r.headers.get("content-security-policy") and r.headers.get("x-frame-options") == "DENY"
    # con Content-Length declarado, igual (ya funcionaba) y también con las cabeceras de seguridad
    r = cliente.post("/api/login", content=b"{" + b" " * (300 * 1024) + b"}", headers={"Content-Type": "application/json"})
    assert r.status_code == 413 and r.headers.get("content-security-policy")
    # un cuerpo por trozos dentro del tope se procesa normal
    r = cliente.post("/api/login", content=_trozos(10 * 1024), headers={"Content-Type": "application/json"})
    assert r.status_code == 401


# ------------------------------------------------------------------------------------- AUTH-06 y AUTH-12 --
import json as _json  # noqa: E402
import os  # noqa: E402
import subprocess  # noqa: E402
import sys  # noqa: E402

from conftest import RAIZ  # noqa: E402


def _arrancar_app(tmp_path, extra, guion_extra=""):
    """Importa app.py en OTRO proceso (SQLite en tmp_path, sin secreto) y devuelve (proceso, json impreso o None)."""
    entorno = {k: v for k, v in os.environ.items() if k not in ("PULLEX_SECRET", "LEXCOL_SECRET", "VERCEL", "RENDER",
                                                               "PULLEX_DOCS", "PULLEX_PRUEBAS_PG_URL", "PULLEX_DB_ESQUEMA")}
    entorno.update({"PULLEX_DATABASE_URL": "", "POSTGRES_URL": "", "DATABASE_URL": "", "PULLEX_DB": str(tmp_path / "p.db"),
                    "PULLEX_BIBLIOTECA_DB": str(tmp_path / "b.db"), "PULLEX_CORPUS_DB": str(tmp_path / "c.db"),
                    "PULLEX_LOG_LEVEL": "ERROR", **extra})
    (tmp_path / "static").symlink_to(RAIZ / "static")
    guion = (f"import sys, json, os\nsys.path.insert(0, {str(RAIZ)!r})\nimport app\n"
             "from fastapi.testclient import TestClient\nc = TestClient(app.app)\n" + guion_extra)
    r = subprocess.run([sys.executable, "-c", guion], cwd=tmp_path, env=entorno, capture_output=True, text=True, timeout=180)
    lineas = r.stdout.strip().splitlines()
    return r, (_json.loads(lineas[-1]) if r.returncode == 0 and lineas else None)


def test_AUTH06_en_vercel_sin_PULLEX_SECRET_la_app_no_arranca(tmp_path):
    r, _ = _arrancar_app(tmp_path, {"VERCEL": "1"})
    assert r.returncode != 0 and "RuntimeError" in r.stderr and "PULLEX_SECRET" in r.stderr
    assert not (tmp_path / "app_secret.key").exists()


def test_AUTH06_secreto_local_con_permisos_0600_y_AUTH12_docs_solo_con_variable(tmp_path):
    r, d = _arrancar_app(tmp_path, {"PULLEX_DOCS": "1"},
                         "print(json.dumps({'secreto': c.get('/salud').json()['secreto_configurado'],\n"
                         "                  'openapi': c.get('/openapi.json').status_code, 'docs': c.get('/docs').status_code,\n"
                         "                  'modo': oct(os.stat(app.APP_SECRET_FILE).st_mode & 0o777)}))\n")
    assert r.returncode == 0, r.stderr[-3000:]
    assert d == {"secreto": False, "openapi": 200, "docs": 200, "modo": "0o600"}


def test_AUTH12_docs_y_openapi_desactivados_por_defecto(cliente):
    for ruta in ("/docs", "/redoc", "/openapi.json"):
        assert cliente.get(ruta).status_code == 404, ruta


def test_AUTH12_salud_sin_sesion_no_dice_modelo_ni_proveedor(cliente):
    s = cliente.get("/salud").json()
    assert set(s) == {"estado", "db", "db_motor", "db_persistente", "secreto_configurado", "ia_configurada"}
    assert s["secreto_configurado"] is True and s["estado"] == "ok"
    assert "claude" not in _json.dumps(s).lower() and "anthropic" not in _json.dumps(s).lower()


# ------------------------------------------------------------------------------------- AUTH-07 y AUTH-11 --
def _contar_pbkdf2(monkeypatch):
    """Registra las iteraciones de cada PBKDF2 que calcula la app."""
    llamadas = []
    original = hashlib.pbkdf2_hmac

    def contado(nombre, clave, sal, iteraciones, *a, **k):
        llamadas.append(iteraciones)
        return original(nombre, clave, sal, iteraciones, *a, **k)
    monkeypatch.setattr(hashlib, "pbkdf2_hmac", contado)
    return llamadas


def test_AUTH07_login_con_cuenta_inexistente_cuesta_lo_mismo_que_con_una_real(cliente, modulo, monkeypatch):
    email, _, _ = nuevo_usuario(cliente)
    llamadas = _contar_pbkdf2(monkeypatch)
    assert cliente.post("/api/login", json={"email": email, "clave": "clave-mala-1"}).status_code == 401
    con_cuenta = list(llamadas)
    llamadas.clear()
    assert cliente.post("/api/login", json={"email": f"nadie_{time.time_ns()}@pruebas.local", "clave": "clave-mala-1"}).status_code == 401
    assert con_cuenta == llamadas == [modulo.ITERACIONES_PBKDF2]


def test_AUTH11_politica_de_600000_iteraciones_en_el_codigo():
    fuente = (RAIZ / "app.py").read_text(encoding="utf-8")
    assert "\nITERACIONES_PBKDF2 = 600_000" in fuente and "\nITERACIONES_PBKDF2_ANTIGUAS = 200_000" in fuente


def test_AUTH11_hash_nuevo_con_prefijo_y_rehash_transparente_de_los_viejos(cliente, modulo, monkeypatch):
    monkeypatch.setattr(modulo, "ITERACIONES_PBKDF2", 600_000)       # la política real (conftest la baja por velocidad)
    t0 = time.perf_counter()
    email, clave, t = nuevo_usuario(cliente)
    print(f"\n[AUTH-11] registro con PBKDF2-SHA256 de 600 000 iteraciones: {(time.perf_counter() - t0) * 1000:.0f} ms")
    assert _usuario(modulo, email)["hash"].startswith("p600000$")
    # cuenta con el formato anterior (200 000 iteraciones, hex sin prefijo)
    sal = bytes.fromhex(_usuario(modulo, email)["sal"])
    viejo = hashlib.pbkdf2_hmac("sha256", clave.encode(), sal, 200_000).hex()
    _sql(modulo, "UPDATE usuarios SET hash=? WHERE email=?", (viejo, email))
    version = _usuario(modulo, email)["sesion_version"]
    assert cliente.post("/api/login", json={"email": email, "clave": "clave-mala-9"}).status_code == 401
    assert _usuario(modulo, email)["hash"] == viejo                   # clave errada: no se toca
    assert cliente.post("/api/login", json={"email": email, "clave": clave}).status_code == 200
    nuevo = _usuario(modulo, email)
    assert nuevo["hash"].startswith("p600000$") and nuevo["sesion_version"] == version
    assert cliente.get("/api/estado", headers=auth(t)).status_code == 200          # el rehash no cierra sesiones
    t0 = time.perf_counter()
    assert cliente.post("/api/login", json={"email": email, "clave": clave}).status_code == 200
    print(f"[AUTH-11] login verificando 600 000 iteraciones: {(time.perf_counter() - t0) * 1000:.0f} ms")


# ------------------------------------------------------------------------------------ AUTH-08, 09 y 10 --
def test_AUTH08_continuar_tiene_tope_de_tres_por_mensaje_aunque_no_quede_cupo(cliente, modulo):
    email, _, t = nuevo_usuario(cliente)
    cid = _conv(cliente, t)
    assert cliente.post("/api/chat", headers=auth(t), json={"conversacion": cid, "mensaje": "hola", "web": False}).status_code == 200
    with closing(modulo.db()) as con:
        mid = con.execute("SELECT id FROM mensajes WHERE conv=? AND rol='assistant'", (cid,)).fetchone()["id"]
    _sql(modulo, "UPDATE usuarios SET usadas=limite WHERE email=?", (email,))        # sin cupo (idor_cuota.py)
    codigos = []
    for _ in range(5):
        _sql(modulo, "UPDATE mensajes SET incompleta=1 WHERE id=?", (mid,))
        antes = len(FakeAnthropic.llamadas_stream)
        r = cliente.post("/api/chat", headers=auth(t), json={"conversacion": cid, "continuar": True, "web": False})
        codigos.append((r.status_code, len(FakeAnthropic.llamadas_stream) > antes))
    assert codigos == [(200, True)] * 3 + [(429, False)] * 2, codigos
    assert "máximo" in r.json()["detail"]
    with closing(modulo.db()) as con:
        assert con.execute("SELECT continuaciones FROM mensajes WHERE id=?", (mid,)).fetchone()["continuaciones"] == 3


def test_AUTH09_escrito_modelo_del_taller_limitado_a_6_por_hora(cliente, modulo):
    email, _, t = nuevo_usuario(cliente)
    eid = cliente.post("/api/taller/escenario", headers=auth(t), json={"tipo": "tutela", "nivel": "basico", "fuente": "banco"}).json()["id"]
    _sql(modulo, "INSERT INTO taller_intentos(escenario_id,usuario,texto,evaluacion,puntaje,creado) VALUES(?,?,?,?,?,0)",
         (eid, email, "t", "{}", 50))
    codigos, llamadas = [], []
    for _ in range(8):
        _sql(modulo, "DELETE FROM taller_modelos")              # sin caché: cada pedido iría al modelo
        antes = len(FakeAnthropic.llamadas_taller)
        codigos.append(cliente.post("/api/taller/modelo", headers=auth(t), json={"escenario_id": eid}).status_code)
        llamadas.append(len(FakeAnthropic.llamadas_taller) - antes)
    assert codigos == [200] * 6 + [429] * 2, codigos
    assert llamadas[6:] == [0, 0] and all(n >= 1 for n in llamadas[:6])


def test_AUTH10_el_reinicio_mensual_no_borra_consumos_de_otra_peticion(cliente, modulo):
    email, _, _ = nuevo_usuario(cliente)
    admin = login_admin(cliente)
    assert cliente.post("/api/admin/actualizar", headers=auth(admin), json={"email": email, "plan": "basico"}).status_code == 200
    _sql(modulo, "UPDATE usuarios SET periodo='2000-01', usadas=5 WHERE email=?", (email,))
    vieja = _usuario(modulo, email)                              # lo que leyó una petición antes del cambio de mes
    # otra petición simultánea ya reinició el mes y gastó 3 consultas
    _sql(modulo, "UPDATE usuarios SET periodo=?, usadas=3 WHERE email=?", (modulo.periodo_actual(), email))
    u = modulo.reiniciar_periodo_si_aplica(vieja)
    assert _usuario(modulo, email)["usadas"] == 3 and u["usadas"] == 3 and u["periodo"] == modulo.periodo_actual()
    # el reinicio normal sigue funcionando
    _sql(modulo, "UPDATE usuarios SET periodo='2000-01', usadas=5 WHERE email=?", (email,))
    assert modulo.reiniciar_periodo_si_aplica(_usuario(modulo, email))["usadas"] == 0
    assert _usuario(modulo, email)["usadas"] == 0


# ---------------------------------------------------------------------------------------------- IA-17 --
def test_IA17_el_registro_exige_aceptar_la_politica_y_la_guarda(cliente, modulo):
    base = {"nombre": "Persona Prueba", "clave": "clave-segura-123"}
    for extra in ({}, {"acepto_politica": False}, {"acepto_politica": "true"}, {"acepto_politica": 1}):
        email = f"politica_{time.time_ns()}@pruebas.local"
        r = cliente.post("/api/registro", json={"email": email, **base, **extra})
        assert r.status_code == 400, extra
        assert r.json()["detail"] == "Debes aceptar la política de tratamiento de datos para crear la cuenta."
        assert _usuario(modulo, email) is None
    email = f"politica_{time.time_ns()}@pruebas.local"
    antes = time.time()
    r = cliente.post("/api/registro", json={"email": email, **base, "acepto_politica": True})
    assert r.status_code == 200, r.text
    perfil = r.json()["perfil"]
    assert perfil["politica_version"] == modulo.POLITICA_VERSION == "2026-10-13" and perfil["politica_vigente"] == "2026-10-13"
    u = _usuario(modulo, email)
    assert u["acepto_politica_version"] == "2026-10-13" and antes - 1 <= u["acepto_politica_en"] <= time.time() + 1
    assert cliente.get("/api/estado", headers=auth(r.json()["token"])).json()["perfil"]["politica_version"] == "2026-10-13"


def test_IA17_la_cuenta_admin_de_las_variables_queda_exenta(cliente, modulo):
    admin = login_admin(cliente)
    perfil = cliente.get("/api/estado", headers=auth(admin)).json()["perfil"]
    assert perfil["politica_version"] is None and perfil["politica_vigente"] == modulo.POLITICA_VERSION
    assert cliente.get("/api/admin/usuarios", headers=auth(admin)).status_code == 200


def test_IA17_ruta_de_la_politica_de_datos(cliente, modulo, monkeypatch, tmp_path):
    monkeypatch.setattr(modulo, "RUTA_POLITICA_DATOS", str(tmp_path / "no-existe.html"))
    assert cliente.get("/politica-de-datos").status_code == 404
    pagina = tmp_path / "politica-datos.html"
    pagina.write_text("<!doctype html><title>Política</title><h1>Política de tratamiento de datos</h1>", encoding="utf-8")
    monkeypatch.setattr(modulo, "RUTA_POLITICA_DATOS", str(pagina))
    r = cliente.get("/politica-de-datos")
    assert r.status_code == 200 and "Política de tratamiento de datos" in r.text
    assert r.headers["content-type"].startswith("text/html") and r.headers.get("content-security-policy")
