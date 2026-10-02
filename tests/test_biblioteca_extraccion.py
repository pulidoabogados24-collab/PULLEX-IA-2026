"""Extracción de la muestra de Drive: limpieza del texto, calidad, campos por completar, datos
personales aparentes, versiones similares y el registro de extracción.

Todos los documentos de estas pruebas son ficticios y están escritos para la prueba."""
import json
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "scripts"))
import biblioteca  # noqa: E402
import extraer_muestra_drive as ext  # noqa: E402

MODELO = ("MODELO DE DERECHO DE PETICIÓN POR COBRO INDEBIDO\n\nCiudad, (día, mes, año)\n\nSeñores\nEMPRESA DE ACUEDUCTO DE \\_\\_\\_\\_\\_\\_\\_\\_\n\n"
          "Yo, \\_\\_\\_\\_\\_\\_\\_\\_\\_\\_, identificado con cédula de ciudadanía No. \\_\\_\\_\\_\\_\\_, en ejercicio del derecho de petición "
          "del artículo 23 de la Constitución, solicito la revisión de la factura [NÚMERO DE FACTURA] del periodo XXXX.\n\n"
          "HECHOS: ........................\n\nPETICIÓN: (Lo que solicita de manera clara)\n\nNotificaciones: {{correo}}\n\nFirma \\_\\_\\_\\_\\_\\_\\_\\_")
CASO_REAL = ("Yo, Ramiro Quintana Bejarano, identificado con cédula de ciudadanía No. 79.123.456 de Bogotá, celular 310 555 1234, "
             "correo ramiro.q@example.com, presento demanda contra Lucía Fernanda Ospina Rey dentro del radicado "
             "11001-31-03-005-2021-00123-00. " * 3)
LEY = ("LEY 9999 DE 2001\n\nPor la cual se dictan disposiciones de prueba.\n\nEL CONGRESO DE COLOMBIA DECRETA:\n\nARTICULO 1o. "
       "Toda persona podrá presentar peticiones respetuosas.\n\nEl Presidente del honorable Senado de la República,\n\nMARIO PRUEBA FICTICIA.\n\n"
       "La suscrita Jefe Encargada de la Oficina Jurídica hace constar que es fiel copia.\n\nEl Ministro de Justicia y del Derecho,\n\nJuan Ejemplo Inventado.")


# --------------------------------------------------------------- limpieza --
def test_desescapar_quita_barras_y_enlaces_pero_deja_el_texto_visible():
    crudo = ("Empresa de \\_\\_\\_\\_ \\[sede\\]\n\n1\\. Hechos\n\n\\*2. [Lucro cesante](X2.LUCRO-CESANTE\\(a\\).xlsm) y el artículo "
             "[15](http://biblioteca.example.edu/#vid/1/node/15) de la Constitución   \n\n\n\n\nFin")
    limpio = biblioteca.desescapar(crudo)
    assert "Empresa de ____ [sede]" in limpio and "1. Hechos" in limpio
    assert "*2. Lucro cesante y el artículo 15 de la Constitución" in limpio
    assert "http" not in limpio and "xlsm" not in limpio and "\n\n\n" not in limpio


def test_calidad_detecta_pdf_sin_texto_y_caracteres_danados():
    assert biblioteca.calidad_texto("", 500_000, "pdf")["parece_escaneado"] is True
    assert biblioteca.calidad_texto("x" * 300, 900_000, "pdf")["parece_escaneado"] is True      # 0,3 caracteres por KB
    bueno = biblioteca.calidad_texto("palabra " * 2000, 120_000, "pdf")
    assert bueno["parece_escaneado"] is False and bueno["palabras"] == 2000
    assert biblioteca.calidad_texto("", 0, "docx") == {**biblioteca.calidad_texto("", 0, "docx"), "vacio": True, "parece_escaneado": False}
    assert biblioteca.calidad_texto("DA�O EMERGENTE", 100, "doc")["caracteres_danados"] == 1


def test_campos_por_completar_reconoce_los_patrones_de_un_modelo():
    r = biblioteca.campos_por_completar(biblioteca.desescapar(MODELO), con_etiquetas=True)
    assert r["por_patron"] == {"subrayas": 4, "puntos": 1, "equis": 1, "corchetes": 1, "parentesis": 2, "llaves": 1}
    assert r["total"] == 10
    assert "NÚMERO DE FACTURA" in r["etiquetas"] and "día, mes, año" in r["etiquetas"]
    assert "etiquetas" not in biblioteca.campos_por_completar(MODELO)       # por defecto no se devuelven textos
    assert biblioteca.campos_por_completar(LEY)["total"] == 0


# ----------------------------------------------------- datos personales --
def test_un_modelo_en_blanco_y_una_ley_no_aparentan_datos_personales():
    assert biblioteca.datos_personales(biblioteca.desescapar(MODELO))["aparentes"] is False
    ley = biblioteca.datos_personales(LEY)       # firmas de funcionarios y cargos no cuentan
    assert ley["aparentes"] is False and ley["motivo"] is None
    assert biblioteca.datos_personales("SEÑOR\n\nJUEZ (O MAGISTRADO) ......... DE .......... (REPARTO)\n\nC.C. No..............de.......")["aparentes"] is False
    assert biblioteca.datos_personales("acción que se dirige en contra de .......... (entidad o particular)")["aparentes"] is False


def test_un_escrito_con_datos_de_personas_se_marca_y_solo_se_cuenta():
    r = biblioteca.datos_personales(CASO_REAL)
    assert r["aparentes"] is True
    assert r["cedulas"] == 3 and r["celulares"] == 3 and r["correos"] == 3 and r["radicados"] == 3
    assert r["nombres_con_senal"] == 6
    volcado = json.dumps(r, ensure_ascii=False)
    for dato in ("Ramiro", "Quintana", "79.123.456", "310", "example.com", "Ospina", "00123"):
        assert dato not in volcado          # el resultado nunca contiene el dato, solo el conteo
    assert set(biblioteca.nombres_con_senal(CASO_REAL)) == {"Ramiro Quintana Bejarano", "Lucía Fernanda Ospina Rey"}


@pytest.mark.parametrize("texto", [
    "Se resuelve la petición formulada por Abelardo Montes Lizcano, para que se retire su nombre.",
    "el amparo invocado por Abelardo Montes Lizcano contra la Sala",
    "La señora MARÍA DEL PILAR ROZO CANO otorga poder",
    "identificado con C.C. 1.020.345.678",
    "Radicación n.° 11001-02-04-000-2018-00824-01",
])
def test_senales_de_dato_personal(texto):
    assert biblioteca.datos_personales(texto)["aparentes"] is True


# ----------------------------------------------- duplicados y versiones --
def test_duplicado_exacto_y_version_similar():
    a = "El peticionario solicita la revisión de la factura del servicio de acueducto por un cobro que considera indebido " * 4
    b = a.replace("acueducto", "energía")       # una versión con una palabra cambiada
    c = "La acción de tutela procede para la protección inmediata de los derechos fundamentales cuando no hay otro medio " * 4
    v = biblioteca.versiones({"A": a, "B": b, "C": c, "D": a})
    assert v["D"]["duplicado_exacto_de"] == "A" and v["A"]["duplicado_exacto_de"] is None
    assert [x["id"] for x in v["A"]["version_similar_de"]] == ["B"] and v["A"]["version_similar_de"][0]["similitud"] >= 0.5
    assert v["C"] == {"duplicado_exacto_de": None, "version_similar_de": []}
    assert biblioteca.similitud(a, a) == 1.0 and biblioteca.similitud(a, c) == 0.0 and biblioteca.similitud("", a) == 0.0


# ------------------------------------------------ guion de extracción --
def _transcripcion(ruta, lecturas):
    lineas = []
    for n, (fid, salida) in enumerate(lecturas):
        hora = f"2026-03-02T09:00:{n:02d}.000Z"
        lineas.append({"timestamp": hora, "message": {"content": [
            {"type": "tool_use", "id": f"t{n}", "name": "mcp__Google_Drive__read_file_content", "input": {"fileId": fid}}]}})
        lineas.append({"timestamp": hora, "message": {"content": [{"type": "tool_result", "tool_use_id": f"t{n}", "content": salida}]}})
    ruta.write_text("\n".join(json.dumps(x) for x in lineas), encoding="utf-8")
    return ruta


def _resultado(titulo, texto):
    return json.dumps({"fileContent": texto, "title": titulo, "viewUrl": "https://drive.google.com/file/d/x/view"})


@pytest.fixture
def entorno(tmp_path):
    def elem(i, titulo, carpeta, estado="ENCONTRADO", ext="docx", tam=9000, prop="tercero"):
        return {"drive_id": i, "titulo": titulo, "ruta": "COLECCION/" + carpeta, "carpeta_id": "C-" + carpeta, "estado": estado,
                "extension": ext, "tamano": tam, "propietario": prop, "mime": "x", "enlace": f"https://drive.google.com/file/d/{i}/view"}
    inv = {"elementos": [
        elem("D1", "Modelo de peticion por cobro indebido.docx", "PETICIONES"),
        elem("D2", "Demanda de un caso.docx", "MINUTAS"),
        elem("D3", "LEY 9999 DE 2001.doc", "LEYES", ext="doc", prop="propio"),
        elem("D4", "Ley escaneada.pdf", "LEYES", ext="pdf", tam=800_000, prop="propio"),
        elem("D5", "LEY 1 DE 2000.rtf", "LEYES", ext="rtf", prop="propio"),
        elem("D6", "Vacio.docx", "MINUTAS", tam=0),
        elem("D7", "[título reservado]", "MINUTAS", estado="PENDIENTE"),
        elem("D8", "Nota.docx", "MINUTAS")]}
    mapa = {"carpetas": [{"drive_id": "C-PETICIONES", "tipo_documental": "plantilla/minuta", "area": "derecho de petición"},
                         {"drive_id": "C-MINUTAS", "tipo_documental": "plantilla/minuta", "area": "civil"},
                         {"drive_id": "C-LEYES", "tipo_documental": "norma", "area": "general (varias áreas)"}]}
    (tmp_path / "inv.json").write_text(json.dumps(inv), encoding="utf-8")
    (tmp_path / "mapa.json").write_text(json.dumps(mapa), encoding="utf-8")
    t = _transcripcion(tmp_path / "s.jsonl", [
        ("D1", _resultado("Modelo de peticion por cobro indebido.docx", MODELO)
               + "\n\n<system-reminder>\naviso de la sesión que no es parte del documento\n</system-reminder>"),
        ("D2", _resultado("Demanda de un caso.docx", CASO_REAL)),
        ("D3", [{"type": "text", "text": _resultado("LEY 9999 DE 2001.doc", LEY)}]),
        ("D4", _resultado("Ley escaneada.pdf", "pág 1")),
        ("D5", "File content cannot be retrieved for item D5 due to unsupported mime type."),
        ("D6", _resultado("Vacio.docx", "")),
        ("D7", _resultado("escrito reservado.docx", CASO_REAL)),
        ("D8", _resultado("Nota.docx", "DOCUMENTO DISPONIBLE SOLO EN FORMATO PDF.")),
        ("FUERA", _resultado("Otro.docx", MODELO))])
    args = [str(t), "--inventario", str(tmp_path / "inv.json"), "--mapa", str(tmp_path / "mapa.json"),
            "--registro", str(tmp_path / "extraccion.json"), "--destino", str(tmp_path / "extraidos")]
    return tmp_path, args


def test_extraccion_guarda_el_texto_fuera_del_registro_y_decide_que_es_apto(entorno):
    tmp, args = entorno
    docs = ext.main(args)["documentos"]
    assert set(docs) == {"D1", "D2", "D3", "D4", "D5", "D6", "D8"}          # ni el PENDIENTE ni el que está fuera de alcance
    assert sorted(p.name for p in (tmp / "extraidos").iterdir()) == ["D1.txt", "D2.txt", "D3.txt", "D4.txt", "D8.txt"]
    d1 = docs["D1"]
    texto = (tmp / "extraidos" / "D1.txt").read_text(encoding="utf-8")
    assert "aviso de la sesión" not in texto and "\\_" not in texto and "____" in texto
    assert d1["estado"] == "EXTRAÍDO" and d1["apto_indice"] is True and d1["tipo_fuente"] == "plantilla"
    assert d1["sha256_texto"] == biblioteca.huella(texto) and d1["campos_por_completar"]["total"] == 10
    assert d1["calidad"]["caracteres"] == len(texto) and d1["area"] == "derecho de petición"
    assert docs["D2"]["apto_indice"] is False and "datos personales aparentes" in docs["D2"]["motivo_no_apto"]
    assert docs["D3"]["apto_indice"] is True and docs["D3"]["tipo_fuente"] == "ley"
    assert docs["D4"]["apto_indice"] is False and "escaneado" in docs["D4"]["motivo_no_apto"]
    assert docs["D5"]["estado"] == "ENCONTRADO" and "unsupported mime type" in docs["D5"]["error"]
    assert docs["D6"]["estado"] == "LEÍDO" and docs["D6"]["motivo_no_apto"] == "sin texto"
    assert docs["D8"]["apto_indice"] is False and "demasiado corto" in docs["D8"]["motivo_no_apto"]
    registro = (tmp / "extraccion.json").read_text(encoding="utf-8")
    for fragmento in ("Ramiro", "79.123.456", "cobro indebido de", "Toda persona podrá"):
        assert fragmento not in registro          # el registro que va a git no lleva texto ni datos de personas


def test_volver_a_extraer_no_pierde_lo_indexado_si_el_texto_no_cambio(entorno):
    tmp, args = entorno
    ext.main(args)
    reg = json.loads((tmp / "extraccion.json").read_text(encoding="utf-8"))
    reg["documentos"]["D1"].update(estado="INDEXADO", indexado={"fuente_id": 7, "fragmentos": 2})
    (tmp / "extraccion.json").write_text(json.dumps(reg), encoding="utf-8")
    docs = ext.main(args)["documentos"]
    assert docs["D1"]["estado"] == "INDEXADO" and docs["D1"]["indexado"]["fuente_id"] == 7
    assert docs["D3"]["estado"] == "EXTRAÍDO"


def test_tipo_para_el_indice():
    assert ext.tipo_para_el_indice("LEY 1755 DE 2015.doc", "norma") == "ley"
    assert ext.tipo_para_el_indice("Estatuto de Ciencia.docx", "norma") == "otro"
    assert ext.tipo_para_el_indice("Modelo.docx", "plantilla/minuta") == "plantilla"
    assert ext.tipo_para_el_indice("Tabla.xlsx", "tabla de liquidación") == "otro"
