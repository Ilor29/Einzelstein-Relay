# CODE//GUARD Referenz: Code-Sicherheit & Programmierfehler (v1.1)

**Stand: 07/2026**

Checklisten für die technische Prüfung. Kontextabhängig anwenden: Abschnitt A gilt immer, B für Browser-/Offline-Tools, C für serverbasierte Systeme, D für Qualität/Robustheit generell.

---

## A. Universelle Sicherheitschecks (immer prüfen)

### A1. XSS (Cross-Site-Scripting) — häufigster Fund bei HTML-Tools
- Jede Stelle suchen, wo Nutzereingaben oder importierte Daten (CSV!) in den DOM gelangen: `innerHTML`, `outerHTML`, `document.write`, `insertAdjacentHTML`, Template-Strings die HTML bauen.
- **Fix-Muster:** `textContent` statt `innerHTML`; wenn HTML nötig, Eingaben escapen:
  ```js
  const esc = s => String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  ```
- Besonders prüfen: CSV-Import (Formeln/HTML in Zellen), Namensfelder, Notizfelder, alles was später in Listen/Karten gerendert wird.

### A2. Geheimnisse im Code
- API-Keys, Tokens, Passwörter, Gateway-Zugangsdaten (SMS-Gateways!), Webhook-URLs mit Secrets — dürfen NIE im Frontend-Code oder in ausgeliefertem HTML stehen.
- Auch prüfen: auskommentierte Credentials, Test-Zugänge, Basic-Auth in URLs.
- **Fix:** Secrets nur serverseitig; Frontend spricht mit eigenem Backend-Endpoint.

### A3. Externe Ressourcen
- CDN-Einbindungen: Bei offline-first-Produkten ein Widerspruch zur Produktphilosophie UND ein Risiko (CDN-Ausfall, Supply-Chain, DSGVO-Thema → siehe recht-check.md US-Dienste).
- Wenn CDN unvermeidbar: Subresource Integrity (`integrity="sha384-..."` + `crossorigin`).
- `target="_blank"`-Links ohne `rel="noopener"` (Reverse Tabnabbing).

### A4. Eingabevalidierung
- Alle Eingaben validieren: Typ, Länge, Format, Wertebereich — vor Verarbeitung UND vor Speicherung.
- Zahlenfelder: `parseFloat`/`parseInt` ohne `isNaN`-Check → `NaN` wandert in Berechnungen (klassiker bei Kalkulations-/KPI-Tools).
- Datumseingaben: ungültige Daten, Zeitzonenfallen (`new Date('2026-01-01')` = UTC-Mitternacht).

### A5. Abhängigkeiten & gefährliche APIs
- **Eingebundene Bibliotheken:** Name + Version notieren. Veraltete Versionen mit bekannten Lücken sind ein 🟠-Kandidat — bei Verdacht aktuelle Sicherheitslage per Websuche prüfen (eine vollständige CVE-Datenbankprüfung leistet CODE//GUARD nicht → in „Prüfumfang & Grenzen" vermerken). Bei Node-Projekten: `npm audit` als Fix empfehlen.
- **`eval()` / `new Function()` / String-Argumente in `setTimeout`/`setInterval`:** grundsätzlich 🟠, mit Nutzereingaben 🔴. Fast immer durch sichere Alternativen ersetzbar.
- **`postMessage`:** Empfängerseitig immer `event.origin` prüfen; senderseitig nie `'*'` als Target-Origin bei sensiblen Daten.
- **Prototype Pollution:** Bei rekursivem Merge von geparstem JSON in Objekte (`__proto__`, `constructor`) — relevant bei Save-File-Import (siehe B2).

---

## B. Browser-/Offline-Tools (Single-File-HTML, localStorage)

### B1. localStorage
- **Quota:** ~5 MB je Origin. Jeden `setItem`-Aufruf auf try/catch prüfen — QuotaExceededError crasht sonst das Tool und Nutzer verlieren Eingaben.
- **Verfügbarkeit:** Privater Modus (v. a. ältere Safari) kann localStorage blockieren → Feature-Detection mit Fallback, nicht nur `if (localStorage)`.
- **Korrupte Daten:** `JSON.parse(localStorage.getItem(...))` immer in try/catch; bei Fehler definierter Fallback statt weißer Seite.
- **Schema-Migration:** Wenn das Tool Updates bekommt (1-Jahres-Update-Modell!): Versionsfeld im gespeicherten Objekt + Migrationslogik, sonst zerschießt v2 die Daten von v1-Kunden.
- **Sensible Daten:** localStorage ist unverschlüsselt und für jedes Script auf der Origin lesbar. Bei sensiblen Kundendaten mindestens darauf hinweisen (→ auch rechtlich relevant, siehe recht-check.md).
- **Doppelter Boden für Nutzerdaten (🟡):** localStorage kann jederzeit verschwinden (Browser-Datenlöschung, „Website-Daten löschen", Gerätewechsel, Origin-Wechsel beim Verschieben der HTML-Datei). Tools, in denen Nutzer über Wochen Daten aufbauen, brauchen eine **Export-/Backup-Funktion** plus eine **aktive Backup-Erinnerung** (z. B. Hinweis nach N Änderungen oder T Tagen ohne Export). Fehlt beides = 🟡; bei geschäftskritischen Daten (Kundenlisten, Umsätze) 🟠.

### B2. File-Import/Export
- CSV-Import: Injection über Zellinhalte (siehe A1), kaputte Encodings (Umlaute! UTF-8 vs. Windows-1252), Trennzeichen-Chaos (deutsches Excel nutzt Semikolon), BOM-Handling.
- CSV-Export: Formeln-Injection absichern — Zellen, die mit `=`, `+`, `-`, `@` beginnen, mit `'` prefixen, wenn die Datei in Excel geöffnet wird.
- JSON-Import (Save-Files): Struktur validieren, nicht blind `Object.assign` in den App-State.

### B3. Aktivierungs-/Lizenzlogik
- Partner-Code-/Freischaltsysteme im Frontend sind per Definition umgehbar (Code ist einsehbar). Bewerten: Ist das akzeptiertes Geschäftsrisiko (bei One-Time-Payment meist ja) oder Problem? Nie als "sicher" verkaufen.
- Codes nicht im Klartext als Liste im Quelltext — mindestens Hash-Vergleich.

---

## C. Serverbasierte Systeme (Multi-User, APIs, Gateways)

### C1. Injection
- SQL: ausschließlich Prepared Statements / Parameter-Binding. Jede String-Konkatenation in Queries = 🔴.
- Command Injection: Nutzereingaben nie in Shell-Befehle.
- Pfad-Traversal: Dateinamen aus Nutzereingaben normalisieren und gegen Whitelist prüfen (`../../etc/passwd`).

### C2. Authentifizierung & Sessions
- Passwörter: nur bcrypt/argon2, nie MD5/SHA1/Klartext.
- Session-Tokens: httpOnly, Secure, SameSite; Ablaufzeit; Invalidierung bei Logout.
- Brute-Force: Rate-Limiting auf Login-Endpoints.
- Autorisierung ≠ Authentifizierung: Prüfen, ob User A die Daten von User B abrufen kann, indem er IDs in Requests ändert (IDOR — bei ADM-Systemen mit Kundenzuordnung besonders relevant).

### C3. APIs & Gateways
- SMS-/WhatsApp-Gateway-Credentials: nur serverseitig, Rotation möglich?
- Rate-Limiting & Kostenbremse: Ein Bug oder Missbrauch darf nicht unbegrenzt kostenpflichtige SMS auslösen (Kill-Switch / Tageslimit).
- Webhooks: Signatur des Absenders verifizieren.
- CORS: keine `Access-Control-Allow-Origin: *` auf authentifizierten Endpoints.

### C4. Transport & Server
- HTTPS erzwungen (Redirect + HSTS).
- Security-Header: Content-Security-Policy, X-Content-Type-Options, Referrer-Policy.
- Fehlerseiten: keine Stack-Traces/Pfade nach außen.
- Backups & Updates: dokumentiert? (auch rechtlich relevant, Art. 32 DSGVO → recht-check.md)

---

## D. Programmierfehler & Robustheit

### D1. Logik & Zustand
- Race Conditions: mehrere async-Operationen auf denselben State (z. B. Doppelklick auf "Senden" → doppelte SMS/Bestellung). **Fix:** Buttons während laufender Operation disablen, Idempotenz.
- Off-by-one bei Schleifen/Slices, besonders bei Paginierung und Datumsbereichen.
- Floating-Point bei Geld: `0.1 + 0.2 !== 0.3`. Preise/DB-Beträge in Cent (Integer) rechnen oder konsequent runden — bei KPI-/Kalkulationstools kritisch.
- Mutierender State: Objekte/Arrays, die per Referenz geteilt und an mehreren Stellen verändert werden.

### D2. Fehlerbehandlung
- Jedes `fetch`/`await` mit Fehlerpfad: Was sieht der Nutzer bei Netzwerkfehler? (Bei offline-first: Was passiert überhaupt offline?)
- Leere Zustände: Was zeigt das Tool bei 0 Kunden, 0 Einträgen, leerer CSV?
- Fehler verschlucken (`catch(e){}` leer) = 🟡 mindestens.

### D3. Kompatibilität & Umgebung
- Browser-Support: verwendete APIs gegen Zielbrowser prüfen (ältere Android-WebViews im Außendienst!).
- Mobile: Touch-Targets, Viewport, funktioniert Datei-Download auf iOS?
- Zeitzonen & Lokalisierung: `toLocaleDateString` ohne explizites Locale, Sommerzeit-Sprünge bei Datumsberechnungen.

### D4. Wartbarkeit (nur als 🔵 Hinweis)
- Fehlende Versionsnummer im Tool sichtbar.
- Magische Zahlen ohne Konstante, tote Codepfade, duplizierte Logik.
- Kein Kommentar an nicht-offensichtlichen Stellen.
