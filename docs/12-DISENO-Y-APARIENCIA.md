# 12 — Diseño y apariencia personalizable

Rediseño de octubre de 2026. Reemplaza el azul marino y dorado anteriores por una dirección
**editorial-jurídica contemporánea**: papel cálido, tinta y un solo color de acento, tipografía con
serifa para los títulos y una sans muy legible para el texto. Nada de estética "IA": sin degradados
neón, brillos, robots, cerebros ni vidrio morado. El único guiño gráfico es el signo de párrafo **§**,
que aparece grande y muy tenue en el ingreso y en el Inicio.

## Dónde está cada cosa

| Archivo | Qué contiene |
|---|---|
| `static/tema.css` | Fuentes (`@font-face`), **tokens semánticos**, los 6 temas en claro y oscuro, alias de los nombres viejos y primitivas comunes (botones, campos, monograma). Lo usan `index.html`, `admin.html` y `restablecer.html`. |
| `static/apariencia.js` | Motor de apariencia. Se carga en `<head>` **antes de pintar**: lee la última apariencia de este navegador (`localStorage`) y pone los atributos `data-*` en `<html>`. También calcula los colores derivados de un acento libre. |
| `static/index.html` | Componentes de la app (solo con tokens), sprite de íconos SVG propios y el marcado de todas las vistas. |
| `static/app.js` | Sección **Ajustes → Apariencia**, guardado en la cuenta, procesamiento de imágenes con canvas. |
| `static/fonts/` | Inter, Fraunces y Source Serif 4 (variables, subconjunto latino, licencia OFL incluida). |
| `scripts/contraste_temas.py` | Mide el contraste de cada tema leyendo `tema.css`; sale con error si algo baja de AA. |

## Tokens semánticos (obligatorios para vistas nuevas)

`--bg` (fondo de la página) · `--surface` (tarjetas, paneles) · `--surface-2` (relleno sutil,
campos secundarios) · `--border` · `--border-strong` (bordes de campos, ≥ 3:1) · `--text` ·
`--text-2` (texto secundario) · `--accent` (botón principal, foco) · `--accent-ink` (texto sobre el
acento) · `--accent-soft` (fondo suave del acento) · `--accent-text` (el acento usado como texto o
enlace) · `--ok` · `--warn` · `--danger` · `--info` · `--radius` / `--radius-sm` / `--radius-lg` ·
`--font-body` · `--font-display` · `--font-ui` · `--shadow` / `--shadow-lg` · `--scrim` (velo de
modales).

Reglas: el texto de color va con `--accent-text`, nunca con `--accent` (en algunos temas el acento
de botón no llega a 4,5:1 como texto). Para un fondo de estado usa
`color-mix(in oklab, var(--ok) 13%, var(--surface))` con el texto en `var(--ok)`. Clases útiles:
`.display` (títulos con la fuente de display), `.eyebrow` (rótulo pequeño en mayúsculas), `.bpri`,
`.bsec`, `.bghost`, `.inp`, `.panel`, `.mono` (monograma).

**Compatibilidad:** los nombres viejos (`--azul`, `--azul2`, `--azul3`, `--linea`, `--oro`, `--oro2`,
`--oro-d`, `--txt`, `--txt2`, `--ok`, `--mal`, `--radio`) siguen existiendo como alias de los nuevos,
y `body.claro` / `body.oscuro` se siguen poniendo, para no romper código anterior.

## Paleta por defecto (tema PULLEX)

| Token | Claro | Oscuro |
|---|---|---|
| `--bg` | `#f7f5f0` papel | `#141311` |
| `--surface` | `#ffffff` | `#1c1b18` |
| `--surface-2` | `#f0ede6` | `#252320` |
| `--border` | `#e4dfd5` | `#35322d` |
| `--text` | `#1b1a17` tinta | `#eeebe4` |
| `--text-2` | `#5c574e` | `#aaa49a` |
| `--accent` | `#b33a16` bermellón | `#ee7a4f` |
| `--accent-ink` | `#ffffff` | `#1d0d06` |
| `--ok` / `--warn` / `--danger` | `#1d7347` / `#965400` / `#b42318` | `#55c793` / `#e9a640` / `#f2766b` |

## Temas curados

| Id | Nombre | Idea | Acento claro / oscuro |
|---|---|---|---|
| `pullex` | PULLEX (por defecto) | Papel, tinta y bermellón | `#b33a16` / `#ee7a4f` |
| `notario` | Notario | Marfil y tinta azul-negra | `#22385e` / `#a9bee3` |
| `bogota` | Bogotá | Gris piedra y pizarra | `#2d5876` / `#8db7d6` |
| `caribe` | Caribe | Arena y turquesa | `#0a7570` / `#3cc7bd` |
| `toga` | Toga | Negro y vino | `#7b1e34` / `#d96f87` |
| `jardin` | Jardín | Verde salvia | `#43654e` / `#9bc4a5` |

Ocho acentos predefinidos (se pueden combinar con cualquier tema): Bermellón `#b33a16`, Tinta
`#22385e`, Cobalto `#2f54c9`, Turquesa `#0a7570`, Salvia `#43654e`, Vino `#7b1e34`, Ocre `#93600c`,
Grafito `#3d3c39`, más un **selector libre** (`input type=color`).

**Acento libre con contraste garantizado** (`PXA.derivar` en `apariencia.js`): elige tinta blanca o
casi negra según cuál contraste más y, si aun así no llega a 4,5:1, oscurece o aclara el acento en
pasos hasta lograrlo; en modo oscuro además aclara el acento hasta que se distinga del fondo
(≥ 3:1). `--accent-soft` es el acento mezclado con la superficie (12 % en claro, 20 % en oscuro) y
`--accent-text` se ajusta hasta tener ≥ 4,5:1 sobre fondo, superficie y acento suave. Ejemplo
medido en el navegador: un amarillo `#ffe14d` queda con botón 14,36:1 y texto 5,08:1; un azul
`#1b2a4a` en modo oscuro queda con botón 6,03:1, texto 5,58:1 y 3,08:1 contra el fondo.

## Tipografía

Autohospedada (la CSP no permite Google Fonts; `font-src 'self' data:` ya estaba en la política).
Se descargaron con `npm pack` de `@fontsource-variable/*` y se usa solo el subconjunto latino
(incluye tildes, ñ, ¿ ¡), en versión variable (un archivo cubre todos los pesos), con
`font-display: swap`:

| Archivo | Tamaño |
|---|---:|
| `inter-var.woff2` (texto e interfaz) | 47 KB |
| `fraunces-var.woff2` (títulos, monograma) | 36 KB |
| `source-serif-4-var.woff2` (par «Clásica») | 50 KB |
| **Total** | **133 KB** (tope pedido: 400 KB) |

Pares elegibles: **Editorial** (Fraunces + Inter, por defecto), **Clásica** (Source Serif 4 para
títulos y lectura) y **Moderna** (todo en Inter). Inter y Fraunces se precargan; Source Serif solo
se descarga si alguien elige «Clásica».

## Movimiento

Transición de entrada en cada vista, aparición escalonada de tarjetas, entrada de cada mensaje del
chat, indicador de escritura, barras de la rúbrica que crecen, micro-interacciones al pasar el
cursor y al presionar, esqueletos de carga en boletín, tablero e historial. Todo se apaga con
`prefers-reduced-motion: reduce` (regla global en `tema.css`).

## Navegación

Escritorio: pestañas con ícono en la cabecera. Móvil (< 760 px): **barra inferior tipo app** con
íconos SVG propios + texto (respeta `env(safe-area-inset-bottom)`); el área principal deja espacio
para ella, así el cuadro del chat queda siempre visible encima. Íconos: sprite `<symbol>` en
`index.html`, trazo 1,75 sobre retícula de 24, puntas redondeadas.

## Logo e íconos de la app

Monograma: una **P** en Fraunces sobre el color de acento con una raya fina debajo (como la línea
de una firma). Junto a él, la palabra **PULLEX** en Fraunces espaciada. El monograma de la cabecera
toma el acento del tema del usuario. `favicon.png`, `apple-touch-icon.png`, `icon-192.png`,
`icon-512.png` e `icon-maskable.png` se rasterizaron con Playwright a partir de ese monograma;
`manifest.webmanifest` usa `#f7f5f0` como `theme_color` y `background_color`.

## Personalización por usuario (Ajustes → Apariencia)

Opciones: **modo** (claro / oscuro / automático según el sistema), **tema** (6), **acento** (8 + libre
+ «el del tema»), **tipografía** (3 pares), **tamaño del texto** (normal / grande = 112,5 %),
**densidad** (cómoda / compacta = espacios × 0,72), **esquinas** (rectas / suaves / redondas),
**imágenes** (fondo del Inicio, foto de perfil, logo propio) y **Restablecer apariencia**.
Cada cambio se aplica al instante en toda la app (más una vista previa en escritorio) y se guarda
con una espera de 450 ms para no enviar una petición por clic.

### Cómo se guarda

- **En la cuenta (fuente de verdad):** `POST /api/preferencias` con `{"apariencia": {...}}`. El
  servidor (`app.py`: `APARIENCIA_OPCIONES`, `actualizar_apariencia`) acepta solo claves de la lista
  blanca; ignora las desconocidas; responde **400** si un valor no está permitido, si el acento no es
  `#rrggbb` o si una imagen no es válida; los cambios son parciales (lo no enviado se conserva). El
  interruptor rápido «Modo claro» (`tema`) se sincroniza con `apariencia.modo`.
- **Imágenes aparte:** tabla `apariencia_imagenes(usuario, tipo, mime, data, actualizado)` y
  `GET /api/apariencia/imagen/{fondo|avatar|logo}` con autenticación (cada usuario solo lee las
  suyas: la clave es su correo). En las preferencias solo queda la **versión** de cada imagen
  (`apariencia.imagenes`), así `/api/estado` no carga cientos de KB en cada ingreso. Como `<img>` no
  envía el token, la app la pide con `fetch` + `Authorization` y la muestra como `blob:`.
  Se eligió esto en vez de guardar la data URL en el perfil por peso (el fondo puede llegar a
  350 KB) y para no exponer imágenes en una respuesta que se pide muchas veces.
- **Validación de imágenes:** solo `data:image/jpeg;base64,` o `data:image/png;base64,`; además se
  verifica la **firma real** del archivo (PNG `\x89PNG` + IHDR, JPEG `FFD8FF` + marcador SOF) y las
  **dimensiones** leídas de la cabecera. Topes: fondo 350 KB y 1600 px; avatar y logo 120 KB y
  512 px. SVG, GIF, WebP, URLs externas y cualquier otra cosa se rechazan (un SVG servido desde el
  propio origen podría traer scripts).
- **En el navegador, antes de subir:** canvas. Fondo: máx. 1600 px de lado, JPEG 0,8 (baja a 0,72,
  0,64, 0,56 y luego reduce el tamaño hasta quedar en ≤ 350 KB). Avatar: recorte cuadrado centrado
  de 256 px, JPEG. Logo: cabe en 512 × 128 px, PNG (conserva transparencia; si pesa más de 120 KB,
  JPEG). Una foto de 3600 × 2400 (5,3 MB) quedó en 1600 × 1067 y 297 KB.
- **En este navegador (pintado rápido):** `localStorage["pullex.apariencia.v1"]`, solo las opciones
  (no las imágenes, por tamaño y privacidad en equipos compartidos). Todo con `try/catch`: en modo
  privado o con el almacenamiento bloqueado la app funciona igual, solo que pinta el tema por defecto
  hasta que el usuario ingresa.
- **CSP:** no hizo falta cambiarla. Ya tenía `img-src 'self' data: blob:` (miniaturas, fondo y
  avatar) y `font-src 'self' data:` (fuentes locales y la demo con fuentes incrustadas). Ningún
  JavaScript en línea: los controles de Apariencia se crean con `addEventListener`.

## Contraste medido (WCAG 2.x, `python scripts/contraste_temas.py`)

Mínimo de cada grupo de pares (AA exige 4,5:1 para texto y 3:1 para bordes de controles):

| Tema | Modo | Texto | Texto secundario | Texto sobre botón | Acento como texto | Estados (ok/ámbar/rojo) | Borde de campo |
|---|---|---:|---:|---:|---:|---:|---:|
| PULLEX | claro | 14.88 | 6.13 | 5.94 | 5.38 | 5.84 | 3.75 |
| PULLEX | oscuro | 13.16 | 6.33 | 6.77 | 6.20 | 6.22 | 3.67 |
| Notario | claro | 14.57 | 5.87 | 11.70 | 9.68 | 5.79 | 3.64 |
| Notario | oscuro | 12.86 | 6.61 | 9.60 | 8.41 | 6.28 | 3.99 |
| Bogotá | claro | 13.23 | 5.74 | 7.58 | 6.59 | 5.59 | 3.61 |
| Bogotá | oscuro | 12.12 | 6.03 | 8.37 | 7.22 | 5.91 | 3.83 |
| Caribe | claro | 13.23 | 5.58 | 5.54 | 5.17 | 5.75 | 3.75 |
| Caribe | oscuro | 12.84 | 6.62 | 8.21 | 7.04 | 5.97 | 3.94 |
| Toga | claro | 15.74 | 6.61 | 10.11 | 8.18 | 5.84 | 3.86 |
| Toga | oscuro | 14.73 | 6.99 | 5.78 | 6.21 | 6.69 | 3.88 |
| Jardín | claro | 13.98 | 5.88 | 6.54 | 5.89 | 5.72 | 3.63 |
| Jardín | oscuro | 12.64 | 6.35 | 8.75 | 7.55 | 6.04 | 3.91 |

Peor par de texto en todos los temas: **5,17:1** (acento como texto sobre acento suave, Caribe
claro). Además se corrió **axe-core 4.10 (regla `color-contrast`)** sobre las pantallas reales
—Inicio, Laboratorio de casos con caso evaluado, Mi mapa con un concepto abierto, Consultar con fuentes
desplegadas y Ajustes— en los 6 temas × 2 modos: **0 infracciones**.

No verificado: texto sobre una **foto de fondo** subida por el usuario (axe no puede medir sobre
imágenes). Se mitiga con un velo oscuro de 78 % a 25 % de izquierda a derecha y el texto alineado a
la izquierda, pero una foto muy clara podría bajar el contraste del lado derecho.
