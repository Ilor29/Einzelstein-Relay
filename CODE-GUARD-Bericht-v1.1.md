# CODE//GUARD Prüfbericht Hetzner-App / „Einzelstein Relay" v1.1 — 18.07.2026 — geprüft mit CODE//GUARD v1.1

Nachprüfung (Delta-Audit) der Versionen 55–66 seit dem Erstbericht v1.0 vom
16.07.2026 (`CODE-GUARD-Bericht.md`). Geprüft wurde, was sich geändert hat;
die offenen Punkte aus v1.0 sind am Ende mit Status aufgeführt.

> CODE//GUARD markiert Bedenken und Prüfpunkte — er ersetzt keine anwaltliche
> Beratung und kein professionelles Penetration-Testing. Für das Rechtsgerüst
> vor dem Verkauf (Impressum, Widerruf, §§ 327 ff. BGB) gilt weiterhin:
> Fachanwalt.

## Zusammenfassung

Die elf neuen Versionen halten das Niveau von v1.0: kein einziger neuer
kritischer Befund. Der größte Umbau — Piper als getrennter Prozess — ist
sicherheitlich ein **Gewinn** (bewusste 127.0.0.1-Bindung statt Pipers
offenem 0.0.0.0-Standard, Absturz-Erholung, Lizenz-Trennung) und wurde live
verifiziert. Ein 🟠 bleibt: Die Neustart-Logik des Piper-Prozesses behandelt
*jeden* Fehler wie einen Absturz — ein leerer Vorlese-Text (der Endpunkt lässt
ihn durch) würde den warmen Prozess grundlos töten und neu laden. Dazu drei 🟡
aus der Kategorie „Produkt-Feinschliff". **Empfehlung: nachbessern — die Fixes
sind zusammen unter einer Stunde.**

## Annahmen

Wie v1.0 (unverändert): kommerzieller B2C-Verkauf geplant (Worst Case),
Fall A — reiner Software-Verkäufer, jede Instanz läuft auf dem Server des
Käufers, Closed Source. Kein Phone-Home (im Delta erneut bestätigt: der neue
Piper-Prozess spricht nur 127.0.0.1).

## Prüfumfang & Grenzen

- **Delta-Prüfung** der seit 16.07. geänderten Bereiche, vollständig gelesen:
  `hetzner_app/tts.py` (568 Z., komplett umgebaut), `hetzner_app/tmux.py`
  (send_text), `hetzner_app/server.py` (Anhang-Aufräumen Z. 54–140,
  speak/senden-Endpunkte, VERSION), `web/app.js` (Anhang-Chips, eigene
  Befehle, Bibliothek-Suche/Favoriten/zuletzt-benutzt, Zeitstempel,
  sendeInSitzung), `web/index.html` (neue Blätter, Suchfeld, Legende),
  `web/styles.css`, `THIRD-PARTY-LICENSES.md`.
- **Live-Verifikation:** Piper-Portbindung per `ss` geprüft (nur 127.0.0.1),
  Prozess-Neustart-Verhalten per Test-Skript (5 Fälle, bestanden).
- Nicht geprüft: unveränderte Bereiche aus v1.0 (Auth, Geräte, WebSocket,
  Melden) — dort gilt der Erstbericht. Kein Pen-Test, keine CVE-Prüfung der
  Bibliotheken, keine Rechtsberatung.

## Ampel (neue Befunde im Delta)

🔴 Kritisch: 0 | 🟠 Hoch: 1 | 🟡 Mittel: 3 | 🔵 Hinweis: 4

## Befunde

### 🟠 HOCH — Piper-Neustart bei jedem HTTP-Fehler + Leertext ungefiltert
- **Fundstelle:** `hetzner_app/tts.py`, `_sprechen()` (Retry-Schleife) und
  `hetzner_app/server.py`, `speak()` (~Z. 480).
- **Problem:** Die Wiederhol-Logik behandelt jeden `OSError` als toten
  Prozess — aber ein HTTP-Fehler von Piper (`HTTPError`, z. B. 500 bei leerem
  Text) ist ein *lebender* Prozess mit einer Fehlermeldung. Folge: Ein leerer
  Text (der Endpunkt validiert `body.text` nicht; das Frontend schützt nur
  client-seitig) tötet den warmen Piper, lädt das Modell sekundenlang neu,
  scheitert erneut — und der nächste echte Vorlese-Wunsch zahlt den
  Kaltstart. Ein wiederholt leer feuernder Client hielte Piper in einer
  dauernden Neustart-Schleife (Selbst-DoS, authentifiziert).
- **Fix:** Zweiteilig. (1) In `_sprechen` den `urllib.error.HTTPError`
  getrennt fangen und OHNE Neustart als `TTSError` durchreichen; nur bei
  echten Verbindungsfehlern (`URLError`/`ConnectionRefusedError`) neu
  starten. (2) Im `speak`-Endpunkt leeren/nur-Whitespace-Text mit 400
  abweisen, bevor er Piper erreicht.

### 🟡 MITTEL — Fremd-Lizenzliste schon wieder unvollständig (Flask fehlt)
- **Fundstelle:** `THIRD-PARTY-LICENSES.md` (Server-Pakete).
- **Problem:** Mit dem Piper-Umbau wurden Flask samt Unterbau installiert
  (flask, werkzeug, jinja2, markupsafe, itsdangerous, blinker — BSD/MIT,
  inhaltlich unkritisch). Sie fehlen in der Liste; die Datei erweckt den
  Eindruck von Vollständigkeit.
- **Fix:** Die sechs Pakete nachtragen; vor Verkauf ohnehin per
  `pip-licenses` neu erzeugen (steht schon in der Datei).

### 🟡 MITTEL — Parallele Sende-Aufrufe können Text-Stücke verschränken
- **Fundstelle:** `hetzner_app/tmux.py`, `send_text()` (Stück-Schleife).
- **Problem:** Vor dem 128-KB-Fix war ein Senden ein einziger tmux-Aufruf —
  atomar. Jetzt sind es mehrere; treffen zwei Sende-Anfragen gleichzeitig ein
  (Eingabe + Schnellbefehl, zwei Geräte), können sich ihre Stücke im
  Eingabepuffer verzahnen und ein zusammengewürfelter Text landet bei Claude.
  Unwahrscheinlich, aber real.
- **Fix:** Ein `threading.Lock` um die Stück-Schleife in `send_text` — zwei
  Zeilen, stellt die Atomarität wieder her.

### 🟡 MITTEL — Keine Obergrenze für Text an Senden/Vorlesen
- **Fundstelle:** `hetzner_app/server.py`, `Nachricht`/`Speak`-Modelle.
- **Problem:** Seit dem Chunking gibt es praktisch kein Limit mehr: Ein
  (authentifizierter) Client kann 50 MB posten — der JSON-Körper liegt voll
  im RAM (3,7-GB-Maschine!), dann tausende tmux-Aufrufe bzw. minutenlange
  Piper-Synthese. Kein Angriffsvektor von außen, aber eine Robustheitslücke
  gegen Versehen (falsches Einfügen) und gegen ein gestohlenes Gerät.
- **Fix:** Pydantic-Feldgrenzen: Senden z. B. `max_length=2_000_000`
  (2 MB ≈ ein sehr dickes Buch), Vorlesen `max_length=100_000` — mit
  verständlicher Fehlermeldung.

### 🔵 HINWEIS — piper.log wächst unbegrenzt
`_LOG` wird nur angehängt. Beim Prozess-Start stutzen (einmal `"wb"` statt
`"ab"` beim Neustart) oder per logrotate — sonst füllt es über Monate die Platte.

### 🔵 HINWEIS — Der Piper-Port ist lokal ungeschützt
Piper lauscht ohne Anmeldung auf 127.0.0.1:5005 und bietet auch
`POST /download` (lädt Stimmen von Hugging Face in den Stimmen-Ordner). Nur
lokale Prozesse kommen dran — auf dieser Ein-Personen-Maschine fein. Fürs
Kunden-Setup dokumentieren: Auf Mehr-Nutzer-Servern gehört der Port per
Firewall/Namespace abgeschottet.

### 🔵 HINWEIS — Der Piper-Kindprozess erbt die Umgebung
Auch `HETZNER_APP_TOKEN` steht in der Umgebung des Kindes (lesbar nur für
denselben Benutzer — geringes Risiko). Sauberer: dem `Popen` ein bereinigtes
`env` mitgeben.

### 🔵 HINWEIS — Flask-Entwicklungsserver
`piper.http_server` nutzt Flasks eingebauten Server (nicht für „Produktion"
gedacht — hier akzeptabel: localhost, ein Nutzer, eine Anfrage zur Zeit; die
Serialisierung ist beim Vorlesen sogar erwünscht). Nur wissen, nicht ändern.

## Rechtliche Prüfpunkte

> Ersetzt keine Rechtsberatung.

- **✅ Verbesserung — Piper/GPL entschärft (4.5):** Der In-Prozess-Import ist
  ausgebaut; Piper läuft als getrenntes Programm hinter einer Schnittstelle.
  Zusammen mit dem geplanten Einrichtungs-Weg („Kunde installiert Piper
  selbst, wir liefern nichts mit") ist das der anerkannt sauberste Umgang mit
  GPL in einem proprietären Produkt. **Offen bleibt:** finale Bestätigung
  durch IT-Fachanwalt (Prozessgrenzen-Doktrin ist nicht höchstrichterlich
  geklärt) und die Disziplin, Piper nie versehentlich mitzupaketieren.
- **🟡 Lizenzliste unvollständig** — siehe Befund oben (Flask & Co.).
- **Offen aus v1.0 (unverändert, Rechtsstand dort am 16.07.2026 per Websuche
  verifiziert):** 🔴 Rechtsgerüst vor Verkauf (Impressum/DSE/Widerruf,
  § 312j BGB), 🟠 Update-Pflicht §§ 327e/f BGB, 🟠 MLS-Stimmen (CC-BY-Credit
  oder raus; Kerstin-Lizenz pro Modellkarte bestätigen).
- **TDDDG (2):** Die neuen localStorage-Nutzungen (eigene Schnellbefehle,
  Favoriten, zuletzt benutzt) sind rein funktional → einwilligungsfrei, kein
  Banner nötig. Kein Tracking hinzugekommen.

## Was gut ist

- **XSS-Disziplin hält:** Alle neuen UI-Teile (Anhang-Chips, Befehls-Blatt,
  Suchfeld, Favoriten-Stern, Legende) bauen DOM über
  `textContent`/`dataset` — kein einziges `innerHTML` mit Nutzerdaten.
- **Piper-Bindung bewusst gehärtet:** Pipers unsicherer 0.0.0.0-Standard
  wurde explizit auf 127.0.0.1 gezwungen und live per `ss` verifiziert.
- **Absturz-Erholung getestet:** Piper hart getötet → nächster Satz startet
  ihn selbst neu (Testprotokoll, 5 Fälle bestanden).
- **Aufräumen mit Umsicht:** `.gitignore` bleibt stehen, nur Dateien (keine
  Ordner), Fehler halten den Lauf nicht auf, Durchgangs-Ordner beider Quellen.
- **Der 128-KB-500er sauber gelöst** (Stückelung mit Kernel-Grenze im
  Kommentar begründet).
- **localStorage durchweg mit try/catch** (lesen UND schreiben) — kein
  Quota-Absturz möglich.

## Abdeckung

| Abschnitt | Status |
|---|---|
| A1 XSS | geprüft (Delta-UI) |
| A2 Geheimnisse | geprüft (Env-Vererbung → 🔵) |
| A3 Externe Ressourcen | geprüft (keine neuen; Piper lokal) |
| A4 Eingabevalidierung | geprüft (→ 🟠 Leertext, 🟡 Länge) |
| A5 Abhängigkeiten/APIs | geprüft (Flask neu → 🟡 Liste) |
| B1 localStorage | geprüft (neue Schlüssel) |
| B2 Import/Export | n. a. (kein Delta) |
| B3 Lizenzlogik | n. a. (nicht vorhanden) |
| C1 Injection | geprüft (send_text-Stücke, Pfad-Guards unverändert) |
| C2 Auth/Sessions | n. a. (kein Delta; v1.0 gilt) |
| C3 APIs | geprüft (Piper-Port → 🔵) |
| C4 Transport/Server | geprüft (Bindung verifiziert) |
| D1 Logik/Zustand | geprüft (→ 🟡 Verschränkung) |
| D2 Fehlerbehandlung | geprüft (→ 🟠 Neustart-Logik) |
| D3 Kompatibilität | geprüft (Chips/Suche: Standard-APIs) |
| D4 Wartbarkeit | geprüft (Version sichtbar seit V57 ✓) |
| Recht 0 Rolle | Fall A bestätigt |
| Recht 1 DSGVO | n. a. im Delta (kein neuer Datenfluss) |
| Recht 2 TDDDG | geprüft (funktional, frei) |
| Recht 3 Impressum | offen aus v1.0 |
| Recht 4.1–4.4 | offen aus v1.0 (BFSG/CRA/327er) |
| Recht 4.5 Lizenzen | geprüft (GPL-Trennung ✓, Liste 🟡) |

## Nachtrag — Fixes umgesetzt (18.07.2026, Version 67)

Noch am Prüftag behoben und einzeln verifiziert:
- 🟠 **Piper-Neustart:** `HTTPError` wird jetzt ohne Neustart durchgereicht;
  Leertext wird dreifach abgefangen (Endpunkt 400, `synthesize`-Wächter,
  Client). **Nachgewiesen:** Leertext-Ablehnung bei identischer Prozess-Nummer,
  warme Sätze danach 0,6–0,9 s.
- 🟡 **Längengrenzen:** Senden max. 2 Mio. Zeichen (413), Vorlesen max.
  100 000; globaler 35-MiB-Deckel in der Middleware, **live getestet**
  (40-MB-Paket → 413, bevor der Körper gelesen wird).
- 🟡 **Stück-Verzahnung:** `threading.Lock` um die Sende-Schleife —
  Atomarität wiederhergestellt.
- 🟡 **Lizenzliste:** Flask-Familie (6 Pakete, BSD/MIT) nachgetragen.
- 🔵 **piper.log** beginnt je Prozess-Start frisch; 🔵 der Kindprozess erbt
  keine `HETZNER_*`-Geheimnisse mehr.

Offen bleiben nur die 🔵-Doku-Hinweise (Piper-Port auf Mehr-Nutzer-Servern)
und die v1.0-Verkaufspunkte.

## Nächste Schritte

1. 🟠 `_sprechen`: HTTPError ohne Neustart behandeln + Leertext-Abweisung im
   `speak`-Endpunkt (zusammen ~15 Min).
2. 🟡 Sende-/Vorlese-Längengrenzen (Pydantic `max_length`, ~10 Min).
3. 🟡 Lock um `send_text`-Stücke (~5 Min).
4. 🟡 Flask & Co. in `THIRD-PARTY-LICENSES.md` nachtragen (~10 Min).
5. 🔵 piper.log beim Start stutzen; bereinigtes `env` für den Kindprozess.
6. Unverändert offen aus v1.0 (vor Verkauf): Rechtsgerüst, Update-Weg,
   MLS/Kerstin-Stimmen, Anwalts-Bestätigung der GPL-Trennung.
