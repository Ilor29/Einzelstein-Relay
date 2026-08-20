# Allgemeine Anweisungen für ALLE Projekte auf diesem Server

Stammfassung: `Hetzner-App/deploy/claude-global.md` (dort ändern, dann nach
`~/.claude/CLAUDE.md` kopieren). Diese Datei lädt Claude Code in jeder Sitzung
auf diesem Server, zusätzlich zur CLAUDE.md des jeweiligen Projekts.

## So arbeitet Roli

- Roli **diktiert per Sprache** und lässt sich Antworten **vorlesen**. Antworten
  kurz und hörbar halten: ganze Sätze, keine Tabellen-Wüsten, keine Pfad- und
  Code-Salven im Fließtext. Diktate enthalten Verhörer. Bei Unklarheit lieber
  kurz nachfragen als raten.
- Nach jeder abgeschlossenen Aufgabe klar **„Fertig" melden**. Roli arbeitet
  nebenbei und braucht das Signal.
- Entscheidungsfragen in **normalen Sätzen** stellen, keine Auswahl-Kärtchen.
- Ein Stein nach dem anderen: Aufgaben einzeln und mit Bedacht abarbeiten,
  nicht fünf Baustellen gleichzeitig aufreißen.
- **Klarschrift:** In normalem, gesprochenem Deutsch schreiben, ganze Sätze,
  wie man sie einem Kollegen sagen würde. Keine Gedankenstrich-Ketten (Komma,
  Doppelpunkt oder Punkt reichen fast immer), keine Aufzählungs-Fragmente,
  keine „**Schlagwort:** Erklärung"-Listen. Keine typischen KI-Floskeln
  („Lassen Sie uns …", „Es ist wichtig zu beachten", „robust", „nahtlos",
  „spielt eine zentrale Rolle", „Zusammenfassend lässt sich sagen"). Kein
  Dreierschema als Betonung („schnell, zuverlässig und elegant"), keine
  Kopula-Vermeidung („fungiert als", „stellt dar" statt „ist"). Kein
  abschließender Fazit- oder „Herausforderungen und Ausblick"-Absatz.
  Fachbegriffe erklären statt aneinanderreihen. Was vorgelesen wird, muss
  beim bloßen Zuhören verständlich sein.

## Regeln für alle Projekte

- **Commits mit sprechenden deutschen Nachrichten** (was und warum), nicht
  „Update" oder „Fix". Die automatische Sicherung committet alle 10 Minuten
  als „Automatisch gesichert". Wichtige Arbeit vorher selbst sauber committen.
- **Fremde Marken** (Claude, Anthropic, Hetzner …) nie in Produktnamen,
  Werbetexten oder öffentlichen Seiten verwenden.
- **Keine Geheimnisse** (Schlüssel, Passwörter, Tokens) in Dateien schreiben,
  die zu GitHub gesichert werden: Umgebungsvariablen oder Dateien außerhalb
  des Projekts nutzen.
- Nach größeren Arbeiten den **Stand ins Brain-Register** nachtragen:
  `~/projekte/Brain/REGISTER.md` (Zweck, Stand, nächster Schritt).
- Vor Behauptungen wie „verkaufsfertig" oder „rechtlich sauber": Lizenz- und
  Rechtslage prüfen (CODE//GUARD), nie aus dem Gedächtnis freigeben.
