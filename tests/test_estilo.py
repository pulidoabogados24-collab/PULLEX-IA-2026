"""Estilo de redacción (estilo_redaccion.py): voces, detector de rasgos de IA, pulir() y su integración
en el chat, los documentos, las preferencias y la herramienta «Revisar estilo»."""
import json
import random
import re
import time
from pathlib import Path

import pytest

import estilo_redaccion as er
from conftest import FakeAnthropic, _Evento, auth, nuevo_usuario

RAIZ = Path(__file__).resolve().parent.parent
CONJUNTO = [json.loads(l) for l in (RAIZ / "evaluacion" / "estilo.jsonl").read_text(encoding="utf-8").splitlines()
            if l.strip()]


# ------------------------------------------------------------------------------ voces y guías --
def test_voces_contienen_el_metodo_y_las_citas_colombianas():
    for frase in ("problema jurídico", "contraria", "conclusión", "artículo 86 de la Constitución Política",
                  "Sentencia T-760 de 2008", "Prosa continua"):
        assert frase in er.VOZ_ESTUDIANTE, frase
    for frase in ("Voz activa", "numera", "respetuosamente", "en mérito de lo expuesto", "Negrita solo"):
        assert frase in er.VOZ_ABOGADO, frase
    assert "Sí" in er.VOZ_CIUDADANO and "25 palabras" in er.VOZ_CIUDADANO
    assert set(er.CONECTORES) >= {"contraste", "consecuencia", "causa", "concesion"}
    assert er.instruccion_voz("auto") == "" and "ESTUDIANTE" in er.instruccion_voz("estudiante")
    assert er.instruccion_voz("cualquier-cosa") == ""


def test_sin_nombres_de_universidades():
    textos = [er.VOZ_ESTUDIANTE, er.VOZ_ABOGADO, er.VOZ_CIUDADANO, er.GUIA_ESCRITURA,
              (RAIZ / "docs" / "16-ESTILO-HUMANO.md").read_text(encoding="utf-8"),
              (RAIZ / "evaluacion" / "estilo.jsonl").read_text(encoding="utf-8")]
    for t in textos:
        assert not re.search(r"universidad|pontificia|externado|javeriana|rosario|uniandes", t, re.I)


# ----------------------------------------------------------------------------- detector --
def _ids(texto):
    return {r["id"] for r in er.rasgos_ia(texto)}


@pytest.mark.parametrize("texto,rasgo", [
    ("Es importante destacar que la tutela procede.", "importante_destacar"),
    ("Cabe resaltar que el plazo vence mañana.", "cabe_destacar"),
    ("El juez juega un papel fundamental en el proceso.", "papel_fundamental"),
    ("¡Excelente pregunta! La tutela procede contra la EPS cuando niega un servicio.", "apertura_relleno"),
    ("La tutela procede.\n\nEspero que esta información te sea útil.", "cierre_servicial"),
    ("La tutela procede 😊 contra la EPS.", "emoji"),
    ("La conciliación es un requisito previo para demandar en muchos asuntos — salvo excepciones legales.", "guion_largo"),
    ("## Marco Normativo Aplicable\n\nTexto.", "titulo_mayusculas"),
    ("¿La clave? Probar la subordinación.", "pregunta_retorica"),
    ("La norma no solo protege al trabajador, sino también a su familia.", "no_solo_sino"),
    ("Como inteligencia artificial no puedo opinar.", "autoidentificacion"),
])
def test_detecta_cada_rasgo(texto, rasgo):
    assert rasgo in _ids(texto)


def test_no_confunde_usos_juridicos_legitimos():
    texto = ("El ámbito de aplicación de la Ley 1581 de 2012 cubre los datos personales. La tutela protege los "
             "derechos fundamentales; la Corte Constitucional, en la Sentencia T-760 de 2008, ordenó medidas "
             "estructurales. El Sistema de Seguridad Social Integral prevé la reparación integral. —Así lo dijo el "
             "juez—, y la raya pegada al inciso es correcta.\n\n## Código General del Proceso\n\nTexto.")
    assert _ids(texto) == set()


def test_no_lee_citas_textuales_ni_codigo():
    texto = ("El testigo dijo: «Es importante destacar que llegué tarde». La guía cita \"cabe resaltar que\" como "
             "ejemplo de muletilla.\n\n```\n¡Excelente pregunta! 😊\n```")
    assert _ids(texto) == set()


def test_revisar_estructura_y_posiciones():
    texto = "Cabe destacar que la tutela procede. Es importante señalar que el plazo es breve."
    r = er.revisar(texto)
    assert r["parece_ia"] is True and r["puntaje"] >= er.UMBRAL_IA and r["palabras"] > 5
    for x in r["rasgos"]:
        assert {"id", "nombre", "categoria", "explicacion", "sugerencia", "veces", "peso", "ejemplos"} <= set(x)
        for ini, fin in x["posiciones"]:
            assert texto[ini:fin].lower().startswith(("cabe", "es importante"))
    assert er.revisar("La tutela procede contra la EPS.")["rasgos"] == []


def test_detector_es_rapido_con_textos_adversos():
    for malo in ("¿" * 20000, "**a** " * 3000, "a, b y " * 3000, "— " * 9000, "😊" * 15000, "no solo " * 2500):
        t0 = time.perf_counter()
        er.revisar(malo[:20000])
        er.pulir(malo[:20000])
        assert time.perf_counter() - t0 < 2.0, malo[:10]


# ------------------------------------------------------------------------- evaluación --
def test_conjunto_de_evaluacion_balanceado():
    assert len(CONJUNTO) == 20
    assert sum(f["etiqueta"] == "ia" for f in CONJUNTO) == 10
    assert len({f["id"] for f in CONJUNTO}) == 20


def metricas():
    vp = fp = fn = 0
    esperados = encontrados = 0
    for f in CONJUNTO:
        r = er.revisar(f["texto"])
        real, pred = f["etiqueta"] == "ia", r["parece_ia"]
        vp += real and pred
        fp += pred and not real
        fn += real and not pred
        ids = {x["id"] for x in r["rasgos"]}
        esperados += len(f["rasgos_esperados"])
        encontrados += sum(x in ids for x in f["rasgos_esperados"])
    precision = vp / (vp + fp) if vp + fp else 0.0
    exhaustividad = vp / (vp + fn) if vp + fn else 0.0
    return precision, exhaustividad, encontrados / esperados


def test_precision_y_exhaustividad_del_detector():
    precision, exhaustividad, rasgos = metricas()
    print(f"\ndetector de estilo: precisión={precision:.2f} exhaustividad={exhaustividad:.2f} "
          f"rasgos esperados hallados={rasgos:.2f}")
    assert precision >= 0.9 and exhaustividad >= 0.9 and rasgos >= 0.9


# ------------------------------------------------------------------------------- pulir --
def test_pulir_limpia_lo_inequivoco():
    t = ("¡Excelente pregunta! 😊 Cabe destacar que la tutela procede contra la EPS cuando niega un medicamento "
         "formulado — siempre que no exista otro medio eficaz — según el artículo 86 de la Constitución Política.\n\n"
         "Espero que esta información te sea útil. Si tienes más preguntas, no dudes en escribirme.")
    p = er.pulir(t)
    assert p == ("La tutela procede contra la EPS cuando niega un medicamento formulado, siempre que no exista otro "
                 "medio eficaz, según el artículo 86 de la Constitución Política.")
    assert er.revisar(p)["rasgos"] == []


def test_pulir_conserva_marcas_citas_y_lista_de_verificacion():
    t = ("**BORRADOR — PROYECTO PARA REVISIÓN DEL FUNCIONARIO**\n\n# ACCIÓN DE TUTELA — Ana Pérez\n\n"
         "Señor juez [COMPLETAR: ciudad de reparto] ✅. Según el corpus [F1] y [F2], el término es breve "
         "(pendiente de verificación). El testigo dijo «es importante destacar que — sí — llegué» y "
         "\"cabe resaltar que\" es literal. Ver [la relatoría](https://www.corteconstitucional.gov.co/a_b) o "
         "https://www.suin-juriscol.gov.co/x — sin más.\n\n| Concepto | Valor 😊 |\n|---|---|\n| Prima — junio | **10** |\n\n"
         "```\nfuncion() — ¡Claro! 😊\n```\n\n" + er.MARCA_VERIFICAR + "\n- Verificar 😊 vigencia — ya\n- Cédula")
    p = er.pulir(t)
    for intacto in ("**BORRADOR — PROYECTO PARA REVISIÓN DEL FUNCIONARIO**", "# ACCIÓN DE TUTELA — Ana Pérez",
                    "[COMPLETAR: ciudad de reparto]", "[F1]", "[F2]", "(pendiente de verificación)",
                    "«es importante destacar que — sí — llegué»", "\"cabe resaltar que\"",
                    "[la relatoría](https://www.corteconstitucional.gov.co/a_b)", "https://www.suin-juriscol.gov.co/x",
                    "| Prima — junio | **10** |", "```\nfuncion() — ¡Claro! 😊\n```",
                    er.MARCA_VERIFICAR + "\n- Verificar 😊 vigencia — ya\n- Cédula"):
        assert intacto in p, intacto
    assert "✅" not in p and "| Concepto | Valor |" in p


def test_pulir_no_rompe_la_coordinacion():
    t = "Es importante destacar que el contrato era indefinido y que la empresa no invocó causal."
    assert er.pulir(t) == t
    assert er.pulir("Cabe resaltar que el plazo vence el lunes.") == "El plazo vence el lunes."


def test_pulir_conserva_advertencia_final_y_conclusion():
    t = ("La tutela procede.\n\nEn conclusión, debes presentarla pronto.\n\n¡Espero haberte ayudado!\n\n"
         "Esto es orientación general, no asesoría jurídica personalizada; para tu caso concreto consulta a un abogado.")
    p = er.pulir(t)
    assert p == ("La tutela procede.\n\nEn conclusión, debes presentarla pronto.\n\n"
                 "Esto es orientación general, no asesoría jurídica personalizada; para tu caso concreto consulta a un abogado.")


def test_pulir_negritas_solo_si_son_excesivas_y_respeta_rotulos():
    pocas = "**Hechos.** El 3 de marzo la **EPS** negó el servicio."
    assert er.pulir(pocas) == pocas
    muchas = "**Hechos.** La **EPS** negó el **servicio** el **3 de marzo** sin **motivación**."
    assert er.pulir(muchas) == "**Hechos.** La EPS negó el servicio el 3 de marzo sin motivación."


def test_pulir_rayas_en_encabezados_de_escritos_no_se_tocan():
    for t in ("JUZGADO CIVIL MUNICIPAL DE BOGOTÁ — REPARTO", "Referencia: Tutela — Ana Pérez contra EPS",
              "Esto es un inciso —bien escrito— con la raya pegada al texto que es correcta en español."):
        assert er.pulir(t) == t


def test_pulir_casos_borde():
    assert er.pulir("") == "" and er.pulir(None) is None and er.pulir("   ") == "   "
    raro = "Texto con  carácter interno — raro."
    assert er.pulir(raro) == raro
    assert er.pulir("¡Claro!") == "¡Claro!"          # no deja la respuesta vacía
    assert er.pulir("☐ Sí ☐ No") == "☐ Sí ☐ No"      # casillas de formulario
    assert er.pulir("- ✅ Reúne las pruebas\n- 📁 Radica") == "- Reúne las pruebas\n- Radica"
    assert er.pulir("Texto  \ncon salto duro") == "Texto  \ncon salto duro"


def test_pulir_no_cambia_textos_humanos_y_mejora_los_de_ia():
    for f in CONJUNTO:
        p = er.pulir(f["texto"])
        if f["etiqueta"] == "humano":
            assert p == f["texto"], f["id"]
        assert er.pulir(p) == p, f["id"]   # idempotente
    mejoran = [f["id"] for f in CONJUNTO if f["etiqueta"] == "ia"
               and er.revisar(er.pulir(f["texto"]))["puntaje"] < er.revisar(f["texto"])["puntaje"]]
    assert len(mejoran) >= 8, mejoran


_PIEZAS = [
    "La tutela procede contra la EPS.", "¡Excelente pregunta!", "😊", "✅ Requisito cumplido.", "[F1]", "[F3]",
    "(pendiente de verificación)", "[COMPLETAR: cédula]", "«Es importante destacar que el texto es literal»",
    "Cabe destacar que el plazo es breve.", "**negrita**", "**Rótulo.**", "— inciso —", "texto — pausa",
    "## Marco Normativo Aplicable", "# HECHOS", "1. Hecho primero con fecha del 3 de marzo de 2026.",
    "- viñeta corta", "| a | b — c |", "```\ncódigo — 😊 ¡Claro!\n```", "`x — y`",
    "[enlace](https://www.ramajudicial.gov.co/x_(y))", "https://www.secretariasenado.gov.co/a?b=c",
    "Espero que esta información te sea útil.", "Si tienes más preguntas, no dudes en escribirme.",
    "Esto es orientación general, no asesoría jurídica personalizada.", "\n", "\n\n", "  \n",
    "El artículo 86 de la Constitución Política permite la tutela.", "\"cita literal — con raya\"",
]
_PROTEGIDOS = [r"\[F\d+\]", r"\[COMPLETAR: cédula\]", r"\(pendiente de verificación\)",
               r"<<<VERIFICAR>>>[\s\S]*\Z", r"\[enlace\]\(https://www\.ramajudicial\.gov\.co/x_\(y\)\)"]


def test_pulir_fuzz_nunca_rompe_marcas_markdown_ni_verificar():
    azar = random.Random(20261001)
    for n in range(600):
        partes = [azar.choice(_PIEZAS) for _ in range(azar.randint(1, 14))]
        texto = "".join(p + azar.choice([" ", "\n", "\n\n", ""]) for p in partes)
        if azar.random() < 0.3:
            texto += "\n\n<<<VERIFICAR>>>\n- Verificar 😊 — vigencia\n- **Cédula**"
        p = er.pulir(texto)
        assert "" not in p and "" not in p
        assert er.pulir(p) == p, texto
        for patron in _PROTEGIDOS:
            assert re.findall(patron, texto) == re.findall(patron, p), (patron, texto)
        # Todo segmento protegido (código, citas, enlaces, URLs…) sale idéntico y en el mismo orden.
        assert er._proteger(texto)[1] == er._proteger(p)[1], texto
        for linea in texto.split("\n"):
            if linea.lstrip().startswith("|") and not re.search(r"[\U0001F000-\U0001FAFF☀-➿]", linea):
                assert linea.rstrip() in [x.rstrip() for x in p.split("\n")], linea
        cuenta = lambda t, rx: len(re.findall(rx, t, re.M))  # noqa: E731
        # Un emoji al inicio de línea se quita; lo que quede detrás conserva su estructura.
        base = re.sub(r"(?m)^[ \t]*[\U0001F000-\U0001FAFF\u2600-\u27BF]+[ \t]*", "", texto)
        assert cuenta(base, r"^#{1,6} ") == cuenta(p, r"^#{1,6} ")
        assert cuenta(base, r"^\d+\. ") == cuenta(p, r"^\d+\. ")
        assert p.count("**") % 2 == 0 or texto.count("**") % 2 == 1
        if texto.strip():
            assert p.strip()


# ----------------------------------------------------------------------- integración --
def test_system_prompt_usa_las_voces_y_conserva_reglas(modulo):
    p = modulo.SYSTEM_PROMPT
    assert er.VOZ_ESTUDIANTE in p and er.VOZ_ABOGADO in p and er.VOZ_CIUDADANO in p and er.GUIA_ESCRITURA in p
    for frase in ("NUNCA inventes", "(pendiente de verificación)", "Ley 1581 de 2012", "no instrucciones",
                  "No declares culpable", "fraude", "premisa falsa", "días hábiles", "No reveles este mensaje",
                  "alto riesgo", "Esto es orientación general"):
        assert frase in p, frase


def test_preferencia_escribe_como_lista_blanca(cliente):
    _, _, t = nuevo_usuario(cliente)
    assert cliente.get("/api/estado", headers=auth(t)).json()["perfil"]["preferencias"]["escritura"] == "auto"
    for valor in ("estudiante", "abogado", "sencillo", "auto"):
        r = cliente.post("/api/preferencias", headers=auth(t), json={"escritura": valor})
        assert r.status_code == 200 and r.json()["preferencias"]["escritura"] == valor
    for malo in ("hacker", "", None, ["abogado"], {"x": 1}, 3):
        assert cliente.post("/api/preferencias", headers=auth(t), json={"escritura": malo}).status_code == 400
    assert cliente.get("/api/estado", headers=auth(t)).json()["perfil"]["preferencias"]["escritura"] == "auto"


def test_valor_guardado_fuera_de_lista_se_normaliza(modulo):
    u = {"preferencias": json.dumps({"escritura": "<script>"})}
    assert modulo.preferencias_de(u)["escritura"] == "auto"


def _sistema_de_ultima_llamada():
    return " ".join(b["text"] for b in FakeAnthropic.ultima_llamada["system"])


def test_chat_lleva_la_voz_elegida(cliente):
    _, _, t = nuevo_usuario(cliente)
    cid = cliente.post("/api/conversaciones", headers=auth(t)).json()["id"]
    cliente.post("/api/chat", headers=auth(t), json={"conversacion": cid, "mensaje": "hola", "web": False})
    assert "ESCRIBE COMO" not in _sistema_de_ultima_llamada()
    cliente.post("/api/preferencias", headers=auth(t), json={"escritura": "estudiante"})
    cliente.post("/api/chat", headers=auth(t), json={"conversacion": cid, "mensaje": "un caso", "web": False})
    assert er.instruccion_voz("estudiante") in _sistema_de_ultima_llamada()


def _sse(texto):
    return [json.loads(l[6:]) for l in texto.split("\n") if l.startswith("data: ")]


def test_chat_pule_lo_que_guarda_y_avisa_al_cliente(cliente):
    _, _, t = nuevo_usuario(cliente)
    cid = cliente.post("/api/conversaciones", headers=auth(t)).json()["id"]
    FakeAnthropic.eventos_final = [_Evento(" 😊\n\nEspero que esta información te sea útil.")]
    try:
        r = cliente.post("/api/chat", headers=auth(t), json={"conversacion": cid, "mensaje": "hola", "web": False})
    finally:
        FakeAnthropic.eventos_final = []
    ev = _sse(r.text)
    assert [e["tipo"] for e in ev][-3:] == ["pulido", "fuentes", "fin"]
    pulido = next(e for e in ev if e["tipo"] == "pulido")["texto"]
    assert "😊" not in pulido and "Espero" not in pulido and pulido.startswith("ECO:")
    guardado = cliente.get(f"/api/conversaciones/{cid}/mensajes", headers=auth(t)).json()[-1]["contenido"]
    assert guardado == pulido


def test_chat_sin_cambios_no_envia_pulido(cliente):
    _, _, t = nuevo_usuario(cliente)
    cid = cliente.post("/api/conversaciones", headers=auth(t)).json()["id"]
    r = cliente.post("/api/chat", headers=auth(t), json={"conversacion": cid, "mensaje": "hola", "web": False})
    assert "pulido" not in [e["tipo"] for e in _sse(r.text)]


def test_documentos_usan_voz_de_abogado_y_salen_pulidos(modulo, cliente):
    import documentos
    assert er.VOZ_ABOGADO in documentos.SISTEMA_DOCUMENTO and er.VOZ_ABOGADO in documentos.SISTEMA_FLUJO
    assert "PULLEX DOCUMENTOS" in documentos.SISTEMA_DOCUMENTO
    _, _, t = nuevo_usuario(cliente)
    original = FakeAnthropic.DOCUMENTO
    FakeAnthropic.DOCUMENTO = ("# ACCIÓN DE TUTELA\n\n¡Claro! Aquí va el borrador. Señor juez [COMPLETAR: ciudad] ✅. "
                               "Cabe destacar que la EPS negó el servicio [F1].\n\nQuedo atento.\n\n<<<VERIFICAR>>>\n- Cédula")
    try:
        r = cliente.post("/api/documentos/generar", headers=auth(t), json={"tipo": "tutela", "campos": {
            "solicitante": "Ana Pérez", "ciudad": "Bogotá", "contraparte": "EPS Salud", "derechos": "salud",
            "hechos": "La EPS negó un medicamento.", "peticiones": "Ordenar la entrega.", "urgente": "No"}})
    finally:
        FakeAnthropic.DOCUMENTO = original
    assert r.status_code == 200, r.text
    d = r.json()
    assert "✅" not in d["texto"] and "Cabe destacar" not in d["texto"] and "La EPS negó el servicio [F1]" in d["texto"]
    assert "[COMPLETAR: ciudad]" in d["texto"] and "Completar: ciudad" in d["verificar"] and "Cédula" in d["verificar"]
    sistema = FakeAnthropic.ultima_create["system"]
    assert "ESCRITO DE PRÁCTICA" not in " ".join(b["text"] for b in sistema)  # la tutela no es de práctica


def test_documento_de_practica_de_estudiante_suma_voz_de_estudiante(cliente):
    import documentos
    t = documentos.INDICE["concepto_juridico"]
    assert documentos.es_practica_estudiante(t, "estudiante", "trabajar")
    assert documentos.es_practica_estudiante(t, "auto", "aprender")
    assert not documentos.es_practica_estudiante(t, "abogado", "aprender")
    assert not documentos.es_practica_estudiante(documentos.INDICE["tutela"], "estudiante", "aprender")
    assert er.VOZ_ESTUDIANTE in documentos.voz_documento(t, "estudiante")
    _, _, tok = nuevo_usuario(cliente)
    cliente.post("/api/preferencias", headers=auth(tok), json={"escritura": "estudiante"})
    campos = {c["id"]: "Dato de prueba suficiente" for c in t["campos"] if c["requerido"]}
    for c in t["campos"]:
        if c["requerido"] and c["tipo"] == "select":
            campos[c["id"]] = c["opciones"][0]
        if c["requerido"] and c["tipo"] == "fecha":
            campos[c["id"]] = "2026-03-01"
        if c["requerido"] and c["tipo"] == "numero":
            campos[c["id"]] = "1000"
    r = cliente.post("/api/documentos/generar", headers=auth(tok), json={"tipo": "concepto_juridico", "campos": campos})
    assert r.status_code == 200, r.text
    sistema = FakeAnthropic.ultima_create["system"]
    assert len(sistema) == 2 and er.VOZ_ESTUDIANTE in sistema[1]["text"]
    assert "cache_control" in sistema[0] and "cache_control" not in sistema[1]


def test_revisar_estilo_endpoint(cliente):
    assert cliente.post("/api/estilo/revisar", json={"texto": "hola"}).status_code == 401
    _, _, t = nuevo_usuario(cliente)
    antes = cliente.get("/api/estado", headers=auth(t)).json()["perfil"]["usadas"]
    r = cliente.post("/api/estilo/revisar", headers=auth(t),
                     json={"texto": "¡Excelente pregunta! Cabe destacar que la tutela procede 😊."})
    assert r.status_code == 200
    d = r.json()
    assert d["parece_ia"] is True and {"apertura_relleno", "cabe_destacar", "emoji"} <= {x["id"] for x in d["rasgos"]}
    assert cliente.get("/api/estado", headers=auth(t)).json()["perfil"]["usadas"] == antes   # no cuesta consultas
    for malo in ({}, {"texto": ""}, {"texto": "   "}, {"texto": 5}, {"texto": ["a"]}):
        assert cliente.post("/api/estilo/revisar", headers=auth(t), json=malo).status_code == 400
    assert cliente.post("/api/estilo/revisar", headers={**auth(t), "content-type": "application/json"},
                        content=b"[1]").status_code == 400
    grande = "a " * 10001
    assert cliente.post("/api/estilo/revisar", headers=auth(t), json={"texto": grande}).status_code == 413


def test_revisar_estilo_tiene_limite_por_cuenta(cliente):
    _, _, t = nuevo_usuario(cliente)
    codigos = [cliente.post("/api/estilo/revisar", headers=auth(t), json={"texto": "Texto."}).status_code
               for _ in range(61)]
    assert codigos[:60] == [200] * 60 and codigos[60] == 429


def test_frontend_sin_js_en_linea_y_con_los_controles():
    html = (RAIZ / "static" / "index.html").read_text(encoding="utf-8")
    assert 'id="cf-escritura"' in html and 'data-change="guardarPrefs"' in html
    for v in ("auto", "estudiante", "abogado", "sencillo"):
        assert f'<option value="{v}">' in html
    assert not re.search(r"\son[a-z]+\s*=", html)
    app_js = (RAIZ / "static" / "app.js").read_text(encoding="utf-8")
    assert "/api/estilo/revisar" in app_js and "Revisar estilo" in app_js and "'pulido'" in app_js
    assert "Revisar estilo" in (RAIZ / "static" / "documentos.js").read_text(encoding="utf-8")
