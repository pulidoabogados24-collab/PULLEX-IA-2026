"""Recorrido completo y verificable de la biblioteca (sección 14 de la especificación):

    localizar documento → extraer contenido → registrar fuente → indexar → encontrarlo desde una
    consulta en lenguaje natural → obtener el enlace para abrir el original → generar un borrador
    trazable → comprobar el resultado

    python scripts/recorrido_biblioteca.py                      # con los documentos reales ya extraídos
    python scripts/recorrido_biblioteca.py --id <drive_id> --consulta "…"
    python scripts/recorrido_biblioteca.py --json

Imprime la evidencia de cada paso y termina con código 1 si alguno falla. Usa lo que ya dejaron los
otros guiones (biblioteca/inventario.json, biblioteca/extraccion.json, corpus/extraidos/) y el índice
corpus/corpus.db.

Qué NO demuestra: el borrador se genera con un doble de prueba (SIMULADO), no con un modelo de IA;
el enlace se compara con el del inventario, no se abre desde aquí (el servidor no tiene acceso a
Drive); y nada de esto valida jurídicamente el modelo.
"""
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
import biblioteca_recorrido as biblioteca  # noqa: E402
import fuentes  # noqa: E402

# Datos de ejemplo, inventados para la demostración: no corresponden a ninguna persona.
HECHOS_DE_EJEMPLO = {"nombre": "PERSONA DE EJEMPLO (dato ficticio)", "ciudad": "Ciudad de Ejemplo (dato ficticio)"}
CONSULTA_POR_DEFECTO = "necesito un modelo de derecho de petición por una fotomulta"


def recorrido(inventario: dict, registro: dict, carpeta_textos, db_ruta: str, drive_id: str, consulta: str,
              hechos: dict, generar=None, nombre_generador: str = None) -> dict:
    """Ejecuta los ocho pasos sobre un documento. Devuelve {"ok", "pasos": [{paso, ok, evidencia}]}.
    Se detiene en el primer paso que falla: lo que sigue no se da por hecho."""
    pasos = []

    def paso(nombre, ok, **evidencia):
        pasos.append({"paso": nombre, "ok": bool(ok), "evidencia": evidencia})
        return bool(ok)

    def fin():
        return {"ok": all(p["ok"] for p in pasos) and len(pasos) == 8, "pasos": pasos, "drive_id": drive_id}

    # 1. localizar: el documento está en el inventario de las raíces autorizadas y no está reservado
    e = next((x for x in inventario.get("elementos", []) if x["drive_id"] == drive_id), None)
    if not paso("1. localizar en el inventario", e is not None and e.get("estado") != "PENDIENTE",
                titulo=e and e["titulo"], ruta=e and e["ruta"], enlace=e and e.get("enlace"), estado=e and e["estado"],
                motivo=None if e and e.get("estado") != "PENDIENTE" else
                ("no está en el inventario" if e is None else "está PENDIENTE por posible dato personal: no se procesa")):
        return fin()

    # 2. extraer: hay texto guardado y su huella es la del registro
    d = registro.get("documentos", {}).get(drive_id) or {}
    archivo = Path(carpeta_textos) / f"{drive_id}.txt"
    texto = archivo.read_text(encoding="utf-8") if archivo.is_file() else ""
    if not paso("2. extraer el contenido", bool(texto) and biblioteca.huella(texto) == d.get("sha256_texto"),
                caracteres=len(texto), sha256=biblioteca.huella(texto) if texto else None,
                coincide_con_el_registro=bool(texto) and biblioteca.huella(texto) == d.get("sha256_texto"),
                parece_escaneado=(d.get("calidad") or {}).get("parece_escaneado"),
                campos_por_completar=(d.get("campos_por_completar") or {}).get("total")):
        return fin()

    # 3. registrar la fuente: la ficha de extracción dice de dónde salió y si se puede indexar
    dp = biblioteca.datos_personales(texto)
    if not paso("3. registrar la fuente", d.get("apto_indice") is True and not dp["aparentes"] and bool(d.get("enlace")),
                apto_para_el_indice=d.get("apto_indice"), motivo_no_apto=d.get("motivo_no_apto"),
                datos_personales_aparentes=dp["aparentes"], tipo_documental=d.get("tipo_documental"), area=d.get("area"),
                propietario=d.get("propietario"), enlace=d.get("enlace")):
        return fin()

    # 4. indexar: queda en el índice con origen = id de Drive, enlace y vigencia pendiente
    con = fuentes.abrir(db_ruta)
    try:
        r = biblioteca.indexar_modelo(
            con, drive_id=drive_id, titulo=d["titulo"], texto=texto, tipo_fuente=d.get("tipo_fuente", "otro"), url=d["enlace"],
            ruta=d.get("ruta", ""), tipo_documental=d.get("tipo_documental"), area=d.get("area"),
            propietario=d.get("propietario", "tercero"), fecha_archivo=e.get("modificado"),
            versiones_relacionadas=[biblioteca.id_catalogo(v["id"]) for v in d.get("version_similar_de", [])])
        fila = con.execute("SELECT origen, url, estado_vigencia FROM fuentes WHERE origen=?", (drive_id,)).fetchone()
    finally:
        con.close()
    ficha = biblioteca.ficha(drive_id, ruta=db_ruta, texto=texto)
    if not paso("4. indexar", fila is not None and r["fragmentos"] >= 1 and ficha is not None,
                fuente_id=r["fuente_id"], fragmentos=r["fragmentos"], accion=r["accion"], id_catalogo=r["id_catalogo"],
                vigencia=fila and fila["estado_vigencia"], derechos=ficha and ficha["derechos"],
                visibilidad=ficha and ficha["visibilidad"], estado_validacion=ficha and ficha["estado_validacion"]):
        return fin()

    # 5. encontrarlo desde una consulta en lenguaje natural
    resultados = biblioteca.buscar_modelos(consulta, ruta=db_ruta, tipos=None, limite=5)
    posicion = next((n for n, x in enumerate(resultados, 1) if x["drive_id"] == drive_id), None)
    hallado = next((x for x in resultados if x["drive_id"] == drive_id), None)
    if not paso("5. encontrar desde una consulta", posicion is not None, consulta=consulta, posicion=posicion,
                resultados=[x["titulo"] for x in resultados], por_que=hallado and hallado["por_que"],
                ubicacion=hallado and hallado["ubicacion"]):
        return fin()

    # 6. abrir el original: el enlace del resultado es el del inventario
    en_chat = [f["origen"] for f in fuentes.buscar(consulta, ruta=db_ruta)]
    if not paso("6. enlace para abrir el original", hallado["enlace_original"] == e.get("enlace") and
                str(hallado["enlace_original"]).startswith("https://"),
                enlace=hallado["enlace_original"], igual_al_del_inventario=hallado["enlace_original"] == e.get("enlace"),
                comprobacion="comparado con el inventario; no se abrió desde este equipo (sin acceso a Drive)",
                visible_en_el_chat_general=drive_id in en_chat):
        return fin()

    # 7. generar un borrador trazable
    b = biblioteca.borrador_trazable(hallado, texto, hechos, generar=generar, nombre_generador=nombre_generador)
    if not paso("7. generar un borrador trazable", hallado["id"] in b["borrador"] and bool(b["cuerpo"].strip()),
                generador=b["generador"], modelo_usado=b["modelo_id"], campos_pendientes=b["campos_pendientes"],
                hechos_usados=b["hechos_usados"], citas_sin_verificar=b["citas_sin_verificar"],
                primeras_lineas=b["borrador"].split("\n")[:7]):
        return fin()

    # 8. comprobar el resultado
    c = biblioteca.comprobar_borrador(b, hechos, texto)
    paso("8. comprobar el resultado", c["ok"], fallos=c["fallos"], **c["comprobaciones"])
    return {**fin(), "borrador": b["borrador"]}


def imprimir(resultado: dict):
    for p in resultado["pasos"]:
        print(("✔" if p["ok"] else "✘"), p["paso"])
        for k, v in p["evidencia"].items():
            if v is None or v == []:
                continue
            if isinstance(v, list):
                print(f"      {k}:")
                for x in v:
                    print(f"        - {x}")
            else:
                print(f"      {k}: {v}")
    hechos = len(resultado["pasos"])
    print(f"\nRecorrido {'COMPLETO' if resultado['ok'] else 'INCOMPLETO'}: {sum(p['ok'] for p in resultado['pasos'])} de 8 pasos "
          f"comprobados" + ("" if hechos == 8 else f" (se detuvo en el paso {hechos})") + ".")


def elegir(registro: dict) -> str:
    """El primer modelo (plantilla) indexable del registro, por título."""
    aptos = sorted((d["titulo"], i) for i, d in registro.get("documentos", {}).items()
                   if d.get("apto_indice") and d.get("tipo_fuente") == "plantilla")
    preferidos = [i for t, i in aptos if "fotomulta" in fuentes.sin_tildes(t).lower()]
    return (preferidos or [i for t, i in aptos] or [None])[0]


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    op = lambda n, d: argv[argv.index(n) + 1] if n in argv else d
    ruta_inv = Path(op("--inventario", RAIZ / "biblioteca" / "inventario.json"))
    ruta_reg = Path(op("--registro", RAIZ / "biblioteca" / "extraccion.json"))
    if not ruta_inv.is_file() or not ruta_reg.is_file():
        print("Faltan biblioteca/inventario.json o biblioteca/extraccion.json: corre antes el cosechador y la extracción.")
        return 2
    inventario = json.loads(ruta_inv.read_text(encoding="utf-8"))
    registro = json.loads(ruta_reg.read_text(encoding="utf-8"))
    drive_id = op("--id", None) or elegir(registro)
    if not drive_id:
        print("No hay ningún modelo extraído y apto para el recorrido.")
        return 2
    resultado = recorrido(inventario, registro, op("--textos", RAIZ / "corpus" / "extraidos"),
                          op("--db", str(RAIZ / "corpus" / "corpus.db")), drive_id,
                          op("--consulta", CONSULTA_POR_DEFECTO), HECHOS_DE_EJEMPLO)
    if "--json" in argv:
        print(json.dumps(resultado, ensure_ascii=False, indent=1))
    else:
        print("RECORRIDO DE LA BIBLIOTECA · documento", drive_id)
        print("Generador del borrador:", biblioteca.GENERADOR_SIMULADO)
        print("Hechos usados: datos de ejemplo ficticios, declarados en el guion.\n")
        imprimir(resultado)
        if "--borrador" in argv and resultado.get("borrador"):
            print("\n" + resultado["borrador"])
    return 0 if resultado["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
