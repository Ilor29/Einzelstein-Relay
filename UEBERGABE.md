# Project Handoff: Hetzner-App (Relay)

Version: v13 (ersetzt v12 vom 22.11. gegen 20:55)
Date: 2026-11-23, gegen 01:35
Owner/User: Roli
Prepared by: Claude (Karte Hetzner-App 25), automatisch vor Cache-Ablauf

Die Wahrheit steht in `BAUBUCH.md` (Einträge V262 bis V266 vom 23.11.) und in `~/projekte/Brain/REGISTER.md`. Diese Datei fasst nur zusammen.

## 1. Stand

Relay V266 läuft, `/api/version` meldet 266. Alles ist committet und auf `github main` gesichert, der Testserver 8799 ist beendet. Nichts ist halb fertig.

## 2. Was in dieser Karte geschah (23.11., 00:05 bis 01:35)

- V262: Bibliothek-Suche findet „code guard“ für code-guard (Bindestrich zählt als Leerzeichen, jedes Wort muss vorkommen). Eigener Reiter „★ Favoriten“ nach „Alle“, nur sichtbar mit Sternen; Favoriten stehen in „Alle“ nicht mehr oben. „Sitzung starten“ in Neue Sitzung ist unten angeheftet.
- V263: Tippt man „/“ am Anfang des Eingabefelds, erscheint eine Skill-Liste mit derselben Suche. Tipp trägt „/name “ ein.
- V264: 28 eingebaute Claude-Code-Befehle (clear, compact, model …) mit deutscher Kurzerklärung stehen in dieser Liste, von Hand gepflegt (`EINGEBAUT` in app.js).
- V265: Zeilen der Änderungen einer Karte sind antippbar, Kommentare lassen sich sammeln und „Ins Eingabefeld legen“ oder „An die Karte senden“. Diff jetzt blau (neu) und orange (entfernt) wegen Rolis Rot-Grün-Schwäche.
- V266: Die Spalte „Zur Hand“ gibt es nur am breiten Rechner, deshalb neuer Punkt „Änderungen ansehen und kommentieren“ im Drei-Punkte-Menü der Karte. Er öffnet ein Blatt, in das der Block aus „Zur Hand“ umzieht.
- Orca (orca.dev) eingeschätzt: Notiz `~/projekte/Brain/wissen/orca-dev-eingeschaetzt-2026-11-23.md`, Zeile im INDEX. Mockup: `https://seiten-roli.65-21-246-222.sslip.io/relay-diff-review/` (zeigt den Weg „Kartenmenü, Änderungen“, jetzt gebaut).

## 3. Beschlüsse (mit Auslöser)

- 00:05 „ich kann per / kein skill aufrufen … code guard … sagt er das gibt es nicht … Favoriten eigener Reiter … Knopf neue Sitzung wandert mit“: V262.
- 00:09 „44. direkt ins eingabe feld das ist bei der app vom claude auch so“: V263.
- 00:19 „45. Ja“: V264.
- 00:25 „46. bevor du was baust bitte mockup damit ich mir das vorstellen kann“: Mockup, nicht gebaut.
- 00:31 „49. lass einbauen ich hatte bis jetzt nicht gewusst das es geht“: V265. Frage 47 (sofort senden oder ins Feld legen) blieb unbeantwortet, gebaut ist die Empfehlung: erst ins Feld legen, Senden gibt es zusätzlich.
- 00:47 „51. Ja“: V266 (Roli hatte 00:38 gesagt, er überblicke nicht, wo die Kommentare stehen).

## 4. Offen

Bei Roli: Frage 50 (sollen Kommentare nach Neuladen bleiben, Empfehlung Nein). Zuletzt vergebene Nummer: 51, die nächste Frage bekommt die 52.

Bei der nächsten Karte, ohne Eile:
- Handyprobe V262 bis V266 steht aus, besonders V266 mit einer Karte, die echte Änderungen hat (Weg: Drei-Punkte-Menü, „Änderungen ansehen und kommentieren“).
- Ungeprüft: V259 am Handy; breiter Bildschirm nach dem Schließen des Blatts; Tastatur über dem Kommentarfeld; „An die Karte senden“ mit laufender Karte.
- Die Befehlsliste in V264 veraltet, wenn Claude Code neue Befehle bekommt.
- Aus der Vorkarte: „Im Verlauf suchen“ an echter Karte, Safari, Cron 04:20 der Übersetzung bei Lorenz und Lea, das verwaiste Etikett `skills/mein-gin-tonic-helfer` nicht ohne Rolis Wort löschen. `UEBERGABE-LAUFEND*.md` nicht angefasst.
- Von Orca denkbar als nächste Steine: Anzeige der Abo-Grenzen in einer Ansicht, zeitgesteuerte Aufträge, Worktrees für parallele Karten. Nur auf Rolis Wort.

## 5. Nächster Schritt

Neue Karte mit „Übergabe lesen“. Zuerst `curl -s localhost:8787/api/version` (soll 266 melden) und Piper auf Port 5005 prüfen (nach einem Dienst-Neustart braucht Piper gut eine Minute). Dann auf Rolis Wort warten.
