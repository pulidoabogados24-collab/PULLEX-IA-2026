"""Estilo de redacción de PULLEX: escribir como un buen estudiante de Derecho y como un abogado
colombiano con oficio, y no como un asistente genérico de IA.

Este módulo no llama al modelo ni a la base de datos. Contiene:

* VOZ_ESTUDIANTE, VOZ_ABOGADO y VOZ_CIUDADANO: guías de voz para los mensajes de sistema.
* GUIA_ESCRITURA: las reglas generales "anti-IA" que comparten el chat y los escritos.
* CONECTORES: conectores por función lógica (para las guías y para enseñar).
* MULETILLAS_IA y rasgos_ia(texto): detector de rasgos típicos del texto generado por IA en español,
  con explicación y sugerencia para cada hallazgo. Es una ayuda de estilo, no una prueba de autoría.
* pulir(texto): correcciones deterministas y seguras (emojis, rellenos inequívocos al inicio y al
  cierre, muletillas de arranque de oración, negritas repartidas por el párrafo y guiones largos
  usados como pausa). Nunca toca citas textuales, marcas [F#], <<<VERIFICAR>>>, [COMPLETAR: …],
  "(pendiente de verificación)", enlaces, código ni tablas.

Fundamento y fuentes de la investigación: docs/16-ESTILO-HUMANO.md.
"""
import re
import statistics

# ===================================================================================== voces
VOZ_ESTUDIANTE = """VOZ DE ESTUDIANTE DE DERECHO (respuesta de examen, parcial, modular o taller de casos)
- Prosa continua, en párrafos de tres a seis oraciones. El razonamiento no va en viñetas: quien califica
  sigue el hilo argumentativo y las listas lo cortan. Si el caso exige enumerar requisitos o elementos,
  nómbralos y desarrolla cada uno en prosa.
- Método, sin anunciarlo con rótulos vacíos: (1) plantea el problema jurídico como una pregunta concreta
  sobre los hechos del caso; (2) identifica la norma o la institución que lo resuelve; (3) aplica cada
  requisito a los hechos, uno por uno: este hecho cumple o no este elemento, y por qué; (4) expone la mejor
  tesis contraria y explica por qué no prospera, o en qué escenario sí; (5) cierra con una conclusión que
  responde exactamente la pregunta formulada.
- Las ideas se unen con conectores que muestran la relación lógica ("por tanto", "sin embargo", "en
  efecto", "de ahí que", "a diferencia de", "en consecuencia"), no con muletillas.
- Primera persona con moderación ("considero que", "a mi juicio") cuando se pide tomar posición; en lo
  demás, impersonal ("se advierte que", "procede", "no se cumple"). No mezcles ambos registros en un párrafo.
- Cita como se cita en Colombia: "el artículo 86 de la Constitución Política", "el Decreto 2591 de 1991",
  "la Corte Constitucional, en la Sentencia T-760 de 2008". Si no tienes certeza de un número, nombra la
  institución y márcalo para verificar: un número inventado es un error grave en un examen.
- Errores que un docente castiga y que no cometes: transcribir artículos sin aplicarlos a los hechos,
  contestar una pregunta distinta de la formulada, enumerar teorías sin tomar posición, pasar por alto un
  hecho del enunciado, olvidar la posición de la contraparte y terminar sin conclusión.
- La extensión la marca la pregunta; una buena respuesta de examen suele caber en cuatro a ocho párrafos."""

VOZ_ABOGADO = """VOZ DE ABOGADO COLOMBIANO (concepto, memorial, demanda, recurso, tutela, correo profesional)
- Sobrio y preciso. Cada frase sirve para decidir: hechos, norma, razón o petición. Sin adjetivos de
  énfasis ("flagrante", "evidentísimo", "absolutamente") salvo que el hecho los demuestre.
- Oraciones de una idea, con sujeto, verbo y complemento en ese orden. Voz activa: "la entidad negó la
  solicitud", no "la solicitud fue negada por parte de la entidad". "Según" mejor que "de conformidad
  con lo establecido en"; "para" mejor que "a fin de".
- Párrafos cortos. Donde el género lo pide (hechos, pretensiones, excepciones, pruebas) numera y pon un
  solo hecho por numeral, con su fecha.
- Fórmulas forenses colombianas con mesura y en su sitio: "respetuosamente", "me permito", "con
  fundamento en", "solicito", "en mérito de lo expuesto" (antes de las pretensiones o de lo que se pide).
  Una por bloque; no las encadenes. Sin arcaísmos ni latinismos de adorno; el latinismo técnico sin
  equivalente cómodo (ratio decidendi, non bis in idem) se usa sin explicarlo a un abogado.
- Cita completa la primera vez ("artículo 86 de la Constitución Política"; "Corte Constitucional,
  Sentencia T-760 de 2008") y abreviada después ("art. 86 C.P."). Nada que no puedas verificar.
- Negrita solo en rótulos del escrito (partes, referencia, títulos de sección), nunca para subrayar frases
  dentro de un párrafo.
- Sin introducciones ni cierres de cortesía vacíos: el escrito termina con lo que pide, las pruebas, las
  notificaciones y la firma, no con un resumen."""

VOZ_CIUDADANO = """VOZ CLARA PARA QUIEN NO ES ABOGADO
- Primero la respuesta: "Sí", "No" o "Depende de…", y en la misma frase de qué depende.
- Frases de menos de 25 palabras, palabras de uso diario, tuteo respetuoso. Si usas un término jurídico,
  explícalo en la misma oración ("la tutela, una acción rápida ante un juez para proteger tus derechos
  fundamentales").
- Habla de su caso y no en abstracto: usa los datos que dio (la EPS, el arrendador, la fecha).
- Cálido sin exagerar: reconoce la preocupación una vez, sin frases de autoayuda ni signos de exclamación.
- Si hay pasos, aquí sí sirve la lista numerada: qué hacer, ante qué entidad, qué llevar y en qué plazo
  (con la advertencia de confirmarlo)."""

VOCES = {"estudiante": VOZ_ESTUDIANTE, "abogado": VOZ_ABOGADO, "sencillo": VOZ_CIUDADANO}
# Preferencia "Escribe como" (Ajustes). "auto" = el modelo elige la voz según quien escribe y lo que pide.
OPCIONES_ESCRITURA = ("auto", "estudiante", "abogado", "sencillo")

GUIA_ESCRITURA = """- Escribe como escribe una persona experta de Colombia, no como un asistente genérico: prosa natural,
  español de Colombia con la ortografía de la RAE y frases de largo variado. Usa encabezados, listas o
  tablas solo cuando ordenan algo que en prosa se leería peor (pasos, requisitos, comparaciones,
  liquidaciones). Una pregunta corta merece una respuesta corta y sin títulos.
- Sin relleno: no repitas la pregunta, no anuncies lo que vas a hacer ("A continuación te explico…"), no
  cierres con un resumen de lo ya dicho ni con ofrecimientos genéricos. Evita muletillas como "En ese orden
  de ideas", "Es importante destacar", "Cabe resaltar", "Cabe mencionar", "Vale la pena señalar", "En el
  ámbito de", "Juega un papel fundamental", "Sin lugar a dudas", "En conclusión", "Espero que esta
  información te sea útil" o "¡Excelente pregunta!".
- No uses los rasgos que delatan un texto de máquina: emojis; negritas repartidas por el párrafo (la
  negrita es para rótulos o para un dato que no puede pasarse por alto); guiones largos como pausa (usa
  coma, dos puntos o punto; la raya pegada al inciso —así— es correcta); grupos de tres adjetivos o
  ejemplos por costumbre; "no solo…, sino también…" como adorno; preguntas retóricas que tú mismo
  respondes ("¿La clave? …"); títulos con Mayúscula En Cada Palabra; entusiasmo artificial y signos de
  exclamación."""

# Para los escritos del automatizador (documentos.py): los rasgos de máquina que nunca deben aparecer.
RASGOS_A_EVITAR_ESCRITOS = (
    "- Sin emojis, sin negritas dentro de los párrafos, sin rayas o guiones largos usados como pausa, sin "
    "títulos con Mayúscula En Cada Palabra y sin muletillas («Es importante destacar», «Cabe resaltar», «En el "
    "ámbito de», «Juega un papel fundamental»). Sin introducción que anuncie el escrito ni cierre de cortesía "
    "(«Espero que…», «Quedo atento…»): el escrito empieza por su encabezado y termina en la firma.")

# Para quien EVALÚA (Laboratorio de casos y Taller de escritos): cómo redactar la retroalimentación y qué mirar en el
# criterio de redacción. El estilo nunca mueve el puntaje de los criterios jurídicos.
ESTILO_EVALUACION = """CÓMO ESCRIBES LA RETROALIMENTACIÓN
- Como un docente que corrige a mano: directa y concreta, con las palabras del caso. Di qué falta o qué sobra
  y cómo arreglarlo. Sin muletillas («Es importante destacar», «Cabe resaltar»), sin elogios de relleno, sin
  emojis ni signos de exclamación.
- En el criterio de redacción (claridad o estilo) valora la prosa en párrafos unidos por conectores con función
  lógica, una idea por oración, las citas a la manera colombiana y el tono sobrio; resta por muletillas,
  relleno, adjetivos de énfasis y normas transcritas sin aplicarlas a los hechos.
- La redacción se califica solo en su criterio: no subas ni bajes un criterio jurídico por el estilo. Conserva
  toda advertencia de verificar la vigencia de una norma o un número del que no estés seguro."""

INSTRUCCION_VOZ = {
    "estudiante": ("ESCRIBE COMO: el usuario eligió la voz de ESTUDIANTE DE DERECHO. Cuando la consulta sea un caso, "
                   "una pregunta de examen o una explicación de estudio, aplica la VOZ DE ESTUDIANTE DE DERECHO del "
                   "mensaje de sistema. En temas no jurídicos escribe con naturalidad."),
    "abogado": ("ESCRIBE COMO: el usuario eligió la voz de ABOGADO. En lo jurídico aplica la VOZ DE ABOGADO "
                "COLOMBIANO del mensaje de sistema. En temas no jurídicos escribe con naturalidad y sobriedad."),
    "sencillo": ("ESCRIBE COMO: el usuario eligió LENGUAJE SENCILLO. Aplica la VOZ CLARA PARA QUIEN NO ES ABOGADO "
                 "aunque el tema sea técnico: el rigor no cambia, solo el lenguaje."),
}


def instruccion_voz(opcion: str) -> str:
    """Texto para el bloque dinámico del sistema según la preferencia "Escribe como" ("" si es automático)."""
    return INSTRUCCION_VOZ.get(opcion, "")


# ================================================================================ conectores
CONECTORES = {
    "adicion": ["además", "asimismo", "a ello se suma", "por otra parte", "de igual modo"],
    "contraste": ["sin embargo", "no obstante", "en cambio", "con todo", "aun así", "a diferencia de"],
    "causa": ["porque", "pues", "dado que", "ya que", "toda vez que", "en razón de"],
    "consecuencia": ["por tanto", "en consecuencia", "por ello", "de ahí que", "así las cosas"],
    "concesion": ["aunque", "si bien", "aun cuando", "a pesar de que"],
    "condicion": ["si", "siempre que", "en caso de que", "salvo que", "a menos que"],
    "ejemplo": ["por ejemplo", "así ocurre cuando", "es el caso de"],
    "precision": ["es decir", "esto es", "en concreto", "dicho con más precisión"],
    "orden": ["en primer lugar", "en segundo lugar", "de un lado", "de otro lado", "por último"],
    "cierre": ["en suma", "por lo expuesto", "en mérito de lo expuesto"],
    "remision_normativa": ["según", "con fundamento en", "conforme a", "en los términos de"],
}

# ======================================================================= zonas que no se tocan
MARCA_VERIFICAR = "<<<VERIFICAR>>>"
ROTULO_FUNCIONARIO = "BORRADOR — PROYECTO PARA REVISIÓN DEL FUNCIONARIO"
_PH_A, _PH_B = "\uE000", "\uE001"   # caracteres de uso privado: marcadores internos de pulir()

# Por prioridad: primero el código y la lista final de verificación (lo que haya dentro no se vuelve a mirar),
# después el resto. Así una URL pegada a una cerca de código no se "come" el bloque.
_PROTEGER_PASOS = [re.compile(p) for p in (
    r"```[\s\S]*?```",                            # bloques de código
    re.escape(MARCA_VERIFICAR) + r"[\s\S]*\Z",     # la lista final de datos a verificar, intacta
    r"`[^`\n]+`",                                  # código en línea
    "|".join([
        r"\[F\d+\]",                               # marcas de fuente del corpus
        r"\[\s*COMPLETAR[^\]\n]*\]",               # marcadores de datos faltantes
        r"\[[^\[\]\n]{1,300}\]\([^()\s]{1,500}\)",  # enlaces markdown
        # URLs sueltas (sin la puntuación final de la frase ni emojis pegados)
        r"https?://[^\s)>\]`*\u2600-\u27BF\U0001F000-\U0001FAFF]*[^\s)>\]`*\u2600-\u27BF\U0001F000-\U0001FAFF.,;:!?'\"]",
        r"«[^«»\n]{0,800}»",                       # citas textuales
        r"“[^“”\n]{0,800}”",
        r"\"[^\"\n]{1,800}\"",
        r"\((?:pendiente de verificación|verificar vigencia)\)",
        re.escape(ROTULO_FUNCIONARIO),
    ]),
)]
_RE_PH = re.compile(_PH_A + r"(\d+)" + _PH_B)


def _proteger(texto: str):
    guardados = []

    def _sustituir(m):
        guardados.append(m.group(0))
        return f"{_PH_A}{len(guardados) - 1}{_PH_B}"

    for rx in _PROTEGER_PASOS:
        texto = rx.sub(_sustituir, texto)
    return texto, guardados


def _restaurar(texto: str, guardados: list) -> str:
    # Un guardado puede contener marcadores de pasos anteriores (una cita con [F1] dentro): se repite.
    for _ in range(len(_PROTEGER_PASOS) + 1):
        if _PH_A not in texto:
            break
        texto = _RE_PH.sub(lambda m: guardados[int(m.group(1))], texto)
    return texto


def _enmascarar(texto: str) -> str:
    """Igual longitud, con las zonas protegidas en blanco: el detector no las lee (una cita textual
    que diga «es importante destacar» no es una muletilla de quien escribe)."""
    for rx in _PROTEGER_PASOS:
        texto = rx.sub(lambda m: re.sub(r"[^\n]", " ", m.group(0)), texto)
    return texto


# ==================================================================================== emojis
_EMOJI_CHARS = (
    "\U0001F000-\U0001FAFF"      # pictogramas, emoticonos, transporte, banderas, símbolos extendidos
    "☀-☏☓-➿"  # símbolos varios y dingbats (se respetan ☐ ☑ ☒, usados en formularios)
    "⬅-⬇⬛⬜⭐⭕"
    "⌚⌛⏩-⏳⏸-⏺⤴⤵〰〽㊗㊙"
)
_EMOJI_SUFIJOS = "️‍⃣\U0001F3FB-\U0001F3FF"
_RE_EMOJI = re.compile(f"[{_EMOJI_CHARS}][{_EMOJI_SUFIJOS}{_EMOJI_CHARS}]*")
_RE_EMOJI_CONTEXTO = re.compile(f"([^\\S\\n]*)(?:[{_EMOJI_CHARS}][{_EMOJI_SUFIJOS}{_EMOJI_CHARS}]*[^\\S\\n]*)+")
# Excepciones dentro de los rangos: marcas de verificación y casillas que se usan en escritos.
_EMOJI_PERMITIDOS = set("✓✗✕☐☑☒")


def _es_emoji(c: str) -> bool:
    return bool(_RE_EMOJI.match(c)) and c not in _EMOJI_PERMITIDOS


# ============================================================================ catálogo de rasgos
# Cada muletilla: id, categoría, patrón (regex, sin distinguir mayúsculas), explicación, sugerencia, peso.
# El peso refleja qué tanto delata texto de máquina: las muletillas forenses que también usan muchas
# personas pesan menos que los rellenos serviles típicos de un asistente.
MULETILLAS_IA = [
    ("importante_destacar", "muletilla",
     r"\bes (?:muy |sumamente |especialmente )?importante (?:destacar|señalar|resaltar|mencionar|subrayar|recordar|"
     r"tener en cuenta|notar|considerar|de (?:destacar|mencionar|señalar))\b",
     "Anuncia que algo es importante en vez de decirlo. Es la muletilla más típica del texto generado por IA.",
     "Bórrala y empieza por el dato: «La tutela procede…».", 1.0),
    ("cabe_destacar", "muletilla",
     r"\bcabe (?:destacar|resaltar|mencionar|señalar|recalcar|subrayar)\b",
     "Fórmula de relleno que no aporta información.",
     "Elimínala o reemplázala por un conector con función («además», «sin embargo»).", 1.0),
    ("vale_la_pena", "muletilla",
     r"\bvale la pena (?:destacar|resaltar|mencionar|señalar|recordar|subrayar|anotar)\b",
     "Fórmula de relleno que no aporta información.", "Elimínala y di el dato directamente.", 1.0),
    ("ambito", "muletilla", r"\ben el ámbito\b(?! de aplicaci)",
     "«En el ámbito de» alarga la frase sin precisar nada (salvo «ámbito de aplicación», que es técnico).",
     "Usa «en», «en materia de» o nombra la rama: «en derecho laboral».", 0.5),
    ("papel_fundamental", "muletilla",
     r"\b(?:juega|juegan|desempeña|desempeñan|cumple|cumplen) un (?:papel|rol) (?:fundamental|crucial|clave|esencial|"
     r"determinante|vital|importante|central)\b",
     "Cliché («juega un papel fundamental»); además, «jugar un rol» es un calco del inglés.",
     "Di qué hace exactamente: «la Superintendencia vigila…».", 1.0),
    ("es_fundamental", "muletilla",
     r"\b(?:es|resulta) (?:fundamental|crucial|esencial|vital|clave) (?:que|tener|entender|comprender|recordar|"
     r"destacar|considerar|conocer)\b",
     "Valora en lugar de explicar; suele preceder a una obviedad.", "Explica la razón o la consecuencia.", 1.0),
    ("mundo_actual", "cliche",
     r"\ben (?:el mundo|la sociedad|el panorama|el contexto) (?:actual|de hoy|moderno|moderna|contemporáneo)\b|"
     r"\ben la era (?:digital|actual|moderna)\b",
     "Apertura genérica que no se refiere al caso.", "Empieza por el hecho o la norma concretos.", 1.0),
    ("abanico", "cliche", r"\b(?:un amplio abanico|una amplia gama|un sinfín|una gran variedad) de\b",
     "Expresión vaga de folleto publicitario.", "Enumera lo que corresponda o di cuántos son.", 0.5),
    ("adjetivo_ia", "lexico",
     r"\b(?:crucial(?:es)?|fascinantes?|apasionantes?|robust[oa]s?|holístic[oa]s?|sin precedentes|"
     r"transformador(?:a|es)?|innovador(?:a|es)?)\b",
     "Adjetivo de énfasis muy frecuente en textos de IA y extraño en el registro jurídico.",
     "Cámbialo por uno preciso o quítalo.", 0.5),
    ("enfoque_integral", "cliche", r"\b(?:enfoque|visión|perspectiva) (?:integral|holística|multidimensional)\b",
     "Cliché de informe genérico.", "Di en qué consiste el enfoque.", 0.5),
    ("anuncio", "relleno",
     r"\b(?:a continuación|seguidamente),? (?:te |les? )?(?:presento|explico|detallo|dejo|comparto|muestro|"
     r"encontrarás|desglos(?:o|aré))\b|\baquí (?:tienes|te (?:dejo|presento|comparto))\b|"
     r"\b(?:te|le) comparto (?:una|un|los|las|el|la)\b",
     "Anuncia lo que viene en vez de darlo.", "Bórralo y entrega el contenido.", 1.0),
    ("verbo_ia", "lexico",
     r"\b(?:profundicemos|sumerj[áa]monos|exploremos|desglosemos|naveguemos|adentrémonos|analicemos juntos)\b",
     "Verbo de presentador que delata a un asistente genérico.", "Ve directo al análisis.", 1.0),
    ("sin_duda", "muletilla", r"\bsin lugar a dudas?\b|\bsin duda alguna\b|\bindudablemente\b",
     "Refuerzo enfático: en derecho casi nada es indudable.", "Quítalo o matiza con la razón.", 0.5),
    ("orden_de_ideas", "muletilla_forense", r"\ben ese orden de ideas\b|\bdicho lo anterior\b|\bdicho esto\b",
     "Muletilla forense gastada; no es exclusiva de la IA, pero alarga sin unir nada.",
     "Usa un conector con función: «por tanto», «así las cosas», «en consecuencia».", 0.5),
    ("no_solo_sino", "estructura",
     r"\bno (?:solo|sólo|solamente|únicamente) [^.;:\n]{1,90}?,? sino (?:también|que también|además)\b",
     "Paralelismo «no solo…, sino también…» usado como adorno: patrón muy frecuente en textos de IA.",
     "Afirma las dos cosas por separado o quédate con la que importa.", 1.0),
    ("autoidentificacion", "relleno",
     r"\bcomo (?:modelo de (?:lenguaje|inteligencia artificial)|(?:una )?inteligencia artificial|asistente virtual)\b",
     "Frase de asistente que no corresponde a un escrito propio.", "Elimínala.", 2.0),
    ("pregunta_retorica", "estructura",
     r"¿(?:(?:y )?(?:la|el|lo|los|las) (?:clave|resultado|respuesta|problema|razón|diferencia|truco|secreto|"
     r"verdad|consecuencia|novedad)|qué significa esto|por qué (?:es|importa) (?:esto|importante)|y (?:ahora|entonces)|"
     r"cómo funciona(?: esto)?|qué quiere decir esto)\?",
     "Pregunta retórica que el propio texto responde enseguida: recurso típico de la IA.",
     "Convierte la pregunta en afirmación.", 1.0),
]
_MULETILLAS = [(i, c, re.compile(p, re.I), e, s, w) for i, c, p, e, s, w in MULETILLAS_IA]

_APERTURA = re.compile(
    r"\A\s*(?:¡\s*(?:excelente|buena|gran|muy buena|qué buena|interesante) pregunta\s*!+|"
    r"¡\s*claro(?: que sí)?\s*!+|¡\s*por supuesto\s*!+|¡\s*con (?:mucho )?gusto\s*!+|¡\s*desde luego\s*!+|"
    r"(?:es una |qué )?(?:excelente|muy buena|gran|buena|interesante) pregunta\s*[.!]+|"
    r"claro que sí\s*[.!]+|por supuesto\s*[.!]+|entiendo perfectamente(?: tu (?:pregunta|duda|inquietud))?\s*[.!]+)",
    re.I)
_CIERRE_FRASE = (
    r"(?:¡\s*)?espero que (?:esto|(?:esta|la|mi|estas) (?:información|respuesta|explicación|guía|orientación|"
    r"aclaración|explicaciones))(?: te| le| les)? (?:sea|haya sido|resulte|sirva|ayude|aclare)[^.!?\n]{0,70}[.!]+|"
    r"(?:¡\s*)?espero (?:haberte|haber|que te haya) (?:ayudado|aclarado|servido|sido de (?:ayuda|utilidad))[^.!?\n]{0,50}[.!]+|"
    r"si tienes (?:más|alguna otra|otras?) (?:preguntas?|dudas?|inquietud(?:es)?)[^.!?\n]{0,50}?,? "
    r"(?:no dudes en|puedes|con gusto|estaré|aquí estoy|quedo|escríbeme|házmelo saber|avísame)[^.!?\n]{0,70}[.!]+|"
    r"no dudes en (?:preguntar(?:me)?|escribirme|consultarme|contactarme|decírmelo|hacérmelo saber)[^.!?\n]{0,60}[.!]+|"
    r"¿(?:hay|necesitas|te puedo ayudar con|puedo ayudarte (?:con|en)) algo más[^?\n]{0,60}\?|"
    r"(?:¡\s*)?(?:estoy|sigo) (?:aquí|a (?:tu|su) disposición) (?:para|a) (?:ayudarte|lo que necesites|"
    r"cualquier (?:otra )?(?:duda|pregunta|inquietud))[^.!?\n]{0,40}[.!]+"
)
# Fórmula de cortesía de correo: frecuente también en personas, así que pesa poco y pulir() no la quita.
_RE_QUEDO_ATENTO = re.compile(r"\bquedo (?:muy )?atent[oa] (?:a|para) (?:cualquier|tus|sus|todas? (?:tus|sus|las))? ?"
                              r"(?:otra )?(?:duda|pregunta|inquietud|comentario|requerimiento)s?\b", re.I)
_RE_CIERRE = re.compile(r"\A\s*(?:" + _CIERRE_FRASE + r")\s*\Z", re.I)
_RE_CIERRE_BUSCAR = re.compile(_CIERRE_FRASE, re.I)
_RE_RESUMEN_FINAL = re.compile(r"\A\s*(?:en resumen|en conclusión|en definitiva|para resumir|para concluir|"
                               r"en síntesis|resumiendo)\s*[,:]", re.I)
_RE_MULETILLA_INICIO = re.compile(
    r"(?m)(^[ \t]*(?:[-*•][ \t]+|\d+[.)][ \t]+|>[ \t]*)?|[.!?…][ \t]+)"
    r"(?:es (?:muy |sumamente |especialmente )?importante (?:destacar|señalar|resaltar|mencionar|subrayar|recordar|"
    r"tener en cuenta|notar)|cabe (?:destacar|resaltar|mencionar|señalar|recalcar|subrayar)|"
    r"vale la pena (?:destacar|resaltar|mencionar|señalar|recordar|subrayar|anotar)) que[ \t]+(\S)", re.I)
_RE_GUION = re.compile(r"(?<=[^\s,;:.(\[—–-])[ \t]+[—–][ \t]+(?=[^\s—–])")
_RE_NEGRITA = re.compile(r"\*\*(?=\S)([^*\n]{1,200}?)(?<=\S)\*\*")
_RE_INICIO_LINEA = re.compile(r"\A[ \t]*(?:[-*•+][ \t]+|\d+[.)][ \t]+|>[ \t]*)?\Z")
_RE_TRIADA = re.compile(r"(?<![,\w])(?:\w+ ){0,2}\w{3,}, (?:\w+ ){0,2}\w{3,},? (?:y|e) (?:\w+ ){0,2}\w{3,}\b")
_RE_ENCABEZADO = re.compile(r"(?m)^[ \t]{0,3}#{1,6}[ \t]+(.+)$")
_RE_VINETA = re.compile(r"(?m)^[ \t]*[-*•+][ \t]+(.+)$")
# Títulos que nombran instituciones o normas llevan mayúsculas legítimas («Código General del Proceso»).
_RE_NOMBRE_PROPIO = re.compile(r"\b(?:Código|Ley|Decreto|Corte|Consejo|Constitución|Sentencia|Tribunal|Juzgado|"
                               r"Superintendencia|Fiscalía|Procuraduría|Defensoría|Ministerio|Registraduría|"
                               r"Personería|Estatuto|Señora?|Sala|República|Rama|Comisión|Contraloría)\b")
_MINUSCULAS_TITULO = {"de", "del", "la", "las", "el", "los", "y", "e", "o", "u", "en", "a", "al", "por", "para",
                      "con", "sin", "que", "un", "una", "sobre", "ante"}


def _termino_definido(contenido: str) -> bool:
    """¿Término definido de un contrato o una demanda («EL ARRENDADOR», «DEMANDANTE», «LAS PARTES»)? Va todo en
    mayúsculas y es una expresión de varias palabras o una palabra de seis letras o más. Una sigla corta
    («EPS», «DIAN», «CGP») no es un término definido: en negrita dentro de una frase es énfasis, como
    cualquier otra palabra resaltada."""
    letras = [c for c in contenido if c.isalpha()]
    if not letras or not all(c.isupper() for c in letras):
        return False
    return len(contenido.split()) >= 2 or len(letras) >= 6


def _negrita_suelta(linea: str, m) -> bool:
    """¿Negrita «de énfasis» dentro de un párrafo? No lo son el rótulo al comienzo de la línea («**Hechos.**»)
    ni los términos definidos en mayúsculas de contratos y demandas («**EL ARRENDADOR**», «**DEMANDANTE**»)."""
    if _RE_INICIO_LINEA.match(linea[:m.start()]):
        return False
    return not _termino_definido(m.group(1))


def _es_linea_especial(linea: str) -> bool:
    s = linea.strip()
    return s.startswith("#") or s.startswith("|") or (s.startswith("**") and s.endswith("**") and s.count("**") == 2)


def _linea_de_prosa(linea: str) -> bool:
    """Para la regla de la raya: solo líneas de prosa. Se excluyen títulos, tablas, rótulos y encabezados
    de escritos («JUZGADO CIVIL — REPARTO», «Referencia: Tutela — Ana Pérez»), que suelen ser cortos o
    estar en mayúsculas."""
    if _es_linea_especial(linea) or _palabras(linea) < 8:
        return False
    letras = [c for c in linea if c.isalpha()]
    return not letras or sum(c.isupper() for c in letras) / len(letras) < 0.6


def _palabras(texto: str) -> int:
    return len(re.findall(r"\w+", texto))


def _fragmento(texto: str, ini: int, fin: int) -> str:
    return re.sub(r"\s+", " ", texto[ini:fin]).strip()[:120]


def _ultimo_parrafo_util(parrafos: list) -> int:
    """Índice del último párrafo que no es la advertencia legal obligatoria ni una línea de fuentes."""
    for i in range(len(parrafos) - 1, -1, -1):
        p = parrafos[i].strip().lower()
        if not p or p.startswith(("esto es orientación general", "_esto es orientación", "*esto es orientación")):
            continue
        if _RE_CIERRE_BUSCAR.match(p):
            continue
        return i
    return -1


def rasgos_ia(texto: str) -> list:
    """Detecta rasgos de estilo típicos del texto generado por IA en español.

    Devuelve una lista de dicts {id, categoria, explicacion, sugerencia, veces, peso, ejemplos,
    posiciones}. Las citas textuales, el código, los enlaces y las marcas [F#] no se analizan.
    Es una ayuda para revisar el estilo, no una prueba de que un texto lo escribió una máquina."""
    texto = texto or ""
    vista = _enmascarar(texto)
    hallados = {}

    def anotar(rid, categoria, explicacion, sugerencia, peso, ini=None, fin=None, ejemplo=None):
        r = hallados.setdefault(rid, {"id": rid, "categoria": categoria, "explicacion": explicacion,
                                      "sugerencia": sugerencia, "veces": 0, "peso": 0.0,
                                      "ejemplos": [], "posiciones": []})
        r["veces"] += 1
        r["peso"] = round(min(r["peso"] + peso, 2.0), 2)   # un mismo rasgo pesa como máximo 2
        if ini is not None and len(r["posiciones"]) < 10:
            r["posiciones"].append([ini, fin])
        ej = ejemplo if ejemplo is not None else (_fragmento(texto, ini, fin) if ini is not None else None)
        if ej and ej not in r["ejemplos"] and len(r["ejemplos"]) < 3:
            r["ejemplos"].append(ej)

    for rid, cat, rx, expl, sug, peso in _MULETILLAS:
        for m in rx.finditer(vista):
            anotar(rid, cat, expl, sug, peso, m.start(), m.end())

    # Apertura y cierre serviles.
    m = _APERTURA.match(vista)
    if m:
        anotar("apertura_relleno", "relleno", "Arranque de asistente («¡Excelente pregunta!», «¡Claro!») que no aporta.",
               "Empieza por la respuesta.", 2.0, m.start(), m.end())
    for m in _RE_CIERRE_BUSCAR.finditer(vista):
        anotar("cierre_servicial", "relleno",
               "Cierre de cortesía genérico («Espero que te sea útil», «Si tienes más preguntas…»).",
               "Termina con el último dato útil o con el paso siguiente concreto.", 2.0, m.start(), m.end())
    for m in _RE_QUEDO_ATENTO.finditer(vista):
        anotar("quedo_atento", "relleno",
               "Fórmula de cortesía de correo («Quedo atento a cualquier inquietud»). La usan muchas personas, pero "
               "en un memorial o en una respuesta sobra.", "Termina con la petición o el dato útil.", 0.5,
               m.start(), m.end())
    parrafos = re.split(r"\n[ \t]*\n", vista.strip())
    k = _ultimo_parrafo_util(parrafos)
    if len(parrafos) >= 2 and k > 0 and _RE_RESUMEN_FINAL.match(parrafos[k]):
        anotar("cierre_resumen", "estructura",
               "El último párrafo arranca con «En resumen/En conclusión» y suele repetir lo ya dicho.",
               "Si la conclusión es nueva, enúnciala sin el rótulo; si repite, bórrala.", 1.0,
               ejemplo=_fragmento(parrafos[k], 0, 80))

    # Emojis.
    for m in list(_RE_EMOJI.finditer(vista)) + list(_RE_KEYCAP.finditer(vista)):
        if any(_es_emoji(c) for c in m.group(0)) or "\u20E3" in m.group(0):
            anotar("emoji", "formato", "Los emojis no tienen cabida en un texto jurídico ni académico.",
                   "Quítalos.", 2.0, m.start(), m.end())

    # Exclamaciones (entusiasmo artificial), fuera de la apertura ya contada.
    excl = [m for m in re.finditer(r"¡[^!\n]{1,120}!", vista) if not (_APERTURA.match(vista) and m.start() < 40)]
    if len(excl) >= 2:
        for m in excl:
            anotar("exclamaciones", "tono", "Entusiasmo artificial: varios signos de exclamación en un texto expositivo.",
                   "Usa punto. El tono lo dan los hechos, no los signos.", 0.5, m.start(), m.end())

    # Guiones largos usados como pausa (con espacio a ambos lados, al estilo inglés).
    guiones = [m for m in _RE_GUION.finditer(vista) if _linea_de_prosa(_linea_de(vista, m.start()))]
    if guiones:
        for m in guiones:
            anotar("guion_largo", "puntuacion",
                   "Raya o guion largo con espacios usado como pausa: rasgo muy frecuente del texto de IA. En español "
                   "la raya de inciso va pegada al texto (—así—) y no reemplaza a la coma.",
                   "Usa coma, dos puntos o punto.", 0.75 if len(guiones) == 1 else 1.0, m.start(), m.end())

    # Negritas repartidas dentro de los párrafos.
    inline = []
    for linea_ini, linea in _lineas(vista):
        if _es_linea_especial(linea):
            continue
        for m in _RE_NEGRITA.finditer(linea):
            if _negrita_suelta(linea, m):
                inline.append((linea_ini + m.start(), linea_ini + m.end()))
    if len(inline) >= 3:
        for ini, fin in inline:
            anotar("negritas", "formato", "Negritas repartidas por los párrafos: el lector ya no sabe qué es lo importante.",
                   "Deja la negrita para rótulos o para un solo dato decisivo.", 0.5, ini, fin)

    # Viñetas cortas en lugar de prosa.
    vinetas = _RE_VINETA.findall(vista)
    lineas_txt = [l for l in vista.splitlines() if l.strip()]
    if len(vinetas) >= 6 and len(vinetas) / max(1, len(lineas_txt)) >= 0.5 and \
            statistics.mean(_palabras(v) for v in vinetas) <= 14:
        anotar("vinetas", "formato",
               "El razonamiento está partido en viñetas cortas; en un concepto o un examen se espera prosa argumentada.",
               "Convierte las viñetas en párrafos unidos por conectores.", 1.0, ejemplo=f"{len(vinetas)} viñetas")

    # Títulos con Mayúscula En Cada Palabra (calco del inglés).
    for m in _RE_ENCABEZADO.finditer(vista):
        palabras = [p for p in re.findall(r"[^\W\d_]+", m.group(1))]
        largas = [p for p in palabras[1:] if p.lower() not in _MINUSCULAS_TITULO]
        if _RE_NOMBRE_PROPIO.search(m.group(1)):
            continue
        if len(largas) >= 2 and all(p[0].isupper() for p in largas) and not m.group(1).isupper():
            anotar("titulo_mayusculas", "formato",
                   "Título con Mayúscula En Cada Palabra: es norma del inglés; en español solo va la inicial.",
                   "Escribe «Marco normativo aplicable», no «Marco Normativo Aplicable».", 1.0,
                   m.start(1), m.end(1))

    # Estructura de informe para una respuesta corta.
    enc = _RE_ENCABEZADO.findall(vista)
    if len(enc) >= 3 and _palabras(vista) < 220:
        anotar("titulos_respuesta_corta", "formato",
               "Muchos títulos para un texto corto: parece una plantilla, no una respuesta.",
               "Responde en uno o dos párrafos sin títulos.", 1.0, ejemplo=f"{len(enc)} títulos en {_palabras(vista)} palabras")

    # Tríadas por costumbre ("claro, preciso y conciso").
    triadas = list(_RE_TRIADA.finditer(vista))
    if len(triadas) >= 3:
        for m in triadas:
            anotar("triadas", "estructura",
                   "Enumeraciones de tres elementos repetidas por costumbre: dan un ritmo mecánico.",
                   "Deja solo los elementos que el caso necesita; varía la construcción.", 0.5, m.start(), m.end())

    orden = ["apertura_relleno", "cierre_servicial", "emoji", "autoidentificacion"]
    for r in hallados.values():
        r["nombre"] = NOMBRES.get(r["id"], r["id"])
    return sorted(hallados.values(), key=lambda r: (r["id"] not in orden, -r["peso"], r["id"]))


def _linea_de(texto: str, pos: int) -> str:
    fin = texto.find("\n", pos)
    return texto[texto.rfind("\n", 0, pos) + 1: fin if fin >= 0 else len(texto)]


def _lineas(texto: str):
    pos = 0
    for linea in texto.split("\n"):
        yield pos, linea
        pos += len(linea) + 1


UMBRAL_IA = 2.0

# Nombre legible de cada rasgo (lo que ve el usuario en «Revisar estilo»).
NOMBRES = {
    "importante_destacar": "«Es importante destacar»", "cabe_destacar": "«Cabe destacar/resaltar»",
    "vale_la_pena": "«Vale la pena señalar»", "ambito": "«En el ámbito de»",
    "papel_fundamental": "«Juega un papel fundamental»", "es_fundamental": "«Es fundamental que…»",
    "mundo_actual": "Apertura genérica («En el mundo actual»)", "abanico": "«Un amplio abanico de»",
    "adjetivo_ia": "Adjetivos de énfasis («crucial», «fascinante»)", "enfoque_integral": "«Enfoque integral»",
    "anuncio": "Anuncio de lo que viene («A continuación te explico»)", "verbo_ia": "«Profundicemos», «Exploremos»",
    "sin_duda": "«Sin lugar a dudas»", "orden_de_ideas": "«En ese orden de ideas»",
    "no_solo_sino": "«No solo…, sino también…»", "autoidentificacion": "Frase de asistente («Como IA…»)",
    "pregunta_retorica": "Pregunta retórica que se responde sola", "apertura_relleno": "Arranque de asistente",
    "cierre_servicial": "Cierre de cortesía genérico", "quedo_atento": "«Quedo atento a cualquier inquietud»",
    "cierre_resumen": "Cierre «En conclusión» que repite", "emoji": "Emojis",
    "exclamaciones": "Exclamaciones de entusiasmo", "guion_largo": "Raya o guion largo como pausa",
    "negritas": "Negritas dentro de los párrafos", "vinetas": "Viñetas en lugar de prosa",
    "titulo_mayusculas": "Títulos con Mayúscula En Cada Palabra",
    "titulos_respuesta_corta": "Demasiados títulos para un texto corto", "triadas": "Tríadas por costumbre",
}


def revisar(texto: str) -> dict:
    """Resultado completo para la herramienta «Revisar estilo»: rasgos, puntaje y una valoración breve."""
    rasgos = rasgos_ia(texto)
    puntaje = round(sum(r["peso"] for r in rasgos), 2)
    if puntaje >= 4:
        valoracion = "Tiene muchos rasgos de texto generado por IA. Revisa las sugerencias antes de entregarlo."
    elif puntaje >= UMBRAL_IA:
        valoracion = "Tiene varios rasgos de texto generado por IA."
    elif rasgos:
        valoracion = "Se lee natural; hay detalles menores que puedes pulir."
    else:
        valoracion = "No encontré rasgos típicos de texto generado por IA."
    return {"rasgos": rasgos, "puntaje": puntaje, "umbral": UMBRAL_IA, "parece_ia": puntaje >= UMBRAL_IA,
            "valoracion": valoracion, "palabras": _palabras(texto or "")}


def resumen_estilo(texto: str, maximo: int = 5) -> dict:
    """Revisión de estilo compacta para acompañar una evaluación (Laboratorio de casos y Taller de escritos): los rasgos
    más pesados con su sugerencia y un ejemplo tomado del propio texto. Es determinista y no altera el puntaje."""
    r = revisar(texto)
    return {"valoracion": r["valoracion"], "puntaje": r["puntaje"], "parece_ia": r["parece_ia"],
            "rasgos": [{"id": x["id"], "nombre": x["nombre"], "veces": x["veces"], "explicacion": x["explicacion"],
                        "sugerencia": x["sugerencia"], "ejemplos": x["ejemplos"][:1]} for x in r["rasgos"][:maximo]],
            "nota": "Ayuda de estilo calculada sin IA. No cambia tu puntaje ni prueba quién escribió el texto."}


def pulir_campos(datos: dict, campos) -> dict:
    """Aplica pulir() a los campos de texto indicados de un dict (cadenas o listas de cadenas), en el sitio.
    Lo usan las evaluaciones y soluciones que el modelo devuelve como JSON."""
    if not isinstance(datos, dict):
        return datos
    for c in campos:
        v = datos.get(c)
        if isinstance(v, str):
            datos[c] = pulir(v)
        elif isinstance(v, list):
            datos[c] = [pulir(x) if isinstance(x, str) else x for x in v]
    return datos


def parece_ia(texto: str) -> bool:
    return revisar(texto)["parece_ia"]


# ===================================================================================== pulir
_RE_MARCADOR = re.compile(r"[ \t]*(?:[-*•+]|\d+[.)]|>|#{1,6})[ \t]*")
_RE_KEYCAP = re.compile(r"([0-9#*])\uFE0F?\u20E3")


def _quitar_emojis(texto: str) -> str:
    texto = _RE_KEYCAP.sub(r"\1", texto)

    def _sust(m):
        grupo = m.group(0)
        if not any(_es_emoji(c) for c in grupo):
            return grupo
        conservar = "".join(c for c in grupo if c in _EMOJI_PERMITIDOS)
        ini, fin = m.start(), m.end()
        antes = texto[texto.rfind("\n", 0, ini) + 1:ini]
        sig = texto[fin:fin + 1]
        hay_der = sig not in ("", "\n")
        if not antes.strip():
            return conservar + (" " if conservar and hay_der else "")
        if _RE_MARCADOR.fullmatch(antes):
            return " " + conservar + (" " if conservar and hay_der else "") if hay_der else ""
        if conservar:
            return " " + conservar + (" " if hay_der else "")
        if not hay_der or sig in ".,;:!?)]»”":
            return ""
        return " "
    return _RE_EMOJI_CONTEXTO.sub(_sust, texto)


def _capitalizar(c: str) -> str:
    return c.upper() if c.isalpha() else c


def _quitar_apertura(texto: str) -> str:
    for _ in range(3):
        m = _APERTURA.match(texto)
        if not m:
            break
        resto = texto[m.end():].lstrip(" \t")
        if len(resto.strip()) < 20:
            break
        resto = resto.lstrip("\n") if resto.startswith("\n") else resto
        texto = _capitalizar(resto[:1]) + resto[1:]
    return texto


def _quitar_cierre(texto: str) -> str:
    """Quita frases finales de cortesía vacía en los últimos párrafos (también si después viene la
    advertencia legal). Solo frases completas que coinciden con el patrón; nunca contenido."""
    cuerpo = texto.rstrip()
    final = texto[len(cuerpo):]
    partes = re.split(r"(\n[ \t]*\n)", cuerpo)        # [p0, sep, p1, sep, p2, …]
    vaciados, revisados = set(), 0
    for i in range(len(partes) - 1, -1, -2):
        if revisados >= 3:
            break
        p = partes[i]
        if not p.strip():
            continue
        revisados += 1
        if p.lstrip().startswith(("#", "|", "-", "*", ">", "+", "•")) or re.match(r"\s*\d+[.)]", p):
            continue
        frases = re.split(r"((?<=[.!?])\s+)", p)
        cambio = False
        while frases and _RE_CIERRE.match(frases[-1]):
            frases = frases[:-2]
            cambio = True
        if cambio:
            partes[i] = "".join(frases).rstrip()
            if not partes[i].strip():
                vaciados.add(i)
    if not vaciados and partes == re.split(r"(\n[ \t]*\n)", cuerpo):
        return texto
    salida = []
    for i in range(0, len(partes), 2):
        if i in vaciados:
            continue
        if salida:
            salida.append(partes[i - 1] if i > 0 else "\n\n")
        salida.append(partes[i])
    out = "".join(salida).rstrip()
    if not out.strip():
        return texto
    return out + ("\n" if "\n" in final else "")


def _quitar_muletillas_inicio(texto: str) -> str:
    def _sust(m):
        # «Es importante destacar que A y que B»: quitar el primer «que» rompería la coordinación.
        if _es_linea_especial(_linea_de(texto, m.end() - 1)):   # títulos y tablas no se tocan
            return m.group(0)
        resto = re.split(r"[.!?\n]", texto[m.end():], maxsplit=1)[0]
        if re.search(r"\b(?:y|e|o|u|ni|pero|sino) que\b|, que\b", resto, re.I):
            return m.group(0)
        return m.group(1) + _capitalizar(m.group(2))
    return _RE_MULETILLA_INICIO.sub(_sust, texto)


def _arreglar_guiones(texto: str) -> str:
    lineas = texto.split("\n")
    for n, linea in enumerate(lineas):
        if not _RE_GUION.search(linea) or not _linea_de_prosa(linea):
            continue
        posiciones = [m for m in _RE_GUION.finditer(linea)]
        nueva, ult, i = [], 0, 0
        while i < len(posiciones):
            m = posiciones[i]
            nueva.append(linea[ult:m.start()])
            # Si hay otra raya en la misma oración, es un inciso: ambas pasan a coma.
            if i + 1 < len(posiciones) and not re.search(r"[.!?;:]", linea[m.end():posiciones[i + 1].start()]):
                nueva.append(", " + linea[m.end():posiciones[i + 1].start()])
                fin2 = posiciones[i + 1].end()
                sig = linea[fin2:fin2 + 1]
                nueva.append(", " if sig and sig not in ".,;:!?)" else "")
                ult = fin2
                i += 2
                continue
            nueva.append(", ")
            ult = m.end()
            i += 1
        nueva.append(linea[ult:])
        lineas[n] = "".join(nueva)
    return "\n".join(lineas)


def _aligerar_negritas(texto: str, minimo: int = 4) -> str:
    """Si hay `minimo` o más negritas dentro de párrafos, las quita de los párrafos. Respeta rótulos al
    inicio de línea ("**Hechos.**"), líneas completas en negrita, títulos y tablas."""
    lineas = texto.split("\n")
    candidatas = []
    for n, linea in enumerate(lineas):
        if _es_linea_especial(linea):
            continue
        for m in _RE_NEGRITA.finditer(linea):
            if _negrita_suelta(linea, m):
                candidatas.append(n)
    if len(candidatas) < minimo:
        return texto
    for n in sorted(set(candidatas)):
        linea = lineas[n]
        lineas[n] = _RE_NEGRITA.sub(lambda m: m.group(1) if _negrita_suelta(linea, m) else m.group(0),
                                    linea)
    return "\n".join(lineas)


def pulir(texto: str) -> str:
    """Correcciones deterministas y seguras de estilo. Idempotente: pulir(pulir(x)) == pulir(x).

    Quita emojis, rellenos inequívocos de apertura («¡Excelente pregunta!») y de cierre («Espero que esta
    información te sea útil»), muletillas al comienzo de una oración («Cabe destacar que …»), el exceso de
    negritas dentro de los párrafos y los guiones largos con espacios usados como pausa. No altera citas
    textuales, código, tablas, enlaces, [F#], [COMPLETAR: …], «(pendiente de verificación)» ni la lista que
    sigue a <<<VERIFICAR>>>. Si el texto trae caracteres internos de uso privado, se devuelve igual."""
    if not isinstance(texto, str) or not texto.strip():
        return texto
    if _PH_A in texto or _PH_B in texto:
        return texto
    cuerpo, guardados = _proteger(texto)
    # Cada regla puede dejar a la vista un caso de otra (quitar un cierre deja otro cierre al final, quitar un
    # emoji deja un «¡Claro!» al comienzo): se repite hasta un punto fijo, así pulir() es idempotente.
    for _ in range(8):
        antes = cuerpo
        cuerpo = _quitar_emojis(cuerpo)
        cuerpo = _quitar_apertura(cuerpo)
        cuerpo = _quitar_muletillas_inicio(cuerpo)
        cuerpo = _quitar_cierre(cuerpo)
        cuerpo = _arreglar_guiones(cuerpo)
        cuerpo = _aligerar_negritas(cuerpo)
        cuerpo = re.sub(r"\n[ \t]*\n(?:[ \t]*\n)+", "\n\n", cuerpo)
        if cuerpo == antes:
            break
    salida = _restaurar(cuerpo, guardados)
    return salida if salida.strip() else texto
