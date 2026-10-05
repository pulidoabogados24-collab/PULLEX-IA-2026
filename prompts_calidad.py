"""Carga de los prompts versionados de `prompts/` (PUL-018).

Funciones puras, sin red ni modelo. El backend puede usarlas así (la integración en `app.py` la hace PUL-017):

    import prompts_calidad as pc
    bloque = pc.cargar_bloque()                       # texto de prompts/calidad_respuesta.md
    maestro = pc.cargar_maestro({"GUIA_ESCRITURA": redaccion.GUIA_ESCRITURA, ...})

Cada archivo guarda su metadato (versión, fecha, estado) en comentarios HTML y el texto que se carga va entre
`<!-- INICIO -->` y `<!-- FIN -->`.
"""
import re
from pathlib import Path

CARPETA = Path(__file__).resolve().parent / "prompts"
ARCHIVO_BLOQUE = "calidad_respuesta.md"
ARCHIVO_MAESTRO = "PROMPT-MAESTRO-PULLEX.md"
MARCADORES_MAESTRO = ("CALIDAD_RESPUESTA", "GUIA_ESCRITURA", "VOZ_ESTUDIANTE", "VOZ_ABOGADO", "VOZ_CIUDADANO")

_RE_CUERPO = re.compile(r"<!--\s*INICIO\s*-->(.*?)<!--\s*FIN\s*-->", re.S)
_RE_VERSION = re.compile(r"<!--\s*version:\s*([0-9]+\.[0-9]+\.[0-9]+)")
_RE_MARCADOR = re.compile(r"\{\{\s*([A-Z_]+)\s*\}\}")


class ErrorPrompt(ValueError):
    """El archivo de prompt no tiene el formato esperado o falta un marcador."""


def _leer(nombre: str, carpeta: Path = None) -> str:
    return ((carpeta or CARPETA) / nombre).read_text(encoding="utf-8")


def extraer_cuerpo(texto: str) -> str:
    m = _RE_CUERPO.search(texto)
    if not m:
        raise ErrorPrompt("falta el bloque entre <!-- INICIO --> y <!-- FIN -->")
    return m.group(1).strip()


def version_de(texto: str) -> str:
    m = _RE_VERSION.search(texto)
    if not m:
        raise ErrorPrompt("falta la línea <!-- version: X.Y.Z -->")
    return m.group(1)


def marcadores_de(cuerpo: str) -> list:
    """Nombres de los {{MARCADORES}} del cuerpo, sin repetir y en orden de aparición."""
    vistos = []
    for n in _RE_MARCADOR.findall(cuerpo):
        if n not in vistos:
            vistos.append(n)
    return vistos


def cargar_bloque(carpeta: Path = None) -> str:
    """Texto del bloque de calidad de respuesta (sin metadatos)."""
    return extraer_cuerpo(_leer(ARCHIVO_BLOQUE, carpeta))


def cargar_maestro(sustituciones: dict, carpeta: Path = None) -> str:
    """Prompt maestro con los marcadores sustituidos. CALIDAD_RESPUESTA se completa solo con el bloque si no se
    pasa. Falla (ErrorPrompt) si queda un marcador sin valor: es preferible no arrancar a mandar «{{VOZ_ABOGADO}}»
    al modelo."""
    cuerpo = extraer_cuerpo(_leer(ARCHIVO_MAESTRO, carpeta))
    valores = dict(sustituciones or {})
    valores.setdefault("CALIDAD_RESPUESTA", cargar_bloque(carpeta))
    faltan = [n for n in marcadores_de(cuerpo) if n not in valores]
    if faltan:
        raise ErrorPrompt("faltan valores para: " + ", ".join(faltan))
    return _RE_MARCADOR.sub(lambda m: str(valores[m.group(1)]).strip(), cuerpo)


def versiones(carpeta: Path = None) -> dict:
    return {n: version_de(_leer(n, carpeta)) for n in (ARCHIVO_BLOQUE, ARCHIVO_MAESTRO)}
