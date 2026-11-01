# Instrucciones para Codex — PULLEX IA Audiencia Live
## Límites
- Trabajar EXCLUSIVAMENTE en `apps/audiencia-live/**`. No alterar root, Flask, API principal, Biblioteca, Vercel ni otras aplicaciones.
- Implementar y verificar incrementalmente. Abrir PR contra main, sin fusionar automáticamente.
- El repositorio es público. NO insertar información judicial real, secretos, datos personales, grabaciones o transcripciones de usuarios.
- Usar solo personajes ficticios. Jamás imprimir material reservado en logs o telemetría.
- Diferenciar claramente hechos documentados, inferencias automáticas y validación humana. Nunca etiquetar “mentira” ni “contradicción probada”.
- No inventar sentencias ni fundamentación; toda sugerencia jurídica requiere revisión.
- No enviar audio o textos a servicios externos sin consentimiento, contrato y medidas de seguridad verificadas.

## Arquitectura
- UI React/TypeScript, adaptador de captura, transcripción, catálogo documental, indexación, `compareStatement()` puro y auditable, revisión, exportación.
- Cada hallazgo DEBE incluir versión actual, fragmento previo literal, documento, hablante y explicación.
- Selección de versiones previas: solo mismo expediente y mismo declarante; en ausencia de vínculo seguro, “No concluyente”.
- “No consta” no significa falsedad ni omisión intencional.
- El navegador puede limitar Web Speech API; fallback manual obligatorio.
- Guardar por expediente, no exponer fuentes sin permiso, no usar URL pública para archivos reales.

## Criterios de aceptación
- `npm test` y `npm run build` pasan.
- Demo Boris: horario 9 pm vs 11 pm => posible contradicción; chaqueta negra => coincide; motocicleta => ampliación.
- Cada alerta muestra fuente exacta y motivo; se puede revisar, descartar, editar pregunta y exportar.
- Funciones esenciales accesibles por teclado, diseño móvil y errores controlados.
- Hacer pruebas negativas: ambigüedad, ausencia de antecedentes, hablante distinto y fallo de permisos de micrófono.

## Orden de trabajo sugerido
1. Revisar arquitectura y ejecutar tests existentes.
2. Completar interfaz, documentos y estado.
3. Mejorar motor con datos etiquetados y regresiones.
4. Seguridad y privacidad.
5. Revisar en PR de forma adversarial antes de autorizar integración.
