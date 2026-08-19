# Bitte beachten — verbindliche Korrekturen für die Fernbedienungs-Seite

Zwei Punkte MÜSSEN vor dem Livegang umgesetzt werden. Beide sind
Ehrlichkeits- und Rechtsfragen — falsche Aussagen auf einer öffentlichen Seite
können abgemahnt werden. Details und korrekte Fakten in `PROJEKTINFO.md`.

---

## 1. Falsche Datenschutz-Aussage entfernen (kritisch)

Im bisherigen Entwurf (`ENTWURF-fernbedienung.md`, Abschnitt „Warum ein eigener
Server") steht sinngemäß: **„Kein Weiterleiten an fremde Wolken, kein
Mitlesen."**

Für die Fernbedienung ist das **falsch**: Das eigentliche KI-Gespräch — das,
was du schreibst, und was die KI zum Antworten liest — **geht sehr wohl an den
KI-Anbieter (Anthropic, USA)**, genau wie bei jeder KI-App. Das lässt sich
nicht vermeiden, wenn man die KI überhaupt nutzt.

**Bitte diesen Absatz durch die ehrliche Fassung ersetzen:**

> ### Warum ein eigener Server
> Die App läuft auf **deinem** Server, mit **deinen** Schlüsseln. Deine
> Dateien, deine Projekte und die Gesprächs-Aufzeichnungen bleiben auf deiner
> Maschine — sie werden nicht bei uns oder sonst wem gespeichert. Was die KI
> zum Antworten braucht, nämlich der Inhalt eures Gesprächs, geht an den
> KI-Anbieter — **genau wie bei jeder KI-App, mehr nicht.** Du entscheidest,
> was du ihm gibst. Die Vorlese-Stimme läuft standardmäßig lokal auf deinem
> Server; schönere Cloud-Stimmen und das Mikrofon-Diktat kannst du dazuschalten,
> gehen dann aber ebenfalls an den jeweiligen Anbieter.

**Nicht verwenden:** „100 % lokal", „nichts verlässt deinen Server", „keine
Cloud", „alle Daten bleiben in Deutschland" — für die Fernbedienung ist das
irreführend.

---

## 2. Fernbedienung nicht unter die Einzelstein-Prinzipien stellen (wichtig)

Die Einzelstein-Seite steht auf den Prinzipien **„100 % lokal · 0 Abos ·
0 Tracker · einmal zahlen"**. Das passt zu den anderen Werkzeugen (z. B.
Diktatwerk) — die **Fernbedienung bricht diese Prinzipien aber alle**:

- Sie braucht ein **Claude-Abo** (also ein Abo) → widerspricht „0 Abos".
- Das Gespräch läuft über die **Cloud** → widerspricht „100 % lokal".
- Sie ist ein **Geschenk** an die Community → nicht „einmal zahlen".

**Bitte:** Die Fernbedienung **nicht** unter dieselbe Überschrift/Prinzipien-
Leiste wie die lokalen Kaufprodukte stellen. Sie braucht ihre **eigene,
ehrliche Einordnung**: ein anderer Typ Produkt — dein eigener KI-Server, den du
selbst betreibst, aktuell als Geschenk an die Community, mit eigenem Claude-Abo.
Sonst widerspricht die Seite sich selbst.

---

## 3. Marken- und Pflicht-Regeln (kurz)

- Marke ist **Einzelstein**. **Keine** Fremdmarken (Claude, Anthropic, Hetzner)
  im Namen, Logo oder als Werbe-Aufhänger. Sachlich sagen, dass es **Claude
  Code** bedient, ist ok — nicht als „offizielles Claude-Produkt" erscheinen.
- Optik genug von der offiziellen Claude-App abheben (keine Verwechslungsgefahr).
- **Impressum + Datenschutzerklärung** Pflicht (sind auf einzelstein-software.de
  vorhanden → verlinken). Der Datenschutz muss den KI-Anbieter (US-Transfer) und
  optionale Dienste (Mikrofon-Diktat, Cloud-Stimmen) nennen.

---

*Fragen zum Produkt beantwortet Roli — die Fakten stehen in `PROJEKTINFO.md`.*
