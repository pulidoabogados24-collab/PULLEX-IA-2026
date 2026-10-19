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


def test_router_integrado_aplica_roles_inactividad_y_revocacion(cliente, modulo, monkeypatch):
    """Usa autenticación real de la app, no el callback simulado de las pruebas de contrato."""
    from contextlib import closing
    from conftest import auth, nuevo_usuario

    consultas = []
    monkeypatch.setattr(biblioteca_packs, "_leer", lambda *args: consultas.append(args) or [])
    email, clave, token = nuevo_usuario(cliente)
    rutas = ("/api/admin/biblioteca/packs/resumen", "/api/admin/biblioteca/packs/buscar",
             "/api/admin/biblioteca/packs/documento/999999")
    for ruta in rutas:
        assert cliente.get(ruta).status_code == 401
        assert cliente.get(ruta, headers=auth(token)).status_code == 403
    assert consultas == []

    with closing(modulo.db()) as con:
        con.execute("UPDATE usuarios SET es_admin=1 WHERE email=?", (email,))
        con.commit()
    assert cliente.get(rutas[0], headers=auth(token)).status_code == 200
    consultas.clear()
    with closing(modulo.db()) as con:
        con.execute("UPDATE usuarios SET activo=0 WHERE email=?", (email,))
        con.commit()
    for ruta in rutas:
        assert cliente.get(ruta, headers=auth(token)).status_code == 403
    assert consultas == []
    with closing(modulo.db()) as con:
        con.execute("UPDATE usuarios SET activo=1,sesion_version=sesion_version+1 WHERE email=?", (email,))
        con.commit()
    for ruta in rutas:
        assert cliente.get(ruta, headers=auth(token)).status_code == 401
    assert consultas == []
    renovada = cliente.post("/api/login", json={"email": email, "clave": clave})
    assert renovada.status_code == 200
    assert cliente.get(rutas[0], headers=auth(renovada.json()["token"])).status_code == 200


@pytest.mark.solo_postgres
def test_catalogo_postgres_real_con_lector_sin_escritura(monkeypatch):
    """Datos sintéticos en esquema temporal; no usa el catálogo operativo ni Google Drive."""
    import secrets
    from contextlib import closing
    import psycopg
    from psycopg.conninfo import make_conninfo
    from conftest import PG_URL

    sufijo = secrets.token_hex(5)
    esquema = "pullex_pruebas_packs_" + sufijo
    rol = "pullex_pruebas_lector_" + sufijo
    with closing(psycopg.connect(PG_URL, autocommit=True)) as admin:
        # El CI desechable puede crear roles. Sin ese permiso, la prueba debe fallar para no
        # presentar la ausencia de comprobación de ACL como una validación satisfactoria.
        admin.execute(f'CREATE ROLE "{rol}" NOLOGIN NOSUPERUSER NOBYPASSRLS NOINHERIT')
        try:
            admin.execute(f'CREATE SCHEMA "{esquema}"')
            admin.execute(f'''CREATE TABLE "{esquema}".biblioteca_documentos (
                id bigint PRIMARY KEY, coleccion text, ruta text, nombre text, mime_type text,
                estado_procesamiento text, vigencia text, drive_id text, url_origen text)''')
            admin.execute(f'''CREATE TABLE "{esquema}".biblioteca_fragmentos (
                documento_id bigint, ordinal integer, ubicacion text, contenido text,
                texto_busqueda tsvector GENERATED ALWAYS AS (to_tsvector('spanish', contenido)) STORED)''')
            for ident, coleccion, estado in ((1, "PACK JURIDICO 1", "INDEXADO"),
                                             (2, "PACK JURIDICO 2", "ENCONTRADO"),
                                             (3, "OTRA COLECCION", "INDEXADO")):
                admin.execute(f'''INSERT INTO "{esquema}".biblioteca_documentos
                    VALUES (%s,%s,'Modelos','Ejemplo sintetico','text/plain',%s,'PENDIENTE',
                            'ID-DRIVE-PRIVADO','https://drive.google.com/privado')''', (ident, coleccion, estado))
                admin.execute(f'''INSERT INTO "{esquema}".biblioteca_fragmentos
                    (documento_id,ordinal,ubicacion,contenido) VALUES (%s,0,'texto','restitucion sintetica')''', (ident,))
            admin.execute(f'GRANT USAGE ON SCHEMA "{esquema}" TO "{rol}"')
            for tabla in ("biblioteca_documentos", "biblioteca_fragmentos"):
                admin.execute(f'ALTER TABLE "{esquema}".{tabla} ENABLE ROW LEVEL SECURITY')
                admin.execute(f'GRANT SELECT ON "{esquema}".{tabla} TO "{rol}"')
                admin.execute(f'CREATE POLICY lector ON "{esquema}".{tabla} FOR SELECT TO "{rol}" USING (true)')
            privada = make_conninfo(PG_URL, options=f"-c role={rol}")
            monkeypatch.setenv("PULLEX_BIBLIOTECA_DATABASE_URL", privada)
            original = biblioteca_packs._leer
            # Solo cambia el esquema del SQL para aislar esta prueba. _leer conserva psycopg,
            # parámetros, transacción READ ONLY y timeout reales.
            monkeypatch.setattr(biblioteca_packs, "_leer",
                                lambda sql, params=(): original(sql.replace("pullex.", f'"{esquema}".'), params))
            c = _app(_usuario_admin)
            assert c.get("/api/admin/biblioteca/packs/resumen").json()["total"] == 2
            r = c.get("/api/admin/biblioteca/packs/buscar", params={"q": "restitucion"})
            # Los fragmentos residuales de un documento ENCONTRADO no habilitan búsqueda por texto.
            assert r.status_code == 200 and r.json()["total"] == 1
            assert "ID-DRIVE-PRIVADO" not in r.text and "drive.google.com" not in r.text
            assert c.get("/api/admin/biblioteca/packs/buscar", params={"q": "' OR 1=1 --"}).json()["total"] == 0
            assert c.get("/api/admin/biblioteca/packs/documento/1").json()["fragmentos"][0]["contenido"] == "restitucion sintetica"
            assert c.get("/api/admin/biblioteca/packs/documento/2").json()["fragmentos"] == []
            assert c.get("/api/admin/biblioteca/packs/documento/3").status_code == 404
            with pytest.raises(HTTPException) as exc:
                original(f'DELETE FROM "{esquema}".biblioteca_documentos')
            assert exc.value.status_code == 503
            # ACL efectiva, incluso fuera de la transacción READ ONLY de la app.
            with closing(psycopg.connect(privada, autocommit=True)) as lector:
                with pytest.raises(psycopg.errors.InsufficientPrivilege):
                    lector.execute(f'DELETE FROM "{esquema}".biblioteca_documentos')
            assert admin.execute(f'SELECT count(*) FROM "{esquema}".biblioteca_documentos').fetchone()[0] == 3
        finally:
            admin.execute(f'DROP SCHEMA IF EXISTS "{esquema}" CASCADE')
            admin.execute(f'DROP OWNED BY "{rol}"')
            admin.execute(f'DROP ROLE "{rol}"')
