# Übergabe Hetzner-App (Relay), 01.11.2026 17:45 (Karte Hetzner-App 7, Fortsetzung)

## Stand
Relay V199 läuft und ist ausgerollt. Neu: Monitor-Baustein 1, Block „Änderungen dieser Karte“ in der rechten
Spalte „Zur Hand“ (nur am breiten Rechner): git diff je Datei, Plus/Minus mit Vorzeichen, aufklappbar,
Geheimdateien (.env, Schlüssel, Token) nur mit Namen. Dateien: hetzner_app/aenderungen.py, Endpunkte
/api/sessions/{name}/aenderungen und …/datei, Block in web/index.html, app.js (zurHandAenderungen), styles.css.
Baubuch und Register sind nachgetragen (Baubuch „V199“, Register 01.11. 17:25), alles committet (6966623) und gepusht.

## Befunde dieser Karte
- Versuch Nachrichten zwischen Karten (Baustein 10) geglückt: ListAgents/SendMessage laufen in tmux in beide
  Richtungen (Test-Karte Haiku). Offen: ob Karten in anderem Berechtigungsmodus Nachrichten bis zur Freigabe
  zurückhalten; echte Karten nicht angeschrieben. Kaira-Assistent 12 wurde informiert.
- Baustein 3 (Kontextkarte) bestand schon (Block „Diese Karte“, Kontextbalken, Verbrauchsblatt, 200k-Regel). /context
  als Aufteilung ist zu fragil (hunderte Zeilen, schiebt das echte Terminal), bleibt bei der Gesamtzahl.
- Baustein 2 (Aufgabenliste) hat keine Quelle: in keiner Mitschrift ein TodoWrite/TaskCreate. Ruht.
- Fehler von mir: Testserver ohne HETZNER_TTS_PORT=5015 hat den echten Piper verdrängt; Dienst neu gestartet,
  läuft wieder. Testserver immer mit HETZNER_TTS_PORT=5015 starten.
- Der Bauplan unter seiten-roli …/relay-monitor-bauplan/ ist in Baustein 2 und 3 überholt, noch nicht angepasst.

## Beschlüsse
01.11. 16:27 „1. Ja“: Monitor-Ansicht vor englischer Oberfläche. 16:38 „1. Ja, 2. Ja“: Versuch und Reihenfolge.
16:46 „3./4. Deine Empfehlung“: Baustein 3 angehen, Kaira informieren. 17:05 „5. Ja“: Baustein 2 prüfen.
17:11 „6. Ja“: Baustein 1 bauen (jetzt V199).

## Nächster Schritt
1. Rolis Antwort auf Frage 7 abwarten (Antwort-Vorschlag im Eingabefeld als Baustein 12 in den Bauplan) und Frage 8.
2. Bei Ja: Baustein 6 (Kartenliste mit Abschnitten und Statuspunkt, Wort plus Form, nie nur Farbe), dann 7 (Vorschau).
3. Bauplan-Seite an die Befunde anpassen (Baustein 2 ruht, 3 besteht, 10 erledigt, 1 gebaut).
4. Englische Oberfläche danach: Schritt 2 bis 7 aus PLAN-ENGLISCHE-OBERFLAECHE.md.

## Offen bei Roli
7. Antwort-Vorschlag (Screenshot „Archiv der Lücken“: vorgeschlagener Antworttext im Eingabefeld mit Pfeil,
   Rolis Satz „Was ich auch gut finde die antwort unter ootional auswählen“) als Baustein 12 aufnehmen? Empfehlung Ja.
   Meine Deutung (Vorschlag annehmen oder überschreiben) ist nicht bestätigt, Bild liegt nach 14 Tagen nicht mehr da.
8. Mit Baustein 6 weitermachen? Empfehlung Ja.
Außerdem: Anmeldung läuft 03.11. ab (/login); Frage 10 der Kaira-Karte hängt am Versuch (jetzt möglich);
Handyprobe Whisper-Diktat; Aussprachetest Runde 2.

## Rolis letzter Wortlaut
01.11. 17:11 „6. Ja“ und „Was ich auch gut finde die antwort unter ootional auswählen“ (mit Screenshot).
