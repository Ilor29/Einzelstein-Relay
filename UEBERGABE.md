# Project Handoff: Hetzner-App (Relay)

Version: v14 (ersetzt v13 vom 23.11.)
Date: 2026-11-24, gegen 09:45
Owner/User: Roli
Prepared by: Claude (Karte Hetzner-App 27), automatisch vor Cache-Ablauf

Die Wahrheit steht in `BAUBUCH.md` (Einträge V262 bis V267) und in `~/projekte/Brain/REGISTER.md`. Diese Datei fasst nur zusammen.

## 1. Stand

Relay V267 läuft, `/api/version` meldet 267, Piper auf Port 5005 antwortet. V267 ist committet (9c0df65) und auf `github main` gesichert. Nichts ist halb fertig.

## 2. Was in dieser Karte geschah (24.11.)

- 08:42 Roli: In der PACHMAYR-Karte (und schon bei anderen) bekommt die Karte den Text, der Chatverlauf zeigt ihn nicht. Befund: kein Einzelfall. Lange Diktate und Einfügungen kommen von Claude Code als `<pasted_content id="…">…</pasted_content>`. `hetzner_app/mitschrift.py` blendete jeden Text mit „<" am Anfang als Systemhinweis aus. In drei Tagen traf es sechs Nachrichten. Die Zuordnung der acht laufenden Karten zu ihren Gesprächen war in Ordnung.
- V267: Hülle wird abgestreift, der Text erscheint als „du". Mit der echten PACHMAYR-30-Mitschrift geprüft: die Nachricht von 08:31 steht jetzt im Verlauf. Baubuch ergänzt.

## 3. Beschlüsse (mit Auslöser)

- 08:42 „kannst du bitte prüfen … Karte kriegt die Info, Chatverlauf nicht angezeigt, ob Einzelfall ist“: V267.
- 09:02 „53. Ja“: Handyprobe von V267 gemeinsam. Sobald Roli eine lange Nachricht schickt und die Karte nennt, liest die Karte den Verlauf auf dem Server und gleicht ab; Roli sagt, ob es am Handy erscheint.

## 4. Offen

Bei Roli: Frage 50 (sollen Zeilenkommentare nach dem Neuladen bleiben, Empfehlung Nein) und die Handyprobe von V267 (53). Zuletzt vergebene Nummer: 53, die nächste Frage bekommt die 54. Die alten Fragen 43, 47 und 48 blieben unbeantwortet, gebaut ist jeweils die Empfehlung.

Bei der nächsten Karte, ohne Eile:
- Handyprobe V262 bis V267 steht aus, besonders V266 (Drei-Punkte-Menü, „Änderungen ansehen und kommentieren“) mit einer Karte, die echte Änderungen hat.
- Einfügungen mitten in einer Nachricht: die Hülle `<pasted_content>` wird nur am Textanfang entfernt, mitten im Text bliebe sie sichtbar.
- Ungeprüft: V259 am Handy; breiter Bildschirm nach dem Schließen des Blatts; Tastatur über dem Kommentarfeld; „An die Karte senden“ mit laufender Karte.
- Befehlsliste in V264 veraltet, wenn Claude Code neue Befehle bekommt.
- Aus der Vorkarte: „Im Verlauf suchen“ an echter Karte, Safari, Cron 04:20 der Übersetzung bei Lorenz und Lea, das verwaiste Etikett `skills/mein-gin-tonic-helfer` nicht ohne Rolis Wort löschen.
- Im Projektordner liegt eine ungesicherte Änderung: `UEBERGABE-LAUFEND.md` gelöscht, `UEBERGABE-LAUFEND-vorher.md` geändert. Nicht von dieser Karte, nicht angefasst.

## 5. Nächster Schritt

Neue Karte mit „Übergabe lesen“. Zuerst `curl -s localhost:8787/api/version` (soll 267 melden) und Piper auf Port 5005 prüfen. Dann auf Rolis Wort warten, besonders auf seine Rückmeldung zur Handyprobe.
