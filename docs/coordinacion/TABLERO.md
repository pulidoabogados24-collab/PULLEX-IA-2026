# Tablero de coordinación PULLEX (Codex coordina · Claude implementa y revisa)

Regla: cada cambio tiene responsable, revisor y evidencia. Nada se marca "hecho" sin evidencia reproducible.
Estados: PENDIENTE · EN CURSO · EN REVISIÓN · HECHO · BLOQUEADA.

| ID | Tarea | Responsable | Revisor | Estado | Evidencia |
|---|---|---|---|---|---|
| PUL-001 | Estado real del proyecto y exportación | Claude | Codex | EN REVISIÓN | `docs/coordinacion/PUL-001-estado-del-proyecto.md`; 147 pytest y 4 e2e sobre `34afb99` |
| PUL-002 | Fusionar acceso por plan y proveedor alterno | Claude | Codex | EN REVISIÓN | Fusionada en `pul/integracion` (540 pytest; `tests/e2e_planes.py` 174 OK). Biblioteca, Perfiles y Coordinador quedan en Premium; Herramientas sin restricción (decisión del dueño pendiente). OpenAI no probado contra la API real |
| PUL-003 | Persistencia: migrar de SQLite efímero a base gestionada | por asignar | por asignar | PENDIENTE | — |
| PUL-004 | Inventario, clasificación y vigencia del corpus de Drive | Claude | Codex | EN CURSO | Inventario y clasificación: ver PUL-010. Vigencia: nada verificado (todo PENDIENTE_VERIFICAR) |
| PUL-005 | Terminar banco del Laboratorio de casos (40/180) e integrarlo | Claude | Codex | EN CURSO | Pasa a PUL-015. Rama `pul/wip-banco-modular`: 40 casos (Constitucional y Penal) |
| PUL-006 | Terminar estilo humano (1 prueba falla) | Claude | Codex | EN REVISIÓN | Resuelta en PUL-014 |
| PUL-007 | Terminar frontend del Taller de escritos | Claude | Codex | EN REVISIÓN | Resuelta en PUL-014 |
| PUL-008 | Primera prueba con modelo real y benchmark jurídico | por asignar | por asignar | BLOQUEADA | Requiere `ANTHROPIC_API_KEY` y presupuesto |
| PUL-009 | Subir `academia` a GitHub y abrir PR | por asignar | por asignar | BLOQUEADA | Requiere acceso de escritura al repositorio |
| PUL-011 | Biblioteca en la aplicación (catálogo, búsqueda, ficha, comparar, copia, recomendar) y registro de motores de IA | Claude | Codex | EN REVISIÓN | `docs/15-BIBLIOTECA.md`; rama `pul/011-biblioteca-app`; 297 pytest; `tests/e2e_biblioteca.py` 195 comprobaciones (1280 y 390 px, catálogo ficticio e inventario real); modelo de IA SIMULADO; ningún modelo real validado; un usuario normal ve 0 modelos reales (los 6 son de un tercero y están restringidos) |
| PUL-010 | Biblioteca de Drive: inventario, mapa, muestra extraída, índice y recorrido verificable | Claude | Codex | EN REVISIÓN | `docs/14-BIBLIOTECA-DRIVE.md`; `biblioteca/INVENTARIO.md` (8.269 archivos, denominador provisional); 27 documentos indexados; `python scripts/recorrido_biblioteca.py` (8 de 8 pasos, borrador SIMULADO); 252 pytest |
| PUL-012 | Procedimientos J01–J09, reglas versionadas y calculadoras (términos, liquidación) | Claude | Codex | EN REVISIÓN | `docs/coordinacion/PUL-012-procedimientos.md`; fusionada en `pul/integracion`; `tests/e2e_herramientas.py` 97 OK. 49 de 50 reglas con URL oficial; ninguna revisada por un abogado |
| PUL-013 | Registro de 1.000 perfiles y coordinador auditable | Claude | Codex | EN REVISIÓN | `perfiles/registro.json`; fusionada en `pul/integracion`; `tests/e2e_perfiles.py` 119 OK. Ningún perfil ejecutado contra el modelo real |
| PUL-014 | Academia de escritos: estilo humano y Taller de escritos | Claude | Codex | EN REVISIÓN | `docs/coordinacion/PUL-014-escritura.md`; rama `pul/014-escritura`; 603 pytest; `tests/e2e_taller.py` 179 OK. Modelo simulado; contenido sin revisión humana |
| PUL-015 | Banco curado del Laboratorio de casos: 20 casos por área (180) y conexión a la app | Claude | Codex | EN CURSO | Rama `pul/wip-banco-modular`: 40/180 |
| PUL-016 | Decidir en qué plan van Herramientas (hoy sin restricción) y el precio del Básico frente al costo del modelo | Dueño | — | PENDIENTE | Ver PUL-002 |
