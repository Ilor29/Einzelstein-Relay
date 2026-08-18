# CODE//GUARD Prüfbericht Hetzner-App v1.2 — 18.08.2026 — geprüft mit CODE//GUARD v1.2

## Zusammenfassung

Die App ist in ihrem sicherheitskritischen Kern sehr solide gebaut — spürbar
gereift gegenüber den Berichten v1.0/v1.1. Anmeldung, Unterprozesse, Uploads,
Pfad-Absicherung und die Trennung der Nutzer sind sauber gelöst. **Keine
kritischen und keine hohen Befunde.** Der einzige reale Punkt, der einen
Handgriff verdient, ist eine fehlende Content-Security-Policy zusammen mit einem
nicht escapten Anzeigenamen — beides nur als Selbst-Angriff ausnutzbar, weil jede
Instanz genau einem Benutzer gehört. Ein Robustheitsfehler (Piper-Zombie) wurde
im Zuge dieser Prüfung **gefunden und behoben**. Empfehlung: nachbessern bei den
zwei 🟡-Punkten, sonst keine Befunde in den geprüften Bereichen.

## Annahmen

- **Fall C — internes Werkzeug.** Die App wird von Roli und zwei Kollegen (lea,
  lorenz) genutzt, nicht verkauft und nicht öffentlich als Dienst angeboten. Sie
  ist über Caddy unter `<nutzer>.65-21-246-222.sslip.io` erreichbar, aber hinter
  Geräte-Anmeldung geschlossen.
- **Ein Benutzer je Instanz.** Jede Fernbedienung läuft als eigener Linux-Nutzer
  (roli/lea/lorenz) mit eigenem Port und eigenem tmux — die Trennung ist auf
  Betriebssystem-Ebene, nicht in der App. Das ist die stärkste Annahme des
  Sicherheitsmodells und hält.
- Keine Verarbeitung von Kundendaten Dritter; verarbeitet werden die eigenen
  Arbeitssitzungen der drei Nutzer.

## Prüfumfang & Grenzen

**Geprüft (Backend, Python):** `server.py` (vollständig gelesen: Auth, alle
Endpunkte, WebSocket, Uploads, Git-Sicherung, Diktat-Glätten), `tmux.py`
(vollständig), `geraete.py` (vollständig, Anmelde-Kern), `tts.py` (Prozess-Start
und -Ende). Überblick über `speicher.py`, `verbrauch.py`, `melden.py`,
`state.py`, systemd-Units.

**NICHT geprüft in diesem Durchlauf:**
- Das **Frontend** unter `web/` (JavaScript). Damit ist nicht verifiziert, ob
  vom Nutzer stammende Texte (Anzeigename, Ordnernamen) beim Rendern escapt
  werden. Siehe Befund 🟡-1.
- Die **Caddy-Konfiguration** (HTTPS-Erzwingung, HSTS, CSP) — liegt außerhalb
  dieses Repos.
- Interna von `bibliothek.py`, `mitschrift.py`, `verlauf.py`, `geraete`-Skripten.

**Was diese Prüfung nicht leistet:** kein Penetrationstest, keine Laufzeittests,
keine CVE-Datenbankprüfung der eingebundenen Bibliotheken, keine Rechtsberatung.

## Ampel

🔴 Kritisch: 0 | 🟠 Hoch: 0 | 🟡 Mittel: 2 | 🔵 Hinweis: 3 (davon 1 bereits behoben)

## Befunde

### 🟡 MITTEL — Anzeigename wird ungefiltert gespeichert und ausgegeben
- **Fundstelle:** `server.py`, `patch_session` (Zeile 367–369); Modell `Patch.anzeige`
  hat keine Zeichen-Prüfung, nur `.strip()[:60]`. Ausgabe über `/api/sessions`.
- **Problem:** Der Anzeigename einer Sitzung darf beliebige Zeichen enthalten,
  auch `<script>` oder `<img onerror=…>`. Ob daraus ein gespeichertes XSS wird,
  hängt allein davon ab, wie das (hier nicht geprüfte) Frontend den Namen
  einsetzt: `textContent` ist sicher, `innerHTML` nicht. **Schwere nur 🟡**, weil
  eine Instanz genau einem Nutzer gehört — es wäre ein Angriff auf sich selbst,
  kein Weg zu fremden Daten.
- **Fix:** Zweifach absichern. Erstens im Frontend beim Anzeigen `textContent`
  statt `innerHTML` verwenden (kurz prüfen). Zweitens als Gürtel-und-Hosenträger
  eine Content-Security-Policy setzen (siehe 🟡-2). Optional serverseitig `<`
  und `>` aus dem Anzeigenamen entfernen.

### 🟡 MITTEL — Keine Content-Security-Policy
- **Fundstelle:** `server.py`, Middleware `sicherheits_header` (Zeile 38–60) —
  CSP ist bewusst ausgelassen, mit dem Vermerk, sie später in Caddy zu setzen.
- **Problem:** Ohne CSP fehlt die zweite Verteidigungslinie gegen XSS (siehe
  🟡-1). Die Begründung im Code ist nachvollziehbar (eine falsche CSP legt
  Inline-Skripte, WebSocket und Audio-Blobs lahm), aber „später" ist noch nicht
  passiert.
- **Fix:** Nach einem kurzen Browser-Test eine CSP in Caddy setzen, die genau
  das Nötige erlaubt (eigener Ursprung, WebSocket zum eigenen Host, Audio-Blobs).
  Die drei vorhandenen Header (nosniff, Referrer-Policy, X-Frame-Options DENY)
  sind gut, ersetzen die CSP aber nicht.

### 🔵 HINWEIS (BEHOBEN) — Piper-Prozess wurde nicht abgeholt (Zombie)
- **Fundstelle:** `tts.py`, `_starten` (Zeile 409 ff.).
- **Problem:** Der alte Piper-Kindprozess wurde beim Neustart nie mit `wait()`
  abgeholt, weder im toten noch im ungesunden Fall. Er blieb als Zombie liegen —
  eine Leiche je Instanz — und ließ die Fernbedienung mit der Zeit hängen.
- **Status:** Am 18.08.2026 **behoben** (Commit „Piper-Zombie behoben"). Ein
  vorhandener Prozess wird jetzt vor dem Neustart sauber beendet und abgeholt.
  Gegenprobe: Die WebSocket-Anbindung (`server.py`, Zeile 1278–1285) macht es
  bereits vorbildlich (terminate + wait im `finally`) — das war die Vorlage.

### 🔵 HINWEIS — Resize-Nachricht ohne Fehlerfang
- **Fundstelle:** `server.py`, `browser_to_server` (Zeile 1262–1264):
  `_, new_cols, new_rows = text[8:].split(":")` und `int(...)`.
- **Problem:** Eine fehlerhaft formatierte Resize-Nachricht des eigenen Clients
  wirft eine Ausnahme und kappt die Terminal-Verbindung. Kein Sicherheitsproblem
  (nur der eigene, angemeldete Client), aber unnötig zerbrechlich.
- **Fix:** Parsen in `try/except (ValueError)` fassen und eine kaputte
  Resize-Nachricht schlicht ignorieren.

### 🔵 HINWEIS — Offene Zufallsaufgaben unauthentifiziert
- **Fundstelle:** `server.py` `/api/aufgabe`; `geraete.aufgabe_stellen`.
- **Problem:** Der Endpunkt legt bei jedem Aufruf einen Eintrag im Speicher an.
  Das ist durch die 120-Sekunden-Frist und das Aufräumen bei jedem Aufruf
  begrenzt, taugt also höchstens zu einem sehr milden Speicher-Kitzeln.
- **Fix:** Nur bei Bedarf — eine kleine Obergrenze für gleichzeitig offene
  Aufgaben. Aktuell vertretbar.

## Rechtliche Prüfpunkte

*Ersetzt keine Rechtsberatung. Bei Zweifeln Fachanwalt/Datenschutzbeauftragten
hinzuziehen. Rechtsstand der Referenz: 07/2026 (jünger als 12 Monate; keine
🔴/🟠-Rechtsbefunde, daher keine Websuche-Verifikation nötig).*

Als **internes Werkzeug (Fall C)** ist die rechtliche Lage entspannt:

- **Impressum / Datenschutzerklärung nach außen:** derzeit nicht erforderlich, da
  geschlossenes, privates Werkzeug ohne öffentliches Dienstangebot. **Achtung:**
  Sobald die App verkauft oder öffentlich angeboten wird, kippt das — dann greifen
  § 5 DDG (Impressum) und Art. 13 DSGVO (Datenschutzerklärung). Vor einem
  Verkauf neu prüfen.
- **Art. 32 DSGVO (technische Maßnahmen):** vorbildlich für die Größe —
  HTTPS über Caddy, Zugriffskontrolle über Geräteschlüssel, Sicherung über Git,
  Nutzer-Trennung auf Systemebene.
- **EU AI Act:** Die App orchestriert Claude. Für ein internes Werkzeug mit
  offensichtlicher KI-Interaktion minimales Risiko, keine gesonderten
  Transparenzpflichten ersichtlich. 🔵
- **Lizenzen (4.5):** eingebundene Bibliotheken (FastAPI, uvicorn, pydantic,
  cryptography) sind permissiv (MIT/BSD/Apache). `THIRD-PARTY-LICENSES.md` ist
  vorhanden. Für den internen Gebrauch ohnehin unkritisch.

## Was gut ist (nicht anfassen)

- **Anmeldung ohne Passwort** über ECDSA-Schlüsselpaar: geheimer Teil bleibt am
  Handy, Zufallsaufgabe gilt nur einmal und nur 120 Sekunden (kein Wiederholen),
  Unterschrift wird gegen hinterlegte öffentliche Schlüssel geprüft. Geräte lassen
  sich nur von Hand freischalten — keine Selbstregistrierung übers Netz.
- **Sitzungs-Marken** kryptografisch zufällig (256 Bit), serverseitig mit Ablauf
  und Gerätebindung, widerrufbar; Cookie httponly + secure + samesite=strict.
- **WebSocket ist authentifiziert** (häufige Lücke — hier geschlossen) und räumt
  seinen Anbindungs-Prozess beim Trennen sauber ab.
- **Unterprozesse** werden durchweg als Argumentliste gestartet (kein `shell=True`);
  wo doch eine Shell nötig ist (`tmux attach`), sind die Werte mit `shlex.quote`
  gesichert, Zahlen mit `int()`.
- **Uploads** bekommen serverseitig erzeugte Dateinamen (nur die Endung stammt aus
  dem Netz, gegen Positivliste geprüft); die Bild-Auslieferung wehrt `../`-Tricks
  aktiv ab (aufgelöster Pfad muss im erlaubten Ordner liegen).
- **Geheimnisse** liegen in `HETZNER_*`-Variablen aus einer EnvironmentFile außerhalb
  des Repos und werden dem Piper-Kindprozess gezielt vorenthalten.
- **Sicherer Ausgangszustand:** Ohne freigeschaltetes Gerät kommt niemand herein.
- **DoS-Bremsen:** Anfragengröße gedeckelt (35 MB, vor dem Einlesen), Kostenbremse
  auf dem Glätten-Endpunkt (12/Minute).
- **Fehlermeldungen** verraten nach außen keine Serverpfade (Git-Fehler nur ins
  Protokoll).

## Abdeckung

| Abschnitt | Status |
|---|---|
| A1 XSS | geprüft (Backend); Frontend-Rendering offen → 🟡-1 |
| A2 Geheimnisse im Code | geprüft — sauber ausgelagert |
| A3 Externe Ressourcen | n. a. (Backend); Frontend/CDN nicht geprüft |
| A4 Eingabevalidierung | geprüft (Namensmuster, cwd-Grenzen, Dateitypen/-größen) |
| A5 Abhängigkeiten/gefährliche APIs | geprüft — permissiv; kein CVE-Scan (siehe Grenzen) |
| B1–B3 Browser/Offline | n. a. — serverbasiert, kein localStorage-Produkt |
| C1 Injection | geprüft — Listen-Argumente, keine Shell-Verkettung |
| C2 Auth & Sessions | geprüft — stark |
| C3 APIs & Gateways | geprüft — Kostenbremse vorhanden |
| C4 Transport & Server | geprüft — Header gut, CSP offen → 🟡-2 |
| D1 Logik/Zustand | geprüft — Sperren gegen Races vorhanden |
| D2 Fehlerbehandlung | geprüft — 1 Zombie behoben, 1 Resize-Hinweis |
| D3 Kompatibilität | n. a. (Backend) |
| D4 Wartbarkeit | geprüft — Versionsnummer sichtbar, gut kommentiert |
| E1 Halluzinierte APIs | geprüft — keine gefunden |
| E2 Scope-Drift | geprüft — nichts Ungefragtes |
| E3 Platzhalter/Debug-Reste | geprüft — keine Stubs in Sicherheitspfaden |
| E4 Robustheit externer Aufrufe | geprüft — Timeouts vorhanden (Glätten 30 s) |
| E5 Tests | n. a. — keine Testsuite im Prüfumfang |

## Nächste Schritte

1. **🟡 Anzeigenamen absichern:** im Frontend prüfen, dass Namen mit `textContent`
   (nicht `innerHTML`) angezeigt werden.
2. **🟡 CSP in Caddy setzen** nach einem kurzen Browser-Test — schließt die
   zweite Verteidigungslinie gegen XSS.
3. **🔵 Resize-Parsing** in `try/except` fassen.
4. Vor einem etwaigen **Verkauf oder öffentlichen Angebot** die rechtliche Lage
   neu prüfen (dann Impressum + Datenschutzerklärung).

---

*CODE//GUARD markiert Bedenken und Prüfpunkte — er ersetzt keine anwaltliche
Beratung und kein professionelles Penetration-Testing.*
