# CODE//GUARD Prüfbericht Erst-Besucher-Kopplung (Entwurfsprüfung) v1.0 — 20.08.2026 — geprüft mit CODE//GUARD v1.2

## Zusammenfassung

Geprüft wurde der ENTWURF (vor dem Bau): Solange noch kein Gerät eingetragen
ist, darf sich das erste Handy ohne Kopplungscode selbst eintragen; danach gilt
der normale Code-Weg. Der Ansatz ist als „Vertrauen beim ersten Kontakt"
bekannt und für diesen Zweck (frischer, leerer Server eines Einzelnutzers)
vertretbar — ABER nur mit den unten genannten Auflagen (Zeitfenster, atomare
Vergabe, ehrliche Texte). Ein Restrisiko bleibt und ist dokumentiert.
Empfehlung: bauen mit Auflagen; mittelfristig den sauberen Weg „Kopplungswort
im Cloud-Init-Text" nachrüsten, der das Fenster ganz schließt.

## Annahmen

- Einsatz: Community-Server (je EIN Besitzer), verschenkt, kein Verkauf.
- Server hat eine öffentliche IP; HTTPS über sslip.io-Adresse (Caddy).
- Es gibt noch keine Nutzerdaten auf dem Server, wenn die Tür offen steht
  (Claude-Anmeldung passiert erst NACH der Kopplung).
- Worst Case angenommen: Das Produkt ist öffentlich bekannt und Angreifer
  kennen den Kopplungs-Endpunkt.

## Prüfumfang & Grenzen

- Entwurfsprüfung, kein Code-Audit (der Code entsteht erst nach diesem
  Bericht). Grundlage: `hetzner_app/geraete.py` (407 Zeilen, vollständig),
  Kopplungs-Endpunkte in `server.py`, Koppel-Ansicht in `web/`.
- Kein Penetration-Test, keine Laufzeittests, keine CVE-Prüfung, keine
  Rechtsberatung.

## Ampel

🔴 Kritisch: 0 | 🟠 Hoch: 1 | 🟡 Mittel: 2 | 🔵 Hinweis: 1

## Befunde

### 🟠 HOCH — Wettlauf beim ersten Kontakt: Ein Fremder kann den leeren Server übernehmen

- **Fundstelle:** Entwurf (geplanter Endpunkt `/api/koppeln` ohne Code).
- **Problem:** Zwischen Server-Geburt und erstem Öffnen durch den Besitzer
  kann JEDER, der die Adresse erreicht, das erste Gerät werden. Verschärfer:
  Die sslip.io-Zertifikate landen im öffentlichen
  Certificate-Transparency-Register — frische Instanzen sind dort in nahezu
  Echtzeit auffindbar. Ein Angreifer, der das Produkt kennt, kann gezielt
  unbeanspruchte Server abgrasen.
- **Begrenzung des Schadens (warum kein 🔴):** Der Server ist zu diesem
  Zeitpunkt LEER — keine Daten, keine Claude-Anmeldung. Der Besitzer merkt
  die Übernahme sofort (er kann sich nicht koppeln) und kann den Server neu
  aufsetzen oder per Konsole den Fremden aussperren. Schaden = gekaperte
  Rechenleistung eines leeren Servers, kein Datenabfluss.
- **Fix (Auflagen für den Bau):**
  1. Tür nur, solange NULL Geräte eingetragen sind — jede Eintragung
     (Erstkopplung, Code, `geraet-erlauben.sh`) schließt sie endgültig.
  2. Zusätzlich ZEITFENSTER: nur innerhalb von 24 Stunden nach dem ersten
     Dienststart (per Umgebungsvariable anpassbar). Danach gilt nur noch der
     Code-Weg.
  3. Vergabe ATOMAR unter der bestehenden Schreibsperre: Leerheit erst im
     gesperrten Block prüfen, dann eintragen — zwei gleichzeitige Erste
     dürfen nicht beide gewinnen.
  4. Ehrliche Oberfläche: Der Erst-Besucher sieht klar „Dieser Server ist
     neu und gehört noch niemandem — jetzt verbinden"; die Geräte-Liste in
     den Einstellungen zeigt das eingetragene Gerät (gibt es schon).
  5. Protokoll-Zeile beim Erstkoppeln (Name, Zeitpunkt) ins Dienst-Log.
- **Restrisiko (bewusst getragen):** Im offenen Fenster kann ein schneller
  Fremder den leeren Server übernehmen. Mittelfristige Schließung:
  **Kopplungswort im Cloud-Init-Text** — der Einrichtungs-Text enthält ein
  vom Besitzer gewähltes/erzeugtes Geheimnis, die App fragt es ab. Dann
  gibt es gar kein offenes Fenster mehr. Als Folge-Stein notiert.

### 🟡 MITTEL — Status-Endpunkt verrät „Server noch unbeansprucht"

- **Fundstelle:** Entwurf (geplanter Endpunkt `/api/kopplung/offen`).
- **Problem:** Die App muss wissen, ob sie den Erst-Verbinden-Knopf zeigt —
  der unangemeldete Status-Endpunkt verrät damit auch Angreifern, ob der
  Server noch zu haben ist.
- **Fix:** Hinnehmbar und kaum vermeidbar: Ein Kopplungs-VERSUCH verrät
  dasselbe. Endpunkt liefert nur ein Ja/Nein, keine Fristen, keine Details.

### 🟡 MITTEL — Fenster verpasst = Neuling steht vor verschlossener Tür

- **Fundstelle:** Entwurf (Zusammenspiel Zeitfenster + 15-Minuten-Code).
- **Problem:** Wer den Server abends anlegt und erst nach Ablauf des
  Fensters koppelt, braucht wieder die Kommandozeile (Code aus
  WILLKOMMEN.txt ist längst abgelaufen).
- **Fix:** Fenster großzügig (24 h Standard) + WILLKOMMEN.txt und
  Konsolen-Ausgabe nennen den Notweg (`kopplungscode.sh`) ausdrücklich.
  Ehrlich dokumentieren, nicht verstecken.

### 🔵 HINWEIS — Geburtszeitpunkt sauber verankern

- Das Zeitfenster braucht einen verlässlichen „Geburtsstempel": beim
  Dienststart einmalig geschrieben (Datei), nie überschrieben. Auf
  BESTEHENDEN Installationen (Roli, Lorenz, Lea) entsteht der Stempel erst
  jetzt — unschädlich, weil dort längst Geräte eingetragen sind und die Tür
  damit zu ist.

## Rechtliche Prüfpunkte

Keine neuen Datenarten, keine neue Verarbeitung: gespeichert werden weiterhin
nur Gerätename + öffentlicher Schlüssel auf dem Server des jeweiligen
Besitzers (Fall A aus Sicht des Software-Gebers). Kein 🔴/🟠-Rechtsbefund;
darum keine Websuchen-Pflicht ausgelöst. Dieser Bericht ersetzt keine
Rechtsberatung.

## Was gut ist

- Die bestehende Kopplungs-Basis ist solide: atomares Schreiben mit eigener
  Temp-Datei, Schlüsselprüfung VOR Code-Verbrauch, zeitkonstanter Vergleich,
  Drossel gegen Erraten, einmaliger Code.
- Geräte-Verwaltung mit echtem Widerruf (Aussperren löscht auch die
  Anmelde-Marken) ist vorhanden — die Übernahme-Erkennung fürs Restrisiko
  gibt es also schon.

## Abdeckung

| Abschnitt | Status |
|---|---|
| A1 XSS | n. a. (Entwurf; beim Bau: nur textContent) |
| A2 Geheimnisse | geprüft (keine neuen Geheimnisse) |
| A3 Externe Ressourcen | n. a. (keine neuen) |
| A4 Eingabevalidierung | geprüft (Schlüsselprüfung vorhanden, Name wird gekürzt) |
| A5 Abhängigkeiten | n. a. (keine neuen) |
| B1–B3 Browser/Offline | n. a. (serverseitige Änderung + ein Knopf) |
| C1 Injection | geprüft (kein SQL/Shell im Pfad) |
| C2 Auth & Sessions | geprüft (Kernbefund 🟠 oben) |
| C3 APIs | geprüft (Status-Endpunkt 🟡 oben) |
| C4 Transport | n. a. (unverändert Caddy/HTTPS) |
| D1–D4 Robustheit | geprüft (Atomarität als Auflage 3) |
| Recht 0–4 | geprüft, keine neuen Verarbeitungen |

## Nächste Schritte

1. Bau nach den fünf Auflagen aus dem 🟠-Befund.
2. Texte (WILLKOMMEN.txt, setup.sh-Ausgabe, Koppel-Ansicht) auf den neuen
   Weg anpassen, Notweg nennen.
3. Folge-Stein notieren: Kopplungswort im Cloud-Init-Text (schließt das
   Fenster ganz).
4. Nach dem Bau: Code-Durchsicht dieser Stellen im nächsten Voll-Audit.
