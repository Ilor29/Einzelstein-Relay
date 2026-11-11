# Project Handoff: Hetzner-App (Relay)

Version: v04 (ersetzt die Übergabe von 22:10)
Date: 2026-11-11, gegen 23:55
Owner/User: Roli
Prepared by: Claude (Karte Hetzner-App 18)

Wahrheit liegt in `BAUBUCH.md` (Ende, Einträge V239 bis V245 vom 11.11.) und `~/projekte/Brain/REGISTER.md` (Einträge „Hetzner-App 18“). Diese Datei fasst nur zusammen. Vor dem Weiterbauen dort nachlesen.

## 1. Project Goal

Relay: Web-App (PWA) plus FastAPI-Dienst, mit der Roli Claude-Code-Sitzungen vom Handy und Tablet aus bedient (tmux auf dem Server, Vorlesen mit Piper, Diktat). Seit dem 11.11. läuft eine Durchsicht der ganzen App, die Funde werden einzeln behoben, je mit eigener Version, Test und Baubuch-Eintrag.

## 2. Current Status

Relay V245 läuft (`curl -s localhost:8787/api/version`), alles committet und auf `github main` gesichert, Arbeitsordner sauber. Nichts ist angefangen und halb liegen geblieben. Piper antwortet nach dem Neustart auf `/voices` (der Start dauert etwa 25 Sekunden). Geprüft wurde im Browser (Playwright, Testserver 8799, Scheinkarten, Schein-WebSocket, Schein-Ton) und mit Probe-Skripten. Am Handy ist von V235 bis V245 nichts geprüft, mit Ausnahme der Handyprobe 18 bis 26 für frühere Stände.

## 3. What Changed in This Session

- V239 Neue Karte: Ohne Suchtreffer ist kein Ordner mehr gewählt, `neueKarteLaeuft` sperrt Doppeltipp, abgelehnte Benachrichtigung meldet sich nach dem Start.
- V240 Vorschau: nach einem Fehler von `/vorschau` höchstens alle 30 Sekunden neu fragen (`vorschauFehlerAm`).
- V241 Lupe im Verlauf: stilles Auffrischen behält den Treffer und lässt das Mitlaufen an (`trefferZeigen(i, scrollen)`), Sprung zu einem Treffer in einem zugeklappten Code-Block klappt ihn auf.
- V242 Vorlesen: zwei rasche Sprünge im Strom brechen den Vortrag nicht ab (`stromSprungLauf`, Ziel sofort merken), Stopp in der Startphase räumt Leiste und Dauerton auf, `onended` gibt Tonquellen frei, `tonUhrQuelle` macht den Wach-Bericht auch beim Android-Strom möglich.
- V243 Vorlese-Leiste: neue Knöpfe „Einen Satz zurück“ und „Einen Satz vor“ (rufen `springe(-1)` und `springe(1)`).
- V244 Terminal: `anSteckdose` schickt sofort oder merkt Eingaben bis zum Öffnen, `steckdoseWeg` leert die Warteschlange beim Kartenwechsel, `open`, `message` und `close` zählen nur für die aktuelle Verbindung.
- V245 Server: `_im_gange` hält den Speicherwächter von einem sprechenden Piper fern, `_ist_unser_piper` vergleicht `--port` genau, `geraete.erlauben` nummeriert doppelte Gerätenamen („(2)“).

## 4. Decisions Made

- Roli 11.11. 22:28 „33. Ja“: „Neue Karte“ beheben (V239). Er schickte dabei die Frage, wie wir Artefakte haben; Antwort: keine aus dem Claude-Chat, Entwürfe liegen im eigenen Webspace. Die neuen Tabellen und Whiteboards von Anthropic habe ich nicht geprüft (Link nicht gelesen).
- Roli 11.11. 22:30 „34. Ja“: Vorschau (V240). 22:32 „35. Ja“: Lupe (V241). 22:35 „36. Ja“: Vorlesen (V242).
- Roli 11.11. 22:52 „37. Wo soll das gehen? Vor zurück knopf“: Es gab in der App keinen solchen Knopf, nur Medientasten. Daraus 22:57 „39. Ja,“: Knöpfe in die Leiste (V243).
- Roli 11.11. 23:18 „38. Deine Empfehlung“ (Terminal angehen, V244) und „40. Deine Empfehlung“ (Handyprobe zum Vorlesen durch ihn, kommt später).
- Roli 11.11. 23:28 „41. Ja“: Rest von Befund 15 (V245).
- Ohne eigenen Beschluss gewählt, bei Roli unbestätigt: dunkle Schrift auf den orangen Knöpfen im Dunkelmodus (V236); doppelte Gerätenamen bekommen ein „(2)“ statt abgewiesen zu werden (V245).

## 5. Important Files and Locations

- `hetzner_app/server.py` (VERSION 245), `hetzner_app/tts.py` (`_im_gange`, `_piper_sprechen`, `_ist_unser_piper`, `speicher_pruefen`), `hetzner_app/geraete.py` (`erlauben`), `web/app.js` (`verbinde`, `anSteckdose`, `stromSpringe`, `sprichHaeppchen`, `verlaufDurchsuchen`, `zurHandVorschau`), `web/index.html` (Vorlese-Leiste, Symbole `i-satz-zurueck`, `i-satz-vor`).
- `BAUBUCH.md`, `~/projekte/Brain/REGISTER.md`, Zweitgehirn `~/Notizen/02 Projekte/Einzelstein Relay.md` (die Beschlüsse 33 bis 41 dieser Karte sind dort noch NICHT nachgetragen, bitte nachholen).
- Prüf-Skripte dieser Karte in `/var/tmp/v239/` (`probe.py` Neue Karte, `probe240.py`, `probe241.py`, `probe242.py` Vorlesen, `probe243.py` plus `probe243_run.py`, `probe244.py` Terminal mit Schein-WebSocket, `probe245.py` Server ohne `tts`-Import) und ältere in `/var/tmp/rennen235/` (`ts.py` startet den Testserver). Sie liegen nicht im Repo, dienen als Vorlage.

## 6. Open Tasks

Offen bei Roli (Nummern laufen weiter, zuletzt vergeben 42):
- 27. Relay-App am Tablet deinstallieren und neu installieren (Manifest-Änderung aus V234).
- 28. Am Tablet im Querformat nachsehen, ob zwei oder drei Spalten erscheinen.
- 30. Soll ich selten gebrauchte Symbole aus der Kopfzeile der Karte ins Drei-Punkte-Menü verschieben? Empfehlung: Ja, sobald Roli sagt, welche er selten braucht; Kandidaten Linkliste, Sichern, Anheften.
- 40. Handyprobe Vorlesen: etwas vorlesen lassen, zweimal schnell auf „Einen Satz vor“ in der Leiste tippen, sagen ob der Vortrag weiterläuft und wie die Stimme klingt (Roli hat „Deine Empfehlung“ gesagt, also macht er es später).
- 42. Soll ich die XSS-Gegenprobe über `.md`-Inhalt im Browser machen? Empfehlung: Ja, einziger offener Punkt mit möglichem Sicherheitsrisiko. **Noch nicht beantwortet, nicht begonnen.**
- Rückmeldung, ob die dunkle Schrift auf den orangen Knöpfen gefällt.

Offen bei mir, Rolis Wahl nötig:
- Barrierefreiheit: „Claude anhalten“, „Nebenfrage stellen“ und Dateibaum-Zeilen unter 40 Pixel hoch, kein Fokusfang in Blättern, Kontrast in Einstellungen, Bibliothek und heller Fassung nicht gemessen.
- `tts.py`: Der Google-Weg fängt ungültiges JSON nicht als `TTSError` (der Strom meldet es seit V233 allgemein).
- Höchstens fünf Erweiterungen mit widerlegendem Test sind noch nicht vorgeschlagen.

Weiter offen aus früheren Karten: Skillkontor-Marketing 39 (gemerkt „fable“, geantwortet hat Sonnet 5.5; ungeklärt). Fund von Krugmeister-Brain 47 (Register 10.11. 23:00): Vorschlagszeile listet alte, schon beantwortete Fragenummern; nicht untersucht. Verhalten im Auto frühestens um den 22.11. Baustein 16 zwei Karten nebeneinander, Baustein 11 Teil 3, Auslieferer für Lea und Lorenz, Englisch zum Schluss, Baustein 18 zurückgestellt, Remote Control liegt.

## 7. Known Issues / Risks

- V235 bis V245 sind am Handy und Tablet nicht geprüft; die Browserproben nutzen Scheinantworten, Schein-WebSocket und Schein-Ton, nicht die echte Stimme oder das echte Terminal.
- Die neun Symbole in der Kopfzeile der Karte sind am Handy 30 Pixel breit (Frage 30).
- Der Testserver zeigt alle echten Karten, schreibende Klicks wirken auf sie. Nur mit Scheinkarten arbeiten (`page.route`), Karten mit `oeffneSitzung(objekt)` per `evaluate` öffnen, nie über Fließtext klicken.
- Nach einem Neustart des Dienstes braucht Piper rund 25 Sekunden, bis `/voices` antwortet; nicht vorschnell als Fehler werten.

## 8. Next Recommended Step

Rolis Antwort auf 42 abwarten. Bei Ja die XSS-Gegenprobe machen: Scheindatei mit Script- und Ereignis-Anteilen als `.md` über den Dateibaum-Blatt-Weg öffnen und im Browser prüfen, ob etwas ausgeführt wird; Ergebnis ins Baubuch. Danach die Barrierefreiheits-Reste einzeln.

## 9. Context for Future Claude Sessions

- Pro Änderung an App oder API `VERSION` in `hetzner_app/server.py` hochzählen, dann `sudo systemctl restart hetzner-app.service` und `curl -s localhost:8787/api/version`. Einzeln committen mit deutscher Nachricht und `git push github main`.
- Die automatische Sicherung committet alle 10 Minuten mitten in die Arbeit. Für eine Gegenprobe mit altem Code `git show HEAD:web/app.js > web/app.js`, danach die neue Fassung aus einer Kopie zurücklegen und `git status` prüfen.
- Testserver: Skript `/var/tmp/rennen235/ts.py` (Port 8799, Anmeldung ausgehängt) mit `.venv/bin/python -I` starten, Beenden mit `fuser -k 8799/tcp`. Playwright aus `~/werkzeuge/browser/.venv`, Kontext mit `bypass_csp=True`, Tour-Schalter `relay_tour_liste_v1` und `relay_tour_sitzung_v1` auf "1". Für Vorlese-Tests Chromium mit `--autoplay-policy=no-user-gesture-required` starten.
- Testmuster: Ein Test zählt erst, wenn er mit dem alten Code durchfällt. Antworten festhalten statt `time.sleep`. Aufrufe nacheinander mit Pausen testen, nicht alle auf einmal (V240). Globale `let`-Variablen von `app.js` sind per `evaluate` erreichbar (`aktuelleSitzung`, `steckdose`, `spricht`, `aktiveQuellen` und so weiter), `sitzungen` nicht.
- Nie `tts` aus einem zweiten Python-Prozess importieren. Funktionen daraus per `ast` aus dem Quelltext lösen (Muster in `/var/tmp/v239/probe245.py`). Echte Prozesse nie beenden, nur die Erkennung prüfen.
- Vor einer Prüfbitte an Roli erst nachsehen, ob der Bedienweg in der App überhaupt existiert (Lehre aus V243).
- Aus Prozess-Umgebungen und Zugangsdateien nur Namen ansehen, nie Werte ausgeben.
- Antworten kurz und hörbar, normale Sätze, Fragen als nummerierte Zeile mit Empfehlung und Fragezeichen, am Ende „Fertig.“, offene Punkte unaufgefordert nennen.
- Rolis letzter Wortlaut: „[11.11. 23:28] 41. Ja“. Davor 23:18 „38. Deine Empfehlung, 40. Deine Empfehlung“.
