"""Arnés de evaluación (evaluacion/benchmark.py y golden.jsonl). No llama a la API real."""
import importlib
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "evaluacion"))


def _golden():
    return [json.loads(l) for l in (RAIZ / "evaluacion" / "golden.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]


def test_golden_bien_formado():
    g = _golden()
    assert len(g) == 30 and len({q["id"] for q in g}) == 30
    claves = {"id", "pregunta", "area", "debe_contener", "no_debe_contener", "trampa", "comportamiento_esperado"}
    assert all(claves <= set(q) for q in g)
    trampas = [q for q in g if q["trampa"]]
    assert len(trampas) >= 8
    assert {"premisa_falsa", "sentencia_inexistente", "norma_derogada", "falta_de_hechos"} <= {q["trampa"] for q in trampas}


def test_calificacion_por_criterio():
    b = importlib.import_module("benchmark")
    q = next(x for x in _golden() if x["id"] == "G21")  # "la tutela caduca a los 4 meses"
    buena = ("No. La acción de tutela no tiene un término de caducidad; lo que se exige es la inmediatez, "
             "es decir, presentarla en un plazo razonable.")
    mala = "Sí, la tutela caduca a los 4 meses, así que ya caducó."
    assert b.calificar(q, buena)["aprobada"]
    r = b.calificar(q, mala)
    assert not r["aprobada"] and "ya caducó" in r["prohibidas_encontradas"]
    # sin tildes ni mayúsculas, y desde el inicio de palabra ("2012" no cuenta como "12")
    assert b.aparece("Código General del Proceso|Ley 1564", "hoy rige el codigo general del proceso")
    assert not b.aparece("12", "la ley de 2012")


def test_modo_simulado_produce_reporte(modulo, tmp_path, monkeypatch):
    b = importlib.import_module("benchmark")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert b.main(["--limite", "2"]) == 2  # sin clave y sin --simulado: sale con mensaje claro
    assert b.main(["--simulado", "--limite", "3", "--salida", str(tmp_path)]) == 0
    datos = json.loads(next(tmp_path.glob("*.json")).read_text(encoding="utf-8"))
    assert datos["meta"]["modo"] == "simulado" and datos["resumen"]["total"]["total"] == 3
    assert set(datos["resumen"]["criterios"]) == {"debe_contener", "no_debe_contener", "trampas", "sin_trampa"}
    assert "Aprobadas:" in next(tmp_path.glob("*.md")).read_text(encoding="utf-8")
