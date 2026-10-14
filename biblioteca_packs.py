"""Rutas privadas de consulta del catálogo de los Packs Jurídicos."""
import os

def catalogo_configurado():
    return bool(os.environ.get("PULLEX_BIBLIOTECA_DATABASE_URL"))
