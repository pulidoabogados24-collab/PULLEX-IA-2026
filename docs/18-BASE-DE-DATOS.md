# 18 · Base de datos principal

Actualizado el 8 de octubre de 2026.

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
- Si el servidor no es local, la conexión exige TLS (`sslmode=require` como mínimo).

La URL lleva la contraseña de la base: va **solo** como variable de entorno en Vercel, marcada como sensible.
Nunca en el repositorio, en un documento ni en un mensaje.

## El esquema

- `datos/esquema_postgres.sql`: las 17 tablas más `esquema_version`. Es idempotente.
- `datos/supabase_seguridad.sql`: quita a los roles públicos de Supabase (`anon`, `authenticated`) todo
  permiso sobre el esquema. Vuelve a aplicarlo cuando agregues tablas.
- Todas las tablas tienen seguridad por filas activada y sin políticas: solo las ve el dueño (el usuario con
  que se conecta la app).
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

Regla al escribir consultas nuevas: SQL que valga en los dos motores. Nada de `INSERT OR …`, `PRAGMA`,
`rowid` ni funciones propias de SQLite en la base principal.

## Pruebas

```bash
python3 -m pytest -q                      # SQLite (por defecto)
PULLEX_PRUEBAS_PG_URL=postgresql://usuario:clave@127.0.0.1:5432/postgres python3 -m pytest -q
```

Con `PULLEX_PRUEBAS_PG_URL` toda la sesión corre contra PostgreSQL en un esquema temporal de nombre único
(`pullex_pruebas_…`), que se crea al empezar y se borra al terminar. Usa siempre un PostgreSQL de pruebas,
nunca el de producción. En ese modo, una prueba falla si la capa de datos registró un error de SQL que el
código se haya tragado.

Estado al 8 de octubre de 2026: 1033 pruebas pasan en SQLite y 1048 en PostgreSQL 16.

## Cómo saber qué base está en uso

- `GET /salud` devuelve `db_motor` (`sqlite` o `postgres`) y `db_persistente`.
- El panel de administración muestra una ficha «Base de datos» con el motor, si conecta y si conserva los
  datos. Nunca muestra servidor, usuario ni contraseña.

## Límites conocidos

- Probado contra PostgreSQL 16 local. **No se ha probado todavía contra el pooler real de Supabase** desde
  Vercel: es lo primero que hay que comprobar al publicar.
- El plan gratuito de Supabase pausa un proyecto tras un periodo sin actividad y limita el tamaño de la
  base. Verifica los valores vigentes en la documentación de Supabase.
- Hoy la base comparte proyecto con otro producto (esquema separado). Si crece, se muda con un volcado del
  esquema `pullex` a un proyecto propio y se cambia la URL.
- Los límites de intentos de ingreso viven en memoria de cada instancia, no en la base.
- Protección de datos: la base queda fuera de Colombia. Revisa lo que exige la Ley 1581 de 2012 sobre
  transferencia internacional de datos personales y dilo en la política de tratamiento (verificar con la
  SIC la lista vigente de países con nivel adecuado).
