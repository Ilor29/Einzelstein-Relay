---
name: handschrift
description: >-
  Hilft, hochwertiges, eigenständiges Webdesign zu bauen und den generischen
  „KI-Einheitslook" (AI-Slop) zu vermeiden — für Landingpages, Web-Apps und
  einzelne Seiten. Gibt dem Entwurf eine eigene Handschrift: Konzept zuerst,
  Charakter-Schrift, bewusste Palette, Bedeutung in der Form, Bewegung mit Sinn,
  und Varianten vergleichen statt blind bauen. Aktivieren bei: „Landingpage
  bauen", „Webseite gestalten", „Design für …", „sieht nach KI aus / zu
  generisch", „hochwertiger machen", „AI-Slop vermeiden", „Hero/Startseite
  entwerfen", „Redesign".
version: 1.0.1
license: MIT
compatible_agents: [claude-code]  # geprüft. Andere Agenten erwartet, aber ungeprüft.
---

# Handschrift — hochwertiges Webdesign statt KI-Einheitslook

© Skillkontor. Dieser Skill liefert **gestalterische Führung und Entwürfe**, die du
selbst beurteilst. Er ersetzt keinen Geschmack und keine Marke — er bringt Handwerk
und eine bewusste Haltung ein, damit ein Entwurf nicht wie von der Stange aussieht.

## Die Haltung

Behandle jede Seite so, wie es ein kleines, vielseitiges Design-Studio täte: mit
bewussten Entscheidungen zu Konzept, Schrift, Farbe, Layout und Bewegung, die **genau
zu diesem Thema** passen. Der häufigste Fehler von KI-Design ist nicht Hässlichkeit,
sondern **Beliebigkeit** — es könnte für jedes beliebige Produkt sein. Dagegen
arbeiten wir.

Passe den Aufwand an die Aufgabe an. Ein Memo braucht saubere Typografie und Ruhe,
keine Show. Eine Landingpage darf eine These haben und ein Wagnis eingehen. Entscheide
das zuerst.

## Der KI-Einheitslook — und was ihn verrät

KI-Design fällt derzeit in wenige, wiedererkennbare Muster. Nutze keins davon aus
Bequemlichkeit; wenn der Nutzer eins ausdrücklich will, folge ihm.

- Creme-Weiß (#F4F1EA) mit Serifen-Display und Terrakotta-Akzent.
- Fast-Schwarz mit **einem** grellen Grün- oder Zinnober-Tupfer.
- Lila-zu-Blau-Verlauf im Hero auf Weiß.
- **Inter** oder **Space Grotesk** als „sichere" Schrift.
- Emojis als Abschnittsmarken; alles zentriert; überall `rounded-lg`.
- Generische Karten mit Akzent-Leiste; „Powered by AI"-Knöpfe.
- Gedankenstrich-Inflation: der lange Strich in jedem zweiten Satz, wo ein
  Komma, Doppelpunkt oder Punkt natürlicher wäre. Sparsam eingesetzt ist er ein
  Stilmittel, gehäuft ist er eine Signatur.

Wo nichts vorgegeben ist, gib diese Freiheit **nicht** für eins dieser Defaults aus.

## Die Methode

### 1. Konzept zuerst — verankere die Gestaltung im Thema
Fasse in einem Satz: das konkrete Thema, die Zielgruppe, die **eine** Aufgabe der
Seite. Aus der Welt des Themas kommen die eigenständigen Entscheidungen — seine
Materialien, Werkzeuge, seine Sprache. (Beispiel aus der Praxis: aus „ein geprüftes
Netz aus Skills" wurden eine lebende Netz-Animation, ein Prüf-Siegel und — über die
Anspielung „Kontor" — ein Wachssiegel, Akten-Karten und eine Serifenschrift.)

### 2. Typografie mit Charakter
Die Schrift trägt die Seite, auch wenn es nicht um Schrift geht.
- Wähle eine **charaktervolle** Display-Schrift bewusst — nicht Inter/Space Grotesk.
- **Hoste Schriften selbst** per `@font-face` (kein Fremd-CDN, keine stillen
  Fallbacks). Für Artefakte mit strenger CSP: als `data:`-URI einbetten.
- Paare Display + Fließtext. Halte Lauftext bei ~65 Zeichen Breite, setze eine
  Typo-Skala und bleib dabei; `text-wrap: balance` für Überschriften.

### 3. Farbe wählen, nicht erben
Beschreibe die Palette als 4–6 benannte Werte. Neutraltöne mit einem **leichten
Hue-Stich** in Richtung des Akzents wirken gewählt; reines Mittelgrau wirkt
unbedacht. Setze **einen** kräftigen Akzent sparsam ein. Semantische Farben
(gut/Warnung/kritisch) sind getrennt vom Akzent.

### 4. Bedeutung in die Form legen
Struktur-Elemente (Nummerierung, Marken, Siegel, Stempel, Trennlinien) sollen etwas
**Wahres** über den Inhalt kodieren, nicht dekorieren. Nummerierte Schritte nur, wenn
es wirklich eine Reihenfolge ist. Zustand in Form zeigen — ein Chip, ein Streifen, ein
Stempel —, damit das Wichtige auf einen Blick lesbar ist. (Beispiel: der „Geprüft"-
Stempel auf den Karten macht die Prüfung zum Blickfang statt zur Deko.)

### 5. Bewegung mit Sinn
Eine **inszenierte** Bewegung wirkt stärker als viele verstreute Effekte: ein
Seitenaufbau, ein Scroll-Reveal, eine ruhige Hintergrund-Atmosphäre. Manchmal ist
weniger mehr — zu viel Animation ist selbst ein KI-Tell. Respektiere immer
`prefers-reduced-motion`. Für dekorative Grafik lieber Canvas/WebGL als
handgeschriebene SVG-Pfade.

### 6. Sauber bauen (Pflicht-Check)
- Beide Themes: Palette als Custom-Properties, per `prefers-color-scheme` **und**
  `:root[data-theme=…]` — beide Richtungen, gleiche Sorgfalt.
- Layout über Flex/Grid + `gap`, nicht über Einzel-Margins. Breite Inhalte (Tabellen,
  Code, Diagramme) in einen `overflow-x:auto`-Container; die Seite scrollt nie
  seitwärts.
- `font-variant-numeric: tabular-nums`, wo Ziffern in Spalten stehen.
- Sichtbarer `:focus-visible`-Zustand; Kontraste lesbar; keine kollidierenden
  Selektor-Spezifitäten, die Abstände still zurücknehmen.
- Weiche Kanten mit `mask-image` statt harter Bildränder; überlappende Ebenen bewusst
  stapeln.

### 7. Varianten vergleichen, nicht blind bauen
Bei wichtigen Weichen — Schrift, Karten, Schlüsselgrafik — **mehrere Fassungen
nebeneinander** zeigen und den Menschen entscheiden lassen. Aus dem Sehen entscheiden
schlägt aus dem Beschreiben raten. (In der Praxis: Schrift-, Karten- und Siegel-
Mockups Seite an Seite, dann live gesetzt.)

### 8. Text ist Gestaltungsmaterial
Schreibe von der Nutzerseite her: benenne Dinge, wie Menschen sie kennen. Aktiv,
konkret, ehrlich. Ein Knopf sagt, was passiert; eine Fehlermeldung sagt, was schiefging
und wie man es behebt. Konkret schlägt clever.

### 9. Am Ende prüfen
Ansehen, nicht hoffen: überlappende Elemente, Kaskaden-Kollisionen, stille Fallbacks
sitzen in der Lücke zwischen Quelltext und Ergebnis. Wenn möglich, rendern und
anschauen (oder rendern lassen), bevor du „fertig" sagst.

## Ablauf im Gespräch
1. Konzept in einem Satz festhalten (Thema, Zielgruppe, Aufgabe der Seite).
2. Kurzer **Design-Plan**: Palette (4–6 Werte), Schriften (2+ Rollen), Layout-Idee in
   ein, zwei Sätzen. Prüfe den Plan gegen den Einheitslook — was klingt nach Default,
   ändere es.
3. Bauen, streng nach dem Plan. Bei wichtigen Weichen Varianten zum Vergleich.
4. Prüf-Check aus Abschnitt 6 durchgehen. Rendern und ansehen.

## Grenzen
- **Kein Ersatz für Geschmack und Marke.** Die Wünsche des Nutzers und ein bestehendes
  Design-System schlagen immer die Vorschläge hier.
- **Keine fremden Marken** in Produktnamen, Logos oder Werbetexten nachbauen.
- Der gelieferte Entwurf ist ein Vorschlag, den der Nutzer beurteilt und verantwortet.
