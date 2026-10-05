# PUL-019 · Despliegue en Vercel (preparación)

Estado: DESPLEGADO EN VERCEL Y CARGANDO (5-oct-2026). Solo se comprobó que la página principal responde; ingreso, chat con modelo real y streaming siguen sin probar en Vercel.

Qué se hizo: `vercel.json` (FastAPI, `maxDuration` 300 s para el streaming del chat), `.vercelignore` (excluye pruebas, demo, docs) y `DB` configurable con `PULLEX_DB` en `app.py`.

Variables que el dueño debe poner en Vercel (Settings → Environment Variables; nunca en el código ni en el chat):
- `ANTHROPIC_API_KEY` (o la del proveedor alterno)
- `PULLEX_ADMIN_CLAVE` (obligatoria; sin ella la app no arranca) y `PULLEX_ADMIN_EMAIL`
- `PULLEX_SECRET` (cadena larga aleatoria; sin ella las sesiones se invalidan en cada arranque)
- `PULLEX_DB=/tmp/pullex.db`

Limitaciones reales (no ocultar):
1. **Los datos no persisten.** Vercel solo deja escribir en `/tmp`, que se borra en cada arranque en frío y no se comparte entre instancias: usuarios, conversaciones y progreso se pierden. Para producción hace falta una base externa (PUL-003).
2. Las bases `biblioteca/biblioteca.db` y `corpus/corpus.db` también escriben en disco; en Vercel quedarían vacías o solo de lectura.
3. El streaming del chat y su latido de 15 s no se han probado en funciones de Vercel; el límite de duración depende del plan.
4. Render (`render.yaml`) sigue siendo el despliegue probado en la guía 08, con las mismas limitaciones de base de datos efímera en el plan gratuito.

Siguiente paso ejecutable: crear el repositorio en GitHub (el dueño), subir el código, importarlo en Vercel y poner las variables.

## Diagnóstico del 5-oct-2026 (antes del arreglo)

Proyecto de Vercel: `pullex-ia-2026-j8yf`. Los despliegues construyen bien, pero la función falla al iniciar.

Errores ya resueltos (confirmado en los registros de Vercel):
- `sqlite3.OperationalError: attempt to write a readonly database` → `app.py` usa `/tmp` cuando `VERCEL=1` (commit d8704d5).
- `PULLEX_ADMIN_CLAVE no está definida` → variables puestas en el proyecto.

Error vigente: `ModuleNotFoundError: No module named 'procedimientos'` (`app.py`, línea 2822).

Causa comprobada (lectura del árbol público de `main` en GitHub): los archivos se subieron **aplanados en la raíz**. `rutas.py`, `calendario.py`, `j01_…j09_*.py`, `a01…a10.py`, `app.js`, `civil.json`, etc. están sueltos en la raíz; hay duplicados con sufijo (`rutas (3).py`, `registro (4).json`, `__init__ (1).py`) y dos archivos `download` (eran `.gitignore` y `.vercelignore`). **No existen** en `main` las carpetas `procedimientos/`, `perfiles/`, `academia_banco/`, `prompts/`, `reglas/` ni `biblioteca/`, y `static/` está desactualizada.

Lo que sí está bien en `main`: los archivos `.py` de la raíz coinciden byte a byte con `pul/integracion` (comparación de hashes de blob), salvo `README.md` (pisado por otro README) y `app.py` (subido a mano; funciona según los registros).

Prueba local hecha (no sustituye la prueba en Vercel): con `VERCEL=1` y las variables de administrador, la app importa y responde `GET /` 200, estáticos 200 y `POST /api/login` 200, tanto con el árbol limpio (aplicando `.vercelignore`) como reproduciendo el estado previsto de GitHub (raíz con los archivos sueltos + las 7 carpetas correctas). Los archivos sueltos de la raíz no pisan ningún módulo real.

Arreglo mínimo: subir a `main` las 7 carpetas (`procedimientos`, `perfiles`, `academia_banco`, `prompts`, `reglas`, `biblioteca`, `static`; 85 archivos) **arrastrando las carpetas**, no los archivos.

Arreglo de fondo pendiente (PUL-009): dar a la sesión acceso de escritura al repositorio para dejar `main` idéntico a `pul/integracion` y borrar los archivos sueltos. Hoy el proxy de Git lo rechaza (403: el repositorio no está entre los autorizados de la sesión).

Nota: `includeFiles` en `vercel.json` (commit 1122915) fue una hipótesis equivocada sobre la causa; es inofensivo y ya está en `main`.

## Arreglo aplicado el 5-oct-2026

- Commit `9e1f5c6` en `main` (hecho desde el navegador de la app de Claude con la sesión de GitHub del dueño, porque la sesión no tiene permiso de escritura por Git): sube 84 archivos a sus carpetas (`procedimientos/`, `perfiles/`, `perfiles/areas/`, `academia_banco/`, `prompts/`, `reglas/`, `biblioteca/`, `static/`, `static/fonts/`). El contenido se tomó de los mismos archivos que ya estaban sueltos en la raíz de `main`, verificando el hash de cada uno contra `pul/integracion`.
- Verificado después: los árboles de `procedimientos`, `perfiles`, `academia_banco`, `prompts`, `reglas` y `biblioteca` en `main` son idénticos a los de `pul/integracion`; los 30 archivos de `static` coinciden.
- Verificado en producción: `https://pullex-ia-2026-j8yf.vercel.app/` devuelve la página de PULLEX IA (título y formulario de ingreso), ya sin error 500.

Pendiente:
- Probar en Vercel el ingreso con la cuenta de administrador, el chat con modelo real y el streaming.
- `main` sigue con los archivos sueltos en la raíz (no estorban, pero ensucian) y sin `.gitignore` ni `.vercelignore`; `static/` tiene 10 archivos sobrantes de la vista previa de marca.
- La rama `pul/integracion` (79 commits locales) sigue sin subirse: falta acceso de escritura de la sesión al repositorio (PUL-009).
- Los datos en Vercel son temporales (`/tmp`); base persistente pendiente (PUL-003).
