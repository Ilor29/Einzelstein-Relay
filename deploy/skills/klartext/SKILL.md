---
name: klartext
description: >-
  Macht deutschsprachige Texte natürlicher und menschlicher: erkennt typische
  KI-Schreibmuster (Floskeln, Nominalstil, Bedeutungsinflation, hohle Einstiege)
  und schreibt sie in klare, lebendige Sprache um — ohne Fakten oder Kernaussage
  zu verändern. Liefert einen Entwurf zum Selbst-Beurteilen. Aktivieren bei:
  „Text menschlicher machen", „klingt nach KI", „KI-Floskeln entfernen",
  „natürlicher schreiben", „Text überarbeiten/entschärfen", „entkiseln".
version: 1.0.0
license: MIT
compatible_agents: [claude-code]  # geprüft. Andere Agenten erwartet, aber ungeprüft (Decision 018).
---

# Klartext — deutsche Texte natürlicher schreiben

© Skillkontor. Erzeugt einen **überarbeiteten Entwurf**, den du selbst prüfst und verantwortest —
der Skill ändert nichts an deinen Fakten und veröffentlicht nichts.

**Ehrliche Grenze:** Dieser Skill dient der **Schreibqualität** — er macht steife, glatte KI-Sprache
lebendiger. Er ist **kein Werkzeug, um KI-Detektoren zu überlisten** und **keine Hilfe, um KI-Arbeit
als eigene menschliche Leistung auszugeben**. Wer Prüfungs- oder Herkunftsregeln umgehen will, ist hier falsch.

## Grundregeln
- Arbeite auf **Deutsch**, sofern der Nutzer nichts anderes verlangt.
- **Kernaussage, Fakten, Reihenfolge** wichtiger Inhalte und den gewünschten Ton bewahren.
- Nicht nur Reizwörter tauschen, sondern dem Text **Stimme, Rhythmus und menschliche Eigenheiten** geben.
- An den Kontext anpassen: sachlich, locker, journalistisch, akademisch, geschäftlich oder persönlich.
- **Nichts erfinden** — keine Quellen, Zahlen, Studien oder Details. Fehlen Belege, vorsichtiger formulieren oder die Stelle markieren.
- Liegt kein Text vor, den Nutzer kurz um den zu überarbeitenden Text bitten.
- Sind Zielgruppe oder Ton unklar, einen natürlichen, sachlichen deutschen Stil wählen.

## Typische KI-Spuren im Deutschen
Besonders auf diese Muster prüfen:

- **Bedeutungsinflation:** „zentrale Rolle", „Meilenstein", „wegweisend", „bahnbrechend", „von entscheidender Bedeutung".
- **Nominalstil:** Häufung von `-ung`, `-heit`, `-keit`, `-tion` mit schwachen Verben („erfolgen", „durchführen", „gewährleisten").
- **KI-Lieblingswörter:** „zudem", „darüber hinaus", „insbesondere", „wesentlich", „umfassend", „fundiert", „vielfältig", „ganzheitlich", „Mehrwert", „Synergie".
- **Werbesprache:** „idyllisch gelegen", „besticht durch", „verzaubert", „atemberaubend", „einzigartig", „erstklassig", „hochwertig".
- **Vage Autoritäten:** „Studien zeigen", „Experten zufolge", „Fachleute gehen davon aus" — ohne konkrete Quelle.
- **Steife Partizipialphrasen:** „unterstreichend", „verdeutlichend", „widerspiegelnd".
- **Kopula-Vermeidung:** „stellt dar", „fungiert als", „bildet die Grundlage", wo „ist" oder „hat" natürlicher wäre.
- **Überstrapazierte Figuren:** „nicht nur … sondern auch", „weniger X, mehr Y", künstliche Dreiergruppen, falsche „von X bis Y"-Spannweiten.
- **Synonymzwang:** unnötig wechselnde Bezeichnungen für dieselbe Sache.
- **Hohle Einstiege:** „In der heutigen schnelllebigen Welt", „Im digitalen Zeitalter", „In Zeiten wie diesen".
- **Chatbot-Reste:** „Gerne!", „Hier ist eine Übersicht", „Ich hoffe, das hilft", „Lass mich wissen …".
- **Wissens-Disclaimer:** „Nach meinem letzten Trainingsstand", „Basierend auf den mir verfügbaren Informationen".
- **Überhöflichkeit:** „Das ist eine sehr gute Frage", „Sie haben absolut recht".
- **Füllphrasen:** „Aufgrund der Tatsache, dass", „zum jetzigen Zeitpunkt", „im Rahmen von", „es ist wichtig zu beachten".
- **Hedging:** „könnte potenziell möglicherweise".
- **Generische Optimismus-Schlüsse:** „Die Zukunft sieht vielversprechend aus", „ein wichtiger Schritt in die richtige Richtung".
- **Format-Tells:** zu viele Gedankenstriche, Fettschrift, Emojis, Bulletpoints mit fetten Labels, künstlich perfekte Gliederung.

## Arbeitsweise
1. **Text erfassen** — vollständig lesen; Zweck, Zielgruppe, Ton und Medium erkennen.
2. **Muster markieren** — die wichtigsten KI-Spuren erkennen, nicht jede Kleinigkeit aufzählen.
3. **Erste Überarbeitung** — auffällige Muster entfernen, Ballast kürzen, stärkere Verben und konkretere Formulierungen.
4. **Menschliche Stimme** — Satzlängen variieren; wo es passt, Haltung, Ambivalenz, Ich-Form, kleine Unebenheiten oder konkrete Beobachtungen zulassen.
5. **Zweiter KI-Check** — intern fragen „Was klingt daran noch nach KI?" und die verbleibenden Tells knapp benennen.
6. **Finale Fassung** — eine zweite, bereinigte Version, die natürlicher und weniger maschinell wirkt.

## Ausgabeformat
Standardmäßig, wenn ein Text zur Überarbeitung kommt:

1. **Erste Überarbeitung**
2. **Was klingt daran noch nach KI?** — knappe Stichpunkte zu den verbleibenden Auffälligkeiten
3. **Zweite, finale Überarbeitung**
4. **Änderungen kurz erklärt** — nur die wichtigsten Eingriffe, wenn es hilft

Will der Nutzer ausdrücklich **nur** die finale Version, liefere nur diese.

## Stilregeln für die Überarbeitung
- Abstrakte Substantivketten durch Verben und konkrete Aussagen ersetzen.
- Einfache Wörter nutzen, wenn sie natürlicher klingen.
- Floskeln **streichen**, nicht durch neue Floskeln ersetzen.
- Fachliche Präzision erhalten, künstliche Schwere entfernen.
- Mechanische Listen vermeiden, wenn Fließtext natürlicher wirkt.
- Fettschrift, Emojis und Gedankenstriche nur, wenn sie ins Zielmedium wirklich passen.
- Unebenheiten erlauben, wenn sie menschlicher wirken und den Text nicht verschlechtern.

## Beispiele für Ersetzungen
- „spielt eine zentrale Rolle" → „ist wichtig" oder die konkrete Wirkung benennen
- „Die Durchführung der Optimierung erfolgt" → „Wir optimieren"
- „Darüber hinaus bietet es einen Mehrwert" → konkret sagen, was besser wird
- „Studien zeigen" → konkrete Quelle nennen oder die Behauptung abschwächen
- „Es geht nicht nur um X, sondern auch um Y" → direkter Gegensatz oder klare Aussage
- „Die Zukunft sieht vielversprechend aus" → den konkreten nächsten Schritt nennen

## Grenzen
- **Keine Garantie**, dass ein Text von KI-Detektoren als menschlich erkannt wird — und das ist nicht der Zweck.
- Fachlich notwendige Begriffe nicht streichen, nur weil sie häufig vorkommen.
- Bei stark formellem, juristischem oder wissenschaftlichem Stil **weniger glätten** und die passende Fachsprache bewahren.
- Wirkt ein Text schon natürlich, das kurz sagen und nur kleine Verbesserungen vorschlagen.
- Der gelieferte Text ist ein **Entwurf**, für den der Nutzer selbst verantwortlich ist.
