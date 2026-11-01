# Übergabe Hetzner-App (Relay), 01.11.2026 20:50 (Karte Hetzner-App 8)

## Stand
Relay V204 läuft und ist gesichert. Heute gebaut (Monitor-Ansicht nach der Claude Desktop App):
V199 Änderungen der Karte, V200 Büroklammer nimmt jede Datei (200 MB), V201 Kartenliste nach Projektordner,
V202 Antwort-Vorschlag über dem Eingabefeld, V203 Vorschau neben dem Chat (Webspace-Adresse in
~/.hetzner-app/umgebung als HETZNER_APP_VORSCHAU_BASIS). Baubuch, Register, Bauplan-Seite sind aktuell.
Bauplan: ~/seiten/relay-monitor-bauplan/ (Bausteine 1 bis 16).

## Beschlüsse
01.11. 19:29 Roli: Englische Oberfläche erst, wenn alles andere steht und geändert ist (Gedächtnis
englische-oberflaeche-erst-zum-schluss). 19:30 „15. Ja“: Spickzettel gegen Bausteine abgleichen (erledigt, neu 13 bis 16).
Das Video selbst liegt nicht auf dem Server; verglichen wurden Spickzettel-PDF und die Auswertung der YouTube-Bibliothek
(/opt/yt-auswertung/auswertungen/2026-11-01-claude-desktop-app-…txt), beides deckt sich mit den Bausteinen.

## Nächster Schritt (Roli „16.–18. Ja“, 22. Ja)
1. Gebaut: Baustein 14 (V204). Danach: die 59 Standbilder der Video-Auswertung ansehen (Frage 22 „Ja“, Ort: /opt/yt-auswertung/web/qmuqhNZAoSzO/bilder/…) und Nachtrag in den Bauplan.
2. Baustein 13 (Tastenkürzel am Rechner).
3. Bausteine 4 (Kartenmenü), 5 (Zurückspulen, Kurzfassung), 8 (Dateibaum), 9 (Hintergrundaufgaben).
4. Ganz am Ende: 15 (Ausgabestil), 16 (zwei Karten), dann englische Oberfläche (PLAN-ENGLISCHE-OBERFLAECHE.md Schritt 2 bis 7).

## Offen bei Roli
16. Baustein 14 als Nächstes? 17. Dann 13? 18. Danach 4, 5, 8, 9? (Empfehlung jeweils Ja.)
19. Auswertung „Claude Desktop App neu gebaut“ (über tmp-87): Zweitgehirn, umsetzen oder beides (siehe Antwort in der Karte).
Außerdem: Anmeldung läuft 03.11. ab (/login); Handyprobe Whisper-Diktat; Aussprachetest Runde 2; Frage 7/8 der
Kaira-Karte hängt am Versuch (Nachrichten zwischen Karten geht in tmux).

## Fallen
Testserver immer mit HETZNER_TTS_PORT=5015 und PYTHONPATH=. starten, Beenden mit fuser -k 8799/tcp 5015/tcp.
