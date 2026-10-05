"""Calendario colombiano determinista: festivos por regla, Pascua, vacancia judicial y días hábiles.

No hay tablas de fechas escritas a mano: cada festivo sale de los parámetros de la regla R-FEST-0001 EN LA
VERSIÓN VIGENTE EL DÍA DEL FESTIVO (el 9 de julio solo es festivo desde la Ley 2578 de 2026) y del cómputo
gregoriano de la Pascua (R-FEST-0003). La vacancia judicial sale de R-VAC-0001 y R-VAC-0002.
"""
from datetime import date, timedelta
from functools import lru_cache

import reglas

DIAS = ("lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo")
MESES = ("enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre",
         "noviembre", "diciembre")
ANIO_MIN, ANIO_MAX = 1984, 2100      # la Ley 51 de 1983 rige desde el 6 de diciembre de 1983


def pascua(anio: int) -> date:
    """Domingo de Pascua (calendario gregoriano; algoritmo anónimo de Meeus/Jones/Butcher)."""
    a = anio % 19
    b, c = divmod(anio, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    mes, dia = divmod(h + l - 7 * m + 114, 31)
    return date(anio, mes, dia + 1)


def al_lunes(d: date) -> date:
    """Traslado de la Ley 51 de 1983: si no cae en lunes pasa al lunes siguiente (también si cae en domingo)."""
    return d if d.weekday() == 0 else d + timedelta(days=7 - d.weekday())


def _candidatos(regla: dict, anio: int) -> list:
    p = regla["parametros"]
    salida = []
    for f in p["fijos"]:
        base = date(anio, f["mes"], f["dia"])
        salida.append((al_lunes(base) if f["traslado_al_lunes"] else base, f["nombre"], base))
    domingo = pascua(anio)
    for f in p["respecto_de_pascua"]:
        base = domingo + timedelta(days=f["dias"])
        salida.append((al_lunes(base) if f["traslado_al_lunes"] else base, f["nombre"], base))
    return salida


@lru_cache(maxsize=256)
def festivos(anio: int) -> dict:
    """{fecha: {"nombre", "fecha_original", "regla", "version"}} de los festivos del año.
    Cada fecha se toma de la versión de R-FEST-0001 vigente ESE día."""
    if not ANIO_MIN <= anio <= ANIO_MAX:
        raise ValueError(f"Año fuera del rango admitido ({ANIO_MIN}-{ANIO_MAX}): {anio}")
    salida = {}
    for regla in reglas.versiones("R-FEST-0001"):
        for observado, nombre, base in _candidatos(regla, anio):
            v = reglas.vigente("R-FEST-0001", observado)
            if v is None or v["version"] != regla["version"]:
                continue
            if observado in salida:      # dos festivos el mismo día: se conservan ambos nombres
                salida[observado]["nombre"] += " / " + nombre
                continue
            salida[observado] = {"nombre": nombre, "fecha_original": base, "regla": regla["id"],
                                 "version": regla["version"]}
    return dict(sorted(salida.items()))


def es_festivo(d: date):
    return festivos(d.year).get(d)


def semana_santa_judicial(anio: int) -> list:
    """Lunes, martes y miércoles santos (R-VAC-0002). Jueves y viernes ya son festivos."""
    regla = reglas.obtener("R-VAC-0002")
    domingo = pascua(anio)
    return [domingo + timedelta(days=n) for n in regla["parametros"]["dias_respecto_de_pascua"]]


def en_vacancia_fin_de_anio(d: date) -> bool:
    """20 de diciembre a 10 de enero, inclusive (R-VAC-0001)."""
    p = reglas.obtener("R-VAC-0001")["parametros"]
    ini, fin = p["inicio"], p["fin"]
    return (d.month == ini["mes"] and d.day >= ini["dia"]) or (d.month == fin["mes"] and d.day <= fin["dia"])


class Calendario:
    """Decide si un día es hábil y por qué no lo es. Todo lo que no es fin de semana ni festivo se activa
    explícitamente: vacancia judicial, Semana Santa judicial, suspensiones y cierres informados."""

    def __init__(self, sabado_habil=False, vacancia_judicial=False, semana_santa_judicial=False,
                 suspensiones=(), dias_no_habiles=()):
        self.sabado_habil = bool(sabado_habil)
        self.vacancia_judicial = bool(vacancia_judicial)
        self.semana_santa_judicial = bool(semana_santa_judicial)
        self.suspensiones = [(a, b, m) for a, b, m in suspensiones]
        self.dias_no_habiles = {d: m for d, m in dias_no_habiles}

    def motivo_inhabil(self, d: date):
        """None si el día es hábil; si no, el motivo en texto."""
        if d.weekday() == 6:
            return "domingo"
        if d.weekday() == 5 and not self.sabado_habil:
            return "sábado"
        f = es_festivo(d)
        if f:
            return "festivo: " + f["nombre"]
        if self.vacancia_judicial and en_vacancia_fin_de_anio(d):
            return "vacancia judicial (20 de diciembre a 10 de enero)"
        if self.semana_santa_judicial and d in semana_santa_judicial(d.year):
            return "vacancia judicial de Semana Santa"
        for a, b, m in self.suspensiones:
            if a <= d <= b:
                return "suspensión de términos" + (f": {m}" if m else "")
        if d in self.dias_no_habiles:
            return "día sin atención informado" + (f": {self.dias_no_habiles[d]}" if self.dias_no_habiles[d] else "")
        return None

    def es_habil(self, d: date) -> bool:
        return self.motivo_inhabil(d) is None

    def en_suspension(self, d: date):
        for a, b, m in self.suspensiones:
            if a <= d <= b:
                return m or "suspensión de términos"
        return None

    def siguiente_habil(self, d: date) -> date:
        """El primer día hábil igual o posterior a d."""
        while not self.es_habil(d):
            d += timedelta(days=1)
        return d


def sumar_meses(d: date, meses: int) -> date:
    """Mismo día del mes correspondiente; si ese mes no tiene ese día, el último del mes (CGP, art. 118)."""
    total = d.month - 1 + meses
    anio, mes = d.year + total // 12, total % 12 + 1
    ultimo = (date(anio + (mes == 12), mes % 12 + 1, 1) - timedelta(days=1)).day
    return date(anio, mes, min(d.day, ultimo))


def fecha_larga(d: date) -> str:
    return f"{DIAS[d.weekday()]} {d.day} de {MESES[d.month - 1]} de {d.year}"
