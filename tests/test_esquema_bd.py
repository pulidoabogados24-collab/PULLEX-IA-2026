"""El esquema de la base principal es el mismo en SQLite (lo crea la app al arrancar) y en PostgreSQL
(datos/esquema_postgres.sql). Si alguien agrega una tabla o una columna en un lado y no en el otro, esto falla.

La comparación con el archivo no necesita servidor. Con PULLEX_PRUEBAS_PG_URL además se compara contra lo que
PostgreSQL crea de verdad al aplicarlo (tipos, llaves, índices, seguridad por filas) y se prueba que el archivo
sea idempotente y que se niegue a instalarse en «public».
"""
import re
import sqlite3
import time
from contextlib import closing

import pytest

import academia
import coordinador
import datos
import taller
import telemetria_respuestas
from conftest import PG_URL, RAIZ, borrar_esquema_de_pruebas

postgres = pytest.mark.solo_postgres
SOLO_POSTGRES = {"esquema_version"}        # control de versión del archivo: SQLite se migra desde el código
# tipo declarado en SQLite → tipo en PostgreSQL
EQUIVALENTE = {"TEXT": "TEXT", "INTEGER": "BIGINT", "REAL": "DOUBLE PRECISION", "BLOB": "BYTEA"}
TIPO_INFORMATION_SCHEMA = {"TEXT": "text", "BIGINT": "bigint", "DOUBLE PRECISION": "double precision", "BYTEA": "bytea"}


@pytest.fixture(scope="module")
def sqlite_de_la_app(tmp_path_factory):
    """Una base SQLite nueva creada con las mismas funciones que usa la app al arrancar (todas las de la base principal)."""
    import app      # el módulo ya importado por la sesión; aquí solo se usan sus funciones de creación
    ruta = tmp_path_factory.mktemp("esquema") / "nueva.db"
    con = sqlite3.connect(ruta)
    con.row_factory = sqlite3.Row
    app._crear_tablas_sqlite(con)           # app.py + academia + telemetría, con sus migraciones
    taller.crear_tablas(con)
    coordinador.crear_tablas(con)
    con.commit()
    yield con
    con.close()


def _esquema_sqlite(con) -> dict:
    """{tabla: {columna: {tipo, notnull, pk, defecto, autoincremental}}}"""
    tablas = {}
    for (nombre, sql) in con.execute("SELECT name, sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"):
        cols = {}
        for c in con.execute(f"PRAGMA table_info({nombre})"):
            cols[c["name"]] = {"tipo": c["type"].upper(), "notnull": bool(c["notnull"]), "pk": c["pk"], "defecto": c["dflt_value"],
                               "autoincremental": bool(c["pk"]) and "AUTOINCREMENT" in sql.upper() and c["type"].upper() == "INTEGER"}
        tablas[nombre] = cols
    return tablas


def _indices_sqlite(con) -> dict:
    return {n: t for n, t in con.execute("SELECT name, tbl_name FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%'")}


def test_las_funciones_de_creacion_cubren_todos_los_modulos(sqlite_de_la_app):
    """Si aparece un módulo nuevo con tablas en la base principal, hay que sumarlo a esta prueba y al archivo."""
    tablas = set(_esquema_sqlite(sqlite_de_la_app))
    assert len(tablas) == 17
    for modulo_tablas in ({"usuarios", "conversaciones", "mensajes", "boletin", "tokens_accion", "modular_casos",
                           "modular_intentos", "apariencia_imagenes", "documentos_generados", "asistente_tareas"},
                          {"conocimiento"}, {"calidad_respuestas"}, {"taller_escenarios", "taller_intentos", "taller_modelos"},
                          {"perfiles_ejecuciones", "perfiles_ejecuciones_perfil"}):
        assert modulo_tablas <= tablas


def test_mismas_tablas_en_sqlite_y_en_el_archivo_de_postgres(sqlite_de_la_app):
    en_sqlite = set(_esquema_sqlite(sqlite_de_la_app))
    en_archivo = set(datos.tablas_del_archivo())
    assert en_archivo - en_sqlite == SOLO_POSTGRES, "tablas que están en datos/esquema_postgres.sql y no crea la app en SQLite"
    assert en_sqlite - en_archivo == set(), "tablas que la app crea en SQLite y faltan en datos/esquema_postgres.sql"


def test_mismas_columnas_y_tipos_equivalentes(sqlite_de_la_app):
    en_sqlite, en_archivo = _esquema_sqlite(sqlite_de_la_app), datos.tablas_del_archivo()
    diferencias = []
    for tabla, cols in en_sqlite.items():
        del_archivo = en_archivo[tabla]
        if list(cols) != [c for c in del_archivo]:
            if set(cols) != set(del_archivo):
                diferencias.append(f"{tabla}: columnas distintas — solo SQLite {sorted(set(cols) - set(del_archivo))}, "
                                   f"solo PostgreSQL {sorted(set(del_archivo) - set(cols))}")
                continue
        for col, info in cols.items():
            definicion = del_archivo[col].upper()
            esperado = EQUIVALENTE[info["tipo"]]
            if not definicion.startswith(esperado):
                diferencias.append(f"{tabla}.{col}: SQLite {info['tipo']} → se esperaba {esperado}; el archivo dice «{del_archivo[col]}»")
            if info["autoincremental"] != ("GENERATED" in definicion and "IDENTITY" in definicion):
                diferencias.append(f"{tabla}.{col}: el id autogenerado no coincide")
            if info["tipo"] == "TEXT" and 'COLLATE "C"' not in definicion:
                diferencias.append(f'{tabla}.{col}: los textos llevan COLLATE "C" (ordenan como en SQLite)')
            if info["notnull"] and "NOT NULL" not in definicion and "PRIMARY KEY" not in definicion:
                diferencias.append(f"{tabla}.{col}: NOT NULL en SQLite y no en el archivo")
            if not info["notnull"] and "NOT NULL" in definicion:
                diferencias.append(f"{tabla}.{col}: NOT NULL en el archivo y no en SQLite")
            defecto = re.search(r"(?<!BY )DEFAULT\s+('[^']*'|\S+)", del_archivo[col], re.I)      # no el «BY DEFAULT» de la identidad
            if (info["defecto"] or None) != (defecto.group(1) if defecto else None):
                diferencias.append(f"{tabla}.{col}: valor por defecto distinto ({info['defecto']!r} vs {defecto and defecto.group(1)!r})")
    assert not diferencias, "\n".join(diferencias)


def test_mismos_indices(sqlite_de_la_app):
    assert _indices_sqlite(sqlite_de_la_app) == datos.indices_del_archivo()


def test_todas_las_tablas_tienen_seguridad_por_filas_y_el_archivo_no_nombra_el_esquema():
    texto = datos.leer_esquema()
    assert datos.tablas_con_rls_del_archivo() == set(datos.tablas_del_archivo())
    sin_comentarios = re.sub(r"--[^\n]*", "", texto)
    assert "CREATE POLICY" not in sin_comentarios.upper()                     # sin políticas: solo el dueño de las tablas
    assert "pullex." not in sin_comentarios and "public." not in sin_comentarios          # nada con el esquema fijo
    for sentencia in ("ALTER ROLE", "ALTER DATABASE", "ALTER SYSTEM", "DROP ", "TRUNCATE", "DELETE FROM", "GRANT "):
        assert sentencia not in sin_comentarios.upper(), sentencia            # nada global ni destructivo
    assert "CREATE SCHEMA IF NOT EXISTS" in sin_comentarios and datos.version_del_archivo() >= 1
    seguridad = re.sub(r"--[^\n]*", "", open(datos.RUTA_SEGURIDAD, encoding="utf-8").read())
    for sentencia in ("ALTER ROLE", "ALTER DATABASE", "DROP ", "GRANT ", "CREATE ROLE"):
        assert sentencia not in seguridad.upper(), sentencia
    assert "'anon'" in seguridad and "'authenticated'" in seguridad and "pullex." not in seguridad


def test_el_analizador_del_archivo_entiende_las_columnas_agregadas_despues(tmp_path):
    ruta = tmp_path / "e.sql"
    ruta.write_text("""-- version: 7
CREATE TABLE IF NOT EXISTS cosa (
    id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    nombre TEXT COLLATE "C" NOT NULL,   -- comentario
    PRIMARY KEY (id)
);
CREATE UNIQUE INDEX IF NOT EXISTS ix_cosa ON cosa (nombre);
ALTER TABLE cosa ADD COLUMN IF NOT EXISTS nueva DOUBLE PRECISION DEFAULT 0;
ALTER TABLE cosa ENABLE ROW LEVEL SECURITY;
""", encoding="utf-8")
    assert datos.tablas_del_archivo(str(ruta)) == {"cosa": {
        "id": "BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY", "nombre": 'TEXT COLLATE "C" NOT NULL',
        "nueva": "DOUBLE PRECISION DEFAULT 0"}}
    assert datos.indices_del_archivo(str(ruta)) == {"ix_cosa": "cosa"}
    assert datos.tablas_con_rls_del_archivo(str(ruta)) == {"cosa"}


def test_vercel_empaqueta_el_archivo_de_esquema():
    """El esquema viaja con el despliegue: la app lo lee al arrancar (versión, tablas con id) y lo aplica si falta."""
    import json
    incluir = json.loads((RAIZ / "vercel.json").read_text(encoding="utf-8"))["functions"]["app.py"]["includeFiles"]
    assert "datos" in re.search(r"\{([^}]*)\}", incluir).group(1).split(",")
    assert (RAIZ / "datos" / "esquema_postgres.sql").is_file() and (RAIZ / "datos" / "supabase_seguridad.sql").is_file()


def test_psycopg_esta_en_las_dependencias_con_version_fijada():
    for archivo in ("requirements.txt", "requirements.lock"):
        lineas = [x.strip() for x in (RAIZ / archivo).read_text(encoding="utf-8").splitlines()]
        assert any(re.fullmatch(r"psycopg(\[binary\])?==\d+\.\d+\.\d+", x) for x in lineas), archivo
    assert any(re.fullmatch(r"psycopg-binary==\d+\.\d+\.\d+", x.strip())
               for x in (RAIZ / "requirements.lock").read_text(encoding="utf-8").splitlines())


# --------------------------------------------------------------------- contra PostgreSQL de verdad --
@pytest.fixture
def esquema_nuevo():
    """Un esquema temporal aparte, con una conexión directa (como quien aplica el archivo a mano)."""
    import psycopg
    nombre = f"pullex_pruebas_esq_{time.time_ns() % 10**10}"
    with closing(psycopg.connect(PG_URL, autocommit=True, connect_timeout=5)) as con:
        yield nombre, con
    borrar_esquema_de_pruebas(nombre)


def _aplicar(con, esquema, ruta):
    """Como dice la cabecera del archivo: transacción, SET LOCAL search_path y el contenido."""
    con.execute("BEGIN")
    try:
        con.execute(f'SET LOCAL search_path TO "{esquema}"')
        con.execute(open(ruta, encoding="utf-8").read())
        con.execute("COMMIT")
    except Exception:
        con.execute("ROLLBACK")
        raise


@postgres
def test_pg_el_archivo_crea_lo_mismo_que_sqlite_y_es_idempotente(esquema_nuevo, sqlite_de_la_app):
    esquema, con = esquema_nuevo
    _aplicar(con, esquema, datos.RUTA_ESQUEMA)
    con.execute(f'INSERT INTO "{esquema}".usuarios(email, nombre) VALUES (%s, %s)', ("queda@pruebas.local", "No se borra"))
    _aplicar(con, esquema, datos.RUTA_ESQUEMA)                    # segunda vez: no falla ni cambia nada
    assert con.execute(f'SELECT count(*) FROM "{esquema}".esquema_version').fetchone()[0] == 1
    assert con.execute(f'SELECT nombre FROM "{esquema}".usuarios').fetchall() == [("No se borra",)]

    en_sqlite = _esquema_sqlite(sqlite_de_la_app)
    filas = con.execute("SELECT table_name, column_name, data_type, is_nullable, is_identity, collation_name "
                        "FROM information_schema.columns WHERE table_schema=%s ORDER BY table_name, ordinal_position",
                        (esquema,)).fetchall()
    en_pg = {}
    for tabla, col, tipo, nulo, identidad, colacion in filas:
        en_pg.setdefault(tabla, {})[col] = (tipo, nulo, identidad, colacion)
    assert set(en_pg) - SOLO_POSTGRES == set(en_sqlite)
    for tabla, cols in en_sqlite.items():
        assert list(cols) == list(en_pg[tabla]), tabla            # mismas columnas y en el mismo orden
        for col, info in cols.items():
            tipo, nulo, identidad, colacion = en_pg[tabla][col]
            assert tipo == TIPO_INFORMATION_SCHEMA[EQUIVALENTE[info["tipo"]]], (tabla, col)
            assert (identidad == "YES") == info["autoincremental"], (tabla, col)
            assert (nulo == "NO") == (info["notnull"] or bool(info["pk"])), (tabla, col)
            if tipo == "text":
                assert colacion == "C", (tabla, col)
    # llaves primarias
    pk_pg = {}
    for tabla, col in con.execute(
            "SELECT c.relname, a.attname FROM pg_index i JOIN pg_class c ON c.oid=i.indrelid JOIN pg_namespace n ON n.oid=c.relnamespace "
            "JOIN pg_attribute a ON a.attrelid=c.oid AND a.attnum = ANY(i.indkey) WHERE i.indisprimary AND n.nspname=%s", (esquema,)):
        pk_pg.setdefault(tabla, set()).add(col)
    for tabla, cols in en_sqlite.items():
        assert pk_pg.get(tabla, set()) == {c for c, i in cols.items() if i["pk"]}, tabla
    # índices con nombre, y el UNIQUE de calidad_respuestas.mensaje_id
    indices = {n: t for n, t in con.execute("SELECT indexname, tablename FROM pg_indexes WHERE schemaname=%s", (esquema,))}
    for nombre, tabla in _indices_sqlite(sqlite_de_la_app).items():
        assert indices.get(nombre) == tabla, nombre
    unicos = con.execute("SELECT count(*) FROM pg_indexes WHERE schemaname=%s AND tablename='calidad_respuestas' "
                         "AND indexdef LIKE %s", (esquema, "%UNIQUE%(mensaje_id)%")).fetchone()[0]
    assert unicos == 1
    # seguridad por filas activada en todas, sin políticas
    rls = dict(con.execute("SELECT c.relname, c.relrowsecurity FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace "
                           "WHERE n.nspname=%s AND c.relkind='r'", (esquema,)).fetchall())
    assert set(rls) == set(en_pg) and all(rls.values())
    assert con.execute("SELECT count(*) FROM pg_policies WHERE schemaname=%s", (esquema,)).fetchone()[0] == 0


@postgres
def test_pg_el_archivo_se_niega_a_instalarse_en_public(esquema_nuevo):
    import psycopg
    _, con = esquema_nuevo
    for ruta in (datos.RUTA_ESQUEMA, datos.RUTA_SEGURIDAD):
        con.execute("BEGIN")
        with pytest.raises(psycopg.errors.RaiseException, match="fija el esquema de destino"):
            con.execute(open(ruta, encoding="utf-8").read())       # search_path por defecto ("$user", public)
        con.execute("ROLLBACK")
        with pytest.raises(psycopg.errors.RaiseException):
            _aplicar(con, "public", ruta)
    assert con.execute("SELECT to_regclass('public.usuarios') IS NULL AND to_regclass('public.esquema_version') IS NULL"
                       ).fetchone()[0] is True


@postgres
def test_pg_seguridad_de_supabase_revoca_a_anon_y_authenticated(esquema_nuevo):
    """El archivo no falla sin esos roles; con ellos (se crean aquí si el servidor de pruebas lo permite) les quita todo."""
    import psycopg
    esquema, con = esquema_nuevo
    with pytest.raises(psycopg.errors.RaiseException, match="no existe"):
        _aplicar(con, esquema, datos.RUTA_SEGURIDAD)              # antes del esquema: lo dice claro
    _aplicar(con, esquema, datos.RUTA_ESQUEMA)
    existentes = {r[0] for r in con.execute("SELECT rolname FROM pg_roles WHERE rolname IN ('anon','authenticated')")}
    if not existentes:
        _aplicar(con, esquema, datos.RUTA_SEGURIDAD)              # PostgreSQL sin los roles de Supabase: no falla
    creados = []
    try:
        for rol in ("anon", "authenticated"):
            if rol not in existentes:
                try:
                    con.execute(f"CREATE ROLE {rol} NOLOGIN")
                    creados.append(rol)
                except psycopg.errors.InsufficientPrivilege:
                    pytest.skip("el usuario de pruebas no puede crear roles: no se puede comprobar la revocación")
        for rol in ("anon", "authenticated"):                     # como si alguien hubiera expuesto el esquema por error
            con.execute(f'GRANT USAGE ON SCHEMA "{esquema}" TO {rol}')
            con.execute(f'GRANT ALL ON ALL TABLES IN SCHEMA "{esquema}" TO {rol}')
            con.execute(f'GRANT ALL ON ALL SEQUENCES IN SCHEMA "{esquema}" TO {rol}')
        assert con.execute("SELECT has_table_privilege('anon', %s, 'SELECT')", (f"{esquema}.usuarios",)).fetchone()[0] is True
        _aplicar(con, esquema, datos.RUTA_SEGURIDAD)
        _aplicar(con, esquema, datos.RUTA_SEGURIDAD)              # idempotente
        for rol in ("anon", "authenticated"):
            assert con.execute("SELECT has_schema_privilege(%s, %s, 'USAGE')", (rol, esquema)).fetchone()[0] is False
            for tabla in ("usuarios", "mensajes", "apariencia_imagenes", "esquema_version"):
                for permiso in ("SELECT", "INSERT", "UPDATE", "DELETE"):
                    assert con.execute("SELECT has_table_privilege(%s, %s, %s)",
                                       (rol, f"{esquema}.{tabla}", permiso)).fetchone()[0] is False, (rol, tabla, permiso)
    finally:
        for rol in creados:
            con.execute(f'DROP OWNED BY {rol}')
            con.execute(f"DROP ROLE {rol}")


@postgres
def test_pg_con_seguridad_por_filas_otro_rol_no_ve_nada_aunque_tenga_permiso(esquema_nuevo):
    """Lo que protege «RLS sin políticas»: un rol que no es el dueño, aun con SELECT concedido, no lee ninguna fila."""
    import psycopg
    esquema, con = esquema_nuevo
    _aplicar(con, esquema, datos.RUTA_ESQUEMA)
    con.execute(f'INSERT INTO "{esquema}".usuarios(email, nombre) VALUES (%s, %s)', ("privado@pruebas.local", "Privado"))
    rol = f"pullex_pruebas_lector_{time.time_ns() % 10**8}"
    try:
        con.execute(f"CREATE ROLE {rol} NOLOGIN")
    except psycopg.errors.InsufficientPrivilege:
        pytest.skip("el usuario de pruebas no puede crear roles")
    try:
        con.execute(f'GRANT USAGE ON SCHEMA "{esquema}" TO {rol}')
        con.execute(f'GRANT SELECT, INSERT ON ALL TABLES IN SCHEMA "{esquema}" TO {rol}')
        assert con.execute(f'SELECT count(*) FROM "{esquema}".usuarios').fetchone()[0] == 1        # el dueño sí
        con.execute("BEGIN")
        con.execute(f"SET LOCAL ROLE {rol}")
        assert con.execute(f'SELECT count(*) FROM "{esquema}".usuarios').fetchone()[0] == 0
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            con.execute(f'INSERT INTO "{esquema}".usuarios(email) VALUES (%s)', ("intruso@pruebas.local",))
        con.execute("ROLLBACK")
    finally:
        con.execute("ROLLBACK")
        con.execute(f"DROP OWNED BY {rol}")
        con.execute(f"DROP ROLE {rol}")
