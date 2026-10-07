# 04 — GUÍA UX/UI

## Filosofía
Minimalista, seria y premium (inspiración: Linear, Notion, ChatGPT), con identidad
colombiana sobria. Diseñada para **abogados y estudiantes**, no para programadores (LX:
Lawyer Experience).

## Prueba de fuego de toda pantalla
- ¿La entiende un abogado de 60 años sin manual? ¿Y un estudiante de primer semestre?
- ¿Responde UNA sola pregunta? (carga cognitiva mínima; nada innecesario a la vista)
- ¿El usuario puede equivocarse sin miedo? (nunca se le regaña; la IA interpreta con buena fe)

## Sistema de diseño vigente
Detalle completo, paleta, temas y ratios de contraste: `docs/12-DISENO-Y-APARIENCIA.md`.
- **Dirección:** el tema por defecto es «Justicia × Inteligencia» (grafito, el retrato de la Justicia como
  única idea fuerte de la pantalla, lima solo para la acción principal). Los otros seis temas son
  editorial-jurídicos (papel, tinta y un solo acento). En todos: nada de estética genérica de "IA" (sin
  degradados morados, manchas flotantes, vidrio esmerilado, robots ni emojis como íconos).
- **Movimiento:** cinco duraciones y tres curvas con nombre (`--mv-*`); nada finge trabajo; todo se apaga
  con movimiento reducido. Detalle en `docs/12-DISENO-Y-APARIENCIA.md`, «Movimiento».
- **Tokens semánticos** en `static/tema.css` (`--bg`, `--surface`, `--text`, `--accent`…): toda vista
  nueva usa SOLO tokens. Los nombres viejos (`--azul`, `--oro`…) quedan como alias.
- **Tipografía:** Syne (títulos) + Plus Jakarta Sans (texto) en el tema por defecto; pares alternativos
  Editorial (Fraunces + Inter), Clásica y Moderna. Todas autohospedadas.
- **Oscuro por defecto**, con modo claro y automático; 7 temas; contraste AA medido con
  `scripts/contraste_temas.py`.
- **Layout:** 5 vistas (Inicio / Laboratorio de casos / Mi mapa / Consultar / Ajustes); en móvil, barra inferior.
- **Cada usuario personaliza** colores, tema, tipografía, tamaño, densidad, esquinas e imágenes
  (fondo del Inicio, foto, logo) en Ajustes → Apariencia; se guarda en su cuenta.

## Métricas LX que se optimizan
Tiempo para: obtener una orientación, redactar un documento, entender una sentencia,
preparar un parcial. Toda funcionalidad nueva debe reducir alguno de estos tiempos.

## Accesos y fricción
- Registro en 3 campos. 10 consultas gratis sin pedir pago.
- Sugerencias de inicio para quien no sabe qué escribir ("Explícame fácil…").
- El contador de consultas siempre visible (transparencia del plan).
- Errores SIEMPRE en lenguaje humano y con salida ("qué puedes hacer ahora").

## Reglas duras
- Nunca exigir "preguntar bien".
- Nunca dejar al usuario sin respuesta (modo degradado con fuentes oficiales).
- Nunca ocultar el costo/límite del plan.
- Exportar siempre disponible: PDF (imprimir), TXT, tablas a Excel/CSV.
