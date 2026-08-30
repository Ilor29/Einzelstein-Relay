# CLAUDE.md — Einzelstein-Fernbedienung (Hetzner-App)

Web-App plus FastAPI-Dienst, mit der Roli Claude-Code-Sitzungen vom Handy aus
bedient (tmux auf diesem Server, Vorlesen mit Piper, Diktat). Den ganzen
Aufbau und die Design-Entscheidungen erklärt das **BAUBUCH.md** — erst lesen,
dann bauen. Produktstand und offene Punkte: `~/projekte/Brain/REGISTER.md`.

## Arbeitsregeln

- Bei jeder Änderung, die die App oder die API betrifft: `VERSION` in
  `hetzner_app/server.py` um eins hochzählen — die App lädt sich darüber neu.
- Ausrollen: `sudo systemctl restart hetzner-app.service`, dann
  `curl -s localhost:8787/api/version` prüfen. Die tmux-Sitzungen überleben
  den Neustart.
- Jede abgeschlossene Änderung einzeln committen (deutsche, sprechende
  Nachricht: was und warum) und mit `git push github main` sichern. Die
  Spiegel von Lorenz und Lea ziehen sich den Stand alle 15 Minuten selbst.
- Läuft die App im Browser anders als erwartet: selbst nachsehen, nicht raten
  — Playwright liegt in `~/werkzeuge/browser/.venv`.
- Größere Umbauten hinterher im BAUBUCH.md und im Brain-Register nachtragen.

## Testen ohne Kollateralschaden

- Testserver: `hetzner_app.server` mit ausgehängter Anmeldung auf Port 8799
  starten (`server.app.dependency_overrides[server.require_auth] = lambda: None`),
  mit dem Python aus `.venv`. Beenden mit `fuser -k 8799/tcp` — ein
  `pkill -f` trifft die eigene Befehlszeile.
- In Playwright-Tests die Tour-Schalter vorbelegen
  (`relay_tour_liste_v1` und `relay_tour_sitzung_v1` auf "1"), sonst liegt das
  Tour-Overlay über allen Knöpfen.
- **Niemals `tts` aus einem zweiten Python-Prozess benutzen:** dessen
  Start-Logik räumt Port 5005 ab und schießt damit den Piper des laufenden
  Dienstes ab. In Tests die Stimme nachmachen (siehe Scratchpad-Muster
  `strom_testserver.py` in alten Sitzungen bzw. BAUBUCH, Lektionen).

## Stolperfallen im Code

Die teuer bezahlten Lektionen (Android-Ton nur als mp3-Strom, kein
Lookbehind-Regex wegen Safari, sw.js cached absichtlich nichts, gekürzte
Fußzeile bei der Zustands-Erkennung, Vertrauensfrage statt Escape) stehen
gesammelt im BAUBUCH.md unter „Teuer bezahlte Lektionen".

## Vor einer Weitergabe an Dritte

- `TON_TAGEBUCH_AN` in `web/app.js` auf `false` (Diagnose-Telemetrie).
- Offene 🔴/🟠-Punkte aus dem jüngsten CODE-GUARD-Bericht prüfen.
