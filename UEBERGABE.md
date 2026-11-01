# Übergabe Hetzner-App (Relay), 01.11.2026 01:55 (Karte Hetzner-App 4)

## Stand
Relay V197 läuft, nichts Neues an der App gebaut. In dieser Karte:
- GitHub-Auftritt: README.md und README.en.md auf Stand V197 (Antwort-Tasten, Nebenfrage, Ordnersuche,
  eigene Stimmen, optionales Whisper-Diktat), Repo-Beschreibung zweisprachig und acht Themen auf GitHub.
  Kaira steht nicht mit Namen drin (Fremde bekommen die Stimme nicht), Roli weiß das.
- Mockup englische Oberfläche: https://seiten-roli.65-21-246-222.sslip.io/relay-englisch-mockup/
  (abgenommen, Roli „7. Ja“).
- Plan: PLAN-ENGLISCHE-OBERFLAECHE.md im Projektordner (Umfang, Bauweise, Aufwand 1,5 bis 3 Stunden,
  Risiken). Bau noch nicht freigegeben.
Alles committet und auf GitHub, Baubuch und Register nachgetragen.

## Beschlüsse 31.10./01.11. (Rolis Wortlaut)
- 31.10. 16:11 „1. Ja“ (GitHub-Auftritt als Nächstes), 16:12 „2. Nein“ (Kaira darf im README stehen;
  trotzdem nicht namentlich, siehe oben), 16:46 „1. Ja“ (nur Auftritt, Oberfläche später).
- 01.11. 01:35 „3. Ja“ (englische Oberfläche planen), „4. Was ist fremde?“ (geklärt: andere Server als
  Roli, Lea, Lorenz). 01:37 „5. Deine Empfehlung“ (Whisper NICHT in setup.sh), „6. Mokup“ (erst Mockup).
  01:43 „7. Ja, anmeldung mache ich montag“ (Mockup abgenommen; /login am Montag 03.11.).

## Offen (Nummern laufen weiter, zuletzt 8)
- 8: Frage an Roli, ob der Bau der englischen Oberfläche beginnt (Schritt 1: Gerüst und Sprachwahl);
  meine Empfehlung: erst nach seiner Handyprobe vom Whisper-Diktat.
- Bei Roli: Handyprobe Whisper-Diktat (V197), Urteil zum Klang von Kaira und zum Aussprachetest
  Runde 2 (https://seiten-roli.65-21-246-222.sslip.io/kaira-aussprachetest-2/ , falsche Wörter als
  Liste an die Kaira-Karte), Anmeldung /login am Montag.
- Nicht am echten Handy geprüft: Whisper-Diktat, Kaira-Vorlesen, Nebenfrage-Zettel, Antwort-Tasten.
- Tour-Skript kennt das Diktat noch nicht.

## Nächster Schritt
Rolis Antwort auf 8 abwarten. Bei Ja: PLAN-ENGLISCHE-OBERFLAECHE.md lesen, Schritt 1 bauen
(web/texte.js mit t(), data-t in index.html, Abschnitt „Language“ in den Einstellungen, Vorgabe Deutsch),
englische Texte selbst schreiben, Umstellen der 173 Stellen in app.js an den Umsetzer (Sonnet).

## Testhinweise
Testserver: /tmp/k192/srv.py (Port 8799, Anmeldung ausgehängt, ohne Piper-Start; mit HETZNER_TTS_PORT=5015
für Stimmen). Beenden mit `fuser -k 8799/tcp`. Playwright aus ~/werkzeuge/browser/.venv, Tour-Schalter
vorbelegen. Mockup-Skripte in /tmp/k201/. `wait_for_function` geht wegen CSP nicht, mit evaluate abfragen.

## Rolis letzter Wortlaut
01.11. 01:43 „7. Ja, anmeldung mache ich montag“
