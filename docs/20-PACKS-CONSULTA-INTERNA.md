# PULLEX IA — consulta interna de Packs Jurídicos 1 y 2

## Fuente y objetivo

La Biblioteca consulta los metadatos del Pack Jurídico 1 y del Pack Jurídico 2 ya
inventariados en `pullex.biblioteca_documentos` (Supabase, esquema privado
`pullex`). Los documentos no se redirigen a Google Drive desde la aplicación.

**No confundir inventario con contenido**: actualmente la importación de ambos
packs contiene fichas; el texto completo requiere extraer e indexar archivos.
El PR no publica títulos privados ni originales en este repositorio público.

## Seguridad

- Solo administradores activos pueden consultar las rutas
  `/api/admin/biblioteca/packs/*`. Los usuarios corrientes no tienen acceso
  a títulos, rutas internas ni fragmentos de terceros.
- Los JSON de la API NO incluyen `drive_id`, `url_origen`, enlaces de Google
  Drive, credenciales ni descargas directas del origen. Solo IDs internos de DB.
- El frontend construye nodos con `textContent`, no inserta HTML del catálogo.
- No configurar `PULLEX_BIBLIOTECA_DATABASE_URL` en JavaScript, HTML, Git,
  `NEXT_PUBLIC_`, `VITE_` ni otra variable expuesta al cliente.
- Usar conexión de servidor a PostgreSQL con TLS, credencial de mínimo privilegio
  y protección del secreto en Vercel. Revisar el PR #4 de seguridad antes de
  habilitar acceso a usuarios no administradores.
- Los permisos de Drive son independientes: ocultar enlaces NO revoca permisos
  que alguna persona ya tenga sobre una carpeta compartida.
- No publicar documentos potencialmente confidenciales sin clasificación,
  autorización de tratamiento, derechos de uso y revisión jurídica.

## Activación de la consulta de metadatos

1. Verificar que existe el esquema `pullex` y las tablas
   `biblioteca_documentos` y `biblioteca_fragmentos` con RLS activada.
2. En Vercel, añadir SOLO al servidor:
   `PULLEX_BIBLIOTECA_DATABASE_URL` (Production y, si procede, Preview).
   No guardar nunca la URL real en el repositorio.
3. Desplegar Preview del PR y autenticar una cuenta administradora activa.
4. Abrir Documentos → Biblioteca → **Packs Jurídicos 1 y 2** → Cargar.
5. Comprobar filtros, paginación y que ninguna respuesta de red incluya
   enlaces al Drive de origen, incluidos errores y pruebas anónimas.
6. Probar que cuentas inactivas y no administradoras obtengan 403/401.

Si la DB no está configurada, la nueva API responde 503 sin revelar secretos.
La biblioteca SQLite antigua continúa activa e independiente.

## Indexación de contenido

Se realiza FUERA de Vercel, en un trabajador seguro con autorización Google
Drive OAuth/ADC y acceso real a los archivos compartidos. El servicio
`drive.readonly` puede requerir autorización OAuth interactiva del propietario
de la cuenta: no basta con que ChatGPT pueda ver metadatos de Drive.

Instalación del trabajador, desde un entorno seguro:

```sh
python -m pip install -r requirements-ingesta.txt
```

Modo simulación (no lee Drive ni modifica la base):

```sh
python scripts/ingestar_contenidos_drive.py --coleccion "PACK JURIDICO 1" --limite 10
```

Cuando las credenciales autorizadas y la conexión PostgreSQL estén presentes:

```sh
python scripts/ingestar_contenidos_drive.py --coleccion "PACK JURIDICO 1" --limite 10 --aplicar
python scripts/ingestar_contenidos_drive.py --coleccion "PACK JURIDICO 2" --limite 10 --aplicar
```

El trabajador soporta PDF con texto, DOCX, documentos Google Docs mediante
exportación y TXT. No hace OCR de imágenes escaneadas ni admite DOC/XLS, y
separa texto por páginas o bloques. Necesita procesamiento complementario
para esos formatos. Antes de ejecutar cargas completas: probar 10 archivos,
validar extracción y permisos, revisar calidad, definir copias de seguridad y
restauración, verificar tamaño/costos y luego aumentar el lote progresivamente.

Para almacenar originales y ofrecer un visor PDF completo sin pasar por Google
Drive, añadir un bucket PRIVADO en Storage con autorización por documento y
descarga servida por backend. Esta primera versión ofrece consulta de texto
indexado, no un visor PDF de originales.

## Endpoints internos

| Ruta | Uso |
| --- | --- |
| `GET /api/admin/biblioteca/packs/resumen` | Conteo de fichas e indexados |
| `GET /api/admin/biblioteca/packs/buscar` | Búsqueda por nombre, carpeta y texto indexado |
| `GET /api/admin/biblioteca/packs/documento/{id}` | Fragmentos ya indexados; no enlace al original |

## Comprobación

```sh
python -m pytest tests/test_biblioteca_packs.py tests/test_ingestar_contenidos_drive.py -q
node --check static/biblioteca.js
```

Sin credenciales de servidor y sin indexación no debe afirmarse que los
documentos estén plenamente consultables. No habilitar a estudiantes o terceros
hasta completar permisos, derechos, revisiones de seguridad y pruebas de
persistencia.
