"""Benchmark de calidad jurídica de PULLEX IA contra evaluacion/golden.jsonl.

Corre cada pregunta contra el modelo con el MISMO mensaje de sistema del chat (SYSTEM_PROMPT, agentes,
fragmentos del corpus si hay índice, reglas de cita) y califica la respuesta por criterio:

- debe_contener: cada idea debe aparecer (cada ítem admite alternativas separadas por "|"; se compara
  sin tildes ni mayúsculas, desde el inicio de una palabra).
- no_debe_contener: ninguna de esas frases debe aparecer (muletillas, premisas falsas aceptadas,
  advertencia legal donde no corresponde).
- trampa: las preguntas con premisa falsa, sentencia inexistente, norma derogada, falta de hechos o
  pedido indebido se reportan aparte.

Uso:
    ANTHROPIC_API_KEY=sk-ant-...  python evaluacion/benchmark.py                 # modelo real
    python evaluacion/benchmark.py --simulado                                  # sin clave ni costo
    python evaluacion/benchmark.py --limite 5 --web --modelo claude-haiku-4-5

El modo --simulado usa un modelo de mentira que repite la pregunta: sirve para probar el arnés y el
formato del reporte, NO mide calidad. La calificación automática es una aproximación por palabras
clave: revisa a mano las fallas antes de sacar conclusiones (HUMAN REVIEW REQUIRED).
"""
import argparse
import json
import os
import re
import sys
import tempfile
import time
import types
import unicodedata
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
GOLDEN = RAIZ / "evaluacion" / "golden.jsonl"


# --------------------------------------------------------------- calificación --
def normalizar(texto: str) -> str:
    t = "".join(c for c in unicodedata.normalize("NFD", str(texto or "")) if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", t.lower())


def aparece(item: str, respuesta_norm: str) -> bool:
    for alt in (a.strip() for a in item.split("|")):
        if not alt:
            continue
        a = normalizar(alt)
        patron = (r"(?<![a-z0-9])" if a[:1].isalnum() else "") + re.escape(a)
        if re.search(patron, respuesta_norm):
            return True
    return False


def calificar(pregunta: dict, respuesta: str) -> dict:
    rn = normalizar(respuesta)
    faltan = [i for i in pregunta.get("debe_contener", []) if not aparece(i, rn)]
    sobran = [i for i in pregunta.get("no_debe_contener", []) if aparece(i, rn)]
    return {"id": pregunta["id"], "area": pregunta.get("area"), "trampa": pregunta.get("trampa"),
            "debe_total": len(pregunta.get("debe_contener", [])), "debe_ok": len(pregunta.get("debe_contener", [])) - len(faltan),
            "faltan": faltan, "prohibidas_encontradas": sobran, "aprobada": not faltan and not sobran}


def resumir(resultados: list) -> dict:
    def tasa(xs):
        return {"aprobadas": sum(1 for r in xs if r["aprobada"]), "total": len(xs)}
    por_area, por_trampa = {}, {}
    for r in resultados:
        por_area.setdefault(r["area"] or "?", []).append(r)
        if r["trampa"]:
            por_trampa.setdefault(r["trampa"], []).append(r)
    return {
        "total": tasa(resultados),
        "criterios": {
            "debe_contener": {"ideas_presentes": sum(r["debe_ok"] for r in resultados),
                              "ideas_esperadas": sum(r["debe_total"] for r in resultados)},
            "no_debe_contener": {"preguntas_con_violacion": sum(1 for r in resultados if r["prohibidas_encontradas"])},
            "trampas": tasa([r for r in resultados if r["trampa"]]),
            "sin_trampa": tasa([r for r in resultados if not r["trampa"]]),
        },
        "por_area": {k: tasa(v) for k, v in sorted(por_area.items())},
        "por_tipo_de_trampa": {k: tasa(v) for k, v in sorted(por_trampa.items())},
    }


def reporte_md(meta: dict, resumen: dict, resultados: list) -> str:
    c = resumen["criterios"]
    l = [f"# Benchmark PULLEX — {meta['fecha']}", "",
         f"Modelo: `{meta['modelo']}` · modo: {meta['modo']} · búsqueda web: {'sí' if meta['web'] else 'no'} · "
         f"corpus: {'sí' if meta['corpus'] else 'no'}", "",
         f"**Aprobadas: {resumen['total']['aprobadas']} / {resumen['total']['total']}**", "",
         "| Criterio | Resultado |", "|---|---|",
         f"| Ideas obligatorias presentes | {c['debe_contener']['ideas_presentes']} / {c['debe_contener']['ideas_esperadas']} |",
         f"| Preguntas con frases prohibidas | {c['no_debe_contener']['preguntas_con_violacion']} |",
         f"| Trampas superadas | {c['trampas']['aprobadas']} / {c['trampas']['total']} |",
         f"| Preguntas sin trampa aprobadas | {c['sin_trampa']['aprobadas']} / {c['sin_trampa']['total']} |", "",
         "## Por área", "", "| Área | Aprobadas |", "|---|---|"]
    l += [f"| {a} | {v['aprobadas']} / {v['total']} |" for a, v in resumen["por_area"].items()]
    l += ["", "## Por tipo de trampa", "", "| Trampa | Aprobadas |", "|---|---|"]
    l += [f"| {a} | {v['aprobadas']} / {v['total']} |" for a, v in resumen["por_tipo_de_trampa"].items()]
    l += ["", "## Fallas", ""]
    fallas = [r for r in resultados if not r["aprobada"]]
    if not fallas:
        l.append("Ninguna.")
    for r in fallas:
        partes = []
        if r["faltan"]:
            partes.append("faltó: " + "; ".join(r["faltan"]))
        if r["prohibidas_encontradas"]:
            partes.append("apareció: " + "; ".join(r["prohibidas_encontradas"]))
        l.append(f"- **{r['id']}** ({r['area']}{', trampa ' + r['trampa'] if r['trampa'] else ''}): " + " · ".join(partes))
    l += ["", "_Calificación automática por palabras clave: revisa las fallas a mano antes de concluir._"]
    return "\n".join(l) + "\n"


# --------------------------------------------------------------- modelo --
class _ModeloSimulado:
    """Repite la pregunta. Prueba el arnés sin clave ni costo; no mide calidad."""

    def __init__(self, *a, **k):
        self.messages = types.SimpleNamespace(create=self._create, stream=None)

    def _create(self, **k):
        pregunta = k["messages"][-1]["content"]
        return types.SimpleNamespace(content=[types.SimpleNamespace(type="text", text="Respuesta simulada: " + pregunta)])


def _cargar_app(simulado: bool):
    """Importa app.py en un directorio temporal (como las pruebas): no toca pullex.db real."""
    trabajo = Path(tempfile.mkdtemp(prefix="pullex-bench-"))
    (trabajo / "static").symlink_to(RAIZ / "static")
    os.environ.setdefault("PULLEX_ADMIN_CLAVE", os.urandom(12).hex())
    os.environ.setdefault("PULLEX_SECRET", os.urandom(16).hex())
    if "PULLEX_CORPUS_DB" not in os.environ and (RAIZ / "corpus" / "corpus.db").exists():
        os.environ["PULLEX_CORPUS_DB"] = str(RAIZ / "corpus" / "corpus.db")
    if simulado:
        os.environ.setdefault("ANTHROPIC_API_KEY", "simulado")
    cwd = os.getcwd()
    os.chdir(trabajo)
    sys.path.insert(0, str(RAIZ))
    try:
        import app  # noqa
    finally:
        os.chdir(cwd)
    return app


def responder(app, cliente, pregunta: str, modelo: str, web: bool) -> dict:
    din = f"Fecha de hoy: {app.fecha_hoy()} (UTC)." + app.enrutar_agentes(pregunta)
    bloque, frags = app.bloque_corpus(pregunta)
    din += bloque
    system = [{"type": "text", "text": app.SYSTEM_PROMPT}, {"type": "text", "text": din}]
    kw = dict(model=modelo, max_tokens=app.MAX_TOKENS_CHAT, system=system,
              messages=[{"role": "user", "content": pregunta}], **app.opciones_modelo(modelo))
    if web:
        kw["tools"] = [app.herramienta_web()]
    r = cliente.messages.create(**kw)
    texto, citas = [], []
    for b in r.content:
        if getattr(b, "type", "") == "text":
            texto.append(b.text)
            for c in getattr(b, "citations", None) or []:
                if getattr(c, "url", None):
                    citas.append(c.url)
    uso = getattr(r, "usage", None)
    return {"texto": "".join(texto), "citas_web": sorted(set(citas)),
            "fragmentos": [f["ref"] + " " + f["titulo"] for f in frags],
            "tokens": {"entrada": getattr(uso, "input_tokens", None), "salida": getattr(uso, "output_tokens", None)}}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--golden", default=str(GOLDEN))
    ap.add_argument("--modelo", default=None, help="por defecto el del chat (PULLEX_MODELO o claude-sonnet-5-5)")
    ap.add_argument("--simulado", action="store_true", help="sin API: modelo que repite la pregunta")
    ap.add_argument("--web", action="store_true", help="activar la búsqueda web restringida (cuesta más)")
    ap.add_argument("--limite", type=int, default=0, help="solo las primeras N preguntas")
    ap.add_argument("--salida", default=str(RAIZ / "evaluacion" / "resultados"))
    a = ap.parse_args(argv)

    if not a.simulado and not os.getenv("ANTHROPIC_API_KEY"):
        print("Falta ANTHROPIC_API_KEY. Este benchmark llama al modelo real (cuesta dinero).\n"
              "Define la variable con tu clave o usa --simulado para probar el arnés sin costo.", file=sys.stderr)
        return 2
    preguntas = [json.loads(l) for l in Path(a.golden).read_text(encoding="utf-8").splitlines() if l.strip()]
    if a.limite:
        preguntas = preguntas[:a.limite]
    app = _cargar_app(a.simulado)
    modelo = a.modelo or app.MODELO
    if a.simulado:
        cliente = _ModeloSimulado()
    else:
        import anthropic
        cliente = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        print(f"Corriendo {len(preguntas)} preguntas contra {modelo} (costo aproximado con Sonnet 5.5: "
              f"~0,03 USD por pregunta sin búsqueda web).", file=sys.stderr)

    resultados, respuestas = [], []
    for p in preguntas:
        t0 = time.time()
        try:
            r = responder(app, cliente, p["pregunta"], modelo, a.web)
        except Exception as e:  # una falla de red no tumba el resto
            r = {"texto": "", "error": f"{type(e).__name__}: {str(e)[:200]}", "citas_web": [], "fragmentos": [], "tokens": {}}
        cal = calificar(p, r["texto"])
        if r.get("error"):
            cal["error"] = r["error"]
        resultados.append(cal)
        respuestas.append({"id": p["id"], "pregunta": p["pregunta"], "respuesta": r["texto"], **{k: v for k, v in r.items() if k != "texto"},
                           "segundos": round(time.time() - t0, 1)})
        print(f"{p['id']} {'OK   ' if cal['aprobada'] else 'FALLA'} {p['pregunta'][:70]}", file=sys.stderr)

    meta = {"fecha": datetime.now().strftime("%Y-%m-%d %H:%M"), "modelo": modelo,
            "modo": "simulado" if a.simulado else "real", "web": a.web,
            "corpus": bool(os.getenv("PULLEX_CORPUS_DB")) and Path(os.environ["PULLEX_CORPUS_DB"]).exists()}
    resumen = resumir(resultados)
    salida = Path(a.salida)
    salida.mkdir(parents=True, exist_ok=True)
    nombre = "benchmark-" + datetime.now().strftime("%Y%m%d-%H%M%S") + ("-simulado" if a.simulado else "")
    (salida / (nombre + ".json")).write_text(json.dumps({"meta": meta, "resumen": resumen, "resultados": resultados,
                                                          "respuestas": respuestas}, ensure_ascii=False, indent=1), encoding="utf-8")
    md = reporte_md(meta, resumen, resultados)
    (salida / (nombre + ".md")).write_text(md, encoding="utf-8")
    print(md)
    print(f"Reporte: {salida / (nombre + '.md')}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
