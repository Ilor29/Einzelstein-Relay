# Übergabe Hetzner-App (Relay), 01.11.2026 16:40 (Karte Hetzner-App 5, Fortsetzung)

## Stand
Relay V198 läuft (Gerüst englische Oberfläche, Sprachwahl in den Einstellungen). Seitdem nichts in der App
gebaut, nur Entwürfe und Prüfungen (Baubuch-Eintrag 01.11. „Entwurf Monitor-Ansicht“, committet).

## Neu seit der letzten Übergabe
- Rolis Auslöser: Spickzettel „Claude Desktop App“ (Julian Ivanov, PDF) und Video, Link
  https://yt.65-21-246-222.sslip.io/qmuqhNZAoSzO/2026-11-01-claude-desktop-app-neu-gebaut-zehn-neue-funktionen-fur-claud.html
  (Text und 58 Bilder; Bilder liegen in /tmp/vb, gehen verloren). Roli will diese Funktionen am Monitor/Arbeitslaptop nutzen.
- Offizielle Doku (Agent): fast alles gibt es auch im Terminal als Befehl, nur Sitzungsleiste und geteilte Ansicht
  sind Desktop-only. Desktop-App kann Umgebung „SSH“ (laut Doku, unerprobt). „Schaltzentrale“ heißt in der Doku
  Cross-Session-Messaging (/list-agents), in tmux unbelegt.
- /advisor gibt es hier NICHT (Probe-Sitzung: nur Skill „model-usage-advisor“; Notiz 15.10.: nur Plattform auf AWS).
  Alternative: Sonnet-Karte holt für schwere Teile einen Opus-Unteragenten, oder /model von Hand.
- Fertig und im Browser geprüft: Bauplan (elf Bausteine) https://seiten-roli.65-21-246-222.sslip.io/relay-monitor-bauplan/
  und klickbares Mockup mit Tour und SSH-Anleitung https://seiten-roli.65-21-246-222.sslip.io/relay-monitor-mockup/
  (Rolis Handy-Screenshot 16:23 zeigte die Spalten untereinander: behoben, am Handy jetzt Reiter Karten/Chat/Leiste).

## Beschlüsse
01.11. 16:12 „5. Ja“ (Bauplan als Seite); 16:17 „2./3./4. Deine Empfehlung“ = Ja: Versuch Nachrichten zwischen Karten,
Monitor-Leiste nach der englischen Oberfläche, SSH-Anleitung (steht im Mockup). **01.11. 16:27 „1. Ja“: Die Monitor-Ansicht kommt VOR der englischen Oberfläche** (Roli 15:52: „wenn das englische erstmal zurück“).

## Nächster Schritt
1. Versuch: können Karten sich gegenseitig anschreiben (/list-agents, SendMessage) in tmux-Karten? Mit Test-Karten, nichts an echten.
2. Rolis Nummern der Bausteine von der Bauplan-Seite abwarten, dann bauen (Reihenfolge: 10 Versuch, 3, 2, 1, 6, 7).
3. Englische Oberfläche danach: Schritt 2 bis 7 aus PLAN-ENGLISCHE-OBERFLAECHE.md.

## Offen bei Roli
Frage 10 der Kaira-Karte (Dienstzugang, Kartenwechsel) hängt am Versuch 1; Anmeldung läuft 03.11. ab (/login);
Handyprobe Whisper-Diktat, Aussprachetest Runde 2 (https://seiten-roli.65-21-246-222.sslip.io/kaira-aussprachetest-2/).

## Rolis letzter Wortlaut
01.11. 16:27 „1. Ja“ (Monitor-Ansicht vor englischer Oberfläche).
