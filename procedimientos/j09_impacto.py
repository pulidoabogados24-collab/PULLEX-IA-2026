"""J09 — Actualización e impacto.

Dado un cambio COMPROBADO (norma, sentencia o documento, con enlace oficial y fecha de consulta) devuelve:

- las reglas del registro que se apoyan en esa norma o la mencionan;
- los tipos de documento y flujos del catálogo (documentos.py) que la nombran;
- los perfiles del registro de 1.000 perfiles que deberían revisarla (identificadores Axx-Syy-Fzz);
- una PROPUESTA versionada: qué versión cerrar, qué versión nueva crear y con qué estado.

Nunca aplica nada: no escribe en reglas/registro.json, no toca el catálogo ni los documentos guardados de los
usuarios. La propuesta la revisa y aplica una persona. Si el cambio no está comprobado, se abstiene.
"""
import re
import unicodedata
from datetime import date, timedelta

import documentos
import reglas

VERSION = "1.0.0"
PROCEDIMIENTO = "J09"
TIPOS_CAMBIO = ("norma", "sentencia", "documento")
FUNCIONES_REVISORAS = ("F04", "F08", "F09")      # verificación de versiones, pruebas y revisión independiente

# Materia de la regla → subespecialidades del registro de perfiles (docs/coordinacion/ESPECIFICACION-LEXCOL.md, § 6).
PERFILES_POR_MATERIA = {
    "procesal": ["A10-S02", "A10-S08"], "general": ["A10-S02"], "derecho de peticion": ["A10-S06", "A07-S02"],
    "tutela": ["A10-S05", "A07-S01"], "laboral": ["A09-S02", "A09-S03", "A09-S04"], "civil": ["A06-S01", "A06-S02"],
    "comercial": ["A06-S06"], "civil y comercial": ["A06-S02", "A06-S06"], "financiera": ["A06-S02"],
    "constitucional": ["A07-S01"], "administrativo": ["A07-S02"],
}
PERFILES_POR_AREA = {
    "Constitucional": ["A07-S01", "A10-S05", "A10-S06"], "Civil y Familia": ["A06-S01", "A06-S04"],
    "Comercial y Societario": ["A06-S06", "A06-S07"], "Laboral y Seguridad Social": ["A09-S01", "A09-S03", "A09-S07"],
    "Penal y Procesal Penal": ["A08-S02"], "Administrativo y Contratación Estatal": ["A07-S02", "A07-S03"],
    "Disciplinario": ["A07-S04"], "Tributario": ["A07-S06"], "Consumidor": ["A06-S08"],
    "Propiedad Intelectual": ["A06-S10"], "Policivo": ["A07-S02"], "Notarial": ["A06-S01"],
    "Insolvencia": ["A06-S06"], "Despachos judiciales y funcionarios": ["A10-S10"],
    "Consultorio jurídico": ["A10-S10"],
}
_NOMBRES_CODIGOS = {
    "ley 1564 de 2012": ["codigo general del proceso"], "ley 1437 de 2011": ["cpaca", "codigo de procedimiento administrativo"],
    "decreto 410 de 1971": ["codigo de comercio"], "decreto 624 de 1989": ["estatuto tributario"],
    "ley 599 de 2000": ["codigo penal"], "ley 906 de 2004": ["codigo de procedimiento penal"],
    "ley 1098 de 2006": ["codigo de la infancia"], "ley 1480 de 2011": ["estatuto del consumidor"],
}


def _norm(texto) -> str:
    t = unicodedata.normalize("NFD", str(texto or "").lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return " " + re.sub(r"[^a-z0-9ñ]+", " ", t).strip() + " "


def _claves(identificador: str) -> list:
    """Formas con que la norma puede aparecer escrita en el catálogo y en el registro."""
    n = _norm(identificador).strip()
    claves = []
    m = re.search(r"\b(ley|decreto)(?: legislativo| ley)? (\d{1,5}) de (\d{4})\b", n)
    if m:
        base = f"{m.group(1)} {m.group(2)} de {m.group(3)}"
        claves.append(base)
        claves += _NOMBRES_CODIGOS.get(base, [])
    m = re.search(r"\b(c|t|su) (\d{1,4}) de (\d{4})\b", n)
    if m:
        claves.append(f"{m.group(1)} {m.group(2)} de {m.group(3)}")
    for nombre in ("codigo sustantivo del trabajo", "codigo civil", "codigo de comercio", "codigo general del proceso",
                   "constitucion politica"):
        if nombre in n:
            claves.append(nombre)
    if not claves and len(n) >= 6:
        claves.append(n)
    return list(dict.fromkeys(claves))


def _perfiles(prefijos: list) -> list:
    return [f"{p}-{f}" for p in sorted(set(prefijos)) for f in FUNCIONES_REVISORAS]


def impacto(cambio: dict, hoy: date = None) -> dict:
    cambio = cambio if isinstance(cambio, dict) else {}
    hoy = hoy or date.today()
    faltantes, contradicciones = [], []
    tipo = str(cambio.get("tipo") or "").strip().lower()
    identificador = str(cambio.get("identificador") or "").strip()[:200]
    articulo = str(cambio.get("articulo") or "").strip()[:40]
    enlace = str(cambio.get("enlace") or "").strip()[:500]
    if not tipo:
        faltantes.append("tipo (norma, sentencia o documento)")
    elif tipo not in TIPOS_CAMBIO:
        contradicciones.append("«tipo» debe ser norma, sentencia o documento.")
    if not identificador:
        faltantes.append("identificador (por ejemplo «Ley 2578 de 2026»)")
    if cambio.get("comprobado") is not True:
        faltantes.append("comprobado: el cambio debe estar comprobado en la fuente por una persona")
    if not enlace:
        faltantes.append("enlace: dirección de la fuente donde se comprobó el cambio")
    elif tipo in ("norma", "sentencia") and not reglas.es_enlace_oficial(enlace):
        faltantes.append("enlace oficial: una norma o sentencia se comprueba en la fuente oficial que la publica")
    f_consulta = f_efecto = None
    for campo, obligatorio in (("fecha_consulta", True), ("fecha_efecto", True)):
        v = cambio.get(campo)
        if v in (None, ""):
            if obligatorio:
                faltantes.append(campo + (": desde cuándo rige o produce efectos el cambio" if campo == "fecha_efecto"
                                          else ": cuándo se consultó la fuente"))
            continue
        try:
            f = reglas.a_fecha(v)
            if campo == "fecha_consulta":
                f_consulta = f
            else:
                f_efecto = f
        except (ValueError, TypeError):
            contradicciones.append(f"«{campo}»: la fecha {v!r} no existe o no es AAAA-MM-DD.")
    if f_consulta and f_consulta > hoy:
        contradicciones.append("La fecha de consulta es futura.")
    base = {"procedimiento": PROCEDIMIENTO, "version": VERSION, "aplicado": False,
            "cambio": {"tipo": tipo or None, "identificador": identificador or None, "articulo": articulo or None,
                       "descripcion": str(cambio.get("descripcion") or "")[:1000], "enlace": enlace or None,
                       "fecha_consulta": f_consulta.isoformat() if f_consulta else None,
                       "fecha_efecto": f_efecto.isoformat() if f_efecto else None},
            "reglas_afectadas": [], "tipos_de_documento_afectados": [], "flujos_afectados": [],
            "perfiles_afectados": [], "propuesta": [], "faltantes": faltantes, "contradicciones": contradicciones,
            "limite": "No se modifica nada en silencio: ni el registro, ni el catálogo, ni los documentos de los "
                      "usuarios. Todo lo de «propuesta» requiere revisión y aplicación por una persona."}
    if contradicciones:
        return {**base, "estado": "CONTRADICCION"}
    if faltantes:
        return {**base, "estado": "ABSTENCION",
                "advertencias": ["Sin un cambio comprobado no se calcula el impacto ni se propone nada."]}

    claves = _claves(identificador)
    # --- reglas: por su soporte (principal o adicional) o porque el texto de la regla nombra la norma
    consulta = identificador + (f" art. {articulo}" if articulo else "")
    por_soporte = {(r["id"], r["version"]) for r in reglas.buscar_por_norma(consulta)}
    afectadas, prefijos = [], []
    for r in reglas.todas():
        texto = _norm(" ".join([r["enunciado"], r.get("notas", ""), r["soporte"]["identificador"]]))
        mencion = any(f" {c} " in texto for c in claves)
        directa = (r["id"], r["version"]) in por_soporte
        if not (directa or mencion):
            continue
        vigente_al_efecto = reglas.vigente(r["id"], f_efecto)
        es_la_vigente = bool(vigente_al_efecto) and vigente_al_efecto["version"] == r["version"]
        afectadas.append({**reglas.referencia(r), "vigencia": r["vigencia"], "procedimientos": r["procedimientos"],
                          "relacion": "se apoya en la norma" if directa else "la menciona en su texto o notas",
                          "es_la_version_vigente_al_cambio": es_la_vigente})
        prefijos += PERFILES_POR_MATERIA.get(_norm(r["ambito"]["materia"]).strip(), [])

    # --- catálogo de documentos y flujos
    tipos = []
    for t in documentos.CATALOGO:
        donde = []
        for campo, etiqueta in (("notas_de_forma", "notas de forma"), ("advertencias", "advertencias"),
                                ("estructura", "estructura"), ("descripcion", "descripción")):
            valor = t[campo] if isinstance(t[campo], str) else " ".join(t[campo])
            if any(f" {c} " in _norm(valor) for c in claves):
                donde.append(etiqueta)
        if donde:
            tipos.append({"id": t["id"], "nombre": t["nombre"], "area": t["area"], "aparece_en": donde})
            prefijos += PERFILES_POR_AREA.get(t["area"], [])
    flujos = []
    for f in documentos.FLUJOS:
        texto = _norm(" ".join([f.get("nombre", ""), f.get("descripcion", "")] +
                               [p["titulo"] + " " + p["instruccion"] for p in f["pasos"]]))
        if any(f" {c} " in texto for c in claves):
            flujos.append({"id": f["id"], "nombre": f.get("nombre", f["id"])})

    # --- propuesta versionada (no se aplica)
    propuesta = []
    dia_anterior = (f_efecto - timedelta(days=1)).isoformat()
    for a in afectadas:
        if not a["es_la_version_vigente_al_cambio"]:
            continue
        propuesta.append({
            "objeto": "regla", "id": a["id"], "version_actual": a["version"],
            "accion": f"Cerrar la versión {a['version']} con vigencia hasta {dia_anterior} y crear la versión "
                      f"{a['version'] + 1} desde {f_efecto.isoformat()}, si el cambio altera su enunciado o sus "
                      "parámetros; si no lo altera, anotar la revisión y la nueva fecha de consulta.",
            "nueva_version": {"id": a["id"], "version": a["version"] + 1,
                              "vigencia": {"desde": f_efecto.isoformat(), "hasta": None, "desde_comprobado": True},
                              "estado": reglas.REVISION_PENDIENTE, "enlace": enlace,
                              "consultado": f_consulta.isoformat(),
                              "enunciado": "[COMPLETAR: redactar con el texto de la fuente]"},
            "reversible": "La versión anterior se conserva; revertir es volver a abrir su vigencia."})
    for t in tipos:
        propuesta.append({"objeto": "tipo_de_documento", "id": t["id"],
                          "accion": f"Revisar {', '.join(t['aparece_en'])} del tipo «{t['nombre']}» y, si cambia, "
                                    "publicar una revisión del catálogo con nota de la fecha.",
                          "documentos_de_usuarios": "No se tocan. Los borradores ya generados con este tipo "
                                                    "conservan su texto; se sugiere mostrar un aviso de «norma "
                                                    "modificada» al abrirlos."})
    if not afectadas and tipo == "norma":
        propuesta.append({"objeto": "regla", "id": None,
                          "accion": "La norma no está en el registro: valorar si debe crearse una regla nueva "
                                    "(estado inicial " + reglas.REVISION_PENDIENTE + ")."})
    advertencias = ["La búsqueda es textual: una regla o un documento afectado de forma indirecta (sin nombrar la "
                    "norma) no aparece aquí."]
    if tipo == "documento":
        advertencias.append("Para un documento de la biblioteca, el impacto sobre los índices de búsqueda lo "
                            "calcula el componente de biblioteca; aquí solo se cruzan reglas y catálogo.")
    return {**base, "estado": "IMPACTO_CALCULADO", "claves_buscadas": claves, "reglas_afectadas": afectadas,
            "tipos_de_documento_afectados": tipos, "flujos_afectados": flujos,
            "perfiles_afectados": {"identificadores": _perfiles(prefijos),
                                   "criterio": "subespecialidades ligadas a la materia de cada regla y al área de "
                                               "cada tipo de documento, en las funciones F04 (verificación de "
                                               "versiones), F08 (pruebas) y F09 (revisión independiente)",
                                   "nota": "Identificadores deterministas del esquema Axx-Syy-Fzz; el registro "
                                           "de perfiles lo mantiene otro componente y no se consultó."},
            "propuesta": propuesta, "advertencias": advertencias,
            "juicio_profesional": ["Determinar el alcance real del cambio y redactar el nuevo enunciado.",
                                   "Decidir el régimen de transición para asuntos en curso."]}
