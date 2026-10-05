"""Muestra del flujo completo con el modelo SIMULADO: un perfil por área (10 en total).

    python -m perfiles.muestra_simulada      # escribe perfiles/muestra_simulada.json

Sirve para probar el recorrido real de la aplicación (sesión → plan → cupo → herramientas → llamada → comprobaciones
→ resumen auditable guardado en la base) sin clave de API. El «modelo» es un doble que devuelve un texto de ejemplo
con la forma del contrato de salida. Por eso:

- cada resumen queda marcado como simulado;
- NINGÚN perfil pasa a EJECUTADO por esta muestra (el estado EJECUTADO exige el modelo real);
- no dice nada sobre la calidad jurídica o técnica de las respuestas.

Corre en un directorio temporal: no toca pullex.db ni app_secret.key del proyecto.
"""
import json
import os
import sys
import tempfile
import time
import types
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SALIDA = RAIZ / "perfiles" / "muestra_simulada.json"

# Un perfil por área, con una tarea verosímil para su subespecialidad. Todos deben estar CONECTADO_A_HERRAMIENTAS.
MUESTRA = (
    ("A01-S08-F06", "Diseña el plan de copias de seguridad de la base SQLite del servicio y cómo se ensaya la restauración."),
    ("A02-S01-F01", "Delimita este requisito funcional: exportar el historial de consultas del usuario a un archivo."),
    ("A03-S03-F09", "Revisa el contrato de la API de perfiles: rutas, códigos de estado, errores y paginación."),
    ("A04-S01-F07", "Produce la especificación de la vista Perfiles con sus estados y su comportamiento a 390 px."),
    ("A05-S10-F05", "Analiza por dónde puede entrar una instrucción maliciosa en el coordinador de perfiles."),
    ("A06-S02-F05", "Analiza el incumplimiento de un contrato de arrendamiento de vivienda: el arrendatario debe tres meses de canon."),
    ("A07-S02-F04", "Verifica qué versión del CPACA rige para un acto administrativo notificado en marzo de 2020."),
    ("A08-S03-F01", "Lo capturaron ayer sin orden judicial y lleva más de 36 horas sin audiencia ante un juez."),
    ("A09-S04-F06", "Me despidieron sin justa causa después de tres años con contrato a término indefinido."),
    ("A10-S06-F07", "Redacta un derecho de petición a la alcaldía para pedir copia del contrato de obra del parque del barrio."),
)


def texto_simulado(sistema: str) -> str:
    """Texto de EJEMPLO con las secciones que piden las instrucciones de un perfil. No es una respuesta del modelo:
    lo usan esta muestra y demo/servidor_simulado.py para probar el flujo."""
    pid = sistema.split()[2]
    titulos = sistema.split("en este orden): ", 1)[1].split(".", 1)[0].split("; ")
    cuerpo = {
        "Hechos considerados": "- Los que trae la tarea del usuario (origen: usuario). No se confirmó ninguno.",
        "Fuentes usadas": "- Ninguna: el modelo simulado no consulta fuentes.",
        "Supuestos": "- Que la tarea describe la situación completa.",
        "No verificado": "- Todo el contenido de esta salida: es un texto de ejemplo del modelo simulado.",
    }
    partes = [f"## {t}\n" + cuerpo.get(t, f"Ejemplo simulado para «{t}» del perfil {pid}. Con el modelo real aquí va "
                                          "el contenido de esta sección.") for t in titulos]
    if "Sentido:" in sistema:
        partes.append("Sentido: indeterminado")
    return "\n\n".join(partes)


class ModeloSimulado:
    """Doble del cliente del modelo: solo atiende llamadas de perfiles."""

    def __init__(self, *a, **k):
        self.messages = types.SimpleNamespace(create=self._create)

    def _create(self, **k):
        sistema = k.get("system") or ""
        if not str(sistema).startswith("PERFIL PULLEX "):
            raise RuntimeError("el modelo simulado de la muestra solo atiende perfiles")
        return types.SimpleNamespace(content=[types.SimpleNamespace(type="text", text=texto_simulado(sistema))])


def main() -> int:
    trabajo = Path(tempfile.mkdtemp(prefix="pullex-muestra-"))
    (trabajo / "static").symlink_to(RAIZ / "static")
    os.chdir(trabajo)
    os.environ.update({"ANTHROPIC_API_KEY": "simulado", "PULLEX_ADMIN_EMAIL": "admin@muestra.local",
                       "PULLEX_ADMIN_CLAVE": "clave-de-la-muestra-simulada", "PULLEX_SECRET": "solo-para-la-muestra",
                       "RESEND_API_KEY": "", "PULLEX_CORPUS_DB": str(trabajo / "corpus.db")})
    sys.path.insert(0, str(RAIZ))
    import app as pullex
    import perfiles
    from fastapi.testclient import TestClient

    pullex.anthropic.Anthropic = ModeloSimulado
    cliente = TestClient(pullex.app)
    r = cliente.post("/api/login", json={"email": "admin@muestra.local", "clave": "clave-de-la-muestra-simulada"})
    cab = {"Authorization": "Bearer " + r.json()["token"]}
    indice, ejecuciones = perfiles.indice(), []
    assert [pid[:3] for pid, _ in MUESTRA] == [f"A{n:02d}" for n in range(1, 11)]
    for pid, tarea in MUESTRA:
        assert indice[pid]["estado_real"] == "CONECTADO_A_HERRAMIENTAS", f"{pid} no está conectado a herramientas"
        r = cliente.post("/api/coordinador/ejecutar", headers=cab, json={"tarea": tarea, "contexto": {"perfiles": [pid]}})
        assert r.status_code == 200, (pid, r.status_code, r.text[:300])
        res = r.json()
        assert res["motor"]["simulado"] is True and res["perfiles"][0]["estado"] == "ejecutado", pid
        ficha = cliente.get("/api/perfiles/" + pid, headers=cab).json()
        ejecuciones.append({
            "perfil": pid, "nombre": indice[pid]["nombre"], "tarea": tarea, "motor": res["motor"],
            "estado_de_la_ejecucion": res["estado"],
            "estado_del_perfil_despues": ficha["estado_real"], "conteo_del_perfil": ficha["ejecuciones"],
            "resumen": {k: res[k] for k in ("tarea", "modo", "perfiles", "fuentes", "herramientas", "resultado",
                                            "comprobaciones", "discrepancias", "errores", "recursos", "avisos")},
        })
        print(f"{pid}  {res['estado']:<30} comprobaciones {res['comprobaciones']['pasan']}/{res['comprobaciones']['total']}  "
              f"herramientas usadas: {', '.join(h['id'] for h in res['herramientas'] if h['usos']) or '—'}")
    reg = perfiles.registro()
    muestra = {
        "tipo": "EJECUCIÓN SIMULADA",
        "cuenta_como_ejecutado": False,
        "nota": ("Diez perfiles (uno por área) ejecutados con un doble del modelo que devuelve texto de ejemplo. Prueba "
                 "el flujo de la aplicación de punta a punta; no mide calidad y no cambia el estado real de ningún perfil."),
        "fecha": time.strftime("%Y-%m-%d", time.gmtime()),
        "registro": {"version": reg["version"], "huella": reg["huella"][:16]},
        "modo": "SECUENCIAL",
        "ejecuciones": ejecuciones,
    }
    SALIDA.write_text(json.dumps(muestra, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"\nEscrito {SALIDA.relative_to(RAIZ)}: {len(ejecuciones)} ejecuciones simuladas; "
          f"perfiles en EJECUTADO después de la muestra: "
          f"{sum(1 for e in ejecuciones if e['estado_del_perfil_despues'] == 'EJECUTADO')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
