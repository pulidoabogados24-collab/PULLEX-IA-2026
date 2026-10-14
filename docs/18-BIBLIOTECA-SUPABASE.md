# Biblioteca jurídica privada en Umbral

Fecha: 2026-10-13. Proyecto Supabase: `npqpqaetjjrmfvpbskfb` (`umbral-licita`).
Solo se usa el esquema `pullex`; las tablas de Umbral Licita no se modifican.

## Estado comprobado

- `Pack Jurídico 1`: 16.232 archivos distintos visibles en 959 carpetas,
  12,79 GB según los tamaños de Drive. Tres carpetas llegaron al límite de
  1.000 elementos.
- `Pack Jurídico 2`: 11.102 archivos distintos visibles en 613 carpetas,
  5,86 GB según los tamaños de Drive. Otras tres carpetas llegaron al límite.
  Por tanto, **27.334 es un mínimo**, no el tamaño final comprobado de ambos
  packs. Hace falta paginación verificable para las seis carpetas limitadas.
- El listado privado se conserva fuera de Git. Puede contener nombres de
  clientes y otros datos personales. En el repositorio se publican solo el
  esquema, el importador y los resultados agregados.
- El inventario anterior del repositorio solo tenía 16 archivos del Pack 1;
  esta revisión encontró una colección mucho mayor.
- La consulta de control en Supabase devolvió exactamente 16.232 fichas del
  Pack 1 y 11.102 del Pack 2. Los metadatos quedan `ENCONTRADO`, con sensibilidad y
  vigencia pendientes y derechos por confirmar. **No equivalen a documentos
  descargados, textos extraídos, búsqueda funcional ni validación jurídica.**
- La aplicación publicada sigue usando su catálogo SQLite; aún no consulta
  las tablas nuevas de Supabase.

## Privacidad y acceso

`sql/biblioteca_privada.sql` crea `pullex.biblioteca_documentos` y
`pullex.biblioteca_fragmentos`. Ambas tienen RLS activada, sin políticas para
clientes, y se retiran los privilegios de `anon` y `authenticated`. El texto de
los fragmentos tiene índice de búsqueda en español y ubicación de origen.
Toda consulta de la aplicación necesitará autorización de servidor comprobada
antes de acceder a este material. Un nombre de archivo puede ser sensible.

## Sincronización incremental

El listado debe guardarse como JSONL **privado**, una línea por archivo con
`id`, `path`, `title`, `mime`, `size` y `url`. Validar sin conexión:

```text
python scripts/importar_inventario_supabase.py RUTA_PRIVADA/inventario.jsonl
```

Para aplicar, configurar `PULLEX_BIBLIOTECA_DATABASE_URL` en el entorno del
servidor, instalar `requirements-ingesta.txt` y añadir `--aplicar`. Nunca
guardar la URL de conexión ni el inventario privado en Git. La carga conserva
el estado de procesamiento, revisiones y huellas previas; un listado parcial
no borra documentos. Una segunda ejecución es segura para actualizar
metadatos que cambiaron.

## Recuperación y siguiente tramo

No se migró ni reemplazó información preexistente: las dos tablas son nuevas.
Antes de cargar originales o fragmentos, hacer una copia verificable del
esquema `pullex` y del almacenamiento privado; probar la restauración en un
entorno separado y conservar el registro de huellas. Las copias deben quedar
cifradas y con acceso limitado. No usar el repositorio público como respaldo.

La importación de contenido necesita acceso programático autorizado a ambos
packs, paginación completa y un almacén privado para originales. Después debe
registrar SHA-256, detectar duplicados, extraer páginas o secciones, marcar
archivos ilegibles, filtrar datos personales y verificar derechos. La
publicación de plantillas y la vigencia jurídica requieren revisión humana.

Referencia técnica para la decisión de permisos: documentación de
[Row Level Security de Supabase](https://supabase.com/docs/guides/database/postgres/row-level-security).
