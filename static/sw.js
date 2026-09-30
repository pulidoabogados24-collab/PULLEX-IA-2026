// Service worker mínimo de LEXCOL — permite instalar la app y cachea la "cara".
const CACHE = "pullex-v3";
const SHELL = ["/", "/static/index.html", "/static/app.js", "/static/icon-192.png", "/static/icon-512.png"];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys().then((ks) => Promise.all(ks.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);
  // Nunca cachear: API/chat, otros dominios, peticiones que no sean GET, ni páginas con
  // enlaces de un solo uso (?token=...) — un token guardado en caché es un token filtrado.
  if (e.request.method !== "GET") return;
  if (url.origin !== self.location.origin) return;
  if (url.pathname.startsWith("/api/")) return;
  if (url.searchParams.has("token") || url.pathname === "/verificar-correo") return;
  // Para lo demás: red primero, y si no hay, lo cacheado (permite abrir sin señal la cáscara).
  e.respondWith(
    fetch(e.request).then((r) => {
      const copia = r.clone();
      caches.open(CACHE).then((c) => c.put(e.request, copia)).catch(() => {});
      return r;
    }).catch(() => caches.match(e.request))
  );
});
