/* Hetzner-App — die Logik.
   Vier Ansichten, ein Terminal, ein Vorlese-Knopf. Kein Framework, kein
   Bauschritt: Datei ändern, Seite neu laden, fertig. */

// Welche Fassung im Handy läuft, entscheidet allein der Server: Er trägt seine
// Versionsnummer beim Ausliefern in die Seite ein und liefert die Seite nie aus
// dem Zwischenspeicher (siehe server.py:index). Stil und Logik hängen mit
// dieser Nummer im Namen daran — bei jedem Öffnen frisch. Darum braucht es hier
// keinen zweiten, fest eingebauten Zähler mehr, der mit dem Server auseinander-
// laufen und die App in eine Neulade-Schleife schicken konnte. Genau daran bist
// du immer wieder hängengeblieben.
const $ = (id) => document.getElementById(id);

const ANSICHTEN = ["anmeldung", "geraet", "liste", "sitzung", "neu", "einstellungen", "bibliothek"];

function zeige(name) {
  for (const a of ANSICHTEN) $(`ansicht-${a}`).hidden = a !== name;
}

// Aus einer Server-Antwort einen lesbaren Fehlersatz machen. FastAPI schickt
// bei einer Formularprüfung `detail` als LISTE von Objekten — landet die roh in
// einer Fehlermeldung, steht dort nur "[object Object]". Also die Klartext-Teile
// (`msg`) herausziehen.
function fehlerText(körper) {
  const d = körper?.detail;
  if (typeof d === "string") return d;
  if (Array.isArray(d)) {
    const saetze = d.map((f) => f?.msg).filter(Boolean);
    if (saetze.length) return saetze.join("; ");
  }
  return null;
}

async function api(pfad, optionen = {}) {
  const antwort = await fetch(`/api${pfad}`, {
    headers: { "Content-Type": "application/json" },
    ...optionen,
  });
  if (antwort.status === 401) {
    zeige("anmeldung");
    throw new Error("Nicht angemeldet.");
  }
  if (!antwort.ok) {
    const körper = await antwort.json().catch(() => ({}));
    throw new Error(fehlerText(körper) || `Fehler ${antwort.status}`);
  }
  return antwort;
}

// --- Anmeldung mit Geräteschlüssel -------------------------------------------
//
// Kein Passwort. Das Gerät erzeugt sich ein Schlüsselpaar; der geheime Teil ist
// so angelegt, dass er sich nicht auslesen lässt — auch nicht von diesem Code.
// Angemeldet wird sich, indem das Gerät eine Zufallsaufgabe des Servers
// unterschreibt.

const SCHLUESSEL_LAGER = "hetzner-app-schluessel";

function b64(puffer) {
  return btoa(String.fromCharCode(...new Uint8Array(puffer)));
}

// Der Schlüssel lebt in der IndexedDB des Browsers. Dort dürfen auch Dinge
// liegen, die man nicht auslesen kann — im localStorage ginge das nicht.
function lager(modus, arbeit) {
  return new Promise((fertig, fehler) => {
    const anfrage = indexedDB.open("hetzner-app", 1);
    anfrage.onupgradeneeded = () => anfrage.result.createObjectStore("schluessel");
    anfrage.onerror = () => fehler(anfrage.error);
    anfrage.onsuccess = () => {
      const db = anfrage.result;
      const laden = db.transaction("schluessel", modus).objectStore("schluessel");
      const auftrag = arbeit(laden);
      auftrag.onsuccess = () => fertig(auftrag.result);
      auftrag.onerror = () => fehler(auftrag.error);
    };
  });
}

async function schluesselHolen() {
  let paar = await lager("readonly", (s) => s.get(SCHLUESSEL_LAGER));

  if (!paar) {
    // extractable: false — der geheime Schlüssel kann das Gerät nicht verlassen.
    paar = await crypto.subtle.generateKey(
      { name: "ECDSA", namedCurve: "P-256" },
      false,
      ["sign", "verify"]
    );
    await lager("readwrite", (s) => s.put(paar, SCHLUESSEL_LAGER));
  }
  return paar;
}

async function oeffentlicherSchluessel(paar) {
  return b64(await crypto.subtle.exportKey("spki", paar.publicKey));
}

async function anmelden() {
  const paar = await schluesselHolen();

  const { aufgabe } = await (await fetch("/api/aufgabe")).json();

  const unterschrift = await crypto.subtle.sign(
    { name: "ECDSA", hash: "SHA-256" },
    paar.privateKey,
    new TextEncoder().encode(aufgabe)
  );

  const antwort = await fetch("/api/anmelden", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ aufgabe, unterschrift: b64(unterschrift) }),
  });

  if (!antwort.ok) throw new Error("nicht freigeschaltet");
  return antwort.json();
}

async function zeigeSchluessel() {
  const paar = await schluesselHolen();
  $("schluessel").textContent = await oeffentlicherSchluessel(paar);
  zeige("geraet");
}

$("knopf-kopieren").addEventListener("click", async () => {
  const knopf = $("knopf-kopieren");
  try {
    await navigator.clipboard.writeText($("schluessel").textContent);
    knopf.textContent = "Kopiert ✓";
    setTimeout(() => (knopf.textContent = "Schlüssel kopieren"), 2000);
  } catch {
    // Kein Zugriff auf die Zwischenablage — dann markieren wir ihn eben.
    const bereich = document.createRange();
    bereich.selectNodeContents($("schluessel"));
    getSelection().removeAllRanges();
    getSelection().addRange(bereich);
    knopf.textContent = "Markiert — jetzt kopieren";
  }
});

$("knopf-nochmal").addEventListener("click", start);

// --- Sitzungsübersicht -------------------------------------------------------

const ETIKETT = {
  running: "läuft",
  waiting: "wartet auf dich",
  idle: "ruht",
  sleeping: "schläft — antippen weckt",
  crashed: "abgestürzt — antippen setzt fort",
};

function alter(sekunden) {
  // Fehlt der Wert oder ist er keine Zahl, lieber gar nichts zeigen als
  // "vor NaN Min." auf der Karte.
  if (!Number.isFinite(sekunden)) return "";
  if (sekunden < 60) return "gerade eben";
  const minuten = Math.round(sekunden / 60);
  if (minuten < 60) return `vor ${minuten} Min.`;
  const stunden = Math.round(minuten / 60);
  if (stunden < 24) return `vor ${stunden} Std.`;
  const tage = Math.round(stunden / 24);
  return tage === 1 ? "gestern" : `vor ${tage} Tagen`;
}

// "krugmeister-website:krugmeister-website" ist kein Name, den ein Mensch
// lesen will. Steht überall dasselbe, sagen wir es einmal.
function lesbar(kennung) {
  const [server, sitzung] = kennung.split(":");
  if (!sitzung) return kennung;
  return server === sitzung ? server : `${server} · ${sitzung}`;
}

// Wie die Sitzung heißen soll: der selbstvergebene Name, sonst der technische.
function benannt(s) {
  return s.anzeige || lesbar(s.name);
}

function karte(sitzung) {
  const el = document.createElement("div");
  el.className = "karte" + (sitzung.pinned ? " angeheftet" : "");
  el.innerHTML = `
    <div class="streifen"></div>
    <div class="zeile-oben">
      <span class="name"></span>
      <button class="nadel" aria-label="Anheften">
        <svg viewBox="0 0 24 24"><use href="#i-nadel"/></svg>
      </button>
      <button class="mond" aria-label="Sitzung schlafen legen — Speicher freigeben">
        <svg viewBox="0 0 24 24"><use href="#i-mond"/></svg>
      </button>
    </div>
    <div class="vorschau"></div>
    <div class="angaben">
      <span class="etikett"></span>
      <span class="wann"></span>
      <span class="terminals"></span>
    </div>
  `;
  // Zustand als CSS-Klasse — aber nur, wenn wir ihn kennen. Käme vom Server je
  // ein unbekannter Zustand, stünde sonst wörtlich "undefined" auf der Karte,
  // und ein interpolierter Wert im class-Attribut bricht das sonst eiserne
  // Muster "Daten nie in HTML-Vorlagen".
  const bekannt = Object.prototype.hasOwnProperty.call(ETIKETT, sitzung.state);
  if (bekannt) {
    el.querySelector(".streifen").classList.add(sitzung.state);
    el.querySelector(".etikett").classList.add(sitzung.state);
  }
  el.querySelector(".etikett").textContent = bekannt ? ETIKETT[sitzung.state] : "unbekannt";

  // Über textContent gesetzt, nicht über innerHTML — ein Sitzungsname oder
  // eine Terminalzeile darf kein HTML in die Seite schmuggeln.
  el.querySelector(".name").textContent = benannt(sitzung);

  // Ein Schild, mehrere Terminals: Im selben Projekt läuft Claude womöglich
  // auch am Rechner. Der Verlauf zeigt alles davon; getippt wird in eines.
  // Das soll man wenigstens sehen können.
  if (sitzung.terminals > 1) {
    el.querySelector(".terminals").textContent = `${sitzung.terminals} Terminals`;
  }
  el.querySelector(".vorschau").textContent = sitzung.preview || "—";
  el.querySelector(".wann").textContent = alter(sitzung.idleSeconds);

  // Eine schlafende oder abgestürzte Sitzung wacht beim Antippen erst auf:
  // Claude startet im alten Ordner und setzt das Gespräch fort — das
  // braucht einen Moment. Für beide Zustände gilt dasselbe, nur wie sie dort
  // hingekommen sind, unterscheidet sich (sanft eingeschlafen vs. abgerissen).
  const weckbar = sitzung.state === "sleeping" || sitzung.state === "crashed";
  el.addEventListener("click", async () => {
    if (!weckbar) {
      oeffneSitzung(sitzung);
      return;
    }
    try {
      melde("Ich wecke die Sitzung — einen Moment …");
      await api(`/sessions/${encodeURIComponent(sitzung.name)}/wecken`, { method: "POST" });
    } catch (err) {
      melde(err.message || "Das Aufwecken hat nicht geklappt.");
      return;
    }
    oeffneSitzung({ ...sitzung, state: "idle" });
    ladeListe();
  });

  // Der Mond legt die Sitzung schlafen: Terminal weg, Speicher frei, Karte
  // bleibt. Nur bei eigenen, wachen Sitzungen — fremde fasst die App nicht an.
  const mond = el.querySelector(".mond");
  if (!sitzung.eigen || weckbar) {
    mond.hidden = true;
  }
  mond.addEventListener("click", async (e) => {
    e.stopPropagation();   // sonst öffnet sich gleichzeitig die Sitzung
    try {
      await api(`/sessions/${encodeURIComponent(sitzung.name)}/schlafen`, { method: "POST" });
      melde("Schläft — der Speicher ist frei. Antippen weckt sie wieder.");
      ladeListe();
    } catch (err) {
      melde(err.message || "Schlafen legen ging gerade nicht.");
    }
  });

  el.querySelector(".nadel").addEventListener("click", async (e) => {
    e.stopPropagation();   // sonst öffnet sich gleichzeitig die Sitzung
    try {
      await api(`/sessions/${encodeURIComponent(sitzung.name)}`, {
        method: "PATCH",
        body: JSON.stringify({ pinned: !sitzung.pinned }),
      });
      ladeListe();
    } catch (err) {
      melde(err.message || "Anheften ging gerade nicht.");
    }
  });

  return el;
}

// Welche klappbaren Gruppen gerade offen stehen — gemerkt über die Neuladungen
// hinweg. Ohne das baute der 5-Sekunden-Takt die Liste neu und klappte alles
// wieder zu; man tippte auf, und beim nächsten Takt war es zu.
const offeneGruppen = new Set();

async function ladeListe() {
  let sitzungen;
  try {
    sitzungen = await (await api("/sessions")).json();
  } catch {
    return;   // nicht angemeldet — die Ansicht hat schon gewechselt
  }

  const liste = $("liste");
  liste.replaceChildren();

  if (sitzungen.length === 0) {
    const leer = document.createElement("p");
    leer.className = "leer";
    leer.textContent = "Noch keine Sitzung. Starte unten deine erste.";
    liste.append(leer);
    return;
  }

  // Wer auf dich wartet, kommt nach oben — egal ob angeheftet oder nicht.
  // Das ist die eine Sache, die du sofort sehen musst.
  const wartend = sitzungen.filter((s) => s.state === "waiting");
  const rest = sitzungen.filter((s) => s.state !== "waiting");

  const angeheftet = rest.filter((s) => s.pinned);
  const eigene = rest.filter((s) => !s.pinned && s.eigen);
  const fremde = rest.filter((s) => !s.pinned && !s.eigen);

  const gruppe = (titel, eintraege, { zu = false } = {}) => {
    if (eintraege.length === 0) return;

    // Steht die Gruppe schon offen? Dann beim Neuaufbau offen lassen.
    const offen = offeneGruppen.has(titel);

    const kopf = document.createElement("div");
    kopf.className = "gruppe" + (zu ? " klappbar" : "");
    kopf.innerHTML = `
      ${zu ? `<span class="pfeil">${offen ? "▾" : "▸"}</span>` : ""}
      <span class="titel"></span>
      <span class="anzahl">${eintraege.length}</span>`;
    kopf.querySelector(".titel").textContent = titel;
    liste.append(kopf);

    const karten = eintraege.map(karte);
    if (!zu) {
      liste.append(...karten);
      return;
    }

    // Eingeklappt: Die fremden Sitzungen sind viele, und meistens will man
    // sie nicht sehen. Ein Tipp auf die Zeile klappt sie auf — und der Zustand
    // bleibt über die Neuladungen hinweg erhalten.
    const fach = document.createElement("div");
    fach.className = "fach";
    fach.hidden = !offen;
    fach.append(...karten);
    liste.append(fach);

    kopf.addEventListener("click", () => {
      fach.hidden = !fach.hidden;
      kopf.querySelector(".pfeil").textContent = fach.hidden ? "▸" : "▾";
      if (fach.hidden) offeneGruppen.delete(titel);
      else offeneGruppen.add(titel);
    });
  };

  gruppe("Wartet auf dich", wartend);
  gruppe("Angeheftet", angeheftet);
  gruppe("Zuletzt benutzt", eigene);
  // Sitzungen, die nicht von dieser App stammen — allen voran die, in der
  // Claude Code gerade selbst läuft. Eingeklappt, weil es viele sind.
  gruppe("Läuft auch auf dem Server", fremde, { zu: true });
}

// Die Speicher-Ampel des Wächters (siehe hetzner_app/speicher.py): grün /
// gelb / rot samt Zahlen; bei Rot mit dem dicksten Chat dahinter. Eigener,
// langsamer Takt — der Wächter misst nur alle drei Minuten, öfter fragen
// bringt nichts Neues.
async function ladeSpeicher() {
  let stand;
  try {
    stand = await (await api("/speicher")).json();
  } catch {
    return;   // nicht angemeldet oder Funkloch — dann bleibt die alte Anzeige
  }
  const zeile = $("speicher-zeile");
  if (!stand?.ampel) { zeile.hidden = true; return; }

  zeile.classList.remove("gruen", "gelb", "rot");
  zeile.classList.add(stand.ampel);
  let text = `Speicher: ${stand.verfuegbarMb} MB verfügbar · `
    + `Swap ${stand.swapBenutztMb}/${stand.swapGesamtMb} MB`;
  if (stand.ampel === "rot" && stand.dicksterChat) {
    text += ` — am dicksten: ${stand.dicksterChat.name} (${stand.dicksterChat.mb} MB)`;
  }
  $("speicher-text").textContent = text;
  zeile.hidden = false;
}

let listenTakt = null;
let speicherTakt = null;

function starteListe() {
  zeige("liste");
  ladeListe();
  ladeSpeicher();
  clearInterval(listenTakt);
  // Alle fünf Sekunden nachsehen — so wandert eine Sitzung von "läuft" nach
  // "wartet auf dich", ohne dass du etwas tun musst.
  listenTakt = setInterval(ladeListe, 5000);
  clearInterval(speicherTakt);
  speicherTakt = setInterval(ladeSpeicher, 60000);
}

function stoppeListe() {
  clearInterval(listenTakt);
  listenTakt = null;
  clearInterval(speicherTakt);
  speicherTakt = null;
}

// --- Eine Sitzung ------------------------------------------------------------

let term = null;
let fit = null;
let steckdose = null;      // die WebSocket-Verbindung
let aktuelleSitzung = null;

// Die Tasten, die einer Handytastatur fehlen — ohne die man Claude Code
// schlicht nicht bedienen kann.
const SONDERTASTEN = [
  { text: "Esc",    sendet: "\x1b",  warm: true },
  { text: "Strg+C", sendet: "\x03",  warm: true },
  { text: "Tab",    sendet: "\t" },
  { text: "↑",      sendet: "\x1b[A" },
  { text: "↓",      sendet: "\x1b[B" },
  { text: "←",      sendet: "\x1b[D" },
  { text: "→",      sendet: "\x1b[C" },
  { text: "/",      sendet: "/" },
  { text: "@",      sendet: "@" },
  { text: "⏎",      sendet: "\r" },
];

function baueSondertasten() {
  const leiste = $("sondertasten");
  leiste.replaceChildren();
  for (const taste of SONDERTASTEN) {
    const knopf = document.createElement("button");
    knopf.type = "button";
    knopf.className = "taste" + (taste.warm ? " warm" : "");
    knopf.textContent = taste.text;
    knopf.addEventListener("click", () => {
      steckdose?.send(taste.sendet);
      term?.focus();
    });
    leiste.append(knopf);
  }
}

// --- Die Unterhaltung zum Lesen ----------------------------------------------
//
// Das Terminal ist zum Arbeiten richtig, zum Nachlesen auf dem Handy aber
// unerträglich: Kreisel drehen, Statuszeilen blinken, Rohtext scrollt. Hier
// steht nur, was zählt — was du gesagt hast und was Claude geantwortet hat.
// Code und Werkzeuge sind eingeklappt, bis du sie sehen willst.

let imTerminal = false;
let verlaufTakt = null;

// Freisprech-Modus: Ist er an, liest die App eine fertige Antwort von selbst
// vor und öffnet danach das Mikrofon — freihändig, ohne einen Knopf. Die
// Einstellung überlebt das Neuladen.
let freisprech = (() => {
  try { return localStorage.getItem("freisprech") === "1"; } catch { return false; }
})();

// Ob Claude gerade beschäftigt ist — geglättet über einen Puffer (denktBis),
// damit kurze Atempausen zwischen zwei Schritten nicht als "fertig" durchgehen.
// Daran hängt alles: Senden gesperrt, "denkt nach"-Anzeige, und der Sprung von
// beschäftigt zu fertig (Freisprech). `warBeschaeftigt` merkt sich den vorigen
// Stand, damit wir "fertig" genau einmal treffen.
let beschaeftigt = false;
let warBeschaeftigt = false;

// Was zuletzt vorgelesen wurde. So erkennt der Freisprech-Modus, ob die frische
// Antwort schon da ist — oder ob die Mitschrift noch am vorigen Block hängt, den
// du längst kennst. Dann warten wir kurz auf die neue.
let zuletztVorgelesen = "";

/** Setzt Claudes Text — mit Fettschrift, Kursiv und Befehlen.
 *
 *  Claude schreibt in Markdown. Ungerendert stehen dann Sternchen und
 *  Backticks im Text herum, und "**wichtig**" liest sich schlechter als
 *  wichtig. Bewusst kein Framework: Wir bauen die Elemente selbst und setzen
 *  jeden Text über textContent — so kann aus einer Antwort niemals HTML werden,
 *  das die Seite verändert.
 */
// Ein mehrzeiliger Code-Kasten mit eigenem Kopierknopf. Auf dem Handy ist
// Markieren und Kopieren die Hölle — und gerade Befehle will man mit einem Tipp
// haben, nicht mühsam mit dem Finger einkreisen.
function codeKasten(code) {
  const box = document.createElement("div");
  box.className = "codekasten";

  const pre = document.createElement("pre");
  pre.textContent = code;

  const knopf = document.createElement("button");
  knopf.className = "code-kopieren";
  knopf.setAttribute("aria-label", "Code kopieren");
  knopf.innerHTML = `<svg viewBox="0 0 24 24"><use href="#i-kopieren"/></svg>`;
  knopf.addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText(code);
      knopf.classList.add("getan");
      knopf.querySelector("use").setAttribute("href", "#i-haken");
      setTimeout(() => {
        knopf.classList.remove("getan");
        knopf.querySelector("use").setAttribute("href", "#i-kopieren");
      }, 1600);
    } catch {
      alert("Kopieren hat nicht geklappt.");
    }
  });

  box.append(pre, knopf);
  return box;
}

// Inline-Auszeichnung eines Textstücks: **fett**, *kursiv*, `befehl`.
function inlineSchreiben(ziel, text) {
  const teile = text.split(/(\*\*[^*]+\*\*|`[^`]+`|\*[^*\n]+\*)/g);
  for (const teil of teile) {
    if (!teil) continue;
    let el;
    if (teil.startsWith("**") && teil.endsWith("**") && teil.length > 4) {
      el = document.createElement("strong");
      el.textContent = teil.slice(2, -2);
    } else if (teil.startsWith("`") && teil.endsWith("`") && teil.length > 2) {
      el = document.createElement("code");
      el.textContent = teil.slice(1, -1);
    } else if (teil.startsWith("*") && teil.endsWith("*") && teil.length > 2) {
      el = document.createElement("em");
      el.textContent = teil.slice(1, -1);
    } else {
      el = document.createTextNode(teil);
    }
    ziel.append(el);
  }
}

function schreibe(ziel, text) {
  // Erst an mehrzeiligen Code-Blöcken (```…```) trennen; der Rest bekommt die
  // Inline-Auszeichnung.
  const segmente = text.split(/(```[\s\S]*?```)/g);
  for (const seg of segmente) {
    if (!seg) continue;
    if (seg.startsWith("```") && seg.endsWith("```") && seg.length > 6) {
      // Eine etwaige Sprach-Angabe in der ersten Zeile ("bash") fällt weg, der
      // abschließende Umbruch auch.
      const code = seg.slice(3, -3).replace(/^[a-zA-Z0-9_-]*\n/, "").replace(/\n$/, "");
      ziel.append(codeKasten(code));
    } else {
      inlineSchreiben(ziel, seg);
    }
  }
}

function verlaufBlock(block) {
  const el = document.createElement("div");

  if (block.typ === "du") {
    el.className = "gesagt";

    const blase = document.createElement("div");
    blase.className = "blase du";
    blase.textContent = block.text;

    // Nochmal senden. Genau für den Fall, dass ein Diktat verloren ging oder
    // Claude nicht antwortete: einmal tippen, statt alles neu zu sprechen.
    const leiste = document.createElement("div");
    leiste.className = "gesagt-leiste";

    const nochmal = document.createElement("button");
    nochmal.className = "klein-knopf";
    nochmal.setAttribute("aria-label", "Nochmal an Claude senden");
    nochmal.innerHTML = `<svg viewBox="0 0 24 24"><use href="#i-nochmal"/></svg>`;
    nochmal.addEventListener("click", async () => {
      if (!confirm("Diese Nachricht nochmal an Claude senden?")) return;
      try {
        await sendeInSitzung(block.text);
        nochmal.classList.add("getan");
        nochmal.querySelector("use").setAttribute("href", "#i-haken");
        setTimeout(() => {
          nochmal.classList.remove("getan");
          nochmal.querySelector("use").setAttribute("href", "#i-nochmal");
        }, 1600);
      } catch (err) {
        alert(err.message || "Senden hat nicht geklappt.");
      }
    });

    leiste.append(nochmal);
    el.append(blase, leiste);
    return el;
  }

  // Ein Foto, das du geschickt hast. Es steht dort als Bild, nicht als
  // kryptischer Pfad — sonst weißt du nach zehn Minuten nicht mehr, welches.
  if (block.typ === "bild") {
    el.className = "foto du";

    const bild = document.createElement("img");
    bild.src = `/api/bilder/${encodeURIComponent(aktuelleSitzung.name)}`
             + `/${encodeURIComponent(block.datei)}`;
    bild.alt = "Geschicktes Foto";
    bild.loading = "lazy";
    // Antippen zeigt es groß.
    bild.addEventListener("click", () => window.open(bild.src, "_blank"));
    el.append(bild);

    if (block.text) {
      const unterschrift = document.createElement("div");
      unterschrift.className = "bildunterschrift";
      unterschrift.textContent = block.text;
      el.append(unterschrift);
    }
    return el;
  }

  if (block.typ === "claude") {
    el.className = "antwort";

    const text = document.createElement("div");
    text.className = "blase claude";
    schreibe(text, block.text);

    const leiste = document.createElement("div");
    leiste.className = "antwort-leiste";

    // Jede Antwort hat ihren eigenen Lautsprecher. Sonst kann man immer nur
    // die letzte hören — und muss den Rest lesen, obwohl man Auto fährt.
    const hoeren = document.createElement("button");
    hoeren.className = "klein-knopf";
    hoeren.setAttribute("aria-label", "Diesen Absatz vorlesen");
    hoeren.innerHTML = `<svg viewBox="0 0 24 24"><use href="#i-lautsprecher"/></svg>`;
    hoeren.addEventListener("click", () => sprich(block.text, hoeren));

    // Kopieren. Auf dem Handy ist Markieren mit dem Finger die Hölle — und
    // Claude nennt einem ständig Befehle und Pfade, die man woanders braucht.
    const kopieren = document.createElement("button");
    kopieren.className = "klein-knopf";
    kopieren.setAttribute("aria-label", "Text kopieren");
    kopieren.innerHTML = `<svg viewBox="0 0 24 24"><use href="#i-kopieren"/></svg>`;
    kopieren.addEventListener("click", async () => {
      try {
        await navigator.clipboard.writeText(block.text);
        kopieren.classList.add("getan");
        kopieren.querySelector("use").setAttribute("href", "#i-haken");
        setTimeout(() => {
          kopieren.classList.remove("getan");
          kopieren.querySelector("use").setAttribute("href", "#i-kopieren");
        }, 1600);
      } catch {
        alert("Kopieren hat nicht geklappt.");
      }
    });

    // Teilen — über das Teilen-Menü des Handys (WhatsApp, SMS, E-Mail …). Das
    // bringt das Betriebssystem mit; wir reichen nur den Text hinein. Kann das
    // Gerät es nicht (z. B. Desktop-Browser), kopieren wir stattdessen.
    const teilen = document.createElement("button");
    teilen.className = "klein-knopf";
    teilen.setAttribute("aria-label", "Antwort teilen");
    teilen.innerHTML = `<svg viewBox="0 0 24 24"><use href="#i-teilen"/></svg>`;
    teilen.addEventListener("click", async () => {
      try {
        if (navigator.share) {
          await navigator.share({ text: block.text });
        } else {
          await navigator.clipboard.writeText(block.text);
          melde("Teilen geht auf diesem Gerät nicht — Text kopiert.");
        }
      } catch (err) {
        // Bricht man das Teilen-Menü ab, ist das kein Fehler.
        if (err?.name !== "AbortError") melde("Teilen hat nicht geklappt.");
      }
    });

    leiste.append(hoeren, kopieren, teilen);
    el.append(text, leiste);
    return el;
  }

  if (block.typ === "werkzeug") {
    el.className = "notiz werkzeug";
    el.textContent = block.text;
    return el;
  }

  // Code: zugeklappt, mit Zeilenzahl. Antippen zeigt ihn.
  el.className = "notiz code";
  const zeile = block.zeilen === 1 ? "Zeile" : "Zeilen";
  el.innerHTML = `<span class="kopfzeile">▸ Code, ${block.zeilen} ${zeile}</span><pre hidden></pre>`;
  el.querySelector("pre").textContent = block.text;
  el.addEventListener("click", () => {
    const pre = el.querySelector("pre");
    pre.hidden = !pre.hidden;
    el.querySelector(".kopfzeile").textContent =
      `${pre.hidden ? "▸" : "▾"} Code, ${block.zeilen} ${zeile}`;
  });
  return el;
}

let zuletztGesehen = "";

// Soll der Verlauf am Ende mitlaufen? Solange du unten stehst — und immer gleich
// nach dem Absenden —, zieht jede neue Antwort nach unten ins Sichtfeld. Scrollst
// du hoch, um Älteres zu lesen, halten wir an und lassen dich in Ruhe. Vorher
// wurde bei jeder Runde neu geraten, und deine erste Antwort blieb unter der
// Kante liegen, halb hinter der Eingabe.
let folgeUnten = true;

// Bis wann die "denkt nach"-Anzeige mindestens stehen bleibt. Direkt nach dem
// Absenden dauert es einen Moment, bis Claude sichtbar zu arbeiten beginnt —
// ohne diesen Puffer flackerte die Anzeige kurz weg und wieder an. So pulsiert
// sie durchgehend, bis die Antwort kommt.
let denktBis = 0;

$("verlauf").addEventListener("scroll", () => {
  const el = $("verlauf");
  folgeUnten = el.scrollHeight - el.scrollTop - el.clientHeight < 120;
});

// Aufeinanderfolgende Claude-Stücke zu EINER Antwort zusammenfassen. Eine
// Antwort mit Werkzeug-Einsatz zerfällt in der Mitschrift in mehrere Text-Stücke
// (Text · Werkzeug · Text …). Die Werkzeug-Stücke fliegen hier ohnehin raus —
// dann gehören die übrigen Text-Stücke zusammen und bekommen EINEN Lautsprecher
// und EINEN Kopieren-Knopf, statt dass man jedes Bruchstück einzeln anhören muss.
function zusammenfassen(bloecke) {
  const raus = [];
  for (const b of bloecke) {
    if (b.typ === "werkzeug") continue;
    const letzter = raus[raus.length - 1];
    if (b.typ === "claude" && letzter && letzter.typ === "claude") {
      // Ans Laufende anhängen — mit Leerzeile, damit Absätze erhalten bleiben.
      letzter.text = `${letzter.text}\n\n${b.text}`;
    } else {
      raus.push({ ...b });     // Kopie: das Original im Zwischenspeicher bleibt unberührt
    }
  }
  return raus;
}

async function ladeVerlauf() {
  if (!aktuelleSitzung || imTerminal) return;

  let bloecke;
  try {
    bloecke = await (await api(`/sessions/${encodeURIComponent(aktuelleSitzung.name)}/verlauf`)).json();
  } catch {
    return;
  }

  // Hat sich überhaupt etwas geändert?
  //
  // Sonst bauen wir den Verlauf alle drei Sekunden neu auf — und reißen dich
  // dabei jedes Mal aus dem Text, den du gerade liest. Genau daran scheiterte
  // das Scrollen: Nicht die Rolle fehlte, sie wurde nur ständig zurückgesetzt.
  const abdruck = JSON.stringify(bloecke);
  if (abdruck === zuletztGesehen) return;
  zuletztGesehen = abdruck;

  const behaelter = $("verlauf");
  // Die Werkzeug-Kästen ("Bash(…)", "Read(…)") gehören ins Terminal, nicht ins
  // Gespräch. Die Lese-Ansicht zeigt, was Claude *sagt* — wer sehen will, was es
  // *tut*, schaltet oben aufs Terminal.
  behaelter.replaceChildren(...zusammenfassen(bloecke).map(verlaufBlock));

  // Ans Ende ziehen, wenn wir mitlaufen sollen — aber erst in der nächsten
  // Bildwiederholung, wenn der neue Inhalt wirklich vermessen ist. Sofort wäre
  // scrollHeight noch der alte Wert, und wir landeten zu kurz.
  if (folgeUnten) {
    requestAnimationFrame(() => { behaelter.scrollTop = behaelter.scrollHeight; });
  }
}

// --- Claudes Rückfragen ------------------------------------------------------
//
// Bevor Claude eine Datei ändert oder einen Befehl ausführt, fragt es um
// Erlaubnis. Im Terminal drückt man eine Zifferntaste. Unterwegs stand die App
// bisher einfach still — sie zeigte "wartet auf dich", aber es gab nichts zum
// Antippen. Man musste die Erlaubnis in der offiziellen App erteilen.

let offeneFrage = "";

async function pruefeFrage() {
  if (!aktuelleSitzung || imTerminal) return;

  let frage;
  try {
    frage = await (await api(
      `/sessions/${encodeURIComponent(aktuelleSitzung.name)}/frage`
    )).json();
  } catch {
    return;
  }

  // Der Anmelde-Link fährt in derselben Antwort huckepack mit (siehe
  // Server). Er hat seinen eigenen Kasten und stört die Rückfragen nicht.
  zeigeAnmeldeLink(frage.anmeldeLink);

  const kasten = $("frage");
  if (!frage.moeglichkeiten) {
    kasten.hidden = true;
    offeneFrage = "";
    return;
  }

  // Dieselbe Frage nicht bei jedem Takt neu bauen — sonst springt ein Knopf
  // unter dem Finger weg, während man ihn drückt.
  const abdruck = JSON.stringify(frage);
  if (abdruck === offeneFrage) return;
  offeneFrage = abdruck;

  $("frage-text").textContent = frage.text;
  $("frage-knoepfe").replaceChildren(
    ...frage.moeglichkeiten.map((m) => {
      const knopf = document.createElement("button");
      // Die erste Antwort ist die zustimmende — sie bekommt das Gewicht.
      knopf.className = m.nummer === 1 ? "frage-knopf ja" : "frage-knopf";
      knopf.textContent = m.text;
      knopf.addEventListener("click", () => antworte(m.nummer));
      return knopf;
    })
  );
  kasten.hidden = false;
}

// Der Anmelde-Kasten: erscheint, wenn Claude Code nach /login seine lange
// OAuth-Adresse auf den Bildschirm gedruckt hat. Öffnen startet die Anmeldung
// im Browser; den Code, den man dort bekommt, setzt man danach ganz normal
// unten ins Eingabefeld. Kopieren als zweiter Weg, falls man den Link lieber
// woanders öffnet.
let anmeldeLink = "";

function zeigeAnmeldeLink(url) {
  const kasten = $("anmelde-link");
  anmeldeLink = url || "";
  kasten.hidden = !anmeldeLink;
}

$("anmelde-oeffnen").addEventListener("click", () => {
  if (anmeldeLink) window.open(anmeldeLink, "_blank", "noopener");
});

$("anmelde-kopieren").addEventListener("click", async () => {
  if (!anmeldeLink) return;
  try {
    await navigator.clipboard.writeText(anmeldeLink);
    melde("Link kopiert.");
  } catch {
    melde("Kopieren ging nicht — nimm den Öffnen-Knopf.");
  }
});

async function antworte(nummer) {
  const kasten = $("frage");
  kasten.hidden = true;
  offeneFrage = "";
  try {
    await api(`/sessions/${encodeURIComponent(aktuelleSitzung.name)}/antwort`, {
      method: "POST",
      body: JSON.stringify({ nummer }),
    });
    setTimeout(ladeVerlauf, 600);
  } catch (err) {
    melde(err.message);
  }
}

// Senden sperren, solange Claude arbeitet: aus dem Pfeil wird ein Stoppschild.
// Nachschieben während des Denkens verwirrte nur ("ist das angekommen?"); wer
// unterbrechen will, nimmt den Anhalten-Knopf.
function sendeSperren(sperr) {
  const knopf = $("knopf-senden");
  knopf.classList.toggle("blockiert", sperr);
  knopf.querySelector("use").setAttribute("href", sperr ? "#i-stopp-schild" : "#i-senden");
  knopf.setAttribute("aria-label", sperr ? "Claude arbeitet — Senden gesperrt" : "Senden");
}

// Der Anhalten-Knopf zeigt sich nur, während Claude wirklich arbeitet.
//
// Nebenbei erkennt diese Runde den Übergang von "arbeitet" zu "ruht" — den
// Moment, in dem Claude fertig geworden ist. Der Freisprech-Modus hängt daran:
// Genau dann liest die App die Antwort von selbst vor.
async function pruefeObClaudeArbeitet() {
  if (!aktuelleSitzung) return;
  try {
    const sitzungen = await (await api("/sessions")).json();
    const jetzt = sitzungen.find((s) => s.name === aktuelleSitzung.name);
    const arbeitet = jetzt?.state === "running";

    // Solange Claude arbeitet, den Puffer immer wieder nachladen. So bleibt
    // "beschäftigt" DURCHGEHEND wahr — auch über die kurzen Atempausen zwischen
    // zwei Schritten hinweg, in denen der Zustand kurz auf "ruht" fällt. Ohne
    // das flackerte die Anzeige und der Freisprech-Vortrag löste zu früh aus.
    if (arbeitet) denktBis = Date.now() + 3500;
    beschaeftigt = Date.now() < denktBis;

    // Der Anhalten-Knopf folgt dem echten Zustand — anhalten kann man nur, was
    // wirklich läuft. Sperre und Anzeige folgen dem geglätteten "beschäftigt".
    $("knopf-abbrechen-arbeit").hidden = !arbeitet;
    sendeSperren(beschaeftigt);
    $("denkt").hidden = !beschaeftigt;
    zeigeSitzungInfo(jetzt);
    zeigeModus(jetzt?.modus);

    // Wirklich fertig = war beschäftigt, ist es jetzt (nach dem Puffer) nicht
    // mehr — nicht schon bei einer kurzen Pause zwischendurch.
    if (warBeschaeftigt && !beschaeftigt) {
      if (freisprech && !imTerminal) {
        freisprechVorlesen();
      }
    }
    warBeschaeftigt = beschaeftigt;
  } catch {
    // dann eben nicht
  }
}

$("knopf-abbrechen-arbeit").addEventListener("click", async () => {
  if (!aktuelleSitzung) return;
  try {
    await api(`/sessions/${encodeURIComponent(aktuelleSitzung.name)}/abbrechen`, {
      method: "POST",
    });
    $("knopf-abbrechen-arbeit").hidden = true;
    setTimeout(ladeVerlauf, 600);
  } catch (err) {
    alert(err.message);
  }
});

function ansichtWechseln() {
  imTerminal = !imTerminal;

  $("verlauf").hidden = imTerminal;
  $("terminal").hidden = !imTerminal;
  $("sondertasten").hidden = !imTerminal;
  // Die Schnellbefehle gehören zur Lese-Ansicht — im Terminal tippt man direkt.
  $("schnellbefehle").hidden = imTerminal;
  if (imTerminal) $("denkt").hidden = true;
  // Der Knopf zeigt, wohin er führt — nicht, wo man ist.
  $("knopf-ansicht").querySelector("use")
    .setAttribute("href", imTerminal ? "#i-lesen" : "#i-terminal");

  if (imTerminal) {
    clearInterval(verlaufTakt);
    verlaufTakt = null;
    baueTerminal();
    fit.fit();
    verbinde(aktuelleSitzung.name);
  } else {
    steckdose?.close();
    steckdose = null;
    ladeVerlauf();
    clearInterval(verlaufTakt);
    verlaufTakt = setInterval(ladeVerlauf, 3000);
  }
}

$("knopf-ansicht").addEventListener("click", ansichtWechseln);

function baueTerminal() {
  if (term) return;

  term = new Terminal({
    fontFamily: "ui-monospace, 'SF Mono', Menlo, Consolas, monospace",
    fontSize: 12,
    lineHeight: 1.25,
    cursorBlink: true,
    convertEol: true,
    theme: {
      background: "#16130F",
      foreground: "#F0EAE2",
      cursor: "#D9764F",
      selectionBackground: "#3A2419",
    },
  });
  fit = new FitAddon.FitAddon();
  term.loadAddon(fit);
  term.open($("terminal"));
  term.onData((daten) => steckdose?.send(daten));
  baueSondertasten();
}

function oeffneSitzung(sitzung) {
  stoppeListe();
  aktuelleSitzung = sitzung;
  // Anhänge gehören zu der Sitzung, aus der sie hochgeladen wurden — beim
  // Wechsel weg damit, sonst schickte man das Foto ins falsche Projekt.
  anhaengeLeeren();

  $("sitzung-name").textContent = benannt(sitzung);
  $("knopf-anheften").classList.toggle("an", sitzung.pinned);
  $("knopf-melden").classList.toggle("an", sitzung.notifyWhenDone);
  freisprechAnzeigen();
  // Erst die Liste holen, dann den Namen zeigen — sonst stünde beim ersten
  // Öffnen "Modell wählen", obwohl längst eines gesetzt ist.
  modelleHolen().then(() => {
    zeigeModell(sitzung.modell, sitzung.modellAufgeloest);
    zeigeSitzungInfo(null);
  });
  zeigeModus(sitzung.modus);
  zeige("sitzung");

  // Zum Lesen aufmachen, nicht ins Terminal. Das ist der Normalfall.
  imTerminal = false;
  $("verlauf").hidden = false;
  $("terminal").hidden = true;
  $("sondertasten").hidden = true;
  $("schnellbefehle").hidden = false;
  $("knopf-ansicht").querySelector("use").setAttribute("href", "#i-terminal");

  $("verlauf").replaceChildren();
  $("frage").hidden = true;
  zeigeAnmeldeLink(null);
  offeneFrage = "";
  zuletztGesehen = "";     // neue Sitzung, alles frisch
  folgeUnten = true;       // beim Öffnen ans Ende, zum Neuesten
  beschaeftigt = false;    // Freisprech soll nicht sofort beim Öffnen auslösen
  warBeschaeftigt = false;
  zuletztVorgelesen = "";  // neue Sitzung: die erste Antwort darf vorgelesen werden
  denktBis = 0;
  $("denkt").hidden = true;
  sendeSperren(false);
  ladeVerlauf();
  pruefeFrage();
  clearInterval(verlaufTakt);
  verlaufTakt = setInterval(() => {
    ladeVerlauf();
    pruefeObClaudeArbeitet();
    pruefeFrage();
    pruefeObTonZurueck();
  }, 3000);
}

function verbinde(name) {
  steckdose?.close();

  const protokoll = location.protocol === "https:" ? "wss:" : "ws:";
  const { cols, rows } = term;
  steckdose = new WebSocket(
    `${protokoll}//${location.host}/ws/${encodeURIComponent(name)}?cols=${cols}&rows=${rows}`
  );
  steckdose.binaryType = "arraybuffer";

  steckdose.addEventListener("open", () => setzeVerbindung(true));
  steckdose.addEventListener("message", (e) => {
    term.write(new Uint8Array(e.data));
  });
  steckdose.addEventListener("close", () => {
    setzeVerbindung(false);
    // Verbindung weg — auf dem Handy passiert das ständig, sobald der
    // Bildschirm ausgeht. Die Sitzung läuft weiter, wir hängen uns nur
    // wieder dran. ABER nur, solange wir wirklich im Terminal sind: In der
    // Leseansicht (imTerminal = false) hat der Wechsel die Verbindung bewusst
    // geschlossen — ohne diese Prüfung verbände sie sich sofort heimlich wieder
    // und ein unsichtbarer Terminal-Strom liefe samt Akku- und Datenverbrauch
    // weiter.
    if (imTerminal && aktuelleSitzung?.name === name && !$("ansicht-sitzung").hidden) {
      setTimeout(() => verbinde(name), 1500);
    }
  });
}

function setzeVerbindung(verbunden) {
  const anzeige = $("verbindung");
  anzeige.classList.toggle("weg", !verbunden);
  anzeige.lastChild.textContent = verbunden ? "verbunden" : "getrennt";
}

// Datum und Uhrzeit dieses Geräts, kurz gehalten — z. B. "18.07. 01:26".
// Claude Code hat keine eigene Uhr: Eine Sitzung läuft tagelang, und ohne
// diesen Hinweis weiß Claude bei "heute Abend" oder "in zwei Stunden" nicht,
// wann jetzt ist. Bewusst ohne Wochentag und Jahr — kurz im Verlauf, für Claude
// trotzdem eindeutig. Wir nehmen die Zeit des Handys, nicht die des Servers —
// der steht womöglich in einer anderen Zeitzone.
function jetztStempel() {
  const jetzt = new Date();
  const datum = jetzt.toLocaleDateString("de-DE", { day: "2-digit", month: "2-digit" });
  const zeit = jetzt.toLocaleTimeString("de-DE", { hour: "2-digit", minute: "2-digit" });
  return `${datum} ${zeit}`;
}

// Text an die Sitzung schicken — von der Eingabezeile oder aus dem Verlauf.
// In der Lese-Ansicht gibt es keine offene Verbindung; der Text geht über den
// Server hinein und erscheint gleich als deine Blase im Verlauf.
async function sendeInSitzung(text) {
  if (!text || !aktuelleSitzung) return;

  if (imTerminal) {
    // Im rohen Terminal NICHT die Zeit voranstellen — dort tippst du Befehle,
    // und ein Zeitstempel davor wäre Unsinn.
    steckdose?.send(text + "\r");
    return;
  }

  // Anmelde-Codes (nach /login) müssen UNVERÄNDERT ankommen — der Zeitstempel
  // davor machte den Code ungültig und die Anmeldung schlug immer fehl. Ein
  // Code ist leicht zu erkennen: ein langes Zeichenpaket ohne Leerzeichen,
  // wie es kein Mensch als Nachricht diktiert.
  const istCode = /^[A-Za-z0-9_#.-]{25,}$/.test(text);
  await api(`/sessions/${encodeURIComponent(aktuelleSitzung.name)}/senden`, {
    method: "POST",
    // Die Uhrzeit still vorangestellt, damit Claude immer weiß, wann jetzt ist.
    body: JSON.stringify({ text: istCode ? text : `[${jetztStempel()}] ${text}` }),
  });
  // Du hast gerade abgeschickt — jetzt willst du die Antwort sehen. Also wieder
  // ans Ende mitlaufen, egal wo du vorher standest.
  folgeUnten = true;
  // Sofort Rückmeldung: angekommen, und es arbeitet — kein stummer Stillstand
  // mehr, bis die Antwort kommt.
  melde("Gesendet — Claude denkt nach …");
  // Sofort auf "beschäftigt" schalten — mit großzügigem Puffer, bis die Arbeit
  // sichtbar anläuft. So sperrt der Senden-Knopf ohne Verzögerung und die
  // Anzeige steht von der ersten Sekunde an.
  denktBis = Date.now() + 6000;
  beschaeftigt = true;
  warBeschaeftigt = true;
  $("denkt").hidden = false;
  sendeSperren(true);
  setTimeout(ladeVerlauf, 600);
}

// Eingabezeile: bequemer als direkt ins Terminal zu tippen, weil die
// Handytastatur so ihre Autokorrektur und das Diktieren anbieten kann.
$("eingabe-formular").addEventListener("submit", async (e) => {
  e.preventDefault();
  const feld = $("eingabe");
  const text = feld.value.trim();
  const pfade = anhaenge.map((a) => a.pfad);
  // Ein bloßer Anhang ohne ein Wort dazu darf raus — dann schaut Claude ihn
  // sich eben ohne weitere Anweisung an.
  if ((!text && !pfade.length) || !aktuelleSitzung) return;

  // Solange Claude arbeitet, nehmen wir nichts Neues an — das Nachschieben
  // führte nur zu "ist das angekommen?"-Verwirrung. Text und Anhänge bleiben
  // stehen, du kannst abschicken, sobald das Stoppschild wieder zum Pfeil wird.
  if (!imTerminal && beschaeftigt) {
    melde("Claude arbeitet noch — gleich wieder frei. Zum Unterbrechen den Anhalten-Knopf.");
    return;
  }

  // Erst das Mikrofon zum Schweigen bringen.
  //
  // Sonst hört es weiter zu, hält seinen bisherigen Satz noch fest und
  // schreibt ihn gleich wieder ins Feld — man löscht ihn und er kommt zurück.
  hoertStoppen?.();

  // Die Anhang-Pfade zuerst, der Text dahinter — genau so, wie man es am
  // Rechner eintippte. Feld und Streifen sofort leeren; klemmt das Senden,
  // stellen wir beides wieder her.
  const gesamt = [...pfade, text].filter(Boolean).join(" ");
  const gemerkt = anhaenge;
  feld.value = "";
  anhaengeLeeren();

  try {
    await sendeInSitzung(gesamt);
  } catch (err) {
    feld.value = text;      // nichts verloren
    anhaenge = gemerkt;     // auch die Anhänge zurück
    anhangStreifenZeichnen();
    beschaeftigt = false;   // ging nicht raus — nicht fälschlich sperren
    sendeSperren(false);
    alert(err.message);
  }
});

// --- Schnellbefehle ----------------------------------------------------------
//
// Ein Tipp schickt einen fertigen Satz an Claude — genau denselben Weg wie die
// Eingabezeile. Solange Claude arbeitet, wird auch hier abgewiesen statt
// nachgeschoben (wie beim Stoppschild an der Eingabe).
async function schnellbefehl(text) {
  if (!aktuelleSitzung || imTerminal || !text) return;

  if (beschaeftigt) {
    melde("Claude arbeitet noch — gleich wieder frei.");
    return;
  }
  hoertStoppen?.();

  // Hängen Fotos oder Dateien am Feld, gehen sie mit — genau wie beim Senden
  // über die Eingabezeile. Sonst tippt man "Los geht's" und die eben angehängten
  // Bilder bleiben unbemerkt liegen. Pfade zuerst, der Befehlssatz dahinter.
  const pfade = anhaenge.map((a) => a.pfad);
  const gesamt = [...pfade, text].filter(Boolean).join(" ");
  const gemerkt = anhaenge;
  anhaengeLeeren();

  try {
    await sendeInSitzung(gesamt);
  } catch (err) {
    anhaenge = gemerkt;          // ging nicht raus — Anhänge zurück
    anhangStreifenZeichnen();
    beschaeftigt = false;
    sendeSperren(false);
    melde(err.message);
  }
}

function befehlsmenue(auf) {
  const wrap = $("schnellbefehle").querySelector(".befehle-wand-wrap");
  $("befehle-mehr").hidden = !auf;
  wrap.classList.toggle("offen", auf);
}

$("schnellbefehle").addEventListener("click", (e) => {
  // War das gerade ein langer Druck? Dann wurde der Satz schon ins Feld gelegt —
  // den nachklappernden Klick nicht auch noch als Senden werten.
  if (langerDruckAus) { langerDruckAus = false; return; }

  // Der Zauberstab klappt das Menü nach oben auf oder wieder zu.
  if (e.target.closest("#knopf-mehr-befehle")) {
    befehlsmenue($("befehle-mehr").hidden);
    return;
  }
  // Der "Eigene Befehle"-Knopf öffnet das Verwalten-Blatt — vor der Sende-
  // Prüfung, denn er trägt selbst die chip-menu-Klasse und würde sonst senden.
  if (e.target.closest("#knopf-befehle-verwalten")) {
    befehleBlattAuf();
    befehlsmenue(false);
    return;
  }
  // Ein Menüpunkt sendet und schließt gleich wieder.
  const menuBefehl = e.target.closest(".chip-menu");
  if (menuBefehl) {
    schnellbefehl(menuBefehl.dataset.text);
    befehlsmenue(false);
    return;
  }
  const chip = e.target.closest(".chip");
  if (chip) schnellbefehl(chip.dataset.text);
});

// Tippt man neben das Menü, klappt es zu.
document.addEventListener("click", (e) => {
  if (!e.target.closest(".befehle-wand-wrap")) befehlsmenue(false);
});

// --- Langer Druck auf einen Schnellbefehl: erst ins Feld statt sofort senden ---
//
// Kurzer Tipp sendet wie gewohnt (der schnelle Weg). Hältst du einen Befehl
// dagegen einen Moment, wandert sein Satz ins Textfeld — dann kannst du noch
// etwas anhängen und selbst senden. Ein Wischen (die Chip-Reihe ist scrollbar)
// soll das nicht auslösen, darum bricht eine größere Fingerbewegung ab.
let druckZeit = null;         // Timer, der den langen Druck erkennt
let druckStart = null;        // wo der Finger aufsetzte — für die Wisch-Schwelle
let langerDruckAus = false;   // löste gerade ein langer Druck aus? (Klick unterdrücken)

function chipInsFeld(text) {
  const feld = $("eingabe");
  const vorher = feld.value.trim();
  feld.value = (vorher ? vorher + " " : "") + text;
  feldAnpassen();
  feld.focus();
  const ende = feld.value.length;
  try { feld.setSelectionRange(ende, ende); } catch { /* manche Felder mögen das nicht */ }
  try { navigator.vibrate?.(15); } catch { /* Handy ohne Vibration */ }
  melde("In die Eingabe gelegt — ergänze noch etwas und sende selbst.");
}

function druckAbbrechen() {
  if (druckZeit) { clearTimeout(druckZeit); druckZeit = null; }
  druckStart = null;
}

$("schnellbefehle").addEventListener("pointerdown", (e) => {
  langerDruckAus = false;                    // jeder neue Druck fängt sauber an
  const chip = e.target.closest(".chip, .chip-menu");
  // Nur echte Befehls-Chips — nicht der „Eigene Befehle"-Knopf (trägt zwar
  // chip-menu, aber keinen data-text).
  if (!chip || chip.id === "knopf-befehle-verwalten" || !chip.dataset.text) return;

  druckStart = { x: e.clientX, y: e.clientY };
  druckZeit = setTimeout(() => {
    langerDruckAus = true;
    chipInsFeld(chip.dataset.text);
    if (chip.classList.contains("chip-menu")) befehlsmenue(false);
    druckZeit = null;
  }, 500);
});

$("schnellbefehle").addEventListener("pointermove", (e) => {
  // Erst eine deutliche Bewegung (Wischen/Scrollen) bricht ab — kleines Zittern
  // beim Halten nicht.
  if (!druckStart) return;
  if (Math.abs(e.clientX - druckStart.x) > 10 || Math.abs(e.clientY - druckStart.y) > 10) {
    druckAbbrechen();
  }
});

$("schnellbefehle").addEventListener("pointerup", druckAbbrechen);
$("schnellbefehle").addEventListener("pointercancel", druckAbbrechen);

// --- Eigene Schnellbefehle ---------------------------------------------------
//
// Zu den fest eingebauten Sätzen darfst du dir eigene anlegen: ein Name auf dem
// Knopf, ein fertiger Satz dahinter. Sie liegen im Gerätespeicher — also auf
// diesem Gerät, nicht in der Wolke; ein zweites Handy sähe sie (noch) nicht.
const BEFEHLE_SPEICHER = "eigene-schnellbefehle";
// Merker, dass die Erstbefüllung mit den Standard-Sätzen schon lief. Ohne den
// würde ein gelöschter Standard bei jedem Laden wiederkommen.
const BEFEHLE_INIT = "eigene-schnellbefehle-init";

// Die früher fest verdrahteten Sätze — jetzt nur noch die STARTausstattung. Beim
// allerersten Laden landen sie im Gerätespeicher und sind ab dann ganz normale,
// änder- und löschbare Befehle. Die ersten drei stehen in der sichtbaren Leiste.
const STANDARD_BEFEHLE = [
  { label: "Los geht's",     text: "Ja, super — leg los.",             leiste: true  },
  { label: "Weiter",         text: "Mach bitte weiter.",               leiste: true  },
  { label: "Zusammenfassen", text: "Fass mir das bitte kurz zusammen.", leiste: true  },
  { label: "Kürzer",         text: "Fass dich bitte kürzer.",          leiste: false },
  { label: "Einfacher",      text: "Erklär's mir bitte einfacher.",    leiste: false },
];

// Welcher Befehl gerade bearbeitet wird (sein Index) — oder null beim Neuanlegen.
let befehlBearbeitung = null;

// Die Befehle im Arbeitsspeicher — die Quelle der Wahrheit. Der Gerätespeicher
// ist nur die Sicherung nach außen; klappt die nicht (strenger Privatmodus),
// gelten die Befehle wenigstens für diese Sitzung, statt ganz zu verschwinden.
let eigeneBefehle = null;

function eigeneBefehleLesen() {
  if (eigeneBefehle) return eigeneBefehle;

  let gespeichert = null;
  try { gespeichert = JSON.parse(localStorage.getItem(BEFEHLE_SPEICHER)); } catch { /* kein Speicher */ }
  gespeichert = Array.isArray(gespeichert) ? gespeichert : null;

  let schonBefuellt = null;
  try { schonBefuellt = localStorage.getItem(BEFEHLE_INIT); } catch { /* kein Speicher */ }

  if (schonBefuellt) {
    // Schon umgestellt: nehmen, was da ist (auch eine leere Liste — dann hat man
    // bewusst alles gelöscht, und nichts kommt ungefragt zurück).
    eigeneBefehle = gespeichert || [];
  } else {
    // Erstmalige Umstellung: die Standard-Sätze VOR die evtl. schon vorhandenen
    // eigenen stellen, dann als erledigt merken.
    eigeneBefehle = [...STANDARD_BEFEHLE, ...(gespeichert || [])];
    eigeneBefehleSchreiben(eigeneBefehle);
    try { localStorage.setItem(BEFEHLE_INIT, "1"); } catch { /* dann eben diese Sitzung */ }
  }
  return eigeneBefehle;
}

function eigeneBefehleSchreiben(liste) {
  eigeneBefehle = liste;      // immer im Arbeitsspeicher halten
  try { localStorage.setItem(BEFEHLE_SPEICHER, JSON.stringify(liste)); }
  catch { /* nicht merkbar — dann gelten sie eben nur für diese Sitzung */ }
}

// Die eigenen Befehle als Chips: die mit "leiste" in die sichtbare Reihe neben
// den festen dreien, alle anderen ins Zauberstab-Menü.
function eigeneBefehleZeichnen() {
  const menu = $("eigene-befehle");
  const reihe = $("chip-reihe-eigene");
  menu.textContent = "";
  reihe.textContent = "";
  for (const b of eigeneBefehleLesen()) {
    const chip = document.createElement("button");
    chip.type = "button";
    chip.dataset.text = b.text;      // dataset ist sicher — landet nie als HTML
    chip.textContent = b.label;      // textContent, denn der Name kommt von dir
    if (b.leiste) {
      chip.className = "chip";        // sichtbare Leiste — sendet über denselben Klick-Weg
      reihe.appendChild(chip);
    } else {
      chip.className = "chip-menu";   // hinterm Zauberstab
      menu.appendChild(chip);
    }
  }
}

// Die Liste im Verwalten-Blatt — jede Zeile mit einem Kreuz zum Löschen.
function befehleListeZeichnen() {
  const liste = $("befehle-liste");
  liste.textContent = "";
  const befehle = eigeneBefehleLesen();
  if (!befehle.length) {
    const leer = document.createElement("p");
    leer.className = "hinweis";
    leer.textContent = "Noch keine eigenen Befehle.";
    liste.appendChild(leer);
    return;
  }
  befehle.forEach((b, i) => {
    const zeile = document.createElement("div");
    zeile.className = "befehl-zeile" + (i === befehlBearbeitung ? " wird-bearbeitet" : "");

    // Ein Tipp auf den Text lädt den Befehl ins Formular zum Ändern.
    const text = document.createElement("button");
    text.type = "button";
    text.className = "befehl-text";
    text.setAttribute("aria-label", "Befehl bearbeiten");
    const name = document.createElement("strong");
    name.textContent = b.label;
    const satz = document.createElement("span");
    satz.textContent = b.text;
    text.append(name, satz);
    text.addEventListener("click", () => befehlBearbeiten(i));

    // Ein sichtbarer Stift-Knopf — damit man das Ändern nicht erraten muss (der
    // Tipp auf den Namen tut dasselbe, war aber unsichtbar).
    const stift = document.createElement("button");
    stift.type = "button";
    stift.className = "befehl-stift";
    stift.setAttribute("aria-label", "Befehl ändern");
    stift.innerHTML = '<svg viewBox="0 0 24 24"><use href="#i-stift"/></svg>';
    stift.addEventListener("click", () => befehlBearbeiten(i));

    const weg = document.createElement("button");
    weg.type = "button";
    weg.className = "befehl-weg";
    weg.setAttribute("aria-label", "Befehl löschen");
    weg.textContent = "✕";
    weg.addEventListener("click", () => {
      const rest = eigeneBefehleLesen();
      rest.splice(i, 1);
      eigeneBefehleSchreiben(rest);
      befehlFormZuruecksetzen();     // ein evtl. laufendes Bearbeiten passt nach dem Löschen nicht mehr
      befehleListeZeichnen();
      eigeneBefehleZeichnen();
    });

    // Umschalter: steht der Befehl in der sichtbaren Leiste oder nur im Menü?
    const leiste = document.createElement("button");
    leiste.type = "button";
    leiste.className = "befehl-leiste" + (b.leiste ? " an" : "");
    leiste.setAttribute("aria-label", b.leiste ? "Aus der Leiste nehmen" : "In die Leiste stellen");
    leiste.textContent = "Leiste";
    leiste.addEventListener("click", () => befehlLeisteUmschalten(i));

    zeile.append(text, stift, leiste, weg);
    liste.appendChild(zeile);
  });
}

// Einen Befehl in die sichtbare Leiste stellen oder wieder ins Menü nehmen.
function befehlLeisteUmschalten(i) {
  const befehle = eigeneBefehleLesen();
  if (!befehle[i]) return;
  befehle[i].leiste = !befehle[i].leiste;
  eigeneBefehleSchreiben(befehle);
  befehleListeZeichnen();
  eigeneBefehleZeichnen();
}

// Formular leeren und zurück in den Neuanlegen-Zustand (Knopf: „Hinzufügen").
function befehlFormZuruecksetzen() {
  befehlBearbeitung = null;
  $("befehl-label").value = "";
  $("befehl-text").value = "";
  $("befehl-hinzufuegen").textContent = "Hinzufügen";
}

// Einen bestehenden Befehl zum Ändern ins Formular holen.
function befehlBearbeiten(i) {
  const b = eigeneBefehleLesen()[i];
  if (!b) return;
  befehlBearbeitung = i;
  $("befehl-label").value = b.label;
  $("befehl-text").value = b.text;
  $("befehl-hinzufuegen").textContent = "Speichern";
  befehleListeZeichnen();       // hebt die Zeile hervor, die gerade dran ist
  $("befehl-label").focus();
}

function befehleBlattAuf() {
  befehlFormZuruecksetzen();
  befehleListeZeichnen();
  $("befehle-blatt").hidden = false;
}
function befehleBlattZu() { $("befehle-blatt").hidden = true; }

$("befehle-schatten").addEventListener("click", befehleBlattZu);
$("befehle-schliessen").addEventListener("click", befehleBlattZu);

$("befehl-hinzufuegen").addEventListener("click", () => {
  const label = $("befehl-label").value.trim();
  const text = $("befehl-text").value.trim();
  if (!label || !text) {
    melde("Bitte einen Namen und den Satz eintragen.");
    return;
  }
  const befehle = eigeneBefehleLesen();
  if (befehlBearbeitung !== null && befehle[befehlBearbeitung]) {
    // Ändern — die Leiste-Wahl des Befehls erhalten, nicht überschreiben.
    befehle[befehlBearbeitung] = { label, text, leiste: befehle[befehlBearbeitung].leiste };
    eigeneBefehleSchreiben(befehle);
    befehlFormZuruecksetzen();
    befehleListeZeichnen();
    eigeneBefehleZeichnen();
    melde("Befehl geändert.");
  } else {
    befehle.push({ label, text, leiste: false });   // neuer Befehl startet im Menü
    eigeneBefehleSchreiben(befehle);
    befehlFormZuruecksetzen();
    befehleListeZeichnen();
    eigeneBefehleZeichnen();
    melde("Befehl angelegt.");
  }
});

// Beim Start die gespeicherten Befehle ins Menü holen.
eigeneBefehleZeichnen();

// --- Ein Foto an Claude ------------------------------------------------------
//
// Claude Code kann Bilder von der Festplatte lesen. Also legt der Server das
// Foto dort ab und wir reichen den Pfad in die Sitzung — genau so, wie man ihn
// am Rechner selbst eintippen würde. Ein Screenshot erklärt oft mehr als drei
// Absätze, und unterwegs ist ein Foto schneller als jede Beschreibung.

// Die Anhänge, die beim nächsten Senden mitgehen. Früher stand ihr Pfad roh
// im Eingabefeld — eine kryptische Zeile, die man aus Versehen zerpflückte.
// Jetzt liegen sie hier und stehen als kleine Vorschau über dem Feld; der Pfad
// wird erst beim Absenden vorangestellt.
let anhaenge = [];

function anhangStreifenZeichnen() {
  const streifen = $("anhang-streifen");
  streifen.textContent = "";
  streifen.hidden = anhaenge.length === 0;

  anhaenge.forEach((a) => {
    const chip = document.createElement("div");
    chip.className = a.istBild ? "anhang-chip" : "anhang-chip datei";

    if (a.istBild) {
      const bild = document.createElement("img");
      bild.src = a.url;
      bild.alt = "Angehängtes Foto";
      chip.appendChild(bild);
    } else {
      // Dokumente haben kein Vorschaubild — Symbol und Name müssen reichen.
      chip.insertAdjacentHTML("beforeend",
        '<svg viewBox="0 0 24 24"><use href="#i-datei"/></svg>');
      const name = document.createElement("span");
      name.textContent = a.name;               // textContent, nie innerHTML: der Name kommt vom Gerät
      chip.appendChild(name);
    }

    const weg = document.createElement("button");
    weg.type = "button";
    weg.className = "anhang-weg";
    weg.setAttribute("aria-label", "Anhang wegnehmen");
    weg.insertAdjacentHTML("beforeend",
      '<svg viewBox="0 0 24 24"><use href="#i-kreuz"/></svg>');
    weg.addEventListener("click", () => {
      anhaenge = anhaenge.filter((x) => x !== a);
      anhangStreifenZeichnen();
    });
    chip.appendChild(weg);

    streifen.appendChild(chip);
  });
}

function anhaengeLeeren() {
  anhaenge = [];
  anhangStreifenZeichnen();
}

// Mehrere Anhänge auf einmal hochladen — Fotos wie Dokumente. Jeder Anhang geht
// einzeln an den Server, der die Datei im Projektordner ablegt und den kurzen
// Pfad zurückgibt. Statt in den Text wandert jeder in den Vorschau-Streifen;
// abgeschickt wird erst, wenn du auf Senden tippst — so kannst du noch etwas
// dazuschreiben.
async function anhaengeHochladen(dateien, endpunkt, feldname, knopf) {
  dateien = [...dateien];
  if (!dateien.length || !aktuelleSitzung) return;

  const istBild = endpunkt === "bild";
  knopf.classList.add("laedt");
  try {
    for (const datei of dateien) {
      const paket = new FormData();
      // Kein Content-Type setzen: Der Browser muss die Grenzmarke selbst
      // eintragen, sonst kommt das Paket zerrissen an.
      paket.append(feldname, datei);
      const antwort = await fetch(
        `/api/sessions/${encodeURIComponent(aktuelleSitzung.name)}/${endpunkt}`,
        { method: "POST", body: paket }
      );
      if (!antwort.ok) {
        const koerper = await antwort.json().catch(() => ({}));
        throw new Error(koerper.detail || "Der Anhang kam nicht an.");
      }
      const { pfad } = await antwort.json();
      const dateiname = pfad.split("/").pop();
      anhaenge.push({
        pfad,
        istBild,
        // Für die Kachel der schöne Name vom Gerät, sonst der vom Server.
        name: datei.name || dateiname,
        // Nur Fotos haben eine Vorschau — über denselben Weg, über den auch der
        // Verlauf ein geschicktes Foto wieder anzeigt.
        url: istBild
          ? `/api/bilder/${encodeURIComponent(aktuelleSitzung.name)}/${encodeURIComponent(dateiname)}`
          : "",
      });
    }
    anhangStreifenZeichnen();
    $("eingabe").focus();
    melde(anhaenge.length === 1
      ? "Angehängt — schreib etwas dazu und sende ab."
      : `${anhaenge.length} Anhänge — schreib etwas dazu und sende ab.`);
  } catch (err) {
    alert(err.message);
  } finally {
    knopf.classList.remove("laedt");
  }
}

// Das Anhängen-Blatt. Der Fortschritt beim Hochladen zeigt sich am Plus-Knopf —
// die einzelnen Symbole gibt es ja nicht mehr, sie stecken jetzt hier drin.
function anhangBlattAuf() { $("anhang-blatt").hidden = false; }
function anhangBlattZu() { $("anhang-blatt").hidden = true; }

$("knopf-anhang").addEventListener("click", anhangBlattAuf);
$("anhang-schatten").addEventListener("click", anhangBlattZu);
$("anhang-schliessen").addEventListener("click", anhangBlattZu);

// Erst das Blatt schließen, dann den Wähler öffnen: Sonst liegt das Blatt beim
// Zurückkommen aus der Kamera noch über der Eingabe.
function ausBlatt(waehler) {
  return () => { anhangBlattZu(); $(waehler).click(); };
}

// Die Kamera direkt: capture="environment" am Wähler öffnet sofort die
// Kamera-App statt der Galerie — Foto knipsen, hängt dran, fertig. Der
// Galerie-Weg daneben bleibt für Screenshots und alte Bilder.
$("kachel-kamera").addEventListener("click", ausBlatt("kamera-waehler"));
$("kamera-waehler").addEventListener("change", (e) => {
  const dateien = [...e.target.files];
  e.target.value = "";
  anhaengeHochladen(dateien, "bild", "bild", $("knopf-anhang"));
});

$("kachel-bild").addEventListener("click", ausBlatt("bild-waehler"));
$("bild-waehler").addEventListener("change", (e) => {
  // ERST die Auswahl in ein eigenes Array kopieren, DANN das Feld leeren.
  // e.target.files ist eine lebende Liste — leert man das Feld vorher, ist die
  // gerade gewählte Datei weg, bevor sie hochlädt. Genau daran scheiterte das
  // Foto-Senden: auswählen ging, absenden nicht.
  const dateien = [...e.target.files];
  e.target.value = "";                 // damit dieselbe Auswahl nochmal ginge
  anhaengeHochladen(dateien, "bild", "bild", $("knopf-anhang"));
});

$("kachel-datei").addEventListener("click", ausBlatt("datei-waehler"));
$("datei-waehler").addEventListener("change", (e) => {
  const dateien = [...e.target.files];
  e.target.value = "";
  anhaengeHochladen(dateien, "datei", "datei", $("knopf-anhang"));
});

// Einfügen aus der Zwischenablage: Am Rechner kopiert man einen Screenshot
// (Snipping Tool, Druck-Taste) und will ihn mit Strg+V direkt anhängen — ohne
// den Umweg, erst eine Datei zu speichern und nachher wieder zu löschen.
// Der Lauscher sitzt am ganzen Dokument, nicht am Eingabefeld: Es soll egal
// sein, wo der Fokus gerade steht. Text-Einfügen bleibt unberührt — nur wenn
// wirklich ein Bild in der Zwischenablage liegt, greifen wir ein.
document.addEventListener("paste", (e) => {
  const bilder = [...(e.clipboardData?.items || [])]
    .filter((eintrag) => eintrag.kind === "file" && eintrag.type.startsWith("image/"))
    .map((eintrag) => eintrag.getAsFile())
    .filter(Boolean);
  if (!bilder.length) return;
  e.preventDefault();
  if (!aktuelleSitzung) {
    melde("Erst eine Sitzung öffnen — dann landet das Bild dort.");
    return;
  }
  anhaengeHochladen(bilder, "bild", "bild", $("knopf-anhang"));
});

// --- Das Eingabefeld wächst mit ----------------------------------------------
//
// Beim Diktieren lief der Text nach rechts aus dem Feld — man sprach ins Leere
// und wusste nicht, ob überhaupt etwas ankommt. Jetzt wächst das Feld, solange
// man spricht, und man sieht seinen Satz entstehen.

const eingabeFeld = $("eingabe");

function feldAnpassen() {
  eingabeFeld.style.height = "auto";
  // Bis zu einer Höhe, ab der es selbst scrollt — sonst frisst ein langer
  // Monolog den halben Bildschirm. Wie hoch, steht im Stil und hängt vom Gerät
  // ab (am Rechner mehr als am Handy); von dort geholt, statt die Zahl hier ein
  // zweites Mal festzuschreiben und beim nächsten Mal zu vergessen.
  const grenze = parseFloat(getComputedStyle(eingabeFeld).maxHeight) || 160;
  eingabeFeld.style.height = Math.min(eingabeFeld.scrollHeight, grenze) + "px";
}

eingabeFeld.addEventListener("input", feldAnpassen);

// Enter schickt ab; Umschalt+Enter macht einen Absatz.
eingabeFeld.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    $("eingabe-formular").requestSubmit();
  }
});

// --- Diktieren ---------------------------------------------------------------
//
// Im Auto ist Tippen keine Option. Ein Druck auf das Mikrofon, sprechen, und
// der Text steht im Feld — abgeschickt wird erst, wenn du es willst, damit ein
// Verhörer nicht sofort bei Claude landet.

const Spracherkennung = window.SpeechRecognition || window.webkitSpeechRecognition;
let hoert = null;
let hoertStoppen = null;    // beendet das Zuhören — von überall her aufrufbar
let hoertVerwerfen = null;  // beendet es und wirft das Diktierte weg

$("knopf-diktat").addEventListener("click", () => {
  const knopf = $("knopf-diktat");
  const feld = $("eingabe");

  if (!Spracherkennung) {
    alert("Dieser Browser kann nicht zuhören. Nimm das Mikrofon auf der Tastatur.");
    return;
  }

  // Nochmal tippen heißt: aufhören.
  if (hoert) {
    hoertStoppen?.();
    return;
  }

  // Was schon im Feld stand, bleibt stehen; das Diktat kommt dahinter.
  const vorher = feld.value ? feld.value.trimEnd() + " " : "";
  let fertig = "";        // die abgeschlossenen Sätze
  let willHoeren = true;  // erst ein zweiter Tipp beendet es

  function lauschen() {
    const erkennung = new Spracherkennung();
    hoert = erkennung;

    erkennung.lang = "de-DE";
    erkennung.interimResults = true;

    // NICHT durchgehend zuhören.
    //
    // Chrome auf Android hält sich hier nicht an die Erwartung: Statt ein
    // Ergebnis laufend zu überarbeiten, hängt es jeden Zwischenstand als
    // neues Ergebnis an — "ich", "ich bin", "ich bin sehr". Wer die
    // aneinanderreiht, bekommt "ichich binich bin sehr".
    //
    // Also lassen wir es je einen Satz erkennen und starten danach neu. Dann
    // gibt es immer nur ein Ergebnis, und die Frage stellt sich nicht.
    erkennung.continuous = false;

    erkennung.onstart = () => {
      knopf.classList.add("hoert");
      feld.placeholder = "Ich höre …";
    };

    erkennung.onresult = (e) => {
      // Redet die App gerade selbst, ist alles, was hereinkommt, ihre eigene
      // Stimme aus dem Lautsprecher — nicht deine. Weghören.
      if (spricht) return;

      // Nur das jüngste Ergebnis zählt — alles davor ist schon in `fertig`.
      const letztes = e.results[e.results.length - 1];
      const stueck = letztes[0].transcript;

      if (letztes.isFinal) {
        fertig += stueck.trim() + " ";
        feld.value = (vorher + fertig).trimStart();
      } else {
        feld.value = (vorher + fertig + stueck).trimStart();
      }

      // Mitwachsen und mitlaufen: Du sollst sehen, dass er dich hört.
      feldAnpassen();
      feld.scrollTop = feld.scrollHeight;
    };

    erkennung.onerror = (e) => {
      if (e.error === "not-allowed") {
        willHoeren = false;
        alert("Ohne Zugriff aufs Mikrofon kann ich nicht zuhören. Erlaube es in den Browser-Einstellungen.");
      }
      // "no-speech" heißt nur: gerade war Stille. Kein Grund aufzuhören.
    };

    erkennung.onend = () => {
      // Ein Satz ist durch. Weiter zuhören, bis du das Mikrofon ausschaltest.
      if (willHoeren) {
        lauschen();
        return;
      }
      hoert = null;
      knopf.classList.remove("hoert");
      feld.placeholder = "Nachricht an Claude …";
    };

    erkennung.start();
  }

  // Nochmal tippen — oder Absenden — heißt: aufhören.
  hoertStoppen = () => {
    willHoeren = false;
    fertig = "";           // nichts aufheben, was gleich wieder auftauchen könnte

    if (hoert) {
      // Ihm das Wort abschneiden, nicht nur den Mund verbieten.
      //
      // Nach einem stop() feuert die Erkennung noch ein letztes Ereignis — und
      // das schrieb den alten Feldinhalt zurück, den man gerade abgeschickt
      // hatte. Der Text stand also wieder da, obwohl er längst weg war.
      hoert.onresult = null;
      hoert.onend = null;
      hoert.stop();
      hoert = null;
    }

    knopf.classList.remove("hoert");
    $("knopf-diktat-weg").hidden = true;
    feld.placeholder = "Nachricht an Claude …";
    hoertStoppen = null;
    hoertVerwerfen = null;
  };

  // Das Kreuz: zu spät gestartet, verhaspelt, Unsinn geredet — weg damit.
  //
  // Es stellt das Feld auf den Stand vor dem Diktat zurück. Was du vorher
  // getippt hattest, bleibt also stehen; nur das Gesprochene verschwindet.
  hoertVerwerfen = () => {
    hoertStoppen?.();
    feld.value = vorher.trimEnd();
    feldAnpassen();
  };

  $("knopf-diktat-weg").hidden = false;
  lauschen();
});

$("knopf-diktat-weg").addEventListener("click", () => hoertVerwerfen?.());

// --- Diktat glätten ----------------------------------------------------------
//
// Räumt den Text im Feld auf: Füllwörter, Wortdopplungen, Verhörer, dazu
// Satzzeichen und Großschreibung. Das übernimmt das schnelle Haiku-Modell auf
// dem Server; es dauert einen Moment, darum funkelt der Knopf solange. Das
// Ergebnis steht im Feld — abgeschickt wird es erst, wenn du es willst.
$("knopf-glaetten").addEventListener("click", async () => {
  const knopf = $("knopf-glaetten");
  const feld = $("eingabe");

  // Erst das Mikrofon zur Ruhe bringen, sonst schreibt es gleich wieder rein.
  hoertStoppen?.();

  if (knopf.disabled) return;
  const text = feld.value.trim();
  if (!text) {
    melde("Erst etwas diktieren oder tippen, dann glätten.");
    return;
  }

  knopf.disabled = true;
  knopf.classList.add("laedt");
  try {
    const { text: sauber } = await (await api("/glaetten", {
      method: "POST",
      body: JSON.stringify({ text }),
    })).json();
    feld.value = sauber;
    feldAnpassen();
    feld.focus();
  } catch (err) {
    melde(err.message || "Das Glätten hat gerade nicht geklappt.");
  } finally {
    knopf.disabled = false;
    knopf.classList.remove("laedt");
  }
});

// --- Die Sitzung umbenennen --------------------------------------------------
//
// Ein Tipp auf den Namen in der Kopfzeile. Umbenannt wird nur das Schild an der
// Tür: Die tmux-Sitzung, der Projektordner und die Mitschrift behalten ihre
// technischen Namen — an denen hängt alles andere. Der neue Name liegt auf dem
// Server, nicht im Handy, und gilt darum auf jedem Gerät.

$("sitzung-name").addEventListener("click", async () => {
  if (!aktuelleSitzung) return;

  const jetzt = aktuelleSitzung.anzeige || "";
  const neu = prompt(
    `Wie soll diese Sitzung heißen?\n\nTechnischer Name: ${lesbar(aktuelleSitzung.name)}\n(Leer lassen, um ihn wieder zu benutzen.)`,
    jetzt
  );
  if (neu === null) return;   // abgebrochen

  try {
    await api(`/sessions/${encodeURIComponent(aktuelleSitzung.name)}`, {
      method: "PATCH",
      body: JSON.stringify({ anzeige: neu }),
    });
    aktuelleSitzung.anzeige = neu.trim();
    $("sitzung-name").textContent = benannt(aktuelleSitzung);
    melde(neu.trim() ? `Heißt jetzt „${neu.trim()}“` : "Wieder der technische Name");
  } catch (err) {
    melde(err.message);
  }
});

$("knopf-zurueck").addEventListener("click", () => {
  steckdose?.close();
  steckdose = null;
  clearInterval(verlaufTakt);
  verlaufTakt = null;
  aktuelleSitzung = null;
  starteListe();
});

$("knopf-anheften").addEventListener("click", async () => {
  if (!aktuelleSitzung) return;
  const neu = !aktuelleSitzung.pinned;
  try {
    await api(`/sessions/${encodeURIComponent(aktuelleSitzung.name)}`, {
      method: "PATCH",
      body: JSON.stringify({ pinned: neu }),
    });
    aktuelleSitzung.pinned = neu;
    $("knopf-anheften").classList.toggle("an", neu);
  } catch (err) {
    melde(err.message || "Anheften ging gerade nicht.");
  }
});

// --- Das Modell wechseln -----------------------------------------------------
//
// Für eine schnelle Frage braucht es kein Opus. Claude Code kennt dafür den
// Befehl /model — wir tippen ihn nur, damit man unterwegs nicht diktieren muss.

let modelle = [];

async function modelleHolen() {
  if (!modelle.length) {
    modelle = await (await api("/modelle")).json();
  }
  return modelle;
}

function zeigeModell(name, aufgeloest) {
  const treffer = modelle.find((m) => m.name === name);
  // Kennen wir Claude Codes eigene Bestätigung ("Opus 5"), zeigen wir die —
  // ehrlicher als der Alias-Name, der jede neue Version stillschweigend
  // mitnimmt. Ohne Bestätigung und ohne bekanntes Modell steht dort nur
  // "Modell": irgendeinen Namen zu behaupten, wäre geraten.
  $("modell-name").textContent = aufgeloest || (treffer ? treffer.anzeige : "Modell");
  $("knopf-modell").classList.toggle("gesetzt", Boolean(treffer));
}

// Die Info-Leiste teilen sich zwei Dinge: links die Modus-Pille zum Antippen,
// dahinter Modell und Kontext-Rest. Beide schreiben ihren Teil und lassen die
// Leiste gemeinsam malen — verschwinden tut sie nur, wenn wirklich nichts
// Bekanntes übrig ist.
let _infoText = "";
let _modus = null;

// Die kurzen Aufschriften für die Modus-Pille. "bypassPermissions" — "fragt
// nie" — lässt sich nur beim Start setzen, steht hier aber mit dabei, damit
// auch so gestartete Sitzungen richtig beschriftet sind.
const MODUS_KURZ = {
  manual: "Fragt",
  acceptEdits: "Änderungen ok",
  plan: "Nur Plan",
  auto: "Auto",
  bypassPermissions: "Fragt nie",
};

function malInfoLeiste() {
  const bekannt = _modus && MODUS_KURZ[_modus];
  const pille = $("knopf-modus");
  pille.textContent = bekannt ? MODUS_KURZ[_modus] : "Modus";
  pille.classList.toggle("gesetzt", Boolean(bekannt));

  $("sitzung-info-text").textContent = _infoText;
  $("sitzung-info").hidden = !bekannt && !_infoText;
}

function zeigeSitzungInfo(jetzt) {
  const teile = [];
  // Der aufgelöste Name ("Opus 5") geht vor dem bloßen Alias-Etikett
  // ("Opus") — siehe zeigeModell().
  const aufgeloest = jetzt?.modellAufgeloest || aktuelleSitzung?.modellAufgeloest;
  const m = modelle.find((x) => x.name === aktuelleSitzung?.modell);
  if (aufgeloest) teile.push(aufgeloest);
  else if (m) teile.push(m.anzeige);
  if (jetzt && typeof jetzt.kontext === "number") {
    teile.push(`Kontext ${jetzt.kontext}% übrig`);
  }
  _infoText = teile.join("  ·  ");
  malInfoLeiste();
}

function zeigeModus(m) {
  _modus = m;
  malInfoLeiste();
}

// Ein Tipp schaltet den Berechtigungs-Modus weiter — genau wie Shift+Tab.
$("knopf-modus").addEventListener("click", async () => {
  if (!aktuelleSitzung) return;
  try {
    const { modus } = await (await api(
      `/sessions/${encodeURIComponent(aktuelleSitzung.name)}/modus`,
      { method: "POST" }
    )).json();
    zeigeModus(modus);
  } catch (err) {
    melde(err.message);
  }
});

// --- Verbrauch: Kontextfenster und Plan-Limits --------------------------------
//
// Ein Tipp auf die Info-Zeile öffnet das Blatt: oben der Füllstand der
// laufenden Unterhaltung, darunter die Plan-Limits des Abos mit ihrer
// Zurücksetzungszeit — dieselben Zahlen, die Claude Code am Rechner unter
// /usage zeigt. Kein Dauer-Gepolle: geholt wird nur beim Öffnen.

function tokenKurz(n) {
  if (n >= 1_000_000) {
    const m = n / 1_000_000;
    return (m === Math.round(m) ? m : m.toFixed(1)) + "M";
  }
  return Math.round(n / 1000) + "k";
}

function resetText(iso) {
  if (!iso) return "";
  const wann = new Date(iso);
  const rest = wann - new Date();
  if (isNaN(rest) || rest <= 0) return "";
  if (rest < 24 * 3600 * 1000) {
    const std = Math.floor(rest / 3600000);
    const min = Math.round((rest % 3600000) / 60000);
    return std > 0
      ? `Zurücksetzung in ${std} Std. ${min} Min.`
      : `Zurücksetzung in ${min} Min.`;
  }
  const tag = wann.toLocaleDateString("de-DE", { weekday: "short" });
  const zeit = wann.toLocaleTimeString("de-DE", { hour: "2-digit", minute: "2-digit" });
  return `Zurücksetzung ${tag}., ${zeit}`;
}

function verbrauchZeile(titel, prozent, detail) {
  const zeile = document.createElement("div");
  zeile.className = "verbrauch-zeile";

  const kopf = document.createElement("div");
  kopf.className = "verbrauch-kopf";
  const name = document.createElement("span");
  name.textContent = titel;
  const wert = document.createElement("span");
  wert.className = "verbrauch-wert";
  wert.textContent = detail ? `${detail} · ${prozent} %` : `${prozent} %`;
  kopf.append(name, wert);

  // Der Balken: grün, ab 70 % gelb, ab 90 % rot — man sieht auf einen Blick,
  // wo es eng wird, ohne eine Zahl lesen zu müssen.
  const balken = document.createElement("div");
  balken.className = "verbrauch-balken";
  const fuellung = document.createElement("div");
  fuellung.className = "verbrauch-fuellung";
  if (prozent >= 90) fuellung.classList.add("rot");
  else if (prozent >= 70) fuellung.classList.add("gelb");
  fuellung.style.width = `${Math.max(2, Math.min(100, prozent))}%`;
  balken.appendChild(fuellung);

  zeile.append(kopf, balken);
  return zeile;
}

function verbrauchBlattZu() { $("verbrauch-blatt").hidden = true; }
$("verbrauch-schatten").addEventListener("click", verbrauchBlattZu);
$("verbrauch-schliessen").addEventListener("click", verbrauchBlattZu);

// Die ganze Info-Zeile öffnet das Blatt — nicht nur der schmale Text. Nur die
// Modus-Pille macht weiter ihr eigenes Ding (Berechtigungs-Modus umschalten).
$("sitzung-info").addEventListener("click", async (e) => {
  if (e.target.closest("#knopf-modus")) return;
  if (!aktuelleSitzung) return;
  $("verbrauch-blatt").hidden = false;
  const liste = $("verbrauch-liste");
  liste.textContent = "Einen Moment …";
  try {
    const daten = await (await api(
      `/sessions/${encodeURIComponent(aktuelleSitzung.name)}/verbrauch`
    )).json();
    liste.textContent = "";
    if (daten.kontext) {
      liste.appendChild(verbrauchZeile(
        "Kontextfenster",
        daten.kontext.prozent,
        `${tokenKurz(daten.kontext.benutzt)} / ${tokenKurz(daten.kontext.limit)}`
      ));
    }
    for (const limit of daten.limits || []) {
      liste.appendChild(verbrauchZeile(limit.name, limit.prozent, resetText(limit.reset)));
    }
    if (!liste.children.length) {
      liste.textContent = "Dazu ist gerade nichts bekannt.";
    }
  } catch {
    liste.textContent = "Das ließ sich gerade nicht abrufen.";
  }
});

function blattZu() {
  $("modell-blatt").hidden = true;
}

$("modell-schatten").addEventListener("click", blattZu);
$("modell-schliessen").addEventListener("click", blattZu);

$("knopf-modell").addEventListener("click", async () => {
  if (!aktuelleSitzung) return;

  const liste = await modelleHolen();
  $("modell-liste").replaceChildren(
    ...liste.map((m) => {
      const zeile = document.createElement("button");
      zeile.type = "button";
      zeile.className = "modell-zeile";
      // Das laufende Modell trägt den Haken — so wie in der offiziellen App.
      const gewaehlt = m.name === aktuelleSitzung.modell;
      zeile.classList.toggle("gewaehlt", gewaehlt);
      // Gerüst ohne Daten; Titel und Art über textContent, damit auch aus der
      // Modell-Liste nie HTML in die Seite gelangt.
      zeile.innerHTML = `
        <span class="modell-titel"></span>
        <span class="modell-art"></span>
        ${gewaehlt ? '<span class="modell-haken">✓</span>' : ""}`;
      zeile.querySelector(".modell-titel").textContent = m.anzeige;
      zeile.querySelector(".modell-art").textContent = m.art;
      zeile.addEventListener("click", () => waehleModell(m));
      return zeile;
    })
  );
  $("modell-blatt").hidden = false;
});

async function waehleModell(m) {
  blattZu();
  try {
    // Die Antwort trägt schon Claude Codes eigene Bestätigung — das braucht
    // ein paar Sekunden (die App wartet serverseitig darauf), zeigt dafür
    // aber gleich den echten Namen statt nur des Alias.
    const antwort = await (await api(`/sessions/${encodeURIComponent(aktuelleSitzung.name)}/modell`, {
      method: "POST",
      body: JSON.stringify({ name: m.name }),
    })).json();
    aktuelleSitzung.modell = m.name;
    aktuelleSitzung.modellAufgeloest = antwort.modellAufgeloest;
    zeigeModell(m.name, antwort.modellAufgeloest);
    melde(antwort.modellAufgeloest ? `${antwort.modellAufgeloest} — ${m.art}` : `${m.anzeige} — ${m.art}`);
    setTimeout(ladeVerlauf, 800);
  } catch (err) {
    melde(err.message);
  }
}

// Den Stand sichern — auf Knopfdruck, nicht durch einen Zeitgeber, der
// unbeaufsichtigt an allen Projekten herumwerkelt. Du drückst, wenn du fertig
// bist; zu Hause holt sich der Rechner den Stand.
$("knopf-sichern").addEventListener("click", async () => {
  if (!aktuelleSitzung) return;
  const knopf = $("knopf-sichern");
  knopf.classList.add("laeuft");

  try {
    const { text } = await (await api(
      `/sessions/${encodeURIComponent(aktuelleSitzung.name)}/sichern`,
      { method: "POST" }
    )).json();

    knopf.classList.remove("laeuft");
    knopf.classList.add("an");
    zeichen(knopf, "#i-haken");
    setTimeout(() => {
      knopf.classList.remove("an");
      zeichen(knopf, "#i-sichern");
    }, 2000);

    melde(text);
  } catch (err) {
    knopf.classList.remove("laeuft");
    melde(err.message);
  }
});

// Eine kurze Rückmeldung, die von selbst wieder verschwindet — besser als ein
// Hinweisfenster, das man wegtippen muss.
function melde(text) {
  let zettel = document.getElementById("zettel");
  if (!zettel) {
    zettel = document.createElement("div");
    zettel.id = "zettel";
    zettel.className = "zettel";
    document.body.append(zettel);
  }
  zettel.textContent = text;
  zettel.classList.add("da");
  clearTimeout(zettel.zeit);
  zettel.zeit = setTimeout(() => zettel.classList.remove("da"), 2600);
}

$("knopf-melden").addEventListener("click", async () => {
  if (!aktuelleSitzung) return;
  const neu = !aktuelleSitzung.notifyWhenDone;

  if (neu) {
    try {
      await meldenEinschalten();
    } catch (err) {
      alert(err.message);
      return;
    }
  }

  try {
    await api(`/sessions/${encodeURIComponent(aktuelleSitzung.name)}`, {
      method: "PATCH",
      body: JSON.stringify({ notify_when_done: neu }),
    });
    aktuelleSitzung.notifyWhenDone = neu;
    $("knopf-melden").classList.toggle("an", neu);
  } catch (err) {
    // Nicht durchgegangen: Der Knopf bleibt aus, damit du nicht auf eine
    // Benachrichtigung wartest, die der Server gar nicht kennt.
    melde(err.message || "Die Benachrichtigung ließ sich gerade nicht umstellen.");
  }
});

// --- Vorlesen ----------------------------------------------------------------

let spricht = false;
let sprecherKnopf = null;     // welcher Knopf gerade "spricht" anzeigt

// Vorlesen über Web Audio statt eines <audio>-Elements. Nur so lassen sich die
// einzelnen Häppchen LÜCKENLOS aneinanderreihen: Wir planen jedes Stück exakt
// auf das Ende des vorigen. Ein <audio> muss die Quelle bei jedem Stück neu
// laden — und genau diese kurze Pause klang abgehakt.
let hörCtx = null;
let aktiveQuellen = [];       // laufende Tonquellen, zum Stoppen
let sprechLauf = 0;           // Zähler, mit dem ein alter Vortrag abbricht
let restStuecke = [];         // was vom Vortrag noch aussteht
let restText = "";            // beim Klingeln abgeschnitten — hierher gerettet

// Vor/Zurück per Kopfhörer- oder Lenkradtaste (Media Session, siehe unten).
// aktuellerIndex sagt springe(), wo der Vortrag gerade steht; sprungZiel ist
// der Wunsch, den die Sprech-Schleife am Kopf jeder Runde bedient.
let aktuellerIndex = null;
let sprungZiel = null;

function springe(richtung) {
  if (!spricht || aktuellerIndex === null) return;
  sprungZiel = aktuellerIndex + richtung;
}

// Die Vorlese-Leiste (Abspiel-Pille über der Eingabe): Pause/Weiter, die
// verstrichene Zeit und ein Kreuz. Erscheint nur während des Vorlesens.
const leisteEl = $("vorlese-leiste");
const zeitEl = $("vl-zeit");
const pauseKnopf = $("vl-pause");
let dauerTakt = null;         // der Sekundentakt, der die Zeit mitlaufen lässt
let manuellPausiert = false;  // von Hand pausiert — unterscheidet vom Anruf

function zeitFormat(sek) {
  sek = Math.max(0, Math.round(sek));
  return Math.floor(sek / 60) + ":" + String(sek % 60).padStart(2, "0");
}

// Das Pause/Weiter-Symbol: zwei Balken, wenn es läuft (Druck pausiert); ein
// Dreieck, wenn es steht (Druck spielt weiter).
function pauseSymbol(pausiert) {
  pauseKnopf?.querySelector("use")?.setAttribute("href", pausiert ? "#i-abspielen" : "#i-pause");
  pauseKnopf?.setAttribute("aria-label", pausiert ? "Weiter" : "Pause");
}

// Der Media Session sagen "hier läuft echte Wiedergabe" — ohne das drosseln
// vor allem iPhones den Ton binnen Sekunden, sobald der Bildschirm sperrt,
// und ein langer Vortrag bricht mitten im Satz ab. Mit der Anmeldung zeigt
// das Handy sogar Titel und Pause/Weiter/Stopp auf dem Sperrbildschirm — und
// Kopfhörer- oder Lenkradtasten steuern "einen Satz vor/zurück" (springe()),
// ganz ohne aufs Handy zu schauen. Rein kosmetisch fürs System — geht sie
// schief (ältere Browser, kein MediaMetadata), soll das nie das eigentliche
// Vorlesen stören, darum alles in try/catch.
function medienSitzungAn() {
  if (!("mediaSession" in navigator)) return;
  try {
    navigator.mediaSession.metadata = new MediaMetadata({
      title: "Antwort wird vorgelesen",
      artist: aktuelleSitzung ? benannt(aktuelleSitzung) : "Einzelstein Relay",
    });
    navigator.mediaSession.playbackState = "playing";
    navigator.mediaSession.setActionHandler("pause", () => {
      if (!manuellPausiert) pauseUmschalten();
    });
    navigator.mediaSession.setActionHandler("play", () => {
      if (manuellPausiert) pauseUmschalten();
    });
    navigator.mediaSession.setActionHandler("stop", () => stille());
    navigator.mediaSession.setActionHandler("previoustrack", () => springe(-1));
    navigator.mediaSession.setActionHandler("nexttrack", () => springe(1));
  } catch { /* dann eben ohne Sperrbildschirm-Anzeige */ }
}

function medienSitzungAus() {
  if (!("mediaSession" in navigator)) return;
  try {
    navigator.mediaSession.playbackState = "none";
    navigator.mediaSession.setActionHandler("pause", null);
    navigator.mediaSession.setActionHandler("play", null);
    navigator.mediaSession.setActionHandler("stop", null);
    navigator.mediaSession.setActionHandler("previoustrack", null);
    navigator.mediaSession.setActionHandler("nexttrack", null);
  } catch { /* dann eben ohne Sperrbildschirm-Anzeige */ }
}

function leisteAn() {
  manuellPausiert = false;
  pauseSymbol(false);
  if (zeitEl) zeitEl.textContent = "0:00";
  if (leisteEl) leisteEl.hidden = false;
  medienSitzungAn();
}

function dauerAus() {
  if (dauerTakt) { clearInterval(dauerTakt); dauerTakt = null; }
  manuellPausiert = false;
  if (leisteEl) leisteEl.hidden = true;
  medienSitzungAus();
}

// Wohin der Ton geht: NICHT geradewegs in den Lautsprecher (c.destination),
// sondern über ein echtes <audio>-Element.
//
// Der Grund ist Android. Für das System ist Web Audio keine Medienwiedergabe —
// nur ein Rechenwerk, das zufällig Töne macht. Ein Player, der im Sperrbildschirm
// steht und in der Hosentasche weiterlaufen darf, ist ein <audio>-Element. Ohne
// dieses Element dreht Android bei dunklem Bildschirm den Ton weg, während unsere
// Zeitachse munter weiterläuft: Man schaltet den Bildschirm wieder ein und der
// Vortrag ist zwanzig Sekunden weiter — genau die zwanzig Sekunden, die man nicht
// gehört hat.
//
// Der Umweg kostet nichts und ändert am Vortrag nichts: Die Häppchen werden
// weiterhin lückenlos auf der Ton-Uhr aneinandergereiht (siehe oben), nur landen
// sie am Ende in einem Strom, den das <audio>-Element abspielt. Klappt das
// Anwerfen nicht (ältere Browser, Autoplay-Sperre), geht es wie früher direkt in
// den Lautsprecher — dann eben nur bei hellem Bildschirm zuverlässig.
let tonAusgang = null;
let playerLief = false;       // hat das <audio> schon einmal wirklich gespielt?

async function tonAusgangAn(c) {
  const el = $("stimme");
  if (!tonAusgang) {
    try {
      const senke = c.createMediaStreamDestination();
      el.srcObject = senke.stream;
      tonAusgang = senke;
    } catch {
      tonAusgang = c.destination;      // kein Strom-Ziel: direkter Weg
    }
  }
  if (tonAusgang === c.destination) return tonAusgang;
  try {
    await el.play();
    playerLief = true;
  } catch {
    // Der Player springt nicht an. Beim ERSTEN Mal heißt das: Dieser Browser
    // macht den Umweg nicht mit — lieber hörbar ohne Hosentaschen-Kniff als
    // stumm mit, also zurück auf den direkten Weg, bevor das erste Häppchen
    // eingereiht wird. Lief er dagegen schon einmal, ist es nur die
    // Autoplay-Sperre nach einer Unterbrechung (Weiterlesen nach einem Anruf
    // kommt ohne Fingertipp). Dann bleibt alles verbunden wie es ist, sonst
    // hinge der halbe Vortrag am einen und der halbe am anderen Ausgang.
    if (!playerLief) {
      el.srcObject = null;
      tonAusgang = c.destination;
    }
  }
  return tonAusgang;
}

function tonAusgangAus() {
  // Den Player anhalten, sonst bleibt die Wiedergabe-Anzeige im Sperrbildschirm
  // stehen, obwohl längst nichts mehr kommt. Der Strom selbst bleibt bestehen
  // und wird beim nächsten Vortrag einfach wieder angeworfen.
  try { $("stimme").pause(); } catch { /* dann eben nicht */ }
}

// Die stille Dauerquelle — sie hält die Ton-Leitung offen, solange der Vortrag
// läuft. Der Grund: Zwischen zwei Häppchen spielt manchmal sekundenlang gar
// nichts (Piper braucht für den nächsten Satz auf der kleinen Maschine seine
// Zeit). Geht in genau so einer Lücke der Bildschirm aus, sieht Android einen
// Ton-Kontext ohne einen einzigen aktiven Ton — und legt ihn schlafen. Der
// Vortrag bricht mitten in der Antwort ab, obwohl der nächste Satz schon
// unterwegs war. Eine endlos laufende Schleife aus purer Stille (ein leerer
// Puffer, unhörbar, kostet nichts) überbrückt die Lücken: Für das System
// spielt IMMER etwas, also bleibt der Ton auch bei dunklem Bildschirm am
// Leben. Genau so löst es Rolis Vox-App auf Android — das hier ist das
// PWA-Gegenstück.
let dauerTon = null;

function dauerTonAn() {
  if (dauerTon || !hörCtx) return;
  try {
    const quelle = hörCtx.createBufferSource();
    quelle.buffer = hörCtx.createBuffer(1, hörCtx.sampleRate, hörCtx.sampleRate);
    quelle.loop = true;
    quelle.connect(tonAusgang || hörCtx.destination);
    quelle.start();
    dauerTon = quelle;
  } catch { /* dann eben ohne — schlimmstenfalls wie vorher */ }
}

function dauerTonAus() {
  try { dauerTon?.stop(); } catch { /* war schon aus */ }
  dauerTon = null;
}

// Ein Schlaf, der die TON-Uhr abwartet, nicht die Wanduhr: Wir warten, bis
// `hörCtx.currentTime` die Zielzeit erreicht. Diese Uhr steht still, solange der
// Kontext pausiert ist — so hält der ganze Vortrag bei „Pause" an, ohne dass die
// Einreih-Schleife im Leerlauf weiterrennt und zu früh alles wegräumt. `abbruch`
// löst sofort aus, wenn der Vortrag gestoppt oder überholt wurde.
function warteBisTonzeit(ziel, abbruch) {
  return new Promise((fertig) => {
    const pruefe = () => {
      if (!hörCtx || abbruch() || hörCtx.currentTime >= ziel) { fertig(); return; }
      setTimeout(pruefe, 80);
    };
    pruefe();
  });
}

function tonKontext() {
  if (!hörCtx) {
    hörCtx = new (window.AudioContext || window.webkitAudioContext)();
    tonKontextUeberwachen(hörCtx);
  }
  return hörCtx;
}

// decodeAudioData gibt es als Promise (moderne Browser) und als Rückruf (ältere).
function dekodiere(bytes) {
  return new Promise((fertig, fehler) => {
    const p = tonKontext().decodeAudioData(bytes, fertig, fehler);
    if (p && p.then) p.then(fertig, fehler);
  });
}

function zeichen(knopf, name) {
  knopf?.querySelector("use")?.setAttribute("href", name);
}

function stille() {
  spricht = false;
  sprechLauf++;               // ein laufender Vortrag erkennt daran: Schluss
  for (const q of aktiveQuellen) {
    try { q.stop(); } catch { /* war schon vorbei */ }
  }
  aktiveQuellen = [];
  restStuecke = [];           // von Hand gestoppt heißt: nichts steht mehr aus
  aktuellerIndex = null;
  sprungZiel = null;
  dauerTonAus();
  tonAusgangAus();
  dauerAus();
  sprecherKnopf?.classList.remove("spricht");
  zeichen(sprecherKnopf, "#i-lautsprecher");
  sprecherKnopf = null;
}

// --- Wenn das Telefon klingelt -----------------------------------------------
//
// Im Auto kommt ein Anruf über dieselbe Freisprecheinrichtung, aus der gerade
// Jonas spricht. Beide gleichzeitig geht nicht, und nach Knöpfen suchen kann man
// am Steuer nicht. Also hört Jonas von selbst auf — und liest danach weiter, wo
// er war.
//
// Das Signal dafür ist der Ton-Zustand, NICHT `visibilitychange`. Der Bildschirm
// geht im Auto nach ein paar Sekunden von selbst aus, während der Vortrag
// weiterläuft; wer daran abbricht, schaltet sich bei jedem Timeout selber ab.
// Nimmt das Telefon dagegen den Lautsprecher an sich, hält der Browser den
// Ton-Kontext an: 'interrupted' (iPhone) oder 'suspended' (Android).

function unterbrechen() {
  if (!spricht) return;
  const rest = restStuecke.join(" ");
  stille();
  hoertStoppen?.();     // das Gespräch braucht das Mikrofon dringender
  restText = rest;
}

let liestWeiter = false;      // Riegel gegen das Weiterlesen im Weiterlesen

async function weiterlesen() {
  if (liestWeiter || !restText || spricht || hoert || !freisprech) return;

  // Der Riegel ist kein Schmuck: Das Aufwecken des Tons meldet selbst wieder
  // "Ton ist da" — und das ist genau das Signal, das hierher führt. Ohne Riegel
  // ruft sich das Weiterlesen endlos selbst auf, bis der Browser aufgibt.
  liestWeiter = true;
  let text;
  try {
    // Den Rest erst aus der Hand geben, wenn der Ton wirklich da ist. Sonst
    // wäre er verloren, falls das Aufwecken scheitert, statt beim nächsten
    // Anklopfen nochmal versucht zu werden.
    text = restText;
    await tonKontext().resume();
    if (tonKontext().state !== "running") return;
    restText = "";
  } catch {
    return;                                  // dann eben beim nächsten Mal
  } finally {
    liestWeiter = false;
  }

  await sprich(text, $("knopf-vorlesen"));

  // Zu Ende gelesen, was der Anruf abgeschnitten hatte — jetzt bist du dran,
  // ohne dass du irgendwo hintippen musst.
  await mikrofonAufmachen();
}

/** Netz unter dem Weiterlesen.
 *
 *  Ob der Browser den Ton nach einem Gespräch von selbst wieder anwirft, hält
 *  jeder anders. Bleibt er hängen, käme das 'statechange'-Signal nie und der
 *  Rest der Antwort bliebe für immer liegen. Also klopfen wir alle drei
 *  Sekunden an — kostet nichts, wenn nichts aussteht.
 */
function pruefeObTonZurueck() {
  if (!restText || spricht || hoert || !freisprech || !hörCtx) return;
  weiterlesen();
}

function tonKontextUeberwachen(c) {
  c.addEventListener("statechange", () => {
    // Ton weg, obwohl wir mitten im Satz sind: Da klingelt etwas. Eine
    // Hand-Pause (manuellPausiert) hält den Ton bewusst an — die ist gemeint,
    // nicht ein Anruf, also hier nicht abbrechen.
    if (spricht && !manuellPausiert && c.state !== "running") {
      unterbrechen();
      return;
    }
    // Der Ton ist zurück — das Gespräch ist vorbei. Weiterlesen, sofern der
    // Freisprech-Modus an ist; sonst wartet der Rest am Lautsprecher-Knopf.
    if (c.state === "running" && restText) weiterlesen();
  });
}

/** Zerlegt einen Text in Häppchen, die sich gut sprechen lassen.
 *
 *  Ein langer Absatz am Stück braucht Sekunden, bis der erste Ton kommt — man
 *  drückt und es passiert nichts. Satzweise beginnt das Sprechen sofort,
 *  während der Rest im Hintergrund nachproduziert wird.
 */
// Der Teil von `voll`, der über das schon Gelesene hinausgeht — oder null, wenn
// nichts sauber anschließt. Grundlage des Folge-Modus: Beim Vorlesen fragt die
// App den mitwachsenden Antwort-Schnappschuss immer wieder ab; was neu ist, wird
// weitergelesen. Schließt der neue Stand nicht sauber an (Anfang aus dem Fenster
// gescrollt o. Ä.), lieber null — dann hört die App auf, statt Falsches zu lesen.
function neuerTeil(gelesen, voll) {
  if (voll.length > gelesen.length && voll.startsWith(gelesen)) {
    return voll.slice(gelesen.length);
  }
  return null;
}

function haeppchen(text, mindestens = 90) {
  // An Satzenden trennen — aber OHNE Lookbehind-Regex. `(?<=…)` kennt Safari
  // erst ab 16.4, und weil es ein Regex-Literal ist, scheitert sonst schon das
  // Einlesen der ganzen app.js: ältere iPhones sähen nur einen weißen
  // Bildschirm. Darum das Satzzeichen zuerst markieren, dann an der Marke
  // trennen — das Zeichen bleibt so beim Satz.
  const saetze = text.match(/[\s\S]*?[.!?:]\s+|[\s\S]+$/g) || [text];
  const stuecke = [];
  let aktuell = "";

  for (const satz of saetze) {
    aktuell += (aktuell ? " " : "") + satz;
    // Das allererste Häppchen so klein wie möglich: schon der erste ganze
    // Satz wird gesprochen, damit der Ton ohne Wartezeit einsetzt — bei der
    // schweren Stimme macht das den Unterschied zwischen vier Sekunden und
    // etwa einer. Erst ab dem zweiten Häppchen sammeln wir größere Portionen,
    // sonst zerhackt es den Vortrag.
    const schwelle = stuecke.length === 0 ? 1 : mindestens;
    if (aktuell.length >= schwelle) {
      stuecke.push(aktuell);
      aktuell = "";
    }
  }
  if (aktuell.trim()) stuecke.push(aktuell);
  return stuecke;
}

/** Liest einen Text vor. Ein zweiter Druck — auf denselben oder einen anderen
 *  Knopf — hört sofort auf. Es spricht immer nur eine Stimme. */
async function sprich(text, knopf, stimmeName = null, nachschub = null) {
  // Läuft schon etwas? Dann erst mal Ruhe.
  const derselbe = sprecherKnopf === knopf;
  if (spricht) {
    stille();
    if (derselbe) return;    // derselbe Knopf: das war der Stopp
  }

  if (!text?.trim()) return;

  // Nie mit offenem Mikrofon sprechen.
  //
  // Sonst hört das Mikrofon die eigene Stimme aus dem Lautsprecher und schreibt
  // sie in die Eingabe: Du diktierst, bekommst die Antwort vorgelesen — und
  // findest sie hinterher in deinem eigenen Text wieder. Das Mikrofon geht im
  // Freisprech-Modus nach dem Vortrag von selbst wieder auf.
  hoertStoppen?.();

  restText = "";       // ein neuer Vortrag hebt einen alten Rest auf
  spricht = true;
  sprecherKnopf = knopf;
  knopf.classList.add("spricht");
  zeichen(knopf, "#i-stopp");

  const meins = knopf;       // um zu merken, ob wir zwischendurch gestoppt wurden
  const lauf = ++sprechLauf; // diese Ausgabe; ein Stopp erhöht den Zähler
  let stuecke = haeppchen(text);   // wächst im Folge-Modus per Nachschub
  // Von der ersten Sekunde an wissen, wo wir stehen — falls gleich das Telefon
  // klingelt, bevor die Anzeige-Uhr das erste Mal getickt hat.
  aktuellerIndex = 0;
  restStuecke = stuecke.slice(0);
  const c = tonKontext();
  try { await c.resume(); } catch { /* Autoplay-Sperre — dann eben nicht */ }
  // Den Player anwerfen, BEVOR das erste Häppchen eingereiht wird — sonst hinge
  // es noch am alten Ausgang (siehe tonAusgangAn).
  await tonAusgangAn(c);
  // Die Leitung offen halten, bevor die erste Synthese-Lücke entsteht —
  // sonst schläft der Ton bei dunklem Bildschirm ein (siehe dauerTonAn).
  dauerTonAn();

  async function hole(stueck) {
    const antwort = await api("/speak", {
      method: "POST",
      // stimmeName nur bei der Hörprobe — sonst spricht die gewählte.
      body: JSON.stringify(
        stimmeName ? { text: stueck, stimme: stimmeName } : { text: stueck }
      ),
    });
    return dekodiere(await antwort.arrayBuffer());
  }

  const abgebrochen = () => !spricht || lauf !== sprechLauf || sprecherKnopf !== meins;

  try {
    // Das erste Häppchen schon holen; das nächste läuft immer im Voraus mit.
    let naechstes = stuecke.length ? hole(stuecke[0]) : null;
    let startZeit = c.currentTime + 0.08;   // kleiner Vorlauf bis zum ersten Ton
    let i = 0;
    // Wann Stück k auf der Ton-Uhr beginnt. Daraus liest die Anzeige ab, welches
    // Stück GERADE HÖRBAR ist — denn eingereiht wird weit im Voraus (s. unten),
    // die Schleifenvariable i ist also nicht mehr "das laufende Stück".
    let startZeiten = [];

    // Ab wann der Ton wirklich läuft — erst beim ersten geplanten Stück bekannt
    // (das Holen dauert). `startZeit` ist dann das Ende des zuletzt Eingereihten,
    // also ist „startZeit − sprechBeginn" die bislang bekannte Gesamtdauer.
    let sprechBeginn = null;
    leisteAn();
    dauerTakt = setInterval(() => {
      if (sprechBeginn === null) return;
      // Welches Stück ist GERADE ZU HÖREN? Aus den Startzeiten abgelesen —
      // daran hängen Vor/Zurück und das Weiterlesen nach einer Unterbrechung.
      // (Die Schleife unten reiht weit im Voraus ein, ihr i taugt dafür nicht.)
      let hoerbar = aktuellerIndex;
      for (let k = 0; k < startZeiten.length; k++) {
        if (startZeiten[k] !== undefined && startZeiten[k] <= c.currentTime) hoerbar = k;
      }
      aktuellerIndex = hoerbar;
      restStuecke = stuecke.slice(hoerbar);
      const gesamt = Math.max(0, startZeit - sprechBeginn);
      const jetzt = Math.min(Math.max(0, c.currentTime - sprechBeginn), gesamt);
      if (zeitEl) zeitEl.textContent = zeitFormat(jetzt);
    }, 500);

    while (true) {
      // Ein Sprung wartet: laufende Quellen abwürgen und an der Zielstelle neu
      // einreihen. Zu weit vor/zurück wird an den Rand geklemmt, statt zu
      // scheitern — am Anfang oder Ende ist "noch einer weiter" kein Fehler.
      if (sprungZiel !== null) {
        i = Math.max(0, Math.min(sprungZiel, stuecke.length - 1));
        sprungZiel = null;
        for (const q of aktiveQuellen) {
          try { q.stop(); } catch { /* war schon vorbei */ }
        }
        aktiveQuellen = [];
        startZeit = c.currentTime + 0.08;
        naechstes = hole(stuecke[i]);
        // Alte Startzeiten ab hier vergessen — die Stücke werden neu eingereiht,
        // und veraltete Einträge würden die Hörbar-Anzeige in die Irre führen.
        startZeiten = startZeiten.slice(0, i);
        aktuellerIndex = i;
        restStuecke = stuecke.slice(i);
      }

      // Bekannte Stücke aufgebraucht? Im Folge-Modus fragen wir nach, ob Claude
      // inzwischen weitergeschrieben hat — sonst ist hier Schluss.
      if (i >= stuecke.length) {
        if (!nachschub) break;
        const mehr = await nachschub(abgebrochen);
        if (abgebrochen()) return;
        if (!mehr) break;                    // Claude ist durch — es kommt nichts mehr
        const neue = haeppchen(mehr);
        if (!neue.length) continue;
        stuecke = stuecke.concat(neue);
        naechstes = hole(stuecke[i]);
      }

      const puffer = await naechstes;
      if (abgebrochen()) return;
      // Während des Holens kam ein Sprung dazwischen — dieses Stück ist schon
      // überholt, nicht mehr abspielen, sondern am Kopf der Schleife springen.
      if (sprungZiel !== null) continue;

      // Das übernächste Stück schon dekodieren, solange dieses läuft — sofern in
      // der bekannten Liste noch eins steht.
      naechstes = i + 1 < stuecke.length ? hole(stuecke[i + 1]) : null;

      const quelle = c.createBufferSource();
      quelle.buffer = puffer;
      quelle.connect(tonAusgang || c.destination);
      const start = Math.max(startZeit, c.currentTime);
      quelle.start(start);
      startZeiten[i] = start;
      if (sprechBeginn === null) sprechBeginn = start;   // ab hier läuft die Uhr
      startZeit = start + puffer.duration;   // das nächste schließt nahtlos an
      aktiveQuellen.push(quelle);

      // So weit wie möglich VORAB einreihen, statt bis kurz vors Stückende zu
      // warten: Die Ton-Uhr spielt Eingereihtes auf einem eigenen System-Faden
      // ab, den Android auch bei dunklem Bildschirm weiterlaufen lässt — das
      // Warten und Anhängen hier dagegen ist Browser-Arbeit, und die friert
      // Android in der Hosentasche ein. Vorher brach der Vortrag deshalb nach
      // dem gerade laufenden Stück (~20 Sekunden) einfach ab. Jetzt liegt der
      // ganze Vortrag in aller Regel komplett auf der Ton-Uhr, bevor der
      // Bildschirm ausgeht. Der Vorrat ist gedeckelt, damit ein sehr langer
      // Vortrag nicht unbegrenzt Speicher frisst (~5 MB je Minute Ton).
      const VORRAT = 900;    // Sekunden Vorsprung — 15 Minuten, reicht praktisch immer
      await warteBisTonzeit(startZeit - VORRAT, () => abgebrochen() || sprungZiel !== null);
      if (abgebrochen()) return;
      i++;
    }

    // Auf das Ende des letzten Stücks warten, dann aufräumen.
    await warteBisTonzeit(startZeit, abgebrochen);
    if (!abgebrochen()) stille();
  } catch (err) {
    if (lauf === sprechLauf) {
      stille();
      melde("Das Vorlesen hat nicht geklappt.");
    }
  }
}

// Der Lautsprecher oben liest die letzte Antwort — der schnelle Griff.
$("knopf-vorlesen").addEventListener("click", async () => {
  const knopf = $("knopf-vorlesen");

  if (spricht && sprecherKnopf === knopf) {
    stille();
    return;
  }
  if (!aktuelleSitzung) return;

  try {
    const { text } = await (await api(
      `/sessions/${encodeURIComponent(aktuelleSitzung.name)}/text`
    )).json();
    if (!text) throw new Error("Da ist nichts zum Vorlesen.");
    zuletztVorgelesen = text;   // damit Freisprech es nicht gleich nochmal liest

    // Folge-Modus: Ist Claude noch am Schreiben, sammelt die App die neu
    // eintrudelnden Sätze ein und liest weiter — du drückst nur EINMAL.
    // Aufgehört wird, wenn Claude fertig ist und nichts Neues mehr nachkommt.
    let gelesen = text;
    const nachschub = async (abgebrochen) => {
      const beginn = Date.now();
      let fertigInFolge = 0;    // wie oft „nichts Neues UND Claude ruht" in Folge
      while (!abgebrochen()) {
        let voll = "";
        try {
          voll = ((await (await api(
            `/sessions/${encodeURIComponent(aktuelleSitzung.name)}/text`
          )).json()).text) || "";
        } catch {
          return null;          // kein Text zu holen — dann eben Schluss
        }
        const neu = neuerTeil(gelesen, voll);
        if (neu) {
          gelesen = voll;
          zuletztVorgelesen = voll;
          return neu;
        }
        // Nichts Neues. Ist Claude fertig? Zweimal in Folge bestätigen, damit
        // eine kurze Atempause (der geglättete Zustand) nicht zu früh abbricht.
        fertigInFolge = beschaeftigt ? 0 : fertigInFolge + 1;
        if (fertigInFolge >= 2) return null;
        // Sicherheitsnetz gegen ein hängendes „beschäftigt": nach 30 s ohne
        // neuen Text ist Schluss, egal was der Zustand sagt.
        if (Date.now() - beginn > 30000) return null;
        await new Promise((r) => setTimeout(r, 700));
      }
      return null;
    };

    await sprich(text, knopf, null, nachschub);
  } catch (err) {
    stille();
    alert(err.message);
  }
});

// Pause/Weiter der Leiste. Wir halten den ganzen Ton-Kontext an (suspend) und
// lassen ihn wieder an (resume) — so bleibt die eingereihte Kette stehen und
// spielt lückenlos weiter, ohne dass etwas neu geholt werden muss. Das Merken
// als „von Hand pausiert" verhindert, dass der Anruf-Melder das als Anruf nimmt.
async function pauseUmschalten() {
  if (!hörCtx || (!spricht && !manuellPausiert)) return;
  if (manuellPausiert) {
    manuellPausiert = false;              // erst freigeben, dann anwerfen
    pauseSymbol(false);
    if ("mediaSession" in navigator) navigator.mediaSession.playbackState = "playing";
    try { await hörCtx.resume(); } catch { /* dann bleibt's eben stehen */ }
  } else {
    manuellPausiert = true;               // erst merken, dann anhalten
    pauseSymbol(true);
    if ("mediaSession" in navigator) navigator.mediaSession.playbackState = "paused";
    try { await hörCtx.suspend(); } catch { /* dann eben nicht */ }
  }
}

$("vl-pause").addEventListener("click", pauseUmschalten);
$("vl-schliessen").addEventListener("click", stille);

// --- Freisprech-Modus --------------------------------------------------------
//
// Im Auto will man weder lesen noch tippen. Ist der Modus an, liest die App die
// fertige Antwort von selbst vor und öffnet danach das Mikrofon — du sprichst,
// Claude arbeitet, die Antwort kommt gesprochen zurück, das Mikrofon steht schon
// offen. Abgeschickt wird weiterhin bewusst mit Senden, damit ein Verhörer nicht
// ungefragt bei Claude landet.

function freisprechAnzeigen() {
  $("knopf-freisprech").classList.toggle("an", freisprech);
}

/** Nach dem Vortrag das Mikrofon öffnen, damit du gleich antworten kannst.
 *
 *  Manche Browser erlauben das nur nach einer Berührung — klappt es nicht,
 *  tippst du das Mikrofon eben selbst an.
 */
async function mikrofonAufmachen() {
  // Dem Lautsprecher einen Augenblick lassen — sonst fängt das Mikrofon den
  // Nachhall des letzten Wortes noch ein.
  await new Promise((r) => setTimeout(r, 400));

  // Steht noch ein Rest aus, ist der Vortrag nicht durch, sondern von einem
  // Anruf abgeschnitten. Dann läuft gerade ein Gespräch — da ist ein
  // aufgehendes Mikrofon das Letzte, was jemand gebrauchen kann.
  if (freisprech && !imTerminal && !hoert && !spricht && !restText &&
      document.visibilityState === "visible") {
    try { $("knopf-diktat").click(); } catch { /* dann von Hand */ }
  }
}

$("knopf-freisprech").addEventListener("click", () => {
  freisprech = !freisprech;
  // Im strengen Privatmodus mancher Browser wirft setItem — dann schaltet der
  // Modus trotzdem für diese Sitzung, er wird nur nicht dauerhaft gemerkt.
  try { localStorage.setItem("freisprech", freisprech ? "1" : "0"); } catch { /* nicht merkbar */ }
  freisprechAnzeigen();
  melde(freisprech
    ? "Freisprech an — ich lese fertige Antworten vor und öffne danach das Mikrofon."
    : "Freisprech aus.");
});

async function freisprechVorlesen() {
  // Hörst du schon etwas oder diktierst gerade, misch dich nicht ein.
  if (spricht || hoert) return;
  if (!aktuelleSitzung) return;

  try {
    // Auf die FRISCHE Antwort warten. Direkt nach "fertig" liefert die
    // Mitschrift manchmal noch den vorigen Block — den hast du schon gehört.
    // Also kurz nachfassen, bis ein neuer Text da ist (höchstens ein paar
    // Sekunden), sonst gar nicht vorlesen.
    let text = "";
    for (let versuch = 0; versuch < 6; versuch++) {
      const antwort = await (await api(
        `/sessions/${encodeURIComponent(aktuelleSitzung.name)}/text`
      )).json();
      text = antwort.text || "";
      if (text && text !== zuletztVorgelesen) break;
      await new Promise((r) => setTimeout(r, 700));
      if (spricht || hoert) return;   // zwischendurch hörst/diktierst du doch
    }
    if (!text || text === zuletztVorgelesen) return;   // nichts Neues
    zuletztVorgelesen = text;

    await sprich(text, $("knopf-vorlesen"));
    await mikrofonAufmachen();
  } catch {
    // Kein Text, kein Netz — dann eben nicht.
  }
}

// Zurück zur Liste heißt auch: Ruhe.
$("knopf-zurueck").addEventListener("click", stille);

// --- Benachrichtigungen ------------------------------------------------------

function rohSchluessel(base64) {
  const gefuellt = (base64 + "===").slice(0, base64.length + (4 - (base64.length % 4)) % 4)
    .replace(/-/g, "+").replace(/_/g, "/");
  const roh = atob(gefuellt);
  return Uint8Array.from([...roh].map((z) => z.charCodeAt(0)));
}

async function meldenEinschalten() {
  if (!("serviceWorker" in navigator) || !("PushManager" in window)) {
    throw new Error("Dieses Handy kann keine Benachrichtigungen empfangen.");
  }

  const erlaubnis = await Notification.requestPermission();
  if (erlaubnis !== "granted") {
    throw new Error("Ohne deine Erlaubnis kann sich das Handy nicht melden.");
  }

  const wache = await navigator.serviceWorker.ready;
  const { schluessel } = await (await api("/melden/schluessel")).json();
  const gewuenscht = rohSchluessel(schluessel);

  let anmeldung = await wache.pushManager.getSubscription();

  // Passt die bestehende Anmeldung noch zum Ausweis des Servers?
  //
  // Hat der Server einen neuen bekommen, weist der Push-Dienst jede Nachricht
  // ab: "Die Zugangsdaten passen nicht zu denen, mit denen die Anmeldung
  // erstellt wurde." Und zwar stumm — man drückt die Glocke, alles sieht gut
  // aus, und es klingelt nie. Also: alte Anmeldung wegwerfen und neu machen.
  if (anmeldung) {
    const alt = new Uint8Array(anmeldung.options?.applicationServerKey ?? []);
    const gleich =
      alt.length === gewuenscht.length &&
      alt.every((wert, i) => wert === gewuenscht[i]);

    if (!gleich) {
      await anmeldung.unsubscribe();
      anmeldung = null;
    }
  }

  if (!anmeldung) {
    anmeldung = await wache.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: gewuenscht,
    });
  }

  await api("/melden/eintragen", {
    method: "POST",
    body: JSON.stringify(anmeldung.toJSON()),
  });
}

// Tippt man eine Benachrichtigung an, springt die App in die Sitzung.
navigator.serviceWorker?.addEventListener("message", async (e) => {
  const name = e.data?.oeffne;
  if (!name) return;
  try {
    const sitzungen = await (await api("/sessions")).json();
    const treffer = sitzungen.find((s) => s.name === name);
    if (treffer) oeffneSitzung(treffer);
  } catch {
    // dann eben nicht
  }
});

// --- Einstellungen: die Stimme ------------------------------------------------

// Die Texte der Stimmprobe — VIER verschiedene, jeder rund fünfzehn Sekunden.
// Beim Durchhören der Stimmen bekommt jede einen anderen, damit man nicht
// viermal dasselbe hört. Alle bewusst neutral: sprechen niemanden mit Namen an
// und nennen keine fremde Marke (die Probe läuft auch in der verkauften Fassung,
// wo Fremde sie hören), und sie sind selbst geschrieben — also ohne jede
// Urheberrechts- oder GEMA-Frage. Jeder zeigt die Stimme etwas anders: mal eine
// Frage, mal ein Innehalten, mal eine Zahl.
const PROBEN = [
  "Willkommen. Hören Sie einfach einen Augenblick zu. Eine gute Stimme hat es " +
  "nicht eilig — sie nimmt sich Zeit für den Satz und lässt das letzte Wort in " +
  "Ruhe ausklingen. Passt dieser Klang zu Ihnen?",

  "So klingt es, wenn Ihnen vorgelesen wird, was Sie sonst selbst lesen " +
  "müssten. Eine kurze Notiz am Morgen, ein längerer Text am Abend — unterwegs, " +
  "freihändig und ganz nebenbei.",

  "Manchmal ist das Schönste, kurz innezuhalten. Ein Wort in Ruhe hören, dem " +
  "nächsten Satz nachlauschen, und dabei merken, dass nichts drängt. So darf " +
  "sich Zuhören anfühlen.",

  "Eine klare Stimme spricht jeden Satz gleich sicher — eine ruhige Aussage, " +
  "eine Frage, oder eine Zahl wie dreihundertsiebenundzwanzig. Klingt das gut " +
  "für Sie? Dann bleiben Sie dabei.",
];

$("knopf-einstellungen").addEventListener("click", async () => {
  stoppeListe();
  zeige("einstellungen");

  const liste = $("stimmen-liste");
  liste.replaceChildren();

  let stimmen;
  try {
    stimmen = await (await api("/stimmen")).json();
  } catch {
    const hinweis = document.createElement("p");
    hinweis.className = "hinweis";
    hinweis.textContent = "Stimmen konnten nicht geladen werden — keine Verbindung?";
    liste.append(hinweis);
    ladeGeraete();
    return;
  }

  let probeNr = 0;
  for (const s of stimmen) {
    // Jede Stimme bekommt einen anderen Probetext (reihum) — so hört man beim
    // Durchprobieren nicht viermal denselben Satz.
    const probeText = PROBEN[probeNr % PROBEN.length];
    probeNr++;

    const el = document.createElement("div");
    el.className = "ordner" + (s.gewaehlt ? " gewaehlt" : "");
    el.innerHTML = `
      <span class="punkt-wahl"></span>
      <span class="stimme-name"></span>
      <span class="sub"></span>
      <button class="klein-knopf" aria-label="Anhören">
        <svg viewBox="0 0 24 24"><use href="#i-lautsprecher"/></svg>
      </button>`;
    el.querySelector(".stimme-name").textContent = s.anzeige;
    el.querySelector(".sub").textContent = s.art;

    // Anhören, ohne zu wählen.
    el.querySelector("button").addEventListener("click", async (e) => {
      e.stopPropagation();
      const knopf = e.currentTarget;
      if (spricht && sprecherKnopf === knopf) {
        stille();
        return;
      }
      await sprich(probeText, knopf, s.name);
    });

    // Wählen.
    el.addEventListener("click", async () => {
      try {
        await api("/stimmen", {
          method: "POST",
          body: JSON.stringify({ name: s.name }),
        });
        liste.querySelectorAll(".ordner").forEach((o) => o.classList.remove("gewaehlt"));
        el.classList.add("gewaehlt");
      } catch (err) {
        melde(err.message || "Die Stimme ließ sich gerade nicht wählen.");
      }
    });

    liste.append(el);
  }

  ladeGeraete();
});

// Die angemeldeten Geräte, jedes mit einem Knopf zum Aussperren. Ein verlorenes
// Handy verliert damit sofort seinen Zugang — nicht erst, wenn die Anmeldung
// von selbst ausläuft.
async function ladeGeraete() {
  const liste = $("geraete-liste");
  liste.replaceChildren();

  let geraete;
  try {
    geraete = await (await api("/geraete")).json();
  } catch {
    const hinweis = document.createElement("p");
    hinweis.className = "hinweis";
    hinweis.textContent = "Geräte konnten nicht geladen werden.";
    liste.append(hinweis);
    return;
  }

  for (const g of geraete) {
    const el = document.createElement("div");
    el.className = "ordner";
    el.innerHTML = `
      <span class="geraet-name"></span>
      <button class="klein-knopf" aria-label="Gerät aussperren">
        <svg viewBox="0 0 24 24"><use href="#i-kreuz"/></svg>
      </button>`;
    el.querySelector(".geraet-name").textContent = g.name;

    el.querySelector("button").addEventListener("click", async () => {
      if (!confirm(
        `Gerät „${g.name}" aussperren? Sein Zugang erlischt sofort. `
        + `Ist das dein aktuelles Handy, wirst du abgemeldet.`
      )) return;
      try {
        await api(`/geraete/${encodeURIComponent(g.name)}`, { method: "DELETE" });
        melde(`„${g.name}" ausgesperrt.`);
        ladeGeraete();
      } catch (err) {
        melde(err.message || "Aussperren hat nicht geklappt.");
      }
    });

    liste.append(el);
  }
}

$("knopf-abmelden").addEventListener("click", async () => {
  if (!confirm("Dieses Gerät abmelden? Du musst dich danach neu anmelden.")) return;
  try {
    await api("/abmelden", { method: "POST" });
  } catch {
    // Cookie ist so oder so weg — der Neuaufbau unten fängt alles auf.
  }
  location.reload();
});

$("knopf-einst-zurueck").addEventListener("click", () => {
  stille();
  starteListe();
});

// --- Neue Sitzung ------------------------------------------------------------

let gewaehlterOrdner = null;

$("knopf-neu").addEventListener("click", async () => {
  stoppeListe();
  zeige("neu");
  $("neu-fehler").hidden = true;

  let ordner;
  try {
    ordner = await (await api("/dirs")).json();
  } catch {
    const feld = $("neu-fehler");
    feld.hidden = false;
    feld.textContent = "Die Ordner konnten nicht geladen werden — keine Verbindung?";
    return;
  }
  const behaelter = $("neu-ordner");
  behaelter.replaceChildren();
  gewaehlterOrdner = ordner[0] ?? null;

  ordner.forEach((pfad, i) => {
    const el = document.createElement("div");
    el.className = "ordner" + (i === 0 ? " gewaehlt" : "");
    el.innerHTML = `<span class="punkt-wahl"></span><span class="pfad"></span>`;
    // Der Pfad ist auf dem Handy zu lang — der letzte Teil genügt.
    el.querySelector(".pfad").textContent = pfad.replace(/^\/home\/[^/]+/, "~");
    el.addEventListener("click", () => {
      behaelter.querySelectorAll(".ordner").forEach((o) => o.classList.remove("gewaehlt"));
      el.classList.add("gewaehlt");
      gewaehlterOrdner = pfad;
    });
    behaelter.append(el);
  });
});

$("knopf-abbrechen").addEventListener("click", starteListe);

$("neu-formular").addEventListener("submit", async (e) => {
  e.preventDefault();
  const fehler = $("neu-fehler");
  fehler.hidden = true;

  // Ein eingetipptes neues Projekt gewinnt über die Auswahl: Dann legt der
  // Server unter ~/projekte einen frischen Ordner samt Vorlage an.
  const neuesProjekt = $("neu-projekt").value.trim();
  const ordner = neuesProjekt ? `~/projekte/${neuesProjekt}` : gewaehlterOrdner;

  if (!ordner) {
    fehler.textContent = "Bitte einen Ordner wählen oder ein neues Projekt eintippen.";
    fehler.hidden = false;
    return;
  }

  const melden = $("neu-melden").checked;

  try {
    // Erst die Erlaubnis holen — danach wäre das Fenster weg, weil wir
    // schon in die Liste gesprungen sind.
    if (melden) {
      try {
        await meldenEinschalten();
      } catch (err) {
        // Kein Grund, die Sitzung deswegen platzen zu lassen.
        console.warn("Benachrichtigungen aus:", err.message);
      }
    }

    await api("/sessions", {
      method: "POST",
      body: JSON.stringify({
        name: $("neu-name").value,
        cwd: ordner,
        first_prompt: $("neu-auftrag").value,
        pinned: $("neu-anheften").checked,
        notify_when_done: melden,
        ohne_rueckfragen: $("neu-ohne-rueckfragen").checked,
      }),
    });
    $("neu-formular").reset();
    starteListe();
  } catch (err) {
    fehler.textContent = err.message;
    fehler.hidden = false;
  }
});

// --- Die Bibliothek ----------------------------------------------------------
//
// Alle Skills als Karten — mit dem Namen, den du vergeben hast, deiner
// Beschreibung und einer Kategorie. Die englischen Originale bleiben, wie sie
// sind; dein Etikett liegt darüber und darf ruhig deutsch und einprägsam sein.
// Von der Startseite aus zum Ordnen, aus einer Sitzung heraus zum Einfügen.

let skills = [];
let bibFach = "Alle";
let bibSuche = "";              // das Suchwort aus dem Lupenfeld
let bibZiel = null;             // die Sitzung, in die "Einfügen" schreibt
let bearbeiteterSkill = null;

const skillName = (s) => s.name || s.original_name;
const skillText = (s) => s.beschreibung || s.original_beschreibung;

// Favoriten — die Skills, die du dauernd brauchst. Ihre IDs liegen im
// Gerätespeicher; in der Liste rutschen sie nach oben, damit du sie sofort hast.
const FAV_SPEICHER = "skill-favoriten";
function favoritenLesen() {
  try { return JSON.parse(localStorage.getItem(FAV_SPEICHER)) || []; }
  catch { return []; }
}
function istFavorit(id) { return favoritenLesen().includes(id); }
function favoritUmschalten(id) {
  const favs = favoritenLesen();
  const i = favs.indexOf(id);
  if (i >= 0) favs.splice(i, 1); else favs.push(id);
  try { localStorage.setItem(FAV_SPEICHER, JSON.stringify(favs)); }
  catch { /* nicht merkbar — dann eben nur für diese Sitzung */ }
}

// Zuletzt benutzt — wann welcher Skill zuletzt kopiert/eingefügt wurde. Damit
// rutscht, was du gerade oft brauchst, von selbst nach oben, ohne Stern.
const BENUTZT_SPEICHER = "skill-benutzt";
function benutztLesen() {
  try { return JSON.parse(localStorage.getItem(BENUTZT_SPEICHER)) || {}; }
  catch { return {}; }
}
function benutztMerken(id) {
  const b = benutztLesen();
  b[id] = Date.now();
  try { localStorage.setItem(BENUTZT_SPEICHER, JSON.stringify(b)); }
  catch { /* nicht merkbar — dann bleibt die Reihenfolge eben, wie sie ist */ }
}

// Ein paar Kategorien zum Anfangen — sie stehen beim Benennen gleich als
// Vorschlag bereit, damit man nicht vor einem leeren Feld sitzt und rätselt,
// was man eintippen könnte. Eigene Kategorien darf man trotzdem frei tippen.
const STANDARD_KATEGORIEN = [
  "Marketing", "Webdesign", "Entwicklung", "Recherche", "Schreiben", "Sprache",
];

// Die Fächer, die es wirklich gibt: die schon vergebenen. Nur diese werden zu
// Reitern — leere Fächer als Reiter zu zeigen, wäre nur Verwirrung.
function bibKategorien() {
  const faecher = new Set(skills.map((s) => s.kategorie).filter(Boolean));
  return [...faecher].sort((a, b) => a.localeCompare(b, "de"));
}

// Was beim Benennen zur Auswahl steht: die vergebenen plus die Vorschläge.
function kategorieVorschlaege() {
  const alle = new Set([...bibKategorien(), ...STANDARD_KATEGORIEN]);
  return [...alle].sort((a, b) => a.localeCompare(b, "de"));
}

async function oeffneBibliothek(ziel) {
  bibZiel = ziel;
  // Von der Startseite: den Fünf-Sekunden-Takt der Liste anhalten. Aus einer
  // Sitzung heraus halten wir nichts an — wir kehren gleich dorthin zurück.
  if (!ziel) stoppeListe();
  zeige("bibliothek");
  // Mit leerer Lupe starten — ein altes Suchwort von letztem Mal würde sonst
  // die halbe Bibliothek verstecken.
  bibSuche = "";
  $("bib-suchfeld").value = "";
  try {
    skills = await (await api("/skills")).json();
  } catch {
    return;   // nicht angemeldet — die Ansicht hat schon gewechselt
  }
  baueReiter();
  zeigeSkills();
  fuelleKategorien();
}

$("knopf-bibliothek").addEventListener("click", () => oeffneBibliothek(null));
$("kachel-skill").addEventListener("click", () => {
  anhangBlattZu();
  oeffneBibliothek(aktuelleSitzung);
});

// Die Lupe: tippt man, wird sofort gefiltert.
$("bib-suchfeld").addEventListener("input", (e) => {
  bibSuche = e.target.value;
  zeigeSkills();
});

$("knopf-bib-zurueck").addEventListener("click", () => {
  const zurueckZurSitzung = Boolean(bibZiel);
  bibZiel = null;
  if (zurueckZurSitzung) zeige("sitzung");
  else starteListe();
});

function baueReiter() {
  const leiste = $("bib-reiter");
  const faecher = ["Alle", ...bibKategorien()];
  // Ein gewähltes Fach, das es nicht mehr gibt, fällt auf "Alle" zurück.
  if (!faecher.includes(bibFach)) bibFach = "Alle";

  leiste.replaceChildren(
    ...faecher.map((fach) => {
      const knopf = document.createElement("button");
      knopf.type = "button";
      knopf.className = "reiter" + (fach === bibFach ? " an" : "");
      knopf.textContent = fach;
      knopf.addEventListener("click", () => {
        bibFach = fach;
        baueReiter();
        zeigeSkills();
      });
      return knopf;
    })
  );
}

function zeigeSkills() {
  const liste = $("bib-liste");
  let sichtbar = bibFach === "Alle"
    ? skills
    : skills.filter((s) => s.kategorie === bibFach);

  // Das Suchwort filtert über Name UND Beschreibung — so findet man einen Skill
  // auch, wenn man nur weiß, wofür er gut war, nicht mehr, wie er heißt.
  const suche = bibSuche.trim().toLowerCase();
  if (suche) {
    sichtbar = sichtbar.filter((s) =>
      (skillName(s) || "").toLowerCase().includes(suche) ||
      (skillText(s) || "").toLowerCase().includes(suche)
    );
  }

  if (sichtbar.length === 0) {
    const leer = document.createElement("p");
    leer.className = "leer";
    leer.textContent = suche
      ? `Nichts gefunden zu „${bibSuche.trim()}".`
      : skills.length === 0
        ? "Keine Skills gefunden."
        : "In diesem Fach ist noch nichts.";
    liste.replaceChildren(leer);
    return;
  }

  // Reihenfolge: erst Favoriten, dann zuletzt Benutztes (neuestes oben), dann
  // der Rest in der Grundsortierung (alphabetisch vom Server — stabil erhalten).
  const favs = new Set(favoritenLesen());
  const benutzt = benutztLesen();
  const rang = (s) => (favs.has(s.id) ? 0 : benutzt[s.id] ? 1 : 2);
  sichtbar = [...sichtbar].sort((a, b) => {
    const ra = rang(a), rb = rang(b);
    if (ra !== rb) return ra - rb;
    if (ra === 1) return (benutzt[b.id] || 0) - (benutzt[a.id] || 0);  // Benutzte: neueste zuerst
    return 0;                                                          // Favoriten & Ungenutzte: Reihenfolge lassen
  });

  liste.replaceChildren(...sichtbar.map(skillKarte));
}

function skillKarte(s) {
  const el = document.createElement("div");
  el.className = "bib-karte";
  // Namen und Texte kommen aus SKILL.md und von dir — nie über innerHTML,
  // damit daraus kein Schadcode in die Seite gerät. Nur das Gerüst ist fest.
  el.innerHTML = `
    <div class="bib-kopf">
      <span class="bib-name"></span>
      ${s.kategorie ? '<span class="bib-fach"></span>' : ""}
      <button class="bib-stern" aria-label="Als Favorit merken"></button>
    </div>
    <div class="bib-desc"></div>
    <div class="bib-fuss">
      <span class="bib-herkunft"></span>
      <span class="fueller"></span>
      <button class="klein-knopf bib-kopie" aria-label="Befehl kopieren">
        <svg viewBox="0 0 24 24"><use href="#i-kopieren"/></svg>
      </button>
      ${bibZiel ? `<button class="klein-knopf bib-einfuegen" aria-label="In die Sitzung einfügen">
        <svg viewBox="0 0 24 24"><use href="#i-senden"/></svg>
      </button>` : ""}
    </div>`;

  el.querySelector(".bib-name").textContent = skillName(s);
  if (s.kategorie) el.querySelector(".bib-fach").textContent = s.kategorie;
  el.querySelector(".bib-desc").textContent = skillText(s) || "—";
  el.querySelector(".bib-herkunft").textContent = s.herkunft;

  // Der Stern: Favorit an/aus. Zeigt gefüllt/leer und färbt sich, wenn an.
  const stern = el.querySelector(".bib-stern");
  const sternMalen = () => {
    const an = istFavorit(s.id);
    stern.textContent = an ? "★" : "☆";
    stern.classList.toggle("an", an);
  };
  sternMalen();
  stern.addEventListener("click", (e) => {
    e.stopPropagation();          // nicht gleichzeitig das Benennen-Blatt öffnen
    favoritUmschalten(s.id);
    zeigeSkills();                // neu zeichnen — Favoriten rutschen nach oben
  });

  // Ein Tipp auf die Karte: benennen.
  el.addEventListener("click", () => skillBearbeiten(s));

  el.querySelector(".bib-kopie").addEventListener("click", (e) => {
    e.stopPropagation();   // sonst öffnet sich gleichzeitig das Benennen-Blatt
    skillKopieren(s, e.currentTarget);
  });

  const einf = el.querySelector(".bib-einfuegen");
  if (einf) {
    einf.addEventListener("click", (e) => {
      e.stopPropagation();
      skillEinfuegen(s);
    });
  }

  return el;
}

async function skillKopieren(s, knopf) {
  try {
    await navigator.clipboard.writeText(s.befehl);
    benutztMerken(s.id);
    knopf.classList.add("getan");
    knopf.querySelector("use").setAttribute("href", "#i-haken");
    setTimeout(() => {
      knopf.classList.remove("getan");
      knopf.querySelector("use").setAttribute("href", "#i-kopieren");
    }, 1600);
  } catch {
    melde("Kopieren hat nicht geklappt.");
  }
}

function skillEinfuegen(s) {
  if (!bibZiel) return;
  benutztMerken(s.id);
  // Nicht sofort abschicken: Der Befehl landet im Eingabefeld, damit du noch
  // etwas dahinter schreiben kannst — die meisten Skills nehmen ja einen Auftrag.
  const feld = $("eingabe");
  const vorher = feld.value.trim();
  feld.value = (vorher ? vorher + " " : "") + s.befehl + " ";
  bibZiel = null;
  zeige("sitzung");
  feldAnpassen();
  feld.focus();
  melde(`${skillName(s)} eingefügt`);
}

// --- Einen Skill benennen ---
//
// Dein Name, deine Beschreibung, deine Kategorie — im Blatt von unten. Das
// Original bleibt unberührt; alles wieder leeren nimmt dein Etikett ab.

function skillBearbeiten(s) {
  bearbeiteterSkill = s;
  $("skill-original").textContent =
    `Original: ${s.original_name} · ${s.herkunft} · ${s.befehl}`;
  $("skill-name").value = s.name;
  $("skill-name").placeholder = s.original_name;
  $("skill-beschreibung").value = s.beschreibung;
  $("skill-beschreibung").placeholder = (s.original_beschreibung || "").slice(0, 140);
  $("skill-kategorie").value = s.kategorie;
  fuelleKategorien();
  $("skill-blatt").hidden = false;
}

function skillBlattZu() {
  $("skill-blatt").hidden = true;
  bearbeiteterSkill = null;
}

$("skill-schatten").addEventListener("click", skillBlattZu);
$("skill-schliessen").addEventListener("click", skillBlattZu);

$("skill-speichern").addEventListener("click", async () => {
  if (!bearbeiteterSkill) return;
  try {
    await api("/skills", {
      method: "PATCH",
      body: JSON.stringify({
        id: bearbeiteterSkill.id,
        name: $("skill-name").value,
        beschreibung: $("skill-beschreibung").value,
        kategorie: $("skill-kategorie").value,
      }),
    });
    skillBlattZu();
    // Frisch holen: Name, Fach und damit die Reiter können sich geändert haben.
    skills = await (await api("/skills")).json();
    baueReiter();
    zeigeSkills();
    fuelleKategorien();
    melde("Gespeichert");
  } catch (err) {
    melde(err.message);
  }
});

function fuelleKategorien() {
  $("bib-kategorien").replaceChildren(
    ...kategorieVorschlaege().map((k) => {
      const o = document.createElement("option");
      o.value = k;
      return o;
    })
  );
}

// --- Einen neuen Skill anlegen ---
//
// Zwei Wege ins selbe Blatt: diktieren/tippen, was der Skill tun soll — oder
// eine fertige SKILL.md bzw. ein .zip hochladen. Danach steht der neue Skill
// gleich im Benennen-Blatt offen, damit du Kategorie und Namen setzen kannst.

function neuskillBlattZu() {
  $("neuskill-blatt").hidden = true;
}

function neuskillFehler(text) {
  const p = $("neuskill-fehler");
  p.textContent = text;
  p.hidden = false;
}

$("knopf-neuskill").addEventListener("click", () => {
  $("neuskill-name").value = "";
  $("neuskill-beschreibung").value = "";
  $("neuskill-anleitung").value = "";
  $("neuskill-fehler").hidden = true;
  $("neuskill-blatt").hidden = false;
});

$("neuskill-schatten").addEventListener("click", neuskillBlattZu);
$("neuskill-schliessen").addEventListener("click", neuskillBlattZu);

async function nachAnlegen(id) {
  neuskillBlattZu();
  skills = await (await api("/skills")).json();
  baueReiter();
  zeigeSkills();
  fuelleKategorien();
  // Den frisch angelegten gleich zum Benennen öffnen — besonders bei einer
  // hochgeladenen Datei, deren Name noch englisch ist.
  const neu = skills.find((s) => s.id === id);
  if (neu) skillBearbeiten(neu);
  melde("Skill angelegt");
}

$("neuskill-anlegen").addEventListener("click", async () => {
  const name = $("neuskill-name").value.trim();
  if (!name) {
    neuskillFehler("Gib dem Skill einen Namen.");
    return;
  }
  try {
    const { id } = await (await api("/skills/neu", {
      method: "POST",
      body: JSON.stringify({
        name,
        beschreibung: $("neuskill-beschreibung").value,
        anleitung: $("neuskill-anleitung").value,
      }),
    })).json();
    await nachAnlegen(id);
  } catch (err) {
    neuskillFehler(err.message);
  }
});

$("neuskill-datei-knopf").addEventListener("click", () => $("neuskill-datei").click());

$("neuskill-datei").addEventListener("change", async (e) => {
  const datei = e.target.files?.[0];
  e.target.value = "";               // damit dieselbe Datei nochmal ginge
  if (!datei) return;

  try {
    const paket = new FormData();
    paket.append("datei", datei);
    paket.append("name", $("neuskill-name").value.trim());

    // Roher fetch, kein api(): Bei einem Datei-Paket darf man den Content-Type
    // nicht selbst setzen, sonst kommt es zerrissen an.
    const antwort = await fetch("/api/skills/hochladen", { method: "POST", body: paket });
    if (!antwort.ok) {
      const koerper = await antwort.json().catch(() => ({}));
      throw new Error(koerper.detail || "Das Hochladen hat nicht geklappt.");
    }
    const { id } = await antwort.json();
    await nachAnlegen(id);
  } catch (err) {
    neuskillFehler(err.message);
  }
});

// --- Los geht's --------------------------------------------------------------

window.addEventListener("resize", () => {
  if (!fit || $("ansicht-sitzung").hidden) return;
  fit.fit();
  steckdose?.send(`\x00resize:${term.cols}:${term.rows}`);
});

if ("serviceWorker" in navigator) {
  navigator.serviceWorker.register("/sw.js").catch(() => {});
}

// Beim Start: Sind wir noch angemeldet? Wenn nicht, einmal mit dem
// Geräteschlüssel anmelden. Klappt auch das nicht, ist dieses Gerät noch nicht
// freigeschaltet — dann zeigen wir seinen öffentlichen Schlüssel.
// "Kein Netz" ist etwas anderes als "nicht angemeldet": fetch wirft bei
// Netzwerkproblemen einen TypeError, unser api() dagegen bei 401 einen normalen
// Error mit Text. Nur so lässt sich ein Gerät im Funkloch von einem wirklich
// abgemeldeten unterscheiden.
function istNetzfehler(err) {
  return err instanceof TypeError;
}

function zeigeNetzHinweis() {
  zeige("anmeldung");
  const feld = $("anmelde-fehler");
  feld.hidden = false;
  feld.textContent = "Keine Verbindung zum Server — ich bin wieder da, sobald Netz da ist.";
  // Sobald das Netz zurück ist, von selbst neu versuchen (nur einmal binden).
  window.addEventListener("online", () => start(), { once: true });
}

// Zwei Wege, wie das Handy die App mit einem Auftrag im Gepäck öffnet — beide
// erst NACH der Anmeldung auswerten, sonst öffnete sich das Blatt hinter dem
// Anmelde-Bildschirm, unsichtbar und ohne Wirkung. Beide räumen ihre Adresse
// danach weg, sonst öffnet ein bloßes Neuladen sie ein zweites Mal.

// Kurzbefehl vom Homescreen: langer Druck aufs Icon, siehe "shortcuts" im
// Manifest, kommt als "?neu=1" herein.
function kurzbefehlAusfuehren() {
  const params = new URLSearchParams(location.search);
  if (params.get("neu") !== "1") return;
  history.replaceState(null, "", location.pathname);
  $("knopf-neu").click();
}

// --- Teilen aus einer anderen App --------------------------------------------
//
// Man liest etwas im Browser, schreibt anderswo eine Datei — und will es hier
// weiterverarbeiten. Über "share_target" im Manifest steht die App im
// Teilen-Menü von Android, zwischen Nachrichten und Mail.
//
// Android schickt das Geteilte allerdings nicht als Adresszeile, sondern als
// echtes Formular mit Dateien daran. Eine Seite kann so etwas nicht annehmen;
// das macht der Service Worker, der es kurz beiseitelegt (siehe sw.js). Hier
// holen wir es wieder hervor und stellen die eine Frage, die die App nicht
// raten kann: in welche Sitzung damit? Danach steht der Text im Eingabefeld und
// die Datei als Anhang bereit — abgeschickt wird nichts von selbst.
const TEILEN_LAGER = "geteiltes";

let geteiltesGut = null;      // wartet darauf, in eine Sitzung zu wandern

async function geteiltesHolen() {
  // Der alte Weg über die Adresszeile bleibt: Wer nur Text teilt, kommt auch
  // ohne Service Worker hier an — und beim allerersten Mal nach dem Einrichten
  // steht der noch gar nicht.
  const params = new URLSearchParams(location.search);
  let texte = ["titel", "text", "url"]
    .map((n) => params.get(n)?.trim())
    .filter(Boolean);
  const dateien = [];

  if ("caches" in window) {
    try {
      const lager = await caches.open(TEILEN_LAGER);
      const textAntwort = await lager.match("/geteilt/texte");
      if (textAntwort) texte = texte.concat(await textAntwort.json());
      const listeAntwort = await lager.match("/geteilt/dateien");
      if (listeAntwort) {
        for (const eintrag of await listeAntwort.json()) {
          const antwort = await lager.match(eintrag.schluessel);
          if (!antwort) continue;
          const blob = await antwort.blob();
          dateien.push(new File([blob], eintrag.name, {
            type: eintrag.typ || blob.type,
          }));
        }
      }
      // Einmal geholt ist geholt — sonst hinge dieselbe Datei beim nächsten
      // Öffnen der App nochmal an.
      await caches.delete(TEILEN_LAGER);
    } catch { /* dann eben nur, was in der Adresszeile stand */ }
  }
  return { text: texte.join("\n\n"), dateien };
}

async function teilenAusfuehren() {
  if (location.pathname !== "/teilen") return;
  const gut = await geteiltesHolen();
  history.replaceState(null, "", "/");
  if (!gut.text && !gut.dateien.length) return;
  geteiltesGut = gut;
  await teilenBlattAuf();
}

async function teilenBlattAuf() {
  const { text, dateien } = geteiltesGut;
  const teile = [];
  if (dateien.length === 1) teile.push(dateien[0].name);
  else if (dateien.length) teile.push(`${dateien.length} Dateien`);
  if (text) teile.push("Text");
  $("teilen-was").textContent = `${teile.join(" und ")} — wohin damit?`;

  // Eine Sitzung, die es noch nicht gibt, kann keinen Anhang annehmen: Beim
  // Anlegen gibt es nur das Auftragsfeld. Also steht der Weg „neue Sitzung" nur
  // offen, wenn reiner Text geteilt wurde — lieber ein Knopf weniger als einer,
  // der die Datei stillschweigend verschluckt.
  $("teilen-neu").hidden = dateien.length > 0;

  const liste = $("teilen-liste");
  liste.replaceChildren();
  let sitzungen = [];
  try {
    sitzungen = await (await api("/sessions")).json();
  } catch { /* nicht angemeldet — dann bleibt die Liste eben leer */ }

  for (const s of sitzungen) {
    const knopf = document.createElement("button");
    knopf.type = "button";
    knopf.className = "blatt-zeile";
    const text = document.createElement("span");
    text.className = "blatt-zeile-text";
    const titel = document.createElement("span");
    titel.className = "blatt-zeile-titel";
    titel.textContent = benannt(s);
    text.append(titel);
    knopf.append(text);
    knopf.addEventListener("click", () => teilenIn(s));
    liste.append(knopf);
  }

  if (!sitzungen.length && dateien.length) {
    const leer = document.createElement("p");
    leer.className = "hinweis";
    leer.textContent = "Noch keine Sitzung da, an die sich etwas hängen ließe.";
    liste.append(leer);
  }
  $("teilen-blatt").hidden = false;
}

function teilenBlattZu() {
  $("teilen-blatt").hidden = true;
  geteiltesGut = null;      // verworfen ist verworfen
}

async function teilenIn(sitzung) {
  const gut = geteiltesGut;
  geteiltesGut = null;
  $("teilen-blatt").hidden = true;
  if (!gut) return;

  // Erst die Sitzung, dann der Anhang: oeffneSitzung räumt die Anhänge weg,
  // weil sie zu der Sitzung gehören, aus der sie kamen.
  oeffneSitzung(sitzung);
  if (gut.text) {
    $("eingabe").value = gut.text;
    feldAnpassen();
  }

  // Fotos und Dokumente nimmt der Server an verschiedenen Stellen entgegen.
  const bilder = gut.dateien.filter((d) => (d.type || "").startsWith("image/"));
  const papiere = gut.dateien.filter((d) => !(d.type || "").startsWith("image/"));
  if (bilder.length) await anhaengeHochladen(bilder, "bild", "bild", $("knopf-anhang"));
  if (papiere.length) await anhaengeHochladen(papiere, "datei", "datei", $("knopf-anhang"));
}

$("teilen-schatten").addEventListener("click", teilenBlattZu);
$("teilen-schliessen").addEventListener("click", teilenBlattZu);
$("teilen-neu").addEventListener("click", () => {
  const gut = geteiltesGut;
  geteiltesGut = null;
  $("teilen-blatt").hidden = true;
  $("knopf-neu").click();
  if (gut?.text) $("neu-auftrag").value = gut.text;
});

function nachAnmeldung() {
  starteListe();
  kurzbefehlAusfuehren();
  teilenAusfuehren();
}

async function start() {
  zeige("anmeldung");
  $("anmelde-fehler").hidden = true;

  // Schon angemeldet?
  try {
    await (await api("/sessions")).json();
    nachAnmeldung();
    return;
  } catch (err) {
    if (istNetzfehler(err)) { zeigeNetzHinweis(); return; }
    // sonst 401 — unten mit dem Geräteschlüssel anmelden
  }

  try {
    await anmelden();
    nachAnmeldung();
  } catch (err) {
    if (istNetzfehler(err)) { zeigeNetzHinweis(); return; }
    // Wirklich nicht freigeschaltet: den öffentlichen Schlüssel zeigen. Auch
    // das kann scheitern (z.B. blockierte IndexedDB im strengen Privatmodus) —
    // dann wenigstens eine verständliche Meldung statt einer toten Seite.
    try {
      await zeigeSchluessel();
    } catch {
      const feld = $("anmelde-fehler");
      feld.hidden = false;
      feld.textContent = "Dieses Gerät kann sich hier keinen Schlüssel anlegen "
        + "(Browser-Einstellungen prüfen: privater Modus oder blockierte Website-Daten).";
    }
  }
}

start();
