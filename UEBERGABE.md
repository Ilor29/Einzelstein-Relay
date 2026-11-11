# Project Handoff: Hetzner-App (Relay)

Version: v03 (ersetzt die Übergabe von 18:50, Commit d01eaa8)
Date: 2026-11-11, gegen 22:10
Owner/User: Roli
Prepared by: Claude (Karte Hetzner-App 17)

Wahrheit liegt in `BAUBUCH.md` (Ende, Einträge V235 bis V238 vom 11.11.) und `~/projekte/Brain/REGISTER.md` (Einträge „Hetzner-App 17“). Diese Datei fasst nur zusammen. Vor dem Weiterbauen dort nachlesen.

## 1. Project Goal

Relay: Web-App (PWA) plus FastAPI-Dienst, mit der Roli Claude-Code-Sitzungen vom Handy und Tablet aus bedient (tmux auf dem Server, Vorlesen mit Piper, Diktat). Seit dem 11.11. läuft eine Durchsicht der ganzen App, die Funde werden einzeln behoben, je mit eigener Version, Test und Baubuch-Eintrag.

## 2. Current Status

Relay V238 läuft (`curl -s localhost:8787/api/version`), alles committet und auf `github main` gesichert, Arbeitsordner sauber. Nichts ist angefangen und halb liegen geblieben. Geprüft wurde im Browser (Playwright, Testserver 8799, Scheinkarten) und mit Probe-Skripten. Die Handyprobe 18 bis 26 ist abgeschlossen.

## 3. What Changed in This Session

- V235: die übrigen Rennen beim Kartenwechsel. Helfer `nochOffen(name)` in `web/app.js`; Senden, Anhänge, Glätten, Umbenennen, Anheften, Glocke, Modus, Archivieren, Verbrauch, Modell, Anmeldung, Vorlesen, Zurückspulen, Dateibaum und Datei-Inhalt merken sich ihre Karte. `blaetterDerKarteZu()` schließt Blätter beim Wechsel. 15 Prüfungen, mit altem Code fallen 10 durch.
- V236: Barrierefreiheit. Speicher-Ampel mit Wort und Form, Schalter per Tastatur erreichbar, `--schrift-schwach` und `--schrift-leise` heller, neue Farbe `--auf-akzent` (dunkle Schrift auf den orangen Knöpfen im Dunkelmodus), `aria-label` für sieben Felder, Blätter als Dialog, unsichtbare größere Tippflächen (Block am Ende von `styles.css`), Manifest-Farbe `#1F1E1D`.
- V237: Einstellungen laden ganz, auch wenn `/stimmen` ausfällt (Knopf „Noch einmal versuchen“); Verlauf meldet nach zwei Fehlschlägen in Folge einmal „Keine Verbindung“; ältere Nachrichten, Kaira-Knopf und Skill-Liste melden ihre Fehler.
- V238: `tts._kind_umgebung` gibt Piper keine Zugänge mehr mit; `melden.schicken` fängt jeden Fehler je Gerät und macht weiter; Sperre um `_vapid()`. Piper läuft am Dienst mit der bereinigten Umgebung (nachgesehen, nur Namen).

## 4. Decisions Made

- Roli 11.11. 20:58 „29. Ja, und bitte die alten Fragen noch“: Rennen in einer Version beheben (V235), alte Fragen noch einmal nennen.
- Roli 11.11. 21:26 „17. Ja“: Barrierefreiheit angehen (V236). Dazu „18. Ja“ bis „22. Ja“: Handyprobe bestanden für Modellnamen in der Liste, Kontext-Balken, Aufwecken, Modus-Knopf bei offener Frage, Foto mit Begleittext.
- Roli 11.11. 21:32 „25. Deine Empfehlung, 26. Deine Empfehlung, 23 passt, 24 passt“: 23 und 24 bestanden; 25 gilt mit der Browser-Prüfung als erledigt; 26 wird nicht eigens geprüft, Roli meldet sich, wenn Lea oder Lorenz ein Link aus `dl` fehlt.
- Roli 11.11. 21:54 „31. Ja“: übrige Befunde weiter beheben, zuerst Einstellungen und stille Netzfehler (V237).
- Roli 11.11. 21:59 „32. Ja“: Piper-Schlüssel und Web-Push (V238).
- Ohne eigenen Beschluss von mir gewählt: Schrift auf Akzentflächen im Dunkelmodus dunkel statt weiß (Kontrast 3,1 zu 1 vorher). Roli wurde darauf hingewiesen, dass es schnell zurückzustellen ist; eine Rückmeldung dazu gibt es noch nicht.

## 5. Important Files and Locations

- `hetzner_app/server.py` (VERSION 238), `hetzner_app/tts.py` (`_kind_umgebung`), `hetzner_app/melden.py` (`schicken`, `_vapid`), `web/app.js`, `web/styles.css`, `web/index.html`, `web/manifest.webmanifest`.
- `BAUBUCH.md`, `~/projekte/Brain/REGISTER.md`, Zweitgehirn `~/Notizen/02 Projekte/Einzelstein Relay.md` (Beschlüsse 29, 17, 31, 32 eingetragen).
- Prüf-Skripte dieser Sitzung liegen in `/var/tmp/rennen235/` (`ts.py` Testserver, `probe.py` Rennen, `mess.py` Kontrast und Tippflächen, `probe237.py` Netzfehler) und `/var/tmp/v238/probe.py`. Sie können weg oder als Vorlage dienen; sie liegen nicht im Repo.

## 6. Open Tasks

Offen bei Roli (Nummern laufen weiter, zuletzt vergeben 33):
- 27. Relay-App am Tablet deinstallieren und neu installieren (Manifest-Änderung aus V234).
- 28. Am Tablet im Querformat nachsehen, ob zwei oder drei Spalten erscheinen.
- 30. Soll ich selten gebrauchte Symbole aus der Kopfzeile der Karte ins Drei-Punkte-Menü verschieben, damit die übrigen breiter werden? Empfehlung: Ja, sobald Roli sagt, welche er selten braucht; Kandidaten Linkliste, Sichern, Anheften.
- 33. Soll ich mit „Neue Karte“ weitermachen (Ordner bleibt bei leerem Suchfilter verborgen, Doppeltipp legt zwei Karten an)? Empfehlung: Ja. **Noch nicht beantwortet, nicht begonnen.**
- Rückmeldung, ob die dunkle Schrift auf den orangen Knöpfen gefällt und ob das Vorlesen nach V238 wie gewohnt klingt.

Noch nicht behoben aus der Durchsicht (Baubuch, Abschnitt „Durchsicht der Oberfläche“, Befunde 9 bis 15):
Neue Karte (verborgener Ordner bei leerem Suchfilter, Doppeltipp, Benachrichtigungs-Erlaubnis); Vorschau fragt bei Fehler pro Frame; Lupe zieht das Mitlaufen weg und zählt Treffer in zugeklappten Code-Blöcken; Vorlesen (zwei rasche Sprünge brechen ab, Leiste bleibt bei Stopp in der Startphase, Tonquellen werden nie freigegeben, Tagebucheintrag „wach-bericht“ fehlt auf Android); Terminal (Eingabe im Zustand CONNECTING geht verloren, späte `close`-Ereignisse verbinden neu); Rest von Befund 15 (`_letzte_nutzung` nur am Satzanfang, `--port 5005` als Teilstring, weitere Punkte in der Baubuch-Zeile); in `tts.py` fängt der Google-Weg ungültiges JSON nicht als `TTSError`. Aus der Barrierefreiheit: „Claude anhalten“, „Nebenfrage stellen“ und Dateibaum-Zeilen unter 40 Pixel hoch, kein Fokusfang in Blättern, Kontrast in Einstellungen, Bibliothek und heller Fassung nicht gemessen. Höchstens fünf Erweiterungen mit widerlegendem Test sind noch nicht vorgeschlagen. Unbestätigt bleibt XSS über `.md`-Inhalt (Gegenprobe im Browser fehlt).

Weiter offen aus früheren Karten: Skillkontor-Marketing 39 (gemerkt „fable“, geantwortet hat Sonnet 5.5; ungeklärt). Fund von Krugmeister-Brain 47 (Register 10.11. 23:00): Vorschlagszeile listet alte, schon beantwortete Fragenummern; nicht untersucht. Verhalten im Auto frühestens um den 22.11. Baustein 16 zwei Karten nebeneinander, Baustein 11 Teil 3, Auslieferer für Lea und Lorenz, Englisch zum Schluss, Baustein 18 zurückgestellt, Remote Control liegt.

## 7. Known Issues / Risks

- V235 bis V238 sind am Handy und Tablet nicht geprüft. Ohne eigenen Test, aber nach demselben Muster gebaut: Anhänge, Glocke, Anheften, Anmeldung, Verbrauchsblatt, Vorlesen und Freisprechen beim Kartenwechsel; Kaira-Knopf mit Pop-up-Sperre; Skill-Liste nach Anlegen.
- Die neun Symbole in der Kopfzeile der Karte sind am Handy 30 Pixel breit, die Trefferfläche wuchs nur in der Höhe (Frage 30).
- Der Testserver zeigt alle echten Karten, schreibende Klicks wirken auf sie. Nur mit Scheinkarten arbeiten (`page.route`), Karten mit `oeffneSitzung(objekt)` per `evaluate` öffnen, nie über Fließtext klicken.

## 8. Next Recommended Step

Rolis Antwort auf 33 abwarten. Bei Ja „Neue Karte“ beheben (eine Version, Test mit Scheinkarten, Baubuch, Register), danach einzeln Vorschau, Lupe, Vorlesen, Terminal. Bei einer Antwort auf 30 die genannten Symbole ins Kartenmenü verschieben.

## 9. Context for Future Claude Sessions

- Pro Änderung an App oder API `VERSION` in `hetzner_app/server.py` hochzählen, dann `sudo systemctl restart hetzner-app.service` und `curl -s localhost:8787/api/version`. Einzeln committen mit deutscher Nachricht und `git push github main`.
- Die automatische Sicherung committet alle 10 Minuten mitten in die Arbeit. `git stash` findet dann nichts; für eine Gegenprobe mit altem Code `git show <commit>:web/app.js > web/app.js`, danach die neue Fassung aus einer Kopie zurücklegen.
- Testserver: Skript in ein eigenes Verzeichnis unter /var/tmp (nicht /tmp, dort überdeckt ein `bisect.py` die Standardbibliothek), `python -I` mit `sys.path.insert`, `dependency_overrides[require_auth]`, `on_startup.clear()`, Port 8799, Beenden mit `fuser -k 8799/tcp`. Playwright aus `~/werkzeuge/browser/.venv`, Kontext mit `bypass_csp=True` (sonst sperrt die Inhaltsrichtlinie `evaluate`), Tour-Schalter `relay_tour_liste_v1` und `relay_tour_sitzung_v1` auf "1".
- Rennen testen: Die Antwort der alten Karte im Routen-Handler festhalten (Route merken, nicht `time.sleep`) und erst nach dem Wechsel beantworten. `page.evaluate` wartet auf zurückgegebene Versprechen, deshalb `() => { f(); }`. Ein Rennen-Test zählt erst, wenn er mit dem alten Code durchfällt.
- `sitzungen` ist in `app.js` keine globale Variable; `aktuelleSitzung`, `oeffneSitzung`, `ladeVerlauf`, `melde` sind global erreichbar.
- Nie `tts` aus einem zweiten Python-Prozess importieren. Funktionen daraus für Tests per `ast` aus dem Quelltext lösen (Muster in `/var/tmp/v238/probe.py`).
- Aus Prozess-Umgebungen und Zugangsdateien nur Namen ansehen, nie Werte ausgeben.
- Antworten kurz und hörbar, nummerierte Fragen mit Empfehlung als normale Zeile, am Ende „Fertig.“ Nach 250.000 Token Kontext neue Karte.

## 10. Rolis letzter Wortlaut

„[11.11. 21:59] 32. Ja“ (erledigt mit V238). Danach kam nur noch der automatische Auftrag zum Kartenwechsel.

## 11. Suggested Next Prompt

```text
Übergabe lesen
```
