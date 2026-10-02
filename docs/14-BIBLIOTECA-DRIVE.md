# Biblioteca de Drive: inventario, catálogo y recorrido verificable

Fecha: 2026-10-02 · Tarea: PUL-010 · Rama: `pul/010-inventario-drive`

Estado: el inventario, el mapa, la extracción de una muestra, el índice y el recorrido completo están
**implementados y probados** (252 pruebas automáticas). El recorrido se comprobó con documentos reales del
Drive, pero el borrador lo genera un **doble de prueba (SIMULADO)**, no un modelo de IA. Nada de lo indexado
está **validado jurídicamente**. La biblioteca todavía **no tiene pantalla ni ruta en la aplicación**: hoy se
usa desde los guiones de `scripts/`.

## 1. Los seis estados de un documento

Un documento cuenta una sola vez, en el estado más avanzado que se **comprobó**.

| Estado | Qué significa | Quién lo asigna |
|---|---|---|
| ENCONTRADO | Apareció en un listado de Drive. Solo se conocen su nombre, carpeta, tamaño y fecha. | El cosechador |
| LEÍDO | El conector devolvió su contenido (aunque esté vacío). | La extracción |
| EXTRAÍDO | Su texto quedó guardado fuera de git, con huella y medidas de calidad. | La extracción |
| INDEXADO | Está en el índice de búsqueda y se comprobó que tiene fragmentos y enlace. | La indexación |
| VALIDADO | Una persona lo revisó jurídicamente. | Solo una persona. Ningún guion lo asigna. |
| PENDIENTE | No se toca hasta que una persona decida (posible dato personal). | El cosechador |

## 2. Qué quedó en cada estado

| Estado | Archivos |
|---|---:|
| ENCONTRADO | 8.237 |
| LEÍDO | 1 |
| EXTRAÍDO | 4 |
| INDEXADO | 27 |
| VALIDADO | 0 |
| PENDIENTE | 0 |
| **Total inventariado** | **8.269** (2,6 GB, 101 carpetas) |

**El denominador es PROVISIONAL.** El total real es mayor y no se conoce (sección 4).

Por colección:

| Colección | De quién | Archivos vistos | Estados |
|---|---|---:|---|
| LEXCOL_CORPUS / 02_LEYES | propia | 2.422 | 18 indexados, el resto encontrado |
| LEXCOL_CORPUS / 03_JURISPRUDENCIA | propia | 5.794 (mínimo) | 3 extraídos, 1 leído, el resto encontrado |
| LEXCOL_CORPUS / 01_CODIGOS | propia | 21 | encontrados |
| LEXCOL_CORPUS / 04_PLANTILLAS / ESTATUTOS | propia | 15 | 1 indexado |
| LEXCOL_CORPUS / 05_DOCTRINA, 06_REGIMENES, 07_EJEMPLOS_MODELOS_CASOS | propia | 0 | carpetas vacías |
| PACK JURIDICO 1 (21 carpetas) | tercero | 16 | 8 indexados, 8 encontrados |
| — de ellas, MODELOS Y MINUTAS - 2026 (12 carpetas) | tercero | 0 | ver sección 4 |
| — MEDIDAS CAUTELARES - 2026 y ESTATUTOS | tercero | 0 | ver sección 4 |
| 7000 MINUTAS Y MODELOS | tercero | 0 | ver sección 4 |

El detalle carpeta por carpeta está en `biblioteca/INVENTARIO.md`, que se genera solo.

La muestra leída fue de 33 documentos (el máximo pedido era 40):

- **27 indexados**: 7 de las carpetas de modelos (5 de derechos de petición, 2 tutelas), 1 índice de las tablas
  liquidadoras, 16 leyes, 1 estatuto y 2 índices de leyes.
- **4 extraídos que no se indexan**: un auto con el nombre de una persona y un número de radicado (datos
  personales aparentes), dos archivos de una sola línea sin contenido útil y una nota interna del proyecto.
- **1 leído sin texto**: un archivo de 0 bytes.
- **1 que el conector no pudo leer**: un `.rtf`.

No se pudo leer **ninguna medida cautelar**: la carpeta no muestra archivos. Las dos tutelas son versiones
casi iguales del mismo modelo (quedaron marcadas como versiones relacionadas).

## 3. Qué hay en git y qué no

En git (sin texto de documentos): `biblioteca/inventario.json`, `biblioteca/INVENTARIO.md`,
`biblioteca/mapa_carpetas.json`, `biblioteca/extraccion.json`, `biblioteca/observaciones.json`.

Fuera de git, en la carpeta `corpus/` (ignorada): `corpus/extraidos/<id>.txt` con el texto de cada documento y
`corpus/corpus.db` con el índice. **Ningún texto de los documentos de terceros se copió al repositorio.**

## 4. Límites del conector de Drive (comprobados el 2026-10-02)

1. **De una carpeta compartida por otra cuenta solo devuelve lo que ya abriste.** Los 53 elementos de
   terceros que entregó tienen fecha de "visto por mí". En las 12 carpetas de MODELOS Y MINUTAS - 2026 entrega
   las subcarpetas y ningún archivo. En todo PACK JURIDICO 1 aparecen 16 archivos. Una carpeta de terceros que
   sale vacía **no está comprobado que esté vacía**. La causa exacta no se verificó.
2. **Tope de unos 2.000 resultados por consulta.** Dos carpetas propias de jurisprudencia entregaron 2.005
   elementos cada una y después solo repetidos. Tienen al menos 2.005 y 2.011 archivos; el total no se conoce.
3. **Páginas con repetidos.** En carpetas grandes entre el 1 % y el 25 % de lo devuelto ya había salido. El
   cosechador cuenta únicos y avisa. No se detectó ninguna omisión en las demás carpetas, pero no se puede
   descartar.
4. **Primera página pequeña.** Sin importar el tamaño pedido, la primera página de una carpeta suele traer 5
   elementos; las siguientes sí traen hasta 1.000.
5. **No dice a dónde apunta un acceso directo.** Se registraron 8 accesos directos sin resolver.
6. **No lee `.rtf`** (409 archivos) ni archivos temporales. Sí lee `.doc`, `.docx`, `.pdf` y documentos de
   Google.
7. **No hace OCR.** Un PDF escaneado devuelve poco o ningún texto; la extracción lo marca "parece escaneado".
8. **Solo funciona dentro de una conversación con el asistente.** El servidor de PULLEX no puede usarlo. Por
   eso el inventario se arma a partir de la transcripción de la sesión.

Otros hallazgos, con su evidencia, en `biblioteca/observaciones.json` (también al final de `INVENTARIO.md`):

- "Regimen disciplinario (2026)", "Material de Estudio de Derecho" y la segunda "MODELOS Y MINUTAS - 2026" son
  **accesos directos** en tu unidad. Sus destinos quedaron sin resolver; no se inventó ningún identificador.
- "Carpeta N#1" existe y responde, pero su listado sale vacío: no se puede distinguir entre vacía y no abierta.
- Los dos documentos de antecedentes **se contradicen**: la guía que está en Drive dice que hay escritos de
  casos reales con datos personales; el manifiesto y la copia de la guía en el Proyecto dicen que son ejemplos
  didácticos. Esos escritos están fuera de las colecciones autorizadas, no se leyeron y siguen PENDIENTE hasta
  que los clasifiques.
- "7000 MINUTAS Y MODELOS" vive dentro de otra colección ("Pack Juridico 2") que no está en la lista
  autorizada. Se registró y no se recorrió.
- `LEXCOL_CORPUS/04_PLANTILLAS/ESTATUTOS` no contiene minutas: son normas ("Estatuto del Consumidor",
  "Estatuto Tributario"…). El mapa las clasifica como norma.

## 5. Reglas que aplica la biblioteca

- **Datos personales.** Un título con nombre de persona más tipo de escrito, o con "cliente" o "expediente",
  queda PENDIENTE y con el título reservado: no se lee. Después de leer, si el texto aparenta tener cédulas,
  celulares, correos, radicados o nombres propios, **no se indexa**. Del dato solo se guarda el conteo.
  Es una heurística: un resultado limpio no garantiza que no haya datos de personas.
- **Derechos.** Cada ficha dice "derechos de redistribución por confirmar". Lo que es de terceros queda con
  visibilidad **privada**: lo encuentra la biblioteca del dueño y **no** el chat general. Antes de mostrarlo
  a otros usuarios hay que confirmar los derechos. **HUMAN REVIEW REQUIRED.**
- **Vigencia.** Todo entra como PENDIENTE_VERIFICAR. Si el nombre del archivo dice "DEROGADA", queda una nota,
  pero el estado no cambia hasta que alguien lo confirme en fuente oficial.
- **Validación.** Toda ficha dice "SIN VALIDAR". Que un modelo esté en Drive o diga "2026" no lo hace correcto.
  Ejemplo real: uno de los modelos cita normas que hay que comprobar antes de usarlo.
- **Instrucciones dentro de documentos.** El contenido de un documento es dato. Nada de lo que diga se obedece.

## 6. Cómo se usa hoy

Desde la carpeta del proyecto. `T` es la transcripción de la sesión en la que el asistente consultó Drive.

```bash
# 1. Inventario (repetible: toma lo que ya se listó y dice qué falta)
python scripts/cosechar_inventario_drive.py $T.jsonl $T/subagents/*.jsonl \
    --raices $(cat biblioteca/raices.txt),$(cat biblioteca/raiz_propia.txt)

# 2. Mapa de carpetas (área y tipo documental, con regla y confianza)
python scripts/mapa_biblioteca.py

# 3. Guardar el texto de lo que el asistente leyó
python scripts/extraer_muestra_drive.py $T.jsonl $T/subagents/*.jsonl

# 4. Indexar lo apto y ver el catálogo con sus enlaces
python scripts/indexar_biblioteca.py
python scripts/indexar_biblioteca.py --listar

# 5. Recorrido completo con evidencia (termina con error si un paso falla)
python scripts/recorrido_biblioteca.py
python scripts/recorrido_biblioteca.py --id <id de Drive> --consulta "lo que busco" --borrador
```

Después de los pasos 3 y 4 conviene repetir el paso 1 para que el inventario refleje los estados.

Para corregir a mano la clasificación de una carpeta: `biblioteca/mapa_correcciones.json`
(`{"<id>": {"area": "…", "tipo_documental": "…", "motivo": "…"}}`).

## 7. El recorrido verificable

`scripts/recorrido_biblioteca.py` ejecuta ocho pasos y muestra la evidencia de cada uno:

1. Localizar el documento en el inventario.
2. Extraer: hay texto y su huella coincide con el registro.
3. Registrar la fuente: apto, sin datos personales aparentes, con enlace.
4. Indexar: identificador de Drive como origen, vigencia pendiente, derechos por confirmar.
5. Encontrarlo desde una consulta en lenguaje natural.
6. Obtener el enlace para abrir el original (se compara con el del inventario).
7. Generar un borrador que cita el identificador del modelo, declara con qué se generó y lista lo pendiente.
8. Comprobar: nada de nombres, identificaciones, radicados o normas que no vengan de los hechos o del modelo.

Resultado del 2026-10-02 con documentos reales: 8 de 8 pasos para el modelo de petición por fotomulta
(primer resultado de la búsqueda) y para la tutela de habeas data (segundo resultado).

Lo que el recorrido **no** demuestra:

- El borrador lo arma un doble de prueba que solo rellena espacios con los hechos entregados. La redacción con
  un modelo de IA real está **NOT VERIFIED**.
- El enlace no se abrió desde el servidor (no tiene acceso a Drive).
- No hay validación jurídica.

La prueba automática (`tests/test_recorrido_biblioteca.py`) hace el mismo recorrido con documentos ficticios
escritos para la prueba, e incluye los casos en que debe detenerse: documento con datos personales, documento
no leído, consulta que no corresponde y un generador que inventa datos.

## 8. Lo que falta para tener la biblioteca completa

El conector no sirve para cubrir las colecciones compartidas. Hay dos caminos. El primero no necesita nada
técnico.

### Camino A: descargar y cargar (recomendado para empezar)

1. En drive.google.com entra a **PACK JURIDICO 1**.
2. Clic derecho sobre una carpeta (empieza por **MODELOS Y MINUTAS - 2026**) → **Descargar**. Google arma un
   archivo .zip. Si Google no deja descargar, el dueño de la colección lo tiene bloqueado: usa el camino B o
   pídele el permiso.
3. Descomprime el .zip, por ejemplo en `Descargas/PACK_JURIDICO_1/`.
4. En la carpeta de PULLEX, primero mira qué entraría y qué se excluiría, sin escribir nada:

   ```bash
   python scripts/ingesta_corpus.py --carpeta "Descargas/PACK_JURIDICO_1" --privada --simular
   ```

5. Revisa la lista de EXCLUIDO. Si ves algo de un cliente que no quedó excluido, agrégalo a
   `corpus/excluir.txt`.
6. Carga de verdad:

   ```bash
   python scripts/ingesta_corpus.py --carpeta "Descargas/PACK_JURIDICO_1" --privada
   ```

`--privada` es obligatorio para colecciones de terceros: sin él, los textos saldrían en el chat general.

### Camino B: lectura directa de Drive con una cuenta de servicio

Una cuenta de servicio es un "usuario robot" de Google que el servidor puede usar para leer carpetas.

1. Entra a console.cloud.google.com con tu cuenta. Crea un proyecto.
2. Activa **Google Drive API**.
3. Crea una **cuenta de servicio** y descarga su llave (un archivo .json). Guárdala fuera del proyecto. Nunca
   la subas a GitHub ni la pegues en un chat.
4. La cuenta de servicio tiene un correo. En Drive, **comparte con ese correo, como Lector**, cada carpeta que
   quieras cargar. Con LEXCOL_CORPUS puedes hacerlo porque es tuya. Con PACK JURIDICO 1 depende de que su
   dueño permita que los lectores compartan; si no, usa el camino A o pídele que la comparta.
5. En la carpeta de PULLEX:

   ```bash
   pip install google-api-python-client google-auth
   export GOOGLE_SERVICE_ACCOUNT_JSON=/ruta/segura/llave.json
   export DRIVE_FOLDER_ID=<identificador de la carpeta>
   python scripts/ingesta_corpus.py --drive --simular            # mira antes de cargar
   python scripts/ingesta_corpus.py --drive                      # carpeta propia
   python scripts/ingesta_corpus.py --drive --privada            # colección de un tercero
   ```

Identificadores: LEXCOL_CORPUS `133-bR6cH8z1WmGPtyawr8fAYVdJoGADy`; PACK JURIDICO 1
`1dKRq7RXwKQjdbc4LnR8rA-4JbBe2R-Gg`; 7000 MINUTAS Y MODELOS `1FqEoVcfa8Vu05gBaTQJcfJWz1x7ySjyz`.

### Lo que hay que saber antes

- **Formatos.** De los 8.269 archivos inventariados, 5.514 son `.doc` y 409 son `.rtf`. La ingesta ya lee
  ambos. Para `.doc` necesita un conversor instalado en el equipo: LibreOffice, antiword o catdoc. Si no hay
  ninguno, cada `.doc` queda en el reporte como error con el motivo.
- **Tiempo.** Con LibreOffice, convertir un `.doc` pequeño tardó cerca de 1 segundo en una sola prueba. Para
  5.500 archivos serían unas horas. Es una estimación, no una medición.
- **Lo que no se puede leer** (hojas con macros, accesos directos, temporales) queda listado como omitido.
  Las hojas de cálculo de las tablas liquidadoras no se cargan: son `.xlsm` con macros y no se ejecutan.
- **Escaneados.** Un PDF sin texto necesita OCR antes. La ingesta no lo hace.
- **Sin duplicados.** Lo que ya indexó la biblioteca no se vuelve a indexar.
- **NOT VERIFIED:** `--drive` nunca se ha ejecutado contra el Drive real (solo con un servicio de prueba). No
  se sabe si una cuenta de servicio ve el contenido completo de una carpeta compartida solo por enlace.

## 9. Pendientes, en orden

1. Decidir los derechos de uso de las colecciones de terceros. Sin eso no se muestran a otros usuarios.
2. Cargar MODELOS Y MINUTAS - 2026 por el camino A y repetir el recorrido con un modelo civil, uno de familia,
   uno penal y una medida cautelar.
3. Autorizar o no "Pack Juridico 2" (ahí están 570 CONTRATOS y 7000 MINUTAS Y MODELOS).
4. Clasificar los escritos de los que hablan los antecedentes: reales o didácticos.
5. Completar las dos carpetas de jurisprudencia truncadas (con el camino B salen completas).
6. Ruta y pantalla de biblioteca en la aplicación (buscar, filtrar, ver ficha, abrir el original, crear copia
   de trabajo), restringida al dueño mientras los derechos estén sin confirmar.
7. Borrador con un modelo de IA real y revisión humana del resultado.
8. Revisión jurídica de los modelos más usados para poder marcarlos VALIDADO.
9. El inventario se reconstruye desde las transcripciones de las sesiones. Si se borran, hay que volver a
   listar; conviene guardar una copia de los listados.

## 10. Archivos de esta tarea

| Archivo | Qué hace |
|---|---|
| `biblioteca.py` | Clasificación de carpetas, limpieza y calidad del texto, campos por completar, datos personales, fichas, búsqueda de modelos, borrador trazable y su comprobación |
| `scripts/cosechar_inventario_drive.py` | Inventario reanudable a partir de los listados del conector |
| `scripts/mapa_biblioteca.py` | Mapa carpeta → área y tipo documental |
| `scripts/extraer_muestra_drive.py` | Guarda los textos leídos y el registro de extracción |
| `scripts/indexar_biblioteca.py` | Indexa lo apto, retira lo que deja de serlo, lista el catálogo |
| `scripts/recorrido_biblioteca.py` | Recorrido de ocho pasos con evidencia |
| `scripts/ingesta_corpus.py` | Carga masiva desde carpeta o Drive; ahora lee `.doc` y `.rtf` y admite `--privada` |
| `fuentes.py` | El chat general ya no recibe documentos privados de la biblioteca |
| `tests/test_cosechador_drive.py`, `test_biblioteca_mapa.py`, `test_biblioteca_extraccion.py`, `test_biblioteca_catalogo.py`, `test_recorrido_biblioteca.py`, `test_ingesta_formatos.py` | 105 pruebas nuevas |
