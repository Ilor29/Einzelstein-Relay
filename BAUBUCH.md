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
- **Login-Bildschirm ist kein wegdrückbarer Dialog:** Auch /login sagt unten
  „Esc to cancel" — der Dialog-Wächter drückte ihn deshalb weg, jede
  Anmeldung vom Handy endete mit „Login interrupted", und Roli musste per
  SSH auf den Server (Aussperrung 07.09.). Seit V159 kennt `dialog_zustand`
  den Zustand „anmeldung" (Methoden-Auswahl, Code-Seite, OAuth-Fehlerseite)
  und die App führt die Anmeldung selbst: Endpunkte `/anmelden` und
  `/anmelde-code` in server.py, Anmelde-Kasten mit Code-Feld in der App.
- **Akku des Handys (V160, 07.09.):** Jeder Push weckt das Handy und macht den
  Bildschirm an. 94 Stöße in anderthalb Tagen, 89 davon „ist fertig", die
  Hälfte von einer einzigen Marketing-Karte. Seither klingelt es NUR bei
  „wartet auf dich" (melden.py); ein offenes Mikrofon streamt pausenlos Ton
  zur Google-Erkennung und schließt sich darum nach zwei Minuten ohne
  verstandenes Wort von selbst. Ob das Ton-Tagebuch funkt, entscheidet
  allein der Server (`HETZNER_APP_TON_TAGEBUCH=1`, in die Seite eingetragen)
  — kein fest eingebautes true mehr im öffentlichen Repo.
- **Anzeige und Klingeln sind zweierlei (V162, 08.09.):** Eine fertige, aber
  ungelesene Antwort steht als eigenes Feld `ungelesen` in der Kartenliste —
  NICHT als neuer `state`. Am `state` hängt `melden.py`, und das klingelt seit
  V160 nur noch bei echten Rückfragen. Wer "ungelesen" in den Zustand hineinbaut,
  holt das abgeschaffte Dauergebimmel zurück. `fertig_seit` setzt `overview()`
  beim Zustandswechsel weg von RUNNING, `gesehen` der Endpunkt
  `POST /sessions/{name}/gesehen` — beides in den Metadaten, damit mehrere
  Geräte denselben Stand sehen.
- **Tastatur am Handy (V166 verworfen, V167, 14.09.):** Ein `position: fixed`-Element
  hängt am LAYOUT-Fenster, und das bleibt in Chrome für Android beim Aufgehen der
  Tastatur standardmäßig gleich groß (`interactive-widget=resizes-visual`). Die
  Eingabezeile lag darum unter der Tastatur. Der erste Versuch (V166 und ein
  Dashboard-Skript) rechnete per `visualViewport` nach und schob mit
  `scrollTo`/`offsetTop` — am echten Handy wurde es dadurch schlimmer (Eingabe halb
  verdeckt, darunter ein leeres Loch), weil Skript und System gegeneinander
  schoben. Richtig ist die dokumentierte Einstellung im Viewport-Tag:
  `interactive-widget=resizes-content` (Chrome ab 108,
  https://developer.chrome.com/blog/viewport-resize-behavior). Dann schrumpft das
  Layout selbst, `inset: 0` rückt mit, kein Skript nötig. Sie gilt nur im obersten
  Dokument — darum steht sie in der Relay UND im LEIT//PULS-Dashboard, dessen
  Rahmen die Relay umschließt. Mit Playwright nicht prüfbar (keine Tastatur);
  der Beweis kommt vom Handy.
- **Fingerziele (V161, 08.09.):** Die Schnellbefehle waren 24 px hoch mit 6 px
  Abstand — am Handy traf Roli regelmäßig den Nachbarn. Jetzt 44 px (Chips)
  bzw. 48 px (Menü). Beim Vergrößern nicht `display: flex` auf einen Chip
  setzen: Das macht ihn zum Block, und jeder Chip bricht in eine eigene Zeile
  (`inline-flex` nehmen). Und die Hüll-Elemente `#chip-reihe-eigene` /
  `#eigene-befehle` brauchen `display: contents`, sonst greift der Abstand der
  Reihe nur um die Hülle herum, nicht zwischen den Chips darin.
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

## 18.09.2026: PNG über den Dokument-Weg wurde abgewiesen

**Auslöser, Roli am 18.09. um 08:51 an die Medienwerk-Karte:** „das eine ist tatsächlich, dass wir
hier in der App keine PNG-Dateien einfügen können, aber das müssen wir an die jeweilige Stelle
weiterleiten, dass das gefixt wird." Die Karte hat es ans Brain weitergegeben, weil hier gerade
keine Sitzung läuft.

**Gesucht, nicht geraten.** Der Foto-Weg nimmt PNG längst an, das steht so in `BILDARTEN`. Im
Protokoll des Dienstes stand die Antwort: Um 08:47 ging ein PNG über `/api/sessions/…/bild` mit 200
durch, um 08:48 scheiterte `/api/sessions/…/datei` mit 400. Roli hatte den Bildschirmausschnitt also
über „Dateien" ausgewählt statt über „Fotos", und am Handy liegt ein Screenshot nun einmal im
Dateimanager. Der Dokument-Weg prüft die Endung gegen eine Positivliste, in der `.png` nichts zu
suchen hat, und die zweite Chance erkannte nur Text und ZIP. Ein Bild ist beides nicht.

**Gebaut:** `_bild_erkannt()` sieht in die Datei und erkennt PNG, JPEG, GIF, WEBP und HEIC an ihrer
Signatur, nicht an der Endung. Der Dokument-Weg nimmt solche Dateien jetzt an und vergibt die
Endung selbst; für Bilder gilt dabei die Bild-Obergrenze von 20 MB statt der 30 MB für Dokumente.
An der Positivliste für Dokumente ändert sich nichts, und ausführbar wird hier weiterhin nichts:
Wir prüfen den Inhalt und schreiben die Endung selbst.

**Geprüft** an sechs echten Dateien aus dem Bilderordner und aus /tmp: PNG, JPEG und WEBP richtig
erkannt, eine Markdown-Datei wird nicht fälschlich als Bild gelesen. Dienst neu gestartet, antwortet
mit 200, keine Fehlerzeilen beim Start.

**Was bewusst offen bleibt:** Ein über den Dokument-Weg geschicktes Bild erscheint in der Oberfläche
als Dokument-Kachel, nicht als Bildvorschau, weil das Frontend die Art am Endpunkt festmacht
(`istBild = endpunkt === "bild"`). Der Anhang kommt an und Claude liest ihn; nur die Kachel sieht
anders aus. Wer das aufräumt, sollte die Art aus der Serverantwort übernehmen.

**Und ein Hinweis für die nächste Sitzung dieser Karte:** Es gibt fünf Sitzungen namens
„Hetzner-App", alle über Remote Control und seit über elf Tagen still. Meldungen an diese Karte
kommen derzeit nirgends an; sie laufen über das Brain.

## V168 (20.09.2026, nachts): Ordner-Wähler zeigt alle Projekte, nach echter Aktivität

Auslöser Roli, 00:29, zwei Screenshots vom Neue-Sitzung-Formular: „hier gibt's kein Skillradar".
Ursache: `/api/dirs` gab nur die 20 zuletzt geänderten Ordner zurück, gemessen an der Änderungszeit
des Ordners selbst. Die ändert sich nur, wenn direkt darin eine Datei entsteht oder verschwindet,
nicht bei Arbeit in Unterordnern. Skillsradar stand deshalb auf dem 6.09., und bei 42 Projekten fiel
es aus der Liste.

Lösung: Alle Ordner werden gezeigt, sortiert nach dem jüngsten von drei Zeitstempeln: Ordner,
Git-Index (jede Sicherung) und jüngste Claude-Mitschrift unter `~/.claude/projects/<kuerzel>`.
Geprüft mit dem Python des Dienstes: 42 Ordner, Skillsradar an dritter Stelle hinter Brain und
Koffer. Neustart über systemctl, `/api/version` zeigt 168. Lea und Lorenz bekommen den Stand über
ihre Aktualisierungs-Timer.

## V169 (20.09.2026): Token-Zahl im Kontext-Balken, Hinweis „neue Karte“ ab 150.000

Auslöser Roli, 20.09. 09:24 (Übergabe der Brain-Karte) und 09:40: Im Kopf soll nicht nur
„Kontext 15 %“ stehen, sondern auch, wie viele Token schon drinstecken, damit er VOR einer neuen
Aufgabe sieht, ob eine neue Karte fällig ist. Auf die Rückfrage „Kontext oder verbrauchte Last?“
nahm er meine Empfehlung: Kontext in Tausend Token.

Lösung: Nur Frontend, der Server lieferte `benutzt` schon. Der Balken zeigt jetzt zum Beispiel
„Kontext 84 % frei · 160k · neue Karte“. Ab 150.000 Token färbt sich die Füllung gelb und der Zusatz
„neue Karte“ erscheint, passend zur Token-Sparen-Regel vom 20.09. Der Grund: Der Balken misst gegen
eine Million Kontext und wäre bei 150k noch fast leer und grün, obwohl die Karte dann schon teuer
wird. Über 90 % bleibt es rot. Die Legende (Symbol-Erklärung) ist mitgezogen. VERSION 169.

Geprüft im echten Browser gegen den Testserver auf Port 8799, mit nachgestelltem `/kontext`:
84k zeigt „92 % frei · 84k“ grün, 160k zeigt „84 % frei · 160k · neue Karte“ gelb, 1,3M zeigt rot.
Keine Konsolenfehler, Text passt auf 400 Pixel Breite. Dienst neu gestartet, `/api/version` = 169.
Nicht geprüft: die Anzeige an einer echten Sitzung über 150k, nur mit nachgestellten Werten.

## V170 (20.09.2026): Kontext-Balken sagt „benutzt“

Auslöser Roli, 20.09. 11:02: „habe ich jetzt noch 63.000 Token oder wurden 63.000 verbraucht?“
Die Anzeige stand als „Kontext 84 % frei · 160k“, vorne die freie Menge, hinten die benutzte, ohne
Wort dazu. Er las die Zahl falsch herum. Jetzt steht „Kontext 84 % frei · 160k benutzt · neue Karte“.
Die Legende sagt ausdrücklich, dass es die benutzten Token sind und nicht die übrigen. Nur Frontend
und VERSION 170.

Geprüft im echten Browser gegen den Testserver auf Port 8799 (Anmeldung per
`dependency_overrides` ausgehängt, Startskript wegwerfbar in /tmp): 84k, 160k und 1,3M passen auf 400
Pixel Breite in eine Zeile, keine Konsolenfehler.


## V171 (20.09.2026): Vertrauensfrage immer beantworten, nie in offene Dialoge tippen, Balken nach Kartenwechsel

Auslöser Roli, 20.09. 16:43 und 16:58: Zwei Karten im Ordner Schmiede „existieren nicht“. Ursache
(Brain-Karte, 17:05): Der Ordner hatte nie eine Sitzung, Claude fragt beim ersten Start „Diesem
Ordner vertrauen?“, vorgewählt ist „No, exit“. Die App beantwortete die Frage nur, wenn beim Anlegen ein
erster Auftrag mitkam. Roli legte ohne Auftrag an und wechselte sofort das Modell; das Enter hinter
`/model` bestätigte „No, exit“, Claude beendete sich, die tmux-Sitzung war weg. Um 17:11 nahm Roli die
Empfehlung an, V171 zu bauen.

Lösung, Server: Neue Prüfung `_eingabe_bereit` in `server.py`. Sie wartet, bis Claude eine Eingabezeile
zeigt (bis 20 Sekunden), beantwortet die Vertrauensfrage mit Ja, drückt Escape-Dialoge weg und meldet
„frei“, „startet“, „anmeldung“ oder „blockiert“. Sie läuft (1) beim Anlegen ohne ersten Auftrag im
Hintergrund, (2) vor dem Modellwechsel, (3) vor dem Senden einer Nachricht. Bei „startet“ und
„blockiert“ gibt es eine ehrliche 409-Meldung statt eines verschluckten Textes. Die alten
Einzelzweige in `session_senden` gingen in die gemeinsame Prüfung auf.

Lösung, Frontend: Der Kontext-Balken hatte eine Zwölf-Sekunden-Sperre für alle Karten zusammen. Wer
innerhalb von zwölf Sekunden die Karte wechselte, sah keinen Balken (die Liste blendet ihn aus). Jetzt
merkt sich `kontextFuer` die Karte des letzten Abrufs, ein Kartenwechsel löst sofort einen neuen aus.
Dazu: Kommt die Antwort für eine Karte an, die inzwischen nicht mehr offen ist, wird sie verworfen.
VERSION 171.

Geprüft: (1) Echt in tmux, frischer Ordner ohne Vertrauens-Eintrag: `_eingabe_bereit` beantwortete die
Vertrauensfrage in 1,6 Sekunden, danach lief `modell_wechseln` durch („Set model to Sonnet 5“), die
Sitzung lebte. (2) Zweiter frischer Ordner: `session_senden` direkt nach dem Anlegen brauchte 3,2
Sekunden, die Nachricht kam bei Claude an, keine Sitzung starb. (3) Balken im echten Browser gegen
Testserver auf 8799 mit nachgestelltem `/kontext`, drei Karten hintereinander in unter zwei Sekunden:
alter Code zeigt ab der zweiten Karte keinen Balken (Fehler nachgestellt), neuer Code zeigt bei jeder
Karte den richtigen Wert; keine Konsolenfehler. Dienst neu gestartet, `/api/version` = 171.

Fehler unterwegs: Die Probe mit `/model sonnet` hat Claudes Standardmodell in `~/.claude/settings.json`
auf „sonnet“ gesetzt (das tut jeder Modellwechsel, auch der aus der App). Der Wert davor ließ sich nicht
mehr feststellen; die vorigen Brain-Karten liefen laut Mitschrift ebenfalls auf Sonnet 5. Künftige
Proben also ohne Modellwechsel machen oder den Wert danach zurücksetzen.
Nicht geprüft: der Weg über die echte Bedienung am Handy (nur der Server-Teil direkt aufgerufen).

## V172 (20.09.2026): Titel bei neuen Karten ist freiwillig

Auslöser Roli, 20.09. 17:25: „wenn ich eine neue Karte öffnen muss ich immer den Titel eingeben, das
nervt ein wenig“. Das Feld „Name“ war Pflicht, und Roli legt am Handy oft Karten an.

Lösung: Der Name ist freiwillig. Bleibt er leer, heißt die Karte wie ihr Ordner; ist der Name schon
vergeben (auch von einer schlafenden oder archivierten Karte), hängt die App eine 2, 3 … an.
Server: `NewSession.name` darf leer sein, neue Funktion `_standardname` in `server.py`, neue Funktion
`state.vergebene_namen`. Formular: `required` entfernt, das Platzhalter-Wort zeigt vorher, welcher Name
es wird („Leer lassen: „Brain““), und zieht mit, wenn man den Ordner wechselt oder ein neues Projekt
eintippt. Ein eingetippter Titel gilt wie bisher. VERSION 172. Keine Legende nötig, kein neuer Knopf.

Geprüft im echten Browser gegen einen Testserver auf Port 8799: Formular ohne Titel zweimal mit dem
Feld „Neues Projekt“ abgeschickt, es entstanden „v172probe“ und „v172probe 2“, beide Karten lebten
und zeigten keinen offenen Dialog (die Vertrauensfrage aus V171 wurde ohne ersten Auftrag beantwortet,
das ist damit auch über den echten Bedienweg belegt). Keine Konsolenfehler, keine Fehlerzeile.
Probe-Karten und Probe-Ordner danach gelöscht. Dienst neu gestartet, `/api/version` = 172.
Unterwegs: Zwei Aufräum-Befehle mit `pkill -f` und `awk` auf den eigenen Skriptnamen haben sich selbst
mitbeendet, weil der Skriptname in der eigenen Befehlszeile stand; Testserver künftig über den Port
finden.
Nicht geprüft: Anlegen am echten Handy.

## V173 (20.09.2026): Warnung am Modell-Knopf, wenn die Karte schon groß ist

Auslöser Roli, 20.09. 17:56, „ja und warnung“ (auf die Frage, ob der Modell-Knopf vor dem Wechsel bei
großen Karten warnen soll). Hintergrund aus der Skool-Lektion zu den Nutzungslimits: Der Zwischenspeicher
hängt am Modell, ein Modellwechsel mitten im Verlauf verarbeitet also den ganzen Verlauf neu.

Lösung: Das Modell-Blatt zeigt oben einen Hinweis mit Warnzeichen und Text („⚠ Achtung: Diese Karte ist
schon groß (128k benutzt) … Besser: eine neue Karte mit dem anderen Modell anfangen“), sobald die Karte
100.000 Token oder mehr benutzt (Konstante `MODELLWECHSEL_WARNUNG_AB` in `app.js`). Die Schwelle liegt
bewusst unter der 150.000er Grenze für „neue Karte“, weil das Neurechnen schon vorher teuer wird; sie ist
eine Setzung, kein Messwert. Die Zahl kommt vom Kontext-Balken (`kontextGroesse`, mit Kartenname, damit
nie die Zahl einer anderen Karte warnt). Der Wechsel bleibt möglich, es ist nur ein Hinweis. Symbol und
Text, nie nur eine Farbe (Rot-Grün-Schwäche). Neuer Absatz `#modell-warnung` in `index.html`, Stil in
`styles.css`. VERSION 173. Keine Legende nötig, kein neuer Knopf.

Geprüft im echten Browser gegen einen Testserver auf Port 8799 mit nachgestelltem `/kontext`: bei 128k
steht die Warnung im Blatt (Screenshot angesehen, Text passt auf 400 Pixel), bei 60k fehlt sie. Keine
Konsolenfehler. Testserver beendet, Dienst neu gestartet, `/api/version` = 173.
Nicht geprüft: am echten Handy und an einer echten Karte über 100k.

## V174 (20.09.2026): Kartenname darf Umlaute enthalten

Auslöser Roli, 20.09. 18:17, Foto vom Laptop (LEIT//PULS, Neue Sitzung, Name „Skills-Prüfung“, Browser-Meldung
„Deine Eingabe muss mit dem geforderten Format übereinstimmen“): „Ja, einbauen und sagen wieso das nicht geht“.

Ursache: Das Namensfeld erlaubte nur A–Z, a–z, 0–9, Punkt, Unterstrich, Bindestrich und Leerzeichen, im Formular
(`pattern` in `index.html`) und noch einmal im Server (`NewSession.name`, `server.py`). Das ü fiel durch. Die
Regel stammt aus der Anfangszeit und war eine vorsichtige Vorsichtsmaßnahme, kein technischer Zwang: Geprüft mit
tmux 3.6 auf einem eigenen Testsocket, ein Sitzungsname mit ü bleibt unverändert, auch mit LANG=C; der
Dienst läuft mit en_US.UTF-8. Die Namen gehen nirgends durch eine Shell (tmux-Aufrufe als Liste, Zustandsdatei
als JSON, Adressen mit encodeURIComponent).

Lösung: Erlaubt sind jetzt Buchstaben und Ziffern aller Schriften (`\p{L}`, `\p{N}`), dazu Punkt, Unterstrich,
Bindestrich und Leerzeichen. Weiter gesperrt: Schrägstrich, Semikolon, Dollarzeichen, Zeilenumbruch und alle
anderen Sonderzeichen. Der Standardname aus dem Ordner (V172) behält jetzt auch Umlaute (`\w` statt A–Z).
Das Feld „NEUES Projekt“ (Ordnername) bleibt bewusst nur ASCII, das ist eine andere Entscheidung (Ordner auf
der Platte). VERSION 174.

Geprüft im echten Browser gegen einen Testserver auf Port 8799: „Skills-Prüfung“ ist gültig, „Skills/Prüfung“
bleibt ungültig, Karte wurde angelegt (tmux-Sitzung „hz-Skills-Prüfung“, Zustand idle), Kontext- und
Verlauf-Abruf liefern 200, keine Konsolenfehler. Pydantic-Muster einzeln geprüft (ü, ß, chinesische Zeichen ok;
Schrägstrich, Semikolon, Dollar, Zeilenumbruch abgelehnt). Probe-Karte und Probe-Ordner gelöscht,
Testserver beendet, Dienst neu gestartet, `/api/version` = 174.
Nicht geprüft: am echten Handy und Laptop; Karten mit Umlaut über Schlafen und Aufwecken.

## V175 (23.09.2026): Verbrauch je Karte wird beim Archivieren dauerhaft festgehalten

Auslöser Roli, 23.09. 08:47–09:13: Er wollte Modell und Token-Verbrauch je Karte über
die Zeit vergleichen können (Opus 5.5 gegen die anderen), um am Ende zu entscheiden, ob
sich die „neue Karte"-Schwelle anheben lässt. Beim Nachsehen stellte sich heraus: Das
Verbrauchs-Blatt (`verbrauch.py`) zeigt nur den Live-Stand, nichts wird gespeichert —
ein früherer Beschluss zum Vergleichen wäre also ins Leere gelaufen. Roli deutlich
verärgert darüber, dass das erst jetzt auffiel: „bitte auf jeden Fall speichern […] das
war damals ja der Beschluss".

Lösung: Neue Funktion `verbrauch.protokolliere(karte, cwd)` liest den aktuellen
Kontext-Stand (Modell, benutzte Token, Limit) und hängt ihn als eine Zeile an
`~/.hetzner-app/verbrauch-verlauf.jsonl` an (JSON Lines, reine Anhänge-Datei, wie
`speicher.py` es für die Speicher-Ampel vormacht). Aufgerufen wird sie in
`patch_session` (`server.py`), genau in dem Moment, in dem `archiviert` erstmals auf
`true` wechselt — das ist der Punkt, an dem der Verbrauch einer Karte feststeht und sich
mit anderen vergleichen lässt. Erneutes Archivieren derselben Karte schreibt keinen
zweiten Datenpunkt (Bedingung `not vorher.archiviert`). Scheitert das Schreiben (Platte
voll o. ä.), bricht das Archivieren trotzdem nicht ab — der Verlauf ist ein Bonus, kein
Pflichtteil. VERSION 175.

Geprüft: `verbrauch.protokolliere()` direkt gegen den echten Ordner dieser Brain-Karte
aufgerufen, lieferte einen korrekten Eintrag (Modell, Token, Limit), danach wieder
entfernt. `py_compile` über beide geänderten Dateien fehlerfrei. Dienst neu gestartet,
`/api/version` = 175, läuft.
Nicht geprüft: eine echte Karte über die App-Oberfläche archiviert und die Datei danach
angesehen; Auswertung/Anzeige der gesammelten Daten (noch kein eigenes Werkzeug dafür,
nur die Ablage).

## V176 (23.09.2026): Karte direkt aus der Eingabezeile ins Archiv

Auslöser Roli, 23.09. 08:11: „ich hätte gern die Möglichkeit, dass ich das gleich ins
Archiv lege, ohne es vorher schlafen zu legen, wenn das technisch geht", dazu der Wunsch,
den Archiv-Knopf nicht zwischen die anderen Knöpfe zu setzen, sondern „direkt neben der
Textzeile". Um 19:00 bestätigt: gemeint ist die Eingabezeile in der geöffneten Karte.

Lösung: Neuer Endpunkt `POST /api/sessions/{name}/archivieren` in `server.py`. Ist die
Karte wach, legt er sie selbst schlafen (der Schlaf-Teil steckt jetzt in der gemeinsamen
Hilfsfunktion `_einschlafen`, die auch `/schlafen` nutzt, samt Sperre „Claude arbeitet
gerade"), hält dann wie beim Kisten-Knopf den Verbrauch fest (`verbrauch.protokolliere`,
nur beim ersten Archivieren) und setzt `archiviert`. Fremde Sitzungen bekommen 403. In der
Oberfläche sitzt eine Kiste (`#knopf-archivieren`) in der Eingabezeile rechts neben dem
Modell-Knopf, mit Rückfrage; danach geht es zurück zur Liste. Bei fremden Sitzungen ist
sie ausgeblendet. Die Kiste auf den Karten der Liste bleibt wie bisher für schlafende und
abgestürzte Karten und zum Zurückholen. Legende ergänzt. VERSION 176.

Geprüft im echten Browser (Chromium, 360 Pixel breit, Testanmeldung danach wieder
entwertet): Probe-Karte in /tmp/probe-archiv angelegt, geöffnet, Kiste sichtbar und
84 Pixel links vom Senden-Knopf, Rückfrage erscheint, danach Zustand „sleeping" und
archiviert, tmux-Sitzung weg, keine Konsolenfehler. Probe-Karte gelöscht.
Unterwegs: Die Einführungs-Tour lag im frischen Testbrowser über allem; im Test per
localStorage als gesehen markiert.
Nicht geprüft: am echten Handy; Verbrauchseintrag über diesen Weg (die Probe-Karte hatte
kein Gespräch, daher kein Datenpunkt).

## Sicherung (23.09.2026): Wächter erinnert täglich, solange GitHub klemmt

Anlass: Roli fragte, ob alles bei GitHub liegt. Es lag nicht: Brain wurde seit 13.09. bei
jedem Lauf abgewiesen, Einzelstein-Webseite seit rund 27 Tagen, Diktatwerk Windows & Chrome,
KI WIKI, KRUGMEISTER_MARKETING und Klartext- seit rund fünf Wochen (Zähler in
`~/.hetzner-app/sicherung-fehler/`). Ursache jeweils: auf GitHub liegt ein Stand, den der
Server nicht hat, der Push wird als nicht vorspulbar abgelehnt. Der Wächter in
`scripts/auto-sichern.sh` hat nur ein einziges Mal gewarnt, beim dritten Fehlschlag, und
danach geschwiegen.

Geändert: Nach der ersten Warnung erinnert er alle 144 Läufe erneut (bei zehn Minuten Takt
einmal am Tag), mit Anzahl der Läufe und ungefähren Tagen. Zusätzlich schreibt er eine
Warnzeile ins gemeinsame Ereignis-Log (`~/.ereignis.sh`, Stufe warn), damit es auch im
Leitstand sichtbar ist und nicht nur als Push, der untergehen kann.

Geprüft: `bash -n` sauber; Bedingung mit Beispielzahlen durchgerechnet (warnt bei 3, 147,
291, nicht bei 2, 4, 146, 148). Nicht geprüft: echte Push-Zustellung (würde Roli eine
Probe-Nachricht schicken). Die sechs klemmenden Projekte werden getrennt zusammengeführt.
Weiterhin nicht abgedeckt: Projekte ganz ohne GitHub-Anbindung meldet der Wächter nicht.

Nachtrag am selben Abend: Vier der sechs Projekte (Diktatwerk Windows & Chrome, KI WIKI,
KRUGMEISTER_MARKETING, Klartext-) waren gar nicht gefährdet. GitHub war nur weiter, weil am
Laptop gearbeitet wurde; der Server hatte nichts, was dort fehlte. Der Push wird trotzdem
abgelehnt, und der Wächter zählte das als Fehlschlag. Jetzt holt er nach einem abgelehnten
Push den GitHub-Stand und prüft, ob der Server-Stand darin schon enthalten ist. Dann meldet
er „GitHub ist weiter als der Server" und setzt den Zähler zurück. Nachgezogen wird bewusst
nicht automatisch, damit sich keine Dateien unter einer laufenden Karte ändern.
Geprüft mit einem echten Lauf: GOOGLE ADS-PULS fiel in den harmlosen Fall, Zähler weg;
übrig bleibt nur Einzelstein-Webseite, die wirklich auseinandergelaufen ist (Server-Stand
liegt vorläufig als Zweig `server-stand` bei GitHub).
