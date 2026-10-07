"""Recorrido completo de la biblioteca (sección 14 de la especificación), de punta a punta y con los
guiones reales: listado de Drive → inventario → mapa → extracción → índice → consulta en lenguaje
natural → enlace al original → borrador trazable → comprobación.

Los documentos son ficticios y están escritos para esta prueba (no dependen de textos de terceros).
El borrador se genera con el doble de prueba `biblioteca.modelo_simulado`: NO es un modelo de IA."""
import json
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "scripts"))
import biblioteca_recorrido as biblioteca  # noqa: E402
import cosechar_inventario_drive as cos  # noqa: E402
import extraer_muestra_drive as ext  # noqa: E402
import fuentes  # noqa: E402
import mapa_biblioteca  # noqa: E402
import recorrido_biblioteca as rec  # noqa: E402

PROPIO, AJENO = cos.PROPIO, "coleccion-ajena@example.com"
DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
MODELO = ("MODELO DE DERECHO DE PETICIÓN POR COBRO INDEBIDO DE ACUEDUCTO\n\nCiudad, (día, mes, año)\n\nSeñores\n\n"
          "EMPRESA DE ACUEDUCTO DE \\_\\_\\_\\_\\_\\_\\_\\_\n\nYo, \\_\\_\\_\\_\\_\\_\\_\\_\\_\\_, identificado con cédula de ciudadanía No. \\_\\_\\_\\_\\_\\_, "
          "en ejercicio del derecho de petición del artículo 23 de la Constitución Política y de la Ley 1755 de 2015, solicito "
          "la revisión de la factura del periodo \\_\\_\\_\\_\\_\\_ porque el consumo cobrado no corresponde a la lectura del medidor.\n\n"
          "HECHOS\n\n1\\. ........................\n\nPETICIÓN\n\nQue se revise la factura y se devuelva lo cobrado en exceso.\n\n"
          "ANEXOS\n\nCopia de la factura\n\nNOTIFICACIONES\n\nRecibo notificaciones en \\_\\_\\_\\_\\_\\_\\_\\_")
MINUTA_ARRIENDO = ("MINUTA DE CONTRATO DE ARRENDAMIENTO DE VIVIENDA URBANA\n\nEntre \\_\\_\\_\\_\\_\\_\\_\\_, arrendador, y \\_\\_\\_\\_\\_\\_\\_\\_, arrendatario, "
                   "se celebra contrato de arrendamiento del inmueble ubicado en \\_\\_\\_\\_\\_\\_\\_\\_ por un canon mensual de \\_\\_\\_\\_\\_\\_ pesos, "
                   "con las cláusulas de destinación, término, servicios públicos y restitución del inmueble.")
ESCRITO_CON_DATOS = ("Yo, Ramiro Quintana Bejarano, identificado con cédula de ciudadanía No. 79.123.456, presento derecho de petición "
                     "por el cobro indebido de la factura del acueducto del periodo de marzo, radicado 11001-31-03-005-2021-00123-00. " * 3)
HECHOS = {"nombre": "PERSONA DE PRUEBA UNO", "ciudad": "Ciudad Ficticia", "identificacion": "000.000.001"}
CONSULTA = "me cobraron de más en la factura del acueducto y quiero reclamar con un derecho de petición"


def _archivo(i, titulo, padre, owner=AJENO, mime=DOCX):
    f = {"id": i, "title": titulo, "parentId": padre, "mimeType": mime, "owner": owner, "modifiedTime": "2026-06-01T00:00:00Z",
         "viewedByMeTime": "2026-06-02T00:00:00Z", "viewUrl": f"https://drive.google.com/file/d/{i}/view?usp=drivesdk"}
    if mime == DOCX:
        f.update(fileSize="9000", fileExtension="docx")
    return f


def _sesion(ruta, pasos):
    lineas = []
    for n, (herramienta, entrada, salida) in enumerate(pasos):
        hora = f"2026-06-03T08:00:{n:02d}.000Z"
        lineas.append({"timestamp": hora, "message": {"content": [
            {"type": "tool_use", "id": f"u{n}", "name": "mcp__Google_Drive__" + herramienta, "input": entrada}]}})
        lineas.append({"timestamp": hora, "message": {"content": [{"type": "tool_result", "tool_use_id": f"u{n}", "content": json.dumps(salida)}]}})
    ruta.write_text("\n".join(json.dumps(x) for x in lineas), encoding="utf-8")
    return str(ruta)


@pytest.fixture
def biblio(tmp_path):
    """Una biblioteca de mentira recorrida con los guiones reales."""
    carpeta = lambda i, t, p: _archivo(i, t, p, mime=cos.CARPETA)
    leer = lambda i, titulo, texto: ("read_file_content", {"fileId": i}, {"fileContent": texto, "title": titulo, "viewUrl": "x"})
    sesion = _sesion(tmp_path / "sesion.jsonl", [
        ("get_file_metadata", {"fileId": "RAIZ"}, carpeta("RAIZ", "PACK DE PRUEBA", None)),
        ("search_files", {"query": "parentId = 'RAIZ'"}, {"files": [carpeta("C-PET", "DERECHOS DE PETICION", "RAIZ"),
                                                                     carpeta("C-CIV", "MINUTAS CIVIL", "RAIZ")]}),
        ("search_files", {"query": "parentId = 'C-PET' or parentId = 'C-CIV'"}, {"files": [
            _archivo("DOC-PET", "Modelo de peticion por cobro indebido de acueducto.docx", "C-PET"),
            _archivo("DOC-REAL", "Peticion ya diligenciada.docx", "C-PET"),
            _archivo("DOC-ARR", "Minuta de contrato de arrendamiento.docx", "C-CIV"),
            _archivo("DOC-NOLEIDO", "Minuta de promesa de compraventa.docx", "C-CIV")]}),
        leer("DOC-PET", "Modelo de peticion por cobro indebido de acueducto.docx", MODELO),
        leer("DOC-REAL", "Peticion ya diligenciada.docx", ESCRITO_CON_DATOS),
        leer("DOC-ARR", "Minuta de contrato de arrendamiento.docx", MINUTA_ARRIENDO)])
    b = tmp_path / "biblioteca"
    b.mkdir()
    cos.main([sesion, "--raices", "RAIZ", "--salida", str(b / "inventario.json"), "--md", str(b / "INVENTARIO.md"),
              "--extraccion", str(b / "extraccion.json"), "--observaciones", str(b / "no-hay.json")])
    mapa_biblioteca.main(["--inventario", str(b / "inventario.json"), "--salida", str(b / "mapa.json"), "--correcciones", str(b / "no-hay.json")])
    ext.main([sesion, "--inventario", str(b / "inventario.json"), "--mapa", str(b / "mapa.json"),
              "--registro", str(b / "extraccion.json"), "--destino", str(tmp_path / "extraidos")])
    carga = lambda n: json.loads((b / n).read_text(encoding="utf-8"))
    return {"inv": carga("inventario.json"), "reg": carga("extraccion.json"), "textos": tmp_path / "extraidos",
            "db": str(tmp_path / "corpus.db"), "dir": b, "sesion": sesion, "tmp": tmp_path}


def _recorrer(biblio, drive_id="DOC-PET", consulta=CONSULTA, hechos=HECHOS, **kw):
    return rec.recorrido(biblio["inv"], biblio["reg"], biblio["textos"], biblio["db"], drive_id, consulta, hechos, **kw)


def test_recorrido_completo_de_ocho_pasos(biblio):
    r = _recorrer(biblio)
    assert r["ok"] is True and [p["ok"] for p in r["pasos"]] == [True] * 8
    ev = {p["paso"].split(".")[0]: p["evidencia"] for p in r["pasos"]}
    # 1 localizar · 2 extraer · 3 registrar
    assert ev["1"]["ruta"] == "PACK DE PRUEBA/DERECHOS DE PETICION" and ev["1"]["enlace"] == "https://drive.google.com/file/d/DOC-PET/view"
    texto = (biblio["textos"] / "DOC-PET.txt").read_text(encoding="utf-8")
    assert ev["2"]["sha256"] == biblioteca.huella(texto) and ev["2"]["coincide_con_el_registro"] is True and ev["2"]["campos_por_completar"] == 7
    assert ev["3"] == {"apto_para_el_indice": True, "motivo_no_apto": None, "datos_personales_aparentes": False,
                       "tipo_documental": "plantilla/minuta", "area": "derecho de petición", "propietario": "tercero",
                       "enlace": "https://drive.google.com/file/d/DOC-PET/view"}
    # 4 indexar: origen = id de Drive, vigencia pendiente, derechos por confirmar, privado
    assert ev["4"]["id_catalogo"] == "DRV-DOC-PET" and ev["4"]["vigencia"] == "PENDIENTE_VERIFICAR" and ev["4"]["fragmentos"] >= 2
    assert ev["4"]["derechos"] == "derechos de redistribución por confirmar" and ev["4"]["visibilidad"] == "privada"
    assert ev["4"]["estado_validacion"].startswith("SIN VALIDAR")
    # 5 encontrar desde lenguaje natural · 6 enlace al original
    assert ev["5"]["posicion"] == 1 and "acueducto" in ev["5"]["por_que"]
    assert ev["6"]["enlace"] == ev["1"]["enlace"] and ev["6"]["igual_al_del_inventario"] is True
    assert ev["6"]["visible_en_el_chat_general"] is False          # es de un tercero: no sale en el chat
    # 7 borrador trazable: cita el modelo, declara el generador, usa solo los hechos y lista lo pendiente
    borrador = r["borrador"]
    assert "Modelo usado: DRV-DOC-PET" in borrador and "https://drive.google.com/file/d/DOC-PET/view" in borrador
    assert ev["7"]["generador"] == biblioteca.GENERADOR_SIMULADO and "SIMULADO" in borrador
    assert "Yo, PERSONA DE PRUEBA UNO, identificado con cédula de ciudadanía No. 000.000.001" in borrador
    assert ev["7"]["hechos_usados"] == ["identificacion", "nombre"]
    assert len(ev["7"]["campos_pendientes"]) >= 4 and "[PENDIENTE: " in borrador and "____" not in borrador
    assert ev["7"]["citas_sin_verificar"] == ["Ley 1755 de 2015", "artículo 23 de la Constitución Política"]
    # 8 comprobar: nada inventado
    assert ev["8"]["fallos"] == [] and ev["8"]["datos_no_respaldados"] == 0 and ev["8"]["citas_nuevas"] == 0
    assert "Ramiro" not in borrador and "11001" not in borrador


def test_el_estado_del_inventario_avanza_con_el_recorrido(biblio):
    estados = lambda: {e["drive_id"]: e["estado"] for e in json.loads((biblio["dir"] / "inventario.json").read_text(encoding="utf-8"))["elementos"]}
    assert estados()["DOC-PET"] == "ENCONTRADO"           # el inventario se hizo antes de leer nada
    reconstruir = lambda: cos.main([biblio["sesion"], "--raices", "RAIZ", "--salida", str(biblio["dir"] / "inventario.json"),
                                    "--md", str(biblio["dir"] / "INVENTARIO.md"), "--extraccion", str(biblio["dir"] / "extraccion.json"),
                                    "--observaciones", str(biblio["dir"] / "no-hay.json")])
    reconstruir()
    assert estados() == {"C-CIV": "ENCONTRADO", "C-PET": "ENCONTRADO", "RAIZ": "ENCONTRADO", "DOC-ARR": "EXTRAÍDO", "DOC-PET": "EXTRAÍDO",
                         "DOC-REAL": "EXTRAÍDO", "DOC-NOLEIDO": "ENCONTRADO"}
    import indexar_biblioteca as idx
    idx.main(["--registro", str(biblio["dir"] / "extraccion.json"), "--inventario", str(biblio["dir"] / "inventario.json"),
              "--textos", str(biblio["textos"]), "--db", biblio["db"]])
    reconstruir()
    e = estados()
    assert e["DOC-PET"] == "INDEXADO" and e["DOC-ARR"] == "INDEXADO"
    assert e["DOC-REAL"] == "EXTRAÍDO"                     # con datos personales aparentes no pasa de ahí
    assert e["DOC-NOLEIDO"] == "ENCONTRADO"                # encontrado no es leído
    resumen = json.loads((biblio["dir"] / "inventario.json").read_text(encoding="utf-8"))["resumen"]["por_estado"]
    assert resumen == {"ENCONTRADO": 1, "EXTRAÍDO": 1, "INDEXADO": 2, "VALIDADO": 0}


def test_un_documento_con_datos_personales_no_pasa_del_registro(biblio):
    r = _recorrer(biblio, drive_id="DOC-REAL")
    assert r["ok"] is False and len(r["pasos"]) == 3 and r["pasos"][2]["ok"] is False
    assert r["pasos"][2]["evidencia"]["datos_personales_aparentes"] is True
    assert biblioteca.ficha("DOC-REAL", ruta=biblio["db"]) is None       # nunca llegó al índice
    assert "Ramiro" not in json.dumps(r, ensure_ascii=False)


def test_encontrado_no_es_leido_y_lo_que_no_esta_en_el_inventario_no_se_procesa(biblio):
    sin_leer = _recorrer(biblio, drive_id="DOC-NOLEIDO")
    assert [p["ok"] for p in sin_leer["pasos"]] == [True, False] and sin_leer["ok"] is False
    fuera = _recorrer(biblio, drive_id="NO-EXISTE")
    assert len(fuera["pasos"]) == 1 and fuera["pasos"][0]["evidencia"]["motivo"] == "no está en el inventario"


def test_una_consulta_que_no_corresponde_no_encuentra_el_modelo(biblio):
    r = _recorrer(biblio, consulta="medida cautelar de embargo y secuestro de un vehículo")
    assert r["ok"] is False and len(r["pasos"]) == 5 and r["pasos"][4]["evidencia"]["posicion"] is None
    otro = _recorrer(biblio, drive_id="DOC-ARR", consulta="necesito un contrato de arrendamiento de vivienda", hechos={})
    assert otro["ok"] is True and otro["pasos"][4]["evidencia"]["posicion"] == 1
    assert otro["pasos"][6]["evidencia"]["hechos_usados"] == []           # sin hechos, todo queda pendiente
    assert len(otro["pasos"][6]["evidencia"]["campos_pendientes"]) == 4


def test_un_generador_que_inventa_datos_no_pasa_la_comprobacion(biblio):
    def inventa(instrucciones, modelo, hechos):
        return ("Yo, Aurelio Inventado Falso, identificado con cédula de ciudadanía No. 52.999.888, dentro del radicado "
                "11001-40-03-010-2024-00456-00 y conforme a la Ley 4321 de 2019, solicito la revisión de la factura.")
    r = _recorrer(biblio, generar=inventa, nombre_generador="doble que inventa (prueba negativa)")
    assert r["ok"] is False and r["pasos"][6]["ok"] is True and r["pasos"][7]["ok"] is False
    fallos = " | ".join(r["pasos"][7]["evidencia"]["fallos"])
    assert "posible invención" in fallos and "Ley 4321 de 2019" in fallos
    assert r["pasos"][7]["evidencia"]["datos_no_respaldados"] == 3        # nombre, identificación y radicado

    def deja_huecos(instrucciones, modelo, hechos):
        return modelo                                                    # devuelve el modelo sin tocar
    r2 = _recorrer(biblio, generar=deja_huecos, nombre_generador="doble perezoso")
    pendientes = r2["pasos"][6]["evidencia"]["campos_pendientes"]
    assert r2["ok"] is True and any("sin completar" in p for p in pendientes)      # lo declara, no lo esconde
    assert "doble perezoso" in r2["borrador"]


def test_comprobar_borrador_exige_trazabilidad():
    modelo = {"id": "DRV-X", "titulo": "Modelo", "enlace_original": "https://drive.google.com/file/d/X/view"}
    b = biblioteca.borrador_trazable(modelo, "Señores ________\n\nYo, ________, solicito ________.", {"nombre": "PERSONA DE PRUEBA DOS"})
    assert biblioteca.comprobar_borrador(b, {"nombre": "PERSONA DE PRUEBA DOS"}, "Señores ________")["ok"] is True
    sin_id = {**b, "borrador": b["borrador"].replace("DRV-X", "")}
    assert "no cita el id del modelo" in biblioteca.comprobar_borrador(sin_id, {}, "")["fallos"][0]
    oculta = {**b, "campos_pendientes": [], "borrador": b["borrador"].replace(f"Campos pendientes ({len(b['campos_pendientes'])})", "Campos pendientes (0)")}
    fallos = biblioteca.comprobar_borrador(oculta, {"nombre": "PERSONA DE PRUEBA DOS"}, "")["fallos"]
    assert any("no están en la lista" in f for f in fallos) and any("dice que no hay pendientes" in f for f in fallos)


def test_guion_por_linea_de_comandos(biblio, capsys):
    args = ["--inventario", str(biblio["dir"] / "inventario.json"), "--registro", str(biblio["dir"] / "extraccion.json"),
            "--textos", str(biblio["textos"]), "--db", biblio["db"], "--consulta", CONSULTA]
    assert rec.main(args + ["--id", "DOC-PET"]) == 0
    salida = capsys.readouterr().out
    assert "Recorrido COMPLETO: 8 de 8 pasos comprobados" in salida and "SIMULADO" in salida and "✔ 8. comprobar el resultado" in salida
    assert rec.main(args + ["--id", "DOC-REAL"]) == 1
    assert "Recorrido INCOMPLETO" in capsys.readouterr().out
    assert rec.main(args + ["--id", "DOC-PET", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["ok"] is True
    assert rec.elegir(biblio["reg"]) in ("DOC-ARR", "DOC-PET")
    assert rec.main(["--inventario", str(biblio["tmp"] / "nada.json")]) == 2
