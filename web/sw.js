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

// Das einzige, was hier liegen bleiben darf: was gerade aus einer anderen App
// hereingeteilt wurde, auf dem Weg von Android zur Seite (siehe unten).
const TEILEN_LAGER = "geteiltes";

self.addEventListener("activate", (e) => {
  e.waitUntil(
    (async () => {
      // Alles wegräumen, was frühere Fassungen zwischengespeichert haben — nur
      // das Teilen-Lager nicht, sonst verschwände eine gerade geteilte Datei,
      // bloß weil zufällig eine neue Fassung aktiv wird.
      const namen = await caches.keys();
      await Promise.all(
        namen.filter((n) => n !== TEILEN_LAGER).map((n) => caches.delete(n))
      );
      await self.clients.claim();
    })()
  );
});

/* --- Teilen aus anderen Apps ----------------------------------------------
 *
 * Android schickt Geteiltes nicht an die Seite, sondern als echtes Formular
 * (POST mit Dateien) an die Adresse aus dem Manifest. Eine Seite kann so etwas
 * nicht entgegennehmen — nur der Service Worker kann. Also fängt er genau
 * diese eine Anfrage ab, legt Text und Dateien kurz beiseite und schickt den
 * Browser weiter zur App, die sich das Beiseitegelegte gleich wieder abholt.
 *
 * Sonst gilt weiter: kein Zwischenspeichern, alles geht direkt ans Netz.
 */
self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);
  if (e.request.method === "POST" && url.pathname === "/teilen") {
    e.respondWith(geteiltesAnnehmen(e.request));
  }
  // Alles andere: kein respondWith — der Browser holt es sich selbst.
});

async function geteiltesAnnehmen(anfrage) {
  try {
    const daten = await anfrage.formData();
    const lager = await caches.open(TEILEN_LAGER);

    const texte = ["titel", "text", "url"]
      .map((n) => daten.get(n))
      .filter((t) => typeof t === "string" && t.trim());
    await lager.put("/geteilt/texte", new Response(JSON.stringify(texte)));

    // Die Dateien einzeln ablegen; die Liste daneben merkt sich Name und Art,
    // denn beides überlebt den Umweg über den Zwischenspeicher nicht von selbst.
    const dateien = daten.getAll("dateien").filter((d) => d && d.size >= 0);
    const liste = [];
    for (let i = 0; i < dateien.length; i++) {
      const d = dateien[i];
      const schluessel = `/geteilt/datei/${i}`;
      liste.push({ schluessel, name: d.name || `geteilt-${i}`, typ: d.type || "" });
      await lager.put(schluessel, new Response(d));
    }
    await lager.put("/geteilt/dateien", new Response(JSON.stringify(liste)));
  } catch {
    // Kam etwas zerrissen an, geht die App wenigstens auf — leer statt gar nicht.
  }
  // 303: Der Browser holt die Seite danach mit GET, nicht nochmal per POST.
  return Response.redirect("/teilen?empfangen=1", 303);
}


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
