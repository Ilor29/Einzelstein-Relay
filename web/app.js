/* Hetzner-App — die Logik.
   Vier Ansichten, ein Terminal, ein Vorlese-Knopf. Kein Framework, kein
   Bauschritt: Datei ändern, Seite neu laden, fertig. */

// Muss zu server.py:VERSION passen. Stimmt es nicht überein, läuft im Handy
// eine veraltete Fassung — und man sucht Fehler, die längst behoben sind.
// Genau das ist passiert: Ein Diktat-Fehler blieb, weil der Browser stur die
// alte Datei weiterbenutzte.
const VERSION = 17;

const $ = (id) => document.getElementById(id);

async function versionPruefen() {
  try {
    const { version } = await (await fetch("/api/version", { cache: "no-store" })).json();
    if (version === VERSION) return;

    // Veraltet. Alles wegwerfen, was der Browser aufbewahrt hat, und neu laden.
    const wachen = await navigator.serviceWorker?.getRegistrations?.() ?? [];
    await Promise.all(wachen.map((w) => w.unregister()));

    const namen = await caches?.keys?.() ?? [];
    await Promise.all(namen.map((n) => caches.delete(n)));

    // Der Zusatz zwingt auch den letzten Zwischenspeicher in die Knie.
    location.replace(location.pathname + "?neu=" + version);
  } catch {
    // Kein Netz, keine Antwort — dann eben weiterarbeiten.
  }
}

const ANSICHTEN = ["anmeldung", "geraet", "liste", "sitzung", "neu"];

function zeige(name) {
  for (const a of ANSICHTEN) $(`ansicht-${a}`).hidden = a !== name;
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
    throw new Error(körper.detail || `Fehler ${antwort.status}`);
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
};

function alter(sekunden) {
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

function karte(sitzung) {
  const el = document.createElement("div");
  el.className = "karte" + (sitzung.pinned ? " angeheftet" : "");
  el.innerHTML = `
    <div class="streifen ${sitzung.state}"></div>
    <div class="zeile-oben">
      <span class="name"></span>
      <button class="nadel" aria-label="Anheften">
        <svg viewBox="0 0 24 24"><use href="#i-nadel"/></svg>
      </button>
    </div>
    <div class="vorschau"></div>
    <div class="angaben">
      <span class="etikett ${sitzung.state}">${ETIKETT[sitzung.state]}</span>
      <span class="wann"></span>
    </div>
  `;
  // Über textContent gesetzt, nicht über innerHTML — ein Sitzungsname oder
  // eine Terminalzeile darf kein HTML in die Seite schmuggeln.
  el.querySelector(".name").textContent = lesbar(sitzung.name);
  el.querySelector(".vorschau").textContent = sitzung.preview || "—";
  el.querySelector(".wann").textContent = alter(sitzung.idleSeconds);

  el.addEventListener("click", () => oeffneSitzung(sitzung));

  el.querySelector(".nadel").addEventListener("click", async (e) => {
    e.stopPropagation();   // sonst öffnet sich gleichzeitig die Sitzung
    await api(`/sessions/${sitzung.name}`, {
      method: "PATCH",
      body: JSON.stringify({ pinned: !sitzung.pinned }),
    });
    ladeListe();
  });

  return el;
}

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

    const kopf = document.createElement("div");
    kopf.className = "gruppe" + (zu ? " klappbar" : "");
    kopf.innerHTML = `
      ${zu ? '<span class="pfeil">▸</span>' : ""}
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
    // sie nicht sehen. Ein Tipp auf die Zeile klappt sie auf.
    const fach = document.createElement("div");
    fach.className = "fach";
    fach.hidden = true;
    fach.append(...karten);
    liste.append(fach);

    kopf.addEventListener("click", () => {
      fach.hidden = !fach.hidden;
      kopf.querySelector(".pfeil").textContent = fach.hidden ? "▸" : "▾";
    });
  };

  gruppe("Wartet auf dich", wartend);
  gruppe("Angeheftet", angeheftet);
  gruppe("Zuletzt benutzt", eigene);
  // Sitzungen, die nicht von dieser App stammen — allen voran die, in der
  // Claude Code gerade selbst läuft. Eingeklappt, weil es viele sind.
  gruppe("Läuft auch auf dem Server", fremde, { zu: true });
}

let listenTakt = null;

function starteListe() {
  zeige("liste");
  ladeListe();
  clearInterval(listenTakt);
  // Alle fünf Sekunden nachsehen — so wandert eine Sitzung von "läuft" nach
  // "wartet auf dich", ohne dass du etwas tun musst.
  listenTakt = setInterval(ladeListe, 5000);
}

function stoppeListe() {
  clearInterval(listenTakt);
  listenTakt = null;
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

/** Setzt Claudes Text — mit Fettschrift, Kursiv und Befehlen.
 *
 *  Claude schreibt in Markdown. Ungerendert stehen dann Sternchen und
 *  Backticks im Text herum, und "**wichtig**" liest sich schlechter als
 *  wichtig. Bewusst kein Framework: Wir bauen die Elemente selbst und setzen
 *  jeden Text über textContent — so kann aus einer Antwort niemals HTML werden,
 *  das die Seite verändert.
 */
function schreibe(ziel, text) {
  // Zerlegen an **fett**, *kursiv* und `befehl` — die Klammern bleiben in den
  // Stücken erhalten, damit wir sie unterscheiden können.
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

function verlaufBlock(block) {
  const el = document.createElement("div");

  if (block.typ === "du") {
    el.className = "blase du";
    el.textContent = block.text;
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

    leiste.append(hoeren, kopieren);
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
  // Wer unten steht, wird mitgenommen. Wer oben liest, bleibt, wo er ist.
  const unten = behaelter.scrollHeight - behaelter.scrollTop - behaelter.clientHeight < 80;

  behaelter.replaceChildren(...bloecke.map(verlaufBlock));

  if (unten) behaelter.scrollTop = behaelter.scrollHeight;
}

// Der Anhalten-Knopf zeigt sich nur, während Claude wirklich arbeitet.
async function pruefeObClaudeArbeitet() {
  if (!aktuelleSitzung) return;
  try {
    const sitzungen = await (await api("/sessions")).json();
    const jetzt = sitzungen.find((s) => s.name === aktuelleSitzung.name);
    $("knopf-abbrechen-arbeit").hidden = jetzt?.state !== "running";
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

  $("sitzung-name").textContent = lesbar(sitzung.name);
  $("knopf-anheften").classList.toggle("an", sitzung.pinned);
  $("knopf-melden").classList.toggle("an", sitzung.notifyWhenDone);
  zeige("sitzung");

  // Zum Lesen aufmachen, nicht ins Terminal. Das ist der Normalfall.
  imTerminal = false;
  $("verlauf").hidden = false;
  $("terminal").hidden = true;
  $("sondertasten").hidden = true;
  $("knopf-ansicht").querySelector("use").setAttribute("href", "#i-terminal");

  $("verlauf").replaceChildren();
  zuletztGesehen = "";     // neue Sitzung, alles frisch
  ladeVerlauf();
  clearInterval(verlaufTakt);
  verlaufTakt = setInterval(() => {
    ladeVerlauf();
    pruefeObClaudeArbeitet();
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
    // wieder dran.
    if (aktuelleSitzung?.name === name && !$("ansicht-sitzung").hidden) {
      setTimeout(() => verbinde(name), 1500);
    }
  });
}

function setzeVerbindung(verbunden) {
  const anzeige = $("verbindung");
  anzeige.classList.toggle("weg", !verbunden);
  anzeige.lastChild.textContent = verbunden ? "verbunden" : "getrennt";
}

// Eingabezeile: bequemer als direkt ins Terminal zu tippen, weil die
// Handytastatur so ihre Autokorrektur und das Diktieren anbieten kann.
$("eingabe-formular").addEventListener("submit", async (e) => {
  e.preventDefault();
  const feld = $("eingabe");
  const text = feld.value.trim();
  if (!text || !aktuelleSitzung) return;

  // Erst das Mikrofon zum Schweigen bringen.
  //
  // Sonst hört es weiter zu, hält seinen bisherigen Satz noch fest und
  // schreibt ihn gleich wieder ins Feld — man löscht ihn und er kommt zurück.
  hoertStoppen?.();

  feld.value = "";

  if (imTerminal) {
    steckdose?.send(text + "\r");
    return;
  }

  // In der Lese-Ansicht gibt es keine offene Verbindung. Der Text geht über
  // den Server hinein — und erscheint gleich als deine Blase im Verlauf.
  try {
    await api(`/sessions/${encodeURIComponent(aktuelleSitzung.name)}/senden`, {
      method: "POST",
      body: JSON.stringify({ text }),
    });
    setTimeout(ladeVerlauf, 600);
  } catch (err) {
    feld.value = text;      // nichts verloren
    alert(err.message);
  }
});

// --- Ein Foto an Claude ------------------------------------------------------
//
// Claude Code kann Bilder von der Festplatte lesen. Also legt der Server das
// Foto dort ab und wir reichen den Pfad in die Sitzung — genau so, wie man ihn
// am Rechner selbst eintippen würde. Ein Screenshot erklärt oft mehr als drei
// Absätze, und unterwegs ist ein Foto schneller als jede Beschreibung.

$("knopf-bild").addEventListener("click", () => $("bild-waehler").click());

$("bild-waehler").addEventListener("change", async (e) => {
  const datei = e.target.files?.[0];
  e.target.value = "";                 // damit dasselbe Bild nochmal ginge
  if (!datei || !aktuelleSitzung) return;

  const knopf = $("knopf-bild");
  knopf.classList.add("laedt");

  try {
    const paket = new FormData();
    paket.append("bild", datei);

    // Kein Content-Type setzen: Der Browser muss die Grenzmarke selbst
    // eintragen, sonst kommt das Paket zerrissen an.
    const antwort = await fetch(
      `/api/sessions/${encodeURIComponent(aktuelleSitzung.name)}/bild`,
      { method: "POST", body: paket }
    );
    if (!antwort.ok) throw new Error("Das Bild kam nicht an.");

    const { pfad } = await antwort.json();

    // Der Text daneben — falls du schon etwas dazu geschrieben hast.
    const feld = $("eingabe");
    const dazu = feld.value.trim();
    feld.value = "";

    await api(`/sessions/${encodeURIComponent(aktuelleSitzung.name)}/senden`, {
      method: "POST",
      body: JSON.stringify({ text: dazu ? `${pfad} ${dazu}` : pfad }),
    });
    setTimeout(ladeVerlauf, 800);
  } catch (err) {
    alert(err.message);
  } finally {
    knopf.classList.remove("laedt");
  }
});

// --- Diktieren ---------------------------------------------------------------
//
// Im Auto ist Tippen keine Option. Ein Druck auf das Mikrofon, sprechen, und
// der Text steht im Feld — abgeschickt wird erst, wenn du es willst, damit ein
// Verhörer nicht sofort bei Claude landet.

const Spracherkennung = window.SpeechRecognition || window.webkitSpeechRecognition;
let hoert = null;
let hoertStoppen = null;   // beendet das Zuhören — von überall her aufrufbar

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
      // Nur das jüngste Ergebnis zählt — alles davor ist schon in `fertig`.
      const letztes = e.results[e.results.length - 1];
      const stueck = letztes[0].transcript;

      if (letztes.isFinal) {
        fertig += stueck.trim() + " ";
        feld.value = (vorher + fertig).trimStart();
      } else {
        feld.value = (vorher + fertig + stueck).trimStart();
      }
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
    feld.placeholder = "Nachricht an Claude …";
    hoertStoppen = null;
  };

  lauschen();
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
  await api(`/sessions/${aktuelleSitzung.name}`, {
    method: "PATCH",
    body: JSON.stringify({ pinned: neu }),
  });
  aktuelleSitzung.pinned = neu;
  $("knopf-anheften").classList.toggle("an", neu);
});

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

  await api(`/sessions/${aktuelleSitzung.name}`, {
    method: "PATCH",
    body: JSON.stringify({ notify_when_done: neu }),
  });
  aktuelleSitzung.notifyWhenDone = neu;
  $("knopf-melden").classList.toggle("an", neu);
});

// --- Vorlesen ----------------------------------------------------------------

const stimme = $("stimme");
let spricht = false;
let sprecherKnopf = null;     // welcher Knopf gerade "spricht" anzeigt

function zeichen(knopf, name) {
  knopf?.querySelector("use")?.setAttribute("href", name);
}

function stille() {
  stimme.pause();
  stimme.currentTime = 0;
  if (stimme.src) URL.revokeObjectURL(stimme.src);
  spricht = false;
  sprecherKnopf?.classList.remove("spricht");
  zeichen(sprecherKnopf, "#i-lautsprecher");
  sprecherKnopf = null;
}

/** Liest einen Text vor. Ein zweiter Druck — auf denselben oder einen anderen
 *  Knopf — hört sofort auf. Es spricht immer nur eine Stimme. */
async function sprich(text, knopf) {
  // Läuft schon etwas? Dann erst mal Ruhe.
  const derselbe = sprecherKnopf === knopf;
  if (spricht) {
    stille();
    if (derselbe) return;    // derselbe Knopf: das war der Stopp
  }

  if (!text?.trim()) return;

  spricht = true;
  sprecherKnopf = knopf;
  knopf.classList.add("spricht");
  zeichen(knopf, "#i-stopp");

  try {
    const antwort = await api("/speak", {
      method: "POST",
      body: JSON.stringify({ text }),
    });
    const klang = await antwort.blob();

    // Zwischenzeitlich gestoppt? Dann nicht doch noch losplappern.
    if (!spricht || sprecherKnopf !== knopf) return;

    stimme.src = URL.createObjectURL(klang);
    stimme.onended = stille;
    await stimme.play();
  } catch (err) {
    stille();
    alert(err.message);
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
    await sprich(text, knopf);
  } catch (err) {
    stille();
    alert(err.message);
  }
});

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

  let anmeldung = await wache.pushManager.getSubscription();
  if (!anmeldung) {
    anmeldung = await wache.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: rohSchluessel(schluessel),
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

// --- Neue Sitzung ------------------------------------------------------------

let gewaehlterOrdner = null;

$("knopf-neu").addEventListener("click", async () => {
  stoppeListe();
  zeige("neu");
  $("neu-fehler").hidden = true;

  const ordner = await (await api("/dirs")).json();
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

  if (!gewaehlterOrdner) {
    fehler.textContent = "Bitte einen Ordner wählen.";
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
        cwd: gewaehlterOrdner,
        first_prompt: $("neu-auftrag").value,
        pinned: $("neu-anheften").checked,
        notify_when_done: melden,
      }),
    });
    $("neu-formular").reset();
    starteListe();
  } catch (err) {
    fehler.textContent = err.message;
    fehler.hidden = false;
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
async function start() {
  zeige("anmeldung");
  $("anmelde-fehler").hidden = true;

  // Erst nachsehen, ob wir überhaupt die aktuelle Fassung sind.
  await versionPruefen();

  try {
    await (await api("/sessions")).json();
    starteListe();
    return;
  } catch {
    // noch nicht angemeldet — weiter unten
  }

  try {
    await anmelden();
    starteListe();
  } catch {
    zeigeSchluessel();
  }
}

start();
