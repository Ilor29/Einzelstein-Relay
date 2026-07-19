# Der Einrichtungs-Assistent — Plan (Stand 19.07.2026)

Das Herz des Produkts: Ein Käufer ohne Entwickler-Wissen bekommt seinen
eigenen Claude-Code-Server aufs Handy. Dieses Dokument hält fest, was dafür
gebaut werden muss, was schon da ist, und welche Entscheidungen offen sind.

## Geschäftsmodell — festgelegt (Roli, 20.07.2026)

- **Verkauft wird NUR die App**, nicht der Server. Wir hosten/betreiben NICHTS
  für den Kunden — bewusst, für minimales Risiko (keine fremden Daten, keine
  Haftung, keine Infrastruktur-Pflege). Weg A (nackte IP + IP-Zertifikat) ist
  damit gesetzt; eigene Kunden-Domains (Weg B) sind RAUS.
- **Vertrieb über den App Store**, als **native Hülle** um die PWA (Wrapper).
  **Android/Play Store zuerst**, Apple später prüfen. Der Kunde installiert
  also wie jede App — kein Code-Download, kein Kommandozeilen-Kram.
- **Zwei Teile, ein Erlebnis:** Für den Kunden ist es „eine App aus dem Store".
  Technisch gehören zusammen: (1) die **Handy-App** (die Hülle/Fernbedienung
  aus dem Store) und (2) ein **kleines Server-Programm** (der „Motor", der mit
  Claude Code über tmux redet). Die App richtet den Motor beim ersten Start auf
  dem Kunden-Server ein. → Der Motor-Auslieferungsweg ist der eine noch offene
  Entwurf (siehe Frage b unten); die Handy-Hälfte ist über den Store gelöst.
- **Kopplung per QR-Code** (Rolis Wunsch, früher schon angedacht, gut befunden):
  Der Server zeigt einen QR; die App scannt ihn und bekommt in EINEM Schritt
  (a) die Server-Adresse und (b) einen Einmal-Schlüssel zur Freischaltung.
  Kein Abtippen von IP oder Code → laientauglich und risikoärmer als ein
  getippter Kopplungscode. Ersetzt den getippten Code aus dem früheren Plan.

## Das Zielbild (die Reise des Kunden)

1. **Kaufen.** Kunde kauft die Einzelstein Fernbedienung (Digistore24 o. Ä.).
2. **Server anlegen.** Kunde legt bei Hetzner ein Konto an und erzeugt einen
   kleinen Cloud-Server. Dabei fügt er einen von uns gelieferten
   Einrichtungs-Text ein (Hetzner nennt das „Cloud-Init" / user data) — mehr
   Kommandozeile sieht er nie.
3. **Warten.** Der Server richtet sich selbst ein: System, App, HTTPS,
   Sprachausgabe, Claude Code. Dauer: einige Minuten.
4. **Koppeln.** Kunde öffnet die angezeigte Adresse am Handy, gibt einen
   einmaligen Kopplungscode ein — sein Handy ist verbunden.
5. **Claude anmelden.** Die App führt durch die Claude-Anmeldung: Der Server
   zeigt den Anmelde-Link, der Kunde tippt ihn am Handy an, meldet sich bei
   seinem eigenen Anthropic-Konto an. (Das eigene Konto ist Teil des
   Produktversprechens: alles seins, nichts läuft über uns.)
6. **Fertig.** Erste Sitzung startet, Jonas liest vor.

Ausbaustufe später: Schritt 2 ganz vom Handy aus über die Hetzner-API
(„Server vom Handy erzeugen") — erst, wenn die Grundstrecke steht.

## Was schon da ist

- `scripts/setup.sh` — richtet App, Caddy, Piper, Dienst ein. Aber gebaut für
  UNS: setzt Domain, installiertes Claude Code und Shell-Kenntnis voraus.
  Außerdem erzeugt es noch ein „Zugangswort" (HETZNER_APP_TOKEN), das die App
  gar nicht mehr benutzt — die Anmeldung läuft längst über Geräteschlüssel.
- `scripts/geraet-erlauben.sh` — schaltet ein Handy frei, muss aber auf dem
  Server ausgeführt werden. Für Käufer unbrauchbar → braucht den
  Kopplungscode (siehe unten).
- `scripts/install-piper.sh` — holt Piper + Jonas. (Rechtsfrage
  Piper/GPL: Kunde installiert selbst — Skript automatisiert nur; Fachanwalt
  fragt das ohnehin ab, siehe CODE-GUARD-Notizen.)
- `deploy/claude-global.md` — die Server-weiten Claude-Regeln. Das ist
  Schicht 2 der Konfig-Weitergabe (siehe unten).

## Die Domain-Frage — ENTSCHEIDUNGSREIF (Recherche 19.07.2026)

Das Problem: HTTPS braucht klassisch eine Domain. Käufer haben keine.

**Neue Lage:** Let's Encrypt stellt seit **15.01.2026** offiziell
**Zertifikate direkt auf IP-Adressen** aus (Kurzläufer, ~6 Tage, automatische
Erneuerung). Certbot kann das seit März 2026. Caddy selbst noch nicht nativ
(Issue #7399) — Übergangsweg: Certbot besorgt/erneuert das Zertifikat, Caddy
liefert es aus.

Drei Wege, mit Empfehlung:

- **Weg A — IP-Zertifikat (EMPFOHLEN):** Keine Domain nötig, keine Abhängigkeit
  von uns, passt perfekt zum Versprechen „alles auf DEINEM Server". Adresse ist
  dann z. B. `https://65.108.x.y`. Technisch heute machbar (Certbot), Caddy
  zieht später nach.
- **Weg B — Einzelstein-Unterdomains** (`kunde.einzelstein-software.de`):
  schönste Adressen, aber WIR werden Dauer-Abhängigkeit (DNS bei uns,
  Rate-Limits, Pflege) — widerspricht dem Fall-A-Versprechen. Nur als
  Komfort-Option später.
- **Weg C — Wegwerf-Domains (sslip.io):** unzuverlässig — geteiltes
  Wochen-Kontingent, regelmäßig erschöpft. Für ein bezahltes Produkt: nein.

Quellen: letsencrypt.org (GA-Ankündigung 15.01.2026, Rate-Limits),
EFF-Blog 03/2026 (Certbot-IP-Unterstützung), caddyserver GitHub #7399,
sslip.io GitHub #108 (Kontingent erschöpft).

## Der Kopplungscode (ersetzt geraet-erlauben.sh für Käufer)

Heute öffnet die Tür nur, wer auf dem Server ist — richtig so, bleibt für
Profis. Für Käufer zusätzlich: Beim Einrichten erzeugt der Server einen
**einmaligen Kopplungscode** (kurz gültig, z. B. 15 Minuten, wenige Versuche,
danach neu erzeugen über die Server-Konsole). Handy öffnet die Adresse, gibt
den Code ein, Gerät wird eingetragen — derselbe Geräteschlüssel-Weg wie heute,
nur die Freischaltung läuft über den Code statt über die Kommandozeile.
SICHERHEIT: vor dem Bau durch CODE//GUARD prüfen (Brute-Force, Timing,
Wiederverwendung).

## Konfig-Weitergabe in zwei Schichten (sonst steht der Kunde vor blankem Claude)

1. **Vorlagen-Projekt** (gibt es: `vorlage/` mit CLAUDE.md + .gitignore) —
   reist mit jedem neuen Projekt.
2. **Server-Schicht**: `deploy/claude-global.md` → `~/.claude/CLAUDE.md` beim
   Einrichten kopieren, damit jede Sitzung die Arbeitsregeln kennt.

## Claude Code auf den Kunden-Server

Installation über den offiziellen Installer (`claude.ai/install.sh`), NICHT
über npm — erspart Node-Gefrickel. Anmeldung: `claude login` in einer
tmux-Sitzung; die App zeigt den Link, Kunde tippt ihn am Handy an. Kein
API-Schlüssel-Gehampel nötig.

## Reihenfolge der Steine

1. **setup.sh modernisieren** (JETZT machbar): totes Zugangswort raus,
   Claude-Code-Installationsschritt rein, claude-global-Schicht rein,
   Kopplungshinweis statt Token-Kasten. Bleibt zugleich UNSER Werkzeug.
2. **Kopplungscode** in der App (nach CODE//GUARD-Blick).
3. **Cloud-Init-Datei** für Hetzner (setzt 1+2 voraus; braucht Entscheidung,
   WOHER der Kunde den App-Code bekommt — privates Repo geht nicht).
4. **Einrichtungs-Ansicht in der App** (Claude-Login-Führung, Verbindungstest,
   IP-Zertifikat-Status).
5. Später: Server-Erzeugung per Hetzner-API vom Handy; APK-Hülle.

## Offene Entscheidungen für Roli

- ~~Adresse~~ — ENTSCHIEDEN: Weg A, nackte IP. Weg B raus.
- ~~Kopplung~~ — ENTSCHIEDEN: QR-Code statt getipptem Code.
- **(b) Auslieferung des „Motors" auf den Kunden-Server** — WEITER OFFEN, der
  eine Knackpunkt. Das Repo ist privat. Wie landet das Server-Programm auf dem
  Server? (Tarball beim Kauf / eigenes Auslieferungs-Repo mit Kauf-Schlüssel,
  löst zugleich die Update-Pflicht / die App bündelt es und schiebt es rauf.)
  Entscheidung vor dem Cloud-Init-/Setup-Stein nötig.
- **Apple später:** ob eine iOS-Fassung machbar/gewollt ist — erst nach Android.
