"""Importa metadatos privados de Drive en Umbral, sin leer ni publicar documentos.

Entrada: JSONL con id, path, title, mime, size y url. Por defecto solo valida y
cuenta. Para escribir se necesita --aplicar y PULLEX_BIBLIOTECA_DATABASE_URL.
La operación es incremental: conserva el texto, revisión y estado ya existentes.
No borra registros ausentes en un inventario parcial.
"""

import argparse
import json
import os
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse


SQL_INSERTAR = """
insert into pullex.biblioteca_documentos
    (proveedor, drive_id, coleccion, ruta, nombre, mime_type, tamano_bytes, url_origen)
values ('google_drive', %s, %s, %s, %s, %s, %s, %s)
on conflict (proveedor, drive_id) do update set
    coleccion = excluded.coleccion,
    ruta = excluded.ruta,
    nombre = excluded.nombre,
    mime_type = excluded.mime_type,
    tamano_bytes = excluded.tamano_bytes,
    url_origen = excluded.url_origen,
    actualizado_en = now()
where (pullex.biblioteca_documentos.coleccion,
       pullex.biblioteca_documentos.ruta,
       pullex.biblioteca_documentos.nombre,
       pullex.biblioteca_documentos.mime_type,
       pullex.biblioteca_documentos.tamano_bytes,
       pullex.biblioteca_documentos.url_origen)
      is distinct from
      (excluded.coleccion, excluded.ruta, excluded.nombre, excluded.mime_type,
       excluded.tamano_bytes, excluded.url_origen)
"""


def normalizar(registro: dict) -> tuple:
    """Valida procedencia y datos; no interpreta el título como fuente jurídica."""
    drive_id = registro["id"]
    ruta = registro["path"]
    nombre = registro["title"]
    mime = registro["mime"]
    tamano = int(registro["size"])
    url = registro["url"]
    if not all(isinstance(v, str) and v.strip() for v in (drive_id, ruta, nombre, mime, url)):
        raise ValueError("campo obligatorio vacío")
    if tamano < 0:
        raise ValueError("tamaño negativo")
    coleccion = ruta.split("/", 1)[0].upper()
    if coleccion not in {"PACK JURIDICO 1", "PACK JURIDICO 2"}:
        raise ValueError("colección no autorizada")
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in {
        "drive.google.com", "docs.google.com"
    }:
        raise ValueError("enlace de origen no es Google Drive")
    return drive_id, coleccion, ruta, nombre, mime, tamano, url


def leer_inventario(ruta: Path):
    vistos = set()
    with ruta.open(encoding="utf-8") as archivo:
        for numero, linea in enumerate(archivo, 1):
            if not linea.strip():
                continue
            try:
                fila = normalizar(json.loads(linea))
            except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
                # Nunca incluir el nombre ni el contenido del registro en el error.
                raise ValueError(f"registro {numero} inválido: {type(error).__name__}") from None
            if fila[0] in vistos:
                continue
            vistos.add(fila[0])
            yield fila


def importar(filas, conexion, lote=200):
    procesados = 0
    pendientes = []
    for fila in filas:
        pendientes.append(fila)
        if len(pendientes) == lote:
            with conexion.transaction():
                with conexion.cursor() as cur:
                    cur.executemany(SQL_INSERTAR, pendientes)
            procesados += len(pendientes)
            pendientes.clear()
    if pendientes:
        with conexion.transaction():
            with conexion.cursor() as cur:
                cur.executemany(SQL_INSERTAR, pendientes)
        procesados += len(pendientes)
    return procesados


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inventario", type=Path)
    parser.add_argument("--aplicar", action="store_true", help="escribir en Supabase")
    args = parser.parse_args(argv)
    filas = list(leer_inventario(args.inventario))
    conteo = Counter(fila[1] for fila in filas)
    print(json.dumps({"archivos_validos": len(filas), "colecciones": conteo,
                      "modo": "aplicar" if args.aplicar else "simular"}, ensure_ascii=False))
    if not args.aplicar:
        return 0

    conninfo = os.environ.get("PULLEX_BIBLIOTECA_DATABASE_URL")
    if not conninfo:
        raise SystemExit("Falta PULLEX_BIBLIOTECA_DATABASE_URL")
    import psycopg  # dependencia opcional, únicamente para la importación

    with psycopg.connect(conninfo, autocommit=True) as con:
        with con.cursor() as cur:
            cur.execute("select to_regclass('pullex.biblioteca_documentos')")
            if cur.fetchone()[0] is None:
                raise SystemExit("Falta la tabla privada de biblioteca")
        cantidad = importar(filas, con)
    print(json.dumps({"metadatos_procesados": cantidad, "documentos_descargados": 0,
                      "documentos_indexados": 0}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
