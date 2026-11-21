# Project Handoff: Hetzner-App (Relay)

Version: v07 (ersetzt die Übergabe vom 20.11.)
Date: 2026-11-21, gegen 10:10
Owner/User: Roli
Prepared by: Claude (Karte Hetzner-App 21)

Die Wahrheit steht in `BAUBUCH.md` (am Ende die Einträge V251 und V252 vom 21.11.) und in `~/projekte/Brain/REGISTER.md` (Einträge „Hetzner-App 21“ vom 21.11. um 09:05 und 09:20). Diese Datei fasst nur zusammen.

## 1. Stand

Relay V252 läuft. Der Dienst wurde nach V252 neu gestartet, als keine andere Karte arbeitete. `/api/version` meldet 252, und Piper antwortet. Alles ist committet und auf `github main` gesichert. Nichts ist halb fertig. Der Testserver 8799 ist beendet, und die Probe-tmux `probeeasel` samt Ordner ist weg.

## 2. Was in dieser Karte geschah

- **V251:** Der MCP-Anmeldekasten weist darauf hin, dass Claude Code nur etwa fünf Minuten wartet, und sagt, dass man sonst im Terminal-Teil neu „Authenticate“ wählt.
- **Neuerungs-Wache:** Roli fragte, wer die Funde der Wache umsetzt. Bisher tat das niemand, weil die Wache bewusst nichts baut. Seit heute legt sie Funde, die eindeutig einer Karte gehören, per `korb.py frage` in den Entscheidungskorb (Schritt 5b in `Brain/werkzeug/claude-neues.md`, gebaut von Brain 75).
- **easel (Diagramm-Mod aus 2.1.330):** Bei einer Probe in eigener tmux-Sitzung erschien es nicht. Claude zeichnete nur Textbalken, fand kein Werkzeug, und `/config` hat keinen Eintrag dazu. Meine erste Vermutung „nur Pro und Max“ war falsch: Das Konto ist Max, das Plugin steckt als `cc-plugin-easel@builtin` im Programm, wird aber nicht freigeschaltet (Brain 75 hat das berichtigt). Für Relay ist derzeit nichts zu bauen.
- **V252, Barrierefreiheit:** Alle 13 Blätter halten den Fokus fest. Tab bleibt im obersten Blatt, Escape schließt es über den Schatten, danach springt der Fokus zum Auslöser zurück. „Claude anhalten“ ist 44 Pixel hoch, „Nebenfrage stellen“ hat eine größere Trefferfläche, und die Zeilen im Dateibaum sind mindestens 40 Pixel hoch. Kontrast in der Bibliothek: Reiter und Fach-Schild kamen auf 4,47, jetzt 4,77. Die Einstellungen waren ohne Befund.
- **Bibliothek:** Sie las alle alten Plugin-Fassungen unter `~/.claude/plugins/cache`, deshalb stand jeder Koffer-Skill bis zu vierzehnmal darin. Jetzt zählt dort nur noch der `installPath` aus `installed_plugins.json` (603 statt 931 Einträge). Kein Etikett ging verloren.
- **Google-Stimme:** Kaputtes JSON, eine Liste statt eines Objekts und ungültiges base64 werden zu `TTSError` „Google hat eine unlesbare Antwort geschickt.“
- **XSS-Durchsicht:** Die 30 `innerHTML`-Stellen in app.js sind ohne Befund, keine Änderung.
- **Cache-Übergabe:** Das Protokoll zeigt 13 Aufträge seit dem 17.11., keinen doppelt. Es gibt nichts zu ändern.
- Die automatische Sicherung um 09:08 nahm die V252-Änderungen an app.js und styles.css vor meinem Commit mit. Der sprechende Commit 9251ce5 ist deshalb leer und verweist auf 19ee1eb.

## 3. Beschlüsse (mit Auslöser)

- Roli 21.11. 08:54: „1. Ja“ (Fünf-Minuten-Hinweis, dann Barrierefreiheit) und die Frage „wer setzt diese Änderungen denn tatsächlich um? … haben wir einen kleinen Suchlauf, der immer wieder die neuesten Updates rausholt … auch bei unserer Version von der Relay-App?“
- Roli 21.11. 09:02: „2. Ja, Ja bitte, dann arbeite alle Punkte ab, ohne mich zu fragen. Nur da, wo du mich wirklich brauchst.“ Dieses Ja galt der Korb-Weitergabe der Wache. Als vierte Wiederholung steht es im Gedächtnis `nur-fragen-was-ich-nicht-entscheiden-kann`.
- Roli 09:09, an Brain 75: Er zweifelte meine easel-Begründung an, zu Recht, sie ist berichtigt.

Rolis letzter Wortlaut (10:07): „Bitte jetzt die Übergabe vorbereiten: Laufenden Stein sauber zu Ende bringen, Stand in Baubuch und Register nachtragen, dann UEBERGABE.md im Projektordner schreiben … und mir den Satz „Übergabe lesen“ für die neue Karte als Codeblock nennen.“

## 4. Offen

Bei Roli (die Nummern laufen weiter, zuletzt vergeben: 15):
- 13. Am Handy prüfen: Terminal (V249), Glocke einschalten, Bibliothek zeigt jeden Skill nur einmal.
- 14. Doppelte Skills aus nicht installierten Plugin-Katalogen (`plugins/marketplaces`) werden nur angefasst, wenn es ihn stört.
- 15 bzw. alte 30: Sollen selten gebrauchte Kopfzeilen-Symbole ins Drei-Punkte-Menü? Erst danach werden die neun Symbole breiter.
- Alt: 27 (Tablet-App neu installieren), 28 (Tablet quer), 40 (Handyprobe Vorlesen), neue Medienwerk-Karte für die Fish-Werkzeuge.

Bei der nächsten Karte:
- Nichts Gebautes ist offen. Ungeprüft sind: Handy, echtes Vorleseprogramm, Höhe von Nebenfrage und Dateibaum im Browser gemessen, echte Google-Antwort.
- Das verwaiste Etikett `skills/mein-gin-tonic-helfer` in `~/.hetzner-app/bibliothek.json` hat keinen Skill mehr. Ohne Rolis Wort nicht löschen.

## 5. Nächster Schritt

Neue Karte mit „Übergabe lesen“. Danach auf Rolis Antworten zu 13 bis 15 warten. Kommt keine, sind die Korb-Fragen der Neuerungs-Wache für die Relay-Karte das Nächste, sobald welche ankommen.
