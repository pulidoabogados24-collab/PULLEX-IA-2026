"""A08 — Derecho penal colombiano. Fuentes: tipos de fuente oficial; los números de ley llevan «verificar vigencia».

Límite común del área: ningún perfil orienta sobre cómo cometer, ocultar o eludir un delito ni la acción de la
justicia; se analiza el derecho, no se declara culpable a nadie.
"""
from perfiles.definiciones import S, VERIFICAR

CLAVES_AREA = ["penal", "delito", "fiscalia", "codigo penal", "proceso penal"]

SUBESPECIALIDADES = [
    S("S01", "teoría del delito",
      tema="la teoría del delito (tipicidad, antijuridicidad, culpabilidad, participación y prescripción de la "
           "acción)",
      objeto="Cubre la adecuación típica objetiva y subjetiva, el dolo y la culpa, las causales de ausencia de "
             "responsabilidad, la tentativa, la autoría y la participación, el concurso y la prescripción de la "
             "acción penal.",
      entradas=["la conducta descrita con fecha, lugar, medio y resultado",
                "quién la habría realizado y con qué conocimiento o intención aparente",
                "el delito que se menciona o se imputa, si ya hay uno"],
      fuentes=["Constitución Política (legalidad, debido proceso y presunción de inocencia)",
               "Código Penal, Ley 599 de 2000, parte general y tipo penal aplicable " + VERIFICAR,
               "relatoría de la Sala de Casación Penal de la Corte Suprema de Justicia",
               "relatoría de la Corte Constitucional sobre la constitucionalidad del tipo penal",
               "SUIN-Juriscol y Secretaría del Senado para el texto vigente en la fecha de los hechos"],
      entregable="análisis dogmático por niveles: tipo objetivo, tipo subjetivo, antijuridicidad, culpabilidad, "
                 "forma de intervención y hechos que faltan para concluir",
      riesgos=["Afirmar que una persona identificada cometió un delito en lugar de analizar si la conducta "
               "descrita se adecua.",
               "Usar el tipo penal o la pena vigentes hoy para hechos anteriores a una reforma menos favorable."],
      comprobaciones=["Cada elemento del tipo se contrasta con un hecho concreto o se marca como no acreditado.",
                      "Se indica el texto del tipo penal vigente en la fecha de los hechos y la regla de "
                      "favorabilidad."],
      extraer="conducta, resultado, medio empleado, fecha y lugar, sujeto activo y pasivo, elementos subjetivos "
              "que se infieren y circunstancias que agravan o atenúan",
      vigencia="el texto del tipo penal y de la pena vigente en la fecha de la conducta, sus reformas "
               "posteriores y el principio de favorabilidad",
      preguntas="¿la conducta se adecua a un tipo penal y a cuál?; ¿concurre alguna causal que excluya la "
                "responsabilidad?",
      opciones="sostener la atipicidad, alegar una causal de ausencia de responsabilidad, discutir la forma de "
               "intervención o plantear la prescripción",
      claves=["es delito", "tipicidad", "tipo penal", "dolo$", "doloso", "culposo", "legitima defensa", "tentativa", "coautor",
              "complice", "antijuridicidad", "culpabilidad", "que delito", "se configura el delito",
              "inimputable", "estado de necesidad"]),
    S("S02", "procedimiento",
      tema="el procedimiento penal acusatorio (indagación, imputación, acusación, juicio y terminaciones "
           "anticipadas)",
      objeto="Cubre las etapas del proceso de la Ley 906, las audiencias y sus finalidades, el procedimiento "
             "abreviado y el acusador privado, los preacuerdos, el principio de oportunidad y los términos de "
             "cada etapa.",
      entradas=["la etapa en que está el proceso y la última audiencia realizada, con su fecha",
                "el delito por el que se procede y si hay persona privada de la libertad",
                "la próxima actuación programada"],
      fuentes=["Código de Procedimiento Penal, Ley 906 de 2004 " + VERIFICAR,
               "Ley 1826 de 2017, procedimiento abreviado y acusador privado " + VERIFICAR,
               "Ley 600 de 2000 para los casos que aún se rigen por ella " + VERIFICAR,
               "relatoría de la Sala de Casación Penal de la Corte Suprema de Justicia",
               "consulta de procesos y acuerdos del Consejo Superior de la Judicatura en la Rama Judicial"],
      entregable="mapa procesal con la etapa actual, lo que debe ocurrir en la siguiente audiencia, las cargas de "
                 "cada parte, los términos que corren y las salidas anticipadas disponibles",
      riesgos=["Aplicar las reglas del sistema acusatorio a un proceso que se tramita por el estatuto anterior.",
               "Dar por vencido o vigente un término sin la fecha de la actuación que lo activa."],
      comprobaciones=["Se identifica el estatuto procesal aplicable por la fecha y el lugar de los hechos.",
                      "Cada término indica la actuación que lo inicia y si hay persona privada de la libertad."],
      extraer="radicado si lo aporta el usuario, delito, fechas de captura, imputación y acusación, despacho, "
              "audiencias realizadas y pendientes",
      vigencia="el estatuto procesal que rige el caso según la fecha de los hechos y las reformas de términos "
               "vigentes en cada etapa",
      preguntas="¿en qué etapa está el proceso y qué sigue?; ¿qué terminación anticipada es viable y con qué "
                "consecuencias?",
      opciones="aceptar cargos, negociar un preacuerdo, solicitar principio de oportunidad o ir a juicio oral",
      claves=["audiencia de imputacion", "imputacion", "acusacion", "audiencia preparatoria", "juicio oral",
              "preacuerdo", "principio de oportunidad", "allanamiento a cargos", "ley 906", "etapa del proceso "
              "penal", "escrito de acusacion", "procedimiento abreviado", "querella", "preclusion"]),
    S("S03", "garantías",
      tema="las garantías penales (captura, control de garantías, medida de aseguramiento, libertad y habeas "
           "corpus)",
      objeto="Cubre la legalidad de la captura, las funciones del juez de control de garantías, los requisitos y "
             "fines de la medida de aseguramiento, su sustitución y revocatoria, la libertad por vencimiento de "
             "términos y el habeas corpus.",
      entradas=["la fecha, hora y circunstancias de la captura o de la privación de la libertad",
                "la medida impuesta y la fecha de la audiencia en que se impuso",
                "las actuaciones posteriores con sus fechas (acusación, inicio de juicio)"],
      fuentes=["Constitución Política (libertad personal, debido proceso y habeas corpus)",
               "Código de Procedimiento Penal, Ley 906 de 2004 (régimen de la libertad y su restricción) "
               + VERIFICAR,
               "Ley 1095 de 2006, habeas corpus " + VERIFICAR,
               "Convención Americana sobre Derechos Humanos (libertad personal y garantías judiciales)",
               "relatorías de la Corte Constitucional y de la Sala de Casación Penal"],
      entregable="análisis de la privación de la libertad con cronología de horas y fechas, requisito "
                 "cuestionado, causal de libertad invocada y la solicitud que procede ante el juez competente",
      riesgos=["Afirmar que un término de libertad está vencido sin descontar las demoras atribuibles a la "
               "defensa.",
               "Usar el habeas corpus para discutir lo que debe pedirse dentro del proceso."],
      comprobaciones=["La cronología indica hora y fecha de captura y de presentación ante el juez.",
                      "La causal de libertad cita su norma y el cómputo muestra las fechas de inicio y fin."],
      extraer="hora y fecha de captura, autoridad que capturó, orden o flagrancia, hora de la audiencia, medida "
              "impuesta, fines invocados y actuaciones posteriores",
      vigencia="los términos de duración de la medida y las causales de libertad vigentes en la fecha de la "
               "captura y sus reformas posteriores favorables",
      preguntas="¿la captura y su legalización respetaron la Constitución y los términos?; ¿la medida de "
                "aseguramiento sigue siendo necesaria, proporcional y está dentro de su plazo?",
      opciones="oponerse a la legalización, pedir la revocatoria o sustitución de la medida, solicitar libertad "
               "por vencimiento de términos o interponer habeas corpus",
      claves=["captura", "capturaron", "detenido", "medida de aseguramiento", "habeas corpus", "juez de control "
              "de garantias", "vencimiento de terminos", "detencion preventiva", "detencion domiciliaria",
              "legalizacion de captura", "lo tienen preso", "flagrancia", "libertad provisional"]),
    S("S04", "investigación",
      tema="la investigación penal (programa metodológico, actos de investigación y cadena de custodia)",
      objeto="Cubre la noticia criminal, el programa metodológico, los actos de investigación con y sin control "
             "judicial, la policía judicial, la recolección y custodia de elementos materiales probatorios y la "
             "investigación propia de la defensa.",
      entradas=["la noticia criminal o la hipótesis que se investiga",
                "los actos de investigación ya realizados y quién los ordenó",
                "los elementos recogidos y su registro de custodia"],
      fuentes=["Código de Procedimiento Penal, Ley 906 de 2004 (indagación, investigación y cadena de custodia) "
               + VERIFICAR,
               "manuales y resoluciones de la Fiscalía General de la Nación sobre policía judicial y cadena de "
               "custodia",
               "Constitución Política (intimidad, inviolabilidad del domicilio y de las comunicaciones)",
               "relatoría de la Sala de Casación Penal de la Corte Suprema de Justicia",
               "relatoría de la Corte Constitucional sobre actos que afectan derechos fundamentales"],
      entregable="plan de investigación con hipótesis, hechos por probar, acto de investigación para cada uno, "
                 "control judicial que exige y estado de la custodia de cada elemento",
      riesgos=["Tratar como hecho acreditado lo que solo consta en un informe o una entrevista.",
               "Practicar o aprovechar un acto que exigía control judicial previo o posterior sin tenerlo."],
      comprobaciones=["Cada acto de investigación indica si requiere control previo, posterior o ninguno, con su "
                      "norma.",
                      "Cada elemento material tiene registrada su recolección, embalaje y traspasos, o se señala "
                      "el vacío."],
      extraer="hipótesis, hechos jurídicamente relevantes, actos ordenados con fecha y autoridad, elementos "
              "recogidos, formatos de custodia y entrevistas",
      vigencia="las reglas de control judicial vigentes en la fecha de cada acto y el manual de cadena de "
               "custodia aplicable entonces",
      preguntas="¿qué hecho relevante sigue sin acto de investigación que lo sustente?; ¿algún acto afectó "
                "derechos fundamentales sin el control debido?",
      opciones="ampliar el programa metodológico, solicitar control de legalidad de lo actuado, pedir la "
               "exclusión del elemento o adelantar investigación de la defensa",
      claves=["investigacion penal", "denuncia", "denunciar", "indagacion", "policia judicial", "cadena de "
              "custodia", "allanamiento", "interceptacion", "programa metodologico", "elemento material "
              "probatorio", "noticia criminal", "me robaron", "me estafaron", "fui victima de un delito"]),
    S("S05", "prueba",
      tema="la prueba penal (descubrimiento, solicitudes, práctica en juicio, exclusión y valoración)",
      objeto="Cubre el descubrimiento probatorio, la pertinencia y admisibilidad, el testimonio y el "
             "interrogatorio cruzado, la prueba pericial y documental, la prueba de referencia, las "
             "estipulaciones y el estándar para condenar.",
      entradas=["la teoría del caso de la parte y los hechos que debe probar",
                "los medios de conocimiento disponibles y cómo se obtuvieron",
                "las pruebas anunciadas por la contraparte"],
      fuentes=["Código de Procedimiento Penal, Ley 906 de 2004 (régimen probatorio) " + VERIFICAR,
               "Constitución Política (debido proceso y exclusión de la prueba ilícita)",
               "relatoría de la Sala de Casación Penal de la Corte Suprema de Justicia",
               "relatoría de la Corte Constitucional",
               "guías técnicas del Instituto Nacional de Medicina Legal y Ciencias Forenses"],
      entregable="matriz probatoria penal: cada hecho jurídicamente relevante con su medio de prueba, el "
                 "testigo de acreditación, las objeciones previsibles y los vacíos",
      riesgos=["Llevar a juicio como prueba una entrevista o un informe que solo sirve para refrescar memoria o "
               "impugnar.",
               "Confundir un indicio con un hecho probado al valorar el conjunto."],
      comprobaciones=["Cada hecho relevante tiene al menos un medio de prueba admisible o aparece como vacío.",
                      "Cada documento o elemento indica su testigo de acreditación y su cadena de custodia."],
      extraer="hechos por probar, testigos y lo que le consta a cada uno, peritos y base de su opinión, "
              "documentos, estipulaciones y pruebas de la contraparte",
      vigencia="las reglas probatorias del estatuto procesal que rige el caso y los criterios de admisibilidad "
               "vigentes en la relatoría",
      preguntas="¿qué hecho de la teoría del caso queda sin prueba admisible?; ¿qué prueba de la contraparte "
                "puede excluirse, rechazarse o impugnarse?",
      opciones="solicitar la prueba con su pertinencia, estipular el hecho, pedir la exclusión o el rechazo, o "
               "impugnar la credibilidad en el contrainterrogatorio",
      claves=["prueba penal", "testigo", "interrogatorio", "contrainterrogatorio", "prueba de referencia",
              "prueba pericial", "descubrimiento probatorio", "exclusion de la prueba", "prueba ilicita",
              "estipulacion probatoria", "duda razonable", "dictamen de medicina legal", "valoracion probatoria"]),
    S("S06", "víctimas",
      tema="los derechos de las víctimas en el proceso penal (verdad, justicia, reparación y protección)",
      objeto="Cubre el reconocimiento como víctima, su intervención en cada etapa, las medidas de protección y "
             "de atención, el restablecimiento del derecho y el incidente de reparación integral tras la condena.",
      entradas=["el hecho sufrido, su fecha y si ya fue denunciado",
                "los daños materiales e inmateriales y sus soportes", "la etapa del proceso y si la víctima "
                "tiene quien la represente"],
      fuentes=["Constitución Política y Código de Procedimiento Penal, Ley 906 de 2004 (derechos de las víctimas "
               "e incidente de reparación) " + VERIFICAR,
               "Ley 1257 de 2008, violencias contra las mujeres " + VERIFICAR,
               "Ley 1719 de 2014, acceso a la justicia de víctimas de violencia sexual " + VERIFICAR,
               "relatoría de la Corte Constitucional sobre la participación de la víctima",
               "relatoría de la Sala de Casación Penal y rutas de atención de la Fiscalía y la Defensoría del "
               "Pueblo"],
      entregable="plan de intervención de la víctima con sus derechos en la etapa actual, las solicitudes que "
                 "puede hacer, las medidas de protección disponibles y la ruta de reparación con sus soportes",
      riesgos=["Prometer una reparación económica cuando aún no hay condena ni bienes identificados.",
               "Exponer a la víctima a repetir su relato sin necesidad o a un careo evitable."],
      comprobaciones=["Cada solicitud indica en qué etapa procede y ante quién se presenta.",
                      "El incidente de reparación se plantea solo con sentencia condenatoria en firme y dentro "
                      "de su término."],
      extraer="hecho, fecha, relación con el agresor, daños y soportes, medidas de protección pedidas u "
              "otorgadas, etapa del proceso y decisiones notificadas",
      vigencia="los derechos de intervención reconocidos a la víctima en la etapa actual según la ley y la "
               "jurisprudencia constitucional vigente",
      preguntas="¿qué puede pedir la víctima en esta etapa y ante quién?; ¿qué medidas de protección y de "
                "reparación son procedentes?",
      opciones="solicitar medidas de protección, intervenir en las audiencias por medio de representante, "
               "promover el incidente de reparación o acudir a la vía civil",
      claves=["victima", "reparacion integral", "incidente de reparacion", "medida de proteccion",
              "representante de victimas", "violencia sexual", "violencia de genero", "feminicidio",
              "me agredieron", "amenazas", "restablecimiento del derecho", "apoderado de victimas"]),
    S("S07", "defensa",
      tema="la defensa penal (teoría del caso, estrategia, negociación y actuación en audiencia)",
      objeto="Cubre el derecho a la defensa técnica y material, la construcción de la teoría del caso, la "
             "decisión entre negociar o ir a juicio, la investigación de la defensa y la intervención en cada "
             "audiencia.",
      entradas=["los hechos que la fiscalía atribuye y los que la persona reconoce o discute",
                "la etapa del proceso y lo que la fiscalía ha descubierto",
                "la situación de libertad y los antecedentes de la persona"],
      fuentes=["Constitución Política (derecho de defensa y no autoincriminación)",
               "Código de Procedimiento Penal, Ley 906 de 2004 (defensa, preacuerdos y juicio) " + VERIFICAR,
               "Código Penal, Ley 599 de 2000 (tipo imputado, punibilidad y subrogados) " + VERIFICAR,
               "Ley 941 de 2005, Sistema Nacional de Defensoría Pública " + VERIFICAR,
               "relatoría de la Sala de Casación Penal de la Corte Suprema de Justicia"],
      entregable="estrategia de defensa con la teoría del caso, los hechos por controvertir, la prueba propia, "
                 "la comparación entre negociar y ir a juicio y los riesgos de cada camino",
      riesgos=["Aconsejar una aceptación de cargos sin revisar si los hechos jurídicamente relevantes tienen "
               "soporte.",
               "Proponer ocultar, alterar pruebas o instruir testigos: es ilícito y el perfil debe negarse."],
      comprobaciones=["La comparación entre negociar y juicio indica rebaja posible, exclusiones legales y pena "
                      "probable con su fuente.",
                      "La estrategia no incluye ninguna actuación para eludir la justicia ni alterar pruebas."],
      extraer="hechos imputados, calificación jurídica, pruebas descubiertas, versión del procesado, debilidades "
              "del caso de la fiscalía y situación de libertad",
      vigencia="la pena y las rebajas vigentes en la fecha de los hechos y las prohibiciones de beneficios "
               "aplicables al delito",
      preguntas="¿cuál es la teoría del caso más sólida con la prueba disponible?; ¿conviene negociar o ir a "
                "juicio y con qué riesgo?",
      opciones="defensa de inocencia en juicio, degradación de la calificación, preacuerdo o allanamiento con "
               "rebaja, o solicitud de preclusión",
      claves=["defensa penal", "me imputaron", "me van a imputar", "teoria del caso", "defensor", "me acusan de",
              "estoy investigado", "me denunciaron", "abogado penalista", "defensa tecnica", "aceptar cargos",
              "me citaron a la fiscalia"]),
    S("S08", "recursos",
      tema="los recursos penales (reposición, apelación, queja, casación, impugnación especial y revisión)",
      objeto="Cubre la procedencia de cada recurso contra autos y sentencias, la oportunidad y la sustentación, "
             "la doble conformidad de la primera condena, la demanda de casación y sus causales, y la acción de "
             "revisión.",
      entradas=["la decisión que se quiere impugnar, con su fecha y la forma de notificación",
                "el sentido de la decisión y sus fundamentos", "el agravio concreto que causa a la parte"],
      fuentes=["Código de Procedimiento Penal, Ley 906 de 2004 (recursos, casación y revisión) " + VERIFICAR,
               "Constitución Política (doble instancia e impugnación de la primera condena), con el Acto "
               "Legislativo 01 de 2018 " + VERIFICAR,
               "relatoría de la Sala de Casación Penal de la Corte Suprema de Justicia",
               "relatoría de la Corte Constitucional sobre doble conformidad",
               "acuerdos y reglamentos de la Corte Suprema de Justicia publicados en la Rama Judicial"],
      entregable="esquema del recurso con la decisión atacada, su procedencia, el término y la forma de "
                 "sustentación, los cargos ordenados y la pretensión concreta",
      riesgos=["Sustentar fuera de término o ante quien no corresponde, lo que deja en firme la decisión.",
               "Plantear en casación un alegato de instancia sin ajustarlo a una causal."],
      comprobaciones=["Se indica el recurso procedente, su norma, el término y la fecha desde la que corre.",
                      "Cada cargo identifica el error, la norma infringida y su trascendencia en la decisión."],
      extraer="tipo y fecha de la decisión, forma de notificación, instancia, fundamentos, agravios y recursos "
              "ya interpuestos",
      vigencia="las reglas de recursos y de casación vigentes en la fecha de la decisión impugnada",
      preguntas="¿qué recurso procede y hasta cuándo?; ¿qué error concreto de la decisión puede demostrarse y "
                "cómo incide en el resultado?",
      opciones="reposición, apelación, impugnación especial de la primera condena, casación o acción de revisión",
      claves=["apelacion penal", "apelar la condena", "casacion penal", "recurso contra la sentencia penal",
              "doble conformidad", "impugnacion especial", "accion de revision", "apelar la sentencia",
              "segunda instancia penal", "me condenaron", "sustentar el recurso"]),
    S("S09", "ejecución de penas",
      tema="la ejecución de la pena (subrogados, prisión domiciliaria, redención, libertad condicional y "
           "extinción)",
      objeto="Cubre la competencia del juez de ejecución de penas, el cómputo de la pena cumplida, la redención "
             "por trabajo, estudio o enseñanza, la prisión domiciliaria, la libertad condicional, las exclusiones "
             "legales y la extinción de la sanción.",
      entradas=["la sentencia: delito, pena impuesta y fecha de ejecutoria",
                "el tiempo en detención y los certificados de redención reconocidos",
                "el beneficio que se quiere pedir y la conducta en reclusión"],
      fuentes=["Código Penal, Ley 599 de 2000 (mecanismos sustitutivos y exclusiones) " + VERIFICAR,
               "Ley 65 de 1993, Código Penitenciario y Carcelario, con la reforma de la Ley 1709 de 2014 "
               + VERIFICAR,
               "Código de Procedimiento Penal, Ley 906 de 2004 (ejecución de la sentencia) " + VERIFICAR,
               "relatoría de la Sala de Casación Penal y de la Corte Constitucional",
               "resoluciones del INPEC sobre certificación de trabajo, estudio y conducta"],
      herramientas={"calculadora_liquidaciones": "F07 F08"},
      entregable="solicitud de ejecución de penas con el cómputo de tiempo físico y redimido, el requisito "
                 "objetivo cumplido, los factores subjetivos, la exclusión legal revisada y los anexos",
      riesgos=["Sumar tiempo de redención no reconocido por el juez o calculado con una regla de otro período.",
               "Pedir un beneficio excluido por la ley para el delito de la condena."],
      comprobaciones=["El cómputo separa tiempo físico y tiempo redimido, con fechas y soportes de cada tramo.",
                      "Se verifica si el delito está excluido del beneficio en la norma vigente en la fecha de "
                      "los hechos."],
      extraer="delito, pena, fechas de captura y de ejecutoria, tiempo en detención, redenciones reconocidas, "
              "calificación de conducta, arraigo y pago de perjuicios",
      vigencia="los requisitos y exclusiones del beneficio vigentes en la fecha de los hechos y las reformas "
               "posteriores más favorables",
      preguntas="¿se cumple el requisito de tiempo del beneficio?; ¿el delito o los antecedentes excluyen el "
                "subrogado?",
      opciones="redención de pena, prisión domiciliaria, libertad condicional, permiso administrativo o "
               "acumulación jurídica de penas",
      claves=["ejecucion de penas", "libertad condicional", "prision domiciliaria", "redencion de pena",
              "juez de ejecucion", "subrogado", "casa por carcel", "inpec", "permiso de 72 horas",
              "tres quintas partes", "extincion de la pena", "acumulacion de penas", "condenado"]),
    S("S10", "delitos informáticos",
      tema="los delitos informáticos y la evidencia digital (acceso abusivo, datos personales, fraude por "
           "medios informáticos)",
      objeto="Cubre los tipos que protegen la información y los datos, el hurto y la transferencia no consentida "
             "por medios informáticos, la suplantación de sitios, y la obtención, preservación y autenticidad de "
             "la evidencia digital.",
      entradas=["qué ocurrió, por qué medio (cuenta, aplicación, sitio, dispositivo) y cuándo",
                "las evidencias conservadas (capturas, correos con cabeceras, registros, extractos)",
                "el perjuicio causado y la entidad o plataforma involucrada"],
      fuentes=["Código Penal, Ley 599 de 2000, título de la protección de la información y de los datos, "
               "adicionado por la Ley 1273 de 2009 " + VERIFICAR,
               "Ley 527 de 1999, mensajes de datos y su fuerza probatoria " + VERIFICAR,
               "Ley 1581 de 2012, protección de datos personales " + VERIFICAR,
               "Convenio de Budapest sobre ciberdelincuencia, aprobado por la Ley 1928 de 2018 " + VERIFICAR,
               "relatoría de la Sala de Casación Penal y guías de la Fiscalía y del Centro Cibernético Policial "
               "sobre evidencia digital"],
      entregable="análisis del incidente con la conducta y su posible adecuación típica, la evidencia digital "
                 "existente, lo que debe preservarse de inmediato y la ruta de denuncia y de reclamación",
      riesgos=["Dar por auténtica una captura de pantalla sin metadatos ni forma de verificar su integridad.",
               "Recomendar acceder a la cuenta o al equipo del presunto autor para «recuperar» pruebas: es un "
               "delito."],
      comprobaciones=["Cada evidencia digital indica su origen, fecha, forma de obtención y cómo se preserva su "
                      "integridad.",
                      "La adecuación típica distingue el tipo informático del delito común cometido por medio "
                      "informático."],
      extraer="fecha y hora del incidente, cuentas y dispositivos afectados, movimientos o accesos, evidencias y "
              "su formato, reportes hechos al banco o a la plataforma",
      vigencia="los tipos penales informáticos vigentes en la fecha del hecho y los términos de reclamación "
               "ante la entidad financiera o la plataforma",
      preguntas="¿qué tipo penal protege el bien afectado y concurre con otro delito?; ¿la evidencia digital es "
                "auténtica, íntegra y se obtuvo lícitamente?",
      opciones="preservar y denunciar ante la Fiscalía, reclamar a la entidad financiera, acudir a la autoridad "
               "de protección de datos o solicitar medidas de restablecimiento",
      claves=["delito informatico", "hackearon", "hackeo", "phishing", "suplantacion", "acceso abusivo",
              "robo por internet", "transferencia no consentida", "evidencia digital", "ciberdelito",
              "me vaciaron la cuenta", "fraude electronico", "violacion de datos personales", "ransomware"]),
]
