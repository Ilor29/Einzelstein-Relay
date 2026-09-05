# Baubuch — so ist die Einzelstein-Fernbedienung gebaut

Stand: 01.09.2026, Version 155. Dieses Buch beschreibt den technischen Aufbau
und die Design-Entscheidungen. Es ist für den nächsten Menschen (oder die
nächste Claude-Sitzung) gedacht, der verstehen will, warum die Dinge so sind,
wie sie sind — nicht als Werbetext. Wenn sich am Aufbau etwas Grundsätzliches
ändert, gehört es hier nachgetragen.

## Was die App ist

Eine Web-App fürs Handy (installierbar, PWA), mit der man Claude-Code-Sitzungen
auf dem eigenen Server bedient: Sitzungen starten, Aufträge diktieren, Antworten
vorlesen lassen, das Terminal ansehen. Die Sitzungen selbst leben in tmux auf
dem Server — der Dienst kann jederzeit neu starten, ohne dass ein Gespräch
verloren geht. Man kann am Rechner anfangen und am Handy weitermachen.

Die größere Produktidee dahinter: ein Einrichtungs-Helfer, der auch
Nicht-Entwicklern einen eigenen Claude-Code-Server aufs Handy bringt (siehe
ANLEITUNG.md und deploy/cloud-init.yaml — ein frischer Hetzner-Server richtet
sich damit selbst ein). Die App ist also nicht nur Rolis Fernbedienung, sondern
soll eines Tages verkaufbar sein; einiges (Rechtsgerüst, offene Punkte) steht
in den CODE-GUARD-Berichten.

## Die zwei Hälften

**Server:** Python, FastAPI, ein einziger Dienst (`hetzner-app.service`,
Port 8787, gestartet aus `.venv`). Davor sitzt Caddy und macht HTTPS über eine
sslip.io-Adresse. Alle Laufzeit-Daten liegen in `~/.hetzner-app/` (Sitzungs-Meta,
Geräte, Stimmen-Wahl, Logs) — nichts davon im Repo.

**App:** `web/` — eine einzige Seite, kein Framework, kein Bauschritt. Datei
ändern, Seite neu laden, fertig. `index.html` (Ansichten und SVG-Symbole),
`app.js` (die ganze Logik), `styles.css`, dazu `sw.js` (macht die App nur
installierbar und speichert bewusst nichts zwischen) und `vendor/` (xterm.js
fürs Terminal). Die Versionsnummer lebt EINMAL, in `server.py` (`VERSION`);
der Server trägt sie beim Ausliefern in die Seite ein, die App prüft sie beim
Start und lädt sich selbst neu, wenn sie veraltet ist.

## Die Bausteine auf dem Server (hetzner_app/)

- **server.py** — der Dienst: alle API-Endpunkte, WebSocket fürs Terminal,
  statische Auslieferung, `VERSION`. Alles andere ist in Module ausgelagert.
- **tmux.py** — der Anschluss an tmux (eigener Socket `-L hz`, Sitzungen heißen
  `hz-<Name>`): Sitzungen anlegen, Text einwerfen, Bildschirm abgreifen. Dazu
  die Dialog-Erkennung (`dialog_zustand`): frei, abbrechbar, blockiert oder
  Vertrauensfrage — Letztere beantwortet der Server selbst, weil Escape dort
  eine Falle ist.
- **state.py** — was tmux nicht weiß: die Meta-Daten je Sitzung
  (`~/.hetzner-app/sitzungen.json`: angeheftet, Glocke, schlafend, Modell …)
  und die Zustands-Erkennung vom Bildschirm (arbeitet / wartet auf dich /
  ruht), erkannt an „esc to in…" und der Kreisel-Zeile in den letzten Zeilen.
- **verlauf.py** — macht aus Terminal-Gewusel eine lesbare Unterhaltung:
  zerlegt den Bildschirm in Blöcke (du, Claude, Werkzeug, Code). Übertragen
  wird der Verlauf nur bei Änderung (ETag/304), das spart unterwegs Daten.
- **mitschrift.py** — die richtige Quelle für den Verlauf: Claude Codes eigene
  Mitschriften unter `~/.claude/projects/`, ein Strang je Gespräch, überlebt
  jeden Neustart. Jeder Block trägt eine laufende Nummer (`nr`, je Datei).
  Beim Öffnen einer Karte kommen nur die letzten 150 Blöcke; beim Hochscrollen
  holt die App über `/verlauf/aelter?vor=` häppchenweise Älteres bis zum
  Anfang (seit V155). Dafür merkt sich der Leser alle 50 Blöcke eine
  Lesemarke (Nummer → Byte-Stelle) und liest ab dort Zeile für Zeile — eine
  13-MB-Datei liegt nie ganz im Speicher. Welche Datei zu welcher Karte
  gehört, vergibt die App seit V155 beim Start selbst (`--session-id`, im
  Meta-Feld `mitschrift`); die Erkennung an der Schreib-Spur
  (`server._mitschrift_zuordnen`) bleibt nur noch für `/clear` und alte Karten.
- **tts.py** — Vorlesen. Der schwierige Teil ist das Aussortieren: Fließtext
  wird gelesen, Code und Werkzeuge werden nur angesagt. Stimmen: Piper lokal
  (eigener Prozess auf Port 5005, Standard „Jonas" = de_DE-thorsten-medium),
  dazu Google Cloud und ElevenLabs als Wolken-Stimmen. Sprechtempo (gemütlich /
  normal / flott) liegt in `~/.hetzner-app/tempo.txt`.
- **strom.py** — das Radio-Prinzip (seit V153): Der Server spricht den ganzen
  Vortrag Satz für Satz in EINEN endlosen mp3-Strom, die App spielt ihn über
  ein `<audio>`-Element wie einen Internet-Radiosender. Nur so behandelt
  Android das Vorlesen als echte Medienwiedergabe (Sperrbildschirm-Player,
  läuft in der Hosentasche weiter). Der Folge-Modus (weiterlesen, solange
  Claude schreibt) läuft hier serverseitig. iPhone/iPad nutzt weiter den
  älteren Web-Audio-Weg in app.js (`sprichHaeppchen`).
- **melden.py** — Push-Nachrichten (Web Push, verschlüsselt): Ein Wächter
  schaut alle zehn Sekunden auf die Sitzungen und klingelt, wenn eine von
  „arbeitet" auf „wartet" oder „fertig" springt und die Glocke an ist. Jeder
  Versand steht im Journal.
- **geraete.py** — Anmeldung ohne Passwort über ein Schlüsselpaar, das auf dem
  Gerät entsteht; der Server kennt nur den öffentlichen Teil. Sitzungs-Cookie,
  Geräteliste, Erstkopplung.
- **speicher.py** — der Speicher-Wächter (eigener systemd-Timer): misst, macht
  eine Ampel, schreibt `speicher.json`. Entstanden nach zwei OOM-Abstürzen.
  Misst auch, was eine schlafende Karte an Speicher freigibt.
- **routinen.py** — zeigt crontab und systemd-Timer als verständliche Liste in
  der App (was läuft wann, zuletzt, als Nächstes; Pause/Weiter/Jetzt).
- **bibliothek.py** — deutsche Etiketten über die englischen Claude-Skills,
  ohne die Originale anzufassen.
- **verbrauch.py** — Füllstand des Kontextfensters (aus der Mitschrift) und
  die Plan-Limits.

## Die App im Browser (web/app.js)

Acht Ansichten in einer Seite (Anmeldung, Geräte, Liste, Sitzung, Neu,
Einstellungen, Bibliothek, Routinen), umgeschaltet über `zeige()`. Die
wichtigsten Stücke: Kartenliste mit Klappgruppen (angeheftet, zuletzt benutzt,
schläft), der Verlauf mit Sprechblasen, Uhrzeit und Tagestrennern und
Vorlese-Knöpfen je Antwort (die App hält alle gesehenen Blöcke nach Nummer in
einer Map und baut beim Takt nur neue Sprechblasen; Hochscrollen lädt die
Vergangenheit nach, der Anker hält die Scroll-Position), das
eingebettete Terminal (xterm.js über WebSocket), Diktat über die
Browser-Spracherkennung (satzweise neu gestartet, Entwurf wird je Karte in
localStorage gemerkt und übersteht das Wegwerfen der Seite), die
Link-Sammlung je Karte (Ketten-Knopf), Schnellbefehle, die Spotlight-Tour für
Neue und die Symbol-Erklärung. Vorlesen: siehe strom.py oben; das Ton-Tagebuch
(`tonEreignis` → `/api/ton-tagebuch`) ist ein abschaltbares Diagnose-Werkzeug
für die Hosentaschen-Jagd und muss vor einer Weitergabe aus (`TON_TAGEBUCH_AN`).

## Design — die Entscheidungen

**Handy zuerst, eine Hand.** Alles Wichtige ist mit dem Daumen erreichbar,
Blätter kommen von unten (wie in der offiziellen Claude-App), lange Listen
klappen. Am Rechner läuft dieselbe App in einer begrenzten Spalte.

**Farben.** Warmes Anthrazit statt Schwarz (`--grund #1F1E1D`), angelehnt an
die Claude-App. EIN Akzent in Terracotta (`--akzent #D97757`) — er markiert
das jeweils Wichtige und sonst nichts. Drei Statusfarben: grün „läuft", gelb
„wartet", grau „ruht". Wegwerfen hat ein eigenes, gedämpftes Rot, damit es
sich vom Akzent absetzt. Dunkel ist der einzige Modus.

**Schrift.** Monospace für alles, was vom Server kommt (Terminal, Pfade,
Code), Groteske für alles, was man drücken kann, Serife für gelesenen
Fließtext — längere Absätze lesen sich so ruhiger.

**Sprache.** Alles auf Deutsch und in Menschensprache: „Karte" statt Session,
„Glocke" statt Notification, „schläft" statt suspended. Fehlermeldungen sagen,
was man tun kann, nicht was intern schiefging. Meldungen erscheinen als
„Zettel", der von selbst verschwindet — keine Fenster, die man wegklicken muss.

**Sprechen und Hören sind erste Klasse.** Roli diktiert und lässt sich
vorlesen; die App ist darauf gebaut (Diktat-Knopf mit Verwerfen-Kreuz und
Glätten, Vorlese-Leiste mit Pause und Zeit, Freisprech-Modus, Tempo-Wahl).
Vorlesbarkeit entscheidet mit, wie Texte formuliert werden.

**Fremde Marken** (Claude, Anthropic, Hetzner …) tauchen im Produktnamen und
in öffentlichen Texten nicht auf; das Produkt heißt Einzelstein.

## Teuer bezahlte Lektionen (nicht wieder hineintappen)

- **Android und Ton:** Web Audio ist für Android keine Medienwiedergabe — in
  der Hosentasche wird der Ton gestoppt und die Seite irgendwann weggeworfen.
  Deshalb der mp3-Strom (strom.py). Ein endloser WAV-Strom taugt nicht:
  Chrome spielt ihn erst ab, wenn er zu Ende ist.
- **Piper und Port 5005:** `tts._starten()` räumt jeden Fremden ab, der
  den Port belegt. Wer tts aus einem ZWEITEN Python-Prozess aufruft (etwa in einem
  Test), schießt damit den Piper des laufenden Dienstes ab. Also: Stimme in
  Tests nachmachen, nie den echten Piper aus Testprozessen benutzen.
- **Piper-Speicher:** `MALLOC_ARENA_MAX=2` senkte den Verbrauch von 1,2 GB auf
  rund 160 MB. Nicht entfernen.
- **Kein Zwischenspeicher für die Hülle:** sw.js speichert absichtlich nichts —
  ein Cache lieferte nach Änderungen tagelang die alte Fassung aus.
- **Safari:** kein Lookbehind-Regex in app.js — ältere iPhones scheitern sonst
  schon am Einlesen der Datei (weißer Bildschirm).
- **Zustands-Erkennung:** Claude Codes Fußzeile wird in schmalen Fenstern
  gekürzt; erkannt wird darum nur „esc to in", und nur in den letzten Zeilen
  (sonst hält ein Zitat im Verlauf die Sitzung ewig für beschäftigt).
- **tmux und Aktivität:** `#{session_activity}` bleibt bei einer Sitzung ohne
  angehängtes Fenster auf der Startzeit stehen, obwohl Claude drinnen
  schreibt. Darum `#{window_activity}` mitnehmen. Mit dem eingefrorenen Wert
  hielt die Gesprächs-Erkennung eine arbeitende Karte für still und hängte
  ihre Mitschrift dem Nachbarn an (Pachmayr/Jour Fix, 01.09.).
- **Vertrauensfrage neuer Projekte:** Escape ist dort eine Falle (bricht ab
  statt zu antworten); der Server wählt selbst „Ja" an.
- **Tests:** Playwright liegt in `~/werkzeuge/browser/.venv`. Beim Testen die
  Tour-Schalter in localStorage vorbelegen, sonst liegt das Tour-Overlay über
  allen Knöpfen. Testserver auf Port 8799 mit ausgehängter Anmeldung; zum
  Beenden `fuser -k 8799/tcp` (ein `pkill -f` trifft die eigene Befehlszeile).

## Wo was liegt

Repo: `/home/roli/projekte/Hetzner-App` (GitHub: Einzelstein-Relay, privat).
Dienst: `hetzner-app.service` → Port 8787, Neustart mit
`sudo systemctl restart hetzner-app.service`, Kontrolle über `/api/version`.
Daten: `~/.hetzner-app/`. Deploy-Bausteine (Caddy, systemd-Einheiten,
cloud-init, Selbst-Aktualisierung, Spiegel für Lorenz und Lea): `deploy/`.
Produkt- und Verkaufsstand: `~/projekte/Brain/REGISTER.md`, Abschnitt
Hetzner-App.

## V158 (05.09.2026): Karten heißen auch als Sitzung so
`tmux.create` gibt Claude Code beim Start `--name <Kartenname>` mit, bei frischen wie bei
geweckten Karten. Grund: Seit Claude Code 2.1.224 können Sitzungen auf derselben Maschine
einander sehen (`/list-agents`) und Nachrichten schicken (`SendMessage`, `@name`), aber nur
benannte Sitzungen sind sauber ansprechbar. So kann das Brain einer Projekt-Karte einen
Beschluss schicken und sich melden lassen, wenn sie fertig ist. Laufende Karten bekommen den
Namen erst beim nächsten Schlafen und Wecken. Dazu in Rolis Nutzer-Einstellungen
`crossSessionInbound: accept` (sonst hält eine Karte im „fragt nie"-Modus jede Nachricht zur
Freigabe zurück) und eine Statuszeile (`~/.claude/statusline.sh`) mit Sitzungsname,
Kontext-Füllstand und den beiden Abo-Balken; sie erscheint als eine Zeile unter der Eingabe.
