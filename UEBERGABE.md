# Übergabe Hetzner-App (Relay), 08.11.2026, Hetzner-App (Relay, Einzelstein-Fernbedienung)

Version: v01
Date: 2026-11-08
Owner/User: Roli
Prepared by: Claude (Karte Hetzner-App 13)

## 1. Project Goal
Web-App plus FastAPI-Dienst, mit der Roli Claude-Code-Sitzungen (tmux auf dem Server) vom Handy bedient, mit Vorlesen und Diktat. Wahrheit liegt in BAUBUCH.md und ~/projekte/Brain/REGISTER.md.

## 2. Current Status
Relay V223 läuft und ist auf GitHub gesichert, Arbeitsordner sauber. Hinweis: Es gibt zwei Commits mit dem Titel „V221“ (meiner: Antwort-Tasten aufräumen; ein fremder: Verbrauchsblatt mit Euro-Wert). Die laufende Version ist 223, daher kein Schaden, aber beim Nachlesen beachten.

## 3. What Changed in This Session
- V219: Pfeilknöpfe und Maus-Ziehen an der Schnellbefehl-Reihe; fester Platz „Fest oben“ für die angeheftete Karte im Ordner Medienwerk.
- Baustein 11 Teil 1: deploy/seiten_auslieferer.py ersetzt python http.server im Dienst seiten-roli und hängt bei ?kommentieren=1 das Hilfsskript deploy/kommentier-hilfe.js an.
- V220: Baustein 11 Teil 2: Kommentiermodus in der Vorschau (Schalter, Sammelliste, Senden an die Karte oder ins Eingabefeld).
- V221: Antwort-Tasten und Vorschlag räumen sich auf (Foto-Antworten zählen, Vorschlag ohne erledigte Fragen, nur die zwei jüngsten Antworten halten Fragen offen).
- V222: Kontext-Balken in der Zeile des Modus, Cache-Hinweis oben entfällt.
- V223: Knopf „Nachgeschobenes jetzt senden“ (Strg+X Strg+S per tmux, nur wenn der Hinweis „to send now“ auf dem Schirm steht).
- Claude-Code-Neuerungen durchgesehen: Selbst-Zusammenfassung ruhender Karten ist an, bisher nirgends eingetreten.

## 4. Decisions Made
- Fester Platz Medienwerk, am Ordner festgemacht (Roli 04.11. „210. Ja“, „2. Ja“).
- Pfeile und Ziehen an der Chip-Reihe (04.11. „1. Ja“).
- Baustein 11 Weg A, zuerst nur Rolis Webspace (04.11. „3. Ja“, „4. Ja"); Teil 3 und Auslieferer für Lea und Lorenz bleiben liegen (04.11. „5. und 6. Deine Empfehlung“).
- Grenze zwei Antworten für offene Fragen bleibt (07.11. „7. Ja“). Überstimmt teilweise den Beschluss vom 02.11.
- Kopfzeile kompakter (08.11. 09:33).
- Knopf Jetzt senden bauen, Selbst-Zusammenfassung nachsehen, Remote Control liegen lassen (08.11. „9. Ja, 10. Ja, 11. Ja“).

## 5. Important Files and Locations
- hetzner_app/server.py (VERSION, Endpunkte wartend und jetzt-senden), hetzner_app/state.py (FESTE_ORDNER), web/app.js, web/index.html, web/styles.css: bearbeitet.
- deploy/seiten_auslieferer.py, deploy/kommentier-hilfe.js: neu. Dienst seiten-roli nutzt sie; alte Unit gesichert in ~/.hetzner-app/seiten-roli.service.vorher.
- ~/seiten/probe-kommentieren/: Probeseite für den Kommentiermodus.
- BAUBUCH.md und Brain/REGISTER.md: aktuell bis V223.

## 6. Open Tasks
- Verhalten im Auto testen (Diktat, Freisprechen, Ton-Tagebuch ~/.hetzner-app/ton-tagebuch.log, Ereignisse mik-*): Roli ist im Urlaub, frühestens um den 22.11.
- Handyprobe für V219 bis V223 (alles nur im Testbrowser geprüft).
- Baustein 16 zwei Karten nebeneinander; Englisch zum Schluss; Baustein 11 Teil 3 (Rahmen um Element, Springen, Kommentare merken); Auslieferer für Lea und Lorenz; Baustein 18 zurückgestellt; Baustein 2 ruht; Remote Control liegt.
- „An die Karte senden“ im Kommentiermodus nie an einer echten Karte ausprobiert.

## 7. Known Issues / Risks
- Doppelter Titel V221 im Git-Verlauf (siehe oben).
- Kommentiermodus am Handy nicht verfügbar (rechte Spalte dort versteckt).
- Die Zwei-Antworten-Grenze lässt ältere offene Fragen ohne Tasten, Nummer muss dann von Hand getippt werden.
- Unklar, ob das Autoproblem mit dem Fix „unsichtbare Zeichen brauchen kein zweites Enter“ (Claude Code 2.1.319) zusammenhängt.

## 8. Next Recommended Step
Roli um Rückmeldung zur Handyprobe bitten, dann nach dem Urlaub das Auto testen. Davor nichts Neues aufbauen.

## 9. Context for Future Claude Sessions
Roli diktiert und lässt vorlesen: kurze ganze Sätze, Fragen als nummerierte Zeile mit Empfehlung und Fragezeichen, Nummern laufen im Gespräch fortlaufend (zuletzt 11), am Ende „Fertig.“. Testserver: Starter /tmp/kaira_test.py (Port 8799, Umgebung aus ~/.hetzner-app/umgebung laden für Vorschau), Beenden mit fuser -k 8799/tcp 5015/tcp. Playwright unter ~/werkzeuge/browser/.venv, Tour-Schalter vorbelegen. Probekarten nur auf eigenem tmux-Socket. Nach jeder App-Änderung VERSION hochzählen, Dienst neu starten, Baubuch, Register, Commit, Push (github main).

## 10. Suggested Next Prompt
```text
Übergabe lesen
```
(Die Karte liest UEBERGABE.md, dann Baubuch-Ende und Register-Abschnitt Hetzner-App.)
