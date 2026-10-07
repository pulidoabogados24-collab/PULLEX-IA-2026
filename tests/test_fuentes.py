"""Motor de fuentes: índice FTS5, clasificación, exclusión de datos de personas, búsqueda con y sin
tildes, evento SSE "fuentes", fuentes guardadas por mensaje, aislamiento entre usuarios, modelo y
búsqueda web restringida. Ninguna prueba llama a la API real."""
import io
import json
import os
import sys
import types
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from conftest import FakeAnthropic, auth, nuevo_usuario

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
import fuentes  # noqa: E402

ns = types.SimpleNamespace

TEXTO_PETICION = ("Toda persona tiene derecho a presentar peticiones respetuosas a las autoridades por motivos de "
                  "interés general o particular y a obtener pronta resolución. La petición debe resolverse de fondo.")
TEXTO_TUTELA = ("La acción de tutela procede para la protección inmediata de los derechos fundamentales. "
                "Se estudian la subsidiariedad y la inmediatez antes de decidir el fondo del asunto.")
TEXTO_PENAL = "El hurto se configura cuando una persona se apodera de una cosa mueble ajena con propósito de provecho."


def _sse(texto):
    return [json.loads(l[6:]) for l in texto.split("\n\n") if l.startswith("data: ")]


@pytest.fixture
def corpus(tmp_path, monkeypatch):
    ruta = tmp_path / "corpus.db"
    con = fuentes.abrir(str(ruta))
    fuentes.indexar(con, origen="local:02_LEYES/Ley 1755 de 2015.txt", nombre="Ley 1755 de 2015.txt",
                    paginas=[("pág. 1", TEXTO_PETICION)], carpeta="02_LEYES",
                    fecha_archivo="2024-02-10T00:00:00+00:00")
    fuentes.indexar(con, origen="local:03_JURISPRUDENCIA/SENTENCIA T-100 DE 2020.txt",
                    nombre="SENTENCIA T-100 DE 2020.txt", paginas=[("pág. 4", TEXTO_TUTELA)],
                    carpeta="03_JURISPRUDENCIA")
    fuentes.indexar(con, origen="local:01_CODIGOS/Codigo penal.txt", nombre="Codigo penal.txt",
                    paginas=[("pág. 80", TEXTO_PENAL)], carpeta="01_CODIGOS")
    con.close()
    monkeypatch.setenv("PULLEX_CORPUS_DB", str(ruta))
    return ruta


@pytest.fixture(autouse=True)
def limpiar_eventos():
    FakeAnthropic.eventos_extra, FakeAnthropic.eventos_final = [], []
    yield
    FakeAnthropic.eventos_extra, FakeAnthropic.eventos_final = [], []


# ---------------------------------------------------------- clasificación --
@pytest.mark.parametrize("nombre,esperado", [
    ("SENTENCIA C-420 DE 2020.pdf", {"tipo": "sentencia", "autoridad": "Corte Constitucional", "numero": "C-420", "anio": 2020}),
    ("Sentencia T-760-08.pdf", {"tipo": "sentencia", "numero": "T-760", "anio": 2008}),
    ("SU-214 de 2016.docx", {"tipo": "sentencia", "numero": "SU-214", "anio": 2016}),
    ("SL1234-2019.pdf", {"tipo": "sentencia", "autoridad": "Corte Suprema de Justicia", "anio": 2019}),
    ("Ley 1755 de 2015.pdf", {"tipo": "ley", "numero": "1755", "anio": 2015}),
    ("LEY 1098 DE 2006.pdf", {"tipo": "ley", "numero": "1098", "anio": 2006}),
    ("Decreto 2591 de 1991.pdf", {"tipo": "decreto", "numero": "2591", "anio": 1991}),
    ("Codigo penal.pdf", {"tipo": "codigo"}),
    ("CÓDIGO GENERAL DEL PROCESO.pdf", {"tipo": "codigo"}),
    ("Modelo de tutela salud.docx", {"tipo": "plantilla"}),
])
def test_clasificacion_por_nombre(nombre, esperado):
    r = fuentes.clasificar_nombre(nombre)
    for k, v in esperado.items():
        assert r[k] == v, (nombre, k, r)


def test_clasificacion_usa_la_carpeta_si_el_nombre_no_basta():
    assert fuentes.clasificar_nombre("pensiones.pdf", "06_REGIMENES")["tipo"] == "otro"
    assert fuentes.clasificar_nombre("responsabilidad civil.pdf", "05_DOCTRINA")["tipo"] == "doctrina"
    assert fuentes.clasificar_nombre("arrendamiento.docx", "04_PLANTILLAS")["tipo"] == "plantilla"


# -------------------------------------------------- exclusión de personas --
@pytest.mark.parametrize("ruta", [
    "CLIENTES/demanda.pdf",
    "07_EJEMPLOS_MODELOS_CASOS/Cliente Gomez/poder.pdf",
    "EXPEDIENTE 2023-0045/contestacion.docx",
    "07_EJEMPLOS_MODELOS_CASOS/JUAN PEREZ GOMEZ TUTELA.pdf",
    "07_EJEMPLOS_MODELOS_CASOS/MARIA LOPEZ - DERECHO DE PETICION.docx",
    "07_EJEMPLOS_MODELOS_CASOS/Ana María Ruiz - Tutela.pdf",
    "CARLOS ANDRES ROJAS/poder.pdf",
])
def test_excluye_carpetas_y_archivos_de_personas(ruta):
    assert fuentes.es_excluido(ruta) is not None, ruta


@pytest.mark.parametrize("ruta", [
    "04_PLANTILLAS/MODELO DE TUTELA.docx",
    "04_PLANTILLAS/DERECHO DE PETICION GENERAL.docx",
    "04_PLANTILLAS/Acción De Tutela - Salud.docx",
    "04_PLANTILLAS/PODER ESPECIAL AMPLIO.docx",
    "01_CODIGOS/Codigo penal.pdf",
    "03_JURISPRUDENCIA/CORTE CONSTITUCIONAL/SENTENCIA C-420 DE 2020.pdf",
    "02_LEYES/LEY 1755 DE 2015.pdf",
])
def test_no_excluye_material_general(ruta):
    assert fuentes.es_excluido(ruta) is None, ruta


def test_lista_de_exclusion_configurable(monkeypatch, tmp_path):
    monkeypatch.setenv("PULLEX_CORPUS_EXCLUIR", "*borrador*, 06_REGIMENES/viejo")
    archivo = tmp_path / "excluir.txt"
    archivo.write_text("# comentario\n*.md\n!TITULOS VALORES*\n", encoding="utf-8")
    monkeypatch.setenv("PULLEX_CORPUS_EXCLUIR_ARCHIVO", str(archivo))
    pats = fuentes.patrones_exclusion()
    assert fuentes.es_excluido("05_DOCTRINA/Borrador tesis.pdf", pats)
    assert fuentes.es_excluido("06_REGIMENES/viejo/pension.pdf", pats)
    assert fuentes.es_excluido("05_DOCTRINA/notas.md", pats)
    assert fuentes.es_excluido("05_DOCTRINA/notas.pdf", pats) is None
    # "!" permite rutas que la heurística de nombres habría excluido, pero nunca anula CLIENTE/EXPEDIENTE.
    assert fuentes.es_excluido("TITULOS VALORES RAROS/letra.pdf", pats) is None
    assert fuentes.es_excluido("TITULOS VALORES RAROS/CLIENTES/letra.pdf", pats)


# ------------------------------------------------------------- vigencia --
def test_estado_inicial_y_vencimiento_de_la_verificacion():
    ahora = datetime(2026, 10, 1, tzinfo=timezone.utc)
    assert fuentes.estado_inicial("2024-02-10T00:00:00+00:00", ahora=ahora) == "PENDIENTE_VERIFICAR"
    assert fuentes.estado_inicial("2026-09-01T00:00:00+00:00", ahora=ahora) == "PENDIENTE_VERIFICAR"  # sin verificación
    assert fuentes.estado_inicial("2026-09-01", verificado_en="2026-09-20", ahora=ahora) == "VIGENTE_VERIFICADA"
    hace_13_meses = (ahora - timedelta(days=400)).date().isoformat()
    assert fuentes.estado_efectivo("VIGENTE_VERIFICADA", hace_13_meses, ahora) == "PENDIENTE_VERIFICAR"
    assert fuentes.estado_efectivo("DEROGADA", None, ahora) == "DEROGADA"


def test_trocear_con_solape():
    texto = " ".join(f"palabra{i}" for i in range(800))
    trozos = fuentes.trocear(texto)
    assert len(trozos) > 3
    assert all(len(t) <= fuentes.TAM_FRAGMENTO for t in trozos)
    assert trozos[0].split()[-1] in trozos[1]  # el final de uno reaparece al inicio del siguiente


# ------------------------------------------------------ indexación y búsqueda --
def test_indexa_y_busca_con_y_sin_tildes(corpus):
    sin = fuentes.buscar("que dice la ley sobre el derecho de peticion")
    con = fuentes.buscar("¿Qué dice la ley sobre el derecho de petición?")
    assert sin and con
    assert sin[0]["titulo"] == con[0]["titulo"] == "Ley 1755 de 2015"
    f = con[0]
    assert f["ref"] == "F1" and f["tipo"] == "ley" and f["ubicacion"] == "pág. 1"
    assert f["estado_vigencia"] == "PENDIENTE_VERIFICAR"   # archivo de 2024 y sin verificación
    # plural/singular y mayúsculas
    assert fuentes.buscar("TUTELAS subsidiariedad")[0]["titulo"] == "SENTENCIA T-100 DE 2020"


def test_busqueda_no_trae_ruido(corpus):
    assert fuentes.buscar("hola, ¿cómo estás?") == []
    assert fuentes.buscar("receta de arepas con queso") == []


def test_sin_indice_no_falla(tmp_path, monkeypatch):
    monkeypatch.setenv("PULLEX_CORPUS_DB", str(tmp_path / "no-existe.db"))
    assert fuentes.buscar("tutela") == [] and not fuentes.disponible()
    assert not (tmp_path / "no-existe.db").exists()  # la búsqueda nunca crea el archivo


def test_reindexar_es_idempotente_y_un_cambio_vuelve_a_pendiente(corpus):
    con = fuentes.abrir(str(corpus))
    fid = con.execute("SELECT id FROM fuentes WHERE titulo='SENTENCIA T-100 DE 2020'").fetchone()["id"]
    assert fuentes.marcar_estado(con, fid, "VIGENTE_VERIFICADA")
    r = fuentes.indexar(con, origen="local:03_JURISPRUDENCIA/SENTENCIA T-100 DE 2020.txt",
                        nombre="SENTENCIA T-100 DE 2020.txt", paginas=[("pág. 4", TEXTO_TUTELA)])
    assert r["accion"] == "sin_cambios"
    assert fuentes.buscar("tutela subsidiariedad")[0]["estado_vigencia"] == "VIGENTE_VERIFICADA"
    r = fuentes.indexar(con, origen="local:03_JURISPRUDENCIA/SENTENCIA T-100 DE 2020.txt",
                        nombre="SENTENCIA T-100 DE 2020.txt", paginas=[("pág. 4", TEXTO_TUTELA + " Texto nuevo.")])
    assert r["accion"] == "actualizado"
    assert con.execute("SELECT COUNT(*) n FROM fragmentos WHERE fuente_id=?", (fid,)).fetchone()["n"] == 1
    assert fuentes.buscar("tutela subsidiariedad")[0]["estado_vigencia"] == "PENDIENTE_VERIFICAR"
    con.close()


# --------------------------------------------------------------- ingesta --
def _docx(texto):
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w") as z:
        z.writestr("[Content_Types].xml", "<Types/>")
        z.writestr("word/document.xml", "<w:document><w:body><w:p><w:r><w:t>" + texto +
                   "</w:t></w:r></w:p></w:body></w:document>")
    return b.getvalue()


def test_ingesta_desde_carpeta_local(tmp_path):
    import importlib
    sys.path.insert(0, str(RAIZ / "scripts"))
    ing = importlib.import_module("ingesta_corpus")
    base = tmp_path / "LEXCOL_CORPUS"
    (base / "01_CODIGOS").mkdir(parents=True)
    (base / "04_PLANTILLAS").mkdir()
    (base / "07_EJEMPLOS_MODELOS_CASOS" / "CLIENTE RAMIREZ").mkdir(parents=True)
    codigo = base / "01_CODIGOS" / "Codigo penal.txt"
    codigo.write_text(TEXTO_PENAL, encoding="utf-8")
    vieja = datetime(2024, 2, 1, tzinfo=timezone.utc).timestamp()
    os.utime(codigo, (vieja, vieja))
    (base / "04_PLANTILLAS" / "Modelo de derecho de peticion.docx").write_bytes(_docx(TEXTO_PETICION))
    (base / "04_PLANTILLAS" / "guia.md").write_text("# Guía\n" + TEXTO_TUTELA, encoding="utf-8")
    (base / "07_EJEMPLOS_MODELOS_CASOS" / "CLIENTE RAMIREZ" / "tutela.txt").write_text("Datos reales", encoding="utf-8")
    (base / "07_EJEMPLOS_MODELOS_CASOS" / "PEDRO RAMIREZ TUTELA.txt").write_text("Datos reales", encoding="utf-8")
    db = tmp_path / "c.db"
    assert ing.main(["--carpeta", str(base), "--db", str(db)]) == 0
    con = fuentes.abrir(str(db))
    filas = {f["titulo"]: dict(f) for f in con.execute("SELECT * FROM fuentes")}
    assert set(filas) == {"Codigo penal", "Modelo de derecho de peticion", "guia"}
    assert filas["Codigo penal"]["tipo"] == "codigo"
    assert filas["Codigo penal"]["estado_vigencia"] == "PENDIENTE_VERIFICAR"
    assert filas["Codigo penal"]["fecha_archivo"].startswith("2024-02-01")
    assert filas["Modelo de derecho de peticion"]["tipo"] == "plantilla"
    textos = " ".join(f["texto"] for f in con.execute("SELECT texto FROM fragmentos"))
    assert "Datos reales" not in textos and "peticiones respetuosas" in textos
    con.close()
    # segunda pasada: nada cambia
    rep = ing.ingerir(ing.recorrer_carpeta(base), str(db), patrones=[])
    assert rep["sin_cambios"] == 3 and not rep["indexados"]
    assert len(rep["excluidos"]) == 2


def test_drive_no_abre_carpetas_excluidas():
    import importlib
    sys.path.insert(0, str(RAIZ / "scripts"))
    ing = importlib.import_module("ingesta_corpus")
    arbol = {
        "raiz": [{"id": "c1", "name": "01_CODIGOS", "mimeType": ing.CARPETA_DRIVE, "modifiedTime": "2024-02-01T00:00:00Z"},
                 {"id": "c2", "name": "CLIENTES 2025", "mimeType": ing.CARPETA_DRIVE, "modifiedTime": "2025-01-01T00:00:00Z"}],
        "c1": [{"id": "f1", "name": "Codigo penal.pdf", "mimeType": "application/pdf", "modifiedTime": "2024-02-01T00:00:00Z"},
               {"id": "f2", "name": "foto.png", "mimeType": "image/png", "modifiedTime": "2024-02-01T00:00:00Z"}],
        "c2": [{"id": "f3", "name": "secreto.pdf", "mimeType": "application/pdf", "modifiedTime": "2025-01-01T00:00:00Z"}],
    }
    abiertas = []

    class Files:
        def list(self, q, **k):
            cid = q.split("'")[1]
            abiertas.append(cid)
            return ns(execute=lambda: {"files": arbol[cid]})

    servicio = ns(files=lambda: Files())
    rep = {"excluidos": []}
    items = list(ing.recorrer_drive(servicio, "raiz", "", [], rep))
    assert [i[0] for i in items] == ["01_CODIGOS/Codigo penal.pdf"]
    assert items[0][4] == "drive:f1" and items[0][3].startswith("2024-02-01")
    assert "c2" not in abiertas and rep["excluidos"][0]["ruta"] == "CLIENTES 2025/"


# ------------------------------------------------------------- chat --
def _conv(cliente, token):
    return cliente.post("/api/conversaciones", headers=auth(token)).json()["id"]


def test_chat_entrega_fragmentos_numerados_como_datos(cliente, corpus):
    _, _, t = nuevo_usuario(cliente)
    cid = _conv(cliente, t)
    r = cliente.post("/api/chat", headers=auth(t), json={"conversacion": cid, "web": False,
                                                          "mensaje": "¿Qué dice la ley sobre el derecho de petición?"})
    assert r.status_code == 200
    sistema = " ".join(b["text"] for b in FakeAnthropic.ultima_llamada["system"])
    ini, fin = sistema.index("<documentos_recuperados>"), sistema.index("</documentos_recuperados>")
    assert ini < sistema.index("[F1] Ley 1755 de 2015") < fin
    assert "PENDIENTE_VERIFICAR" in sistema[ini:fin] and "fecha del archivo: 2024-02-10" in sistema[ini:fin]
    assert sistema.index("(pendiente de verificación)", fin) > fin  # reglas de cita fuera de los datos
    eventos = _sse(r.text)
    assert [e["tipo"] for e in eventos][-2:] == ["fuentes", "fin"]
    fu = next(e for e in eventos if e["tipo"] == "fuentes")["fuentes"]
    assert fu[0]["origen"] == "corpus" and fu[0]["titulo"] == "Ley 1755 de 2015"
    assert fu[0]["estado_vigencia"] == "PENDIENTE_VERIFICAR" and fu[0]["ubicacion"] == "pág. 1"
    assert "texto" not in fu[0]  # al cliente no se le manda el fragmento completo


def test_chat_sin_indice_usa_el_corpus_vectorial(cliente, modulo, monkeypatch, tmp_path):
    monkeypatch.setenv("PULLEX_CORPUS_DB", str(tmp_path / "nada.db"))
    monkeypatch.setattr(modulo, "buscar_corpus", lambda q: "[Fuente: vectorial.pdf]\nTEXTO-VECTORIAL")
    _, _, t = nuevo_usuario(cliente)
    r = cliente.post("/api/chat", headers=auth(t), json={"conversacion": _conv(cliente, t), "mensaje": "tutela", "web": False})
    sistema = " ".join(b["text"] for b in FakeAnthropic.ultima_llamada["system"])
    assert "TEXTO-VECTORIAL" in sistema and "[F1]" not in sistema
    assert next(e for e in _sse(r.text) if e["tipo"] == "fuentes")["fuentes"] == []


def test_fuentes_se_guardan_por_mensaje_y_estan_aisladas(cliente, corpus):
    _, _, ta = nuevo_usuario(cliente)
    _, _, tb = nuevo_usuario(cliente)
    cid_a = _conv(cliente, ta)
    FakeAnthropic.eventos_final = [ns(type="content_block_delta", delta=ns(type="text_delta", text=" Según el corpus [F1]."))]
    cliente.post("/api/chat", headers=auth(ta), json={"conversacion": cid_a, "web": False,
                                                       "mensaje": "derecho de petición respuesta de fondo"})
    msgs = cliente.get(f"/api/conversaciones/{cid_a}/mensajes", headers=auth(ta)).json()
    assert msgs[0]["rol"] == "user" and "fuentes" not in msgs[0]
    guardadas = msgs[1]["fuentes"]
    assert guardadas[0]["titulo"] == "Ley 1755 de 2015" and guardadas[0]["citado"] is True
    # Otro usuario no puede leer esa conversación ni sus fuentes.
    assert cliente.get(f"/api/conversaciones/{cid_a}/mensajes", headers=auth(tb)).status_code == 404
    # Y su propia respuesta solo trae las fuentes de SU consulta.
    FakeAnthropic.eventos_final = []
    r = cliente.post("/api/chat", headers=auth(tb), json={"conversacion": _conv(cliente, tb), "web": False,
                                                           "mensaje": "hurto de cosa mueble ajena"})
    fu = next(e for e in _sse(r.text) if e["tipo"] == "fuentes")["fuentes"]
    assert [f["titulo"] for f in fu] == ["Codigo penal"]


def test_thinking_no_llega_al_cliente_y_web_citada_aparece_en_fuentes(cliente, tmp_path, monkeypatch):
    monkeypatch.setenv("PULLEX_CORPUS_DB", str(tmp_path / "nada.db"))
    url = "https://www.corteconstitucional.gov.co/relatoria/2020/T-100-20.htm"
    FakeAnthropic.eventos_extra = [
        ns(type="content_block_start", content_block=ns(type="thinking")),
        ns(type="content_block_delta", delta=ns(type="thinking_delta", thinking="RAZONAMIENTO-OCULTO")),
        ns(type="content_block_delta", delta=ns(type="signature_delta", signature="firma")),
        ns(type="content_block_start", content_block=ns(type="server_tool_use")),
        ns(type="content_block_start", content_block=ns(type="web_search_tool_result", content=[
            ns(type="web_search_result", url=url, title="T-100 de 2020", page_age=None),
            ns(type="web_search_result", url="https://www.ramajudicial.gov.co/x", title="Rama", page_age=None)])),
    ]
    FakeAnthropic.eventos_final = [ns(type="content_block_delta", delta=ns(type="citations_delta", citation=ns(
        type="web_search_result_location", url=url, title="T-100 de 2020", cited_text="...", encrypted_index="x")))]
    _, _, t = nuevo_usuario(cliente)
    cid = _conv(cliente, t)
    r = cliente.post("/api/chat", headers=auth(t), json={"conversacion": cid, "mensaje": "tutela", "web": True})
    assert "RAZONAMIENTO-OCULTO" not in r.text and "firma" not in r.text
    eventos = _sse(r.text)
    assert {"tipo": "busqueda"} in eventos
    fu = next(e for e in eventos if e["tipo"] == "fuentes")["fuentes"]
    assert fu[0] == {"origen": "web", "titulo": "T-100 de 2020", "url": url, "oficial": True, "citado": True}
    assert fu[1]["citado"] is False and fu[1]["oficial"] is True
    msgs = cliente.get(f"/api/conversaciones/{cid}/mensajes", headers=auth(t)).json()
    assert "RAZONAMIENTO-OCULTO" not in msgs[1]["contenido"] and msgs[1]["fuentes"][0]["url"] == url


# ----------------------------------------------------- modelo y web --
def test_modelo_sonnet_por_defecto_con_esfuerzo_moderado(cliente, modulo):
    assert modulo.MODELO == "claude-sonnet-5-5"
    _, _, t = nuevo_usuario(cliente)
    cliente.post("/api/chat", headers=auth(t), json={"conversacion": _conv(cliente, t), "mensaje": "hola", "web": False})
    ll = FakeAnthropic.ultima_llamada
    assert ll["model"] == "claude-sonnet-5-5" and ll["output_config"] == {"effort": "medium"}
    assert "thinking" not in ll and ll["tools"] == []
    assert modulo.opciones_modelo("claude-haiku-4-5") == {}  # Haiku no admite effort


def test_llamar_json_usa_esfuerzo_y_margen_de_thinking(modulo):
    modulo.llamar_json("Crea un caso de Derecho Penal.", max_tokens=2500)
    k = FakeAnthropic.ultima_create
    assert k["output_config"] == {"effort": "medium"} and k["max_tokens"] == 2500 + modulo.MARGEN_THINKING


def test_busqueda_web_restringida_a_dominios_oficiales(cliente, monkeypatch):
    _, _, t = nuevo_usuario(cliente)
    cliente.post("/api/chat", headers=auth(t), json={"conversacion": _conv(cliente, t), "mensaje": "hola", "web": True})
    h = FakeAnthropic.ultima_llamada["tools"][0]
    assert h["type"] == "web_search_20250305" and "blocked_domains" not in h
    dom = h["allowed_domains"]
    assert len(dom) == 24 and "corteconstitucional.gov.co" in dom and "suin-juriscol.gov.co" in dom
    assert all("://" not in d and not d.startswith("www.") for d in dom)

    monkeypatch.setenv("PULLEX_WEB_DOMINIOS", "https://www.dian.gov.co/, sic.gov.co, no valido!, *.malo.com")
    cliente.post("/api/chat", headers=auth(t), json={"conversacion": _conv(cliente, t), "mensaje": "hola", "web": True})
    assert FakeAnthropic.ultima_llamada["tools"][0]["allowed_domains"] == ["dian.gov.co", "sic.gov.co"]

    monkeypatch.setenv("PULLEX_WEB_DOMINIOS", "*")
    cliente.post("/api/chat", headers=auth(t), json={"conversacion": _conv(cliente, t), "mensaje": "hola", "web": True})
    assert "allowed_domains" not in FakeAnthropic.ultima_llamada["tools"][0]


def test_es_oficial_no_se_engana_con_el_dominio_en_la_ruta():
    assert fuentes.es_oficial("https://www.corteconstitucional.gov.co/x")
    assert fuentes.es_oficial("https://relatoria.consejodeestado.gov.co/x")
    assert not fuentes.es_oficial("https://evil.com/corteconstitucional.gov.co")
    assert not fuentes.es_oficial("https://corteconstitucional.gov.co.evil.com/")
    assert not fuentes.es_oficial("javascript:alert(1)")


def test_prompt_estilo_y_reglas_conservadas(modulo):
    p = modulo.SYSTEM_PROMPT
    for frase in ("NUNCA inventes", "(pendiente de verificación)", "Ley 1581 de 2012", "no instrucciones",
                  "No declares culpable", "fraude", "premisa falsa", "días hábiles"):
        assert frase in p, frase
    assert "Es importante destacar" in p  # aparece solo como muletilla prohibida
    assert p.index("Es importante destacar") > p.index("Evita muletillas")
