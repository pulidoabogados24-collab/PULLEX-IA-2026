"""Integración del motor de respuestas en /api/chat (PUL-017): contrato en el mensaje de sistema, presupuesto de tokens,
continuación automática, respuesta incompleta + «Continuar», latido, guardado de lo parcial, telemetría y valoración.

El modelo es un doble (FakeAnthropic con «guion»): estas pruebas verifican la tubería, NO la calidad jurídica del modelo real."""
import json
import threading
import time
from contextlib import closing

import pytest

from conftest import FakeAnthropic, auth, login_admin, nuevo_usuario

PREGUNTA_4 = "¿Qué delito sería, qué artículo aplica, hay dolo y qué podría alegar la defensa?"


@pytest.fixture(autouse=True)
def limpio(modulo):
    FakeAnthropic.guion = []
    FakeAnthropic.demora = 0.0
    FakeAnthropic.llamadas_stream = []
    FakeAnthropic.eventos_extra, FakeAnthropic.eventos_final = [], []
    yield
    FakeAnthropic.guion = []
    FakeAnthropic.demora = 0.0


def _conv(cliente, t):
    return cliente.post("/api/conversaciones", headers=auth(t)).json()["id"]


def _enviar(cliente, t, cid, mensaje, **extra):
    r = cliente.post("/api/chat", headers=auth(t), json={"conversacion": cid, "mensaje": mensaje, "web": False, **extra})
    assert r.status_code == 200, r.text
    return r


def _eventos(r):
    return [json.loads(l[6:]) for l in r.text.split("\n\n") if l.startswith("data: ")]


def _texto(ev):
    return "".join(e["texto"] for e in ev if e["tipo"] == "texto")


def _sistema(llamada):
    return " ".join(b["text"] for b in llamada["system"])


def _fila_mensaje(modulo, mid):
    with closing(modulo.db()) as con:
        return dict(con.execute("SELECT * FROM mensajes WHERE id=?", (mid,)).fetchone())


def _fila_calidad(modulo, mid):
    with closing(modulo.db()) as con:
        f = con.execute("SELECT * FROM calidad_respuestas WHERE mensaje_id=?", (mid,)).fetchone()
        return dict(f) if f else None


# ------------------------------------------------------------------------------ contrato y presupuesto
def test_el_contrato_viaja_en_el_bloque_dinamico_del_sistema(cliente):
    _, _, t = nuevo_usuario(cliente)
    _enviar(cliente, t, _conv(cliente, t), PREGUNTA_4)
    ll = FakeAnthropic.ultima_llamada
    sis = ll["system"]
    assert "cache_control" in sis[0] and "cache_control" in sis[1]               # fijo y guía de calidad, cacheados
    assert "cache_control" not in sis[-1]
    din = sis[-1]["text"]
    assert "CONTRATO DE RESPUESTA" in din and "«hay dolo»" in din and "«qué podría alegar la defensa»" in din
    assert "TODAS estas partes" in din


def test_la_guia_de_calidad_sale_del_archivo_si_existe(cliente, tmp_path, monkeypatch):
    ruta = tmp_path / "calidad.md"
    ruta.write_text("<!-- INICIO -->\nREGLA-DE-CALIDAD-DE-PRUEBA " + "x " * 150 + "\n<!-- FIN -->", encoding="utf-8")
    monkeypatch.setenv("PULLEX_PROMPT_CALIDAD", str(ruta))
    _, _, t = nuevo_usuario(cliente)
    _enviar(cliente, t, _conv(cliente, t), "Hola")
    assert "REGLA-DE-CALIDAD-DE-PRUEBA" in _sistema(FakeAnthropic.ultima_llamada)
    monkeypatch.setenv("PULLEX_PROMPT_CALIDAD", str(tmp_path / "no_existe.md"))
    _enviar(cliente, t, _conv(cliente, t), "Hola")
    assert "CALIDAD DE LA RESPUESTA" in _sistema(FakeAnthropic.ultima_llamada)      # constante de respaldo


def test_saludo_no_lleva_contrato(cliente):
    _, _, t = nuevo_usuario(cliente)
    _enviar(cliente, t, _conv(cliente, t), "Hola")
    assert "CONTRATO DE RESPUESTA" not in _sistema(FakeAnthropic.ultima_llamada)


def test_max_tokens_depende_de_la_profundidad_y_supera_el_tope_antiguo(cliente, modulo):
    _, _, t = nuevo_usuario(cliente)
    _enviar(cliente, t, _conv(cliente, t), "Hola")
    simple = FakeAnthropic.ultima_llamada["max_tokens"]
    _enviar(cliente, t, _conv(cliente, t), "Investiga la jurisprudencia reciente de la Corte Constitucional sobre tutela contra providencias judiciales")
    experta = FakeAnthropic.ultima_llamada["max_tokens"]
    assert simple < 4000 and experta > 8000 and experta <= modulo.MAX_TOKENS_CHAT


def test_seguimiento_lleva_la_pregunta_anterior_al_contrato_y_a_la_recuperacion(cliente):
    _, _, t = nuevo_usuario(cliente)
    cid = _conv(cliente, t)
    _enviar(cliente, t, cid, "Una persona golpeó a otra con una botella en una riña, ¿qué delito puede haber?")
    _enviar(cliente, t, cid, "¿y el dolo?")
    sis = _sistema(FakeAnthropic.ultima_llamada)
    assert "SEGUIMIENTO" in sis and "botella" in sis
    assert "AGENTE PENAL" in sis        # el área sale de la pregunta anterior, no solo de «¿y el dolo?»


def test_cabeceras_del_stream_evitan_buffering(cliente):
    _, _, t = nuevo_usuario(cliente)
    r = _enviar(cliente, t, _conv(cliente, t), "Hola")
    assert ("no-store" in r.headers["cache-control"] or "no-cache" in r.headers["cache-control"]) and r.headers["x-accel-buffering"] == "no"


# ----------------------------------------------------------------------------------- continuación
def test_se_corta_por_limite_y_el_servidor_continua_solo(cliente, modulo):
    _, _, t = nuevo_usuario(cliente)
    cid = _conv(cliente, t)
    FakeAnthropic.guion = [("La tutela es una acción constitucional prevista en el artículo 86 de la Constitución que permite", "max_tokens"),
                           ("prevista en el artículo 86 de la Constitución que permite proteger derechos fundamentales.", "end_turn")]
    ev = _eventos(_enviar(cliente, t, cid, "¿Qué es la tutela?"))
    esperado = "La tutela es una acción constitucional prevista en el artículo 86 de la Constitución que permite proteger derechos fundamentales."
    assert _texto(ev) == esperado
    assert any(e["tipo"] == "continuando" for e in ev) and not any(e["tipo"] == "incompleta" for e in ev)
    fin = ev[-1]
    assert fin["tipo"] == "fin" and fin["completo"] is True
    assert _fila_mensaje(modulo, fin["mensaje_id"])["contenido"] == esperado and not _fila_mensaje(modulo, fin["mensaje_id"])["incompleta"]
    seg = FakeAnthropic.llamadas_stream[1]["messages"]
    assert seg[-2]["role"] == "assistant" and seg[-1]["role"] == "user" and "se cortó" in seg[-1]["content"]
    q = _fila_calidad(modulo, fin["mensaje_id"])
    assert q["continuaciones"] == 1 and q["incompleta"] == 0 and q["parada"] == "fin"


def test_si_sigue_cortada_no_se_finge_que_esta_completa(cliente, modulo):
    _, _, t = nuevo_usuario(cliente)
    cid = _conv(cliente, t)
    FakeAnthropic.guion = [("Primer tramo del análisis jurídico que no termina porque se acabó el espacio disponible " + str(i), "max_tokens")
                           for i in range(10)]
    ev = _eventos(_enviar(cliente, t, cid, "¿Qué es la tutela?"))
    tipos = [e["tipo"] for e in ev]
    assert "incompleta" in tipos and tipos.index("incompleta") < tipos.index("fin")
    inc = next(e for e in ev if e["tipo"] == "incompleta")
    assert inc["motivo"] == "limite"
    assert ev[-1] == {"tipo": "fin", "mensaje_id": inc["mensaje_id"], "completo": False}
    assert len(FakeAnthropic.llamadas_stream) == modulo.motor.MAX_CONTINUACIONES + 1
    assert _fila_mensaje(modulo, inc["mensaje_id"])["incompleta"] == 1
    msgs = cliente.get(f"/api/conversaciones/{cid}/mensajes", headers=auth(t)).json()
    assert msgs[-1]["incompleta"] is True and msgs[-1]["id"] == inc["mensaje_id"] and msgs[0]["rol"] == "user"
    assert _fila_calidad(modulo, inc["mensaje_id"])["incompleta"] == 1


def test_boton_continuar_completa_la_respuesta_guardada_y_no_gasta_consultas(cliente, modulo):
    email, _, t = nuevo_usuario(cliente)
    cid = _conv(cliente, t)
    FakeAnthropic.guion = [("El término para contestar la demanda corre desde la notificación y se cuenta en días hábiles, de modo que", "max_tokens")] * 4
    ev = _eventos(_enviar(cliente, t, cid, "¿Cuántos días tengo para contestar la demanda?"))
    mid = next(e for e in ev if e["tipo"] == "incompleta")["mensaje_id"]
    usadas = cliente.get("/api/estado", headers=auth(t)).json()["perfil"]["usadas"]
    FakeAnthropic.llamadas_stream = []
    FakeAnthropic.guion = [("en días hábiles, de modo que son veinte días hábiles (verifica en el Código General del Proceso).", "end_turn")]
    r = cliente.post("/api/chat", headers=auth(t), json={"conversacion": cid, "continuar": True, "web": False})
    assert r.status_code == 200, r.text
    ev2 = _eventos(r)
    assert ev2[-1] == {"tipo": "fin", "mensaje_id": mid, "completo": True}
    fila = _fila_mensaje(modulo, mid)
    assert fila["incompleta"] == 0 and fila["contenido"].startswith("El término para contestar") and fila["contenido"].endswith("(verifica en el Código General del Proceso).")
    assert "de modo que son veinte días" in fila["contenido"] and fila["contenido"].count("de modo que") == 1   # sin duplicar el empalme
    assert cliente.get("/api/estado", headers=auth(t)).json()["perfil"]["usadas"] == usadas       # no cobró
    ll = FakeAnthropic.llamadas_stream[0]["messages"]
    assert ll[-2]["role"] == "assistant" and ll[-2]["content"].startswith("El término") and "se cortó" in ll[-1]["content"]
    assert _fila_calidad(modulo, mid)["pidio_continuar"] == 1
    # ya no hay nada que continuar
    r = cliente.post("/api/chat", headers=auth(t), json={"conversacion": cid, "continuar": True})
    assert r.status_code == 400


def test_continuar_no_funciona_con_conversaciones_ajenas_ni_sin_respuesta_incompleta(cliente):
    _, _, dueno = nuevo_usuario(cliente)
    _, _, otro = nuevo_usuario(cliente)
    cid = _conv(cliente, dueno)
    FakeAnthropic.guion = [("Texto cortado que no termina de explicar el tema porque se agotó el espacio", "max_tokens")] * 4
    _enviar(cliente, dueno, cid, "¿Qué es la tutela?")
    assert cliente.post("/api/chat", headers=auth(otro), json={"conversacion": cid, "continuar": True}).status_code == 404
    nueva = _conv(cliente, otro)
    assert cliente.post("/api/chat", headers=auth(otro), json={"conversacion": nueva, "continuar": True}).status_code == 400
    assert cliente.post("/api/chat", json={"conversacion": cid, "continuar": True}).status_code in (401, 403)


# ------------------------------------------------------------------------- errores y conexiones
def test_caida_a_mitad_de_la_respuesta_conserva_el_texto_y_permite_continuar(cliente, modulo):
    _, _, t = nuevo_usuario(cliente)
    cid = _conv(cliente, t)
    FakeAnthropic.guion = [("La acción de tutela protege derechos fundamentales cuando no existe otro medio de defensa judicial y, además,", RuntimeError("se cayó"))]
    usadas0 = cliente.get("/api/estado", headers=auth(t)).json()["perfil"]["usadas"]
    ev = _eventos(_enviar(cliente, t, cid, "¿Qué es la tutela?"))
    inc = next(e for e in ev if e["tipo"] == "incompleta")
    assert inc["motivo"] == "interrumpida" and "no está disponible" not in _texto(ev)
    assert _fila_mensaje(modulo, inc["mensaje_id"])["contenido"].startswith("La acción de tutela protege")
    assert cliente.get("/api/estado", headers=auth(t)).json()["perfil"]["usadas"] == usadas0 + 1      # recibió contenido: no se reintegra


def test_sin_una_sola_palabra_sigue_el_modo_degradado_y_se_reintegra(cliente, modulo):
    import anthropic as sdk
    _, _, t = nuevo_usuario(cliente)
    cid = _conv(cliente, t)
    FakeAnthropic.guion = [("", sdk.APIConnectionError(request=None))]
    usadas0 = cliente.get("/api/estado", headers=auth(t)).json()["perfil"]["usadas"]
    ev = _eventos(_enviar(cliente, t, cid, "¿Qué es la tutela?"))
    assert "no está disponible" in _texto(ev) and not any(e["tipo"] == "incompleta" for e in ev)
    assert ev[-1]["tipo"] == "fin" and cliente.get("/api/estado", headers=auth(t)).json()["perfil"]["usadas"] == usadas0


def test_si_la_persona_cierra_la_conexion_lo_generado_queda_guardado_como_incompleto(modulo, cliente):
    email, _, t = nuevo_usuario(cliente)
    cid = _conv(cliente, t)
    FakeAnthropic.guion = [("Respuesta que ya había empezado a llegar antes de que se cerrara la pestaña del navegador del usuario " * 3, "end_turn")]
    contrato = modulo.motor.clasificar("¿Qué es la tutela?")
    gen = modulo._flujo_chat(email=email, cid=cid, contrato=contrato, mensajes_api=[{"role": "user", "content": "¿Qué es la tutela?"}],
                             system=[{"type": "text", "text": "s"}], frags=[], restantes=5, info_ctx={}, usar_web=False)
    primero = next(gen)                                   # restantes
    while True:
        e = next(gen)
        if e.startswith("data:") and '"texto"' in e:
            break
    time.sleep(0.2)                                       # el hilo del modelo alcanza a escribir
    gen.close()                                           # la persona se fue
    with closing(modulo.db()) as con:
        f = con.execute("SELECT contenido, incompleta FROM mensajes WHERE conv=? AND rol='assistant'", (cid,)).fetchone()
    assert f is not None and f["incompleta"] == 1 and f["contenido"].startswith("Respuesta que ya había empezado")


def test_latido_mientras_el_modelo_tarda(cliente, modulo, monkeypatch):
    monkeypatch.setattr(modulo, "LATIDO_S", 0.05)
    FakeAnthropic.demora = 0.4
    _, _, t = nuevo_usuario(cliente)
    r = _enviar(cliente, t, _conv(cliente, t), "Hola")
    assert r.text.count(": latido\n\n") >= 2
    assert _eventos(r)[-1]["tipo"] == "fin"                # el cliente ignora los comentarios y recibe lo demás


def test_tiempo_agotado_sin_senales_usa_el_modo_degradado(cliente, modulo, monkeypatch):
    monkeypatch.setattr(modulo, "LATIDO_S", 0.05)
    monkeypatch.setattr(modulo, "INACTIVIDAD_S", 0.2)
    FakeAnthropic.demora = 1.0
    _, _, t = nuevo_usuario(cliente)
    ev = _eventos(_enviar(cliente, t, _conv(cliente, t), "¿Qué es la tutela?"))
    assert "no está disponible" in _texto(ev)
    time.sleep(1.1)                                       # deja terminar el hilo del doble


# ------------------------------------------------------------------------------------ MINERVA
def test_minerva_completa_la_parte_que_faltaba_con_un_solo_intento(cliente, modulo):
    _, _, t = nuevo_usuario(cliente)
    cid = _conv(cliente, t)
    primera = ("Sí, hay lesiones personales dolosas (artículo 111 de la Ley 599 de 2000, verificar). Hay dolo. " + "Análisis del caso. " * 50 +
               "En conclusión, lesiones personales dolosas.")
    FakeAnthropic.guion = [(primera, "end_turn"), ("Sobre la defensa: podría alegar legítima defensa.", "end_turn"), ("NO", "end_turn")]
    ev = _eventos(_enviar(cliente, t, cid, PREGUNTA_4))
    assert any(e["tipo"] == "reparando" for e in ev)
    assert len(FakeAnthropic.llamadas_stream) == 2
    texto = _texto(ev)
    assert texto.endswith("legítima defensa.") and "defensa:" in texto
    q = _fila_calidad(modulo, ev[-1]["mensaje_id"])
    assert q["reparada"] == 1 and q["n_partes"] == 4


# -------------------------------------------------------------------------------------- contexto
def test_contexto_enorme_se_recorta_sin_perder_la_pregunta_ni_los_hechos(cliente, modulo, monkeypatch):
    monkeypatch.setenv("PULLEX_CONTEXTO_MAX_CARACTERES", "12000")
    email, _, t = nuevo_usuario(cliente)
    cid = _conv(cliente, t)
    with closing(modulo.db()) as con:
        con.execute("INSERT INTO mensajes(conv,rol,contenido,creada) VALUES(?,?,?,?)",
                    (cid, "user", "El 3 de mayo de 2026 me despidieron de Acme S.A.S. con salario de $2.500.000. " + "hechos " * 50, time.time()))
        for i in range(20):
            con.execute("INSERT INTO mensajes(conv,rol,contenido,creada) VALUES(?,?,?,?)",
                        (cid, "assistant", f"Respuesta {i} " + "análisis " * 300, time.time()))
            con.execute("INSERT INTO mensajes(conv,rol,contenido,creada) VALUES(?,?,?,?)",
                        (cid, "user", f"Seguimiento {i} sobre la Ley 2466 de 2025", time.time()))
        con.commit()
    FakeAnthropic.guion = [("Listo.", "end_turn")]
    _enviar(cliente, t, cid, "PREGUNTA-ACTUAL-CLAVE ¿y la indemnización?")
    ll = FakeAnthropic.ultima_llamada
    assert ll["messages"][-1]["content"].endswith("PREGUNTA-ACTUAL-CLAVE ¿y la indemnización?")
    assert "Acme" in str(ll["messages"][0]["content"])
    assert sum(len(m["content"]) for m in ll["messages"]) < 20000
    assert "CONTEXTO RECORTADO" in _sistema(ll)


# --------------------------------------------------------------------------- telemetría y valoración
def test_la_telemetria_no_guarda_texto_de_la_persona_ni_su_correo(cliente, modulo):
    email, _, t = nuevo_usuario(cliente)
    cid = _conv(cliente, t)
    FakeAnthropic.guion = [("Respuesta de prueba sobre el despido de Carlos Ruiz en Medellín.", "end_turn")]
    ev = _eventos(_enviar(cliente, t, cid, "Me llamo Carlos Ruiz y me despidieron en Medellín, ¿cuánto me deben?"))
    q = _fila_calidad(modulo, ev[-1]["mensaje_id"])
    volcado = json.dumps(q, default=str).lower()
    for dato in ("carlos", "ruiz", "medell", email.lower(), email.split("@")[0].lower()):
        assert dato not in volcado
    assert q["usuario"] == modulo.anonimo(email) and q["usuario"] != email
    assert q["intencion"] and q["profundidad"] and q["area"] == "laboral" and q["caracteres"] > 0 and q["latencia_ms"] >= 0


def test_valoracion_con_motivos_y_tablero(cliente, modulo):
    email, _, t = nuevo_usuario(cliente)
    cid = _conv(cliente, t)
    ev = _eventos(_enviar(cliente, t, cid, "¿Qué es la tutela?"))
    mid = ev[-1]["mensaje_id"]
    r = cliente.post("/api/feedback", headers=auth(t), json={"mensaje": mid, "valor": "abajo",
                                                            "motivos": ["incompleta", "no_respondio", "inventado", "otro", "otro"]})
    assert r.status_code == 200 and r.json()["motivos"] == ["incompleta", "no_respondio", "otro"]
    q = _fila_calidad(modulo, mid)
    assert q["valoracion"] == "abajo" and json.loads(q["motivos"]) == ["incompleta", "no_respondio", "otro"]
    # cambiar de opinión reemplaza; 👍 no guarda motivos
    cliente.post("/api/feedback", headers=auth(t), json={"mensaje": mid, "valor": "arriba", "motivos": ["muy_larga"]})
    q = _fila_calidad(modulo, mid)
    assert q["valoracion"] == "arriba" and json.loads(q["motivos"]) == []
    cliente.post("/api/feedback", headers=auth(t), json={"mensaje": mid, "valor": "abajo", "motivos": ["error_juridico"]})
    adm = cliente.get("/api/admin/calidad?dias=7", headers=auth(login_admin(cliente))).json()
    assert adm["respuestas"] >= 1 and adm["valoraciones"]["abajo"] >= 1 and adm["motivos_abajo"]["error_juridico"] >= 1
    assert "tasa_truncada_final" in adm and "tasa_pregunta_omitida" in adm
    assert cliente.get("/api/admin/calidad", headers=auth(t)).status_code in (401, 403)


def test_valoracion_validaciones_y_aislamiento(cliente):
    _, _, dueno = nuevo_usuario(cliente)
    _, _, otro = nuevo_usuario(cliente)
    mid = _eventos(_enviar(cliente, dueno, _conv(cliente, dueno), "Hola"))[-1]["mensaje_id"]
    assert cliente.post("/api/feedback", headers=auth(otro), json={"mensaje": mid, "valor": "abajo"}).status_code == 404
    assert cliente.post("/api/feedback", headers=auth(dueno), json={"mensaje": mid, "valor": "regular"}).status_code == 400
    assert cliente.post("/api/feedback", headers=auth(dueno), json={"mensaje": "x", "valor": "arriba"}).status_code == 400
    assert cliente.post("/api/feedback", headers=auth(dueno), json={"mensaje": 999999, "valor": "arriba"}).status_code == 404
    assert cliente.post("/api/feedback", json={"mensaje": mid, "valor": "arriba"}).status_code in (401, 403)
    # no se puede valorar un mensaje del usuario (solo respuestas)
    cid = _conv(cliente, dueno)
    _enviar(cliente, dueno, cid, "Hola")
    msgs = cliente.get(f"/api/conversaciones/{cid}/mensajes", headers=auth(dueno)).json()
    id_usuario = next(m["id"] for m in msgs if m["rol"] == "user")
    assert cliente.post("/api/feedback", headers=auth(dueno), json={"mensaje": id_usuario, "valor": "arriba"}).status_code == 404


def test_borrar_la_conversacion_borra_su_telemetria(cliente, modulo):
    _, _, t = nuevo_usuario(cliente)
    cid = _conv(cliente, t)
    mid = _eventos(_enviar(cliente, t, cid, "Hola"))[-1]["mensaje_id"]
    assert _fila_calidad(modulo, mid) is not None
    assert cliente.delete(f"/api/conversaciones/{cid}", headers=auth(t)).status_code == 200
    assert _fila_calidad(modulo, mid) is None


def test_mensajes_incluyen_id_para_valorar(cliente):
    _, _, t = nuevo_usuario(cliente)
    cid = _conv(cliente, t)
    _enviar(cliente, t, cid, "Hola")
    msgs = cliente.get(f"/api/conversaciones/{cid}/mensajes", headers=auth(t)).json()
    assert all(isinstance(m["id"], int) for m in msgs) and msgs[1]["incompleta"] is False


def test_el_prompt_de_sistema_sigue_siendo_el_mismo_bloque_cacheado(cliente, modulo):
    _, _, t = nuevo_usuario(cliente)
    _enviar(cliente, t, _conv(cliente, t), "Hola")
    assert FakeAnthropic.ultima_llamada["system"][0]["text"] == modulo.SYSTEM_PROMPT
