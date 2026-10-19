# Cierre de despliegue PULLEX

18 de octubre de 2026. No constituye aprobación de producción.

## Evidencia ejecutada

Commit `165a561d165bfaa0488fabfb3df2794ba2cf02f2`, Ubuntu 24.04, Python 3.11, PostgreSQL 16.15
en servicio desechable de GitHub Actions. Datos sintéticos y credenciales exclusivas de CI.

[Ejecución 39182130548](https://github.com/pulidoabogados24-collab/PULLEX-IA-2026/actions/runs/39182130548):

- SQLite: 1154 aprobadas, 28 omitidas.
- PostgreSQL: 1180 aprobadas, 2 omitidas.
- Restauración focalizada: 2 aprobadas, sin omisiones (copia clara y cifrada).
- Se comprobaron rechazo de destino existente sin forzar, rechazo de confirmación equivocada,
  recuperación de conteos, dato binario, RLS y secuencias, y reemplazo confirmado del esquema de prueba.
- Los informes JUnit quedan como artefactos de esa ejecución con retención de 14 días; archivar la
  evidencia si se necesita conservarla más tiempo. Los logs también identifican commit y resultados.

Este resultado acredita las pruebas indicadas en ese commit; no certifica credenciales reales,
pooler, aislamiento efectivo del proyecto compartido, Vercel ni recuperación de una copia operativa.
Revisar también el CI del commit final de cada PR antes de fusionarlo.

## Verificación pendiente del despliegue (operación + seguridad)

El 18 de octubre se intentó consultar metadatos de variables, sin descifrar valores, en ambos proyectos
Vercel asociados. La API devolvió 403 para el equipo `pulidoabogados24-4353s-projects`. No había CLI de
Vercel disponible. No se verificaron ni cambiaron secretos, despliegues o bases reales.

| Comprobación | Resultado requerido para cerrar | Estado |
|---|---|---|
| Proyecto y entorno | Identificar cuál de los dos proyectos atiende producción; Preview separada y sin BD productiva | No verificado |
| Base principal | URL servidor (`PULLEX_DATABASE_URL`, o fallback documentado), esquema propio, TLS y roles correctos; no SQLite efímera para cuentas | No verificado |
| Catálogo privado #7 | `PULLEX_BIBLIOTECA_DATABASE_URL` servidor, lectura mínima, sin permiso de ingesta ni credenciales Google en runtime | No verificado |
| Secretos | Tipo secreto, alcance por entorno/rama; sin prefijos públicos ni valores en logs/build/cliente; rotar solo si se confirma exposición | No verificado |
| Salud y flujos | `/salud` informa postgres y persistencia; login, conversación, documento y exportación funcionan con cuenta sintética autorizada | No verificado |
| Persistencia real | Conservar los datos sintéticos tras redeploy, arranque en frío y otra instancia; una caída de PostgreSQL debe producir 503 sin guardar en SQLite | No verificado |
| Biblioteca #6 | Resumen y búsqueda dan 200 con sesión válida; repetir tras segundo arranque frío y revisar errores readonly | No verificado |
| Autorización #7 | 401 anónimo; 403 usuario común/inactivo; revocación efectiva y permisos por ID; sin enlaces/IDs Drive en respuestas/DOM/tráfico | No verificado en despliegue |
| Esquema compartido | Permisos efectivos, RLS y exclusión de API pública; comprobar que respaldar/restaurar no toca otros productos | No verificado en proyecto real |

No incluir valores secretos ni datos de clientes en capturas o actas. Registrar fecha, commit,
deployment ID, entorno, método, resultados positivos/negativos y responsable de cada cierre.

## Restauración operativa pendiente (operación + administrador de BD)

1. Autorizar un entorno de recuperación aislado, su almacenamiento y quién puede acceder al volcado.
2. Obtener una copia operativa cifrada y su suma; custodiar la clave por separado. No usar datos reales
   en CI pública ni subir el volcado como artefacto de estas pruebas.
3. Restaurar en PostgreSQL aislado con destino explícito, sin tráfico de la app; conservar el original.
4. Comparar filas y contenido, binarios, secuencias y permisos; comprobar alcance del esquema y los
   efectos de las bajas atendidas después de la fecha del respaldo.
5. Medir pérdida máxima de datos y tiempo de recuperación contra objetivos aprobados; probar acceso
   de la app al entorno restaurado con cuentas autorizadas y registrar el acta.
6. Confirmar almacenamiento externo, retención aprobada, alertas ante fallos y custodia de claves.
   Solo después activar la programación de respaldos y comprobar la primera ejecución.

## Decisiones de fusión

- #6 ya está fusionado: conservarlo como mitigación de escritura, sin presentarlo como persistencia.
- #8: conflicto resuelto; mantener borrador hasta cerrar revisión jurídica y comprobaciones reales de
  configuración/recuperación. Las suites aisladas tienen evidencia favorable.
- #7: depende de la integración con #8; mantener administrador activo y trabajar con datos sintéticos.
  Ingesta real y ampliación de acceso requieren credenciales autorizadas, derechos y validación por lote.
- No activar producción a partir de un CI verde si estos controles siguen abiertos.
