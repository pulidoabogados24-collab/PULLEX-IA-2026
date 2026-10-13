"""Capa de datos (datos.py): la base principal en SQLite o en PostgreSQL (docs/18-BASE-DE-DATOS.md).

Tres grupos:
* lo que no necesita un servidor (traducción de SQL, limpieza de la URL, validación del esquema, estado);
* lo que necesita PostgreSQL (marca ``solo_postgres``: corre con PULLEX_PRUEBAS_PG_URL) — la envoltura de conexión
  contra un servidor de verdad, reconexión, transacciones y el reinicio que perdía las cuentas;
* cómo responde la app cuando la base no contesta.
"""
import importlib.util
import json
import logging
import os
import subprocess
import sys
import threading
import time
from contextlib import closing

import pytest

import datos
from conftest import ADMIN_CLAVE, ADMIN_EMAIL, EN_POSTGRES, PG_URL, RAIZ, auth, borrar_esquema_de_pruebas, nuevo_usuario

postgres = pytest.mark.solo_postgres
URL_REMOTA = "postgres://usuario.proyecto:Cl4ve-Secreta@aws-0-us-east-1.pooler.ejemplo.com:6543/postgres"
URL_SIN_SERVIDOR = "postgresql://nadie:Cl4ve-Secreta@127.0.0.1:1/postgres?connect_timeout=2"


@pytest.fixture
def sin_postgres(monkeypatch):
    """Deja la capa de datos en modo SQLite durante la prueba (aunque la sesión corra en PostgreSQL)."""
    for v in datos.VARIABLES_URL:
        monkeypatch.setenv(v, "")
    yield


def _admin_pg():
    """Conexión directa al servidor de pruebas (por fuera de la envoltura), para observarlo o matar conexiones."""
    import psycopg
    return closing(psycopg.connect(PG_URL, autocommit=True, connect_timeout=5))


# ------------------------------------------------------------------------- traducción de SQL --
def test_traduce_los_marcadores_de_sqlite_a_los_de_psycopg():
    assert datos.traducir("SELECT * FROM usuarios WHERE email=? AND activo=?") == \
        "SELECT * FROM usuarios WHERE email=%s AND activo=%s"
    assert datos.traducir("INSERT INTO t(a,b) VALUES(?,?)") == "INSERT INTO t(a,b) VALUES(%s,%s)"


def test_no_toca_los_interrogantes_dentro_de_literales_ni_comentarios():
    assert datos.traducir("SELECT '¿qué?' q, x FROM t WHERE y=?") == "SELECT '¿qué?' q, x FROM t WHERE y=%s"
    assert datos.traducir("""SELECT 'it''s ? ok', "col?" FROM t WHERE a=?""") == \
        """SELECT 'it''s ? ok', "col?" FROM t WHERE a=%s"""
    assert datos.traducir("SELECT a -- ¿por qué?\nFROM t WHERE b=? /* ¿y esto? */ AND c=?") == \
        "SELECT a -- ¿por qué?\nFROM t WHERE b=%s /* ¿y esto? */ AND c=%s"


def test_dobla_los_porcentajes_literales_esten_donde_esten():
    # psycopg interpreta «%» en toda la sentencia: dentro de un literal también hay que doblarlo
    assert datos.traducir("SELECT * FROM t WHERE a LIKE '%x%' AND b=?") == "SELECT * FROM t WHERE a LIKE '%%x%%' AND b=%s"
    assert datos.traducir("SELECT 10 % 3, '100%', ?") == "SELECT 10 %% 3, '100%%', %s"


def test_agrega_returning_id_solo_a_los_insert_de_tablas_con_id_generado():
    sql, devuelve = datos._preparar("INSERT INTO conversaciones(usuario,titulo,creada) VALUES(?,?,?)")
    assert devuelve and sql == "INSERT INTO conversaciones(usuario,titulo,creada) VALUES(%s,%s,%s) RETURNING id"
    sql, devuelve = datos._preparar("  insert into mensajes(conv,rol) VALUES(?,?);  ")
    assert devuelve and sql.endswith("VALUES(%s,%s) RETURNING id")
    for otra in ("INSERT INTO usuarios(email) VALUES(?)",                       # llave primaria de texto
                 "INSERT INTO boletin(fecha,contenido,creado) VALUES(?,?,?) ON CONFLICT(fecha) DO NOTHING",
                 "UPDATE conversaciones SET titulo=? WHERE id=?",
                 "INSERT INTO conversaciones(usuario) VALUES(?) RETURNING id, usuario"):
        assert datos._preparar(otra)[1] is False, otra


def test_las_tablas_con_id_generado_salen_del_archivo_de_esquema():
    assert datos.tablas_con_id() == {"conversaciones", "mensajes", "modular_casos", "modular_intentos",
                                     "documentos_generados", "asistente_tareas", "taller_escenarios", "taller_intentos",
                                     "perfiles_ejecuciones", "calidad_respuestas"}


def test_adapta_los_parametros_que_postgres_no_acepta_igual_que_sqlite():
    assert datos._adaptar(None) == ()
    assert datos._adaptar([True, False, 3, None, 1.5, b"\x00b"]) == (1, 0, 3, None, 1.5, b"\x00b")
    assert all(type(x) is int for x in datos._adaptar((True, False)))
    assert datos._adaptar(("ho\x00la",)) == ("hola",)            # PostgreSQL no admite NUL en un texto
    with pytest.raises(TypeError):
        datos._adaptar({"a": 1})


def test_fila_se_comporta_como_sqlite3_row():
    f = datos.Fila(("id", "titulo", "n"), {"id": 0, "titulo": 1, "n": 2}, (7, "Hola", None))
    assert f["id"] == 7 and f[1] == "Hola" and f[-1] is None and f["TITULO"] == "Hola"
    assert f.keys() == ["id", "titulo", "n"] and len(f) == 3 and list(f) == [7, "Hola", None]
    assert dict(f) == {"id": 7, "titulo": "Hola", "n": None} and tuple(f) == (7, "Hola", None)
    with pytest.raises(IndexError):
        f["no_existe"]
    with pytest.raises(IndexError):
        f[9]


# ------------------------------------------------------------------- configuración y la URL --
def test_el_motor_se_elige_por_las_variables_en_orden(monkeypatch):
    for v in datos.VARIABLES_URL:
        monkeypatch.setenv(v, "")
    assert datos.motor() == "sqlite" and datos.variable_en_uso() is None and not datos.es_postgres()
    monkeypatch.setenv("DATABASE_URL", "postgresql://c/c")
    assert datos.variable_en_uso() == "DATABASE_URL" and datos.motor() == "postgres"
    monkeypatch.setenv("POSTGRES_URL", "postgresql://b/b")
    assert datos.variable_en_uso() == "POSTGRES_URL"
    monkeypatch.setenv("PULLEX_DATABASE_URL", "postgresql://a/a")
    assert datos.variable_en_uso() == "PULLEX_DATABASE_URL"
    monkeypatch.setenv("PULLEX_DATABASE_URL", "   ")             # vacía o en blanco no cuenta
    assert datos.variable_en_uso() == "POSTGRES_URL"


def test_limpia_de_la_url_lo_que_libpq_no_conoce():
    pytest.importorskip("psycopg")
    p = datos.limpiar_url(URL_REMOTA + "?workaround=supabase-pooler.vercel&supa=base-pooler.x&pgbouncer=true"
                                       "&connection_limit=1&schema=public&application_name=pullex")
    assert p["host"] == "aws-0-us-east-1.pooler.ejemplo.com" and str(p["port"]) == "6543" and p["dbname"] == "postgres"
    assert p["user"] == "usuario.proyecto" and p["password"] == "Cl4ve-Secreta"
    assert p["application_name"] == "pullex"                     # lo que libpq sí conoce se conserva
    for desconocido in ("workaround", "supa", "pgbouncer", "connection_limit", "schema"):
        assert desconocido not in p


def test_exige_tls_cuando_el_servidor_no_es_local():
    pytest.importorskip("psycopg")
    assert datos.limpiar_url(URL_REMOTA)["sslmode"] == "require"
    assert datos.limpiar_url(URL_REMOTA + "?sslmode=disable")["sslmode"] == "require"
    assert datos.limpiar_url(URL_REMOTA + "?sslmode=prefer&supa=x")["sslmode"] == "require"
    assert datos.limpiar_url(URL_REMOTA + "?sslmode=verify-full")["sslmode"] == "verify-full"    # más estricto: se respeta
    for local in ("postgresql://u:c@127.0.0.1:5432/db", "postgresql://u:c@localhost/db", "postgresql://u:c@[::1]/db",
                  "postgresql:///db?host=/var/run/postgresql"):
        assert "sslmode" not in datos.limpiar_url(local), local


def test_tiempo_de_conexion_corto_por_defecto():
    pytest.importorskip("psycopg")
    assert int(datos.limpiar_url(URL_REMOTA)["connect_timeout"]) == 5
    assert int(datos.limpiar_url(URL_REMOTA + "?connect_timeout=2")["connect_timeout"]) == 2


@pytest.mark.parametrize("url", ["postgresql://u:Cl4ve%zzSecreta@servidor.ejemplo.com/db",
                                 "postgresql://u:Cl4ve-Secreta@[servidor.ejemplo.com/db",
                                 "host=servidor.ejemplo.com password='Cl4ve-Secreta"])
def test_una_url_ilegible_no_filtra_su_contenido(url):
    """El error de libpq cita la URL (con la contraseña): se reemplaza por uno que no la lleva."""
    pytest.importorskip("psycopg")
    with pytest.raises(datos.ErrorConfiguracion) as e:
        datos.limpiar_url(url)
    for secreto in ("Cl4ve", "Secreta", "servidor.ejemplo.com"):
        assert secreto not in str(e.value)
    assert e.value.__cause__ is None and e.value.__suppress_context__      # el error original no viaja encadenado


@pytest.mark.parametrize("nombre", ['pullex"; DROP SCHEMA public CASCADE; --', "Pullex", "pullex prod", "1pullex", "pullex-ia",
                                    "public", "pg_catalog", "information_schema", "a" * 64, "esquema;"])
def test_el_nombre_del_esquema_se_valida_como_identificador(monkeypatch, nombre):
    monkeypatch.setenv("PULLEX_DB_ESQUEMA", nombre)
    with pytest.raises(datos.ErrorConfiguracion):
        datos.esquema()


def test_el_esquema_por_defecto_es_pullex(monkeypatch):
    monkeypatch.delenv("PULLEX_DB_ESQUEMA", raising=False)
    assert datos.esquema() == "pullex"
    monkeypatch.setenv("PULLEX_DB_ESQUEMA", "pullex_pruebas_1")
    assert datos.esquema() == "pullex_pruebas_1"


def test_sin_psycopg_y_con_url_el_error_es_claro(monkeypatch):
    monkeypatch.setattr(datos, "_pg_modulo", None)
    monkeypatch.setattr(datos, "_pg_intentado", False)
    monkeypatch.setitem(sys.modules, "psycopg", None)            # importar psycopg falla
    with pytest.raises(datos.ErrorConfiguracion, match="psycopg"):
        datos.limpiar_url(URL_REMOTA)
    assert datos.errores_integridad() == (datos.sqlite3.IntegrityError,)


def test_en_modo_sqlite_la_app_arranca_sin_psycopg(tmp_path):
    """Importación perezosa: sin URL de PostgreSQL, psycopg ni siquiera se intenta importar al arrancar y usar la base."""
    guion = (
        "import sys, os\n"
        "sys.modules['psycopg'] = None\n"                       # cualquier «import psycopg» lanzaría ImportError
        f"sys.path.insert(0, {str(RAIZ)!r})\n"
        "import app\n"
        "from contextlib import closing\n"
        "with closing(app.db()) as con:\n"
        "    n = con.execute('SELECT COUNT(*) c FROM usuarios').fetchone()['c']\n"
        "print('OK', app.base_datos.motor(), n, type(con).__module__, app.salud()['db_motor'])\n")
    (tmp_path / "static").symlink_to(RAIZ / "static")
    entorno = {**os.environ, "PULLEX_DATABASE_URL": "", "POSTGRES_URL": "", "DATABASE_URL": "", "PULLEX_DB": "",
               "PULLEX_BIBLIOTECA_DB": str(tmp_path / "b.db"), "PULLEX_CORPUS_DB": str(tmp_path / "c.db")}
    entorno.pop("VERCEL", None)
    r = subprocess.run([sys.executable, "-c", guion], cwd=tmp_path, env=entorno, capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stderr[-2000:]
    assert r.stdout.strip().splitlines()[-1] == "OK sqlite 1 sqlite3 sqlite"
    assert (tmp_path / "pullex.db").is_file()


def test_estado_en_sqlite_avisa_si_la_base_es_temporal(sin_postgres, monkeypatch):
    monkeypatch.delenv("VERCEL", raising=False)
    e = datos.estado("pullex.db")
    assert e["motor"] == "sqlite" and e["persistente"] is True and e["conecta"] is True
    monkeypatch.setenv("VERCEL", "1")
    e = datos.estado("/tmp/pullex.db")
    assert e["persistente"] is False and "NO se conservan" in e["detalle"] and "docs/18-BASE-DE-DATOS.md" in e["detalle"]


def test_conectar_en_sqlite_devuelve_la_conexion_de_siempre(sin_postgres, tmp_path):
    with closing(datos.conectar(str(tmp_path / "x.db"))) as con:
        assert isinstance(con, datos.sqlite3.Connection)
        con.execute("CREATE TABLE t(a)")
        con.execute("INSERT INTO t VALUES(?)", (1,))
        assert con.execute("SELECT a FROM t").fetchone()["a"] == 1


# ------------------------------------------------------- el mismo comportamiento en los dos motores --
def test_lastrowid_rowcount_y_filas_por_la_conexion_de_la_app(modulo):
    """Corre en el motor de la sesión (SQLite o PostgreSQL): lo que el código usa de la conexión se comporta igual."""
    email = f"capa_{time.time_ns()}@pruebas.local"
    with closing(modulo.db()) as con:
        c1 = con.execute("INSERT INTO conversaciones(usuario,titulo,creada) VALUES(?,?,?)", (email, "100% ¿sí?", 1.5))
        c2 = con.execute("INSERT INTO conversaciones(usuario,titulo,creada) VALUES(?,?,?)", (email, "it's", 2.5))
        assert isinstance(c1.lastrowid, int) and c2.lastrowid == c1.lastrowid + 1
        con.commit()
        f = con.execute("SELECT id, titulo, creada, '¿?' q, 7 % 4 resto FROM conversaciones "
                        "WHERE usuario=? AND titulo LIKE '100%' ORDER BY id", (email,)).fetchone()
        assert f["id"] == c1.lastrowid == f[0] and f["titulo"] == "100% ¿sí?" == f[1] and f["q"] == "¿?" and f["resto"] == 3
        assert f.keys() == ["id", "titulo", "creada", "q", "resto"] and isinstance(f["creada"], float)
        assert dict(f) == {"id": c1.lastrowid, "titulo": "100% ¿sí?", "creada": 1.5, "q": "¿?", "resto": 3}
        cur = con.execute("UPDATE conversaciones SET titulo=? WHERE usuario=?", ("x", email))
        assert cur.rowcount == 2
        assert con.execute("UPDATE conversaciones SET titulo=? WHERE usuario=?", ("x", "nadie@x")).rowcount == 0
        filas = con.execute("SELECT id FROM conversaciones WHERE usuario=? ORDER BY id", (email,)).fetchall()
        assert [x["id"] for x in filas] == [c1.lastrowid, c2.lastrowid]
        assert [x[0] for x in con.execute("SELECT id FROM conversaciones WHERE usuario=? ORDER BY id DESC", (email,))] == \
            [c2.lastrowid, c1.lastrowid]
        assert con.execute("SELECT id FROM conversaciones WHERE usuario=?", ("nadie@x",)).fetchone() is None
        agg = con.execute("SELECT COUNT(*) n, AVG(id) p, SUM(id) s, MAX(creada) m FROM conversaciones WHERE usuario=?",
                          (email,)).fetchone()
        assert agg["n"] == 2 and type(agg["n"]) is int and isinstance(agg["p"], float) and type(agg["s"]) is int
        assert agg["p"] == c1.lastrowid + 0.5 and agg["m"] == 2.5
        con.execute("DELETE FROM conversaciones WHERE usuario=?", (email,))
        con.commit()


def test_cerrar_sin_confirmar_deshace_los_cambios(modulo):
    email = f"sinconfirmar_{time.time_ns()}@pruebas.local"
    with closing(modulo.db()) as con:
        con.execute("INSERT INTO conversaciones(usuario,titulo,creada) VALUES(?,?,?)", (email, "t", 1.0))
        assert con.execute("SELECT COUNT(*) c FROM conversaciones WHERE usuario=?", (email,)).fetchone()["c"] == 1
    with closing(modulo.db()) as con:
        assert con.execute("SELECT COUNT(*) c FROM conversaciones WHERE usuario=?", (email,)).fetchone()["c"] == 0


def test_booleanos_bytes_nulos_y_reemplazos_se_guardan_igual(modulo):
    email = f"tipos_{time.time_ns()}@pruebas.local"
    imagen = bytes(range(256)) * 3
    with closing(modulo.db()) as con:
        cur = con.execute("INSERT INTO mensajes(conv,rol,contenido,creada,incompleta) VALUES(?,?,?,?,?)",
                          (-1, "assistant", "con comillas ' y \" y % y ?", time.time(), True))
        mid = cur.lastrowid
        f = con.execute("SELECT contenido, incompleta, fuentes FROM mensajes WHERE id=?", (mid,)).fetchone()
        assert f["incompleta"] == 1 and type(f["incompleta"]) is int and f["fuentes"] is None
        assert f["contenido"] == "con comillas ' y \" y % y ?"
        for mime in ("image/png", "image/jpeg"):                 # el segundo reemplaza al primero (misma llave)
            con.execute("INSERT INTO apariencia_imagenes(usuario,tipo,mime,data,actualizado) VALUES(?,?,?,?,?) "
                        "ON CONFLICT(usuario,tipo) DO UPDATE SET mime=excluded.mime, data=excluded.data, "
                        "actualizado=excluded.actualizado", (email, "fondo", mime, imagen, 1.0))
        g = con.execute("SELECT mime, data FROM apariencia_imagenes WHERE usuario=?", (email,)).fetchall()
        assert len(g) == 1 and g[0]["mime"] == "image/jpeg" and bytes(g[0]["data"]) == imagen
        nulo = con.execute("SELECT id IS NULL a, id IS NOT NULL b FROM mensajes WHERE id=?", (mid,)).fetchone()
        assert (nulo["a"], nulo["b"]) == (0, 1) and type(nulo["a"]) is int and type(nulo["b"]) is int     # 0/1, no False/True
        con.rollback()


def test_un_mensaje_con_caracter_nulo_no_tumba_el_chat(cliente):
    """PostgreSQL no admite el carácter NUL en un texto (SQLite sí): la capa de datos lo quita en vez de fallar."""
    _, _, t = nuevo_usuario(cliente)
    cid = cliente.post("/api/conversaciones", headers=auth(t)).json()["id"]
    r = cliente.post("/api/chat", headers=auth(t), json={"conversacion": cid, "mensaje": "hola\u0000 mundo", "web": False})
    assert r.status_code == 200
    textos = [m["contenido"] for m in cliente.get(f"/api/conversaciones/{cid}/mensajes", headers=auth(t)).json()]
    assert textos and textos[0].replace("\x00", "") == "hola mundo"


def test_reintegrar_consulta_nunca_baja_de_cero(cliente, modulo):
    email, _, _ = nuevo_usuario(cliente)
    modulo.reintegrar_consulta(email)
    assert modulo.obtener_usuario(email)["usadas"] == 0
    modulo.consumir_consulta(modulo.obtener_usuario(email))
    modulo.consumir_consulta(modulo.obtener_usuario(email))
    modulo.reintegrar_consulta(email)
    assert modulo.obtener_usuario(email)["usadas"] == 1


def test_registro_duplicado_simultaneo_responde_409_y_no_500(cliente, modulo, monkeypatch):
    """Dos registros a la vez con el mismo correo: el segundo choca con la llave primaria en cualquiera de los motores."""
    email, clave, _ = nuevo_usuario(cliente)
    monkeypatch.setattr(modulo, "obtener_usuario", lambda e: None)       # como si el otro registro aún no se viera
    r = cliente.post("/api/registro", json={"email": email, "nombre": "Otra Persona", "clave": "otra-clave-123"})
    assert r.status_code == 409 and "Ya existe" in r.json()["detail"]
    monkeypatch.undo()
    assert cliente.post("/api/login", json={"email": email, "clave": clave}).status_code == 200


test_registro_duplicado_simultaneo_responde_409_y_no_500 = pytest.mark.errores_sql_esperados(
    test_registro_duplicado_simultaneo_responde_409_y_no_500)


# ------------------------------------------------------------------ estado para el operador --
def test_salud_y_panel_dicen_que_base_esta_en_uso(cliente, modulo):
    s = cliente.get("/salud").json()
    assert s["db"] is True and s["db_motor"] == ("postgres" if EN_POSTGRES else "sqlite")
    t = cliente.post("/api/login", json={"email": ADMIN_EMAIL, "clave": ADMIN_CLAVE}).json()["token"]
    b = cliente.get("/api/admin/metricas", headers=auth(t)).json()["base_datos"]
    assert b["motor"] == s["db_motor"] and b["conecta"] is True
    if EN_POSTGRES:
        assert b["persistente"] is True and b["esquema_al_dia"] is True and b["nombre"] == "PostgreSQL"
        assert b["esquema"].startswith("pullex_pruebas_") and b["variable"] == "PULLEX_DATABASE_URL"
    # nunca el servidor, el usuario, la contraseña ni la URL
    texto = json.dumps(b)
    for secreto in ("127.0.0.1", "54329", "pullex_pruebas:", "postgresql://", "password", "@"):
        assert secreto not in texto, secreto
    assert set(b) <= {"motor", "nombre", "conecta", "persistente", "detalle", "variable", "esquema", "esquema_al_dia", "tls", "aviso"}
    assert "aviso" not in b                                      # el usuario de las pruebas es dueño de las tablas
    u = nuevo_usuario(cliente)[2]
    assert cliente.get("/api/admin/metricas", headers=auth(u)).status_code == 403


# ----------------------------------------------------------- la base no responde: 503, no SQLite --
@pytest.fixture
def base_caida(monkeypatch):
    """Apunta la capa de datos a un PostgreSQL que no existe (puerto cerrado en la propia máquina)."""
    pytest.importorskip("psycopg")
    monkeypatch.setenv("PULLEX_DATABASE_URL", URL_SIN_SERVIDOR)
    monkeypatch.setenv("PULLEX_DB_ESQUEMA", "pullex_pruebas_caida")
    yield
    monkeypatch.undo()
    datos._config()         # vuelve a la configuración de la sesión antes de la siguiente prueba


def test_si_postgres_no_responde_la_app_responde_503_y_no_cae_a_sqlite(cliente, modulo, base_caida, caplog):
    caplog.set_level(logging.INFO)
    assert modulo.base_datos.motor() == "postgres"
    with pytest.raises(datos.ErrorConexion):
        with closing(modulo.db()) as con:
            con.execute("SELECT 1")
    r = cliente.post("/api/login", json={"email": ADMIN_EMAIL, "clave": ADMIN_CLAVE})
    assert r.status_code == 503 and r.json()["codigo"] == "base_no_disponible"
    assert "base de datos no responde" in r.json()["detail"] and r.headers["retry-after"] == "5"
    assert "content-security-policy" in r.headers                 # pasa por las cabeceras de seguridad de siempre
    # una ruta protegida por plan pasa primero por el middleware de acceso: también 503, no 500
    r = cliente.get("/api/documentos", headers={"Authorization": "Bearer " + _token_firmado(modulo)})
    assert r.status_code == 503 and r.json()["codigo"] == "base_no_disponible"
    s = cliente.get("/salud")
    assert s.status_code == 200 and s.json()["db"] is False and s.json()["estado"] == "degradado"
    assert s.json()["db_motor"] == "postgres"
    assert cliente.get("/").status_code == 200                    # la portada no depende de la base
    e = datos.estado()
    assert e["motor"] == "postgres" and e["conecta"] is False and "No conecta" in e["detalle"]
    # el registro lo dice claro y sin la URL, el servidor, el usuario ni la contraseña
    registro = "\n".join(x.getMessage() for x in caplog.records)
    assert "No hay conexión con la base de datos PostgreSQL" in registro and "PULLEX_DATABASE_URL" in registro
    for secreto in ("Cl4ve-Secreta", "nadie", "127.0.0.1", "postgresql://"):
        assert secreto not in registro and secreto not in json.dumps(e) and secreto not in r.text, secreto


def _token_firmado(modulo, email="alguien@pruebas.local"):
    """Un token con firma válida (la app solo consulta la base después de comprobar la firma)."""
    import base64
    import hashlib
    import hmac
    cuerpo = json.dumps({"u": email, "t": time.time(), "v": 0}).encode()
    firma = hmac.new(modulo.SECRET, cuerpo, hashlib.sha256).digest()
    return base64.urlsafe_b64encode(cuerpo).decode() + "." + base64.urlsafe_b64encode(firma).decode()


def _importar_app_nueva(nombre):
    spec = importlib.util.spec_from_file_location(nombre, RAIZ / "app.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_la_app_arranca_aunque_postgres_no_responda_y_se_recupera_sola(modulo, base_caida, monkeypatch, caplog):
    """Arranque en frío con la base caída: la app queda arriba (degradada) y, cuando la base vuelve, la siguiente
    petición termina de prepararla sin reiniciar."""
    from fastapi.testclient import TestClient
    caplog.set_level(logging.ERROR)
    m = _importar_app_nueva("app_base_caida")                    # no lanza: registra el error y sigue
    assert m._base["lista"] is False
    assert "no quedó lista al arrancar" in "\n".join(x.getMessage() for x in caplog.records)
    c = TestClient(m.app)
    assert c.get("/salud").json()["db"] is False
    r = c.post("/api/login", json={"email": ADMIN_EMAIL, "clave": ADMIN_CLAVE})
    assert r.status_code == 503 and r.json()["codigo"] == "base_no_disponible"
    assert m._base["lista"] is False
    # la base «vuelve»: se restituye la configuración de la sesión (SQLite o el PostgreSQL de pruebas)
    monkeypatch.undo()
    r = c.post("/api/login", json={"email": ADMIN_EMAIL, "clave": ADMIN_CLAVE})
    assert r.status_code == 200 and m._base["lista"] is True
    assert c.get("/salud").json()["db"] is True


# ------------------------------------------------------------------- PostgreSQL de verdad --
@postgres
def test_pg_la_url_con_parametros_de_vercel_conecta(modulo, monkeypatch):
    sep = "&" if "?" in PG_URL else "?"
    monkeypatch.setenv("PULLEX_DATABASE_URL", PG_URL + sep + "workaround=supabase-pooler.vercel&supa=base-pooler.x&pgbouncer=true")
    with closing(modulo.db()) as con:
        assert con.execute("SELECT COUNT(*) c FROM usuarios").fetchone()["c"] >= 1
    monkeypatch.undo()
    datos._config()


@postgres
def test_pg_el_esquema_se_fija_por_transaccion_y_no_queda_en_la_sesion(modulo):
    cfg = datos._config()
    with closing(modulo.db()) as con:
        assert con.execute("SELECT current_schema() s").fetchone()["s"] == cfg.esquema
        assert con.execute("SHOW search_path").fetchone()[0].strip('"') == cfg.esquema
        pid = con.execute("SELECT pg_backend_pid() p").fetchone()["p"]
        con.commit()
        # tras confirmar, la siguiente sentencia empieza otra transacción y vuelve a fijarlo
        assert con.execute("SELECT current_schema() s").fetchone()["s"] == cfg.esquema
    # la conexión real, ya devuelta al grupo y fuera de transacción, conserva el search_path del servidor
    cruda = datos._grupo_actual.tomar()
    try:
        assert cruda.execute("SELECT pg_backend_pid()").fetchone()[0] == pid         # es la misma: se reutilizó
        assert cfg.esquema not in cruda.execute("SHOW search_path").fetchone()[0]
        assert cruda.execute("SELECT count(*) FROM pg_prepared_statements").fetchone()[0] == 0
    finally:
        datos._grupo_actual.devolver(cruda)


@postgres
def test_pg_sin_sentencias_preparadas_aunque_se_repita_la_consulta(modulo):
    with closing(modulo.db()) as con:
        for _ in range(12):                                      # psycopg prepara a la quinta repetición por defecto
            con.execute("SELECT email FROM usuarios WHERE email=?", (ADMIN_EMAIL,)).fetchone()
        assert con.execute("SELECT COUNT(*) c FROM pg_prepared_statements").fetchone()["c"] == 0
        assert con._pg.prepare_threshold is None


@postgres
def test_pg_las_conexiones_se_reutilizan_y_no_quedan_en_transaccion(modulo):
    antes = datos.estadisticas["conexiones_abiertas"]
    pids = set()
    for _ in range(6):
        with closing(modulo.db()) as con:
            pids.add(con.execute("SELECT pg_backend_pid() p").fetchone()["p"])
    assert len(pids) == 1 and datos.estadisticas["conexiones_abiertas"] == antes
    with _admin_pg() as admin:
        estado = admin.execute("SELECT state FROM pg_stat_activity WHERE pid=%s", (pids.pop(),)).fetchone()[0]
    assert estado == "idle"                                      # ni «idle in transaction» ni abortada
    assert 1 <= datos._grupo_actual.libres() <= datos.MAX_LIBRES


@postgres
def test_pg_el_grupo_guarda_pocas_conexiones_aunque_haya_muchas_a_la_vez(modulo):
    """8 peticiones a la vez: como mucho max_abiertas() (5) usan conexión al mismo tiempo (BD-08), las demás esperan su
    turno sin error, y al terminar solo quedan guardadas MAX_LIBRES."""
    errores, cerrojo, uso = [], threading.Lock(), {"ahora": 0, "maximo": 0}

    def trabajo():
        try:
            with closing(modulo.db()) as con:
                con.execute("SELECT 1")
                with cerrojo:
                    uso["ahora"] += 1
                    uso["maximo"] = max(uso["maximo"], uso["ahora"])
                time.sleep(0.3)
                con.execute("SELECT COUNT(*) c FROM usuarios").fetchone()
                with cerrojo:
                    uso["ahora"] -= 1
        except Exception as e:      # noqa: BLE001
            errores.append(e)
    hilos = [threading.Thread(target=trabajo) for _ in range(8)]
    [h.start() for h in hilos]
    [h.join(timeout=30) for h in hilos]
    assert not errores, errores
    assert 2 <= uso["maximo"] <= datos.max_abiertas() == datos.MAX_ABIERTAS_POR_DEFECTO == 5
    assert datos._grupo_actual.libres() <= datos.MAX_LIBRES == 3 and datos._grupo_actual.en_uso() == 0
    with _admin_pg() as admin:
        abiertas = admin.execute("SELECT count(*) FROM pg_stat_activity WHERE pid <> pg_backend_pid() AND datname = current_database() "
                                 "AND state IS NOT NULL").fetchone()[0]
    assert abiertas <= datos.MAX_LIBRES                           # las que sobraban se cerraron al devolverlas


@postgres
def test_pg_reconecta_si_la_conexion_guardada_murio(modulo, caplog):
    """Lo que pasa cuando Vercel congela la instancia y el servidor cierra la conexión: la siguiente transacción la
    encuentra muerta al empezar, abre otra y sigue, sin que quien llama se entere."""
    caplog.set_level(logging.WARNING)
    with closing(modulo.db()) as con:
        pid = con.execute("SELECT pg_backend_pid() p").fetchone()["p"]
    with _admin_pg() as admin:
        assert admin.execute("SELECT pg_terminate_backend(%s)", (pid,)).fetchone()[0] is True
    time.sleep(0.2)
    antes = datos.estadisticas["reconexiones"]
    with closing(modulo.db()) as con:
        f = con.execute("SELECT pg_backend_pid() p, (SELECT COUNT(*) FROM usuarios) n").fetchone()
        assert f["p"] != pid and f["n"] >= 1
        cur = con.execute("INSERT INTO conversaciones(usuario,titulo,creada) VALUES(?,?,?)", ("reconexion@x", "t", 1.0))
        assert cur.lastrowid > 0
        con.rollback()
    assert datos.estadisticas["reconexiones"] == antes + 1
    aviso = "\n".join(x.getMessage() for x in caplog.records)
    assert "se abre otra y se reintenta una vez" in aviso and "127.0.0.1" not in aviso and "pullex_pruebas:" not in aviso


@postgres
@pytest.mark.errores_sql_esperados
def test_pg_no_reintenta_a_mitad_de_una_transaccion(modulo):
    email = f"mitad_{time.time_ns()}@pruebas.local"
    reconexiones = datos.estadisticas["reconexiones"]
    with closing(modulo.db()) as con:
        con.execute("INSERT INTO conversaciones(usuario,titulo,creada) VALUES(?,?,?)", (email, "a medias", 1.0))
        pid = con.execute("SELECT pg_backend_pid() p").fetchone()["p"]
        with _admin_pg() as admin:
            admin.execute("SELECT pg_terminate_backend(%s)", (pid,))
        time.sleep(0.2)
        with pytest.raises(datos.ErrorConexion):                 # no se reintenta: lo anterior de la transacción se perdió
            con.execute("INSERT INTO conversaciones(usuario,titulo,creada) VALUES(?,?,?)", (email, "segunda", 2.0))
        with pytest.raises(datos.ErrorTransaccion):
            con.commit()
    assert datos.estadisticas["reconexiones"] == reconexiones
    with closing(modulo.db()) as con:                            # la siguiente conexión funciona y no hay nada a medias
        assert con.execute("SELECT COUNT(*) c FROM conversaciones WHERE usuario=?", (email,)).fetchone()["c"] == 0


@postgres
@pytest.mark.errores_sql_esperados
def test_pg_confirmar_tras_un_error_avisa_en_vez_de_perder_los_cambios_en_silencio(modulo):
    import psycopg
    email = f"abortada_{time.time_ns()}@pruebas.local"
    with closing(modulo.db()) as con:
        con.execute("INSERT INTO conversaciones(usuario,titulo,creada) VALUES(?,?,?)", (email, "antes", 1.0))
        with pytest.raises(psycopg.errors.UniqueViolation) as e:
            con.execute("INSERT INTO usuarios(email,nombre) VALUES(?,?)", (ADMIN_EMAIL, "duplicado"))
        assert isinstance(e.value, datos.errores_integridad()) and isinstance(e.value, datos.errores_bd())
        with pytest.raises(psycopg.errors.InFailedSqlTransaction):       # PostgreSQL: la transacción quedó abortada
            con.execute("SELECT 1")
        with pytest.raises(datos.ErrorTransaccion):
            con.commit()
        # después de eso la misma conexión vuelve a servir (empieza una transacción nueva)
        assert con.execute("SELECT COUNT(*) c FROM conversaciones WHERE usuario=?", (email,)).fetchone()["c"] == 0


@postgres
def test_pg_executescript_ejecuta_varias_sentencias_y_confirma(modulo):
    with closing(modulo.db()) as con:
        con.executescript("""
            CREATE TABLE IF NOT EXISTS zz_prueba_guion(a BIGINT, b TEXT);
            INSERT INTO zz_prueba_guion VALUES (1, '100% ¿sí?');
            INSERT INTO zz_prueba_guion VALUES (2, 'dos');
        """)
    with closing(modulo.db()) as con:
        assert [tuple(f) for f in con.execute("SELECT a, b FROM zz_prueba_guion ORDER BY a")] == [(1, "100% ¿sí?"), (2, "dos")]
        con.executescript("DROP TABLE zz_prueba_guion")


@postgres
def test_pg_el_arranque_normal_no_ejecuta_ddl(modulo, monkeypatch):
    """Con el esquema al día, asegurar_esquema hace una consulta y nada más: ni lee ni aplica el archivo."""
    def no_debe_leerse(*a, **k):
        raise AssertionError("no debería aplicarse el archivo de esquema si la versión está al día")
    aplicadas = datos.estadisticas["esquema_aplicado"]
    version = datos.version_del_archivo()
    monkeypatch.setattr(datos, "leer_esquema", no_debe_leerse)
    sentencias = []
    original = datos._Grupo.tomar

    def tomar_espiando(self):
        cruda = original(self)
        ejecutar = cruda.execute
        cruda.execute = lambda sql, *a, **k: (sentencias.append(str(sql)), ejecutar(sql, *a, **k))[1]
        return cruda
    monkeypatch.setattr(datos._Grupo, "tomar", tomar_espiando)
    try:
        assert datos.asegurar_esquema() == {"motor": "postgres", "aplicado": False, "version": version}
    finally:
        monkeypatch.undo()
        datos._grupo_actual.descartar_libres()                   # la conexión espiada no vuelve a usarse
    assert datos.estadisticas["esquema_aplicado"] == aplicadas
    assert [s for s in sentencias if not s.startswith(("BEGIN", "ROLLBACK"))] == ["SELECT MAX(version) FROM esquema_version"]
    assert not any(p in " ".join(sentencias).upper() for p in ("CREATE ", "ALTER ", "DROP "))


@postgres
def test_pg_la_cuenta_sigue_existiendo_despues_de_un_reinicio(cliente, modulo, tmp_path):
    """El fallo que tuvo el dueño: se registró, la instancia se reinició y la cuenta ya no estaba.
    Aquí la cuenta se crea en este proceso y se ingresa desde OTRO proceso recién arrancado, en otra carpeta (sin
    ningún archivo de base local), contra el mismo PostgreSQL."""
    email, clave, token = nuevo_usuario(cliente, nombre="Persona Que Vuelve")
    cid = cliente.post("/api/conversaciones", headers=auth(token)).json()["id"]
    assert cliente.post("/api/chat", headers=auth(token), json={"conversacion": cid, "mensaje": "¿Qué es la tutela?",
                                                                 "web": False}).status_code == 200
    modulo.base_datos.reiniciar()                                # este proceso suelta sus conexiones
    guion = (
        "import sys, json\n"
        f"sys.path.insert(0, {str(RAIZ)!r})\n"
        "import app\n"
        "from fastapi.testclient import TestClient\n"
        "c = TestClient(app.app)\n"
        f"r = c.post('/api/login', json={{'email': {email!r}, 'clave': {clave!r}}})\n"
        "t = r.json().get('token', '')\n"
        "h = {'Authorization': 'Bearer ' + t}\n"
        "convs = c.get('/api/conversaciones', headers=h)\n"
        f"msjs = c.get('/api/conversaciones/{cid}/mensajes', headers=h)\n"
        "print(json.dumps({'login': r.status_code, 'nombre': (r.json().get('perfil') or {}).get('nombre'),\n"
        "                  'convs': [x['id'] for x in convs.json()], 'mensajes': len(msjs.json()),\n"
        "                  'motor': app.base_datos.motor(), 'aplico_esquema': app.base_datos.estadisticas['esquema_aplicado'],\n"
        "                  'salud': c.get('/salud').json()['db']}))\n")
    (tmp_path / "static").symlink_to(RAIZ / "static")
    entorno = {**os.environ, "PULLEX_BIBLIOTECA_DB": str(tmp_path / "b.db"), "PULLEX_CORPUS_DB": str(tmp_path / "c.db")}
    r = subprocess.run([sys.executable, "-c", guion], cwd=tmp_path, env=entorno, capture_output=True, text=True, timeout=180)
    assert r.returncode == 0, r.stderr[-3000:]
    d = json.loads(r.stdout.strip().splitlines()[-1])
    assert d == {"login": 200, "nombre": "Persona Que Vuelve", "convs": [cid], "mensajes": 2, "motor": "postgres",
                 "aplico_esquema": 0, "salud": True}
    assert not (tmp_path / "pullex.db").exists()                 # el proceso nuevo no creó ninguna base local
    # y en este proceso, con conexiones nuevas, la sesión anterior sigue sirviendo
    assert cliente.get("/api/estado", headers=auth(token)).status_code == 200


@postgres
def test_pg_esquema_propio_y_esquema_inexistente_se_crea_al_arrancar(monkeypatch):
    """asegurar_esquema sobre un esquema que no existe: lo crea, aplica el archivo una vez y la segunda vez no hace nada."""
    nombre = f"pullex_pruebas_nuevo_{time.time_ns() % 10**9}"
    monkeypatch.setenv("PULLEX_DB_ESQUEMA", nombre)
    try:
        assert datos.estado()["esquema_al_dia"] is False and datos.estado()["conecta"] is True
        assert datos.asegurar_esquema() == {"motor": "postgres", "aplicado": True, "version": datos.version_del_archivo()}
        assert datos.asegurar_esquema()["aplicado"] is False
        assert datos.estado()["esquema_al_dia"] is True
        with closing(datos.conectar()) as con:
            assert con.execute("SELECT COUNT(*) c FROM usuarios").fetchone()["c"] == 0
            assert con.execute("SELECT COUNT(*) c FROM esquema_version").fetchone()["c"] == datos.version_del_archivo()
        with _admin_pg() as admin:                               # nada en «public»
            assert admin.execute("SELECT to_regclass('public.usuarios') IS NULL AND to_regclass('public.esquema_version') IS NULL"
                                 ).fetchone()[0] is True
    finally:
        datos.reiniciar()
        borrar_esquema_de_pruebas(nombre)
        monkeypatch.undo()
        datos._config()
