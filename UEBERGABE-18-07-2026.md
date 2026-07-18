# Übergabe Hetzner-App: Hetzner 1.0 → 1.1

**Datum:** 18.07.2026, 18:12  
**Version:** 75 (live)  
**Chat-Historie:** kompaktiert → neuer Chat als 1.1

---

## Vision & Kernidee (für Gedächtnis)

**Relay** — PWA für Claude-Code-Sitzungen vom Handy. Der echte Zweck: **Einrichtungs-Helfer für Nicht-Entwickler** (ein Kunde soll seinen eigenen Claude-Server aufs Handy kriegen und Claude selbst installieren). Nicht als „Rolis Fernsteuerung" verstehen, sondern als **Produkt**.

**Markenname:** „Einzelstein Fernbedienung" (unter Rolis Marke, nicht Claude/Anthropic/Hetzner).

---

## Stand heute: Version 75, live

### Was in V75 gerade fertig wurde

**Vorlesen-Verbesserungen (V69–V74):**
- **Folge-Modus (V69):** Einmal drücken → App liest weiter, während Claude noch schreibt. Keine wiederholten Drücke nötig.
- **Vier Probetexte (V72):** Jede Stimme hat einen anderen Text; nicht viermal dasselbe hören.
- **Antwort-Zusammenfassung (V73):** Wenn eine Antwort in mehrere Bruchstücke zerfällt (wegen Werkzeug-Einsatz), zeigt die App einen Lautsprecher — nicht einen pro Bruchstück. „Alles gemeinsam" statt Stein für Stein.
- **Teilen (V74):** Jede Antwort hat einen Teilen-Knopf → Handy-Menü (WhatsApp, SMS, E-Mail …).

**Stimmen bereinigt (V75):**
- **Marie (de_DE-kerstin-low) gelöscht:** war rau und unangenehm.
- **Angebot jetzt:** Jonas (schnell, Standard), Jonas·fein (premium, braucht starken Server), Max (lebhaft).
- **Gemessen:** Jonas synth ~0,15× Echtzeit → flüssig. Jonas·fein ~1,0× → Lücken auf kleinem Server. **Verkaufsargument:** besserer Server = schönere Stimme (CPU-abhängig, nicht GPU).

**Projekt-Vorlage (V68):**
- Neue Projekte bekommen auto Start-CLAUDE.md + .gitignore + Git-Repo.
- Knopf „neues Projekt anlegen" im Startformular (Leitplanken: nur unter ~/projekte, keine Punkt-Namen).

**Allgemeinbefehl (V68):**
- Global CLAUDE.md für alle Server-Projekte: Arbeitsweise, Commits auf Deutsch, keine fremden Marken, Register pflegen.
- Liegt in `deploy/claude-global.md`, wird nach `~/.claude/CLAUDE.md` kopiert.

**Piper-Umbau (V66–V67):**
- Piper läuft als **separater HTTP-Server** (127.0.0.1:5005), nicht als in-process Import.
- **GPL-Blocker gelöst:** Prozess-Trennung + Kunde installiert Piper selbst = keine GPL-Verteilung durch uns.
- Alle Fixes verifiziert: Leertext 3-fach gefiltert, HTTPError ≠ OSError, Längen-Limits (senden 2M, vorlesen 100K, body middleware 35 MB), Piper-Neustart nur bei echten Fehlern.

---

## Offene Aufgaben (priorisiert)

### 🔴 Kritisch für Verkauf

1. **Weibliche Frauenstimme finden**
   - Option A: MLS-Stimme (CC-BY) zurück + einen Credit-Satz im Impressum („Stimmen: MLS, CC-BY 4.0")
   - Option B: Stimmen-Portfolio vorerst nur männlich, dann später eigene Frauenstimme trainieren
   - **Entscheidung:** Roli entscheidet
   - **Wenn A:** MLS-Stimme laden, Menü aufräumen, THIRD-PARTY-LICENSES.md updaten

2. **Rechtliche Finalprüfung (noch offen)**
   - Piper-Prozess-Trennung + Customer-Install-Modell: IT-Fachanwalt-Freigabe einholen
   - Stimmen-Lizenzen: Thorsten CC0 bestätigen, Kerstin CC0 bestätigen
   - THIRD-PARTY-LICENSES.md mit `pip-licenses` gegen-checken

3. **Impressum & Datenschutzerklärung (Rechtsgerüst)**
   - Wer? Impressum-Pflicht (EU-Richtlinie).
   - Wo? Handy-App (PWA oder APK später)?
   - Was schreiben? Vorlage/Beispiel nötig.
   - **Koordination:** Fachanwalt

### 🟠 Für Produktnutzen

4. **Längenbegrenzung bei Vorlesen: Dauer anzeigen**
   - Wie Grok: „4:20" unter dem Lautsprecher
   - Web-Audio-Puffer summieren, Zeitformat HMS
   - **Effort:** klein

5. **Vorlese-Spieler (Pause/Satz vor·zurück)**
   - Kleine Leiste während des Vorlesens
   - Satzweise Kontrolle (nicht starr 15s wie Grok)
   - Braucht: Sätze merken statt wegwerfen
   - **Effort:** mittel

### 🟡 Einrichtungs-Assistent (Kern der Verkaufsidee)

6. **„Setup"-Flow für Neukunden**
   - Erste Frage: Server-Adresse eingeben
   - Zweite Frage: Claude-API-Token
   - Automatische Piper-Installation prüfen / anleiten
   - Test-Verbindung
   - **Effort:** groß, aber kernig für Verkauf
   - **Abhängig von:** APK-Wrapper-Strategie (Domain vs. IP-Binding — noch offen)

### 🔵 Später

7. **APK-Wrapper („Seidenhülle")**
   - Abhängig von: Domain/IP-Binding-Entscheidung
   - Wenn geregelt: PNG-Icons (192×192, 512×512), manifest.json, Bubblewrap-Build

8. **Eigene Frauenstimme trainieren**
   - Aus Rolis Aufnahmen
   - Piper-Trainings-Flow
   - **Effort:** XXL, erst nach Setup-Assistent

9. **Brain als systemd-Dienst verankern**
   - Damit Brain nach Absturz auto-startet (war am 17.07. OOM-gestorben)

---

## Entscheidungen & Learnings

### Stimmen & Server-Performance
- **Jonas-Medium ist Standard** → flüssig auf kleiner CPU
- **Jonas-High ist Premium** → braucht starken Server, aber besserer Klang
- **Marketing-Punkt:** „Besserer Server, schönere Stimme" ist echt (CPU-Effekt, messbar)

### Piper-Lizenz: Prozess-Trennung
- **Gelöst:** HTTP-Server auf 127.0.0.1:5005, kein in-process Import
- **Folge:** Kein GPL-Kontakt für uns; Kunde installiert selbst → eigene GPL-Verteilung
- **Noch offen:** Fachanwalt-Bestätigung vor Verkauf

### Chat-Länge & Modelle
- **Opus ist langsam bei langen Chats** (Verlauf wird immer wieder gelesen)
- **Sonnet schneller, aber weniger schlau**
- **Lösung:** Model-Advisor proaktiv starten; neue Chat-Version bei Längung
- **Haiku für kurze Fragen ohne Code-Arbeit:** O.k.

### Übergabe-Logik (für künftige Chats)
- Wenn ein Chat länger wird als ~2 Stunden oder sehr viele Tokens: neue Version aufmachen
- Alte Inhalte ins Brain (Register), neue Chat fängt frisch an
- Automatische Versionierung (1.0 → 1.1 → 1.2 …)

---

## Was ins Brain gehört (für Langzeit)

Folgende Einträge sind bereits ins Gedächtnis geschrieben:
- Roli arbeitet per Sprache (Diktat + Vorlesen)
- Hetzner-App: echtes Produkt (Einrichtungs-Helfer), nicht Spielzeug
- Piper-Lösung: Prozess-Trennung, Fachanwalt-Abwartung
- Stimmen: Jonas/Jonas-fein/Max (CC0), Marie raus
- Vorlese-Qualität: CPU-abhängig, nicht GPU

**Noch zu speichern (für Hetzner 1.1):**
- Model-Advisor-Integration (vor großer Arbeit proaktiv starten)
- Übergabe-Logik & Chat-Versionierung (1.0, 1.1, 1.2 …)
- Brain & Claude-Chat-Aufteilung (Archiv vs. Arbeit)
- APK-Domain/IP-Binding-Frage (noch offen — für Einrichtungs-Assistent crucial)

---

## Nächster Chat (1.1): Start-Anweisungen

**Model:** Opus 4.8, aber:
- Vor großer Code-Arbeit: Model-Advisor aufrufen
- Wenn Gespräch > 2h: Übergabe schreiben, neue Chat-Version

**Vorrang 1.1:**
1. Weibliche Stimme: Entscheidung treffen (MLS + Credit vs. nur männlich)
2. Setup-Assistent anfangen (oder: Domain/IP-Binding erst klären?)
3. Länge-Anzeige beim Vorlesen (schneller Stein)

**Brain:**
- Beim Start alle Gedächtnis-Einträge laden (sollte automatisch happen)
- Falls nicht: `~/projekte/Hetzner-App/memory/` durchsehen

---

**Hetzner-App 1.0 ist fertig, weitermachen in 1.1. Los geht's!**
