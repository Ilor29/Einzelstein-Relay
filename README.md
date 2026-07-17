# Hetzner-App

Deine Claude-Code-Sitzungen vom Handy aus — mit der Übersicht, die in der
offiziellen App fehlt: Sitzungen anheften, auf einen Blick sehen, welche
laufen und welche auf dich warten, neue starten, und dir lange Antworten
vorlesen lassen.

Die Sitzungen leben in **tmux auf dem Server**. Deshalb läuft eine Sitzung
weiter, wenn du das Handy weglegst oder die Verbindung abbricht — und deshalb
kannst du morgens am Rechner anfangen und mittags unterwegs genau dort
weitermachen.

## Was drin ist

| Teil | Datei | Wozu |
|---|---|---|
| tmux-Anbindung | `hetzner_app/tmux.py` | Sitzungen anlegen, auflisten, Tasten schicken |
| Anheften & Zustand | `hetzner_app/state.py` | merkt sich Angeheftetes, erkennt läuft/wartet/ruht |
| Vorlesen | `hetzner_app/tts.py` | bereitet Terminaltext fürs Ohr auf, spricht ihn mit Piper |
| Der Dienst | `hetzner_app/server.py` | Schnittstelle und Terminal-Durchreiche |
| Die Oberfläche | `web/` | die PWA fürs Handy |

## Auf dem Hetzner einrichten

Voraussetzung: Eine Domain zeigt auf den Server (ein A-Eintrag genügt), und
Claude Code ist dort schon installiert und angemeldet.

```bash
git clone <dein-repo> ~/Hetzner-App
cd ~/Hetzner-App
./scripts/setup.sh hetzner.deine-domain.de
```

Das Skript legt alles an, besorgt ein HTTPS-Zertifikat, richtet die
Sprachausgabe ein und zeigt dir **einmalig dein Zugangswort** — das notieren.

Danach am Handy im Chrome die Adresse öffnen, anmelden, und im Chrome-Menü
**»Zum Startbildschirm hinzufügen«** wählen. Ab dann hast du ein Icon auf dem
Homescreen und die App startet im Vollbild.

## Zur Sicherheit

Diese App gibt dir eine Shell auf deinem Server. Wer das Zugangswort hat, hat
deinen Server. Deshalb:

- Der Dienst lauscht **nur auf 127.0.0.1**. Nach außen geht ausschließlich
  Caddy, und der spricht nur HTTPS.
- Ohne `HETZNER_APP_TOKEN` **startet der Dienst nicht**. Kein Ausprobieren
  ohne Passwort, auch nicht "nur kurz".
- Das Zugangswort wird zeitkonstant verglichen, damit es sich nicht Zeichen
  für Zeichen erraten lässt.

Wenn du zusätzlich Tailscale oder Wireguard benutzt, binde den Dienst
stattdessen an die VPN-Adresse — dann steht er gar nicht erst im offenen Netz.

## Lokal weiterentwickeln

```bash
python3 -m venv .venv
.venv/bin/pip install fastapi "uvicorn[standard]" websockets
./scripts/install-piper.sh

HETZNER_APP_TOKEN=testwort .venv/bin/python -m hetzner_app.server
# → http://127.0.0.1:8787
```

Kein Bauschritt: Datei ändern, Seite neu laden. Das Anmelde-Plätzchen ist als
`secure` markiert, funktioniert also nur über HTTPS — beim Testen auf
`localhost` macht Chrome eine Ausnahme.

## Immer auf demselben Stand

Das Grundproblem: Du arbeitest am Windows-Rechner, in einer Linux-VM und
unterwegs am Handy — und keiner weiß vom anderen. Die Lösung nutzt aus, dass
mit dieser App **die Arbeit auf dem Server passiert**. Der Hetzner ist damit die
Wahrheit, alle anderen holen sich von dort ab.

Der Anbieter dieser App sieht davon nichts: kein Phone-Home, keine Telemetrie,
kein Lizenzserver. Der Abgleich läuft über dein eigenes GitHub-Konto — die
Sicherung schiebt dorthin, damit sie den Server überlebt.

**Einmalig auf dem Hetzner:**

```bash
./scripts/lager-einrichten.sh Hetzner-App Skillsradar KI-WIKI
sudo cp deploy/auto-sichern.{service,timer} /etc/systemd/system/
sudo systemctl enable --now auto-sichern.timer
```

Ab jetzt sichert der Server alle zehn Minuten von selbst, was Claude Code
geändert hat.

**Einmalig auf dem Windows-Rechner:** `scripts/abgleich-windows.ps1` nach
`D:\Virtual Code\` legen, Server und Benutzer eintragen, und in der
Aufgabenplanung als Aufgabe *„Bei Anmeldung"* eintragen. Danach ist dein
Rechner beim Hochfahren automatisch auf dem Stand von unterwegs.

Das Skript ist absichtlich vorsichtig: Liegen auf dem Rechner ungesicherte
Änderungen, überspringt es das Projekt und sagt es dir, statt deine Arbeit zu
überfahren.

## Was noch fehlt

- **Benachrichtigungen**, wenn Claude fertig ist oder nachfragt. Der Schalter
  ist im Formular schon da, dahinter passiert aber noch nichts.
- **Wischgesten** in der Liste (nach links wischen zum Anheften).
- Die Audio-Antwort kommt als WAV, was auf Mobilfunk unnötig groß ist. Mit
  ffmpeg nach Opus wandeln wäre etwa zehnmal kleiner.
