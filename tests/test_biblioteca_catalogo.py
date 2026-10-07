"""Catálogo de la biblioteca: indexación de modelos extraídos de Drive, fichas, búsqueda en lenguaje
natural con enlace al original y separación entre lo privado (de terceros) y el chat general.

Los modelos de estas pruebas son ficticios y están escritos para la prueba."""
import json
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "scripts"))
import biblioteca_recorrido as biblioteca  # noqa: E402
import fuentes  # noqa: E402
import indexar_biblioteca as idx  # noqa: E402

PETICION = """MODELO DE DERECHO DE PETICIÓN POR COBRO INDEBIDO DE ACUEDUCTO

Ciudad, (día, mes, año)

Señores
EMPRESA DE ACUEDUCTO DE ________

Yo, __________, identificado con cédula de ciudadanía No. ______, en ejercicio del derecho de petición del artículo 23 de la Constitución Política y de la Ley 1755 de 2015, solicito la revisión de la factura del periodo ______ porque el consumo cobrado no corresponde a la lectura del medidor.

HECHOS

1. ........................

PETICIÓN

Que se revise la factura y se devuelva lo cobrado en exceso.

ANEXOS

Copia de la factura
Copia de la cédula

NOTIFICACIONES

Recibo notificaciones en ________
"""
TUTELA = """MODELO DE ACCIÓN DE TUTELA POR FALTA DE RESPUESTA A UNA PETICIÓN

Señor JUEZ (REPARTO)

__________, mayor de edad, presento acción de tutela contra __________ por la vulneración del derecho fundamental de petición, con fundamento en el Decreto 2591 de 1991 y en la Sentencia T-377 de la Corte Constitucional.

HECHOS

El día ______ radiqué una petición que no ha sido contestada.
"""
LEY = "LEY 9999 DE 2001\n\nARTICULO 1o. Toda petición deberá resolverse dentro de los quince días siguientes a su recepción.\n\nARTICULO 2o. Rige desde su promulgación."
URL = "https://drive.google.com/file/d/{}/view"


@pytest.fixture
def db(tmp_path):
    ruta = str(tmp_path / "corpus.db")
    con = fuentes.abrir(ruta)
    biblioteca.indexar_modelo(con, drive_id="ID-PET", titulo="Modelo peticion cobro indebido acueducto.docx", texto=PETICION,
                              tipo_fuente="plantilla", url=URL.format("ID-PET"), ruta="COLECCION/PETICIONES",
                              tipo_documental="plantilla/minuta", area="derecho de petición", propietario="tercero",
                              fecha_archivo="2026-09-01T00:00:00Z", versiones_relacionadas=["DRV-OTRA"])
    biblioteca.indexar_modelo(con, drive_id="ID-TUT", titulo="Modelo tutela por falta de respuesta.docx", texto=TUTELA,
                              tipo_fuente="plantilla", url=URL.format("ID-TUT"), ruta="COLECCION/TUTELAS",
                              tipo_documental="plantilla/minuta", area="constitucional (tutela)", propietario="tercero")
    biblioteca.indexar_modelo(con, drive_id="ID-LEY", titulo="LEY 9999 DE 2001.doc", texto=LEY, tipo_fuente="ley",
                              url=URL.format("ID-LEY"), ruta="PROPIA/LEYES", tipo_documental="norma",
                              area="general (varias áreas)", propietario="propio")
    con.close()
    return ruta


def test_el_modelo_queda_indexado_con_origen_enlace_y_vigencia_pendiente(db):
    con = fuentes.abrir(db)
    f = con.execute("SELECT * FROM fuentes WHERE origen='ID-PET'").fetchone()
    assert f["tipo"] == "plantilla" and f["url"] == URL.format("ID-PET") and f["estado_vigencia"] == "PENDIENTE_VERIFICAR"
    assert f["verificado_en"] is None and f["sha256"] == biblioteca.huella(PETICION)
    b = con.execute("SELECT * FROM biblioteca_fichas WHERE origen='ID-PET'").fetchone()
    assert b["derechos"] == "derechos de redistribución por confirmar" and b["visibilidad"] == "privada"
    assert b["id_catalogo"] == "DRV-ID-PET" and b["estado_validacion"].startswith("SIN VALIDAR")
    ubic = [x[0] for x in con.execute("SELECT ubicacion FROM fragmentos WHERE fuente_id=? ORDER BY rowid", (f["id"],))]
    assert ubic[0] == "título" and all(u.startswith("párr. ") for u in ubic[1:])     # cada fragmento vuelve a su párrafo
    assert con.execute("SELECT visibilidad FROM biblioteca_fichas WHERE origen='ID-LEY'").fetchone()[0] == "general"
    con.close()


def test_busqueda_en_lenguaje_natural_devuelve_el_modelo_y_el_enlace_al_original(db):
    r = biblioteca.buscar_modelos("me estan cobrando de mas en la factura del acueducto, necesito una peticion", ruta=db)
    assert r[0]["id"] == "DRV-ID-PET" and r[0]["enlace_original"] == URL.format("ID-PET")
    assert r[0]["derechos"] == biblioteca.AVISO_DERECHOS and r[0]["estado_validacion"].startswith("SIN VALIDAR")
    assert r[0]["campos_por_completar"] == 7 and "factura" in r[0]["por_que"] and len(r[0]["vista_previa"]) <= 281
    assert [x["id"] for x in biblioteca.buscar_modelos("tutela porque no contestaron mi peticion", ruta=db)][0] == "DRV-ID-TUT"
    assert biblioteca.buscar_modelos("Modelo tutela falta de respuesta", ruta=db)[0]["ubicacion"] == "título"     # por nombre
    assert biblioteca.buscar_modelos("medida cautelar de embargo y secuestro", ruta=db) == []       # no hay modelo: se dice
    assert biblioteca.buscar_modelos("peticion factura", ruta=str(Path(db).parent / "no-existe.db")) == []
    con_ley = biblioteca.buscar_modelos("plazo quince dias para resolver una peticion", ruta=db, tipos=None)
    assert "DRV-ID-LEY" in [x["id"] for x in con_ley]
    assert "DRV-ID-LEY" not in [x["id"] for x in biblioteca.buscar_modelos("plazo quince dias para resolver una peticion", ruta=db)]


def test_el_chat_general_no_recibe_los_documentos_privados_de_terceros(db):
    pregunta = "peticion por cobro indebido en la factura del acueducto"
    general = fuentes.buscar(pregunta, ruta=db)
    assert all(f["origen"] not in ("ID-PET", "ID-TUT") for f in general)
    assert any(f["origen"] == "ID-PET" for f in fuentes.buscar(pregunta, ruta=db, incluir_privadas=True))
    assert [f["origen"] for f in fuentes.buscar("peticion resolverse quince dias", ruta=db)] == ["ID-LEY"]     # lo propio sí
    for f in fuentes.para_cliente(fuentes.buscar(pregunta, ruta=db, incluir_privadas=True)):
        assert f["url"] is None and "origen" not in f or f["origen"] == "corpus"      # al cliente del chat nunca va el enlace de Drive


def test_ficha_tiene_los_campos_de_la_especificacion_y_no_afirma_lo_que_nadie_reviso(db):
    f = biblioteca.ficha("ID-PET", ruta=db, texto=PETICION)
    for campo in ("id", "titulo", "finalidad", "area", "supuestos_de_uso", "limites", "datos_requeridos", "anexos",
                  "fuentes_citadas", "fecha_de_revision", "enlace_original", "versiones_relacionadas", "estado_validacion"):
        assert campo in f
    assert f["finalidad"].startswith("por describir") and f["fecha_de_revision"] == "nunca revisado"
    assert f["anexos"] == ["Copia de la factura", "Copia de la cédula"]
    assert {c["cita"] for c in f["fuentes_citadas"]} == {"Ley 1755 de 2015", "artículo 23 de la Constitución Política"}
    assert all("NO verificada" in c["estado"] for c in f["fuentes_citadas"])
    assert f["datos_requeridos"]["total"] == 7 and "día, mes, año" in f["datos_requeridos"]["etiquetas"]
    assert f["versiones_relacionadas"] == ["DRV-OTRA"] and f["derechos"] == biblioteca.AVISO_DERECHOS
    assert f["estado_vigencia"] == "PENDIENTE_VERIFICAR" and f["enlace_original"] == URL.format("ID-PET")
    sin_texto = biblioteca.ficha("ID-PET", ruta=db)
    assert sin_texto["datos_requeridos"]["total"] == 7 and sin_texto["fuentes_citadas"] == []
    assert biblioteca.ficha("NO-EXISTE", ruta=db) is None
    assert biblioteca.fuentes_citadas(TUTELA) == ["Decreto 2591 de 1991", "Sentencia T-377"]


def test_reindexar_respeta_la_validacion_humana_si_el_texto_no_cambio(db):
    con = fuentes.abrir(db)
    con.execute("UPDATE biblioteca_fichas SET estado_validacion='VALIDADO por una abogada el 2026-10-01' WHERE origen='ID-PET'")
    fuentes.marcar_estado(con, con.execute("SELECT id FROM fuentes WHERE origen='ID-LEY'").fetchone()[0], "VIGENTE_VERIFICADA")
    kw = dict(titulo="Modelo peticion cobro indebido acueducto.docx", tipo_fuente="plantilla", url=URL.format("ID-PET"))
    assert biblioteca.indexar_modelo(con, drive_id="ID-PET", texto=PETICION, **kw)["accion"] == "sin_cambios"
    assert con.execute("SELECT estado_validacion FROM biblioteca_fichas WHERE origen='ID-PET'").fetchone()[0].startswith("VALIDADO")
    biblioteca.indexar_modelo(con, drive_id="ID-LEY", titulo="LEY 9999 DE 2001.doc", texto=LEY, tipo_fuente="ley",
                              url=URL.format("ID-LEY"), propietario="propio")
    assert con.execute("SELECT estado_vigencia FROM fuentes WHERE origen='ID-LEY'").fetchone()[0] == "VIGENTE_VERIFICADA"
    # si el texto cambia, hay que revisar y verificar otra vez
    r = biblioteca.indexar_modelo(con, drive_id="ID-PET", texto=PETICION + "\nCláusula nueva.", **kw)
    assert r["accion"] == "actualizado"
    assert con.execute("SELECT estado_validacion FROM biblioteca_fichas WHERE origen='ID-PET'").fetchone()[0].startswith("SIN VALIDAR")
    con.close()


def test_titulo_que_dice_derogada_deja_nota_y_no_cambia_la_vigencia(tmp_path):
    ruta = str(tmp_path / "c.db")
    con = fuentes.abrir(ruta)
    biblioteca.indexar_modelo(con, drive_id="ID-D", titulo="LEY 8888 DE 1996- DEROGADA.doc", texto=LEY, tipo_fuente="ley",
                              url=URL.format("ID-D"), propietario="propio")
    con.close()
    f = biblioteca.ficha("ID-D", ruta=ruta)
    assert "DEROGADA" in f["nota_vigencia"] and "sin verificar" in f["nota_vigencia"]
    assert f["estado_vigencia"] == "PENDIENTE_VERIFICAR"


def test_paginas_por_parrafos_dan_un_localizador_a_cada_trozo():
    texto = "\n\n".join(f"Párrafo número {n} con algo de contenido para llenar." for n in range(1, 11))
    pags = biblioteca.paginas_por_parrafos(texto, objetivo=150)
    assert [p[0] for p in pags] == ["párr. 1–2", "párr. 3–4", "párr. 5–6", "párr. 7–8", "párr. 9–10"]
    assert "".join(p[1] for p in pags).count("Párrafo") == 10
    assert [p[0] for p in biblioteca.paginas_por_parrafos("a\n\nb\n\n" + "c" * 200, objetivo=100)] == ["párr. 1–2", "párr. 3"]
    assert biblioteca.paginas_por_parrafos("") == [] and biblioteca.paginas_por_parrafos("uno solo") == [("párr. 1", "uno solo")]


# ------------------------------------------------------ guion de indexación --
@pytest.fixture
def registro(tmp_path):
    textos = tmp_path / "extraidos"
    textos.mkdir()
    def doc(i, texto, apto=True, prop="tercero", tipo="plantilla", **extra):
        (textos / f"{i}.txt").write_text(texto, encoding="utf-8")
        return {"titulo": f"Documento {i}.docx", "ruta": "COLECCION", "enlace": URL.format(i), "propietario": prop,
                "estado": "EXTRAÍDO", "apto_indice": apto, "sha256_texto": biblioteca.huella(texto), "tipo_fuente": tipo,
                "tipo_documental": "plantilla/minuta", "area": "civil", **extra}
    reg = {"documentos": {
        "A": doc("A", PETICION, version_similar_de=[{"id": "B", "similitud": 0.7}]),
        "B": doc("B", TUTELA),
        "C": doc("C", LEY, apto=False, motivo_no_apto="datos personales aparentes"),
        "D": doc("D", LEY, prop="propio", tipo="ley"),
        "E": doc("E", "Yo, Ramiro Quintana Bejarano, identificado con cédula de ciudadanía No. 79.123.456, demando."),
        "F": {**doc("F", TUTELA), "sha256_texto": "0" * 64},
        "G": {"titulo": "Sin texto.docx", "ruta": "COLECCION", "estado": "EXTRAÍDO", "apto_indice": True, "sha256_texto": "x"}}}
    ruta_reg = tmp_path / "extraccion.json"
    ruta_reg.write_text(json.dumps(reg), encoding="utf-8")
    inv = tmp_path / "inventario.json"
    inv.write_text(json.dumps({"elementos": [{"drive_id": "A", "modificado": "2026-08-01T00:00:00Z"}]}), encoding="utf-8")
    args = ["--registro", str(ruta_reg), "--inventario", str(inv), "--textos", str(textos), "--db", str(tmp_path / "corpus.db")]
    return tmp_path, args, ruta_reg


def test_guion_indexa_solo_lo_apto_y_comprueba_antes_de_decir_indexado(registro):
    tmp, args, ruta_reg = registro
    informe = idx.main(args)
    assert sorted(informe["indexados"]) == ["A", "B", "D"] and informe["no_aptos"] == ["C"]
    assert {e["id"]: e["error"].split(":")[0] for e in informe["errores"]} == {
        "E": "datos personales aparentes", "F": "el texto guardado no coincide con la huella del registro",
        "G": "no está el texto extraído (corpus/extraidos)"}
    docs = json.loads(ruta_reg.read_text(encoding="utf-8"))["documentos"]
    assert docs["A"]["estado"] == "INDEXADO" and docs["A"]["indexado"]["fragmentos"] >= 2
    assert docs["A"]["indexado"]["visibilidad"] == "privada" and docs["D"]["indexado"]["visibilidad"] == "general"
    assert docs["A"]["indexado"]["derechos"] == biblioteca.AVISO_DERECHOS and docs["A"]["indexado"]["vigencia"] == "PENDIENTE_VERIFICAR"
    for i in ("C", "E", "F", "G"):
        assert docs[i]["estado"] == "EXTRAÍDO" and "indexado" not in docs[i]
    db = str(tmp / "corpus.db")
    assert biblioteca.ficha("A", ruta=db)["versiones_relacionadas"] == ["DRV-B"]
    assert biblioteca.ficha("A", ruta=db)["fecha_del_archivo"] == "2026-08-01"
    assert biblioteca.ficha("E", ruta=db) is None           # lo que aparenta datos personales no entra
    segunda = idx.main(args)
    assert segunda["indexados"] == [] and sorted(segunda["sin_cambios"]) == ["A", "B", "D"]


def test_guion_retira_del_indice_lo_que_deja_de_ser_apto_y_lista_el_catalogo(registro, capsys):
    tmp, args, ruta_reg = registro
    idx.main(args)
    reg = json.loads(ruta_reg.read_text(encoding="utf-8"))
    reg["documentos"]["B"].update(apto_indice=False, motivo_no_apto="una persona vio datos reales")
    ruta_reg.write_text(json.dumps(reg), encoding="utf-8")
    informe = idx.main(args)
    assert informe["retirados"] == ["B"]
    db = str(tmp / "corpus.db")
    assert biblioteca.ficha("B", ruta=db) is None and biblioteca.buscar_modelos("tutela peticion contestada", ruta=db) == []
    assert json.loads(ruta_reg.read_text(encoding="utf-8"))["documentos"]["B"]["estado"] == "EXTRAÍDO"
    capsys.readouterr()
    filas = idx.main(["--listar", "--db", db])
    salida = capsys.readouterr().out
    assert len(filas) == 2 and URL.format("A") in salida and "derechos de redistribución por confirmar" in salida
