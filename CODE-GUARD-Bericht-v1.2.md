# CODE//GUARD Prüfbericht Hetzner-App / „Einzelstein Relay" v1.2 — 18.08.2026 — geprüft mit CODE//GUARD v1.2

## Zusammenfassung

Der Kern der App ist solide und für viel KI-generierten Code ungewöhnlich
diszipliniert: Die Anmeldung über echte Geräteschlüssel, die strengen
Positivlisten für Namen und Pfade, das atomare Schreiben der Zustandsdateien
und die durchgehende `textContent`-Disziplin in der Oberfläche halten der
Prüfung stand. **Kein kritischer Befund.** Vier Punkte der Stufe Hoch sind
aber real und sollten vor einer breiten Weitergabe geschlossen werden — allen
voran, dass die Aktualisierungs-Dienste für Lorenz und Lea als root ein
Skript ausführen, das ein normaler Benutzer beschreiben kann. Empfehlung:
nachbessern in der unten genannten Reihenfolge, dann ist der Stand für die
Verschenk-Runde tragfähig.

## Annahmen

- **Nutzung heute:** Rolis persönliches Werkzeug, das an eine kleine Community
  (~30–40 Personen) **verschenkt** wird — kein Verkauf (Entscheidung 03.08.).
  Jede Person betreibt später ihren **eigenen** Server mit eigenem Claude-Abo
  und eigenem GitHub.
- **Server heute:** Drei Instanzen auf Rolis Hetzner unter getrennten
  Linux-Konten (roli, lorenz, lea). Roli **hostet damit fremde Daten** (Lorenz'
  und Leas Sitzungen) auf seiner Maschine — informell im Familien-/Freundeskreis.
- **Vertrauensgrenze:** Terminal- und Verlaufsinhalte gelten als **nicht
  vertrauenswürdig**, weil Claude fremde Webinhalte zitiert.
- **Worst-Case-Vorbehalt (Skill-Regel):** Ein späterer Verkauf ist nicht
  ausgeschlossen; verkaufsrelevante Rechtspflichten sind darum weiter als
  Prüfpunkte geführt, aber als „nur bei Verkauf" gekennzeichnet.

## Prüfumfang & Grenzen

- **Vollständig gelesen:** Backend (`server.py`, `geraete.py`, `tmux.py`,
  `state.py`, `speicher.py`, `tts.py`, `verlauf.py`, `mitschrift.py`,
  `bibliothek.py`, `melden.py`, `verbrauch.py`), Oberfläche (`app.js` 4019 Z.,
  `index.html`, `sw.js`, `manifest.webmanifest`), Skripte unter `scripts/` und
  `deploy/`, die Live-`/etc/caddy/Caddyfile` sowie die systemd-Dienste samt
  Datei-Eigentümern auf der Platte.
- **Was diese Prüfung NICHT leistet:** kein Penetration-Test, keine
  Laufzeittests, keine vollständige CVE-Datenbankprüfung eingebundener
  Bibliotheken (xterm.js siehe 🟡), keine Rechtsberatung. **Keine frische
  Websuche zum Rechtsstand**, da es keinen NEUEN 🔴-Rechtsbefund gibt; die
  bestehenden Verkaufs-Rechtspunkte wurden zuletzt am 16.07.2026 per Websuche
  verifiziert (Referenz-Stand 07/2026, unter 12 Monate).

## Ampel
🔴 Kritisch: 0 | 🟠 Hoch: 4 | 🟡 Mittel: 12 | 🔵 Hinweis: 16

---

## Befunde — Stufe Hoch

### 🟠 HOCH — Rechte-Eskalation: root führt beschreibbare Benutzer-Skripte aus
- **Fundstelle:** systemd-Dienste `lorenz-aktualisieren.service` und
  `lea-aktualisieren.service` (laufen als root) → führen
  `deploy/lorenz-aktualisieren.sh` bzw. `lea-aktualisieren.sh` aus; beide
  gehören `roli:roli` und sind für roli beschreibbar.
- **Problem:** Wer das roli-Konto in die Hand bekommt — das realistische
  Szenario ist eine bösartige Anweisung, die sich in eine frei laufende
  Claude-Sitzung schmuggelt —, kann diese Skripte umschreiben und wartet
  höchstens 15 Minuten, bis root sie ausführt. Damit ist die Maschine
  vollständig übernommen. Dieselbe Dienstkette ruft zudem `chown -R` und
  `reset --hard` als root auf.
- **Fix:** Skripte nach `/usr/local/sbin/` verschieben, Eigentümer `root:root`,
  Rechte `755`; die `ExecStart=`-Pfade der beiden Dienste nachziehen. Danach
  kann kein normaler Benutzer mehr am von root ausgeführten Inhalt drehen.

### 🟠 HOCH — Größen-Deckel per „chunked"-Kodierung umgehbar
- **Fundstelle:** `server.py`, `sicherheits_header`, Z. 52–54.
- **Problem:** Der 35-MB-Deckel liest nur die Kopfzeile `Content-Length`. Eine
  Anfrage mit `Transfer-Encoding: chunked` hat keine — sie rutscht durch, und
  der ganze Körper landet im Speicher, bevor die Feld-Limits (2 Mio. Zeichen,
  20/30 MB Upload) greifen. Genau der Speichertod der kleinen Maschine, den der
  Deckel abwehren soll.
- **Fix:** Am robustesten in Caddy `request_body { max_size 35MB }` je
  App-Block — greift auch bei chunked. Zusätzlich in der Middleware POST/PATCH
  ohne `Content-Length` ablehnen (die eigene App schickt immer eine).

### 🟠 HOCH — yt-Auswertung: Schreib-Endpunkte nur mit Pfad-Token, Dateien ohne Anmeldung
- **Fundstelle:** `/etc/caddy/Caddyfile`, Block `yt.203-0-113-20.sslip.io`
  (eigenes Projekt yt-auswertung, aber auf demselben Server).
- **Problem:** `…/senden`, `…/hochladen`, `…/entfernen` sind aus dem offenen
  Internet erreichbar; einzige Hürde ist das Geheim-Token im Pfad. Solche URLs
  landen in Browser-Verläufen, Server-Logs und im Referer. Der Block setzt als
  einziger **keine** Kopfzeilen. `file_server` liefert `/opt/yt-auswertung/web`
  ganz ohne Anmeldung aus.
- **Fix:** Echte Anmeldung (`basic_auth` oder Header-Token statt Pfad-Token),
  Kopfzeilen-Block wie bei den App-Instanzen ergänzen, Token wechseln, prüfen,
  was im ausgelieferten Ordner öffentlich liegt.

### 🟠 HOCH — Kaputt kodierter Link friert die Lese-Ansicht dauerhaft ein
- **Fundstelle:** `app.js`, `linkAnzeige()`, Z. 589.
- **Problem:** Der mailto-Zweig ruft `decodeURIComponent` **vor** dem
  schützenden try/catch. Ein E-Mail-Link mit verrutschter Prozent-Kodierung
  (`mailto:a%zz@x.de` oder ein abgeschnittenes `%2`) wirft einen Fehler, der
  ungefangen die ganze Verlaufs-Darstellung abbricht — ab da bleibt die
  Lese-Ansicht dieser Sitzung leer. Auslösbar durch einen zitierten
  Webinhalt, aber auch ganz harmlos, wenn Claude selbst einen E-Mail-Entwurf
  mit kodiertem Text baut.
- **Fix:** Die Entschlüsselung in try/catch legen (Rückfall „E-Mail öffnen"),
  zusätzlich in `ladeVerlauf` jeden Block einzeln absichern, damit ein
  kaputter Block auf Rohtext zurückfällt statt die Ansicht zu töten.

---

## Befunde — Stufe Mittel

**Backend / Ressourcen**
- 🟡 **`/api/aufgabe` unangemeldet und ungebremst** (`server.py` Z. 167,
  `geraete.py` Z. 157): Jeder anonyme Aufruf legt 120 s einen Eintrag an — im
  Zeitfenster mit Millionen Anfragen flutbar. Fix: harte Obergrenze offener
  Aufgaben + Rate-Limit in Caddy.
- 🟡 **`_aufgaben`-Liste ohne Sperre** (`geraete.py` Z. 161): Zwei gleichzeitige
  Anmeldungen können einen 500er auslösen („dictionary changed size"). Fix:
  Zugriffe unter die vorhandene Sperre legen.
- 🟡 **`git push` ohne Timeout** (`server.py`, `session_sichern`): Hängt GitHub,
  hängt der Thread endlos; einige davon fressen den Threadpool. Fix:
  `timeout=` + saubere Meldung.
- 🟡 **Sitzungserzeugung ohne Obergrenze** (`server.py`, `create_session`
  Z. 288): ~15 Sitzungen von einem Gerät reichen für den dokumentierten
  OOM-Tod. Fix: Deckel (z. B. 8 lebende eigene Sitzungen), darüber 429.
- 🟡 **Fremde Sitzungen werden als „eigene abgestürzte" wiedergeboren**
  (`state.py`, `overview` Z. 433/510): erzeugt beim Wecken unlöschbar wirkende
  Geisterkarten. Fix: `cwd` nur für eigene Sitzungen merken; Wecken von
  Kennungen mit `:` ablehnen.
- 🟡 **WebSocket-Resize ohne Fangnetz / tmux-Aufrufe nach exists-Prüfung**
  (`server.py` Z. 1262 u. a.): kaputte Resize-Nachricht reißt die Verbindung
  ab; stirbt die Sitzung zwischen Prüfung und Zugriff, gibt es einen 500er.
  Fix: Parsen und tmux-Aufrufe in try/except (409/404).

**Oberfläche**
- 🟡 **Keine Content-Security-Policy** (`server.py` Z. 42, bewusst weggelassen;
  auch Caddy): Die `textContent`-Disziplin ist die einzige Verteidigung. Ein
  einziges künftig vergessenes `innerHTML` wäre sofort voller Angriff bis auf
  die Terminal-Verbindung. Fix: CSP in Caddy setzen und mit dem Browser-Prüfer
  real durchtesten (WebSocket, Ton, Service Worker).
- 🟡 **xterm.js von 2023** (`web/vendor/`, ~5.2/5.3, altes unscoped Paket): Das
  Terminal rendert per Definition fremde Steuerzeichen; das Projekt lebt als
  `@xterm/xterm` weiter. Kein bekannter kritischer CVE, **aber keine
  CVE-Prüfung geleistet** (siehe Grenzen). Fix: auf `@xterm/xterm` 5.5+ heben,
  Lizenzdatei nachziehen.

**Deployment / Dienste**
- 🟡 **Off-Site-Sicherung scheitert weiterhin fast stumm**
  (`scripts/auto-sichern.sh` Z. 78): Der GitHub-Fehlschlag meldet sich nur ins
  journald, das niemand liest — genau die Lücke hinter dem Wochen-Stau. Fix:
  ab 3 Fehlschlägen in Folge eine Push-Nachricht oder einen Warnzustand für
  die App-Ampel; Divergenz getrennt von „kein Netz" melden.
- 🟡 **Push-Versand ohne Timeout** (`melden.py`, `schicken`): Ein hängender
  Push-Dienst blockiert den Wächter — alle weiteren Meldungen bleiben stumm
  aus. Fix: `webpush(…, timeout=10)`.
- 🟡 **Zip-Bombe beim Skill-Upload** (`bibliothek.py`, `neu_aus_datei` Z. 238):
  `extractall` prüft die entpackte Größe nicht; 5 MB komprimierte Nullen werden
  zu Gigabytes. Fix: Summe der `file_size` und Anzahl der Einträge vor dem
  Entpacken deckeln.
- 🟡 **Piper-Ports offen zwischen den Konten** (`tts.py`, Ports 5005–5007):
  127.0.0.1 schützt vor dem Internet, nicht vor lorenz/lea untereinander — sie
  können sich gegenseitig CPU-Last erzeugen. Fix: per nftables auf den
  jeweiligen Konto-Besitzer beschränken oder das Restrisiko bewusst festhalten.

---

## Befunde — Hinweise (Auswahl, vollständig im Anhang der Prüfnotizen)

- 🔵 Markdown-Links erlauben Text-Spoofing (Anzeigetext lügt über das Ziel) —
  Phishing-Fläche bei zitiertem Webinhalt; Anzeigetext, der wie eine URL
  aussieht, gegen den echten Host abgleichen.
- 🔵 401 mitten in der Sitzung: App bietet keine stille Neuanmeldung, Takte
  pollen weiter gegen 401.
- 🔵 `block.zeilen` als einzige Datenstelle in einer innerHTML-Vorlage
  (`app.js` Z. 787) — heute Zahl, aber Musterbruch; auf `textContent` umstellen.
- 🔵 Strg+V lädt Bilder sofort hoch; „Anhang wegnehmen" löscht die Server-Datei
  nicht (räumt sich nach 3 Tagen selbst).
- 🔵 `window.open(bild.src)` ohne `noopener`; WebSocket ohne Origin-Prüfung
  (durch SameSite=strict abgefedert); toter `ws:`-Fallback.
- 🔵 **Ton-Tagebuch** (`app.js`/`server.py`): Debug-Telemetrie im
  Produktionscode — vor Weitergabe ausbauen oder in die Datenschutzerklärung
  (auch rechtlich relevant).
- 🔵 Bild-Upload prüft nur den gemeldeten Typ, nicht den Inhalt
  (`nosniff` fängt es ab); tmux-`-t` macht Präfix-Matching → exaktes `=`-Matching
  nutzen; toter Parameter `first_prompt` in `tmux.create`; tmux-stderr geht 1:1
  an den Client.
- 🔵 `melden.py`: Notnagel-Kontakt `example.com`, wenn Kontakt nicht gesetzt;
  fängt nur `WebPushException`. Google-Schlüssel im URL-Query statt Header;
  Piper-Kind erbt die Wolken-Schlüssel unnötig; piper.log ungedeckelt.
- 🔵 `mitschrift.py`: Ordnernamen-Kollision („KI WIKI"/„KI-WIKI"); Cache
  `_gemerkt` wächst unbegrenzt.
- 🔵 `bibliothek.py`: Zeilenumbruch in der Skill-Beschreibung zerreißt den
  Frontmatter.
- 🔵 `setup.sh`: `curl | bash` (bewusster Vertrauensvorschuss, dokumentieren);
  `$DOMAIN` ungeprüft in `sed`.
- 🔵 Caddy: Repo-Vorlage und Live-Konfiguration auseinandergelaufen (Käufer
  bekämen die schwächere); Nebenblöcke (`alfred.`, `n8n.`, `jourfix.`) ohne
  `X-Frame-Options`.

---

## Rechtliche Prüfpunkte

> Ersetzt keine Rechtsberatung. Bei Verkauf mit Abmahn-/Bußgeldrisiko
> Fachanwalt bzw. Datenschutzbeauftragten hinzuziehen.

- **Rolle:** Solange verschenkt und jede Person ihren eigenen Server betreibt,
  ist jeder Empfänger **eigener Verantwortlicher** — Roli verarbeitet keine
  fremden Daten zentral (Fall A). **Neu und relevant:** Auf dem gemeinsamen
  Server hostet Roli aktuell Lorenz' und Leas Sitzungsdaten (Fall B/C-Nuance).
  Im Familien-/Freundeskreis informell vertretbar; wächst der Kreis oder wird
  Geld genommen, gehört das klar geregelt.
- **Nur bei Verkauf (unverändert aus v1.0, Rechtsstand 16.07.2026 verifiziert,
  < 12 Monate):** 🔴 Rechtsgerüst (Impressum, Datenschutzerklärung, Widerruf,
  § 312j BGB), 🟠 Update-Pflicht §§ 327e/f BGB, 🟠 Stimmen-Lizenz. Diese Punkte
  sind **derzeit nicht scharf**, weil nicht verkauft wird.
- **TDDDG:** Der localStorage der App ist reiner Funktionsspeicher
  (Schnellbefehle, Favoriten, Anmeldeschlüssel) → einwilligungsfrei, **kein
  Cookie-Banner** nötig. Kein Tracking hinzugekommen.
- **Neu:** Das **Ton-Tagebuch** wäre in einer weitergegebenen Fassung
  ungefragte Nutzungs-Telemetrie — vor breiter Weitergabe ausbauen oder
  deklarieren.

## Was gut ist (geprüft und für solide befunden)

- **Anmeldung & Krypto:** ECDSA P-256 über die `cryptography`-Bibliothek,
  Einmal-Aufgabe mit 120-s-Frist (kein Replay), privater Schlüssel im Browser
  nicht exportierbar, Cookie httpOnly/Secure/SameSite=strict mit
  serverseitig gültiger, widerrufbarer Marke.
- **Injection/Pfade:** subprocess durchweg als Argumentliste ohne Shell,
  `shlex.quote` an der tmux-Anbindung, Sitzungsnamen streng auf Positivliste,
  Pfad-Traversal beim Bild-Ausliefern durch `resolve()`+Eltern-Vergleich
  geschlossen, Upload-Namen komplett vom Server vergeben.
- **XSS-Disziplin:** Alle 15 innerHTML-Stellen einzeln geprüft — konstante
  Vorlagen; die neue Link-Erkennung riegelt `javascript:`/`data:` schon im
  Muster ab, Anker mit `noopener`.
- **Zustandsdateien:** alle Lese-ändern-Schreib-Zyklen gesperrt und atomar
  (`mkstemp`+`os.replace`); Geheimnisdateien 600, Heimatverzeichnisse 750;
  in keinem der 18 Projekt-Repos ist ein Anhang/Bild getrackt.
- **SSRF:** Push-Endpunkte gegen eine Host-Positivliste mit https-Zwang
  geprüft; `verbrauch.py` spricht nur die fest verdrahtete Anthropic-Adresse
  an, mit Timeout und sauberem Rückfall.
- **speicher.py & die meisten externen Aufrufe:** Timeouts vorhanden,
  defensiv, Fehler brechen die Messung nicht ab.

## Abdeckung

| Abschnitt | Status |
|---|---|
| A1 XSS | geprüft (→ 🟠 decodeURIComponent, 🔵 Musterbruch/Spoofing) |
| A2 Geheimnisse | geprüft (Git-Leaks ausgeschlossen; 🔵 Schlüssel im Query/Env) |
| A3 Externe Ressourcen | geprüft (kein CDN, alles selbst gehostet) |
| A4 Eingabevalidierung | geprüft (Namen/Pfade solide; 🟡 Größen-Deckel umgehbar) |
| A5 Abhängigkeiten/APIs | geprüft (🟡 xterm veraltet; CVE-DB nicht geprüft) |
| B1 localStorage | geprüft (alle Zugriffe in try/catch, nur Funktionsdaten) |
| B2 File-Import/Export | geprüft (🟡 Zip-Bombe; Uploads sonst sauber) |
| B3 Lizenzlogik | n. a. (keine im Produkt) |
| C1 Injection | geprüft — keine |
| C2 Auth/Sessions | geprüft (solide; 🟡 kein Rate-Limit, 🟡 Aufgaben-Sperre) |
| C3 APIs/Gateways | geprüft (🟠 yt-Block; 🟡 Push-Timeout) |
| C4 Transport/Server | geprüft (🟠 Rechte-Eskalation, 🟡 CSP, 🟡 Sicherungs-Meldung) |
| D1 Logik/Zustand | geprüft (🟡 Geisterkarten, 🟡 Sitzungsdeckel) |
| D2 Fehlerbehandlung | geprüft (🟡 WebSocket/tmux-500er) |
| D3 Kompatibilität | geprüft (Fallbacks vorhanden) |
| D4 Wartbarkeit | geprüft (🔵 toter Code, Musterbrüche) |
| E1 Halluzinierte APIs | geprüft — keine, Web-APIs echt benutzt |
| E2 Scope-Drift | geprüft (🔵 Ton-Tagebuch als Zusatz-Telemetrie) |
| E3 Platzhalter/Debug | geprüft (🔵 toter Parameter, ws:-Fallback) |
| E4 Externe Aufrufe | geprüft (🟡 zwei fehlende Timeouts: push, git push) |
| E5 Tests | n. a. (keine automatischen Tests — offener Punkt im Fahrplan) |
| Recht 0–4.5 | geprüft (Rolle geklärt; Verkaufspunkte geparkt) |

## Nachtrag — Fixes umgesetzt (18.08.2026)

- ✅ **🟠 Rechte-Eskalation geschlossen:** Beide Aktualisierungs-Skripte liegen
  jetzt als `root:root` (755) unter `/usr/local/sbin/hz-*-aktualisieren.sh`, die
  Dienste zeigen dorthin. Das roli-Konto kann den von root ausgeführten Inhalt
  nicht mehr verändern. Testläufe beider Dienste erfolgreich, beide Instanzen
  erreichbar. Repo-Vorlagen mit Installationshinweis versehen.
- ✅ **🟠 Einfrierender Link behoben (Version 109):** `decodeURIComponent` in
  `linkAnzeige()` im Fangnetz (Rückfall „E-Mail öffnen", mit kaputtem Link
  getestet), und der Verlauf rendert jeden Block einzeln in try/catch — ein
  kaputter Block wird zur schlichten Text-Blase statt zum toten Bildschirm.
  Auf allen drei Instanzen ausgerollt.
- ✅ **🟠 Chunked-Bypass geschlossen:** In Caddy je App-Block
  `request_body { max_size 35MB }` — greift auch ohne Content-Length. Live
  getestet: 40-MB-Chunked-Anfrage → 413, kleine Anfrage kommt normal durch.
  Repo-Vorlage `deploy/Caddyfile` nachgezogen; Sicherung der alten
  Live-Konfiguration unter `/etc/caddy/Caddyfile.bak-vor-maxsize-20260818`.
- ✅ **🟡 CSP eingeführt (19.08., V117):** Content-Security-Policy im
  Server-Header, streng (`default-src 'self'`), der Hash des einen
  Inline-Skripts wird beim Start aus der Datei berechnet (veraltet nie);
  zwei Inline-Stile in Klassen umgezogen. Live im Browser-Prüfer: Seite
  rendert, 0 CSP-Verletzungen; xterm ohne eval/Worker. Offen bleibt nur
  xterm.js-Version heben.
- ✅ **🟡 Fünf Mittel-Punkte abgehärtet (19.08.):** Sitzungs-Obergrenze
  (`MAX_SITZUNGEN`=10, gegen OOM), Anmelde-Aufgaben unter eigener Sperre +
  Obergrenze (gegen 500er-Race und Flutung), Zip-Bomben-Schutz beim
  Skill-Upload (entpackte Größe/Anzahl vor `extractall`), Timeouts für
  `webpush` (10 s) und den git-Push in der Sicherung (120 s). Getestet.

## Nächste Schritte (priorisiert)

1. ✅ ~~🟠 Aktualisierungs-Skripte nach root-Eigentum verschieben~~ **erledigt
   18.08.** (siehe Nachtrag).
2. ✅ ~~🟠 `request_body max_size` in Caddy je App-Block~~ **erledigt 18.08.**
   (live per 413-Test bestätigt).
3. 🟠 **yt-Block absichern** (echte Anmeldung, Kopfzeilen, Token wechseln).
4. ✅ ~~🟠 `decodeURIComponent` absichern + Block-weises Fangnetz im Verlauf~~
   **erledigt 18.08., Version 109** (siehe Nachtrag).
5. ✅ ~~🟡 Schnelle Wins: Push-Timeout, Aufgaben-Sperre, Sitzungsdeckel,
   Zip-Größenprüfung~~ **erledigt 19.08.** (siehe Nachtrag). Offen davon nur
   noch die GitHub-Fehlschlag-Warnung fürs Handy.
6. ✅ ~~🟡 CSP setzen und mit dem Browser-Prüfer testen~~ **erledigt 19.08.,
   Version 117.** Offen davon nur noch: xterm.js auf `@xterm/xterm` heben.
7. 🔵 Vor breiter Weitergabe: Ton-Tagebuch ausbauen oder deklarieren;
   Caddy-Vorlage im Repo nachziehen.
