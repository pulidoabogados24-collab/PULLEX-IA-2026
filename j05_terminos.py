"""J05 — Cómputo de términos. Calculadora DETERMINISTA y reproducible.

Entrada (dict):
    regimen               "cgp" | "contencioso" | "administrativo" | "tutela" | "otro"
    termino_id            id de la tabla de términos frecuentes (R-PLAZO-…)   — o, en su lugar:
    cantidad, unidad      número y "dias" | "meses" | "anios"
    tipo_dias             "habiles" | "calendario" (solo para días; obligatorio si la tabla no lo fija)
    fecha_notificacion    AAAA-MM-DD: día en que se surtió la notificación, recepción o hecho que dispara el término
    forma_notificacion    ver FORMAS
    acuse_constatado      true si hay acuse de recibo o acceso constatado (solo "mensaje_datos")
    vacancia_judicial     true | false | null: ¿el despacho tuvo vacancia colectiva del 20 dic al 10 ene?
    semana_santa_judicial true | false | null: ¿el despacho no atendió lunes a miércoles santos?
    sabado_habil          true si el despacho o la entidad atiende los sábados (por defecto false)
    suspensiones          [{"desde","hasta","motivo"}]
    dias_no_habiles       [{"fecha","motivo"}] cierres del despacho o de la entidad
    fecha_providencia     opcional, para detectar contradicciones
    cronologia            true para recibir el detalle día por día

Salida: estado CALCULADO | ABSTENCION | CONTRADICCION, fecha de vencimiento, cronología, normas (reglas del
registro con su estado), supuestos, advertencias y lo que queda a juicio profesional.

Lo determinista: calendario, conteo y validaciones. Lo que NO decide: cuándo se surtió la notificación, si el
despacho tuvo vacancia, si el término fue suspendido, si el recurso procede. Si falta un dato esencial, o un dato
desconocido cambia el resultado, se ABSTIENE de dar una fecha definitiva y muestra los escenarios.
"""
import hashlib
import json
from datetime import date, timedelta

import reglas
from procedimientos import calendario as cal

VERSION = "1.0.0"
PROCEDIMIENTO = "J05"

REGIMENES = {
    "cgp": {"nombre": "Proceso judicial regido por el Código General del Proceso", "judicial": True},
    "contencioso": {"nombre": "Proceso contencioso administrativo (CPACA)", "judicial": True},
    "tutela": {"nombre": "Acción de tutela", "judicial": True},
    "administrativo": {"nombre": "Actuación ante una autoridad administrativa", "judicial": False},
    "otro": {"nombre": "Otro (el usuario indica todo el régimen)", "judicial": False},
}
FORMAS = {
    "estado": "Notificación por estado",
    "personal": "Notificación personal (presencial)",
    "mensaje_datos": "Notificación personal por mensaje de datos (Ley 2213 de 2022, art. 8)",
    "aviso": "Notificación por aviso",
    "conducta_concluyente": "Notificación por conducta concluyente",
    "recepcion": "Recepción del escrito o de la petición por la autoridad",
    "comunicacion": "Comunicación, publicación o ejecución del acto",
    "hecho": "Ocurrencia o conocimiento del hecho",
    "audiencia": "Decisión notificada en audiencia (estrados)",
    "otra": "Otra forma (la fecha indicada es la del día en que quedó surtida)",
}
UNIDADES = ("dias", "meses", "anios")
MAX_CANTIDAD = {"dias": 400, "meses": 240, "anios": 30}
MAX_CRONOLOGIA = 450
TABLA = tuple(f"R-PLAZO-{n:04d}" for n in range(1, 16))


def tabla_terminos(fecha) -> list:
    """La tabla de términos frecuentes VIGENTE A UNA FECHA (solo reglas del registro, con su estado)."""
    salida = []
    for rid in TABLA:
        r = reglas.vigente(rid, fecha)
        if not r:
            continue
        p = r.get("parametros") or {}
        salida.append({"id": rid, "version": r["version"], "etiqueta": p.get("etiqueta") or r["titulo"],
                       "cantidad": p.get("cantidad"), "unidad": p.get("unidad"), "tipo_dias": p.get("tipo_dias"),
                       "regimen": p.get("regimen"), "evento_inicial": p.get("evento_inicial"),
                       "estado": r["estado"], "norma": reglas.referencia(r)["norma"],
                       "solo_informativo": bool(p.get("solo_informativo")),
                       "inicio_especial": bool(p.get("inicio_especial"))})
    return salida


def opciones(fecha=None) -> dict:
    hoy = reglas.a_fecha(fecha) if fecha else date.today()
    return {"regimenes": [{"id": k, "nombre": v["nombre"], "judicial": v["judicial"]} for k, v in REGIMENES.items()],
            "formas_notificacion": [{"id": k, "nombre": v} for k, v in FORMAS.items()],
            "unidades": list(UNIDADES), "tabla": tabla_terminos(hoy), "tabla_a_fecha": hoy.isoformat(),
            "version": VERSION}


# ------------------------------------------------------------------------------ utilidades --
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


def _tri(valor):
    """true/false/None desde JSON o desde un formulario ('si', 'no', 'no_se')."""
    if isinstance(valor, bool) or valor is None:
        return valor
    s = str(valor).strip().lower()
    if s in ("si", "sí", "true", "1"):
        return True
    if s in ("no", "false", "0"):
        return False
    return None


def _ref(rid, fecha, usadas):
    r = reglas.vigente(rid, fecha) if len(reglas.versiones(rid)) > 1 else reglas.obtener(rid)
    if r and r["id"] not in {u["id"] for u in usadas}:
        d = reglas.referencia(r)
        d["vigencia_comprobada_a_la_fecha"] = reglas.vigencia_comprobada(r, fecha)["comprobada"]
        usadas.append(d)
    return r


def _huella(entrada, resultado) -> str:
    base = json.dumps({"e": entrada, "r": resultado}, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(base.encode("utf-8")).hexdigest()[:16]


def _salida(estado, entrada_norm, **campos) -> dict:
    cuerpo = {"procedimiento": PROCEDIMIENTO, "version": VERSION,
              "version_registro": reglas.registro()["version_registro"], "estado": estado,
              "fecha_vencimiento": None, "fecha_vencimiento_texto": None, "inicio_computo": None,
              "termino": None, "cronologia": [], "normas": [], "supuestos": [], "advertencias": [],
              "juicio_profesional": [], "faltantes": [], "contradicciones": [], "escenarios": []}
    cuerpo.update(campos)
    cuerpo["entrada"] = entrada_norm
    cuerpo["huella"] = _huella(entrada_norm, {k: cuerpo[k] for k in ("estado", "fecha_vencimiento", "escenarios")})
    cuerpo["aviso"] = ("Cálculo de apoyo para revisión profesional. Verifique el expediente, el estado del proceso "
                       "y las normas citadas antes de actuar; no reemplaza el criterio del abogado.")
    return cuerpo


# ---------------------------------------------------------------------------------- conteo --
def _contar_dias(inicio: date, cantidad: int, habiles: bool, c: cal.Calendario):
    """Cuenta `cantidad` días desde `inicio` (incluido). Devuelve (vencimiento, cronología)."""
    crono, n, d = [], 0, inicio
    limite = inicio + timedelta(days=cantidad * 4 + 800)
    while True:
        if d > limite:
            raise ValueError("El conteo no termina: revise las suspensiones informadas.")
        if habiles:
            motivo = c.motivo_inhabil(d)
        else:
            s = c.en_suspension(d)
            motivo = ("suspensión de términos: " + s) if s else None
        if motivo is None:
            n += 1
        crono.append({"fecha": d.isoformat(), "dia": cal.DIAS[d.weekday()], "cuenta": n if motivo is None else None,
                      "motivo": motivo})
        if n == cantidad:
            return d, crono
        d += timedelta(days=1)


def _dias_suspendidos(desde: date, hasta: date, c: cal.Calendario) -> int:
    n, d = 0, desde
    while d <= hasta:
        if c.en_suspension(d):
            n += 1
        d += timedelta(days=1)
    return n


def _vencimiento_meses(inicio: date, cantidad: int, unidad: str, c: cal.Calendario):
    """Meses o años: mismo día del mes o año correspondiente; las suspensiones informadas corren el
    vencimiento tantos días como duraron dentro del término; si cae en inhábil, primer hábil siguiente."""
    nominal = cal.sumar_meses(inicio, cantidad * (12 if unidad == "anios" else 1))
    corrido, contados = nominal, 0
    while True:
        s = _dias_suspendidos(inicio, corrido, c)
        if s == contados:
            break
        corrido, contados = nominal + timedelta(days=s), s
    final = c.siguiente_habil(corrido)
    return nominal, corrido, final, contados


def _calcular(inicio, cantidad, unidad, habiles, c: cal.Calendario):
    if unidad == "dias":
        venc, crono = _contar_dias(inicio, cantidad, habiles, c)
        return {"vencimiento": venc, "cronologia": crono, "nominal": None, "suspendidos": None}
    nominal, corrido, final, susp = _vencimiento_meses(inicio, cantidad, unidad, c)
    crono = [{"fecha": inicio.isoformat(), "dia": cal.DIAS[inicio.weekday()], "cuenta": None,
              "motivo": "empieza a correr el término"},
             {"fecha": nominal.isoformat(), "dia": cal.DIAS[nominal.weekday()], "cuenta": None,
              "motivo": f"mismo día del {'año' if unidad == 'anios' else 'mes'} correspondiente"}]
    if corrido != nominal:
        crono.append({"fecha": corrido.isoformat(), "dia": cal.DIAS[corrido.weekday()], "cuenta": None,
                      "motivo": f"se corre {susp} día(s) por suspensión informada"})
    d = corrido
    while d < final:
        crono.append({"fecha": d.isoformat(), "dia": cal.DIAS[d.weekday()], "cuenta": None,
                      "motivo": "día inhábil: " + (c.motivo_inhabil(d) or "")})
        d += timedelta(days=1)
    crono.append({"fecha": final.isoformat(), "dia": cal.DIAS[final.weekday()], "cuenta": None, "motivo": "vence"})
    return {"vencimiento": final, "cronologia": crono, "nominal": nominal, "suspendidos": susp}


# ------------------------------------------------------------------------------- principal --
def calcular(entrada: dict) -> dict:
    if not isinstance(entrada, dict):
        return _salida("CONTRADICCION", {}, contradicciones=["La entrada debe ser un objeto con los datos del término."])
    faltantes, contradicciones, supuestos, advertencias, juicio, normas = [], [], [], [], [], []

    regimen = str(entrada.get("regimen") or "").strip().lower()
    forma = str(entrada.get("forma_notificacion") or "").strip().lower()
    if not regimen:
        faltantes.append("regimen")
    elif regimen not in REGIMENES:
        contradicciones.append(f"Régimen desconocido: {regimen!r}.")
    if not forma:
        faltantes.append("forma_notificacion")
    elif forma not in FORMAS:
        contradicciones.append(f"Forma de notificación desconocida: {forma!r}.")
    f_not = _fecha(entrada.get("fecha_notificacion"), "fecha_notificacion", contradicciones, faltantes)
    f_prov = _fecha(entrada.get("fecha_providencia"), "fecha_providencia", contradicciones, faltantes, False)

    # --- suspensiones y cierres informados
    suspensiones, cierres = [], []
    for i, s in enumerate(entrada.get("suspensiones") or [], 1):
        if not isinstance(s, dict):
            contradicciones.append(f"Suspensión {i}: formato no válido.")
            continue
        a = _fecha(s.get("desde"), f"suspensiones[{i}].desde", contradicciones, faltantes)
        b = _fecha(s.get("hasta"), f"suspensiones[{i}].hasta", contradicciones, faltantes)
        if a and b:
            if b < a:
                contradicciones.append(f"Suspensión {i}: termina ({b.isoformat()}) antes de empezar ({a.isoformat()}).")
            else:
                suspensiones.append((a, b, str(s.get("motivo") or "")[:160]))
    for i, x in enumerate(entrada.get("dias_no_habiles") or [], 1):
        x = x if isinstance(x, dict) else {"fecha": x}
        d = _fecha(x.get("fecha"), f"dias_no_habiles[{i}]", contradicciones, faltantes)
        if d:
            cierres.append((d, str(x.get("motivo") or "")[:160]))

    # --- el término: de la tabla (regla vigente A LA FECHA de la notificación) o indicado por el usuario
    termino_id = str(entrada.get("termino_id") or "").strip().upper()
    cantidad, unidad, tipo_dias, etiqueta, regla_plazo = None, None, None, None, None
    if termino_id:
        if termino_id not in TABLA:
            contradicciones.append(f"El término {termino_id!r} no está en la tabla de términos verificados.")
        elif f_not:
            regla_plazo = reglas.vigente(termino_id, f_not)
            if regla_plazo is None:
                faltantes.append(f"regla aplicable: {termino_id} no tiene versión registrada para "
                                 f"{f_not.isoformat()}; indique cantidad y unidad con su norma")
            else:
                p = regla_plazo.get("parametros") or {}
                cantidad, unidad, tipo_dias, etiqueta = p.get("cantidad"), p.get("unidad"), p.get("tipo_dias"), p.get("etiqueta")
                d = reglas.referencia(regla_plazo)
                d["vigencia_comprobada_a_la_fecha"] = reglas.vigencia_comprobada(regla_plazo, f_not)["comprobada"]
                normas.append(d)
                if regla_plazo.get("requiere_juicio_profesional"):
                    juicio.append(regla_plazo["requiere_juicio_profesional"])
                if regla_plazo["estado"] != reglas.VERIFICADA or cantidad is None:
                    faltantes.append(f"número de días aplicable: la regla {termino_id} versión "
                                     f"{regla_plazo['version']} está {regla_plazo['estado']} para esa fecha "
                                     f"({regla_plazo['soporte']['identificador']}); verifique el plazo en la "
                                     "fuente oficial e indíquelo en «cantidad»")
                    cantidad = None
                if regimen and p.get("regimen") and regimen in REGIMENES and regimen != p["regimen"]:
                    contradicciones.append(f"El término {termino_id} es del régimen «{p['regimen']}» y se indicó "
                                           f"«{regimen}».")
                if p.get("inicio_especial"):
                    advertencias.append("El punto de partida de este término es especial (ver juicio "
                                        "profesional): la fecha indicada debe ser la del día anterior a aquel en "
                                        "que empieza a correr.")
    if entrada.get("cantidad") not in (None, ""):
        try:
            cant_usuario = int(entrada["cantidad"])
            if isinstance(entrada["cantidad"], bool) or str(entrada["cantidad"]).strip() != str(cant_usuario):
                raise ValueError
        except (ValueError, TypeError):
            contradicciones.append("«cantidad» debe ser un número entero.")
            cant_usuario = None
        if cant_usuario is not None:
            if regla_plazo is not None and cantidad is not None and cant_usuario != cantidad:
                contradicciones.append(f"Se indicó cantidad {cant_usuario} pero la regla {termino_id} fija {cantidad}.")
            elif cantidad is None:
                cantidad = cant_usuario
                faltantes[:] = [f for f in faltantes if not f.startswith("número de días aplicable")]
                supuestos.append(f"El número ({cant_usuario}) lo indicó el usuario; no proviene de una regla verificada.")
    if entrada.get("unidad") and not unidad:
        unidad = str(entrada["unidad"]).strip().lower()
    unidad = {"días": "dias", "años": "anios", "mes": "meses", "dia": "dias", "anio": "anios"}.get(unidad, unidad)
    if entrada.get("tipo_dias") and not tipo_dias:
        tipo_dias = str(entrada["tipo_dias"]).strip().lower()
    tipo_dias = {"hábiles": "habiles"}.get(tipo_dias, tipo_dias)
    pendiente_de_fecha = termino_id in TABLA and f_not is None     # la regla se elige a la fecha: falta la fecha
    if cantidad is None and not pendiente_de_fecha and not any(
            f.startswith(("número de días", "regla aplicable")) for f in faltantes):
        faltantes.append("cantidad (o termino_id)")
    if not unidad:
        if not pendiente_de_fecha:
            faltantes.append("unidad")
    elif unidad not in UNIDADES:
        contradicciones.append(f"Unidad desconocida: {unidad!r}.")
    elif cantidad is not None and not 1 <= cantidad <= MAX_CANTIDAD[unidad]:
        contradicciones.append(f"La cantidad debe estar entre 1 y {MAX_CANTIDAD[unidad]} {unidad}.")
    if unidad == "dias":
        if not tipo_dias:
            faltantes.append("tipo_dias (hábiles o calendario)" + (
                ": la norma de este término no dice qué clase de días son" if regla_plazo is not None else ""))
        elif tipo_dias not in ("habiles", "calendario"):
            contradicciones.append(f"Tipo de días desconocido: {tipo_dias!r}.")

    # --- coherencia de fechas
    if f_not and f_prov and f_not < f_prov:
        contradicciones.append(f"La notificación ({f_not.isoformat()}) es anterior a la providencia "
                               f"({f_prov.isoformat()}).")
    if f_not and not cal.ANIO_MIN <= f_not.year <= cal.ANIO_MAX - 31:
        contradicciones.append(f"La fecha {f_not.isoformat()} está fuera del rango que maneja el calendario.")

    entrada_norm = {"regimen": regimen or None, "forma_notificacion": forma or None,
                    "fecha_notificacion": f_not.isoformat() if f_not else None,
                    "termino_id": termino_id or None, "cantidad": cantidad, "unidad": unidad, "tipo_dias": tipo_dias,
                    "vacancia_judicial": _tri(entrada.get("vacancia_judicial")),
                    "semana_santa_judicial": _tri(entrada.get("semana_santa_judicial")),
                    "sabado_habil": bool(_tri(entrada.get("sabado_habil"))),
                    "acuse_constatado": _tri(entrada.get("acuse_constatado")),
                    "suspensiones": [{"desde": a.isoformat(), "hasta": b.isoformat(), "motivo": m} for a, b, m in suspensiones],
                    "dias_no_habiles": [{"fecha": d.isoformat(), "motivo": m} for d, m in cierres]}
    termino = {"cantidad": cantidad, "unidad": unidad, "tipo_dias": tipo_dias if unidad == "dias" else None,
               "etiqueta": etiqueta}
    if contradicciones:
        return _salida("CONTRADICCION", entrada_norm, contradicciones=contradicciones, faltantes=faltantes,
                       normas=normas, termino=termino, juicio_profesional=juicio)
    if forma == "audiencia":
        r = _ref("R-TERM-0001", f_not, normas) if f_not else None
        juicio.append((r or {}).get("requiere_juicio_profesional") or
                      "El término concedido en audiencia corre «a partir de su otorgamiento».")
        faltantes.append("regla de inicio para decisiones notificadas en audiencia: requiere juicio profesional "
                         "(CGP, art. 118, inciso 1); indique como fecha el día desde el cual debe contarse y use la "
                         "forma «otra»")
    if forma == "mensaje_datos" and _tri(entrada.get("acuse_constatado")) is not True:
        faltantes.append("acuse_constatado: confirme que hay acuse de recibo o que se constató el acceso del "
                         "destinatario al mensaje (Ley 2213 de 2022, art. 8)")
    if faltantes:
        return _salida("ABSTENCION", entrada_norm, faltantes=faltantes, normas=normas, termino=termino,
                       juicio_profesional=juicio, advertencias=advertencias + [
                           "No se calcula una fecha: faltan datos esenciales. Complete lo indicado en «faltantes»."])

    judicial = REGIMENES[regimen]["judicial"]
    sabado = entrada_norm["sabado_habil"]
    habiles = unidad != "dias" or tipo_dias == "habiles"

    def calendario(vac, ss):
        return cal.Calendario(sabado_habil=sabado, vacancia_judicial=vac, semana_santa_judicial=ss,
                              suspensiones=suspensiones, dias_no_habiles=cierres)

    # --- contradicción: notificación judicial por estado en un día en que no hay estados
    base = calendario(judicial and entrada_norm["vacancia_judicial"] is True,
                      judicial and entrada_norm["semana_santa_judicial"] is True)
    if judicial and forma == "estado" and base.motivo_inhabil(f_not):
        return _salida("CONTRADICCION", entrada_norm, termino=termino, normas=normas, contradicciones=[
            f"La notificación por estado se indicó para el {cal.fecha_larga(f_not)}, que es día inhábil "
            f"({base.motivo_inhabil(f_not)}): no pudo fijarse un estado ese día. Revise la fecha."])
    if forma in ("personal", "aviso") and judicial and base.motivo_inhabil(f_not):
        advertencias.append(f"La fecha de notificación indicada ({cal.fecha_larga(f_not)}) es día inhábil "
                            f"({base.motivo_inhabil(f_not)}). Confirme la fecha en el expediente.")

    # --- inicio del cómputo
    def inicio_con(c: cal.Calendario):
        if forma == "mensaje_datos":
            d, n = f_not, 0
            while n < 2:                                   # dos días hábiles siguientes al envío
                d += timedelta(days=1)
                if c.es_habil(d):
                    n += 1
            return d + timedelta(days=1), d
        return f_not + timedelta(days=1), f_not

    def escenario(vac, ss):
        c = calendario(vac, ss)
        inicio, surtida = inicio_con(c)
        r = _calcular(inicio, cantidad, unidad, habiles, c)
        r.update(inicio=inicio, surtida=surtida, calendario=c)
        return r

    vac_in, ss_in = entrada_norm["vacancia_judicial"], entrada_norm["semana_santa_judicial"]
    if judicial:
        combos = [(v, s) for v in ([vac_in] if vac_in is not None else [True, False])
                  for s in ([ss_in] if ss_in is not None else [True, False])]
    else:
        combos = [(False, False)]
        if vac_in or ss_in:
            advertencias.append("La vacancia judicial no se aplica a una actuación administrativa; si la entidad "
                                "cerró, informe esos días como «días sin atención».")
    resultados = [(v, s, escenario(v, s)) for v, s in combos]
    fechas = {r["vencimiento"] for _, _, r in resultados}

    # --- normas y supuestos comunes
    _ref("R-FEST-0001", f_not, normas)
    _ref("R-FEST-0002", f_not, normas)
    _ref("R-FEST-0003", f_not, normas)
    if unidad == "dias":
        if judicial:
            _ref("R-TERM-0001", f_not, normas)
            _ref("R-TERM-0003", f_not, normas)
        _ref("R-TERM-0004", f_not, normas)
    else:
        _ref("R-TERM-0002", f_not, normas)
        _ref("R-TERM-0004", f_not, normas)
        if not judicial or regimen != "cgp":
            juicio.append(reglas.obtener("R-TERM-0002")["requiere_juicio_profesional"])
    if regimen == "contencioso":
        r = _ref("R-TERM-0009", f_not, normas)
        juicio.append(r["requiere_juicio_profesional"])
    if forma == "mensaje_datos":
        r = _ref("R-TERM-0006", f_not, normas)
        if reglas.vigente("R-TERM-0006", f_not) is None:
            return _salida("ABSTENCION", entrada_norm, termino=termino, normas=normas, faltantes=[
                "regla aplicable a la notificación por mensaje de datos en esa fecha: la Ley 2213 de 2022 rige "
                "desde el 13 de junio de 2022 y el régimen anterior no está registrado"])
        juicio.append(r["requiere_juicio_profesional"])
        juicio.append("Se entendió surtida la notificación al terminar el segundo día hábil siguiente al envío y "
                      "el término se contó desde el día siguiente. Existe otra lectura que lo inicia un día después; "
                      "aquí se usa la que da la fecha más temprana.")
    _ref("R-TERM-0005", f_not, normas)
    sab = _ref("R-TERM-0007", f_not, normas)
    supuestos.append(("El sábado se contó como día hábil porque así se indicó." if sabado else
                      "El sábado NO se contó como día hábil (supuesto no verificado en fuente oficial: cámbielo si "
                      "el despacho o la entidad atiende los sábados).") + f" [{sab['id']}]")
    if unidad == "dias":
        supuestos.append("El término empieza a contarse el día siguiente al de la notificación o recepción indicada.")
        if not habiles:
            supuestos.append("Días calendario: se cuentan todos los días, salvo los de suspensión informada.")
    else:
        supuestos.append("El término de meses o años vence el mismo día en que empezó a correr del mes o año "
                         "correspondiente; si es inhábil, pasa al primer día hábil siguiente.")
    if suspensiones:
        supuestos.append("Las suspensiones las informó el usuario; el procedimiento no verifica que existan ni "
                         "su duración.")
        juicio.append("Si hubo suspensión o interrupción del término y entre qué fechas es una cuestión jurídica "
                      "que debe constar en el expediente.")
        if unidad != "dias":
            juicio.append("En términos de meses o años, las suspensiones se aplicaron corriendo el vencimiento "
                          "tantos días calendario como duró la suspensión dentro del término (método declarado).")
    if cierres:
        supuestos.append("Los días sin atención los informó el usuario.")
    sin_verificar = [n["id"] for n in normas if n["estado"] != reglas.VERIFICADA]
    no_comprobadas = [n["id"] for n in normas
                      if n["estado"] == reglas.VERIFICADA and not n["vigencia_comprobada_a_la_fecha"]]
    if sin_verificar:
        advertencias.append("Este cálculo usa supuestos no verificados en fuente oficial: " +
                            ", ".join(sin_verificar) + " (ver «supuestos»).")
    if no_comprobadas:
        advertencias.append("Reglas verificadas el " + reglas.registro()["actualizado"] + " cuya vigencia en la "
                            "fecha del cómputo no está comprobada: " + ", ".join(no_comprobadas) +
                            ". Confirme que la norma era la misma en esa fecha.")

    if judicial and len(fechas) > 1:
        # Un dato desconocido cambia el resultado: no se da fecha definitiva.
        _ref("R-VAC-0001", f_not, normas)
        _ref("R-VAC-0002", f_not, normas)
        _ref("R-VAC-0003", f_not, normas)
        desconocidos = []
        # ¿Cuál de los datos desconocidos cambia el resultado? (se compara dejando fijo el otro)
        afecta_vac = vac_in is None and any(
            len({r["vencimiento"] for v, s, r in resultados if s == s0}) > 1 for s0 in {s for _, s, _ in resultados})
        afecta_ss = ss_in is None and any(
            len({r["vencimiento"] for v, s, r in resultados if v == v0}) > 1 for v0 in {v for v, _, _ in resultados})
        if afecta_vac:
            desconocidos.append("vacancia_judicial: indique si el despacho tuvo vacancia colectiva del 20 de "
                                "diciembre al 10 de enero")
        if afecta_ss:
            desconocidos.append("semana_santa_judicial: indique si el despacho no atendió el lunes, martes y "
                                "miércoles santos")
        escenarios, vistos = [], set()
        for v, s, r in resultados:
            clave = (v if afecta_vac else None, s if afecta_ss else None)
            if clave in vistos:
                continue
            vistos.add(clave)
            e = {"fecha_vencimiento": r["vencimiento"].isoformat(),
                 "fecha_vencimiento_texto": cal.fecha_larga(r["vencimiento"])}
            if afecta_vac:
                e["vacancia_judicial"] = v
            if afecta_ss:
                e["semana_santa_judicial"] = s
            escenarios.append(e)
        return _salida("ABSTENCION", entrada_norm, termino=termino, normas=normas, supuestos=supuestos,
                       faltantes=desconocidos, escenarios=escenarios, juicio_profesional=juicio,
                       advertencias=advertencias + [
                           "No se da una fecha definitiva: el resultado cambia según un dato que no se indicó. "
                           "Se muestran los escenarios posibles."])

    vac, ss, res = resultados[0]
    c = res["calendario"]
    venc = res["vencimiento"]
    if judicial:
        usados_vac = any(x["motivo"] and "vacancia judicial (20" in x["motivo"] for x in res["cronologia"])
        usados_ss = any(x["motivo"] and "Semana Santa" in x["motivo"] for x in res["cronologia"])
        if usados_vac:
            _ref("R-VAC-0001", f_not, normas)
            _ref("R-VAC-0003", f_not, normas)
            supuestos.append("Se descontó la vacancia judicial del 20 de diciembre al 10 de enero porque el "
                             "usuario indicó que el despacho la tuvo.")
        if usados_ss:
            r = _ref("R-VAC-0002", f_not, normas)
            supuestos.append("Se descontaron el lunes, martes y miércoles santos porque el usuario indicó que el "
                             "despacho no atendió.")
            juicio.append(r["requiere_juicio_profesional"])
        if vac_in is None or ss_in is None:
            supuestos.append("No se indicó si hubo vacancia judicial o cierre en Semana Santa; el resultado es el "
                             "mismo en cualquiera de los casos.")
    if unidad == "dias" and not habiles and c.motivo_inhabil(venc):
        advertencias.append(f"El último día ({cal.fecha_larga(venc)}) es inhábil ({c.motivo_inhabil(venc)}). La "
                            "extensión al primer día hábil siguiente solo está verificada para plazos de meses y "
                            "años: confirme la regla aplicable a este plazo en días calendario.")
    if regimen == "tutela":
        juicio.append("En tutela, confirme con el despacho la fecha en que se surtió la notificación y si atendió "
                      "durante la vacancia judicial.")
    if regimen == "otro":
        juicio.append("Régimen «otro»: el usuario fijó la clase de días y el número; verifique la norma especial "
                      "que rige el término.")
    crono = res["cronologia"]
    if forma == "mensaje_datos":
        previos, d = [], f_not
        while d <= res["surtida"]:
            previos.append({"fecha": d.isoformat(), "dia": cal.DIAS[d.weekday()], "cuenta": None,
                            "motivo": "envío del mensaje" if d == f_not else
                            (c.motivo_inhabil(d) or "día hábil siguiente al envío (aún no corre el término)")})
            d += timedelta(days=1)
        crono = previos + crono
        supuestos.append(f"Notificación entendida como surtida el {cal.fecha_larga(res['surtida'])}.")
    elif unidad == "dias":
        crono = [{"fecha": f_not.isoformat(), "dia": cal.DIAS[f_not.weekday()], "cuenta": None,
                  "motivo": "día de la notificación o recepción (no se cuenta)"}] + crono
    recortada = len(crono) > MAX_CRONOLOGIA
    return _salida("CALCULADO", entrada_norm, termino=termino, normas=normas, supuestos=supuestos,
                   advertencias=advertencias, juicio_profesional=juicio,
                   fecha_vencimiento=venc.isoformat(), fecha_vencimiento_texto=cal.fecha_larga(venc),
                   inicio_computo=res["inicio"].isoformat(),
                   cronologia=(crono[:MAX_CRONOLOGIA] if entrada.get("cronologia", True) else []),
                   cronologia_recortada=recortada,
                   dias_inhabiles_descontados=sum(1 for x in res["cronologia"] if x["motivo"] and x["cuenta"] is None)
                   if unidad == "dias" else None)
