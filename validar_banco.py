"""Valida el banco curado de casos del Laboratorio de casos (academia_banco/*.json).

    python scripts/validar_banco.py            → informe legible; sale con 1 si hay errores
    python scripts/validar_banco.py --json     → el mismo informe en JSON

Revisa estructura, conteos por área y nivel, longitudes, que cada concepto empareje con un nodo del
Mapa del Derecho (`academia.emparejar`), que la respuesta modelo sea prosa con conectores reales y
que no aparezcan números de sentencias fuera de una lista blanca. NO verifica la exactitud jurídica:
eso exige revisión docente (todos los casos llevan revision_humana: true).
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
import academia  # noqa: E402

AREAS = ["Constitucional", "Penal", "Civil", "Laboral", "Administrativo", "Comercial",
         "Familia", "Procesal", "Probatorio"]
ARCHIVOS = {"Constitucional": "constitucional.json", "Penal": "penal.json", "Civil": "civil.json",
            "Laboral": "laboral.json", "Administrativo": "administrativo.json", "Comercial": "comercial.json",
            "Familia": "familia.json", "Procesal": "procesal.json", "Probatorio": "probatorio.json"}
POR_NIVEL = {"basico": 6, "intermedio": 6, "avanzado": 5, "experto": 3}
CASOS_POR_AREA = sum(POR_NIVEL.values())  # 20
PALABRAS_ENUNCIADO = (120, 220)
PALABRAS_RESPUESTA = (250, 400)
MIN_CONECTORES = 6          # conectores distintos detectados en la respuesta modelo
MIN_CATEGORIAS = 4          # categorías distintas de conectores en la respuesta modelo
# Únicas sentencias que el banco puede nombrar: muy conocidas y de número seguro.
SENTENCIAS_PERMITIDAS = {"C-355 de 2006", "T-760 de 2008", "SU-214 de 2016"}
RX_SENTENCIA = re.compile(r"\b(?:SU|C|T|A)\s?-\s?\d{1,4}(?:\s?(?:de|/)\s?\d{2,4})?", re.IGNORECASE)
RX_RADICADO = re.compile(r"radicad[oa]s?\s*(?:n\.?\s*º?|no\.?|número)?\s*\d", re.IGNORECASE)
RX_FECHA = re.compile(r"\b(?:\d{1,2} de (?:enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|"
                      r"noviembre|diciembre)|(?:enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|"
                      r"octubre|noviembre|diciembre) de (?:19|20)\d\d|\d{1,2}/\d{1,2}/(?:19|20)\d\d)", re.IGNORECASE)
RX_LISTA = re.compile(r"^\s*(?:[-*•]|\d+[.)])\s", re.MULTILINE)
CAMPOS_SOLUCION = ("problema_juridico", "normas", "analisis", "contraargumento", "conclusion", "errores_comunes")


def palabras(t: str) -> int:
    return len(re.findall(r"\S+", t or ""))


def _textos(caso: dict):
    """Todo el texto de un caso, para buscar sentencias y nombres prohibidos."""
    pila = [caso]
    while pila:
        x = pila.pop()
        if isinstance(x, str):
            yield x
        elif isinstance(x, dict):
            pila.extend(x.values())
        elif isinstance(x, list):
            pila.extend(x)


def validar(directorio=None) -> dict:
    d = Path(directorio) if directorio else academia.BANCO_DIR
    errores, avisos = [], []
    sin_emparejar, cobertura, conteo = [], Counter(), {}
    ids = Counter()
    stats = {"enunciado": [], "respuesta_modelo": []}
    sentencias_citadas = Counter()
    for area in AREAS:
        ruta = d / ARCHIVOS[area]
        if not ruta.is_file():
            errores.append(f"falta el archivo {ruta.name}")
            continue
        try:
            datos = json.loads(ruta.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            errores.append(f"{ruta.name}: JSON inválido ({e})")
            continue
        if datos.get("area") != area:
            errores.append(f"{ruta.name}: el campo area debe ser {area!r}")
        casos = datos.get("casos") or []
        niveles = Counter(c.get("nivel") for c in casos)
        conteo[area] = dict(niveles)
        if len(casos) != CASOS_POR_AREA:
            errores.append(f"{area}: tiene {len(casos)} casos (deben ser {CASOS_POR_AREA})")
        for n, k in POR_NIVEL.items():
            if niveles.get(n, 0) != k:
                errores.append(f"{area}: {niveles.get(n, 0)} casos de nivel {n} (deben ser {k})")
        for c in casos:
            cid = c.get("id") or "?"
            ids[cid] += 1
            e = lambda m: errores.append(f"{cid}: {m}")  # noqa: E731
            if c.get("area") != area:
                e(f"area {c.get('area')!r} distinta de la del archivo ({area})")
            if c.get("nivel") not in POR_NIVEL:
                e(f"nivel inválido {c.get('nivel')!r}")
            for k in ("titulo", "enunciado", "pregunta", "respuesta_modelo"):
                if not isinstance(c.get(k), str) or not c[k].strip():
                    e(f"falta {k}")
            n_en, n_rm = palabras(c.get("enunciado")), palabras(c.get("respuesta_modelo"))
            stats["enunciado"].append(n_en)
            stats["respuesta_modelo"].append(n_rm)
            if not PALABRAS_ENUNCIADO[0] <= n_en <= PALABRAS_ENUNCIADO[1]:
                e(f"enunciado de {n_en} palabras (rango {PALABRAS_ENUNCIADO[0]}-{PALABRAS_ENUNCIADO[1]})")
            if not PALABRAS_RESPUESTA[0] <= n_rm <= PALABRAS_RESPUESTA[1]:
                e(f"respuesta_modelo de {n_rm} palabras (rango {PALABRAS_RESPUESTA[0]}-{PALABRAS_RESPUESTA[1]})")
            if not RX_FECHA.search(c.get("enunciado") or ""):
                e("el enunciado no trae hechos con fecha")
            if not str(c.get("pregunta") or "").strip().endswith("?"):
                e("la pregunta debe terminar en «?»")
            if c.get("nivel") in ("avanzado", "experto") and not str(c.get("distractor") or "").strip():
                e("los niveles avanzado y experto deben declarar su hecho distractor en «distractor»")
            pistas = c.get("pistas")
            if not (isinstance(pistas, list) and len(pistas) == 2 and all(isinstance(p, str) and p.strip() for p in pistas)):
                e("debe tener exactamente 2 pistas")
            conceptos = c.get("conceptos")
            if not (isinstance(conceptos, list) and 2 <= len(conceptos) <= 4):
                e("debe tener de 2 a 4 conceptos")
                conceptos = conceptos if isinstance(conceptos, list) else []
            for t in conceptos:
                nodo = academia.emparejar(t, area)
                if nodo:
                    cobertura[nodo] += 1
                else:
                    sin_emparejar.append(f"{cid}: «{t}»")
            sol = c.get("solucion")
            if not isinstance(sol, dict):
                e("falta solucion")
                sol = {}
            for k in CAMPOS_SOLUCION:
                if not sol.get(k):
                    e(f"solucion.{k} vacío")
            normas = sol.get("normas") or []
            if not all(isinstance(x, dict) and str(x.get("norma") or "").strip() and str(x.get("para_que") or "").strip()
                       for x in normas):
                e("cada norma de la solución necesita «norma» y «para_que»")
            if len(sol.get("errores_comunes") or []) < 2:
                e("solucion.errores_comunes debe traer al menos 2 errores")
            rm = c.get("respuesta_modelo") or ""
            if RX_LISTA.search(rm):
                e("la respuesta modelo debe ser prosa, sin listas")
            det = academia.detectar_conectores(rm)
            frases = {x["frase"] for x in det}
            cats = {x["categoria"] for x in det}
            if len(frases) < MIN_CONECTORES or len(cats) < MIN_CATEGORIAS:
                e(f"la respuesta modelo usa {len(frases)} conectores de {len(cats)} categorías "
                  f"(mínimo {MIN_CONECTORES} y {MIN_CATEGORIAS})")
            usados = c.get("conectores_usados")
            if not isinstance(usados, list) or len(usados) < MIN_CONECTORES:
                e(f"conectores_usados debe listar al menos {MIN_CONECTORES} conectores")
                usados = usados if isinstance(usados, list) else []
            for u in usados:
                if academia.normalizar(u) not in {academia.normalizar(f) for f in frases}:
                    e(f"conectores_usados incluye «{u}», que no aparece como conector en la respuesta modelo")
            var = c.get("variacion")
            if not (isinstance(var, dict) and str(var.get("cambio") or "").startswith("¿Qué cambia si")
                    and str(var.get("cambio") or "").strip().endswith("?") and str(var.get("respuesta") or "").strip()):
                e("variacion debe tener «cambio» (¿Qué cambia si…?) y «respuesta»")
            if c.get("revision_humana") is not True:
                e("revision_humana debe ser true")
            for t in _textos(c):
                for m in RX_SENTENCIA.finditer(t):
                    s = re.sub(r"\s+", " ", m.group(0)).replace(" -", "-").replace("- ", "-")
                    if re.fullmatch(r"(?:SU|C|T|A)-\d{1,4} de \d{4}", s, re.IGNORECASE) and s in SENTENCIAS_PERMITIDAS:
                        sentencias_citadas[s] += 1
                    else:
                        e(f"cita una sentencia fuera de la lista blanca: «{m.group(0)}»")
                if RX_RADICADO.search(t):
                    e("menciona un número de radicado")
                if re.search(r"universidad", t, re.IGNORECASE):
                    e("menciona una universidad (prohibido en el banco)")
    for cid, n in ids.items():
        if n > 1:
            errores.append(f"id repetido: {cid} ({n} veces)")
    sin_cubrir = sorted(cid for cid in academia.INDICE if cid not in cobertura)
    if sin_cubrir:
        avisos.append("conceptos del mapa sin ningún caso en el banco: " + ", ".join(sin_cubrir))
    resumen = lambda xs: {"min": min(xs), "max": max(xs), "promedio": round(sum(xs) / len(xs))} if xs else None  # noqa: E731
    return {"ok": not errores and not sin_emparejar, "errores": errores, "avisos": avisos,
            "conceptos_sin_emparejar": sin_emparejar, "total": sum(ids.values()), "por_area_nivel": conteo,
            "cobertura_mapa": {"cubiertos": len(cobertura), "total": len(academia.INDICE), "sin_cubrir": sin_cubrir},
            "palabras": {k: resumen(v) for k, v in stats.items()},
            "sentencias_citadas": dict(sentencias_citadas)}


def main():
    r = validar()
    if "--json" in sys.argv:
        print(json.dumps(r, ensure_ascii=False, indent=2))
    else:
        print(f"Banco curado: {r['total']} casos")
        for area, niveles in r["por_area_nivel"].items():
            print(f"  {area:15s} " + "  ".join(f"{n}={niveles.get(n, 0)}" for n in POR_NIVEL))
        cm = r["cobertura_mapa"]
        print(f"Conceptos del mapa cubiertos: {cm['cubiertos']}/{cm['total']}")
        print(f"Palabras: {r['palabras']}")
        print(f"Sentencias citadas (lista blanca): {r['sentencias_citadas'] or 'ninguna'}")
        print(f"Conceptos que no emparejan con el mapa: {len(r['conceptos_sin_emparejar'])}")
        for x in r["conceptos_sin_emparejar"]:
            print("  -", x)
        for x in r["avisos"]:
            print("AVISO:", x)
        for x in r["errores"]:
            print("ERROR:", x)
        print("RESULTADO:", "VÁLIDO" if r["ok"] else "CON ERRORES",
              "· Exactitud jurídica: NOT VERIFIED (requiere revisión docente)")
    sys.exit(0 if r["ok"] else 1)


if __name__ == "__main__":
    main()
