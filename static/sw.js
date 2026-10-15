// Service worker de PULLEX IA — permite instalar la app (Android, iPhone/iPad, escritorio) y abrir la «cara» sin señal.
const CACHE = "pullex-v14";
// Página que se muestra cuando se navega sin conexión (static/sin-conexion.html): no depende de la API ni de cdnjs.
const SIN_CONEXION = "/static/sin-conexion.html";
// SHELL: todo lo que static/index.html enlaza de este mismo sitio (hojas y scripts) más fuentes e imágenes de la cara.
// Si se agrega un <script> o un <link rel="stylesheet"> a la página, va aquí también (lo cuida tests/test_movimiento.py).
const SHELL = ["/", "/static/index.html", "/static/app.js", "/static/tema.css", "/static/justicia.css", "/static/apariencia.js",
  "/static/movimiento.css", "/static/movimiento.js",
  "/static/planes.css", "/static/escritura.css", "/static/calidad.css",
  "/static/planes.js", "/static/documentos.js", "/static/herramientas.js", "/static/biblioteca.js", "/static/perfiles.js", "/static/taller.js",
  "/static/sin-conexion.html", "/static/paginas.css",
  "/static/fonts/inter-var.woff2", "/static/fonts/fraunces-var.woff2",
  "/static/fonts/syne-var.woff2", "/static/fonts/plus-jakarta-sans-var.woff2",
  "/static/img/justicia.webp", "/static/img/justicia-luz.webp", "/static/img/marca/emblema.webp", "/static/icon-192.png", "/static/icon-512.png"];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys().then((ks) => Promise.all(ks.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

// Solo se guarda la cara de la app: la portada, /static/ y el manifiesto. Nada de /salud, /admin ni páginas de error.
function guardable(url) {
  return url.pathname === "/" || url.pathname === "/manifest.webmanifest" || url.pathname.startsWith("/static/");
}
// Una respuesta entra a la caché solo si salió bien (2xx), es de este sitio y el servidor no la marcó «no-store».
function sePuedeGuardar(r) {
  return r && r.ok && r.type === "basic" && !/no-store|private/i.test(r.headers.get("cache-control") || "");
}

self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);
  // Nunca cachear: API/chat, otros dominios, peticiones que no sean GET, ni páginas con
  // enlaces de un solo uso (?token=...) — un token guardado en caché es un token filtrado.
  if (e.request.method !== "GET") return;
  if (url.origin !== self.location.origin) return;
  if (url.pathname.startsWith("/api/")) return;
  if (url.searchParams.has("token") || url.pathname === "/verificar-correo") return;
  const navegacion = e.request.mode === "navigate";
  // Red primero. Sin red: lo guardado de la cara de la app; si es una navegación, la página «Sin conexión»;
  // si no hay nada, un error de red normal (nunca una respuesta inventada con estado 200).
  e.respondWith(
    fetch(e.request).then((r) => {
      if (guardable(url) && sePuedeGuardar(r)) {
        const copia = r.clone();
        caches.open(CACHE).then((c) => c.put(e.request, copia)).catch(() => {});
      }
      return r;
    }).catch(async () => {
      if (navegacion) {
        const pagina = await caches.match(SIN_CONEXION);
        return pagina || new Response("Sin conexión. Revisa tu internet e inténtalo de nuevo.",
          { status: 503, headers: { "content-type": "text/plain; charset=utf-8" } });
      }
      const guardada = guardable(url) ? await caches.match(e.request) : null;
      return guardada || Response.error();
    })
  );
});
