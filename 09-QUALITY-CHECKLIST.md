# 09 — CHECKLIST DE CALIDAD (obligatorio antes de cerrar cualquier tarea)

Nada se entrega si no pasa TODAS las puertas de calidad que le apliquen.

## Puerta 1 — Revisión técnica
- [ ] Sintaxis validada y servidor arranca sin errores.
- [ ] Endpoints probados (registro, login, estado, chat, admin, /salud).
- [ ] Sin secretos en el código ni en el paquete (.env, *.db, app_secret.key fuera).
- [ ] SQL parametrizado; entradas del usuario nunca concatenadas.
- [ ] ¿Hay duplicidad o deuda técnica nueva? Si es aceptada, documentarla en 08.

## Puerta 2 — Revisión jurídica
- [ ] Ninguna norma/sentencia inventada en prompts, plantillas o textos de la app.
- [ ] Jerarquía de fuentes respetada; advertencias de verificación presentes.
- [ ] Advertencia "no sustituye a un abogado" donde corresponde.
- [ ] Habeas Data: no se piden datos innecesarios nuevos.

## Puerta 3 — Revisión UX
- [ ] ¿Lo entiende un estudiante de primer semestre sin manual?
- [ ] ¿La pantalla responde UNA pregunta? ¿Sobró algo? Quitarlo.
- [ ] Errores en lenguaje humano con "qué hacer ahora".
- [ ] Probado en móvil (la mayoría de estudiantes entra por el celular).

## Puerta 4 — Revisión IA
- [ ] ¿La respuesta jurídica incluye confianza y fuentes?
- [ ] ¿El cambio aumenta el costo por consulta? Calcularlo antes de aprobar.
- [ ] ¿Latencia dentro del objetivo (primer token <3 s)?
- [ ] ¿Se probó al menos una consulta real de cada área afectada?

## Puerta 5 — Seguridad
- [ ] Rutas nuevas con autenticación/autorización correcta.
- [ ] Sin XSS (todo markdown pasa por sanitizador).
- [ ] Sin datos de un usuario visibles para otro.

## Puerta 6 — Negocio
- [ ] ¿Protege o mejora el margen? (límites, costos API).
- [ ] ¿El admin puede operarlo sin tocar código?
- [ ] Documentación y guía de usuario actualizadas en el mismo cambio.

## Regla final (Self-criticism + mejora continua)
Antes de entregar, pregunta: ¿qué está mal aquí? ¿qué haría mejor un equipo de clase mundial?
¿cómo se mejora un 20% con el mismo esfuerzo? Aplica lo encontrado y SOLO entonces entrega.
