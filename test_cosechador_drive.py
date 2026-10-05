"""Cosechador del inventario de Drive (scripts/cosechar_inventario_drive.py).

Todo con transcripciones de mentira: ids, títulos y cuentas son ficticios. Ninguna prueba llama a Drive."""
import json
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "scripts"))
import cosechar_inventario_drive as cos  # noqa: E402

CARPETA, ATAJO = cos.CARPETA, cos.ATAJO
DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
TERCERO = "coleccion-ajena@example.com"


def archivo(i, titulo, padre, mime=DOCX, tam=1000, owner=cos.PROPIO, visto=True, ext="docx"):
    f = {"id": i, "title": titulo, "parentId": padre, "mimeType": mime, "owner": owner,
         "modifiedTime": "2026-01-01T00:00:00Z", "viewUrl": f"https://drive.google.com/file/d/{i}/view?usp=drivesdk"}
    if mime not in (CARPETA, ATAJO):
        f.update(fileSize=str(tam), fileExtension=ext)
    if visto:
        f["viewedByMeTime"] = "2026-02-01T00:00:00Z"
    return f


def carpeta(i, titulo, padre, owner=cos.PROPIO):
    return archivo(i, titulo, padre, mime=CARPETA, owner=owner)


class Sesion:
    """Escribe una transcripción con el mismo formato que deja una sesión real."""

    def __init__(self, ruta):
        self.ruta, self.n, self.lineas = Path(ruta), 0, []

    def _par(self, nombre, entrada, salida):
        self.n += 1
        uid = f"toolu_{self.ruta.stem}_{self.n}"
        hora = f"2026-03-01T10:{self.n // 60:02d}:{self.n % 60:02d}.000Z"
        self.lineas.append({"timestamp": hora, "message": {"content": [
            {"type": "tool_use", "id": uid, "name": "mcp__Google_Drive__" + nombre, "input": entrada}]}})
        self.lineas.append({"timestamp": hora, "message": {"content": [
            {"type": "tool_result", "tool_use_id": uid, "content": salida}]}})
        self.ruta.write_text("\n".join(json.dumps(x) for x in self.lineas), encoding="utf-8")
        return self

    def listar(self, consulta, archivos, token_usado=None, siguiente=None, guardar_en=None):
        r = {"files": archivos}
        if siguiente:
            r["nextPageToken"] = siguiente
        ent = {"query": consulta, **({"pageToken": token_usado} if token_usado else {})}
        if guardar_en:      # resultado demasiado grande: la sesión lo guarda en disco
            Path(guardar_en).write_text(json.dumps(r), encoding="utf-8")
            return self._par("search_files", ent, f"Error: result exceeds maximum allowed tokens. "
                                                 f"Output has been saved to {guardar_en}.\nFormat: JSON")
        return self._par("search_files", ent, json.dumps(r))

    def metadatos(self, f):
        return self._par("get_file_metadata", {"fileId": f["id"]}, [{"type": "text", "text": json.dumps(f)}])


def padre(*ids):
    return " or ".join(f"parentId = '{i}'" for i in ids)


@pytest.fixture
def sesion(tmp_path):
    return Sesion(tmp_path / "a.jsonl")


# ------------------------------------------------------------ paginación y cola --
def test_listado_en_dos_paginas_queda_completo_y_con_ruta(sesion):
    sesion.listar(padre("R"), [carpeta("C1", "PLANTILLAS", "R"), archivo("F1", "Modelo de poder.docx", "R")], siguiente="t1")
    sesion.listar(padre("R"), [archivo("F2", "Modelo de recurso.docx", "R")], token_usado="t1")
    sesion.listar(padre("C1"), [archivo("F3", "Minuta de arrendamiento.docx", "C1")])
    inv = cos.construir([sesion.ruta], ["R"])
    assert inv["pendientes"] == [] and inv["a_medias"] == []
    assert inv["resumen"]["archivos"] == 3 and inv["resumen"]["carpetas"] == 1
    assert inv["resumen"]["denominador"].startswith("COMPLETO")
    f3 = next(e for e in inv["elementos"] if e["drive_id"] == "F3")
    assert f3["ruta"] == "PLANTILLAS" and f3["estado"] == "ENCONTRADO"
    assert f3["enlace"] == "https://drive.google.com/file/d/F3/view"


def test_pagina_a_medias_deja_token_y_carpeta_pendiente(sesion):
    sesion.listar(padre("R"), [carpeta("C1", "MINUTAS", "R")])
    sesion.listar(padre("C1"), [archivo("F1", "Minuta uno.docx", "C1")], siguiente="tok-2")
    inv = cos.construir([sesion.ruta], ["R"])
    assert inv["pendientes"] == ["C1"]
    assert inv["a_medias"] == [{"consulta": padre("C1"), "pageToken": "tok-2", "faltan": ["C1"]}]
    assert inv["resumen"]["denominador"] == "PROVISIONAL"
    assert next(c for c in inv["carpetas"] if c["drive_id"] == "C1")["listado"] == "A_MEDIAS"


def test_reanudar_en_otra_sesion_cierra_lo_que_estaba_a_medias(sesion, tmp_path):
    sesion.listar(padre("R"), [carpeta("C1", "MINUTAS", "R")])
    sesion.listar(padre("C1"), [archivo("F1", "Minuta uno.docx", "C1")], siguiente="tok-2")
    otra = Sesion(tmp_path / "b.jsonl")
    otra.n = 100       # ocurre después
    otra.listar(padre("C1"), [archivo("F2", "Minuta dos.docx", "C1")], token_usado="tok-2")
    inv = cos.construir([otra.ruta, sesion.ruta], ["R"])       # el orden de los archivos no importa
    assert inv["pendientes"] == [] and inv["a_medias"] == []
    assert {e["drive_id"] for e in inv["elementos"]} == {"C1", "F1", "F2"}


def test_listado_de_varias_carpetas_a_la_vez_cierra_todas(sesion):
    sesion.listar(padre("R"), [carpeta("A", "CIVIL", "R"), carpeta("B", "PENAL", "R")])
    sesion.listar(padre("A"), [archivo("F1", "Demanda modelo.docx", "A")], siguiente="viejo")
    sesion.listar(padre("A", "B"), [archivo("F1", "Demanda modelo.docx", "A"), archivo("F2", "Denuncia modelo.docx", "B")])
    inv = cos.construir([sesion.ruta], ["R"])
    assert inv["pendientes"] == [] and inv["a_medias"] == []
    assert inv["resumen"]["carpetas_listadas_completas"] == 3


def test_consulta_de_solo_subcarpetas_explora_pero_no_lista(sesion):
    sesion.listar(padre("R"), [carpeta("A", "CIVIL", "R")])
    sesion.listar(f"mimeType = '{CARPETA}' and ({padre('A')})", [carpeta("A1", "CONTRATOS", "A")])
    inv = cos.construir([sesion.ruta], ["R"])
    assert inv["pendientes"] == ["A", "A1"]      # falta listar archivos
    assert inv["sin_explorar"] == ["A1"]         # de A ya se conocen las subcarpetas


def test_busqueda_por_titulo_no_cuenta_como_listado(sesion):
    sesion.listar("title contains 'minuta'", [archivo("F1", "Minuta suelta.docx", "R")])
    inv = cos.construir([sesion.ruta], ["R"])
    assert inv["pendientes"] == ["R"] and inv["resumen"]["archivos"] == 1


def test_resultado_grande_guardado_en_disco_se_lee(sesion, tmp_path):
    guardado = tmp_path / "resultado-grande.txt"
    sesion.listar(padre("R"), [archivo(f"F{i}", f"Ley {i} de 2001.docx", "R") for i in range(30)], guardar_en=guardado)
    inv = cos.construir([sesion.ruta], ["R"])
    assert inv["resumen"]["archivos"] == 30 and inv["pendientes"] == []


def test_metadatos_de_la_raiz_le_dan_nombre_a_la_ruta(sesion):
    sesion.metadatos(carpeta("R", "BIBLIOTECA PROPIA", None))
    sesion.listar(padre("R"), [archivo("F1", "Modelo de poder.docx", "R")])
    inv = cos.construir([sesion.ruta], ["R"])
    assert next(e for e in inv["elementos"] if e["drive_id"] == "F1")["ruta"] == "BIBLIOTECA PROPIA"


def test_tope_del_conector_marca_la_carpeta_como_truncada(sesion, monkeypatch):
    monkeypatch.setattr(cos, "TOPE_CONECTOR", 4)
    sesion.listar(padre("R"), [archivo(f"F{i}", f"Auto {i}.docx", "R") for i in range(3)], siguiente="t")
    sesion.listar(padre("R"), [archivo(f"F{i}", f"Auto {i}.docx", "R") for i in range(2, 5)], token_usado="t")
    inv = cos.construir([sesion.ruta], ["R"])
    assert inv["truncadas"] == [{"consulta": padre("R"), "padres": ["R"], "unicos": 5}]
    assert inv["carpetas"][0]["listado"] == "TRUNCADO_POR_EL_CONECTOR"
    assert inv["resumen"]["denominador"] == "PROVISIONAL" and inv["pendientes"] == []
    assert inv["paginacion_con_repetidos"][0]["repetidos"] == 1


def test_omision_de_un_listado_que_dijo_estar_completo(sesion):
    sesion.listar("title contains 'ley'", [archivo("F9", "Ley 9 de 1999.docx", "R")])
    sesion.listar(padre("R"), [archivo("F1", "Ley 1 de 1999.docx", "R")])
    inv = cos.construir([sesion.ruta], ["R"])
    assert inv["omisiones_detectadas"] == [{"carpeta_id": "R", "consulta": padre("R"), "omitidos": 1}]
    assert inv["carpetas"][0]["listado"] == "COMPLETO_CON_OMISIONES"


# ---------------------------------------------------- datos personales --
def test_carpeta_con_nombre_de_persona_queda_pendiente_y_reservada(sesion):
    sesion.listar(padre("R"), [carpeta("P", "ANA MARIA PEREZ GOMEZ, DERECHO DE PETICION COBRO 2008", "R"),
                               archivo("F0", "MODELO DE TUTELA.docx", "R")])
    sesion.listar("title contains 'escrito'", [archivo("F1", "escrito final.docx", "P")])
    inv = cos.construir([sesion.ruta], ["R"])
    p = next(e for e in inv["elementos"] if e["drive_id"] == "P")
    f1 = next(e for e in inv["elementos"] if e["drive_id"] == "F1")
    assert p["estado"] == "PENDIENTE" and p["titulo"] == cos.RESERVADO
    assert f1["estado"] == "PENDIENTE" and f1["ruta"] == cos.RESERVADO     # hereda la reserva y no revela el nombre
    assert "P" not in inv["pendientes"]                                    # no entra en la cola de listado
    assert "PEREZ" not in json.dumps(inv, ensure_ascii=False)
    assert inv["resumen"]["por_estado"]["PENDIENTE"] == 1
    assert next(c for c in inv["carpetas"] if c["drive_id"] == "P")["listado"].startswith("NO_SE_LISTA")


@pytest.mark.parametrize("titulo,es_carpeta", [
    ("EXAMENES PREPARATORIOS", True), ("FUNCION PUBLICA", True), ("MATERIAL DE ESTUDIO CONCURSO DIAN", True),
    ("MEDIDAS CAUTELARES - 2026", True), ("TABLAS LIQUIDADORAS - 2026", True), ("ACCIONES DE TUTELA", True),
    ("CONCURSO RAMA JUDICIAL MAGISTRADOS Y JUECES", True), ("Libros Juridicos", True),
    ("TUTELA PARA PROTEGER DERECHO AL BUEN NOMBRE (1).docx", False), ("MODELO DERECHO DE PETICION PARA FOTOMULTAS (1).docx", False),
    ("LEY 336 DE 1996-ESTATUTO GENERAL DE TRANSPORTE.rtf", False), ("SL2734-2022.doc", False),
])
def test_nombres_de_colecciones_y_modelos_no_se_confunden_con_personas(titulo, es_carpeta):
    assert cos.sensibilidad(titulo, es_carpeta) == "SIN_INDICIOS"


@pytest.mark.parametrize("titulo,es_carpeta", [
    ("ANA MARIA PEREZ GOMEZ, DERECHO DE PETICION COBRO 2008", True), ("PEDRO RUIZ SALAS TUTELA.docx", False),
    ("CLIENTES 2024", True), ("Expediente 2023-001.pdf", False), ("CARLOS ANDRES ROJAS", True),
])
def test_nombre_de_persona_o_expediente_se_reserva(titulo, es_carpeta):
    assert cos.sensibilidad(titulo, es_carpeta) == "POSIBLE_DATO_PERSONAL"


# ------------------------------------------- atajos, ciclos, duplicados --
def test_atajo_se_registra_sin_resolver_y_con_candidato_por_nombre(sesion):
    sesion.listar(padre("R"), [carpeta("C1", "MODELOS Y MINUTAS", "R"),
                               archivo("S1", "MODELOS Y MINUTAS", "R", mime=ATAJO)])
    sesion.listar(padre("C1"), [])
    inv = cos.construir([sesion.ruta], ["R"])
    a = inv["atajos"][0]
    assert a["drive_id"] == "S1" and a["resuelto"] is False and a["destino"] is None
    assert a["candidatos_por_nombre"] == ["C1"] and "NO está comprobado" in a["motivo"]
    assert inv["resumen"]["atajos_en_alcance"] == 1 and inv["resumen"]["archivos"] == 0    # un atajo no es un archivo


def test_ciclo_de_carpetas_no_cuelga_el_recorrido(sesion):
    sesion.listar(padre("R"), [carpeta("A", "UNO", "B"), carpeta("B", "DOS", "A"), archivo("F", "Modelo.docx", "A")])
    inv = cos.construir([sesion.ruta], ["R"])
    assert inv["resumen"]["archivos"] == 0        # nada cuelga de la raíz: no está en alcance
    assert "resumen" in inv


def test_duplicados_por_titulo_y_tamano_y_homonimos(sesion):
    sesion.listar(padre("R"), [carpeta("A", "PROPIA", "R"), carpeta("B", "AJENA", "R", owner=TERCERO)])
    sesion.listar(padre("A", "B"), [
        archivo("F1", "Codigo penal.pdf", "A", tam=500), archivo("F2", "Codigo penal (1).pdf", "B", tam=500, owner=TERCERO),
        archivo("F3", "Estatuto tributario.pdf", "A", tam=10), archivo("F4", "ESTATUTO TRIBUTARIO.docx", "A", tam=99),
        archivo("F5", "Otro modelo.docx", "A", tam=500)])
    inv = cos.construir([sesion.ruta], ["R"])
    assert inv["posibles_duplicados"] == [{"grupo": "D0001", "titulo": "codigo penal", "tamano": 500,
                                           "ids": ["F1", "F2"], "propio_y_tercero": True}]
    assert inv["homonimos"] == [{"titulo": "estatuto tributario", "ids": ["F3", "F4"], "tamanos": [10, 99]}]
    assert next(e for e in inv["elementos"] if e["drive_id"] == "F2")["posible_duplicado"] == "D0001"
    assert "posible_duplicado" not in next(e for e in inv["elementos"] if e["drive_id"] == "F5")


# ------------------------------------------ terceros, alcance y estados --
def test_carpeta_de_tercero_se_lista_segun_conector_y_el_denominador_es_provisional(sesion):
    sesion.metadatos(carpeta("R", "COLECCION COMPARTIDA", None, owner=TERCERO))
    sesion.listar(padre("R"), [archivo("F1", "Modelo de poder.docx", "R", owner=TERCERO)])
    inv = cos.construir([sesion.ruta], ["R"])
    assert inv["carpetas"][0]["listado"] == "SEGUN_CONECTOR"
    assert inv["resumen"]["denominador"] == "PROVISIONAL"
    assert inv["resumen"]["denominador_detalle"]["carpetas_de_terceros"].startswith("DESCONOCIDO")
    assert inv["resumen"]["evidencia_limite_terceros"] == {
        "elementos_de_terceros_en_alcance": 1, "con_fecha_de_visto_por_el_usuario": 1, "sin_fecha_de_visto": 0}
    e = inv["elementos"][-1]
    assert e["propietario"] == "tercero" and e["propietario_ref"].startswith("tercero-")
    assert TERCERO not in json.dumps(inv)          # no se guardan correos de terceros


def test_carpeta_fuera_de_las_raices_se_registra_pero_no_entra(sesion):
    sesion.listar(padre("R"), [archivo("F1", "Modelo.docx", "R")])
    sesion.listar("title contains 'contratos'", [carpeta("X", "CONTRATOS VARIOS", "Z"), archivo("FX", "Contrato.docx", "X"),
                                                 carpeta("Y", "CARPETA DE UN DESCONOCIDO", "Z", owner="alguien@example.org")])
    inv = cos.construir([sesion.ruta], ["R"])
    assert [f["drive_id"] for f in inv["fuera_de_alcance"]] == ["X"]
    assert inv["fuera_de_alcance"][0]["archivos_vistos_dentro"] == 1
    assert inv["fuera_de_alcance"][0]["estado"] == "FUERA_DE_ALCANCE"
    assert {e["drive_id"] for e in inv["elementos"]} == {"F1"} and "X" not in inv["pendientes"]


def test_estados_del_registro_de_extraccion_y_conteos_cuadran(sesion):
    sesion.listar(padre("R"), [carpeta("A", "MINUTAS", "R"), archivo("F1", "Modelo uno.docx", "R"),
                               archivo("F2", "Modelo dos.docx", "R"),
                               archivo("F3", "LUIS TORO DIAZ TUTELA.docx", "R"), archivo("F4", "~WRL0001.tmp", "R", ext="tmp", mime="application/octet-stream"),
                               archivo("F5", "LEY 1 DE 2000.rtf", "R", ext="rtf", mime="application/rtf")])
    sesion.listar(padre("A"), [archivo("F6", "Minuta.docx", "A")])
    registro = {"F1": {"estado": "INDEXADO", "sha256_texto": "ab" * 32, "calidad": {"caracteres": 900},
                       "indexado": {"fuente_id": 1, "fragmentos": 1}},
                "F2": {"estado": "EXTRAÍDO", "apto_indice": False, "motivo_no_apto": "datos personales aparentes"},
                "F3": {"estado": "LEÍDO"}}        # un PENDIENTE no avanza aunque el registro diga otra cosa
    inv = cos.construir([sesion.ruta], ["R"], registro)
    r = inv["resumen"]
    assert r["por_estado"] == {"ENCONTRADO": 3, "EXTRAÍDO": 1, "INDEXADO": 1, "VALIDADO": 0, "PENDIENTE": 1}
    assert sum(r["por_estado"].values()) == r["archivos"] == 6
    assert sum(c["archivos"] for c in inv["carpetas"]) == r["archivos"]
    assert sum(sum(c["por_estado"].values()) for c in inv["carpetas"]) == r["archivos"]
    assert r["no_procesables_con_el_conector"] == {"tmp": 1, "rtf": 1}
    f1 = next(e for e in inv["elementos"] if e["drive_id"] == "F1")
    assert f1["sha256_texto"] == "ab" * 32 and f1["indexado"]["fuente_id"] == 1
    assert next(e for e in inv["elementos"] if e["drive_id"] == "F2")["motivo_no_apto"] == "datos personales aparentes"


def test_informe_y_archivo_json(sesion, tmp_path):
    sesion.metadatos(carpeta("R", "BIBLIOTECA PROPIA", None))
    sesion.listar(padre("R"), [archivo("F1", "Modelo de poder.docx", "R"), archivo("S", "Atajo", "R", mime=ATAJO)], siguiente="t")
    inv = cos.construir([sesion.ruta], ["R"])
    md = cos.informe_md(inv)
    for seccion in ("## Archivos por estado", "## Por carpeta", "## Accesos directos", "## Cola de trabajo",
                    "## Posibles duplicados y homónimos", "Denominador: PROVISIONAL"):
        assert seccion in md
    assert "| ENCONTRADO | 1 |" in md and "| VALIDADO | 0 |" in md
    salida = tmp_path / "inventario.json"
    cos.escribir_json(inv, salida)
    assert json.loads(salida.read_text(encoding="utf-8")) == json.loads(json.dumps(inv))


def test_main_escribe_inventario_e_informe(sesion, tmp_path):
    sesion.listar(padre("R"), [archivo("F1", "Modelo de poder.docx", "R")])
    reg = tmp_path / "extraccion.json"
    reg.write_text(json.dumps({"documentos": {"F1": {"estado": "EXTRAÍDO"}}}), encoding="utf-8")
    obs = tmp_path / "observaciones.json"
    obs.write_text(json.dumps({"observaciones": [{"id": "OBS-99", "tema": "Prueba", "estado": "COMPROBADO",
                                                  "comprobado": "un hecho", "consecuencia": "una consecuencia"}]}), encoding="utf-8")
    cos.main([str(sesion.ruta), "--raices", "R", "--extraccion", str(reg), "--salida", str(tmp_path / "inv.json"),
              "--md", str(tmp_path / "INV.md"), "--observaciones", str(obs)])
    assert "### OBS-99 — Prueba" in (tmp_path / "INV.md").read_text(encoding="utf-8")
    inv = json.loads((tmp_path / "inv.json").read_text(encoding="utf-8"))
    assert inv["resumen"]["por_estado"]["EXTRAÍDO"] == 1
    assert "| EXTRAÍDO | 1 |" in (tmp_path / "INV.md").read_text(encoding="utf-8")
