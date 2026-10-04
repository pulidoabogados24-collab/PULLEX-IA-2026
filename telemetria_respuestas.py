"""Telemetría de calidad de las respuestas del chat (PUL-017, ítems 100 a 103 y 157 a 159 de la especificación).

Guarda en SQLite SOLO etiquetas y conteos por respuesta: intención, profundidad, área, cuántas partes pidió la persona y
cuántas se cubrieron, cómo terminó la generación (fin, límite, interrumpida…), cuántas continuaciones hubo, duración y largo.
NUNCA guarda el texto de la pregunta ni el de la respuesta, ni el correo: el usuario se identifica con un código
irreversible (HMAC con el secreto de la aplicación) que solo sirve para contar usuarios distintos (Ley 1581 de 2012,
principio de minimización). La valoración (👍/👎) guarda el motivo elegido de una lista cerrada, sin texto libre.

Las filas se borran con la conversación a la que pertenecen (ver ``borrar_de_mensajes``) y por antigüedad (``purgar``).
Sin dependencias de app.py: todas las funciones reciben la conexión SQLite.
"""
import json
import time

MOTIVOS = ("incompleta", "no_respondio", "error_juridico", "muy_larga", "otro")
ETIQUETAS_MOTIVO = {"incompleta": "Quedó incompleta", "no_respondio": "No respondió lo que pedí",
                    "error_juridico": "Tiene un error jurídico", "muy_larga": "Es demasiado larga", "otro": "Otro motivo"}
VALORES = ("arriba", "abajo")

_COLUMNAS = ("modelo", "intencion", "entregable", "profundidad", "area", "riesgo", "n_partes", "n_cubiertas", "veredicto",
             "puntaje", "caracteres", "palabras", "tokens_salida", "max_tokens", "latencia_ms", "primer_texto_ms", "parada",
             "continuaciones", "reparada", "incompleta", "fuentes", "web", "seguimiento", "reparacion_intencion",
             "contexto_omitidos", "sin_conclusion", "exceso_advertencias", "prompt_calidad")


def crear_tabla(con):
    cols = ", ".join(f"{c} {'TEXT' if c in ('modelo', 'intencion', 'entregable', 'profundidad', 'area', 'riesgo', 'veredicto', 'parada', 'prompt_calidad') else 'INTEGER'}"
                     for c in _COLUMNAS)
    con.executescript(f"""
    CREATE TABLE IF NOT EXISTS calidad_respuestas(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        mensaje_id INTEGER UNIQUE,
        creada REAL NOT NULL,
        usuario TEXT,
        {cols},
        pidio_continuar INTEGER DEFAULT 0,
        valoracion TEXT,
        motivos TEXT,
        valorada REAL);
    CREATE INDEX IF NOT EXISTS ix_calidad_creada ON calidad_respuestas(creada);
    """)


def registrar(con, mensaje_id, usuario_anonimo: str, datos: dict):
    """Una fila por respuesta. Solo se guardan las columnas conocidas; cualquier otra clave (p. ej. un texto) se ignora."""
    fila = {c: datos.get(c) for c in _COLUMNAS if c in datos}
    for k, v in list(fila.items()):
        if isinstance(v, bool):
            fila[k] = int(v)
        elif isinstance(v, float):
            fila[k] = round(v, 3)
        elif isinstance(v, str):
            fila[k] = v[:40]
    cols = ["mensaje_id", "creada", "usuario"] + list(fila)
    con.execute(f"INSERT OR REPLACE INTO calidad_respuestas({','.join(cols)}) VALUES({','.join('?' * len(cols))})",
                [mensaje_id, time.time(), usuario_anonimo] + list(fila.values()))
    con.commit()


def actualizar_resultado(con, mensaje_id, datos: dict):
    """Tras una continuación manual: la fila de la respuesta refleja cómo quedó al final."""
    fila = {c: (int(v) if isinstance(v, bool) else v) for c, v in datos.items() if c in _COLUMNAS}
    if not fila:
        return
    con.execute(f"UPDATE calidad_respuestas SET {','.join(c + '=?' for c in fila)} WHERE mensaje_id=?",
                list(fila.values()) + [mensaje_id])
    con.commit()


def marcar_continuar(con, mensaje_id):
    """La persona pulsó «Continuar»: señal de que la respuesta quedó insuficiente o cortada (ítem 101)."""
    con.execute("UPDATE calidad_respuestas SET pidio_continuar=pidio_continuar+1 WHERE mensaje_id=?", (mensaje_id,))
    con.commit()


def motivos_validos(motivos) -> list:
    if not isinstance(motivos, (list, tuple)):
        return []
    salida = []
    for m in motivos:
        if isinstance(m, str) and m in MOTIVOS and m not in salida:
            salida.append(m)
    return salida


def valorar(con, mensaje_id, usuario_anonimo: str, valor: str, motivos=()):
    """Guarda 👍 (arriba) o 👎 (abajo) con motivos de la lista cerrada. Una valoración por respuesta; volver a valorar la
    reemplaza. Si la respuesta no tenía fila (mensajes anteriores a la telemetría) se crea una mínima."""
    if valor not in VALORES:
        raise ValueError("valoración inválida")
    lista = motivos_validos(motivos) if valor == "abajo" else []
    cur = con.execute("UPDATE calidad_respuestas SET valoracion=?, motivos=?, valorada=? WHERE mensaje_id=?",
                      (valor, json.dumps(lista), time.time(), mensaje_id))
    if cur.rowcount != 1:
        con.execute("INSERT INTO calidad_respuestas(mensaje_id, creada, usuario, valoracion, motivos, valorada) "
                    "VALUES(?,?,?,?,?,?)", (mensaje_id, time.time(), usuario_anonimo, valor, json.dumps(lista), time.time()))
    con.commit()
    return lista


def borrar_de_mensajes(con, conversacion_id):
    """Al borrar una conversación se borran también las filas de telemetría de sus respuestas."""
    con.execute("DELETE FROM calidad_respuestas WHERE mensaje_id IN (SELECT id FROM mensajes WHERE conv=?)", (conversacion_id,))


def purgar(con, dias: int = 180) -> int:
    cur = con.execute("DELETE FROM calidad_respuestas WHERE creada < ?", (time.time() - dias * 86400,))
    con.commit()
    return cur.rowcount


def _percentil(valores, p):
    if not valores:
        return None
    v = sorted(valores)
    return v[min(len(v) - 1, int(round(p * (len(v) - 1))))]


def resumen(con, dias: int = 30) -> dict:
    """Métricas del tablero de calidad (ítems 157 a 159). ``tasa_pregunta_omitida`` es la métrica experimental
    «missed_question_rate»: partes pedidas sin cubrir sobre partes pedidas, según la comprobación léxica de ARGOS."""
    desde = time.time() - dias * 86400
    filas = [dict(f) for f in con.execute("SELECT * FROM calidad_respuestas WHERE creada >= ? AND caracteres IS NOT NULL", (desde,))]
    valoradas = [dict(f) for f in con.execute(
        "SELECT valoracion, motivos FROM calidad_respuestas WHERE valorada >= ?", (desde,))]
    n = len(filas)

    def tasa(cond):
        return round(sum(1 for f in filas if cond(f)) / n, 4) if n else None
    partes = sum(f["n_partes"] or 0 for f in filas)
    cubiertas = sum(f["n_cubiertas"] or 0 for f in filas)
    por_motivo = {}
    for v in valoradas:
        for mo in json.loads(v["motivos"] or "[]"):
            por_motivo[mo] = por_motivo.get(mo, 0) + 1
    lat = [f["latencia_ms"] for f in filas if f["latencia_ms"] is not None]
    por_prof = {}
    for f in filas:
        k = f["profundidad"] or "?"
        d = por_prof.setdefault(k, {"n": 0, "caracteres": 0})
        d["n"] += 1
        d["caracteres"] += f["caracteres"] or 0
    return {
        "dias": dias, "respuestas": n,
        "tasa_truncada_final": tasa(lambda f: f["incompleta"]),                     # objetivo: casi cero (ítem 158)
        "tasa_continuada_automatica": tasa(lambda f: (f["continuaciones"] or 0) > 0),
        "tasa_reparada": tasa(lambda f: f["reparada"]),
        "tasa_pidio_continuar": tasa(lambda f: (f["pidio_continuar"] or 0) > 0),
        "tasa_pregunta_omitida": round(1 - cubiertas / partes, 4) if partes else None,
        "tasa_sin_conclusion": tasa(lambda f: f["sin_conclusion"]),
        "caracteres_promedio": round(sum(f["caracteres"] or 0 for f in filas) / n) if n else None,
        "latencia_ms_p50": _percentil(lat, 0.5), "latencia_ms_p95": _percentil(lat, 0.95),
        "valoraciones": {"arriba": sum(1 for v in valoradas if v["valoracion"] == "arriba"),
                         "abajo": sum(1 for v in valoradas if v["valoracion"] == "abajo")},
        "motivos_abajo": por_motivo,
        "por_profundidad": {k: {"n": d["n"], "caracteres_promedio": round(d["caracteres"] / d["n"])} for k, d in por_prof.items()},
        "nota": "Solo etiquetas y conteos; no se guarda texto de preguntas ni de respuestas.",
    }
