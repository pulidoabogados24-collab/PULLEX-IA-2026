"""
PULLEX IA — Registro de motores de IA (registro B de la especificación, sección 4)
==================================================================================
Lee motores_ia.json (lo que hay en el código, verificado a mano) y le suma la DISPONIBILIDAD en
este entorno: si el motor está configurado aquí y ahora. No guarda ni devuelve secretos: de una
clave solo informa si existe.

Separado a propósito de la Biblioteca (biblioteca.py), que cataloga modelos JURÍDICOS. Una carpeta
de minutas no es un catálogo de motores de IA.

Reglas del archivo: no se registran proveedores que no estén en el código; un costo solo es
"comprobado" si se leyó en la página oficial de precios (con URL y fecha); lo demás es "desconocido".
"""
import importlib.util
import json
import os
import shutil
import sqlite3
from datetime import datetime, timezone

import biblioteca
import fuentes

RUTA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "motores_ia.json")
COSTOS = ("comprobado", "desconocido", "no_aplica")


def cargar(ruta: str = None) -> dict:
    with open(ruta or RUTA, encoding="utf-8") as f:
        return json.load(f)


def _hay_modulo(nombre: str) -> bool:
    try:
        return importlib.util.find_spec(nombre) is not None
    except (ImportError, ValueError):
        return False


def _disponibilidad(comprobacion: str, entorno: dict) -> dict:
    """{configurado, detalle} del motor en ESTE entorno. `entorno` lo arma app.py (sin secretos)."""
    clave = bool(entorno.get("api"))
    if comprobacion == "anthropic":
        return {"configurado": clave, "detalle": ("Clave de API presente. Modelo en uso: " + str(entorno.get("modelo")))
                if clave else "No configurado: falta ANTHROPIC_API_KEY."}
    if comprobacion == "anthropic_boletin":
        return {"configurado": clave, "detalle": ("Clave de API presente. Modelo en uso: " + str(entorno.get("modelo_boletin")))
                if clave else "No configurado: falta ANTHROPIC_API_KEY (el boletín muestra un aviso)."}
    if comprobacion == "corpus":
        ok = fuentes.disponible()
        return {"configurado": ok, "detalle": ("Índice con fragmentos en " + fuentes.ruta_db()) if ok else
                "No configurado: no existe el índice o está vacío (" + fuentes.ruta_db() + "). SQLite " + sqlite3.sqlite_version + "."}
    if comprobacion == "biblioteca":
        try:
            con = biblioteca.conexion()
            try:
                n = con.execute("SELECT COUNT(*) FROM biblioteca_modelos WHERE retirado=0").fetchone()[0]
                t = con.execute("SELECT COUNT(*) FROM biblioteca_textos").fetchone()[0]
            finally:
                con.close()
        except sqlite3.Error:
            return {"configurado": False, "detalle": "No se pudo abrir la base de la biblioteca."}
        return {"configurado": n > 0, "detalle": f"{n} elementos en el catálogo; {t} con texto extraído. SQLite {sqlite3.sqlite_version}."
                if n else "Catálogo vacío: falta sincronizar el inventario (scripts/sincronizar_biblioteca.py)."}
    if comprobacion == "extraccion":
        partes = {"python-docx": _hay_modulo("docx"), "pypdf": _hay_modulo("pypdf"),
                  "pdftotext": shutil.which("pdftotext") is not None}
        pdf = partes["pypdf"] or partes["pdftotext"]
        return {"configurado": partes["python-docx"] or pdf,
                "detalle": ", ".join(f"{k}: {'sí' if v else 'no'}" for k, v in partes.items()) +
                ("" if pdf else ". Sin extractor de PDF en este servidor.") + " OCR: no."}
    if comprobacion == "voyage":
        carpeta, llave = os.path.isdir("bd_vectorial"), bool(os.getenv("VOYAGE_API_KEY"))
        paquetes = _hay_modulo("chromadb") and _hay_modulo("voyageai")
        ok = carpeta and llave and paquetes
        return {"configurado": ok, "detalle": "Configurado." if ok else
                "No configurado: " + "; ".join(x for x, falta in (("falta la carpeta bd_vectorial/", not carpeta),
                                                                  ("falta VOYAGE_API_KEY", not llave),
                                                                  ("chromadb o voyageai no están instalados", not paquetes)) if falta) + "."}
    return {"configurado": True, "detalle": "Forma parte del código; no necesita configuración."}


def registro(entorno: dict = None, ruta: str = None) -> dict:
    """El registro con la disponibilidad calculada. Lanza ValueError si el archivo afirma un costo
    "comprobado" sin fuente, para que esa regla no se pueda saltar por descuido."""
    entorno = entorno or {}
    datos = cargar(ruta)
    verificaciones = datos.get("verificaciones") or {}
    salida = []
    for m in datos.get("motores") or []:
        costo = dict(m.get("costo") or {})
        if costo.get("estado") not in COSTOS:
            raise ValueError(f"motor {m.get('id')}: estado de costo inválido")
        fuente = verificaciones.get(costo.get("verificacion") or "")
        if costo["estado"] == "comprobado" and not (fuente and fuente.get("url") and fuente.get("fecha")):
            raise ValueError(f"motor {m.get('id')}: costo «comprobado» sin URL y fecha de verificación")
        costo["fuente"] = fuente
        version = m.get("version")
        if m.get("comprobacion") == "anthropic" and m.get("version_variable") == "PULLEX_MODELO":
            version = entorno.get("modelo") or version
        elif m.get("comprobacion") == "anthropic_boletin":
            version = entorno.get("modelo_boletin") or version
        salida.append({**m, "version_en_uso": version, "costo": costo,
                       "disponibilidad": _disponibilidad(m.get("comprobacion") or "siempre", entorno)})
    return {
        "version": datos.get("version"), "que_es": datos.get("que_es"), "como_se_levanto": datos.get("como_se_levanto"),
        "advertencia_pruebas": datos.get("advertencia_pruebas"), "motores": salida,
        "no_configurados": datos.get("no_configurados") or [], "verificaciones": verificaciones,
        "consultado": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
