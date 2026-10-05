# PUL-019 · Despliegue en Vercel (preparación)

Estado: PREPARADO, NO DESPLEGADO NI PROBADO EN VERCEL.

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
