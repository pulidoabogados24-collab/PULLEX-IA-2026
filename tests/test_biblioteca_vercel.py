"""Regresión: rutas SQLite de Biblioteca en despliegues de Vercel (PUL-019).

No usa datos reales del catálogo ni credenciales. El test de escritura usa
una ruta aislada para no interferir con otras instancias o suites de prueba.
"""
import os
from contextlib import closing

import biblioteca


def test_vercel_usa_tmp_si_falta_variable(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("VERCEL", "1")
    monkeypatch.delenv("PULLEX_BIBLIOTECA_DB", raising=False)
    assert biblioteca.ruta_db() == "/tmp/biblioteca.db"
    assert not (tmp_path / "biblioteca" / "biblioteca.db").exists()


def test_variable_explicita_tiene_prioridad_y_sqlite_es_escribible(monkeypatch, tmp_path):
    ruta = tmp_path / "biblioteca.db"
    monkeypatch.setenv("VERCEL", "1")
    monkeypatch.setenv("PULLEX_BIBLIOTECA_DB", str(ruta))
    with closing(biblioteca.conexion()) as con:
        assert con.execute(
            "select name from sqlite_master where type='table' and name='biblioteca_modelos'"
        ).fetchone()["name"] == "biblioteca_modelos"
    assert ruta.is_file()


def test_fuera_de_vercel_conserva_ruta_local(monkeypatch):
    monkeypatch.delenv("VERCEL", raising=False)
    monkeypatch.delenv("PULLEX_BIBLIOTECA_DB", raising=False)
    assert biblioteca.ruta_db() == os.path.join("biblioteca", "biblioteca.db")
