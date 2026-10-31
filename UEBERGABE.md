# Übergabe Hetzner-App (Relay), 31.10.2026 09:45

## Stand
Relay V191 ausgerollt und auf GitHub: Ordnersuche mit Lupe in „Neue Sitzung“, Chip „Übergabe
lesen“, „Fragt nie“ vorbelegt, neue Karten starten mit Sonnet (Aufwecken behält das Modell),
Schnellbefehl-Leiste am Rechner per Mausrad rollbar. Baubuch (31.10., V191), Register und
Zweitgehirn („02 Projekte/Einzelstein Relay.md“) sind nachgetragen. APK-Anregung gelöscht.

## Beschlüsse 31.10.
- Roli 09:22 (Screenshot „Neue Sitzung“): Lupe, Übergabe-Chip, Fragt nie an, Sonnet als Start.
- Roli 09:22 „5. Ja“: APK über die Büroklammer kommt am Handy an. „8. Ja“: Anregung löschen.
- Über die Kaira-Karte (Roli 00:48 „24. Ja“, 04:03 „25. Ja“, 09:03 „27. Ja“): Relay liest mit
  Kairas Piper-Stimme vor, wählbar in den Einstellungen, Kaira als Vorgabe, alte Stimme bleibt.
  Nur in Rolis Relay (Lizenz der Trainingsdaten ungeprüft). Auftrag:
  ~/projekte/Kaira-Assistent/AUFTRAG-RELAY-STIMME.md (Modell stimmen/kaira/kaira_de-DE.onnx).

## Offen (Fragen an Roli, Nummern laufen weiter)
- 9: Kairas Stimme jetzt einbauen? (Empfehlung Ja)
- 10: Lokales Diktat (Whisper auf dem Server) als zweite Wahl neben Google, gegen Aussetzer
  und Verhörer? (Empfehlung Ja, nach der Stimme). Unklar: Rolis Satz „dann ein bitte überprüfen“.
- 11: Zweisprachig und auf GitHub bewerben, Kehrtwende zum Beschluss 03.08. (Relay bleibt
  persönliches Werkzeug)? Empfehlung Ja, ohne „Claude“ im Namen, Hinweis auf eigenes Abo.
- Roli 09:31 schickte den Artikel „Claude Code 2.0“ (kiberatung.de, Text in
  /tmp/claude-code-2-0-beitrag.md): ganz gelesen, Doku-Prüfung durch Agenten lief, Antwort an
  Roli noch offen. Konkreter Fund: Relay sperrt Senden, während Claude arbeitet; `/btw`
  (Nebenfrage) wäre damit vom Handy nicht nutzbar.
- Karte Zerlegen weiß noch nicht, dass .apk direkt geht (läuft nicht).

## Nächster Schritt
Rolis Antworten zu 9 bis 11 abwarten, dann Kairas Stimme (eigener Stein, Hörprobe als Link).

## Wissen
Recherche ähnlicher Werkzeuge: ~/projekte/Brain/wissen/relay-aehnliche-werkzeuge-2026-10-31.md

## Merkhilfe für Tests
Testserver: PYTHONPATH=Projektordner, Anmeldung aushängen, app.router.on_startup.clear(),
Port 8799, beenden mit fuser -k 8799/tcp. Playwright in ~/werkzeuge/browser/.venv, Tour-Schalter
relay_tour_liste_v1 und relay_tour_sitzung_v1 auf "1".
