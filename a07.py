"""A07 — Derecho público colombiano. Fuentes: tipos de fuente oficial; los números de ley llevan «verificar vigencia»."""
from perfiles.definiciones import S, VERIFICAR

CLAVES_AREA = ["derecho publico", "entidad publica", "entidad estatal", "consejo de estado", "funcionario publico"]

SUBESPECIALIDADES = [
    S("S01", "constitucional",
      tema="el derecho constitucional (derechos, control de constitucionalidad, precedente y acciones "
           "constitucionales distintas de la tutela)",
      objeto="Cubre el alcance de los derechos, el bloque de constitucionalidad, la acción pública de "
             "inconstitucionalidad, el valor del precedente y las acciones popular, de grupo y de cumplimiento.",
      entradas=["la norma, el acto o la situación que se considera contraria a la Constitución",
                "el derecho o principio constitucional comprometido", "quién resulta afectado y desde cuándo"],
      fuentes=["Constitución Política de 1991 y tratados de derechos humanos ratificados",
               "Decreto 2067 de 1991, juicios ante la Corte Constitucional " + VERIFICAR,
               "Ley 472 de 1998, acciones populares y de grupo, y Ley 393 de 1997, acción de cumplimiento "
               + VERIFICAR,
               "relatoría de la Corte Constitucional",
               "SUIN-Juriscol para el texto de la norma examinada y las decisiones sobre ella"],
      entregable="concepto constitucional con la norma o el acto examinado, el parámetro de control, el cargo o "
                 "problema, el precedente aplicable y la acción procedente",
      riesgos=["Atribuir efectos generales a una decisión de revisión de tutela o tratar un comentario incidental "
               "como regla.",
               "Demandar una norma sobre la que ya existe cosa juzgada constitucional sin advertirlo."],
      comprobaciones=["El precedente citado distingue tipo de decisión, problema resuelto y regla de decisión.",
                      "Se verifica si la norma ya fue examinada y con qué alcance, o se declara pendiente."],
      extraer="norma o acto cuestionado, derecho invocado, sujetos afectados, decisiones previas sobre la misma "
              "norma y cargos posibles",
      vigencia="el texto de la norma examinada con sus modificaciones y las decisiones de constitucionalidad que "
               "la condicionan o la retiraron",
      preguntas="¿qué derecho o principio constitucional está en juego y con qué alcance?; ¿existe cosa juzgada o "
                "precedente que resuelva el punto?",
      opciones="acción pública de inconstitucionalidad, excepción de inconstitucionalidad en el caso concreto, "
               "acción popular o de grupo, o acción de cumplimiento",
      claves=["inconstitucional", "constitucionalidad", "accion popular", "accion de grupo", "accion de "
              "cumplimiento", "derechos colectivos", "bloque de constitucionalidad", "exequible", "inexequible",
              "excepcion de inconstitucionalidad", "corte constitucional", "derecho fundamental"]),
    S("S02", "administrativo",
      tema="el derecho administrativo (acto administrativo, procedimiento, recursos, medios de control y "
           "responsabilidad del Estado)",
      objeto="Cubre la formación y la notificación del acto, los recursos en sede administrativa, el silencio y "
             "la revocatoria directa, los medios de control con su caducidad y la responsabilidad patrimonial del "
             "Estado.",
      entradas=["el acto, la omisión o el hecho de la administración, con su fecha",
                "la fecha y la forma en que se notificó o se conoció", "los recursos ya presentados y su respuesta"],
      fuentes=["Constitución Política (función administrativa y responsabilidad patrimonial del Estado)",
               "Código de Procedimiento Administrativo y de lo Contencioso Administrativo, Ley 1437 de 2011, con "
               "la reforma de la Ley 2080 de 2021 " + VERIFICAR,
               "relatoría del Consejo de Estado",
               "Gestor Normativo de la Función Pública",
               "SUIN-Juriscol y Secretaría del Senado para el texto vigente"],
      entregable="ruta administrativa con la actuación identificada, los recursos procedentes, el medio de "
                 "control, el cómputo de la caducidad y el requisito de conciliación previa",
      riesgos=["Escoger el medio de control por el nombre que le dio el usuario y no por el origen del daño.",
               "Contar la caducidad desde una fecha distinta a la notificación, la ejecución o el conocimiento "
               "del hecho."],
      comprobaciones=["La caducidad indica el medio de control, la fecha desde la que corre y la fuente del "
                      "término.",
                      "Se establece si los recursos eran obligatorios y si quedó agotada la actuación "
                      "administrativa."],
      extraer="autoridad que actuó, tipo y fecha del acto, forma y fecha de notificación, recursos interpuestos, "
              "respuesta o silencio y daño alegado",
      vigencia="la versión del código vigente en la fecha de la actuación y las reglas de transición de su "
               "reforma",
      preguntas="¿la actuación es un acto, un hecho, una omisión o un contrato?; ¿la acción está en término y con "
                "los requisitos previos cumplidos?",
      opciones="recursos de reposición y apelación, revocatoria directa, nulidad y restablecimiento del derecho o "
               "reparación directa",
      claves=["acto administrativo", "resolucion de la", "nulidad y restablecimiento", "reparacion directa",
              "cpaca$", "recurso de reposicion", "silencio administrativo", "revocatoria directa", "alcaldia",
              "gobernacion", "comparendo", "multa de transito", "sancion administrativa", "caducidad del medio de "
              "control", "contencioso administrativo"]),
    S("S03", "contratación estatal",
      tema="la contratación estatal (selección del contratista, ejecución, incumplimiento, liquidación y "
           "controversias)",
      objeto="Cubre las modalidades de selección, los requisitos habilitantes y la evaluación, la ejecución con "
             "sus modificaciones, las multas y la caducidad, el equilibrio económico, la liquidación y el medio "
             "de control contractual.",
      entradas=["el proceso o contrato, la entidad y la etapa en que está",
                "el pliego de condiciones o el contrato con sus modificaciones",
                "el hecho discutido (rechazo, incumplimiento, multa, desequilibrio) y su fecha"],
      fuentes=["Ley 80 de 1993 y Ley 1150 de 2007, estatuto de contratación " + VERIFICAR,
               "Decreto 1082 de 2015, reglamentario del sector Planeación " + VERIFICAR,
               "Ley 1474 de 2011 (imposición de multas y declaratoria de incumplimiento) " + VERIFICAR,
               "conceptos, manuales y documentos tipo de Colombia Compra Eficiente y expediente en SECOP",
               "relatoría de la Sección Tercera del Consejo de Estado"],
      entregable="análisis contractual con la modalidad y su fundamento, la regla del pliego o del contrato en "
                 "discusión, el trámite seguido, la caducidad y la pretensión viable",
      riesgos=["Dar por subsanable un requisito que otorga puntaje, o por insubsanable uno habilitante.",
               "Aplicar el estatuto general a una entidad con régimen especial de contratación."],
      comprobaciones=["Se identifica el régimen de contratación de la entidad antes de aplicar cualquier regla.",
                      "Cada regla del pliego o cláusula invocada se cita con su numeral del documento a la vista."],
      extraer="entidad y régimen, modalidad, cronograma, requisitos habilitantes y de puntaje, plazo, valor, "
              "garantías, otrosíes, actas y requerimientos",
      vigencia="las normas y el reglamento vigentes al abrirse el proceso de selección, que rigen el contrato, y "
               "el pliego con sus adendas",
      preguntas="¿la entidad aplicó la modalidad y las reglas del pliego que correspondían?; ¿el incumplimiento "
                "es imputable y se respetó el debido proceso para sancionarlo?",
      opciones="observaciones al pliego o a la evaluación, solicitud de restablecimiento del equilibrio, "
               "arreglo directo o medio de control de controversias contractuales",
      claves=["contratacion estatal", "licitacion", "secop", "pliego de condiciones", "contrato estatal",
              "contratista del estado", "seleccion abreviada", "minima cuantia", "contratacion directa",
              "liquidacion del contrato estatal", "equilibrio economico", "interventoria", "adjudicacion",
              "oferente", "proponente"]),
    S("S04", "disciplinario",
      tema="el derecho disciplinario (falta, ilicitud sustancial, culpabilidad, procedimiento y sanción)",
      objeto="Cubre los destinatarios de la ley disciplinaria, la tipicidad de la falta, la ilicitud sustancial, "
             "el dolo y la culpa, las etapas del proceso con la separación entre instrucción y juzgamiento, las "
             "sanciones y la prescripción.",
      entradas=["la conducta atribuida, con fecha, cargo y funciones de quien la realizó",
                "la etapa del proceso y la última decisión notificada", "las pruebas que obran y las que se "
                "quieren pedir"],
      fuentes=["Constitución Política (debido proceso y función pública)",
               "Ley 1952 de 2019, Código General Disciplinario, con la reforma de la Ley 2094 de 2021 " + VERIFICAR,
               "Ley 1123 de 2007, Código Disciplinario del Abogado " + VERIFICAR,
               "doctrina y decisiones de la Procuraduría General de la Nación y relatoría de la Comisión Nacional "
               "de Disciplina Judicial",
               "relatoría de la Sección Segunda del Consejo de Estado"],
      entregable="análisis disciplinario con la falta imputada, su tipicidad, la ilicitud sustancial, la forma de "
                 "culpabilidad, la etapa procesal y los argumentos de defensa o de cargo",
      riesgos=["Aplicar el código vigente hoy a una conducta anterior sin revisar favorabilidad y transición.",
               "Confundir el incumplimiento formal de un deber con la afectación sustancial que exige la falta."],
      comprobaciones=["La falta se adecua a un tipo disciplinario citado con su norma y su clasificación.",
                      "Se indica el término de prescripción o caducidad y desde cuándo corre."],
      extraer="cargo y funciones, deber o prohibición presuntamente infringido, fechas de la conducta, decisiones "
              "del proceso, pruebas y descargos",
      vigencia="el régimen disciplinario vigente en la fecha de la conducta, el que rige el procedimiento en "
               "curso y las reglas de transición entre ambos",
      preguntas="¿la conducta es típica, sustancialmente ilícita y culpable?; ¿el proceso respetó competencia, "
                "etapas y términos?",
      opciones="versión libre y solicitud de archivo, descargos con pruebas, nulidad por violación del debido "
               "proceso o recursos contra el fallo",
      claves=["disciplinario", "procuraduria", "falta disciplinaria", "pliego de cargos", "control interno "
              "disciplinario", "proceso disciplinario", "suspension del cargo", "destitucion", "inhabilidad general",
              "queja disciplinaria", "personeria", "disciplina judicial"]),
    S("S05", "responsabilidad fiscal",
      tema="la responsabilidad fiscal (gestión fiscal, daño patrimonial al Estado, culpa grave y proceso ante la "
           "contraloría)",
      objeto="Cubre quién es gestor fiscal, el daño patrimonial al Estado y su cuantificación, la conducta dolosa "
             "o gravemente culposa, el nexo causal, las etapas del proceso ordinario y verbal y la vinculación del "
             "garante.",
      entradas=["el hallazgo o el auto que origina la actuación, con su fecha",
                "el cargo o contrato de la persona vinculada y los recursos que manejaba",
                "los soportes de la gestión cuestionada y del valor del daño"],
      fuentes=["Constitución Política (control fiscal), con el Acto Legislativo 04 de 2019 " + VERIFICAR,
               "Ley 610 de 2000, proceso de responsabilidad fiscal " + VERIFICAR,
               "Ley 1474 de 2011 (procedimiento verbal) y Decreto Ley 403 de 2020 " + VERIFICAR,
               "conceptos y decisiones de la Contraloría General de la República",
               "relatoría del Consejo de Estado"],
      entregable="análisis de responsabilidad fiscal con la calidad de gestor, el daño cuantificado y su soporte, "
                 "la conducta, el nexo, la etapa del proceso y la defensa o imputación posible",
      riesgos=["Imputar responsabilidad a quien no tenía a su cargo la gestión de los recursos.",
               "Tratar como daño cierto una irregularidad administrativa sin pérdida patrimonial demostrada."],
      comprobaciones=["El daño se expresa en una cifra con su soporte y su fecha, o se declara no cuantificado.",
                      "Se establece la caducidad de la acción fiscal y la prescripción con sus fechas de partida."],
      extraer="entidad afectada, recursos comprometidos, hechos y fechas, valor del presunto daño, personas "
              "vinculadas, pólizas y decisiones del proceso",
      vigencia="las reglas de caducidad, prescripción y procedimiento vigentes en la fecha de los hechos y las "
               "que introdujo la reforma al control fiscal",
      preguntas="¿hay daño patrimonial cierto y cuantificado?; ¿la persona era gestor fiscal y obró con dolo o "
                "culpa grave?",
      opciones="exposición libre con soportes, argumentos de defensa frente a la imputación, resarcimiento con "
               "cesación de la acción o recursos contra el fallo",
      claves=["responsabilidad fiscal", "contraloria", "detrimento patrimonial", "hallazgo fiscal", "gestor fiscal",
              "proceso fiscal", "auto de imputacion fiscal", "dano patrimonial al estado", "juicio fiscal",
              "boletin de responsables fiscales"]),
    S("S06", "tributario",
      tema="el derecho tributario (obligación, declaración, fiscalización, discusión y sanciones)",
      objeto="Cubre los elementos del tributo, la declaración y su firmeza, los requerimientos y liquidaciones "
             "oficiales, el recurso de reconsideración, las sanciones con su reducción y la demanda ante la "
             "jurisdicción.",
      entradas=["el impuesto, el período y la autoridad (DIAN o entidad territorial)",
                "el acto recibido (emplazamiento, requerimiento, liquidación o resolución) y su fecha de "
                "notificación", "la declaración presentada y sus soportes"],
      fuentes=["Estatuto Tributario, Decreto 624 de 1989, con sus reformas " + VERIFICAR,
               "Decreto 1625 de 2016, reglamentario en materia tributaria " + VERIFICAR,
               "doctrina oficial, conceptos y resoluciones de la DIAN (incluido el valor de la UVT del año)",
               "estatuto de rentas de la entidad territorial cuando el tributo es local",
               "relatoría de la Sección Cuarta del Consejo de Estado"],
      herramientas={"calculadora_liquidaciones": "F07 F08"},
      entregable="análisis tributario con el hecho generador, la etapa de la discusión, el término para "
                 "responder, la sanción aplicable con su reducción y la respuesta o recurso que procede",
      riesgos=["Usar la tarifa, la UVT o la tasa de interés de un año distinto al del período discutido.",
               "Dejar vencer el término para responder el requerimiento o interponer el recurso."],
      comprobaciones=["Cada término indica el acto que lo activa, su fecha de notificación y la norma que lo "
                      "fija.",
                      "Las cifras (UVT, tarifas, intereses) citan el acto oficial y el año de donde salen."],
      extraer="impuesto y período, fechas de presentación y de notificación, valores declarados y propuestos, "
              "sanciones, y firmeza de la declaración",
      vigencia="la norma sustancial vigente en el período gravable discutido y la norma de procedimiento vigente "
               "al iniciarse cada término",
      preguntas="¿la declaración está en firme o la administración actuó en tiempo?; ¿la glosa y la sanción "
                "tienen sustento normativo y probatorio?",
      opciones="corregir la declaración con sanción reducida, responder el requerimiento, interponer recurso de "
               "reconsideración o demandar la liquidación",
      claves=["tributario", "dian$", "impuesto", "declaracion de renta", "iva$", "retencion en la fuente",
              "requerimiento especial", "liquidacion oficial", "sancion por extemporaneidad", "estatuto tributario",
              "recurso de reconsideracion", "predial", "industria y comercio", "uvt$", "emplazamiento para "
              "declarar"]),
    S("S07", "aduanero",
      tema="el derecho aduanero (importación y exportación, clasificación, valoración, aprehensión y sanciones)",
      objeto="Cubre las obligaciones del importador, exportador y declarante, los regímenes aduaneros, la "
             "clasificación arancelaria, la valoración y el origen, la aprehensión y el decomiso, y las "
             "liquidaciones oficiales y sanciones.",
      entradas=["la mercancía, la operación y el régimen declarado",
                "la declaración y sus documentos soporte (factura, documento de transporte, certificado de origen)",
                "el acto de la autoridad aduanera y su fecha de notificación"],
      fuentes=["Decreto 1165 de 2019, régimen de aduanas, y su resolución reglamentaria de la DIAN " + VERIFICAR,
               "régimen sancionatorio y de decomiso aduanero vigente " + VERIFICAR,
               "Arancel de Aduanas vigente y resoluciones de clasificación arancelaria de la DIAN",
               "Acuerdo sobre Valoración en Aduana de la OMC y normas andinas de valoración",
               "conceptos de la DIAN y relatoría del Consejo de Estado (secciones Primera y Cuarta)"],
      entregable="análisis aduanero con la operación y su régimen, la causal invocada por la autoridad, la prueba "
                 "documental, el término de respuesta y la defensa o la legalización posible",
      riesgos=["Citar un régimen sancionatorio que fue reemplazado o que ha sido retirado del ordenamiento.",
               "Discutir la clasificación arancelaria sin la ficha técnica ni la descripción mínima de la "
               "mercancía."],
      comprobaciones=["La norma sancionatoria citada se verifica como vigente en la fecha de los hechos o queda "
                      "pendiente.",
                      "La subpartida y el valor se apoyan en documentos identificados de la operación."],
      extraer="importador y declarante, subpartida, valor y origen declarados, documentos soporte, fecha de "
              "levante o de aprehensión y causal invocada",
      vigencia="el régimen aduanero y sancionatorio vigente en la fecha de la declaración o de la infracción y "
               "el arancel aplicable ese día",
      preguntas="¿la mercancía estaba amparada y correctamente descrita?; ¿la causal de aprehensión o la sanción "
                "tienen soporte y se impusieron en término?",
      opciones="legalización con pago de rescate, objeción a la aprehensión, respuesta al requerimiento "
               "aduanero o recurso de reconsideración",
      claves=["aduana", "aduanero", "importacion", "exportacion", "aprehension de mercancia", "decomiso",
              "arancel", "subpartida", "declaracion de importacion", "contrabando", "zona franca", "levante",
              "agencia de aduanas", "valoracion aduanera"]),
    S("S08", "empleo público",
      tema="el empleo público (carrera administrativa, concursos, provisionalidad, situaciones administrativas y "
           "retiro)",
      objeto="Cubre las clases de empleo y de vinculación, el concurso de méritos y la lista de elegibles, el "
             "encargo y la provisionalidad, las situaciones administrativas, la evaluación del desempeño y las "
             "causales de retiro.",
      entradas=["la entidad, el empleo y la forma de vinculación de la persona",
                "el acto discutido (nombramiento, insubsistencia, exclusión del concurso, traslado) y su fecha",
                "la convocatoria o el manual de funciones aplicable"],
      fuentes=["Constitución Política (función pública y mérito)",
               "Ley 909 de 2004, empleo público y carrera administrativa " + VERIFICAR,
               "Decreto 1083 de 2015, reglamentario del sector Función Pública " + VERIFICAR,
               "acuerdos y criterios de la Comisión Nacional del Servicio Civil y conceptos del Gestor Normativo "
               "de la Función Pública",
               "relatoría de la Sección Segunda del Consejo de Estado"],
      entregable="análisis de empleo público con la naturaleza del empleo, el derecho de permanencia o de acceso "
                 "que se discute, el acto, su motivación y la vía de reclamación con su término",
      riesgos=["Reconocer estabilidad de carrera a un provisional o negarle la motivación del retiro.",
               "Aplicar el régimen general a una entidad con sistema específico o especial de carrera."],
      comprobaciones=["Se identifica el sistema de carrera (general, específico o especial) antes de aplicar "
                      "reglas.",
                      "El acto de retiro o de exclusión se examina frente a su motivación y a la regla de la "
                      "convocatoria."],
      extraer="entidad y sistema de carrera, denominación, código y grado del empleo, tipo de vinculación, fechas "
              "de posesión y de retiro, y reglas de la convocatoria",
      vigencia="las reglas de la convocatoria, que son la ley del concurso, y las normas de carrera vigentes en "
               "la fecha del acto discutido",
      preguntas="¿qué clase de empleo y de vinculación tiene la persona?; ¿el acto respetó el mérito, la "
                "motivación y el debido proceso?",
      opciones="reclamación ante la entidad o la comisión del servicio civil, acción de tutela si hay perjuicio "
               "irremediable o nulidad y restablecimiento del derecho",
      claves=["empleo publico", "carrera administrativa", "concurso de meritos", "cnsc$", "lista de elegibles",
              "provisionalidad", "nombramiento provisional", "insubsistencia", "libre nombramiento", "servidor publico",
              "funcion publica", "nombramiento en encargo", "manual de funciones", "periodo de prueba en carrera"]),
    S("S09", "electoral",
      tema="el derecho electoral (inscripción, inhabilidades, escrutinio, nulidad electoral y pérdida de "
           "investidura)",
      objeto="Cubre el derecho a elegir y ser elegido, la inscripción y la revocatoria de candidaturas, las "
             "inhabilidades e incompatibilidades, el escrutinio y sus reclamaciones, la nulidad electoral y los "
             "mecanismos de participación.",
      entradas=["la elección o el nombramiento, la fecha y la corporación o el cargo",
                "el candidato o elegido y la causal que se discute", "el acto de declaratoria de elección o de "
                "inscripción y su fecha"],
      fuentes=["Constitución Política (derechos políticos, organización electoral e inhabilidades)",
               "Código Electoral, Decreto 2241 de 1986 " + VERIFICAR,
               "Ley 1475 de 2011 y Ley 130 de 1994, partidos y procesos electorales " + VERIFICAR,
               "Ley 1437 de 2011 (medio de control de nulidad electoral) " + VERIFICAR,
               "resoluciones del Consejo Nacional Electoral, circulares de la Registraduría y relatoría de la "
               "Sección Quinta del Consejo de Estado"],
      entregable="análisis electoral con la causal invocada, los hechos y fechas que la configuran, la prueba "
                 "disponible, la autoridad competente y el término para actuar",
      riesgos=["Dejar vencer el término muy breve de la nulidad electoral o de la reclamación en el escrutinio.",
               "Aplicar una inhabilidad por analogía cuando su interpretación es restrictiva."],
      comprobaciones=["La inhabilidad o causal se cita con su norma y se contrasta con fechas probadas.",
                      "El término para demandar o reclamar indica el acto desde el que corre y su fecha."],
      extraer="cargo o corporación, fecha de inscripción y de elección, causal alegada, parentescos, contratos o "
              "cargos previos con sus fechas, y actas de escrutinio",
      vigencia="las normas electorales vigentes en la fecha de la inscripción y de la elección, incluida "
               "cualquier reforma que no hubiera entrado a regir",
      preguntas="¿se configura la inhabilidad o la irregularidad con los hechos probados?; ¿la reclamación o la "
                "demanda está en término y ante la autoridad competente?",
      opciones="solicitud de revocatoria de la inscripción, reclamación ante la comisión escrutadora, nulidad "
               "electoral o pérdida de investidura",
      claves=["electoral", "elecciones", "candidato", "inhabilidad para ser elegido", "registraduria",
              "consejo nacional electoral", "nulidad electoral", "escrutinio", "perdida de investidura",
              "revocatoria del mandato", "inscripcion de candidatura", "doble militancia", "jurado de votacion"]),
    S("S10", "ambiental",
      tema="el derecho ambiental (licencias y permisos, sancionatorio ambiental, participación y daño ambiental)",
      objeto="Cubre las autoridades ambientales y sus competencias, la licencia ambiental y los permisos de uso "
             "de recursos, el procedimiento sancionatorio con sus medidas preventivas, la consulta previa y las "
             "acciones de defensa del ambiente.",
      entradas=["el proyecto, la obra o la actividad y dónde se desarrolla",
                "la autoridad ambiental que actúa y el acto expedido, con su fecha",
                "los permisos o la licencia existentes y los hechos de la presunta infracción"],
      fuentes=["Constitución Política (ambiente sano y función ecológica de la propiedad)",
               "Ley 99 de 1993 y Decreto Ley 2811 de 1974, Código de Recursos Naturales " + VERIFICAR,
               "Decreto 1076 de 2015, reglamentario del sector Ambiente " + VERIFICAR,
               "Ley 1333 de 2009, procedimiento sancionatorio ambiental, con sus reformas " + VERIFICAR,
               "actos de la ANLA y de la corporación autónoma regional competente, y relatorías del Consejo de "
               "Estado y de la Corte Constitucional"],
      entregable="análisis ambiental con la autoridad competente, el instrumento exigible (licencia, permiso o "
                 "plan), la infracción imputada, la etapa del sancionatorio y la actuación que procede",
      riesgos=["Dar por competente a la autoridad equivocada entre la nacional, la regional y la urbana.",
               "Olvidar que en el sancionatorio ambiental la culpa o el dolo se presumen y hay que desvirtuarlos."],
      comprobaciones=["Se identifica qué autoridad es competente y por qué criterio (actividad, tamaño o lugar).",
                      "Cada infracción imputada se liga a la norma o a la obligación del permiso que se habría "
                      "incumplido."],
      extraer="actividad y ubicación, autoridad, licencia o permisos con sus obligaciones, medida preventiva, "
              "cargos formulados y fechas de cada actuación",
      vigencia="la norma ambiental y el reglamento vigentes en la fecha de la actividad y las obligaciones del "
               "permiso o la licencia tal como estaban en ese momento",
      preguntas="¿la actividad requería licencia o permiso y lo tenía?; ¿la infracción y la sanción propuesta "
                "tienen soporte técnico y jurídico?",
      opciones="solicitar o modificar el instrumento ambiental, presentar descargos con prueba técnica, pedir el "
               "levantamiento de la medida preventiva o acudir a la acción popular",
      claves=["ambiental", "licencia ambiental", "car$", "anla$", "corporacion autonoma", "sancionatorio ambiental",
              "vertimiento", "tala$", "tala de arboles", "permiso ambiental", "contaminacion", "consulta previa", "medida preventiva "
              "ambiental", "dano ambiental", "mineria"]),
]
