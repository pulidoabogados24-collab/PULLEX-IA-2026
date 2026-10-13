#!/usr/bin/env bash
# PULLEX IA — restaura una copia hecha con scripts/respaldar_bd.sh (BD-01, docs/18-BASE-DE-DATOS.md).
#
# Uso:
#   scripts/restaurar_bd.sh ARCHIVO(.dump|.dump.gpg) --destino-url URL [opciones]
#
# Opciones:
#   --destino-url URL       base donde restaurar (o la variable PULLEX_RESTAURAR_URL). Obligatoria y explícita: este
#                           script NUNCA toma PULLEX_DATABASE_URL ni la URL de la app. Conexión directa (5432).
#   --esquema NOMBRE        esquema que trae la copia (por defecto PULLEX_DB_ESQUEMA o «pullex»).
#   --esquema-destino NOMBRE  nombre con que queda restaurado (por defecto, el mismo). Si es distinto, la copia se
#                           restaura con su nombre original y se renombra dentro de la misma transacción; por eso el
#                           esquema original no puede existir en la base de destino (restaura en otra base o usa el
#                           mismo nombre).
#   --confirmar NOMBRE      confirmación sin preguntar: debe ser exactamente el esquema de destino. Sin ella, el
#                           script pregunta en la terminal y exige escribir ese nombre.
#   --forzar                si el esquema de destino YA existe, lo borra (DROP SCHEMA … CASCADE) y lo reemplaza por la
#                           copia. Sin --forzar nunca se borra nada: si existe, el script se detiene.
#
# Todo ocurre en UNA transacción (psql --single-transaction): si algo falla, la base de destino queda como estaba,
# incluido el esquema que --forzar iba a reemplazar. Después aplica datos/supabase_seguridad.sql al esquema restaurado.
# Una copia cifrada (.gpg) se descifra con PULLEX_RESPALDO_CLAVE en una carpeta temporal privada que se borra al final.
set -euo pipefail
umask 077

error() { echo "restaurar_bd: $1" >&2; exit "${2:-1}"; }
raiz="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

archivo="" ; url="${PULLEX_RESTAURAR_URL:-}" ; origen="${PULLEX_DB_ESQUEMA:-pullex}" ; destino="" ; confirmar="" ; forzar=0
while [ $# -gt 0 ]; do
  case "$1" in
    --destino-url) url="${2:-}"; shift 2 ;;
    --esquema) origen="${2:-}"; shift 2 ;;
    --esquema-destino) destino="${2:-}"; shift 2 ;;
    --confirmar) confirmar="${2:-}"; shift 2 ;;
    --forzar) forzar=1; shift ;;
    -h|--help) sed -n '2,25p' "$0"; exit 0 ;;
    -*) error "opción desconocida: $1" 2 ;;
    *) [ -z "$archivo" ] || error "sobra el argumento «$1»" 2; archivo="$1"; shift ;;
  esac
done
destino="${destino:-$origen}"

[ -n "$archivo" ] || error "falta el archivo de la copia (ver --help)." 2
[ -f "$archivo" ] || error "no existe el archivo «$archivo»." 2
[ -n "$url" ] || error "falta la base de destino: --destino-url o PULLEX_RESTAURAR_URL (nunca se usa la URL de la app)." 2
case "$url" in *:6543/*|*:6543) error "la URL de destino es la del pooler (6543): usa la conexión directa (5432)." 2 ;; esac
for nombre in "$origen" "$destino"; do
  [[ "$nombre" =~ ^[a-z_][a-z0-9_]{0,62}$ ]] || error "nombre de esquema inválido: «$nombre»." 2
  case "$nombre" in public|information_schema|pg_*) error "no se restaura sobre el esquema «$nombre»." 2 ;; esac
done
for orden in pg_restore psql; do command -v "$orden" >/dev/null 2>&1 || error "falta «$orden» (cliente de PostgreSQL)."; done

# Integridad: si está el .sha256 que deja respaldar_bd.sh, se comprueba.
if [ -f "$archivo.sha256" ]; then
  ( cd "$(dirname "$archivo")" && sha256sum --check --quiet "$(basename "$archivo").sha256" ) \
    || error "la suma SHA-256 no coincide: la copia está dañada o fue alterada."
else
  echo "restaurar_bd: aviso: no hay $archivo.sha256; no se comprueba la integridad." >&2
fi

trabajo="$(mktemp -d)"
trap 'rm -rf "$trabajo"' EXIT
copia="$archivo"
case "$archivo" in
  *.gpg)
    [ -n "${PULLEX_RESPALDO_CLAVE:-}" ] || error "la copia está cifrada: define PULLEX_RESPALDO_CLAVE."
    command -v gpg >/dev/null 2>&1 || error "falta «gpg» para descifrar la copia."
    copia="$trabajo/copia.dump"
    printf '%s' "$PULLEX_RESPALDO_CLAVE" | gpg --batch --yes --quiet --pinentry-mode loopback --passphrase-fd 0 \
        --decrypt --output "$copia" "$archivo" || error "no se pudo descifrar la copia (¿clave equivocada?)."
    ;;
esac
pg_restore --list "$copia" > "$trabajo/lista" || error "el archivo no es una copia de pg_dump en formato custom."
grep -q " SCHEMA - $origen " "$trabajo/lista" || error "la copia no contiene el esquema «$origen» (usa --esquema)." 2
tablas="$(grep -c " TABLE DATA $origen " "$trabajo/lista" || true)"

existe() {
  # (el nombre ya pasó la validación de identificador; va como variable de psql, no pegado en el SQL)
  echo "SELECT to_regnamespace(quote_ident(:'nombre')) IS NOT NULL;" \
    | psql "$url" -X -At -v ON_ERROR_STOP=1 -v nombre="$1" -f - 2>/dev/null \
    || error "no se pudo consultar la base de destino (revisa la conexión)."
}
ya_destino="$(existe "$destino")"
if [ "$destino" != "$origen" ] && [ "$(existe "$origen")" = "t" ]; then
  error "el esquema «$origen» ya existe en la base de destino y la copia se restaura con ese nombre antes de renombrarla. Restaura en otra base o con --esquema-destino $origen." 3
fi
if [ "$ya_destino" = "t" ] && [ "$forzar" != "1" ]; then
  error "el esquema «$destino» ya existe en la base de destino. No se borra nada sin --forzar." 3
fi

echo "restaurar_bd: se restaurará la copia del esquema «$origen» ($tablas tablas con datos) como «$destino»." >&2
[ "$ya_destino" = "t" ] && echo "restaurar_bd: ATENCIÓN: --forzar BORRARÁ el esquema «$destino» que ya existe y todo su contenido." >&2
if [ -z "$confirmar" ]; then
  [ -r /dev/tty ] || error "sin terminal: confirma con --confirmar $destino." 4
  printf 'Escribe el nombre del esquema de destino (%s) para continuar: ' "$destino" > /dev/tty
  IFS= read -r confirmar < /dev/tty || true
fi
[ "$confirmar" = "$destino" ] || error "confirmación incorrecta: no se hizo nada." 4

{
  echo "\\set ON_ERROR_STOP on"
  [ "$ya_destino" = "t" ] && echo "DROP SCHEMA \"$destino\" CASCADE;"
  echo "CREATE SCHEMA \"$origen\";"
  # --schema: aunque se pase la copia de una base entera, solo entra el esquema de la app.
  pg_restore --schema="$origen" --no-owner --no-privileges --file=- "$copia"
  [ "$destino" != "$origen" ] && echo "ALTER SCHEMA \"$origen\" RENAME TO \"$destino\";"
  echo "SET LOCAL search_path TO \"$destino\";"
  echo "\\i $raiz/datos/supabase_seguridad.sql"
} | psql "$url" -X -q -v ON_ERROR_STOP=1 --single-transaction -f - >/dev/null \
  || error "la restauración falló y se deshizo completa: la base de destino quedó como estaba."

echo "restaurar_bd: listo. Esquema «$destino» restaurado." >&2
