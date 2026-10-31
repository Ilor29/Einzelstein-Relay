# Übergabe Hetzner-App (Relay), 31.10.2026 12:40 (Karte Hetzner-App 3, Kontext rund 155k)

## Stand
Relay V197 ausgerollt und auf GitHub. In dieser Karte gebaut, alles in Baubuch und Register:
- V195: Tasten-Rätsel gelöst. Antwort-Tasten unter nummerierten Fragen blieben nur unter den
  letzten drei Antworten stehen; jetzt bleiben sie, bis Roli nach der Frage etwas schreibt.
- V196: Satzzeichen hinter Lautschrift in [[ ]] kommt vor die Klammern (Hinweis der Kaira-Karte).
- V197: Eigenes Diktat mit Whisper (small) als zweite Wahl in Einstellungen, Abschnitt „Diktat“
  (Google bleibt Vorgabe). Server: hetzner_app/diktat.py und whisper_worker.py (Python aus
  ~/werkzeuge/whisper/.venv, Arbeiter bleibt warm, 10 Minuten Leerlauf), POST/GET /api/diktat.
  Aufnahme per Tipp, zweiter Tipp erkennt, Kreuz verwirft. Wortschatz-Hinweis aus Kairas aussprache.txt.
- Aussprachetest für Kaira: Seite ~/seiten/kaira-aussprachetest/ (189 Wörter), Rolis Falschliste
  (61 Wörter) ging an die Kaira-Karte, die hat sie als Lautschrift eingetragen und Runde 2 gebaut:
  https://seiten-roli.65-21-246-222.sslip.io/kaira-aussprachetest-2/ (Roli hat sie noch nicht abgehakt).

## Beschlüsse 31.10. (Rolis Wortlaut)
- 11:24 „20. Ja“ Tasten-Rätsel zuerst (gebaut). 11:33 „21. Ja, und bitte auch ein test mit den
  gängigsten englischen wörtern“ (gebaut). 11:59 „Ja“ auf Frage 22: Whisper-Diktat mit Modell small
  und Wortschatz als Hinweis (gebaut). Frühere Beschlüsse 10 und 11 siehe Zweitgehirn
  „02 Projekte/Einzelstein Relay.md“.

## Offen (Nummern laufen weiter, zuletzt 23)
- 18: Roli soll sich neu anmelden (/login), Claude Code meldete „login expires in 3 days“.
- 23: Frage an Roli, ob der zweisprachige GitHub-Auftritt (Beschluss 11) als Nächstes drankommt;
  meine Empfehlung: erst nach seiner Handyprobe vom Diktat.
- Nicht am echten Handy geprüft: Whisper-Diktat (Mikrofon-Erlaubnis, Aufnahmeformat Chrome Android,
  Freisprech-Modus ohne Stille-Erkennung), Kaira-Vorlesen, Nebenfrage-Zettel, neue Antwort-Tasten.
- Rolis Urteil zum Klang von Kaira und zu Aussprachetest Runde 2 steht aus; falsche Wörter kommen
  als kopierte Liste, die geht an die Kaira-Karte (Kaira-Assistent), nicht in die Relay.
- Das Tour-Skript kennt das Diktat noch nicht (Wahl in den Einstellungen, kein Tour-Schritt).

## Nächster Schritt
Rolis Antwort auf 23 abwarten. Danach GitHub-Auftritt zweisprachig (Aufwand und Modell vorher nennen;
ohne „Claude“ im Namen, Hinweis aufs eigene Abo, Kaira bleibt draußen).

## Testhinweise
Testserver: /tmp/k192/srv.py (Port 8799, ohne Piper-Start; mit HETZNER_TTS_PORT=5015 für Stimmen).
Beenden mit `fuser -k 8799/tcp`. Playwright aus ~/werkzeuge/browser/.venv; Fake-Mikrofon mit
`--use-fake-device-for-media-stream --use-file-for-fake-audio-capture=<wav>` (Beispiel /tmp/k195/dik.py).
Hinweis: `wait_for_function` geht wegen der CSP nicht, mit evaluate abfragen.

## Rolis letzter Wortlaut
11:59 „Ja“ (auf Frage 22)
