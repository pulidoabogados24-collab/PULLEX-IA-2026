# 05 — VISIÓN Y ROADMAP DE PRODUCTO

## Visión
Plataforma de inteligencia jurídica colombiana con método y fuentes verificables. Mercado
inicial: estudiantes de Derecho en Villavicencio (mercado que el fundador conoce y puede
atender personalmente). Regla de marca: el producto no menciona ninguna institución educativa.

## MVP — YA CONSTRUIDO (V1)
- Cuentas de estudiante, planes con límite (Prueba 10 / Básico 200 / Pro 500 / Premium 1.000).
- Precios: $30.000 / $45.000 / $60.000 COP; semestral $150.000 (pago único).
- Panel admin (/admin): activar cuentas, asignar plan, reiniciar uso (cobro manual por Nequi).
- Chat con streaming, agentes por área, confianza+fuentes, adjuntos (PDF/fotos), memoria,
  boletín jurídico diario cacheado, PWA instalable, exportar PDF/Excel, modo degradado.

## V2 — Cuando haya ~20 clientes pagos
| Función | Valor | Complejidad | Prioridad | Estado |
|---|---|---|---|---|
| Prompt caching | Baja el costo por consulta | Baja | Alta | ✅ HECHO |
| Panel de facturación admin (ingresos/costo/margen) | Ver el negocio | Baja | Alta | ✅ HECHO |
| Restablecer contraseña (admin) | Menos soporte manual | Baja | Media | ✅ HECHO |
| Pasarela de pagos (Wompi/MercadoPago) | Cobro automático recurrente | Media | Alta | Pendiente |
| PostgreSQL | Datos robustos y respaldables | Media | Alta | Pendiente |
| Corpus RAG conectado (lexcol-rag) | Respuestas citando códigos propios | Media | Media | Pendiente |
| Verificación de correo (autoservicio) | Menos soporte manual | Baja | Media | Pendiente |
| Métricas de uso y evaluación IA (preguntas doradas) | Calidad medible | Media | Media | Pendiente |

## V3 — Crecimiento (otras universidades / abogados)
- Plan "Profesional" para abogados litigantes (precio mayor, más consultas, Sonnet).
- Versionado normativo ("time travel legal") y motor de precedentes.
- Agentes con herramientas (citación verificable, redacción de piezas con plantillas).
- Equipos/facultades (multi-tenant simple), White Label para consultorios jurídicos.

## Estrategia de crecimiento
1. **Semilla (mes 1):** 10–20 compañeros de confianza a precio de lanzamiento; feedback semanal.
2. **Boca a boca (mes 2-3):** referidos ("trae un amigo → mes con descuento"); grupos de estudio.
3. **Institucional (mes 4+):** propuesta formal a semilleros y consultorios jurídicos (sin usar
   marcas de instituciones sin convenio escrito); luego otras facultades de Derecho de la región.

## Regla de priorización
Toda funcionalidad nueva se evalúa con la ficha de 43-FEATURE (valor usuario, valor negocio,
complejidad, riesgo, dependencias, prioridad, impacto, tiempo). Si no reduce un tiempo LX o
no aumenta ingresos/retención, no entra.
