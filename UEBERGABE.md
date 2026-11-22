# Project Handoff: Hetzner-App (Relay)

Version: v12 (ersetzt v11 vom 22.11. gegen 13:42)
Date: 2026-11-22, gegen 20:55
Owner/User: Roli
Prepared by: Claude (Karte Hetzner-App 24), auf Rolis Bitte

Die Wahrheit steht in `BAUBUCH.md` (Einträge V256 bis V261 vom 22.11.) und in `~/projekte/Brain/REGISTER.md`. Diese Datei fasst nur zusammen.

## 1. Stand

Relay V261 läuft, `/api/version` meldet 261, Piper lauscht auf Port 5005. Alles ist committet und auf `github main` gesichert, der Testserver 8799 ist beendet. Nichts ist halb fertig. Die Beschlüsse stehen auch im Zweitgehirn unter „02 Projekte/Einzelstein Relay.md“.

## 2. Was in dieser Karte geschah (22.11.)

- V256: Knopf „Übergabe vorbereiten“ steht immer im Verbrauchs-Blatt. Am Handy bestätigt, im hellen Schema im Browser geprüft.
- V257: Der Blitz klappt die Befehlsreihe auch ohne Tastatur ein, die Wahl wird gemerkt. Am Handy bestätigt.
- Im Browser geprüft: alle zwölf Kartenmenü-Punkte mit Symbol, Tour der Sitzungsansicht mit sieben Schritten.
- V258: Die Bibliothek fasst Skills mit gleichem Namen und gleicher Beschreibung zusammen (Katalog und Zwischenspeicher), 600 auf 479 Einträge. Am Handy bestätigt („35. Ja“).
- V259: Gleichnamige, aber verschiedene Skills tragen das Plugin im Namen, etwa „account-research (common-room)“ oder „(sales, synced)“. Dafür liefert der Server das neue Feld `quelle`.
- V260: Die Skill-Beschreibungen erscheinen in der Sprache der Oberfläche. Der Knopf „Original“ oben in der Bibliothek zeigt den Urtext (`relay_bib_original_v1`). Neues Modul `hetzner_app/uebersetzung.py` übersetzt über das Abo (`claude -p --model haiku`, ohne Werkzeuge, Hooks und Plugins), gespeichert in `~/.hetzner-app/bibliothek-sprachen.json`. `/api/skills` stößt bei Lücken einen Lauf an (höchstens alle zehn Minuten), dazu Cron täglich 04:20, Protokoll `~/logs/bibliothek-uebersetzung.log`. Alle 479 Beschreibungen sind übersetzt, am Handy bestätigt („sind auf deutsch“).
- V261: Ein Text, der sich nicht übersetzen lässt, wird nach drei Fehlversuchen nicht mehr probiert (`_fehl` im Speicher).
- Tablet quer geht nach Neuinstallation (Roli 15:04).
- Kaira-Stimmtraining: Diese Karte war es nicht, das waren laut Register Kaira Assistent 8 bis 11. Kairas Stimme liest seit Relay V192 auch in Relay vor.

## 3. Beschlüsse (mit Auslöser)

- 10:19 „wir hatten doch früher die hier die Übergabe datei mit drin“, 10:22 „26. Ja“: V256.
- 11:06 „Die Schnellwahltaste die muss einfahrbar sein“, 11:08 „30. Ja“: V257, ersetzt Beschluss 22 vom 21.11.
- 13:06 „Siehe bilder oder hat das was mit Code und Cache zu tun“, 13:08 „33. Ja“: V258.
- 15:09 „38. Ja“: V259.
- 15:09 „dann können wir das so machen, dass bei der deutschen Version Skills auf Deutsch angezeigt werden und in der englischen Version in Englisch … dazu switchen kann … wenn wir neu installieren, dass es immer gleich die deutsche Beschreibung sichtbar ist“, 15:12 „39. Ja“: V260.
- 16:46 „42. Ja“: V261.
- Achtung Begriff: Mit „Schnellwahltaste“ meinte Roli am 21.11. die Symbolleiste oben, am 22.11. die Befehlsreihe über dem Eingabefeld. Bei dem Wort nachfragen.

Rolis letzter Wortlaut (20:52): „Bitte jetzt die Übergabe vorbereiten: Laufenden Stein sauber zu Ende bringen, Stand in Baubuch und Register nachtragen, dann UEBERGABE.md im Projektordner schreiben … und mir den Satz ‚Übergabe lesen‘ für die neue Karte als Codeblock nennen.“

## 4. Offen

Bei Roli: nichts. Zuletzt vergebene Nummer: 42, die nächste Frage bekommt die 43.

Bei der nächsten Karte, ohne Eile:
- Ungeprüft: Menüpunkt „Im Verlauf suchen“ an echter Karte, Safari, Umschalten der Sprache zur Laufzeit bei offener Bibliothek (beim Öffnen wird neu gezeichnet, das ist geprüft).
- Spiegel von Lorenz und Lea: Dort übersetzt der Server über deren eigenes Abo, sobald sie die Bibliothek öffnen. Den Cron für 04:20 hat nur Roli. Nicht geprüft.
- Das verwaiste Etikett `skills/mein-gin-tonic-helfer` in `~/.hetzner-app/bibliothek.json` nicht ohne Rolis Wort löschen.
- `UEBERGABE-LAUFEND.md` und `UEBERGABE-LAUFEND-vorher.md` im Projektordner stammen nicht von diesen Karten, nicht angefasst.

## 5. Nächster Schritt

Neue Karte mit „Übergabe lesen“. Zuerst `curl -s localhost:8787/api/version` (soll 261 melden) und Piper auf Port 5005 prüfen. Nach einem Dienst-Neustart braucht Piper gut eine Minute, bis der Port wieder offen ist. Dann auf Rolis Wort warten.

## Nach der Übergabe gekommen (automatisch mitgeschrieben, Rolis Wortlaut)
