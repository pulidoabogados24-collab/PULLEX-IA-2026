"""Genera docs/procedimientos/REGISTRO-DE-REGLAS.md a partir de reglas/registro.json.

    python scripts/tabla_reglas.py            # escribe el archivo
    python scripts/tabla_reglas.py --comprobar  # sale con 1 si el archivo no coincide con el registro

La fuente de verdad es el JSON; el Markdown es una vista para leer.
"""
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
import reglas  # noqa: E402

SALIDA = RAIZ / "docs" / "procedimientos" / "REGISTRO-DE-REGLAS.md"
ETIQUETA = {reglas.VERIFICADA: "VERIFICADA", reglas.NO_VERIFICADO: "NO VERIFICADO",
            reglas.REVISION_PENDIENTE: "REVISIÓN HUMANA PENDIENTE"}


def _celda(texto) -> str:
    return str(texto or "—").replace("|", "\\|").replace("\n", " ")


def generar() -> str:
    res = reglas.resumen()
    lineas = [
        "# Registro de reglas jurídicas",
        "",
        "Vista de `reglas/registro.json` (versión " + res["version_registro"] + ", actualizado el " + res["actualizado"] +
        "). Generada con `python scripts/tabla_reglas.py`; no se edita a mano.",
        "",
        "| Estado | Versiones de regla |",
        "|---|---|",
    ]
    for estado in reglas.ESTADOS:
        lineas.append(f"| {ETIQUETA[estado]} | {res['por_estado'][estado]} |")
    lineas += [
        f"| **Total** | **{res['total_versiones']}** ({res['reglas_distintas']} reglas distintas) |",
        "",
        f"Las {res['verificadas_con_enlace']} versiones verificadas tienen enlace a una fuente oficial y fecha de "
        "consulta. Una regla sin fecha «desde» comprobada solo está verificada el día de la consulta: los "
        "procedimientos lo advierten cuando calculan para otra fecha.",
        "",
        "Cómo se consulta: `reglas.vigente(id, fecha)` devuelve la versión cuyo período contiene la fecha; no existe "
        "«la regla vigente» sin fecha. `GET /api/reglas?fecha=AAAA-MM-DD` hace lo mismo por HTTP.",
        "",
        "## Reglas",
        "",
        "| Regla | V. | Título | Norma de soporte | Vigencia | Estado | Usan | Fuente (consulta) |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in reglas.todas():
        s = r["soporte"]
        norma = s["identificador"] + ("" if s["articulo"] in ("—", "", None) else f", art. {s['articulo']}")
        v = r["vigencia"]
        desde = v["desde"] or "sin comprobar"
        vigencia = f"{desde} → {v['hasta'] or 'sin fin registrado'}"
        fuente = f"[enlace]({r['enlace']}) ({r['consultado']})" if r.get("enlace") else "—"
        lineas.append("| " + " | ".join(_celda(x) for x in (
            r["id"], r["version"], r["titulo"], norma, vigencia, ETIQUETA[r["estado"]],
            ", ".join(r["procedimientos"]), fuente)) + " |")
    pendientes = [r for r in reglas.todas() if r["estado"] != reglas.VERIFICADA]
    lineas += ["", "## Lo que falta verificar", ""]
    for r in pendientes:
        lineas.append(f"- **{r['id']} v{r['version']} — {r['titulo']}** ({ETIQUETA[r['estado']]}). {r['notas']}")
    juicio = [r for r in reglas.todas() if r.get("requiere_juicio_profesional")]
    lineas += ["", "## Reglas verificadas cuyo uso exige juicio profesional", ""]
    for r in juicio:
        lineas.append(f"- **{r['id']} v{r['version']}**: {r['requiere_juicio_profesional']}")
    lineas += ["", "## Discrepancias y citas indirectas entre fuentes", ""]
    vistas = {}
    for r in reglas.todas():
        for s in r.get("soportes_adicionales", []):
            if s.get("nota") and ("no menciona" in s["nota"] or "solo por la cita" in s["nota"]):
                vistas.setdefault((s["identificador"], s["nota"]), []).append(f"{r['id']} v{r['version']}")
    for (identificador, nota), ids in vistas.items():
        lineas.append(f"- **{', '.join(ids)}** — {identificador}: {nota}")
    return "\n".join(lineas) + "\n"


if __name__ == "__main__":
    texto = generar()
    if "--comprobar" in sys.argv:
        sys.exit(0 if SALIDA.exists() and SALIDA.read_text(encoding="utf-8") == texto else 1)
    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    SALIDA.write_text(texto, encoding="utf-8")
    print(SALIDA, len(texto.splitlines()), "líneas")
