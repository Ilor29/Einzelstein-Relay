# Übergabe Hetzner-App (Relay), Karte Hetzner-App 15, 11.11.2026 gegen 16:20

**Thema:** Durchsicht der App mit Fable 5.2. Der Server-Teil ist durchgesehen und repariert, jetzt folgt die Oberfläche. Wahrheit liegt in BAUBUCH.md (Ende, Einträge vom 11.11.) und ~/projekte/Brain/REGISTER.md.

## Fertig in dieser Karte
- Relay V227 läuft, gesichert (github main), Arbeitsordner sauber.
- V225: Modell-Anzeige liest aus der letzten Antwort der Karten-Mitschrift (`state.modell_anzeige`, `verbrauch.modell_anzeige`, neues Feld `Meta.modell_gewechselt`). Kontext-Balken, Wert ohne Abo und Datenpunkt beim Archivieren hängen an der gebundenen Mitschrift (`verbrauch._mitschrift_datei`).
- V226: Aufwecken fällt nur bei Scheitern in den ersten 20 Sekunden zurück, immer auf ein frisches Gespräch (`tmux._mit_rueckfall`).
- V227: `state.frage()` sucht den Arbeits-Hinweis nur ab der ersten Antwortzeile; `modus_wechseln` lehnt bei offenem Dialog mit 409 ab.
- Alles mit Probekarten und Testserver geprüft, nichts davon am Handy.

## Nächster Schritt: Frage 8, Oberfläche durchsehen (Roli „8. Ja“, „9. Ja“, „12. Ja“)
`web/` ganz lesen (rund 7.800 Zeilen, vor allem app.js), dazu die noch nicht gelesenen Module mitschrift.py, melden.py, strom.py, tts.py, geraete.py. Erst Befunde als Liste ins Baubuch, dann Roli fragen, dann einzeln ändern. Aus Rolis Prüf-Prompt gilt nur diese Auswahl:
- Von den Dateien ausgehen, nicht von Zusammenfassungen.
- Code starten und die Bedienwege durchspielen (Testserver 8799, Playwright, Probekarte).
- Jeden Fund einstufen als falsch, unklar oder Geschmack. Ohne Skript-Ausgabe oder Nachstellen steht er als „unbestätigt“ da.
- Höchstens fünf Erweiterungen, jede mit dem günstigsten Test, der sie widerlegen würde.
- Am Ende die Liste dessen, was Roli am Handy prüfen muss.
Nicht übernommen: Excel-Nachrechnung, Fragen an Anwalt und Steuerberater, versionierte Dateinamen.
Als Vergleich dienen Rolis zwei Bilder der Einstellungen der Original-App (Gruppen im Baubuch unter V224 notiert, die Bilder verfallen um den 25.11.).

## Offen bei Roli
- 11. Diese Karte (Hetzner-App 15) steht seit dem Testfehler auf „Auto“ statt „fragt nie“; Roli wurde gebeten, die Modus-Pille zurückzuschalten, Antwort steht aus. Betrifft die neue Karte nicht.
- Handyprobe V225 bis V227: Modellnamen in der Liste, Kontext-Balken, Aufwecken einer echten Karte, Modus-Knopf bei offener Frage.

## Weiter offen
- Skillkontor-Marketing 39: gemerkt ist „fable“, geantwortet hat zuletzt Sonnet 5.5; ob der Wechsel scheiterte, ist ungeklärt.
- Kleine Befunde aus der Durchsicht, nicht bearbeitet: `overview()` ruft je wacher Karte vier Mal tmux auf; `gesehen`/`ungelesen` legen für unbekannte Namen Einträge an; Senden bei offener Erlaubnisfrage drückt Escape und lehnt damit still ab.
- Verhalten im Auto (Diktat, Freisprechen, Ton-Tagebuch): frühestens um den 22.11.
- Baustein 16 zwei Karten nebeneinander; Baustein 11 Teil 3; Auslieferer für Lea und Lorenz; Englisch zum Schluss; Baustein 18 zurückgestellt; Remote Control liegt.

## Beschlüsse dieser Sitzung
- Roli 11.11. 10:12: „5. Ja, 6. Ja, 7. Ja, 8. Ja“, dazu der Prüf-Prompt mit dem Satz „Ich denke nicht alles ist brauchbar aus dem Prompt“.
- Roli 11.11. 13:36: „9. Ja“ (Durchsicht der Oberfläche mit der Auswahl oben), „10. Ja“ (Punkt 7, zuerst Aufweck-Kette).
- Roli 11.11. 16:17: „12. Ja“ (Oberfläche in neuer Karte, Übergabe schreiben).

## Hinweise für die neue Karte
Fragen-Nummern laufen weiter, zuletzt 12. Testserver: Skript mit `server.app.dependency_overrides[server.require_auth] = lambda: None` und `server.app.router.on_startup.clear()`, Port 8799, mit `PYTHONPATH=.` und dem Python aus `.venv`, Beenden mit `fuser -k 8799/tcp`. Probekarten nur auf eigenem tmux-Socket (zuletzt `tmux -L probe225`, Ordner /tmp/probe-aufweck, dort ist die Vertrauensfrage schon beantwortet); sie erscheinen in der App als fremde Karte „probe225:<name>“ mit dem Ordnernamen als Schild. Wichtig: Der Testserver zeigt alle echten Karten, schreibende Klicks wirken auf sie. Im Browsertest eine Karte nie über Fließtext suchen, vor jedem Klick auf Senden, Modus, Modell oder Anhalten den Kartennamen im Kopf prüfen (Fehler vom 11.11., siehe Baubuch V227). Die Relay startet neue Karten mit Sonnet; für die Durchsicht hat Roli bisher von Hand auf Fable gestellt.

## Rolis letzter Wortlaut
„12. Ja“ (11.11. 16:17).
