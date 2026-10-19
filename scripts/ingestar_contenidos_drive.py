"""Extracción incremental de los dos Packs a Supabase PRIVADO (nunca en Vercel).

Requiere credenciales Google Drive OAuth/ADC con acceso de lectura a los packs
y PULLEX_BIBLIOTECA_DATABASE_URL en un trabajador aislado. Simulación por
defecto; ejecutar con --aplicar para escribir. No imprime títulos ni texto.
No redistribuir contenido de terceros sin comprobar permisos y finalidad.
"""
import argparse
import hashlib
import io
import os

MAX_BYTES = 12 * 1024 * 1024
COLECCIONES = ("PACK JURIDICO 1", "PACK JURIDICO 2")
NATIVO_DOC = "application/vnd.google-apps.document"
PDF = "application/pdf"
DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
PLAIN = {"text/plain", "text/markdown"}


def extraer(data, mime, max_fragmentos=250):
    """Devuelve fragmentos (ubicación, texto); no inventa texto de imágenes."""
    if mime == PDF:
        from pypdf import PdfReader
        paginas = [(f"página {i}", p.extract_text() or "")
                   for i, p in enumerate(PdfReader(io.BytesIO(data)).pages, 1)]
    elif mime == DOCX:
        from docx import Document
        doc = Document(io.BytesIO(data))
        parrafos = [p.text for p in doc.paragraphs if p.text.strip()]
        paginas = [("cuerpo", "\n".join(parrafos))]
    elif mime in PLAIN or mime == NATIVO_DOC:
        paginas = [("texto", data.decode("utf-8", errors="replace"))]
    else:
        return []
    fragmentos = []
    for ubicacion, texto in paginas:
        texto = texto.replace("\x00", "").strip()
        for inicio in range(0, len(texto), 6000):
            bloque = texto[inicio:inicio+6000].strip()
            if bloque:
                fragmentos.append((ubicacion, bloque))
            if len(fragmentos) >= max_fragmentos:
                return fragmentos
    return fragmentos


def obtener_drive(servicio, identificador, mime, tamano_maximo):
    """Descarga privada a RAM; la salida nunca llega al navegador."""
    meta = servicio.files().get(fileId=identificador, fields="id,mimeType,size").execute()
    tipo = meta.get("mimeType", "")
    if tipo not in {PDF, DOCX, NATIVO_DOC, *PLAIN}:
        raise ValueError("MIME_NO_COMPATIBLE")
    if meta.get("size") and int(meta["size"]) > tamano_maximo:
        raise ValueError("ARCHIVO_GRANDE")
    if tipo == NATIVO_DOC:
        datos = servicio.files().export(fileId=identificador, mimeType="text/plain").execute()
    else:
        datos = servicio.files().get_media(fileId=identificador).execute()
    if len(datos) > tamano_maximo:
        raise ValueError("ARCHIVO_GRANDE")
    return datos, tipo


def pendientes(con, coleccion, limite, tamano_maximo):
    from psycopg.rows import dict_row
    with con.cursor(row_factory=dict_row) as cur:
        cur.execute("""
            SELECT id, drive_id, mime_type, tamano_bytes
            FROM pullex.biblioteca_documentos
            WHERE coleccion = %s AND estado_procesamiento = 'ENCONTRADO'
              AND tamano_bytes <= %s
            ORDER BY id LIMIT %s
        """, (coleccion, tamano_maximo, limite))
        return cur.fetchall()


def guardar(con, identificador, datos, fragmentos):
    with con.transaction():
        with con.cursor() as cur:
            cur.execute("DELETE FROM pullex.biblioteca_fragmentos WHERE documento_id=%s", (identificador,))
            cur.executemany("""
                INSERT INTO pullex.biblioteca_fragmentos
                    (documento_id, ordinal, ubicacion, contenido) VALUES (%s,%s,%s,%s)
            """, [(identificador, i, ubicacion, texto)
                  for i, (ubicacion, texto) in enumerate(fragmentos)])
            cur.execute("""
                UPDATE pullex.biblioteca_documentos
                SET estado_procesamiento='INDEXADO', sha256_original=%s,
                    error_procesamiento=NULL, actualizado_en=now()
                WHERE id=%s
            """, (hashlib.sha256(datos).hexdigest(), identificador))


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--coleccion", choices=COLECCIONES, required=True)
    p.add_argument("--limite", type=int, default=10)
    p.add_argument("--max-bytes", type=int, default=MAX_BYTES)
    p.add_argument("--aplicar", action="store_true")
    args = p.parse_args(argv)
    if not 1 <= args.limite <= 500 or not 1 <= args.max_bytes <= MAX_BYTES:
        p.error("limites fuera de rango")
    if not args.aplicar:
        print("SIMULACION: sin acceso Drive ni escrituras; configure credenciales y use --aplicar.")
        return 0
    conninfo = os.environ.get("PULLEX_BIBLIOTECA_DATABASE_URL")
    if not conninfo:
        p.error("Falta PULLEX_BIBLIOTECA_DATABASE_URL")
    import google.auth
    from googleapiclient.discovery import build
    import psycopg
    credenciales, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/drive.readonly"])
    servicio = build("drive", "v3", credentials=credenciales, cache_discovery=False)
    procesados = errores = no_extraibles = 0
    with psycopg.connect(conninfo) as con:
        con.autocommit = True
        for doc in pendientes(con, args.coleccion, args.limite, args.max_bytes):
            try:
                datos, tipo = obtener_drive(servicio, doc["drive_id"], doc["mime_type"], args.max_bytes)
                fragmentos = extraer(datos, tipo)
                if not fragmentos:
                    no_extraibles += 1
                    continue
                guardar(con, doc["id"], datos, fragmentos)
                procesados += 1
            except Exception as exc:
                # Evitar imprimir ID de Drive, título o contenido potencialmente reservado.
                errores += 1
                print("Error procesando un archivo: " + type(exc).__name__)
    print(f"procesados={procesados} sin_texto={no_extraibles} errores={errores}")
    return 0 if not errores else 1


if __name__ == "__main__":
    raise SystemExit(main())
