"""Biblioteca de DEMOSTRACIÓN: monta un catálogo ficticio (demo/biblioteca_demo.json) con el backend real
(biblioteca.py). La usan demo/servidor_simulado.py (rutas reales sobre datos de ejemplo) y demo/construir_demo.py
(para incrustar las fichas en la demostración de un solo archivo).

Ningún documento de este catálogo existe en Drive. En la demostración los derechos de los documentos «de terceros»
se dan por confirmados (PULLEX_BIBLIOTECA_TERCEROS=general) solo para poder mostrar cómo se ve su ficha; su texto
sigue reservado al administrador, igual que en la aplicación real."""
import json
import os
import sys
import tempfile
from contextlib import closing
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
DATOS = json.loads((RAIZ / "demo" / "biblioteca_demo.json").read_text(encoding="utf-8"))


def montar(carpeta: str = None) -> dict:
    """Crea (o actualiza) la biblioteca de demostración en `carpeta` y deja las variables de entorno
    PULLEX_BIBLIOTECA_* apuntando a ella. Devuelve el reporte de la sincronización."""
    import biblioteca
    carpeta = Path(carpeta or tempfile.mkdtemp(prefix="pullex-biblioteca-demo-"))
    carpeta.mkdir(parents=True, exist_ok=True)
    rutas = {"PULLEX_BIBLIOTECA_DB": carpeta / "biblioteca_demo.db", "PULLEX_BIBLIOTECA_INVENTARIO": carpeta / "inventario.json",
             "PULLEX_BIBLIOTECA_IDS": carpeta / "ids.json", "PULLEX_BIBLIOTECA_FICHAS": carpeta / "fichas.json",
             "PULLEX_BIBLIOTECA_MAPA": carpeta / "mapa.json"}
    for clave, contenido in (("PULLEX_BIBLIOTECA_INVENTARIO", DATOS["inventario"]), ("PULLEX_BIBLIOTECA_FICHAS", DATOS["fichas"]),
                             ("PULLEX_BIBLIOTECA_MAPA", DATOS["mapa"])):
        rutas[clave].write_text(json.dumps(contenido, ensure_ascii=False), encoding="utf-8")
    for clave, ruta in rutas.items():
        os.environ[clave] = str(ruta)
    os.environ["PULLEX_BIBLIOTECA_TERCEROS"] = "general"
    rep = biblioteca.sincronizar_archivos()
    with closing(biblioteca.conexion()) as con:
        for drive_id, texto in DATOS["textos"].items():
            biblioteca.registrar_texto(con, drive_id, [("", texto)], origen="demostración")
    return rep
