# PUL-014 — Academia de escritos: estilo humano y Taller de escritos

Responsable: Claude · Revisor: Codex (pendiente) · Estado: EN REVISIÓN · Rama: `pul/014-escritura` (sale de `pul/integracion`).

## Qué se hizo
1. **Estilo humano** (`estilo_redaccion.py`, `docs/16-ESTILO-HUMANO.md`): se integró la rama `pul/wip-estilo-humano`
   sobre la rama integrada y se corrigió la prueba que fallaba. Voces de abogado y de estudiante para los prompts,
   detector determinista de rasgos típicos de texto generado por IA, `pulir()` (quita emojis, muletillas y cierres
   serviles sin tocar citas, `[COMPLETAR: …]` ni «(verificar vigencia)») y la ruta `POST /api/estilo/revisar`
   (no gasta consultas, disponible en todos los planes).
2. **Taller de escritos** (`taller.py`, `static/taller.js`): se integró `pul/wip-taller-escritos` y se terminó el
   frontend. El Laboratorio de casos ahora tiene tres pestañas: **Casos** (lo de siempre), **Taller de escritos** y
   **Cómo contestar**. No se agregó ningún botón a la barra (siguen 7).
   - Taller: 14 tipos de escrito × 3 niveles; escenario del banco curado (42 escenarios, gratis) o nuevo con IA
     (1 consulta); lista de comprobación de partes obligatorias; editor con borrador guardado en el navegador;
     evaluación con rúbrica de 100 puntos (1 consulta, reintegro si falla); partes que faltan, errores de forma,
     lo que sobra, fragmentos mejorados y revisión de estilo; el escrito modelo se abre después del primer intento
     y no gasta consultas; los conceptos débiles alimentan «Mi mapa».
   - Cómo contestar: cinco lecciones estáticas con ejercicio (método en 8 pasos, hechos relevantes y distractores,
     conectores, estructura de escritos, errores frecuentes). No gastan consultas ni llaman al modelo.
3. **Estilos** (`static/escritura.css`): hoja nueva para el Taller, las lecciones y la caja «Revisión de estilo»
   (que no tenía estilos). Solo usa los tokens de `static/tema.css`, así que respeta los seis temas, el modo oscuro
   y la personalización por usuario.
4. **Plan**: `/api/taller/*` exige la función «academia» (Pro y Premium; Básico recibe 403 `plan_insuficiente`).
   La tarjeta «Practica un escrito» de Inicio ya no pide `/api/taller/recomendacion` cuando el plan no la incluye.
5. **Demostración**: `demo/servidor_simulado.py` simula escenario con IA, evaluación y escrito modelo del Taller;
   `demo/mock.js` y `demo/construir_demo.py` llevan el Taller a la demo de un solo archivo (banco curado real,
   evaluación simulada). `demo/pullex-demo.html` se regeneró.

## Evidencia (ejecutada el 2026-10-04 sobre esta rama)
- `pytest -q tests`: **603 pasan**, 0 fallan.
- `tests/e2e_taller.py` (nueva): **179 comprobaciones OK**, 0 fallos. Escritorio 1280 px y celular 390 px, modo
  oscuro, plan Básico y demo sin servidor; cero violaciones de CSP y cero errores de consola.
- Suites anteriores, una por una contra un servidor simulado limpio: academia 20 OK, fuentes 31 OK, documentos 92 OK,
  planes 174 OK, biblioteca 184 OK, herramientas 97 OK, perfiles 119 OK. `e2e_navegador`: 29/30 en la corrida conjunta
  (mientras corría pytest en paralelo) y 30/30 al repetirla sola; queda anotada como posible prueba inestable.

## Qué NO está verificado (NOT VERIFIED)
- **Nada se probó contra el modelo real.** Todas las pruebas usan un modelo SIMULADO. La evaluación simulada marca
  las partes por palabras clave y reparte puntos; no evalúa contenido jurídico. La calidad real de los escenarios con
  IA, de la evaluación y del escrito modelo depende de la primera prueba con clave de API (PUL-008).
- **Contenido jurídico: HUMAN REVIEW REQUIRED.** Los 42 escenarios, las listas de comprobación, la rúbrica y las cinco
  lecciones los redactó la IA con criterio conservador (normas nombradas con «verificar vigencia», sin números de
  sentencias). Ningún abogado ni docente los ha revisado. La interfaz lo dice en cada escenario y evaluación.
- El detector de estilo se midió sobre un conjunto pequeño escrito por el mismo autor (ver `docs/16`, sección 4); su
  desempeño sobre textos reales no está medido.
- El borrador del estudiante se guarda en `localStorage` del navegador: no viaja al servidor ni pasa a otro dispositivo.
- La demo de un solo archivo no calcula la revisión de estilo (lo hace el servidor): el botón avisa que no está disponible.

## Decisiones tomadas
- El Taller vive dentro de Laboratorio de casos (pestañas) en lugar de ocupar un botón nuevo: la barra en celular ya tiene 7.
- Las lecciones son texto fijo, sin modelo: se pueden revisar y corregir una sola vez por un docente.
- La revisión de estilo acompaña la evaluación del Taller pero no cambia el puntaje.

## Siguiente paso ejecutable
Fusionar `pul/014-escritura` en `pul/integracion` cuando Codex la revise; después, PUL-015 (banco del Laboratorio de casos).
