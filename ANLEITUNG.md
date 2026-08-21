# Dein eigener Server in einer Viertelstunde — Schritt für Schritt

Diese Anleitung bringt dich von null zu deinem eigenen Einzelstein-Relay-
Server. Du brauchst kein Technik-Wissen, nur ein bisschen Geduld: einfach
die Schritte der Reihe nach machen. Und wenn etwas anders aussieht als hier
beschrieben, nicht raten — frag in der Community nach.

## Was du brauchst

- Etwa 15 Minuten Zeit.
- Ein Handy mit Chrome, am besten Android. Auf dem iPhone bitte auch
  Chrome benutzen; das Diktat ist dort durch Apple eingeschränkt.
- Eine Bankkarte oder PayPal für den Server-Anbieter. Der Server kostet je
  nach Größe etwa 5–10 € im Monat und gehört dir; du kannst ihn jederzeit
  wieder löschen.
- Ein Claude-Konto mit Abo von Anthropic (claude.ai). Damit meldest du
  dich am Ende an. Deine Gespräche laufen über dein eigenes Konto, nicht
  über fremde.

## Schritt 1 — Konto beim Server-Anbieter anlegen

Wir beschreiben es für **Hetzner** (deutscher Anbieter); andere gehen auch.

1. Öffne **console.hetzner.cloud** und registriere dich.
2. Bestätige deine E-Mail und hinterlege eine Zahlungsart.

## Schritt 2 — Den Einrichtungs-Text kopieren

1. Öffne diese Adresse (am Rechner ist es bequemer, das Handy geht auch):

   https://raw.githubusercontent.com/Ilor29/Einzelstein-Relay/main/deploy/cloud-init.yaml

2. Markiere **den gesamten Text** und kopiere ihn (Strg+A, Strg+C — am
   Handy: lange drücken, „Alles auswählen", „Kopieren").

## Schritt 3 — Server erstellen

In der Hetzner-Übersicht auf **„Server erstellen"** klicken und so wählen:

1. **Standort:** egal — z. B. Nürnberg oder Falkenstein (Deutschland).
2. **Image (Betriebssystem):** **Debian 12**.
3. **Typ:** die günstigste Stufe mit **4 GB Arbeitsspeicher** reicht gut.
4. Ganz unten das Feld **„Cloud config"** aufklappen und den kopierten
   Text **komplett einfügen**.
5. Alles andere so lassen und **„Kaufen / Erstellen"** klicken.

Der Server richtet sich jetzt selbst ein. Das dauert 5 bis 10 Minuten.
Zeit für einen Kaffee.

## Schritt 4 — Deine Adresse bauen und öffnen

1. In der Hetzner-Übersicht steht bei deinem Server eine **IP-Adresse**,
   vier Zahlen mit Punkten — zum Beispiel `91.98.12.34`.
2. Daraus baust du deine App-Adresse: **Punkte durch Bindestriche ersetzen**
   und **`.sslip.io`** anhängen. Aus dem Beispiel wird:

   `https://91-98-12-34.sslip.io`

3. Diese Adresse am **Handy in Chrome** öffnen. Kommt eine Fehlermeldung,
   war der Server noch nicht fertig — zwei, drei Minuten warten und neu laden.

## Schritt 5 — Handy verbinden

Die App begrüßt dich mit **„Dieser Server ist frisch eingerichtet und gehört
noch niemandem"**. Tippe auf **„Diesen Server jetzt verbinden"**. Fertig —
dein Handy ist das erste Gerät. (Dieser Knopf erscheint nur beim allerersten
Gerät und nur in den ersten 24 Stunden. Danach geht es mit dem
Kopplungscode — siehe unten.)

Dann noch: Chrome-Menü (die drei Punkte) → **„Zum Startbildschirm
hinzufügen"**. Ab jetzt startet die App wie eine normale App vom
Startbildschirm.

## Schritt 6 — Bei Claude anmelden

1. Tippe auf **„Neue Sitzung"** und gib ihr einen Namen — zum Beispiel
   „Erste Schritte".
2. Beim allerersten Gespräch fragt Claude nach deiner Anmeldung. Die App
   zeigt dir dafür einen **Anmelde-Link als Knopf**: antippen, mit deinem
   Claude-Konto anmelden, den angezeigten Code bestätigen, zurück zur App.
3. Das war's — ab jetzt schreibst oder **diktierst** du einfach. Die
   eingebaute Einführung zeigt dir beim ersten Start, wo alles ist; du
   findest sie jederzeit wieder unter Einstellungen → „Die Einführung noch
   einmal ansehen".

## Weitere Geräte (Tablet, Rechner, Zweithandy)

Auf dem schon verbundenen Gerät: **Einstellungen → „Weiteres Gerät
hinzufügen"** — es erscheint ein Kopplungscode. Den am neuen Gerät eintippen,
fertig. Der Code gilt 15 Minuten und nur einmal.

## Gut zu wissen

- **Updates kommen von selbst.** Dein Server holt sich alle 15 Minuten die
  neueste Fassung — du musst nichts tun.
- **Deine Daten liegen auf deinem Server.** Dateien, Projekte und
  Mitschriften bleiben dort; das Vorlesen läuft lokal. Sobald Claude
  arbeitet, geht der Gesprächsinhalt an Anthropic — über dein eigenes
  Konto, genau wie in der offiziellen Claude-App.
- **Etwas klemmt?** In der App von oben nach unten wischen lädt sie frisch.
  Hilft das nicht: Server in der Hetzner-Übersicht neu starten — die App
  kommt von selbst wieder. Und sonst: in der Community melden.
