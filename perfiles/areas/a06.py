"""A06 — Derecho privado colombiano. Fuentes: tipos de fuente oficial; los números de ley llevan «verificar vigencia»."""
from perfiles.definiciones import S, VERIFICAR

CLAVES_AREA = ["derecho privado", "derecho civil", "codigo civil", "codigo de comercio", "juzgado civil"]

SUBESPECIALIDADES = [
    S("S01", "civil",
      tema="las personas, los bienes y las obligaciones del derecho civil (capacidad, dominio, posesión y "
           "prescripción)",
      objeto="Cubre la capacidad y los apoyos, el dominio y los demás derechos reales, la posesión y la "
             "pertenencia, la tradición y el registro de inmuebles, y las reglas generales de las obligaciones.",
      entradas=["los hechos con fechas y quién tiene hoy el bien o el derecho",
                "los títulos y documentos disponibles (escritura, certificado de tradición, contrato)",
                "lo que la persona busca (declarar, recuperar, sanear o cobrar)"],
      fuentes=["Código Civil, libros primero, segundo y cuarto " + VERIFICAR,
               "Código General del Proceso, Ley 1564 de 2012 (declaración de pertenencia y procesos declarativos) "
               + VERIFICAR,
               "Ley 1996 de 2019, capacidad legal de las personas con discapacidad " + VERIFICAR,
               "relatoría de la Sala de Casación Civil de la Corte Suprema de Justicia",
               "SUIN-Juriscol y Secretaría del Senado para el texto vigente y sus modificaciones"],
      entregable="concepto civil con el derecho en discusión, sus requisitos uno a uno, el hecho que respalda cada "
                 "requisito y la prescripción aplicable",
      riesgos=["Confundir posesión con mera tenencia, o sumar posesiones sin título que lo permita.",
               "Aplicar el término de prescripción vigente hoy a una posesión iniciada bajo una ley anterior."],
      comprobaciones=["Cada requisito del derecho alegado está ligado a un hecho con su soporte o marcado como "
                      "faltante.",
                      "El término de prescripción indica desde cuándo se cuenta y qué ley regía al iniciarse."],
      extraer="titular inscrito, fechas de posesión y de los títulos, actos de señor y dueño, gravámenes y "
              "anotaciones del certificado de tradición",
      vigencia="el texto del Código Civil aplicable en la fecha de los hechos y la ley que fijaba el término de "
               "prescripción cuando empezó a correr",
      preguntas="¿quién es titular del derecho y con qué título y modo?; ¿se cumplió el término de prescripción y "
                "hubo interrupción o suspensión?",
      opciones="proceso declarativo de pertenencia, acción reivindicatoria, acción posesoria o saneamiento por "
               "acuerdo y escritura",
      claves=["posesion", "pertenencia", "prescripcion adquisitiva", "reivindicatoria", "escritura publica",
              "certificado de tradicion", "servidumbre", "usufructo", "lindero", "predio", "lote", "finca",
              "propietario del inmueble", "interdiccion", "capacidad legal"]),
    S("S02", "contratos",
      tema="los contratos civiles y mercantiles (formación, validez, interpretación e incumplimiento)",
      objeto="Cubre la formación del consentimiento, los requisitos de validez, la interpretación de cláusulas, el "
             "incumplimiento y sus remedios, y los contratos de uso frecuente como compraventa, promesa, "
             "arrendamiento y mandato.",
      entradas=["el texto del contrato o la descripción de lo pactado", "qué obligación se incumplió, por quién y "
                "desde cuándo", "las comunicaciones y pagos que lo prueban"],
      fuentes=["Código Civil, libro cuarto (obligaciones y contratos) " + VERIFICAR,
               "Código de Comercio, Decreto 410 de 1971, libro cuarto (contratos mercantiles) " + VERIFICAR,
               "Ley 820 de 2003, arrendamiento de vivienda urbana " + VERIFICAR,
               "relatoría de la Sala de Casación Civil de la Corte Suprema de Justicia",
               "SUIN-Juriscol y Secretaría del Senado para el texto vigente"],
      entregable="ficha del contrato con partes, obligaciones, cláusulas críticas, incumplimiento alegado, remedio "
                 "disponible y requisitos previos para ejercerlo",
      riesgos=["Pedir la resolución o el cumplimiento sin haber constituido en mora cuando el contrato lo exige.",
               "Tratar como promesa válida un documento al que le falta el plazo o la determinación del contrato "
               "prometido."],
      comprobaciones=["Cada cláusula invocada se cita por su número o texto y no se le atribuye lo que no dice.",
                      "El remedio propuesto indica sus requisitos previos y si quien demanda cumplió lo suyo."],
      extraer="partes, objeto, precio y forma de pago, plazos, cláusula penal, garantías, causales de terminación y "
              "cláusula compromisoria",
      vigencia="la ley vigente al celebrarse el contrato, que es la que lo rige, y las normas de orden público "
               "posteriores que lo afecten",
      preguntas="¿el contrato existe y es válido?; ¿quién incumplió primero y qué remedio corresponde?",
      opciones="requerir el cumplimiento, resolver con indemnización, cobrar la cláusula penal o renegociar por "
               "escrito",
      claves=["contrato", "incumplimiento", "clausula", "promesa de compraventa", "compraventa", "arrendamiento",
              "arriendo", "arrendador", "arrendatario", "inquilino", "canon", "mandato", "resolucion del contrato",
              "clausula penal", "otrosi"]),
    S("S03", "responsabilidad",
      tema="la responsabilidad civil contractual y extracontractual (daño, imputación y cuantía de los perjuicios)",
      objeto="Cubre el daño y su prueba, la culpa o la actividad peligrosa, el nexo causal, las causales de "
             "exoneración, la clasificación de los perjuicios y su estimación razonada.",
      entradas=["el hecho dañoso con fecha, lugar y quiénes intervinieron",
                "los daños sufridos y sus soportes (historia clínica, facturas, incapacidades, ingresos)",
                "la relación previa entre las partes, si la había"],
      fuentes=["Código Civil, título de la responsabilidad común por los delitos y las culpas " + VERIFICAR,
               "Código General del Proceso, Ley 1564 de 2012 (juramento estimatorio) " + VERIFICAR,
               "relatoría de la Sala de Casación Civil de la Corte Suprema de Justicia",
               "tablas e indicadores oficiales (IPC del DANE y tablas de mortalidad de la Superintendencia "
               "Financiera) para actualizar y proyectar",
               "SUIN-Juriscol para el texto vigente"],
      herramientas={"calculadora_liquidaciones": "F07 F08"},
      entregable="matriz de responsabilidad con daño, hecho, imputación, nexo, exoneración posible y perjuicios "
                 "discriminados con su base de cálculo",
      riesgos=["Pedir perjuicios sin prueba del daño cierto o repetir el mismo perjuicio bajo dos nombres.",
               "Usar una tasa, un índice o un tope de memoria en lugar del valor oficial del período."],
      comprobaciones=["Cada perjuicio reclamado indica su soporte y la fórmula o criterio con que se estimó.",
                      "El término de prescripción de la acción está identificado y contado desde una fecha "
                      "concreta."],
      extraer="fecha y circunstancias del hecho, lesiones o pérdidas, ingresos de la víctima, gastos probados, "
              "testigos y pólizas involucradas",
      vigencia="los criterios jurisprudenciales de tasación vigentes en la relatoría y los índices oficiales del "
               "período que se liquida",
      preguntas="¿hay daño cierto, hecho imputable y nexo causal?; ¿qué causal de exoneración puede oponer el "
                "demandado?",
      opciones="reclamación directa al responsable o a su aseguradora, conciliación extrajudicial o demanda "
               "declarativa de responsabilidad",
      claves=["responsabilidad civil", "indemnizacion de perjuicios", "accidente de transito", "dano moral",
              "lucro cesante", "dano emergente", "perjuicios", "me chocaron", "atropell", "negligencia medica",
              "responsabilidad medica", "actividad peligrosa", "responsabilidad extracontractual"]),
    S("S04", "familia",
      tema="las relaciones de familia (matrimonio y unión marital, divorcio, alimentos, custodia y violencia "
           "intrafamiliar)",
      objeto="Cubre el matrimonio y la unión marital de hecho, el divorcio y la liquidación de la sociedad, los "
             "alimentos, la custodia y las visitas, la patria potestad, la filiación y las medidas de protección.",
      entradas=["el vínculo entre las personas y las fechas relevantes (matrimonio, convivencia, separación)",
                "los hijos menores de edad y con quién viven", "los ingresos y gastos que se conocen de cada parte"],
      fuentes=["Código Civil, libro primero " + VERIFICAR,
               "Ley 1098 de 2006, Código de la Infancia y la Adolescencia " + VERIFICAR,
               "Ley 54 de 1990, unión marital de hecho, y Ley 294 de 1996, violencia intrafamiliar " + VERIFICAR,
               "Código General del Proceso, Ley 1564 de 2012 (procesos de familia) " + VERIFICAR,
               "relatorías de la Corte Constitucional y de la Sala de Casación Civil, Agraria y Rural; conceptos "
               "del ICBF"],
      entregable="ruta de familia con la pretensión, la autoridad competente (juez de familia, notaría, comisaría "
                 "o defensoría), los requisitos y los documentos del estado civil que deben aportarse",
      riesgos=["Proponer un acuerdo que desconozca el interés superior del niño o renuncie a alimentos futuros.",
               "Dejar vencer el término para pedir la declaración de la sociedad patrimonial tras la separación."],
      comprobaciones=["La ruta indica la autoridad competente y por qué factor lo es.",
                      "Toda decisión que afecta a un menor de edad explica cómo atiende su interés superior."],
      extraer="fechas de matrimonio, convivencia y separación, registros civiles, hijos y edades, bienes y deudas "
              "de la sociedad, ingresos y antecedentes de violencia",
      vigencia="las causales y los trámites vigentes en la fecha de la solicitud y las reglas de la unión marital "
               "aplicables cuando empezó la convivencia",
      preguntas="¿qué vínculo existe y cómo se prueba?; ¿qué exige el interés superior del menor en custodia, "
                "visitas y alimentos?",
      opciones="acuerdo ante notaría o centro de conciliación, proceso ante el juez de familia o medida de "
               "protección ante la comisaría",
      claves=["divorcio", "alimentos", "cuota alimentaria", "custodia", "regimen de visitas", "union marital",
              "sociedad conyugal", "patria potestad", "paternidad", "violencia intrafamiliar", "comisaria de familia",
              "mi esposo", "mi esposa", "separacion de bienes", "mi expareja"]),
    S("S05", "sucesiones",
      tema="la sucesión por causa de muerte (herederos, testamento, inventario, partición y adjudicación)",
      objeto="Cubre los órdenes hereditarios, el testamento y las legítimas, la aceptación de la herencia, el "
             "inventario de bienes y deudas, la partición, y el trámite notarial o judicial.",
      entradas=["la fecha del fallecimiento y el último domicilio del causante",
                "quiénes son los parientes y si hay testamento", "los bienes y deudas conocidos, con sus títulos"],
      fuentes=["Código Civil, libro tercero " + VERIFICAR,
               "Código General del Proceso, Ley 1564 de 2012 (proceso de sucesión) " + VERIFICAR,
               "Decreto 902 de 1988, liquidación de herencias ante notario " + VERIFICAR,
               "Ley 1934 de 2018, reforma al régimen de legítimas " + VERIFICAR,
               "relatoría de la Sala de Casación Civil y conceptos de la Superintendencia de Notariado y Registro"],
      entregable="cuadro de la sucesión con herederos por orden, cuotas, activo y pasivo inventariado, vía "
                 "notarial o judicial y documentos por reunir",
      riesgos=["Aplicar las reglas de legítimas vigentes hoy a una sucesión abierta antes de la reforma.",
               "Omitir la liquidación previa de la sociedad conyugal o patrimonial del causante."],
      comprobaciones=["Las cuotas se calculan con la ley vigente en la fecha de la muerte, que queda indicada.",
                      "Cada heredero tiene el registro civil que prueba su parentesco o se marca como faltante."],
      extraer="fecha de la muerte, cónyuge o compañero, descendientes y ascendientes, testamento, bienes con "
              "matrícula o placa, deudas y donaciones en vida",
      vigencia="la ley vigente al abrirse la sucesión, es decir, en la fecha de la muerte del causante",
      preguntas="¿quiénes heredan y en qué proporción?; ¿la sucesión puede ir por notaría o debe ir al juez?",
      opciones="sucesión notarial de común acuerdo, proceso judicial de sucesión o partición adicional de bienes "
               "omitidos",
      claves=["sucesion", "herencia", "heredero", "testamento", "fallecio", "murio", "causante", "particion",
              "legitimas$", "legitima rigorosa", "albacea", "repudiar la herencia", "bienes del difunto"]),
    S("S06", "comercial",
      tema="la actividad mercantil (comerciante, registro, títulos valores, garantías e insolvencia)",
      objeto="Cubre la calidad de comerciante y sus deberes, el registro mercantil y el establecimiento de "
             "comercio, los títulos valores y su cobro, las garantías mobiliarias y el régimen de insolvencia.",
      entradas=["el negocio o la operación y quiénes intervienen",
                "los documentos de la obligación (pagaré, factura, letra, contrato)",
                "la situación de pagos del deudor"],
      fuentes=["Código de Comercio, Decreto 410 de 1971 " + VERIFICAR,
               "Ley 1116 de 2006, régimen de insolvencia empresarial " + VERIFICAR,
               "Ley 1676 de 2013, garantías mobiliarias " + VERIFICAR,
               "doctrina y providencias de la Superintendencia de Sociedades",
               "relatoría de la Sala de Casación Civil y registro mercantil de la cámara de comercio (RUES)"],
      entregable="análisis mercantil con la obligación, el título que la contiene, sus requisitos formales, la "
                 "prescripción de la acción cambiaria y la vía de cobro o de reorganización",
      riesgos=["Cobrar como título valor un documento al que le falta un requisito esencial.",
               "Iniciar un cobro individual contra un deudor ya admitido a un proceso de insolvencia."],
      comprobaciones=["Cada título se revisa contra sus requisitos generales y particulares, uno por uno.",
                      "La prescripción de la acción cambiaria está contada desde el vencimiento que consta en el "
                      "título."],
      extraer="tipo de título, fechas de creación y vencimiento, valor, firmas, endosos, espacios en blanco e "
              "instrucciones para llenarlos",
      vigencia="las reglas vigentes al crearse el título y el régimen de insolvencia aplicable en la fecha de la "
               "solicitud",
      preguntas="¿el documento es un título valor completo y exigible?; ¿la acción cambiaria está vigente o "
                "prescrita?",
      opciones="proceso ejecutivo con medidas cautelares, proceso monitorio, acuerdo de pago o solicitud de "
               "reorganización",
      claves=["pagare", "letra de cambio", "titulo valor", "factura electronica", "cheque", "camara de comercio",
              "registro mercantil", "establecimiento de comercio", "insolvencia", "reorganizacion empresarial",
              "garantia mobiliaria", "endoso", "accion cambiaria", "comerciante"]),
    S("S07", "sociedades",
      tema="las sociedades comerciales (constitución, órganos, administradores, reformas y conflictos entre socios)",
      objeto="Cubre la elección y constitución del tipo societario, los estatutos, las reuniones y sus actas, los "
             "deberes y la responsabilidad de los administradores, las reformas, la disolución y la liquidación.",
      entradas=["los estatutos y el certificado de existencia y representación",
                "el acto o la decisión que se quiere tomar o impugnar",
                "la composición del capital y quiénes administran"],
      fuentes=["Código de Comercio, Decreto 410 de 1971, libro segundo " + VERIFICAR,
               "Ley 222 de 1995 (administradores, reuniones y grupos) " + VERIFICAR,
               "Ley 1258 de 2008, sociedad por acciones simplificada " + VERIFICAR,
               "doctrina, circulares y providencias de la Superintendencia de Sociedades",
               "SUIN-Juriscol y Secretaría del Senado para el texto vigente"],
      entregable="concepto societario con el órgano competente, convocatoria, quórum y mayorías exigidos, el vicio "
                 "posible de la decisión y el término para impugnarla",
      riesgos=["Aplicar mayorías o reglas de un tipo societario a otro sin leer los estatutos.",
               "Dejar pasar el término breve para impugnar una decisión de asamblea o junta."],
      comprobaciones=["La convocatoria, el quórum y las mayorías se contrastan con los estatutos y con la ley, en "
                      "ese orden.",
                      "Cada deber de administrador invocado cita su fuente y el hecho que lo compromete."],
      extraer="tipo societario, capital y participaciones, cláusulas de convocatoria y mayorías, representante "
              "legal y sus límites, actas y fechas de las reuniones",
      vigencia="los estatutos vigentes en la fecha de la decisión, según el registro mercantil, y la ley societaria "
               "aplicable a ese tipo de sociedad",
      preguntas="¿la decisión fue tomada por el órgano competente con convocatoria, quórum y mayoría?; ¿el "
                "administrador obró dentro de sus facultades y deberes?",
      opciones="impugnar la decisión, convocar una nueva reunión que la ratifique, reformar los estatutos o "
               "acudir a la Superintendencia de Sociedades",
      claves=["sociedad", "sas$", "socios", "accionista", "asamblea de accionistas", "junta de socios",
              "junta directiva", "estatutos", "representante legal", "acta de asamblea", "disolucion", "liquidar la "
              "empresa", "constituir una empresa", "administrador de la sociedad", "capital social"]),
    S("S08", "consumo",
      tema="la protección al consumidor (garantía, información, publicidad, cláusulas abusivas y reclamación)",
      objeto="Cubre la relación de consumo, la garantía legal, el deber de información, la publicidad engañosa, "
             "las ventas a distancia con retracto y reversión del pago, y la reclamación ante el proveedor y la "
             "Superintendencia de Industria y Comercio.",
      entradas=["el producto o servicio, la fecha de compra y el valor", "la falla o el incumplimiento y cuándo "
                "apareció", "la reclamación hecha al proveedor y su respuesta"],
      fuentes=["Ley 1480 de 2011, Estatuto del Consumidor " + VERIFICAR,
               "Decreto 1074 de 2015, reglamentario del sector Comercio, Industria y Turismo " + VERIFICAR,
               "Circular Única de la Superintendencia de Industria y Comercio",
               "Ley 1328 de 2009, consumidor financiero " + VERIFICAR,
               "decisiones de la Delegatura para Asuntos Jurisdiccionales de la SIC"],
      entregable="reclamación de consumo con relación de consumo acreditada, defecto o infracción, pretensión "
                 "concreta (reparación, cambio o devolución) y agotamiento de la reclamación directa",
      riesgos=["Acudir a la acción de protección al consumidor sin haber reclamado antes al proveedor.",
               "Tratar como consumidor a quien adquirió el bien para su actividad económica."],
      comprobaciones=["Consta la reclamación directa previa, con fecha, o se indica que falta.",
                      "El término de la garantía y el de la acción están contados desde fechas identificadas."],
      extraer="fecha de compra y de entrega, término de garantía ofrecido, descripción del defecto, "
              "reclamaciones con fecha y respuestas del proveedor",
      vigencia="el término de garantía legal o suplementaria aplicable en la fecha de la compra y la competencia "
               "vigente de la SIC",
      preguntas="¿existe relación de consumo?; ¿la garantía sigue vigente y qué puede exigirse con ella?",
      opciones="reclamación directa, acción de protección al consumidor ante la SIC o el juez, o denuncia "
               "administrativa por la infracción",
      claves=["consumidor", "garantia del producto", "producto defectuoso", "publicidad enganosa", "retracto",
              "reversion del pago", "devolucion del dinero", "no me responden por la garantia", "compre un",
              "clausula abusiva", "sic$", "proveedor no responde", "electrodomestico", "tienda"]),
    S("S09", "seguros",
      tema="el contrato de seguro (póliza, riesgo, siniestro, reclamación, objeción y prescripción)",
      objeto="Cubre los elementos esenciales del seguro, la declaración del riesgo y la reticencia, las "
             "exclusiones, la reclamación con prueba del siniestro y de la cuantía, la objeción de la aseguradora "
             "y la prescripción de las acciones.",
      entradas=["la póliza con sus condiciones generales y particulares", "el siniestro: qué pasó, cuándo y "
                "cuándo se conoció", "la reclamación presentada y la respuesta de la aseguradora"],
      fuentes=["Código de Comercio, Decreto 410 de 1971, título del contrato de seguro " + VERIFICAR,
               "Estatuto Orgánico del Sistema Financiero, Decreto 663 de 1993 " + VERIFICAR,
               "Circular Básica Jurídica y conceptos de la Superintendencia Financiera",
               "Ley 1328 de 2009, consumidor financiero " + VERIFICAR,
               "relatoría de la Sala de Casación Civil de la Corte Suprema de Justicia"],
      entregable="análisis de cobertura con amparo invocado, exclusiones revisadas, prueba del siniestro y de la "
                 "cuantía, fecha de la reclamación y cómputo de la prescripción",
      riesgos=["Contar la prescripción desde el siniestro cuando corre desde que el interesado lo conoció, o al "
               "revés.",
               "Dar por cubierto un hecho sin leer las exclusiones y las garantías de la póliza concreta."],
      comprobaciones=["El amparo y cada exclusión se citan por su cláusula de la póliza a la vista.",
                      "El cómputo de la prescripción distingue la ordinaria de la extraordinaria y da sus fechas."],
      extraer="tomador, asegurado y beneficiario, vigencia, amparos y sumas aseguradas, exclusiones, deducible, "
              "fecha del siniestro y de la reclamación",
      vigencia="las condiciones de la póliza vigentes en la fecha del siniestro y las normas del contrato de "
               "seguro aplicables en esa fecha",
      preguntas="¿el hecho está amparado y no excluido?; ¿la objeción fue oportuna y la acción sigue vigente?",
      opciones="reconsideración ante la aseguradora, queja ante el defensor del consumidor financiero, "
               "conciliación o demanda contra la aseguradora",
      claves=["seguros$", "contrato de seguro", "seguro del carro", "poliza", "aseguradora", "siniestro", "objecion de la aseguradora", "soat$", "seguro de vida", "reticencia",
              "amparo", "deducible", "beneficiario del seguro", "no me pagan el seguro"]),
    S("S10", "propiedad intelectual",
      tema="la propiedad intelectual (marcas, patentes, diseños, derechos de autor y competencia desleal)",
      objeto="Cubre el registro y la defensa de marcas y otros signos, las patentes y diseños, los derechos "
             "morales y patrimoniales de autor, las licencias y cesiones, y los actos de competencia desleal "
             "vinculados.",
      entradas=["el signo, la obra o la invención y quién la creó o la usa",
                "los registros o solicitudes existentes y sus fechas", "el uso por terceros que se quiere impedir "
                "o el uso propio que se quiere asegurar"],
      fuentes=["Decisión 486 de 2000 de la Comunidad Andina, régimen común de propiedad industrial " + VERIFICAR,
               "Ley 23 de 1982 y Decisión Andina 351 de 1993, derecho de autor " + VERIFICAR,
               "Ley 256 de 1996, competencia desleal " + VERIFICAR,
               "bases de datos y resoluciones de la Superintendencia de Industria y Comercio (propiedad "
               "industrial) y Dirección Nacional de Derecho de Autor",
               "interpretaciones prejudiciales del Tribunal de Justicia de la Comunidad Andina"],
      entregable="concepto de propiedad intelectual con el derecho identificado, su titular, su vigencia, el riesgo "
                 "de confusión o de infracción y la acción administrativa o judicial disponible",
      riesgos=["Afirmar que un signo está disponible sin una búsqueda de antecedentes en la base oficial.",
               "Confundir el registro de la marca con el nombre de la sociedad o con el dominio de internet."],
      comprobaciones=["La titularidad y la vigencia del derecho se apoyan en el registro oficial o quedan como "
                      "pendientes.",
                      "El cotejo de signos compara aspecto visual, fonético y conceptual, y las clases de "
                      "productos o servicios."],
      extraer="signo u obra, titular, fecha de solicitud o de creación, clases de la Clasificación de Niza, "
              "vigencia del registro, licencias y usos de terceros",
      vigencia="el estado del registro en la base oficial a la fecha de consulta y los plazos de oposición o "
               "renovación que estén corriendo",
      preguntas="¿quién es el titular y hasta cuándo?; ¿el uso del tercero genera riesgo de confusión o "
                "aprovecha la reputación ajena?",
      opciones="solicitar el registro, presentar oposición, requerir al infractor o demandar por infracción o "
               "competencia desleal",
      claves=["marca$", "marcas$", "patente", "derechos de autor", "derecho de autor", "propiedad intelectual",
              "propiedad industrial", "logo$", "logotipo", "plagio", "competencia desleal", "registro de marca", "oposicion a la "
              "marca", "licencia de uso", "diseno industrial", "copiaron mi"]),
]
