# CODE//GUARD Referenz: KI-generierter Code („Vibe Coding") (v1.2)

**Stand: 08/2026**

Zusatz-Checkliste für Code, der ganz oder überwiegend von einer KI erzeugt wurde.
Anwenden, wenn der Nutzer das sagt, wenn es aus dem Kontext hervorgeht — oder im
Zweifel immer dann, wenn Herkunft unklar ist (Worst Case: KI-generiert).

Leitgedanke: KI-Code kann **syntaktisch korrekt und semantisch falsch** zugleich
sein. Er halluziniert mit Selbstbewusstsein — erfundene APIs sehen echten täuschend
ähnlich. Deshalb: nichts glauben, alles rückführbar machen (auf Anforderung,
Doku oder Test).

---

## E1. Halluzinierte Abhängigkeiten & APIs

- **Jede importierte Bibliothek existiert wirklich?** Paketname exakt prüfen —
  Tippfehler-Pakete (Typosquatting, z. B. `reqeusts` statt `requests`) sind ein
  aktiver Angriffsvektor: 🔴.
- **Jeder API-Aufruf gegen die offizielle Doku verifiziert?** Methodenname,
  Parameter (Name, Typ, Reihenfolge), Rückgabestruktur, dokumentierte Fehler.
  KI erfindet plausibel klingende Methoden und Parameter: nicht gefundene
  Methode = 🔴, ungeprüfte = 🟠 mit Vermerk.
- **Versionskompatibilität:** Passt das verwendete API-Muster zur tatsächlich
  installierten Version? (KI mischt gern Versionen aus dem Training.)
- **Unnötige Abhängigkeiten:** Jede neue Dependency muss sich rechtfertigen —
  KI zieht gern Bibliotheken für Dinge, die drei Zeilen Standardcode wären.
  Weniger Fremdcode = weniger Angriffsfläche.
- **Wartungszustand:** Verlassene Pakete (Jahre ohne Release) als 🟡 markieren.

## E2. Ungefragte Zusatz-Logik (Scope-Drift)

- **Gibt es Funktionen, die niemand bestellt hat?** KI ergänzt „hilfsbereit"
  Caching, Konfigurationslogik, Hilfsfunktionen, ganze Features. Alles, was
  keiner Anforderung zuzuordnen ist, benennen — es ist ungeprüfte Angriffsfläche
  und künftige Wartungslast.
- **Doppelte Geschäftsregeln:** Dieselbe Logik an zwei Stellen implementiert
  (typisch bei iterativer Generierung) — Änderungen greifen dann nur halb: 🟠.
- **Architektur-Ausbrüche:** Verstößt der generierte Teil gegen die Muster des
  Projekts (z. B. DB-Zugriff aus der Oberfläche, Geschäftslogik im Controller)?

## E3. Platzhalter-, Mock- und Debug-Reste

- **Stubs im Ernstbetrieb:** `return true`-Platzhalter, hartcodierte
  Beispieldaten, Mock-Antworten als Fallback — KI setzt Platzhalter und
  „vergisst" sie. In Sicherheits- oder Bezahlpfaden: 🔴.
- **TODO / FIXME / „implement later"** und auskommentierte Alt-Varianten:
  aufzählen; im Auslieferungscode haben sie nichts verloren.
- **Debug-Hinterlassenschaften:** `console.log`, `print()`, `debugger`,
  Test-Endpunkte, geloggte sensible Daten (Letzteres auch rechtlich relevant
  → recht-check.md).
- **Toter Code:** Funktionen/Klassen ohne einen einzigen Aufrufer.

## E4. Robustheit externer Aufrufe (KI-Klassiker)

- **Timeout an jedem externen Aufruf** (HTTP, DB, Queue) — KI generiert
  standardmäßig ohne: 🟠.
- **Retry nur mit Verstand:** idempotent (keine doppelten Buchungen/Mails),
  begrenzte Versuche mit Backoff, nur bei vorübergehenden Fehlern (nicht bei
  4xx-Antworten).
- **Pagination:** Holt der Code wirklich alle Seiten, oder stillschweigend nur
  die erste? (Sehr häufiger KI-Fehler, fällt erst bei >1 Seite Daten auf.)
- **Async-Fallen:** Fehlende `await`s, vermischte blockierende und
  nicht-blockierende Aufrufe, unbehandelte Promise-Fehler.

## E5. Tests: Zirkelschluss erkennen

- **Bestätigen die Tests die Spezifikation — oder nur den generierten Code?**
  KI-Tests schreiben oft das Ist-Verhalten fest, inklusive der Fehler. Stichprobe:
  Widerspricht ein Testfall der Anforderung, gewinnt die Anforderung.
- **Fehlerpfade getestet?** Nicht nur der Gutfall: ungültige Eingaben, leere
  Antworten, Timeouts, volle Speicher.
- **Scheingenauigkeit:** Viele Tests ≠ gute Tests. Ein Test ohne Assertion oder
  mit gemocktem Kern prüft nichts.

---

**In den Bericht:** Befunde aus E wie gewohnt einordnen (🔴–🔵) und in der
Abdeckungstabelle als E1–E5 führen. Wenn der Abschnitt nicht angewendet wurde
(nachweislich handgeschriebener Code), als „n. a." mit Begründung eintragen.
