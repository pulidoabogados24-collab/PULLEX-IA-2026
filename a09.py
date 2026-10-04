"""A09 — Derecho laboral y protección social colombiana. Fuentes: tipos de fuente oficial; los números de ley
llevan «verificar vigencia». Las cifras (salario mínimo, auxilio de transporte, tasas, topes) nunca se dan de
memoria: salen del acto oficial del período o quedan como «No verificado».
"""
from perfiles.definiciones import S, VERIFICAR

CLAVES_AREA = ["laboral", "trabajador", "empleador", "mi jefe", "la empresa donde trabajo", "seguridad social"]

SUBESPECIALIDADES = [
    S("S01", "contratación laboral",
      tema="la vinculación laboral (existencia del contrato de trabajo, modalidades, período de prueba y "
           "tercerización)",
      objeto="Cubre los elementos del contrato de trabajo y la primacía de la realidad frente a la prestación de "
             "servicios, las modalidades por duración, el período de prueba, el trabajo remoto y la "
             "intermediación o tercerización.",
      entradas=["cómo se presta el servicio: horario, órdenes, lugar, herramientas y a quién se reporta",
                "el contrato firmado o la forma en que se pactó, con fechas de inicio y de fin",
                "cómo y cuánto se paga, y quién asume la seguridad social"],
      fuentes=["Constitución Política (trabajo y principios mínimos fundamentales)",
               "Código Sustantivo del Trabajo, parte individual " + VERIFICAR,
               "Ley 2466 de 2025, reforma laboral, con su entrada en vigor por etapas " + VERIFICAR,
               "Decreto 1072 de 2015, reglamentario del sector Trabajo " + VERIFICAR,
               "relatoría de la Sala de Casación Laboral de la Corte Suprema de Justicia y conceptos del "
               "Ministerio del Trabajo"],
      entregable="análisis de la vinculación con los tres elementos del contrato contrastados con los hechos, la "
                 "modalidad aplicable, los indicios de subordinación y la prueba disponible de cada uno",
      riesgos=["Dar por probado el contrato de trabajo por la sola continuidad, sin indicios de subordinación.",
               "Aplicar las reglas de la reforma laboral a un período anterior a su entrada en vigor."],
      comprobaciones=["Cada elemento (prestación personal, subordinación y remuneración) se liga a un hecho con "
                      "su prueba o se marca como faltante.",
                      "La modalidad del contrato y sus prórrogas se establecen con las fechas del caso."],
      extraer="fechas de inicio y fin, funciones, horario, órdenes recibidas, forma de pago, contratos y "
              "prórrogas, afiliaciones a seguridad social y quién las pagó",
      vigencia="las reglas de contratación vigentes al celebrarse el contrato y en cada prórroga, incluida la "
               "etapa de la reforma laboral que ya regía",
      preguntas="¿existió un contrato de trabajo aunque se llamara de otra forma?; ¿qué modalidad y qué duración "
                "tiene según los hechos?",
      opciones="reclamación directa al contratante, queja ante el inspector del trabajo, conciliación o demanda "
               "de declaración del contrato realidad",
      claves=["contrato de trabajo", "prestacion de servicios", "contrato realidad", "periodo de prueba",
              "contrato a termino fijo", "termino indefinido", "obra o labor", "subordinacion", "ops$",
              "tercerizacion", "empresa de servicios temporales", "teletrabajo", "contrato de aprendizaje",
              "me contrataron"]),
    S("S02", "salarios",
      tema="el salario y la jornada (qué es salario, salario integral, recargos, horas extras y descuentos)",
      objeto="Cubre los pagos que constituyen salario y los que no, el salario integral y en especie, la jornada "
             "máxima, el trabajo suplementario, nocturno, dominical y festivo, los descuentos permitidos y la "
             "igualdad salarial.",
      entradas=["el salario pactado y todos los pagos recibidos, con sus comprobantes",
                "la jornada real: horarios, días trabajados y descansos", "el período que se quiere revisar"],
      fuentes=["Código Sustantivo del Trabajo (salario, jornada y descansos) " + VERIFICAR,
               "Ley 2466 de 2025 y Ley 2101 de 2021, recargos y reducción de la jornada, con su aplicación "
               "gradual " + VERIFICAR,
               "decreto anual del salario mínimo y del auxilio de transporte del año que se liquida",
               "relatoría de la Sala de Casación Laboral de la Corte Suprema de Justicia",
               "conceptos del Ministerio del Trabajo y texto vigente en SUIN-Juriscol"],
      herramientas={"calculadora_liquidaciones": "F05 F07 F08"},
      entregable="reliquidación salarial con la base de cada período, los pagos incluidos y excluidos, los "
                 "recargos causados, la fórmula aplicada y la fuente de cada valor",
      riesgos=["Usar el salario mínimo, el auxilio de transporte o un porcentaje de recargo de un año distinto "
               "al liquidado.",
               "Excluir de la base un pago habitual que retribuye el servicio solo porque el contrato lo llamó no "
               "salarial."],
      comprobaciones=["Cada valor oficial (salario mínimo, auxilio, recargo) cita el acto y el año de donde sale.",
                      "La liquidación muestra fórmula, base, período y resultado de cada concepto."],
      extraer="salario básico, pagos adicionales y su periodicidad, horarios, horas extras, dominicales y "
              "festivos trabajados, y descuentos aplicados",
      vigencia="el salario mínimo, la jornada máxima y los porcentajes de recargo vigentes en cada período que "
               "se liquida",
      preguntas="¿qué pagos hacen parte del salario y cuáles no?; ¿se causaron recargos o trabajo suplementario "
                "que no se pagaron?",
      opciones="solicitud de reliquidación al empleador, queja ante el inspector del trabajo, conciliación o "
               "demanda ordinaria laboral",
      claves=["salario", "horas extras", "recargo nocturno", "dominicales", "festivos", "salario integral",
              "salario minimo", "auxilio de transporte", "jornada laboral", "no me pagan el sueldo", "bonificacion",
              "pago no salarial", "descuento de nomina", "me deben el sueldo"]),
    S("S03", "prestaciones",
      tema="las prestaciones sociales y los descansos remunerados (cesantías, intereses, prima, vacaciones y "
           "dotación)",
      objeto="Cubre la causación y la base de liquidación de cesantías, intereses a las cesantías, prima de "
             "servicios y vacaciones, la dotación, y las sanciones por no consignar o no pagar a tiempo.",
      entradas=["las fechas de inicio y de corte del contrato", "el salario de cada período y sus variaciones",
                "lo que el empleador ya pagó o consignó, con soportes"],
      fuentes=["Código Sustantivo del Trabajo (prestaciones patronales comunes y vacaciones) " + VERIFICAR,
               "Ley 50 de 1990, régimen de cesantías y sanción por no consignación " + VERIFICAR,
               "decreto anual del salario mínimo y del auxilio de transporte de cada año liquidado",
               "relatoría de la Sala de Casación Laboral de la Corte Suprema de Justicia",
               "conceptos del Ministerio del Trabajo y texto vigente en la Secretaría del Senado"],
      herramientas={"calculadora_liquidaciones": "F05 F07 F08"},
      entregable="liquidación de prestaciones por concepto y período, con fórmula, base, días, valor pagado, "
                 "diferencia y sanciones que podrían causarse",
      riesgos=["Presentar una cifra final sin mostrar la base, los días y la fórmula de cada concepto.",
               "Dar por causada la sanción moratoria sin advertir que depende de la buena o mala fe del "
               "empleador."],
      comprobaciones=["Cada concepto muestra fórmula, base salarial, días y resultado, y puede recalcularse a "
                      "mano.",
                      "Las sanciones se presentan como eventuales, con la condición de la que dependen."],
      extraer="fechas de ingreso y retiro, salarios por período, auxilio de transporte, consignaciones de "
              "cesantías, primas y vacaciones pagadas y ausencias no remuneradas",
      vigencia="las reglas de liquidación y los valores oficiales vigentes en cada año del período trabajado",
      preguntas="¿qué prestaciones se causaron y cuánto se adeuda de cada una?; ¿procede alguna sanción por mora "
                "o por no consignación?",
      opciones="reclamación escrita al empleador, conciliación ante el inspector del trabajo o demanda ordinaria "
               "laboral",
      claves=["cesantias", "prima de servicios", "vacaciones", "prestaciones sociales", "liquidacion laboral",
              "intereses a las cesantias", "liquidacion de prestaciones", "dotacion", "sancion moratoria",
              "no me han pagado la liquidacion", "calcula mi liquidacion", "fondo de cesantias"]),
    S("S04", "terminación",
      tema="la terminación del contrato de trabajo (justas causas, despido sin justa causa, renuncia e "
           "indemnización)",
      objeto="Cubre los modos de terminación, las justas causas y su trámite, el despido sin justa causa con su "
             "indemnización, el despido indirecto, la renuncia y el mutuo acuerdo, y el pago de salarios y "
             "prestaciones al terminar.",
      entradas=["la fecha y la forma de la terminación, con la carta o la comunicación recibida",
                "la modalidad del contrato, la fecha de ingreso y el último salario",
                "si hubo llamados de atención, descargos o condiciones especiales (salud, embarazo, fuero)"],
      fuentes=["Código Sustantivo del Trabajo (terminación del contrato, justas causas e indemnización) "
               + VERIFICAR,
               "Ley 789 de 2002, tabla de indemnización por despido " + VERIFICAR,
               "Ley 2466 de 2025, reforma laboral (procedimiento disciplinario y terminación) " + VERIFICAR,
               "relatoría de la Sala de Casación Laboral de la Corte Suprema de Justicia",
               "relatoría de la Corte Constitucional sobre debido proceso en el despido"],
      herramientas={"calculadora_liquidaciones": "F07 F08"},
      entregable="análisis de la terminación con el modo invocado, la causa alegada y su prueba, el trámite "
                 "seguido, la indemnización que correspondería y lo que debe pagarse al terminar",
      riesgos=["Calcular la indemnización sin conocer la modalidad del contrato, la antigüedad y el salario "
               "base.",
               "Pasar por alto una condición de estabilidad reforzada que haría ineficaz el despido."],
      comprobaciones=["La causa de terminación invocada por el empleador se contrasta con la carta y con su "
                      "prueba.",
                      "La indemnización indica modalidad, antigüedad, salario base y la tabla legal aplicada."],
      extraer="fecha de ingreso y de retiro, modalidad del contrato, causa invocada, carta de terminación, "
              "descargos, último salario y pagos hechos al finalizar",
      vigencia="la tabla de indemnización y las reglas de terminación vigentes en la fecha del despido, incluida "
               "la etapa de la reforma laboral que ya regía",
      preguntas="¿la terminación tuvo justa causa y se respetó el trámite?; ¿qué indemnización y qué pagos "
                "finales corresponden?",
      opciones="reclamación directa de la indemnización, conciliación ante el inspector del trabajo, demanda "
               "ordinaria laboral o solicitud de reintegro si hay estabilidad reforzada",
      claves=["despid", "despido", "sin justa causa", "me echaron", "me sacaron del trabajo", "justa causa",
              "carta de despido", "renuncia", "renuncie", "terminacion del contrato de trabajo",
              "indemnizacion por despido", "despido indirecto", "me terminaron el contrato", "no me renovaron",
              "diligencia de descargos", "citacion a descargos"]),
    S("S05", "estabilidad",
      tema="la estabilidad laboral reforzada (maternidad, salud, fuero sindical, prepensión y acoso laboral)",
      objeto="Cubre las protecciones especiales frente al despido por embarazo y lactancia, debilidad manifiesta "
             "por salud, fuero sindical y cercanía a la pensión, la autorización previa del inspector y el "
             "reintegro.",
      entradas=["la condición especial de la persona y desde cuándo la conocía el empleador",
                "la fecha y la forma de la terminación o de la medida tomada",
                "los soportes médicos, sindicales o de cotización que acreditan la condición"],
      fuentes=["Constitución Política (igualdad, protección a la maternidad y estabilidad en el empleo)",
               "Código Sustantivo del Trabajo (protección a la maternidad y fuero sindical) " + VERIFICAR,
               "Ley 361 de 1997, protección de personas en situación de discapacidad " + VERIFICAR,
               "Ley 1010 de 2006, acoso laboral " + VERIFICAR,
               "relatorías de la Corte Constitucional y de la Sala de Casación Laboral, que no siempre coinciden"],
      entregable="análisis de estabilidad con la condición protegida y su prueba, el conocimiento del empleador, "
                 "la existencia de autorización, la consecuencia jurídica y la vía judicial más eficaz",
      riesgos=["Presentar como pacífico un punto en que la jurisprudencia constitucional y la laboral difieren.",
               "Afirmar la protección sin prueba de que el empleador conocía la condición antes de despedir."],
      comprobaciones=["Se indica cómo y cuándo conoció el empleador la condición, con su soporte.",
                      "Cuando las altas cortes difieren, se exponen ambas posiciones sin escoger por mayoría."],
      extraer="condición protegida, fechas de diagnóstico, incapacidades o embarazo, comunicación al empleador, "
              "fecha del despido, autorización del inspector y pagos recibidos",
      vigencia="los criterios vigentes de cada corte sobre la condición protegida y la norma de protección "
               "aplicable en la fecha del despido",
      preguntas="¿la persona estaba en una condición protegida que el empleador conocía?; ¿el despido necesitaba "
                "autorización y la tuvo?",
      opciones="acción de tutela como mecanismo transitorio, demanda ordinaria con pretensión de reintegro, "
               "queja por acoso laboral o proceso especial de fuero sindical",
      claves=["estabilidad laboral reforzada", "embarazada", "embarazo", "licencia de maternidad", "incapacidad",
              "fuero de salud", "fuero sindical", "prepensionado", "acoso laboral", "reintegro",
              "me despidieron enferma", "me despidieron enfermo", "debilidad manifiesta", "discapacidad"]),
    S("S06", "derecho colectivo",
      tema="el derecho colectivo del trabajo (sindicatos, negociación colectiva, huelga y convención)",
      objeto="Cubre la libertad sindical y la constitución de sindicatos, el fuero, el pliego de peticiones y el "
             "arreglo directo, la huelga y el tribunal de arbitramento, y la convención, el pacto y el laudo.",
      entradas=["la organización sindical o el grupo de trabajadores y la empresa",
                "la etapa del conflicto colectivo y sus fechas", "la convención, el pacto o el laudo vigente, si "
                "existe"],
      fuentes=["Constitución Política (asociación sindical, negociación colectiva y huelga)",
               "Código Sustantivo del Trabajo, parte colectiva " + VERIFICAR,
               "convenios 87 y 98 de la Organización Internacional del Trabajo, ratificados por Colombia",
               "relatoría de la Sala de Casación Laboral (incluidos los recursos de anulación de laudos)",
               "conceptos y registros del Ministerio del Trabajo y relatoría de la Corte Constitucional"],
      entregable="análisis del conflicto colectivo con la etapa actual, los términos que corren, las opciones "
                 "legales de cada parte, las garantías sindicales comprometidas y los riesgos de cada decisión",
      riesgos=["Contar mal los términos de la etapa de arreglo directo o de la decisión entre huelga y tribunal.",
               "Aplicar una convención que perdió vigencia o que fue denunciada sin revisar su prórroga."],
      comprobaciones=["Cada etapa del conflicto indica fecha de inicio, duración legal y lo que ocurre al vencer.",
                      "La cláusula convencional invocada se cita del texto depositado y con su vigencia."],
      extraer="sindicato y su clase, número de afiliados, fecha de presentación del pliego, actas de la "
              "negociación, convención o pacto vigente y trabajadores aforados",
      vigencia="la convención, el pacto o el laudo vigente en la fecha de los hechos, con su depósito, su "
               "denuncia y sus prórrogas",
      preguntas="¿en qué etapa está el conflicto colectivo y qué término corre?; ¿qué garantía sindical o "
                "cláusula convencional se está desconociendo?",
      opciones="continuar el arreglo directo, votar la huelga, convocar tribunal de arbitramento o acudir a la "
               "querella y a la acción judicial por las garantías sindicales",
      claves=["sindicato", "convencion colectiva", "pliego de peticiones", "huelga", "negociacion colectiva",
              "pacto colectivo", "tribunal de arbitramento", "laudo arbitral", "afiliacion sindical",
              "persecucion sindical", "derecho de asociacion", "sindical"]),
    S("S07", "pensiones",
      tema="las pensiones (vejez, invalidez y sobrevivientes, traslado de régimen e historia laboral)",
      objeto="Cubre los requisitos de cada pensión en el régimen de prima media y en el de ahorro individual, el "
             "régimen de transición, el traslado y su ineficacia, la corrección de la historia laboral y las "
             "prestaciones sustitutas.",
      entradas=["la fecha de nacimiento y la historia laboral con las semanas cotizadas",
                "el régimen y el fondo actual, y los traslados con sus fechas",
                "la prestación que se pide y la respuesta de la administradora, si la hay"],
      fuentes=["Ley 100 de 1993, sistema general de pensiones, con la Ley 797 de 2003 " + VERIFICAR,
               "Ley 2381 de 2024, reforma pensional: confirmar su entrada en vigor y su estado en la Corte "
               "Constitucional " + VERIFICAR,
               "Constitución Política (seguridad social y Acto Legislativo 01 de 2005) " + VERIFICAR,
               "relatorías de la Sala de Casación Laboral y de la Corte Constitucional",
               "historia laboral y actos de Colpensiones o de la administradora de fondos, y conceptos de la "
               "Superintendencia Financiera"],
      herramientas={"calculadora_liquidaciones": "F07 F08"},
      entregable="estudio pensional con el régimen aplicable, los requisitos de la prestación contrastados con la "
                 "historia laboral, las semanas faltantes o en mora y la reclamación que procede",
      riesgos=["Dar por aplicable la reforma pensional sin confirmar su vigencia y sus reglas de transición.",
               "Calcular una mesada o un ingreso base sin la historia laboral completa y actualizada."],
      comprobaciones=["Los requisitos se contrastan con las semanas y fechas de la historia laboral a la vista.",
                      "Se indica qué norma rige por la fecha de cumplimiento de los requisitos o de la "
                      "estructuración."],
      extraer="fecha de nacimiento, semanas cotizadas por empleador y período, períodos en mora o faltantes, "
              "traslados de régimen, fecha de estructuración y beneficiarios",
      vigencia="la norma vigente cuando se cumplieron los requisitos, se estructuró la invalidez o ocurrió la "
               "muerte, y el régimen de transición que conserve la persona",
      preguntas="¿qué régimen y qué norma rigen la prestación?; ¿la persona cumple los requisitos o qué le "
                "falta?",
      opciones="solicitud de corrección de historia laboral, reclamación de la prestación ante la "
               "administradora, demanda ordinaria laboral o acción de tutela si hay afectación del mínimo vital",
      claves=["pension", "colpensiones", "semanas cotizadas", "fondo de pensiones", "regimen de transicion",
              "pension de vejez", "pension de invalidez", "pension de sobrevivientes", "sustitucion pensional",
              "traslado de regimen", "historia laboral", "indemnizacion sustitutiva", "bono pensional", "mesada"]),
    S("S08", "salud",
      tema="la seguridad social en salud (afiliación, prestación de servicios, incapacidades y licencias)",
      objeto="Cubre la afiliación y la cotización, el acceso a servicios y tecnologías, las negaciones y demoras "
             "de la entidad promotora, el pago de incapacidades según su duración y las licencias de maternidad y "
             "paternidad.",
      entradas=["el servicio, medicamento o prestación económica que se necesita y quién lo ordenó",
                "la respuesta o el silencio de la entidad, con fechas",
                "el estado de afiliación y de cotización de la persona"],
      fuentes=["Ley 1751 de 2015, estatutaria del derecho fundamental a la salud " + VERIFICAR,
               "Ley 100 de 1993, sistema general de seguridad social en salud, con sus reformas " + VERIFICAR,
               "Decreto 780 de 2016, reglamentario del sector Salud " + VERIFICAR,
               "resoluciones del Ministerio de Salud sobre servicios financiados y circulares de la "
               "Superintendencia de Salud",
               "relatoría de la Corte Constitucional en materia de salud"],
      entregable="ruta de acceso en salud con el servicio u obligación económica exigible, el responsable según "
                 "la norma, la orden médica que lo soporta y el mecanismo de reclamación más rápido",
      riesgos=["Señalar al responsable equivocado del pago de una incapacidad según el día en que va.",
               "Sustituir el criterio del médico tratante por una opinión propia sobre el tratamiento."],
      comprobaciones=["El responsable de cada tramo de la incapacidad se identifica por número de días y con su "
                      "norma.",
                      "La pretensión se apoya en una orden o concepto del médico tratante que consta en los "
                      "documentos."],
      extraer="diagnóstico y orden médica con fecha, servicio negado o demorado, respuesta de la entidad, días "
              "de incapacidad acumulados y estado de las cotizaciones",
      vigencia="las reglas vigentes de financiación de servicios y de pago de incapacidades en la fecha de la "
               "orden médica",
      preguntas="¿quién está obligado a prestar el servicio o a pagar la prestación?; ¿la negativa o la demora "
                "vulneran el derecho a la salud?",
      opciones="petición y queja ante la entidad, reclamo ante la Superintendencia Nacional de Salud, acción de "
               "tutela o incidente de desacato si ya hay fallo",
      claves=["eps$", "salud$", "medicamento", "cirugia", "incapacidad medica", "pago de incapacidades",
              "no me autorizan", "tratamiento medico", "cita con especialista", "supersalud", "licencia de paternidad",
              "afiliacion a salud", "negaron el servicio", "orden medica"]),
    S("S09", "riesgos laborales",
      tema="los riesgos laborales (accidente de trabajo, enfermedad laboral, calificación y culpa del empleador)",
      objeto="Cubre el reporte y la calificación del origen, la pérdida de capacidad laboral y sus instancias, "
             "las prestaciones asistenciales y económicas de la administradora, la indemnización plena por culpa "
             "patronal y el sistema de gestión de seguridad y salud en el trabajo.",
      entradas=["el accidente o la enfermedad: fecha, labor que se realizaba y reporte hecho",
                "los dictámenes de origen y de pérdida de capacidad, con sus fechas",
                "las medidas de prevención que existían y la afiliación a la administradora"],
      fuentes=["Ley 1562 de 2012 y Decreto Ley 1295 de 1994, sistema de riesgos laborales " + VERIFICAR,
               "Ley 776 de 2002, prestaciones del sistema de riesgos laborales " + VERIFICAR,
               "Decreto 1072 de 2015 (sistema de gestión de seguridad y salud en el trabajo) y manual único de "
               "calificación vigente " + VERIFICAR,
               "Código Sustantivo del Trabajo (indemnización plena por culpa del empleador) " + VERIFICAR,
               "relatoría de la Sala de Casación Laboral y dictámenes de las juntas de calificación de invalidez"],
      entregable="análisis del siniestro laboral con el origen calificado, la pérdida de capacidad, las "
                 "prestaciones del sistema, la prueba de la culpa del empleador y los términos para controvertir",
      riesgos=["Confundir las prestaciones tarifadas del sistema con la indemnización plena, que exige probar "
               "culpa.",
               "Dejar en firme un dictamen por no controvertirlo dentro de su término."],
      comprobaciones=["Se indica la instancia de calificación en que va el caso y el término para controvertir.",
                      "La culpa del empleador se apoya en una obligación de prevención concreta y en su "
                      "incumplimiento."],
      extraer="fecha y circunstancias del evento, reporte, diagnóstico, dictámenes con porcentaje y fecha de "
              "estructuración, incapacidades, medidas de prevención y capacitaciones",
      vigencia="el manual de calificación y las reglas de prestaciones vigentes en la fecha del accidente o de "
               "la estructuración",
      preguntas="¿el evento es de origen laboral y con qué pérdida de capacidad?; ¿hubo culpa suficientemente "
                "comprobada del empleador?",
      opciones="controvertir el dictamen ante la junta, reclamar las prestaciones a la administradora, demandar "
               "la indemnización plena o reportar el incumplimiento al Ministerio del Trabajo",
      claves=["accidente de trabajo", "accidente laboral", "enfermedad laboral", "arl$", "riesgos laborales",
              "perdida de capacidad laboral", "junta de calificacion", "culpa patronal", "calificacion de origen",
              "sg-sst", "seguridad y salud en el trabajo", "me accidente trabajando", "enfermedad profesional"]),
    S("S10", "procedimiento laboral",
      tema="el procedimiento laboral y de la seguridad social (competencia, demanda, audiencias, recursos y "
           "prescripción)",
      objeto="Cubre la competencia y la cuantía, la reclamación administrativa previa, los requisitos de la "
             "demanda y su contestación, las audiencias del proceso ordinario, los recursos, la casación laboral, "
             "el ejecutivo laboral y la prescripción.",
      entradas=["las pretensiones y su valor aproximado", "contra quién se dirige la demanda y dónde se prestó "
                "el servicio", "las fechas en que se hizo exigible cada derecho y las reclamaciones ya "
                "presentadas"],
      fuentes=["Código Procesal del Trabajo y de la Seguridad Social " + VERIFICAR,
               "Código General del Proceso, Ley 1564 de 2012, en lo que el procesal laboral remite a él "
               + VERIFICAR,
               "Ley 1149 de 2007, oralidad en el proceso laboral " + VERIFICAR,
               "relatoría de la Sala de Casación Laboral de la Corte Suprema de Justicia",
               "actas del inspector del trabajo y consulta de procesos de la Rama Judicial"],
      entregable="plan procesal laboral con el juez competente, la clase de proceso por cuantía, los requisitos "
                 "previos, la prescripción de cada pretensión y la lista de pruebas por aportar o pedir",
      riesgos=["Demandar a una entidad pública sin la reclamación administrativa previa.",
               "Dejar prescribir un derecho por contar el término desde la terminación y no desde su "
               "exigibilidad."],
      comprobaciones=["La prescripción se examina pretensión por pretensión, con la fecha de exigibilidad de "
                      "cada una.",
                      "Se indica el juez competente por territorio y cuantía y si el proceso es de única o de "
                      "primera instancia."],
      extraer="pretensiones y valores, demandados, lugar de prestación del servicio, fechas de exigibilidad, "
              "reclamaciones que interrumpen la prescripción y pruebas disponibles",
      vigencia="las reglas procesales vigentes al presentarse la demanda y en cada actuación, incluidas las de "
               "justicia digital",
      preguntas="¿qué juez es competente y qué proceso corresponde?; ¿qué pretensiones están prescritas y "
                "cuáles se interrumpieron?",
      opciones="reclamación escrita que interrumpe la prescripción, conciliación ante el inspector del trabajo, "
               "demanda ordinaria de única o primera instancia o proceso ejecutivo laboral",
      claves=["demanda laboral", "juez laboral", "proceso ordinario laboral", "casacion laboral",
              "ejecutivo laboral", "prescripcion laboral", "audiencia laboral", "reclamacion administrativa",
              "demandar a mi empleador", "inspector de trabajo", "ministerio del trabajo", "conciliacion laboral"]),
]
