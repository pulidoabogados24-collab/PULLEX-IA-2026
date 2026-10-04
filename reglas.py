"""PULLEX IA — Registro de reglas jurídicas (reglas/registro.json).

Cada regla tiene identificador (R-TERM-0001), versión, ámbito, enunciado, norma de soporte, enlace comprobado,
fecha de consulta, período de aplicación y estado de revisión. Una misma regla puede tener varias versiones con
períodos distintos (por ejemplo, la lista de festivos antes y después de la Ley 2578 de 2026).

La consulta siempre es A UNA FECHA: `vigente(id, fecha)` devuelve la versión cuyo período contiene esa fecha, no
la más reciente. Una regla sin fecha «desde» comprobada solo está verificada el día en que se consultó la fuente;
`vigencia_comprobada(regla, fecha)` lo dice, y los procedimientos lo advierten.

Este módulo no llama al modelo de IA ni a la red. El registro lo edita una persona (o J09 propone el cambio);
nada aquí lo modifica.
"""
import json
import re
import unicodedata
from datetime import date, datetime
from functools import lru_cache
from pathlib import Path

RUTA = Path(__file__).resolve().parent / "reglas" / "registro.json"

VERIFICADA = "VERIFICADA_EN_FUENTE_OFICIAL"
NO_VERIFICADO = "NO_VERIFICADO"
REVISION_PENDIENTE = "REVISIÓN_HUMANA_PENDIENTE"
ESTADOS = (VERIFICADA, NO_VERIFICADO, REVISION_PENDIENTE)

DOMINIOS_OFICIALES = ("secretariasenado.gov.co", "suin-juriscol.gov.co", "funcionpublica.gov.co",
                      "ramajudicial.gov.co", "corteconstitucional.gov.co", "mintrabajo.gov.co", "banrep.gov.co",
                      "superfinanciera.gov.co", "dane.gov.co", "consejodeestado.gov.co", "cortesuprema.gov.co")
_RE_ID = re.compile(r"^R-[A-Z]{2,6}-\d{4}$")
_CAMPOS = ("id", "version", "titulo", "ambito", "enunciado", "soporte", "enlace", "consultado", "vigencia",
           "estado", "procedimientos")


class ErrorRegistro(ValueError):
    """El registro no cumple su propio esquema."""


def a_fecha(valor) -> date:
    """Convierte 'AAAA-MM-DD', date o datetime en date. Lanza ValueError si la fecha no existe."""
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    if not isinstance(valor, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", valor.strip()):
        raise ValueError(f"Fecha no válida: {valor!r} (se espera AAAA-MM-DD)")
    a, m, d = (int(x) for x in valor.strip().split("-"))
    return date(a, m, d)


def _norm(texto) -> str:
    t = unicodedata.normalize("NFD", str(texto or "").lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9ñ]+", " ", t).strip()


def es_enlace_oficial(url) -> bool:
    m = re.match(r"^https?://([^/:?#]+)", str(url or "").strip().lower())
    if not m:
        return False
    host = m.group(1)
    return any(host == d or host.endswith("." + d) for d in DOMINIOS_OFICIALES)


@lru_cache(maxsize=4)
def _cargar(ruta: str) -> dict:
    datos = json.loads(Path(ruta).read_text(encoding="utf-8"))
    validar(datos)
    return datos


def registro(ruta=None) -> dict:
    return _cargar(str(ruta or RUTA))


def todas(ruta=None) -> list:
    return registro(ruta)["reglas"]


def validar(datos: dict) -> None:
    """Comprueba el esquema del registro. Lanza ErrorRegistro con la lista completa de problemas."""
    problemas = []
    reglas = datos.get("reglas")
    if not isinstance(reglas, list) or not reglas:
        raise ErrorRegistro("El registro no tiene reglas.")
    vistos, periodos = set(), {}
    for r in reglas:
        rid = r.get("id", "?")
        ref = f"{rid} v{r.get('version', '?')}"
        for c in _CAMPOS:
            if c not in r:
                problemas.append(f"{ref}: falta «{c}»")
        if not _RE_ID.match(str(rid)):
            problemas.append(f"{ref}: identificador mal formado")
        if not isinstance(r.get("version"), int) or r.get("version", 0) < 1:
            problemas.append(f"{ref}: versión no válida")
        if (rid, r.get("version")) in vistos:
            problemas.append(f"{ref}: versión duplicada")
        vistos.add((rid, r.get("version")))
        if r.get("estado") not in ESTADOS:
            problemas.append(f"{ref}: estado desconocido {r.get('estado')!r}")
        amb = r.get("ambito") or {}
        if not amb.get("materia") or not amb.get("jurisdiccion"):
            problemas.append(f"{ref}: ámbito incompleto")
        sop = r.get("soporte") or {}
        if not all(k in sop for k in ("autoridad", "identificador", "articulo")):
            problemas.append(f"{ref}: soporte incompleto")
        if not isinstance(r.get("procedimientos"), list) or not r.get("procedimientos"):
            problemas.append(f"{ref}: sin procedimientos que la usen")
        vig = r.get("vigencia") or {}
        try:
            desde = a_fecha(vig["desde"]) if vig.get("desde") else None
            hasta = a_fecha(vig["hasta"]) if vig.get("hasta") else None
            if desde and hasta and hasta < desde:
                problemas.append(f"{ref}: vigencia termina antes de empezar")
            periodos.setdefault(rid, []).append((desde or date.min, hasta or date.max, r.get("version")))
        except (ValueError, KeyError) as e:
            problemas.append(f"{ref}: vigencia no válida ({e})")
        if r.get("estado") == VERIFICADA:
            # Una regla verificada exige enlace oficial, fecha de consulta y cita o enunciado comprobable.
            if not es_enlace_oficial(r.get("enlace")):
                problemas.append(f"{ref}: verificada sin enlace de fuente oficial")
            try:
                a_fecha(r.get("consultado"))
            except ValueError:
                problemas.append(f"{ref}: verificada sin fecha de consulta")
        elif not r.get("notas"):
            problemas.append(f"{ref}: una regla no verificada debe explicar qué falta en «notas»")
    for rid, ps in periodos.items():
        ps.sort()
        for (d1, h1, v1), (d2, h2, v2) in zip(ps, ps[1:]):
            if d2 <= h1:
                problemas.append(f"{rid}: las versiones {v1} y {v2} se solapan en el tiempo")
    if problemas:
        raise ErrorRegistro("; ".join(problemas))


def versiones(rid: str, ruta=None) -> list:
    return sorted((r for r in todas(ruta) if r["id"] == rid), key=lambda r: r["version"])


def obtener(rid: str, version: int = None, ruta=None):
    """Una versión concreta. Sin `version` exige que la regla tenga UNA sola versión (no adivina la «última»)."""
    vs = versiones(rid, ruta)
    if version is not None:
        return next((r for r in vs if r["version"] == version), None)
    if len(vs) > 1:
        raise ValueError(f"{rid} tiene {len(vs)} versiones: indique la versión o consulte con vigente(id, fecha)")
    return vs[0] if vs else None


def _contiene(regla: dict, f: date) -> bool:
    vig = regla["vigencia"]
    desde = a_fecha(vig["desde"]) if vig.get("desde") else None
    hasta = a_fecha(vig["hasta"]) if vig.get("hasta") else None
    return (desde is None or desde <= f) and (hasta is None or f <= hasta)


def vigente(rid: str, fecha, ruta=None):
    """La versión de la regla cuyo período de aplicación contiene `fecha`, o None.
    `fecha` es obligatoria: no existe «la regla vigente» sin decir a qué fecha."""
    if fecha is None:
        raise ValueError("Indique la fecha a la que consulta la regla.")
    f = a_fecha(fecha)
    candidatas = [r for r in versiones(rid, ruta) if _contiene(r, f)]
    return candidatas[-1] if candidatas else None


def vigencia_comprobada(regla: dict, fecha) -> dict:
    """¿Está comprobado que la regla regía en `fecha`? Distingue tres situaciones:
    - comprobada: la fecha cae en el período y su inicio está verificado (o es el propio día de consulta);
    - anterior_sin_inicio: la fecha es anterior a la consulta y el inicio de vigencia no se verificó;
    - posterior_a_consulta: la fuente se consultó antes de esa fecha (pudo cambiar después)."""
    f = a_fecha(fecha)
    vig = regla["vigencia"]
    if not _contiene(regla, f):
        return {"comprobada": False, "motivo": "fuera_de_periodo",
                "detalle": f"La versión {regla['version']} de {regla['id']} no aplica a {f.isoformat()}."}
    if regla["estado"] != VERIFICADA:
        return {"comprobada": False, "motivo": "regla_no_verificada",
                "detalle": f"{regla['id']} está en estado {regla['estado']}."}
    consultado = a_fecha(regla["consultado"])
    if f > consultado:
        return {"comprobada": False, "motivo": "posterior_a_consulta",
                "detalle": f"{regla['id']} se comprobó el {consultado.isoformat()}; la norma pudo cambiar después."}
    if vig.get("desde") and vig.get("desde_comprobado"):
        return {"comprobada": True, "motivo": "en_periodo_comprobado", "detalle": ""}
    if f == consultado:
        return {"comprobada": True, "motivo": "fecha_de_consulta", "detalle": ""}
    return {"comprobada": False, "motivo": "anterior_sin_inicio",
            "detalle": f"{regla['id']}: no se comprobó desde cuándo rige; el texto se verificó el "
                       f"{consultado.isoformat()}."}


def vigentes(fecha, procedimiento: str = None, materia: str = None, estado: str = None, ruta=None) -> list:
    f = a_fecha(fecha)
    salida = []
    for r in todas(ruta):
        if not _contiene(r, f):
            continue
        if procedimiento and procedimiento not in r["procedimientos"]:
            continue
        if materia and _norm(materia) not in _norm(r["ambito"]["materia"]):
            continue
        if estado and r["estado"] != estado:
            continue
        salida.append(r)
    return salida


def buscar_por_norma(texto: str, ruta=None) -> list:
    """Reglas cuyo soporte (principal o adicional) menciona la norma indicada: «Ley 1755 de 2015», «CGP art. 118»…
    La comparación es textual y normalizada; devuelve todas las versiones."""
    q = _norm(_expandir_siglas(texto))
    if not q:
        return []
    m_art = re.search(r"\bart(?:iculo|s)? (\d+[a-z]?)\b", q)
    articulo = m_art.group(1) if m_art else None
    norma = re.sub(r"\bart(?:iculo|s)? \d+[a-z]?\b", " ", q)
    norma = re.sub(r"\b(del|de la|de)\b\s*$", "", norma.strip()).strip()
    claves = _claves_norma(norma)
    salida = []
    for r in todas(ruta):
        soportes = [r["soporte"]] + list(r.get("soportes_adicionales") or [])
        for s in soportes:
            ident = _norm(s.get("identificador"))
            if claves and not any(c in ident for c in claves):
                continue
            if articulo and not re.search(r"(?<!\d)%s(?!\d)" % re.escape(articulo), _norm(s.get("articulo"))):
                continue
            if not claves and not articulo:
                continue
            salida.append(r)
            break
    return salida


_SIGLAS = {"cgp": "ley 1564 de 2012", "cpaca": "ley 1437 de 2011", "cst": "codigo sustantivo del trabajo",
           "c p": "constitucion politica", "cp": "constitucion politica", "c co": "codigo de comercio",
           "cc": "codigo civil", "crpm": "ley 4 de 1913"}


def _expandir_siglas(texto: str) -> str:
    t = " " + _norm(texto) + " "
    for sigla, completo in _SIGLAS.items():
        t = re.sub(r"(?<![a-z0-9])%s(?![a-z0-9])" % re.escape(sigla), completo, t)
    return t


def _claves_norma(norma: str) -> list:
    """Extrae formas buscables: «ley 1755 de 2015», «decreto 2591 de 1991», «codigo civil»…"""
    claves = []
    for m in re.finditer(r"\b(ley|decreto(?: legislativo| ley)?) (\d{1,5}) de (\d{4})\b", norma):
        tipo = "decreto" if m.group(1).startswith("decreto") else "ley"
        claves.append(f"{tipo} {m.group(2)} de {m.group(3)}")
        if tipo == "decreto":
            claves.append(f"decreto legislativo {m.group(2)} de {m.group(3)}")
    for nombre in ("codigo general del proceso", "codigo sustantivo del trabajo", "codigo civil",
                   "codigo de comercio", "constitucion politica"):
        if nombre in norma:
            claves.append(nombre)
    return claves


def publica(regla: dict) -> dict:
    """La regla tal como se entrega por la API (copia superficial; el registro no se muta)."""
    return json.loads(json.dumps(regla, ensure_ascii=False))


def referencia(regla: dict) -> dict:
    """Cita corta de una regla para las salidas de los procedimientos."""
    s = regla["soporte"]
    art = "" if s["articulo"] in ("—", "", None) else f", art. {s['articulo']}"
    return {"id": regla["id"], "version": regla["version"], "titulo": regla["titulo"],
            "norma": f"{s['identificador']}{art}", "autoridad": s["autoridad"], "estado": regla["estado"],
            "enlace": regla.get("enlace"), "consultado": regla.get("consultado")}


def resumen(ruta=None) -> dict:
    rs = todas(ruta)
    por_estado = {e: sum(1 for r in rs if r["estado"] == e) for e in ESTADOS}
    return {"version_registro": registro(ruta)["version_registro"], "actualizado": registro(ruta)["actualizado"],
            "total_versiones": len(rs), "reglas_distintas": len({r["id"] for r in rs}), "por_estado": por_estado,
            "verificadas_con_enlace": sum(1 for r in rs if r["estado"] == VERIFICADA and es_enlace_oficial(r["enlace"]))}
