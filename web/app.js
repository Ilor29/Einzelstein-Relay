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

// Wie die Sitzung heißen soll: der selbstvergebene Name, sonst der technische.
function benannt(s) {
  return s.anzeige || lesbar(s.name);
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
      <span class="terminals"></span>
    </div>
  `;
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

// Freisprech-Modus: Ist er an, liest die App eine fertige Antwort von selbst
// vor und öffnet danach das Mikrofon — freihändig, ohne einen Knopf. Die
// Einstellung überlebt das Neuladen; `letzterZustand` merkt sich den vorigen
// Zustand, damit wir den Sprung von "arbeitet" zu "fertig" genau einmal treffen.
let freisprech = localStorage.getItem("freisprech") === "1";
let letzterZustand = null;

// Nachrichten, die du abgeschickt hast, während Claude noch arbeitete. Sie
// warten hier und werden einzeln nachgeschoben, sobald er fertig ist — so
// vermischt sich nichts und die Reihenfolge bleibt.
let warteschlange = [];

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
    const zustand = jetzt?.state;
    $("knopf-abbrechen-arbeit").hidden = zustand !== "running";
    zeigeSitzungInfo(jetzt);
    zeigeModus(jetzt?.modus);

    // Claude ist gerade fertig geworden.
    if (letzterZustand === "running" && zustand === "idle") {
      // Wartet noch etwas in der Schlange, geht das zuerst raus — du willst ja,
      // dass es weitergeht. Erst wenn nichts mehr wartet, liest Freisprech vor.
      if (!warteschlangeWeiter() && freisprech && !imTerminal) {
        freisprechVorlesen();
      }
    }
    letzterZustand = zustand;
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

  $("sitzung-name").textContent = benannt(sitzung);
  $("knopf-anheften").classList.toggle("an", sitzung.pinned);
  $("knopf-melden").classList.toggle("an", sitzung.notifyWhenDone);
  freisprechAnzeigen();
  // Erst die Liste holen, dann den Namen zeigen — sonst stünde beim ersten
  // Öffnen "Modell wählen", obwohl längst eines gesetzt ist.
  modelleHolen().then(() => {
    zeigeModell(sitzung.modell);
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
  offeneFrage = "";
  zuletztGesehen = "";     // neue Sitzung, alles frisch
  letzterZustand = null;   // Freisprech soll nicht sofort beim Öffnen auslösen
  warteschlange = [];      // die Schlange gehört zur alten Sitzung, nicht zur neuen
  zeigeWarteschlange();
  ladeVerlauf();
  pruefeFrage();
  clearInterval(verlaufTakt);
  verlaufTakt = setInterval(() => {
    ladeVerlauf();
    pruefeObClaudeArbeitet();
    pruefeFrage();
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

// Text an die Sitzung schicken — von der Eingabezeile oder aus dem Verlauf.
// In der Lese-Ansicht gibt es keine offene Verbindung; der Text geht über den
// Server hinein und erscheint gleich als deine Blase im Verlauf.
async function sendeInSitzung(text) {
  if (!text || !aktuelleSitzung) return;

  if (imTerminal) {
    steckdose?.send(text + "\r");
    return;
  }

  await api(`/sessions/${encodeURIComponent(aktuelleSitzung.name)}/senden`, {
    method: "POST",
    body: JSON.stringify({ text }),
  });
  setTimeout(ladeVerlauf, 600);
}

// --- Warteschlange -----------------------------------------------------------

function zeigeWarteschlange() {
  const el = $("warteschlange");
  el.replaceChildren();
  warteschlange.forEach((text, i) => {
    const zeile = document.createElement("div");
    zeile.className = "wartend";

    const t = document.createElement("span");
    t.className = "text";
    t.textContent = text;

    const weg = document.createElement("button");
    weg.type = "button";
    weg.setAttribute("aria-label", "Aus der Warteschlange nehmen");
    weg.innerHTML = '<svg viewBox="0 0 24 24" width="16" height="16"><use href="#i-kreuz"/></svg>';
    weg.addEventListener("click", () => {
      warteschlange.splice(i, 1);
      zeigeWarteschlange();
    });

    zeile.append(t, weg);
    el.append(zeile);
  });
  el.hidden = warteschlange.length === 0;
}

// Die nächste wartende Nachricht nachschieben. Gibt true zurück, wenn eine
// abging — dann hat das Vorrang vor allem anderen, was bei "fertig" passiert.
function warteschlangeWeiter() {
  if (!warteschlange.length) return false;
  const text = warteschlange.shift();
  zeigeWarteschlange();
  sendeInSitzung(text).catch(() => {
    // Ging nicht raus — vorne zurück in die Schlange, damit nichts verloren geht.
    warteschlange.unshift(text);
    zeigeWarteschlange();
  });
  return true;
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

  // Arbeitet Claude noch, wird die Nachricht nicht sofort hineingetippt — sie
  // wartet und geht ab, sobald er fertig ist. Sonst landete sie mitten in
  // seiner Arbeit und die Reihenfolge geriete durcheinander.
  if (!imTerminal && letzterZustand === "running") {
    warteschlange.push(text);
    zeigeWarteschlange();
    return;
  }

  try {
    await sendeInSitzung(text);
    // Ab jetzt arbeitet Claude — tippst du gleich noch etwas, wandert es in die
    // Schlange, statt seine Arbeit zu zerschneiden. Die nächste Runde bestätigt
    // den Zustand ohnehin.
    if (!imTerminal) letzterZustand = "running";
  } catch (err) {
    feld.value = text;      // nichts verloren
    alert(err.message);
  }
});

// --- Schnellbefehle ----------------------------------------------------------
//
// Ein Tipp schickt einen fertigen Satz an Claude — genau denselben Weg wie die
// Eingabezeile, also wandert er auch in die Warteschlange, wenn Claude noch
// arbeitet.
async function schnellbefehl(text) {
  if (!aktuelleSitzung || imTerminal || !text) return;
  hoertStoppen?.();

  if (letzterZustand === "running") {
    warteschlange.push(text);
    zeigeWarteschlange();
    return;
  }
  try {
    await sendeInSitzung(text);
    letzterZustand = "running";
  } catch (err) {
    melde(err.message);
  }
}

$("schnellbefehle").addEventListener("click", (e) => {
  const chip = e.target.closest(".chip");
  if (chip) schnellbefehl(chip.dataset.text);
});

// --- Ein Foto an Claude ------------------------------------------------------
//
// Claude Code kann Bilder von der Festplatte lesen. Also legt der Server das
// Foto dort ab und wir reichen den Pfad in die Sitzung — genau so, wie man ihn
// am Rechner selbst eintippen würde. Ein Screenshot erklärt oft mehr als drei
// Absätze, und unterwegs ist ein Foto schneller als jede Beschreibung.

// Mehrere Anhänge auf einmal hochladen — Fotos wie Dokumente. Jeder Anhang geht
// einzeln an den Server, der die Datei im Projektordner ablegt und den kurzen
// Pfad zurückgibt. Alle Pfade landen vorne im Eingabefeld; abgeschickt wird
// erst, wenn du auf Senden tippst — so kannst du noch etwas dazuschreiben.
async function anhaengeHochladen(dateien, endpunkt, feldname, knopf) {
  dateien = [...dateien];
  if (!dateien.length || !aktuelleSitzung) return;

  knopf.classList.add("laedt");
  const pfade = [];
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
      pfade.push(pfad);
    }

    const feld = $("eingabe");
    const bisher = feld.value.trim();
    const vorne = pfade.join(" ");
    feld.value = bisher ? `${vorne} ${bisher}` : `${vorne} `;
    feldAnpassen();
    feld.focus();
    melde(pfade.length === 1
      ? "Anhang angehängt — schreib etwas dazu und sende ab."
      : `${pfade.length} Anhänge angehängt — schreib etwas dazu und sende ab.`);
  } catch (err) {
    alert(err.message);
  } finally {
    knopf.classList.remove("laedt");
  }
}

$("knopf-bild").addEventListener("click", () => $("bild-waehler").click());
$("bild-waehler").addEventListener("change", (e) => {
  const dateien = e.target.files;
  e.target.value = "";                 // damit dieselbe Auswahl nochmal ginge
  anhaengeHochladen(dateien, "bild", "bild", $("knopf-bild"));
});

$("knopf-datei").addEventListener("click", () => $("datei-waehler").click());
$("datei-waehler").addEventListener("change", (e) => {
  const dateien = e.target.files;
  e.target.value = "";
  anhaengeHochladen(dateien, "datei", "datei", $("knopf-datei"));
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
  // Monolog den halben Bildschirm.
  eingabeFeld.style.height = Math.min(eingabeFeld.scrollHeight, 160) + "px";
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
  await api(`/sessions/${aktuelleSitzung.name}`, {
    method: "PATCH",
    body: JSON.stringify({ pinned: neu }),
  });
  aktuelleSitzung.pinned = neu;
  $("knopf-anheften").classList.toggle("an", neu);
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

function zeigeModell(name) {
  const treffer = modelle.find((m) => m.name === name);
  // Ohne bekanntes Modell steht dort nur "Modell" — behaupten, es liefe Opus,
  // wäre geraten. Claude Code sagt uns nicht, womit es gestartet ist.
  $("modell-name").textContent = treffer ? treffer.anzeige : "Modell";
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
  const m = modelle.find((x) => x.name === aktuelleSitzung?.modell);
  if (m) teile.push(m.anzeige);
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
      zeile.innerHTML = `
        <span class="modell-titel">${m.anzeige}</span>
        <span class="modell-art">${m.art}</span>
        ${gewaehlt ? '<span class="modell-haken">✓</span>' : ""}`;
      zeile.addEventListener("click", () => waehleModell(m));
      return zeile;
    })
  );
  $("modell-blatt").hidden = false;
});

async function waehleModell(m) {
  blattZu();
  try {
    await api(`/sessions/${encodeURIComponent(aktuelleSitzung.name)}/modell`, {
      method: "POST",
      body: JSON.stringify({ name: m.name }),
    });
    aktuelleSitzung.modell = m.name;
    zeigeModell(m.name);
    melde(`${m.anzeige} — ${m.art}`);
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
  stimme.onended = null;
  stimme.onerror = null;
  stimme.currentTime = 0;
  spricht = false;
  sprecherKnopf?.classList.remove("spricht");
  zeichen(sprecherKnopf, "#i-lautsprecher");
  sprecherKnopf = null;
}

/** Zerlegt einen Text in Häppchen, die sich gut sprechen lassen.
 *
 *  Ein langer Absatz am Stück braucht Sekunden, bis der erste Ton kommt — man
 *  drückt und es passiert nichts. Satzweise beginnt das Sprechen sofort,
 *  während der Rest im Hintergrund nachproduziert wird.
 */
function haeppchen(text, mindestens = 90) {
  const saetze = text.split(/(?<=[.!?:])\s+/);
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
async function sprich(text, knopf, stimmeName = null) {
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

  const meins = knopf;       // um zu merken, ob wir zwischendurch gestoppt wurden
  const stuecke = haeppchen(text);

  async function hole(stueck) {
    const antwort = await api("/speak", {
      method: "POST",
      // stimmeName nur bei der Hörprobe — sonst spricht die gewählte.
      body: JSON.stringify(
        stimmeName ? { text: stueck, stimme: stimmeName } : { text: stueck }
      ),
    });
    return URL.createObjectURL(await antwort.blob());
  }

  function spiele(quelle) {
    return new Promise((fertig, fehler) => {
      stimme.src = quelle;
      stimme.onended = fertig;
      stimme.onerror = fehler;
      stimme.play().catch(fehler);
    });
  }

  try {
    // Das erste Häppchen holen und sofort abspielen — während das nächste
    // schon unterwegs ist.
    let naechstes = hole(stuecke[0]);

    for (let i = 0; i < stuecke.length; i++) {
      const quelle = await naechstes;
      if (!spricht || sprecherKnopf !== meins) {
        URL.revokeObjectURL(quelle);
        return;
      }

      // Das übernächste schon anfordern, solange dieses noch läuft.
      naechstes = i + 1 < stuecke.length ? hole(stuecke[i + 1]) : null;

      await spiele(quelle);
      URL.revokeObjectURL(quelle);

      if (!spricht || sprecherKnopf !== meins) return;
    }

    stille();
  } catch (err) {
    stille();
    melde("Das Vorlesen hat nicht geklappt.");
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

$("knopf-freisprech").addEventListener("click", () => {
  freisprech = !freisprech;
  localStorage.setItem("freisprech", freisprech ? "1" : "0");
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
    const { text } = await (await api(
      `/sessions/${encodeURIComponent(aktuelleSitzung.name)}/text`
    )).json();
    if (!text) return;

    await sprich(text, $("knopf-vorlesen"));

    // Vorlesen durch, Modus noch an, keiner hört zu: das Mikrofon öffnen, damit
    // du gleich antworten kannst. Manche Browser erlauben das nur nach einer
    // Berührung — klappt es nicht, tippst du das Mikrofon eben selbst an.
    if (freisprech && !imTerminal && !hoert && !spricht &&
        document.visibilityState === "visible") {
      try { $("knopf-diktat").click(); } catch { /* dann von Hand */ }
    }
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

const PROBE = "Hallo Roli. So klinge ich, wenn ich dir vorlese, was Claude geschrieben hat.";

$("knopf-einstellungen").addEventListener("click", async () => {
  stoppeListe();
  zeige("einstellungen");

  const liste = $("stimmen-liste");
  liste.replaceChildren();

  const stimmen = await (await api("/stimmen")).json();

  for (const s of stimmen) {
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
      await sprich(PROBE, knopf, s.name);
    });

    // Wählen.
    el.addEventListener("click", async () => {
      await api("/stimmen", {
        method: "POST",
        body: JSON.stringify({ name: s.name }),
      });
      liste.querySelectorAll(".ordner").forEach((o) => o.classList.remove("gewaehlt"));
      el.classList.add("gewaehlt");
    });

    liste.append(el);
  }
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
let bibZiel = null;             // die Sitzung, in die "Einfügen" schreibt
let bearbeiteterSkill = null;

const skillName = (s) => s.name || s.original_name;
const skillText = (s) => s.beschreibung || s.original_beschreibung;

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
$("knopf-skill").addEventListener("click", () => oeffneBibliothek(aktuelleSitzung));

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
  const sichtbar = bibFach === "Alle"
    ? skills
    : skills.filter((s) => s.kategorie === bibFach);

  if (sichtbar.length === 0) {
    const leer = document.createElement("p");
    leer.className = "leer";
    leer.textContent = skills.length === 0
      ? "Keine Skills gefunden."
      : "In diesem Fach ist noch nichts.";
    liste.replaceChildren(leer);
    return;
  }

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
async function start() {
  zeige("anmeldung");
  $("anmelde-fehler").hidden = true;

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
