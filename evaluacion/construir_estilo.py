"""Genera evaluacion/estilo.jsonl: 20 textos escritos para PULLEX (10 con rasgos de IA y 10 humanos bien
escritos) para medir el detector de estilo (estilo_redaccion.rasgos_ia). Todos los textos son originales,
con hechos y nombres ficticios. Los números de normas y sentencias son de uso corriente y solo ilustran el
estilo: no son material jurídico verificado.

    python evaluacion/construir_estilo.py      → reescribe evaluacion/estilo.jsonl
"""
import json
from pathlib import Path

IA = [
    ("chat_ciudadano", ["apertura_relleno", "emoji", "cierre_servicial"],
     "¡Excelente pregunta! 😊 Te explico de manera clara cómo funciona el derecho de petición en Colombia.\n\n"
     "El derecho de petición es una herramienta fundamental que te permite dirigirte a las autoridades y "
     "obtener una respuesta de fondo. Las entidades deben responder dentro de los términos legales.\n\n"
     "✅ Puedes presentarlo por escrito o de forma verbal.\n✅ No necesitas abogado.\n\n"
     "Espero que esta información te sea útil. Si tienes más preguntas, no dudes en escribirme."),
    ("examen_estudiante", ["importante_destacar", "cabe_destacar", "cierre_resumen", "no_solo_sino"],
     "El problema jurídico consiste en determinar si Laura puede reclamar la indemnización por despido sin "
     "justa causa. Es importante destacar que el contrato era a término indefinido y que la empresa no invocó "
     "ninguna causal.\n\n"
     "Cabe resaltar que el Código Sustantivo del Trabajo regula la terminación unilateral del contrato. La "
     "empresa no solo omitió la carta de terminación, sino también desconoció el procedimiento interno.\n\n"
     "Por otro lado, la empresa alega que Laura llegó tarde varias veces. Sin embargo, no hubo llamado de "
     "atención ni descargos.\n\n"
     "En conclusión, Laura tiene derecho a la indemnización, ya que la terminación fue unilateral y sin justa causa."),
    ("concepto_formato", ["titulo_mayusculas", "negritas", "vinetas", "titulos_respuesta_corta"],
     "## Análisis Del Caso Concreto\n\n"
     "La **acción de tutela** es **procedente** cuando existe una **vulneración** de **derechos fundamentales**.\n\n"
     "## Requisitos De Procedencia\n\n"
     "- Legitimación por activa\n- Legitimación por pasiva\n- Subsidiariedad\n- Inmediatez\n- Relevancia constitucional\n"
     "- Perjuicio irremediable\n\n"
     "## Conclusión Final\n\n"
     "La tutela **procede** en este caso."),
    ("chat_guiones", ["guion_largo", "papel_fundamental", "pregunta_retorica"],
     "La conciliación extrajudicial — en muchos asuntos civiles — es requisito antes de demandar. ¿La razón? "
     "El legislador quiso descongestionar los despachos y darles a las partes una oportunidad de acuerdo.\n\n"
     "El conciliador juega un papel fundamental — dirige la audiencia y levanta el acta. Si no hay acuerdo, se "
     "expide una constancia que permite acudir al juez."),
    ("chat_entusiasta", ["apertura_relleno", "exclamaciones", "verbo_ia", "anuncio"],
     "¡Claro que sí! Profundicemos en el tema de la prescripción adquisitiva. A continuación te explico los "
     "puntos clave.\n\n"
     "La prescripción adquisitiva permite adquirir el dominio de un bien por haberlo poseído durante el tiempo "
     "que exige la ley. ¡Es una figura muy interesante! La posesión debe ser pública, pacífica e "
     "ininterrumpida.\n\n"
     "¡Ojo con los tiempos! La ley distingue entre la prescripción ordinaria y la extraordinaria."),
    ("explicacion_cliche", ["mundo_actual", "es_fundamental", "adjetivo_ia", "sin_duda", "ambito"],
     "En el mundo actual, la protección de los datos personales se ha convertido en un tema crucial. Es "
     "fundamental entender que en el ámbito de la Ley 1581 de 2012 el titular tiene derecho a conocer, "
     "actualizar y rectificar su información.\n\n"
     "Sin lugar a dudas, las empresas deben contar con una política de tratamiento y con la autorización del "
     "titular. La Superintendencia de Industria y Comercio vigila el cumplimiento de estas reglas y puede "
     "imponer sanciones."),
    ("memorial_ia", ["quedo_atento", "negritas", "guion_largo"],
     "Señor juez, respetuosamente me permito solicitar el **aplazamiento** de la audiencia programada para el "
     "**15 de marzo**, toda vez que el apoderado tiene otra diligencia — previamente fijada — en un juzgado de "
     "otra ciudad. Adjunto la **constancia** correspondiente y solicito fijar **nueva fecha**.\n\n"
     "Quedo atento a cualquier inquietud."),
    ("respuesta_triadas", ["triadas", "enfoque_integral", "abanico", "no_solo_sino"],
     "El proceso de alimentos exige un enfoque integral, humano y responsable. El juez valora las necesidades, "
     "la capacidad económica y la proporcionalidad. También tiene en cuenta la edad, la salud y la educación "
     "del menor, así como un amplio abanico de pruebas documentales, testimoniales y periciales.\n\n"
     "La cuota no solo cubre la comida, sino también la vivienda, el vestuario y la recreación."),
    ("ia_sutil", ["importante_destacar", "orden_de_ideas", "cierre_servicial"],
     "La caducidad del medio de control de reparación directa es de dos años, contados desde el día siguiente "
     "a la ocurrencia del daño o desde que la víctima tuvo conocimiento de él (pendiente de verificación).\n\n"
     "En ese orden de ideas, es importante tener en cuenta que la solicitud de conciliación suspende el término "
     "mientras se tramita.\n\n"
     "Espero haberte ayudado con tu consulta."),
    ("ia_lista_corta", ["vinetas", "emoji", "autoidentificacion"],
     "Como inteligencia artificial, no puedo darte asesoría legal, pero te dejo los pasos:\n\n"
     "- Reúne las pruebas 📁\n- Redacta los hechos\n- Identifica a la entidad\n- Presenta la tutela\n"
     "- Espera el fallo\n- Impugna si pierdes\n- Pide el desacato si no cumplen"),
]

HUMANO = [
    ("examen_estudiante",
     "El problema jurídico es si la EPS vulneró el derecho a la salud de Martha al negarle un medicamento "
     "formulado por su médico tratante con el argumento de que no está en el plan de beneficios.\n\n"
     "La acción de tutela procede porque Martha no cuenta con otro medio judicial eficaz para obtener el "
     "medicamento con la urgencia que exige su tratamiento. El mecanismo ante la Superintendencia de Salud "
     "existe, pero no resuelve a tiempo un caso en el que la interrupción del tratamiento pone en riesgo su "
     "vida. La inmediatez también se cumple: la negativa ocurrió hace tres semanas.\n\n"
     "En cuanto al fondo, la Corte Constitucional ha sostenido que el concepto del médico tratante prevalece "
     "sobre las consideraciones administrativas de la EPS, de modo que la exclusión del plan no es razón "
     "suficiente para negar el servicio. La EPS podría alegar que existe un medicamento sustituto; sin "
     "embargo, el médico descartó esa alternativa por razones clínicas que constan en la historia.\n\n"
     "Por tanto, considero que el juez debe amparar el derecho a la salud y ordenar la entrega del medicamento."),
    ("concepto_abogado",
     "Usted pregunta si puede terminar el contrato de arrendamiento del local antes del vencimiento sin pagar "
     "indemnización. La respuesta corta es no, salvo que el arrendador haya incumplido o que el contrato le "
     "conceda esa facultad.\n\n"
     "El contrato que nos envió fija un término de tres años y no contiene cláusula de terminación anticipada "
     "a favor del arrendatario. Tampoco encontramos en los hechos un incumplimiento del arrendador: las goteras "
     "que usted menciona fueron reparadas dentro del mes siguiente al aviso.\n\n"
     "Si decide entregar el local, el arrendador podrá cobrarle la cláusula penal pactada, que equivale a dos "
     "cánones. Recomendamos proponerle una terminación de mutuo acuerdo antes de entregar, por escrito y con "
     "una fecha cierta."),
    ("tutela_hechos",
     "## HECHOS\n\n"
     "1. El 3 de febrero de 2026 radiqué ante la Alcaldía de Soacha un derecho de petición en el que solicité "
     "copia del expediente de la licencia de construcción del predio vecino.\n\n"
     "2. La Alcaldía no ha respondido, pese a que el término legal para hacerlo ya venció.\n\n"
     "3. El 10 de marzo de 2026 envié un correo electrónico para pedir información sobre el trámite. Tampoco "
     "recibí respuesta.\n\n"
     "4. Necesito los documentos para presentar una queja ante la curaduría, porque la obra invade el lindero "
     "de mi casa."),
    ("chat_ciudadano",
     "Sí puedes reclamar, y lo primero es pedirle por escrito a la tienda que te cambie el celular o te "
     "devuelva el dinero. Como el equipo falló a las dos semanas de comprado, está dentro de la garantía legal.\n\n"
     "Escribe una carta corta con la fecha de compra, el número de la factura y lo que pasó con el equipo, y "
     "guarda una copia con el sello de recibido. La tienda tiene un plazo para responder; si no lo hace o se "
     "niega, puedes presentar una queja ante la Superintendencia de Industria y Comercio, que es gratuita y no "
     "necesita abogado.\n\n"
     "Esto es orientación general, no asesoría jurídica personalizada; para tu caso concreto consulta a un abogado."),
    ("memorial_abogado",
     "Señora jueza:\n\n"
     "Como apoderado de la parte demandante, solicito respetuosamente que se aplace la audiencia inicial "
     "fijada para el 15 de marzo de 2026. Ese mismo día debo asistir a una audiencia de juicio oral en Tunja, "
     "programada con anterioridad, según la constancia que adjunto.\n\n"
     "Pido que la nueva fecha se fije a partir del 1 de abril.\n\n"
     "Atentamente,"),
    ("explicacion_estudio",
     "La diferencia entre prescripción y caducidad se entiende mejor con un ejemplo. Si un trabajador deja "
     "pasar el tiempo sin reclamar sus cesantías, el empleador puede alegar la prescripción como excepción, y "
     "el juez solo la declara si se la proponen. Ese término, además, se interrumpe con un simple reclamo "
     "escrito.\n\n"
     "La caducidad funciona de otra manera. Si alguien quiere demandar la nulidad de un acto administrativo y "
     "deja vencer el plazo, el juez debe rechazar la demanda aunque la entidad no diga nada, porque el término "
     "es de orden público y no admite interrupción. Por eso se dice que la caducidad mira a la acción y la "
     "prescripción mira al derecho."),
    ("respuesta_corta",
     "No. El cheque posfechado se puede cobrar antes de la fecha que tiene escrita, porque la ley considera "
     "que es pagadero a la vista. Si el banco lo paga, el girador no puede reclamarle por haberlo hecho."),
    ("examen_penal",
     "Debe establecerse si la conducta de Andrés, que tomó el celular olvidado en una mesa del restaurante y "
     "se lo llevó, encaja en el hurto o en otra figura.\n\n"
     "A mi juicio se configura el hurto. Andrés se apoderó de una cosa mueble ajena con el propósito de "
     "obtener provecho, y el hecho de que el dueño la hubiera olvidado no la convierte en cosa abandonada: "
     "el teléfono seguía en el lugar donde su dueño lo dejó, que podía volver por él en cualquier momento.\n\n"
     "La defensa podría sostener que se trató de un aprovechamiento de cosa extraviada, que tiene una pena "
     "menor. Ese argumento pierde fuerza porque el bien no estaba perdido en sentido jurídico; el dueño sabía "
     "dónde lo había dejado y regresó a los diez minutos.\n\n"
     "La conducta es típica de hurto simple, sin perjuicio de revisar si el valor del celular permite aplicar "
     "alguna rebaja."),
    ("correo_profesional",
     "Doctor Ramírez, buenos días.\n\n"
     "Le confirmo que radicamos ayer la contestación de la demanda dentro del término. Propusimos la excepción "
     "de pago parcial y pedimos el interrogatorio del representante legal de la demandante.\n\n"
     "El juzgado aún no ha fijado fecha para la audiencia inicial. Le aviso en cuanto salga el auto.\n\n"
     "Cordialmente,\nCatalina Gómez"),
    ("concepto_tecnico",
     "La Ley 1258 de 2008 permite que la sociedad por acciones simplificada se constituya por documento "
     "privado, siempre que los activos aportados no incluyan bienes cuya transferencia exija escritura "
     "pública. En el caso consultado, uno de los socios pretende aportar un apartamento, de modo que la "
     "constitución deberá hacerse por escritura y registrarse también en la oficina de instrumentos públicos.\n\n"
     "Recomendamos, además, revisar la cláusula de objeto social. El borrador enumera actividades muy "
     "específicas; la ley admite un objeto indeterminado, que evitaría reformas estatutarias futuras si la "
     "empresa amplía su negocio."),
]


def construir() -> list:
    filas = []
    for n, (genero, esperados, texto) in enumerate(IA, 1):
        filas.append({"id": f"ia{n:02d}", "etiqueta": "ia", "genero": genero, "rasgos_esperados": esperados,
                      "texto": texto})
    for n, (genero, texto) in enumerate(HUMANO, 1):
        filas.append({"id": f"hu{n:02d}", "etiqueta": "humano", "genero": genero, "rasgos_esperados": [],
                      "texto": texto})
    return filas


if __name__ == "__main__":
    destino = Path(__file__).resolve().parent / "estilo.jsonl"
    with destino.open("w", encoding="utf-8") as f:
        for fila in construir():
            f.write(json.dumps(fila, ensure_ascii=False) + "\n")
    print(f"{destino}: {len(construir())} textos")
