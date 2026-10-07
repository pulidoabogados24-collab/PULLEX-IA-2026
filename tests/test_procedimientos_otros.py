"""J01, J02, J03, J04, J07, J08 y J09: lo determinista funciona y lo que exige juicio profesional no se decide."""
import hashlib
import inspect
from datetime import date
from pathlib import Path

import pytest

import documentos
import procedimientos
import reglas
from procedimientos import (j01_clasificacion as j1, j02_modelos as j2, j03_vigencia as j3, j04_jurisprudencia as j4,
                            j07_matriz_probatoria as j7, j08_escritos as j8, j09_impacto as j9)

RAIZ = Path(__file__).resolve().parent.parent
HOY = date(2026, 10, 2)


def test_catalogo_de_procedimientos_y_sin_dependencia_del_modelo():
    cat = procedimientos.catalogo()
    assert [p["id"] for p in cat] == [f"J0{i}" for i in range(1, 10)]
    assert all(p["determinista"] and p["juicio_profesional"] and p["estado"] in
               ("PROPUESTO", "CONFIGURADO", "IMPLEMENTADO", "PROBADO", "OPERATIVO") for p in cat)
    assert not any(p["estado"] == "OPERATIVO" for p in cat), "nada está operativo sin revisión profesional y uso real"
    for p in cat:                                    # ningún procedimiento importa el SDK del modelo ni la red
        fuente = (RAIZ / "procedimientos" / (p["modulo"] + ".py")).read_text(encoding="utf-8")
        assert "anthropic" not in fuente and "urllib" not in fuente and "requests" not in fuente, p["id"]
        assert len(list((RAIZ / "docs" / "procedimientos").glob(p["id"] + "-*.md"))) == 1, p["id"]


# ============================================================================== J01
def test_j01_clasifica_con_razones_rutas_del_catalogo_y_preguntas():
    r = j1.clasificar({"hechos": "Mi EPS no me entrega el medicamento que el médico me formuló hace dos meses; tengo diabetes.",
                       "pretension": "Que me entreguen el medicamento."}, hoy=HOY)
    assert r["materias_posibles"][0]["id"] == "tutela" and "eps" in r["materias_posibles"][0]["coincidencias"]
    assert {"tutela", "tutela_salud"} <= {x["id"] for x in r["rutas_candidatas"]}
    assert all(x["estado"] == "CANDIDATA" and x["por_verificar"] for x in r["rutas_candidatas"])
    assert {"fechas", "sujetos", "lugar", "documentos"} <= {d["dato"] for d in r["datos_faltantes"]}
    assert any("subsidiariedad" in q for q in r["preguntas_necesarias"])
    assert "R-CONST-0001" in {n["id"] for n in r["normas"]}
    assert any("competencia" in l for l in r["limites"]) and r["propuesta_modelo"] is None
    assert "competente" not in " ".join(x["por_que"] for x in r["rutas_candidatas"]).lower()


def test_j01_todas_las_rutas_existen_en_el_catalogo_real():
    for m in j1.MATERIAS:
        assert m["rutas"] and all(t in documentos.INDICE for t in m["rutas"]), m["id"]
        assert m["area_perfiles"][:3] in {"A06", "A07", "A08", "A09", "A10"}
    assert all(t in documentos.INDICE for t in j1.VERIFICAR_RUTA)


@pytest.mark.parametrize("hechos,materia", [
    ("Me despidieron sin justa causa después de tres años de trabajo y no me pagaron la liquidación ni las cesantías.", "laboral"),
    ("Le presté plata a un amigo, firmó un pagaré y no me paga la deuda desde hace un año.", "civil_obligaciones"),
    ("El padre de mi hija no paga la cuota alimentaria desde enero y quiero la custodia.", "familia"),
    ("Me robaron el celular con amenazas en la calle y quiero poner la denuncia en la fiscalía.", "penal"),
    ("La alcaldía me impuso una multa con una resolución y quiero interponer el recurso de reposición.", "administrativo"),
    ("La DIAN me envió un requerimiento especial por mi declaración de renta del año pasado.", "tributario"),
    ("Colpensiones me negó la pensión aunque tengo las semanas cotizadas completas en mi historia laboral.", "seguridad_social"),
])
def test_j01_materias_por_palabras_completas(hechos, materia):
    r = j1.clasificar({"hechos": hechos}, hoy=HOY)
    assert r["materias_posibles"] and r["materias_posibles"][0]["id"] == materia, r["materias_posibles"]


def test_j01_insuficiente_ambiguo_sin_coincidencias_y_alertas():
    assert j1.clasificar({"hechos": "hola"}, hoy=HOY)["estado"] == "INSUFICIENTE"
    assert j1.clasificar({}, hoy=HOY)["estado"] == "INSUFICIENTE"
    r = j1.clasificar({"hechos": "La primavera llegó temprano este año y las flores del jardín crecieron muchísimo."}, hoy=HOY)
    assert r["estado"] == "SIN_COINCIDENCIAS" and r["rutas_candidatas"] == [], "«primavera» no es «prima»"
    r = j1.clasificar({"hechos": "Radiqué un derecho de petición ante la EPS por un medicamento y no me han respondido."}, hoy=HOY)
    assert r["estado"] in ("AMBIGUO", "CLASIFICADO") and {m["id"] for m in r["materias_posibles"]} >= {"tutela", "peticion"}
    r = j1.clasificar({"hechos": "A mi hermano lo tienen detenido desde ayer en la estación de policía sin orden judicial."}, hoy=HOY)
    assert any("privación de la libertad" in a for a in r["alertas"])


def test_j01_el_apoyo_del_modelo_es_solo_propuesta_y_no_cambia_la_clasificacion():
    entrada = {"hechos": "Me despidieron sin justa causa después de tres años de trabajo en la empresa."}
    base = j1.clasificar(entrada, hoy=HOY)
    con = j1.clasificar(entrada, apoyo_modelo=lambda e, r: {"materias": ["penal"]}, hoy=HOY)
    assert con["materias_posibles"] == base["materias_posibles"] and con["rutas_candidatas"] == base["rutas_candidatas"]
    assert con["propuesta_modelo"]["estado"] == "PROPUESTA_NO_VERIFICADA"
    roto = j1.clasificar(entrada, apoyo_modelo=lambda e, r: 1 / 0, hoy=HOY)
    assert roto["materias_posibles"] == base["materias_posibles"] and roto["propuesta_modelo"]["contenido"] == {"error": "ZeroDivisionError"}
    assert "PROPUESTA" in j1.instruccion_apoyo(entrada, base)


# ============================================================================== J02
def test_j02_candidatos_con_razones_requisitos_y_advertencia_de_similitud():
    r = j2.buscar_modelos("tutela contra EPS por medicamento")
    assert r["estado"] == "CANDIDATOS" and r["candidatos"][0]["id"] == "tutela_salud"
    c = r["candidatos"][0]
    assert c["origen"] == "catalogo_interno" and c["estado_validacion"] == "PLANTILLA_GENERADA_SIN_REVISION_HUMANA"
    assert any("nombre" in x for x in c["razones"]) and c["requisitos"]["datos_obligatorios"] and c["requisitos"]["estructura"]
    assert c["enlace_original"] is None
    assert any("no demuestra" in a for a in r["advertencias"])
    assert any("no está conectada" in a for a in r["advertencias"])
    assert r["proveedores_consultados"] == ["catalogo"]


def test_j02_filtros_sin_modelo_y_abstencion():
    r = j2.buscar_modelos("recurso", {"area": "Tributario"})
    assert r["candidatos"] and all(c["area"] == "Tributario" for c in r["candidatos"])
    r = j2.buscar_modelos("", {"funcionario": True}, limite=30)
    assert r["candidatos"] and all(c["borrador_funcionario"] for c in r["candidatos"])
    nada = j2.buscar_modelos("xilofono cuantico")
    assert nada["estado"] == "SIN_MODELO_ADECUADO" and "borrador nuevo" in nada["advertencias"][0]
    assert j2.buscar_modelos("")["estado"] == "ABSTENCION"
    assert j2.buscar_modelos("tutela", {"area": "Marítimo"})["estado"] == "CONTRADICCION"
    assert j2.buscar_modelos("pagares")["candidatos"][0]["id"] == "pagare", "el plural encuentra el singular"


def test_j02_punto_de_extension_para_la_biblioteca():
    recibido = {}

    def biblioteca(consulta, filtros, usuario):
        recibido.update(consulta=consulta, usuario=usuario)
        return [{"id": "drive:abc", "titulo": "Minuta de tutela (biblioteca)", "puntaje": 99, "razones": ["coincide"],
                 "enlace_original": "https://drive.google.com/file/d/abc"}, {"sin": "titulo"}]
    j2.registrar_proveedor("biblioteca", biblioteca)
    j2.registrar_proveedor("roto", lambda c, f, u: 1 / 0)
    try:
        r = j2.buscar_modelos("tutela salud", usuario="ana@pruebas.local")
        assert r["candidatos"][0]["id"] == "drive:abc" and r["candidatos"][0]["origen"] == "biblioteca"
        assert recibido == {"consulta": "tutela salud", "usuario": "ana@pruebas.local"}, "el proveedor recibe al usuario para aplicar permisos"
        assert {"catalogo", "biblioteca"} <= set(r["proveedores_consultados"])
        assert r["errores_de_proveedores"] == [{"proveedor": "roto", "error": "ZeroDivisionError"}]
        assert not any("no está conectada" in a for a in r["advertencias"])
        assert all(c.get("titulo") for c in r["candidatos"])
    finally:
        j2.quitar_proveedor("biblioteca")
        j2.quitar_proveedor("roto")
    assert j2.proveedores() == ["catalogo"]
    with pytest.raises(TypeError):
        j2.registrar_proveedor("x", "no es función")


# ============================================================================== J03
def test_j03_devuelve_la_regla_aplicable_a_los_hechos_no_la_mas_reciente():
    r = j3.verificar("Ley 1437 de 2011, art. 14", "2019-05-10", "2026-10-02")
    regla = next(x for x in r["reglas"] if x["id"] == "R-PLAZO-0001")
    assert regla["aplicable_a_la_fecha_de_los_hechos"]["version"] == 1
    assert regla["vigente_a_la_fecha_del_analisis"]["version"] == 3 and regla["cambio_entre_las_dos_fechas"] is True
    assert len(regla["versiones_registradas"]) == 3
    assert r["estado"] == "REGLA_APLICABLE_COMPROBADA" and any("no la última" in a for a in r["advertencias"])
    assert "no es automáticamente la aplicable" in r["limite"]


def test_j03_vigencia_pendiente_con_lista_de_que_verificar_y_donde():
    emergencia = j3.verificar("Ley 1437 de 2011 art. 14", "2021-03-01", "2026-10-02")
    assert emergencia["estado"] == j3.PENDIENTE
    v = emergencia["reglas"][0]["aplicable_a_la_fecha_de_los_hechos"]
    assert v["version"] == 2 and v["estado"] == reglas.NO_VERIFICADO and v["motivo"] == "regla_no_verificada"
    sin_inicio = j3.verificar("CGP art. 118", "2019-03-01", "2026-10-02")
    assert sin_inicio["estado"] == j3.PENDIENTE
    assert sin_inicio["reglas"][0]["aplicable_a_la_fecha_de_los_hechos"]["motivo"] == "anterior_sin_inicio"
    desconocida = j3.verificar("Ley 9999 de 2031, art. 3", "2026-01-10", "2026-10-02")
    assert desconocida["estado"] == j3.PENDIENTE and desconocida["reglas"] == []
    for r in (emergencia, sin_inicio, desconocida):
        assert len(r["por_verificar"]) == 5 and len(r["donde_verificar"]) >= 4
        assert all(reglas.es_enlace_oficial(d["enlace"]) or "imprenta.gov.co" in d["enlace"] for d in r["donde_verificar"])
    hoy = j3.verificar("CGP art. 118", "2026-10-02", "2026-10-02")
    assert hoy["estado"] == "REGLA_APLICABLE_COMPROBADA"


def test_j03_abstencion_y_contradiccion():
    assert j3.verificar("", "2026-01-01")["estado"] == "ABSTENCION"
    assert j3.verificar("CGP art. 118", None)["estado"] == "ABSTENCION"
    assert j3.verificar("CGP art. 118", "2026-02-30")["estado"] == "CONTRADICCION"
    assert j3.verificar("CGP art. 118", "2026-05-01", "2026-01-01")["estado"] == "CONTRADICCION"


# ============================================================================== J04
FICHA = {"autoridad": "Corte Constitucional", "tipo_decision": "Sentencia T", "identificador": "T-123 de 2020",
         "fecha": "2020-05-01", "problema_juridico": "p", "fundamento_determinante": "r",
         "diferencias_con_el_caso": "d", "efectos": "Solo para las partes del caso.",
         "enlace": "https://www.corteconstitucional.gov.co/relatoria/2020/T-123-20.htm", "fecha_consulta": "2026-10-02"}


def test_j04_sin_base_de_sentencias_devuelve_ficha_vacia_y_no_inventa():
    r = j4.analizar("¿Procede la tutela contra particulares?")
    assert r["estado"] == "SIN_BASE_DE_SENTENCIAS" and r["precedentes"] == [] and r["base_de_sentencias"] == "NO_CARGADA"
    assert set(r["ficha"]) == {c for c, _ in j4.CAMPOS} and not any(r["ficha"].values())
    assert {c["campo"] for c in r["campos_de_la_ficha"]} >= {"autoridad", "tipo_decision", "identificador", "fecha",
                                                           "problema_juridico", "fundamento_determinante",
                                                           "diferencias_con_el_caso", "efectos"}
    assert len(r["faltantes"]) == 2 and "no propone sentencias de memoria" in r["limite"]
    assert j4.analizar("")["estado"] == "ABSTENCION"
    # El módulo no trae ninguna sentencia escrita: ni números de la Corte Constitucional ni radicados.
    fuente = inspect.getsource(j4)
    assert not j8._sentencias(fuente.replace("T-123", "")), "no hay sentencias en el código de J04"


def test_j04_efectos_solo_con_reglas_verificadas():
    c = j4.efectos_verificados("C", "2026-10-02")
    assert {x["id"] for x in c["afirmables"]} == {"R-JUR-0001", "R-JUR-0002", "R-JUR-0005"} and not c["sin_verificar"]
    t = j4.efectos_verificados("T", "2026-10-02")
    assert [x["id"] for x in t["afirmables"]] == ["R-JUR-0003"]
    su = j4.efectos_verificados("SU", "2026-10-02")
    assert su["afirmables"] == [] and [x["id"] for x in su["sin_verificar"]] == ["R-JUR-0004"]
    assert j4.efectos_verificados(None)["afirmables"] == []
    assert (j4.tipo_de("C-355 de 2006"), j4.tipo_de("SU-637/16"), j4.tipo_de("T 760 de 2008"), j4.tipo_de("SL1234-2020")) == \
        ("C", "SU", "T", None)


def test_j04_no_atribuir_efectos_generales_sin_comprobarlos():
    ok = j4.validar_ficha(FICHA)
    assert ok["estado"] == "COMPLETA_PENDIENTE_DE_REVISION_HUMANA" and ok["tipo_detectado"] == "T"
    assert ok["existencia"] == "ENLACE_OFICIAL_DECLARADO_NO_ABIERTO_POR_EL_SISTEMA"
    general = j4.validar_ficha({**FICHA, "efectos": "Tiene efectos erga omnes y obliga a todos los jueces."})
    assert general["estado"] == "CON_ALERTAS" and "R-JUR-0003" in general["alertas"][0]
    su = j4.validar_ficha({**FICHA, "identificador": "SU-123 de 2020", "tipo_decision": "SU", "efectos": "Vinculante para todos."})
    assert any("R-JUR-0004" in a and "NO_VERIFICADO" in a for a in su["alertas"])
    csj = j4.validar_ficha({**FICHA, "identificador": "SL1234-2020", "tipo_decision": "casación", "efectos": "Efectos generales."})
    assert any("no tiene regla verificada" in a for a in csj["alertas"])
    c_mal = j4.validar_ficha({**FICHA, "identificador": "C-123 de 2020", "tipo_decision": "C", "efectos": "inter partes"})
    assert any("R-JUR-0002" in a for a in c_mal["alertas"])


def test_j04_ficha_incompleta_incoherente_o_sin_fuente_de_la_autoridad():
    assert j4.validar_ficha({})["estado"] == "INCOMPLETA" and len(j4.validar_ficha({})["faltan"]) == len(j4.CAMPOS)
    assert any("año" in a for a in j4.validar_ficha({**FICHA, "fecha": "2019-05-01"})["alertas"])
    assert any("tipo declarado" in a for a in j4.validar_ficha({**FICHA, "tipo_decision": "Sentencia C"})["alertas"])
    blog = j4.validar_ficha({**FICHA, "enlace": "https://blog.ejemplo.com/t-123"})
    assert blog["existencia"] == "NO_VERIFICADA" and any("relatoría" in a for a in blog["alertas"])
    assert any("no existe" in a for a in j4.validar_ficha({**FICHA, "fecha": "2020-02-30"})["alertas"])
    r = j4.analizar("problema", fichas=[FICHA, {**FICHA, "identificador": "T-999 de 2021", "fecha": "2021-01-01",
                                                "fundamento_determinante": "otra razón distinta"}])
    assert r["estado"] == "FICHAS_VALIDADAS" and len(r["precedentes"]) == 2 and r["posibles_lineas_distintas"] == 2


# ============================================================================== J07
MATRIZ = {"hechos": [{"id": "H1", "texto": "Trabajé tres años para la empresa."}, {"id": "H2", "texto": "Me despidieron el 3 de marzo."},
                     {"id": "H3", "texto": "No me pagaron la liquidación."}, {"id": "H4", "texto": "El jefe me insultó."}],
          "elementos": [{"id": "E1", "tipo": "contrato", "descripcion": "Contrato de trabajo", "aportado": True, "hechos": ["H1"]},
                        {"id": "E2", "tipo": "testimonio", "descripcion": "Compañero", "aportado": False, "hechos": ["H2", "H4"]},
                        {"id": "E3", "tipo": "certificado", "descripcion": "Carta de renuncia", "aportado": True, "hechos": ["H2"],
                         "sentido": "contradice"},
                        {"id": "E4", "tipo": "comunicacion", "descripcion": "Correo", "aportado": True, "hechos": ["H3"], "directo": False}],
          "pretensiones": [{"id": "P1", "texto": "Pago de la liquidación", "hechos": ["H1", "H3"]}, {"id": "P2", "texto": "Disculpas"}]}


def test_j07_distingue_afirmacion_indicio_y_acreditado():
    r = j7.construir(MATRIZ)
    niveles = {m["hecho"]: m for m in r["matriz"]}
    assert niveles["H1"]["nivel"] == j7.ACREDITADO and "E1" in niveles["H1"]["razon"]
    assert niveles["H2"]["nivel"] == j7.INDICIO and niveles["H2"]["controvertido"] is True
    assert niveles["H3"]["nivel"] == j7.INDICIO and "indirecta" in niveles["H3"]["razon"]
    assert niveles["H4"]["nivel"] == j7.INDICIO and "no aportados" in niveles["H4"]["razon"]
    assert r["conteo"] == {j7.AFIRMACION: 0, j7.INDICIO: 3, j7.ACREDITADO: 1}
    assert r["contradicciones_probatorias"][0]["hecho"] == "H2" and r["contradicciones_probatorias"][0]["elementos_que_contradicen"] == ["E3"]
    p = {x["id"]: x for x in r["pretensiones"]}
    assert p["P1"]["hechos_sin_acreditar_o_controvertidos"] == ["H3"] and p["P2"]["sin_hechos"] is True
    assert {"pretension": "P2", "vacio": "no se relacionó con ningún hecho"} in r["vacios"]
    assert any("H2" in n and "E2" in n for n in r["necesidades_de_verificacion"])
    assert any("no valora" in l for l in r["limites"])


def test_j07_un_hecho_sin_elementos_es_solo_afirmacion_del_usuario():
    r = j7.construir({"hechos": ["Me amenazaron por teléfono."], "elementos": []})
    assert r["estado"] == "MATRIZ" and r["matriz"][0]["nivel"] == j7.AFIRMACION and r["matriz"][0]["hecho"] == "H1"
    assert r["vacios"] == [{"hecho": "H1", "vacio": "sin respaldo"}]
    # Un documento mencionado pero no aportado NO acredita; un testimonio aportado tampoco.
    for elemento in ({"tipo": "contrato", "aportado": False, "hechos": ["H1"]}, {"tipo": "testimonio", "aportado": True, "hechos": ["H1"]}):
        assert j7.construir({"hechos": ["x y z"], "elementos": [elemento]})["matriz"][0]["nivel"] == j7.INDICIO


def test_j07_abstencion_contradiccion_y_propuestas_del_modelo():
    assert j7.construir({})["estado"] == "ABSTENCION"
    malo = j7.construir({"hechos": [{"id": "H1", "texto": "a"}], "elementos": [
        {"tipo": "contrato", "aportado": True, "hechos": ["H9"]}, {"tipo": "holograma", "aportado": True, "hechos": ["H1"]},
        {"tipo": "contrato", "hechos": ["H1"]}]})
    assert malo["estado"] == "CONTRADICCION" and len(malo["contradicciones"]) == 3
    con = j7.construir({**MATRIZ, "propuestas_modelo": [{"hecho": "H4", "sugerencia": "pedir grabaciones"}]})
    assert con["matriz"] == j7.construir(MATRIZ)["matriz"], "la propuesta del modelo no cambia la matriz"
    assert con["propuestas"][0]["estado"] == "PROPUESTA_NO_VERIFICADA"


# ============================================================================== J08
CAMPOS = {"solicitante": "Ana Pérez", "ciudad": "Bogotá", "contraparte": "EPS Ejemplo", "derechos": "salud",
          "hechos": "El 3 de marzo de 2026 me negaron el medicamento. Mi cédula es 52.123.456.",
          "peticiones": "Que ordene entregarlo.", "urgente": "Sí"}
LIMPIO = ("# ACCIÓN DE TUTELA\n\nSeñor Juez de la República (reparto)\n\nAna Pérez, identificada con C.C. 52.123.456, presenta "
          "acción de tutela contra EPS Ejemplo.\n\n## Hechos\n\n1. El 3 de marzo de 2026 la entidad negó el medicamento.\n\n"
          "## Fundamentos\n\nArt. 86 de la Constitución y Decreto 2591 de 1991.\n\n## Firma\n\nAna Pérez\nC.C. [COMPLETAR: lugar de expedición]\n\n"
          "<<<VERIFICAR>>>\n- Verificar la vigencia del Decreto 2591 de 1991\n- Dirección de notificaciones")
INVENTADO = ("# ACCIÓN DE TUTELA\n\nAna Pérez, C.C. 52.123.456, contra EPS Ejemplo.\n\nEl 3 de marzo de 2026 el doctor Carlos Ramírez "
             "negó el servicio, como consta en el radicado 11001-31-03-001-2020-00123-00 del 15 de abril de 2025. Según la "
             "Sentencia T-760 de 2008, la Ley 1751 de 2015 y el artículo 49 de la Constitución, debe pagar $ 4.500.000. "
             "Contacto: carlos@ejemplo.com, 310 555 1234. NIT 900.123.456. Fecha imposible: 30 de febrero de 2026.")


def test_j08_borrador_sin_invenciones_solo_reporta_pendientes():
    r = j8.verificar_escrito(LIMPIO, CAMPOS, [], "tutela", hoy=HOY)
    assert r["posibles_invenciones"] == [], r["posibles_invenciones"]
    assert r["estado"] == "PENDIENTES" and r["tiene_bloque_verificar"] is True
    assert "Dirección de notificaciones" in r["pendientes"] and any("lugar de expedición" in p for p in r["pendientes"])
    assert "Decreto 2591 de 1991" in r["citas_respaldadas"], "la norma está en las notas del modelo elegido"
    assert r["limites"] and r["juicio_profesional"]


def test_j08_detecta_datos_que_no_estaban_en_las_entradas_ni_en_las_fuentes():
    r = j8.verificar_escrito(INVENTADO, CAMPOS, [], "tutela", hoy=HOY)
    hallados = {(h["categoria"], h["valor"]) for h in r["posibles_invenciones"]}
    assert r["estado"] == "POSIBLES_INVENCIONES"
    for esperado in (("nombre", "Carlos Ramírez"), ("radicado", "11001-31-03-001-2020-00123-00"), ("fecha", "15 de abril de 2025"),
                     ("sentencia", "T-760 de 2008"), ("norma", "Ley 1751 de 2015"), ("articulo", "artículo 49"),
                     ("valor", "$ 4.500.000"), ("contacto", "carlos@ejemplo.com"), ("contacto", "310 555 1234"),
                     ("fecha", "30 de febrero de 2026")):
        assert esperado in hallados, (esperado, hallados)
    assert any(c == "identificacion" and "900.123.456" in v for c, v in hallados)
    # Lo que SÍ estaba en las entradas no se marca.
    valores = {v for _, v in hallados}
    assert not any("Ana Pérez" in v or "52.123.456" in v or v == "3 de marzo de 2026" for v in valores)
    assert all(h["contexto"] and h["confianza"] in ("alta", "media") for h in r["posibles_invenciones"])
    assert r["por_categoria"]["fecha"] == 2 and r["por_categoria"]["contacto"] == 2
    assert any("no existe en el calendario" in h["motivo"] for h in r["posibles_invenciones"])


def test_j08_las_fuentes_respaldan_citas_y_la_fecha_de_hoy_no_es_invencion():
    fuentes = [{"titulo": "Ley Estatutaria de Salud", "texto": "Ley 1751 de 2015, artículo 49 de la Constitución. Sentencia T-760 de 2008."}]
    r = j8.verificar_escrito(INVENTADO + " Bogotá, 2 de octubre de 2026.", CAMPOS, fuentes, "tutela", hoy=HOY)
    categorias = {h["categoria"] for h in r["posibles_invenciones"]}
    assert not categorias & {"sentencia", "norma", "articulo"}
    assert {"T-760 de 2008", "Ley 1751 de 2015"} <= set(r["citas_respaldadas"])
    assert not any(h["valor"] == "2 de octubre de 2026" for h in r["posibles_invenciones"])
    sin_tipo = j8.verificar_escrito(LIMPIO, CAMPOS, [], None, hoy=HOY)
    assert ("norma", "Decreto 2591 de 1991") in {(h["categoria"], h["valor"]) for h in sin_tipo["posibles_invenciones"]}


def test_j08_vacio_recortado_y_sin_entradas():
    assert j8.verificar_escrito("", CAMPOS)["estado"] == "ABSTENCION"
    r = j8.verificar_escrito("Texto sin datos. " * 3, None, None, hoy=HOY)
    assert r["estado"] == "SIN_HALLAZGOS" and len(r["advertencias"]) == 2
    largo = j8.verificar_escrito("palabra " * 20000, CAMPOS, [], hoy=HOY)
    assert any("primeros" in a for a in largo["advertencias"])


def test_j08_preparar_exige_modelo_hechos_confirmados_y_fuentes():
    base = {"tipo": "tutela", "campos": CAMPOS, "hechos_confirmados": True, "fuentes": [], "sin_fuentes": True}
    listo = j8.preparar(base)
    assert listo["estado"] == "LISTO" and listo["anexos_requeridos"] == ["Pruebas y anexos"]
    assert "Acción de tutela" in listo["pedido"] and "Ana Pérez" in listo["datos"]
    assert any("No inventar" in x for x in listo["reglas_de_generacion"]) and any("Sin fuentes" in x for x in listo["reglas_de_generacion"])
    for cambio, falta in (({"tipo": "no_existe"}, "tipo"), ({"hechos_confirmados": "sí"}, "hechos_confirmados"),
                          ({"sin_fuentes": False}, "fuentes"), ({"fuentes": None}, "fuentes"),
                          ({"campos": {"solicitante": "Ana"}}, "campos")):
        r = j8.preparar({**base, **cambio})
        assert r["estado"] == "ABSTENCION" and any(f.startswith(falta) for f in r["faltantes"]), (cambio, r["faltantes"])
    assert j8.revisar_generado(LIMPIO, listo, hoy=HOY)["posibles_invenciones"] == []


# ============================================================================== J09
CAMBIO = {"tipo": "norma", "identificador": "Ley 1755 de 2015", "descripcion": "Cambia el plazo de respuesta",
          "enlace": "http://www.secretariasenado.gov.co/senado/basedoc/ley_1755_2015.html", "fecha_consulta": "2026-10-02",
          "fecha_efecto": "2026-11-01", "comprobado": True}


def _huella(ruta):
    return hashlib.sha256(Path(ruta).read_bytes()).hexdigest()


def test_j09_lista_reglas_documentos_y_perfiles_y_propone_sin_aplicar():
    antes = (_huella(RAIZ / "reglas" / "registro.json"), _huella(RAIZ / "documentos.py"))
    r = j9.impacto(CAMBIO, hoy=HOY)
    assert r["estado"] == "IMPACTO_CALCULADO" and r["aplicado"] is False
    ids = {a["id"] for a in r["reglas_afectadas"]}
    assert {"R-PLAZO-0001", "R-PLAZO-0002", "R-PLAZO-0003", "R-PET-0001"} <= ids
    tipos = {t["id"] for t in r["tipos_de_documento_afectados"]}
    assert {"peticion_general", "peticion_informacion"} <= tipos and all(t in documentos.INDICE for t in tipos)
    perfiles = r["perfiles_afectados"]["identificadores"]
    assert "A10-S06-F04" in perfiles and all(len(p) == 11 and p[-3:] in ("F04", "F08", "F09") for p in perfiles)
    propuestas = [p for p in r["propuesta"] if p["objeto"] == "regla"]
    p1 = next(p for p in propuestas if p["id"] == "R-PLAZO-0001")
    assert p1["version_actual"] == 3 and p1["nueva_version"]["version"] == 4
    assert p1["nueva_version"]["estado"] == reglas.REVISION_PENDIENTE and p1["nueva_version"]["vigencia"]["desde"] == "2026-11-01"
    assert "2026-10-31" in p1["accion"] and "COMPLETAR" in p1["nueva_version"]["enunciado"]
    assert all("No se tocan" in p["documentos_de_usuarios"] for p in r["propuesta"] if p["objeto"] == "tipo_de_documento")
    assert "No se modifica nada en silencio" in r["limite"]
    assert antes == (_huella(RAIZ / "reglas" / "registro.json"), _huella(RAIZ / "documentos.py")), "J09 no escribe nada"
    assert reglas.vigente("R-PLAZO-0001", "2026-11-15")["version"] == 3, "el registro sigue igual tras calcular el impacto"


def test_j09_se_abstiene_si_el_cambio_no_esta_comprobado():
    for cambio, falta in (({"comprobado": False}, "comprobado"), ({"enlace": ""}, "enlace"),
                          ({"enlace": "https://blog.ejemplo.com/ley"}, "enlace oficial"), ({"fecha_efecto": None}, "fecha_efecto"),
                          ({"fecha_consulta": None}, "fecha_consulta"), ({"identificador": ""}, "identificador")):
        r = j9.impacto({**CAMBIO, **cambio}, hoy=HOY)
        assert r["estado"] == "ABSTENCION" and r["propuesta"] == [] and r["reglas_afectadas"] == []
        assert any(f.startswith(falta) for f in r["faltantes"]), (cambio, r["faltantes"])
    assert j9.impacto({**CAMBIO, "fecha_efecto": "2026-02-30"}, hoy=HOY)["estado"] == "CONTRADICCION"
    assert j9.impacto({**CAMBIO, "fecha_consulta": "2027-01-01"}, hoy=HOY)["estado"] == "CONTRADICCION"
    assert j9.impacto({**CAMBIO, "tipo": "rumor"}, hoy=HOY)["estado"] == "CONTRADICCION"


def test_j09_norma_que_no_esta_en_el_registro_y_cambio_por_codigo():
    r = j9.impacto({**CAMBIO, "identificador": "Ley 9999 de 2031"}, hoy=HOY)
    assert r["estado"] == "IMPACTO_CALCULADO" and r["reglas_afectadas"] == []
    assert r["propuesta"] == [{"objeto": "regla", "id": None, "accion": r["propuesta"][0]["accion"]}]
    assert "crearse una regla nueva" in r["propuesta"][0]["accion"]
    cgp = j9.impacto({**CAMBIO, "identificador": "Ley 1564 de 2012", "articulo": "118"}, hoy=HOY)
    assert {"R-TERM-0001", "R-TERM-0002", "R-TERM-0003"} <= {a["id"] for a in cgp["reglas_afectadas"]}
    assert len(cgp["tipos_de_documento_afectados"]) >= 5, "los tipos que nombran el Código General del Proceso"
    nueva = j9.impacto({**CAMBIO, "identificador": "Ley 2578 de 2026",
                        "enlace": "http://www.secretariasenado.gov.co/senado/basedoc/ley_2578_2026.html"}, hoy=HOY)
    assert "R-FEST-0001" in {a["id"] for a in nueva["reglas_afectadas"]}
