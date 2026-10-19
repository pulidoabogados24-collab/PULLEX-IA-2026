"""Biblioteca privada (metadatos y fragmentos) de los dos Packs Jurídicos.

El servidor consulta PostgreSQL. Ninguna respuesta devuelve URL, ID externo o
credencial de Google Drive. Hasta validar derechos y datos personales, se exige
autenticación de administrador activo. Los registros no indexados son solo
metadatos, no documentos consultables en texto completo.
"""
import logging
import os
from contextlib import closing

from fastapi import APIRouter, HTTPException, Request
from datos import ErrorConfiguracion, limpiar_url

LOG = logging.getLogger(__name__)
COLECCIONES = ("PACK JURIDICO 1", "PACK JURIDICO 2")


def catalogo_configurado():
    return bool(os.environ.get("PULLEX_BIBLIOTECA_DATABASE_URL"))


def _leer(sql, params=()):
    conninfo = os.getenv("PULLEX_BIBLIOTECA_DATABASE_URL", "")
    if not conninfo:
        raise HTTPException(503, "El catálogo privado aún no está conectado")
    try:
        import psycopg
        from psycopg.rows import dict_row
    except ImportError:
        raise HTTPException(503, "El lector privado aún no está instalado") from None
    try:
        parametros = limpiar_url(conninfo)  # TLS obligatorio fuera del servidor local, igual que la base principal.
        parametros["connect_timeout"] = 5
        with closing(psycopg.connect(**parametros, row_factory=dict_row)) as con:
            with con.transaction():
                with con.cursor() as cur:
                    cur.execute("SET TRANSACTION READ ONLY")
                    cur.execute("SET LOCAL statement_timeout = '8s'")
                    cur.execute(sql, params)
                    return cur.fetchall()
    except (psycopg.Error, ErrorConfiguracion):
        LOG.warning("Fallo de consulta del catálogo privado")
        raise HTTPException(503, "Catálogo temporalmente no disponible") from None


def crear_router(*, admin_actual, limitar_cuenta=None):
    router = APIRouter()

    def proteger(request):
        u = admin_actual(request)
        if not u.get("activo"):
            raise HTTPException(403, "Cuenta inactiva")
        if limitar_cuenta:
            limitar_cuenta("biblioteca_privada:" + u["email"], 60, 60)

    @router.get("/api/admin/biblioteca/packs/resumen")
    def resumen(request: Request):
        proteger(request)
        filas = _leer("""
            SELECT coleccion, count(*)::integer total,
                   count(*) FILTER (WHERE estado_procesamiento='INDEXADO')::integer indexados
            FROM pullex.biblioteca_documentos
            WHERE coleccion IN ('PACK JURIDICO 1','PACK JURIDICO 2')
            GROUP BY coleccion ORDER BY coleccion
        """)
        mapa = {f["coleccion"]: f for f in filas}
        return {
            "total": sum(f["total"] for f in filas),
            "colecciones": [
                {"nombre": c, "total": mapa.get(c, {}).get("total", 0),
                 "indexados": mapa.get(c, {}).get("indexados", 0)}
                for c in COLECCIONES
            ],
            "alcance": "catalogo_privado",
            "nota": "Los documentos pendientes de extracción no permiten consulta de texto.",
        }

    @router.get("/api/admin/biblioteca/packs/buscar")
    def buscar(request: Request, q: str = "", coleccion: str = "",
               pagina: int = 1, por_pagina: int = 20):
        proteger(request)
        if coleccion and coleccion not in COLECCIONES:
            raise HTTPException(400, "Colección inválida")
        if not 1 <= pagina <= 1000 or not 1 <= por_pagina <= 50:
            raise HTTPException(400, "Paginación inválida")
        q = q.strip()[:150]
        parametros = (coleccion, coleccion, q, q, q, q)
        where = """
            coleccion IN ('PACK JURIDICO 1','PACK JURIDICO 2')
            AND (%s = '' OR coleccion = %s)
            AND (%s = '' OR strpos(lower(nombre),lower(%s)) > 0
                         OR strpos(lower(ruta),lower(%s)) > 0
                         OR (estado_procesamiento = 'INDEXADO' AND EXISTS (
                             SELECT 1 FROM pullex.biblioteca_fragmentos f
                             WHERE f.documento_id = pullex.biblioteca_documentos.id
                               AND f.texto_busqueda @@ plainto_tsquery('spanish', %s)
                         )))
        """
        cuentas = _leer(
            "SELECT count(*)::integer total FROM pullex.biblioteca_documentos WHERE " + where,
            parametros,
        )
        total = int(cuentas[0]["total"]) if cuentas else 0
        resultados = _leer("""
            SELECT id, coleccion, ruta, nombre, mime_type,
                   estado_procesamiento, vigencia
            FROM pullex.biblioteca_documentos WHERE """ + where + """
            ORDER BY nombre, id LIMIT %s OFFSET %s
        """, parametros + (por_pagina, (pagina - 1) * por_pagina))
        return {
            "total": total, "pagina": pagina, "por_pagina": por_pagina,
            "paginas": max(1, (total + por_pagina - 1) // por_pagina),
            "resultados": resultados, "busqueda": "titulo_ruta_y_fragmentos_indexados",
        }

    @router.get("/api/admin/biblioteca/packs/documento/{documento_id}")
    def documento(documento_id: int, request: Request):
        proteger(request)
        if documento_id < 1:
            raise HTTPException(404, "Documento no encontrado")
        encontrados = _leer("""
            SELECT id, coleccion, nombre, estado_procesamiento, vigencia
            FROM pullex.biblioteca_documentos
            WHERE id = %s AND coleccion IN ('PACK JURIDICO 1','PACK JURIDICO 2')
        """, (documento_id,))
        if not encontrados:
            raise HTTPException(404, "Documento no encontrado")
        doc = encontrados[0]
        texto = []
        if doc["estado_procesamiento"] == "INDEXADO":
            texto = _leer("""
                SELECT ordinal, ubicacion, left(contenido, 8000) AS contenido
                FROM pullex.biblioteca_fragmentos
                WHERE documento_id = %s ORDER BY ordinal LIMIT 25
            """, (documento_id,))
        return {
            **doc, "fragmentos": texto,
            "completo": bool(texto) and len(texto) < 25,
            "nota": "Texto sujeto a verificación de integridad, vigencia, derechos y revisión jurídica.",
        }

    return router
