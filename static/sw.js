// Service worker mínimo de LEXCOL — permite instalar la app y cachea la "cara".
const CACHE = "lexcol-v1";
const SHELL = ["/", "/static/index.html", "/static/icon-192.png", "/static/icon-512.png"];

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
  // Nunca cachear las llamadas a la API ni el chat en streaming: siempre a la red.
  if (url.pathname.startsWith("/api/")) return;
  // Para lo demás: red primero, y si no hay, lo cacheado (permite abrir sin señal la cáscara).
  e.respondWith(
    fetch(e.request).then((r) => {
      const copia = r.clone();
      caches.open(CACHE).then((c) => c.put(e.request, copia)).catch(() => {});
      return r;
    }).catch(() => caches.match(e.request))
  );
});
