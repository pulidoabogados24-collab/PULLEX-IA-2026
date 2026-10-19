# Configuración observada de Supabase

18 de octubre de 2026 (Colombia). Proyecto `umbral-licita`, identificado expresamente por el responsable.
Inspección de solo lectura mediante consultas de metadatos y asesor de seguridad; sin expedientes,
consultas de usuarios, secretos, cambios de roles ni migraciones aplicadas.

| Control | Evidencia observada | Alcance y decisión |
|---|---|---|
| Servidor | PostgreSQL 17.11 | CI se amplía a PostgreSQL 17, además de 16; validar también el pooler y cliente de respaldo efectivos |
| Versión de esquema | `pullex.esquema_version` tiene máximo 1 | #8 propone versión 2; probar migración 1→2 sobre copia aislada antes de habilitarla en el despliegue |
| Límites y política | No existe `pullex.limites`; falta `usuarios.acepto_politica_version` | No dar por activos los límites compartidos ni el registro de aceptación de #8 en este proyecto |
| Tablas | 20 tablas en `pullex`, con RLS activada y no forzada | Es configuración observada; no acredita aislamiento de usuarios en la API de PULLEX |
| Roles públicos | `anon`, `authenticated`, `service_role`: sin USAGE en `pullex` y sin SELECT ni INSERT/UPDATE/DELETE efectivos sobre sus tablas | Control favorable; no se alteraron estos permisos |
| Propietario de tablas | Las 20 tablas pertenecen a un rol con BYPASSRLS | El propietario/rol privilegiado evita RLS. No se conoce aún qué rol utiliza realmente Vercel; verificarlo sin asumir aislamiento por RLS |
| Políticas | Asesor informa RLS sin políticas en las 20 tablas | Compatible con el diseño de conexión del dueño en #8. Un lector no dueño de #7 necesita permisos y políticas SELECT explícitas, limitadas a las dos tablas de packs y colecciones autorizadas; no usar credencial del dueño como atajo |
| Exposición Data API | `current_setting('pgrst.db_schemas', true)` no devolvió valor | No permite concluir qué esquemas expone la configuración del servicio; verificar en el panel/API correspondiente |
| Vercel | Metadatos de variables rechazados con 403 en ambos proyectos | Variables efectivas, TLS de conexión, rol de aplicación y separación de entornos continúan no verificados |

No se consultaron filas de packs ni se confirmó de nuevo el inventario de 27.334 fichas.
No se ejecutó restauración operativa ni se accedió a las credenciales Google del trabajador.

## Cierres necesarios antes de aplicar cambios al proyecto compartido

1. Confirmar rol de conexión de la app y estrategia de permisos de migración/runtime; inventariar objetos
   de packs y de base principal. No extender a los packs el privilegio de escritura de la app principal.
2. Obtener copia recuperable; restaurar en destino aislado y probar migración versión 1→2. Comprobar
   filas existentes, aceptación histórica sin inventar consentimientos, límites y esquemas de otros productos.
3. Definir un lector de packs con USAGE, SELECT y políticas que permitan solo las colecciones aprobadas;
   sin escritura ni acceso a cuentas/conversaciones. El trabajador de ingesta usa otro rol/credencial.
4. Verificar permisos como cada rol real con casos positivos y negativos, incluidos campos externos y
   estado de indexación. Conceder SELECT sin una política no basta cuando RLS está activada.
5. Revisar, aplicar en ventana controlada y verificar versión/seguridad; no ejecutar automáticamente
   sobre producción mientras los bloqueos jurídicos, de respaldo y acceso sigan abiertos.

El asesor también informa protección de contraseñas filtradas desactivada en Supabase Auth. PULLEX
implementa autenticación propia; falta establecer la aplicabilidad de ese aviso al servicio antes de
modificar configuración del proyecto compartido.

Referencias de los avisos:
- [RLS sin políticas: guía del asesor de Supabase](https://supabase.com/docs/guides/database/database-linter?lint=0008_rls_enabled_no_policy).
- [Protección de contraseñas de Supabase Auth](https://supabase.com/docs/guides/auth/password-security#password-strength-and-leaked-password-protection).
