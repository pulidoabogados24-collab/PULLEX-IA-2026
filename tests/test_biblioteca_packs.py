"""Seguridad y contrato JSON de Biblioteca privada; sin Google Drive real."""
import pytest
from fastapi import FastAPI, HTTPException, Request
from fastapi.testclient import TestClient

import biblioteca_packs


def _app(auth):
    app = FastAPI()
    app.include_router(biblioteca_packs.crear_router(admin_actual=auth))
    return TestClient(app)


def _usuario_admin(_request):
    return {"email": "admin@pruebas.local", "activo": 1, "es_admin": True}


def _sin_sesion(_request):
    raise HTTPException(401, "No autenticado")


def test_protege_las_rutas_antes_de_consultar_db(monkeypatch):
    def prohibido(*_args):
        pytest.fail("La DB no se debe consultar sin sesión")
    monkeypatch.setattr(biblioteca_packs, "_leer", prohibido)
    cliente = _app(_sin_sesion)
    for path in ("/api/admin/biblioteca/packs/resumen",
                 "/api/admin/biblioteca/packs/buscar",
                 "/api/admin/biblioteca/packs/documento/1"):
        assert cliente.get(path).status_code == 401


def test_rechaza_administrador_inactivo(monkeypatch):
    monkeypatch.setattr(biblioteca_packs, "_leer", lambda *_: pytest.fail("DB consultada"))
    cliente = _app(lambda _: {"email": "x@y.z", "activo": 0, "es_admin": True})
    assert cliente.get("/api/admin/biblioteca/packs/buscar").status_code == 403


def test_busqueda_no_devuelve_enlace_ni_identificador_drive(monkeypatch):
    def falso(sql, params=()):
        if "count(*)" in sql.lower():
            return [{"total": 1}]
        return [{"id": 17, "coleccion": "PACK JURIDICO 1", "ruta": "Modelos",
                 "nombre": "Tutela ilustrativa", "mime_type": "application/pdf",
                 "estado_procesamiento": "ENCONTRADO", "vigencia": "PENDIENTE"}]
    monkeypatch.setattr(biblioteca_packs, "_leer", falso)
    respuesta = _app(_usuario_admin).get("/api/admin/biblioteca/packs/buscar?q=Tutela")
    assert respuesta.status_code == 200
    datos = respuesta.json()
    assert datos["total"] == 1
    assert "drive" not in str(datos).lower()
    assert "http" not in str(datos).lower()
    assert "url_origen" not in str(datos)


def test_validacion_de_coleccion_y_paginacion(monkeypatch):
    monkeypatch.setattr(biblioteca_packs, "_leer", lambda *_: pytest.fail("DB consultada"))
    c = _app(_usuario_admin)
    assert c.get("/api/admin/biblioteca/packs/buscar?coleccion=otro").status_code == 400
    assert c.get("/api/admin/biblioteca/packs/buscar?por_pagina=200").status_code == 400


def test_un_documento_sin_indexar_no_tiene_texto(monkeypatch):
    def falso(sql, params=()):
        if "FROM pullex.biblioteca_documentos" in sql:
            return [{"id": 7, "coleccion": "PACK JURIDICO 2", "nombre": "Modelo",
                     "estado_procesamiento": "ENCONTRADO", "vigencia": "PENDIENTE"}]
        pytest.fail("No debe intentar obtener fragmentos del documento sin indexar")
    monkeypatch.setattr(biblioteca_packs, "_leer", falso)
    resp = _app(_usuario_admin).get("/api/admin/biblioteca/packs/documento/7")
    assert resp.status_code == 200
    assert resp.json()["fragmentos"] == []


def test_no_configurado_devuelve_503(monkeypatch):
    monkeypatch.delenv("PULLEX_BIBLIOTECA_DATABASE_URL", raising=False)
    with pytest.raises(HTTPException) as exc:
        biblioteca_packs._leer("SELECT 1")
    assert exc.value.status_code == 503
