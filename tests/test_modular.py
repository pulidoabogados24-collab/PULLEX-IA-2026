"""Laboratorio de casos y formas de respuesta del chat (con el doble del modelo)."""
from conftest import FakeAnthropic, auth, chat, nuevo_usuario

RESPUESTA = ("Procede la tutela porque el derecho a la salud es fundamental. La EPS negó un "
             "medicamento ordenado por el médico tratante y no hay otro medio eficaz.")


def _caso(cliente, t, **k):
    body = {"area": "Constitucional", "nivel": "basico", **k}
    return cliente.post("/api/modular/caso", headers=auth(t), json=body)


def test_opciones(cliente):
    _, _, t = nuevo_usuario(cliente)
    d = cliente.get("/api/modular/opciones", headers=auth(t)).json()
    assert "Penal" in d["areas"] and sum(r["max"] for r in d["rubrica"]) == 100


def test_caso_no_revela_la_solucion(cliente):
    _, _, t = nuevo_usuario(cliente)
    r = _caso(cliente, t)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["titulo"] and d["enunciado"] and d["pregunta"] and d["n_pistas"] == 2
    assert "solucion" not in d and "pistas" not in d and "CONCLUSION-SECRETA" not in str(d)
    assert d["restantes"] == 9  # generar un caso cuesta 1 consulta


def test_pistas_en_orden_y_gratis(cliente):
    _, _, t = nuevo_usuario(cliente)
    cid = _caso(cliente, t).json()["id"]
    p0 = cliente.post("/api/modular/pista", headers=auth(t), json={"caso_id": cid, "n": 0}).json()
    p1 = cliente.post("/api/modular/pista", headers=auth(t), json={"caso_id": cid, "n": 1}).json()
    assert p0["quedan"] == 1 and p1["quedan"] == 0 and p0["pista"] != p1["pista"]
    assert cliente.post("/api/modular/pista", headers=auth(t), json={"caso_id": cid, "n": 2}).status_code == 404
    assert cliente.get("/api/estado", headers=auth(t)).json()["perfil"]["restantes"] == 9


def test_evaluacion_con_rubrica_acotada(cliente):
    _, _, t = nuevo_usuario(cliente)
    cid = _caso(cliente, t).json()["id"]
    r = cliente.post("/api/modular/evaluar", headers=auth(t), json={"caso_id": cid, "respuesta": RESPUESTA})
    assert r.status_code == 200, r.text
    ev = r.json()
    # el doble devuelve normas=25 (fuera de escala): el servidor lo acota a 20
    assert ev["puntajes"]["normas"] == 20
    assert ev["total"] == 18 + 20 + 12 + 14 + 8 + 9
    assert ev["omitiste"] == ["inmediatez"] and ev["restantes"] == 8
    assert [x["nombre"] for x in ev["rubrica"]][0] == "Identificación del problema"


def test_respuesta_muy_corta_no_gasta_consulta(cliente):
    _, _, t = nuevo_usuario(cliente)
    cid = _caso(cliente, t).json()["id"]
    r = cliente.post("/api/modular/evaluar", headers=auth(t), json={"caso_id": cid, "respuesta": "procede"})
    assert r.status_code == 400
    assert cliente.get("/api/estado", headers=auth(t)).json()["perfil"]["restantes"] == 9


def test_solucion_y_variacion(cliente):
    _, _, t = nuevo_usuario(cliente)
    cid = _caso(cliente, t).json()["id"]
    sol = cliente.get(f"/api/modular/solucion?caso_id={cid}", headers=auth(t)).json()
    assert sol["conclusion"] == "CONCLUSION-SECRETA" and sol["normas"][0]["norma"] == "Art. 86 C.P."
    v = cliente.post("/api/modular/caso", headers=auth(t), json={"variacion_de": cid}).json()
    assert v["padre_id"] == cid and v["cambio"].startswith("¿Qué cambia si")
    assert "CASO ORIGINAL" in FakeAnthropic.llamadas_json[-1]


def test_casos_de_otro_estudiante_no_accesibles(cliente):
    _, _, a = nuevo_usuario(cliente)
    _, _, b = nuevo_usuario(cliente)
    cid = _caso(cliente, a).json()["id"]
    assert cliente.get(f"/api/modular/solucion?caso_id={cid}", headers=auth(b)).status_code == 404
    assert cliente.post("/api/modular/pista", headers=auth(b), json={"caso_id": cid}).status_code == 404


def test_progreso(cliente):
    _, _, t = nuevo_usuario(cliente)
    vacio = cliente.get("/api/modular/progreso", headers=auth(t)).json()
    assert vacio["resueltos"] == 0 and vacio["promedio"] is None
    cid = _caso(cliente, t).json()["id"]
    cliente.post("/api/modular/evaluar", headers=auth(t), json={"caso_id": cid, "respuesta": RESPUESTA})
    p = cliente.get("/api/modular/progreso", headers=auth(t)).json()
    assert p["resueltos"] == 1 and p["promedio"] == 81
    assert p["por_area"][0]["area"] == "Constitucional" and "inmediatez" in p["a_reforzar"]


def test_area_invalida(cliente):
    _, _, t = nuevo_usuario(cliente)
    assert _caso(cliente, t, area="Astrología").status_code == 400


def test_estilo_ensename_llega_al_modelo(cliente):
    _, _, t = nuevo_usuario(cliente)
    cid = cliente.post("/api/conversaciones", headers=auth(t)).json()["id"]
    cliente.post("/api/chat", headers=auth(t),
                 json={"conversacion": cid, "mensaje": "¿Qué es la prescripción?", "web": False, "estilo": "conmigo"})
    sistema = " ".join(b["text"] for b in FakeAnthropic.ultima_llamada["system"])
    assert "RESUÉLVELO CONMIGO" in sistema


def test_camino_en_preferencias(cliente):
    _, _, t = nuevo_usuario(cliente)
    r = cliente.post("/api/preferencias", headers=auth(t), json={"camino": "trabajar"})
    assert r.json()["preferencias"]["camino"] == "trabajar"
