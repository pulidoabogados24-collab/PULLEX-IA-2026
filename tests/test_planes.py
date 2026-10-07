"""Acceso por plan: Básico = Consultar; Pro = + Academia (Laboratorio de casos, Mi mapa, Taller);
Premium = + Automatizador (Documentos, Flujos, Asistente); Prueba = todo (limitado por sus 10
consultas); administrador = todo."""
import re

import pytest

from conftest import auth, login_admin, nuevo_usuario


def _con_plan(cliente, plan):
    email, _, t = nuevo_usuario(cliente)
    if plan != "prueba":
        r = cliente.post("/api/admin/actualizar", headers=auth(login_admin(cliente)),
                         json={"email": email, "plan": plan, "activo": True})
        assert r.status_code == 200, r.text
    return email, t


ACADEMIA = [("GET", "/api/modular/opciones", None), ("GET", "/api/modular/progreso", None),
            ("GET", "/api/academia/mapa", None), ("GET", "/api/academia/resumen", None),
            ("GET", "/api/academia/errores", None)]
AUTOMATIZADOR = [("GET", "/api/documentos/catalogo", None), ("GET", "/api/documentos/mis", None),
                 ("GET", "/api/flujos", None),
                 ("POST", "/api/asistente/tarea", {"tarea": "Prepara una tutela contra mi EPS por un medicamento."}),
                 # integración PUL-010..013: biblioteca de modelos, perfiles y coordinador
                 ("GET", "/api/biblioteca/resumen", None), ("GET", "/api/biblioteca/buscar?q=tutela", None),
                 ("GET", "/api/perfiles?por_pagina=5", None), ("GET", "/api/coordinador/ejecuciones", None)]
LIBRES = [("GET", "/api/procedimientos", None), ("GET", "/api/reglas", None)]  # Herramientas: sin restricción de plan
ESPERADO = {  # plan → (academia, automatizador)
    "prueba": (200, 200), "basico": (403, 403), "pro": (200, 403), "premium": (200, 200)}


def _pedir(cliente, t, metodo, ruta, cuerpo):
    return cliente.request(metodo, ruta, headers=auth(t), json=cuerpo)


@pytest.mark.parametrize("plan", ["prueba", "basico", "pro", "premium"])
def test_matriz_plan_por_ruta(cliente, plan):
    _, t = _con_plan(cliente, plan)
    esperado_ac, esperado_au = ESPERADO[plan]
    for metodo, ruta, cuerpo in ACADEMIA:
        r = _pedir(cliente, t, metodo, ruta, cuerpo)
        assert r.status_code == esperado_ac, (plan, ruta, r.text)
    for metodo, ruta, cuerpo in AUTOMATIZADOR:
        r = _pedir(cliente, t, metodo, ruta, cuerpo)
        assert r.status_code == esperado_au, (plan, ruta, r.text)
    # Consultar (chat) está en todos los planes
    cid = cliente.post("/api/conversaciones", headers=auth(t)).json()["id"]
    assert cliente.post("/api/chat", headers=auth(t), json={"conversacion": cid, "mensaje": "hola"}).status_code == 200


def test_admin_tiene_todo(cliente):
    t = login_admin(cliente)
    for metodo, ruta, cuerpo in ACADEMIA + AUTOMATIZADOR[:3]:
        assert _pedir(cliente, t, metodo, ruta, cuerpo).status_code == 200, ruta
    e = cliente.get("/api/estado", headers=auth(t)).json()
    assert e["funciones"] == ["chat", "academia", "automatizador"]


def test_respuesta_403_con_codigo_y_plan_requerido(cliente):
    _, t = _con_plan(cliente, "basico")
    r = cliente.get("/api/modular/opciones", headers=auth(t))
    assert r.status_code == 403
    d = r.json()
    assert set(d) == {"detail", "codigo", "funcion", "plan_requerido"}
    assert d["codigo"] == "plan_insuficiente" and d["funcion"] == "academia" and d["plan_requerido"] == "pro"
    assert "Pro" in d["detail"]
    assert "default-src 'self'" in r.headers["content-security-policy"]   # cabeceras de seguridad intactas
    assert r.headers["cache-control"] == "no-store"
    d = cliente.get("/api/flujos", headers=auth(t)).json()
    assert d["funcion"] == "automatizador" and d["plan_requerido"] == "premium"
    _, t = _con_plan(cliente, "pro")
    d = cliente.get("/api/documentos/catalogo", headers=auth(t)).json()
    assert d["codigo"] == "plan_insuficiente" and d["plan_requerido"] == "premium"


def _rutas_protegidas(modulo):
    salida = []
    for r in modulo.app.routes:
        ruta = getattr(r, "path", "")
        funcion = modulo.funcion_de_ruta(ruta)
        if funcion:
            concreta = re.sub(r"\{[^}]+\}", "1", ruta)
            for metodo in sorted(getattr(r, "methods", None) or ["GET"]):
                if metodo != "HEAD":
                    salida.append((metodo, concreta, funcion))
    return salida


def test_todas_las_rutas_protegidas_estan_cubiertas(cliente, modulo):
    """Toda ruta bajo /api/modular, /api/academia, /api/taller, /api/documentos, /api/flujos y /api/asistente
    responde 403 a un plan que no la incluye, sin llegar a la lógica de la ruta (ni gastar consultas)."""
    rutas = _rutas_protegidas(modulo)
    assert len(rutas) >= 20 and {f for _, _, f in rutas} == {"academia", "automatizador"}
    _, basico = _con_plan(cliente, "basico")
    _, pro = _con_plan(cliente, "pro")
    for metodo, ruta, funcion in rutas:
        r = cliente.request(metodo, ruta, headers=auth(basico), json={})
        assert r.status_code == 403 and r.json()["codigo"] == "plan_insuficiente", (metodo, ruta, r.text)
        if funcion == "automatizador":
            assert cliente.request(metodo, ruta, headers=auth(pro), json={}).status_code == 403, ruta
    e = cliente.get("/api/estado", headers=auth(basico)).json()
    assert e["perfil"]["usadas"] == 0


def test_prefijo_cubre_rutas_futuras_del_taller(cliente):
    _, basico = _con_plan(cliente, "basico")
    _, pro = _con_plan(cliente, "pro")
    r = cliente.post("/api/taller/escritos", headers=auth(basico), json={})
    assert r.status_code == 403 and r.json()["funcion"] == "academia"
    assert cliente.post("/api/taller/escritos", headers=auth(pro), json={}).status_code == 404
    # el prefijo no atrapa rutas parecidas pero distintas
    assert cliente.get("/api/modularx", headers=auth(basico)).status_code == 404


def test_sin_sesion_sigue_siendo_401(cliente):
    assert cliente.get("/api/modular/opciones").status_code == 401
    assert cliente.get("/api/documentos/catalogo", headers={"Authorization": "Bearer basura"}).status_code == 401


def test_estado_informa_funciones_y_planes(cliente):
    _, t = _con_plan(cliente, "pro")
    e = cliente.get("/api/estado", headers=auth(t)).json()
    assert e["funciones"] == ["chat", "academia"] and e["perfil"]["funciones"] == ["chat", "academia"]
    assert e["plan_funciones"] == {"prueba": ["chat", "academia", "automatizador"], "basico": ["chat"],
                                   "pro": ["chat", "academia"], "premium": ["chat", "academia", "automatizador"]}
    assert e["plan_requerido"] == {"academia": "pro", "automatizador": "premium"}
    assert e["planes"]["pro"]["precio"] == 45000 and e["contacto_planes"]["correo"]


def test_cambiar_el_plan_desde_admin_cambia_el_acceso(cliente):
    email, t = _con_plan(cliente, "basico")
    assert cliente.get("/api/academia/mapa", headers=auth(t)).status_code == 403
    adm = auth(login_admin(cliente))
    cliente.post("/api/admin/actualizar", headers=adm, json={"email": email, "plan": "pro"})
    assert cliente.get("/api/academia/mapa", headers=auth(t)).status_code == 200
    assert cliente.get("/api/documentos/mis", headers=auth(t)).status_code == 403
    cliente.post("/api/admin/actualizar", headers=adm, json={"email": email, "plan": "premium"})
    assert cliente.get("/api/documentos/mis", headers=auth(t)).status_code == 200
    cliente.post("/api/admin/actualizar", headers=adm, json={"email": email, "plan": "basico"})
    assert cliente.get("/api/documentos/mis", headers=auth(t)).status_code == 403
    assert cliente.get("/api/estado", headers=auth(t)).json()["funciones"] == ["chat"]


def test_plan_de_prueba_configurable_en_una_constante(cliente, modulo, monkeypatch):
    monkeypatch.setitem(modulo.PLAN_FUNCIONES, "prueba", ("chat",))
    _, _, t = nuevo_usuario(cliente)
    r = cliente.get("/api/modular/opciones", headers=auth(t))
    assert r.status_code == 403 and r.json()["plan_requerido"] == "pro"


@pytest.mark.parametrize("plan", ["basico", "pro", "premium"])
def test_herramientas_no_se_restringen_por_plan(cliente, plan):
    _, t = _con_plan(cliente, plan)
    for metodo, ruta, cuerpo in LIBRES:
        r = _pedir(cliente, t, metodo, ruta, cuerpo)
        assert r.status_code == 200, (plan, ruta, r.text)
