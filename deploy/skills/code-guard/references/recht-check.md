# CODE//GUARD Referenz: Rechts-Check DE/EU (v1.1)

**Stand der Rechtslage: 07/2026** — bei Nutzung dieser Referenz das Stand-Datum beachten.

Prüfpunkte nach deutschem und EU-Recht für Software-Produkte und interne Tools.

**Grundsatz:** Dieser Check identifiziert Prüfpunkte und wahrscheinliche Probleme. Er ist keine Rechtsberatung. Bei 🔴-Befunden mit Abmahn- oder Bußgeldrisiko immer den Hinweis auf Fachanwalt/Datenschutzbeauftragten in den Bericht schreiben.

**Aktualitäts-Regel (Pflicht):** Für jeden 🔴-Rechtsbefund den aktuellen Rechtsstand per Websuche verifizieren, bevor er in den Bericht kommt. Ist das Stand-Datum dieser Referenz älter als 12 Monate, gilt das auch für 🟠-Befunde. Verifikation mit Datum im Bericht vermerken.

---

## 0. Zuerst: Rollenklärung (entscheidet über fast alles)

Vor jedem DSGVO-Befund die Rolle des Anbieters bestimmen:

**Fall A — Reiner Software-Verkäufer (localStorage-Modell):**
Software läuft komplett beim Kunden, alle Daten bleiben lokal auf dessen Gerät, der Anbieter hat keinerlei Zugriff auf personenbezogene Daten der Endkunden. → Der Anbieter ist **kein Auftragsverarbeiter** (Art. 28 DSGVO) und benötigt **keinen AV-Vertrag** mit Kunden. Verantwortlicher für die Datenverarbeitung im Tool ist der Kunde selbst.
- Trotzdem prüfen: Telefoniert das Tool wirklich NIRGENDS nach Hause? (Analytics, Fonts, CDN, Update-Check, Aktivierungs-Server → jeder dieser Punkte kann Fall A kippen.)
- 🔵 Empfehlung: Diese Architektur als Verkaufsargument dokumentieren ("keine Datenverarbeitung durch uns").

**Fall B — Serverbasiertes System / Anbieter hostet Daten:**
Sobald personenbezogene Daten (auch nur Handynummern von Kunden der Kunden!) über den Server des Anbieters laufen: volle DSGVO-Pflichten, je nach Konstellation als Verantwortlicher oder Auftragsverarbeiter. → Abschnitte 1–4 vollständig prüfen.

**Fall C — Internes Tool:**
Auch intern gilt die DSGVO (Mitarbeiter- und Kundendaten). Kein Impressum/keine Datenschutzerklärung nach außen nötig, aber Verzeichnis von Verarbeitungstätigkeiten (Art. 30) und TOMs (Art. 32) relevant.

---

## 1. DSGVO — Kernprüfpunkte

### 1.1 Rechtsgrundlage (Art. 6)
- Für jede Verarbeitung personenbezogener Daten muss eine Rechtsgrundlage benennbar sein: Vertrag, berechtigtes Interesse, Einwilligung.
- **Werbliche Nachrichten (SMS/WhatsApp/E-Mail) an Kunden:** zusätzlich § 7 UWG! Elektronische Werbung braucht grundsätzlich ausdrückliche Einwilligung (Opt-in); Ausnahme § 7 Abs. 3 UWG nur eng (Bestandskunden, ähnliche Produkte, Hinweis auf Widerspruch bei Erhebung UND in jeder Nachricht). Broadcast-Systeme an Kundenlisten sind hier der klassische 🔴-Kandidat — Abmahnrisiko.
- Opt-out muss in jeder Nachricht möglich und technisch umgesetzt sein (Abmeldelink/STOP-Antwort, und die muss auch verarbeitet werden).
- **Nachweisbarkeit der Einwilligung (Art. 7 Abs. 1 DSGVO):** Der Verantwortliche muss die Einwilligung **nachweisen** können. Ein Opt-in ohne Protokollierung ist im Streitfall wertlos. Prüfen: Wird gespeichert, **wer** wann, **wie** (Formular/mündlich/Checkbox) und **wofür** eingewilligt hat — und wird auch der Widerruf protokolliert? Broadcast-System ohne Einwilligungs-Log = 🟠, selbst wenn Opt-in behauptet wird.

### 1.2 Informationspflichten (Art. 13/14)
- Datenschutzerklärung vorhanden, erreichbar, vollständig? (Zwecke, Rechtsgrundlagen, Empfänger, Speicherdauer, Betroffenenrechte, Kontakt.)
- Bei Web-Produkten: von jeder Seite aus erreichbar.

### 1.3 Auftragsverarbeitung (Art. 28)
- Liste aller Dienstleister erstellen, die personenbezogene Daten verarbeiten: Hoster, SMS-Gateway, E-Mail-Versand, Payment, Analytics. Für jeden: AV-Vertrag vorhanden?
- Deutsche/EU-Anbieter unproblematischer als US-Dienste (siehe 1.5).

### 1.4 Technisch-organisatorische Maßnahmen (Art. 32)
- Verschlüsselung Transport (HTTPS) und ggf. at rest, Zugriffskontrollen, Backups, Löschkonzept.
- **Löschkonzept konkret:** Werden Daten nach Zweckfortfall gelöscht? Gibt es überhaupt eine Löschfunktion? Fehlende Löschmöglichkeit = 🟠.

### 1.5 Drittlandtransfer (Art. 44 ff.)
- US-Dienste (Google Fonts vom Google-Server!, US-CDNs, US-Analytics, US-Cloud) sind Prüfpunkte. Google-Fonts-Einbindung vom Google-Server hat bereits zu Abmahnwellen geführt (LG München I, 2022) → Fonts lokal hosten = 🔴-Fix mit 5 Minuten Aufwand.
- Rechtsgrundlage für Transfer prüfen (Angemessenheitsbeschluss/Data Privacy Framework, SCCs) — Status ggf. per Websuche aktualisieren.

### 1.6 Besondere Datenkategorien & Betroffenenrechte
- Gesundheits-, Religions- u. ä. Daten (Art. 9): strengere Anforderungen — im Gastro-/Vertriebskontext selten, aber z. B. Allergie-Daten in Menü-Tools können hineinspielen.
- Auskunft (Art. 15) und Datenübertragbarkeit (Art. 20): Export-Funktion vorhanden?

---

## 2. TDDDG (ehem. TTDSG) — Cookies & Endgerätezugriff

- § 25 TDDDG: Jeder Zugriff auf das Endgerät, der nicht **unbedingt erforderlich** ist, braucht Einwilligung (Cookie-Banner). Gilt auch für localStorage/Fingerprinting, nicht nur Cookies!
- **Aber:** Technisch notwendige Speicherung (App-State eines Tools, das der Nutzer aktiv nutzt; Warenkorb; Login-Session) ist einwilligungsfrei. → Ein Offline-Tool, das localStorage nur als Funktionsspeicher nutzt, braucht **kein Cookie-Banner**. Falsch-positive Banner sind selbst ein 🔵 (UX-Schaden ohne Nutzen).
- Tracking/Analytics/Marketing-Pixel ohne Consent-Management = 🔴.

## 3. Impressumspflicht (§ 5 DDG, ehem. TMG)

- Jede geschäftsmäßige Website/Web-App braucht ein Impressum: Name, Anschrift, Kontakt (E-Mail), ggf. USt-IdNr., Vertretungsberechtigte. Fehlend/unvollständig = abmahnfähig = 🔴.
- Von jeder Seite in zwei Klicks erreichbar.
- Bei Shops zusätzlich: Widerrufsbelehrung, AGB-Einbindung, Grundpreisangaben, "zahlungspflichtig bestellen"-Button (§ 312j BGB).
- Bei Verkauf über Reseller (z. B. Digistore24 als Vertragspartner des Kunden): Reseller übernimmt Teile der Shop-Pflichten — Abgrenzung im Bericht dokumentieren, eigene Produkt-/Landingpage braucht trotzdem Impressum + Datenschutzerklärung.

## 4. Weitere Prüfpunkte nach Kontext

### 4.1 Barrierefreiheitsstärkungsgesetz (BFSG, seit 28.06.2025)
- Gilt für B2C-E-Commerce und bestimmte Verbraucherprodukte/-dienste. Reine B2B-Software: grundsätzlich nicht erfasst — aber Shops mit Verbraucherkunden (E-Commerce!) schon. Kleinstunternehmen-Ausnahme (< 10 MA und ≤ 2 Mio. € Umsatz) für Dienstleistungen prüfen.
- Bei Anwendbarkeit: WCAG-2.1-AA-Niveau als Maßstab.

### 4.2 NIS2 / Cyberresilienz
- NIS2 betrifft wichtige/wesentliche Einrichtungen ab bestimmten Größen — für Kleinunternehmen meist nicht direkt, aber Kunden können Anforderungen vertraglich weiterreichen. Nur als 🔵 erwähnen, wenn relevant.
- Cyber Resilience Act (CRA): kommt für Produkte mit digitalen Elementen; Übergangsfristen laufen. Bei kommerziellen Software-Produkten als 🔵 "auf dem Radar behalten" vermerken, aktuellen Stand bei Bedarf per Websuche prüfen.

### 4.3 Vertrags- & Gewährleistungsrecht bei Software-Verkauf
- Seit 2022: §§ 327 ff. BGB für digitale Produkte an Verbraucher — **Update-Pflicht** für die Dauer, die der Verbraucher erwarten kann, unabhängig vom "1 Jahr Updates"-Marketing-Modell. Verkaufte Einmalzahlung-Tools an Verbraucher: Update-Pflicht für Sicherheitsupdates besteht auch danach → als 🟠-Prüfpunkt aufnehmen, wenn B2C verkauft wird. Reines B2B: vertraglich gestaltbar.
- Gewährleistung kann bei B2C nicht ausgeschlossen werden.

### 4.4 KI-Einsatz (EU AI Act)
- Wenn das Tool KI-Funktionen enthält: Transparenzpflichten (Kennzeichnung von KI-Interaktion/KI-generierten Inhalten) prüfen; Risikoklasse bestimmen (Vertriebs-/Gastro-Tools i. d. R. minimales Risiko). Stand der anwendbaren Pflichten per Websuche verifizieren, das Feld bewegt sich.

### 4.5 Urheberrecht & Lizenzen
- Verwendete Bibliotheken/Fonts/Icons: Lizenz kompatibel mit kommerziellem Verkauf? (GPL in verkauftem Closed-Source-Tool = 🔴; MIT/Apache/OFL ok, Attribution beachten.)
- Lizenzhinweise Dritter im Produkt aufführen, wo die Lizenz es verlangt.

---

## Prüf-Reihenfolge (Kurzfassung)

1. Rolle klären (Fall A/B/C) → bestimmt Tiefe von Abschnitt 1
2. Kommunikations-Features? → 1.1 + UWG zuerst (höchstes Abmahnrisiko)
3. Web-Auftritt? → 2 + 3 (Banner, Impressum, Google Fonts)
4. Verkaufskanal? → 3 (Shop-Pflichten) + 4.3 (B2C vs. B2B)
5. Rest nach Kontext (4.1, 4.2, 4.4, 4.5)
