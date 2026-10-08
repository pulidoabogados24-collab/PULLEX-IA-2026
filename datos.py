"""
PULLEX IA — Acceso a la base de datos principal (SQLite en local, PostgreSQL en producción)
============================================================================================
La base principal guarda cuentas, conversaciones, progreso de Academia, documentos, tareas y
telemetría. Este módulo decide el motor y entrega una conexión que el resto del código usa igual
en los dos casos (``with closing(db()) as con: con.execute(...); con.commit()``):

* **PostgreSQL** si existe alguna de estas variables, en este orden: ``PULLEX_DATABASE_URL``,
  ``POSTGRES_URL``, ``DATABASE_URL``. Las tablas viven en un esquema propio (``PULLEX_DB_ESQUEMA``,
  por defecto ``pullex``): la base puede compartirse con otros productos sin tocar ``public``.
* **SQLite** (archivo local) si ninguna está definida: desarrollo y pruebas, como siempre.

Si hay una URL de PostgreSQL configurada y la base no responde, la app NO cae a SQLite: quedaría
guardando datos en un archivo temporal sin que nadie lo note. Responde 503 y lo dice en el registro.

No migran y siguen en SQLite: el corpus (fuentes.py) y el catálogo de la Biblioteca (biblioteca.py).

Detalles que importan (docs/18-BASE-DE-DATOS.md):

* Pensado para el *pooler* de Supabase en modo transacción (puerto 6543): sin sentencias preparadas
  y sin estado de sesión. El esquema se fija con ``SET LOCAL search_path`` al empezar cada transacción.
* Las conexiones se reutilizan dentro del proceso (grupo pequeño). Si una conexión guardada murió
  mientras la instancia estaba congelada, se detecta al EMPEZAR la transacción, se abre otra y se
  reintenta una sola vez. A mitad de una transacción nunca se reintenta.
* En PostgreSQL un error dentro de una transacción la deja abortada (en SQLite no). ``commit()`` sobre
  una transacción abortada lanza ``ErrorTransaccion`` en vez de perder los cambios en silencio.
* ``psycopg`` se importa solo cuando hace falta: en modo SQLite la app arranca sin tenerlo instalado.
* Ninguna función de este módulo escribe la URL, el host, el usuario ni la contraseña en el registro.
"""
import functools
import logging
import os
import re
import sqlite3
import threading
import time
from contextlib import closing
from urllib.parse import parse_qsl, urlencode

log = logging.getLogger("pullex.datos")

VARIABLES_URL = ("PULLEX_DATABASE_URL", "POSTGRES_URL", "DATABASE_URL")
VARIABLE_ESQUEMA = "PULLEX_DB_ESQUEMA"
ESQUEMA_POR_DEFECTO = "pullex"
RUTA_ESQUEMA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "datos", "esquema_postgres.sql")
RUTA_SEGURIDAD = os.path.join(os.path.dirname(os.path.abspath(__file__)), "datos", "supabase_seguridad.sql")

TIEMPO_CONEXION_S = 5          # connect_timeout: una base que no responde no deja colgada la función
MAX_LIBRES = 3                 # conexiones abiertas que se guardan para reutilizar (por proceso)
MAX_INACTIVA_S = 300           # una conexión guardada más tiempo que esto se descarta sin probarla
_RE_IDENTIFICADOR = re.compile(r"^[a-z_][a-z0-9_]{0,62}$")
_ESQUEMAS_PROHIBIDOS = ("public", "information_schema")
_HOSTS_LOCALES = ("", "localhost", "127.0.0.1", "::1")
_SSL_EXIGENTES = ("require", "verify-ca", "verify-full")

# Contadores del proceso (sin datos sensibles). Las pruebas los usan para detectar errores de SQL que
# el código haya tragado con un ``except Exception``.
estadisticas = {"conexiones_abiertas": 0, "reconexiones": 0, "errores_sql": 0, "esquema_aplicado": 0}


# ------------------------------------------------------------------------------------ errores --
class ErrorBase(Exception):
    """La base de datos principal no está disponible. app.py lo convierte en una respuesta 503."""


class ErrorConexion(ErrorBase):
    """No se pudo abrir la conexión o se perdió. El mensaje nunca lleva la URL ni credenciales."""


class ErrorConfiguracion(ErrorBase):
    """La configuración de PostgreSQL no sirve (URL ilegible, esquema inválido, falta psycopg)."""


class ErrorEsquema(ErrorBase):
    """Las tablas no están y no se pudieron crear (por ejemplo, el usuario no tiene permiso)."""


class ErrorTransaccion(Exception):
    """Se pidió confirmar una transacción que PostgreSQL ya había abortado por un error anterior."""


def errores_integridad() -> tuple:
    """Clases de «violación de restricción» de los dos motores, para usar en un ``except``."""
    pg = _psycopg(obligatorio=False)
    return (sqlite3.IntegrityError,) + ((pg.IntegrityError,) if pg else ())


def errores_bd() -> tuple:
    """Clases base de error de base de datos de los dos motores, para usar en un ``except``."""
    pg = _psycopg(obligatorio=False)
    return (sqlite3.Error, ErrorBase, ErrorTransaccion) + ((pg.Error,) if pg else ())


# -------------------------------------------------------------------------- psycopg perezoso --
_pg_modulo = None
_pg_intentado = False


def _psycopg(obligatorio: bool = True):
    """Importa psycopg la primera vez que se necesita. En modo SQLite nunca se llama con obligatorio."""
    global _pg_modulo, _pg_intentado
    if _pg_modulo is None and (obligatorio or not _pg_intentado):
        _pg_intentado = True
        try:
            import psycopg
            import psycopg.errors  # noqa: F401 - se usa como psycopg.errors.*
            _pg_modulo = psycopg
        except ImportError:
            _pg_modulo = None
    if _pg_modulo is None and obligatorio:
        raise ErrorConfiguracion("Hay una base PostgreSQL configurada pero falta el controlador: instala las "
                                 "dependencias de requirements.txt (psycopg).")
    return _pg_modulo


# ------------------------------------------------------------------------------ configuración --
def variable_en_uso():
    """Nombre de la variable de entorno que define la URL de PostgreSQL, o None (modo SQLite)."""
    for nombre in VARIABLES_URL:
        if (os.getenv(nombre) or "").strip():
            return nombre
    return None


def es_postgres() -> bool:
    return variable_en_uso() is not None


def motor() -> str:
    return "postgres" if es_postgres() else "sqlite"


def esquema() -> str:
    """Nombre del esquema, validado como identificador simple (va dentro de un ``SET LOCAL``: no puede
    llevar comillas, espacios ni nada que permita inyectar SQL)."""
    nombre = (os.getenv(VARIABLE_ESQUEMA) or ESQUEMA_POR_DEFECTO).strip()
    if not _RE_IDENTIFICADOR.match(nombre) or nombre in _ESQUEMAS_PROHIBIDOS or nombre.startswith("pg_"):
        raise ErrorConfiguracion(
            f"{VARIABLE_ESQUEMA} no es válido: usa solo minúsculas, números y guion bajo, empezando por letra, "
            "y un esquema propio (no «public» ni los del sistema).")
    return nombre


def _es_local(host: str) -> bool:
    partes = [h.strip() for h in (host or "").split(",")] or [""]
    return all(h in _HOSTS_LOCALES or h.startswith("/") for h in partes)


def _parametros_conocidos() -> set:
    """Palabras clave que libpq acepta en una cadena de conexión (las de esta instalación)."""
    pg = _psycopg()
    return {d.keyword.decode() for d in pg.pq.Conninfo.get_defaults()}


def limpiar_url(url: str) -> dict:
    """Convierte la URL en parámetros de conexión, sin lo que libpq no entiende y con TLS si no es local.

    La integración de Supabase con Vercel (y varios ORM) agregan a la URL parámetros que no son de
    PostgreSQL, como ``?workaround=supabase-pooler.vercel``, ``supa=...`` o ``pgbouncer=true``: libpq
    rechaza la conexión completa si los ve. Aquí se descartan. Nunca se registra la URL."""
    pg = _psycopg()
    url = (url or "").strip()
    if re.match(r"^postgres(ql)?://", url, re.I):
        base, _, consulta = url.partition("?")
        consulta, _, _ = consulta.partition("#")
        conocidos = _parametros_conocidos()
        pares = [(k, v) for k, v in parse_qsl(consulta, keep_blank_values=True) if k in conocidos]
        url = base + ("?" + urlencode(pares) if pares else "")
    try:
        params = pg.conninfo.conninfo_to_dict(url)
    except Exception:       # noqa: BLE001 - el mensaje original puede citar la URL: no se propaga
        raise ErrorConfiguracion("La URL de PostgreSQL no se pudo interpretar. Revisa la variable de entorno "
                                 f"({' / '.join(VARIABLES_URL)}).") from None
    if not _es_local(str(params.get("host") or "")):
        if str(params.get("sslmode") or "") not in _SSL_EXIGENTES:
            params["sslmode"] = "require"
    params.setdefault("connect_timeout", TIEMPO_CONEXION_S)
    # Una conexión guardada puede quedar «muda» (sin RST) tras congelarse la instancia: sin este tope el
    # primer envío esperaría el tiempo de TCP del sistema (minutos) antes de fallar y reconectar.
    params.setdefault("tcp_user_timeout", 10000)
    return params


class _Config:
    __slots__ = ("firma", "params", "esquema", "variable", "inicio_tx")

    def __init__(self, firma, params, esq, variable):
        self.firma, self.params, self.esquema, self.variable = firma, params, esq, variable
        self.inicio_tx = f'BEGIN; SET LOCAL search_path TO "{esq}"'


_cerrojo = threading.RLock()
_config_actual = None
_grupo_actual = None


def _firma():
    return tuple(os.getenv(v) or "" for v in VARIABLES_URL) + (os.getenv(VARIABLE_ESQUEMA) or "",)


def _config():
    """Configuración vigente de PostgreSQL (None en modo SQLite). Se recalcula si cambian las variables."""
    global _config_actual, _grupo_actual
    firma = _firma()
    cfg = _config_actual
    if cfg is not None and cfg.firma == firma:
        return cfg
    with _cerrojo:
        if _config_actual is not None and _config_actual.firma == firma:
            return _config_actual
        if _grupo_actual is not None:
            _grupo_actual.cerrar_todo()
            _grupo_actual = None
        variable = variable_en_uso()
        if variable is None:
            _config_actual = None
            return None
        cfg = _Config(firma, limpiar_url(os.getenv(variable)), esquema(), variable)
        _config_actual, _grupo_actual = cfg, _Grupo(cfg)
        return cfg


def reiniciar():
    """Cierra todas las conexiones guardadas y olvida la configuración (como un reinicio del proceso)."""
    global _config_actual, _grupo_actual
    with _cerrojo:
        if _grupo_actual is not None:
            _grupo_actual.cerrar_todo()
        _config_actual = _grupo_actual = None
    tablas_con_id.cache_clear()
    version_del_archivo.cache_clear()


# --------------------------------------------------------------------------- traducción de SQL --
_RE_INSERT = re.compile(r"\s*INSERT\s+INTO\s+([A-Za-z_][A-Za-z0-9_]*)", re.I)
_RE_RETURNING = re.compile(r"\bRETURNING\b", re.I)


def _fin_de_literal(sql: str, i: int) -> int:
    """Posición siguiente al cierre de la cadena o identificador entre comillas que empieza en ``i``."""
    comilla, n, j = sql[i], len(sql), i + 1
    while j < n:
        if sql[j] == comilla:
            if j + 1 < n and sql[j + 1] == comilla:      # comilla doblada: sigue dentro
                j += 2
                continue
            return j + 1
        j += 1
    return n


@functools.lru_cache(maxsize=1024)
def traducir(sql: str) -> str:
    """SQL con marcadores ``?`` (sqlite3) → marcadores ``%s`` (psycopg).

    Los ``?`` dentro de cadenas literales, identificadores entre comillas o comentarios no se tocan.
    Los ``%`` literales se doblan (``%%``) estén donde estén, porque psycopg los interpreta en toda la
    sentencia. No cambia nada más: las consultas se escriben de forma que valgan en los dos motores."""
    salida, i, n = [], 0, len(sql)
    while i < n:
        c = sql[i]
        if c in ("'", '"'):
            j = _fin_de_literal(sql, i)
        elif c == "-" and sql.startswith("--", i):
            j = sql.find("\n", i)
            j = n if j < 0 else j
        elif c == "/" and sql.startswith("/*", i):
            j = sql.find("*/", i + 2)
            j = n if j < 0 else j + 2
        else:
            salida.append("%s" if c == "?" else "%%" if c == "%" else c)
            i += 1
            continue
        salida.append(sql[i:j].replace("%", "%%"))
        i = j
    return "".join(salida)


@functools.lru_cache(maxsize=1024)
def _preparar(sql: str) -> tuple:
    """(sql para psycopg, devuelve_id): a los INSERT sobre tablas con ``id`` autogenerado se les agrega
    ``RETURNING id`` para que ``cursor.lastrowid`` funcione como en sqlite3."""
    m = _RE_INSERT.match(sql)
    if m and m.group(1).lower() in tablas_con_id() and not _RE_RETURNING.search(sql):
        return traducir(sql.rstrip().rstrip(";")) + " RETURNING id", True
    return traducir(sql), False


def _adaptar(parametros):
    """Parámetros como los acepta PostgreSQL: los booleanos van como 0/1 (las columnas son enteras, como en
    SQLite) y se quita el carácter NUL de los textos (PostgreSQL no lo admite; SQLite sí)."""
    if parametros is None:
        return ()
    if isinstance(parametros, dict):
        raise TypeError("la capa de datos solo admite marcadores «?» con una lista o tupla de valores")
    salida = []
    for p in parametros:
        if isinstance(p, bool):
            p = int(p)
        elif isinstance(p, str) and "\x00" in p:
            p = p.replace("\x00", "")
        salida.append(p)
    return tuple(salida)


# ------------------------------------------------------------------------------ esquema (archivo) --
_RE_VERSION = re.compile(r"^--\s*version\s*:\s*(\d+)\s*$", re.I | re.M)
_RE_TABLA = re.compile(r"CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+([a-z_][a-z0-9_]*)\s*\((.*?)\n\);", re.I | re.S)
_RE_ADD = re.compile(r"ALTER\s+TABLE\s+([a-z_][a-z0-9_]*)\s+ADD\s+COLUMN\s+IF\s+NOT\s+EXISTS\s+([a-z_][a-z0-9_]*)\s+([^;]+);",
                     re.I)
_RE_INDICE = re.compile(r"CREATE\s+(?:UNIQUE\s+)?INDEX\s+IF\s+NOT\s+EXISTS\s+([a-z_][a-z0-9_]*)\s+ON\s+([a-z_][a-z0-9_]*)",
                        re.I)
_RE_RLS = re.compile(r"ALTER\s+TABLE\s+([a-z_][a-z0-9_]*)\s+ENABLE\s+ROW\s+LEVEL\s+SECURITY", re.I)


def leer_esquema(ruta: str = None) -> str:
    with open(ruta or RUTA_ESQUEMA, encoding="utf-8") as f:
        return f.read()


@functools.lru_cache(maxsize=1)
def version_del_archivo() -> int:
    """Versión declarada en la cabecera del archivo de esquema (``-- version: N``)."""
    m = _RE_VERSION.search(leer_esquema())
    if not m:
        raise ErrorEsquema("datos/esquema_postgres.sql no declara su versión (línea «-- version: N»).")
    return int(m.group(1))


def tablas_del_archivo(ruta: str = None) -> dict:
    """{tabla: {columna: definición}} tal como queda tras aplicar el archivo (CREATE TABLE más los
    ADD COLUMN). Lo usan la prueba que compara los dos esquemas y ``tablas_con_id``."""
    texto = re.sub(r"--[^\n]*", "", leer_esquema(ruta))
    tablas = {}
    for nombre, cuerpo in _RE_TABLA.findall(texto):
        columnas = {}
        for linea in cuerpo.split("\n"):
            linea = linea.strip().rstrip(",")
            if not linea or re.match(r"(PRIMARY\s+KEY|UNIQUE|CONSTRAINT|CHECK|FOREIGN\s+KEY)\b", linea, re.I):
                continue
            col, _, definicion = linea.partition(" ")
            columnas[col.lower()] = " ".join(definicion.split())
        tablas[nombre.lower()] = columnas
    for tabla, col, definicion in _RE_ADD.findall(texto):
        tablas[tabla.lower()].setdefault(col.lower(), " ".join(definicion.split()))
    return tablas


def indices_del_archivo(ruta: str = None) -> dict:
    """{índice: tabla} declarados en el archivo."""
    texto = re.sub(r"--[^\n]*", "", leer_esquema(ruta))
    return {i.lower(): t.lower() for i, t in _RE_INDICE.findall(texto)}


def tablas_con_rls_del_archivo(ruta: str = None) -> set:
    texto = re.sub(r"--[^\n]*", "", leer_esquema(ruta))
    return {t.lower() for t in _RE_RLS.findall(texto)}


@functools.lru_cache(maxsize=1)
def tablas_con_id() -> frozenset:
    """Tablas cuyo ``id`` lo genera la base (identidad): sus INSERT devuelven el id nuevo."""
    return frozenset(t for t, cols in tablas_del_archivo().items()
                     if "GENERATED" in cols.get("id", "").upper())


# -------------------------------------------------------------------------------------- filas --
class Fila:
    """Fila de resultado con la misma forma que ``sqlite3.Row``: acceso por nombre y por índice,
    ``keys()``, ``len()``, iteración por valores y ``dict(fila)``."""
    __slots__ = ("_nombres", "_indice", "_valores")

    def __init__(self, nombres, indice, valores):
        self._nombres, self._indice, self._valores = nombres, indice, valores

    def __getitem__(self, clave):
        if isinstance(clave, (int, slice)):
            return self._valores[clave]
        try:
            return self._valores[self._indice[clave]]
        except KeyError:
            pass
        try:        # sqlite3.Row no distingue mayúsculas en el nombre; PostgreSQL devuelve minúsculas
            return self._valores[self._indice[str(clave).lower()]]
        except KeyError:
            raise IndexError(f"No hay una columna llamada {clave!r}") from None

    def keys(self):
        return list(self._nombres)

    def __iter__(self):
        return iter(self._valores)

    def __len__(self):
        return len(self._valores)

    def __eq__(self, otra):
        if isinstance(otra, Fila):
            return self._nombres == otra._nombres and tuple(self._valores) == tuple(otra._valores)
        return NotImplemented

    def __hash__(self):
        return hash((self._nombres, tuple(self._valores)))

    def __repr__(self):
        return "Fila(" + ", ".join(f"{n}={v!r}" for n, v in zip(self._nombres, self._valores)) + ")"


def _fabrica_filas(cursor):
    descripcion = cursor.description
    if descripcion is None:
        return tuple
    nombres = tuple(c.name for c in descripcion)
    indice = {}
    for i, nombre in enumerate(nombres):
        indice.setdefault(nombre, i)        # nombre repetido: gana la primera columna, como en sqlite3.Row

    def hacer(valores):
        return Fila(nombres, indice, tuple(valores))
    return hacer


class Cursor:
    """Resultado de ``execute`` con lo que el código usa de un cursor de sqlite3."""
    __slots__ = ("_cur", "lastrowid")

    def __init__(self, cur, lastrowid=None):
        self._cur, self.lastrowid = cur, lastrowid

    @property
    def rowcount(self):
        return self._cur.rowcount

    @property
    def description(self):
        return self._cur.description

    def _hay_filas(self):
        return self._cur.description is not None

    def fetchone(self):
        return self._cur.fetchone() if self._hay_filas() else None

    def fetchall(self):
        return self._cur.fetchall() if self._hay_filas() else []

    def fetchmany(self, n=1):
        return self._cur.fetchmany(n) if self._hay_filas() else []

    def __iter__(self):
        return iter(self._cur) if self._hay_filas() else iter(())

    def close(self):
        self._cur.close()


# ----------------------------------------------------------------------------- conexión cruda --
def _motivo(e) -> str:
    """Causa de un fallo de conexión en palabras fijas. El mensaje de libpq nombra el servidor y a veces
    el usuario, así que nunca se copia al registro ni a una respuesta."""
    texto = str(e).lower()
    codigo = getattr(e, "sqlstate", None)
    if "timeout" in texto or "timed out" in texto:
        causa = "se agotó el tiempo de espera"
    elif "password authentication failed" in texto or codigo in ("28P01", "28000"):
        causa = "el servidor rechazó el usuario o la contraseña"
    elif "could not translate host name" in texto or "name or service not known" in texto or "nodename nor servname" in texto:
        causa = "no se pudo resolver el nombre del servidor"
    elif "connection refused" in texto:
        causa = "el servidor rechazó la conexión"
    elif "ssl" in texto or "tls" in texto or "certificate" in texto:
        causa = "falló la negociación TLS"
    elif "too many" in texto or codigo in ("53300", "08004"):
        causa = "el servidor no admite más conexiones en este momento"
    elif "terminating connection" in texto or "server closed the connection" in texto or "connection is closed" in texto \
            or "connection is lost" in texto or "eof detected" in texto or codigo in ("57P01", "57P02", "57P03", "08006", "08003"):
        causa = "el servidor cerró la conexión"
    else:
        causa = "error de conexión"
    return f"{causa} [{type(e).__name__}{' ' + codigo if codigo else ''}]"


def _abrir(cfg):
    """Abre una conexión nueva en modo autocommit (las transacciones las abre la envoltura con BEGIN),
    sin sentencias preparadas (el pooler en modo transacción no las conserva entre transacciones)."""
    pg = _psycopg()
    try:
        con = pg.connect(autocommit=True, prepare_threshold=None, row_factory=_fabrica_filas, **cfg.params)
    except pg.Error as e:
        motivo = _motivo(e)
        log.error("No hay conexión con la base de datos PostgreSQL: %s. La app responde 503 hasta que vuelva; "
                  "no se usa SQLite como reemplazo. Variable en uso: %s.", motivo, cfg.variable)
        raise ErrorConexion(motivo) from None
    con.adapters.register_loader("numeric", _cargadores()[0])
    con.adapters.register_loader("bool", _cargadores()[1])
    estadisticas["conexiones_abiertas"] += 1
    return con


@functools.lru_cache(maxsize=1)
def _cargadores():
    pg = _psycopg()

    class Numerico(pg.adapt.Loader):
        """``numeric`` (AVG, SUM de enteros grandes) como en SQLite: float si trae decimales, int si no."""

        def load(self, dato):
            texto = bytes(dato)
            return float(texto) if (b"." in texto or b"e" in texto.lower() or b"n" in texto.lower()) else int(texto)

    class Booleano(pg.adapt.Loader):
        """Una expresión booleana (``x IS NULL``, ``EXISTS``) se lee como 0/1, igual que en SQLite."""

        def load(self, dato):
            return 1 if bytes(dato) == b"t" else 0

    return Numerico, Booleano


class _Grupo:
    """Grupo pequeño de conexiones abiertas para reutilizar dentro del proceso. Se guardan como máximo
    ``MAX_LIBRES``; si en un momento hacen falta más (peticiones simultáneas) se abren y, al devolverlas,
    las que sobran se cierran. Nunca bloquea esperando una conexión."""

    def __init__(self, cfg):
        self.cfg = cfg
        self._libres = []            # [(conexión, momento en que se devolvió)], la más reciente al final
        self._cerrojo = threading.Lock()

    def tomar(self):
        ahora = time.monotonic()
        while True:
            with self._cerrojo:
                par = self._libres.pop() if self._libres else None
            if par is None:
                return _abrir(self.cfg)
            con, devuelta = par
            if con.closed or con.broken or ahora - devuelta > MAX_INACTIVA_S:
                _cerrar_en_silencio(con)
                continue
            return con

    def nueva(self):
        return _abrir(self.cfg)

    def devolver(self, con):
        if con is None or con.closed or con.broken:
            _cerrar_en_silencio(con)
            return
        with self._cerrojo:
            if len(self._libres) < MAX_LIBRES:
                self._libres.append((con, time.monotonic()))
                return
        _cerrar_en_silencio(con)

    def descartar_libres(self):
        with self._cerrojo:
            libres, self._libres = self._libres, []
        for con, _ in libres:
            _cerrar_en_silencio(con)

    cerrar_todo = descartar_libres

    def libres(self) -> int:
        with self._cerrojo:
            return len(self._libres)


def _cerrar_en_silencio(con):
    try:
        if con is not None:
            con.close()
    except Exception:       # noqa: BLE001 - cerrar una conexión rota no debe romper nada más
        pass


# ---------------------------------------------------------------------------------- envoltura --
class ConexionPG:
    """Conexión a PostgreSQL con la interfaz de ``sqlite3.Connection`` que usa la app.

    La conexión real se toma del grupo al ejecutar la primera sentencia y se devuelve en ``close()``.
    Cada transacción empieza con ``BEGIN; SET LOCAL search_path TO <esquema>`` (un solo viaje)."""
    motor = "postgres"

    def __init__(self, grupo):
        self._grupo = grupo
        self._pg = None
        self._en_tx = False
        self._abortada = False
        self._cerrada = False

    # -- transacciones --
    def _empezar(self):
        pg = _psycopg()
        inicio = self._grupo.cfg.inicio_tx
        if self._pg is None:
            self._pg = self._grupo.tomar()
        try:
            self._pg.execute(inicio)
        except (pg.OperationalError, pg.InterfaceError) as e:
            # La conexión guardada estaba muerta (instancia congelada, el pooler la cerró). Todavía no se
            # ha ejecutado nada de esta transacción: es el único punto donde reintentar es seguro.
            _cerrar_en_silencio(self._pg)
            self._pg = None
            self._grupo.descartar_libres()       # las otras guardadas tienen la misma edad: fuera también
            estadisticas["reconexiones"] += 1
            log.warning("La conexión guardada a PostgreSQL no servía (%s): se abre otra y se reintenta una vez.",
                        _motivo(e))
            self._pg = self._grupo.nueva()
            try:
                self._pg.execute(inicio)
            except (pg.OperationalError, pg.InterfaceError) as e2:
                motivo = _motivo(e2)
                _cerrar_en_silencio(self._pg)
                self._pg = None
                log.error("No se pudo empezar una transacción en PostgreSQL tras reconectar: %s.", motivo)
                raise ErrorConexion(motivo) from None
        self._en_tx, self._abortada = True, False

    def _terminar(self, orden: str):
        pg = _psycopg()
        try:
            self._pg.execute(orden)
        except (pg.OperationalError, pg.InterfaceError) as e:
            motivo = _motivo(e)
            _cerrar_en_silencio(self._pg)
            self._pg = None
            if orden == "COMMIT":
                # Nunca se reintenta un COMMIT: no se sabe si el servidor alcanzó a confirmarlo.
                log.error("Se perdió la conexión a PostgreSQL al confirmar una transacción: %s.", motivo)
                raise ErrorConexion(motivo) from None
        finally:
            self._en_tx, self._abortada = False, False

    def commit(self):
        if self._cerrada or not self._en_tx:
            return
        if self._abortada:
            self._terminar("ROLLBACK")
            raise ErrorTransaccion("La transacción quedó abortada por un error anterior y no se guardó nada. "
                                   "En PostgreSQL no se puede seguir usando la conexión tras un error sin deshacer.")
        self._terminar("COMMIT")

    def rollback(self):
        if self._cerrada or not self._en_tx:
            return
        self._terminar("ROLLBACK")

    def close(self):
        if self._cerrada:
            return
        try:
            if self._en_tx and self._pg is not None:
                self._terminar("ROLLBACK")          # lo no confirmado se deshace, como al cerrar en sqlite3
        finally:
            self._cerrada = True
            con, self._pg = self._pg, None
            if con is not None:
                self._grupo.devolver(con)

    def __del__(self):
        try:
            self.close()
        except Exception:       # noqa: BLE001
            pass

    def __enter__(self):
        return self

    def __exit__(self, tipo, valor, traza):
        # Igual que sqlite3: el bloque ``with con:`` confirma o deshace, pero no cierra.
        if tipo is None:
            self.commit()
        else:
            self.rollback()
        return False

    # -- sentencias --
    def _ejecutar(self, sql, parametros=None):
        pg = _psycopg()
        if self._cerrada:
            raise pg.InterfaceError("la conexión ya se cerró")
        if not self._en_tx:
            self._empezar()
        try:
            return self._pg.execute(sql, parametros)
        except pg.Error as e:
            self._abortada = True
            estadisticas["errores_sql"] += 1
            if isinstance(e, (pg.OperationalError, pg.InterfaceError)) and (self._pg.closed or self._pg.broken):
                motivo = _motivo(e)
                log.error("Se perdió la conexión a PostgreSQL a mitad de una transacción (no se reintenta): %s.", motivo)
                raise ErrorConexion(motivo) from None
            raise

    def execute(self, sql, parametros=None):
        sql_pg, devuelve_id = _preparar(sql)
        cur = self._ejecutar(sql_pg, _adaptar(parametros))
        if devuelve_id:
            fila = cur.fetchone()
            return Cursor(cur, fila[0] if fila else None)
        return Cursor(cur)

    def executemany(self, sql, secuencia):
        ultimo = None
        for parametros in secuencia:
            ultimo = self.execute(sql, parametros)
        return ultimo

    def executescript(self, guion: str):
        """Varias sentencias sin parámetros, en UNA transacción que se confirma al final (en sqlite3
        ``executescript`` también deja confirmado lo anterior y lo que ejecuta)."""
        if self._en_tx:
            self.commit()
        try:
            self._ejecutar(guion)
        except Exception:
            self.rollback()
            raise
        self.commit()


def conectar(ruta_sqlite: str = "pullex.db"):
    """Una conexión a la base principal: PostgreSQL si está configurado; si no, el archivo SQLite."""
    cfg = _config()
    if cfg is None:
        con = sqlite3.connect(ruta_sqlite)
        con.row_factory = sqlite3.Row
        return con
    return ConexionPG(_grupo_actual)


# ------------------------------------------------------------------------- esquema (aplicación) --
def asegurar_esquema() -> dict:
    """Solo PostgreSQL. Comprueba con UNA consulta si ``esquema_version`` está al día y, solo si no lo
    está, aplica datos/esquema_postgres.sql (idempotente) dentro de una transacción con un candado, para
    que dos instancias que arrancan a la vez no lo apliquen al mismo tiempo."""
    pg = _psycopg()
    cfg = _config()
    if cfg is None:
        return {"motor": "sqlite", "aplicado": False}
    esperada = version_del_archivo()

    def version_actual(con):
        try:
            fila = con._pg.execute("SELECT MAX(version) FROM esquema_version").fetchone()
            return int(fila[0] or 0)
        except pg.errors.UndefinedTable:
            return None

    with closing(conectar()) as con:
        con._empezar()
        actual = version_actual(con)
        if actual is not None and actual >= esperada:
            return {"motor": "postgres", "aplicado": False, "version": actual}
        con.rollback()      # si la tabla no existía, la consulta dejó abortada la transacción: se empieza otra
        log.info("El esquema «%s» de PostgreSQL está en la versión %s; se aplica datos/esquema_postgres.sql (versión %s).",
                 cfg.esquema, actual or 0, esperada)
        try:
            con._empezar()
            # Candado de transacción (se suelta solo al confirmar; no deja estado de sesión en el pooler). Si otra
            # instancia lo aplicó mientras esperábamos, volver a aplicarlo no cambia nada: el archivo es idempotente.
            con._pg.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", ("pullex_ia.esquema." + cfg.esquema,))
            con._pg.execute(leer_esquema())
            con.commit()
        except pg.Error as e:
            rota = con._pg is None or con._pg.closed or con._pg.broken
            con.rollback()
            if rota:
                raise ErrorConexion(_motivo(e)) from None
            codigo = getattr(e, "sqlstate", None) or type(e).__name__
            log.error("No se pudo aplicar el esquema de PostgreSQL (%s). Si el usuario de la base no puede crear "
                      "tablas, aplica datos/esquema_postgres.sql a mano (docs/18-BASE-DE-DATOS.md).", codigo)
            raise ErrorEsquema(f"no se pudo aplicar el esquema ({codigo})") from None
    estadisticas["esquema_aplicado"] += 1
    return {"motor": "postgres", "aplicado": True, "version": esperada}


# ---------------------------------------------------------------------------- estado (operador) --
def estado(ruta_sqlite: str = None, probar: bool = True) -> dict:
    """Qué base está en uso y si responde, para /salud y el panel de administración.
    No incluye servidor, usuario ni contraseña: solo el motor, el nombre del esquema y la variable."""
    en_vercel = bool(os.getenv("VERCEL"))
    if not es_postgres():
        temporal = en_vercel or str(ruta_sqlite or "").startswith("/tmp/")
        return {
            "motor": "sqlite", "nombre": "SQLite (archivo local)", "conecta": True, "persistente": not temporal,
            "detalle": ("Base temporal: en este servidor el archivo se borra en cada reinicio o despliegue. Las cuentas, "
                        "conversaciones y progreso NO se conservan. Configura PostgreSQL (docs/18-BASE-DE-DATOS.md).")
            if temporal else
            "Archivo local. Los datos se conservan mientras el disco de este servidor sea persistente.",
        }
    salida = {"motor": "postgres", "nombre": "PostgreSQL", "conecta": False, "persistente": True,
              "variable": variable_en_uso(), "esquema": None, "esquema_al_dia": None}
    try:
        cfg = _config()
        salida["esquema"] = cfg.esquema
        salida["tls"] = str(cfg.params.get("sslmode") or "") in _SSL_EXIGENTES
        if probar:
            with closing(conectar()) as con:
                con._empezar()
                try:
                    fila = con._pg.execute("SELECT MAX(version) FROM esquema_version").fetchone()
                    salida["esquema_al_dia"] = int(fila[0] or 0) >= version_del_archivo()
                except (_psycopg().ProgrammingError, _psycopg().DataError):     # no existe la tabla o no hay permiso
                    salida["esquema_al_dia"] = False
        if not probar:
            salida["conecta"] = None
            salida["detalle"] = "Configurada (sin comprobar la conexión en esta consulta)."
            return salida
        salida["conecta"] = True
        if salida["esquema_al_dia"] is False:
            salida["detalle"] = (f"Conecta, pero faltan las tablas en el esquema «{cfg.esquema}» o están desactualizadas. "
                                 "Aplica datos/esquema_postgres.sql (docs/18-BASE-DE-DATOS.md).")
        else:
            salida["detalle"] = (f"Conectada. Los datos se conservan entre despliegues (esquema «{cfg.esquema}»"
                                 + (", conexión cifrada" if salida["tls"] else ", conexión local sin cifrar") + ").")
    except ErrorBase as e:
        salida["detalle"] = f"No conecta: {e}. La app responde 503 en lo que use la base hasta que vuelva."
    except Exception as e:      # noqa: BLE001 - el diagnóstico nunca tumba la pantalla que lo muestra
        salida["detalle"] = f"No conecta: error inesperado ({type(e).__name__})."
    return salida
