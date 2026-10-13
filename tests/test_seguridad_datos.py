"""Regresión de la auditoría del 13 de octubre de 2026, área base de datos, respaldo y derechos del titular.

Cada prueba reproduce un hallazgo (BD-xx) y falla con el código anterior a la corrección. Las marcadas
``solo_postgres`` corren con PULLEX_PRUEBAS_PG_URL (docs/18-BASE-DE-DATOS.md); el resto, en los dos motores.
"""
import base64
import json
import os
import re
import secrets
import shutil
import stat
import subprocess
import threading
import time
import types
from contextlib import closing

import pytest

import academia
import datos
import telemetria_respuestas as telemetria
from conftest import ADMIN_CLAVE, ADMIN_EMAIL, EN_POSTGRES, PG_URL, RAIZ, auth, borrar_esquema_de_pruebas, login_admin

postgres = pytest.mark.solo_postgres


def _admin_pg():
    import psycopg
    return closing(psycopg.connect(PG_URL, autocommit=True, connect_timeout=5))


# ============================================================ BD-11: traducir() y la sintaxis que no entiende ==
@pytest.mark.parametrize("sql", [
    "SELECT d ?| ARRAY['a'] FROM t",
    "SELECT d ?& ARRAY['a'] FROM t",
    "SELECT d ? 'a' FROM t",
    "SELECT '{\"a\":1}'::jsonb ? ?",
    "SELECT $$¿qué?$$, ?",
    "SELECT $cuerpo$ hola ? $cuerpo$, ?",
    "SELECT E'it\\'s ?', ?",
    "SELECT e'x', ?",
])
def test_traducir_rechaza_lo_que_traduciria_mal(sql):
    with pytest.raises(ValueError):
        datos.traducir(sql)


def test_traducir_sigue_aceptando_lo_de_siempre():
    assert datos.traducir("SELECT ? || '%' x") == "SELECT %s || '%%' x"           # concatenación, no operador ?|
    assert datos.traducir("SELECT a && ARRAY[?] FROM t") == "SELECT a && ARRAY[%s] FROM t"
    assert datos.traducir("SELECT jsonb_exists(d, ?) FROM t WHERE a=?") == "SELECT jsonb_exists(d, %s) FROM t WHERE a=%s"
    assert datos.traducir("SELECT 'E''x', nombre, '$$' FROM t WHERE c LIKE ? ESCAPE '!'") == \
        "SELECT 'E''x', nombre, '$$' FROM t WHERE c LIKE %s ESCAPE '!'"
    assert datos.traducir("SELECT precio$total FROM t WHERE a=? ELSE 'b'") == "SELECT precio$total FROM t WHERE a=%s ELSE 'b'"


@postgres
def test_pg_sql_no_soportado_no_llega_al_servidor(modulo):
    errores = datos.estadisticas["errores_sql"]
    with closing(modulo.db()) as con:
        with pytest.raises(datos.SQLNoSoportado):
            con.execute("SELECT $$hola?$$, ?", (1,))
        with pytest.raises(datos.SQLNoSoportado):
            con.execute("SELECT '{\"a\":1}'::jsonb ? 'a'")
        assert con.execute("SELECT jsonb_exists('{\"a\":1}'::jsonb, ?) x", ("a",)).fetchone()["x"] == 1
    assert datos.estadisticas["errores_sql"] == errores


# ================================================================== BD-08: tope de conexiones del grupo ==
def test_el_grupo_tiene_tope_y_espera_con_limite(monkeypatch):
    monkeypatch.setenv("PULLEX_DB_MAX_CONEXIONES", "2")
    monkeypatch.setenv("PULLEX_DB_ESPERA_S", "0.2")
    grupo = datos._Grupo(types.SimpleNamespace())
    assert grupo.max_abiertas == 2
    grupo.reservar()
    grupo.reservar()
    t0 = time.monotonic()
    with pytest.raises(datos.ErrorConexion):            # ErrorBase: la app responde 503
        grupo.reservar()
    assert 0.15 <= time.monotonic() - t0 < 2
    grupo.liberar()
    grupo.reservar()                                    # al soltarse una, la siguiente entra
    assert grupo.en_uso() == 2


def test_el_tope_por_defecto_es_cinco_y_se_acota(monkeypatch):
    monkeypatch.delenv("PULLEX_DB_MAX_CONEXIONES", raising=False)
    assert datos.max_abiertas() == 5
    for valor, esperado in (("0", 1), ("1000", 100), ("abc", 5), ("12", 12)):
        monkeypatch.setenv("PULLEX_DB_MAX_CONEXIONES", valor)
        assert datos.max_abiertas() == esperado


@postgres
def test_pg_con_el_tope_lleno_la_app_responde_503_y_luego_se_recupera(cliente, modulo, monkeypatch):
    from conftest import nuevo_usuario
    _, _, token = nuevo_usuario(cliente)
    monkeypatch.setenv("PULLEX_DB_MAX_CONEXIONES", "2")
    monkeypatch.setenv("PULLEX_DB_ESPERA_S", "0.3")
    abiertas = []
    try:
        for _ in range(2):
            con = modulo.db()
            con.execute("SELECT 1").fetchone()
            abiertas.append(con)
        assert datos._grupo_actual.en_uso() == 2
        r = cliente.get("/api/estado", headers=auth(token))
        assert r.status_code == 503 and r.json()["codigo"] == "base_no_disponible"
        abiertas.pop().close()
        assert cliente.get("/api/estado", headers=auth(token)).status_code == 200
    finally:
        for con in abiertas:
            con.close()
        monkeypatch.undo()
        datos._config()


# ============================================================== BD-09: devolver() solo guarda conexiones IDLE ==
@postgres
@pytest.mark.errores_sql_esperados
def test_pg_una_conexion_en_transaccion_no_vuelve_al_grupo(modulo):
    import psycopg
    datos._config()
    grupo = datos._grupo_actual
    grupo.descartar_libres()
    for preparar in ("BEGIN", "BEGIN; SELECT 1/0"):
        cruda = grupo.tomar()
        try:
            cruda.execute(preparar)
        except psycopg.Error:
            pass                                          # queda «en transacción abortada»
        assert cruda.info.transaction_status != psycopg.pq.TransactionStatus.IDLE
        grupo.devolver(cruda)
        assert cruda.closed and grupo.libres() == 0
    cruda = grupo.tomar()                                 # una sana sí vuelve
    grupo.devolver(cruda)
    assert not cruda.closed and grupo.libres() == 1


# ========================================== BD-10: errores de PostgreSQL al revisar el esquema → 503, no 500 ==
@postgres
def test_pg_un_error_al_leer_la_version_del_esquema_es_error_base(monkeypatch):
    nombre = f"pullex_pruebas_bd10_{time.time_ns() % 10**9}"
    with _admin_pg() as admin:
        admin.execute(f'CREATE SCHEMA "{nombre}"')
        # esquema_version existe pero leerla falla con un error que no es «la tabla no existe»
        admin.execute(f'CREATE VIEW "{nombre}".esquema_version AS SELECT 1::bigint / (SELECT 0) AS version')
    monkeypatch.setenv("PULLEX_DB_ESQUEMA", nombre)
    try:
        with pytest.raises(datos.ErrorBase) as e:
            datos.asegurar_esquema()
        assert isinstance(e.value, datos.ErrorEsquema) and "22012" in str(e.value)
        assert datos._grupo_actual.en_uso() == 0
    finally:
        datos.reiniciar()
        borrar_esquema_de_pruebas(nombre)
        monkeypatch.undo()
        datos._config()


# ================================ BD-12: la app aplica supabase_seguridad.sql y avisa si no es dueña de las tablas ==
@pytest.fixture
def roles_de_supabase():
    """Crea anon, authenticated y service_role si no existen (y los borra al final). Salta si no se puede."""
    import psycopg
    creados = []
    with _admin_pg() as admin:
        try:
            for rol in ("anon", "authenticated", "service_role"):
                if not admin.execute("SELECT 1 FROM pg_roles WHERE rolname=%s", (rol,)).fetchone():
                    admin.execute(f"CREATE ROLE {rol} NOLOGIN")
                    creados.append(rol)
        except psycopg.errors.InsufficientPrivilege:
            pytest.skip("el usuario de pruebas no puede crear roles")
    yield ("anon", "authenticated", "service_role")
    with _admin_pg() as admin:
        for rol in creados:
            admin.execute(f"DROP OWNED BY {rol}")
            admin.execute(f"DROP ROLE {rol}")


@postgres
def test_pg_asegurar_esquema_aplica_la_seguridad_de_supabase(monkeypatch, roles_de_supabase):
    nombre = f"pullex_pruebas_bd12_{time.time_ns() % 10**9}"
    monkeypatch.setenv("PULLEX_DB_ESQUEMA", nombre)
    try:
        assert datos.asegurar_esquema()["aplicado"] is True
        with _admin_pg() as admin:
            # alguien expone el esquema por error y deja privilegios por defecto para lo que se cree después
            for rol in roles_de_supabase:
                admin.execute(f'GRANT USAGE ON SCHEMA "{nombre}" TO {rol}')
                admin.execute(f'GRANT ALL ON ALL TABLES IN SCHEMA "{nombre}" TO {rol}')
                admin.execute(f'ALTER DEFAULT PRIVILEGES IN SCHEMA "{nombre}" GRANT ALL ON TABLES TO {rol}')
            admin.execute(f'DELETE FROM "{nombre}".esquema_version WHERE version = %s', (datos.version_del_archivo(),))
        assert datos.asegurar_esquema()["aplicado"] is True     # la versión «vieja» hace que se vuelva a aplicar
        with _admin_pg() as admin:
            admin.execute(f'CREATE TABLE "{nombre}".tabla_futura (a bigint)')
            for rol in roles_de_supabase:
                assert admin.execute("SELECT has_schema_privilege(%s, %s, 'USAGE')", (rol, nombre)).fetchone()[0] is False
                for tabla in ("usuarios", "mensajes", "apariencia_imagenes", "tabla_futura"):
                    assert admin.execute("SELECT has_table_privilege(%s, %s, 'SELECT')",
                                         (rol, f'"{nombre}".{tabla}')).fetchone()[0] is False, (rol, tabla)
        assert datos.estadisticas["seguridad_fallida"] == 0
    finally:
        datos.reiniciar()
        borrar_esquema_de_pruebas(nombre)
        monkeypatch.undo()
        datos._config()


@postgres
def test_pg_con_un_usuario_que_no_es_dueno_se_ven_cero_filas_y_la_app_lo_avisa(modulo):
    """Reproducción de la auditoría (rls_rol.py): un rol con permiso pero que no es dueño ve 0 filas sin error."""
    import psycopg
    nombre = f"pullex_pruebas_dueno_{time.time_ns() % 10**9}"
    rol = f"pullex_pruebas_rol_{secrets.token_hex(3)}"
    with _admin_pg() as admin:
        try:
            admin.execute(f"CREATE ROLE {rol} NOLOGIN")
        except psycopg.errors.InsufficientPrivilege:
            pytest.skip("el usuario de pruebas no puede crear roles")
        try:
            admin.execute("BEGIN")
            admin.execute(f'SET LOCAL search_path TO "{nombre}"')
            admin.execute(open(datos.RUTA_ESQUEMA, encoding="utf-8").read())
            admin.execute("COMMIT")
            admin.execute(f'INSERT INTO "{nombre}".usuarios(email) VALUES (%s)', ("x@y.z",))
            admin.execute(f'GRANT USAGE ON SCHEMA "{nombre}" TO {rol}')
            admin.execute(f'GRANT SELECT ON ALL TABLES IN SCHEMA "{nombre}" TO {rol}')
            admin.execute("BEGIN")
            admin.execute(f'SET LOCAL search_path TO "{nombre}"')
            assert datos.aviso_de_dueno(admin) is None                              # el dueño: todo bien
            admin.execute(f"SET LOCAL ROLE {rol}")
            assert admin.execute("SELECT count(*) FROM usuarios").fetchone()[0] == 0   # 0 filas y ningún error
            assert "no es el dueño" in datos.aviso_de_dueno(admin)
            admin.execute("ROLLBACK")
        finally:
            admin.execute("ROLLBACK")
            admin.execute(f'DROP SCHEMA IF EXISTS "{nombre}" CASCADE')
            admin.execute(f"DROP OWNED BY {rol}")
            admin.execute(f"DROP ROLE {rol}")


# ========================================================== BD-14: verificación del certificado del servidor ==
def test_con_certificado_raiz_se_verifica_el_servidor(monkeypatch, tmp_path):
    pytest.importorskip("psycopg")
    url = "postgres://u:c@db.proyecto.ejemplo.com:5432/postgres?sslmode=require"
    monkeypatch.delenv("PULLEX_DB_SSLROOTCERT", raising=False)
    assert datos.limpiar_url(url)["sslmode"] == "require"
    raiz = tmp_path / "raiz.crt"
    raiz.write_text("-----BEGIN CERTIFICATE-----\n")
    monkeypatch.setenv("PULLEX_DB_SSLROOTCERT", str(raiz))
    p = datos.limpiar_url(url)
    assert p["sslmode"] == "verify-full" and p["sslrootcert"] == str(raiz)
    assert "sslrootcert" not in datos.limpiar_url("postgresql://u:c@127.0.0.1:5432/x")      # local: no aplica
    monkeypatch.setenv("PULLEX_DB_SSLROOTCERT", str(tmp_path / "no-existe.crt"))
    with pytest.raises(datos.ErrorConfiguracion) as e:
        datos.limpiar_url(url)
    assert "c@" not in str(e.value)


# =========================================================================== BD-15: statement_timeout ==
def test_cada_transaccion_lleva_tope_de_duracion(monkeypatch):
    monkeypatch.delenv("PULLEX_DB_TIMEOUT_MS", raising=False)
    cfg = datos._Config((), {}, "pullex", "X", datos.timeout_sentencia_ms())
    assert cfg.inicio_tx == 'BEGIN; SET LOCAL search_path TO "pullex"; SET LOCAL statement_timeout = 15000'
    monkeypatch.setenv("PULLEX_DB_TIMEOUT_MS", "2500; DROP TABLE usuarios")
    assert datos.timeout_sentencia_ms() == 15000                     # solo números
    monkeypatch.setenv("PULLEX_DB_TIMEOUT_MS", "0")
    assert datos.timeout_sentencia_ms() == 0


@postgres
@pytest.mark.errores_sql_esperados
def test_pg_una_consulta_que_tarda_demasiado_se_corta(modulo, monkeypatch):
    import psycopg
    with closing(modulo.db()) as con:
        assert con.execute("SHOW statement_timeout").fetchone()[0] == "15s"
    monkeypatch.setenv("PULLEX_DB_TIMEOUT_MS", "300")
    try:
        with closing(modulo.db()) as con:
            with pytest.raises(psycopg.errors.QueryCanceled):
                con.execute("SELECT pg_sleep(2)").fetchone()
    finally:
        monkeypatch.undo()
        datos._config()
    with _admin_pg() as admin:                                       # no queda puesto en la sesión
        assert admin.execute("SHOW statement_timeout").fetchone()[0] == "0"


# ========================================================= BD-06: INSERT … ON CONFLICT en vez de SELECT+INSERT ==
@postgres
def test_pg_dos_evaluaciones_a_la_vez_no_chocan_en_conocimiento(modulo):
    email, cid = f"carrera_{secrets.token_hex(4)}@pruebas.local", "concepto:carrera"
    a, b = modulo.db(), modulo.db()
    errores = []
    try:
        academia._actualizar(a, email, cid, "Concepto", "Civil", "fallo", time.time())     # A inserta, sin confirmar

        def en_b():
            try:
                academia._actualizar(b, email, cid, "Concepto", "Civil", "acierto", time.time())
                b.commit()
            except Exception as e:      # noqa: BLE001
                errores.append(e)
        h = threading.Thread(target=en_b)
        h.start()
        time.sleep(0.8)                  # B espera el candado de la fila que insertó A
        a.commit()
        h.join(10)
    finally:
        a.close()
        b.close()
    assert not errores, errores
    with closing(modulo.db()) as con:
        f = con.execute("SELECT aciertos, fallos FROM conocimiento WHERE usuario=? AND concepto_id=?", (email, cid)).fetchone()
        assert (f["aciertos"], f["fallos"]) == (1, 1)
        con.execute("DELETE FROM conocimiento WHERE usuario=?", (email,))
        con.commit()


class _ConfirmaCuandoSeLeDiga:
    """Envoltura de conexión cuyo commit() espera una señal: deja una transacción abierta a mitad de valorar()."""

    def __init__(self, con, senal):
        self._con, self._senal = con, senal

    def execute(self, *a):
        return self._con.execute(*a)

    def commit(self):
        self._senal.wait(10)
        self._con.commit()


@postgres
def test_pg_dos_valoraciones_a_la_vez_de_la_misma_respuesta_no_chocan(modulo):
    mid = 9_000_000_000 + secrets.randbelow(10**6)
    senal, errores = threading.Event(), []
    a, b = modulo.db(), modulo.db()
    try:
        ha = threading.Thread(target=lambda: telemetria.valorar(_ConfirmaCuandoSeLeDiga(a, senal), mid, "anon-a", "arriba"))
        ha.start()
        time.sleep(0.4)                  # A ya insertó y espera para confirmar

        def en_b():
            try:
                telemetria.valorar(b, mid, "anon-b", "abajo", ["incompleta"])
            except Exception as e:      # noqa: BLE001
                errores.append(e)
        hb = threading.Thread(target=en_b)
        hb.start()
        time.sleep(0.6)
        senal.set()
        ha.join(10)
        hb.join(10)
    finally:
        a.close()
        b.close()
    assert not errores, errores
    with closing(modulo.db()) as con:
        filas = con.execute("SELECT valoracion, motivos FROM calidad_respuestas WHERE mensaje_id=?", (mid,)).fetchall()
        assert [(f["valoracion"], json.loads(f["motivos"])) for f in filas] == [("abajo", ["incompleta"])]
        con.execute("DELETE FROM calidad_respuestas WHERE mensaje_id=?", (mid,))
        con.commit()


def test_valorar_actualiza_sin_borrar_lo_demas_de_la_fila(modulo):
    mid = 8_000_000_000 + secrets.randbelow(10**6)
    with closing(modulo.db()) as con:
        telemetria.registrar(con, mid, "anon", {"intencion": "consulta", "caracteres": 120})
        telemetria.valorar(con, mid, "anon", "abajo", ["muy_larga", "inventado"])
        telemetria.valorar(con, mid, "anon", "arriba")
        f = con.execute("SELECT intencion, caracteres, valoracion, motivos FROM calidad_respuestas WHERE mensaje_id=?",
                        (mid,)).fetchone()
        assert (f["intencion"], f["caracteres"], f["valoracion"], json.loads(f["motivos"])) == ("consulta", 120, "arriba", [])
        con.execute("DELETE FROM calidad_respuestas WHERE mensaje_id=?", (mid,))
        con.commit()


# ===================================================================== BD-18: ids fuera de rango → 404 ==
def _rutas_con_id(app):
    """Todas las rutas con un parámetro de ruta entero, sacadas del esquema OpenAPI de la app (incluye las de los
    routers montados: taller, biblioteca…). Una ruta nueva con {id} queda cubierta sola."""
    for ruta, metodos in app.openapi()["paths"].items():
        for metodo, op in metodos.items():
            enteros = [p["name"] for p in op.get("parameters", [])
                       if p.get("in") == "path" and p.get("schema", {}).get("type") == "integer"]
            if enteros:
                yield metodo.upper(), ruta, enteros


@pytest.mark.parametrize("valor", ["99999999999999999999999", str(2 ** 63), "0", "-3"])
def test_ids_fuera_de_rango_responden_404_en_todas_las_rutas(cliente, modulo, valor):
    token = login_admin(cliente)
    rutas = list(_rutas_con_id(modulo.app))
    assert {r for _, r, _ in rutas} >= {"/api/conversaciones/{cid}/mensajes", "/api/documentos/{did}", "/api/modular/caso/{caso_id}",
                                        "/api/taller/escenario/{eid}", "/api/coordinador/ejecuciones/{eid}"}, rutas
    for metodo, ruta, nombres in rutas:
        url = ruta
        for nombre in nombres:
            url = url.replace("{" + nombre + "}", valor)
        r = cliente.request(metodo, url, headers=auth(token), json={"titulo": "x", "texto": "x"})
        assert r.status_code == 404, (metodo, url, r.status_code, r.text[:200])
    for url in ("/api/modular/solucion?caso_id=", "/api/modular/conceptos?caso_id="):
        assert cliente.get(url + valor, headers=auth(token)).status_code == 404
    r = cliente.post("/api/chat", headers=auth(token), json={"conversacion": int(valor), "mensaje": "hola", "web": False})
    assert r.status_code == 404


def test_id_valido():
    assert datos.id_valido("7") == 7 and datos.id_valido(2 ** 63 - 1) == 2 ** 63 - 1
    assert datos.id_valido(2 ** 63) is None and datos.id_valido(0) is None and datos.id_valido("-1") is None
    with pytest.raises(ValueError):
        datos.id_valido("abc")


# ================================================= BD-13: índice de modular_intentos(caso_id), sin FK aún ==
def test_indice_de_intentos_por_caso_y_sin_claves_foraneas_todavia(modulo):
    assert datos.indices_del_archivo()["ix_mintentos_caso"] == "modular_intentos"
    texto = re.sub(r"--[^\n]*", "", datos.leer_esquema())
    assert "REFERENCES" not in texto.upper() and "FOREIGN KEY" not in texto.upper()
