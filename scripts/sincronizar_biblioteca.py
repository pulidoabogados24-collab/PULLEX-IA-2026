"""Carga o actualiza la biblioteca de modelos jurídicos (tabla `biblioteca_modelos`) desde el
inventario de Drive. No llama a ninguna IA ni necesita claves. Detalle: docs/15-BIBLIOTECA.md.

Uso (desde la carpeta del proyecto):

    # 1) Sincronizar con biblioteca/inventario.json (incremental: solo procesa lo que cambió;
    #    retira del índice lo que desapareció o cambió de sensibilidad):
    python scripts/sincronizar_biblioteca.py

    # Ver qué cambiaría, sin escribir nada:
    python scripts/sincronizar_biblioteca.py --simular

    # 2) Cargar el TEXTO ya extraído de los modelos. Carpeta con archivos llamados
    #    <drive_id>.<pdf|docx|txt|md> (o <ID de catálogo>.<ext>, p. ej. MOD-000012.docx):
    python scripts/sincronizar_biblioteca.py --textos descargas/modelos

    # 3) Traer el texto de lo que ya está en el corpus del chat (origen "drive:<id>"):
    python scripts/sincronizar_biblioteca.py --desde-corpus

    # 4) Una persona confirma que el texto y la clasificación de un modelo corresponden al original
    #    (INDEXADO → VALIDADO; NO es la validación jurídica, que va en biblioteca/fichas.json):
    python scripts/sincronizar_biblioteca.py --validar-procesamiento MOD-000012

    # Cantidades por estado y por carpeta:
    python scripts/sincronizar_biblioteca.py --resumen

Estados de cada elemento: ENCONTRADO (solo metadatos) → LEÍDO → EXTRAÍDO → INDEXADO → VALIDADO,
o PENDIENTE (con su motivo). Un archivo encontrado NO es un documento leído ni validado.
El original en Drive nunca se modifica ni se borra desde aquí.
"""
import argparse
import hashlib
import json
import sys
from contextlib import closing
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
import biblioteca  # noqa: E402


def cargar_textos(con, carpeta: Path) -> dict:
    """Lee archivos <referencia>.<ext> y registra su texto. Usa los extractores de la ingesta del
    corpus (pypdf o pdftotext para PDF, python-docx para DOCX). Sin OCR: un PDF escaneado queda
    LEÍDO con su motivo. No se ejecutan macros ni código de los documentos: solo se lee texto."""
    sys.path.insert(0, str(RAIZ / "scripts"))
    import ingesta_corpus  # noqa: E402
    rep = {"indexados": [], "sin_cambios": 0, "sin_texto": [], "pendientes": [], "rechazados": [], "errores": []}
    for p in sorted(carpeta.iterdir()):
        if not p.is_file() or p.name.startswith((".", "~$")):
            continue
        ref = p.stem
        if p.suffix.lower() not in ingesta_corpus.EXTENSIONES:
            rep["errores"].append({"archivo": p.name, "error": "extensión no admitida (usa pdf, docx, txt o md)"})
            continue
        try:
            datos = p.read_bytes()
            paginas = ingesta_corpus.extraer(p.name, datos)
            r = biblioteca.registrar_texto(con, ref, paginas, origen="archivo:" + p.suffix.lower().lstrip("."))
        except Exception as e:  # un archivo dañado no detiene la carga
            rep["errores"].append({"archivo": p.name, "error": f"{type(e).__name__}: {str(e)[:160]}"})
            continue
        accion = r["accion"]
        if accion in ("indexado", "actualizado"):
            rep["indexados"].append({"id": r["id"], "fragmentos": r["fragmentos"], "alertas": r.get("alertas") or []})
        elif accion == "sin_cambios":
            rep["sin_cambios"] += 1
        elif accion == "sin_texto":
            rep["sin_texto"].append(r["id"])
        elif accion == "pendiente_sensibilidad":
            rep["pendientes"].append({"id": r["id"], "indicios": r["indicios"]})
        elif accion == "rechazado":
            rep["rechazados"].append({"id": r["id"], "motivo": r["motivo"]})
        else:
            rep["errores"].append({"archivo": p.name, "error": "no corresponde a ningún elemento del catálogo"})
    return rep


def imprimir_sincronizacion(rep: dict, simulado: bool):
    print(("SIMULACIÓN (no se escribió nada)\n" if simulado else "") +
          f"Nuevos: {rep['nuevos']}   Actualizados: {rep['actualizados']}   Sin cambios: {rep['sin_cambios']}   "
          f"Retirados: {rep['retirados']}   Reactivados: {rep['reactivados']}   "
          f"Retirados del índice: {rep['retirados_del_indice']}")
    print(f"No son archivos: {rep['omitidos']['carpetas']} carpetas, {rep['omitidos']['atajos']} accesos directos.")
    print(f"Activos en el catálogo: {rep.get('total_activos', '—')}")
    for c in rep["cambios"][:40]:
        print(f"  {c['accion']:<12} {c['id']}" + (("  (" + "; ".join(c["notas"]) + ")") if c.get("notas") else ""))
    if len(rep["cambios"]) > 40:
        print(f"  … y {len(rep['cambios']) - 40} más")
    for e in rep["errores"]:
        print(f"  ! {e['elemento']}: {e['error']}")


def imprimir_resumen(con):
    a = biblioteca.auditoria(con, por_pagina=1)
    print(f"Elementos en el catálogo: {a['total']} (retirados: {a['retirados']}; visibles para usuarios: {a['visibles_para_usuarios']})")
    print(f"Denominador del inventario: {a['denominador']}" +
          ("  ← aún faltan carpetas por listar: los totales son provisionales" if not a["denominador"].startswith("COMPLETO") else ""))
    for titulo, clave in (("Por estado de procesamiento", "por_estado"), ("Por validación jurídica", "por_validacion"),
                          ("Por clase de documento", "por_clase"), ("Por acceso", "por_acceso"),
                          ("Por sensibilidad", "por_sensibilidad")):
        print(titulo + ": " + ", ".join(f"{k}={v}" for k, v in a[clave].items()))
    print("Por carpeta de primer nivel (estado: cantidad):")
    for carpeta, estados in sorted(a["por_carpeta"].items()):
        print(f"  {carpeta}: " + ", ".join(f"{k}={v}" for k, v in sorted(estados.items())))
    print(f"Última sincronización: {a['ultima_sincronizacion']} · reglas {a['reglas_version']}")


def _ruta(argumento, defecto: str) -> str:
    """Ruta indicada por el usuario (relativa a donde está parado) o la del proyecto por defecto."""
    if argumento:
        return str(Path(argumento).expanduser().resolve())
    p = Path(defecto)
    return str(p if p.is_absolute() else RAIZ / p)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--inventario", default=None, help="por defecto biblioteca/inventario.json")
    ap.add_argument("--db", default=None, help="por defecto PULLEX_BIBLIOTECA_DB o biblioteca/biblioteca.db")
    ap.add_argument("--ids", default=None, help="registro de IDs de catálogo (por defecto biblioteca/ids_catalogo.json)")
    ap.add_argument("--fichas", default=None, help="fichas revisadas por personas (por defecto biblioteca/fichas.json)")
    ap.add_argument("--simular", action="store_true", help="mostrar los cambios sin escribir nada")
    ap.add_argument("--permitir-retiro-masivo", action="store_true",
                    help="retirar aunque desaparezca más de la mitad del catálogo (por defecto se evita: inventario truncado)")
    ap.add_argument("--textos", metavar="CARPETA", help="carpeta con <drive_id o ID>.<pdf|docx|txt|md> ya descargados")
    ap.add_argument("--desde-corpus", action="store_true", help="traer el texto de lo ya indexado en el corpus del chat")
    ap.add_argument("--validar-procesamiento", metavar="ID", help="marcar VALIDADO el procesamiento de un modelo indexado")
    ap.add_argument("--resumen", action="store_true", help="cantidades por estado y por carpeta")
    ap.add_argument("--json", action="store_true", help="imprimir el reporte en JSON")
    a = ap.parse_args(argv)
    ruta_bd = _ruta(a.db, biblioteca.ruta_db())
    ruta_ids, ruta_fichas = _ruta(a.ids, biblioteca.ruta_ids()), _ruta(a.fichas, biblioteca.ruta_fichas())
    salida = {}

    if a.resumen:
        with closing(biblioteca.conexion(ruta_bd)) as con:
            if a.json:
                print(json.dumps(biblioteca.auditoria(con, por_pagina=200), ensure_ascii=False, indent=1))
            else:
                imprimir_resumen(con)
        return 0
    if a.validar_procesamiento:
        with closing(biblioteca.conexion(ruta_bd)) as con:
            r = biblioteca.validar_procesamiento(con, a.validar_procesamiento)
        print(json.dumps(r, ensure_ascii=False))
        return 0 if r["accion"] == "validado" else 1
    if a.textos or a.desde_corpus:
        with closing(biblioteca.conexion(ruta_bd)) as con:
            if a.textos:
                carpeta = Path(a.textos).expanduser()
                if not carpeta.is_dir():
                    sys.exit(f"No existe la carpeta: {carpeta}")
                salida["textos"] = cargar_textos(con, carpeta)
            if a.desde_corpus:
                salida["desde_corpus"] = biblioteca.importar_del_corpus(con, _ruta(None, biblioteca.fuentes.ruta_db()))
        print(json.dumps(salida, ensure_ascii=False, indent=1))
        return 0

    ruta_inv = _ruta(a.inventario, biblioteca.ruta_inventario())
    if not Path(ruta_inv).is_file():
        sys.exit(f"No existe el inventario: {ruta_inv}. Genéralo con scripts/cosechar_inventario_drive.py.")
    if a.simular:
        # Se sincroniza sobre una COPIA en memoria de la base: se ve el resultado sin tocar el archivo.
        import sqlite3
        inventario = json.loads(Path(ruta_inv).read_text(encoding="utf-8"))
        ids = biblioteca._leer_json(ruta_ids, {})
        fichas = biblioteca._leer_json(ruta_fichas, {})
        memoria = sqlite3.connect(":memory:")
        memoria.row_factory = sqlite3.Row
        if Path(ruta_bd).is_file():
            with closing(sqlite3.connect(ruta_bd)) as origen:
                origen.backup(memoria)
        memoria.executescript(biblioteca.ESQUEMA)
        rep = biblioteca.sincronizar(memoria, inventario, ids if isinstance(ids, dict) else {}, fichas,
                                     permitir_retiro_masivo=a.permitir_retiro_masivo)
        memoria.close()
    else:
        rep = biblioteca.sincronizar_archivos(ruta_inv, ruta_bd, ruta_ids, ruta_fichas,
                                              permitir_retiro_masivo=a.permitir_retiro_masivo)
    if a.json:
        print(json.dumps(rep, ensure_ascii=False, indent=1))
    else:
        imprimir_sincronizacion(rep, a.simular)
        if not a.simular:
            sha = hashlib.sha256(Path(ruta_inv).read_bytes()).hexdigest()[:12]
            print(f"\nBase: {ruta_bd} · inventario {ruta_inv} ({sha}). Todo lo nuevo queda «sin validar jurídicamente».")
    return 1 if rep.get("retiro_masivo_evitado") else 0


if __name__ == "__main__":
    sys.exit(main())
