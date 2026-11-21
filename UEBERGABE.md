# Project Handoff: Hetzner-App (Relay)

Version: v09 (ersetzt die Übergabe vom 21.11. gegen 14:10)
Date: 2026-11-21, gegen 15:50
Owner/User: Roli
Prepared by: Claude (Karte Hetzner-App 23)

Die Wahrheit steht in `BAUBUCH.md` (am Ende die Einträge V254 und V255 vom 21.11.) und in `~/projekte/Brain/REGISTER.md`. Diese Datei fasst nur zusammen.

## 1. Stand

Relay V255 läuft, `/api/version` meldet 255, Piper lauscht auf Port 5005. Alles ist committet und auf `github main` gesichert. Nichts ist halb fertig, der Testserver 8799 ist beendet.

## 2. Was in dieser Karte geschah

- **V254:** Das Ketten-Symbol für „Gesammelte Links“ steht wieder oben in der Kopfzeile, die Lupe wanderte hinter die drei Punkte (neuer Menüpunkt „Im Verlauf suchen“). Bei offener Tastatur wird oben die Kette statt der Lupe ausgeblendet. Strg+K prüft nicht mehr die Sichtbarkeit der Lupe. Tour-Schritte nachgezogen: Der Link-Schritt zeigt auf die Kette, der Such-Schritt hat keine Markierung mehr und nennt das Menü.
- **V255:** Alle zwölf Punkte im Kartenmenü tragen vor dem Text ihr Symbol (Lupe, Kette, Glocke, Sichern, Stift, Nadel, Ungelesen, Zurück, Buch, Kopie, Archiv, Mülleimer). Der Text steht in einem `span`, Anheften und Melden ändern nur diesen Text.
- Rolis Handy-Bildschirmfoto von 15:47 zeigt das Menü mit Symbolen und die Kette oben in der Kopfzeile: Beides funktioniert am echten Gerät. Das Bild fällt nach 14 Tagen weg; das Ergebnis steht hier.

## 3. Beschlüsse (mit Auslöser)

- Roli 21.11. 15:29: „22. Nein“ (Schnellbefehle ohne Tastatur bleiben sichtbar, kein Blitz-Einklappen) und „23. Ja, Bitte noch einmal die Lupe gegen den Link tauschen, weil das ist das, was ich häufiger brauche … Die Lupe verschwindet in den drei Punkten, aber die Linkklammer brauche ich auf jeden Fall auf der Schnellwahltaste oben.“
- Roli 15:31: „hinter den drei Punkten ist mehr Platz, wenn man die Symbole auch dazu sehen würde, dann weiß man, was sich hinter den Wörtern versteckt“ und „24. Ja“.
- Roli 15:47: „25. Ja, gute Arbeit, bitte Übergabe machen“.

Rolis letzter Wortlaut (15:47): „25. Ja, gute arbeit bitte übergabe machen“ (mit Handy-Bildschirmfoto des Menüs).

## 4. Offen

Bei Roli (die Nummern laufen weiter, zuletzt vergeben: 25):
- 21: Zeigt die Bibliothek am Handy jeden Skill nur einmal?
- Alt: 27 (Tablet-App neu installieren), 28 (Tablet quer), 40 (Handyprobe Vorlesen), neue Medienwerk-Karte für die Fish-Werkzeuge.

Bei der nächsten Karte:
- Nichts Gebautes ist offen. Ungeprüft: die unteren vier Menüpunkte im Bild (Kurzfassung, Fork, Archiv, Löschen), Menüpunkt „Im Verlauf suchen“ an einer echten Karte, der Tour-Durchlauf, Safari.
- Beobachtung, kein Auftrag: Auf Rolis Bild liegt links über dem Verlaufstext ein runder, halb durchsichtiger Lautsprecher-Knopf. Ob er zur Relay-App oder zum LEIT//PULS-Rahmen gehört, ist nicht nachgesehen.
- Das verwaiste Etikett `skills/mein-gin-tonic-helfer` in `~/.hetzner-app/bibliothek.json` hat keinen Skill mehr; ohne Rolis Wort nicht löschen.
- Im Projektordner liegt eine nicht eingecheckte `UEBERGABE-LAUFEND.md` (geändert, nicht von dieser Karte); nicht angefasst.

## 5. Nächster Schritt

Neue Karte mit „Übergabe lesen“. Zuerst `curl -s localhost:8787/api/version` (soll 255 melden) und Piper auf Port 5005 prüfen. Danach auf Rolis Wort warten oder Korb-Fragen der Neuerungs-Wache abarbeiten.
