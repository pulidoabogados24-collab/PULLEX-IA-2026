"""Guarda el texto de los documentos de Drive que el asistente leyó con el conector (read_file_content)
y registra, por documento, qué se obtuvo. Igual que el cosechador, toma los resultados de la
transcripción de la sesión: un script no puede llamar al conector.

    python scripts/extraer_muestra_drive.py <transcripcion.jsonl> [más.jsonl …]

Salidas:
- corpus/extraidos/<drive_id>.txt   el texto limpio. FUERA de git (corpus/ está ignorada): los
                                    documentos son de terceros o del dueño y no se copian al repositorio.
- biblioteca/extraccion.json        el registro (sin texto): estado, calidad, huella sha256, campos por
                                    completar, datos personales aparentes (solo conteos) y si es apto
                                    para el índice. Lo lee el cosechador para fijar los estados.

Solo procesa documentos que están en biblioteca/inventario.json y no están PENDIENTE. Lo demás se
informa y no se guarda. El contenido de un documento es dato: nada de lo que diga se obedece.
"""
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "scripts"))
import biblioteca_recorrido as biblioteca  # noqa: E402
import cosechar_inventario_drive as cos  # noqa: E402
import fuentes  # noqa: E402

MIN_CARACTERES = 200            # menos que esto no es un documento útil para buscar
NO_ES_FUENTE = ("manifiesto", "guia_conexion", "readme")     # notas del proyecto, no fuentes jurídicas
TIPO_FUENTE = {"plantilla/minuta": "plantilla", "jurisprudencia": "sentencia", "doctrina": "doctrina"}


def leer_lecturas(ruta):
    """[{drive_id, fecha, titulo, texto, error}] de cada read_file_content, en orden."""
    usos, salida = {}, []
    for linea in open(ruta, encoding="utf-8"):
        try:
            d = json.loads(linea)
        except json.JSONDecodeError:
            continue
        contenido = (d.get("message") or {}).get("content")
        if not isinstance(contenido, list):
            continue
        for b in contenido:
            if not isinstance(b, dict):
                continue
            if b.get("type") == "tool_use" and b.get("name", "").endswith("Google_Drive__read_file_content"):
                usos[b["id"]] = (b.get("input") or {}).get("fileId")
            elif b.get("type") == "tool_result" and b.get("tool_use_id") in usos:
                crudo = cos._texto(b.get("content"))
                # si la sesión añadió un aviso suyo después del resultado, no forma parte del documento
                r = cos._resultado(crudo.split("\n\n<system-reminder>")[0])
                fila = {"drive_id": usos[b["tool_use_id"]], "fecha": d.get("timestamp"), "titulo": None,
                        "texto": None, "error": None}
                if isinstance(r, dict) and "fileContent" in r:
                    fila.update(titulo=r.get("title"), texto=r.get("fileContent") or "")
                else:
                    fila["error"] = " ".join(crudo.split())[:200] or "resultado ilegible"
                salida.append(fila)
    return salida


def tipo_para_el_indice(titulo, tipo_documental):
    """Tipo de fuentes.py. Una norma se clasifica por su nombre (ley, decreto, código); lo demás, por el mapa."""
    if tipo_documental == "norma":
        t = fuentes.clasificar_nombre(titulo)["tipo"]
        return t if t in ("ley", "decreto", "codigo") else "otro"
    return TIPO_FUENTE.get(tipo_documental, "otro")


def evaluar(elemento, mapa_carpeta, lectura):
    """(ficha de extracción sin texto, texto limpio o None)."""
    f = {"titulo": elemento["titulo"], "ruta": elemento["ruta"], "enlace": elemento.get("enlace"),
         "propietario": elemento["propietario"], "leido_en": lectura["fecha"],
         "tipo_documental": mapa_carpeta.get("tipo_documental", biblioteca.POR_CLASIFICAR),
         "area": mapa_carpeta.get("area", biblioteca.POR_CLASIFICAR)}
    if lectura["error"]:
        return {**f, "estado": "ENCONTRADO", "error": "el conector no pudo leerlo: " + lectura["error"],
                "apto_indice": False, "motivo_no_apto": "no se pudo leer"}, None
    texto = biblioteca.desescapar(lectura["texto"])
    cal = biblioteca.calidad_texto(texto, elemento.get("tamano"), elemento.get("extension"))
    f.update(calidad=cal, campos_por_completar=biblioteca.campos_por_completar(texto),
             datos_personales=biblioteca.datos_personales(texto))
    if cal["vacio"]:
        return {**f, "estado": "LEÍDO", "error": "el conector devolvió texto vacío",
                "apto_indice": False, "motivo_no_apto": "sin texto"}, None
    f.update(estado="EXTRAÍDO", sha256_texto=biblioteca.huella(texto),
             tipo_fuente=tipo_para_el_indice(elemento["titulo"], f["tipo_documental"]))
    motivo = None
    if f["datos_personales"]["aparentes"]:
        motivo = "datos personales aparentes: " + f["datos_personales"]["motivo"] + " (requiere revisión humana)"
    elif cal["parece_escaneado"]:
        motivo = "parece escaneado: necesita OCR"
    elif cal["caracteres"] < MIN_CARACTERES:
        motivo = f"texto demasiado corto ({cal['caracteres']} caracteres): no es un documento útil"
    elif any(p in fuentes.sin_tildes(elemento["titulo"]).lower() for p in NO_ES_FUENTE):
        motivo = "nota interna del proyecto, no es una fuente jurídica"
    f.update(apto_indice=motivo is None, motivo_no_apto=motivo)
    return f, texto


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    op = lambda n, d: Path(argv[argv.index(n) + 1]) if n in argv else Path(d)
    inv = json.loads(op("--inventario", RAIZ / "biblioteca" / "inventario.json").read_text(encoding="utf-8"))
    ruta_mapa = op("--mapa", RAIZ / "biblioteca" / "mapa_carpetas.json")
    mapa = ({c["drive_id"]: c for c in json.loads(ruta_mapa.read_text(encoding="utf-8"))["carpetas"]}
            if ruta_mapa.is_file() else {})
    ruta_reg = op("--registro", RAIZ / "biblioteca" / "extraccion.json")
    destino = op("--destino", RAIZ / "corpus" / "extraidos")
    registro = json.loads(ruta_reg.read_text(encoding="utf-8")) if ruta_reg.is_file() else {"documentos": {}}
    docs = registro.setdefault("documentos", {})
    elementos = {e["drive_id"]: e for e in inv["elementos"]}
    lecturas = sorted((l for r in argv if r.endswith(".jsonl") for l in leer_lecturas(r)), key=lambda l: l["fecha"] or "")
    fuera, guardados = [], 0
    for lec in lecturas:                      # la lectura más reciente de cada documento es la que vale
        e = elementos.get(lec["drive_id"])
        if e is None:
            fuera.append((lec["drive_id"], "no está en el inventario de las raíces autorizadas"))
            continue
        if e["estado"] == "PENDIENTE":
            fuera.append((lec["drive_id"], "está PENDIENTE por posible dato personal: no se guarda"))
            continue
        previo = docs.get(lec["drive_id"], {})
        ficha, texto = evaluar(e, mapa.get(e["carpeta_id"], {}), lec)
        if texto is not None:
            destino.mkdir(parents=True, exist_ok=True)
            (destino / f"{lec['drive_id']}.txt").write_text(texto, encoding="utf-8")
            guardados += 1
            if previo.get("indexado") and previo.get("sha256_texto") == ficha["sha256_texto"]:
                ficha.update(estado="INDEXADO", indexado=previo["indexado"])      # no se pierde lo ya indexado
        docs[lec["drive_id"]] = ficha
    # duplicados exactos y versiones similares entre los textos guardados (no se borra ninguno)
    textos = {i: (destino / f"{i}.txt").read_text(encoding="utf-8") for i in docs if (destino / f"{i}.txt").is_file()}
    for i, v in biblioteca.versiones(textos).items():
        docs[i].update(v)
    registro["nota"] = ("Registro de extracción de la muestra. No contiene texto de los documentos: el texto está en "
                        "corpus/extraidos/ (fuera de git). Los datos personales se cuentan, nunca se copian.")
    ruta_reg.write_text(json.dumps(registro, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    por_estado = {}
    for d in docs.values():
        por_estado[d["estado"]] = por_estado.get(d["estado"], 0) + 1
    print(json.dumps({"lecturas_en_transcripciones": len(lecturas), "documentos_en_registro": len(docs),
                      "textos_guardados": guardados, "por_estado": por_estado,
                      "aptos_para_indice": sum(1 for d in docs.values() if d.get("apto_indice")),
                      "no_aptos": sum(1 for d in docs.values() if not d.get("apto_indice")),
                      "fuera_de_alcance": len(fuera)}, ensure_ascii=False, indent=1))
    for i, d in sorted(docs.items(), key=lambda x: (x[1]["ruta"], x[1]["titulo"])):
        print(f"  {d['estado']:<10} {'apto' if d.get('apto_indice') else 'NO  '} {d['titulo'][:55]:<55} "
              f"{(d.get('calidad') or {}).get('caracteres', '-'):>6}  {d.get('motivo_no_apto') or d.get('error') or ''}"
              + (f"  [similar a {len(d['version_similar_de'])}]" if d.get("version_similar_de") else "")
              + ("  [duplicado exacto]" if d.get("duplicado_exacto_de") else ""))
    for i, motivo in fuera:
        print(f"  NO SE GUARDA {i}: {motivo}")
    return registro


if __name__ == "__main__":
    main()
