# La Biblioteca en la aplicación: catálogo navegable y registro de motores de IA

Fecha: 2026-10-02 · Tarea: PUL-011 · Rama: `pul/011-biblioteca-app` (incluye `pul/010-inventario-drive`)

Este documento describe la pantalla y las rutas de la Biblioteca. El inventario de Drive, la extracción de la
muestra y los límites del conector están en `docs/14-BIBLIOTECA-DRIVE.md`.

## 1. Estado real de cada capacidad

Estados: PROPUESTO → CONFIGURADO → IMPLEMENTADO → PROBADO → OPERATIVO. «Probado» significa pruebas automáticas
con datos ficticios y con el modelo de IA **simulado**. Nada está OPERATIVO: no se ha desplegado ni lo ha usado
una persona con su biblioteca completa.

| Capacidad | Estado | Evidencia | Qué falta para el siguiente estado |
|---|---|---|---|
| Catálogo desde el inventario de Drive (ficha, ID estable) | PROBADO | `tests/test_biblioteca.py` BIB_001–010; 8.269 archivos reales sincronizados en 2,2 s (segunda pasada, sin cambios: 0,6 s) | Desplegarlo y que el dueño lo use |
| Sincronización incremental | PROBADO | BIB_002–008 (sin cambios, cambio de archivo, retiro, reactivación, inventario truncado) | Un segundo inventario real para ver un cambio de verdad |
| Clasificación por reglas y mapa de carpetas | PROBADO | BIB_020–024; inventario real: 6 modelos, 2.416 normas, 5.796 providencias | Medir aciertos contra una muestra revisada por una persona |
| Búsqueda literal y ampliada, con explicación | PROBADO | BIB_030–036; navegador | Medir si lo que encuentra sirve (conjunto de evaluación) |
| Filtros combinables y paginación | PROBADO | BIB_033–035; navegador a 1280 y 390 px | — |
| Permisos antes de recuperar, sin fuga | PROBADO | BIB_040–045 | Permisos reales por usuario de Drive (hoy hay tres niveles fijos) |
| Ficha, vista previa y enlace al original | PROBADO | BIB_050–054; navegador | Abrir un enlace real desde un navegador con sesión de Drive (NOT VERIFIED) |
| Comparar dos documentos | PROBADO | BIB_060; navegador | — |
| Copia de trabajo sin tocar el original | PROBADO | BIB_070–072; navegador | — |
| Recomendación por caso (determinista) | PROBADO | BIB_080–081; navegador | Medir pertinencia con casos reales |
| Explicación de la recomendación con IA | IMPLEMENTADO | BIB_082 con un doble del modelo | Una llamada real al proveedor (requiere clave y presupuesto) |
| Texto de los modelos dentro del catálogo | IMPLEMENTADO | BIB_090; en un equipo con el corpus del operador se importaron los 27 documentos de la muestra | Cargar el texto en el servidor (hoy el servidor no tiene corpus) |
| Registro de motores de IA | PROBADO | BIB_100–101; navegador (panel de administración) | Medir costo y latencia reales |
| Búsqueda por significado (embeddings) | PROPUESTO | Solo existe el punto de extensión `biblioteca.PUNTUADORES_EXTRA` | Elegir motor, costo y política de datos |
| OCR de escaneados | PROPUESTO | — | Elegir motor |
| Validación jurídica de los modelos | PROPUESTO | El mecanismo existe (`biblioteca/fichas.json`); ningún modelo real está validado | Que un abogado los revise. **HUMAN REVIEW REQUIRED** |

## 2. Qué hay hoy en el catálogo real

Sincronizado desde `biblioteca/inventario.json` (2026-10-02):

| | Cantidad |
|---|---:|
| Archivos en el catálogo | 8.269 |
| Jurisprudencia (propia) | 5.796 |
| Normas (propias y 4 de un tercero) | 2.416 |
| Otros (índices, cuadros, 19 temporales de Word, una nota interna) | 46 |
| **Modelos jurídicos (plantillas y minutas)** | **6** |
| Material de estudio | 3 |
| Tabla de liquidación | 1 |
| Por clasificar | 1 |

- Los **6 modelos** son 4 derechos de petición y 2 tutelas. **Todos son de un tercero**, así que están
  restringidos al administrador (sección 5).
- Un **usuario normal ve 8.251 documentos y 0 modelos**. La pantalla lo dice así: «Todavía no hay modelos
  jurídicos disponibles para tu cuenta».
- El administrador ve 8.268 (los 8.251 más 17 restringidos). El que falta tiene datos personales aparentes y
  solo aparece en la auditoría.
- **El denominador es provisional.** Las colecciones de terceros, donde están las carpetas de modelos y minutas,
  no se han podido enumerar (docs/14, sección 4). No se sabe cuántos modelos hay.
- **Procesamiento en este catálogo:** 8.249 ENCONTRADO y 20 PENDIENTE. El inventario registra además 27
  INDEXADO, 4 EXTRAÍDO y 1 LEÍDO, pero ese trabajo se hizo en el equipo del operador y su texto no está en git
  ni en el servidor. La ficha muestra los dos datos por separado.

## 3. Para quien la usa

Entra a **Documentos** y toca la pestaña **Biblioteca**.

1. **Lee el resumen.** Dice cuántos modelos hay para tu cuenta y, en «Qué cubre hoy la biblioteca y qué falta»,
   qué no se ha podido cargar.
2. **Busca.** Por nombre («petición fotomulta»), por contenido o describiendo el problema («no me responden una
   solicitud»). Cada resultado dice **por qué coincide**.
3. **Filtra.** Tipo documental, área, tipo de escrito, trámite, autoridad, año, carpeta y procesamiento. Se
   combinan. «Quitar filtros» vuelve al inicio.
4. **Mira los chips.** Cada resultado lleva su estado con texto: «Encontrado (solo metadatos)», «Indexado para
   búsqueda», «Sin validar jurídicamente», «Histórico», «Ficha incompleta», «De un tercero».
5. **Abre la ficha.** Trae ID, finalidad, área, supuestos de uso, límites, datos por completar, anexos, fuentes
   citadas, fecha de revisión, enlace al original, versiones relacionadas y estado de validación.
6. **Abrir original en Drive.** Se abre en otra pestaña. Necesitas tener acceso a esa carpeta en tu cuenta de
   Google; la aplicación no descarga el archivo.
7. **Crear copia de trabajo.** Queda en «Mis documentos». El original no se toca. No usa consultas.
8. **Comparar.** Marca «Comparar» en dos resultados y pulsa el botón. Verás qué datos, campos y secciones
   comparten y en cuáles difieren. No dice cuál es mejor.
9. **¿No sabes qué modelo necesitas?** Describe el caso. La biblioteca propone modelos, dice por qué, qué datos
   faltan y qué hay que adaptar. Si no hay uno adecuado, lo dice y te lleva al generador de la pestaña Escritos.

Avisos que verás:

- **«Modelo sin validar jurídicamente»**: nadie lo ha revisado. Estar en Drive o llevar «2026» en el nombre no
  lo hace correcto ni vigente.
- **«Histórico»**: el archivo no se modifica hace más de 24 meses.
- **«Ficha incompleta»**: su contenido no se ha leído o su clasificación está por confirmar.

### Por qué es una pestaña de Documentos y no una sección propia

- En celular la barra inferior ya tiene seis secciones. Una séptima deja 55 px por botón.
- La copia de trabajo termina en «Mis documentos», que está en la misma vista.
- Cuando no hay modelo, la salida es el generador de la pestaña Escritos.

## 4. Los estados (no se mezclan)

| Qué mide | Valores | Quién lo cambia |
|---|---|---|
| Procesamiento **en este catálogo** | ENCONTRADO → LEÍDO → EXTRAÍDO → INDEXADO → VALIDADO, o PENDIENTE | La sincronización y la carga de texto. VALIDADO lo marca una persona con `--validar-procesamiento` |
| Procesamiento según el **inventario** | Los mismos | Los guiones de `docs/14`, fuera de la aplicación |
| **Validación jurídica** | sin validar, en revisión, validado, con observaciones, desactualizado | Solo una persona, en `biblioteca/fichas.json` |
| **Sensibilidad** | SIN_INDICIOS, POSIBLE_DATO_PERSONAL, DATO_PERSONAL_CONFIRMADO | El cosechador, la extracción y la carga de texto; una persona la resuelve en `fichas.json` |
| **Derechos** | propio, autorizado, redistribución por confirmar, no redistribuible | Por defecto según el dueño del archivo; una persona lo cambia en `fichas.json` |
| **Acceso** | general, restringido, excluido | Regla por defecto; una persona lo cambia en `fichas.json` |

Si el archivo cambia en Drive (fecha o tamaño), su texto sale del índice, vuelve a ENCONTRADO y la validación
que no fijó una persona vuelve a «sin validar».

## 5. Permisos

Se aplican **dentro de la consulta a la base**, antes de recuperar nada (`biblioteca.predicado`).

| Nivel | Quién lo ve | Qué entra aquí |
|---|---|---|
| general | Todo usuario con sesión | Material propio sin indicios de datos personales |
| restringido | Solo el administrador | Material de terceros (por defecto) y notas internas del proyecto |
| excluido | Nadie; solo la auditoría | Lo que una persona excluye en `fichas.json` |
| (sensible) | Nadie; solo la auditoría | Todo lo que no sea SIN_INDICIOS |

Lo que un usuario no puede ver no aparece en resultados, conteos, filtros, carpetas, versiones relacionadas ni
recomendaciones. Pedir su ficha responde lo mismo que un identificador que no existe (404).

**Decisiones que solo toma el dueño** (HUMAN REVIEW REQUIRED):

- `PULLEX_BIBLIOTECA_TERCEROS=general` muestra a todos los usuarios las **fichas** del material de terceros.
  Hazlo solo cuando hayas confirmado que puedes mostrarlas.
- `PULLEX_BIBLIOTECA_TEXTO_TERCEROS=1` muestra además su **texto** (vista previa, extractos, copia con texto).
  Sin esto, un usuario recibe la ficha y una copia con la estructura y los campos, sin el texto.

Límite: hoy los permisos son tres niveles fijos y una sola cuenta de administrador. No hay permisos por usuario
tomados de Drive.

## 6. Cómo se llena la ficha

| Campo | De dónde sale |
|---|---|
| ID (`MOD-000123`) | `biblioteca/ids_catalogo.json`. No cambia aunque se rehaga la base |
| Título, carpeta, formato, fechas, enlace | Inventario de Drive |
| Tipo documental, área, tipo de escrito, trámite, autoridad | Reglas sobre el título, la carpeta y el mapa de carpetas. La ficha muestra la regla y la confianza |
| Año | El del nombre o la carpeta; si no lo trae, el de la última modificación. Para una ley es el de su número |
| Finalidad | Descripción general del tipo de escrito (la ficha lo advierte) o la que redacte una persona |
| Datos por completar, anexos, fuentes citadas | Del texto, si está cargado. Si no, los campos típicos del tipo de escrito |
| Supuestos de uso, fecha de revisión, revisor | Solo los escribe una persona |
| Versiones relacionadas | Mismo nombre, misma huella del texto o texto parecido (≥ 50 % de secuencias de cuatro palabras) |

Lo que ninguna regla reconoce queda **«por clasificar»**. Una norma o una providencia llevan **«no aplica»** en
tipo de escrito y trámite. Las fuentes citadas siempre dicen «citada en el texto; no verificada».

Para fijar algo a mano, `biblioteca/fichas.json` (por ID de Drive o de catálogo):

```json
{
  "MOD-008268": {
    "validacion_juridica": "validado",
    "fecha_revision": "2026-11-15",
    "revisor": "Nombre de quien revisó",
    "finalidad": "Pedir la revisión de un comparendo electrónico.",
    "supuestos_uso": ["El comparendo no se notificó en término."],
    "acceso": "general"
  }
}
```

## 7. Búsqueda

- **Literal:** palabras del título, de la clasificación y del texto cargado. Sin tildes ni plurales.
- **Ampliada:** 20 grupos de sinónimos jurídicos («comparendo» ≈ «fotomulta», «amparo» ≈ «tutela») y un
  diccionario de 10 trámites que reconoce descripciones («no me contestan» → derecho de petición).
- **No usa embeddings ni servicios externos.** La pantalla lo dice. «Ampliada» significa diccionarios revisables
  en `biblioteca.py` (`SINONIMOS`, `TRAMITES`), no similitud de significado.
- Por defecto busca solo **modelos**. Si la consulta coincide en normas o jurisprudencia, lo avisa y ofrece
  verlas con un clic.
- **Tiempo medido** con los 8.269 archivos reales: entre 1 y 33 ms por consulta en el servidor (20 consultas
  distintas); 0,36 s en el navegador contando la espera de escritura.

Límites: la búsqueda en el contenido solo cubre documentos con texto cargado. Con el inventario real en git
(solo metadatos), una providencia se encuentra por su número, no por su tema.

## 8. Recomendación

`POST /api/biblioteca/recomendar` con la descripción del caso.

- La parte que decide es **determinista** y no usa consultas: puntaje ≥ 12 y al menos una coincidencia fuerte.
- Cada candidato trae por qué corresponde, qué datos pide el modelo que no se ven en la descripción y qué
  adaptar. Va rotulado «plantilla recuperada».
- **Si ninguno alcanza el umbral, lo dice** y propone tipos del generador para un «borrador nuevo».
- Con `explicar: true`, el modelo de IA redacta una explicación (1 consulta; se reintegra si falla). Recibe solo
  las fichas, nunca el texto de los modelos. Se descartan los candidatos que no se le entregaron.

## 9. Mantenimiento

```bash
# Sincronizar con el inventario (solo procesa lo que cambió)
python scripts/sincronizar_biblioteca.py
python scripts/sincronizar_biblioteca.py --simular        # ver qué cambiaría

# Cargar texto: archivos <id de Drive o MOD-…>.<pdf|docx|doc|rtf|txt|md>
python scripts/sincronizar_biblioteca.py --textos corpus/extraidos
# …o traerlo del corpus del chat
python scripts/sincronizar_biblioteca.py --desde-corpus

# Una persona confirma que texto y clasificación corresponden al original (no es la validación jurídica)
python scripts/sincronizar_biblioteca.py --validar-procesamiento MOD-008268

# Cantidades por estado y por carpeta
python scripts/sincronizar_biblioteca.py --resumen
```

- La aplicación sincroniza sola al arrancar si cambiaron el inventario, las reglas, las fichas, el mapa o la
  política de terceros. Un fallo de la biblioteca no impide que la aplicación arranque.
- Si un inventario nuevo retiraría más de la mitad del catálogo, no retira nada y avisa (inventario truncado).
  `--permitir-retiro-masivo` lo fuerza.
- La base (`biblioteca/biblioteca.db`) no está en git: se reconstruye desde el inventario. Los identificadores
  sobreviven porque `biblioteca/ids_catalogo.json` sí está en git.
- Un texto con cédulas, correos, celulares o radicados aparentes **no se indexa** y queda PENDIENTE.
- En el plan gratuito de Render el disco es efímero: el texto cargado con `--textos` se pierde en cada despliegue.

Variables: `PULLEX_BIBLIOTECA_DB`, `PULLEX_BIBLIOTECA_INVENTARIO`, `PULLEX_BIBLIOTECA_IDS`,
`PULLEX_BIBLIOTECA_FICHAS`, `PULLEX_BIBLIOTECA_MAPA`, `PULLEX_BIBLIOTECA_TERCEROS`,
`PULLEX_BIBLIOTECA_TEXTO_TERCEROS`.

## 10. Rutas

Todas exigen sesión. Las dos últimas, cuenta de administrador.

| Ruta | Qué hace |
|---|---|
| `GET /api/biblioteca/resumen` | Totales por tipo documental, valores de los filtros y notas de cobertura |
| `GET /api/biblioteca/buscar` | `q`, `clase`, `area`, `tipo`, `tramite`, `autoridad`, `anio`, `carpeta`, `estado`, `validacion`, `pagina`, `por_pagina` (máx. 50) |
| `GET /api/biblioteca/modelo/{id}` | Ficha, vista previa (600 caracteres) y enlace a Drive |
| `GET /api/biblioteca/comparar?a=&b=` | Metadatos, campos y secciones de dos documentos |
| `POST /api/biblioteca/modelo/{id}/copia` | Crea la copia en los documentos del usuario. Solo escritos; tope de 40 copias por hora y por cuenta |
| `POST /api/biblioteca/recomendar` | `{caso, explicar}` |
| `GET /api/biblioteca/auditoria` | Todo el inventario, con lo oculto y su motivo |
| `GET /api/admin/motores` | Registro de motores de IA |

## 11. Registro de motores de IA

Es un registro **distinto** del catálogo de modelos jurídicos. Una carpeta de minutas no es un catálogo de
motores.

- `motores_ia.json`: ocho motores que **están en el código** (modelo de lenguaje, boletín, búsqueda web, índice
  del corpus, búsqueda de la biblioteca, clasificador por reglas, extracción de texto y el corpus vectorial
  anterior). No se agregó ningún proveedor que no esté en el código.
- `motores.py` suma si cada uno está configurado en ese servidor. De una clave solo dice si existe.
- Se ve en el panel de administración, botón **Motores de IA**.
- **Costo:** «comprobado» solo con página oficial y fecha; el programa rechaza el archivo si falta la fuente.
  Las cuatro páginas se leyeron dos veces el 2026-10-02. El costo **por consulta** es «desconocido» en todos:
  no se ha medido con tráfico real.
- **Pruebas:** «solo simuladas» en siete motores y «sin pruebas» en el corpus vectorial. Ninguna llamada se ha
  hecho contra un proveedor real.

## 12. Demostración y datos de prueba

- `demo/biblioteca_demo.json`: 19 archivos **ficticios**. Ningún identificador ni enlace existe en Drive.
- `demo/servidor_simulado.py` sirve las rutas reales sobre ese catálogo. Con
  `PULLEX_BIBLIOTECA_INVENTARIO=biblioteca/inventario.json` usa el inventario real.
- `demo/pullex-demo.html` lo incluye; `demo/mock.js` busca, filtra y compara en el navegador con una versión
  simplificada de la búsqueda.
- `tests/datos/`: inventario, fichas y mapa ficticios de las pruebas.

## 13. Pruebas

```bash
python -m pytest -q tests                                     # 297 passed
rm -f pullex.db && PORT=8781 python demo/servidor_simulado.py
BASE=http://127.0.0.1:8781 python3 tests/e2e_biblioteca.py     # 184 comprobaciones
# con el inventario real en un segundo servidor (BASE_REAL): 195 comprobaciones
```

- `tests/test_biblioteca.py`: 45 pruebas.
- `tests/e2e_biblioteca.py`: escritorio (1280 px), celular (390 px), administrador, panel de motores y la
  demostración de un solo archivo. Cero violaciones de CSP, cero errores de consola, sin desbordamiento.
- Regresión: `tests/e2e_documentos.py` 92 comprobaciones y `tests/e2e_navegador.py` 30 de 30.

## 14. Lo que no está verificado

- **NOT VERIFIED:** ninguna llamada a un modelo de IA real. La explicación de la recomendación solo se probó
  con un doble.
- **NOT VERIFIED:** abrir un enlace real de Drive desde la aplicación con la sesión de un usuario.
- **NOT VERIFIED:** la calidad de la clasificación y de la búsqueda sobre el Drive real. Solo se midió el tiempo.
- Ningún modelo real está validado jurídicamente.
- La detección de datos personales es por patrones: puede dejar pasar un caso.
- No hubo revisión manual con lector de pantalla; la accesibilidad se comprobó con teclado y con pruebas
  automáticas (etiquetas, foco, roles).

## 15. Decisiones

1. **Dos módulos.** `biblioteca.py` es el catálogo de la aplicación; `biblioteca_recorrido.py` es el módulo de
   `pul/010-inventario-drive` (mapa, extracción, borrador trazable), renombrado al integrar la rama.
2. **Terceros restringidos por defecto.** Sigue la regla de docs/14: no se muestran a otros usuarios hasta
   confirmar derechos. Consecuencia: hoy un usuario normal no ve ningún modelo real.
3. **Dos estados de procesamiento.** El del catálogo dice lo que esta instalación puede hacer; el del
   inventario, lo que se procesó fuera.
4. **Copia solo de escritos.** Una norma o una providencia se consultan en su original.
5. **El año es el del identificador.** «LEY 767 DE 2002» se filtra por 2002, no por la fecha en que se subió.
6. **Base propia** (`biblioteca.db`), separada del corpus del chat: el chat no recibe material de terceros.

## 16. Pendientes, con su dependencia

| # | Pendiente | Depende de |
|---|---|---|
| 1 | Enumerar las colecciones de terceros (MODELOS Y MINUTAS, MEDIDAS CAUTELARES, 7000 MINUTAS) | Que el dueño las descargue o comparta con una cuenta de servicio (docs/14, sección 8) |
| 2 | Decidir si las fichas y el texto de terceros se muestran a los usuarios | Confirmación de derechos por el dueño. **HUMAN REVIEW REQUIRED** |
| 3 | Texto de los modelos en el servidor | Disco persistente (PUL-003) y el punto 1 |
| 4 | Validar jurídicamente los modelos más usados | Un abogado. **HUMAN REVIEW REQUIRED** |
| 5 | Probar la explicación con IA y medir costo y latencia | `ANTHROPIC_API_KEY` y presupuesto (PUL-008) |
| 6 | Medir la calidad de búsqueda y clasificación | Conjunto de evaluación revisado por una persona |
| 7 | Búsqueda por significado y OCR | Elegir motor, costo y política de datos |
| 8 | Permisos por usuario tomados de Drive | Conector de Drive dentro de la aplicación |
| 9 | Revisar la pantalla con lector de pantalla | Una persona con el lector |
| 10 | Borrar del Drive los 19 temporales de Word | Decisión del dueño |

## 17. Archivos

| Archivo | Qué hace |
|---|---|
| `biblioteca.py` | Esquema, sincronización, clasificación, permisos, búsqueda, ficha, comparar, copia, recomendar, auditoría y rutas |
| `biblioteca_recorrido.py` | Mapa de carpetas, extracción y borrador trazable (docs/14) |
| `motores.py`, `motores_ia.json` | Registro de motores de IA |
| `scripts/sincronizar_biblioteca.py` | Sincronizar, cargar texto, validar procesamiento, resumen |
| `biblioteca/ids_catalogo.json` | Identificadores `MOD-…` del inventario real |
| `static/biblioteca.js`, bloque «Biblioteca» de `static/index.html` | Pantalla |
| `static/admin.js`, `static/admin.html` | Vista del registro de motores |
| `demo/biblioteca_demo.json`, `demo/biblioteca_demo.py`, `demo/mock.js` | Catálogo ficticio de la demostración |
| `tests/test_biblioteca.py`, `tests/e2e_biblioteca.py`, `tests/datos/` | Pruebas |
