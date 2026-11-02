# Übergabe Hetzner-App (Relay), 02.11.2026 17:30 (Karte Hetzner-App 11)

## Stand
Relay V216 läuft und ist gesichert (GitHub). Heute gebaut und ausgerollt:
V213 Kaira-Knopf (zuerst schwebender Rahmen, ging nicht: Tor-Cookie kommt im Rahmen nicht an),
V215 Kaira-Knopf öffnet Kaira in eigenem Fenster (am Handy bestätigt, Roli 16:43 „geht“),
V214 Whisper-Diktat endet nach 2,5 s Stille, Freisprech sendet danach mit Zähler,
V216 Cache-Uhr unter dem Eingabefeld (Monitor-Baustein 17).
Ohne App-Version: automatischer Kartenwechsel (hetzner_app/kartenwechsel.py, Cron alle 5 Min, Ausschalter ~/.hetzner-app/kartenwechsel.aus, Protokoll ~/logs/kartenwechsel.log) und Kartendienst für Kaira (hetzner_app/kartendienst.py, Dienst hetzner-kartendienst auf 127.0.0.1:8831, Schlüssel ~/.kaira-karten-schluessel, Katalog kaira-karten, Protokoll ~/logs/kaira-karten.log). Baubuch und Register sind aktuell.

## Beschlüsse (mit Auslöser)
02.11. 14:24 „1. Ja“ Kaira-Knopf; 16:14 „1. Ja“ eigenes Fenster statt Rahmen, „2. Deine Empfehlung“ Tor-Cookie nicht umstellen lassen.
02.11. 14:30 „1. Ja“ Kartenwechsel; 14:38 „1. Ja“ Stille-Erkennung; 15:32 „1. Ja“ Dienstzugang; 16:00 „1. Nein“ Kartenschlüssel nicht in Bitwarden (ersetzbar).
02.11. 17:06 „1. Ja“ Kaira-Karte soll den Assistenz-Teil anfangen (Auftrag an Kaira-Assistent 13 gesendet); 17:07 „1. Ja“ Cache-Uhr.

## Rolis letzter Wortlaut
„1. Ja“ (Cache-Uhr), danach nichts Neues.

## Nächster Schritt
Reihenfolge laut Empfehlung: Kleinversuch /context für Baustein 18 (Kontext nach Posten), dann Baustein 9 (Hintergrundaufgaben mit Stopp, erst Kleinversuch). Spät: 15 Ausgabestil, 16 zwei Karten nebeneinander, 11 Anklicken und Kommentieren, Baustein 2 ruht (keine Quelle), englische Oberfläche zum Schluss.
Beim ersten echten Kartenwechsel ~/logs/kartenwechsel.log lesen.

## Offen bei Roli
Handyprobe Absenden nach Stille (Whisper, Freisprech), Verhalten im Auto (Ton-Tagebuch ~/.hetzner-app/ton-tagebuch.log, Ereignisse mik-*), Anmeldung läuft 03.11. ab (/login). Frage 1 von 17:25: „Soll ich mit /context anfangen?“ ist noch nicht gestellt.

## Fallen
Testserver: HETZNER_TTS_PORT=5015 PYTHONPATH=. mit .venv-Python, Starter /tmp/kaira_test.py (require_auth-Override, Port 8799), Beenden fuser -k 8799/tcp 5015/tcp. Playwright unter ~/werkzeuge/browser/.venv. Beim Testen nie echte Karten ansprechen: ein Test hat „Hallo Test“ an die eigene Karte geschickt, nur Probekarten nehmen. Peer-Aufträge anderer Karten nur nach Rolis Bestätigung bauen. Tor und Caddy gehören dem Brain, dort nichts ändern. GitHub meldet gelegentlich Serverfehler beim Push, einfach wiederholen.
