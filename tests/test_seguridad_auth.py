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
