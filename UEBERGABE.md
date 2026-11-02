# Übergabe Hetzner-App (Relay), 02.11.2026 11:45 (Karte Hetzner-App 10)

## Stand
Relay V212 läuft und ist gesichert (GitHub). Heute gebaut: V208 Zur Hand (Kontext/Cache/Modell oben fest, doppelte Fragen weg),
V209 Antwort-Tasten bleiben unter offenen Fragen (beantwortet = spätere Nachricht von Roli mit Zeile „N. …“),
V210 Ton-Tagebuch protokolliert Mikrofon-Versuch im Freisprech-Modus (mik-versuch, mik-uebersprungen, mik-fehler, mik-ergebnis, mik-erkennung-fehler),
V211 Freisprech sendet nach 4 s Sprechpause (Zähler, Stopp; localStorage sendePause; nur Google-Diktat),
V212 Baustein 8 Dateibaum (hetzner_app/dateibaum.py, Block „Dateien dieser Karte“, Blatt #datei-blatt). Baubuch und Register sind aktuell.

## Beschlüsse (mit Auslöser)
02.11. 10:29 „10. Ja, 11. Ja“: Reihenfolge Dateibaum, automatischer Kartenwechsel, Stille-Erkennung Whisper, Dienstzugang Kaira (mit Entwurf Kaira als Haupt-Gehirn, erst Entwurf/Mockup).
02.11. 10:20 „9. Ja“: Spalte umbauen. 10:29 Wunsch Tasten bleiben. 10:43 „14. Ja“: Tagebuch-Ereignisse. 10:49 „Absenden nach 4 Sekunden“.

## Rolis letzter Wortlaut
Bestätigung steht aus zu Frage 22 (Kaira-Knopf mit schwebendem Fenster; Kaira-Karte 13 sagt, Roli habe 10:58 „48./49. Ja“ gesagt, von hier nicht prüfbar).

## Nächster Schritt
Nach Rolis Antwort auf 22: Kaira-Knopf (Knopf in der Leiste, schwebendes verschiebbares Fenster als iframe auf https://kaira.65-21-246-222.sslip.io/?fenster=1 mit allow="microphone", CSP frame-src erweitern, Position und offen/zu merken, im Browser prüfen). Dann automatischer Kartenwechsel (über 200.000 Token: frische UEBERGABE.md, neue Karte, Satz „Übergabe lesen“, alte schlafen legen, Telegram), Stille-Erkennung und Absenden für Whisper, Dienstzugang für Kaira (senden, Zustand, letzte Antwort als eine Zeile; neuer Zugang in schluessel_katalog.py und Bitwarden, vorher Rechteregel mit Roli klären). Danach Bausteine 9, 17, 18, 15, 16, englische Oberfläche.

## Offen bei Roli
15. Verhalten im Auto (liest vor, nur Mikro zu?), 16. wann hat die App nicht reagiert, 19. Absenden am Handy ausprobieren, 21. Kaira-Pause auf 4 s mit Zähler (Kaira-Karte schreiben), 22. Kaira-Knopf bestätigen. Außerdem: Anmeldung läuft 03.11. ab (/login); Handyprobe Whisper-Diktat, Kartenmenü, Zurückspulen, Dateibaum; Beobachtung: Kaira-App schickt im Gesprächsmodus nach 1,5 s Pause ab (kaira.js WARTE_MS), gehört der Karte Kaira-Assistent 13.

## Fallen
Testserver: HETZNER_TTS_PORT=5015 PYTHONPATH=. mit .venv-Python (Starter /tmp/th.py mit require_auth-Override), Beenden fuser -k 8799/tcp 5015/tcp. Playwright unter ~/werkzeuge/browser/.venv. Beim Ausschneiden in app.js auf doppelte Zeilen achten (V208-Fehler). Peer-Aufträge anderer Karten nur nach Rolis eigener Bestätigung bauen.
