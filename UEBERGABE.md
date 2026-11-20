# Project Handoff: Hetzner-App (Relay)

Version: v06 (ersetzt die Übergabe vom 17.11.)
Date: 2026-11-20, gegen 23:58
Owner/User: Roli
Prepared by: Claude (Karte Hetzner-App 20)

Die Wahrheit liegt in `BAUBUCH.md` (Ende: XSS-Gegenprobe, V248, Nachtrag Fish-Anmeldung, V249, V250, alle vom 20.11.) und in `~/projekte/Brain/REGISTER.md` (Einträge „Hetzner-App 20“ vom 20.11. 22:45 und 23:55). Diese Datei fasst nur zusammen.

## 1. Stand

Relay V250 läuft. Alles ist committet und auf `github main` gesichert. Der Dienst wurde nach V250 neu gestartet, `/api/version` meldet 250 und Piper antwortet. Nichts ist halb fertig. Die Probe-tmux-Server (`probemcp`, `fishauth`, `hz-probeterm`) sind weg, und der Testserver 8799 ist beendet.

## 2. Was in dieser Karte geschah

- **XSS-Gegenprobe** für den Verlaufstext: bestanden, ohne Codeänderung. Acht Schadtexte über `schreibe()` im Browser, kein Skript lief. Die übrigen 28 `innerHTML`-Stellen sind nicht geprüft.
- **V248, `/mcp`:** Das Menü galt wegen „Esc to close“ und „Esc to go back“ als frei, deshalb schloss die nächste Nachricht es („MCP dialog dismissed“ bei Medienwerk 175). Jetzt gilt es als abbrechbar, und `_eingabe_bereit` drückt bis zu dreimal Escape. Die MCP-OAuth-Seite hat den eigenen Zustand `mcp-anmeldung`. `state.mcp_anmeldung` fährt im `/frage`-Takt als `mcpAnmeldung` mit. Neuer Endpunkt `POST /api/sessions/{name}/mcp-rueckgabe` (nur `http://localhost` und `127.0.0.1`). Der Anmelde-Kasten hat jetzt eine MCP-Fassung mit Link und Feld für die Rückgabe-Adresse.
- **Fish Audio angemeldet** über die Nebensitzung im Medienwerk-Ordner: `claude mcp get fish-audio` meldet „Connected“. Die Werkzeuge erscheinen erst in einer NEUEN Medienwerk-Karte, Medienwerk 175 weiß das. Lehre: Claude Code wartet nach „Authenticate“ nur etwa fünf Minuten. Zwei Anläufe liefen ab, einmal kam die Adresse vom alten Link.
- **V249, Terminal am Handy abgeschnitten:** `fenster_zuruecksetzen` (resize-window) stellte tmux auf `window-size manual`, deshalb blieb das Fenster bei 120x40, obwohl das Handy 52x23 meldete. Jetzt ruft der WebSocket nach dem Anhängen `tmux.resize(name, cols, rows)` auf.
- **V250, Linkliste:** zeigt die Uhrzeit der Antwort, sortiert danach, markiert den obersten Link mit „neueste“ (als Wort im Rahmen) und zeigt bei langen Adressen Anfang und Ende.
- Brains Auftrag Teil 1 (automatische Übergabe vor Cache-Ablauf) lief schon seit V246, er wurde nicht neu gebaut.

## 3. Beschlüsse (mit Auslöser)

- Roli 20.11. 22:09: „1. Ja“ (XSS-Gegenprobe), „2. Nein, bitte medienwefk fragen wegdn mpc“ (Frage 95 bei Medienwerk erfragt, dort unbekannt, als nicht auffindbar liegen gelassen).
- Brain-Auftrag 22:10 (Teil 2): Erst sagen, welcher Weg bei `/mcp` sinnvoller ist, dann bauen.
- Roli 22:29: „1. Ja, 2. Ja“, erst an einer Probekarte durchspielen, dann nur Link und Einfügefeld in die Lese-Ansicht holen, keinen ganzen Dialog nachbauen (V248).
- Roli 22:59: „3. Ja“ (Neustart, sobald keine Karte arbeitet).
- Roli 23:06: „Das ist aber nicht sichtbar hier in der App“ (Bildschirmfotos vom Terminal), 23:10 „6. Ja, 7. Ja“ (Fish über Nebensitzung, Terminal reparieren).
- Roli 23:37: „wenn du gleich Links hast sehe ich nicht welches das neueste ist. Auch übrigens eine Verbesserung für die App“, 23:39 „12. Ja, Frag nur was du wirklich nicht entscheiden kannst!“ (im Gedächtnis `nur-fragen-was-ich-nicht-entscheiden-kann` als dritte Wiederholung nachgetragen).

Rolis letzter Wortlaut: „12. Ja, Frag nur was du wirklich nicht entscheiden kannst!“ (23:39). Danach kamen nur noch Adressen aus dem Browser (23:29, 23:33, 23:36, 23:38).

## Bewusst weggelassen

Der vollständige Wortlaut des Brain-Auftrags von 22:10 (Teil 1 automatische Übergabe vor Cache-Ablauf, Teil 2 `/mcp`) steht nicht hier. Teil 1 war schon seit V246 gebaut und läuft, Einzelheiten stehen im Baubuch unter V246. Teil 2 ist mit V248 erledigt und oben zusammengefasst.

## 4. Offen

Bei Roli (die Nummern laufen weiter, zuletzt vergeben: 12):
- Terminal am Handy ansehen, ob es jetzt passt (V249).
- Für die Fish-Werkzeuge eine neue Medienwerk-Karte öffnen.
- Alt: 27 (Tablet-App neu installieren), 28 (Tablet quer), 30 (selten gebrauchte Kopfzeilen-Symbole ins Drei-Punkte-Menü), 40 (Handyprobe Vorlesen), Glocke am Handy einschalten und prüfen.

Bei der nächsten Karte:
- Im MCP-Kasten auf die Frist von etwa fünf Minuten hinweisen. Klein, ohne Frage gleich machen.
- Barrierefreiheit: drei Knöpfe unter 40 Pixel, kein Fokusfang, Kontrast in Einstellungen und Bibliothek.
- Der Google-Weg in `tts.py` fängt ungültiges JSON nicht als TTSError.
- Die übrigen `innerHTML`-Stellen in app.js auf XSS durchsehen.
- Die Wirkung der ungenauen Cache-Uhr beim automatischen Übergabe-Auftrag weiter beobachten (`~/logs/uebergabe-cache.log`).

## 5. Nächster Schritt

Neue Karte mit „Übergabe lesen“. Dann den Fünf-Minuten-Hinweis im MCP-Kasten einbauen und danach die Barrierefreiheit angehen. Nur fragen, was Roli wirklich entscheiden muss.
