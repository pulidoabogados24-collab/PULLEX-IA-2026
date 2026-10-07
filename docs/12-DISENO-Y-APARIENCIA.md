# 12 — Diseño y apariencia personalizable

La app tiene **un sistema de diseño y siete temas**. Desde octubre de 2026 el tema por defecto es
**«Justicia × Inteligencia»**, la dirección que aprobó el dueño del producto: grafito, una imagen
fuerte por pantalla (el retrato de la Justicia) y tres luces tomadas de esa misma imagen (lima, cian y
rosa). Los otros seis temas conservan la dirección anterior, **editorial-jurídica**: papel cálido,
tinta, un solo color de acento y títulos con serifa; en ellos el guiño gráfico sigue siendo el signo de
párrafo **§**, grande y muy tenue en el Inicio.

Lo que NO cambia con ningún tema: nada de estética genérica de «IA». Sin degradados morados o arcoíris,
sin manchas de color flotando, sin vidrio esmerilado, sin robots ni cerebros, sin emojis como íconos,
sin partículas ni fondos animados. El neón de «Justicia × Inteligencia» no es un adorno aplicado a la
interfaz: es la luz que ya trae la imagen de la Justicia, y la interfaz solo la cita con avaricia (ver
«Tema por defecto» y «Movimiento»).

## Dónde está cada cosa

| Archivo | Qué contiene |
|---|---|
| `static/tema.css` | Fuentes (`@font-face`), **tokens semánticos**, los 6 temas en claro y oscuro, alias de los nombres viejos y primitivas comunes (botones, campos, monograma). Lo usan `index.html`, `admin.html` y `restablecer.html`. |
| `static/apariencia.js` | Motor de apariencia. Se carga en `<head>` **antes de pintar**: lee la última apariencia de este navegador (`localStorage`) y pone los atributos `data-*` en `<html>`. También calcula los colores derivados de un acento libre. |
| `static/justicia.css` | Capa «Justicia × Inteligencia»: barra lateral, barra superior con miga, retrato (`.retrato`), portada, estado inicial de Consultar y accesibilidad común (foco, objetivos táctiles de 44 px). Sirve a todos los temas. |
| `static/movimiento.css` | Todo lo que se mueve: coreografías de entrada, estados de trabajo, microinteracciones y la transición entre secciones. Usa solo los tokens `--mv-*` de `tema.css`. |
| `static/movimiento.js` | Lo que el CSS no puede hacer solo: partir el titular de la portada por líneas, paralaje del retrato, borde de luz de las tarjetas, indicador de la barra lateral, View Transitions y cifras que cuentan. Expone `window.MV`; la app funciona igual si no carga. |
| `static/img/` | `justicia.webp`/`.jpg` (retrato), `justicia-luz.webp` (solo las vetas de neón del retrato, sobre transparente) y `marca/emblema.webp` (busto vendado). |
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

## Tema por defecto: «Justicia × Inteligencia»

Es lo que ve quien nunca eligió otra apariencia (`data-tema="justicia"`, oscuro, par tipográfico `syne`).

| Rol | Token | Valor (oscuro) |
|---|---|---|
| Fondo / tarjeta / relleno | `--bg` / `--surface` / `--surface-2` | `#101115` / `#17191e` / `#24282f` |
| Texto / texto secundario | `--text` / `--text-2` | `#f4f6f9` / `#979da7` |
| Acción principal (lima) | `--accent`, `--lima` | `#d9ff68`, con texto `#101115` |
| Acento como texto y enlaces (cian) | `--accent-text`, `--cian` | `#68e4f4` |
| Error y segunda luz (rosa) | `--danger`, `--rosa` | `#ff73b1` |

- **Tipografía:** Syne (titulares, peso 600; marca 800) y Plus Jakarta Sans (texto), alojadas en
  `static/fonts/`. Ningún texto por debajo de 12 px.
- **El retrato** (`.retrato` en `justicia.css`): la estatua de la Justicia, vendada y con la balanza,
  en mármol con vetas de luz cian y rosa. Es **la única idea fuerte de cada pantalla** donde aparece:
  panel a sangre en la portada (izquierda) y en el estado inicial de Consultar (**derecha**, para que el
  titular y las sugerencias queden donde empieza la lectura); franja superior en pantallas angostas; fondo
  de la tarjeta de saludo en el Inicio. Siempre lleva el lema **JUSTICIA × INTELIGENCIA** (con el signo ×
  en lima). Es una pieza de marca siempre oscura: trae sus propios colores y se ve igual sobre cualquier tema.
- **El emblema:** el busto de la Justicia vendada dentro de un círculo (`static/img/marca/emblema.webp`),
  junto a la palabra **PUL·LEX·IA** (LEX en lima, IA en cian). Reemplaza al monograma «P» solo en este
  tema; los demás temas conservan el monograma con el acento del usuario.
- **Nombre:** el producto y el asistente se llaman **PULLEX IA**. La figura de la Justicia no tiene nombre
  propio en la interfaz: se presenta con el lema.
- **Lima con avaricia:** solo para la acción principal de la pantalla (enviar, «Nueva consulta», ingresar),
  el indicador de dónde estás y **un** acento (la segunda línea del titular de Consultar, el × del lema, el
  día de vencimiento en el calendario de términos). El cian es el color de enlaces, rótulos y foco de
  lectura; el rosa queda para errores y para una de las cuatro sugerencias.
- **Estados sin depender del color:** todo estado va escrito («Corpus · verificar vigencia», «Buscando en
  fuentes…», «Vence»), y el color solo acompaña.

## Paleta del tema PULLEX (el anterior por defecto)

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

El movimiento es parte del sistema de diseño, no una capa de efectos. Vive en `static/movimiento.css`
(y lo poco que necesita JavaScript, en `static/movimiento.js`).

### Lenguaje: cinco duraciones y tres curvas (`tema.css`)

| Token | Valor | Para qué |
|---|---:|---|
| `--mv-instante` | 90 ms | Respuesta al toque: presionar y soltar. |
| `--mv-rapida` | 160 ms | Hover, foco, cambios de color. |
| `--mv-media` | 260 ms | Entra una pieza: mensaje, ficha, aviso. |
| `--mv-lenta` | 420 ms | Piezas grandes: titular, panel, indicador de navegación. |
| `--mv-escena` | 700 ms | Una vez por pantalla: el revelado del retrato. |
| `--mv-paso` | 60 ms | Separación entre piezas de una misma serie. |
| `--mv-entra` | `cubic-bezier(.2,.8,.2,1)` | Llega y frena. Es la curva por omisión de las entradas. |
| `--mv-sale` | `cubic-bezier(.55,0,.9,.4)` | Arranca y se va. Las salidas duran menos que las entradas. |
| `--mv-enfasis` | `cubic-bezier(.34,1.4,.64,1)` | Rebote leve. Solo para lo que el usuario acaba de tocar o para la pieza que remata una serie. |

Los nombres anteriores (`--t-rapida`, `--t-media`, `--curva`) siguen existiendo como alias. Los bucles
(esqueleto de carga, cursor de escritura, respiración del retrato, aros de estado) tienen su propio
periodo escrito en la regla, porque no son transiciones entre dos estados.

**Regla de oro:** cada tipo de pieza entra a su manera. Un rótulo se desliza, un titular se descubre por
líneas, un párrafo solo aparece, una tarjeta sube con un rebote leve, el compositor sube sin rebote, el
retrato se revela desde su borde. Si todo entra con el mismo fundido hacia arriba, está mal.

### Qué se mueve hoy

- **Portada:** el retrato se revela (de izquierda a derecha; de arriba abajo en móvil), el × del lema da un
  giro corto, el titular entra por líneas, la tarjeta de ingreso sube y las cuatro características esperan a
  entrar en pantalla. El botón de ingreso dice «Ingresando…» mientras el servidor responde.
- **Consultar, estado inicial:** rótulo → titular por líneas → bajada → sugerencias una a una →
  compositor; el retrato se revela desde la derecha. La escena completa se ve **una vez por sesión**; las
  siguientes visitas entran sin coreografía, para que volver a Consultar nunca haga esperar.
- **Retrato:** las vetas de neón «respiran» muy despacio (7,5 s). No es un filtro: es una segunda imagen
  con solo las vetas (`justicia-luz.webp`) a la que se le anima la opacidad. Con ratón, la figura y los
  rótulos se separan unos píxeles según el puntero (paralaje de 2 a 6 px); en táctil no hay paralaje.
- **Trabajo real:** mientras la app espera o recibe una respuesta, `app.js` pone `data-trabajo` en `<html>`
  (`ingreso`, `espera`, `fuentes`, `escribe`) con los eventos reales del envío y del stream. Con eso laten
  las vetas del retrato, aparece un aro en el emblema de la cabecera y en el avatar de la respuesta (arco
  que gira al esperar o buscar en fuentes; aro completo al escribir), el punto de «consultas» suelta una
  onda, el botón de enviar cambia la flecha por un aro y junto al nombre se lee el estado («Esperando la
  respuesta…», «Buscando en fuentes…», «Escribiendo…»).
- **Chat:** el mensaje propio sale del compositor; la respuesta solo aparece. El texto que llega no salta:
  el bloque nunca encoge mientras se escribe, una negrita a medio llegar se cierra de forma provisional y
  la conversación solo sigue el final si la persona ya estaba ahí (si subió a releer, no se la arrastra).
  Al terminar, las fuentes citadas se despliegan una a una como fichas, encima del bloque «Fuentes
  consultadas».
- **Navegación:** un solo indicador se desliza por la barra lateral de un destino a otro. El cambio de
  sección usa la View Transitions API (lo que se va sale rápido, lo que llega sube 10 px); donde no
  existe, la sección cambia como siempre.
- **Microinteracciones:** presionar encoge el control a 0,98 y soltar lo devuelve con un rebote leve; el
  anillo de foco se asienta desde el borde; las tarjetas del Inicio y de Consultar llevan un borde de luz
  que sigue al puntero (solo con ratón); las cifras de progreso y del mapa cuentan hasta su valor real; los
  avisos entran con rebote leve y salen más rápido.
- **Herramientas → Términos:** un calendario dibuja día por día cómo se contó el plazo (qué días contaron,
  cuáles no y por qué) y remata en el vencimiento. Usa la misma cronología que la tabla.

### Límites (no se negocian)

1. **Nada finge trabajo.** Un indicador de estado solo existe si lo enciende un estado real de `app.js`.
   No hay temporizadores que simulen «pensando», ni barras de progreso inventadas.
2. **Solo `transform`, `opacity` y `clip-path`.** Nada cambia de tamaño ni empuja a sus vecinos; nada
   provoca reflujo en bucle; no hay `will-change` permanente.
3. **Movimiento reducido.** Con `prefers-reduced-motion: reduce`, o con **Ajustes → Apariencia →
   Movimiento: Reducido**, todo el bloque de movimiento deja de existir: el contenido aparece ya en su
   sitio, sin paralaje, sin transiciones entre secciones y con los estados de trabajo quietos (el aro se
   ve, no gira; el texto de estado sigue ahí).
4. **Nada parpadea** más de tres veces por segundo, y lo único que se mueve solo por más de cinco segundos
   es opacidad (respiración del retrato) o un indicador de carga mientras hay una carga real.
5. **El contenido no depende de JavaScript para verse.** Los estados ocultos de partida viven dentro de la
   propia animación (`animation-fill-mode: backwards`). Si `movimiento.js` no carga, todo se ve igual; si
   lo que no carga es `movimiento.css`, simplemente no hay coreografía.
6. **Sin librerías.** CSS, Web Animations, View Transitions e IntersectionObserver del navegador. La CSP
   no cambió.

### Cómo agregar movimiento nuevo

Usa un token de duración y una de las tres curvas; escribe la regla dentro del bloque
`@media (prefers-reduced-motion:no-preference){ :root:not([data-movimiento="reducido"]){ … } }` de
`movimiento.css`; define solo el fotograma `from` y usa `backwards`; y pregúntate qué explica ese
movimiento. Si la respuesta es «nada, se ve bonito», no va.

Además siguen existiendo los esqueletos de carga (boletín, tablero, historial y ahora Mi mapa y
Herramientas), las barras de la rúbrica que crecen y el indicador de escritura.

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

Opciones: **modo** (claro / oscuro / automático según el sistema), **tema** (7), **acento** (8 + libre
+ «el del tema»), **tipografía** (4 pares), **tamaño del texto** (normal / grande = 112,5 %),
**densidad** (cómoda / compacta = espacios × 0,72), **esquinas** (rectas / suaves / redondas),
**movimiento** (completo / reducido), **imágenes** (fondo del Inicio, foto de perfil, logo propio) y
**Restablecer apariencia**. «Movimiento» se guarda **solo en este navegador** (el servidor aún no tiene
ese campo en `APARIENCIA_OPCIONES`); por eso la interfaz dice «Guardado en este navegador» y no «en tu
cuenta». Para que viaje con la cuenta basta agregarlo a esa lista en `app.py` y quitar la excepción de
`apCambiar` en `app.js`.
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
