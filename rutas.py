"""Rutas HTTP del registro de perfiles y del coordinador. Se montan desde app.py con una sola llamada:

    perfiles.rutas.montar(app, sys.modules[__name__])

`nucleo` es el módulo app: de él se toman la sesión, el cupo, la base de datos y el cliente del modelo (este
último en el momento de cada llamada, para que las pruebas puedan reemplazarlo por un doble).

    GET  /api/perfiles                      búsqueda y filtros, paginada
    GET  /api/perfiles/{id}                 ficha completa con su estado real de hoy
    POST /api/coordinador/plan              qué perfiles se usarían; no gasta consultas ni llama al modelo
    POST /api/coordinador/ejecutar          ejecuta (máx. 4 perfiles; 1 consulta por perfil, con reintegro)
    GET  /api/coordinador/ejecuciones       resúmenes auditables del usuario
    GET  /api/coordinador/ejecuciones/{id}  un resumen auditable (solo de su dueño)
"""
import math
import threading
from contextlib import closing

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

import coordinador
import perfiles

POR_PAGINA_MAX = 50
_en_curso = set()
_en_curso_candado = threading.Lock()


def _motor_simulado(nucleo) -> bool:
    """True cuando el cliente del modelo fue reemplazado por un doble (pruebas o servidor de demostración)."""
    return not str(getattr(nucleo.anthropic.Anthropic, "__module__", "")).startswith("anthropic")


def _heno(p: dict) -> str:
    return coordinador._norm(" ".join([p["id"], p["nombre"], p["proposito"], " ".join(p["fuentes"]),
                                       " ".join(h["nombre"] for h in p["herramientas_permitidas"])]))


def montar(app, nucleo):
    with closing(nucleo.db()) as con:
        coordinador.crear_tablas(con)
        con.commit()
    busqueda = {}

    def _error(e: coordinador.ErrorCoordinador):
        raise HTTPException(e.codigo, e.mensaje)

    def _con_ejecucion_real() -> set:
        with closing(nucleo.db()) as con:
            return {f["perfil_id"] for f in con.execute(
                "SELECT DISTINCT perfil_id FROM perfiles_ejecuciones_perfil WHERE simulada=0 AND estado='ejecutado'")}

    def _estado_hoy(p: dict, reales: set) -> str:
        return "EJECUTADO" if p["estado_real"] == "CONECTADO_A_HERRAMIENTAS" and p["id"] in reales else p["estado_real"]

    def _resumen(p: dict, reales: set) -> dict:
        estado = _estado_hoy(p, reales)
        return {"id": p["id"], "nombre": p["nombre"], "area": p["area"], "subespecialidad": p["subespecialidad"],
                "funcion": p["funcion"], "estado_real": estado, "estado_texto": coordinador.ESTADO_TEXTO[estado],
                "solo_administracion": p["solo_administracion"], "proposito": p["proposito"]}

    def _meta(reg: dict, reales: set, u: dict) -> dict:
        por_estado = {e["id"]: 0 for e in reg["estados"]}
        matriz = {}
        for p in reg["perfiles"]:
            estado = _estado_hoy(p, reales)
            por_estado[estado] += 1
            c = matriz.setdefault(p["area"]["id"], {}).setdefault(p["funcion"]["id"], {"total": 0, "ejecutables": 0})
            c["total"] += 1
            c["ejecutables"] += estado in coordinador.ESTADOS_EJECUTABLES
        sim = reg["resumen"]["similitud_de_propositos"]
        return {
            "version": reg["version"], "huella": reg["huella"][:16], "total": reg["resumen"]["total"], "nota": reg["nota"],
            "areas": [{"id": a["id"], "nombre": a["nombre"], "tipo": a["tipo"],
                       "subespecialidades": [{"id": s["id"], "nombre": s["nombre"], "objeto": s["objeto"]}
                                             for s in a["subespecialidades"]]} for a in reg["areas"]],
            "funciones": reg["funciones"], "estados": reg["estados"], "por_estado": por_estado, "matriz": matriz,
            "por_area": reg["resumen"]["por_area"],
            "herramientas": [{"id": hid, "nombre": h["nombre"], "estado": h["estado"], "modo": h["modo"],
                              "solo_administracion": h["solo_administracion"], "nota": h["nota"],
                              "perfiles": h["perfiles_que_la_usan"]} for hid, h in reg["herramientas"].items()],
            "limites": dict(coordinador.LIMITES),
            "similitud": {"media_misma_funcion": sim["misma_funcion_media_global"],
                          "maxima_misma_funcion": sim["misma_funcion_maxima_global"], "metrica": sim["metrica"]},
            "motor": {"modelo": nucleo.MODELO, "configurado": bool(nucleo.ANTHROPIC_API_KEY),
                      "simulado": _motor_simulado(nucleo)},
            "es_admin": bool(u["es_admin"]),
        }

    @app.get("/api/perfiles")
    def perfiles_lista(request: Request, q: str = "", area: str = "", subespecialidad: str = "", funcion: str = "",
                       estado: str = "", pagina: int = 1, por_pagina: int = 20, meta: int = 0):
        u = nucleo.usuario_actual(request)
        reg = perfiles.registro()
        areas = {a["id"] for a in reg["areas"]}
        if area and area not in areas:
            raise HTTPException(400, "Área no válida")
        if funcion and funcion not in {f["id"] for f in reg["funciones"]}:
            raise HTTPException(400, "Función no válida")
        if estado and estado not in {e["id"] for e in reg["estados"]}:
            raise HTTPException(400, "Estado no válido")
        if subespecialidad and not (len(subespecialidad) == 3 and subespecialidad[0] == "S" and subespecialidad[1:].isdigit()):
            raise HTTPException(400, "Subespecialidad no válida")
        if pagina < 1 or not 1 <= por_pagina <= POR_PAGINA_MAX:
            raise HTTPException(400, f"Paginación no válida (por_pagina entre 1 y {POR_PAGINA_MAX})")
        reales = _con_ejecucion_real()
        toks = coordinador._tokens(q[:120])
        if toks and not busqueda:
            busqueda.update({p["id"]: _heno(p) for p in reg["perfiles"]})
        hallados = []
        for p in reg["perfiles"]:
            if area and p["area"]["id"] != area:
                continue
            if subespecialidad and p["subespecialidad"]["id"] != subespecialidad:
                continue
            if funcion and p["funcion"]["id"] != funcion:
                continue
            if estado and _estado_hoy(p, reales) != estado:
                continue
            if toks:
                heno = " " + busqueda[p["id"]]
                if not all((" " + t) in heno for t in toks):
                    continue
            hallados.append(p)
        total = len(hallados)
        ini = (pagina - 1) * por_pagina
        salida = {"total_registro": reg["resumen"]["total"], "total": total, "pagina": pagina, "por_pagina": por_pagina,
                  "paginas": max(1, math.ceil(total / por_pagina)),
                  "perfiles": [_resumen(p, reales) for p in hallados[ini:ini + por_pagina]]}
        if meta:
            salida["meta"] = _meta(reg, reales, u)
        return salida

    @app.get("/api/perfiles/{pid}")
    def perfiles_ficha(pid: str, request: Request):
        u = nucleo.usuario_actual(request)
        p = perfiles.indice().get(pid)
        if not p:
            raise HTTPException(404, "Perfil no encontrado")
        with closing(nucleo.db()) as con:
            conteo = coordinador.conteo_de(con, pid)
        estado = coordinador.estado_efectivo(p, conteo)
        ficha = coordinador._ficha_plan(p, bool(u["es_admin"]), "")
        return {**p, "estado_real": estado["id"], "estado_texto": estado["texto"], "ejecuciones": conteo,
                "ejecutable_por_ti": ficha["ejecutable"], "motivo_no_ejecutable": ficha["motivo_no_ejecutable"]}

    def _pedido(datos: dict, u: dict):
        tarea = datos.get("tarea")
        if not isinstance(tarea, str):
            raise HTTPException(400, "Falta la tarea.")
        contexto = datos.get("contexto") or {}
        if not isinstance(contexto, dict):
            raise HTTPException(400, "El contexto debe ser un objeto.")
        # Solo se aceptan estas claves del cliente; «es_admin» sale siempre de la sesión.
        limpio = {k: contexto[k] for k in ("perfiles", "area", "subespecialidad", "funciones") if contexto.get(k)}
        limpio["es_admin"] = bool(u["es_admin"])
        return tarea, limpio

    @app.post("/api/coordinador/plan")
    async def coordinador_plan(request: Request):
        """Propone los perfiles para una tarea. Es determinista, no llama al modelo y no gasta consultas."""
        u = nucleo.usuario_actual(request)
        tarea, contexto = _pedido(await nucleo.json_de(request), u)
        try:
            return coordinador.seleccionar(tarea, contexto)
        except coordinador.ErrorCoordinador as e:
            _error(e)

    def _llamar_modelo(sistema, mensaje, max_tokens, tiempo_max_s, herramienta_web):
        cliente = nucleo.anthropic.Anthropic(api_key=nucleo.ANTHROPIC_API_KEY)
        extra = {"tools": [herramienta_web]} if herramienta_web else {}
        r = cliente.messages.create(model=nucleo.MODELO, max_tokens=nucleo._max_tokens(max_tokens), system=sistema,
                                    messages=[{"role": "user", "content": mensaje}], timeout=float(tiempo_max_s),
                                    **extra, **nucleo.opciones_modelo())
        # Solo bloques de texto: los de razonamiento (thinking) nunca se leen ni se guardan.
        texto, busquedas, web = [], 0, []
        for b in getattr(r, "content", None) or []:
            tipo = getattr(b, "type", "")
            if tipo == "text":
                texto.append(getattr(b, "text", "") or "")
            elif tipo == "server_tool_use":
                busquedas += 1
            elif tipo == "web_search_tool_result" and isinstance(getattr(b, "content", None), list):
                web += [{"titulo": getattr(x, "title", None), "url": getattr(x, "url", None)} for x in b.content]
        uso = getattr(r, "usage", None)
        cortada = getattr(r, "stop_reason", None) == "max_tokens"
        if cortada:
            # Una salida cortada por el límite no puede pasar por completa ni alimentar al perfil siguiente sin aviso.
            texto.append("\n\n[AVISO: la respuesta de este perfil se cortó por límite de longitud y puede estar incompleta.]")
        return {"texto": "".join(texto), "cortada": cortada, "busquedas_web": busquedas, "fuentes_web": web,
                "tokens_entrada": getattr(uso, "input_tokens", None), "tokens_salida": getattr(uso, "output_tokens", None)}

    @app.post("/api/coordinador/ejecutar")
    async def coordinador_ejecutar(request: Request):
        """Ejecuta el plan de una tarea en modo secuencial. Máximo 4 perfiles; cada perfil ejecutado cuesta 1
        consulta, que se reintegra si ese perfil falla. Devuelve y guarda el resumen auditable."""
        u = nucleo.usuario_actual(request)
        datos = await nucleo.json_de(request)
        tarea, contexto = _pedido(datos, u)
        material = datos.get("material") or ""
        if not isinstance(material, str):
            raise HTTPException(400, "El material debe ser texto.")
        if len(material) > coordinador.LIMITES["max_caracteres_material"]:
            raise HTTPException(400, f"El material supera {coordinador.LIMITES['max_caracteres_material']} caracteres.")
        try:
            plan = coordinador.seleccionar(tarea, contexto)
        except coordinador.ErrorCoordinador as e:
            _error(e)
        if plan["estado"] != "LISTO":
            return JSONResponse(status_code=409, content={
                "detail": "Faltan datos para elegir los perfiles. Responde las preguntas y vuelve a intentarlo.", "plan": plan})
        ejecutables = [f for f in plan["perfiles"] if f["ejecutable"]]
        if not ejecutables:
            return JSONResponse(status_code=409, content={
                "detail": "Ninguno de los perfiles del plan se puede ejecutar hoy.", "plan": plan})
        if not nucleo.ANTHROPIC_API_KEY:
            raise HTTPException(503, "El motor de IA no está configurado en el servidor")
        nucleo._verificar_cupo(u, len(ejecutables))
        email = u["email"]
        nucleo.limitar_cuenta("coordinador:" + email, coordinador.LIMITES["max_ejecuciones_por_hora"], 3600)

        def cobrar():
            try:
                nucleo.consumir_consulta(nucleo.obtener_usuario(email))
            except HTTPException as e:
                raise coordinador.ErrorCoordinador(str(e.detail), e.status_code)

        def guardar_documento(titulo, texto, lista_fuentes):
            return nucleo._guardar_documento(email, "", titulo, "perfil", {"tarea": tarea}, texto, [],
                                             [nucleo.documentos.AVISO_GENERAL], lista_fuentes)

        def estado_plataforma():
            return {k: v for k, v in nucleo.salud().items() if k != "hora"}

        entorno = coordinador.Entorno(
            usuario=email, es_admin=bool(u["es_admin"]), llamar_modelo=_llamar_modelo, cobrar=cobrar,
            reintegrar=lambda: nucleo.reintegrar_consulta(email), guardar_documento=guardar_documento,
            estado_plataforma=estado_plataforma, modelo=nucleo.MODELO, simulado=_motor_simulado(nucleo),
            web=datos.get("web") is True, costo_consulta_cop=getattr(nucleo, "COSTO_CONSULTA_COP", None),
            nuevo_error_id=nucleo._nuevo_error_id,
            registrar_error=lambda pid, eid: nucleo.log.exception("fallo ejecutando perfil %s error_id=%s", pid, eid))
        with _en_curso_candado:
            if email in _en_curso:
                raise HTTPException(429, "Ya tienes una tarea en ejecución. Espera a que termine.")
            _en_curso.add(email)
        try:
            resumen = await run_in_threadpool(coordinador.ejecutar, plan, entorno, material)
        except coordinador.ErrorCoordinador as e:
            _error(e)
        finally:
            with _en_curso_candado:
                _en_curso.discard(email)
        with closing(nucleo.db()) as con:
            eid = coordinador.guardar_resumen(con, email, resumen)
        return {"id": eid, **resumen, "plan": {k: plan.get(k) for k in ("intencion", "subespecialidad", "secundaria", "avisos")},
                "restantes": nucleo._restantes(email)}

    @app.get("/api/coordinador/ejecuciones")
    def coordinador_ejecuciones(request: Request, limite: int = 30):
        u = nucleo.usuario_actual(request)
        with closing(nucleo.db()) as con:
            return {"ejecuciones": coordinador.listar_ejecuciones(con, u["email"], limite)}

    @app.get("/api/coordinador/ejecuciones/{eid}")
    def coordinador_ejecucion(eid: int, request: Request):
        u = nucleo.usuario_actual(request)
        with closing(nucleo.db()) as con:
            e = coordinador.obtener_ejecucion(con, u["email"], eid)
        if not e:
            raise HTTPException(404, "Ejecución no encontrada")
        return e
