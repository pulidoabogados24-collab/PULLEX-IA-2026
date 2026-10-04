"""Evaluación de los procedimientos deterministas (J05 términos y J06 liquidaciones).

Lee evaluacion/procedimientos.jsonl. Cada caso trae la entrada, el resultado esperado CALCULADO A MANO y la
explicación del cálculo. Los casos están separados en dos conjuntos:

    desarrollo   usados mientras se construía el código (pueden haberse mirado al depurar)
    medicion     reservados para medir: su resultado esperado se fijó a mano antes de ejecutarlos

UMBRAL DE ACEPTACIÓN (fijado el 2026-10-02, antes de medir): 100 % de aciertos en ambos conjuntos. Son cálculos
deterministas: un solo caso errado impide aprobar la capacidad.

Uso:
    python evaluacion/evaluar_procedimientos.py                 # tabla y código de salida 0/1
    python evaluacion/evaluar_procedimientos.py --json          # resumen en JSON
    python evaluacion/evaluar_procedimientos.py --conjunto medicion

Qué se compara: el estado (CALCULADO, ABSTENCION, CONTRADICCION), la fecha de vencimiento o el total, el valor de
cada concepto del desglose, las fechas de los escenarios de una abstención y que «faltantes» nombre el dato
esperado. Este evaluador no usa el modelo de IA ni la red.
"""
import argparse
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
CASOS = RAIZ / "evaluacion" / "procedimientos.jsonl"
UMBRAL = 1.0
CONJUNTOS = ("desarrollo", "medicion")
CATEGORIAS = ("normal", "frontera", "falta_de_datos", "contradiccion")


def cargar(ruta=CASOS) -> list:
    return [json.loads(l) for l in Path(ruta).read_text(encoding="utf-8").splitlines() if l.strip()]


def ejecutar(caso: dict) -> dict:
    from procedimientos import j05_terminos, j06_liquidaciones
    if caso["procedimiento"] == "J05":
        return j05_terminos.calcular(caso["entrada"])
    if caso["procedimiento"] == "J06":
        return j06_liquidaciones.liquidar(caso["entrada"])
    raise ValueError("Procedimiento sin evaluador: " + caso["procedimiento"])


def comparar(caso: dict, obtenido: dict) -> list:
    """Lista de diferencias (vacía = acierto)."""
    esp, dif = caso["esperado"], []
    if obtenido.get("estado") != esp["estado"]:
        dif.append(f"estado: esperado {esp['estado']}, obtenido {obtenido.get('estado')}")
    if "fecha_vencimiento" in esp and obtenido.get("fecha_vencimiento") != esp["fecha_vencimiento"]:
        dif.append(f"fecha: esperada {esp['fecha_vencimiento']}, obtenida {obtenido.get('fecha_vencimiento')}")
    if "total" in esp and obtenido.get("total") != esp["total"]:
        dif.append(f"total: esperado {esp['total']}, obtenido {obtenido.get('total')}")
    if "desglose" in esp:
        valores = {d["concepto"]: d["valor"] for d in obtenido.get("desglose", [])}
        for concepto, valor in esp["desglose"].items():
            if valores.get(concepto) != valor:
                dif.append(f"{concepto}: esperado {valor}, obtenido {valores.get(concepto)}")
        if set(valores) != set(esp["desglose"]):
            dif.append(f"conceptos: esperados {sorted(esp['desglose'])}, obtenidos {sorted(valores)}")
    if "escenarios" in esp:
        fechas = sorted(e["fecha_vencimiento"] for e in obtenido.get("escenarios", []))
        if fechas != sorted(esp["escenarios"]):
            dif.append(f"escenarios: esperados {sorted(esp['escenarios'])}, obtenidos {fechas}")
    for dato in esp.get("faltantes_contiene", []):
        if not any(dato in str(f) for f in obtenido.get("faltantes", [])):
            dif.append(f"faltantes: no nombra «{dato}» ({obtenido.get('faltantes')})")
    if esp["estado"] != "CALCULADO" and (obtenido.get("fecha_vencimiento") or obtenido.get("total") is not None):
        dif.append("entregó un resultado definitivo cuando debía abstenerse o rechazar la entrada")
    return dif


def evaluar(casos: list) -> dict:
    resultados = []
    for c in casos:
        try:
            dif = comparar(c, ejecutar(c))
        except Exception as e:                                  # un fallo del código es un caso errado
            dif = [f"excepción: {type(e).__name__}: {e}"]
        resultados.append({"id": c["id"], "conjunto": c["conjunto"], "procedimiento": c["procedimiento"],
                           "categoria": c["categoria"], "acierto": not dif, "diferencias": dif})

    def tasa(xs):
        return {"aciertos": sum(1 for r in xs if r["acierto"]), "total": len(xs)}
    resumen = {"umbral": UMBRAL, "total": tasa(resultados), "por_conjunto": {}, "por_procedimiento": {},
               "por_categoria": {}, "errores": [r for r in resultados if not r["acierto"]]}
    for clave, campo, valores in (("por_conjunto", "conjunto", CONJUNTOS),
                                  ("por_procedimiento", "procedimiento", ("J05", "J06")),
                                  ("por_categoria", "categoria", CATEGORIAS)):
        for v in valores:
            resumen[clave][v] = tasa([r for r in resultados if r[campo] == v])
    for conj in CONJUNTOS:
        for proc in ("J05", "J06"):
            resumen["por_conjunto"][f"{conj}/{proc}"] = tasa(
                [r for r in resultados if r["conjunto"] == conj and r["procedimiento"] == proc])
    t = resumen["total"]
    resumen["aprobado"] = t["total"] > 0 and t["aciertos"] / t["total"] >= UMBRAL
    resumen["resultados"] = resultados
    return resumen


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Evalúa J05 y J06 contra casos calculados a mano.")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--conjunto", choices=CONJUNTOS)
    a = ap.parse_args(argv)
    casos = [c for c in cargar() if not a.conjunto or c["conjunto"] == a.conjunto]
    r = evaluar(casos)
    if a.json:
        print(json.dumps({k: v for k, v in r.items() if k != "resultados"}, ensure_ascii=False, indent=1))
    else:
        print(f"Umbral de aceptación (fijado antes de medir): {int(UMBRAL * 100)} % en cálculos deterministas\n")
        for titulo, clave in (("Por conjunto", "por_conjunto"), ("Por procedimiento", "por_procedimiento"),
                              ("Por categoría", "por_categoria")):
            print(titulo + ":")
            for k, v in r[clave].items():
                if v["total"]:
                    print(f"  {k:<22} {v['aciertos']}/{v['total']}")
        print(f"\nTOTAL {r['total']['aciertos']}/{r['total']['total']} — " + ("APROBADO" if r["aprobado"] else "NO APROBADO"))
        for e in r["errores"]:
            print(f"  ERROR {e['id']}: " + "; ".join(e["diferencias"]))
    return 0 if r["aprobado"] else 1


if __name__ == "__main__":
    sys.exit(main())
