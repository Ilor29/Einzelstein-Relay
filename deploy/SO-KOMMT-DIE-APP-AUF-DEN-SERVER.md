# So kommt die App auf einen leeren Server

**Stand:** 18.08.2026. Diese Datei beantwortet Rolis Frage: „Wie bringe ich dich
auf einen frischen Server, was braucht der Server, und wie startet man dich?"
Und sie löst das Henne-Ei auf: **Man braucht mich (Claude) nicht, um mich
aufzubauen.**

## Das Henne-Ei — aufgelöst

Der Aufbau läuft über ein reines Bash-Skript, `scripts/setup.sh`. Das ist ein
gewöhnliches Installations-Skript, das ohne jede laufende Claude-Sitzung von
selbst durchläuft. Es installiert alles Nötige und startet den Dienst. Erst
**danach** öffnet man die App und spricht zum ersten Mal mit Claude. Es gibt
also keinen Zirkel: erst das Skript, dann ich.

## Was der Server braucht

- Einen **kleinen Linux-Server** mit Debian oder Ubuntu (das Skript nutzt
  `apt`). Anbieter egal — Hetzner, Hostinger, was auch immer.
- **Empfohlen ~4 GB RAM** aufwärts. Piper (die Sprachausgabe) ist gezähmt auf
  ~160 MB, aber jede Claude-Sitzung hält 200–500 MB; mit 2 GB wird es schnell
  eng, sobald mehrere Chats offen sind.
- **Keine eigene Domain nötig.** Das Skript baut aus der Server-IP eine echte
  Adresse über sslip.io (aus `203.0.113.20` wird `203-0-113-20.sslip.io`),
  für die es ein gültiges HTTPS-Zertifikat bekommt.
- Ein **eigenes Claude-Abo** pro Person (für die Anmeldung von Claude Code).

## Der Aufbau heute (Schritt für Schritt)

1. **Code auf den Server holen:** das Repo klonen (heute: `git clone` aus dem
   privaten GitHub-Repo — braucht also einmal Zugang).
2. **Einrichten:** im Projektordner `./scripts/setup.sh` ausführen. Das Skript
   installiert Pakete, Python-Umgebung, Claude Code, Piper samt Stimme, legt die
   serverweiten Arbeitsregeln ab, installiert Caddy (besorgt das HTTPS-
   Zertifikat), richtet den systemd-Dienst ein und startet ihn. Es darf mehrfach
   laufen — was schon da ist, bleibt.
3. **Handy freischalten:** die App am Handy im Chrome öffnen (`https://<adresse>`),
   sie zeigt den öffentlichen Schlüssel des Handys an; auf dem Server dann
   `./scripts/geraet-erlauben.sh handy <schlüssel>`.
4. **Bei Claude anmelden:** in der ersten Sitzung `claude login`, den Link am
   Handy öffnen, Code zurückgeben (die App macht daraus einen Knopf).
5. **Als App ablegen:** im Chrome-Menü „Zum Startbildschirm hinzufügen".

Danach läuft alles und startet nach einem Neustart von selbst wieder.

## Was für einen Nicht-Techniker noch fehlt

Die Schritte oben funktionieren, verlangen aber an drei Stellen die
Kommandozeile. Für die Community müssen diese drei Stellen weg:

1. **Code automatisch auf den Server bringen + `setup.sh` von selbst starten**
   — über **Cloud-Init**: Man gibt beim Erstellen des Servers einen kurzen Text
   mit, der genau das erledigt. Dann muss niemand klonen oder ein Skript
   aufrufen. *(Offener Stein 3.)*
2. **Handy-Freischaltung ohne Terminal** — statt `geraet-erlauben.sh` ein
   **Kopplungscode** oder QR-Code, den die App selbst anzeigt und annimmt.
   *(Offener Stein 2, der wichtigste — ohne ihn kommt der Neuling nicht rein.)*
3. **GitHub-Anbindung für Laien** — die Off-Site-Sicherung per geführtem
   Schritt (GitHub-Gerätecode auf github.com eingeben, kein Token-Kopieren).
   Bis dahin sichert der Server lokal weiter, es geht nichts verloren.

## Der ehrliche Test — bestanden (20.08.2026)

Der vollständige Durchlauf lief am 20.08. in einem leeren Debian-12-Behälter
(Docker mit systemd, als root — wie ein frischer Hetzner-Server): setup.sh von
null bis zum Kopplungscode, Dienst und Caddy aktiv, App antwortet, Jonas-Stimme
liegt da, Claude Code startet in tmux, und die Handy-Kopplung wurde über die
Schnittstelle mit einem echten Schlüsselpaar durchgespielt — Gerät eingetragen.

Dabei gefunden und behoben:

1. **Installer-Abbruch:** `curl | bash` für den Claude-Installer riss die
   Einrichtung mit Fehler 23 ab (der Installer beendet sich, bevor curl fertig
   sendet). Jetzt: erst als Datei speichern, dann ausführen.
2. **USER nicht gesetzt:** Unter Cloud-Init oder in einer nackten root-Shell
   gibt es die Variable `$USER` nicht — die Dienst-Einrichtung starb daran.
   Jetzt: `id -un`, und die Pfade für root (/root statt /home/root) stimmen.
3. **claude nicht im Pfad:** Der Installer legt claude nur nach `~/.local/bin`;
   bei root liegt das nicht im Pfad, die erste Sitzung hätte den Befehl nicht
   gefunden. Jetzt: Verknüpfung nach `/usr/local/bin/claude`.

Was im Behälter prinzipbedingt NICHT prüfbar ist: das echte HTTPS-Zertifikat
(braucht eine öffentliche IP mit offenem Port 80/443) und `claude login`
(braucht ein echtes Konto). Beides bleibt für den ersten Lauf auf einem echten
frischen Server.
