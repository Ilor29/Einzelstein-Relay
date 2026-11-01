# Übergabe Hetzner-App (Relay), 02.11.2026 00:00 (Karte Hetzner-App 9)

## Stand
Relay V207 läuft und ist gesichert (Commit ce03953, GitHub). Heute gebaut (Monitor-Ansicht nach der Claude Desktop App):
V199 Änderungen, V200 jede Datei hochladen, V201 Kartenliste nach Projekt, V202 Antwort-Vorschlag, V203 Vorschau,
V204 Baustein 14 (Spickzettel-Befehle), V205 Baustein 13 (Tastenkürzel), V206 Baustein 4 (Kartenmenü ⋯ mit Fork,
Als ungelesen, Löschen), V207 Baustein 5 (Zurückspulen /rewind in zwei Stufen, Kurzfassung /recap, Esc Esc).
Baubuch, Register und Bauplan (~/seiten/relay-monitor-bauplan/) sind aktuell.

## Beschlüsse
01.11. 19:29 Roli: Englische Oberfläche erst, wenn alles andere steht.
01.11. 19:57 „16.–18. Ja“: Reihenfolge 14, 13, dann 4, 5, 8, 9, ganz am Ende 15, 16, Englisch.
01.11. 23:07 „Wir haben hier genug platz mach mit 4 weiter“, 23:24 „4. Ja“: 4 und 5 in derselben Karte gebaut.

## Rolis letzter Wortlaut
„[01.11. 23:24] 4. Ja“ (Baustein 5 bauen, erledigt). Frage 5 (Baustein 8 als Nächstes, Empfehlung Ja, besser in neuer Karte) ist offen.

## Nächster Schritt
Baustein 8 (Dateibaum zum Lesen), dann 9 (Hintergrundaufgaben mit Stopp), 17 (Cache-Leiste unter dem Eingabefeld, Cache steht schon in Zur Hand), 18 (Kontext nach Posten, vorher /context in tmux ausprobieren), zuletzt 15, 16 und englische Oberfläche (PLAN-ENGLISCHE-OBERFLAECHE.md Schritt 2 bis 7).

## Offen bei Roli
5. Baustein 8 bauen? Dazu: Auswertung „Claude Desktop App neu gebaut“ (tmp-87) ins Zweitgehirn/umsetzen; Anmeldung läuft 03.11. ab (/login); Handyprobe Whisper-Diktat, Kartenmenü, Zurückspulen; Aussprachetest Runde 2; Frage 7/8 der Kaira-Karte.

## Fallen
Testserver: HETZNER_TTS_PORT=5015 PYTHONPATH=. mit .venv-Python (Starter /tmp/ts13.py mit require_auth-Override), Beenden fuser -k 8799/tcp 5015/tcp. Playwright unter ~/werkzeuge/browser/.venv. Der Testserver teilt die tmux-Sitzungen mit dem echten Dienst, Proben nur an Wegwerf-Karten. Steht Text in der Eingabezeile, hängt ein getipptes /Befehl daran (bei Rewind abgefangen). Sichtbarkeit fest positionierter Blöcke mit getClientRects prüfen.
