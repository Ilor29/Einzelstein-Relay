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

## 27.09.2026: Befehle mit / und ! kommen ohne Uhrzeit an (Version 177)

**Auslöser:** Roli schickte „/doctor" aus der Lese-Ansicht, Claude bekam „[27.09. 08:46] /doctor" als
normalen Text. Roli, 08:48: „wäre da nicht auch sinnig, dass ich sowas in der Relay-App eintragen kann".
Ursache: `sendeInSitzung` in `web/app.js` stellt jeder Nachricht still die Uhrzeit voran; Claude Code
erkennt Befehle aber nur, wenn Schrägstrich oder Ausrufezeichen ganz vorne stehen. Seit 27.08. zweimal
beobachtet (Gedächtnis „schraegstrich-befehle-kommen-als-text").

**Wie gelöst:** Neben der Ausnahme für Anmelde-Codes eine zweite: `istBefehl = /^\s*(\/[a-z]|!\s*\S)/i`.
Trifft sie, geht der Text ohne Uhrzeit (und ohne führende Leerzeichen) raus. Absichtlich nicht erfasst:
„/ doctor", „/12 Uhr", ein einzelnes „!". Befehle mit Auswahlmenü (/doctor, /model) zeigen ihr Menü nur in
der Terminal-Ansicht vollständig.

**Geprüft:** Testserver 8799, Senden per Playwright abgefangen: „/doctor" und „! ls -la" unverändert,
„Ganz normaler Satz" mit Uhrzeit, keine Konsolenfehler. Ausgerollt, `/api/version` = 177.

### 28.09.2026 11:26 — Speicher-Ampel: voller Swap allein ist kein Rot mehr (Brain 12)
Auslöser (Roli): „ich hatte ja vorher gar nichts im Swap … wieso taucht es rot auf also bitte noch mal kontrollieren überprüfen"
und vorher „die saugt sehr am speichern" über die Pachmayr-Karte.

Befund: Laut sar war der Swap bis 10:40 leer. Zwischen 10:42 und 10:53 hat die Pachmayr-Karte für die Sortier-Probe
zwei Sprachmodelle (Qwen3.5 4B und 9B, llama.cpp auf der CPU) geladen, das hat rund 3,9 GB in den Swap verdrängt.
Die Modelle waren danach beendet, der Swap blieb aber voll, und die Ampel stand bei 22 GB verfügbarem Speicher auf Rot.
Die Zeile „am dicksten: PACHMAYR (337 MB)" nannte nur die größte Karte, nicht den Verursacher, und hielt so die
Pachmayr-Karte für schuld, obwohl sie nur ein paar MB größer war als die anderen.

Lösung: Swap per `sudo swapoff -a && sudo swapon -a` zurück in den Arbeitsspeicher geholt (danach 0 MB Swap, 18 GB
verfügbar). In `hetzner_app/speicher.py` zählt der Swap-Anteil jetzt nur, wenn zugleich wenig Speicher verfügbar
ist (Rot: Swap über 85 % und unter 2000 MB verfügbar; Gelb: über 60 % und unter 4000 MB). Neu `groesstes_programm()`:
das größte Programm auf dem ganzen Server, mit Projektname statt „python". Push-Text und Anzeige (`web/app.js`)
nennen bei Rot zuerst das größte Programm, dann die größte Karte.

Geprüft: ampel() mit den Zahlen vom Bild (22 GB frei, 86 % Swap) ergibt grün, 1,5 GB frei mit vollem Swap rot,
300 MB frei rot; lauf() schreibt grün. Die app.js-Änderung wirkt erst nach dem nächsten Neustart des App-Dienstes
(Versionsnummer), bewusst nicht neu gestartet, um laufende Karten nicht zu stören.

## 29.09.2026 · CODE//GUARD 1.3: Prüfrunden je Angriffsart und Gegenprüfung (Brain-Karte 16)

Auslöser: Roli 29.09. 10:00 „Code upgrade ja, bitte skillradar karte mitgeben damit es auf der webseite upgeradet
werden kann“, 15:17 „Ja, loslegen“. Idee aus dem Cloudflare-Beitrag „Build your own vulnerability harness“
(Code dort nicht veröffentlicht, nur das Vorgehen übernommen).

Lösung: Stammfassung `deploy/skills/code-guard` auf Version 1.3. Neue Referenz `references/angriffsrunden.md`:
erst eine Landkarte (Eingänge, Senken, Vertrauensgrenzen, Geheimnisse), dann sieben Runden R1–R7 (Injection,
Zugriff, Geheimnisse, Uploads, Anfragen nach außen, KI-Anbindung, Logik), bei mittleren Projekten als parallele
Unteragenten. Jeder Fund braucht einen Angriffsweg mit Datei:Zeile, sonst kein Rot oder Orange. Jeder rote und
orange Verdacht geht vor dem Bericht an einen unabhängigen Gegenprüfer, der nur die Behauptung kennt und sie zu
widerlegen versucht. Bericht hat neue Blöcke „Prüfrunden“ und „Verworfene Verdachtsfälle“, Ampel zählt nur
Gegengeprüftes. Installiert per `scripts/skills-installieren.sh`; Lea und Lorenz bekommen es mit dem nächsten
Selbst-Update.

Geprüft: Probelauf an CONTO (Server-Grundgerüst). Fünf Runden, vier Orange-Verdachtsfälle, davon einer bestätigt
(andere Konten umgehen die Anmeldung über 127.0.0.1), drei auf Gelb abgeschwächt, einer davon mit falschen
Zeilennummern der Runde, die der Gegenprüfer berichtigt hat. Bericht: `~/projekte/CONTO/doku/CODEGUARD-v1.0-2026-09-29.md`.

Fehler unterwegs, als Lehre in die Anleitung übernommen: Die Zugriffsrunde konnte das Caddyfile nicht lesen
(braucht sudo) und hat deshalb geraten; jetzt gibt die Hauptprüfung solche Auszüge wörtlich in die Landkarte.
Zwei Runden widersprachen sich beim Formular-Schutz; solche Widersprüche gehen jetzt ausdrücklich in die
Gegenprüfung.

## V178 (10.10.2026): Cache-Wärme im Kontext-Balken und im Verbrauchs-Blatt (Brain-Karte 23)

Auslöser Roli, 10.10. 16:40: „Können wir in der Relay-App oder in der Leitzentrale den Cache
sehen? Wie viel Zeit ist da noch, wann läuft das ab, damit man Token sparen kann oder dass man
eine Übergabe macht.“ Vorbild waren die Mods „cache-tax“ und „keepwarm“ von Julian Ivanov; der
Sperr-Mechanismus (Eingabe blockieren) wurde bewusst weggelassen, hier wird nur angezeigt und gewarnt.

Hintergrund: Anthropic hält den unveränderten Verlauf als Prompt-Cache vor. Trifft ein Zug den
Speicher, kosten diese Token ein Zehntel; ist er abgelaufen, wird alles neu angelegt (1,25-fach),
also rund das Zwölffache eines warmen Zuges. Jeder Zug erneuert die Lebensdauer. Vorfrage „5 Minuten
oder 1 Stunde“ aus der Mitschrift beantwortet: Jede Abrechnung trägt `cache_creation` mit
`ephemeral_1h_input_tokens` oder `ephemeral_5m_input_tokens`; Zählung über alle Mitschriften am
10.10.: 114.000 Einträge mit 1 h, 46 mit 5 min. Die Lebensdauer wird je Karte aus der Abrechnung
gelesen, Annahme 1 h nur, wenn die letzten 40 Züge reine Lese-Züge waren.

Lösung: `verbrauch._kontext_lesen` liest zusätzlich den jüngsten Zug der Hauptunterhaltung (Frage
oder Antwort, ohne Unteragenten) und die Lebensdauer; `kontext()` liefert dazu `cache` mit `ttl_s`,
`zuletzt`, `warm_bis`, und bei jedem Aufruf frisch `rest_s`, `warm`, `kalt_seit_s` (die Mitschrift
bleibt zwischengespeichert, nur die Restzeit wird neu gerechnet). Der Balken zeigt „Cache warm
42 min“ oder „Cache kalt“, bei kalt und über 100.000 Token „⚠ Cache kalt, Neuaufbau teuer“. Im
Verbrauchs-Blatt eine Zeile „Cache-Wärme“ mit Balken (wie viel der Lebensdauer um ist) und einem
Satz dazu; bei kalt und groß der Rat, Übergabe zu schreiben und eine neue Karte zu öffnen. Keine
Preise in Dollar, nur der Faktor, weil Preise je Modell anders sind.

Fehler unterwegs: Der längere Text verschluckte den Balken (auf 430 Pixel blieb ein Stummel). Jetzt
hat die Schiene eine Mindestbreite und der Text darf in zwei Zeilen umbrechen.

Geprüft: Mit dem Python des Dienstes an allen laufenden Karten (warm mit Restzeit, PACHMAYR 10 kalt
seit 32 h). Im echten Browser gegen den Testserver 8799 (Anmeldung per dependency_overrides
ausgehängt, Startskript in /tmp): Brain 23 „Cache warm 60 min“, PACHMAYR 10 Warnung, Blatt mit
Hinweistext, keine Konsolenfehler, Screenshots angesehen. Dienst neu gestartet, `/api/version` 178.
Derselbe Leser versorgt den LEIT//PULS (leitstand/lage-messen.py importiert `hetzner_app.verbrauch`).
Nicht geprüft: am echten Handy. Bekannte Grenze: Karten im selben Ordner (Skillsradar 15/17/20)
teilen sich die jüngste Mitschrift, wie schon beim Kontext-Füllstand.

## V179 (10.10.2026): Kontext-Balken in zwei Zeilen, Modus-Zeile weg bei offener Tastatur (Brain 23)

Auslöser Roli, 10.10. 17:09 mit zwei Handybildern: „Aufteilung besser machen“ (der Cache-Text brach
in zwei Zeilen um und ließ vom Balken einen Stummel) und 17:11 „1. Deine Empfehlung 2. Ja. Das alles
so viel frisst, wenn ich was eintippen muss“.

Lösung: Der Balken läuft dünn über die ganze Breite, darunter eine Zeile mit links „Kontext 81 %
frei · 187k benutzt“ und rechts „Cache warm 48 min“ (eigenes Element `cache-text`; bei kalt und groß
orange und fett mit Warnzeichen, Text bleibt, wegen Rot-Grün-Schwäche nie nur Farbe). Dazu die
Tastatur-Messung aus dem LEIT//PULS übernommen (sichtbare Höhe gegen die größte je gemessene,
unter drei Viertel heißt Tastatur offen, `body.eng`); dann verschwindet die Modus-Zeile.
Geprüft im Browser gegen Testserver 8799: Medienwerk 75 warm, PACHMAYR 10 Warnung, Balken voll
breit, Tastatur-Modus per Klasse nachgestellt, keine Konsolenfehler. Nicht geprüft: am echten Handy.

## V180 (10.10.2026): Schnellwahl unter nummerierten Fragen, Knopf „Übergabe vorbereiten“ (Brain 23)

Auslöser Roli, 10.10. 18:44: „bei Nummer 20 ja bitte Übergabe vorbereiten“ und „wenn jetzt eine Zahl kommt … eine Schnellwahltaste, wo ich dann einfach nur sagen kann ja, nein, deine Empfehlung, bevor ich jedes Mal was tippen muss“.

Lösung: (1) Unter der jüngsten Claude-Antwort erscheint für jede Zeile „N. … ?“ (Nummer, Ende mit Fragezeichen) eine Reihe Ja / Nein / Empfehlung. Ein Tipp schreibt „N. Ja“ ins Eingabefeld (sortiert nach Nummer, zweiter Tipp nimmt zurück, Haken ✓ zusätzlich zur Farbe), gesendet wird erst mit dem Pfeil. Bei mehreren Fragen dazu „Überall: deine Empfehlung“. Ältere Antworten zeigen keine Tasten (MutationObserver setzt Klasse `juengste`). (2) Im Verbrauchs-Blatt ab 100.000 Token oder bei kaltem Cache ein Knopf „Übergabe vorbereiten“; nach Rückfrage geht ein fester Auftrag an die Karte (Stein zu Ende, Baubuch, Register, UEBERGABE.md, Satz „Übergabe lesen“ als Codeblock). (3) Regel in der globalen Anleitung und im Gedächtnis: jede Frage an Roli trägt meine Empfehlung.

Geprüft im Browser gegen Testserver 8799: Tasten unter der 20, „20. Ja“ im Feld, Wechsel auf Empfehlung ersetzt statt anzuhängen, Blatt zeigt Knopf, Rückfrage erscheint (im Test abgebrochen, nichts gesendet). Schönheitsfehler: die Tasten stehen nur, wenn die jüngste Antwort die Fragen enthält; schreibt eine Karte nach der Frage noch einen Satz, sind sie weg. Nicht geprüft: am echten Handy.

## V181 (10.10.2026): Schnellwahl erkennt Fragen mit Empfehlung dahinter, bleibt unter den letzten drei Antworten
Auslöser Roli, 10.10. 18:52 (zwei Handybilder): „Da kommen keine Boxen“. Ursache: Die Erkennung verlangte ein Fragezeichen am Zeilenende, meine Fragen führen aber die Empfehlung im selben Absatz weiter („8. Soll ich …? … Meine Empfehlung: Ja.“). Jetzt reicht ein Fragezeichen irgendwo in der nummerierten Zeile. Zweitens verschwanden die Tasten, sobald die nächste Antwort keine Frage enthielt; jetzt stehen sie unter der jüngsten Antwort mit Fragen, solange sie unter den letzten drei liegt. Lehre: gegen den echten Verlauf prüfen, nicht gegen eine selbst gebaute Probe. Im Browser gegen den echten Verlauf der Karte geprüft (vier Fragen, „Überall: deine Empfehlung“, einzelne Änderung, Feldinhalt stimmt). Regelzeile in der globalen Anleitung angepasst („enthalten ein Fragezeichen“).

## V182 (10.10.2026): Schnellwahl direkt unter jeder Frage (Brain 24)
Auslöser Roli, 10.10. 19:05 „Wäre es nicht sinniger direkt unter der Frage die Antworten?“, bestätigt 20:12 „32. Ja“.
Lösung: `schreibeMitWahl` in web/app.js zerlegt die Antwort an den Fragezeilen („N. … ?“, nicht in Code-Blöcken) und setzt unter jede Frage eine Reihe Ja / Nein / Empfehlung. Der Tipp trägt „N. Ja“ ins Eingabefeld ein, wie bisher (`waehle`). Bei mehr als einer Frage bleibt „Überall: deine Empfehlung“ am Ende der Antwort. Sichtbar nur in der jüngsten Antwort mit Fragen (unter den letzten drei), CSS vereinfacht.
Geprüft im Browser gegen Testserver 8799 (Anmeldung ausgehängt, Testserver per gemerkter PID beendet): zwei Fragen, Frage im Code-Block bekommt keine Tasten, Haken auf der gewählten Taste, „Überall“ füllt beide Zeilen, keine Konsolenfehler, Screenshot angesehen. Nicht geprüft: am echten Handy.

## V183 (10.10.2026): Entscheidungskorb oben in der Kartenliste (Brain 24)
Auslöser Roli, 10.10. 21:44 „wo soll der Korb sein“, Vorschlag Relay, bestätigt 22:20 „37. Ja“.
Lösung: neues Modul `hetzner_app/korb.py` liest `Brain/korb/fragen.json` (Pfad per HETZNER_APP_KORB änderbar) und hält Antworten mit Sperre fest. Endpunkte `GET /api/korb` und `POST /api/korb/{id}/antwort` (ja, nein, empfehlung). Die Antwort geht sofort per `session_senden` in die Karte, die gefragt hat, wenn eine Relay-Karte genauso heißt wie das Feld „karte“ im Korb (Anzeigename oder Kennung, ohne Groß/Klein). Sonst oder bei Fehler (Karte beschäftigt) bleibt sie auf „beantwortet“, das Brain gibt sie mit `korb.py zustellen` weiter. Oben in der Liste steht der Kasten „Entscheidungskorb“ mit Karte, Frage, Hintergrund, Vorschlag und den Tasten Ja, Nein, Empfehlung. Ein Tipp sendet sofort, es gibt kein Zurück.
Geprüft: Browser gegen Testserver 8799 mit Probe-Korb in /tmp (Anmeldung ausgehängt, Versand durch Attrappe ersetzt, damit keine echte Karte eine Nachricht bekommt): Kasten oben, Tipp auf Nein stellt zu, Status wechselt auf zugestellt, zweite Antwort auf dieselbe Frage 404, Karte ohne Gegenstück bleibt „beantwortet“, Karte beschäftigt fällt zurück. Nicht geprüft: echter Versand in eine laufende Karte, Handy.
Regel für Karten: Feld „karte“ so schreiben, wie die Karte in der Relay heißt (z. B. „Medienwerk 77“).

## V184 (11.10.2026): Helle Fassung, wenn der LEIT//PULS hell ist (Brain 28)
Auslöser Roli, 11.10. 21:07 „Es bleibt in der Mitte trotz Umstellung dunkel“ (Screenshot der eingebetteten Relay im hellen LEIT//PULS), bestätigt 23:48 „57. Ja, 58. Ja, 59. Ja“.
Lösung: `:root.hell` in web/styles.css mit den Farben des hellen LEIT//PULS (Grund #F5F6FA, Flächen weiß, Schrift Navy #14182B, Akzent Rost #B5541D, Statusfarben dunkler für Kontrast auf Weiß); dazu die eingeschaltete Glocke, die sonst fest Hellorange war. Die Klasse setzt die neue Datei web/farbe.js im Kopf, bevor etwas gezeichnet wird: Sie liest `?farbe=hell|dunkel` aus der Adresse und merkt es für den Reiter in sessionStorage. Nur eingebettet (window.parent ≠ window), allein geöffnet bleibt die Relay dunkel, auch für Lea und Lorenz. Wechselt Roli im LEIT//PULS, schickt der eine Nachricht `{tu:"farbe", wert}`; app.js nimmt sie im vorhandenen Leitstand-Empfänger an (gleiche Herkunftsprüfung wie beim Schlafenlegen).
Fehler unterwegs: Zuerst stand der Schalter als zweites Inline-Skript in index.html. Die CSP erlaubt nur ein Inline-Skript (die Notbremse, Hash wird beim Start aus der Datei gerechnet), der Browser blockte es. Deshalb eigene Datei farbe.js von der eigenen Herkunft.
Geprüft: Testserver 8799 (Anmeldung ausgehängt, per gemerkter PID beendet), Klasse im Browser gesetzt: Liste und geöffnete Karte hell, gut lesbar, keine Konsolenfehler. Einbetten in eine fremde Probeseite verbietet der Testserver (frame-ancestors), deshalb Weitergabe im LEIT//PULS getrennt geprüft. Nicht geprüft: das echte Zusammenspiel im angemeldeten LEIT//PULS und am Handy.

## V185 (12.10.2026): Ton-Kontext schläft nach dem Vortrag (Brain 28)
Auslöser Roli, 12.10. 00:10: hoher Stromverbrauch am Handy, im Akku läuft alles über Chrome; bestätigt 00:45 „65. Ja“.
Befund vorher: Die Abfragen sind es nicht. Das Server-Protokoll zeigt vom Handy zwischen 02 und 08 Uhr keine einzige Anfrage, tagsüber wenige hundert je Stunde; der Akku-Stein vom 22.08. wirkt. Verdacht: Der Ton-Kontext (hörCtx) wird bei jedem Tipp auf einen Lautsprecher-Knopf geweckt, auch auf Android, und danach nie wieder angehalten. stille() stoppte nur Quellen, Dauerton und Strom. Ein laufender Kontext hält die Ton-Leitung offen. Beweis steht aus, Roli schaut in den Akku-Einstellungen nach Vorder- und Hintergrund-Anteil von Chrome.
Lösung: `tonSchlafenLegen()` am Ende von stille(): nach zehn Sekunden hörCtx.suspend(), aber nicht bei Freisprech (Auto, nächster Vortrag ohne Tipp bei dunklem Bildschirm), offenem Mikrofon, Rest nach Anruf oder Hand-Pause. Geweckt wird wie bisher im Tipp (synchrones resume) und in sprichHaeppchen. Tagebuch-Ereignis „kontext-schlafen“.
Geprüft: Testserver 8799 in Chromium: Kontext läuft, nach stille() nach 5 s noch an, nach 11 s „suspended“, wieder weckbar, mit Freisprech bleibt er an, keine Konsolenfehler. Nicht geprüft: echtes Vorlesen am Handy und ob der Akku tatsächlich länger hält.
Nachtrag 12.10.: Roli bestätigt, das Vorlesen mit V185 klappt am Handy und am Rechner (Roli 10:04 „sowohl am Handy als auch auf dem Computer“).
Nachtrag 12.10. 01:09, Rolis Akku-Screenshot (Xiaomi, 14 Std. aktiv, Stand vor V185 über den Tag): Chrome 40,49 Prozent des Akkus. CPU gesamt 57 Min 5 Sek, davon im Vordergrund nur 6 Min 30 Sek, also rund 50 Minuten Rechenzeit im Hintergrund. Aktiv lassen (Wakelock) 7 Sek, mobile Daten 37 MB gesendet, 264 MB erhalten. Energiesparmodus für Chrome: „Keine Beschränkungen“. Deutung: Der Verbrauch kommt überwiegend aus dem Hintergrund, nicht vom Bildschirm; das passt zum dauerhaft laufenden Ton-Kontext (sein Ton-Faden rechnet auch bei Stille). Vergleich: nach einem Tag mit V185 dieselbe Seite noch einmal ansehen.

## 12.10.2026 (Brain 29): Mockup breite Relay am Rechner

Auslöser: Roli 12.10. 01:20 „rechts links ist auf jeden Fall Platz, da paar Sachen noch reinzunehmen“, beschlossen 01:36 „70. Ja, 71. Ja, 72. Ja“, Start 09:46 „73. Ja“.
Entwurf unter ~/seiten/relay-breit/index.html: links dauerhaft die Kartenliste (300 px), Mitte das Gespräch mit Lesespalte bis 760 px, rechts „Zur Hand“ mit offenen Fragen der Karte (Ja, Nein, Empfehlung), Entscheidungskorb und Kontext, Cache, Modell. Farben aus styles.css, hell und dunkel per Knopf oben. Unter 1180 px fällt die rechte Spalte weg, unter 760 px die linke (dann wie Handy). Statuszeichen immer mit Text, nicht nur Farbe.
Geprüft: Chromium 1600 und 1100 px, hell und dunkel, keine Konsolenfehler; ein schief sitzendes Schildchen in der Kartenliste gefunden und behoben. Echte Relay noch nicht angefasst, wartet auf Rolis Urteil.

## 12.10.2026 (Brain 29): V186, drei Spalten am breiten Rechner

Auslöser: Roli 12.10. 01:20 (Foto vom Rechner) „rechts links ist auf jeden Fall Platz, da paar Sachen noch reinzunehmen“, Mockup ~/seiten/relay-breit abgenommen 10:04 „78. Ja“.
Lösung: Keine zweite Oberfläche. `zeige("sitzung")` lässt ab 1280 px (`BREIT`, matchMedia) die Listen-Ansicht sichtbar und setzt body.drei-spalten; CSS stellt die Liste links auf 320 px, die Sitzung dazwischen (Lesespalte 860 px), rechts das neue `<aside id="zur-hand">`. Der Listen-Takt läuft in der breiten Ansicht weiter (`listeOffen` bleibt an). `oeffneSitzung` räumt beim direkten Kartenwechsel auf, was sonst der Zurück-Knopf tut (Steckdose zu, alte Karte gesehen). Zur Hand: offene Fragen aus der `.antwort.juengste` (jede Wahlreihe trägt jetzt ihre Fragezeile als data-frage), mit denselben Tasten; `waehle` setzt den Haken jetzt überall im Dokument, so stimmen Verlauf und Spalte überein. Korb kommt aus `ladeListe` (`zurHandKorb`), links ausgeblendet. Kontext, Cache, Modell werden per MutationObserver aus der Mitte mitgelesen, der Balken in der Mitte ist ausgeblendet; Klick öffnet das Verbrauchs-Blatt. Fenster schmaler gezogen: zurück zur Einzelansicht.
Fehler unterwegs: „Sitzungen“ wurde in der schmalen Spalte zu „S…“ gequetscht und das Zahnrad angeschnitten (Knöpfe enger, Wort „verbunden“ ausgeblendet, Punkt bleibt); „Kontext“ stand rechts doppelt (Vorsilbe abgeschnitten).
Geprüft: Testserver 8799 in Chromium bei 1600 px dunkel und hell, Taste rechts füllt „78. Ja“ ins Feld und setzt den Haken auch im Verlauf, zweiter Tipp nimmt es zurück; Wechsel Brain 29 → Medienwerk 84 → zurück mit richtiger Markierung und deren Fragen; 1100 px fällt auf eine Ansicht zurück und wieder breit; Handy 390 px unverändert; keine Seitenfehler. Nicht geprüft: am echten Rechner mit Anmeldung, Korb mit echter Frage, eingebettet im LEIT//PULS (dort ist die Relay meist schmaler als 1280 px, dann bleibt sie einspaltig).

Nachtrag 12.10.2026 19:10 (Brain 30), Vergleich Chrome-Akku nach V185: Rolis Screenshot 19:08 zeigt Chrome 37,67 Prozent bei 8 Std. 14 Min. aktiv, CPU gesamt 59:09, Vordergrund 5:28, Aktiv lassen 9:21, Daten 45 MB gesendet und 138 MB erhalten. Vorher (01:09): 40,49 Prozent bei 14 Std., CPU 57:05, Vordergrund 6:30, Aktiv lassen 7 s, 37 und 264 MB. Keine klare Besserung, die Zeiträume sind nicht gleich lang. Relay-Code durchgesehen: Takte ruhen bei document.hidden, der 3-Sekunden-Takt pruefeObTonZurueck ist billig, keine Wach-Sperre vorhanden, deshalb nichts geändert. Aktiv lassen passt zu Vorlesen mit Ton, nicht belegt. Offen: ob die Relay als App oder Tab läuft und welche anderen Seiten in Chrome offen sind (Roli).

## 13.10.2026 (Brain 30): V187, eigene Antwort unter jeder nummerierten Frage
Auslöser Roli, 13.10. 11:47: „entweder ich habe die Möglichkeit direkt unter der Frage eine eigene Antwort einzugeben … weil es gibt ja nur ja nein … und dann bitte für alle Karten nachziehen“, bestätigt 12:01 „2 bitte“.
Lösung in web/app.js: `baueWahlReihe` bekommt eine vierte Taste „Eigene Antwort“, die ein Textfeld unter der Frage aufklappt (Tippen oder Diktat der Handy-Tastatur). Der Text wird als „N. <Text>“ ins Eingabefeld geschrieben, sortiert nach Nummer, gesendet wird mit dem Senden-Pfeil wie bei den Tasten. Leeres Feld nimmt die Zeile zurück; eine Taste ersetzt den eigenen Text; nach dem Senden leert sich das Feld (`eigeneAntwortenAbgleichen`). Wirkt im Verlauf und in „Zur Hand“, weil beide `baueWahlReihe` nutzen, und damit auf allen Karten. Stile in web/styles.css (.wahl-eigen).
Geprüft: Testserver 8799, Playwright: Feld klappt auf, Zeile „7. Ja, aber …“, Taste Nein ersetzt sie und leert das Feld, Leeren entfernt die Zeile, keine Konsolenfehler. Nicht geprüft: Aussehen in einer echten Antwort mit Frage, Handy, Diktat mit Google-Tastatur, Verhalten im Korb (dort anderer Weg).

## 15.10.2026: Nachrichten erschienen doppelt im Verlauf
**Auslöser:** Roli 13:19 „meine Antworten werden leider doppelt ausgegeben“, 14:40 „Meine Antworten, die ich dir gebe, kommen immer doppelt bei dir an“ (Screenshot, Karte Krugmeister-Brain 23).
**Ursache:** Claude Code schreibt seit Oktober 2026 zu jeder Nachricht eine Kopie als Eintrag vom Typ `api-request-blob` ins Protokoll (mit `message`, aber ohne Zeitstempel). `mitschrift._bloecke_aus` hielt sie für echte Nachrichten. Angekommen ist die Nachricht in der Karte nur einmal.
**Lösung:** In `hetzner_app/mitschrift.py` werden Einträge übersprungen, deren Typ weder `user` noch `assistant` (noch fehlend) ist. Server neu gestartet.
**Geprüft:** Protokoll der Karte Krugmeister-Brain 23 neu gelesen, die Nachricht erscheint jetzt einmal. Browser nicht geprüft.

## 18.10.2026: V188, Büroklammer nimmt Android-Apps an
**Auslöser:** Roli 18.10. 14:30 „57. Ja“ auf die Frage aus der Karte Zerlegen, ob die Büroklammer APK-Dateien anbieten soll (Anregung in ANREGUNG-APK-ANHANG-2026-10-18.md). Die erste APK kam nie am Server an, weil Android sie in der Dateiauswahl nicht anbot; erst als .zip umbenannt ging es.
**Lösung:** `accept` des Datei-Wählers in web/index.html und das Teilen-Ziel im Manifest kennen jetzt .apk, .apks und .xapk (dazu der MIME-Typ application/vnd.android.package-archive). In server.py behalten diese Dateien ihre Endung (`APP_ENDUNGEN`), aber nur, wenn der Inhalt mit dem ZIP-Kopf beginnt; sonst 400. Die Grenze hängt jetzt am Inhalt: ZIP-Dateien (auch Word, Excel, Apps) bis 200 MB (`MAX_ZIP`), alles andere bleibt bei 30 MB. Gelesen wird häppchenweise mit Abbruch bei 200 MB.
**Fehler unterwegs:** Es gab zwei weitere Deckel vor dem Endpunkt, beide mussten für den Anhang-Weg mit: die App-eigene Middleware `sicherheits_header` (35 MB nach Content-Length, jetzt 210 MB nur für /api/sessions/<name>/datei) und Caddy (`request_body` 35 MB). Im Caddyfile gilt für die Relay von Roli, Lorenz und Lea jetzt `@anhang path /api/sessions/*/datei` bis 210 MB, alles andere weiter 35 MB. Sicherung /etc/caddy/Caddyfile.vor-apk-2026-10-18. Testsitzungen müssen auf dem tmux-Kanal `hz` mit Präfix `hz-` liegen, sonst kennt die App sie nicht. Im Testserver `app.router.on_startup.clear()`, damit weder Melde-Wächter noch Piper mitstarten.
**Geprüft:** Testserver 8799 mit Rolis echter App aus Zerlegen (15 MB, .apk bleibt), einer 120-MB-App (angenommen), einer Text-Datei namens .apk (abgelehnt), einem 40-MB-PDF (abgelehnt), einem 205-MB-ZIP (abgelehnt), kleinem PDF (angenommen). Playwright im Profil Pixel 7: Büroklammer, Dateien, echte APK, Anhang-Kärtchen erscheint, Antwort 200, keine Konsolenfehler. Nach dem Ausrollen von außen: 120 MB auf dem Anhang-Weg kommt durch Caddy bis zur Anmeldung (401), 40 MB auf einem anderen Weg 413. **Nicht geprüft:** echte Auswahl am Android-Handy und große Uploads über das Mobilnetz. Anhänge räumt `anhaenge_aufraeumen` wie bisher von selbst weg.

## 18.10.2026: V189, Schnellbefehle per Griff verschieben
**Auslöser:** Roli 18:32 „ich würde gerne die schnellwahl knöpfe verschiebbar machen“, auf Rückfrage 18:33 „6. Ja“ (die Leiste über dem Eingabefeld, Reihenfolge selbst festlegen, auf dem Server gespeichert).
**Lösung:** Im Blatt „Eigene Schnellbefehle“ hat jede Zeile links einen Griff (sechs Punkte). Daran zieht man die Zeile nach oben oder unten, sie wandert sofort mit; beim Loslassen geht die neue Reihenfolge über den bestehenden Weg (`eigeneBefehleSchreiben`, PUT /api/befehle) zum Server, und Leiste und Zauberstab-Menü übernehmen sie. Gezogen wird bewusst im Blatt und nicht in der Leiste, weil dort langer Druck schon den Satz ins Feld legt und die Leiste seitlich rollt. Griff mit `touch-action: none`, Hinweistext im Blatt und Tour-Text ergänzt. Server unverändert, `befehle._sauber` behält die Reihenfolge.
**Fehler unterwegs:** Mit Zeiger-Fang am Griff riss das Ziehen nach der ersten Stelle ab, weil das Umhängen der Zeile im DOM den Fang löst. Jetzt hängen die Lauscher an `document` und achten auf die pointerId.
**Geprüft:** Testserver 8799 mit Kopie der Befehlsdatei (echte Datei per Prüfsumme unverändert), Playwright Pixel 7 mit echten Touch-Ereignissen über CDP: „Zusammenfassen“ ganz nach oben, „Empfehlung Go“ vor „Stein für Stein“, Liste, Leiste und Server-Datei stimmen, keine Konsolenfehler. **Nicht geprüft:** echtes Handy, Ziehen über den sichtbaren Bereich hinaus (das Blatt rollt beim Ziehen nicht von selbst mit).

## 26.10.2026 (Brain 61): V190, Terminalschrift im hellen LEIT//PULS lesbar
**Auslöser:** Roli 26.10. 13:41 mit Screenshot der Karte Krugmeister-Brain 35 im LEIT//PULS: „das müssen wir anpassen im terminal kann mann so nichts lesen“. Die Terminalschrift war Dunkelblau auf fast Schwarz.
**Ursache:** xterm setzt Schriftfarbe, Farbtabelle (256 Farben), Cursor, Auswahl und Zeichenmaße über eigene `<style>`-Blöcke im Terminal. Die Sicherheitsregel der App (`style-src 'self'`) sperrt solche Blöcke, also galt keine davon. Die Schrift erbte die Textfarbe der Seite: dunkel zufällig hell, im hellen Modus (`:root.hell`, `--schrift` #14182B) Dunkelblau. Auch alle Farben aus Claude Code (Grau, Grün, Rot) fehlten schon immer. Gemessen im Screenshot: Schrift genau (20, 24, 43).
**Lösung:** `terminalStileSpiegeln()` in web/app.js, direkt nach `term.open`: liest den Text der xterm-Stilblöcke, legt ihn in ein per Skript gebautes Stilblatt (`new CSSStyleSheet`, `document.adoptedStyleSheets`), das die Regel erlaubt, und zieht es per MutationObserver nach, wenn xterm die Blöcke neu schreibt (Größe, Schrift). Die Sicherheitsregel bleibt unverändert streng. Die Meldungen „Applying inline style violates …“ in der Konsole bleiben, sie gehören zu den gesperrten Originalblöcken und sind harmlos.
**Geprüft:** Nachbau mit echter App am laufenden Dienst (Test-Anmeldung über `geraete.anmeldung_ausstellen`, danach abgemeldet), Playwright: hell vorher `rgb(20, 24, 43)`, nachher `rgb(240, 234, 226)`; Screenshot zeigt helle Schrift mit grünen und roten Punkten und grauen Zeilen; dunkel ebenso, Grau 246 kommt als `rgb(148, 148, 148)` an. Ausgerollt, `/api/version` 190. **Nicht geprüft:** am Windows-Rechner im LEIT//PULS selbst und am Handy.

## 31.10.2026: V191, Neue Sitzung mit Ordnersuche, Übergabe-Chip, Fragt nie und Sonnet als Vorgabe
**Auslöser:** Roli 31.10. 09:22 mit Screenshot des Bildschirms „Neue Sitzung“: „weil wir so viele Repos haben eine Suchlupe, bei Erster Auftrag Schnellwahl Übergabe lesen, automatisches Ausführen immer an und Modellwahl Standard immer Sonnet beim Start einer neuen Karte“, dazu „7. Allerdings am Laptop ist die Schnellwahltaste nicht scrollbar“ und „8. Ja“ (erledigte APK-Anregung löschen).
**Lösung:**
- Über der Ordnerliste steht ein Suchfeld mit Lupe (gleiche Optik wie in der Bibliothek). Es filtert die 57 Ordner rein im Browser; fällt der gewählte Ordner aus der Sicht, rückt der erste sichtbare nach, damit „Sitzung starten“ nie einen unsichtbaren Ordner nimmt. Kein Treffer zeigt einen Hinweis.
- Unter „Erster Auftrag“ liegt der Chip „Übergabe lesen“, ein Tipp füllt den Satz ins Feld.
- „Fragt nie“ ist jetzt vorbelegt an (Formular-Reset fällt darauf zurück).
- Neue Karten starten mit `--model sonnet`: `NewSession.modell` (leer heißt `STARTMODELL`), `tmux.create(..., modell=)` hängt `--model` an, der Zustand merkt sich das Modell, das Modell-Blatt zeigt sofort „Sonnet“. Beim Aufwecken bekommt die Karte ihr gemerktes Modell wieder mit (vorher fiel sie auf die Konto-Voreinstellung zurück). Unbekannte Namen weist der Server mit 400 ab.
- Am Rechner (`hover: hover` und `pointer: fine`) hat die Schnellbefehl-Leiste eine schmale Rollleiste, und das Mausrad rollt sie quer; der alte Rad-Weiterreicher an den Verlauf lässt die Leiste aus.
- Tourtext „Ein Gespräch beginnen“ ergänzt (Lupe, Sonnet, Fragt nie).
- `ANREGUNG-APK-ANHANG-2026-10-18.md` gelöscht (eigener Commit).
**Geprüft:** Startbefehl ohne echtes tmux nachgebaut (`--model sonnet` beim Start, dreimal `--model opus` in der Aufweck-Kette). Testserver 8799, Playwright Pixel 7 und 1280 px: 57 Ordner, „hetz“ lässt einen übrig und wählt ihn, „gibtsnicht“ zeigt den Hinweis, Leeren bringt alle zurück, Chip füllt „Übergabe lesen“, Fragt nie an, keine Konsolenfehler; am Rechner rollt das Mausrad die Leiste von 0 auf 300 px, Rollleiste „thin“. Ausgerollt, `/api/version` 191. **Nicht geprüft:** eine echte Karte über die App anlegen (das würde Claude Code starten) und das Rad am echten Laptop.

## 31.10.2026: V192, Kairas Stimme liest in der Relay vor
Auslöser Roli über die Kaira-Karte, 31.10. 00:48 „24. Ja, kannst du sie einbauen beim Relay App“, 04:03 „25. Ja“ (Auswahl in den Einstellungen, Kaira als Vorgabe, alte Stimme bleibt), 09:03 „27. Ja“ (die Hetzner-App-Karte baut); hier 10:16 „9. Ja“. Auftrag: ~/projekte/Kaira-Assistent/AUFTRAG-RELAY-STIMME.md.
Lösung: Das Piper-Modell `kaira_de-DE.onnx` samt `.onnx.json` liegt als Kopie in `~/.hetzner-app/stimmen` (nicht im Repo). In `hetzner_app/tts.py` steht Kaira als erster Eintrag im KATALOG, und STANDARD ist Kaira, sobald die Datei im Stimmen-Ordner liegt, sonst wie bisher Jonas (Thorsten medium). Damit bekommen Lea und Lorenz über ihre Spiegel nur den Code, Kaira taucht bei ihnen nicht auf, solange die Lizenz der Trainingsdaten (Mila-Sätze) ungeprüft ist. Rolis `~/.hetzner-app/stimme.txt` auf `kaira_de-DE` gestellt, weil dort ausdrücklich Thorsten stand. Der bestehende Piper-Dienst lädt Kaira über `--data-dir` ohne weitere Änderung; nach dem Neustart startet er mit Kaira als Modell.
Geprüft: Vor dem Umbau auf Port 5005 nachgesehen, dort lief der eigene Piper des Dienstes. Direkter Aufruf an Piper mit voice kaira_de-DE: HTTP 200, erster Satz mit Laden gut 5 Sekunden. Testserver 8799 mit HETZNER_TTS_PORT=5015 (eigener Test-Piper, damit das Aufräumen den echten nicht trifft), Pixel-7-Profil: Einstellungen zeigen Kaira oben und gewählt, Lautsprecher-Knopf spielt die Hörprobe als mp3-Strom (vortrag/…mp3, 200), keine Konsolenfehler. Test-Piper danach über PID beendet. Hörprobe Kaira gegen Jonas unter https://seiten-roli.65-21-246-222.sslip.io/relay-kaira-stimme/ im Browser geprüft.
Fehler unterwegs: Im ersten Browsertest auf den Namen getippt, das wählt nur; die Probe liegt auf dem Lautsprecher-Knopf. Der Test-Piper auf 5015 blieb nach dem Beenden des Testservers als Waise stehen und musste einzeln beendet werden.
Nicht geprüft: Vorlesen am echten Handy, Länge der Pausen zwischen Sätzen bei langen Antworten.

## 31.10.2026: V193, Knopf „Nebenfrage stellen“ (/btw) und Wächter fürs Nebenfrage-Fenster
Auslöser Roli 31.10. 10:02 „13. Ja“ (Nebenfrage-Knopf für /btw), 10:46 „17. Ja“ (jetzt bauen).
Testkanal vorher (eigene tmux-Sitzung `-L btwtest` mit Haiku in /tmp/k192/btw): /btw wird angenommen, während Claude arbeitet, die Hauptarbeit läuft weiter. Die Antwort steht aber nur in einem Fenster über der Eingabe (Fußzeile „… · Esc to close“, während des Schreibens „✽ Answering…“, ältere Nebenfragen darüber, lange Fragen auf eine Zeile mit „…“ gekürzt). Weder Frage noch Antwort stehen im Protokoll (.jsonl). Das Fenster bleibt offen, auch wenn Claude fertig ist. Befund: Eine normale Nachricht, die bei offenem Fenster getippt wird, verschwindet spurlos, und c und f sind dort Kurztasten (Kopieren, Abzweigen). Der Dialog-Wächter hielt den Schirm für frei, weil die Statuszeile „shift+tab to cycle“ darunter stehen bleibt.
Lösung Server: `tmux.dialog_zustand` meldet „nebenfrage“, wenn in den unteren 12 Zeilen „esc to close“ steht, geprüft vor der Statuszeile. `_eingabe_bereit` drückt dann Escape wie bei „abbrechbar“, so kommen normale Nachrichten wieder an. `tmux.nebenfrage_lesen` liest Frage und Antwort der neuesten /btw-Zeile vom Schirm. Neue Endpunkte: POST /api/sessions/{name}/nebenfrage (tippt „/btw …“ auch während der Arbeit, schließt vorher ein altes Fenster), GET …/nebenfrage (offen, frage, antwort, fertig), POST …/nebenfrage/schliessen (Escape nur, wenn das Fenster wirklich offen ist, weil Escape an der normalen Eingabe die Arbeit abbricht).
Lösung App: In der Leiste „Claude denkt nach …“ steht rechts der Knopf „Nebenfrage stellen“. Er nimmt den Text aus dem Eingabefeld (leer: Hinweis), zeigt einen Zettel „Nebenfrage“ über der Eingabe mit Frage und „Claude antwortet …“, fragt alle 1,5 Sekunden nach, bis die Antwort fertig ist (bis 2 Minuten; der Anfang der Frage muss passen, weil das Fenster lange Fragen kürzt). Lautsprecher liest die Antwort vor, bei Freisprech von selbst. Das Kreuz schließt Zettel und Fenster; beim Kartenwechsel ebenso. Die Pulsanimation der Leiste ist jetzt ein sanftes Ausblenden des Textes (die alte Ringanimation zeichnete Striche, sobald die Leiste einen Knopf bekam).
Geprüft: Schnittstelle gegen die Probe-Sitzung (Kennung btwtest:btwtest, damit keine Testkarte in Rolis Liste erscheint): Frage während der Arbeit, Antwort gelesen, normale Nachricht bei offenem Fenster kommt an, doppeltes Schließen drückt beim zweiten Mal nichts. Playwright im Pixel-7-Profil: Knopf sichtbar während der Arbeit, leerer Knopfdruck zeigt Hinweis, Zettel mit Antwort „Rom“, Kreuz schließt Fenster, kein „Interrupted“, keine Konsolenfehler.
Nicht geprüft: echtes Handy, sehr lange Antworten, die im Fenster scrollen müssten (dann fehlt der Rest, Terminal öffnen), Tour-Text (Knopf erscheint nur während der Arbeit, darum kein Tour-Schritt).
Nebenbei: Claude Code meldet in der Probe-Sitzung „Your login expires in 3 days“.

## 31.10.2026: V194, Kaira spricht englische Wörter nach der Aussprache-Liste
Auslöser: Roli 31.10. 10:34 (in der Kaira-Karte) bemerkte, dass Kaira GitHub, Relay, committed deutsch ausspricht; 10:46 „29. Ja“ zur Liste, ausdrücklich auch für die Relay; hier 11:12 „19. Ja“.
Lösung: `tts.aussprache_anwenden` liest direkt `~/projekte/Kaira-Assistent/server/aussprache.txt` (Zeilen „Wort = Lautschrift“, # Kommentar), neu eingelesen bei geänderter Datei, Regel wie in Kaira: ganze Wörter, Groß/Klein egal, längste Einträge zuerst. Angewendet in `_sprechen` nur für Stimmen in `AUSSPRACHE_STIMMEN` (Kaira); Jonas und Wolkenstimmen bleiben unberührt. Bei Lea und Lorenz fehlt die Datei, dann passiert nichts.
Geprüft: „Ich habe auf GitHub committed, die Relay-App …“ wird zu „Gitt-Habb kommittet, die Rieläi-Äpp …“, „Gitter“ bleibt. Testserver 8799 mit Test-Piper 5015, POST /api/speak mit Kaira: 200, Hörprobe vorher/nachher auf https://seiten-roli.65-21-246-222.sslip.io/relay-kaira-stimme/ (Proben 3 und 4).
Fehler unterwegs: Erst /api/tts statt /api/speak aufgerufen (405). Die PID-Datei des Testservers hielt die Hülle statt des Python-Prozesses, der Server lief weiter und musste über seine eigene PID beendet werden.

## 31.10.2026: V195, Antwort-Tasten bleiben unter der offenen Frage (Tasten-Rätsel)
**Auslöser:** Roli 31.10. 10:46 „Das war übrigens in deinem eigenen Chat“ (Antwort-Tasten unter nummerierten Fragen waren verschwunden); hier 11:24 „20. Ja“.
**Ursache:** Die Tasten standen nur unter der jüngsten Antwort mit Fragen, und die musste unter den letzten drei Antworten liegen. Schreibt Claude nach der Frage noch drei Zwischentexte (typisch beim Bauen mit Werkzeuglauf), fiel die Frage heraus, obwohl Roli noch nicht geantwortet hatte. In den Protokollen der Karte folgten auf Fragen oft 7 bis 34 weitere Textblöcke. Die Erkennung der Fragezeilen selbst war in Ordnung.
**Lösung:** In web/app.js (Marker `juengste`) gilt jetzt: Tasten unter der letzten Antwort mit Fragen, solange danach keine Nachricht von Roli (`.gesagt`) im Verlauf steht.
**Geprüft:** Testserver 8799, Playwright: Frage mit vier Zwischentexten danach zeigt die Tasten, nach einer Nachricht von Roli sind sie weg, keine Konsolenfehler. Ausgerollt, /api/version 195. **Nicht geprüft:** echtes Handy.

## 31.10.2026: V196, Satzzeichen hinter der Lautschrift in [[ ]]
**Auslöser:** Nachricht der Kaira-Karte (Kaira-Assistent 11), Roli 31.10. 11:37 „31. Überall B“: Die Aussprache-Liste enthält jetzt Piper-Lautschrift in `[[ ]]`. Steht ein Satzzeichen direkt hinter „]]“, schluckt Piper es samt Pause („[[ ˈapdeɪt ]]. Die“ wird zu „ˈapdeɪtdiː“).
**Lösung:** `tts.aussprache_anwenden` setzt nach dem Ersetzen das Satzzeichen vor die schließenden Klammern (`re.sub(r"\s*\]\]([.,!?;:])", r"\1 ]]", …)`), wie in Kaira. Eckige Klammern entfernt danach keine Textreinigung mehr (die Ersetzung läuft als letzter Schritt vor Piper).
**Geprüft:** Ersetzung am Beispielsatz mit der echten Liste; direkter Aufruf an Piper 5005: Satz mit Fix 2,47 s, ohne Fix 2,28 s (die Pause bleibt erhalten, der Satz klebt nicht zusammen). Ausgerollt, /api/version 196. Nicht gehört: Klang am Handy.

## 31.10.2026: V197, Eigenes Diktat mit Whisper als zweite Wahl neben Google
**Auslöser:** Roli 31.10. 10:16 „10. Ja“ (lokales Whisper-Diktat als zweite Wahl neben Google, gegen Aussetzer und Verhörer), 11:33 „21. Ja“, 11:59 „Ja“ auf Frage 22 (Modell small, Wortschatz als Hinweis).
**Lösung Server:** `hetzner_app/diktat.py` nimmt die Aufnahme (roher Körper, bis 8 MB, 180 s), wandelt sie mit ffmpeg auf 16 kHz Mono und gibt sie an einen dauerhaften Arbeiter (`whisper_worker.py`). Der läuft mit dem Python aus `~/werkzeuge/whisper/.venv` (dort liegt faster-whisper, das Modell „small“ ist im Cache), lädt das Modell beim ersten Auftrag, bleibt warm und beendet sich nach 10 Minuten Leerlauf von selbst. Hinweis an Whisper (`initial_prompt`): Grundworte plus die Wörter links aus Kairas aussprache.txt (höchstens 80). Endpunkte GET /api/diktat (verfügbar ja/nein, fehlt der Whisper-Ordner bei Lea/Lorenz, blendet die App die Wahl aus) und POST /api/diktat.
**Lösung App:** Einstellungen, neuer Abschnitt „Diktat“: Google (Vorgabe) oder Eigener Server, gemerkt auf dem Gerät (`diktat_art`). Beim eigenen Diktat startet ein Tipp aufs Mikrofon die Aufnahme (MediaRecorder), der zweite Tipp schickt sie zur Erkennung, der Text kommt hinter den vorhandenen Feldtext. Das Kreuz verwirft, Absenden/Kartenwechsel brechen ab, ohne etwas zu schreiben; nach 150 s endet die Aufnahme von selbst.
**Geprüft:** 17 s Kaira-Sprache (webm/opus): fehlerfreier Text, GitHub und Relay richtig, 8,7 s beim ersten Mal, 5,5 s warm. Playwright mit Fake-Mikrofon: Wahl sichtbar, Aufnahme, zweiter Tipp, Text im Feld; Kreuz stellt den alten Feldtext her, keine Anfrage, keine Konsolenfehler. Ausgerollt, /api/version 197.
**Nicht geprüft:** echtes Handy (Mikrofon-Erlaubnis, Aufnahmeformat Chrome Android, Xiaomi-Hintergrundregeln), Freisprech-Modus mit eigenem Diktat (dort öffnet sich das Mikrofon wie sonst, beendet wird per Tipp, keine Stille-Erkennung), Lea/Lorenz.

## 31.10.2026: GitHub-Auftritt zweisprachig (README und Repo-Beschreibung)
**Auslöser:** Roli 31.10. 10:16 „11. Ja“ (Relay zweisprachig und auf GitHub bewerben), 16:46 „1. Ja“ (nur der kleine Teil: Auftritt, englische Oberfläche später als eigener Stein), 16:12 „2. Nein“ (Kaira darf im README stehen).
**Lösung:** README.md und README.en.md um die Neuerungen seit V190 ergänzt: Antwort-Tasten, Nebenfrage-Knopf, Neue Sitzung mit Ordnersuche und Sonnet, Schnellbefehle ordnen, eigene Piper-Stimmen, optionales Whisper-Diktat (ausdrücklich nicht Teil der automatischen Einrichtung, der Pfad zu faster-whisper ist noch fest auf Rolis Server). Repo-Beschreibung (Englisch und Deutsch) und acht Themen-Stichworte auf GitHub gesetzt, ohne „Claude“ im Namen, Hinweis aufs eigene Abo steht schon im README.
**Entscheidung dazu:** Kaira steht nicht mit Namen im Text, weil Fremde die Stimme nicht bekommen können (Modell liegt nur in ~/.hetzner-app/stimmen, Lizenz der Trainingsdaten ungeprüft); das README sagt nur, dass weitere Piper-Stimmen in einen Ordner gelegt werden können.
**Nicht geprüft:** Die englische Oberfläche der App (eigener Stein, mehrere Stunden), Whisper-Einrichtung für Fremde (setup.sh installiert es nicht).

## 01.11.2026: Mockup und Plan für die englische Oberfläche (nichts gebaut)
**Auslöser:** Roli 01.11. 01:35 „3. Ja“ (englische Oberfläche als eigenen Stein planen), 01:37 „6. Mokup“ (erst ein Mockup statt Plan-Dokument), 01:43 „7. Ja“ (Aufbau abgenommen).
**Lösung:** Mockup aus der echten App im Testserver 8799 (Playwright Pixel 7, Texte per Skript ins Englische getauscht, Kartennamen als Platzhalter) unter ~/seiten/relay-englisch-mockup/: Kartenliste auf Englisch und Einstellungen mit neuem Abschnitt „Language“ ganz oben. Danach PLAN-ENGLISCHE-OBERFLAECHE.md mit gezähltem Umfang (144 Texte + 63 Attribute in index.html, ~173 Stellen in app.js, 99 Servermeldungen, Stimme und Diktat), Bauweise (texte.js mit t(), data-t, Accept-Language, englische Piper-Stimme) und Aufwand (1,5 bis 3 Stunden, zwei bis drei Karten, Umstellen durch Umsetzer auf Sonnet).
**Fehler unterwegs:** Beim Mockup-Skript war der Textersatz erst groß/klein-empfindlich, Chips wie „wartet auf dich“ blieben deutsch; behoben durch Ersetzen des ganzen Textknotens.
**Nicht geprüft:** Mockup-Seite nur als Bild angesehen, Link nicht im Browser geöffnet. Beschluss 5 (Roli „Deine Empfehlung“): Whisper-Diktat kommt nicht in setup.sh.

## 01.11.2026: V198, Gerüst der englischen Oberfläche und Sprachwahl (Schritt 1)
**Auslöser:** Roli 01.11. 11:25 „8. Ja“ (Bau der englischen Oberfläche beginnt), Plan in PLAN-ENGLISCHE-OBERFLAECHE.md.
**Lösung:** Neue Datei web/texte.js mit Textliste de/en, `t(schluessel, werte)` (Rückfall auf Deutsch), `texteAnwenden()` für `data-t` und `data-t-attr`, `spracheSetzen()`; Wahl in localStorage „sprache“, Vorgabe Deutsch, `<html lang>` wechselt mit. In den Einstellungen steht ganz oben der Abschnitt „Sprache/Language“ (Deutsch, English), Umschalten wirkt sofort. Als Beispiel sind die Überschriften und Hinweise der Einstellungen schon umgestellt.
**Geprüft:** Testserver 8799, Playwright Pixel 7: Umschalten ändert Titel, Marken und Hinweise, bleibt nach Neuladen, keine Konsolenfehler. Ausgerollt, /api/version 198.
**Noch offen (Schritte 2 bis 7):** restliche Texte in index.html, die 173 Stellen in app.js, Server-Meldungen, englische Stimme und Diktat-Sprache, Tour, automatische Suche nach deutschem Rest.

## 01.11.2026: Entwurf Monitor-Ansicht (Bauplan und klickbares Mockup, nichts in der App gebaut)
**Auslöser:** Roli 01.11. 15:52 (Spickzettel „Claude Desktop App“ von Julian Ivanov und Video, die neuen Funktionen auch am Monitor nutzen), 16:09 „5. Ja“, 16:17 „2./3./4. Deine Empfehlung“, klickbares Mockup mit geführter Tour gewünscht.
**Ergebnis:** Bauplan mit elf Bausteinen unter ~/seiten/relay-monitor-bauplan/, klickbares Mockup (Kartenliste mit Wort und Form je Zustand, Kartenmenü, Aufgabenliste, Modellwahl, Leiste mit Kontext, Änderungen, Aufgaben, Dateien, Vorschau, Hintergrund, „Was ist neu?“-Markierung, zehnstufige Tour, SSH-Anleitung) unter ~/seiten/relay-monitor-mockup/. Alle Daten erfunden.
**Prüfung der offiziellen Doku (Agent) und eigener Versuch:** Fast alle Funktionen gibt es auch im Terminal als Befehl, nur die Sitzungsleiste und die geteilte Ansicht sind Desktop-only. Die Desktop-App kann als Umgebung SSH nutzen (laut Doku, nicht ausprobiert). Die „Schaltzentrale“ heißt in der Doku Cross-Session-Messaging (/list-agents), in tmux nicht belegt. **/advisor** gibt es in Claude Code 2.1.316 hier nicht: im Versuch (Probe-Sitzung mit tmux) erscheint nur ein Skill „model-usage-advisor“; das deckt sich mit der Notiz vom 15.10. (nur Claude Platform on AWS), die Aussage des Doku-Agenten (ab 2.1.260 allgemein) trifft hier nicht zu.
**Nicht geprüft:** Bilder zu Schaltzentrale, Untersessions, Artefakten nur nach Beschreibung; SSH-Weg am Arbeitslaptop; Nachrichten zwischen Karten in tmux.

## 01.11.2026: Versuch Nachrichten zwischen Karten (Baustein 10, nichts in der App gebaut)
**Auslöser:** Roli 01.11. 16:17 „2./3./4. Deine Empfehlung“ (Versuch), 16:38 „1. Ja“ (Versuch starten).
**Versuch:** Eigene tmux-Sitzung (`-L sendtest`) mit `claude --model haiku` im leeren Ordner /tmp/k_send (Vertrauensfrage einmal bestätigt). Sie erscheint in ListAgents von selbst als „k-send-14“ mit dem Vermerk der tmux-Sitzung. SendMessage von der Hetzner-App-Karte an sie kam an, die Haiku-Karte hat ohne Zutun von Hand geantwortet, die Antwort kam in der Hetzner-App-Karte an.
**Ergebnis:** Karten in tmux können sich gegenseitig anschreiben (ListAgents, SendMessage), beide Richtungen. Die Schaltzentrale aus dem Desktop-Spickzettel ist damit in tmux ohne eigene Oberfläche schon nutzbar. Die Relay-App könnte die Liste der Karten und ihren Zustand (idle/busy) für die Monitor-Ansicht aus denselben Daten ziehen.
**Vorbehalt:** Eine Karte in anderem Berechtigungsmodus hält Nachrichten bis zur Freigabe zurück (laut Werkzeugbeschreibung). Die Test-Karte lief im Automodus. Ob Rolis echte Karten (Kaira-Assistent 12 usw.) Nachrichten ohne Rückfrage annehmen, ist nicht geprüft; dafür wurde absichtlich keine echte Karte angeschrieben.
**Aufgeräumt:** tmux-Server sendtest beendet, /tmp/k_send gelöscht.

## 01.11.2026: Baustein 3 (Kontextkarte) geprüft, besteht schon, nichts gebaut
**Auslöser:** Roli 01.11. 16:46 „3. Deine Empfehlung“ (Monitor-Bausteine in der Reihenfolge 3, 2, 1, 6, 7 bauen).
**Befund:** Der Bauplan führt Baustein 3 als ungebaut, aber die rechte Spalte „Zur Hand“ (ab dreiSpalten, index.html) hat schon den Block „Diese Karte“ mit Füllbalken, Kontext, Cache und Modell; dazu den Kontextbalken im Kopf, das Verbrauchsblatt mit Token von/bis und Prozent, die 200.000-Token-Regel (neueKarte) und den Übergabe-Knopf ab 100.000. Die Zahlen kommen aus der Mitschrift (verbrauch.py), nicht vom Schirm.
**Aufteilung nach Nachrichten, Werkzeugen, Skills:** an einer Test-Karte (Haiku, tmux `-L ctxtest`) /context ausprobiert. Die Ausgabe ist ein langer Baum mit hunderten Zeilen je Skill und Fachkraft, läuft in das echte Terminal der Karte und schiebt deren Schirm. Als Anzeige zu fragil und zu schwer, deshalb bleibt es bei der Gesamtzahl (wie im Bauplan als Rückfall vorgesehen). Test-Karte beendet, Ordner gelöscht.
**Ergebnis:** Baustein 3 gilt als erledigt, kein neuer Code, keine neue Version. Nächster ist Baustein 2 (Aufgabenliste mit Haken).

## 01.11.2026: Baustein 2 (Aufgabenliste mit Haken) geprüft, Quelle fehlt
**Auslöser:** Roli 01.11. 17:05 „5. Ja“ (erst das Protokoll prüfen, ob die Liste dort steht).
**Befund:** In den 40 jüngsten Mitschriften aller Karten (und in der Suche über alle) kommt kein Aufruf TodoWrite, TaskCreate oder TaskUpdate vor; es gibt auch keinen Ordner ~/.claude/todos oder tasks. Die Claude-Code-Version 2.1.316 führt hier offenbar keine solche Liste, die die App auslesen könnte. Vom Schirm lesen wäre die einzige Quelle und zu fragil. Nichts gebaut, keine neue Version.
**Folge:** Baustein 2 ruht, bis eine Karte nachweislich eine Liste führt. Weiter mit Baustein 1 (Änderungen der Karte per git diff).

## 01.11.2026: V199, Baustein 1 der Monitor-Ansicht: „Änderungen dieser Karte“
**Auslöser:** Roli 01.11. 17:11 „6. Ja“ (Baustein 1 bauen). Dazu ein Handy-Screenshot aus der Claude-Oberfläche (Karte „Archiv der Lücken“): unter der Antwort drei Knöpfe „Diff +2583 −3“, „PR erstellen“, „Artefakte · 1“, im Eingabefeld ein vorgeschlagener Antworttext („Los, Punkt 1 bis 6 wie vorgeschlagen, bau Schritt 2“) mit Pfeil. Roli: „Was ich auch gut finde, die Antwort unter optional auswählen.“ (vermutlich der vorgeschlagene Antworttext; siehe offene Rückfrage an Roli).
**Lösung Server:** Neue Datei `hetzner_app/aenderungen.py`. `uebersicht` liest im Kartenordner `git diff --numstat HEAD` plus neue, nicht erfasste Dateien (`ls-files --others --exclude-standard`), je Datei Plus und Minus, Summe; kein Git-Ordner liefert `git: false`. `datei_diff` liefert die Zeilen einer Datei (bis 400), nur für Pfade aus der Übersicht (kein „../“, keine fremden Pfade). Dateien mit Zugangsdaten (.env, Schlüssel, Token, Passwort im Namen) erscheinen nur mit Namen, nie mit Inhalt. Neue Endpunkte `GET /api/sessions/{name}/aenderungen` und `…/aenderungen/datei?pfad=`. `GIT_OPTIONAL_LOCKS=0`, damit die Anzeige nie einen Git-Lock hält.
**Lösung App:** In der rechten Spalte „Zur Hand“ (nur am breiten Rechner) neuer Block „Änderungen dieser Karte“ über „Diese Karte“: Summe in der Kopfzeile, je Datei Name, `+N −M` (Zeichen, nicht nur Farbe), Tipp klappt die Zeilen auf (grün hinterlegt Plus, rot Minus, Vorzeichen bleiben sichtbar). Abruf beim Kartenwechsel sofort, sonst höchstens alle 12 Sekunden, offene Dateien bleiben offen.
**Geprüft:** Testserver 8799 mit eigenem Piper 5015, Playwright 1500x900: Block zeigt 5 Dateien +244 −2 der eigenen Karte, Aufklappen zeigt Zeilen, keine Konsolenfehler. Schutzfälle in einem Wegwerf-Git-Ordner: `.env` ohne Inhalt, `../außen` und `/etc/passwd` abgewiesen, Ordner ohne Git gibt `git: false`. Ausgerollt, /api/version 199.
**Fehler unterwegs:** Der erste Testserver ohne `HETZNER_TTS_PORT` hat den echten Piper auf 5005 durch seinen eigenen ersetzt (genau die Falle aus der CLAUDE.md). Gemerkt, weil die Prozessnummer auf 5005 neuer war als die des Testservers. Testserver samt Piper beendet, Dienst neu gestartet, Piper läuft wieder unter dem Dienst. Lehre: Testserver immer mit `HETZNER_TTS_PORT=5015` starten, gleich beim ersten Mal.
**Nicht geprüft:** echtes Handy (Block ist dort versteckt), sehr große Änderungen (Liste auf 200 Dateien, Diff auf 400 Zeilen gekürzt), Umbenennungen werden nur mit dem neuen Namen gezeigt.

## 01.11.2026: V200, Büroklammer nimmt jede Datei an
**Auslöser:** Roli 01.11. 18:30: früher habe die App ein „Senden“ gehabt, mit dem er jede Datei über Android hätte schicken können; mp4 und vieles andere werde jetzt abgelehnt, er lade ja nichts Falsches hoch, nur bei zu viel Daten leuchte ihm eine Grenze ein.
**Lösung:** In `session_datei` fällt die Positivliste (DOK_ENDUNGEN, APP_ENDUNGEN-Prüfung, Text-und-ZIP-Raten) weg. Jede nicht leere Datei wird angenommen, Grenze für alle 200 MB (vorher 30 MB außer ZIP/Apps; Caddy lässt auf diesem Weg 210 MB durch). Die Endung bleibt, wenn sie aus 1 bis 8 Buchstaben oder Ziffern besteht, sonst wird sie am Inhalt erraten oder „.bin“. Der Dateiname wird weiter von uns vergeben, abgelegt in `.hetzner-dateien` (gitignoriert, nach 3 Tagen aufgeräumt), ausgeführt wird nichts. In `web/index.html` fehlt der `accept`-Filter am Datei-Wähler, damit Android alle Dateien zeigt. Die Fotos-Wege (Kamera, Galerie) bleiben wie sie sind, 20 MB.
**Geprüft:** Testserver 8799 mit eigenem Piper 5015: mp4, exe und eine Datei ohne Endung werden angenommen (Endungen mp4, exe, bin), eine leere Datei mit 400 abgewiesen; Testdateien gelöscht, Piper auf 5005 unberührt. Ausgerollt, /api/version 200.
**Nicht geprüft:** echtes Handy (Dateifenster zeigt jetzt alle Typen), Upload nahe 200 MB, ob Claude eine mp4 sinnvoll verarbeiten kann (nur ablegen, Lesen ist Sache der Karte, etwa mit ffmpeg).

## 01.11.2026: V201, Baustein 6: Abschnitte je Projekt in der Kartenliste (und Baustein 12 im Bauplan)
**Auslöser:** Roli 01.11. 18:51 „7. Deine Empfehlung, 8. Deine Empfehlung“ (Ja zu Baustein 12 im Bauplan und zu Baustein 6). Das Bild dazu (Karte „Archiv der Lücken“, nach 14 Tagen weg): graue Antwortzeile im Eingabefeld „Los, Punkt 1 bis 6 wie vorgeschlagen, bau Schritt 2“ mit Pfeilchen daneben, darüber Knöpfe Diff, PR erstellen, Artefakte. Das bestätigt meine Deutung: Rolis „die Antwort unter optional auswählen“ meint den vorgeschlagenen Antworttext. Er steht jetzt als Baustein 12 im Bauplan (seiten-roli …/relay-monitor-bauplan/), dort sind auch die Stände von 1, 2, 3, 10 nachgetragen. Gebaut ist 12 noch nicht.
**Befund:** Statuspunkt mit Wort (läuft, wartet auf dich, fertig noch nicht gesehen, ruht), Anheften und die Gruppen „Wartet auf dich“, „Angeheftet“, „Schläft“, „Archiv“ gab es schon. Gefehlt hat nur die Gliederung nach Projekt.
**Lösung:** In `ladeListe` (web/app.js) werden die Karten aus „Zuletzt benutzt“ nach dem Ordnernamen ihres `cwd` gruppiert. Ab zwei Karten im selben Ordner gibt es einen eigenen Abschnitt mit dem Ordnernamen, einzelne Karten bleiben in „Zuletzt benutzt“. Nichts am Server außer VERSION 201.
**Geprüft:** Testserver 8799 mit HETZNER_TTS_PORT=5015, Playwright 412x915: mit erfundenen Karten (zwei Kaira, zwei Medienwerk, je eine Brain und Alleine) entstehen die Abschnitte Kaira-Assistent, Medienwerk und Zuletzt benutzt, keine Konsolenfehler. Mit den echten Karten sieht die Liste unverändert aus (alles wartet oder ist angeheftet). Piper auf 5005 blieb unberührt.
**Nicht geprüft:** echtes Handy; Reihenfolge der Abschnitte (folgt der Reihenfolge der Karten, nicht einer eigenen Sortierung).

## 01.11.2026: V202, Baustein 12: Antwort-Vorschlag über dem Eingabefeld
**Auslöser:** Roli 01.11. 19:04 „9. Deine Empfehlung“ (Baustein 12 bauen), Vorbild der graue Antworttext aus dem Screenshot vom 01.11. (siehe V201).
**Lösung:** Ist das Eingabefeld leer und hat die jüngste Antwort nummerierte Fragen, steht über dem Feld ein gestrichelter grauer Zettel „Vorschlag: 11. Ja, 12. Nein, 13. Deine Empfehlung ›“. Je Frage wird das Ja oder Nein genommen, das Claude hinter „Meine Empfehlung:“ nennt, sonst „Deine Empfehlung“. Ein Tipp trägt die Zeilen über die vorhandene Schnellwahl-Funktion `waehle` ins Feld ein (Tasten leuchten mit), danach lässt sich alles ändern. Es wird nie von selbst gesendet. Neue Dateien nur im Aufbau: Knopf `#antwort-vorschlag` in `web/index.html`, `vorschlagBilden`/`vorschlagAuffrischen` in `web/app.js`, Stil in `web/styles.css`. Server nur VERSION 202.
**Geprüft:** Testserver 8799 (Piper-Port 5015), Playwright 412x915: eingesetzte Fragen 11 (Empfehlung Ja), 12 (Nein), 13 (ohne) ergeben den Vorschlag, Tipp füllt das Feld mit drei Zeilen, der Zettel verschwindet danach; keine Konsolenfehler; Piper auf 5005 unberührt. Mit der echten Karte kein Zettel, weil Roli schon geantwortet hatte (so gewollt).
**Nicht geprüft:** echtes Handy, sehr lange Vorschlagszeile bei vielen Fragen (bricht um), Zusammenspiel mit Diktat.

## 01.11.2026: V203, Baustein 7: Vorschau neben dem Chat
**Auslöser:** Roli 01.11. 19:10 „11. Ja“ (Baustein 7 bauen; 18:51 „10. Deine Empfehlung“).
**Lösung Server:** Neue Datei `hetzner_app/vorschau.py` und Endpunkt `GET /api/vorschau`: listet die Ordner mit index.html aus `~/seiten` (oder `HETZNER_APP_VORSCHAU_ORDNER`), jüngste zuerst, höchstens 60, mit `<title>`. Nur lesen. Die Adresse des Webspace kommt aus `HETZNER_APP_VORSCHAU_BASIS` (nur https, ohne Pfad); fehlt sie, gibt es keine Vorschau und der Block bleibt weg (Lea und Lorenz haben eigene Adressen). Die Content-Security-Policy bekommt dann genau eine zusätzliche Zeile `frame-src <Herkunft>`; sonst bleibt alles dicht. Für Rolis Dienst steht die Basis in `~/.hetzner-app/umgebung` (kein Geheimnis).
**Lösung App:** In „Zur Hand“ (nur am breiten Rechner) der Block „Vorschau“: Auswahlliste der Seiten, „Neu laden“, „Eigenes Fenster“ und ein Rahmen (iframe, sandbox mit Skripten, gleicher Herkunft und Formularen, kein Referrer). Die gewählte Seite merkt sich das Gerät (`vorschau_seite`). Kein Anklicken und Kommentieren (das ist Baustein 11).
**Geprüft:** Testserver 8799 (Piper-Port 5015) mit gesetzter Basis, Playwright 1500x900: Block sichtbar, Wahl „relay-monitor-bauplan“ lädt die Seite im Rahmen (Titel stimmt), „Neu laden“ hängt einen Zähler an, `frame-src` steht in der Kopfzeile, keine Konsolenfehler; Piper auf 5005 unberührt.
**Nicht geprüft:** echtes Handy (Block dort versteckt), Seiten mit eigener Anmeldung oder mit `X-Frame-Options` im Rahmen (würden leer bleiben, „Eigenes Fenster“ hilft dann), Lea und Lorenz (haben die Basis nicht gesetzt).

## 01.11.2026: Beschluss Reihenfolge, Englisch ganz zum Schluss
**Auslöser:** Roli 01.11. 19:29 „wieso willst du dann englisch machen, da macht so kein sinn bitte erst wenn alles steht und geändert worden ist. dann machen wir die englische version“.
**Folge:** Schritt 2 bis 7 aus PLAN-ENGLISCHE-OBERFLAECHE.md ruhen, bis die Monitor-Bausteine fertig sind. Meine Frage 12 („Englisch als Nächstes“) war falsch gestellt. Es bleiben der Videoabgleich (Frage 13) und die Bausteine 4, 5, 8, 9, 11.

## 01.11.2026: Abgleich Spickzettel „Claude Desktop App“ gegen die Bausteine
**Auslöser:** Roli 01.11. 19:26 „hast du alles eingebaut aus dem video?“, 19:30 „15. Ja“ (Abgleich). Das Video selbst liegt nicht auf dem Server, nur der Spickzettel (PDF, 7 Seiten plus Prompts und Kürzel, Bilder stammen laut Zettel aus dem Video). Verglichen wurde also der Zettel, nicht das Video Bild für Bild.
**Ergebnis:** Neu gefunden und als Bausteine 13 bis 16 in den Bauplan gesetzt: Tastenkürzel (13), Befehle /doctor, /skill-doctor, /insights und die acht Prompts als Schnellbefehle (14), Ausgabestil und Transkript-Ansicht (15), geteilte Ansicht mit zwei Karten (16). Nicht übernommen, weil nur Desktop oder nicht möglich: iOS-Simulator, Weiter in Cloud, Claude Code Projects, Mods, Artefakte, Konnektoren. Bereits da oder gebaut: Seitenchat (V193), Abschnitte (V201), Status je Karte, Änderungen (V199), Kontext, Vorschau (V203). Offen: Untersitzungen, in tmux nicht als eigene Karten sichtbar.

**Berichtigung zum Abgleich (Roli 01.11. 19:57):** Meine Aussage „das Video liegt nicht auf dem Server“ war falsch. Es liegt in der YouTube-Bibliothek unter /opt/yt-auswertung (Auswertung, mp3, 59 Standbilder alle 18 Sekunden in web/qmuqhNZAoSzO/bilder/…). Verglichen habe ich bisher nur Spickzettel und Auswertung, die Bilder noch nicht einzeln. Beschluss 19:57 „16. Ja, 17. Ja, 18. Ja“: Baustein 14, dann 13, dann 4, 5, 8, 9.

## 01.11.2026: V204, Baustein 14: Vorschläge vom Spickzettel im Schnellbefehl-Blatt
**Auslöser:** Roli 01.11. 19:57 „16. Ja“ (Baustein 14 zuerst).
**Lösung:** Im Blatt „Eigene Schnellbefehle“ steht unter der Liste ein Abschnitt „Vorschläge vom Spickzettel“ mit neun fertigen Einträgen: /doctor, /skill-doctor, /insights, /recap, Karten-Überblick (Schaltzentrale mit ListAgents), In Teile zerlegen (Unteragenten), Ergebnis prüfen, Git einrichten, Kurz und ohne Fachwörter. Ein Tipp legt den Eintrag ins Menü (nicht in die sichtbare Leiste), danach verschwindet er aus den Vorschlägen und lässt sich wie jeder eigene Befehl ändern oder in die Leiste stellen. Deine bestehende Liste bleibt unangetastet. /advisor fehlt absichtlich (gibt es hier nicht), /rewind kommt mit Baustein 5. Nur App-Dateien, Server nur VERSION 204.
**Geprüft:** Testserver 8799 (Piper-Port 5015), Playwright 412x915: neun Vorschläge sichtbar, Tipp auf den ersten schickt eine Liste mit /doctor an den Server (im Test abgefangen, die echte befehle.json blieb unverändert, Prüfsumme gleich) und der Vorschlag verschwindet; keine Konsolenfehler.
**Nicht geprüft:** echtes Handy; ob /skill-doctor und /insights in Claude Code 2.1.316 hier tatsächlich vorhanden sind (ihre Existenz kommt aus dem Spickzettel, wie bei /advisor fehlt sie vielleicht; nach dem ersten Einsatz prüfen).

## 01.11.2026: Standbilder des Videos angesehen, Bauplan um 17 und 18 ergänzt
**Auslöser:** Roli 01.11. „22. Ja“ und 20:46 „1. Ja“ (die 59 Standbilder ansehen, Nachtrag in den Bauplan).
**Ergebnis:** Alle 59 Bilder (fünf Übersichtsblätter) durchgesehen. Neu: Baustein 17 (Cache-Uhr und Kontingent-Leiste), Baustein 18 (Kontext nach Posten). Fork, Spalten der Schaltzentrale, Hintergrundaufgaben-Fenster und /doctor-Karte als Hinweise bei den Bausteinen 4, 10, 9, 14. Sonst deckt sich das Video mit dem Spickzettel. Nichts in der App geändert.
**Nicht geprüft:** ob /context in tmux lesbaren Text liefert; ob das Kontingent aus den Protokollen zu holen ist.

## 01.11.2026: V205, Baustein 13: Tastenkürzel am Rechner
**Auslöser:** Roli 01.11. 20:47 „2. Ja“ (Baustein 13 bauen).
**Lösung:** Ein Tastendruck-Hörer am Seitenende von `web/app.js`; jedes Kürzel tippt den vorhandenen Knopf an. Esc stoppt die Arbeit (Knopf „Abbrechen“, nur wenn kein Blatt offen und nicht im Suchfeld), Strg K öffnet die Verlaufssuche, Strg D das Diktat, Strg Umschalt D springt zu den Änderungen in „Zur Hand“ (mit kurzem Rahmen), Strg / zeigt das neue Blatt „Tastenkürzel“ (`#kuerzel-blatt` in `index.html`, Stil am Ende von `styles.css`). Server nur VERSION 205. Strg Enter (Warteschlange) und Esc Esc (Zurückspulen) fehlen absichtlich, sie gehören zu Baustein 5, weil die Relay bei Arbeit das Senden sperrt.
**Fehler unterwegs:** `offsetParent` ist bei fest positionierten Blöcken leer, darum galt „Zur Hand“ als unsichtbar; jetzt `getClientRects`.
**Geprüft:** Testserver 8799 (Piper-Port 5015), Playwright 1500x900: Strg / öffnet und Esc schließt das Blatt, Strg K öffnet die Suche, Esc schließt sie, Strg Umschalt D markiert den Änderungen-Block, Esc bei sichtbarem Abbrechen-Knopf löst genau einen Klick aus (im Test abgefangen), keine Konsolenfehler. Ausgerollt, /api/version 205.
**Nicht geprüft:** Mac (Befehlstaste ist miterfasst, aber nicht probiert), ob ein Browser Strg D oder Strg K trotz preventDefault selbst behält (Firefox).

## 01.11.2026: V206, Baustein 4: Kartenmenü mit Fork
**Auslöser:** Roli 01.11. 22:58 „3. Ja“ und 23:07 „Wir haben hier genug platz mach mit 4 weiter“ (die Karte durfte weiterlaufen, trotz Übergabe-Auftrag des Wächters).
**Befund:** Umbenennen (Name antippen), Anheften, Archiv, Ungelesen (nur in der Liste) und Löschen (Server `DELETE`) gab es verstreut. Neu sind nur Fork und ein gemeinsames Menü.
**Lösung Server:** `tmux.create(abzweigen_von=…)` startet `claude --resume <alt> --fork-session --session-id <neu>`; die Kombination mit eigener neuer Kennung wurde vorher mit zwei Haiku-Aufrufen in einem Wegwerf-Ordner bestätigt (zwei Dateien, Kopie kennt das alte Gespräch). Neuer Endpunkt `POST /api/sessions/{name}/fork`: Name „<Name> Fork“, bei Kollision mit Zahl; übernimmt Ordner, Modell, Startmodus und Melden, nicht das Anheften; setzt die neue Kennung als Mitschrift.
**Lösung App:** Knopf „⋯“ am Ende der Kopfzeile öffnet das Blatt `#kartenmenue-blatt` mit Umbenennen, Anheften/Nicht mehr anheften, Als ungelesen markieren, Fork, Ins Archiv, Löschen (rot). Die ersten drei und das Archiv rufen die vorhandenen Knöpfe an; Fork und Löschen fragen vorher nach; fremde Karten (nicht von der App) zeigen weder Fork noch Archiv noch Löschen. Nach „Als ungelesen“ geht die App zur Liste, ohne dass das Hinausgehen die Markierung wieder löscht (Merker `ungelesenBleibt`).
**Geprüft:** Testserver 8799 (Piper-Port 5015): Fork der eigenen Karte angelegt, die Kopie zeigt das Gespräch samt dem unterbrochenen Befehl; im Browser (412x915) Menü mit allen sechs Punkten, „Als ungelesen“ setzt `ungelesen` auf wahr und bleibt nach dem Hinausgehen, „Löschen“ mit Rückfrage entfernt die Kopie samt tmux-Sitzung; keine Konsolenfehler. Ausgerollt, /api/version 206.
**Nicht geprüft:** echtes Handy; Fork einer Karte, die gerade mitten in einer Antwort ist; Name in der Kopfzeile wird durch den zusätzlichen Knopf etwas enger abgeschnitten; „In Abschnitt verschieben“ aus dem Video gibt es nicht (Abschnitte folgen dem Ordner, V201).

## 01.11.2026: V207, Baustein 5: Zurückspulen (/rewind) und Kurzfassung (/recap)
**Auslöser:** Roli 01.11. 23:24 „4. Ja“ (Baustein 5 bauen, in derselben Karte weiter).
**Befund (Probe in einer Wegwerf-Sitzung mit Haiku):** /rewind zeigt erst eine Liste der eigenen Nachrichten (je eine Zeile Text, eine Zeile „No code changes“ oder Änderungen, unten „(current)“, Pfeiltasten und Enter), danach eine Bestätigung mit nummerierten Möglichkeiten (Restore conversation, Summarize from here, Summarize up to here, Never mind; mit Codeänderungen kommen vermutlich Restore code and conversation und Restore code dazu). Escape schließt beide ohne Folgen; die gewählte Nachricht steht danach wieder in der Eingabezeile.
**Lösung Server:** neues Modul `hetzner_app/zurueckspulen.py` (liest beide Bildschirme als Text, übersetzt die Möglichkeiten) und vier Endpunkte unter `/api/sessions/{name}/rewind/`: `start` (Eingabe muss frei sein, leert vorhandenen Entwurf mit Strg U, tippt /rewind, liefert die Nachrichten), `waehlen` (Pfeil nach oben je Schritt, Enter, liefert Nachricht und Möglichkeiten), `ausfuehren` (tippt die Ziffer, „Never mind“ wird zu Escape), `abbrechen` (Escape nur, wenn eine der beiden Auswahlen wirklich offen ist). Jede Stufe prüft vorher, welcher Bildschirm offen ist.
**Lösung App:** Im Kartenmenü neu „Zurückspulen“ und „Kurzfassung“ (schickt /recap), dazu Esc Esc (Kürzel, nur wenn nichts arbeitet und kein Blatt offen). Blatt `#rewind-blatt` in zwei Stufen: Nachricht wählen (neueste oben, Hinweis auf Codeänderungen), dann Möglichkeit wählen (Zurücksetzen rot). Schließen mit ✕ bricht in der Karte ab.
**Fehler unterwegs:** Stand in der Eingabezeile ein Entwurf (etwa die zurückgespulte Nachricht), hängte der erste Versuch „/rewind“ hinten an und schickte alles als Nachricht ab. Jetzt wird der Entwurf vorher geleert.
**Geprüft:** Testserver 8799 (Piper-Port 5015) mit Probekarte: Liste, Wahl, „Doch nicht“ (nichts geändert), echtes Zurücksetzen (Gespräch endet bei „Sag nur ok“, Nachricht wieder im Feld), Abbrechen über ✕, Esc Esc, Kurzfassung; keine Konsolenfehler. Probekarte und Wegwerf-Ordner gelöscht. Ausgerollt, /api/version 207.
**Nicht geprüft:** Codeänderungen im Verlauf (die Zeile „N files changed“ wird nur durchgereicht, nicht ausgewertet), sehr lange Nachrichten oder mehr als eine Bildschirmseite Nachrichten (nur die sichtbaren werden angeboten), echtes Handy.

## 02.11.2026: V208, Zur Hand: Kontext oben fest, doppelte Fragen entfernt
**Auslöser:** Roli 02.11. 10:15 „ich würde bevorzugen, dass wir Kontext, Cache und Modell oben fest haben … ob wir die offenen Fragen dieser Karte doppelt brauchen“, 10:20 „9. Ja“.
**Lösung:** Der Block „Diese Karte“ (Kontext, Cache, Modell) steht jetzt über dem Rollbereich der rechten Spalte und rollt nicht mit. Der Block „Offene Fragen dieser Karte“ ist samt Code und Stilen entfernt, denn dieselben Fragen stehen im Chat mit den Antwort-Tasten. Reihenfolge nun: Diese Karte, Entscheidungskorb, Änderungen, Vorschau.
**Fehler unterwegs:** Mein erster Schnitt in app.js erwischte wegen einer gleichlautenden Zeile in vorschlagBilden zu viel (100 Zeilen weg, Konsole meldete „zurHandAuffrischen is not defined“). Zurückgenommen, Schnitt auf die Funktion eingegrenzt.
**Geprüft:** Testserver 8799, Playwright 1500x900: Block oben fest, vier Überschriften in der richtigen Reihenfolge, Screenshot angesehen, keine Konsolenfehler. Ausgerollt, /api/version 208. **Nicht geprüft:** Handy (Spalte ist dort versteckt).

## 02.11.2026: V209, Antwort-Tasten bleiben, bis die Frage beantwortet ist
**Auslöser:** Roli 02.11. 10:29 „wenn ich was Neues in den Chat schreibe und die Fragen davon nicht beantwortet habe, … bleiben die Antwort-Felder nicht erhalten, können wir das so machen, dass die erhalten bleiben“.
**Ursache:** Die Tasten standen nur unter der jüngsten Antwort, und nur solange danach nichts von Roli kam (V195). Jede freie Nachricht ließ sie verschwinden.
**Lösung:** In `mark()` (app.js) gilt eine Frage als beantwortet, wenn in einer späteren Nachricht von Roli eine Zeile „N. …“ mit ihrer Nummer steht (auch hinter einem Zeitstempel in eckigen Klammern). Nur beantwortete Zeilen werden ausgeblendet (Klasse `erledigt`), die Taste „Überall“ verschwindet, wenn weniger als zwei Fragen offen sind. Offene Fragen älterer Antworten behalten ihre Tasten. Eigene Antworten und Haken liegen weiter im Eingabefeld, das beim freien Schreiben unberührt bleibt.
**Geprüft:** Testserver 8799, Playwright mit nachgebautem Verlauf: Frage 5 beantwortet → weg, Frage 6 nach einer Zwischennachricht noch da, nach „6. Nein“ weg; keine Konsolenfehler. Ausgerollt, /api/version 209. **Nicht geprüft:** echter langer Verlauf (alte, nie beantwortete Fragen früherer Antworten zeigen jetzt ihre Tasten weiter), Handy.

## 02.11.2026: V210, Ton-Tagebuch protokolliert den Mikrofon-Versuch im Freisprech-Modus
**Auslöser:** Roli 02.11. 10:36 „was ist mit dem Kopfhörer-Knopf, warum funktioniert der nicht“, 10:43 „14. Ja“.
**Befund:** Die Kette Vorlesen, dann Mikrofon öffnen läuft im Testbrowser mit nachgestellter Antwort (Schalter an, `sprich` aufgerufen, Diktat-Knopf geklickt). Das Ton-Tagebuch vom Handy zeigt Vorlesen und „vortrag-ende“, aber nichts zum Mikrofon. Ursache am Handy daher noch offen; Verdacht (unbelegt): Chrome Android erlaubt den Mikrofonstart ohne Fingertipp nicht zuverlässig.
**Lösung:** Neue Tagebuch-Ereignisse `mik-versuch`, `mik-uebersprungen` (mit den Bedingungen: Freisprech, Terminal, hört, spricht, Rest, Sichtbarkeit), `mik-fehler`, `mik-ergebnis` (1,5 s später: offen oder nicht) und `mik-erkennung-fehler` (Fehlercode der Spracherkennung). Nachlesen in ~/.hetzner-app/ton-tagebuch.log.
**Nicht geprüft:** echtes Handy. Nächster Schritt: nach Rolis nächster Fahrt das Tagebuch lesen.

## 02.11.2026: V211, Freisprech sendet nach vier Sekunden Sprechpause
**Auslöser:** Roli 02.11. 10:46 „ab wann sendest du ab, wenn ich im Auto sitze, muss ich ja trotzdem auf den Knopf drücken“, 10:49 „das automatische Absenden nach 4 Sekunden“ (Rest des Diktats zerhackt, gelesen als: ohne dass ich ein Wort wie „senden“ sagen muss).
**Lösung:** Nur bei eingeschaltetem Freisprech-Modus und Google-Diktat. Jedes Spracherkennungs-Ergebnis startet einen Zähler neu (`autoSendePlanen`); nach der Pause (Standard 4 s, einstellbar über localStorage `sendePause`, 2 bis 30) schickt `requestSubmit()` das Formular ab. In den letzten drei Sekunden zeigt die Leiste „Sende in N …“ mit Knopf „Stopp“. Abgebrochen wird durch Stopp, echtes Tippen ins Feld (nur vertraute Ereignisse), Mikrofon aus oder Absenden. Leeres Feld sendet nie. Arbeitet Claude noch, greift die bestehende Sperre des Formulars.
**Geprüft:** Testserver 8799, Playwright 412x915 mit Drei-Sekunden-Pause: Zähler sichtbar („Sende in 2 …“), Stopp verhindert das Senden, ohne Stopp genau eine Sendung, leeres Feld keine; keine Konsolenfehler. Ausgerollt, /api/version 211.
**Nicht geprüft:** echtes Diktat am Handy (Spracherkennung liefert dort Satz für Satz, der Zähler startet nach jedem Ergebnis neu), Whisper-Diktat (keine Stille-Erkennung, kommt als eigener Stein), keine Einstellung in der Oberfläche für die Pause.

## 02.11.2026: V212, Baustein 8: Dateibaum zum Lesen
**Auslöser:** Roli 02.11. 10:29 „11. Ja“ (Reihenfolge Dateibaum, Kartenwechsel, Stille-Erkennung, Dienstzugang).
**Lösung Server:** Neues Modul `hetzner_app/dateibaum.py` und zwei Endpunkte `GET /api/sessions/{name}/dateien?pfad=` und `.../dateien/inhalt?pfad=`. Alles bleibt unter dem echten Pfad des Kartenordners (`realpath`, Verknüpfungen nach draußen und `..` werden abgelehnt). Nie aufgelistet werden .git, .ssh, .gnupg, .aws, .claude, .hetzner-app, .config, .cache, node_modules, .venv und ähnliche. Dateien mit Zugangsdaten-Namen (gleiche Regel wie bei den Änderungen) erscheinen als „geschützt“, ihr Inhalt wird nie ausgeliefert; Binärdateien werden nicht gezeigt; Text bis 200 KB.
**Lösung App:** Block „Dateien dieser Karte“ in der rechten Spalte (Ordner klappen beim Antippen auf, werden erst dann geladen), Datei öffnet das Blatt `#datei-blatt` (Markdown gesetzt, sonst Text, Esc schließt).
**Geprüft:** Python-Probe mit Wegwerf-Ordner (.env geschützt, .ssh weg, Verknüpfung nach /etc/passwd abgelehnt, `../` und `.git` abgelehnt); Testserver 8799, Playwright 1500x900: Baum lädt, Ordner klappt auf, CLAUDE.md öffnet, keine Konsolenfehler, Screenshot angesehen; Zeilenumbrüche in Markdown nachgebessert. Ausgerollt, /api/version 212.
**Nicht geprüft:** Handy (Spalte dort versteckt), Bilder (werden als Nicht-Text gemeldet, keine Vorschau), sehr große Ordner.

## 02.11.2026: V213, Kaira-Knopf mit schwebendem Fenster
**Auslöser:** Roli 02.11. 13:41 „22. Ja“, „23. Ja“, „24. Ja“ und 14:24 „1. Ja“ (Kaira-Knopf bauen). Die Kaira-Karte hat die Seite `?fenster=1` fertig und erlaubt das Einbetten durch die Relay-Adresse.
**Lösung:** Neue Umgebungsvariable `HETZNER_APP_KAIRA_FENSTER` (https-Adresse der Kaira-Seite, steht bei Roli in ~/.hetzner-app/umgebung, ohne Einstellung gibt es keinen Knopf, Lea und Lorenz sehen nichts). Endpunkt `GET /api/kaira-fenster` liefert die Adresse, die Content-Security-Policy bekommt dafür `frame-src` (zusammen mit der Vorschau). Knopf mit Sprechblasen-Symbol in der Kopfzeile der Liste und der Sitzung. Das Fenster hängt direkt am Seitenrumpf (nicht in einer Ansicht), ist am Kopf mit Maus und Finger verschiebbar, über die Ecke in der Größe änderbar, und merkt Lage, Größe und offen/zu in localStorage `kaira_fenster_v1`. Der Rahmen hat `allow="microphone"`.
**Fehler unterwegs:** Das Fenster lag zuerst in der versteckten Sitzungsansicht und war nie sichtbar; es wird jetzt beim Start an `document.body` gehängt.
**Geprüft:** Testserver 8799, Playwright 1100x900 und 412x800: Knopf sichtbar, Fenster öffnet, Verschieben, Merken nach Neuladen, Schließen. **Nicht geprüft:** der Inhalt der Kaira-Seite selbst (Testbrowser hat kein Werkstatt-Tor-Cookie, der Rahmen blieb weiß), Mikrofon im Rahmen am Handy. Läuft das Tor-Cookie ab, wird die Anmeldeseite des Tors im Rahmen blockiert.

## 02.11.2026: Automatischer Kartenwechsel (ohne App-Version, läuft per Cron)
**Auslöser:** Roli 02.11. 13:41 „19. Ja“, „20. Ja“ (Kartenwechsel bauen), Reihenfolge Punkt 2.
**Lösung:** Neues Modul `hetzner_app/kartenwechsel.py`, alle 5 Minuten per Cron (`python -m hetzner_app.kartenwechsel`, Probe mit `--probe`, Ausschalten mit Datei ~/.hetzner-app/kartenwechsel.aus, Protokoll ~/logs/kartenwechsel.log, Stand ~/.hetzner-app/kartenwechsel.json). Karte mit mehr als 200.000 Token, still seit 10 Minuten, nicht an einem Gerät geöffnet, ohne offenen Dialog, eigener Ordner: Fehlt eine frische UEBERGABE.md (jünger als eine Stunde), bekommt sie den Auftrag, sie zu schreiben (einmal je 3 Stunden, nicht doppelt zum Übergabe-Wächter). Liegt sie vor, startet eine Folgekarte im selben Ordner (Namenszahl plus eins, gleiche Betriebsart und gleiches Modell) mit „Übergabe lesen“, die alte legt sich schlafen, Telegram über den privaten Bot. Je Karte nur ein Wechsel.
**Geprüft:** Probe ohne Treffer (keine Karte über 200.000); Wegwerf-Karten in /tmp mit Haiku: Folgekarte startet, liest die UEBERGABE.md und fasst sie richtig zusammen, alte Karte schläft; Probekarten und Zustand danach entfernt. **Nicht geprüft:** der Auslöse-Pfad im Cron mit einer echten Karte über 200.000, Telegram-Nachricht, Auftrag-Pfad an eine laufende Karte. Das erste echte Mal bitte im Protokoll nachsehen.

## 02.11.2026: V214, Stille-Erkennung für das Whisper-Diktat
**Auslöser:** Roli 02.11. 10:29 „11. Ja“ (Reihenfolge Punkt 3), 13:41 „17. Ja“ (Absenden nach Sprechpause auch hier).
**Lösung:** In `whisperDiktat` misst ein Analysator den Pegel alle 100 ms. Grundrauschen ist der leiseste bisherige Pegel (höchstens 0,05), als Sprache gilt mehr als das Dreifache, mindestens 0,02. Hat man gesprochen und schweigt danach 2,5 Sekunden, endet die Aufnahme von selbst und geht zur Erkennung. Kommt in 12 Sekunden keine Sprache, wird verworfen (nichts geschrieben, nichts gesendet). Zweiter Tipp beendet wie bisher. Im Freisprech-Modus startet nach dem erkannten Text der bekannte Zähler (2 Sekunden, „Sende in N …“, Stopp, Tippen hält an), dann geht die Nachricht raus (`autoSendePlanen(sekunden)`).
**Fehler unterwegs:** Die erste Fassung eichte das Rauschen in der ersten Dreiviertelsekunde; wer sofort losspricht, wurde als Rauschen gewertet und nie erkannt. Ersetzt durch das laufende Minimum. Außerdem ging beim Test „Hallo Test“ an die eigene Karte, weil die Sendung nicht abfangbar war; künftig nur gegen eine Probekarte testen.
**Geprüft:** Playwright 412x800 mit Fake-Mikrofon (Ton 2 s, dann Stille, Schleife) und vorgetäuschter Erkennung: Aufnahme endet rund 2,5 s nach Tonende, Text im Feld, Zähler „Sende in 2 …“, Nachricht geht raus. **Nicht geprüft:** echtes Sprechen am Handy, laute Umgebung (Auto: Dauerrauschen über 0,02 könnte das Ende hinauszögern, dann beendet nur der zweite Tipp oder die Höchstdauer von 150 s), Verwerfen nach 12 s ohne Sprache im Browser.

## 02.11.2026: Kartendienst für Kaira (ohne App-Version, eigener Dienst)
**Auslöser:** Roli 02.11. 13:41 „22. bis 24. Ja“, 14:25 „52. Ja“, „53. Ja“ (Rechteregel `Kaira-Assistent/RECHTE-KARTEN.md`), 15:32 „1. Ja“ (Dienstzugang bauen).
**Lösung:** Neues Modul `hetzner_app/kartendienst.py`, eigener Dienst `hetzner-kartendienst.service` (Vorlage in `deploy/`, nur 127.0.0.1:8831, nicht hinter Caddy, KillMode=process damit ein Neustart keine Karten mitreißt). Jeder Aufruf braucht `Authorization: Bearer` mit dem Schlüssel aus `~/.kaira-karten-schluessel` (Rechte 600, außerhalb von Git, Vergleich zeitkonstant). Lesen: `GET /karten` (Name, Zustand, Ordner, Kontext-Token, letzte Antwort als eine Zeile, nie der Verlauf), `GET /protokoll`. Schreiben (Kaira holt vorher Rolis Ja ein): `POST /senden`, `/starten` (nur vorhandene Ordner direkt unter ~/projekte, Name ohne `..`), `/schlafen`, `/uebergabe`. Nachrichten tragen den Vorspann „[Kaira im Auftrag von Roli, von ihm bestätigt]“. Harte Grenzen im Dienst: höchstens 10 schreibende Aktionen je Stunde, nicht an arbeitende Karten oder offene Dialoge, nur eigene Karten, Text bis 2.000 Zeichen, keine Löschung, keine Rechte, kein Neustart, keine Zugangsdaten. Jede Aktion steht mit Zeit, Ziel und Wortlaut in `~/logs/kaira-karten.log` (Rechte 600).
**Schlüssel:** Selbst erzeugt, im Katalog `leitstand/schluessel_katalog.py` unter INTERN als `kaira-karten` eingetragen (ersetzbar, nicht in Bitwarden markiert). Neu erzeugen: Datei löschen, neue Zeile schreiben, Dienst neu starten.
**Geprüft:** ohne und mit falschem Schlüssel 401; Lesen zeigt alle Karten mit einer Zeile; zweite Instanz auf Port 8832 mit höherer Kartengrenze: Karte starten mit Auftrag, Nachricht senden (die Karte antwortete beide Male richtig), schlafen legen, Protokoll vollständig; ungültiger Ordner, fehlende Karte und die Kartengrenze von zehn werden abgelehnt. Probekarte und Ordner danach entfernt. **Nicht geprüft:** die Bremse von zehn je Stunde im Lauf, `/uebergabe`, Kairas eigener Aufruf (baut die Kaira-Karte).

## 02.11.2026: V215, Kaira-Knopf öffnet ein eigenes Fenster statt eines Rahmens
**Auslöser:** Roli 02.11. 16:01 „kaira karte geht auf aber bekommt keine verbindung“, 16:11 „kaira.65-21-246-222.sslip.io hat die Verbindung abgelehnt“, 16:14 „1. Ja“ (auf eigenes Fenster umstellen), „2. Deine Empfehlung“ (Cookie-Umstellung am Tor nicht beauftragen).
**Befund:** Beim Öffnen des Rahmens kam bei Kaira keine einzige Anfrage an (journalctl kaira), Kairas Antwort selbst verbietet das Einbetten nicht. Wahrscheinliche Ursache (nicht bewiesen): Das Anmelde-Cookie des Werkstatt-Tors (SameSite=Lax) wird im Rahmen nicht mitgeschickt, das Tor leitet um, und die Relay blockiert den Sprung zu tor.* per frame-src.
**Lösung:** Der Knopf öffnet `window.open(adresse, "kaira-fenster", "popup=yes,width=400,height=680")` (am Handy ein neuer Tab). Das schwebende Fenster (HTML, CSS, JS) ist entfernt, die Content-Security-Policy gibt nur noch die Vorschau-Herkunft für frame-src frei. Der Endpunkt `/api/kaira-fenster` und die Umgebungsvariable `HETZNER_APP_KAIRA_FENSTER` bleiben. Das Tor und Caddy wurden nicht angefasst.
**Geprüft:** Testserver 8799, Playwright: Knopf sichtbar, Klick öffnet ein neues Fenster auf die Kaira-Adresse (im Testbrowser ohne Tor-Cookie folgt die Tor-Umleitung), keine Konsolenfehler der App. **Nicht geprüft:** am Handy. Ein schwebendes Fenster wäre später wieder möglich, wenn das Tor-Cookie in Rahmen mitgeschickt wird.

## 02.11.2026: V216, Baustein 17: Cache-Uhr unter dem Eingabefeld
**Auslöser:** Roli 02.11. 17:07 „1. Ja“ (Cache-Uhr als Nächstes aus dem Bauplan der Monitor-Ansicht).
**Lösung:** Kleine Zeile `#cache-uhr` unten im Eingabefeld. Der Stand (Restwärme, warm oder kalt) kommt mit dem bestehenden Kontext-Abruf (`k.cache`), die Sekunden zählt die App jede Sekunde selbst weiter: „Cache warm, noch 41:53“. Ist die Karte groß (ab 100.000 Token) und bleiben unter fünf Minuten, steht „⚠ Cache läuft in 3:19 ab, jetzt ist eine Übergabe günstig“. Kalt: „Cache kalt seit 10 min“, bei großer Karte mit „⚠ … der nächste Zug ist teuer“. Warnung immer mit Zeichen und Wort, nicht nur Farbe (Rot-Grün-Schwäche). Die Uhr gehört nur zur geöffneten Karte.
**Geprüft:** Playwright 412x800 mit vorgetäuschtem Kontext-Abruf: Uhr zählt herunter, Warnung unter fünf Minuten bei großer Karte, kalt mit und ohne Warnung; Screenshot angesehen; keine Konsolenfehler. **Nicht geprüft:** Handy, die echte Abruf-Taktung (zeigt Wechsel warm zu kalt erst mit dem nächsten Abruf, wenige Sekunden später). Das Kontingent („76 % übrig“) bleibt offen, hat nur Claude selbst.

## 02.11.2026: Baustein 18, Kleinversuch /context (nichts gebaut)
**Auslöser:** Roli 02.11. 18:14 „1. Ja“ (Kleinversuch /context für Baustein 18, Kontext nach Posten).
**Versuch:** Probekarte (Haiku, eigene tmux-Sitzung `-L ctxtest2`, leerer Ordner /tmp/k_ctx), `/context` getippt, Schirm mit `capture-pane -S -2000` gelesen.
**Ergebnis:** In tmux kommt lesbarer Text. Gesamtausgabe rund 390 Zeilen, aber die Kopfzeilen sind sauber auslesbar: „45.2k/1m tokens (5%)“ sowie je eine Zeile für System prompt, System tools, MCP tools, MCP server instructions, Custom agents, Memory files, Skills, Messages, Free space, Autocompact buffer, jeweils „Name: Zahl tokens (Prozent)“. Darunter folgt der lange Baum (├ …) je Werkzeug, Fachkraft und Skill, der für die Anzeige nicht gebraucht wird. Das Fenster ist auf Rolis Server 1m Token groß (Probekarte).
**Berichtigung zum früheren Eintrag (Baustein 3):** Dort stand, die Ausgabe sei als Anzeige zu fragil. Die neun Summenzeilen sind es nicht; fragil ist nur der Baum und das Hineinschreiben in den echten Schirm.
**Offenes Problem:** `/context` in eine echte Karte zu tippen, schiebt deren Schirm und kostet einen Zug in ihrem Verlauf. Gangbare Wege: nur in Ruhe-Karten abfragen und den Schirm danach wieder auf Eingabe zurücksetzen, oder die Posten aus der Mitschrift schätzen (Messages ist dort die einzige echte Größe). Nicht entschieden, nichts gebaut.
**Aufgeräumt:** tmux-Server ctxtest2 beendet, Ordner und Zwischendateien gelöscht.

## 02.11.2026: V217, Baustein 9: Laufende Befehle mit Stopp
**Auslöser:** Roli 02.11. 20:14 „2. Ja“ (mit Baustein 9 weitermachen), „1. Nein“ (Baustein 18 nicht mit Abfrage an ruhenden Karten bauen, bleibt zurückgestellt).
**Kleinversuch:** Claude Code startet jeden Shell-Befehl als `bash -c … eval '<Befehl>' < /dev/null` direkt unter dem `claude`-Prozess der Karte, als eigener Prozessgruppen-Leiter. Laufzeit steht in der Prozessliste (`etimes`), den Befehlstext liest man aus dem `eval '…'`. Hintergrund- und Vordergrundbefehle sehen gleich aus; beide gelten als „läuft gerade“.
**Lösung:** Neues Modul `hetzner_app/hintergrund.py`. `aufgaben(name)` sucht unter den Panes der Karte den `claude`-Prozess und listet nur dessen direkte Befehls-Kinder (Befehl bis 300 Zeichen, Laufzeit). `stoppen(name, pid)` prüft bei jedem Aufruf neu, dass die Pid ein solches Kind dieser Karte ist, und sendet SIGTERM an die Prozessgruppe, damit auch Unterprozesse enden. Endpunkte `GET /api/sessions/{name}/befehle-laufend` und `POST …/befehle-laufend/{pid}/stopp` (409, wenn fremd oder weg). App: Block „Laufende Befehle“ in der rechten Spalte, Abfrage alle 4 Sekunden, Laufzeit zählt zwischen den Abfragen weiter, Stopp fragt vorher per Bestätigung nach.
**Geprüft:** Python: eigener `sleep` wird gelistet und beendet; Shell der Pane, `claude` selbst, Pid 1 und eine Pid einer anderen Karte werden abgelehnt, `claude` lief weiter. Probekarte (Haiku) mit `sleep 300` im Hintergrund: Testserver 8799, Playwright 1500x900, Block zeigt Befehl und Laufzeit, Stopp mit Rückfrage beendet ihn, Liste zeigt danach „Gerade läuft kein Befehl.“, keine Konsolenfehler, Screenshot angesehen. Probekarte, Eintrag in sitzungen.json und Testdateien entfernt.
**Nicht geprüft:** Handy (Spalte dort versteckt), Karten fremder tmux-Server, Befehle mit Anführungszeichen in sehr langen Texten (Text wird nur gekürzt angezeigt). Einen reinen Vordergrundbefehl zu stoppen wirkt wie Esc: Claude meldet ihn als fehlgeschlagen.

## 03.11.2026: Baustein 15, Kleinversuch /output-style (nichts gebaut)
**Auslöser:** Roli 03.11. 22:27 „1. Ja, läuft alles“ (Handyprobe bestanden, mit Baustein 15 weitermachen).
**Versuch:** Probekarte (Haiku, eigene tmux-Sitzung, leerer Ordner /tmp/k_stil), `/output-style` und `/output-style Concise` getippt.
**Ergebnis:** Beide Befehle liefern lesbaren Text, kein Auswahlmenü. Ohne Wort: „Output style: <aktuell>“ und eine Zeile je Stil („- Name (current): Beschreibung“); auf Rolis Server stehen default, Proactive, Concise, Explanatory, Learning und roli-koffer:Klarschrift zur Wahl. Mit Wort: „Output style set to Concise“.
**Wichtig:** Das Setzen schreibt `{"outputStyle": "Concise"}` in `<Kartenordner>/.claude/settings.local.json`. Es gilt also für alle Karten und Folgekarten in diesem Ordner, nicht nur für eine. Ob der neue Stil in der laufenden Sitzung sofort greift oder erst im nächsten Gespräch, ist nicht geprüft (Claude Code hält den Systemprompt aus Cache-Gründen meist fest).
**Folge für den Bau:** Anzeige des aktuellen Stils ist ungefährlich (nur lesen, `/output-style` in Ruhe-Karte tippen schiebt aber deren Schirm, wie bei /context). Wechseln ist riskant: Rolis Karten brauchen Klarschrift (Fertig-Meldung, nummerierte Fragen), und ein Wechsel auf Concise würde das für den ganzen Ordner aushebeln. Der zweite Teil des Bausteins (Transkript-Ansicht, wie viel von Claudes Arbeit der Verlauf zeigt) ist unberührt.
**Aufgeräumt:** tmux-Server und Ordner gelöscht. Entscheidung von Roli steht aus, nichts gebaut.

## 03.11.2026: Baustein 15, Anzeige des Ausgabestils nicht gebaut (Quelle lügt)
**Auslöser:** Roli 03.11. 22:29 „1. Ja“ (nur Anzeige des Stils bauen), „2. Ja“ (danach Transkript-Ansicht prüfen).
**Befund:** Die Klarschrift-Datei des Koffer-Plugins trägt `force-for-plugin: true`. Solange das Plugin aktiv ist, gilt Klarschrift für jede Karte, unabhängig vom Eintrag `outputStyle` in den Einstellungen. Beleg: Probekarte (Haiku, leerer Ordner) meldet bei `/output-style` „default (current)“, nennt auf die Frage nach ihrem Stil im Systemprompt aber „roli-koffer:Klarschrift“. In Rolis Einstellungen und im Hetzner-App-Ordner steht kein `outputStyle`.
**Folge:** Weder `/output-style` noch die Einstellungsdateien sagen, welcher Stil wirklich gilt. Eine Anzeige daraus würde überall „default“ zeigen, also falsch. Deshalb nichts gebaut, keine Version. Außerdem gilt die Warnung vom Kleinversuch (Wechsel auf Concise nähme Rolis Regeln weg) wohl nicht: Klarschrift ist erzwungen. Auch das ist nicht mit einem Wechsel in einer Karte geprüft.
**Offen:** Wer den Stil sicher anzeigen will, müsste die Plugin-Regel selbst nachbilden (Plugin aktiv, Datei mit force-for-plugin, dann dieser Name), das wäre eine Annahme und kein Messwert. Transkript-Ansicht noch nicht geprüft.
**Aufgeräumt:** Probekarten (tmux-Server ostest, ostest2) und Ordner gelöscht.

## 03.11.2026: V218, Baustein 15: Verlauf mit Arbeitsschritten (Transkript-Ansicht)
**Auslöser:** Roli 03.11. 22:32 „1. Ja“ (Stil-Anzeige streichen, mit der Transkript-Ansicht weitermachen, erst als Kleinversuch).
**Kleinversuch:** Die Werkzeugschritte liefert der Server schon (`mitschrift.py` Typ „werkzeug“, etwa „Bash(…)“), die App warf sie in `zusammenfassen()` weg. Damit braucht die Ansicht keine neue Serverarbeit und keinen Eingriff in die Karte.
**Lösung:** Schalter „Verlauf“ in den Einstellungen mit zwei Wahlen („Nur das Gespräch“, „Mit Arbeitsschritten“), gemerkt je Gerät in localStorage `verlauf_arbeit`. Ist er an, behält `zusammenfassen()` die Werkzeugblöcke als leise graue Zeilen (vorhandene Gestaltung `.notiz.werkzeug`), der Verlauf wird sofort neu gezeichnet. Standard ist aus, ändert sich also für niemanden etwas ohne Zutun. Stil-Anzeige (zweiter Teil des Bausteins) ist gestrichen, siehe Eintrag davor.
**Geprüft:** Testserver 8799, Playwright 1500x900 gegen die laufende Karte Hetzner-App 12 (nur lesen): ohne Schalter 0 Werkzeugzeilen, mit Schalter 73, danach wieder 0, keine Konsolenfehler, beide Bilder angesehen. **Nicht geprüft:** Handy-Format (Einstellungen dort aus der Liste erreichbar, Verlauf unverändert gebaut), sehr lange Verläufe mit tausenden Zeilen, Verhalten der Antwort-Tasten unter einer Werkzeugzeile mit Schalter an, Englisch (Texte stehen nur auf Deutsch, Englisch kommt zum Schluss).

## 03.11.2026: Baustein 11, Anklicken und Kommentieren: Machbarkeit geprüft, noch nichts gebaut
**Auslöser:** Roli 03.11. 22:48 „1. Ja“ (Baustein 11 angehen; meine Empfehlung war Nein, er wollte es trotzdem).
**Befund:** Die Vorschau lädt Seiten von `https://seiten-roli.…sslip.io` in einem Rahmen der Relay-Seite. Das sind zwei verschiedene Herkünfte, die App kann deshalb nicht in die Seite hineinsehen und keine Elemente anklicken oder auslesen. Der Webspace ist ein schlichter `python3 -m http.server` (Dienst seiten-roli, Port 8803) hinter Caddy; Caddy und Tor bleiben unberührt.
**Wege:** (A) Ein kleiner eigener Auslieferer statt `http.server`, der bei HTML-Seiten mit `?kommentieren=1` ein Hilfsskript anhängt. Das Skript markiert beim Überfahren das Element, meldet beim Anklicken per `postMessage` Selektor, Beschriftung und Text an die App (die App prüft `event.origin` gegen die Vorschau-Herkunft). Die App sammelt die Kommentare und sendet sie gesammelt an die Karte. Ohne den Parameter bleibt jede Seite unverändert. (B) Seiten über die Relay selbst ausliefern und dort das Skript einsetzen: abgelehnt, weil fremder oder eigener Seitencode dann in der Herkunft der App läuft (Zugriff auf Anmeldung und Karten).
**Empfehlung:** A, in drei Teilen: erst Auslieferer mit Hilfsskript und Versuch an einer Probeseite, dann Sammelliste und Senden in der App, zuletzt Feinheiten (Kommentar bearbeiten, Rahmen um das gewählte Element). Aufwand etwa ein halber bis ein Tag. Der Dienst seiten-roli gehört nicht der Hetzner-App-Karte allein (auch Lea und Lorenz haben eigene Webspaces mit gleichem Aufbau).
**Offen:** Entscheidung von Roli zu A und zum Umbau des Dienstes seiten-roli.

## 04.11.2026: V219, Pfeile an der Schnellbefehl-Reihe und fester Platz für Medienwerk
**Auslöser:** Roli 04.11. 14:01 „wieso kann ich auf dem Laptop nicht nach rechts oder links scrollen, es wird abgeschnitten“, 14:09 „1. Ja“ (Pfeile und Ziehen). Dazu 04.11. 13:38 „210. Ja“ (über Medienwerk 160) und 14:09 „2. Ja“: Karte aus dem Ordner Medienwerk steht ganz oben.
**Befund Reihe:** Seitliches Rollen gab es seit V191 (Mausrad über der Reihe, dünne Leiste), im Test bei 1100 Pixeln ging es. Es fehlte der sichtbare Hinweis, dass es weitergeht.
**Lösung Reihe:** Pfeilknöpfe links und rechts (nur am Rechner mit Maus, nur wenn etwas abgeschnitten ist) und Ziehen mit der linken Maustaste; der Klick nach dem Ziehen wird geschluckt, damit kein Befehl gesendet wird.
**Lösung Platz:** `FESTE_ORDNER = ["Medienwerk"]` in `state.py` und `app.js`. Angeheftete Karten aus diesen Ordnern stehen in der Gruppe „Fest oben“ vor „Wartet auf dich“, festgemacht am Ordnernamen, nicht am Kartennamen. Ohne Anheften greift es nicht. Weitere Ordner einfach in die Liste eintragen.
**Geprüft:** Playwright mit vorgetäuschter Kartenliste: Reihenfolge Fest oben, Wartet, Angeheftet stimmt, auch wenn Medienwerk die älteste Aktivität hat; Pfeil rechts rollt, Pfeil links erscheint; Screenshot angesehen. **Nicht geprüft:** Ziehen mit echter Maus, echter Kartenwechsel, Handy (Pfeile dort ausgeblendet).

## 04.11.2026: Baustein 11, Teil 1: Auslieferer mit Hilfsskript für den Kommentiermodus
**Auslöser:** Roli 04.11. 14:21 „3. Ja“ (Weg A, zuerst nur für Rolis Webspace).
**Lösung:** `deploy/seiten_auslieferer.py` ersetzt `python3 -m http.server` im Dienst seiten-roli (nur ExecStart geändert, Sicherung der alten Unit in `~/.hetzner-app/seiten-roli.service.vorher`). Verhält sich wie vorher, nur HTML-Seiten mit `?kommentieren=1` bekommen vor `</body>` das Skript `deploy/kommentier-hilfe.js` (Rahmen beim Überfahren, Klick wird abgefangen, `postMessage` mit Typ `relay-kommentar`, Seite, Selektor, Tag, Text bis 200 Zeichen an die umgebende Herkunft). Caddy und Tor unberührt. Lea und Lorenz laufen noch auf dem alten Server, Umstellung erst auf Wunsch.
**Geprüft:** Ohne Parameter ist die Seite byte-gleich, mit Parameter genau ein Skript; im Rahmen einer Seite anderer Herkunft kommen beide Klicks (Überschrift, Link) als Nachricht an, der Link navigiert nicht; öffentlich über die sslip-Adresse mit und ohne Parameter geprüft. Probeseite: `~/seiten/probe-kommentieren/`. **Nicht geprüft:** Handy, Seiten ohne `</body>`, Verzeichnis ohne Schrägstrich am Ende (liefert die Startseite ohne Umleitung).
**Nächster Teil:** Sammelliste und Senden in der App (Teil 2), Feinheiten (Teil 3).

## 04.11.2026: V220, Baustein 11, Teil 2: Kommentieren in der Vorschau
**Auslöser:** Roli 04.11. 14:22 „4. Ja“ (Teil 2: Schalter, Sammelliste, Senden).
**Lösung:** Im Vorschau-Block der rechten Spalte steht der Schalter „Kommentieren: aus/an“. An: Die Seite lädt mit `?kommentieren=1`, jeder Antipper (Hilfsskript aus Teil 1) legt einen Eintrag mit Selektor und Text in die Liste, daneben ein Feld für den Kommentar und „Entfernen“. Darunter: „An die Karte senden“ (über `sendeInSitzung`, nicht während Claude arbeitet), „Ins Eingabefeld legen“ (zum Nachlesen und selbst Senden) und „Leeren“. Der Satz an die Karte nennt Seite, Nummer, Element, Text und Kommentar. Die App nimmt Nachrichten nur an, wenn `event.source` der Vorschau-Rahmen und `event.origin` die Webspace-Herkunft ist. Einträge ohne Kommentar werden nicht mitgesendet.
**Geprüft:** Testserver 8799 mit der echten Vorschau-Basis, Playwright 1500x900: Probeseite gewählt, Schalter an, zwei Klicks im Rahmen ergeben zwei Einträge, Kommentare getippt, „Ins Eingabefeld legen“ erzeugt den richtigen Text, keine Konsolenfehler, Screenshot angesehen. Dabei zeigte die Liste auch „Fest oben“ mit der echten Medienwerk-Karte. **Nicht geprüft:** „An die Karte senden“ an eine echte Karte, Handy (die Spalte ist dort versteckt, der Kommentiermodus damit auch), Einträge bleiben nicht über Neuladen erhalten.
**Teil 3 offen:** Rahmen um das gewählte Element bleibt stehen, Eintrag antippen springt zum Element, Kommentare merken.

## 04.11.2026: V221, Wert ohne Abo im Verbrauchsblatt (Brain 67)
**Auslöser:** Roli 14:34 „46. Ja“ (Euro-Zeile auch im Relay), 20:37 „47. Deine Empfehlung, 48. Deine Empfehlung“ (Wert der einzelnen Karte, Umbau durch das Brain selbst).
**Lösung:** `verbrauch.gegenwert(cwd)` rechnet die ganze jüngste Mitschrift der Karte zum API-Listenpreis (gleiche Preistabelle wie leitstand/token-bauen.py, doppelt geführt; bei neuen Modellen beide nachtragen), dieselbe Antwort wird nur einmal gezählt. Kurs aus `~/.claude/kurs-usd-eur.json` (schreibt der LEIT//PULS), fehlt er, steht der Betrag in Dollar. Die Schnittstelle `/api/sessions/<name>/verbrauch` liefert `gegenwert`, das Blatt zeigt die Zeile „Wert ohne Abo“ mit dem Hinweis „Nicht deine Rechnung“. Ergebnis wird je Datei zwischengespeichert (erster Lauf 0,01 s).
**Geprüft:** Python und app.js kompilieren, Funktion direkt gegen die laufende Karte (2,32 € bei 49 Zügen), Dienst neu gestartet, /api/version meldet 221. **Nicht geprüft:** das Blatt im Browser (Anmeldung am Testserver nicht aufgesetzt), httpx2 fehlt für den TestClient und wurde nicht installiert. Roli schaut am Handy nach.

## 07.11.2026: V221, Antwort-Tasten und Vorschlag räumen sich auf
**Auslöser:** Roli 07.11. 18:57 Bild vom Handy (Karte Krugmeister-Brain), 19:04 „die ganzen Fragen verschwinden nicht, obwohl sie schon beantwortet sind oder ältere dabei sind“.
**Befund:** Am echten Verlauf von Krugmeister-Brain geprüft (nur gelesen). Drei Ursachen: (1) Eine Antwort per Foto mit Unterschrift („16. Schau Bild an …“) hat die Klasse `foto`, nicht `gesagt`, und zählte deshalb nie als Antwort auf die Frage. (2) Der Vorschlag über dem Eingabefeld nahm auch die schon erledigten Reihen mit, daher „1. 2. 19. 20“ zwischen den anderen. (3) Fragen, die er frei ohne Nummer beantwortet („Leider geht der Knopf nicht“), blieben für immer offen, bis hinauf zu Nr. 8.
**Lösung:** Fotos mit Unterschrift zählen als Antwort. Der Vorschlag nimmt nur Reihen ohne `erledigt`. Nur die beiden jüngsten Antworten der Karte halten Fragen offen, ältere gelten als überholt. Das überstimmt teilweise den Beschluss vom 02.11. („Tasten bleiben unter jeder offenen Frage“), jetzt mit Grenze zwei Antworten.
**Geprüft:** Gleicher Verlauf vorher und nachher im Testbrowser: vorher 14 offene Reihen von Nr. 8 bis 24, nachher nur noch 24 und 25. **Nicht geprüft:** Handy, Karten, in denen er bewusst über mehr als zwei Antworten hinweg etwas offen lassen will (dort fehlen die Tasten, tippen per Hand geht).

## 08.11.2026: V222, Kopfzeile der Karte kompakter
**Auslöser:** Roli 08.11. 09:33 (Handybild): das Fenster werde eng, in der zweiten Zeile sei viel Platz, „Cache kalt“ stehe doppelt da.
**Lösung:** Der Kontext-Balken (Schiene mit Text) sitzt jetzt in der Zeile des Modus und des Modells statt in einer eigenen Zeile darunter, das spart eine Zeile. Der Cache-Hinweis oben rechts ist weg, er steht nur noch in der Cache-Uhr unter dem Eingabefeld (der Text wird im Hintergrund weiter gesetzt, die Spalte „Zur Hand“ liest ihn). Klick auf den Balken öffnet wie vorher das Verbrauchs-Blatt, die Zeile reagiert nicht doppelt.
**Geprüft:** Testserver 8799, Playwright 412x800 gegen Hetzner-App 13: eine Zeile, Klick öffnet genau ein Blatt, keine Konsolenfehler, Bild angesehen. **Nicht geprüft:** echtes Handy, sehr lange Modellnamen, Zustand mit Warnfarbe des Balkens (Farbe wie vorher).
