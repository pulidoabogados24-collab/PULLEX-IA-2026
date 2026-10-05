"""J07 — Matriz probatoria.

Relaciona cada hecho con los elementos disponibles y distingue tres niveles, sin valorar la prueba:

    AFIRMACION_DEL_USUARIO          solo lo dice quien cuenta el caso; ningún elemento lo respalda
    INDICIO                         hay elementos, pero no están aportados, no son documentales o no son directos
    ACREDITADO_POR_DOCUMENTO        al menos un documento APORTADO respalda el hecho de forma directa

«Acreditado» significa aquí «respaldado por un documento que el usuario aportó»; no dice que el documento sea
auténtico, pertinente ni suficiente: eso lo valora el juez o la autoridad. La matriz es determinista sobre la
estructura que recibe; si un modelo de IA propone relaciones, entran en `propuestas` y no cambian el nivel.
"""
import re

VERSION = "1.0.0"
PROCEDIMIENTO = "J07"
AFIRMACION, INDICIO, ACREDITADO = "AFIRMACION_DEL_USUARIO", "INDICIO", "ACREDITADO_POR_DOCUMENTO"
TIPOS_DOCUMENTALES = ("documento", "contrato", "certificado", "acto_administrativo", "providencia", "comunicacion",
                      "factura", "historia_clinica", "registro_civil", "escritura", "titulo_valor")
TIPOS_NO_DOCUMENTALES = ("testimonio", "declaracion_de_parte", "dictamen_pericial", "inspeccion", "fotografia",
                         "audio_video", "mensaje_de_datos", "indicio", "otro")
TIPOS = TIPOS_DOCUMENTALES + TIPOS_NO_DOCUMENTALES
SENTIDOS = ("apoya", "contradice")
MAX_ITEMS = 200


def _id(item, prefijo, i):
    v = str((item or {}).get("id") or "").strip()
    return v[:40] if re.fullmatch(r"[\w.-]{1,40}", v) else f"{prefijo}{i}"


def construir(entrada: dict) -> dict:
    entrada = entrada if isinstance(entrada, dict) else {}
    problemas, faltantes = [], []
    hechos_in = entrada.get("hechos") if isinstance(entrada.get("hechos"), list) else []
    elementos_in = entrada.get("elementos") if isinstance(entrada.get("elementos"), list) else []
    pret_in = entrada.get("pretensiones") if isinstance(entrada.get("pretensiones"), list) else []
    if not hechos_in:
        faltantes.append("hechos: al menos un hecho, cada uno con su texto")
    if len(hechos_in) > MAX_ITEMS or len(elementos_in) > MAX_ITEMS:
        problemas.append(f"Máximo {MAX_ITEMS} hechos y {MAX_ITEMS} elementos.")
        hechos_in, elementos_in = hechos_in[:MAX_ITEMS], elementos_in[:MAX_ITEMS]

    hechos, orden = {}, []
    for i, h in enumerate(hechos_in, 1):
        h = h if isinstance(h, dict) else {"texto": h}
        hid = _id(h, "H", i)
        texto = str(h.get("texto") or "").strip()[:2000]
        if not texto:
            problemas.append(f"El hecho {hid} no tiene texto.")
            continue
        if hid in hechos:
            problemas.append(f"Identificador de hecho repetido: {hid}.")
            continue
        hechos[hid] = {"id": hid, "texto": texto, "fecha": str(h.get("fecha") or "")[:10] or None,
                       "apoyan": [], "contradicen": []}
        orden.append(hid)

    elementos, sueltos = [], []
    for i, e in enumerate(elementos_in, 1):
        if not isinstance(e, dict):
            problemas.append(f"El elemento {i} no tiene el formato esperado.")
            continue
        eid = _id(e, "E", i)
        tipo = str(e.get("tipo") or "").strip().lower()
        sentido = str(e.get("sentido") or "apoya").strip().lower()
        if tipo not in TIPOS:
            problemas.append(f"Elemento {eid}: tipo desconocido {tipo!r} (use uno de: {', '.join(TIPOS)}).")
            continue
        if sentido not in SENTIDOS:
            problemas.append(f"Elemento {eid}: «sentido» debe ser «apoya» o «contradice».")
            continue
        if not isinstance(e.get("aportado"), bool):
            problemas.append(f"Elemento {eid}: indique si está aportado (true) o solo mencionado (false).")
            continue
        refs = [str(x) for x in (e.get("hechos") or [])] if isinstance(e.get("hechos"), list) else []
        desconocidos = [r for r in refs if r not in hechos]
        if desconocidos:
            problemas.append(f"Elemento {eid}: se refiere a hechos que no existen ({', '.join(desconocidos)}).")
        item = {"id": eid, "tipo": tipo, "descripcion": str(e.get("descripcion") or "").strip()[:500],
                "aportado": e["aportado"], "directo": e.get("directo") is not False, "sentido": sentido,
                "documental": tipo in TIPOS_DOCUMENTALES, "hechos": [r for r in refs if r in hechos]}
        elementos.append(item)
        if not item["hechos"]:
            sueltos.append(eid)
        for hid in item["hechos"]:
            hechos[hid]["apoyan" if sentido == "apoya" else "contradicen"].append(eid)

    por_id = {e["id"]: e for e in elementos}
    matriz, vacios, contradicciones, necesidades = [], [], [], []
    for hid in orden:
        h = hechos[hid]
        apoyan = [por_id[x] for x in h["apoyan"]]
        fuertes = [e for e in apoyan if e["documental"] and e["aportado"] and e["directo"]]
        if fuertes:
            nivel = ACREDITADO
            razon = "Respaldado por documento aportado: " + ", ".join(e["id"] for e in fuertes) + "."
        elif apoyan:
            nivel = INDICIO
            motivos = []
            if any(not e["aportado"] for e in apoyan):
                motivos.append("hay elementos mencionados pero no aportados")
            if any(e["aportado"] and not e["documental"] for e in apoyan):
                motivos.append("hay elementos aportados que no son documentales")
            if any(e["aportado"] and e["documental"] and not e["directo"] for e in apoyan):
                motivos.append("el documento aportado solo lo respalda de forma indirecta")
            razon = "Indicio: " + "; ".join(motivos) + "."
        else:
            nivel = AFIRMACION
            razon = "Ningún elemento respalda este hecho: por ahora es solo la afirmación de quien relata el caso."
        if h["contradicen"]:
            contradicciones.append({"hecho": hid, "elementos_que_contradicen": list(h["contradicen"]),
                                    "elementos_que_apoyan": list(h["apoyan"]),
                                    "nota": "Hay elementos en sentidos opuestos: debe resolverse antes de afirmar "
                                            "el hecho en un escrito."})
        if nivel == AFIRMACION:
            vacios.append({"hecho": hid, "vacio": "sin respaldo"})
            necesidades.append(f"{hid}: conseguir un documento o una prueba que respalde el hecho.")
        elif nivel == INDICIO:
            pendientes = [e["id"] for e in apoyan if not e["aportado"]]
            if pendientes:
                necesidades.append(f"{hid}: aportar los elementos mencionados ({', '.join(pendientes)}).")
            else:
                necesidades.append(f"{hid}: buscar respaldo documental directo; hoy solo hay indicios.")
        matriz.append({"hecho": hid, "texto": h["texto"], "fecha": h["fecha"], "nivel": nivel, "razon": razon,
                       "apoyan": list(h["apoyan"]), "contradicen": list(h["contradicen"]),
                       "controvertido": bool(h["contradicen"])})

    pretensiones = []
    for i, p in enumerate(pret_in, 1):
        p = p if isinstance(p, dict) else {"texto": p}
        pid = _id(p, "P", i)
        refs = [str(x) for x in (p.get("hechos") or [])] if isinstance(p.get("hechos"), list) else []
        existentes = [r for r in refs if r in hechos]
        niveles = {m["hecho"]: m for m in matriz}
        debiles = [r for r in existentes if niveles[r]["nivel"] != ACREDITADO or niveles[r]["controvertido"]]
        pretensiones.append({"id": pid, "texto": str(p.get("texto") or "").strip()[:1000], "hechos": existentes,
                             "hechos_sin_acreditar_o_controvertidos": debiles,
                             "sin_hechos": not existentes})
        if not existentes:
            vacios.append({"pretension": pid, "vacio": "no se relacionó con ningún hecho"})
        if [r for r in refs if r not in hechos]:
            problemas.append(f"Pretensión {pid}: se refiere a hechos que no existen.")

    propuestas = entrada.get("propuestas_modelo") if isinstance(entrada.get("propuestas_modelo"), list) else []
    conteo = {n: sum(1 for m in matriz if m["nivel"] == n) for n in (AFIRMACION, INDICIO, ACREDITADO)}
    if faltantes:
        estado = "ABSTENCION"
    elif problemas:
        estado = "CONTRADICCION"
    else:
        estado = "MATRIZ"
    return {"procedimiento": PROCEDIMIENTO, "version": VERSION, "estado": estado, "matriz": matriz,
            "elementos": elementos, "pretensiones": pretensiones, "vacios": vacios,
            "contradicciones_probatorias": contradicciones, "elementos_sin_hecho": sueltos,
            "necesidades_de_verificacion": necesidades, "conteo": conteo, "faltantes": faltantes,
            "contradicciones": problemas,
            "propuestas": [{"estado": "PROPUESTA_NO_VERIFICADA", "contenido": p} for p in propuestas[:50]],
            "limites": ["«Acreditado por documento» solo indica que hay un documento aportado que respalda el "
                        "hecho; no valora autenticidad, pertinencia, conducencia ni suficiencia.",
                        "La matriz no lee los documentos: usa la relación hecho–elemento que recibe."],
            "juicio_profesional": ["Valorar cada prueba y decidir qué hechos se afirman en el escrito.",
                                   "Definir la carga de la prueba de cada hecho."]}
