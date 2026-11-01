# Übergabe Hetzner-App (Relay), 01.11.2026 13:55 (Karte Hetzner-App 5)

## Stand
Relay V198 läuft. Neu: web/texte.js (Textliste de/en, t(), texteAnwenden(), spracheSetzen()), Abschnitt
„Sprache/Language“ oben in den Einstellungen, Wahl in localStorage „sprache“, Vorgabe Deutsch.
Nur die Einstellungen-Überschriften und -Hinweise sind umgestellt (Schlüssel einst_titel, sprache_*,
stimme_*, diktat_*, tempo_*, geraete_marke). Alles committet (ff2ba04), auf GitHub, Baubuch und Register stehen.

## Beschlüsse
01.11. 11:25 „8. Ja“ (Bau beginnt), 13:50 „9. Ja“ (Texte schreiben und Umstellung, in neuer Karte).

## Nächster Schritt (Schritt 2 bis 7 aus PLAN-ENGLISCHE-OBERFLAECHE.md)
1. Englische Texte für alle 144 Texte und 63 Attribute in web/index.html selbst schreiben, in texte.js
   eintragen, data-t / data-t-attr setzen (Muster steht in den Einstellungen).
2. Die rund 173 Stellen in app.js auf t() umstellen (Umsetzer, Sonnet, mit fertiger Textliste), dazu Tour,
   relative Zeiten, Datumsformate (de-DE ist fest in Zeile ca. 1297, 2097).
3. Server-Meldungen (99) in hetzner_app/texte.py, Sprache per Accept-Language.
4. Englische Piper-Stimme, Browser-Diktat en-US, Whisper mit language.
5. Playwright in beiden Sprachen, automatische Suche nach deutschem Rest, VERSION hoch, READMEs anpassen.

## Offen bei Roli
Handyprobe Whisper-Diktat, Urteil zu Kaira und Aussprachetest Runde 2
(https://seiten-roli.65-21-246-222.sslip.io/kaira-aussprachetest-2/), Anmeldung /login am Montag 03.11.
Nicht am Handy geprüft: Sprachwahl, Whisper-Diktat, Kaira-Vorlesen, Nebenfrage, Antwort-Tasten.

## Testhinweise
Testserver: HETZNER_TTS_PORT=5015 .venv/bin/python /tmp/k192/srv.py (Port 8799, Anmeldung aus).
Beenden mit fuser -k 8799/tcp. Testskript Sprachwahl: /tmp/spr.py (Playwright aus ~/werkzeuge/browser/.venv).
`wait_for_function` geht wegen CSP nicht.

## Rolis letzter Wortlaut
01.11. 13:50 „9. Ja“
