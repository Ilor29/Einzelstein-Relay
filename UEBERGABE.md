# Project Handoff: Hetzner-App (Relay)

Version: v08 (ersetzt die Übergabe vom 21.11. gegen 10:10)
Date: 2026-11-21, gegen 14:10
Owner/User: Roli
Prepared by: Claude (Karte Hetzner-App 22)

Die Wahrheit steht in `BAUBUCH.md` (am Ende der Eintrag V253 vom 21.11. mit zwei Nachträgen) und in `~/projekte/Brain/REGISTER.md` (Eintrag „Hetzner-App 22“ vom 21.11. um 13:10). Diese Datei fasst nur zusammen.

## 1. Stand

Relay V253 läuft. Der Dienst wurde nach V253 neu gestartet, `/api/version` meldet 253, Piper lauscht auf Port 5005. Alles ist committet und auf `github main` gesichert. Nichts ist halb fertig. Der Testserver 8799 ist beendet. Roli startet nach dieser Übergabe den ganzen Server neu (sein Wort 14:05).

## 2. Was in dieser Karte geschah

- **Mockup:** `~/seiten/relay-leseflaeche/index.html`, erreichbar unter `https://seiten-roli.65-21-246-222.sslip.io/relay-leseflaeche/`. Es zeigt heute, Vorschlag A (Griff am Rand), Vorschlag B (schlank beim Tippen) und die neue Kopfzeile.
- **V253, Tastatur offen (`body.eng`):** Die Kopfzeile wird flach (43 statt 64 Pixel) und zeigt nur Zurück, Name, Vorlesen und die drei Punkte. Die Schnellbefehle sind eingeklappt, der Blitz-Knopf `#knopf-schnell` links vom Senden-Pfeil holt sie hervor (`schnellKlappe` in app.js). Ein gewählter Befehl oder das Schließen der Tastatur klappt sie wieder ein. Lesefläche 319 statt 246 von 480 Pixeln.
- **V253, Kopfzeile:** Oben stehen Lupe, Terminal, Vorlesen, Freisprech und die drei Punkte, 39 statt 30 Pixel breit. Kette, Sichern und Nadel tragen die Klasse `ins-menue` und sind oben unsichtbar, bleiben aber im Aufbau, weil das Kartenmenü sie auslöst. Neue Menüpunkte: „Gesammelte Links“, „Melden, wenn die Karte dich braucht“, „Stand sichern“. Die Glocke steht oben nur, solange sie an ist. Tour-Schritt „Gesammelte Links“ und die Symbol-Erklärung in den Einstellungen sind nachgezogen.
- **Abweichung vom Mockup:** Der Griff schwebt nicht am Rand über dem Text (hätte „Nebenfrage stellen“ und die Erlaubnis-Knöpfe verdeckt), sondern ist der Blitz in der Knopfzeile des Eingabefelds.
- **Berichtigte Zahl:** Das Mockup nennt „heute 210 Pixel“ und „111 Pixel mehr“. Richtig sind 246 und 73 mehr, weil die Modus-Zeile bei offener Tastatur schon seit 10.10. verschwindet. Das Mockup selbst ist nicht berichtigt.

## 3. Beschlüsse (mit Auslöser)

- Roli 21.11. 12:39: „13. Ja, 14. Deine Empfehlung“ (doppelte Skills aus nicht installierten Plugin-Katalogen bleiben, wie sie sind) und zu 15: „Vielleicht wäre die Überlegung, dass wir die Schnellwahltaste etwas schmäler machen oder sogar seitlich, dass es einklappt, damit man halt einfach wirklich mehr Lesefläche hat … kannst ja gerne ein Mock-up machen.“
- Roli 12:57: „16. Ja, 18. Ja“ (Vorschlag B bauen, Aufteilung der Kopfzeile passt). Frage 17 blieb ohne Antwort, gebaut ist die Empfehlung: einklappen nur bei offener Tastatur.
- Roli 13:41: „19. Ja, testbestanden“ (V253 am Handy mit echter Tastatur). 13:42: „Glocke auch erledigt geht terminal auch“.
- Roli 14:05 zu zwei Bildschirmfotos von 12:37: „war nur als Beleg für dich“. Frage 20 (schwebender Lautsprecher-Knopf über dem Text) ist damit kein Auftrag.

Rolis letzter Wortlaut (14:05): „war nur als Beleg für dich dann sind wir quasi fertig dann würde ich dich bitten dass du jetzt die Übergabe vorbereitest weil wir den Server neu starten müssen“.

## 4. Offen

Bei Roli (die Nummern laufen weiter, zuletzt vergeben: 20):
- Rest von 13: Zeigt die Bibliothek am Handy jeden Skill nur einmal?
- 17: Sollen die Schnellbefehle auch ohne Tastatur hinter dem Blitz liegen? Gebaut ist Nein.
- Alt: 27 (Tablet-App neu installieren), 28 (Tablet quer), 40 (Handyprobe Vorlesen), neue Medienwerk-Karte für die Fish-Werkzeuge.

Bei der nächsten Karte:
- Nichts Gebautes ist offen. Ungeprüft an V253: „Stand sichern“ und Glocke aus dem Menü an einer echten Karte, der Tour-Schritt im Durchlauf, Safari (ohne `:has` bleiben Terminal-Wechsel und Blitz einfach sichtbar).
- Beobachtung aus Rolis Bildern, kein Auftrag: Ein runder, halb durchsichtiger Lautsprecher-Knopf liegt links über dem Verlaufstext. Ob er zur Relay-App oder zum LEIT//PULS-Rahmen gehört, ist nicht nachgesehen. Bei Roli steht in der Kopfzeile außerdem die Sprechblase mit Plus (vermutlich Kaira), die bleibt oben.
- Das verwaiste Etikett `skills/mein-gin-tonic-helfer` in `~/.hetzner-app/bibliothek.json` hat keinen Skill mehr. Ohne Rolis Wort nicht löschen.
- Im Projektordner liegt eine nicht eingecheckte `UEBERGABE-LAUFEND.md`, die nicht von dieser Karte stammt. Nicht angefasst.

## 5. Nächster Schritt

Nach dem Server-Neustart: neue Karte mit „Übergabe lesen“. Zuerst prüfen, ob `hetzner-app.service` wieder läuft (`curl -s localhost:8787/api/version` soll 253 melden) und ob Piper auf Port 5005 lauscht. Danach auf Rolis Wort warten oder die Korb-Fragen der Neuerungs-Wache abarbeiten, sobald welche ankommen.
