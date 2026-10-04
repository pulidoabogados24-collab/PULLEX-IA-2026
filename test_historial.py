"""Historial de conversaciones que usa la pestaña Consultar."""
import time

from conftest import auth, chat, nuevo_usuario


def _nueva(cliente, t):
    return cliente.post("/api/conversaciones", headers=auth(t)).json()["id"]


def test_lista_omite_conversaciones_vacias(cliente):
    _, _, t = nuevo_usuario(cliente)
    vacia = _nueva(cliente, t)
    usada = _nueva(cliente, t)
    assert chat(cliente, t, usada, "Consulta sobre arrendamiento").status_code == 200
    ids = [c["id"] for c in cliente.get("/api/conversaciones", headers=auth(t)).json()]
    assert ids == [usada] and vacia not in ids


def test_lista_ordena_por_ultima_actividad(cliente):
    _, _, t = nuevo_usuario(cliente)
    a, b = _nueva(cliente, t), _nueva(cliente, t)
    chat(cliente, t, a, "Primera consulta")
    time.sleep(0.01)
    chat(cliente, t, b, "Segunda consulta")
    lista = cliente.get("/api/conversaciones", headers=auth(t)).json()
    assert [c["id"] for c in lista] == [b, a]
    assert lista[0]["titulo"] == "Segunda consulta" and lista[0]["actualizada"] > 0
    # retomar la conversación antigua la sube al primer lugar
    time.sleep(0.01)
    chat(cliente, t, a, "Sigo con la primera")
    assert [c["id"] for c in cliente.get("/api/conversaciones", headers=auth(t)).json()] == [a, b]
    # el título se fija con el primer mensaje y no cambia después
    assert cliente.get("/api/conversaciones", headers=auth(t)).json()[0]["titulo"] == "Primera consulta"


def test_lista_solo_muestra_las_propias(cliente):
    _, _, dueno = nuevo_usuario(cliente)
    _, _, otro = nuevo_usuario(cliente)
    cid = _nueva(cliente, dueno)
    chat(cliente, dueno, cid, "Mi consulta privada")
    assert cliente.get("/api/conversaciones", headers=auth(otro)).json() == []
    assert [c["id"] for c in cliente.get("/api/conversaciones", headers=auth(dueno)).json()] == [cid]


def test_renombrar_conversacion_propia(cliente):
    _, _, t = nuevo_usuario(cliente)
    cid = _nueva(cliente, t)
    chat(cliente, t, cid, "SOLICITUD DE REDACCIÓN — ACCIÓN DE TUTELA\n\nDatos…")
    r = cliente.post(f"/api/conversaciones/{cid}/titulo", headers=auth(t),
                     json={"titulo": "  Tutela\ncontra\tla EPS  " + "x" * 200})
    assert r.status_code == 200
    titulo = cliente.get("/api/conversaciones", headers=auth(t)).json()[0]["titulo"]
    assert titulo.startswith("Tutela contra la EPS x") and len(titulo) == 80 and "\n" not in titulo


def test_renombrar_conversacion_ajena_da_404(cliente):
    _, _, dueno = nuevo_usuario(cliente)
    _, _, atacante = nuevo_usuario(cliente)
    cid = _nueva(cliente, dueno)
    chat(cliente, dueno, cid, "Mi consulta")
    r = cliente.post(f"/api/conversaciones/{cid}/titulo", headers=auth(atacante), json={"titulo": "Hackeado"})
    assert r.status_code == 404
    assert cliente.get("/api/conversaciones", headers=auth(dueno)).json()[0]["titulo"] == "Mi consulta"


def test_renombrar_valida_el_titulo(cliente):
    _, _, t = nuevo_usuario(cliente)
    cid = _nueva(cliente, t)
    for malo in ({"titulo": "   "}, {"titulo": 123}, {}):
        assert cliente.post(f"/api/conversaciones/{cid}/titulo", headers=auth(t), json=malo).status_code == 400
    assert cliente.post(f"/api/conversaciones/{cid}/titulo", json={"titulo": "Sin sesión"}).status_code == 401
