# CODE//GUARD Referenz: Prüfrunden je Angriffsart und Gegenprüfung (v1.0)

**Stand: 09/2026**

Idee nach dem Cloudflare-Bericht „Build your own vulnerability harness" (blog.cloudflare.com, 2026):
Ein Prüfer, der alles auf einmal sucht, übersieht viel und meldet viel Falsches. Besser findet
eine Runde je Angriffsart, und jeder schwere Fund wird von einem zweiten Prüfer, der die
Begründung des ersten nicht kennt, zu widerlegen versucht. Nur was diese Gegenprüfung übersteht,
kommt als 🔴/🟠 in den Bericht.

---

## 1. Landkarte vor den Runden (immer zuerst)

Bevor eine Runde startet, einmal die Angriffsfläche aufschreiben (kurz, für den Bericht und als
Übergabe an die Runden):

- **Eingänge:** Wo kommen Daten von außen herein? HTTP-Routen, Formulare, Uploads, Webhooks,
  Kommandozeile, Dateien, E-Mails, Antworten fremder Dienste, Antworten von KI-Modellen.
- **Senken:** Wo richten Daten Schaden an? Datenbankabfragen, Shell-Aufrufe, Dateipfade,
  HTML-Ausgabe, Anfragen nach außen, Modell-Prompts mit Werkzeugrechten.
- **Vertrauensgrenzen:** Wer darf was? Anonym, angemeldet, Admin, anderer Mandant.
- **Geheimnisse:** Welche Schlüssel braucht das System, wo liegen sie?

Kleines Projekt (eine Datei, unter ca. 500 Zeilen, kein Server): Landkarte in drei Sätzen reicht.

## 2. Die Runden

Jede Runde sucht **nur ihre Angriffsart**. Runden, die im Projekt keinen Eingang oder keine
Senke haben, werden mit Begründung als „n. a." vermerkt, nicht stillschweigend ausgelassen.

| Runde | Angriffsart | Checklisten-Bezug |
|---|---|---|
| R1 | Injection: SQL, Shell, Pfad, Template, XSS | A1, C1, B2 |
| R2 | Zugriff und Berechtigung: fehlende Anmeldung, fremde Daten per ID (IDOR), Admin-Wege, Sitzungen | C2, B3 |
| R3 | Geheimnisse und Konfiguration: Schlüssel im Code, in Git, in Logs, in Fehlermeldungen, offene Debug-Schalter | A2, C4, E3 |
| R4 | Uploads und Dateien: Dateityp, Größe, Speicherort, Pfad aus Nutzereingabe, Import fremder Dateien | B2, C1 |
| R5 | Anfragen nach außen: SSRF (Server holt beliebige Adresse), Webhook-Signatur, Kostenbremse bei bezahlten Diensten | C3, E4 |
| R6 | KI-Anbindung: Prompt-Injection über Nutzertext, Mails oder Webseiten, Modell mit zu weiten Werkzeugrechten, Modellausgabe ungeprüft in Senke | A1, C1, E4 |
| R7 | Logik und Zustand: Doppelklick, Wettlauf, Zahlen- und Geldfehler, die zu Schaden führen | D1 |

Rechtsprüfung (recht-check.md) und die übrigen Punkte aus ki-code-check.md laufen danach wie
bisher als eigene Durchgänge.

### Wie eine Runde arbeitet

1. Mit der Landkarte und gezielter Suche die Stellen finden, an denen diese Angriffsart
   möglich ist. Suchmuster-Beispiele (je Sprache anpassen):
   - R1: `execute(`, `f"SELECT`, `subprocess`, `shell=True`, `os.system`, `innerHTML`, `|safe`, `open(` mit Variablen
   - R2: Routen-Dekoratoren ohne Anmeldeprüfung, Abfragen per `id` ohne Besitzer-Filter
   - R3: `KEY`, `TOKEN`, `SECRET`, `PASSWORD`, `.env`, `print(`/`log` neben Geheimnissen, `debug=True`
   - R4: `upload`, `multipart`, `save(`, `filename`
   - R5: `requests.get(`, `fetch(`, `urlopen` mit Nutzer-Adresse, Webhook-Routen
   - R6: Prompt-Bau aus fremdem Text, Werkzeuglisten fürs Modell, `eval`/Shell mit Modellausgabe
   - R7: Schreibende Routen ohne Sperre oder Idempotenz, Geldbeträge als Kommazahl
2. Für jeden Verdacht den **Angriffsweg** aufschreiben: Welcher Eingang, welcher Weg durch den
   Code (Datei:Zeile je Station), welche Senke, was der Angreifer am Ende erreicht.
   Ohne vollständigen Weg ist es höchstens 🟡 oder ein Hinweis, kein 🔴/🟠.
3. Prüfen, ob unterwegs schon etwas schützt (Escaping, Parameterbindung, Anmeldeprüfung in einer
   Middleware, Proxy davor). Wenn ja: kein Fund, oder niedrigere Stufe.

### Parallel oder nacheinander

- **Mit Unteragenten (Agent-Werkzeug verfügbar), mittlere und große Projekte:** Jede zutreffende
  Runde als eigener Unteragent, alle gleichzeitig gestartet. Jeder bekommt Landkarte, Dateiliste,
  seine Runde aus dieser Datei und die Anweisung, nur Verdachtsfälle mit Angriffsweg
  zurückzugeben (keinen Bericht). Das Gesamtbild und die Bewertung behält die Hauptprüfung.
- **Ohne Unteragenten oder bei kleinen Projekten:** Runden nacheinander selbst durchgehen, je
  Runde bewusst nur diese eine Angriffsart ansehen.

## 3. Gegenprüfung jedes 🔴/🟠-Verdachts

Jeder Verdacht, der 🔴 oder 🟠 werden soll, geht vor dem Bericht an einen **unabhängigen
Gegenprüfer** (eigener Unteragent je Fund oder je kleiner Gruppe, parallel). Der Gegenprüfer
bekommt nur die **Behauptung** (Angriffsweg mit Fundstellen) und Zugriff auf den Code, nicht die
Begründung oder Einschätzung der Runde. Sein Auftrag ist, den Fund zu **widerlegen**.

Auftrag an den Gegenprüfer (Vorlage):

```
Du prüfst einen gemeldeten Sicherheitsfund gegen. Dein Ziel ist, ihn zu widerlegen.
Projekt: <Pfad>. Behauptung: <Eingang> → <Stationen mit Datei:Zeile> → <Senke> → <Schaden>.
Lies den Code selbst. Prüfe: Ist der Eingang von außen wirklich erreichbar (Route aktiv,
Anmeldung davor, Proxy/Firewall)? Schützt unterwegs etwas (Escaping, Parameterbindung,
Typprüfung, Rechteprüfung)? Stimmen die Zeilen? Ist der Schaden so groß wie behauptet?
Führe nichts aus, was Daten ändert oder Dienste stört; lesen und harmlose Proben an Kopien sind erlaubt.
Antworte mit: Urteil (bestätigt / abgeschwächt auf <Stufe> / widerlegt), Begründung in
zwei bis vier Sätzen, und der Stelle, an der dein Urteil hängt (Datei:Zeile).
```

Auswertung:
- **bestätigt:** Fund bleibt in seiner Stufe.
- **abgeschwächt:** Fund geht mit der neuen Stufe in den Bericht, Begründung des Gegenprüfers kurz dazu.
- **widerlegt:** Fund fällt aus den Befunden und erscheint nur im Block „Verworfene Verdachtsfälle"
  mit einem Satz, warum. So sieht der Leser, dass daran gedacht wurde.
- Widersprechen sich Runde und Gegenprüfer und ist es nicht klar entscheidbar: Fund bleibt,
  mit Vermerk „strittig" und beiden Sichtweisen. Lieber strittig melden als still streichen.

**Ohne Unteragenten:** Gegenprüfung selbst in einem getrennten Durchgang, mit genau den Fragen
aus der Vorlage, und im Bericht vermerken: „Gegenprüfung ohne unabhängigen Prüfer durchgeführt".
