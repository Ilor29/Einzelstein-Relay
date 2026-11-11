# Project Handoff: Hetzner-App (Relay)

Version: v02 (ersetzt die Übergabe von 16:20, die in Git steht, Commit 390cd14)
Date: 2026-11-11, gegen 18:50
Owner/User: Roli
Prepared by: Claude (Karte Hetzner-App 16)

Wahrheit liegt in `BAUBUCH.md` (Ende, Einträge vom 11.11.) und `~/projekte/Brain/REGISTER.md`. Diese Datei fasst nur zusammen.

## 1. Project Goal

Relay: Web-App (PWA) plus FastAPI-Dienst, mit der Roli Claude-Code-Sitzungen vom Handy und Tablet aus bedient (tmux auf dem Server, Vorlesen mit Piper, Diktat). Aktuell läuft eine Durchsicht der ganzen App mit Fable 5.2, danach einzelne Reparaturen.

## 2. Current Status

Relay V234 läuft und ist auf GitHub (`github main`) gesichert, Arbeitsordner sauber. Server-Teil und Oberfläche sind durchgesehen. Sechs belegte oder schwere Funde sind behoben und einzeln committet. Alles wurde im Browser (Playwright, Testserver 8799, Scheinkarten) oder mit Probe-Skript geprüft, nichts am Handy.

## 3. What Changed in This Session

- Durchsicht von `web/app.js`, `index.html`, `styles.css`, `sw.js`, `manifest.webmanifest`, `mitschrift.py`, `melden.py`, `strom.py`, `tts.py`, `geraete.py` durch fünf Leser; die Funde mit Einstufung (belegt, Code, Geschmack) stehen im Baubuch unter „Durchsicht der Oberfläche …“.
- V228: Ordner `web/dl` nur noch nach Anmeldung (eigene Route vor dem Static-Mount).
- V229: Foto mit Begleittext und Werkzeugzeilen gehen im Verlauf nicht mehr verloren (Kennung je Block mit Stelle im Eintrag).
- V230: Eingabefeld und Diktat werden beim Kartenwechsel und bei Zurück geleert und gestoppt (`feldFuerKarteLeeren`).
- V231: Antwort-Knöpfe und Verlauf gehören nur zu ihrer Karte (Kartenname vor dem `await` merken, danach prüfen; `antworte(nummer, fuer)`).
- V232: Antwort-Tipp (`waehle`) lässt Freitext und Leerzeilen im Feld stehen.
- V233: Vorlese-Strom meldet unerwartete Fehler (`except Exception` in `strom.strom`).
- V234: Manifest `orientation` von `portrait` auf `any`, damit sich die installierte App am Tablet drehen lässt.
- Roli koppelte sein Tablet; die App fragt dort nach einem Kopplungscode (nicht nach dem Geräteschlüssel). Gedächtnis-Eintrag `relay-zweites-geraet-ueber-einstellungen` angelegt.

## 4. Decisions Made

- Roli 11.11. 17:21 „14. Deine Empfehlung“: die schweren Funde einzeln beheben, je mit eigener Version und Test. Grund: sie verfälschen Nachrichten oder schicken sie an die falsche Karte. Umgesetzt (V229 bis V233).
- Roli 11.11. 17:21 „15. Deine Empfehlung“: Ordner `dl` hinter die Anmeldung. Umgesetzt (V228). Folge: Links ohne Anmeldung (Lea, Lorenz, Handys ohne Cookie) bekommen 401.
- Roli 11.11. 16:27 „13. Ja“: Durchsicht der Oberfläche beginnen. Die Modus-Pille der Karte Hetzner-App 15 ließ sich laut Roli wieder umschalten, damit erledigt.
- Aus Rolis Prüf-Prompt gilt nur die vereinbarte Auswahl (von den Dateien ausgehen, Bedienwege durchspielen, Funde einstufen, höchstens fünf Erweiterungen mit widerlegendem Test, Liste der Handyprüfungen). Nicht übernommen: Excel-Nachrechnung, Anwalts- und Steuerfragen, versionierte Dateinamen.
- Manifest-Orientierung auf `any` gestellt, ohne dass im Baubuch ein Beschluss für Hochformat stand (Auslöser: Rolis Foto 11.11. 18:47).

## 5. Important Files and Locations

- `hetzner_app/server.py` (VERSION 234, Route `/dl/{pfad}`), `hetzner_app/mitschrift.py` (Block-Kennung), `hetzner_app/strom.py` (Fehlerfang), `web/app.js` (`feldFuerKarteLeeren`, `pruefeFrage`, `ladeVerlauf`, `antworte`, `waehle`), `web/manifest.webmanifest` (orientation), alle bearbeitet und committet.
- `BAUBUCH.md`, `~/projekte/Brain/REGISTER.md` (Eintrag 11.11. 17:50, **V234 dort noch nicht nachgetragen**).
- Gedächtnis: `~/.claude/memory-gemeinsam/relay-zweites-geraet-ueber-einstellungen.md`.

## 6. Open Tasks

Offen bei Roli (Nummern laufen weiter, zuletzt 28):
- 16. Soll ich die übrigen Rennen beim Kartenwechsel (Dateibaum, Datei-Inhalt, Zurückspulen, Glätten, Modellwahl, Umbenennen) nach demselben Muster in einer Version beheben? Empfehlung: Ja.
- 17. Soll danach die Barrierefreiheit folgen (Ampel mit Text, erreichbare Schalter, Kontrast, größere Tippflächen)? Empfehlung: Ja.
- 27. Relay-App am Tablet neu installieren (Manifest-Änderung); 28. Querformat testen, ob zwei oder drei Spalten erscheinen.
- Handyprobe V225 bis V234, Liste 18 bis 26: Modellnamen in der Kartenliste, Kontext-Balken, Aufwecken einer echten Karte, Modus-Knopf bei offener Frage, Foto mit Text, Kartenwechsel mit Entwurf, Antwort-Knöpfe nach schnellem Wechsel, Antwort-Tipp mit Freitext, `dl` ohne Anmeldung.

Noch nicht behoben aus der Durchsicht: Einstellungen laden nur halb, wenn `/stimmen` ausfällt; Neue Karte (verborgener Ordner bei leerem Suchfilter, Doppeltipp, Benachrichtigungs-Erlaubnis); Vorschau fragt bei Fehler pro Frame; Lupe zieht das Mitlaufen weg; Vorlesen (rasche Sprünge, Leiste bleibt, Tonquellen); Netzfehler still; Terminal-Eingabe im Zustand CONNECTING; Piper erbt `ELEVENLABS_API_KEY` und `GOOGLE_TTS_API_KEY`; Web-Push fängt nur `WebPushException`; Barrierefreiheit (Punkt 16 im Baubuch). Höchstens fünf Erweiterungen mit Test sind noch nicht vorgeschlagen.

Weiter offen: Skillkontor-Marketing 39 (gemerkt „fable“, geantwortet hat Sonnet 5.5; ungeklärt). Verhalten im Auto (Diktat, Freisprechen, Ton-Tagebuch) frühestens um den 22.11. Baustein 16 zwei Karten nebeneinander, Baustein 11 Teil 3, Auslieferer für Lea und Lorenz, Englisch zum Schluss, Baustein 18 zurückgestellt, Remote Control liegt.

## 7. Known Issues / Risks

- Nichts davon ist am Handy oder Tablet geprüft. Diktat und die Strom-Meldung ließen sich im Testbrowser nicht prüfen (kein Mikrofon, kein echter Fehler).
- Ob das Tablet im Querformat 1280 CSS-Pixel erreicht (dreispaltige Ansicht), ist offen; sonst zwei Spalten ab 900 Pixel.
- Eine schon installierte PWA übernimmt das neue Manifest erst nach Aktualisierung durch Android.
- Der Server zeigt im Testserver alle echten Karten, schreibende Klicks wirken auf sie. Keine Karte über Fließtext suchen, vor jedem Klick auf Senden, Modus, Modell oder Anhalten den Kartennamen prüfen. Die Scheinkarten-Methode (Liste per `page.route` vortäuschen) ist sicher.
- Der Kopplungscode für das Tablet (einmalig, 15 Minuten) steht bewusst nicht in dieser Datei.

## 8. Next Recommended Step

Rolis Antworten auf 16 und 17 abwarten; bei Ja die Rennen in einer Version beheben, dann die Barrierefreiheit, jeweils mit Probe und Baubuch-Eintrag. Zuerst V234 im Register nachtragen.

## 9. Context for Future Claude Sessions

- Pro Änderung an App oder API `VERSION` in `hetzner_app/server.py` hochzählen, dann `sudo systemctl restart hetzner-app.service` und `curl -s localhost:8787/api/version`. Einzeln committen mit deutscher Nachricht und `git push github main`.
- Testserver: Skript **nicht nach /tmp** legen (dort liegt ein `bisect.py`, das die Standardbibliothek überdeckt), sondern in ein frisches Verzeichnis unter /var/tmp; `python -I` ignoriert `PYTHONPATH`, also `sys.path.insert` im Skript. `dependency_overrides[require_auth]` und `on_startup.clear()`, Port 8799, Beenden mit `fuser -k 8799/tcp`. Playwright aus `~/werkzeuge/browser/.venv`. Tour-Schalter `relay_tour_liste_v1` und `relay_tour_sitzung_v1` auf "1".
- Aufräumen mit `rm -rf /var/tmp/ts.*` geht, mit `$(...)` im Pfad sperrt die Schutzprüfung den Befehl.
- Nie `tts` aus einem zweiten Python-Prozess nutzen, sondern die Stimme nachbauen (Test in V233).
- Probeeintrag in Mitschrift-Tests braucht einen Zeilenumbruch am Ende, sonst wird die letzte Zeile nicht gelesen.
- Nach 250.000 Token Kontext neue Karte. Antworten kurz, nummerierte Fragen mit Empfehlung, am Ende „Fertig.“

## 10. Suggested Next Prompt

```text
Übergabe lesen
```
