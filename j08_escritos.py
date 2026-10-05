"""J08 — Generación y revisión de escritos.

Dos piezas deterministas alrededor del generador de documentos.py (que es quien llama al modelo de IA):

1. `preparar(entrada)`: antes de generar exige modelo seleccionado, datos válidos, hechos CONFIRMADOS por el
   usuario y fuentes (o la declaración expresa de que no hay). Si falta algo, se abstiene.
2. `verificar_escrito(texto, entradas, fuentes)`: después de generar, busca en el borrador nombres, cédulas,
   radicados, fechas, valores, normas y sentencias que NO estaban en las entradas ni en las fuentes (posible
   invención) y reúne los campos pendientes («<<<VERIFICAR>>>» y «[COMPLETAR: …]»).

El verificador trabaja por patrones: puede dar falsos positivos (por eso dice «posible») y puede no ver una
invención redactada de otra forma. Que un dato esté en las entradas no prueba que sea cierto ni que la cita sea
correcta: solo que no lo inventó el generador.
"""
import re
import unicodedata
from datetime import date

import documentos

VERSION = "1.0.0"
PROCEDIMIENTO = "J08"
MAX_TEXTO = 120000
MAX_HALLAZGOS = 120
MESES = {m: i for i, m in enumerate(documentos.MESES, 1)}
MESES["setiembre"] = 9

_MAY = "A-ZÁÉÍÓÚÑÜ"
_MIN = "a-záéíóúñü"
_RE_SENT_CC = re.compile(r"(?<![A-Za-z0-9])(C|T|SU)\s?[-–]\s?(\d{1,4})[A-Z]?\s*(?:de|/)\s*(\d{4}|\d{2})(?!\d)")
_RE_SENT_CSJ = re.compile(r"(?<![A-Za-z0-9])(SL|SC|SP|STC|STL|STP|AL|AC|AP)\s?(\d{2,6})\s?[-–]\s?(\d{4})(?!\d)")
_RE_NORMA = re.compile(r"\b(Ley|Decreto(?:[\s-]+Ley|\s+Legislativo)?|Resoluci[oó]n|Acuerdo|Circular)\s+"
                       r"(?:Estatutaria\s+|Org[aá]nica\s+)?(?:n[úu]mero\s+|N[o°º]\.?\s*)?(\d{1,5})\s+de(?:l)?\s+(\d{4})\b",
                       re.I)
_RE_ARTS = re.compile(r"\b(?:art[íi]culos?|arts?\.)\s*((?:\d{1,4}\s*[A-Z]?\b(?:\s*(?:,|y|e|o|al?)\s*)?)+)", re.I)
_RE_RAD23 = re.compile(r"(?<!\d)(\d{5}[-\s.]?\d{2}[-\s.]?\d{2}[-\s.]?\d{3}[-\s.]?\d{4}[-\s.]?\d{5}[-\s.]?\d{2})(?!\d)")
_RE_RAD = re.compile(r"\b(?:radicad[oa]|radicaci[oó]n|expediente|rad\.)\s*(?:n[úu]mero|N[o°º]\.?)?\s*[:#]?\s*"
                     r"(\d[0-9A-Za-z.\-/]{3,40})", re.I)
_RE_IDENT = re.compile(r"(?<![A-Za-z])(?:C\.\s?C\.|CC|c[ée]dula(?:\s+de\s+ciudadan[íi]a)?|NIT|T\.\s?I\.|C\.\s?E\.|"
                       r"T\.\s?P\.|tarjeta\s+profesional)\s*(?:n[úu]mero|N[o°º]\.?)?\s*[:#]?\s*(\d[\d.\s-]{4,16}\d)", re.I)
_RE_FECHA_LARGA = re.compile(r"\b(\d{1,2})\s*(?:°|º)?\s+de\s+([a-záéíóú]+)\s+(?:de(?:l)?\s+)?(\d{4})\b", re.I)
_RE_FECHA_NUM = re.compile(r"(?<![\d/-])(\d{1,2})[/-](\d{1,2})[/-](\d{4})(?![\d/-])")
_RE_FECHA_ISO = re.compile(r"(?<![\d-])(\d{4})-(\d{2})-(\d{2})(?![\d-])")
_RE_MONTO = re.compile(r"\$\s?(\d[\d.,]*\d|\d)")
_RE_CORREO = re.compile(r"\b[\w.+-]+@[\w-]+(?:\.[\w-]+)+\b")
_RE_TEL = re.compile(r"(?<!\d)(3\d{2}[\s-]?\d{3}[\s-]?\d{4}|60\d[\s-]?\d{3}[\s-]?\d{4})(?!\d)")
_RE_NOMBRE = re.compile(
    rf"\b[{_MAY}][{_MIN}]+(?:(?:\s+(?:de|del|la|las|los|y|e)){{0,2}}\s+[{_MAY}][{_MIN}]+){{1,4}}")
_RE_NOMBRE_MAY = re.compile(rf"\b[{_MAY}]{{3,}}(?:\s+(?:DE|DEL|LA|LAS|LOS|Y))?(?:\s+[{_MAY}]{{2,}}){{1,4}}\b")
_INICIALES = {"el", "la", "los", "las", "en", "por", "con", "de", "se", "que", "al", "del", "para", "como", "segun",
              "ante", "sin", "sobre", "este", "esta", "estos", "estas", "un", "una", "lo", "su", "sus", "mi",
              "yo", "no", "si", "es", "a", "y", "o", "e", "dicho", "dicha", "tal", "todo", "toda", "cuando",
              "desde", "hasta", "entre", "mediante", "conforme", "respetado", "respetada", "respetados", "senor",
              "senora", "senores", "doctor", "doctora", "honorable", "honorables", "atentamente", "cordialmente"}
# Vocabulario jurídico y de forma: una secuencia hecha solo de estas palabras no es un nombre de persona.
_VOCABULARIO = set("""
accion acciones tutela peticion derecho derechos fundamental fundamentales hecho hechos pretension pretensiones
fundamento fundamentos prueba pruebas anexo anexos notificacion notificaciones juramento firma lugar fecha
referencia asunto proceso procesos demanda demandante demandado demandada accionante accionado accionada
solicitante peticionario apoderado apoderada poderdante juez jueza juzgado juzgados tribunal tribunales sala
seccion corte suprema justicia constitucional consejo estado superior judicatura republica colombia nacional
nacionales nacion general generales codigo civil penal laboral comercio comercial procedimiento procesal
administrativo contencioso sustantivo trabajo seguridad social constitucion politica ley leyes decreto decretos
articulo articulos numeral paragrafo inciso literal capitulo titulo libro parte primera segunda tercera cuarta
quinta primero segundo tercero cuarto quinto sexto septimo octavo noveno decimo municipal circuito distrito
judicial promiscuo familia oral pequenas causas competencia multiple reparto secretaria despacho ministerio
publico superintendencia financiera industria salud proteccion fiscalia procuraduria defensoria pueblo
contraloria registraduria policia direccion impuestos aduanas instituto colombiano bienestar familiar
administradora pensiones alcaldia gobernacion departamento municipio notaria camara registro instrumentos
publicos entidad promotora diario oficial estatuto tributario consumidor regimen politico infancia adolescencia
senor senora senores doctor doctora honorable respetado respetada cordial saludo atentamente ciudad
borrador proyecto revision funcionario competente verificar completar vigencia documento escrito memorial recurso
reposicion apelacion nulidad restablecimiento reparacion directa ejecutivo ejecutiva verbal sumario monitorio
medida medidas provisional cautelar cautelares subsidiariedad inmediatez legitimacion activa pasiva procedencia
identificacion partes parte consideraciones resuelve resuelva ordena ordenar conceder amparar tutelar negar
declarar vulnerado vulnerados vulneracion vida digna minimo vital debido igualdad dignidad humana informacion
habeas data corpus servicio servicios domiciliarios contrato contratos arrendamiento compraventa prestacion
empresa sociedad anonima simplificada limitada acciones bogota medellin cali barranquilla cartagena santa marta
enero febrero marzo abril mayo junio julio agosto septiembre octubre noviembre diciembre lunes martes miercoles
jueves viernes sabado domingo cedula ciudadania tarjeta profesional numero pesos moneda corriente
""".split())


def _norm(texto) -> str:
    t = unicodedata.normalize("NFD", str(texto or "").lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9ñ]+", " ", t).strip()


def _aplanar(valor) -> str:
    if valor is None:
        return ""
    if isinstance(valor, dict):
        return "\n".join(_aplanar(v) for v in valor.values())
    if isinstance(valor, (list, tuple)):
        return "\n".join(_aplanar(v) for v in valor)
    return str(valor)


def _digitos(s) -> str:
    return re.sub(r"\D", "", str(s))


def _fecha_iso(d, m, a):
    try:
        return date(int(a), int(m), int(d)).isoformat()
    except ValueError:
        return None


def _fechas(texto: str) -> list:
    salida = []
    for mt in _RE_FECHA_LARGA.finditer(texto):
        mes = MESES.get(_norm(mt.group(2)))
        if mes:
            salida.append((mt.group(0), _fecha_iso(mt.group(1), mes, mt.group(3)), mt.start()))
    for mt in _RE_FECHA_NUM.finditer(texto):
        salida.append((mt.group(0), _fecha_iso(mt.group(1), mt.group(2), mt.group(3)), mt.start()))
    for mt in _RE_FECHA_ISO.finditer(texto):
        salida.append((mt.group(0), _fecha_iso(mt.group(3), mt.group(2), mt.group(1)), mt.start()))
    return salida


def _anio4(a: str) -> int:
    n = int(a)
    return n if n > 99 else (1900 + n if n >= 92 else 2000 + n)


def _sentencias(texto: str) -> list:
    s = [(m.group(0), f"{m.group(1).upper()}-{int(m.group(2))}-{_anio4(m.group(3))}", m.start())
         for m in _RE_SENT_CC.finditer(texto)]
    s += [(m.group(0), f"{m.group(1).upper()}{int(m.group(2))}-{m.group(3)}", m.start())
          for m in _RE_SENT_CSJ.finditer(texto)]
    return s


def _normas(texto: str) -> list:
    salida = []
    for m in _RE_NORMA.finditer(texto):
        tipo = _norm(m.group(1)).split()[0]
        salida.append((m.group(0), f"{tipo} {int(m.group(2))} {m.group(3)}", m.start()))
    return salida


def _articulos(texto: str) -> list:
    salida = []
    for m in _RE_ARTS.finditer(texto):
        for n in re.findall(r"\d{1,4}", m.group(1)):
            salida.append((f"artículo {n}", n, m.start()))
    return salida


def _radicados(texto: str) -> list:
    r = [(m.group(1), _digitos(m.group(1)), m.start()) for m in _RE_RAD23.finditer(texto)]
    vistos = {k for _, k, _ in r}
    for m in _RE_RAD.finditer(texto):
        clave = re.sub(r"[^0-9a-z]", "", m.group(1).lower())
        if len(_digitos(clave)) >= 4 and clave not in vistos and not any(clave in v or v in clave for v in vistos):
            r.append((m.group(1).rstrip(".,;"), clave, m.start()))
    return r


def _identificaciones(texto: str) -> list:
    return [(m.group(0).strip(), _digitos(m.group(1)), m.start()) for m in _RE_IDENT.finditer(texto)
            if len(_digitos(m.group(1))) >= 5]


def _montos(texto: str) -> list:
    salida = []
    for m in _RE_MONTO.finditer(texto):
        bruto = m.group(1)
        entero = re.split(r",\d{1,2}$", bruto)[0] if re.search(r",\d{1,2}$", bruto) else bruto
        entero = re.split(r"\.\d{1,2}$", entero)[0] if re.search(r"\.\d{1,2}$", entero) and "," in bruto else entero
        clave = _digitos(entero)
        if len(clave) >= 4:
            salida.append((m.group(0), clave, m.start()))
    return salida


def _numeros_base(texto: str) -> set:
    """Todos los números de la base, sin separadores, para comparar valores, cédulas y radicados."""
    nums = set()
    for m in re.finditer(r"\d[\d.,\s-]*\d|\d", texto):
        bruto = m.group(0)
        nums.add(_digitos(bruto))
        nums.add(_digitos(re.sub(r"[.,]\d{1,2}$", "", bruto)))
        for trozo in re.split(r"[\s-]+", bruto):
            nums.add(_digitos(trozo))
    nums.discard("")
    return nums


def _nombres(texto: str) -> list:
    salida, vistos = [], set()
    for patron in (_RE_NOMBRE, _RE_NOMBRE_MAY):
        for m in patron.finditer(texto):
            palabras = m.group(0).split()
            while palabras and _norm(palabras[0]) in _INICIALES:
                palabras = palabras[1:]
            sig = [_norm(p) for p in palabras if _norm(p) not in ("de", "del", "la", "las", "los", "y", "e")]
            if len(sig) < 2 or all(p in _VOCABULARIO for p in sig):
                continue
            # Se recortan del borde las palabras de forma («Señor Juan Pérez» → «Juan Pérez»).
            while sig and sig[0] in _VOCABULARIO:
                sig = sig[1:]
            while sig and sig[-1] in _VOCABULARIO:
                sig = sig[:-1]
            if len(sig) < 2:
                continue
            clave = " ".join(sig)
            if clave in vistos:
                continue
            vistos.add(clave)
            salida.append((" ".join(palabras), clave, m.start()))
    return salida


def _contexto(texto: str, pos: int, largo: int = 70) -> str:
    return re.sub(r"\s+", " ", texto[max(0, pos - largo): pos + largo]).strip()


CATEGORIAS = {
    "sentencia": ("Sentencia citada que no está en las fuentes", "alta"),
    "norma": ("Norma citada que no está en las fuentes ni en el modelo", "alta"),
    "articulo": ("Artículo citado que no está en las fuentes ni en el modelo", "media"),
    "radicado": ("Radicado o expediente que no está en las entradas", "alta"),
    "identificacion": ("Número de identificación que no está en las entradas", "alta"),
    "fecha": ("Fecha que no está en las entradas ni en las fuentes", "media"),
    "valor": ("Valor en pesos que no está en las entradas", "media"),
    "contacto": ("Correo o teléfono que no está en las entradas", "alta"),
    "nombre": ("Nombre propio que no está en las entradas", "media"),
}


def verificar_escrito(texto: str, entradas=None, fuentes=None, tipo_id: str = None, hoy: date = None) -> dict:
    """Detector determinista de posibles invenciones y de campos pendientes en un borrador."""
    texto = str(texto or "")
    if not texto.strip():
        return {"procedimiento": PROCEDIMIENTO, "version": VERSION, "estado": "ABSTENCION",
                "faltantes": ["texto: el borrador que se va a revisar"], "posibles_invenciones": [], "pendientes": []}
    recortado = len(texto) > MAX_TEXTO
    texto = texto[:MAX_TEXTO]
    cuerpo, pendientes = documentos.separar_respuesta(texto)
    hoy = hoy or documentos.hoy_colombia().date()
    tipo = documentos.INDICE.get(str(tipo_id or ""))
    base_entradas = _aplanar(entradas)
    base_fuentes = _aplanar(fuentes)
    base_modelo = _aplanar([tipo["nombre"], tipo["descripcion"], tipo["estructura"], tipo["notas_de_forma"],
                            tipo["advertencias"]]) if tipo else ""
    base_datos = base_entradas + "\n" + base_fuentes               # hechos, personas, fechas, valores
    base_citas = base_datos + "\n" + base_modelo                   # normas: también valen las del modelo
    norm_datos = " " + _norm(base_datos) + " "
    palabras_datos = set(norm_datos.split())
    numeros = _numeros_base(base_datos)
    fechas_ok = {iso for _, iso, _ in _fechas(base_datos) if iso} | {hoy.isoformat()}
    normas_ok = {k for _, k, _ in _normas(base_citas)}
    arts_ok = {k for _, k, _ in _articulos(base_citas)}
    sent_ok = {k for _, k, _ in _sentencias(base_citas)}
    correos_ok = {c.lower() for c in _RE_CORREO.findall(base_datos)}

    hallazgos, respaldadas, vistos = [], [], set()

    def hallazgo(cat, valor, pos, extra=""):
        if (cat, valor) in vistos or len(hallazgos) >= MAX_HALLAZGOS:
            return
        vistos.add((cat, valor))
        motivo, confianza = CATEGORIAS[cat]
        hallazgos.append({"categoria": cat, "valor": valor, "motivo": motivo + extra, "confianza": confianza,
                          "contexto": _contexto(cuerpo, pos)})

    for bruto, clave, pos in _sentencias(cuerpo):
        (respaldadas.append(bruto) if clave in sent_ok else hallazgo("sentencia", bruto, pos))
    for bruto, clave, pos in _normas(cuerpo):
        (respaldadas.append(bruto) if clave in normas_ok else hallazgo("norma", bruto, pos))
    for bruto, clave, pos in _articulos(cuerpo):
        if clave not in arts_ok:
            hallazgo("articulo", bruto, pos)
    for bruto, clave, pos in _radicados(cuerpo):
        if clave not in numeros and clave not in re.sub(r"[^0-9a-z]", "", base_datos.lower()):
            hallazgo("radicado", bruto, pos)
    for bruto, clave, pos in _identificaciones(cuerpo):
        if clave not in numeros:
            hallazgo("identificacion", bruto, pos)
    for bruto, iso, pos in _fechas(cuerpo):
        if iso is None:
            hallazgo("fecha", bruto, pos, " (además, la fecha no existe en el calendario)")
        elif iso not in fechas_ok:
            hallazgo("fecha", bruto, pos)
    for bruto, clave, pos in _montos(cuerpo):
        if clave not in numeros:
            hallazgo("valor", bruto, pos)
    for m in _RE_CORREO.finditer(cuerpo):
        if m.group(0).lower() not in correos_ok:
            hallazgo("contacto", m.group(0), m.start())
    for m in _RE_TEL.finditer(cuerpo):
        if _digitos(m.group(1)) not in numeros:
            hallazgo("contacto", m.group(1), m.start())
    for bruto, clave, pos in _nombres(cuerpo):
        if not all(p in palabras_datos for p in clave.split()):
            hallazgo("nombre", bruto, pos)

    por_categoria = {}
    for h in hallazgos:
        por_categoria[h["categoria"]] = por_categoria.get(h["categoria"], 0) + 1
    advertencias = []
    if recortado:
        advertencias.append(f"El texto se revisó hasta los primeros {MAX_TEXTO} caracteres.")
    if not base_fuentes.strip():
        advertencias.append("No se entregaron fuentes: toda norma o sentencia del borrador que no esté en el "
                            "modelo aparece como posible invención.")
    if not base_entradas.strip():
        advertencias.append("No se entregaron las entradas del usuario: todos los datos del borrador aparecerán "
                            "como no respaldados.")
    return {"procedimiento": PROCEDIMIENTO, "version": VERSION,
            "estado": "POSIBLES_INVENCIONES" if hallazgos else ("PENDIENTES" if pendientes else "SIN_HALLAZGOS"),
            "posibles_invenciones": hallazgos, "por_categoria": por_categoria,
            "pendientes": pendientes, "tiene_bloque_verificar": documentos.MARCA_VERIFICAR in texto,
            "citas_respaldadas": sorted(set(respaldadas)), "advertencias": advertencias, "faltantes": [],
            "limites": ["Detector por patrones: «posible» no significa que el dato sea falso, y un dato inventado "
                        "con otra redacción puede no detectarse.",
                        "Que una cita esté en las fuentes no prueba que la fuente diga lo que el borrador le "
                        "atribuye: eso lo revisa una persona.",
                        "Los nombres se comparan palabra por palabra con las entradas; no se valida que "
                        "correspondan a la misma persona."],
            "juicio_profesional": ["Leer el borrador completo y decidir si se presenta.",
                                   "Confirmar cada cita en su fuente oficial y completar los campos pendientes."]}


def preparar(entrada: dict) -> dict:
    """Comprueba los requisitos previos a la generación. No llama al modelo."""
    entrada = entrada if isinstance(entrada, dict) else {}
    faltantes, errores = [], {}
    t = documentos.INDICE.get(str(entrada.get("tipo") or ""))
    if not t:
        faltantes.append("tipo: seleccione un modelo del catálogo (use J02 para encontrarlo)")
    limpios = {}
    if t:
        limpios, errores = documentos.validar_campos(t, entrada.get("campos"))
        if errores:
            faltantes.append("campos: hay datos obligatorios sin diligenciar o no válidos")
    if entrada.get("hechos_confirmados") is not True:
        faltantes.append("hechos_confirmados: el usuario debe confirmar expresamente que los hechos del "
                         "formulario son los que quiere afirmar")
    fuentes = entrada.get("fuentes")
    if not isinstance(fuentes, list):
        faltantes.append("fuentes: lista de fuentes aplicables (puede ir vacía si se marca «sin_fuentes»)")
        fuentes = []
    elif not fuentes and entrada.get("sin_fuentes") is not True:
        faltantes.append("fuentes: no hay ninguna; agréguelas o confirme «sin_fuentes» para generar un borrador "
                         "que no cite normas ni sentencias con número")
    base = {"procedimiento": PROCEDIMIENTO, "version": VERSION, "tipo": t["id"] if t else None,
            "errores_de_campos": errores, "faltantes": faltantes}
    if faltantes:
        return {**base, "estado": "ABSTENCION",
                "advertencias": ["No se genera el borrador: faltan requisitos previos."]}
    opcionales_vacios = [c["etiqueta"] for c in t["campos"] if not c["requerido"] and c["id"] not in limpios]
    anexos = [s for s in t["estructura"] if re.search(r"anex|prueba", s, re.I)]
    reglas_generacion = ["Usar solo los hechos, nombres, fechas y valores del formulario.",
                         "Lo que falte se deja como [COMPLETAR: …] y se lista bajo " + documentos.MARCA_VERIFICAR + ".",
                         "No inventar radicados, pruebas, firmas ni acontecimientos."]
    if not fuentes:
        reglas_generacion.append("Sin fuentes: no citar sentencias; nombrar las normas solo como lo hace el modelo "
                                 "y marcar «verificar vigencia».")
    return {**base, "estado": "LISTO", "tipo_nombre": t["nombre"], "campos": limpios,
            "pedido": documentos.instrucciones_documento(t), "datos": documentos.texto_campos(t, limpios),
            "fuentes": fuentes, "anexos_requeridos": anexos, "campos_opcionales_sin_diligenciar": opcionales_vacios,
            "reglas_de_generacion": reglas_generacion, "advertencias": documentos.advertencias_de(t),
            "siguiente_paso": "Generar con el automatizador y pasar el resultado por verificar_escrito()."}


def revisar_generado(texto: str, preparado: dict, hoy: date = None) -> dict:
    """Atajo: verifica un borrador contra lo que dejó listo `preparar`."""
    return verificar_escrito(texto, preparado.get("campos"), preparado.get("fuentes"), preparado.get("tipo"), hoy)
