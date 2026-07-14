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


/* --- Benachrichtigungen ---------------------------------------------------
 *
 * Das Einzige, wofür der Service Worker hier wirklich gebraucht wird: Er
 * empfängt Nachrichten vom Server, auch wenn die App geschlossen ist und das
 * Handy in der Tasche steckt.
 */

self.addEventListener("push", (e) => {
  let inhalt = { titel: "Hetzner", text: "", sitzung: "" };
  try {
    inhalt = { ...inhalt, ...e.data.json() };
  } catch {
    // Kaputte Nachricht — dann eben ohne Text.
  }

  e.waitUntil(
    self.registration.showNotification(inhalt.titel, {
      body: inhalt.text,
      icon: "/icon.svg",
      badge: "/icon.svg",
      // Nachrichten zur selben Sitzung ersetzen einander, statt sich zu
      // stapeln. Zehn Meldungen zu "shop-backend" will niemand.
      tag: inhalt.sitzung || "hetzner",
      renotify: true,
      data: { sitzung: inhalt.sitzung },
    })
  );
});

// Tippt man die Nachricht an, soll die App aufgehen — und zwar in der Sitzung,
// um die es geht.
self.addEventListener("notificationclick", (e) => {
  e.notification.close();
  const ziel = e.notification.data?.sitzung
    ? `/?sitzung=${encodeURIComponent(e.notification.data.sitzung)}`
    : "/";

  e.waitUntil(
    (async () => {
      const fenster = await self.clients.matchAll({
        type: "window",
        includeUncontrolled: true,
      });
      // Läuft die App schon? Dann nach vorne holen, statt sie neu zu öffnen.
      for (const f of fenster) {
        if (f.url.includes(self.location.origin)) {
          await f.focus();
          f.postMessage({ oeffne: e.notification.data?.sitzung });
          return;
        }
      }
      await self.clients.openWindow(ziel);
    })()
  );
});
