# Übergabe Hetzner-App (Relay), 03.11.2026 23:00 (Karte Hetzner-App 12)

## Stand
Relay V218 läuft und ist gesichert (GitHub). Seit der letzten Übergabe gebaut:
V217 Baustein 9: Block „Laufende Befehle“ in der rechten Spalte mit Laufzeit und Stopp (hetzner_app/hintergrund.py, nur direkte Befehle des claude-Prozesses der Karte, fremde Prozesse abgelehnt).
V218 Baustein 15: Schalter „Verlauf“ in den Einstellungen, „Mit Arbeitsschritten“ zeigt Werkzeugzeilen grau (Standard aus, je Gerät in localStorage verlauf_arbeit).
Nicht gebaut, bewusst: Baustein 18 (Kontext nach Posten, /context stört den Schirm der Karte), Stil-Anzeige (Klarschrift ist per Plugin force-for-plugin erzwungen, /output-style meldet trotzdem „default“, Anzeige wäre falsch).
Baubuch und Register sind aktuell. Nichts Ungesichertes im Arbeitsordner.

## Beschlüsse (mit Auslöser)
02.11. 20:14 „1. Nein“ Baustein 18 nicht mit Abfrage an ruhenden Karten, „2. Ja“ Baustein 9.
03.11. 22:27 „1. Ja, läuft alles“ Handyprobe Absenden nach Stille bestanden, Baustein 15 angehen.
03.11. 22:29 „1. Ja“ nur Stil-Anzeige, „2. Ja“ danach Transkript-Ansicht; 22:32 „1. Ja“ Stil-Anzeige streichen, Transkript-Ansicht bauen.
03.11. 22:48 „1. Ja“ Baustein 11 angehen (meine Empfehlung war Nein, er wollte es trotzdem).

## Rolis letzter Wortlaut
„[03.11. 22:48] 1. Ja“ (Baustein 11 angehen). Danach kam von mir die Rückfrage zu Weg A, noch nicht beantwortet.

## Offen bei Roli
1. Frage zu Baustein 11 ist offen: Soll ich den Auslieferer für den Webspace (Dienst seiten-roli, heute python http.server auf 8803) umbauen, der im Kommentiermodus (?kommentieren=1) ein Hilfsskript anhängt, das per postMessage meldet, was angetippt wurde? Empfehlung: Ja, zuerst nur für Rolis Webspace. Weg B (Relay liefert Seiten selbst aus) ist abgelehnt (Sicherheit). Plan und Begründung stehen im Baubuch unter „Baustein 11“.
Außerdem: Verhalten im Auto (Ton-Tagebuch ~/.hetzner-app/ton-tagebuch.log, Ereignisse mik-*). Die Anmeldung lief am 03.11. ab, falls /login nötig war, ist das erledigt oder steht noch aus.

## Nächster Schritt
Antwort auf die Baustein-11-Frage abwarten. Bei Ja: Teil 1 Auslieferer mit Hilfsskript und Versuch an einer Probeseite (Caddy und Tor nie anfassen), Teil 2 Sammelliste und Senden in der App, Teil 3 Feinheiten. Danach spät: 16 zwei Karten nebeneinander, Englisch zum Schluss. Baustein 2 ruht (keine Quelle).

## Fallen
Testserver: HETZNER_TTS_PORT=5015 PYTHONPATH=. mit .venv-Python, Starter /tmp/kaira_test.py (require_auth-Override, Port 8799; falls weg, neu schreiben), Beenden fuser -k 8799/tcp 5015/tcp. Playwright unter ~/werkzeuge/browser/.venv; am Handy-Format liegt der Einstellungen-Knopf nur in der Liste, Tests am breiten Format (1500x900). Probekarten nur auf eigenem tmux-Socket oder mit Namen „Probe-…“, danach auch den Eintrag in ~/.hetzner-app/sitzungen.json entfernen (Sicherung vorher). Echte Karten nie ansprechen. Tor und Caddy gehören dem Brain. GitHub meldet gelegentlich Serverfehler beim Push, wiederholen.
