/* Hetzner-App — die Logik.
   Vier Ansichten, ein Terminal, ein Vorlese-Knopf. Kein Framework, kein
   Bauschritt: Datei ändern, Seite neu laden, fertig. */

const $ = (id) => document.getElementById(id);

const ANSICHTEN = ["anmeldung", "liste", "sitzung", "neu"];

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

// --- Anmeldung ---------------------------------------------------------------

$("anmelde-formular").addEventListener("submit", async (e) => {
  e.preventDefault();
  const fehler = $("anmelde-fehler");
  fehler.hidden = true;
  try {
    await api("/login", {
      method: "POST",
      body: JSON.stringify({ token: $("zugangswort").value }),
    });
    $("zugangswort").value = "";
    starteListe();
  } catch (err) {
    fehler.textContent = err.message;
    fehler.hidden = false;
  }
});

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

function karte(sitzung) {
  const el = document.createElement("div");
  el.className = "karte" + (sitzung.pinned ? " angeheftet" : "");
  el.innerHTML = `
    <div class="streifen ${sitzung.state}"></div>
    <div class="zeile-oben">
      <span class="name"></span>
      <span class="nadel" role="button" aria-label="Anheften">📌</span>
    </div>
    <div class="vorschau"></div>
    <div class="angaben">
      <span class="etikett ${sitzung.state}">${ETIKETT[sitzung.state]}</span>
      <span class="wann"></span>
    </div>
  `;
  // Über textContent gesetzt, nicht über innerHTML — ein Sitzungsname oder
  // eine Terminalzeile darf kein HTML in die Seite schmuggeln.
  el.querySelector(".name").textContent = sitzung.name;
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

  const angeheftet = sitzungen.filter((s) => s.pinned);
  const rest = sitzungen.filter((s) => !s.pinned);

  const gruppe = (titel, eintraege) => {
    if (eintraege.length === 0) return;
    const kopf = document.createElement("div");
    kopf.className = "gruppe";
    kopf.innerHTML = `<span></span><span class="anzahl">${eintraege.length}</span>`;
    kopf.firstElementChild.textContent = titel;
    liste.append(kopf, ...eintraege.map(karte));
  };

  gruppe("Angeheftet", angeheftet);
  gruppe("Zuletzt benutzt", rest);
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

function oeffneSitzung(sitzung) {
  stoppeListe();
  aktuelleSitzung = sitzung;

  $("sitzung-name").textContent = sitzung.name;
  $("knopf-anheften").classList.toggle("an", sitzung.pinned);
  zeige("sitzung");

  if (!term) {
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

  term.reset();
  fit.fit();
  verbinde(sitzung.name);
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
$("eingabe-formular").addEventListener("submit", (e) => {
  e.preventDefault();
  const feld = $("eingabe");
  const text = feld.value;
  if (!text) return;
  steckdose?.send(text + "\r");
  feld.value = "";
});

$("knopf-zurueck").addEventListener("click", () => {
  steckdose?.close();
  steckdose = null;
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

// --- Vorlesen ----------------------------------------------------------------

const stimme = $("stimme");
let spricht = false;

$("knopf-vorlesen").addEventListener("click", async () => {
  const knopf = $("knopf-vorlesen");

  if (spricht) {
    stimme.pause();
    stimme.currentTime = 0;
    spricht = false;
    knopf.classList.remove("spricht");
    return;
  }
  if (!aktuelleSitzung) return;

  knopf.classList.add("spricht");
  spricht = true;

  try {
    // Erst den Bildschirminhalt holen, schon aufbereitet: ohne Code, ohne
    // Werkzeugaufrufe, ohne Rahmen.
    const { text } = await (await api(`/sessions/${aktuelleSitzung.name}/text`)).json();
    if (!text) throw new Error("Da ist nichts zum Vorlesen.");

    const antwort = await api("/speak", {
      method: "POST",
      body: JSON.stringify({ text }),
    });
    const klang = await antwort.blob();

    stimme.src = URL.createObjectURL(klang);
    stimme.onended = () => {
      spricht = false;
      knopf.classList.remove("spricht");
      URL.revokeObjectURL(stimme.src);
    };
    await stimme.play();
  } catch (err) {
    spricht = false;
    knopf.classList.remove("spricht");
    alert(err.message);
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

  try {
    await api("/sessions", {
      method: "POST",
      body: JSON.stringify({
        name: $("neu-name").value,
        cwd: gewaehlterOrdner,
        first_prompt: $("neu-auftrag").value,
        pinned: $("neu-anheften").checked,
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

// Beim Start gleich versuchen, die Liste zu laden. Klappt das, sind wir noch
// angemeldet; wenn nicht, landen wir automatisch bei der Anmeldung.
api("/sessions")
  .then(starteListe)
  .catch(() => zeige("anmeldung"));
