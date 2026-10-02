"""A10 — Procedimiento, litigación y gestión jurídica. Fuentes: tipos de fuente oficial; los números de ley llevan
«verificar vigencia». Ningún perfil da una fecha de vencimiento como definitiva: el cómputo depende del
expediente, del calendario judicial y de una calculadora que todavía es una propuesta.
"""
from perfiles.definiciones import S, VERIFICAR

CLAVES_AREA = ["juzgado", "proceso judicial", "litigio", "demanda", "expediente", "procesal"]

SUBESPECIALIDADES = [
    S("S01", "competencia",
      tema="la jurisdicción y la competencia (a qué juez o autoridad corresponde el asunto y por qué factor)",
      objeto="Cubre la jurisdicción que conoce del asunto, los factores objetivo, subjetivo, territorial, "
             "funcional y de conexión, la cuantía, la clase de proceso, el pacto arbitral y los conflictos de "
             "competencia.",
      entradas=["la pretensión y los hechos esenciales, con las partes y su naturaleza (persona, empresa, "
                "entidad pública)", "el valor aproximado de lo que se reclama",
                "los domicilios de las partes y el lugar de los hechos o del cumplimiento"],
      fuentes=["Código General del Proceso, Ley 1564 de 2012 (reglas de competencia y cuantía) " + VERIFICAR,
               "Código de Procedimiento Administrativo y de lo Contencioso Administrativo, Ley 1437 de 2011, con "
               "la reforma de la Ley 2080 de 2021 " + VERIFICAR,
               "Código Procesal del Trabajo y de la Seguridad Social " + VERIFICAR,
               "Ley 270 de 1996, Estatutaria de la Administración de Justicia, y Ley 1563 de 2012, arbitraje "
               + VERIFICAR,
               "acuerdos del Consejo Superior de la Judicatura sobre el mapa judicial, en la Rama Judicial"],
      entregable="ficha de competencia con la jurisdicción, cada factor aplicado al caso, la cuantía y su "
                 "cálculo, la clase de proceso y los datos que faltan para afirmarla",
      riesgos=["Afirmar una competencia definitiva sin haber comprobado cada factor con los datos del caso.",
               "Determinar la cuantía con los salarios mínimos de un año distinto al de la presentación."],
      comprobaciones=["Cada factor de competencia se aplica con un dato del caso o se marca como pendiente.",
                      "La cuantía muestra qué pretensiones suma y con qué valor de referencia del año de la "
                      "demanda."],
      extraer="naturaleza de las partes, domicilios, lugar de los hechos y del cumplimiento, pretensiones con su "
              "valor, cláusula compromisoria y procesos relacionados",
      vigencia="las reglas de competencia vigentes al presentarse la demanda y el salario mínimo de ese año "
               "para fijar la cuantía",
      preguntas="¿qué jurisdicción y qué juez conocen del asunto?; ¿qué clase de proceso corresponde por "
                "naturaleza y cuantía?",
      opciones="juez civil municipal o del circuito, juez de familia, juez laboral, juez administrativo o "
               "tribunal de arbitramento según los factores",
      claves=["competencia", "juez competente", "a que juez", "ante que juez", "jurisdiccion", "cuantia",
              "donde demando", "donde debo demandar", "factor territorial", "conflicto de competencia",
              "que juzgado", "clausula compromisoria", "minima cuantia judicial", "reparto"]),
    S("S02", "términos",
      tema="los términos procesales (cómputo de plazos, notificaciones, ejecutoria, caducidad y prescripción)",
      objeto="Cubre cómo se cuenta un término según su unidad y su régimen, desde cuándo corre según la "
             "notificación, qué lo suspende o interrumpe, la vacancia judicial y la diferencia entre caducidad y "
             "prescripción.",
      entradas=["la actuación o la decisión y el régimen procesal que la rige",
                "la fecha y la forma exactas de la notificación o del hecho que inicia el término",
                "los eventos que pueden alterar el cómputo (vacancia, paros, suspensiones, recursos)"],
      fuentes=["Código General del Proceso, Ley 1564 de 2012 (cómputo de términos y notificaciones) " + VERIFICAR,
               "Ley 2213 de 2022 (notificaciones por mensaje de datos) " + VERIFICAR,
               "Código de Régimen Político y Municipal, Ley 4 de 1913 (cómputo de plazos de días, meses y años) "
               + VERIFICAR,
               "Ley 270 de 1996 (vacancia judicial) y acuerdos del Consejo Superior de la Judicatura sobre "
               "suspensión de términos, en la Rama Judicial " + VERIFICAR,
               "norma especial que fija el término concreto, en SUIN-Juriscol o en la Secretaría del Senado"],
      herramientas={"calculadora_terminos": "F05 F07 F08"},
      entregable="cronología del término con la norma que lo fija, la fecha de inicio y su soporte, los días "
                 "descontados con su causa, la fecha calculada y los supuestos de los que depende",
      riesgos=["Entregar una fecha de vencimiento como definitiva cuando falta un dato esencial del cómputo.",
               "Contar en días calendario un término de días hábiles, o ignorar una suspensión de términos."],
      comprobaciones=["La fecha calculada va acompañada de la norma, la fecha de inicio, los días excluidos y "
                      "los supuestos.",
                      "Si falta la fecha o la forma de notificación, el perfil se abstiene de dar una fecha "
                      "definitiva."],
      extraer="decisión o hecho que inicia el término, forma y fecha de notificación, unidad del término, "
              "festivos y vacancia en el intervalo, y actuaciones que suspenden o interrumpen",
      vigencia="la norma que fijaba el término cuando empezó a correr y el calendario judicial del año, con sus "
               "suspensiones",
      preguntas="¿desde qué fecha corre el término y en qué unidad se cuenta?; ¿hubo suspensión, interrupción o "
                "vacancia dentro del intervalo?",
      opciones="actuar de inmediato dentro del término más corto posible, pedir constancia secretarial del "
               "cómputo o solicitar la nulidad por indebida notificación",
      claves=["terminos$", "termino para", "termino legal", "termino de", "plazo", "cuantos dias tengo", "cuando vence", "hasta cuando puedo",
              "dias habiles", "vacancia judicial", "ejecutoria", "caducidad", "prescripcion", "vence el termino",
              "computo de terminos", "me notificaron el"]),
    S("S03", "prueba",
      tema="la prueba en el proceso (carga, medios, oportunidad, contradicción y matriz probatoria)",
      objeto="Cubre la carga de la prueba, los medios admisibles y su oportunidad, la aportación y el decreto, "
             "la contradicción del dictamen y de los documentos, y la relación de cada hecho con su soporte.",
      entradas=["los hechos que la parte debe demostrar y las pretensiones o excepciones",
                "los documentos y demás elementos que ya tiene", "la etapa del proceso o si aún no se ha "
                "demandado"],
      fuentes=["Código General del Proceso, Ley 1564 de 2012 (régimen probatorio) " + VERIFICAR,
               "Código de Procedimiento Administrativo y de lo Contencioso Administrativo, Ley 1437 de 2011 "
               "(pruebas) " + VERIFICAR,
               "Ley 527 de 1999, mensajes de datos como prueba " + VERIFICAR,
               "relatoría de la Sala de Casación Civil de la Corte Suprema de Justicia",
               "relatoría del Consejo de Estado y de la Corte Constitucional sobre debido proceso probatorio"],
      entregable="matriz probatoria con cada hecho, quién tiene la carga de probarlo, el medio disponible, su "
                 "estado (afirmación, indicio o acreditado), las contradicciones y lo que falta conseguir",
      riesgos=["Tratar una afirmación del usuario como hecho acreditado.",
               "Dejar pasar la oportunidad de aportar o pedir una prueba, que por regla no se repite."],
      comprobaciones=["Cada hecho se clasifica como afirmación del usuario, indicio o hecho con soporte.",
                      "Cada prueba indica la oportunidad procesal para aportarla o pedirla."],
      extraer="hechos relevantes, documentos con fecha y autor, testigos y lo que le consta a cada uno, "
              "dictámenes, contradicciones entre documentos y vacíos",
      vigencia="las reglas probatorias del estatuto que rige el proceso y las oportunidades de la etapa en que "
               "se encuentra",
      preguntas="¿qué hechos tienen soporte y cuáles son solo afirmación?; ¿qué prueba falta y cuándo puede "
                "pedirse o aportarse?",
      opciones="aportar el documento con la demanda o la contestación, pedir el testimonio o el dictamen, "
               "solicitar exhibición o practicar prueba extraprocesal",
      claves=["matriz probatoria", "carga de la prueba", "pruebas para la demanda", "dictamen pericial",
              "prueba documental", "testimonio", "que pruebas necesito", "tacha de falsedad",
              "prueba extraprocesal", "declaracion de parte", "como pruebo", "inspeccion judicial"]),
    S("S04", "medidas cautelares",
      tema="las medidas cautelares (embargo, secuestro, inscripción de la demanda, innominadas y suspensión "
           "provisional)",
      objeto="Cubre las medidas procedentes según la clase de proceso, sus requisitos de apariencia de buen "
             "derecho y peligro en la demora, la caución, la práctica, la oposición y el levantamiento.",
      entradas=["la clase de proceso y la pretensión principal", "los bienes o la situación que se quiere "
                "asegurar, con su identificación", "la urgencia o el riesgo concreto de que la sentencia quede "
                "sin efecto"],
      fuentes=["Código General del Proceso, Ley 1564 de 2012 (medidas cautelares en procesos declarativos y "
               "ejecutivos) " + VERIFICAR,
               "Código de Procedimiento Administrativo y de lo Contencioso Administrativo, Ley 1437 de 2011 "
               "(medidas cautelares) " + VERIFICAR,
               "relatoría de la Sala de Casación Civil de la Corte Suprema de Justicia",
               "relatoría del Consejo de Estado",
               "registros públicos donde se inscribe la medida (instrumentos públicos, cámara de comercio, "
               "tránsito)"],
      entregable="solicitud cautelar con la medida precisa, su fundamento según la clase de proceso, los bienes "
                 "identificados, la caución y la justificación de necesidad y proporcionalidad",
      riesgos=["Pedir un embargo en un proceso declarativo donde solo procede la inscripción de la demanda.",
               "Solicitar la medida sobre un bien inembargable o sin identificarlo de forma suficiente."],
      comprobaciones=["La medida solicitada corresponde a las que la ley admite para esa clase de proceso.",
                      "Cada bien se identifica con matrícula, placa, cuenta o registro, o se indica el dato que "
                      "falta."],
      extraer="clase de proceso, pretensión, bienes del demandado con su identificación, gravámenes previos, "
              "valor del crédito y caución exigible",
      vigencia="las reglas cautelares del estatuto procesal aplicable y los límites de inembargabilidad vigentes",
      preguntas="¿qué medida procede en esta clase de proceso?; ¿se acreditan la apariencia de buen derecho y "
                "el peligro en la demora?",
      opciones="embargo y secuestro, inscripción de la demanda, medida innominada, suspensión provisional del "
               "acto o caución para impedir o levantar la medida",
      claves=["medida cautelar", "embargo", "embargar", "secuestro de bienes", "inscripcion de la demanda",
              "suspension provisional", "me embargaron", "levantar el embargo", "caucion", "medida innominada",
              "inembargable", "desembargo"]),
    S("S05", "tutela",
      tema="la acción de tutela (procedencia, competencia, contenido, impugnación, cumplimiento y desacato)",
      objeto="Cubre la legitimación, la subsidiariedad y la inmediatez, el reparto, el contenido de la "
             "solicitud y la medida provisional, la impugnación, el cumplimiento del fallo, el desacato y la "
             "tutela contra providencias.",
      entradas=["el derecho fundamental afectado y la acción u omisión que lo afecta, con fechas",
                "quién vulnera y qué se le ha pedido antes", "los otros medios de defensa disponibles y por qué "
                "no bastan"],
      fuentes=["Constitución Política (acción de tutela y derechos fundamentales)",
               "Decreto 2591 de 1991, reglamentario de la acción de tutela " + VERIFICAR,
               "Decreto 1069 de 2015, reglas de reparto de la acción de tutela, con sus modificaciones "
               + VERIFICAR,
               "relatoría de la Corte Constitucional",
               "consulta de procesos de la Rama Judicial para el estado de la tutela y del desacato"],
      entregable="borrador de tutela o de impugnación con los hechos numerados, el derecho vulnerado, el examen "
                 "de subsidiariedad e inmediatez, la pretensión concreta y el juramento de no temeridad",
      riesgos=["Presentar la tutela cuando existe otro medio eficaz sin explicar el perjuicio irremediable.",
               "Presentar dos tutelas por los mismos hechos: es temeridad y tiene consecuencias."],
      comprobaciones=["El escrito examina por separado legitimación, subsidiariedad e inmediatez con hechos del "
                      "caso.",
                      "La pretensión es una orden concreta y posible, dirigida a quien puede cumplirla."],
      extraer="accionante y accionado, hechos con fecha, derecho invocado, peticiones previas y respuestas, "
              "otros medios de defensa, pruebas y fallos anteriores",
      vigencia="las reglas de reparto vigentes al presentar la tutela y el precedente constitucional vigente "
               "sobre el derecho invocado",
      preguntas="¿la tutela es procedente por subsidiariedad e inmediatez?; ¿qué orden concreta protege el "
                "derecho?",
      opciones="acción de tutela con medida provisional, impugnación del fallo, solicitud de cumplimiento, "
               "incidente de desacato o el medio ordinario si la tutela no procede",
      claves=["tutela", "accion de tutela", "derecho fundamental vulnerado", "desacato", "impugnar la tutela",
              "impugnacion de tutela", "subsidiariedad", "inmediatez", "perjuicio irremediable", "minimo vital",
              "fallo de tutela", "no cumplen la tutela", "tutela contra providencia"]),
    S("S06", "petición",
      tema="el derecho de petición (modalidades, términos de respuesta, respuesta de fondo, reserva e "
           "insistencia)",
      objeto="Cubre las clases de petición ante autoridades y particulares, sus requisitos mínimos, los términos "
             "para responder según la modalidad, lo que es una respuesta de fondo, la reserva de información y "
             "los remedios ante el silencio.",
      entradas=["a quién se dirige la petición y qué se pide exactamente",
                "la fecha y el medio de radicación, si ya se presentó", "la respuesta recibida o el tiempo "
                "transcurrido sin respuesta"],
      fuentes=["Constitución Política (derecho de petición y acceso a documentos públicos)",
               "Ley 1755 de 2015, estatutaria del derecho de petición " + VERIFICAR,
               "Ley 1437 de 2011 (actuación administrativa) y Ley 1712 de 2014, transparencia y acceso a la "
               "información " + VERIFICAR,
               "relatoría de la Corte Constitucional",
               "conceptos del Gestor Normativo de la Función Pública y canales oficiales de radicación de la "
               "entidad"],
      entregable="borrador de petición con el destinatario competente, los hechos breves, las solicitudes "
                 "numeradas, la modalidad con su término de respuesta y la forma de recibir notificaciones",
      riesgos=["Afirmar un término de respuesta sin identificar la modalidad de la petición.",
               "Pedir información reservada sin advertir la reserva ni el recurso de insistencia."],
      comprobaciones=["Cada solicitud es concreta, numerada y puede responderse con un sí, un no o un "
                      "documento.",
                      "La modalidad de la petición y su término se indican con la norma y «verificar vigencia»."],
      extraer="destinatario, fecha y número de radicación, solicitudes formuladas, respuesta con su fecha, "
              "puntos sin responder y fundamento de la negativa",
      vigencia="los términos de respuesta vigentes en la fecha de radicación y cualquier ampliación temporal "
               "que rigiera entonces",
      preguntas="¿la entidad respondió de fondo, de forma clara y en término?; ¿qué remedio procede ante el "
                "silencio o la respuesta evasiva?",
      opciones="petición nueva y mejor delimitada, reiteración con advertencia, recurso de insistencia o acción "
               "de tutela por falta de respuesta",
      claves=["derecho de peticion", "peticion", "no me responden", "no me han respondido", "solicitud de "
              "informacion", "respuesta de fondo", "pqrs$", "copia de documentos", "recurso de insistencia",
              "radique una solicitud", "pedir informacion a la entidad"]),
    S("S07", "conciliación",
      tema="la conciliación y los demás mecanismos de solución de conflictos (requisito de procedibilidad, "
           "acta, efectos y arbitraje)",
      objeto="Cubre los asuntos conciliables, la conciliación como requisito previo según la jurisdicción, el "
             "conciliador competente, el contenido y los efectos del acta, la suspensión de términos, la "
             "transacción y el pacto arbitral.",
      entradas=["el conflicto, las partes y lo que cada una pretende", "el valor o el contenido de lo que se "
                "reclama y lo que la persona estaría dispuesta a ceder", "la vía judicial que seguiría si no "
                "hay acuerdo y los términos que están corriendo"],
      fuentes=["Ley 2220 de 2022, Estatuto de Conciliación " + VERIFICAR,
               "Código General del Proceso, Ley 1564 de 2012, y Ley 1437 de 2011 (requisito de procedibilidad) "
               + VERIFICAR,
               "Ley 1563 de 2012, Estatuto de Arbitraje " + VERIFICAR,
               "lineamientos del Ministerio de Justicia y del Derecho y de la Procuraduría General de la Nación "
               "sobre conciliación",
               "relatorías de la Corte Constitucional y del Consejo de Estado"],
      entregable="solicitud de conciliación con las partes, los hechos, las pretensiones cuantificadas, las "
                 "pruebas, la fórmula de arreglo y la advertencia sobre términos que se suspenden",
      riesgos=["Conciliar sobre derechos ciertos e indiscutibles o sobre asuntos que la ley no permite "
               "conciliar.",
               "Suponer que la solicitud suspende la caducidad por más tiempo del que la ley permite."],
      comprobaciones=["Se establece si la conciliación es requisito de procedibilidad para ese asunto y esa "
                      "jurisdicción.",
                      "Las obligaciones del acuerdo propuesto son claras, expresas y con fecha, para que el "
                      "acta preste mérito ejecutivo."],
      extraer="partes y representantes, hechos, pretensiones con valor, pruebas, fecha en que vence la acción, "
              "propuestas previas y respuesta de la contraparte",
      vigencia="el estatuto de conciliación vigente al presentar la solicitud y sus reglas de transición frente "
               "a las normas que reemplazó",
      preguntas="¿el asunto es conciliable y la conciliación es requisito previo?; ¿qué fórmula de arreglo es "
                "realista y qué efecto tendría el acta?",
      opciones="conciliación ante centro, notaría o Ministerio Público, transacción directa entre las partes, "
               "arbitraje si hay pacto o demanda si fracasa el arreglo",
      claves=["conciliacion", "conciliar", "centro de conciliacion", "acta de conciliacion", "requisito de "
              "procedibilidad", "audiencia de conciliacion", "arbitraje", "contrato de transaccion", "transar", "acuerdo de pago",
              "arreglo directo", "amigable composicion", "mediacion"]),
    S("S08", "recursos",
      tema="los recursos y medios de impugnación en procesos civiles, de familia y contencioso administrativos",
      objeto="Cubre la reposición, la apelación con sus efectos y su sustentación, la súplica, la queja, la "
             "casación civil, la revisión y los recursos del contencioso administrativo, además de la nulidad "
             "procesal.",
      entradas=["la providencia que se quiere atacar, con su fecha y forma de notificación",
                "lo que decidió y el agravio que causa", "la clase de proceso, la instancia y la cuantía"],
      fuentes=["Código General del Proceso, Ley 1564 de 2012 (medios de impugnación y nulidades) " + VERIFICAR,
               "Ley 2213 de 2022 (trámite de la apelación de sentencias) " + VERIFICAR,
               "Código de Procedimiento Administrativo y de lo Contencioso Administrativo, Ley 1437 de 2011, con "
               "la reforma de la Ley 2080 de 2021 " + VERIFICAR,
               "relatoría de la Sala de Casación Civil de la Corte Suprema de Justicia",
               "relatoría del Consejo de Estado y estados electrónicos de la Rama Judicial"],
      entregable="borrador del recurso con la providencia atacada, la procedencia y la oportunidad, los reparos "
                 "concretos, el fundamento de cada uno y la petición de revocar, modificar o adicionar",
      riesgos=["Interponer apelación contra un auto que no la admite y dejar pasar la reposición.",
               "Limitarse a anunciar el recurso y no sustentarlo en la oportunidad debida."],
      comprobaciones=["Se indica si la providencia admite el recurso, con su norma, y el término contado desde "
                      "la notificación.",
                      "Cada reparo señala la parte de la providencia que ataca y el error concreto que le "
                      "atribuye."],
      extraer="tipo de providencia, fecha y forma de notificación, decisión, fundamentos, instancia, cuantía y "
              "recursos ya interpuestos",
      vigencia="las reglas de procedencia y trámite de recursos vigentes en la fecha de la providencia",
      preguntas="¿qué recurso procede contra esta providencia y hasta cuándo?; ¿qué error concreto puede "
                "demostrarse?",
      opciones="reposición, apelación directa o en subsidio, queja, solicitud de aclaración o adición, o "
               "nulidad procesal",
      claves=["recurso de apelacion", "apelar", "apelacion", "reposicion", "recurso de queja", "casacion civil",
              "recurso de suplica", "impugnar el auto", "impugnar la sentencia", "recurso extraordinario de "
              "revision", "nulidad procesal", "sustentar la apelacion"]),
    S("S09", "derecho procesal informático",
      tema="el proceso judicial por medios digitales (expediente electrónico, notificaciones, audiencias "
           "virtuales y prueba electrónica)",
      objeto="Cubre la presentación de demandas y memoriales por canales digitales, el poder por mensaje de "
             "datos, las notificaciones electrónicas y su prueba, las audiencias virtuales, el expediente "
             "electrónico y el valor probatorio de mensajes y documentos electrónicos.",
      entradas=["la actuación digital realizada o por realizar y el despacho",
                "los correos, constancias de envío y acuses que la respaldan",
                "el documento o mensaje electrónico que se quiere hacer valer como prueba"],
      fuentes=["Ley 2213 de 2022, tecnologías de la información en las actuaciones judiciales " + VERIFICAR,
               "Ley 527 de 1999, mensajes de datos, firmas y entidades de certificación " + VERIFICAR,
               "Código General del Proceso, Ley 1564 de 2012 (uso de tecnologías y documentos electrónicos) "
               + VERIFICAR,
               "acuerdos y protocolos del Consejo Superior de la Judicatura sobre expediente electrónico, en la "
               "Rama Judicial",
               "relatorías de la Corte Suprema de Justicia y de la Corte Constitucional sobre notificación "
               "electrónica"],
      entregable="constancia razonada de la actuación digital con canal usado, fecha y hora de envío, prueba de "
                 "entrega o de acceso, momento en que se entiende surtida y riesgos de nulidad",
      riesgos=["Dar por surtida una notificación electrónica sin prueba de que el mensaje llegó a la dirección "
               "correcta.",
               "Aportar un pantallazo como prueba sin conservar el mensaje original ni sus metadatos."],
      comprobaciones=["Cada actuación indica el canal oficial del despacho y la constancia de envío y de "
                      "recepción.",
                      "Cada prueba electrónica señala cómo se garantiza su autenticidad e integridad."],
      extraer="direcciones electrónicas usadas, fechas y horas de envío, acuses de recibo, archivos adjuntos, "
              "formato y tamaño, y enlace del expediente",
      vigencia="las reglas de notificación electrónica vigentes en la fecha del envío y los protocolos del "
               "despacho aplicables entonces",
      preguntas="¿la notificación o la radicación digital se surtió válidamente y cuándo?; ¿el documento "
                "electrónico es auténtico e íntegro?",
      opciones="repetir la actuación por el canal oficial, pedir constancia secretarial, solicitar la nulidad "
               "por indebida notificación o aportar el mensaje original con su certificación",
      claves=["expediente electronico", "notificacion electronica", "notificacion por correo", "audiencia "
              "virtual", "justicia digital", "ley 2213", "mensaje de datos", "firma electronica", "firma digital",
              "poder por correo", "memorial por correo", "prueba electronica", "pantallazo", "whatsapp como "
              "prueba"]),
    S("S10", "gestión de modelos",
      tema="la gestión de modelos y minutas jurídicas (catálogo, ficha, versiones, validación y adaptación al "
           "caso)",
      objeto="Cubre la localización del modelo adecuado, su ficha con finalidad, supuestos, datos requeridos y "
             "anexos, el control de versiones, la clasificación de sensibilidad, el estado de validación y la "
             "adaptación trazable a un caso.",
      entradas=["la finalidad del escrito, la materia, el trámite y la etapa",
                "las características del caso que condicionan el modelo",
                "el modelo o la minuta candidata, si el usuario ya tiene una"],
      fuentes=["catálogo de 203 tipos de escrito de la plataforma (documentos.py) y docs/13-AUTOMATIZADOR.md",
               "biblioteca/inventario.json, inventario parcial de metadatos de la biblioteca de Drive (nada leído "
               "ni validado)",
               "docs/coordinacion/ESPECIFICACION-LEXCOL.md (secciones 3, 4 y 5)",
               "norma procesal que fija los requisitos del escrito, en SUIN-Juriscol o en la Secretaría del "
               "Senado " + VERIFICAR,
               "relatoría de la corte competente cuando el modelo cita jurisprudencia"],
      herramientas={"biblioteca_modelos": "F02 F04 F07"},
      entregable="ficha del modelo con identificador, finalidad, supuestos de uso, límites, datos requeridos, "
                 "anexos, fuentes que cita, fecha de revisión y estado de validación",
      riesgos=["Dar por jurídicamente correcto un modelo porque existe en la biblioteca o lleva un año en el "
               "nombre.",
               "Reutilizar un escrito con nombres o radicados de personas reales como si fuera una plantilla."],
      comprobaciones=["La ficha distingue plantilla recuperada, ejemplo didáctico y borrador nuevo, y declara el "
                      "estado de validación.",
                      "Cada norma citada por el modelo lleva su estado de verificación y la fecha de la "
                      "revisión."],
      extraer="título y finalidad del modelo, campos variables, anexos exigidos, normas y providencias que "
              "cita, datos personales presentes y fecha de la última revisión",
      vigencia="la fecha de la última revisión del modelo frente a las reformas posteriores de las normas que "
               "cita",
      preguntas="¿qué modelo corresponde al caso y qué le falta para usarse?; ¿las normas que cita siguen "
                "vigentes y aplican al supuesto?",
      opciones="usar un tipo del catálogo de la plataforma, adaptar un modelo recuperado dejando constancia de "
               "los cambios o redactar un borrador nuevo declarado como tal",
      claves=["minuta", "modelo de demanda", "modelo de contrato", "plantilla", "formato de", "modelos y minutas",
              "biblioteca de modelos", "ficha del modelo", "que modelo uso", "catalogo de documentos",
              "version del modelo", "gestion de modelos"]),
]
