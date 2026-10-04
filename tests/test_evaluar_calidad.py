"""Evaluación determinista de calidad de respuesta (evaluacion/evaluar_calidad.py y calidad_respuesta.jsonl).

No llama al modelo. Las respuestas «buenas» y «malas» de estas pruebas están escritas a mano para ejercitar las
comprobaciones; NO son respuestas reales de PULLEX ni garantizan corrección jurídica (HUMAN REVIEW REQUIRED).
"""
import json
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "evaluacion"))

import evaluar_calidad as ec  # noqa: E402

CASOS = ec.cargar_casos()
POR_ID = {c["id"]: c for c in CASOS}


# ------------------------------------------------------------------------------ el conjunto de casos --
def test_conjunto_bien_formado_y_marcado_sin_revisar():
    assert len(CASOS) >= 36
    assert ec.validar_casos(CASOS) == {}
    assert len({c["id"] for c in CASOS}) == len(CASOS)
    assert all(c["estado_revision"].startswith("SIN_REVISAR_POR_ABOGADO") for c in CASOS)


def test_cubre_areas_perfiles_y_tipos_pedidos():
    assert {c["area"] for c in CASOS} == set(ec.AREAS)
    assert {c["perfil"] for c in CASOS} == set(ec.PERFILES)
    tipos = {c["tipo"] for c in CASOS}
    for t in ("simple", "multi_parte", "caso_largo", "ambigua_respondible", "ambigua_critica", "seguimiento",
              "redaccion", "revision", "riesgo_alucinacion", "premisa_falsa", "reparacion_intencion", "documento",
              "alto_riesgo"):
        assert t in tipos, t
    # los siete casos de prueba históricos de la especificación (punto 155) tienen representante
    assert sum(1 for c in CASOS if c["tipo"] == "multi_parte") >= 4
    assert sum(1 for c in CASOS if c["tipo"] == "riesgo_alucinacion") >= 4
    assert sum(1 for c in CASOS if c["tipo"] == "seguimiento") >= 3


def test_casos_con_hechos_citados_no_exigen_numeros_de_sentencia():
    """El conjunto no obliga a la IA a citar una sentencia concreta: las pistas no deben tener forma de T-123."""
    import re
    for c in CASOS:
        for p in c["partes_obligatorias"]:
            for x in p["pistas"]:
                assert not re.search(r"\b(?:SU|C|T)-\d", x, re.I), (c["id"], x)


def test_validar_caso_detecta_defectos():
    assert ec.validar_caso({"id": "X"})  # le faltan campos
    malo = dict(POR_ID["CR16"])
    malo["partes_obligatorias"] = malo["partes_obligatorias"][:1]
    assert any("preguntas" in p for p in ec.validar_caso(malo))
    sin_contexto = dict(POR_ID["CR05"])
    del sin_contexto["contexto_previo"]
    assert any("contexto_previo" in p for p in ec.validar_caso(sin_contexto))
    revisado = dict(POR_ID["CR01"], estado_revision="REVISADO")
    assert any("SIN_REVISAR" in p for p in ec.validar_caso(revisado))


def _oraculo(caso):
    """Texto hecho solo con la primera alternativa de la primera pista de cada parte."""
    return " ".join(p["pistas"][0].split("|")[0] for p in caso["partes_obligatorias"])


@pytest.mark.parametrize("caso", CASOS, ids=[c["id"] for c in CASOS])
def test_pistas_son_coherentes(caso):
    """Un texto armado con las pistas cubre todas las partes y no cae en un error prohibido; así no hay pistas
    mal escritas ni errores que se contradigan con las partes."""
    texto = _oraculo(caso)
    cov = ec.cobertura_de_partes(texto, caso["partes_obligatorias"])
    assert cov["faltantes"] == [], (caso["id"], cov)
    assert ec.errores_prohibidos(texto, caso["errores_prohibidos"]) == []


@pytest.mark.parametrize("caso", CASOS, ids=[c["id"] for c in CASOS])
def test_repetir_la_pregunta_o_responder_vacio_no_aprueba(caso):
    """Un modelo de mentira que repite la consulta (o no responde) jamás debe aprobar."""
    assert not ec.evaluar_respuesta(caso, caso["consulta"])["aprobado"]
    assert not ec.evaluar_respuesta(caso, "")["aprobado"]


# ---------------------------------------------------------------------------------------- cobertura --
def test_test1_pregunta_con_cuatro_subpreguntas():
    c = POR_ID["CR16"]
    assert ec.contar_preguntas(c["consulta"]) == 4
    buena = ("Probablemente hurto calificado: hubo violencia con un cuchillo para apoderarse de dinero ajeno. "
             "El artículo aplicable está en el título de delitos contra el patrimonio (pendiente de verificación del número "
             "exacto). Hay dolo: quien amenaza con un cuchillo y se lleva la caja actúa con conocimiento y voluntad. "
             "La defensa podría alegar problemas de identificación del autor, la cuantía y el reconocimiento. "
             * 3 + " Por tanto, lo más probable es que se impute hurto calificado.")
    cob = ec.cobertura_de_partes(buena, c["partes_obligatorias"])
    assert cob["cobertura"] == 1.0
    incompleta = "Probablemente hurto calificado, por la violencia con el cuchillo."
    cob2 = ec.cobertura_de_partes(incompleta, c["partes_obligatorias"])
    assert cob2["cobertura"] == 0.25 and len(cob2["faltantes"]) == 3
    r = ec.evaluar_respuesta(c, incompleta)
    assert not r["aprobado"] and any(f["nombre"] == "cobertura_completa" for f in r["fallas"])


def test_cobertura_alternativas_y_sin_tildes():
    partes = [{"parte": "plazo", "pistas": ["diez días|10 días"]}, {"parte": "norma", "pistas": ["artículo 86"]}]
    assert ec.cobertura_de_partes("El juez decide en DIEZ DIAS según el Articulo 86.", partes)["cobertura"] == 1.0
    assert ec.cobertura_de_partes("Tiene 100 días", partes)["cobertura"] == 0.0
    assert ec.cobertura_de_partes("lo que sea", [])["cobertura"] == 1.0


def test_missed_question_rate_en_el_resumen():
    c1, c2 = POR_ID["CR08"], POR_ID["CR16"]
    rep = ec.evaluar_lote([c1, c2], {"CR08": "Se paga en junio y en diciembre.", "CR16": "Hurto."})
    r = rep["resumen"]
    assert r["casos"] == 2 and 0 < r["missed_question_rate"] < 1
    assert rep["sin_respuesta"] == []
    assert ec.evaluar_lote([c1], {})["sin_respuesta"] == ["CR08"]


# ------------------------------------------------------------------------------------ directitud --
def test_test3_pregunta_simple_respuesta_directa_no_ensayo():
    c = POR_ID["CR08"]
    directa = "Se paga en dos pagos: la primera mitad a más tardar el 30 de junio y la segunda a más tardar el 20 de diciembre."
    r = ec.evaluar_respuesta(c, directa)
    assert r["aprobado"], r["fallas"]
    ensayo = ("Es importante destacar que la prima de servicios es una prestación social. " + "Esta prestación tiene una larga historia y muchas características. " * 40)
    assert not ec.evaluar_respuesta(c, ensayo)["aprobado"]  # no cubre junio/diciembre, arranca con relleno y es larga


@pytest.mark.parametrize("apertura", [
    "Claro, con gusto te ayudo. Sí puedes presentarlo.",
    "Entiendo tu preocupación. Sí puedes presentarlo.",
    "Antes de responder, debo explicar qué es el desacato.",
    "A continuación te explico el desacato.",
    "Es importante aclarar que esto no es asesoría jurídica.",
    "Esto no es asesoría legal, pero sí puedes presentarlo.",
    "Gracias por tu consulta. Sí puedes presentarlo.",
])
def test_apertura_con_relleno_no_es_directa(apertura):
    assert not ec.apertura_directa(apertura, "¿Puedo presentar desacato?")["directa"]


def test_apertura_directa_para_si_no():
    ok = ec.apertura_directa("Sí, podrías, pero depende de dos cosas: que la orden esté incumplida y quién responde.", "¿Puedo presentar desacato?")
    assert ok["directa"]
    mal = ec.apertura_directa("La acción de tutela es un mecanismo constitucional consagrado en el artículo 86 de la Carta.", "¿Puedo presentar desacato?")
    assert not mal["directa"] and "sí o no" in mal["motivo"]
    assert ec.apertura_directa("", "¿Puedo?")["directa"] is False


# -------------------------------------------------------------------------------------- truncamiento --
@pytest.mark.parametrize("texto", [
    "Puedes presentar la tutela ante el juez y debes adjuntar las pruebas de la",
    "Los pasos son:\n1. Reunir los documentos\n2. Presentar la solicitud ante la",
    "Primero verifica el plazo.\n\n```python\nprint('x')",
    "Te explico el trámite.\n\n## Siguientes pasos",
    "Estos son los requisitos:",
    "El juez dijo (y esto es importante que lo sepas",
    "",
])
def test_test7_detecta_respuestas_cortadas(texto):
    assert ec.detectar_truncamiento(texto)["truncada"], texto


@pytest.mark.parametrize("texto", [
    "Sí, puedes hacerlo. El siguiente paso es radicar el escrito.",
    "Pasos:\n1. Reúne los documentos\n2. Preséntalos en la oficina\n3. Guarda la constancia",
    "- Alimentos\n- Custodia\n- Visitas",
    "| Figura | Quién lo propone |\n|---|---|\n| Preacuerdo | Fiscal |",
    'El texto dice «hasta cinco días». Fin.',
    "Cierra con una pregunta: ¿quieres que redacte el escrito?",
])
def test_no_marca_como_cortadas_respuestas_completas(texto):
    assert not ec.detectar_truncamiento(texto)["truncada"], texto


def test_motivo_de_parada_manda_sobre_el_texto():
    completo = "Sí, puedes hacerlo. Fin."
    for motivo in ("max_tokens", "length", "model_context_window_exceeded", "incomplete"):
        t = ec.detectar_truncamiento(completo, motivo)
        assert t["truncada"] and motivo in t["senales"][0]
    assert not ec.detectar_truncamiento(completo, "end_turn")["truncada"]


def test_continuacion_sin_duplicar():
    parcial = "Primero presenta el escrito ante el juez que dictó el fallo y adjunta la copia del fallo, la constancia del incumplimiento y tu identificación"
    cont = "adjunta la copia del fallo, la constancia del incumplimiento y tu identificación. Luego espera la decisión."
    n = ec.continuacion_duplicada(parcial, cont)
    assert n >= 6
    assert ec.continuacion_duplicada("una frase cualquiera", "otra distinta por completo") == 0


# ------------------------------------------------------------------------------------ citas sospechosas --
@pytest.mark.parametrize("texto,tipo", [
    ("según la sentencia T-99999 de 2024", "sentencia"),
    ("la Sentencia C-0 de 2010", "sentencia"),
    ("la Sentencia T-100 de 1985 de la Corte Constitucional", "sentencia"),
    ("la sentencia T-760 de 2090", "sentencia"),
    ("el artículo 9999 del Código Penal", "articulo"),
    ("el artículo 400 de la Constitución Política", "articulo"),
    ("el artículo 70 del Decreto 2591 de 1991", "articulo"),
    ("la Ley 599 de 2020", "ley"),
    ("la Ley 1098 de 1999", "ley"),
    ("la Ley 2500 de 2010", "ley"),
    ("el Decreto 100 de 2090", "decreto"),
])
def test_citas_con_formato_imposible_son_graves(texto, tipo):
    h = ec.citas_sospechosas(texto)
    assert any(x["severidad"] == "grave" and x["tipo"] == tipo for x in h), (texto, h)


@pytest.mark.parametrize("texto", [
    "El artículo 86 de la Constitución Política regula la tutela.",
    "Según el Decreto 2591 de 1991, el juez decide en diez días.",
    "La Ley 1755 de 2015 regula el derecho de petición.",
    "La Ley 599 de 2000 es el Código Penal y la Ley 906 de 2004 el procedimiento acusatorio.",
    "La Ley 1564 de 2012 expidió el Código General del Proceso.",
    "El artículo 64 del CST trata la indemnización por despido.",
    "La Sentencia T-760 de 2008 trató el derecho a la salud.",
    "La SU-1184 de 2001 existe y la C-355 de 2006 también.",
])
def test_citas_normales_no_se_marcan_graves(texto):
    assert [x for x in ec.citas_sospechosas(texto) if x["severidad"] == "grave"] == []


def test_citas_avisos_radicado_ponente_y_cita_textual():
    t = ("El radicado 11001-31-05-012-2020-00123-01 es de la Sala Laboral, M.P. Carlos Pérez. "
         "Dijo la Corte: «" + " ".join(["palabra"] * 14) + "».")
    tipos = {x["tipo"] for x in ec.citas_sospechosas(t)}
    assert {"radicado", "ponente", "cita_textual"} <= tipos
    assert all(x["severidad"] == "aviso" for x in ec.citas_sospechosas(t))


def test_sentencia_sin_anio_es_aviso_y_lo_que_dio_el_usuario_no_se_marca():
    h = ec.citas_sospechosas("La T-123 dijo algo.")
    assert h and h[0]["severidad"] == "aviso"
    previa = "La sentencia T-99999 de 2024 que me notificaron, radicado 2025-00456."
    assert ec.citas_sospechosas("Sobre la sentencia T-99999 de 2024 que mencionas.", permitidas=previa) == []


def test_test6_no_inventa_sentencia_inexistente():
    c = POR_ID["CR40"]
    inventa = "La Corte decidió que la tutela era procedente y concedió el amparo. La sentencia T-88888 de 2023 fijó la ratio decidendi."
    r = ec.evaluar_respuesta(c, inventa)
    assert not r["aprobado"]
    nombres = {f["nombre"] for f in r["fallas"]}
    assert {"sin_errores_prohibidos", "citas_sin_formato_imposible", "marca_lo_no_verificado"} <= nombres
    honesta = ("No pude verificar esa sentencia: el número no corresponde a ninguna que yo conozca. "
               "Búscala en la relatoría de la Corte Constitucional; si pegas el texto, la resumo.")
    r2 = ec.evaluar_respuesta(c, honesta)
    assert r2["aprobado"], r2["fallas"]


def test_radicado_o_ponente_inventado_es_critico_donde_se_prohibe():
    c = POR_ID["CR11"]
    t = ("La indemnización moratoria está en el artículo 65 del CST. La sentencia es la del radicado 11001-31-05-012-2020-00123-01, "
         "M.P. Gerardo Botero. No pude verificar más.")
    r = ec.evaluar_respuesta(c, t)
    assert any(f["nombre"] == "sin_radicado_ni_ponente_no_dados" and f["gravedad"] == "critica" for f in r["fallas"])


# -------------------------------------------------------------------------- advertencias y preguntas --
def test_advertencia_no_sustituye_la_respuesta():
    c = POR_ID["CR01"]
    solo = "Consulta con un abogado. Esto no es asesoría jurídica personalizada."
    r = ec.evaluar_respuesta(c, solo)
    assert not r["aprobado"]
    assert any(f["nombre"] == "advertencia_no_sustituye_respuesta" for f in r["fallas"])
    adv = ec.advertencias("Sí puedes. " + "Esto es una explicación larga sobre el desacato. " * 10 + "Consulta con un abogado. Recuerda que esto es orientación general.")
    assert adv["cantidad"] == 2 and not adv["solo_advertencia"]


def test_abogado_no_recibe_advertencia_de_ciudadano():
    c = POR_ID["CR02"]
    t = ec.evaluar_respuesta(c, "El cumplimiento (art. 27) y el desacato (art. 52) son trámites distintos ante el juez de primera instancia. "
                                "Esto es orientación general, no asesoría jurídica personalizada.")
    assert any(f["nombre"] == "sin_advertencia_de_ciudadano_a_abogado" for f in t["fallas"])


def test_test5_ambigua_respondible_no_responde_solo_con_preguntas():
    c = POR_ID["CR03"]
    solo_preguntas = "¿Cuál medicamento es? ¿De qué EPS? ¿Tienes la orden médica? ¿Cuándo te lo negaron? ¿Qué motivo dieron?"
    r = ec.evaluar_respuesta(c, solo_preguntas)
    nombres = {f["nombre"] for f in r["fallas"]}
    assert not r["aprobado"] and "responde_en_vez_de_preguntar" in nombres and "no_pregunta_de_mas" in nombres
    buena = ("Primero pide la entrega por escrito a la EPS, con la orden médica, y exige que te respondan el motivo de la negativa. "
             "Si no la entregan o no responden, procede la tutela, y puedes quejarte ante la Superintendencia de Salud. " * 3 +
             "En resumen, lo recomendable es radicar hoy la solicitud y guardar la constancia. ¿Cuál fue el motivo que te dieron?")
    assert ec.preguntas_en_respuesta(buena)["cantidad"] == 1
    assert ec.evaluar_respuesta(c, buena)["aprobado"]


def test_ambigua_critica_exige_exactamente_una_pregunta():
    c = POR_ID["CR17"]
    ok = ("Una denuncia se presenta ante la Fiscalía, en una URI o ante la Policía, y no necesitas abogado para hacerla. "
          "Cuéntame primero: ¿qué fue lo que pasó?")
    assert ec.evaluar_respuesta(c, ok)["aprobado"]
    sin = "Una denuncia se presenta ante la Fiscalía o la Policía, que te tomarán el relato de lo ocurrido en detalle."
    assert any(f["nombre"] == "hace_la_pregunta_necesaria" for f in ec.evaluar_respuesta(c, sin)["fallas"])
    de_mas = "Una denuncia va ante la Fiscalía. ¿Qué pasó? ¿Cuándo? ¿Dónde? ¿Quién fue?"
    assert any(f["nombre"] == "no_pregunta_de_mas" for f in ec.evaluar_respuesta(c, de_mas)["fallas"])


# ---------------------------------------------------------------------------- seguimientos y reparación --
def test_test_seguimiento_usa_el_caso_y_no_define_en_abstracto():
    c = POR_ID["CR21"]
    generica = ("El dolo es la conciencia y la voluntad de realizar la conducta típica. Se divide en dolo directo, dolo de consecuencias "
                "necesarias y dolo eventual. " * 3)
    r = ec.evaluar_respuesta(c, generica)
    assert any(f["nombre"] == "cobertura_completa" for f in r["fallas"])  # no menciona cuchillo/abdomen/tentativa
    buena = ("Probablemente hay dolo, al menos eventual: el arma (un cuchillo), la zona del cuerpo (el abdomen) y la profundidad de la herida "
             "son indicios de que el procesado aceptó el riesgo de matar. Si se prueba dolo de matar, sería tentativa de homicidio; si solo "
             "quiso lesionar, lesiones personales. " * 2)
    assert ec.cobertura_de_partes(buena, c["partes_obligatorias"])["cobertura"] == 1.0


def test_explicame_mas_no_repite_lo_anterior():
    c = POR_ID["CR34"]
    previo = c["contexto_previo"][1]["texto"]
    repite = (previo + " ") * 8
    r = ec.evaluar_respuesta(c, repite)
    assert any(f["nombre"] == "no_repite_lo_anterior" for f in r["fallas"])
    assert ec.repeticion_de_previo("Algo completamente distinto con ejemplo y base jurídica en la Ley 1755 de 2015.", previo) == 0
    assert ec.repeticion_de_previo("", previo) == 0


def test_reparacion_de_intencion_sin_ensayo_de_disculpas():
    c = POR_ID["CR13"]
    mal = ("Lamento mucho el malentendido, mil disculpas. El salario es la retribución que recibe el trabajador. " * 3)
    r = ec.evaluar_respuesta(c, mal)
    assert any(f["nombre"] == "sin_errores_prohibidos" for f in r["fallas"])
    bien = ("Tienes razón. En principio no: tu jefe no puede descontarte del sueldo sin tu autorización por escrito o un respaldo legal; "
            "que un cliente no pague es riesgo del negocio. Si ya lo hizo, reclama por escrito y acude al inspector del Ministerio del Trabajo.")
    assert ec.cobertura_de_partes(bien, c["partes_obligatorias"])["cobertura"] == 1.0


# -------------------------------------------------------------------------------------- otras formas --
def test_conclusion_heuristica():
    corto = "Sí, puedes."
    assert ec.tiene_conclusion(corto)
    largo_sin = "Texto explicativo sobre la norma y su historia. " * 40
    assert not ec.tiene_conclusion(largo_sin)
    largo_con = largo_sin + "En conclusión, lo recomendable es radicar el escrito esta semana."
    assert ec.tiene_conclusion(largo_con)


def test_marcador_de_verificacion():
    assert ec.marcador_de_verificacion("El plazo es de tres días (pendiente de verificación).")
    assert ec.marcador_de_verificacion("No pude verificar esa sentencia en una fuente oficial.")
    assert ec.marcador_de_verificacion("Debes confirmar la vigencia en SUIN-Juriscol.")
    assert not ec.marcador_de_verificacion("El plazo es de tres días.")


def test_longitud_orientativa_sin_premiar_lo_largo():
    c = POR_ID["CR10"]  # exige al menos 380 palabras
    corta = "Hay contrato realidad por la primacía de la realidad, con subordinación."
    assert any(f["nombre"] == "longitud_minima" for f in ec.evaluar_respuesta(c, corta)["fallas"])
    # un texto largo y vacío no mejora el resultado: el relleno no cubre las partes
    relleno = "Texto sin contenido útil. " * 200
    r = ec.evaluar_respuesta(c, relleno)
    assert not r["aprobado"] and r["cobertura"] == 0.0
    assert ec.longitud("a b c", minimo=5)["corta"] and ec.longitud("a b c", maximo=2)["larga"]


def test_resumen_vacio_y_por_area():
    assert ec.resumir([]) == {"casos": 0}
    rep = ec.evaluar_lote([POR_ID["CR08"], POR_ID["CR39"]], {"CR08": "Se paga en junio y diciembre.", "CR39": "No existe ese artículo; verifica en SUIN-Juriscol."})
    assert set(rep["resumen"]["por_area"]) == {"Laboral", "Transversal"}


def test_cli_validar_y_evaluar(tmp_path, capsys):
    assert ec._cli(["validar"]) == 0
    out = capsys.readouterr().out
    assert "sin revisión de un abogado" in out
    arch = tmp_path / "r.jsonl"
    arch.write_text(json.dumps({"id": "CR08", "respuesta": "Se paga en junio y en diciembre.", "stop_reason": "max_tokens"}, ensure_ascii=False) + "\n",
                    encoding="utf-8")
    salida = tmp_path / "out" / "res.json"
    assert ec._cli(["evaluar", "--respuestas", str(arch), "--salida", str(salida)]) == 0
    datos = json.loads(salida.read_text(encoding="utf-8"))
    assert datos["resumen"]["truncation_rate"] == 1.0
    assert datos["resultados"][0]["truncada"] is True
