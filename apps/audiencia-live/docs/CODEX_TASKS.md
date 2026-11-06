# Plan de implementación listo para Codex
Este archivo sirve como backlog priorizado para Codex. No asumir que Codex ya lo ha ejecutado.

## P0 — Base funcional
- [ ] Instalar dependencias y ejecutar `npm test`, `npm run build`.
- [ ] Revisar el motor y sus límites. Conservar datos ficticios y referencias exactas.
- [ ] Completar/ajustar UI responsive, navegación, keyboard focus y errores.
- [ ] Demo Boris funcionando: 9 vs 11 p. m., chaqueta negra, motocicleta; revisar y descartar alerta.
- [ ] Añadir casos múltiples en interfaz, fragmentos por declarante y entrada manual.
- [ ] Exportar JSON/CSV con estado de revisión.
- [ ] Corregir toda prueba fallida sin desactivar reglas.

## P1 — Ingesta y calidad
- [ ] Lector de PDF/DOCX textual, detecta páginas y fallos de OCR.
- [ ] Índice híbrido local para recuperar fragmentos y no confundir personas.
- [ ] Evidencia con fuentes verificables, sin invenciones.
- [ ] Matriz de pruebas: horarios aproximados, negación, omisión, distancia y contradicción aparente.
- [ ] Telemetría agregada sin datos sensibles.

## P2 — Seguridad antes de usos reales
- [ ] Backend autenticado MFA con multi-tenancy y pruebas RLS.
- [ ] Retención, encriptación, logs auditables y control de consentimiento de audio.
- [ ] Adaptador STT streaming, fuente de audio permitida y fallback.
- [ ] Revisión legal/ciberseguridad previa a piloto con expedientes reales.

## Definition of Done
Compilación y pruebas verdes, demo repetible, fuentes exactas, matriz de riesgos documentada, no datos reales ni secretos, PR revisado. Nunca fusionar por automatismo.
