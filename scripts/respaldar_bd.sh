#!/usr/bin/env bash
# PULLEX IA — copia de seguridad del esquema de la app en PostgreSQL (BD-01, docs/18-BASE-DE-DATOS.md).
#
# Uso:   scripts/respaldar_bd.sh [CARPETA_DESTINO]
#
# Variables:
#   PULLEX_DATABASE_URL_DIRECTA  (obligatoria) conexión DIRECTA a PostgreSQL, puerto 5432. NO la del pooler (6543):
#                                pg_dump necesita una sesión propia y el pooler en modo transacción no la da.
#   PULLEX_DB_ESQUEMA            esquema a copiar (por defecto «pullex»). Solo ese esquema: la base se comparte con
#                                otros productos y su respaldo no es asunto de este script.
#   PULLEX_RESPALDO_CLAVE        si existe, la copia se cifra con gpg (AES-256, simétrico) y el archivo sin cifrar se
#                                borra. La clave se pasa por la entrada estándar, nunca en la línea de órdenes.
#   PULLEX_RESPALDO_EXIGIR_CIFRADO=1  falla si no hay clave (lo usa el flujo de GitHub Actions).
#   PULLEX_RESPALDO_DIR          carpeta de destino si no se pasa como argumento (por defecto ./respaldos).
#
# Salida: la última línea de stdout es la ruta del archivo final (.dump o .dump.gpg). Junto a él queda un .sha256.
# Formato: pg_dump «custom» (-Fc), que se restaura con scripts/restaurar_bd.sh (pg_restore).
# Nunca imprime la URL ni la clave.
set -euo pipefail
umask 077

error() { echo "respaldar_bd: $*" >&2; exit 1; }

url="${PULLEX_DATABASE_URL_DIRECTA:-}"
[ -n "$url" ] || error "falta PULLEX_DATABASE_URL_DIRECTA (conexión directa, puerto 5432)."
case "$url" in
  *:6543/*|*:6543) error "PULLEX_DATABASE_URL_DIRECTA apunta al pooler (puerto 6543). Usa la conexión directa (5432)." ;;
esac
esquema="${PULLEX_DB_ESQUEMA:-pullex}"
[[ "$esquema" =~ ^[a-z_][a-z0-9_]{0,62}$ ]] || error "PULLEX_DB_ESQUEMA no es un nombre de esquema válido."
case "$esquema" in public|information_schema|pg_*) error "no se respalda el esquema «$esquema»: solo el de la app." ;; esac
for orden in pg_dump pg_restore; do
  command -v "$orden" >/dev/null 2>&1 || error "falta «$orden» (instala el cliente de PostgreSQL de la MISMA versión mayor que el servidor o una posterior)."
done
clave="${PULLEX_RESPALDO_CLAVE:-}"
if [ -z "$clave" ] && [ "${PULLEX_RESPALDO_EXIGIR_CIFRADO:-0}" = "1" ]; then
  error "PULLEX_RESPALDO_EXIGIR_CIFRADO=1 y no hay PULLEX_RESPALDO_CLAVE: no se genera una copia sin cifrar."
fi
if [ -n "$clave" ]; then command -v gpg >/dev/null 2>&1 || error "falta «gpg» para cifrar la copia."; fi

destino="${1:-${PULLEX_RESPALDO_DIR:-respaldos}}"
mkdir -p "$destino"
chmod 700 "$destino" 2>/dev/null || true
marca="$(date -u +%Y%m%dT%H%M%SZ)"
archivo="$destino/pullex_${esquema}_${marca}.dump"
temporal="$archivo.parcial"
trap 'rm -f "$temporal"' EXIT

# pg_dump deja row_security=off y falla (en vez de copiar 0 filas en silencio) si la seguridad por filas ocultara algo:
# hay que conectarse con el usuario dueño de las tablas.
pg_dump --dbname="$url" --schema="$esquema" --format=custom --compress=6 --file="$temporal" \
  || error "pg_dump falló (revisa la conexión, el usuario dueño del esquema y la versión del cliente)."
pg_restore --list "$temporal" >/dev/null || error "la copia generada no se puede leer con pg_restore."
pg_restore --list "$temporal" | grep -q " SCHEMA - $esquema " || error "la copia no contiene el esquema «$esquema»."
mv "$temporal" "$archivo"

if [ -n "$clave" ]; then
  printf '%s' "$clave" | gpg --batch --yes --quiet --pinentry-mode loopback --passphrase-fd 0 \
      --symmetric --cipher-algo AES256 --output "$archivo.gpg" "$archivo" \
    || { rm -f "$archivo" "$archivo.gpg"; error "gpg no pudo cifrar la copia."; }
  rm -f "$archivo"
  archivo="$archivo.gpg"
fi
( cd "$(dirname "$archivo")" && sha256sum "$(basename "$archivo")" > "$(basename "$archivo").sha256" )
echo "respaldar_bd: copia del esquema «$esquema» lista ($(wc -c < "$archivo") bytes)." >&2
echo "$archivo"
