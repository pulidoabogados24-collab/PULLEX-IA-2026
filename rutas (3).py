"""Rutas HTTP de los procedimientos J01–J09 y del registro de reglas.

Se registran desde app.py con `registrar(app, …)` para no importar app aquí (evita el ciclo) y para que el
bloque en app.py sea de dos líneas. Todas exigen sesión. Ninguna llama al modelo de IA ni descuenta consultas:
son cálculos y validaciones deterministas.
"""
import json
from datetime import date

from fastapi import HTTPException, Request

import procedimientos
import reglas
from procedimientos import (j01_clasificacion, j02_modelos, j03_vigencia, j04_jurisprudencia, j05_terminos,
                            j06_liquidaciones, j07_matriz_probatoria, j08_escritos, j09_impacto)

MAX_JSON = 400_000          # caracteres del cuerpo ya interpretado (el límite duro de bytes lo pone app.py)
TOPE_POR_MINUTO = 90


def registrar(app, *, usuario_actual, admin_actual, json_de, limitar_cuenta=None, documento_de=None):
    async def _entrada(request: Request):
        u = usuario_actual(request)
        if limitar_cuenta:
            limitar_cuenta("proc:" + u["email"], TOPE_POR_MINUTO, 60)
        datos = await json_de(request)
        if len(json.dumps(datos, ensure_ascii=False, default=str)) > MAX_JSON:
            raise HTTPException(413, "La solicitud es demasiado grande.")
        return u, datos

    def _fecha_param(valor: str):
        if not valor:
            return date.today()
        try:
            return reglas.a_fecha(valor)
        except ValueError:
            raise HTTPException(400, "Fecha no válida (use AAAA-MM-DD).")

    @app.get("/api/procedimientos")
    def procedimientos_catalogo(request: Request, fecha: str = ""):
        usuario_actual(request)
        f = _fecha_param(fecha)
        return {"procedimientos": procedimientos.catalogo(), "registro": reglas.resumen(),
                "terminos": j05_terminos.opciones(f), "liquidacion": j06_liquidaciones.opciones(),
                "nota": "Herramientas de cálculo deterministas: no usan el modelo de IA ni descuentan consultas."}

    @app.post("/api/procedimientos/terminos")
    async def procedimientos_terminos(request: Request):
        _, datos = await _entrada(request)
        return j05_terminos.calcular(datos)

    @app.post("/api/procedimientos/liquidacion")
    async def procedimientos_liquidacion(request: Request):
        _, datos = await _entrada(request)
        return j06_liquidaciones.liquidar(datos)

    @app.post("/api/procedimientos/clasificar")
    async def procedimientos_clasificar(request: Request):
        _, datos = await _entrada(request)
        return j01_clasificacion.clasificar(datos)          # sin apoyo del modelo: no gasta consultas

    @app.post("/api/procedimientos/modelos")
    async def procedimientos_modelos(request: Request):
        u, datos = await _entrada(request)
        return j02_modelos.buscar_modelos(datos.get("consulta"), datos.get("filtros"),
                                          limite=datos.get("limite") if isinstance(datos.get("limite"), int) else 8,
                                          usuario=u["email"])

    @app.post("/api/procedimientos/vigencia")
    async def procedimientos_vigencia(request: Request):
        _, datos = await _entrada(request)
        return j03_vigencia.verificar(datos.get("disposicion"), datos.get("fecha_hechos"), datos.get("fecha_analisis"))

    @app.post("/api/procedimientos/jurisprudencia")
    async def procedimientos_jurisprudencia(request: Request):
        _, datos = await _entrada(request)
        fichas = datos.get("fichas") if isinstance(datos.get("fichas"), list) else None
        return j04_jurisprudencia.analizar(datos.get("problema_juridico"), datos.get("hechos") or "", fichas)

    @app.post("/api/procedimientos/matriz-probatoria")
    async def procedimientos_matriz(request: Request):
        _, datos = await _entrada(request)
        return j07_matriz_probatoria.construir(datos)

    @app.post("/api/procedimientos/verificar-escrito")
    async def procedimientos_verificar_escrito(request: Request):
        """Revisa un borrador. Con `documento_id` revisa un documento guardado del propio usuario contra los
        datos de su formulario y sus fuentes; si no, revisa el `texto` contra `entradas` y `fuentes`."""
        u, datos = await _entrada(request)
        texto, entradas, fuentes, tipo = datos.get("texto"), datos.get("entradas"), datos.get("fuentes"), datos.get("tipo")
        origen = "texto"
        if datos.get("documento_id") not in (None, ""):
            if documento_de is None:
                raise HTTPException(400, "La revisión por documento no está disponible.")
            doc = documento_de(datos["documento_id"], u["email"])        # 404 si no es del usuario
            texto = doc.get("texto") or ""
            try:
                campos = json.loads(doc.get("campos") or "{}")
                fuentes_doc = json.loads(doc.get("fuentes") or "[]")
            except ValueError:
                campos, fuentes_doc = {}, []
            entradas = [campos, entradas]
            fuentes = [fuentes_doc, fuentes]
            tipo = doc.get("tipo")
            origen = "documento"
        r = j08_escritos.verificar_escrito(texto, entradas, fuentes, tipo)
        r["origen"] = origen
        return r

    @app.post("/api/procedimientos/impacto")
    async def procedimientos_impacto(request: Request):
        admin_actual(request)                 # propone cambios al registro: solo administración
        _, datos = await _entrada(request)
        return j09_impacto.impacto(datos)

    @app.get("/api/reglas")
    def reglas_lista(request: Request, fecha: str = "", procedimiento: str = "", estado: str = "", id: str = ""):
        """Registro de reglas. Con `fecha` devuelve solo las versiones aplicables ese día."""
        usuario_actual(request)
        if estado and estado not in reglas.ESTADOS:
            raise HTTPException(400, "Estado no válido.")
        if fecha:
            lista = reglas.vigentes(_fecha_param(fecha), procedimiento or None, None, estado or None)
        else:
            lista = [r for r in reglas.todas()
                     if (not procedimiento or procedimiento in r["procedimientos"]) and (not estado or r["estado"] == estado)]
        if id:
            lista = [r for r in lista if r["id"] == id.strip().upper()]
        return {"resumen": reglas.resumen(), "a_fecha": fecha or None, "n": len(lista),
                "reglas": [reglas.publica(r) for r in lista],
                "nota": "Sin «fecha» se listan todas las versiones; con «fecha», solo las aplicables ese día."}
