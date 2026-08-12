"""
PULLEX IA — Asistente jurídico colombiano (multiusuario, dinámico)
==================================================================
App para vender por suscripción a estudiantes de Derecho:
- Registro e ingreso de estudiantes (cada uno con su cuenta).
- Planes con LÍMITE DE CONSULTAS por mes (protege tu costo de API).
- Panel de ADMINISTRADOR para activar cuentas y asignar plan (cobro manual por Nequi).
- INICIO dinámico: boletín jurídico diario (noticias verificadas, sentencias recientes,
  novedades normativas) generado con IA + búsqueda web y CACHEADO 1 vez al día (no gasta
  las consultas del estudiante ni multiplica el costo).
- PERSONALIZACIÓN: áreas de interés, modo por defecto, tema claro/oscuro, búsqueda web.
- Chat con la API de Claude (modelo Haiku, económico) y búsqueda web opcional.

Ejecutar:
    pip install -r requirements.txt
    cp .env.example .env      (y pega tu ANTHROPIC_API_KEY)
    python app.py
    → abre http://localhost:8000     (panel admin: /admin)
"""
import os
import json
import time
import hmac
import base64
import sqlite3
import hashlib
import secrets
import threading
import urllib.request
import urllib.error
from datetime import datetime, timezone
from contextlib import closing

from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse, Response
from fastapi.staticfiles import StaticFiles
import anthropic

load_dotenv()

# ------------------------------------------------------------------ config --
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
MODELO = os.getenv("PULLEX_MODELO", os.getenv("LEXCOL_MODELO", "claude-haiku-4-5"))
# Para el boletín diario se puede usar un modelo un poco más potente (solo 1 vez/día).
MODELO_BOLETIN = os.getenv("PULLEX_MODELO_BOLETIN", MODELO)
APP_SECRET_FILE = "app_secret.key"
DB = "pullex.db"

ADMIN_EMAIL = os.getenv("PULLEX_ADMIN_EMAIL", os.getenv("LEXCOL_ADMIN_EMAIL", "admin@pullex.co"))
ADMIN_CLAVE = os.getenv("PULLEX_ADMIN_CLAVE", os.getenv("LEXCOL_ADMIN_CLAVE", ""))
# Nunca un valor por defecto adivinable aquí (hallazgo S1, cerrado 26-jul-2026): si
# PULLEX_ADMIN_CLAVE no está definida como variable de entorno, la app debe negarse a crear
# la cuenta admin con una clave conocida — mejor fallar de forma visible que dejar el panel de
# administrador protegido por una contraseña que cualquiera que haya visto este repo conoce.

# Correo saliente (verificación de cuenta y recuperación de contraseña) vía Resend.
# Proveedor elegido por ser el estándar simple para un operador único: capa gratuita de
# 3.000 correos/mes, API HTTP sin necesidad de manejar SMTP. Aislado en enviar_correo() para
# poder cambiar de proveedor sin tocar el resto del código si más adelante conviene otro.
RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
EMAIL_FROM = os.getenv("PULLEX_EMAIL_FROM", "PULLEX IA <onboarding@resend.dev>")
APP_URL = os.getenv("PULLEX_APP_URL", "http://localhost:8000")

PLANES = {
    "prueba":  {"nombre": "Prueba gratis", "limite": 10,   "precio": 0},
    "basico":  {"nombre": "Básico",        "limite": 200,  "precio": 30000},
    "pro":     {"nombre": "Pro",           "limite": 500,  "precio": 45000},
    "premium": {"nombre": "Premium",       "limite": 1000, "precio": 60000},
}

AREAS = ["Constitucional / Tutela", "Penal", "Civil", "Familia", "Laboral",
         "Administrativo", "Comercial / Societario", "Marcas / Propiedad Intelectual",
         "Consumidor", "Tributario"]

PREFS_DEFECTO = {"areas": [], "modo": "auto", "tema": "oscuro", "web": True, "memoria": ""}

SYSTEM_PROMPT = """Eres PULLEX IA, un asistente inteligente, cercano y humano. Tu especialidad es el
derecho colombiano, pero NO te limitas a eso: también acompañas a la persona en preguntas
cotidianas, de estudio, personales o de cualquier tema, con sentido común y calidez.

TRATO HUMANO E INTELIGENCIA EMOCIONAL:
- Habla como una persona real, cálida y respetuosa, no como un formulario. Saluda, anima y
  reconoce cómo se siente quien te escribe (si está estresado, confundido, con afán, apóyalo).
- NUNCA exijas que la pregunta esté "bien formulada" ni le pidas requisitos para ayudar. Si algo
  no es claro, interpreta con buena voluntad, responde lo mejor que puedas y, si hace falta,
  haz UNA sola pregunta amable para precisar.
- Si la persona dice que no sabe de derecho, tranquilízala y explícale con palabras sencillas,
  paso a paso, sin tecnicismos innecesarios.
- Nunca hagas sentir mal a nadie por no saber. Estás para ayudar.

CUANDO EL TEMA ES JURÍDICO (modo dual):
- PROFESIONAL (usa lenguaje técnico, cita normas, radicados, pide piezas): responde con rigor:
  problema jurídico, marco normativo, jurisprudencia y subreglas, análisis, conclusión y pasos.
- CIUDADANO (lenguaje cotidiano, "¿qué puedo hacer?"): responde directo ("Sí puedes / No puedes /
  Depende"), explica sencillo, define tecnicismos, y cierra con "Qué puedes hacer ahora" y
  "A dónde acudir". En temas jurídicos personales agrega: "Esta información es orientación
  general, no asesoría jurídica personalizada. Para tu caso concreto consulta a un abogado."
El selector de modo del usuario (si viene indicado) prevalece sobre tu detección. En preguntas
NO jurídicas responde natural, sin ese formato ni la advertencia legal.

REGLA DE ORO — CERO ALUCINACIONES JURÍDICAS:
Nunca inventes normas, artículos, sentencias, radicados, magistrados ni fechas. Si no estás
seguro de un número exacto, dilo y remite a la fuente oficial (SUIN-Juriscol, Secretaría del
Senado, relatorías de las cortes). Distingue lo cierto, lo que debe verificarse y lo que
desconoces. Advierte confirmar la VIGENCIA de las normas. Si tienes búsqueda web disponible,
úsala para verificar en fuentes oficiales y cita las fuentes que uses.

Jerarquía normativa: Constitución de 1991 y bloque de constitucionalidad; leyes y códigos;
decretos; actos administrativos; jurisprudencia (C- erga omnes; T- y SU- fijan precedente;
distingue ratio decidendi de obiter dicta); doctrina como criterio auxiliar (art. 230 C.P.).

ÉTICA: no sustituyes a un abogado; no garantices resultados; protege datos personales
(Ley 1581 de 2012); rechaza fraude o ayuda para violar la ley; no declares culpable a nadie.
Español de Colombia, ortografía RAE. En cálculos de términos distingue días hábiles y calendario.

JERARQUÍA DE FUENTES (nunca la inviertas): 1) Constitución, 2) Ley, 3) Decreto,
4) Jurisprudencia, 5) Conceptos oficiales, 6) Doctrina, 7) Academia, 8) Opinión.

EXPLICABILIDAD Y CONFIANZA (solo en respuestas jurídicas de fondo): cierra con un bloque breve:
---
**Confianza:** Alta / Media / Baja — y en una frase por qué.
**Fuentes:** normas, sentencias o enlaces en que te basaste, o "conocimiento general — verificar en fuente oficial".
No agregues este bloque en charla casual ni en temas no jurídicos."""

# ---------------------------------------------------- orquestador de agentes --
# Enrutador ligero: detecta el área y suma la instrucción del agente especialista.
AGENTES = {
    "penal": (("penal", "delito", "fiscal", "captura", "imputa", "condena", "denunci",
               "carcel", "cárcel", "homicidio", "hurto", "estafa", "audiencia"),
              "AGENTE PENAL: aplica Ley 599 de 2000 y Ley 906 de 2004; distingue tipicidad, "
              "antijuridicidad y culpabilidad; cuida garantías del art. 29 C.P."),
    "laboral": (("laboral", "trabajo", "despido", "liquidaci", "cesant", "prima", "pension",
                 "pensión", "salario", "empleador", "contrato de trabajo"),
                "AGENTE LABORAL: aplica CST y Ley 100 de 1993; primacía de la realidad (art. 53 C.P.); "
                "en liquidaciones muestra fórmulas y cálculo paso a paso en TABLA."),
    "constitucional": (("tutela", "derecho fundamental", "constituci", "habeas", "petición", "peticion"),
                       "AGENTE CONSTITUCIONAL: verifica procedencia de tutela (subsidiariedad, "
                       "inmediatez, legitimación); Decreto 2591 de 1991; precedente C-, T-, SU-."),
    "civil": (("civil", "contrato", "arriendo", "arrendamiento", "compraventa", "deuda",
               "pagar", "sucesi", "herencia", "familia", "divorcio", "alimentos", "custodia"),
              "AGENTE CIVIL/FAMILIA: aplica Código Civil y CGP; identifica la vía procesal "
              "y la competencia; en familia prima el interés superior del menor (Ley 1098 de 2006)."),
    "administrativo": (("administrativ", "tránsito", "transito", "comparendo", "multa", "entidad",
                        "alcaldía", "alcaldia", "gobernación", "nulidad", "cpaca"),
                       "AGENTE ADMINISTRATIVO: aplica CPACA (Ley 1437 de 2011); revisa recursos, "
                       "caducidad y medios de control; art. 90 C.P. para responsabilidad estatal."),
    "comercial": (("comercial", "sociedad", "empresa", "sas", "marca", "competencia", "consumidor",
                   "garantía", "garantia", "sic"),
                  "AGENTE COMERCIAL/MARCAS/CONSUMIDOR: Código de Comercio, Ley 1258 de 2008, "
                  "Decisión 486 CAN y Ley 1480 de 2011 según el caso."),
}

def enrutar_agentes(texto: str) -> str:
    t = texto.lower()
    activos = [inst for claves, inst in AGENTES.values() if any(k in t for k in claves)]
    return ("\n\n" + "\n".join(activos[:3])) if activos else ""

app = FastAPI(title="PULLEX IA")

# ------------------------------------------------------------------- secret --
_env_secret = os.getenv("PULLEX_SECRET", os.getenv("LEXCOL_SECRET"))
if _env_secret:
    SECRET = hashlib.sha256(_env_secret.encode()).digest()
elif os.path.exists(APP_SECRET_FILE):
    SECRET = open(APP_SECRET_FILE, "rb").read()
else:
    SECRET = secrets.token_bytes(32)
    try:
        with open(APP_SECRET_FILE, "wb") as f:
            f.write(SECRET)
    except OSError:
        pass

# ----------------------------------------------------------------------- db --
def db():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    return con

with closing(db()) as con:
    con.executescript("""
    CREATE TABLE IF NOT EXISTS usuarios(
        email TEXT PRIMARY KEY,
        nombre TEXT, sal TEXT, hash TEXT,
        plan TEXT DEFAULT 'prueba',
        limite INTEGER DEFAULT 10,
        usadas INTEGER DEFAULT 0,
        periodo TEXT,
        activo INTEGER DEFAULT 1,
        es_admin INTEGER DEFAULT 0,
        email_verificado INTEGER DEFAULT 0,
        preferencias TEXT DEFAULT '{}',
        creado REAL);
    CREATE TABLE IF NOT EXISTS conversaciones(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario TEXT, titulo TEXT, creada REAL);
    CREATE TABLE IF NOT EXISTS mensajes(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        conv INTEGER, rol TEXT, contenido TEXT, creada REAL);
    CREATE TABLE IF NOT EXISTS boletin(
        fecha TEXT PRIMARY KEY, contenido TEXT, creado REAL);
    CREATE TABLE IF NOT EXISTS tokens_accion(
        token TEXT PRIMARY KEY,
        email TEXT NOT NULL,
        tipo TEXT NOT NULL,
        creado REAL NOT NULL,
        expira REAL NOT NULL,
        usado INTEGER DEFAULT 0);
    """)
    con.commit()
    # Migración suave: si la base ya existía sin la columna email_verificado, se agrega.
    # Cuentas ya existentes (creadas antes de este cambio) quedan como no verificadas —
    # no se asume que un correo antiguo sea válido solo porque la cuenta ya existía.
    try:
        con.execute("ALTER TABLE usuarios ADD COLUMN email_verificado INTEGER DEFAULT 0")
        con.commit()
    except sqlite3.OperationalError:
        pass  # la columna ya existe

# -------------------------------------------------------------- utilidades --
def _hash(clave: str, sal: bytes) -> str:
    return hashlib.pbkdf2_hmac("sha256", clave.encode(), sal, 200_000).hex()

# ------------------------------------------------------------ correo saliente --
def enviar_correo(destinatario: str, asunto: str, html: str) -> bool:
    """Envía un correo vía Resend. Nunca lanza excepción hacia el llamador: si el correo no
    sale (proveedor no configurado, error de red, clave inválida), se registra en el log y se
    devuelve False — un correo de verificación o de recuperación de clave que falla NUNCA debe
    tumbar el registro/login del usuario ni exponer detalles del proveedor en la respuesta."""
    if not RESEND_API_KEY:
        print(f"[correo] RESEND_API_KEY no configurada — no se envió a {destinatario}: {asunto}")
        return False
    cuerpo = json.dumps({
        "from": EMAIL_FROM, "to": [destinatario], "subject": asunto, "html": html,
    }).encode("utf-8")
    peticion = urllib.request.Request(
        "https://api.resend.com/emails", data=cuerpo, method="POST",
        headers={"Authorization": f"Bearer {RESEND_API_KEY}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(peticion, timeout=10) as r:
            return 200 <= r.status < 300
    except urllib.error.HTTPError as e:
        print(f"[correo] Resend rechazó el envío a {destinatario}: {e.code} {e.read()[:300]}")
        return False
    except Exception as e:
        print(f"[correo] Error de red enviando a {destinatario}: {e}")
        return False

def _plantilla_correo(titulo: str, cuerpo_html: str, boton_texto: str, boton_url: str) -> str:
    """Plantilla mínima coherente con la identidad de marca (azul marino + dorado)."""
    return f"""<div style="font-family:Segoe UI,Arial,sans-serif;background:#0A1E3F;padding:32px 16px">
  <div style="max-width:460px;margin:0 auto;background:#0E2A57;border-radius:16px;padding:28px;
              border:1px solid #1c3f74">
    <div style="text-align:center;margin-bottom:18px">
      <div style="display:inline-block;width:52px;height:52px;border-radius:14px;
                  background:linear-gradient(160deg,#FFC93C,#c9971f);line-height:52px;
                  font-weight:800;font-size:22px;color:#20170a">P</div>
      <div style="color:#fff;font-weight:800;letter-spacing:2px;margin-top:8px">
        PUL<span style="color:#FFC93C">LEX</span> IA</div>
    </div>
    <h2 style="color:#fff;font-size:18px;margin:0 0 12px">{titulo}</h2>
    <div style="color:#a9bad6;font-size:14px;line-height:1.6">{cuerpo_html}</div>
    <div style="text-align:center;margin:26px 0 10px">
      <a href="{boton_url}" style="display:inline-block;background:linear-gradient(180deg,#FFC93C,#FDB813);
         color:#20170a;font-weight:800;text-decoration:none;padding:13px 26px;border-radius:12px;
         font-size:14px">{boton_texto}</a>
    </div>
    <p style="color:#5b6b86;font-size:11.5px;text-align:center;margin-top:20px">
      Si el botón no funciona, copia y pega este enlace en tu navegador:<br>
      <a href="{boton_url}" style="color:#FFC93C;word-break:break-all">{boton_url}</a></p>
  </div>
</div>"""

# ------------------------------------------------------- tokens de un solo uso --
def generar_token_accion(email: str, tipo: str, horas_validez: float) -> str:
    """tipo: 'verificar_correo' | 'restablecer_clave'. El token es de un solo uso y expira."""
    token = secrets.token_urlsafe(32)
    ahora = time.time()
    with closing(db()) as con:
        con.execute(
            "INSERT INTO tokens_accion(token,email,tipo,creado,expira,usado) VALUES(?,?,?,?,?,0)",
            (token, normaliza_email(email), tipo, ahora, ahora + horas_validez * 3600))
        con.commit()
    return token

def validar_token_accion(token: str, tipo: str):
    """Devuelve el email asociado si el token es válido (existe, tipo correcto, no usado,
    no expirado); None en cualquier otro caso. No distingue el motivo del rechazo en la
    respuesta pública — evita dar pistas útiles para adivinar tokens de otros usuarios."""
    with closing(db()) as con:
        f = con.execute(
            "SELECT * FROM tokens_accion WHERE token=? AND tipo=?", (token, tipo)).fetchone()
    if not f or f["usado"] or f["expira"] < time.time():
        return None
    return f["email"]

def marcar_token_usado(token: str):
    with closing(db()) as con:
        con.execute("UPDATE tokens_accion SET usado=1 WHERE token=?", (token,))
        con.commit()

def periodo_actual() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m")

def fecha_hoy() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")

def normaliza_email(email: str) -> str:
    return (email or "").strip().lower()

def crear_usuario(email, nombre, clave, plan="prueba", activo=1, es_admin=0, email_verificado=0):
    email = normaliza_email(email)
    sal = secrets.token_bytes(16)
    limite = PLANES.get(plan, PLANES["prueba"])["limite"]
    with closing(db()) as con:
        con.execute(
            """INSERT INTO usuarios(email,nombre,sal,hash,plan,limite,usadas,periodo,activo,es_admin,email_verificado,preferencias,creado)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (email, nombre.strip(), sal.hex(), _hash(clave, sal), plan, limite, 0,
             periodo_actual(), activo, es_admin, email_verificado, json.dumps(PREFS_DEFECTO), time.time()))
        con.commit()

def obtener_usuario(email):
    email = normaliza_email(email)
    with closing(db()) as con:
        f = con.execute("SELECT * FROM usuarios WHERE email=?", (email,)).fetchone()
    return dict(f) if f else None

def preferencias_de(u):
    try:
        p = json.loads(u.get("preferencias") or "{}")
    except Exception:
        p = {}
    return {**PREFS_DEFECTO, **p}

def verificar_clave(email, clave) -> bool:
    u = obtener_usuario(email)
    if not u:
        return False
    return hmac.compare_digest(u["hash"], _hash(clave, bytes.fromhex(u["sal"])))

def reiniciar_periodo_si_aplica(u):
    if u["plan"] == "prueba":
        return u
    hoy = periodo_actual()
    if u["periodo"] != hoy:
        with closing(db()) as con:
            con.execute("UPDATE usuarios SET usadas=0, periodo=? WHERE email=?", (hoy, u["email"]))
            con.commit()
        u["usadas"] = 0
        u["periodo"] = hoy
    return u

if ADMIN_EMAIL and not obtener_usuario(ADMIN_EMAIL):
    if not ADMIN_CLAVE:
        raise RuntimeError(
            "PULLEX_ADMIN_CLAVE no está definida. No se crea la cuenta admin con una clave "
            "por defecto conocida (hallazgo de seguridad S1, cerrado 26-jul-2026). Define la "
            "variable de entorno PULLEX_ADMIN_CLAVE con una contraseña fuerte y aleatoria antes "
            "de arrancar la aplicación."
        )
    crear_usuario(ADMIN_EMAIL, "Administrador", ADMIN_CLAVE,
                  plan="premium", activo=1, es_admin=1, email_verificado=1)
    # El admin se marca verificado de una vez: lo crea el propio operador con sus variables
    # de entorno al arrancar, no un desconocido registrándose — no aplica el mismo riesgo de
    # correo ajeno que justifica exigir verificación a los estudiantes.

# -------------------------------------------------------------------- token --
def emitir_token(email: str) -> str:
    cuerpo = json.dumps({"u": normaliza_email(email), "t": int(time.time())}).encode()
    firma = hmac.new(SECRET, cuerpo, hashlib.sha256).digest()
    return base64.urlsafe_b64encode(cuerpo).decode() + "." + base64.urlsafe_b64encode(firma).decode()

def validar_token(token: str) -> str:
    try:
        cuerpo_b64, firma_b64 = token.split(".")
        cuerpo = base64.urlsafe_b64decode(cuerpo_b64)
        firma = base64.urlsafe_b64decode(firma_b64)
        if not hmac.compare_digest(firma, hmac.new(SECRET, cuerpo, hashlib.sha256).digest()):
            raise ValueError
        datos = json.loads(cuerpo)
        if time.time() - datos["t"] > 60 * 60 * 24 * 14:
            raise ValueError
        return datos["u"]
    except Exception:
        raise HTTPException(401, "Sesión inválida o expirada")

def usuario_actual(request: Request) -> dict:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(401, "No autenticado")
    u = obtener_usuario(validar_token(auth[7:]))
    if not u:
        raise HTTPException(401, "Cuenta no encontrada")
    return u

# -------------------------------------------------- rate limiting (seguridad) --
# Defensa simple contra fuerza bruta en login/registro (Skill 15 — Security First).
_intentos = {}
_intentos_lock = threading.Lock()

def limitar(ip: str, tope: int = 8, ventana: int = 300):
    ahora = time.time()
    with _intentos_lock:
        reg = [t for t in _intentos.get(ip, []) if ahora - t < ventana]
        if len(reg) >= tope:
            raise HTTPException(429, "Demasiados intentos. Espera unos minutos e inténtalo de nuevo.")
        reg.append(ahora)
        _intentos[ip] = reg

def ip_de(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for", "")
    return fwd.split(",")[0].strip() if fwd else (request.client.host if request.client else "?")

def admin_actual(request: Request) -> dict:
    u = usuario_actual(request)
    if not u["es_admin"]:
        raise HTTPException(403, "Requiere permisos de administrador")
    return u

def perfil_publico(u):
    plan = PLANES.get(u["plan"], PLANES["prueba"])
    return {"email": u["email"], "nombre": u["nombre"], "plan": u["plan"],
            "plan_nombre": plan["nombre"], "limite": u["limite"], "usadas": u["usadas"],
            "restantes": max(0, u["limite"] - u["usadas"]), "activo": bool(u["activo"]),
            "es_admin": bool(u["es_admin"]),
            "email_verificado": bool(u["email_verificado"]) if "email_verificado" in u.keys() else False,
            "preferencias": preferencias_de(u)}

# ----------------------------------------------------------- corpus opcional --
def buscar_corpus(pregunta: str) -> str:
    try:
        import chromadb, voyageai  # noqa
        if not os.path.isdir("bd_vectorial") or not os.getenv("VOYAGE_API_KEY"):
            return ""
        vo = voyageai.Client(api_key=os.getenv("VOYAGE_API_KEY"))
        cli = chromadb.PersistentClient(path="bd_vectorial")
        col = cli.get_collection("derecho_colombiano")
        vec = vo.embed([pregunta], model="voyage-law-2", input_type="query").embeddings[0]
        res = col.query(query_embeddings=[vec], n_results=6)
        partes = []
        for texto, meta in zip(res["documents"][0], res["metadatas"][0]):
            partes.append(f"[Fuente: {meta.get('documento','?')}]\n{texto}")
        return "\n\n".join(partes)
    except Exception:
        return ""

# ------------------------------------------------------- boletín diario --
_boletin_lock = threading.Lock()

BOLETIN_PROMPT = """Eres el editor jurídico de PULLEX IA. Usando búsqueda web, arma el BOLETÍN
JURÍDICO COLOMBIANO de hoy para estudiantes de Derecho. Devuélvelo en Markdown, con TRES
secciones y viñetas breves. En CADA punto incluye la fecha aproximada y el ENLACE a la fuente
(prioriza fuentes oficiales: cortes, Diario Oficial, Función Pública, medios jurídicos serios).
No inventes nada: si no encuentras algo reciente, dilo. Máximo 4 puntos por sección.

## 📰 Noticias jurídicas
(novedades relevantes del sector justicia en Colombia, recientes)

## ⚖️ Jurisprudencia reciente
(sentencias o decisiones recientes de la Corte Constitucional, Corte Suprema o Consejo de Estado,
con la corporación, el tipo/número si se conoce y el tema)

## 📕 Novedades normativas
(leyes, decretos o reformas nuevas o en trámite relevante)

Cierra con una línea: "Verifica siempre en la fuente oficial antes de citar en un escrito."
"""

def generar_boletin_texto() -> str:
    cliente = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    try:
        r = cliente.messages.create(
            model=MODELO_BOLETIN, max_tokens=1800,
            messages=[{"role": "user", "content": BOLETIN_PROMPT}],
            tools=[{"type": "web_search_20250305", "name": "web_search", "max_uses": 5}],
        )
        partes = [b.text for b in r.content if getattr(b, "type", "") == "text"]
        return "\n".join(partes).strip() or "No fue posible generar el boletín hoy."
    except Exception as e:
        return f"No fue posible generar el boletín hoy ({e})."

def obtener_boletin(forzar=False):
    hoy = fecha_hoy()
    if not forzar:
        with closing(db()) as con:
            f = con.execute("SELECT contenido FROM boletin WHERE fecha=?", (hoy,)).fetchone()
        if f:
            return {"fecha": hoy, "contenido": f["contenido"]}
    if not ANTHROPIC_API_KEY:
        return {"fecha": hoy, "contenido": "_Configura la clave de API para activar el boletín._"}
    with _boletin_lock:  # evita generarlo dos veces a la vez
        with closing(db()) as con:
            f = con.execute("SELECT contenido FROM boletin WHERE fecha=?", (hoy,)).fetchone()
        if f and not forzar:
            return {"fecha": hoy, "contenido": f["contenido"]}
        texto = generar_boletin_texto()
        with closing(db()) as con:
            con.execute("INSERT OR REPLACE INTO boletin(fecha,contenido,creado) VALUES(?,?,?)",
                        (hoy, texto, time.time()))
            con.commit()
        return {"fecha": hoy, "contenido": texto}

# ------------------------------------------------------------- rutas web --
@app.get("/", response_class=HTMLResponse)
def index():
    return open(os.path.join("static", "index.html"), encoding="utf-8").read()

@app.get("/admin", response_class=HTMLResponse)
def admin_page():
    return open(os.path.join("static", "admin.html"), encoding="utf-8").read()

@app.get("/salud")
def salud():
    """Health check (observabilidad): estado del servicio, base de datos y motor."""
    ok_db = True
    try:
        with closing(db()) as con:
            con.execute("SELECT 1").fetchone()
    except Exception:
        ok_db = False
    return {"servicio": "pullex-ia", "estado": "ok" if ok_db else "degradado",
            "db": ok_db, "ia_configurada": bool(ANTHROPIC_API_KEY),
            "modelo": MODELO, "hora": datetime.now(timezone.utc).isoformat()}

@app.get("/sw.js")
def service_worker():
    return Response(open(os.path.join("static", "sw.js"), encoding="utf-8").read(),
                    media_type="application/javascript")

@app.get("/manifest.webmanifest")
def manifest():
    return Response(open(os.path.join("static", "manifest.webmanifest"), encoding="utf-8").read(),
                    media_type="application/manifest+json")

# ------------------------------------------------------------ rutas auth --
@app.post("/api/registro")
async def registro(request: Request):
    limitar(ip_de(request))
    datos = await request.json()
    email = normaliza_email(datos.get("email", ""))
    nombre = (datos.get("nombre", "") or "").strip()
    clave = datos.get("clave", "")
    if not email or "@" not in email:
        raise HTTPException(400, "Correo inválido")
    if len(nombre) < 2:
        raise HTTPException(400, "Escribe tu nombre")
    if len(clave) < 8:
        raise HTTPException(400, "La contraseña debe tener al menos 8 caracteres")
    if obtener_usuario(email):
        raise HTTPException(409, "Ya existe una cuenta con ese correo")
    crear_usuario(email, nombre, clave, plan="prueba", activo=1, es_admin=0, email_verificado=0)
    _enviar_verificacion(email, nombre)
    return {"token": emitir_token(email), "perfil": perfil_publico(obtener_usuario(email))}

@app.post("/api/login")
async def login(request: Request):
    limitar(ip_de(request))
    datos = await request.json()
    email = normaliza_email(datos.get("email", datos.get("usuario", "")))
    if verificar_clave(email, datos.get("clave", "")):
        return {"token": emitir_token(email), "perfil": perfil_publico(obtener_usuario(email))}
    raise HTTPException(401, "Correo o contraseña incorrectos")

def _actualizar_clave(email: str, nueva_clave: str):
    sal = secrets.token_bytes(16)
    with closing(db()) as con:
        con.execute("UPDATE usuarios SET sal=?, hash=? WHERE email=?",
                    (sal.hex(), _hash(nueva_clave, sal), normaliza_email(email)))
        con.commit()

@app.post("/api/cambiar-clave")
async def api_cambiar_clave(request: Request):
    u = usuario_actual(request)
    datos = await request.json()
    if not verificar_clave(u["email"], datos.get("actual", "")):
        raise HTTPException(401, "La contraseña actual no coincide")
    if len(datos.get("nueva", "")) < 8:
        raise HTTPException(400, "La nueva contraseña debe tener al menos 8 caracteres")
    _actualizar_clave(u["email"], datos["nueva"])
    return {"ok": True}

# --------------------------------------------- verificación de correo --
def _enviar_verificacion(email: str, nombre: str):
    token = generar_token_accion(email, "verificar_correo", horas_validez=24)
    url = f"{APP_URL}/verificar-correo?token={token}"
    html = _plantilla_correo(
        f"Hola, {nombre.split(' ')[0] if nombre else ''} — confirma tu correo",
        "Gracias por crear tu cuenta en PULLEX IA. Confirma tu correo para activarla del todo. "
        "Este enlace vence en 24 horas.",
        "Confirmar mi correo", url)
    enviar_correo(email, "Confirma tu correo — PULLEX IA", html)

@app.post("/api/reenviar-verificacion")
async def api_reenviar_verificacion(request: Request):
    limitar(ip_de(request), tope=4, ventana=600)
    u = usuario_actual(request)
    if u["email_verificado"]:
        return {"ok": True, "mensaje": "Tu correo ya está verificado."}
    _enviar_verificacion(u["email"], u["nombre"])
    return {"ok": True, "mensaje": "Te reenviamos el correo de verificación."}

@app.get("/verificar-correo")
async def verificar_correo(token: str = ""):
    email = validar_token_accion(token, "verificar_correo")
    if not email:
        cuerpo = ("<p>Este enlace no es válido o ya venció. Inicia sesión y pide reenviar "
                   "la verificación desde Configuración.</p>")
        icono, titulo = "✕", "Enlace no válido"
    else:
        marcar_token_usado(token)
        with closing(db()) as con:
            con.execute("UPDATE usuarios SET email_verificado=1 WHERE email=?", (email,))
            con.commit()
        cuerpo = "<p>Tu correo quedó confirmado. Ya puedes volver a la app.</p>"
        icono, titulo = "✓", "Correo verificado"
    return HTMLResponse(f"""<!doctype html><html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{titulo} — PULLEX IA</title>
<style>body{{margin:0;min-height:100vh;display:flex;align-items:center;justify-content:center;
  background:#0A1E3F;font-family:'Segoe UI',system-ui,sans-serif;color:#eaf0fb;padding:24px}}
.card{{max-width:380px;background:#0E2A57;border:1px solid #1c3f74;border-radius:20px;
  padding:32px 26px;text-align:center}}
.ic{{width:56px;height:56px;border-radius:50%;background:linear-gradient(160deg,#FFC93C,#c9971f);
  display:flex;align-items:center;justify-content:center;margin:0 auto 16px;font-size:26px;
  color:#20170a;font-weight:800}}
a{{color:#FFC93C}}</style></head>
<body><div class="card"><div class="ic">{icono}</div><h2>{titulo}</h2>{cuerpo}
<p><a href="/">Ir a PULLEX IA</a></p></div></body></html>""")

# --------------------------------------------- recuperación de contraseña --
@app.post("/api/recuperar-clave")
async def api_recuperar_clave(request: Request):
    limitar(ip_de(request), tope=4, ventana=600)
    datos = await request.json()
    email = normaliza_email(datos.get("email", ""))
    u = obtener_usuario(email)
    # Siempre la misma respuesta exista o no la cuenta — evita que este formulario sirva
    # para averiguar qué correos están registrados (enumeración de cuentas).
    mensaje = {"ok": True, "mensaje": "Si ese correo tiene una cuenta, te enviamos un enlace."}
    if u:
        token = generar_token_accion(email, "restablecer_clave", horas_validez=1)
        url = f"{APP_URL}/restablecer.html?token={token}"
        html = _plantilla_correo(
            "Restablece tu contraseña",
            "Pediste restablecer tu contraseña en PULLEX IA. Este enlace vence en 1 hora. "
            "Si no fuiste tú, ignora este correo — tu contraseña actual sigue funcionando.",
            "Elegir nueva contraseña", url)
        enviar_correo(email, "Restablece tu contraseña — PULLEX IA", html)
    return mensaje

@app.post("/api/restablecer-clave")
async def api_restablecer_clave(request: Request):
    limitar(ip_de(request), tope=6, ventana=600)
    datos = await request.json()
    token = datos.get("token", "")
    nueva = datos.get("clave", "")
    if len(nueva) < 8:
        raise HTTPException(400, "La contraseña debe tener al menos 8 caracteres")
    email = validar_token_accion(token, "restablecer_clave")
    if not email:
        raise HTTPException(400, "Este enlace no es válido o ya venció. Pide uno nuevo.")
    marcar_token_usado(token)
    _actualizar_clave(email, nueva)
    return {"ok": True}

@app.post("/api/preferencias")
async def api_preferencias(request: Request):
    u = usuario_actual(request)
    datos = await request.json()
    prefs = preferencias_de(u)
    if "areas" in datos and isinstance(datos["areas"], list):
        prefs["areas"] = [a for a in datos["areas"] if a in AREAS][:6]
    if datos.get("modo") in ("auto", "profesional", "ciudadano"):
        prefs["modo"] = datos["modo"]
    if datos.get("tema") in ("claro", "oscuro"):
        prefs["tema"] = datos["tema"]
    if "web" in datos:
        prefs["web"] = bool(datos["web"])
    if "memoria" in datos:
        prefs["memoria"] = str(datos["memoria"])[:1500]
    with closing(db()) as con:
        con.execute("UPDATE usuarios SET preferencias=? WHERE email=?",
                    (json.dumps(prefs), u["email"]))
        con.commit()
    return {"ok": True, "preferencias": prefs}

@app.get("/api/estado")
def estado(request: Request):
    u = usuario_actual(request)
    u = reiniciar_periodo_si_aplica(u)
    return {"perfil": perfil_publico(u), "api": bool(ANTHROPIC_API_KEY),
            "planes": PLANES, "areas": AREAS,
            "corpus": os.path.isdir("bd_vectorial") and bool(os.getenv("VOYAGE_API_KEY"))}

@app.get("/api/boletin")
def api_boletin(request: Request):
    usuario_actual(request)   # el boletín está cacheado: no gasta consultas del estudiante
    return obtener_boletin()

# ------------------------------------------------------ conversaciones --
@app.get("/api/conversaciones")
def listar(request: Request):
    u = usuario_actual(request)
    with closing(db()) as con:
        filas = con.execute(
            "SELECT id,titulo FROM conversaciones WHERE usuario=? ORDER BY creada DESC",
            (u["email"],)).fetchall()
    return [dict(f) for f in filas]

@app.post("/api/conversaciones")
async def crear(request: Request):
    u = usuario_actual(request)
    with closing(db()) as con:
        cur = con.execute(
            "INSERT INTO conversaciones(usuario,titulo,creada) VALUES(?,?,?)",
            (u["email"], "Nueva consulta", time.time()))
        con.commit()
        return {"id": cur.lastrowid, "titulo": "Nueva consulta"}

@app.delete("/api/conversaciones/{cid}")
def borrar(cid: int, request: Request):
    u = usuario_actual(request)
    with closing(db()) as con:
        con.execute("DELETE FROM conversaciones WHERE id=? AND usuario=?", (cid, u["email"]))
        con.execute("DELETE FROM mensajes WHERE conv=?", (cid,))
        con.commit()
    return {"ok": True}

@app.get("/api/conversaciones/{cid}/mensajes")
def mensajes(cid: int, request: Request):
    usuario_actual(request)
    with closing(db()) as con:
        filas = con.execute(
            "SELECT rol,contenido FROM mensajes WHERE conv=? ORDER BY id", (cid,)).fetchall()
    return [dict(f) for f in filas]

# --------------------------------------------------------------- chat --
@app.post("/api/chat")
async def chat(request: Request):
    u = usuario_actual(request)
    if not u["activo"]:
        raise HTTPException(403, "Tu cuenta está inactiva. Escríbele al administrador para activarla.")
    u = reiniciar_periodo_si_aplica(u)
    if u["usadas"] >= u["limite"]:
        raise HTTPException(402, "Alcanzaste el límite de consultas de tu plan. Actualiza tu plan para seguir.")

    datos = await request.json()
    cid = datos["conversacion"]
    texto = datos["mensaje"].strip()
    prefs = preferencias_de(u)
    usar_web = bool(datos.get("web", prefs.get("web", True)))
    modo = datos.get("modo", prefs.get("modo", "auto"))
    # Adjuntos: lista de {tipo:"image"|"document", media_type, datos(base64), nombre}
    adjuntos = datos.get("adjuntos", []) or []

    if not ANTHROPIC_API_KEY:
        raise HTTPException(500, "Falta ANTHROPIC_API_KEY en la configuración del servidor")

    nota_adj = ""
    if adjuntos:
        nombres = ", ".join(a.get("nombre", "archivo") for a in adjuntos)
        nota_adj = f"\n\n[Adjuntó: {nombres}]"

    with closing(db()) as con:
        con.execute("UPDATE usuarios SET usadas=usadas+1 WHERE email=?", (u["email"],))
        con.execute("INSERT INTO mensajes(conv,rol,contenido,creada) VALUES(?,?,?,?)",
                    (cid, "user", texto + nota_adj, time.time()))
        n = con.execute("SELECT COUNT(*) c FROM mensajes WHERE conv=?", (cid,)).fetchone()["c"]
        if n == 1:
            con.execute("UPDATE conversaciones SET titulo=? WHERE id=?",
                        (texto[:60] + ("…" if len(texto) > 60 else ""), cid))
        historial = con.execute(
            "SELECT rol,contenido FROM mensajes WHERE conv=? ORDER BY id", (cid,)).fetchall()
        restantes = con.execute("SELECT limite-usadas r FROM usuarios WHERE email=?",
                                (u["email"],)).fetchone()["r"]
        con.commit()

    mensajes_api = [{"role": f["rol"], "content": f["contenido"]} for f in historial]
    # Adjunta los archivos (imágenes/PDF) al último mensaje del usuario para esta consulta.
    if adjuntos and mensajes_api:
        bloques = [{"type": "text", "text": texto or "Analiza el archivo adjunto."}]
        for a in adjuntos:
            if a.get("tipo") == "image":
                bloques.append({"type": "image", "source": {"type": "base64",
                                "media_type": a.get("media_type", "image/png"),
                                "data": a.get("datos", "")}})
            elif a.get("tipo") == "document":
                bloques.append({"type": "document", "source": {"type": "base64",
                                "media_type": a.get("media_type", "application/pdf"),
                                "data": a.get("datos", "")}})
        mensajes_api[-1] = {"role": "user", "content": bloques}

    # SYSTEM_PROMPT es fijo → se cachea (prompt caching) para abaratar cada consulta.
    # Lo dinámico (agentes, modo, nombre, memoria, corpus) va en un segundo bloque sin caché.
    din = enrutar_agentes(texto)
    if modo != "auto":
        din += f"\n\nEl usuario seleccionó explícitamente el modo {modo.upper()}: responde en ese registro."
    din += f"\n\nTe diriges a {u['nombre']}. Trátalo por su nombre con calidez."
    if prefs.get("areas"):
        din += ("\n\nAREAS DE INTERÉS del usuario (dales prioridad y contexto cuando apliquen): "
                + ", ".join(prefs["areas"]) + ".")
    if prefs.get("memoria"):
        din += ("\n\nMEMORIA SOBRE EL USUARIO (recuérdala y tenla en cuenta en tus respuestas): "
                + prefs["memoria"])
    contexto = buscar_corpus(texto)
    if contexto:
        din += ("\n\nFRAGMENTOS DEL CORPUS PROPIO (priorízalos y cita la fuente):\n" + contexto)

    system = [{"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}]
    if din.strip():
        system.append({"type": "text", "text": din})

    cliente = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    herramientas = ([{"type": "web_search_20250305", "name": "web_search", "max_uses": 5}]
                    if usar_web else [])

    def flujo():
        yield "data: " + json.dumps({"tipo": "restantes", "restantes": max(0, restantes)}) + "\n\n"
        completo = []
        try:
            with cliente.messages.stream(
                model=MODELO, max_tokens=4000, system=system,
                messages=mensajes_api, tools=herramientas,
            ) as stream:
                for evento in stream:
                    if evento.type == "content_block_start" and getattr(
                            evento.content_block, "type", "") == "server_tool_use":
                        yield "data: " + json.dumps({"tipo": "busqueda"}) + "\n\n"
                    if evento.type == "content_block_delta" and hasattr(evento.delta, "text"):
                        completo.append(evento.delta.text)
                        yield "data: " + json.dumps({"tipo": "texto",
                                                     "texto": evento.delta.text}) + "\n\n"
        except anthropic.APIError as e:
            # FAIL-SAFE: nunca dejar al usuario sin respuesta — modo degradado con
            # orientación básica y fuentes oficiales para consultar manualmente.
            msg = (f"⚠️ El motor de IA no está disponible en este momento "
                   f"({getattr(e, 'message', str(e))}).\n\n"
                   "**Mientras se restablece, puedes consultar directamente:**\n"
                   "- Normas vigentes: [SUIN-Juriscol](https://www.suin-juriscol.gov.co) y "
                   "[Secretaría del Senado](http://www.secretariasenado.gov.co)\n"
                   "- Jurisprudencia: [Corte Constitucional](https://www.corteconstitucional.gov.co), "
                   "[Corte Suprema](https://cortesuprema.gov.co), "
                   "[Consejo de Estado](https://www.consejodeestado.gov.co)\n"
                   "- Estado de procesos: [Rama Judicial](https://www.ramajudicial.gov.co)\n\n"
                   "Tu consulta quedó guardada; vuelve a intentarlo en unos minutos "
                   "(no se te descontará doble).")
            completo.append(msg)
            # devuelve la consulta al usuario: no se cobra la fallida
            try:
                with closing(db()) as con:
                    con.execute("UPDATE usuarios SET usadas=MAX(usadas-1,0) WHERE email=?",
                                (u["email"],))
                    con.commit()
            except Exception:
                pass
            yield "data: " + json.dumps({"tipo": "texto", "texto": msg}) + "\n\n"
        respuesta = "".join(completo)
        with closing(db()) as con:
            con.execute("INSERT INTO mensajes(conv,rol,contenido,creada) VALUES(?,?,?,?)",
                        (cid, "assistant", respuesta, time.time()))
            con.commit()
        yield "data: " + json.dumps({"tipo": "fin"}) + "\n\n"

    return StreamingResponse(flujo(), media_type="text/event-stream")

# -------------------------------------------------------------- admin --
@app.get("/api/admin/usuarios")
def admin_usuarios(request: Request):
    admin_actual(request)
    with closing(db()) as con:
        filas = con.execute(
            "SELECT email,nombre,plan,limite,usadas,activo,es_admin,creado FROM usuarios ORDER BY creado DESC"
        ).fetchall()
    return {"usuarios": [dict(f) for f in filas], "planes": PLANES}

@app.post("/api/admin/actualizar")
async def admin_actualizar(request: Request):
    admin_actual(request)
    datos = await request.json()
    email = normaliza_email(datos.get("email", ""))
    u = obtener_usuario(email)
    if not u:
        raise HTTPException(404, "Usuario no encontrado")
    plan = datos.get("plan", u["plan"])
    if plan not in PLANES:
        raise HTTPException(400, "Plan inválido")
    activo = 1 if datos.get("activo", u["activo"]) else 0
    limite = PLANES[plan]["limite"]
    with closing(db()) as con:
        if datos.get("reiniciar"):
            con.execute("UPDATE usuarios SET plan=?, limite=?, activo=?, usadas=0, periodo=? WHERE email=?",
                        (plan, limite, activo, periodo_actual(), email))
        else:
            con.execute("UPDATE usuarios SET plan=?, limite=?, activo=? WHERE email=?",
                        (plan, limite, activo, email))
        con.commit()
    return {"ok": True, "perfil": perfil_publico(obtener_usuario(email))}

# Costo estimado por consulta en COP (Haiku 4.5, con holgura). Ajustable por entorno.
COSTO_CONSULTA_COP = float(os.getenv("PULLEX_COSTO_CONSULTA_COP", "45"))

@app.get("/api/admin/metricas")
def admin_metricas(request: Request):
    """Panel de negocio (pensamiento CFO): ingresos estimados, suscriptores y consumo."""
    admin_actual(request)
    with closing(db()) as con:
        filas = con.execute(
            "SELECT plan,activo,usadas,es_admin FROM usuarios WHERE es_admin=0").fetchall()
    por_plan = {k: 0 for k in PLANES}
    ingreso = 0
    consultas = 0
    activos = 0
    for f in filas:
        por_plan[f["plan"]] = por_plan.get(f["plan"], 0) + 1
        consultas += f["usadas"] or 0
        if f["activo"]:
            activos += 1
            ingreso += PLANES.get(f["plan"], {}).get("precio", 0)
    costo_api = round(consultas * COSTO_CONSULTA_COP)
    return {
        "estudiantes": len(filas),
        "activos": activos,
        "por_plan": por_plan,
        "ingreso_mensual_estimado": ingreso,
        "consultas_totales": consultas,
        "costo_api_estimado": costo_api,
        "margen_estimado": ingreso - costo_api,
        "planes": PLANES,
    }

@app.post("/api/admin/reset-clave")
async def admin_reset_clave(request: Request):
    """Genera una contraseña temporal para un estudiante que la olvidó.
    Se la devuelve al admin para que se la comunique; el estudiante la cambia al entrar."""
    admin_actual(request)
    datos = await request.json()
    email = normaliza_email(datos.get("email", ""))
    u = obtener_usuario(email)
    if not u:
        raise HTTPException(404, "Usuario no encontrado")
    temporal = "Pullex-" + secrets.token_hex(3)
    sal = secrets.token_bytes(16)
    with closing(db()) as con:
        con.execute("UPDATE usuarios SET sal=?, hash=? WHERE email=?",
                    (sal.hex(), _hash(temporal, sal), email))
        con.commit()
    return {"ok": True, "temporal": temporal}

@app.post("/api/admin/boletin/regenerar")
def admin_regenerar_boletin(request: Request):
    admin_actual(request)
    return obtener_boletin(forzar=True)

app.mount("/static", StaticFiles(directory="static"), name="static")

if __name__ == "__main__":
    import uvicorn
    print("\n⚖  PULLEX IA — abre http://localhost:8000   (panel admin: /admin)")
    print(f"   Admin: {ADMIN_EMAIL}   (cámbialo con PULLEX_ADMIN_EMAIL / PULLEX_ADMIN_CLAVE)\n")
    uvicorn.run(app, host="0.0.0.0", port=8000)
