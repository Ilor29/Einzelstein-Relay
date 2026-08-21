# Einzelstein Relay

Dein eigener KI-Arbeitsplatz auf deinem eigenen Server — bedient vom Handy,
per Sprache. Du diktierst, die Antwort wird dir vorgelesen. Die Gespräche
laufen als Claude-Code-Sitzungen in tmux auf deinem Server: Sie arbeiten
weiter, wenn du das Handy weglegst, und du machst am Rechner genau dort
weiter, wo du unterwegs aufgehört hast.

Einzelstein Relay ist ein unabhängiges Projekt von Einzelstein Software. Es
arbeitet mit Claude Code (Anthropic) zusammen, ist aber kein Produkt von
Anthropic; du meldest dich mit deinem eigenen Claude-Konto an.

## Was du bekommst

- **Sitzungs-Übersicht:** alle Gespräche als Karten — anheften, schlafen
  legen, archivieren; auf einen Blick sehen, was läuft und was auf dich wartet.
- **Diktat und Vorlesen:** Mikrofon antippen und sprechen; Antworten liest
  die lokale Stimme „Jonas" (Piper) vor — auf Wunsch stattdessen
  Wolken-Stimmen mit eigenem Schlüssel.
- **Brain:** ein fest eingebauter Überblicks-Chat, der deine Vorhaben kennt
  und den Einstieg erklärt.
- **Geführte Einführung:** eine Tour zeigt Neulingen beim ersten Start, wo
  alles ist.
- **Mitgelieferte Skills** (u. a. CODE//GUARD zur Code- und Rechtsprüfung),
  die sich mit der App aktuell halten.
- **Benachrichtigungen:** die App meldet sich, wenn eine Sitzung fertig ist
  oder eine Rückfrage hat (Web-Push).

## Was du brauchst

- Einen kleinen **Linux-Server** (Debian oder Ubuntu, empfohlen ab 4 GB RAM,
  ~5–10 € im Monat bei Anbietern wie Hetzner oder Hostinger). Keine Domain
  nötig — die Adresse entsteht aus der Server-IP (sslip.io).
- Ein eigenes **Claude-Abo** (Anthropic) für die Anmeldung von Claude Code.
- Ein Handy mit **Chrome** (am besten Android; auf dem iPhone läuft das
  Vorlesen in Chrome, das Diktat ist dort durch Apple-Grenzen eingeschränkt).

## So kommt es auf deinen Server

**Der bequeme Weg (empfohlen):** Beim Anlegen des Servers den Inhalt von
[`deploy/cloud-init.yaml`](deploy/cloud-init.yaml) in das Feld „Cloud config"
einfügen. Der Server richtet sich beim ersten Start selbst ein; danach am
Handy die Server-Adresse öffnen und auf **Diesen Server jetzt verbinden**
tippen — das erste Gerät braucht keinen Code (24 Stunden lang, solange noch
kein Gerät eingetragen ist). Dann im Chrome-Menü **„Zum Startbildschirm
hinzufügen"**.

**Der Hand-Weg:** Repo auf den Server klonen und einrichten:

```bash
git clone <repo-adresse> ~/Hetzner-App
cd ~/Hetzner-App
./scripts/setup.sh
```

Das Skript installiert alles (Pakete, Python-Umgebung, Claude Code, Piper
samt Stimme, Caddy mit HTTPS, den Dienst) und zeigt am Ende Adresse und
einen Kopplungscode. Es darf mehrfach laufen; Bestehendes bleibt. Details:
[`deploy/SO-KOMMT-DIE-APP-AUF-DEN-SERVER.md`](deploy/SO-KOMMT-DIE-APP-AUF-DEN-SERVER.md).

Weitere Geräte kommen per Kopplungscode dazu: ein verbundenes Gerät erzeugt
ihn in den Einstellungen, das neue tippt ihn ein.

## Zur Sicherheit

Diese App gibt Zugriff auf deinen Server — entsprechend ernst nimmt sie die
Tür:

- **Kein Passwort, sondern Geräteschlüssel:** Jedes Handy erzeugt sich ein
  eigenes Schlüsselpaar; der geheime Teil verlässt das Gerät nie. Angemeldet
  wird per Unterschrift, es gibt nichts abzufangen und nichts zu erraten.
- **Nur eingetragene Geräte kommen herein.** Verlorene Geräte sperrst du in
  den Einstellungen aus — sofort, samt laufender Anmeldung.
- Der Dienst lauscht **nur auf 127.0.0.1**; nach außen spricht ausschließlich
  Caddy, und der nur HTTPS.
- Die Erst-Besucher-Kopplung (erstes Gerät ohne Code) ist bewusst doppelt
  begrenzt und vorab geprüft — Abwägung und Restrisiko stehen offen in
  [`CODE-GUARD-Bericht-Erstkopplung.md`](CODE-GUARD-Bericht-Erstkopplung.md).

## Wo deine Daten sind

Dateien, Projekte und Mitschriften liegen auf **deinem** Server; das Vorlesen
mit Piper läuft dort, ohne Wolke. Sobald Claude arbeitet, geht der Inhalt des
Gesprächs an Anthropic (dort läuft das Modell) — genau wie in der offiziellen
Claude-App, über dein eigenes Konto. Optional und nur wenn du es einschaltest:
Browser-Diktat (Google) und Wolken-Stimmen (eigener Schlüssel). Der Anbieter
dieser App sieht nichts davon: kein Phone-Home, keine Telemetrie, kein
Lizenzserver.

## Entwickeln

Kein Bauschritt: Datei ändern, Seite neu laden.

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
./scripts/install-piper.sh
.venv/bin/python -m hetzner_app.server
# → http://127.0.0.1:8787
```

Die Bausteine: `hetzner_app/tmux.py` (Sitzungen), `state.py` (Zustand),
`tts.py` (Vorlesen), `geraete.py` (Geräte und Kopplung), `server.py`
(Schnittstelle), `web/` (die Oberfläche als PWA).

## Lizenzen

Fremde Bausteine und ihre Lizenzen stehen in
[`THIRD-PARTY-LICENSES.md`](THIRD-PARTY-LICENSES.md). Die Sprachausgabe
Piper läuft bewusst als getrennter Prozess.

Dieses Projekt ist öffentlich einsehbar, steht aber noch unter keiner
offenen Lizenz — alle Rechte vorbehalten. Anschauen, ausprobieren und auf
dem eigenen Server betreiben ist ausdrücklich erwünscht; eine offene Lizenz
folgt nach Abstimmung. Verbesserungsvorschläge gern als Issue oder Pull
Request — Änderungen übernimmt ausschließlich der Betreiber, denn dieses
Repo ist die Update-Quelle der laufenden Installationen.
