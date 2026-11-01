# Übergabe Hetzner-App (Relay), 01.11.2026 21:15 (Karte Hetzner-App 9)

## Stand
Relay V205 läuft und ist gesichert (Commit 0acb1c6, auf GitHub). Heute gebaut (Monitor-Ansicht nach der Claude Desktop App):
V199 Änderungen der Karte, V200 Büroklammer nimmt jede Datei, V201 Kartenliste nach Projekt, V202 Antwort-Vorschlag,
V203 Vorschau neben dem Chat, V204 Baustein 14 (Vorschläge vom Spickzettel), V205 Baustein 13 (Tastenkürzel am Rechner:
Esc, Strg K, Strg D, Strg Umschalt D, Strg /). Alle 59 Standbilder des Videos sind angesehen; Bauplan hat neu 17 und 18.
Baubuch, Register und Bauplan-Seite (~/seiten/relay-monitor-bauplan/) sind aktuell.

## Beschlüsse
01.11. 19:29 Roli: Englische Oberfläche erst, wenn alles andere steht (Gedächtnis englische-oberflaeche-erst-zum-schluss).
01.11. 19:57 „16.–18. Ja“: Reihenfolge 14, 13, dann 4, 5, 8, 9, ganz am Ende 15, 16, Englisch.
01.11. 20:46 „1. Ja“: Standbilder ansehen, Nachtrag in den Bauplan (erledigt). 20:47 „2. Ja“: Baustein 13 bauen (erledigt).

## Rolis letzter Wortlaut
„[01.11. 22:58] 3. Ja“ (Baustein 4 bauen). Noch nicht begonnen, das ist der erste Stein der neuen Karte.

## Nächster Schritt
Baustein 4 (Kartenmenü: Umbenennen, Fork, Als ungelesen markieren, In Abschnitt verschieben, Archivieren), danach 5 (Zurückspulen mit Esc Esc, Kurzfassung), 8 (Dateibaum), 9 (Hintergrundaufgaben), dann 17 (Cache-Leiste unter dem Eingabefeld; der Cache steht schon in Zur Hand), 18 (Kontext nach Posten, vorher /context in tmux ausprobieren), zuletzt 15, 16 und die englische Oberfläche (PLAN-ENGLISCHE-OBERFLAECHE.md Schritt 2 bis 7).

## Offen bei Roli
Frage 3 ist mit „Ja“ beantwortet. Dazu aus früher: Auswertung „Claude Desktop App neu gebaut“ (tmp-87) ins Zweitgehirn und/oder umsetzen; Anmeldung läuft 03.11. ab (/login); Handyprobe Whisper-Diktat und der neuen Kürzel-Blätter; Aussprachetest Runde 2; Frage 7/8 der Kaira-Karte.

## Fallen
Testserver mit HETZNER_TTS_PORT=5015 und PYTHONPATH=. starten, Beenden mit fuser -k 8799/tcp 5015/tcp. Playwright liegt unter ~/werkzeuge/browser/.venv (nicht im Projekt-.venv). Bei fest positionierten Blöcken ist offsetParent leer, Sichtbarkeit mit getClientRects prüfen.
