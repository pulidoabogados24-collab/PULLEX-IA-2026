# PULLEX IA — Audiencia Live
> Módulo experimental de apoyo a litigación penal colombiana, desarrollado de manera aislada de PULLEX IA principal.

## Alcance
Audiencia simulada con el testigo ficticio Boris; declaraciones previas, transcripción manual o mediante Web Speech API si el navegador lo soporta; contraste local explicable de horarios, prendas y ampliaciones; hallazgos con fuente, revisión humana, preguntas editables y exportación.

**Estado: MVP experimental.** No es un sistema de valoración probatoria, no detecta mentiras, no reemplaza el criterio jurídico ni una transcripción oficial. Repositorio **público**: NO subir expedientes, nombres reales, audio judicial, tokens o datos reservados.

## Ejecutar
Desde esta carpeta:
```bash
npm install
npm run dev
npm test
npm run build
```
La base técnica es React + TypeScript + Vite. Los datos de demo son ficticios. La persistencia del MVP es en almacenamiento local del navegador, sin sincronización segura. No cargar expedientes auténticos.

## Desarrollo con Codex
Leer [AGENTS.md](./AGENTS.md), [Arquitectura](./docs/ARCHITECTURE.md), [Plan de entregas](./docs/CODEX_TASKS.md) y [Modelo de dominio](./docs/DATA_MODEL.md) antes de editar. Mantener todos los cambios dentro de esta carpeta, en rama separada y con PR de revisión.

## Modo demostración
1. Abrir Audiencia Live y reproducir la simulación de Boris.
2. Debe aparecer posible contradicción sobre 21:00 frente a 23:00; coincidencia de chaqueta negra; ampliación por motocicleta.
3. Seleccionar alerta para consultar texto anterior y actual y validar/descartar.
4. Introducir una declaración manual o dictarla cuando el navegador lo permita; consultar hallazgos.
5. Exportar revisión como JSON. Las fuentes textuales deben coincidir exactamente con los documentos cargados.

## Próxima fase
Auth MFA, PostgreSQL/RLS, storage privado, STT profesional bajo contrato, recuperación híbrida y pipeline de evaluación. Requiere revisión de seguridad y de cumplimiento de confidencialidad judicial. El MVP nunca debe tratar como apta para producción una configuración local.
