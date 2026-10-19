# 18 · Base de datos principal

Actualizado el 13 de octubre de 2026 (correcciones de la auditoría: BD-01, BD-05 a BD-18).

## Qué resuelve

En Vercel el disco es de solo lectura salvo `/tmp`, y `/tmp` se borra en cada arranque en frío y no se
comparte entre instancias. Con SQLite las cuentas, las conversaciones y el progreso se perdían en cada
despliegue: por eso «no dejaba ingresar» con una cuenta creada el día anterior.

Desde esta versión la **base principal** puede vivir en PostgreSQL (Supabase). El código de la app no cambia
de forma: sigue usando `with closing(db()) as con: con.execute(...); con.commit()`. Quien decide el motor es
`datos.py`.

| Qué | Dónde vive | Por qué |
|---|---|---|
| Cuentas, conversaciones, Academia, documentos, taller, perfiles, telemetría | PostgreSQL en producción; SQLite en local y en pruebas | Son los datos que no se pueden perder |
| Corpus de fuentes (`corpus/corpus.db`) | SQLite, de solo lectura, viaja con el despliegue | Es un índice de texto (FTS5) que se genera fuera |
| Catálogo de la Biblioteca | SQLite en `/tmp` cuando corre en Vercel | Se reconstruye del inventario al arrancar |

## Cómo se elige el motor

`datos.py` usa PostgreSQL si existe alguna de estas variables de entorno, en este orden:

1. `PULLEX_DATABASE_URL`
2. `POSTGRES_URL` (la que crea la integración de Supabase con Vercel)
3. `DATABASE_URL`

Si no hay ninguna, usa el archivo SQLite de siempre (`PULLEX_DB`, o `pullex.db`).

Las tablas van en un esquema propio, `pullex` por defecto (`PULLEX_DB_ESQUEMA` para cambiarlo). La app nunca
escribe en `public`: la base se puede compartir con otros productos sin mezclarse.

**Si hay URL y la base no responde, la app no cae a SQLite.** Guardaría cuentas en un archivo temporal sin
que nadie lo notara. Responde 503 con un mensaje claro, lo deja en el registro (sin URL ni credenciales) y
reintenta en la siguiente petición.

## La URL correcta para Vercel

Usa la del **pooler en modo transacción** de Supabase (puerto 6543). Es la pensada para funciones sin
servidor: muchas instancias que abren y cierran conexiones.

- La app no usa sentencias preparadas ni estado de sesión, que ese modo no conserva.
- El esquema se fija con `SET LOCAL search_path` al empezar cada transacción.
- Los parámetros que libpq no entiende (`?workaround=supabase-pooler.vercel`, `pgbouncer=true`, `supa=…`) se
  descartan solos.
- Si el servidor no es local, la conexión exige TLS (`sslmode=require` como mínimo). Con
  `PULLEX_DB_SSLROOTCERT=/ruta/al/certificado-raiz.crt` (el certificado raíz que Supabase publica en el panel
  del proyecto, empaquetado con el despliegue) se usa `sslmode=verify-full`: además de cifrar, se verifica el
  certificado y el nombre del servidor. Si la ruta no existe, la app responde 503 y lo dice en el registro.
- Cada transacción lleva `SET LOCAL statement_timeout` (`PULLEX_DB_TIMEOUT_MS`, por defecto 15000; `0` sin
  límite). Al aplicar el esquema el tope es de 120 s.
- Grupo de conexiones: como mucho `PULLEX_DB_MAX_CONEXIONES` (por defecto 5) en uso a la vez por proceso. Si
  están todas ocupadas, la petición espera hasta `PULLEX_DB_ESPERA_S` (por defecto 10 s) y luego responde 503.
  Solo vuelve al grupo una conexión fuera de transacción (IDLE); las demás se cierran.

La URL lleva la contraseña de la base: va **solo** como variable de entorno en Vercel, marcada como sensible.
Nunca en el repositorio, en un documento ni en un mensaje.

## El esquema

- `datos/esquema_postgres.sql`: las 18 tablas más `esquema_version` (versión 2). Es idempotente.
- `datos/supabase_seguridad.sql`: quita a los roles de la API de Supabase (`anon`, `authenticated` y
  `service_role`) todo permiso sobre el esquema y los privilegios por defecto que el usuario que lo aplica les
  daría sobre lo que cree después en él. **La app lo aplica sola**, en la misma transacción y justo después del
  esquema, cada vez que sube la versión. Si falla (por ejemplo, porque el usuario no es dueño del esquema), el
  esquema queda aplicado, se registra el error y hay que aplicarlo a mano. No toca los privilegios por defecto
  globales: la base se comparte con otros productos.
- Todas las tablas tienen seguridad por filas activada y sin políticas: solo las ve el dueño (el usuario con
  que se conecta la app). **Si la app se conecta con un usuario que no es el dueño, ve 0 filas sin ningún
  error** (parecería que no hay cuentas). El panel de administración lo avisa (campo `aviso` de la ficha «Base
  de datos»).
- Sin claves foráneas todavía (BD-13). Agregarlas exige primero limpiar las filas huérfanas que ya existan y
  coordinarlas con el borrado de cuenta (que borra hijos antes que padres). Mientras tanto hay índices en las
  columnas de enlace (`ix_mintentos_caso`, `ix_mensajes_conv`…).

Versión 2 (13 de octubre de 2026): tabla `limites` (límites de intentos compartidos entre instancias),
`usuarios.acepto_politica_version` y `usuarios.acepto_politica_en` (aceptación de la política de datos),
`mensajes.continuaciones` e índice `ix_mintentos_caso`. Al desplegarla, la primera instancia que arranca la
aplica sola (`ALTER TABLE … ADD COLUMN IF NOT EXISTS`: no borra ni reescribe datos).
- El esquema `pullex` **no** debe agregarse a los «esquemas expuestos» de la API de Supabase.

La app comprueba con una consulta, al arrancar, si `esquema_version` está al día. Solo si no lo está aplica
el archivo, dentro de una transacción con candado. Para aplicarlo a mano:

```sql
BEGIN;
SET LOCAL search_path TO pullex;
-- pegar aquí datos/esquema_postgres.sql
COMMIT;
```

### Cambiar el esquema

1. Cambia la tabla en SQLite (en `app.py` o en el módulo dueño de la tabla).
2. Agrega la columna en su `CREATE TABLE` de `datos/esquema_postgres.sql` y un
   `ALTER TABLE … ADD COLUMN IF NOT EXISTS …` en «Cambios posteriores».
3. Sube el número de `-- version:` y agrega su fila al final.

`tests/test_esquema_bd.py` compara los dos esquemas: si una columna está en un lado y no en el otro, falla.

## Diferencias entre motores que ya están resueltas

- Marcadores `?` → `%s`, sin tocar los que están dentro de cadenas o comentarios.
- `cursor.lastrowid`: a los `INSERT` sobre tablas con `id` autogenerado se les agrega `RETURNING id`.
- Filas con acceso por nombre y por índice, como `sqlite3.Row`.
- `INSERT OR REPLACE` / `INSERT OR IGNORE` se reescribieron como `ON CONFLICT`, que vale en los dos.
- Booleanos como 0/1 y `numeric` como número de Python, igual que en SQLite.
- En PostgreSQL un error deja abortada la transacción. `commit()` sobre una transacción abortada lanza
  `ErrorTransaccion` en vez de perder los cambios en silencio.

- Orden de los nulos: SQLite los pone primero en orden ascendente y al final en descendente; PostgreSQL al
  revés. Las consultas que ordenan por columnas que pueden ser nulas lo dicen explícito (`NULLS FIRST` en
  ascendente, `NULLS LAST` en descendente), igual en los dos motores.
- Ids fuera de rango (≤ 0 o mayores que 2^63−1) en las rutas con `{id}`: 404 antes de consultar, en los dos
  motores (antes SQLite respondía 500).

Regla al escribir consultas nuevas: SQL que valga en los dos motores. Nada de `INSERT OR …`, `PRAGMA`,
`rowid` ni funciones propias de SQLite en la base principal. Para «insertar si no existe» usa
`INSERT … ON CONFLICT (…) DO NOTHING` o `DO UPDATE`, nunca «SELECT y luego INSERT» (con dos peticiones a la
vez, la segunda choca con la llave en PostgreSQL).

`datos.traducir` rechaza (`ValueError`) lo que no sabe traducir sin riesgo: cadenas con dólar (`$$…$$`),
cadenas con escapes (`E'…'`) y los operadores de jsonb `?`, `?|` y `?&`. Para jsonb usa
`jsonb_exists(col, ?)`, `jsonb_exists_any(col, ?)` y `jsonb_exists_all(col, ?)`. Los archivos `datos/*.sql`
sí usan `DO $$ … $$`: se ejecutan crudos, sin pasar por la traducción.

## Derechos del titular: exportar y eliminar la cuenta

- `GET /api/cuenta/exportar`: descarga en JSON todo lo que la base principal guarda de la cuenta (sin la sal ni
  el hash de la contraseña ni los tokens de un solo uso).
- `POST /api/cuenta/eliminar` con `{"clave": "…"}`: borra la cuenta y todos sus datos en una sola transacción.
  La cuenta del administrador principal (`PULLEX_ADMIN_EMAIL`) no se puede borrar por esta vía.
- La lista de tablas y cómo se encuentran las filas de una persona está en `app.py`, `TABLAS_DEL_USUARIO`.
  **Si agregas una tabla con datos de personas, agrégala ahí** (o en `TABLAS_SIN_TITULAR` si no los tiene):
  `tests/test_seguridad_datos.py` descubre las tablas de la base y falla si una no está en ninguna de las dos.
- Lo que quede en las copias de seguridad se borra cuando esas copias vencen (ver abajo). Plazos de
  conservación y lo que deba guardarse por obligación legal: **pendiente de revisión jurídica**.

## Copias de seguridad y restauración

El respaldo automático de Supabase es del proyecto entero: restaurarlo pisaría también los datos del otro
producto que comparte la base. Por eso PULLEX IA respalda **solo su esquema** con `pg_dump`.

**Qué conexión usar.** `PULLEX_DATABASE_URL_DIRECTA` = la conexión **directa** de Supabase (puerto 5432,
usuario dueño del esquema), no la del pooler (6543): `pg_dump` necesita una sesión propia. El cliente
(`pg_dump`/`pg_restore`) debe ser de la misma versión mayor que el servidor o posterior.

**Copia diaria.**

```bash
export PULLEX_DATABASE_URL_DIRECTA='postgresql://…:5432/postgres'   # nunca en el repositorio
export PULLEX_RESPALDO_CLAVE='frase larga y aleatoria'             # cifra la copia con gpg (AES-256)
scripts/respaldar_bd.sh /ruta/privada/respaldos
```

Deja `pullex_pullex_AAAAMMDDTHHMMSSZ.dump.gpg` (formato custom de `pg_dump`, cifrado) y su `.sha256`, con
permisos solo para el dueño (`umask 077`). Sin `PULLEX_RESPALDO_CLAVE` deja el `.dump` sin cifrar: úsalo solo
en un equipo propio y cifrado.

Automatizado: `.github/workflows/respaldo-bd.yml` hace la copia cifrada y la sube como artefacto de GitHub
con 5 días de retención. **Está desactivado**: solo corre a mano. Para activarlo, crea los secretos
`PULLEX_DATABASE_URL_DIRECTA` y `PULLEX_RESPALDO_CLAVE` en el repositorio. Las acciones están fijadas por SHA.
Antes de descomentar `schedule`, verificar configuración, custodia de claves, destino externo y restauración
de una copia representativa. Una prueba con datos sintéticos no acredita recuperar la última copia operativa.

**Dónde guardarla.** El artefacto de GitHub es de paso, no el archivo de respaldos. Guarda las copias cifradas
fuera de Supabase y fuera de GitHub (por ejemplo, una carpeta privada de Google Drive o un almacenamiento de
objetos con acceso restringido), con esta retención sugerida: diarias 7 días, semanales 4 semanas, mensuales
6 meses (confirmar con la revisión jurídica). La frase de cifrado se guarda aparte (gestor de contraseñas del
dueño): sin ella la copia no se puede restaurar, y con ella cualquiera puede leer las cuentas.

**Restaurar.**

```bash
export PULLEX_RESPALDO_CLAVE='…'                        # si la copia está cifrada
scripts/restaurar_bd.sh respaldos/pullex_pullex_….dump.gpg \
    --destino-url 'postgresql://…:5432/postgres' --esquema pullex          # pregunta y exige escribir «pullex»
```

- La base de destino se pasa siempre explícita (`--destino-url` o `PULLEX_RESTAURAR_URL`); el script nunca
  usa la URL de la app por su cuenta.
- Si el esquema de destino ya existe, **se detiene sin borrar nada**. Para reemplazarlo hay que agregar
  `--forzar` (y confirmar). Todo va en una sola transacción: si algo falla, la base queda como estaba.
- `--esquema-destino otro_nombre` restaura con otro nombre (útil para revisar una copia junto a la de
  producción en otra base). `--confirmar NOMBRE` confirma sin preguntar (para scripts).
- Restaura con el usuario que se conecta como dueño y vuelve a aplicar `datos/supabase_seguridad.sql`.
- Antes de restaurar en producción: detén el tráfico (modo mantenimiento o pausa en Vercel), haz una copia
  del estado actual y restaura primero en una base de prueba para revisar los conteos.

**Prueba trimestral.** Cada tres meses: descarga la última copia, restáurala en un PostgreSQL de prueba (nunca
en producción) con `--esquema-destino pullex_prueba_restauracion`, compara el número de filas de `usuarios`,
`conversaciones` y `mensajes` con producción y anota fecha y resultado en `docs/coordinacion/`.
`tests/test_seguridad_datos.py` hace ese mismo recorrido (respaldar, borrar, restaurar y comparar conteos)
contra el PostgreSQL de pruebas en cada corrida con `PULLEX_PRUEBAS_PG_URL`.

## Pruebas

```bash
python3 -m pytest -q                      # SQLite (por defecto)
PULLEX_PRUEBAS_PG_URL=postgresql://usuario:clave@127.0.0.1:5432/postgres python3 -m pytest -q
```

Con `PULLEX_PRUEBAS_PG_URL` toda la sesión corre contra PostgreSQL en un esquema temporal de nombre único
(`pullex_pruebas_…`), que se crea al empezar y se borra al terminar. Usa siempre un PostgreSQL de pruebas,
nunca el de producción. En ese modo, una prueba falla si la capa de datos registró un error de SQL que el
código se haya tragado.

Los conteos históricos de 1060 pruebas SQLite y 1086 PostgreSQL no tienen aquí un informe reproducible
vinculado a commit, entorno y fecha; no deben usarse como evidencia de aprobación. El PR #8 informó una
ejecución parcial en Windows y declaró pendientes PostgreSQL y restauración reales.

El flujo `auditoria-datos.yml` ejecuta las suites SQLite y PostgreSQL 16 sobre un servicio desechable,
sin secretos operativos, y conserva informes JUnit. Además exige que las dos variantes de restauración
(clara y cifrada) se ejecuten sin omisiones. Consultar la ejecución del commit revisado: añadir el flujo
no equivale a haber superado las pruebas. Estos resultados no certifican el pooler de Supabase ni Vercel.

## Cómo saber qué base está en uso

- `GET /salud` devuelve `db_motor` (`sqlite` o `postgres`) y `db_persistente`.
- El panel de administración muestra una ficha «Base de datos» con el motor, si conecta y si conserva los
  datos. Nunca muestra servidor, usuario ni contraseña.

## Límites conocidos

- PostgreSQL 16 se valida mediante el flujo aislado descrito arriba. **No se ha probado todavía contra el pooler real de Supabase** desde
  Vercel: es lo primero que hay que comprobar al publicar.
- El plan gratuito de Supabase pausa un proyecto tras un periodo sin actividad y limita el tamaño de la
  base. Verifica los valores vigentes en la documentación de Supabase.
- Hoy la base comparte proyecto con otro producto (esquema separado). Si crece, se muda con un volcado del
  esquema `pullex` a un proyecto propio y se cambia la URL.
- Los límites de intentos de ingreso viven en memoria de cada instancia; la tabla `limites` (versión 2 del
  esquema) existe para compartirlos entre instancias.
- Protección de datos: la base queda fuera de Colombia. Revisa lo que exige la Ley 1581 de 2012 sobre
  transferencia internacional de datos personales y dilo en la política de tratamiento (verificar con la
  SIC la lista vigente de países con nivel adecuado).
