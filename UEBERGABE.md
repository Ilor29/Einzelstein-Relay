# Project Handoff: Hetzner-App (Relay)

Version: v05 (ersetzt die Übergabe vom 11.11.)
Date: 2026-11-17, gegen 15:40
Owner/User: Roli
Prepared by: Claude (Karte Hetzner-App 19)

Wahrheit liegt in `BAUBUCH.md` (Ende, V246 und V247 vom 17.11.) und `~/projekte/Brain/REGISTER.md` (Eintrag „Hetzner-App 19“, 17.11. 14:00). Diese Datei fasst nur zusammen.

## 1. Stand

Relay V247 läuft, alles committet und auf `github main` gesichert (letzter Commit f5a0b4d), Dienst um 15:04 neu gestartet, Piper antwortet. Nichts halb fertig.

## 2. Was in dieser Karte geschah

- V246: Übergabe automatisch zwei Minuten vor Cache-Ablauf. Modul `hetzner_app/uebergabe_cache.py`, Schleife alle 30 Sekunden im Server. Auftrag beginnt mit „Automatischer Auftrag“. Schutz: UEBERGABE.md jünger als Rolis letzte Nachricht, je Karte ein Auftrag je Cache-Zeit (`~/.hetzner-app/uebergabe-cache.json`), nichts bei Entwurf im Eingabefeld, Dialog, laufender Karte, gemeinsamem Ordner oder wenn Übergabe-Wächter/Kartenwechsel eben selbst schickten. Aus: Datei `~/.hetzner-app/uebergabe-cache.aus`. Log `~/logs/uebergabe-cache.log`. Erster echter Fall: Medienwerk 173 um 15:03, schrieb die Übergabe. Auch diese Karte bekam um 15:40 den Auftrag, also läuft es.
- Panne: Mein erster Probelauf schickte fünf echten Karten (Artcode_lab 2, Distilmind 9, MitrAIse-APP 7, Mixkultur-Systems-Webseite 4, Skillkontor-Pruefung 8) um 13:50 versehentlich den Auftrag. Lehre im Baubuch: Proben mit Ersatzauskunft nur für den Probe-Ordner.
- V247: Glocke standardmäßig aus (Meta, API-Standard, Haken im Formular „Neue Karte“); alle 621 bestehenden Karten einmalig auf aus gestellt.

## 3. Beschlüsse (mit Auslöser)

- Roli 17.11. 13:26: „Cache hat einen Timer, und 2 Minuten bevor die Zeit abläuft wird eine Übergabe geschrieben, egal wie hoch oder niedrig die Token sind.“
- Roli 17.11. 13:49 „185. Deine Empfehlung“ (Eingabezeile prüfen, kein Telegram) und „186. Deine Empfehlung“ (Karten mit gemeinsamem Ordner auslassen).
- Roli 17.11. 15:03 „187. Ja“ (Neustart nach Medienwerk 173), „188. Ja“ (XSS-Gegenprobe) und: „die Benachrichtigungsglocke … standardmäßig gefühlt bei jeder Karte an, die möchte ich gerne aus haben. Und erst wenn ich dann draufdrücke, dass das dann angeht, weil das ist wahnsinnig nervig.“

## 4. Offen

Bei Roli (Nummern laufen weiter, zuletzt vergeben 189):
- 189. Frage an Roli: XSS-Gegenprobe jetzt machen? Empfehlung Ja. Unbeantwortet (188 war „Ja“, daher wohl einfach beginnen).
- 27. Relay-App am Tablet deinstallieren und neu installieren (Manifest V234). 28. Tablet im Querformat prüfen (zwei oder drei Spalten).
- 30. Selten gebrauchte Symbole der Kartenkopfzeile ins Drei-Punkte-Menü? Empfehlung Ja, sobald Roli die Kandidaten nennt (Linkliste, Sichern, Anheften).
- 40. Handyprobe Vorlesen (zweimal schnell „Einen Satz vor“). Rückmeldung zur dunklen Schrift auf den orangen Knöpfen.
- Glocke am Handy einschalten und prüfen (Erlaubnis-Abfrage), nicht geprüft.

Bei mir: XSS-Gegenprobe über `.md`-Inhalt im Browser; Barrierefreiheit (drei Knöpfe unter 40 Pixel, kein Fokusfang, Kontrast Einstellungen/Bibliothek); Google-Weg fängt ungültiges JSON nicht als TTSError. Beschlüsse 33 bis 41 der Vorkarte und die von heute sind im Zweitgehirn (`~/Notizen/02 Projekte/Einzelstein Relay.md`) noch nicht nachgetragen. Echte Wirkung der ungenauen Cache-Uhr (Antwortdauer des letzten Zugs) beobachten.

## 5. Nächster Schritt

Neue Karte mit „Übergabe lesen“, dann XSS-Gegenprobe. Rolis letzter Wortlaut: siehe Beschlüsse oben (15:03).
