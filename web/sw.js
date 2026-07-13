/* Der Service Worker macht die App überhaupt erst zur App: erst dadurch darf
   sie auf den Homescreen und im Vollbild starten.

   Gecacht wird ausschließlich die Hülle — HTML, CSS, Javascript. Sitzungen,
   Terminal und Vorlesen laufen immer live gegen den Server. Würden wir die
   auch zwischenspeichern, sähest du beim Öffnen alte Sitzungsstände, und das
   wäre schlimmer als gar keine App. */

const CACHE = "hetzner-huelle-v1";

const HUELLE = [
  "/",
  "/styles.css",
  "/app.js",
  "/icon.svg",
  "/manifest.webmanifest",
  "/vendor/xterm.js",
  "/vendor/xterm.css",
  "/vendor/xterm-addon-fit.js",
];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(HUELLE)));
  self.skipWaiting();
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys().then((namen) =>
      Promise.all(namen.filter((n) => n !== CACHE).map((n) => caches.delete(n)))
    )
  );
  self.clients.claim();
});

self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);

  // Alles Lebendige geht am Cache vorbei.
  if (url.pathname.startsWith("/api/") || url.pathname.startsWith("/ws/")) return;
  if (e.request.method !== "GET") return;

  // Für die Hülle: erst das Netz fragen, damit Änderungen sofort ankommen;
  // ist kein Netz da, nimm die zwischengespeicherte Fassung.
  e.respondWith(
    fetch(e.request)
      .then((antwort) => {
        const kopie = antwort.clone();
        caches.open(CACHE).then((c) => c.put(e.request, kopie));
        return antwort;
      })
      .catch(() => caches.match(e.request).then((treffer) => treffer || caches.match("/")))
  );
});
