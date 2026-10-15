# Integración Claude Code + Codex + GitHub — PULLEX IA

## Estado
Este archivo documenta cómo habilitar una colaboración segura. Añadir un workflow **no instala** software en el PC, no concede acceso a una cuenta de terceros ni crea una clave API automáticamente.

## 1. Trabajo local
En Claude Code, dentro de este repositorio:

```text
/plugin marketplace add openai/codex-plugin-cc
/plugin install codex@openai-codex
/reload-plugins
/codex:setup
```

Requiere Node.js >= 18.18 y autenticación de Codex con una cuenta compatible de ChatGPT o API de OpenAI.
Luego, revisa cambios con `/codex:review` y cuestiona la arquitectura con `/codex:adversarial-review`. No permitir escritura en producción.

Documentación: https://github.com/openai/codex-plugin-cc

## 2. GitHub
- Usar PR, ramas y revisión humana antes de integrar.
- Mantener el repositorio **privado** antes de activar agentes con secretos.
- La comprobación de sintaxis y rutas de secretos no necesita API key.
- Las revisiones automáticas con Codex se habilitan solo al configurar un secreto `OPENAI_API_KEY` y variable `PULLEX_CODEX_REVIEW_ENABLED=true`.
- La revisión de Claude por GitHub Actions se habilita solo con `ANTHROPIC_API_KEY` y variable `PULLEX_CLAUDE_REVIEW_ENABLED=true`.
- El uso de OpenAI/Anthropic en GitHub Actions puede generar cargos de API adicionales.
- No utilizar flujos `pull_request_target` que ejecuten código del PR con secretos.
- Se recomienda limitar el acceso de las credenciales a este proyecto y restringir disparadores a colaboradores de confianza.
- Las condiciones de privacidad se comprueban en el YAML, pero no sustituyen ajustar la visibilidad de GitHub.

Los workflows están inicialmente deshabilitados por variables hasta completar estos pasos.

## 3. Seguridad antes de habilitar
1. Confirmar cuál de los repositorios PULLEX es el canónico y cuál está conectado al despliegue.
2. Revisar que no haya secretos antiguos en historial público; rotarlos si hubo filtraciones.
3. Cambiar el repositorio canónico a privado si su código y datos deben ser confidenciales.
4. Configurar secretos en Settings > Secrets and variables > Actions; nunca pegarlos en archivos o chats.
5. Revisar quién tiene permisos de escritura en GitHub.
6. Crear y exigir controles de branch/PR apropiados para el plan de GitHub.
7. Ejecutar las acciones en una rama de prueba y evaluar gastos/resultado antes de habilitar revisiones automáticas.
8. Un resultado favorable de un agente no equivale a aprobación de seguridad.

## 4. Roles
- Claude Code: implementar cambios solicitados en rama, comprobar pruebas.
- Codex: revisión independiente en modo solo lectura.
- GitHub Actions: comprobar sintaxis, rutas de archivos sensibles, revisar PR cuando se habilite con credenciales.
- Propietario: aprobar cambios, decidir despliegues, verificar datos/privacidad.

## 5. Prompt de mejora
Para la instrucción de dirección técnica completa, consulta el prompt maestro compartido por el propietario. La versión del repositorio debe mantener directrices generales y no detallar vulnerabilidades explotables mientras el repositorio sea público.

Referencias:
- https://github.com/openai/codex-action
- https://github.com/anthropics/claude-code-action
- https://docs.github.com/en/actions/security-for-github-actions/security-guides/using-secrets-in-github-actions
