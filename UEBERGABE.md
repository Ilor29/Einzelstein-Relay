# Project Handoff: Hetzner-App (Relay)

Version: v11 (ersetzt v10 vom 22.11. gegen 11:40)
Date: 2026-11-22, gegen 13:42
Owner/User: Roli
Prepared by: Claude (Karte Hetzner-App 24), automatisch vor Cache-Ablauf

Die Wahrheit steht in `BAUBUCH.md` (Einträge V256 bis V258 vom 22.11.) und in `~/projekte/Brain/REGISTER.md`. Diese Datei fasst nur zusammen.

## 1. Stand

Relay V258 läuft, `/api/version` meldet 258, Piper lauscht auf Port 5005 (nach dem Neustart wieder oben). Alles ist committet und auf `github main` gesichert, der Testserver 8799 ist beendet. Nichts ist halb fertig.

## 2. Was in dieser Karte geschah

- V256 (Übergabe-Knopf immer im Verbrauchs-Blatt) und V257 (Blitz klappt die Befehlsreihe auch ohne Tastatur ein) sind am Handy bestätigt.
- Im Browser geprüft: V256 im hellen Schema, alle zwölf Kartenmenü-Punkte mit Symbol, Tour der Sitzungsansicht (sieben Schritte) ohne Konsolenfehler.
- V258: Bibliothek fasst Skills mit gleichem Namen und gleicher Beschreibung zusammen (Katalog und Zwischenspeicher), 600 auf 479 Einträge. Vorrang: eigenes Etikett, eigen, installiert, Katalog. Gleicher Name mit anderer Beschreibung bleibt stehen.
- Stimmtraining Kaira: nicht von dieser Karte. Laut Register von Kaira Assistent 8 bis 11, Kairas Stimme liest seit Relay V192 auch in Relay vor.

## 3. Beschlüsse (mit Auslöser)

- Roli 22.11. 13:06 „Siehe bilder oder hat das was mit Code und Cache zu tun“, 13:08 „33. Ja“: V258, jeder Skill nur einmal.
- Roli 13:06: „29. Ja“ (Tablet-App neu installieren), „40. Ja“ (Handyprobe Vorlesen), „28. Prüfe ich gleich“.

Rolis letzter Wortlaut (13:38): „also Querformat funktioniert bei diesem noch nicht, ich bin gerade auf dem Tablet … bei den Skills Account research ist sogar dreimal drin“.

## 4. Offen

Bei Roli (die Nummern laufen weiter, zuletzt vergeben: 38):
- 36: Tablet-App schon neu installiert (altes Symbol weg, in Chrome neu hinzufügen)? Die App-Datei (Manifest) sagt „orientation: any“, die Ursache liegt vermutlich in der alten Installation. Geraten, nicht geprüft.
- 37: Wie zeigt sich das Querformat-Problem genau (dreht gar nicht, oder Layout schief)? Gern Bildschirmfoto quer.
- 38: Soll bei gleichnamigen Skills das Plugin hinter den Namen („account-research (Common Room)“)? Empfehlung Ja. Account-research ist dreimal da, weil es drei verschiedene Skills sind (synced, Vertrieb, Common Room), kein Zusammenfassfehler.
- 35: Bibliothek am Handy anschauen (V258 nur an Zahlen geprüft).
- 28 Tablet quer (hängt an 36/37), 29 Neuinstallation, 40 Handyprobe Vorlesen.
- 34 (Kaira-Stimme im Register nachsehen) ist beantwortet: siehe Abschnitt 2.

Bei der nächsten Karte:
- Ungeprüft: Menüpunkt „Im Verlauf suchen“ an echter Karte, Safari.
- Das verwaiste Etikett `skills/mein-gin-tonic-helfer` in `~/.hetzner-app/bibliothek.json` nicht ohne Rolis Wort löschen.
- `UEBERGABE-LAUFEND.md` und `UEBERGABE-LAUFEND-vorher.md` im Projektordner stammen nicht von diesen Karten, nicht angefasst.

## 5. Nächster Schritt

Neue Karte mit „Übergabe lesen“. Zuerst `curl -s localhost:8787/api/version` (soll 258 melden) und Piper auf Port 5005 prüfen. Dann Rolis Antworten auf 36 bis 38 abholen: bei Ja auf 38 Plugin-Zusatz im Namen bauen (V259), beim Tablet je nach 37 die Ursache suchen (alte Installation, Android-Rotationssperre oder Layout bei quer, etwa 1000 Pixel Breite, mit Playwright nachstellen).
