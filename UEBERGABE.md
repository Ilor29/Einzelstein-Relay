# Übergabe Hetzner-App (Relay), 31.10.2026 11:25 (Karte Hetzner-App 2, Kontext rund 170k)

## Stand
Relay V194 ausgerollt und auf GitHub. Heute in dieser Karte gebaut, alles in Baubuch und Register:
- V192: Kairas Piper-Stimme liest vor, Vorgabe in Rolis Relay, Jonas wählbar. Modell nur in
  ~/.hetzner-app/stimmen, nicht im Repo (Lizenz Trainingsdaten ungeprüft, Lea/Lorenz ohne Kaira).
- V193: Knopf „Nebenfrage stellen“ (/btw) in der Leiste „Claude denkt nach“, Antwort auf einem
  Zettel über der Eingabe. Behoben: offenes /btw-Fenster verschluckte Nachrichten (Wächter-Zustand
  „nebenfrage“, Escape nur wenn das Fenster offen ist).
- V194: Aussprache-Liste aus Kaira-Assistent/server/aussprache.txt, nur für Kairas Stimme.
Hörproben: https://seiten-roli.65-21-246-222.sslip.io/relay-kaira-stimme/ (1 bis 4).

## Beschlüsse 31.10. (Rolis Wortlaut)
- 10:16 „9. Ja“ Kaira-Stimme (gebaut). „10. Ja“ lokales Whisper-Diktat als zweite Wahl neben
  Google, gegen Aussetzer und Verhörer. „11. Ja“ Relay zweisprachig und auf GitHub bewerben,
  Kehrtwende zum 03.08., ohne „Claude“ im Namen, Hinweis aufs eigene Abo, Kaira bleibt draußen.
- 10:46 „17. Ja“ Nebenfrage-Knopf (gebaut). 11:12 „19. Ja“ Aussprache-Liste (gebaut).
- Alle drei Beschlüsse stehen auch im Zweitgehirn „02 Projekte/Einzelstein Relay.md“.

## Offen (Nummern laufen weiter, zuletzt 19)
- 18: Roli soll sich neu anmelden (/login), Claude Code meldete „login expires in 3 days“.
- Tasten-Rätsel (15/16): Roli 10:46 „Das war übrigens in deinem eigenen Chat“, also in der
  Hetzner-App-Karte verschwanden die Antwort-Tasten unter nummerierten Fragen. Erkennung in
  web/app.js schreibeMitWahl() / baueWahlReihe prüfen, mit Rolis echten Antworttexten aus dieser
  Karte (Fragen mit „N. Soll ich …? Meine Empfehlung: …“) im Testbrowser nachstellen.
- Rolis Urteil zum Klang von Kaira und zur Aussprache steht aus.
- Nicht am echten Handy geprüft: Kaira-Vorlesen, Nebenfrage-Zettel.
- Danach: Whisper-Diktat (10), dann GitHub-Auftritt zweisprachig (11).

## Nächster Schritt
Tasten-Rätsel nachstellen und beheben, dann Whisper-Diktat planen (Aufwand und Modell vorher nennen).

## Testhinweise
Testserver: /tmp/k192/srv.py mit HETZNER_TTS_PORT=5015 starten (eigener Test-Piper), danach
Server UND Test-Piper über ihre echten PIDs beenden (PID-Datei hält nur die Hülle).
Probe-Sitzungen auf eigenem tmux-Kanal, in der App über die Kennung „kanal:sitzung“ ansprechbar,
dann taucht keine Testkarte in Rolis Liste auf.

## Rolis letzter Wortlaut
11:12 „19. Ja“
