"""J02 — Recuperación de modelos.

Interfaz única: `buscar_modelos(consulta, filtros)`. Hoy consulta el catálogo de documentos.py (203 tipos de
escrito, plantillas generadas por el sistema). La biblioteca de modelos del Drive se conecta con
`registrar_proveedor("biblioteca", funcion)`: la función recibe (consulta, filtros, usuario) y devuelve
candidatos con la misma forma. Este módulo no asume que esa biblioteca exista.

Cada candidato trae las razones de la selección (qué palabras coincidieron y dónde), los requisitos (datos
obligatorios) y su estado de validación. Límite: la similitud textual no demuestra procedencia jurídica.
"""
import re
import unicodedata

import documentos

VERSION = "1.0.0"
PROCEDIMIENTO = "J02"
MAX_CONSULTA = 300
ESTADO_CATALOGO = "PLANTILLA_GENERADA_SIN_REVISION_HUMANA"
_VACIAS = set("a al de del la las el los un una unos unas y o u en con por para que se su sus mi mis me lo le "
              "como contra sobre entre es son fue ser quiero necesito hacer modelo minuta formato escrito "
              "documento plantilla".split())
_PESOS = (("nombre", 4, "el nombre"), ("claves", 3, "las palabras clave"), ("subarea", 2, "el trámite"),
          ("descripcion", 1, "la descripción"), ("area", 1, "el área"))

_PROVEEDORES = {}


def _norm(texto) -> str:
    t = unicodedata.normalize("NFD", str(texto or "").lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9ñ]+", " ", t).strip()


def _raiz(tok: str) -> str:
    """Raíz muy simple para que «tutelas» encuentre «tutela» y «arrendatario», «arrendamiento»."""
    for suf in ("aciones", "acion", "amiento", "imiento", "atario", "ador", "es", "s"):
        if tok.endswith(suf) and len(tok) - len(suf) >= 4:
            return tok[: -len(suf)]
    return tok


def terminos(consulta: str) -> list:
    vistos, salida = set(), []
    for tok in _norm(consulta)[:MAX_CONSULTA].split():
        if len(tok) < 3 or tok in _VACIAS or tok in vistos:
            continue
        vistos.add(tok)
        salida.append(tok)
    return salida[:12]


def registrar_proveedor(nombre: str, funcion) -> None:
    """Punto de extensión: `funcion(consulta, filtros, usuario) -> [candidato, …]`.
    Cada candidato debe traer al menos id, titulo y origen; el proveedor responde por aplicar los permisos del
    usuario ANTES de devolver nombres o extractos."""
    if not callable(funcion):
        raise TypeError("El proveedor debe ser una función.")
    _PROVEEDORES[str(nombre)] = funcion


def quitar_proveedor(nombre: str) -> None:
    _PROVEEDORES.pop(str(nombre), None)


def proveedores() -> list:
    return ["catalogo"] + sorted(_PROVEEDORES)


def _proveedor_catalogo(consulta: str, filtros: dict, usuario=None) -> list:
    toks = terminos(consulta)
    area, para = filtros.get("area") or "", filtros.get("para") or ""
    candidatos = []
    for t in documentos.CATALOGO:
        if area and t["area"] != area:
            continue
        if para and para not in t["para_quien"]:
            continue
        if "funcionario" in filtros and bool(filtros["funcionario"]) != bool(t["borrador_funcionario"]):
            continue
        campos = {k: _norm(t.get(k, "")) for k, _, _ in _PESOS}
        puntaje, razones, hallados = 0, [], set()
        for campo, peso, etiqueta in _PESOS:
            palabras = {_raiz(p) for p in campos[campo].split()}
            dentro = [tok for tok in toks if _raiz(tok) in palabras]
            if dentro:
                puntaje += peso * len(dentro)
                hallados.update(dentro)
                razones.append(f"Coincide en {etiqueta}: {', '.join(dentro)}.")
        if toks and not hallados:
            continue
        cobertura = len(hallados) / len(toks) if toks else 0
        obligatorios = [c["etiqueta"] for c in t["campos"] if c["requerido"]]
        candidatos.append({
            "id": t["id"], "origen": "catalogo_interno", "titulo": t["nombre"], "area": t["area"],
            "subarea": t["subarea"], "finalidad": t["descripcion"], "para_quien": list(t["para_quien"]),
            "puntaje": round(puntaje * (0.5 + cobertura / 2), 2), "cobertura_de_la_consulta": round(cobertura, 2),
            "razones": razones or ["Sin texto de búsqueda: se lista por los filtros indicados."],
            "terminos_sin_coincidencia": [tok for tok in toks if tok not in hallados],
            "requisitos": {"datos_obligatorios": obligatorios,
                           "datos_opcionales": len(t["campos"]) - len(obligatorios),
                           "estructura": list(t["estructura"])},
            "advertencias": list(t["advertencias"]), "notas_de_forma": list(t["notas_de_forma"]),
            "borrador_funcionario": bool(t["borrador_funcionario"]),
            "estado_validacion": ESTADO_CATALOGO, "enlace_original": None,
            "que_adaptar": "Todo el contenido lo redacta el generador con los datos del formulario; revise "
                           "hechos, pretensiones, competencia y cada norma citada."})
    return candidatos


def buscar_modelos(consulta: str, filtros: dict = None, limite: int = 8, usuario=None) -> dict:
    """Candidatos de todos los proveedores registrados, ordenados por puntaje. No decide cuál procede."""
    filtros = dict(filtros) if isinstance(filtros, dict) else {}
    consulta = str(consulta or "")[:MAX_CONSULTA]
    problemas = []
    if filtros.get("area") and filtros["area"] not in documentos.AREAS:
        problemas.append(f"Área desconocida: {filtros['area']!r}.")
    if filtros.get("para") and filtros["para"] not in documentos.PARA_QUIEN:
        problemas.append(f"Destinatario desconocido: {filtros['para']!r}.")
    base = {"procedimiento": PROCEDIMIENTO, "version": VERSION, "consulta": consulta, "filtros": filtros,
            "terminos": terminos(consulta), "proveedores_consultados": [], "errores_de_proveedores": [],
            "candidatos": [], "advertencias": [
                "La similitud entre la consulta y un modelo es textual: no demuestra que el modelo proceda "
                "jurídicamente para el caso.",
                "Los modelos del catálogo interno son plantillas generadas por el sistema, sin revisión de un "
                "profesional; no provienen de la biblioteca de Drive."],
            "juicio_profesional": ["Decidir si el trámite del modelo corresponde al caso, a su etapa y a la "
                                   "autoridad competente."]}
    if problemas:
        return {**base, "estado": "CONTRADICCION", "contradicciones": problemas}
    if not base["terminos"] and not any(filtros.get(k) for k in ("area", "para")) and "funcionario" not in filtros:
        return {**base, "estado": "ABSTENCION",
                "faltantes": ["consulta: describa la finalidad, la materia o el trámite del modelo que busca"]}
    todos = []
    for nombre, fn in [("catalogo", _proveedor_catalogo)] + sorted(_PROVEEDORES.items()):
        try:
            encontrados = fn(consulta, filtros, usuario) or []
            base["proveedores_consultados"].append(nombre)
            for c in encontrados:
                if isinstance(c, dict) and c.get("id") and c.get("titulo"):
                    todos.append({"puntaje": 0, "razones": [], "origen": nombre, **c})
        except Exception as e:                       # un proveedor caído no tumba la búsqueda
            base["errores_de_proveedores"].append({"proveedor": nombre, "error": type(e).__name__})
    todos.sort(key=lambda c: (-float(c.get("puntaje") or 0), str(c["titulo"])))
    limite = max(1, min(int(limite or 8), 30))
    base["candidatos"] = todos[:limite]
    base["total_encontrados"] = len(todos)
    if "biblioteca" not in base["proveedores_consultados"]:
        base["advertencias"].append("La biblioteca de modelos de Drive no está conectada a este procedimiento: "
                                    "solo se consultó el catálogo interno.")
    if not todos:
        base["estado"] = "SIN_MODELO_ADECUADO"
        base["advertencias"].insert(0, "No se encontró un modelo que coincida. Si se redacta un escrito, será un "
                                       "borrador nuevo, no una plantilla recuperada.")
    else:
        base["estado"] = "CANDIDATOS"
    return base
