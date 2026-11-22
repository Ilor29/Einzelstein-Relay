# Project Handoff: Hetzner-App (Relay)

Version: v10 (ersetzt v09 vom 21.11. gegen 15:50)
Date: 2026-11-22, gegen 11:40
Owner/User: Roli
Prepared by: Claude (Karte Hetzner-App 24), automatisch vor Cache-Ablauf

Die Wahrheit steht in `BAUBUCH.md` (Einträge V256 und V257 vom 22.11.) und in `~/projekte/Brain/REGISTER.md`. Diese Datei fasst nur zusammen.

## 1. Stand

Relay V257 läuft, `/api/version` meldet 257, Piper lauscht auf Port 5005. Alles ist committet und auf `github main` gesichert, der Testserver 8799 ist beendet. Nichts ist halb fertig.

## 2. Was in dieser Karte geschah

- **V256:** Der Knopf „Übergabe vorbereiten“ steht immer im Verbrauchs-Blatt. Vorher erschien er erst ab 100.000 Token oder bei kaltem Zwischenspeicher. Unter der Grenze sieht er zurückhaltend aus, darüber hervorgehoben (weiche Akzentfläche, 2 Pixel Akzentrand). Roli hat ihn am Handy bestätigt („27. Ja“).
- **V257:** Der Blitz (`#knopf-schnell`) steht immer in der Knopfzeile des Eingabefelds. Ohne Tastatur klappt er die Befehlsreihe dauerhaft ein oder aus (`body.schnell-zu`, gemerkt unter `relay_schnell_zu_v1`). Bei offener Tastatur bleibt alles wie seit V253. Erklärtext in den Einstellungen nachgezogen.
- Beschlüsse stehen auch in der Zweitgehirn-Notiz „02 Projekte/Einzelstein Relay.md“.

## 3. Beschlüsse (mit Auslöser)

- Roli 22.11. 10:19: „wir hatten doch früher die hier die Übergabe datei mit drin“, 10:22 „26. Ja“ (Übergabe-Knopf immer zeigen).
- Roli 11:06: „war das so geplant wie auf dem Bild? Die Schnellwahltaste die muss einfahrbar sein“, 11:08 „30. Ja“ (Befehlsreihe auch ohne Tastatur einklappbar, Wahl gemerkt). Das ersetzt Beschluss 22 vom 21.11.
- Achtung Begriff: Mit „Schnellwahltaste“ meinte Roli am 21.11. die Symbolleiste oben, am 22.11. die Befehlsreihe über dem Eingabefeld. Bei dem Wort nachfragen.

Rolis letzter Wortlaut (11:08): „30. Ja“.

## 4. Offen

Bei Roli (die Nummern laufen weiter, zuletzt vergeben: 31):
- 31: Blitz am Handy antippen, bleibt die Reihe nach dem Neuladen eingeklappt?
- 21: Zeigt die Bibliothek am Handy jeden Skill nur einmal?
- 28: Tablet quer. 29: Tablet-App neu installieren (früher Nummer 27, umnummeriert). 40: Handyprobe Vorlesen.

Bei der nächsten Karte:
- Ungeprüft: V256 im hellen Farbschema, V257 am Handy, Tour-Durchlauf, Safari. Aus V255 noch: untere vier Menüpunkte, „Im Verlauf suchen“ an echter Karte.
- Das verwaiste Etikett `skills/mein-gin-tonic-helfer` in `~/.hetzner-app/bibliothek.json` nicht ohne Rolis Wort löschen.
- `UEBERGABE-LAUFEND.md` und `UEBERGABE-LAUFEND-vorher.md` im Projektordner stammen nicht von diesen Karten, nicht angefasst.

## 5. Nächster Schritt

Neue Karte mit „Übergabe lesen“. Zuerst `curl -s localhost:8787/api/version` (soll 257 melden) und Piper auf Port 5005 prüfen. Dann auf Rolis Antwort zu 31 warten.
