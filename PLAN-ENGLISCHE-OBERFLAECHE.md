# Plan: Englische Oberfläche der Relay (Sprachwahl in den Einstellungen)

Stand 01.11.2026 01:50. Beschlossen: Roli 31.10. 10:16 „11. Ja“ (Relay zweisprachig),
01.11. 01:35 „3. Ja“ (als eigener Stein planen), 01:43 „7. Ja“ (Aufbau laut Mockup
https://seiten-roli.65-21-246-222.sslip.io/relay-englisch-mockup/ : Abschnitt „Language“ oben in
den Einstellungen, Wahl auf dem Gerät gemerkt, Deutsch bleibt Vorgabe). Noch nicht gebaut.

## Was zu übersetzen ist (gezählt am Stand V197)

- web/index.html: 144 sichtbare Texte und 63 Beschriftungen in Attributen (aria-label, title,
  placeholder), zusammen rund 6.300 Zeichen.
- web/app.js: rund 173 deutsche Textstellen (Hinweise, Zustände wie „wartet auf dich“, Knöpfe,
  Zettel), rund 8.000 Zeichen. Dazu die Tour-Schritte (ab `tourSchritte`, Zeile 6365), die
  relativen Zeiten („vor 5 Min.“, Zeile 272) und die Datumsformate mit `de-DE` (Zeile 1297, 2097).
- hetzner_app/server.py: 99 Fehler- und Hinweistexte, die als Meldung in der App erscheinen.
- Stimme und Diktat: die eingebauten Piper-Stimmen sind deutsch; Browser-Diktat ist fest auf
  `de-DE` (app.js Zeile 3189); das Whisper-Diktat bekommt keine Sprache mit.
- Bleibt vorerst deutsch, mit Hinweis im README: ANLEITUNG.md, das Tour-Paket zum Herunterladen
  (web/dl/tour-paket.md, 13.000 Zeichen), die Brain-Anweisungen, Kairas Aussprache-Liste (nur
  für Kaira, also nur deutsch sinnvoll).

## Bauweise

1. Eine Textliste `web/texte.js` mit Schlüsseln und beiden Sprachen, eine Funktion `t("schluessel")`,
   die nach der gemerkten Sprache (`localStorage sprache`, Vorgabe `de`) nachschlägt. Fehlt ein
   Schlüssel, fällt sie auf Deutsch zurück, damit nie ein leerer Knopf entsteht.
2. In index.html bekommen alle festen Texte ein `data-t="schluessel"`; beim Start und beim
   Umschalten läuft einmal `texteAnwenden()` über die Seite. `<html lang>` wechselt mit.
3. In app.js werden die 173 Stellen auf `t(...)` umgestellt; Texte mit Einsetzern (Zahl, Name)
   als Vorlage mit Platzhaltern. Tour-Schritte ebenso. Zeiten und Datum über `Intl` mit der
   gewählten Sprache.
4. Der Server bekommt die Sprache per Kopfzeile `Accept-Language` aus der App mit; die 99
   Meldungen wandern in eine kleine Liste `hetzner_app/texte.py`. Fehlt die Sprache: Deutsch.
5. Stimme: eine englische Piper-Stimme (z. B. `en_GB-alan-medium` oder `en_US-lessac-medium`,
   beide MIT) kommt in `scripts/install-piper.sh` und in den KATALOG in tts.py, als Vorgabe bei
   Sprache Englisch. Browser-Diktat auf `en-US` bei Englisch, Whisper bekommt `language` mit.
6. Abschnitt „Language“ in den Einstellungen nach dem Mockup; Umschalten wirkt sofort, ohne
   Neuladen. Tour-Text zur Sprachwahl ergänzen.
7. Prüfung mit Playwright in beiden Sprachen (Liste, Sitzung, Einstellungen, Neue Sitzung, Tour),
   Screenshots, Konsole, kein deutscher Rest in der englischen Ansicht (automatisch gesucht nach
   Umlauten und typischen deutschen Wörtern). Dann VERSION hoch, ausrollen, README-Hinweis
   „German only“ in beiden READMEs ersetzen.

## Aufwand und Modell

Nach den Erfahrungswerten der Zeiten-Seite rund anderthalb bis drei Stunden Kartenzeit, verteilt
auf zwei bis drei Karten, weil der Umbau fast jede Datei berührt und der Kontext voll läuft.
Gerüst (Schritt 1, 2, 6), englische Formulierungen und Abnahme macht die Hauptkarte selbst; die
Fleißarbeit (Schritt 3 und 4, Stellen auf `t()` umstellen) geht an den Umsetzer auf Sonnet mit
fertiger Textliste. Die englischen Texte schreibe ich vor dem Umstellen, damit der Umsetzer nur
noch einsetzt und nicht übersetzt.

## Risiken

- Vergessene Stellen fallen erst beim Umschalten auf; deshalb die automatische Suche in Schritt 7.
- Zustände, die der Dialog-Wächter vom Claude-Code-Schirm liest, sind englisch und bleiben es,
  betroffen ist nur die Anzeige.
- Lea und Lorenz ziehen den Stand per Spiegel; für sie ändert sich nichts, Vorgabe bleibt Deutsch.
- Die englische Piper-Stimme ist ein Download von rund 60 MB in install-piper.sh; auf
  bestehenden Servern holt sie der nächste Setup-Lauf nach, bis dahin liest bei Englisch Jonas.
