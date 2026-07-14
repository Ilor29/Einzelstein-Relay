/* Der Service Worker macht die App installierbar — mehr nicht.
 *
 * Er speichert bewusst NICHTS zwischen. Ohne Server ist diese App wertlos:
 * Sitzungen, Terminal und Vorlesen kommen alle von dort. Eine offline
 * verfügbare Hülle nützt niemandem — sie sorgt nur dafür, dass nach einer
 * Änderung tagelang die alte Fassung ausgeliefert wird. Genau das ist
 * passiert: Die App lud ohne Gestaltung, weil eine veraltete Datei aus dem
 * Zwischenspeicher kam.
 *
 * Also: durchreichen, nichts behalten.
 */

self.addEventListener("install", () => {
  self.skipWaiting();
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    (async () => {
      // Alles wegräumen, was frühere Fassungen zwischengespeichert haben.
      const namen = await caches.keys();
      await Promise.all(namen.map((n) => caches.delete(n)));
      await self.clients.claim();
    })()
  );
});

// Kein fetch-Empfänger: Jede Anfrage geht direkt ans Netz, wie ohne
// Service Worker. Das ist Absicht.
