"""J06 — Liquidaciones. Fórmulas versionadas y aritmética reproducible (decimal, no binaria).

Tres liquidaciones (campo «tipo»):

    prestaciones    cesantías, intereses sobre cesantías, prima de servicios y vacaciones (CST)
    intereses_mora  interés legal civil (6 % anual), moratorio comercial (1,5 × bancario corriente) o tasa indicada
    indexacion      valor histórico × IPC final / IPC inicial

Regla de oro: el procedimiento NO trae de memoria tasas, índices, salarios mínimos ni auxilios. Son ENTRADAS
obligatorias del usuario, con su fuente, o salen de reglas/parametros.json cuando un valor oficial está cargado
con enlace y fecha (hoy la tabla está vacía). Las únicas cifras propias son las que fija una norma verificada del
registro: 12 % de intereses sobre cesantías (R-LIQ-0003), 6 % de interés legal civil (R-INT-0001) y el factor 1,5
del interés moratorio comercial (R-INT-0002).

Lo que NO decide: qué pagos son salario, si el auxilio de transporte entra en la base (R-LIQ-0006, no verificado),
qué tasa o índice corresponde a cada período, ni el método de intereses (R-INT-0004). Lo declara en la salida.
"""
import hashlib
import json
import re
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP, localcontext
from pathlib import Path

import reglas

VERSION = "1.0.0"
PROCEDIMIENTO = "J06"
TIPOS = ("prestaciones", "intereses_mora", "indexacion")
CONCEPTOS = ("cesantias", "intereses_cesantias", "prima", "vacaciones")
NOMBRES = {"cesantias": "Cesantías", "intereses_cesantias": "Intereses sobre las cesantías",
           "prima": "Prima de servicios", "vacaciones": "Vacaciones (compensación en dinero)"}
CLASES_INTERES = {"legal_civil": "Interés legal civil (6 % anual)",
                  "comercial_moratorio": "Interés moratorio comercial (1,5 veces el bancario corriente)",
                  "tasa_indicada": "Tasa indicada por el usuario (pactada o fijada en una decisión)"}
METODOS = {"simple": "Interés simple: capital × tasa anual × días / base de días",
           "equivalente_diaria": "Tasa efectiva anual convertida a tasa diaria equivalente, sin capitalizar"}
REDONDEO = {"modo": "ROUND_HALF_UP", "decimales": 0,
            "descripcion": "Cada concepto se redondea al peso más cercano (mitad hacia arriba). Los cálculos "
                           "intermedios usan el valor sin redondear, con 34 dígitos de precisión."}
PRECISION = 34
MAX_VALOR = Decimal("1e15")
MAX_PERIODOS = 240
RUTA_PARAMETROS = Path(__file__).resolve().parent.parent / "reglas" / "parametros.json"
_RE_MILES = re.compile(r"^\d{1,3}(\.\d{3})+(,\d+)?$")
_RE_SIMPLE = re.compile(r"^\d+([.,]\d+)?$")


# ---------------------------------------------------------------------------- utilidades --
def _dec(valor, campo, contradicciones, faltantes, obligatorio=True, minimo=None, maximo=MAX_VALOR):
    if valor is None or (isinstance(valor, str) and not valor.strip()):
        if obligatorio:
            faltantes.append(campo)
        return None
    if isinstance(valor, bool):
        contradicciones.append(f"«{campo}» no es un número.")
        return None
    if isinstance(valor, (int, Decimal)):
        d = Decimal(valor)
    elif isinstance(valor, float):
        if valor != valor or valor in (float("inf"), float("-inf")):
            contradicciones.append(f"«{campo}» no es un número válido.")
            return None
        d = Decimal(repr(valor))
    else:
        s = str(valor).strip().replace("$", "").replace(" ", "").replace("%", "")
        if _RE_MILES.match(s):
            s = s.replace(".", "").replace(",", ".")
        elif _RE_SIMPLE.match(s):
            s = s.replace(",", ".")
        else:
            contradicciones.append(f"«{campo}»: {valor!r} no es un número (use 1500000 o 1.500.000,50).")
            return None
        try:
            d = Decimal(s)
        except InvalidOperation:
            contradicciones.append(f"«{campo}»: {valor!r} no es un número.")
            return None
    if minimo is not None and d < minimo:
        contradicciones.append(f"«{campo}» no puede ser menor que {minimo}.")
        return None
    if maximo is not None and d > maximo:
        contradicciones.append(f"«{campo}» es demasiado grande.")
        return None
    return d


def _fecha(valor, campo, contradicciones, faltantes, obligatorio=True):
    if valor in (None, ""):
        if obligatorio:
            faltantes.append(campo)
        return None
    try:
        return reglas.a_fecha(valor)
    except (ValueError, TypeError):
        contradicciones.append(f"«{campo}»: la fecha {valor!r} no existe o no tiene el formato AAAA-MM-DD.")
        return None


def pesos(d: Decimal) -> Decimal:
    return d.quantize(Decimal("1"), rounding=ROUND_HALF_UP)


def _txt(d: Decimal, decimales=6) -> str:
    """Número exacto como texto, sin notación científica."""
    q = d.quantize(Decimal(1).scaleb(-decimales), rounding=ROUND_HALF_UP)
    s = format(q, "f")
    return s.rstrip("0").rstrip(".") if "." in s else s


def _ref(rid, fecha, usadas):
    r = reglas.vigente(rid, fecha) if len(reglas.versiones(rid)) > 1 else reglas.obtener(rid)
    if r and r["id"] not in {u["id"] for u in usadas}:
        d = reglas.referencia(r)
        d["vigencia_comprobada_a_la_fecha"] = reglas.vigencia_comprobada(r, fecha)["comprobada"]
        usadas.append(d)
    return r


def ultimo_dia_del_mes(d: date) -> bool:
    return (d + timedelta(days=1)).month != d.month


def dias_360(desde: date, hasta: date) -> int:
    """Días entre dos fechas, ambas incluidas, con meses de 30 días (supuesto R-LIQ-0007):
    el día 31 cuenta como 30 y el último día de febrero, cuando es la fecha final, también."""
    d1 = min(desde.day, 30)
    d2 = 30 if ultimo_dia_del_mes(hasta) else min(hasta.day, 30)
    return (hasta.year - desde.year) * 360 + (hasta.month - desde.month) * 30 + (d2 - d1) + 1


def parametro(nombre: str, fecha) -> dict:
    """Valor oficial cargado en reglas/parametros.json para una fecha (o None). Cada entrada lleva nombre, valor,
    vigencia desde/hasta, norma, enlace y fecha de consulta. La tabla solo admite valores verificados."""
    try:
        datos = json.loads(RUTA_PARAMETROS.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    f = reglas.a_fecha(fecha)
    for p in datos.get("parametros", []):
        if p.get("nombre") != nombre or not reglas.es_enlace_oficial(p.get("enlace")):
            continue
        desde = reglas.a_fecha(p["desde"]) if p.get("desde") else None
        hasta = reglas.a_fecha(p["hasta"]) if p.get("hasta") else None
        if (desde is None or desde <= f) and (hasta is None or f <= hasta):
            return p
    return None


def _salida(estado, tipo, entrada_norm, **campos) -> dict:
    cuerpo = {"procedimiento": PROCEDIMIENTO, "version": VERSION,
              "version_registro": reglas.registro()["version_registro"], "tipo": tipo, "estado": estado,
              "total": None, "desglose": [], "parametros": {}, "redondeo": REDONDEO, "normas": [], "supuestos": [],
              "advertencias": [], "juicio_profesional": [], "faltantes": [], "contradicciones": []}
    cuerpo.update(campos)
    cuerpo["entrada"] = entrada_norm
    base = json.dumps({"e": entrada_norm, "t": cuerpo["total"], "d": cuerpo["desglose"]}, ensure_ascii=False,
                      sort_keys=True, default=str)
    cuerpo["huella"] = hashlib.sha256(base.encode("utf-8")).hexdigest()[:16]
    cuerpo["aviso"] = ("Liquidación de apoyo para revisión profesional. Las tasas, índices, salarios y bases son "
                       "datos de entrada: verifíquelos en la fuente oficial. No reemplaza el criterio del abogado "
                       "ni del contador.")
    return cuerpo


def _advertir_vigencia(normas, advertencias):
    sin_verificar = [n["id"] for n in normas if n["estado"] != reglas.VERIFICADA]
    no_comprobadas = [n["id"] for n in normas
                      if n["estado"] == reglas.VERIFICADA and not n["vigencia_comprobada_a_la_fecha"]]
    if sin_verificar:
        advertencias.append("Esta liquidación usa supuestos no verificados en fuente oficial: " +
                            ", ".join(sin_verificar) + " (ver «supuestos»).")
    if no_comprobadas:
        advertencias.append("Reglas verificadas el " + reglas.registro()["actualizado"] + " cuya vigencia en la "
                            "fecha de la liquidación no está comprobada: " + ", ".join(no_comprobadas) + ".")


# -------------------------------------------------------------------------- prestaciones --
def _prestaciones(e: dict) -> dict:
    falt, contra, sup, adv, juicio, normas = [], [], [], [], [], []
    ini = _fecha(e.get("fecha_inicio"), "fecha_inicio", contra, falt)
    fin = _fecha(e.get("fecha_fin"), "fecha_fin", contra, falt)
    salario = _dec(e.get("salario_mensual"), "salario_mensual", contra, falt, minimo=Decimal("0.01"))
    auxilio = _dec(e.get("auxilio_transporte_mensual"), "auxilio_transporte_mensual", contra, falt, minimo=Decimal(0))
    tomados = _dec(e.get("vacaciones_dias_tomados"), "vacaciones_dias_tomados", contra, falt, False, Decimal(0),
                   Decimal(2000)) or Decimal(0)
    base_anio = _dec(e.get("base_dias_anio"), "base_dias_anio", contra, falt, False, Decimal(1), Decimal(366))
    conceptos = e.get("conceptos") or list(CONCEPTOS)
    if not isinstance(conceptos, list) or any(c not in CONCEPTOS for c in conceptos):
        contra.append("«conceptos» solo admite: " + ", ".join(CONCEPTOS) + ".")
        conceptos = []
    conceptos = [c for c in CONCEPTOS if c in conceptos]
    if "intereses_cesantias" in conceptos and "cesantias" not in conceptos:
        contra.append("Los intereses sobre cesantías se calculan sobre las cesantías: incluya ambos conceptos.")
    incluir = e.get("auxilio_en_base_prestaciones")
    if auxilio is not None and auxilio > 0 and not isinstance(incluir, bool):
        falt.append("auxilio_en_base_prestaciones: indique (true o false) si el auxilio de transporte entra en la "
                    "base de cesantías y prima; el registro no lo tiene verificado (R-LIQ-0006)")
    if ini and fin and fin < ini:
        contra.append(f"La fecha final ({fin.isoformat()}) es anterior a la inicial ({ini.isoformat()}).")
    dias_usuario = e.get("dias") if isinstance(e.get("dias"), dict) else {}
    periodos_usuario = e.get("periodos") if isinstance(e.get("periodos"), dict) else {}
    norm = {"tipo": "prestaciones", "fecha_inicio": ini.isoformat() if ini else None,
            "fecha_fin": fin.isoformat() if fin else None, "salario_mensual": _txt(salario) if salario else None,
            "auxilio_transporte_mensual": _txt(auxilio) if auxilio is not None else None,
            "auxilio_en_base_prestaciones": incluir if isinstance(incluir, bool) else None,
            "conceptos": conceptos, "vacaciones_dias_tomados": _txt(tomados),
            "base_dias_anio": _txt(base_anio) if base_anio else None,
            "salario_variable": bool(e.get("salario_variable"))}
    if contra:
        return _salida("CONTRADICCION", "prestaciones", norm, contradicciones=contra, faltantes=falt)
    if falt:
        return _salida("ABSTENCION", "prestaciones", norm, faltantes=falt, advertencias=[
            "No se liquida: faltan datos esenciales. El procedimiento no supone salarios, auxilios ni bases."])

    r7 = _ref("R-LIQ-0007", fin, normas)
    if base_anio is None:
        base_anio = Decimal(r7["parametros"]["base_dias_anio"])
        sup.append(f"Año de {base_anio} días y meses de 30 días (supuesto no verificado en fuente oficial, "
                   "modificable con «base_dias_anio» y «dias») [R-LIQ-0007].")
    else:
        sup.append(f"Base de {base_anio} días por año indicada por el usuario.")
    incluir = bool(incluir) if auxilio > 0 else False
    base_prest = salario + (auxilio if incluir else Decimal(0))
    if auxilio > 0:
        _ref("R-LIQ-0006", fin, normas)
        sup.append(("El auxilio de transporte SE INCLUYÓ" if incluir else "El auxilio de transporte NO se incluyó") +
                   " en la base de cesantías y prima por decisión del usuario; no entra en la base de vacaciones "
                   "[R-LIQ-0006, no verificado].")
    if norm["salario_variable"]:
        juicio.append("Salario variable: la base debe ser el promedio que fija el art. 253 del CST (cesantías) y "
                      "el art. 192 (vacaciones). Se usó el valor indicado por el usuario como base ya promediada.")
    juicio.append("Qué pagos constituyen salario y si hubo variación en los tres últimos meses (CST, art. 253) lo "
                  "determina el profesional; aquí se usa la base indicada.")

    def periodo(concepto, desde_defecto):
        p = periodos_usuario.get(concepto) if isinstance(periodos_usuario.get(concepto), dict) else {}
        d = _fecha(p.get("desde"), f"periodos.{concepto}.desde", contra, falt, False) or desde_defecto
        h = _fecha(p.get("hasta"), f"periodos.{concepto}.hasta", contra, falt, False) or fin
        if h < d:
            contra.append(f"Período de {NOMBRES[concepto]}: termina antes de empezar.")
        n = dias_usuario.get(concepto)
        if n is not None:
            nd = _dec(n, f"dias.{concepto}", contra, falt, minimo=Decimal(0), maximo=Decimal(40000))
            return d, h, nd, "indicados por el usuario"
        return d, h, Decimal(dias_360(d, h)) if h >= d else Decimal(0), "método 30/360"

    anio_ini = date(fin.year, 1, 1)
    sem_ini = date(fin.year, 1, 1) if fin.month <= 6 else date(fin.year, 7, 1)
    desglose, total, ces_exacta = [], Decimal(0), None
    with localcontext() as ctx:
        ctx.prec = PRECISION
        for c in conceptos:
            if c in ("cesantias", "intereses_cesantias"):
                d, h, n, origen = periodo("cesantias", max(ini, anio_ini))
            elif c == "prima":
                d, h, n, origen = periodo("prima", max(ini, sem_ini))
            else:
                d, h, n, origen = periodo("vacaciones", ini)
            if contra:
                break
            item = {"concepto": c, "nombre": NOMBRES[c], "periodo": {"desde": d.isoformat(), "hasta": h.isoformat()},
                    "dias": _txt(n), "origen_dias": origen}
            if c == "cesantias":
                r = _ref("R-LIQ-0001", fin, normas)
                _ref("R-LIQ-0002", fin, normas)
                valor = base_prest * n / base_anio
                ces_exacta = valor
                item.update(base=_txt(base_prest), regla=r["id"], formula=r["parametros"]["formula"],
                            formula_valores=f"{_txt(base_prest)} × {_txt(n)} / {_txt(base_anio)}")
            elif c == "intereses_cesantias":
                r = _ref("R-LIQ-0003", fin, normas)
                tasa = Decimal(r["parametros"]["tasa_anual"])
                valor = ces_exacta * tasa * n / base_anio
                item.update(base=_txt(ces_exacta), regla=r["id"], formula=r["parametros"]["formula"], tasa_anual=_txt(tasa),
                            formula_valores=f"{_txt(ces_exacta)} × {_txt(tasa)} × {_txt(n)} / {_txt(base_anio)}")
            elif c == "prima":
                r = _ref("R-LIQ-0004", fin, normas)
                if reglas.vigencia_comprobada(r, fin)["motivo"] == "fuera_de_periodo":
                    adv.append("La regla de la prima registrada rige desde el 7 de julio de 2016 (Ley 1788 de "
                               "2016); para fechas anteriores verifique el texto entonces vigente.")
                valor = base_prest * n / base_anio
                item.update(base=_txt(base_prest), regla=r["id"], formula=r["parametros"]["formula"],
                            formula_valores=f"{_txt(base_prest)} × {_txt(n)} / {_txt(base_anio)}")
            else:
                r = _ref("R-LIQ-0005", fin, normas)
                causados = n * Decimal(r["parametros"]["dias_por_anio"]) / base_anio
                pendientes = causados - tomados
                if pendientes < 0:
                    contra.append(f"Los días de vacaciones ya tomados ({_txt(tomados)}) superan los causados "
                                  f"({_txt(causados, 4)}).")
                    break
                valor = salario / Decimal(30) * pendientes
                item.update(base=_txt(salario), regla=r["id"], formula=r["parametros"]["formula"],
                            dias_vacaciones_causados=_txt(causados, 4), dias_vacaciones_tomados=_txt(tomados),
                            dias_vacaciones_pendientes=_txt(pendientes, 4),
                            formula_valores=f"{_txt(salario)} / 30 × ({_txt(n)} × 15 / {_txt(base_anio)} − {_txt(tomados)})")
                juicio.append(r["requiere_juicio_profesional"])
            item["valor_exacto"] = _txt(valor)
            item["valor"] = int(pesos(valor))
            total += pesos(valor)
            desglose.append(item)
    if contra:
        return _salida("CONTRADICCION", "prestaciones", norm, contradicciones=contra)
    if any(i["concepto"] == "cesantias" for i in desglose) and ini < anio_ini and "cesantias" not in periodos_usuario:
        adv.append(f"Cesantías e intereses se liquidaron solo por el año {fin.year} (desde el 1 de enero). Las de "
                   "años anteriores debieron liquidarse a 31 de diciembre de cada año: verifique su consignación "
                   "o indique otro período en «periodos».")
    if any(i["concepto"] == "prima" for i in desglose) and "prima" not in periodos_usuario:
        adv.append("La prima se liquidó por el semestre en curso a la fecha final. Si se debe un semestre "
                   "anterior, indíquelo en «periodos».")
    if any(i["concepto"] == "vacaciones" for i in desglose):
        adv.append("Vacaciones: se liquidó todo el tiempo trabajado menos los días indicados como ya disfrutados "
                   f"o pagados ({_txt(tomados)}). Verifique los períodos realmente pendientes.")
    adv.append("No incluye salarios pendientes, indemnización por despido, sanciones moratorias ni aportes a "
               "seguridad social.")
    _advertir_vigencia(normas, adv)
    return _salida("CALCULADO", "prestaciones", norm, total=int(total), desglose=desglose, normas=normas,
                   supuestos=sup, advertencias=adv, juicio_profesional=juicio,
                   parametros={"salario_mensual": _txt(salario), "auxilio_transporte_mensual": _txt(auxilio),
                               "base_cesantias_y_prima": _txt(base_prest), "base_vacaciones": _txt(salario),
                               "base_dias_anio": _txt(base_anio), "fuente_de_los_valores": "indicados por el usuario"})


# ------------------------------------------------------------------------- intereses de mora --
def _intereses(e: dict) -> dict:
    falt, contra, sup, adv, juicio, normas = [], [], [], [], [], []
    capital = _dec(e.get("capital"), "capital", contra, falt, minimo=Decimal("0.01"))
    clase = str(e.get("clase") or "").strip().lower()
    metodo = str(e.get("metodo") or "").strip().lower()
    base = _dec(e.get("base_dias"), "base_dias", contra, falt)
    fuente = str(e.get("fuente_tasas") or "").strip()[:300]
    if not clase:
        falt.append("clase")
    elif clase not in CLASES_INTERES:
        contra.append("«clase» debe ser: " + ", ".join(CLASES_INTERES) + ".")
    if base is not None and base not in (Decimal(360), Decimal(365)):
        contra.append("«base_dias» debe ser 360 o 365.")
    if clase == "legal_civil":
        metodo = metodo or "simple"
        if metodo != "simple":
            contra.append("El interés legal civil se liquida como interés simple (los intereses atrasados no "
                          "producen interés).")
    elif clase in CLASES_INTERES:
        if not metodo:
            falt.append("metodo (simple o equivalente_diaria)")
        elif metodo not in METODOS:
            contra.append("«metodo» debe ser: " + ", ".join(METODOS) + ".")
        if not fuente:
            falt.append("fuente_tasas: indique de dónde tomó cada tasa (por ejemplo, la certificación de la "
                        "Superintendencia Financiera con su número y fecha, o la cláusula del contrato)")
    periodos_in = e.get("periodos")
    if not isinstance(periodos_in, list) or not periodos_in:
        falt.append("periodos")
        periodos_in = []
    if len(periodos_in) > MAX_PERIODOS:
        contra.append(f"Máximo {MAX_PERIODOS} períodos.")
        periodos_in = []
    periodos = []
    for i, p in enumerate(periodos_in, 1):
        if not isinstance(p, dict):
            contra.append(f"Período {i}: formato no válido.")
            continue
        d = _fecha(p.get("desde"), f"periodos[{i}].desde", contra, falt)
        h = _fecha(p.get("hasta"), f"periodos[{i}].hasta", contra, falt)
        tasa = None
        if clase in ("comercial_moratorio", "tasa_indicada"):
            tasa = _dec(p.get("tasa_pct"), f"periodos[{i}].tasa_pct", contra, falt, minimo=Decimal(0), maximo=Decimal(1000))
        elif clase == "legal_civil" and p.get("tasa_pct") not in (None, ""):
            contra.append(f"Período {i}: el interés legal civil no admite otra tasa; use la clase «tasa_indicada».")
        if d and h:
            if h < d:
                contra.append(f"Período {i}: termina ({h.isoformat()}) antes de empezar ({d.isoformat()}).")
            else:
                periodos.append({"desde": d, "hasta": h, "tasa_pct": tasa})
    orden = sorted(periodos, key=lambda p: p["desde"])
    for a, b in zip(orden, orden[1:]):
        if b["desde"] <= a["hasta"]:
            contra.append(f"Los períodos {a['desde'].isoformat()}–{a['hasta'].isoformat()} y "
                          f"{b['desde'].isoformat()}–{b['hasta'].isoformat()} se solapan.")
    norm = {"tipo": "intereses_mora", "capital": _txt(capital) if capital else None, "clase": clase or None,
            "metodo": metodo or None, "base_dias": _txt(base) if base else None, "fuente_tasas": fuente or None,
            "periodos": [{"desde": p["desde"].isoformat(), "hasta": p["hasta"].isoformat(),
                          "tasa_pct": _txt(p["tasa_pct"]) if p["tasa_pct"] is not None else None} for p in orden]}
    if contra:
        return _salida("CONTRADICCION", "intereses_mora", norm, contradicciones=contra, faltantes=falt)
    if falt:
        return _salida("ABSTENCION", "intereses_mora", norm, faltantes=falt, advertencias=[
            "No se liquida: faltan datos esenciales. El procedimiento no supone tasas, bases ni métodos."])

    ref = orden[0]["desde"]
    _ref("R-INT-0003", ref, normas)
    factor = Decimal(1)
    if clase == "legal_civil":
        r = _ref("R-INT-0001", ref, normas)
        tasa_fija = Decimal(r["parametros"]["tasa_anual"]) * 100
        for p in orden:
            p["tasa_pct"] = tasa_fija
        sup.append("Tasa del 6 % anual fijada por el art. 1617 del Código Civil [R-INT-0001].")
    elif clase == "comercial_moratorio":
        r = _ref("R-INT-0002", ref, normas)
        factor = Decimal(r["parametros"]["factor_sobre_bancario_corriente"])
        juicio.append(r["requiere_juicio_profesional"])
        sup.append("Cada «tasa_pct» se tomó como el interés bancario corriente efectivo anual del período y se "
                   f"multiplicó por {factor} [R-INT-0002]. Fuente declarada por el usuario: {fuente}.")
    else:
        sup.append(f"Tasas indicadas por el usuario. Fuente declarada: {fuente}.")
        juicio.append("Que la tasa indicada sea exigible y no supere el límite legal lo verifica el profesional.")
    if metodo == "equivalente_diaria":
        r4 = _ref("R-INT-0004", ref, normas)
        sup.append("Método: tasa diaria equivalente = (1 + tasa efectiva anual)^(1/" + _txt(base) + ") − 1; "
                   "interés = capital × tasa diaria × días, sin capitalizar [R-INT-0004, pendiente de revisión "
                   "humana].")
        juicio.append(r4["notas"])
    else:
        sup.append("Método: interés simple = capital × tasa anual × días / " + _txt(base) + ".")
    sup.append("Los días de cada período se cuentan por calendario, con ambas fechas incluidas.")
    sup.append("La base de días (" + _txt(base) + ") la eligió el usuario.")
    juicio.append("Desde qué día hay mora, si procede cobrar intereses y si pueden acumularse con otras sumas "
                  "(por ejemplo, indexación) son decisiones jurídicas que el procedimiento no toma.")

    desglose, total = [], Decimal(0)
    with localcontext() as ctx:
        ctx.prec = PRECISION
        for p in orden:
            dias = Decimal((p["hasta"] - p["desde"]).days + 1)
            tasa = p["tasa_pct"] / Decimal(100) * factor
            if metodo == "equivalente_diaria":
                diaria = (Decimal(1) + tasa) ** (Decimal(1) / base) - Decimal(1)
                valor = capital * diaria * dias
                formula = (f"{_txt(capital)} × ((1 + {_txt(tasa, 8)})^(1/{_txt(base)}) − 1) × {_txt(dias)}")
                extra = {"tasa_diaria": _txt(diaria, 12)}
            else:
                valor = capital * tasa * dias / base
                formula = f"{_txt(capital)} × {_txt(tasa, 8)} × {_txt(dias)} / {_txt(base)}"
                extra = {}
            desglose.append({"concepto": "intereses", "nombre": "Intereses del período",
                             "periodo": {"desde": p["desde"].isoformat(), "hasta": p["hasta"].isoformat()},
                             "dias": _txt(dias), "tasa_entrada_pct": _txt(p["tasa_pct"], 8),
                             "tasa_aplicada_anual_pct": _txt(tasa * 100, 8), "formula_valores": formula,
                             "valor_exacto": _txt(valor), "valor": int(pesos(valor)), **extra})
            total += pesos(valor)
    _advertir_vigencia(normas, adv)
    adv.append("Verifique cada tasa contra su fuente oficial antes de usar la liquidación.")
    return _salida("CALCULADO", "intereses_mora", norm, total=int(total), desglose=desglose, normas=normas,
                   supuestos=sup, advertencias=adv, juicio_profesional=juicio,
                   total_con_capital=int(total + pesos(capital)),
                   parametros={"capital": _txt(capital), "clase": CLASES_INTERES[clase], "metodo": METODOS[metodo],
                               "base_dias": _txt(base), "factor": _txt(factor), "fuente_tasas": fuente or None})


# -------------------------------------------------------------------------------- indexación --
def _indexacion(e: dict) -> dict:
    falt, contra, sup, adv, juicio, normas = [], [], [], [], [], []
    vh = _dec(e.get("valor_historico"), "valor_historico", contra, falt, minimo=Decimal("0.01"))
    ii = _dec(e.get("ipc_inicial"), "ipc_inicial", contra, falt, minimo=Decimal("0.000001"), maximo=Decimal(1000000))
    fi = _dec(e.get("ipc_final"), "ipc_final", contra, falt, minimo=Decimal("0.000001"), maximo=Decimal(1000000))
    fuente = str(e.get("fuente_ipc") or "").strip()[:300]
    mes_i = str(e.get("periodo_inicial") or "").strip()[:40]
    mes_f = str(e.get("periodo_final") or "").strip()[:40]
    if not fuente:
        falt.append("fuente_ipc: indique de dónde tomó los índices (serie del DANE, base y fecha de consulta)")
    norm = {"tipo": "indexacion", "valor_historico": _txt(vh) if vh else None, "ipc_inicial": _txt(ii, 8) if ii else None,
            "ipc_final": _txt(fi, 8) if fi else None, "fuente_ipc": fuente or None, "periodo_inicial": mes_i or None,
            "periodo_final": mes_f or None}
    if contra:
        return _salida("CONTRADICCION", "indexacion", norm, contradicciones=contra, faltantes=falt)
    if falt:
        return _salida("ABSTENCION", "indexacion", norm, faltantes=falt, advertencias=[
            "No se liquida: faltan datos esenciales. El procedimiento no trae índices de precios de memoria."])
    r = _ref("R-IDX-0001", date.today(), normas)
    with localcontext() as ctx:
        ctx.prec = PRECISION
        factor = fi / ii
        valor = vh * factor
    if fi < ii:
        adv.append("El índice final es menor que el inicial: revise que no estén invertidos o que sean de la misma "
                   "serie y base.")
    sup.append(f"Índices indicados por el usuario. Fuente declarada: {fuente}.")
    if not (mes_i and mes_f):
        adv.append("No se indicó a qué meses corresponden los índices: anótelo para que la liquidación sea verificable.")
    juicio.append(r["requiere_juicio_profesional"])
    juicio.append(r["notas"])
    _advertir_vigencia(normas, adv)
    item = {"concepto": "indexacion", "nombre": "Valor actualizado", "regla": r["id"],
            "formula": r["parametros"]["formula"],
            "formula_valores": f"{_txt(vh)} × {_txt(fi, 8)} / {_txt(ii, 8)}", "factor": _txt(factor, 10),
            "valor_exacto": _txt(valor), "valor": int(pesos(valor)),
            "diferencia": int(pesos(valor) - pesos(vh))}
    return _salida("CALCULADO", "indexacion", norm, total=int(pesos(valor)), desglose=[item], normas=normas,
                   supuestos=sup, advertencias=adv, juicio_profesional=juicio,
                   parametros={"valor_historico": _txt(vh), "ipc_inicial": _txt(ii, 8), "ipc_final": _txt(fi, 8),
                               "periodo_inicial": mes_i or None, "periodo_final": mes_f or None, "fuente_ipc": fuente})


def liquidar(entrada: dict) -> dict:
    if not isinstance(entrada, dict):
        return _salida("CONTRADICCION", None, {}, contradicciones=["La entrada debe ser un objeto."])
    tipo = str(entrada.get("tipo") or "").strip().lower()
    if not tipo:
        return _salida("ABSTENCION", None, {}, faltantes=["tipo (" + ", ".join(TIPOS) + ")"])
    if tipo not in TIPOS:
        return _salida("CONTRADICCION", tipo, {}, contradicciones=["«tipo» debe ser: " + ", ".join(TIPOS) + "."])
    return {"prestaciones": _prestaciones, "intereses_mora": _intereses, "indexacion": _indexacion}[tipo](entrada)


def opciones() -> dict:
    return {"tipos": list(TIPOS), "conceptos": [{"id": c, "nombre": NOMBRES[c]} for c in CONCEPTOS],
            "clases_interes": [{"id": k, "nombre": v} for k, v in CLASES_INTERES.items()],
            "metodos": [{"id": k, "nombre": v} for k, v in METODOS.items()], "redondeo": REDONDEO,
            "version": VERSION}
