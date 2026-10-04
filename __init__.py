"""Registro de perfiles especializados de PULLEX (ver docs/16-PERFILES-Y-COORDINADOR.md).

`registro()` carga `perfiles/registro.json` una sola vez. Ese archivo lo produce `python -m perfiles.generar`
a partir de `perfiles/definiciones.py` y `perfiles/areas/`; no se edita a mano.
"""
import json
import threading
from pathlib import Path

RUTA_REGISTRO = Path(__file__).resolve().parent / "registro.json"
_cache = {}
_candado = threading.Lock()


def registro() -> dict:
    """El registro completo (áreas, funciones, herramientas, resumen y los 1.000 perfiles)."""
    with _candado:
        if "registro" not in _cache:
            datos = json.loads(RUTA_REGISTRO.read_text(encoding="utf-8"))
            _cache["registro"] = datos
            _cache["indice"] = {p["id"]: p for p in datos["perfiles"]}
        return _cache["registro"]


def indice() -> dict:
    """{id: perfil}."""
    registro()
    return _cache["indice"]


def recargar() -> dict:
    """Olvida la copia en memoria (lo usan las pruebas tras regenerar el archivo)."""
    with _candado:
        _cache.clear()
    return registro()
