# Übergabe Hetzner-App (Relay), Karte Hetzner-App 14, 11.11.2026 gegen 10:30

**Thema:** Durchsicht der App mit dem neuen Modell Fable 5.2 (Logik, Aufbau, Erweiterungen). Wahrheit liegt in BAUBUCH.md (Ende) und ~/projekte/Brain/REGISTER.md.

## Fertig
- Relay V224 läuft, gesichert (github main), Arbeitsordner sauber.
- Fable 5.2 in den Preistabellen für „Wert ohne Abo“: hetzner_app/verbrauch.py und leitstand/token-bauen.py (8 / 40 / 0,20 Dollar je Million Token), dazu Anzeigename im LEIT//PULS. Cache-Lesepreis Sonnet 5.5 auf 0,10 korrigiert (nicht abgesprochen, Roli gemeldet).
- Server-Teil ganz gelesen (tmux.py, state.py, server.py). Befunde stehen im Baubuch, Eintrag „11.11.2026: Durchsicht Server-Teil“. An der Logik wurde nichts geändert.
- Handyprobe V219 bis V223: Roli hat viel getestet, nichts Auffälliges („4. Nein“).

## Offen: vier Fragen an Roli, noch ohne Antwort
5. Modell-Anzeige aus der letzten Antwort der gebundenen Mitschrift lesen statt aus der Bestätigungszeile am Schirm? Empfehlung Ja. (Das ist Rolis Fehler „nicht in allen Karten wird Fable 5.2 angezeigt“: Medienwerk 167 läuft mit Fable 5.2, gemerkt nur „Fable“; Skillkontor-Marketing 39 als Fable gemerkt, letzte Antwort von Sonnet 5.5, Ursache ungeklärt.)
6. Kontext-Balken und Euro-Wert an die Mitschrift der Karte binden statt an die jüngste Datei des Ordners (verbrauch.kontext, verbrauch.gegenwert)? Empfehlung Ja.
7. Danach einzeln: Aufweck-Kette (`--resume || --continue || frisch` springt auch bei spätem Absturz an), Modus-Knopf tippt Umschalt+Tab ohne Dialog-Prüfung (Wirkung im Dialog nicht nachgeprüft), state.frage() sucht „esc to in“ auf dem ganzen Schirm? Empfehlung Ja, je mit Probekarte.
8. Danach Oberfläche (web/, 7.800 Zeilen) durchsehen und mit den Bildern der neuen Original-App-Einstellungen vergleichen, in eigener Karte? Empfehlung Ja.

## Weiter offen
- Nicht gelesen: mitschrift.py, melden.py, strom.py, tts.py, geraete.py, übrige Module, ganze Oberfläche.
- Verhalten im Auto (Diktat, Freisprechen, Ton-Tagebuch): Roli im Urlaub, frühestens um den 22.11.
- Baustein 16 zwei Karten nebeneinander; Baustein 11 Teil 3; Auslieferer für Lea und Lorenz; Englisch zum Schluss; Baustein 18 zurückgestellt; Remote Control liegt.

## Nächster Schritt
Rolis Antworten auf 5 bis 8 abwarten. Bei „5. Ja“ zuerst die Modell-Anzeige, dann 6, ein Stein nach dem anderen. Vorher nichts bauen.

## Beschlüsse dieser Sitzung
- Roli 11.11. 09:49: „ich möchte das du die app auf logik aufbau uodates erweiterungen prüfts mit der neuen version“ (Durchsicht mit Fable 5.2).
- Roli 11.11. 09:54: „2. Ja“ (Preis Fable 5.2 nachschlagen, in beide Tabellen), „3. Ja“ (Durchsicht mit dem Server-Teil beginnen, erst Befunde, dann ändern), „4. Nein“ (beim Testen nichts aufgefallen), dazu „Neuer original app aufbau“ mit zwei Bildern der Einstellungen (Gruppen im Baubuch V224 notiert, Bilder verfallen nach 14 Tagen).

## Hinweise für die neue Karte
Fragen-Nummern laufen weiter, zuletzt 8. Die Relay startet neue Karten mit Sonnet (Beschluss 31.10.); Roli hat diese Karte von Hand auf Fable gestellt. Testserver Port 8799 mit ausgehängter Anmeldung, Beenden mit fuser -k 8799/tcp; nie tts aus zweitem Prozess laden; Probekarten nur auf eigenem tmux-Socket. Preise stehen doppelt (Relay und leitstand), bei neuen Modellen beide nachtragen.

## Rolis letzter Wortlaut
„2. Ja / 3. Ja / 4. Nein / Neuer original app aufbau“ (11.11. 09:54, mit zwei Bildern).
