# 06 — CONVENCIONES DE CÓDIGO, PRUEBAS Y DESPLIEGUE

## Código
- Español en nombres de dominio (usuarios, planes, boletin) — el dominio ES en español.
- Funciones cortas, una responsabilidad. Comentarios que explican el "porqué", no el "qué".
- Configuración SOLO por variables de entorno (`PULLEX_*`). Nada de secretos en el código.
- SQL siempre parametrizado (nunca concatenar texto del usuario en consultas).

## Pruebas mínimas antes de cada entrega (checklist ejecutable)
1. `python -c "import ast; ast.parse(open('app.py').read())"` — sintaxis.
2. Arrancar servidor local y probar con curl:
   - POST /api/registro (crea cuenta, devuelve token y perfil).
   - POST /api/login (correcto e incorrecto → 401).
   - GET /api/estado con token.
   - POST /api/chat sin API key → error controlado 500 con mensaje claro.
   - GET /api/admin/usuarios con token de admin; con token normal → 403.
   - POST /api/admin/actualizar (cambio de plan y activación).
   - GET /salud → estado ok.
3. Verificar que NO queden en el paquete: `.env`, `*.db`, `app_secret.key`, `__pycache__`.

## Git / GitHub
- `.gitignore` obligatorio: `.env`, `*.db`, `usuarios.json`, `app_secret.key`,
  `__pycache__/`, `venv/`, `bd_vectorial/`, `pullex.db`.
- Los archivos van en la RAÍZ del repositorio (no dentro de una subcarpeta) — Render
  busca `render.yaml` en la raíz. (Incidente documentado: deploy fallido por anidación.)

## Despliegue (Render, plan free)
- Blueprint desde `render.yaml`. Variables: `ANTHROPIC_API_KEY` (secreta),
  `PULLEX_ADMIN_EMAIL`, `PULLEX_ADMIN_CLAVE`, `PULLEX_MODELO`, `PULLEX_SECRET` (generada).
- Tras cada deploy: revisar Logs hasta ver "Live"; probar /salud y un login.
- Limitación conocida del plan free: cold start ~40 s; el disco es efímero → en V2 migrar
  a PostgreSQL para que usuarios e historial sobrevivan reinicios. AVISO: en V1-free, la
  base puede reiniciarse en cada deploy; comunicarlo y priorizar la migración al crecer.

## Changelog
Cada versión entregada registra: fecha, cambios, decisiones y pendientes (en README o
CHANGELOG.md). La documentación se actualiza EN el mismo cambio, no después.
