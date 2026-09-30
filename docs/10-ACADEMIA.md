# PULLEX Academia — modelo individual del conocimiento

Estado: implementado y probado con el modelo de IA simulado (68 pruebas `pytest` y 20 verificaciones de
navegador en `tests/e2e_academia.py`). **NOT VERIFIED** con el modelo real: la calidad depende de que
el modelo devuelva conceptos (`conceptos`, `conceptos_debiles`) reconocibles.

## Piezas

| Pieza | Dónde | Qué hace |
|---|---|---|
| Mapa del Derecho | `academia.py` → `MAPA` | 9 áreas, 20 temas, 61 conceptos con descripción corta y palabras clave. Casi sin números de artículo, a propósito: orienta el estudio y remite a la fuente oficial. |
| Emparejamiento | `academia.emparejar()` | Convierte el texto del modelo ("confundió la inmediatez") en un nodo del mapa. Palabra completa, sin tildes; las claves "solo del área" resuelven ambigüedades (`caducidad` en Administrativo ≠ en Civil; `prescripción` en Laboral). Lo que no encaja se guarda como concepto libre del área. |
| Estado por concepto | tabla `conocimiento` (usuario, concepto) | aciertos, fallos, caja 0-5, próximo repaso, primer/último visto, último fallo, fecha de superación. |
| Repetición espaciada | `academia.registrar_resultado()` | Error → caja 1, repaso mañana. Acierto (puntaje total ≥ 60 y el concepto no fue señalado como débil) → sube una caja: 1, 3, 7, 15, 30 días. Caja ≥ 4 = Dominado; al llegar ahí un error previo queda "superado". Con puntaje < 60, los conceptos no señalados solo se registran como vistos. |
| Caso enfocado | `POST /api/modular/caso {concepto_id}` | Solo acepta ids del mapa o conceptos libres del propio estudiante; nunca texto libre del cliente en el prompt. Nivel por defecto: el sugerido para esa área. |

## Rutas nuevas

- `GET /api/academia/mapa` — mapa con el estado de cada concepto para el usuario, promedio y nivel sugerido por área.
- `GET /api/academia/errores` — banco de errores (máx. 50), sin resolver primero.
- `GET /api/academia/resumen` — tablero: caso recomendado, continuar, repasos de hoy, próximo repaso, tema débil, último modular.
- `GET /api/modular/caso/{id}` — reabre un caso propio sin la solución.
- `GET /api/modular/conceptos?caso_id=` — nombres de los conceptos del caso (paso "Explícame el concepto").
- `POST /api/modular/evaluar` ahora devuelve también `conocimiento`: los cambios aplicados al mapa.

Todas exigen sesión y filtran por el usuario autenticado (probado: `test_banco_de_errores_aislado_por_usuario`,
`test_concepto_libre_de_otro_usuario_no_es_accesible`, `test_continuar_reabre_el_caso_sin_solucion`).

## Límites conocidos

- Los indicadores son orientativos para el propio estudiante. No deben usarse para calificaciones ni
  decisiones académicas oficiales sin intervención humana (la interfaz lo dice).
- Nivel sugerido por área: promedio < 55 básico, < 75 intermedio, < 88 avanzado, si no experto. Umbrales
  elegidos a criterio, sin calibrar con datos reales. **HUMAN REVIEW REQUIRED** cuando haya uso real.
- Las descripciones del mapa las escribió la IA con criterio conservador. **HUMAN REVIEW REQUIRED** por
  un docente antes de presentarlas como material de estudio.
- La base sigue en SQLite sobre el disco efímero de Render (SEC-10): un redeploy borra el progreso.
