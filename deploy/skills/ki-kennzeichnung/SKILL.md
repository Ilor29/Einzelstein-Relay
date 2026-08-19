---
name: ki-kennzeichnung
description: >-
  Erinnert daran, KI-erzeugte Inhalte richtig zu kennzeichnen, bevor sie
  veröffentlicht werden — für Instagram, Facebook, YouTube, TikTok, Websites.
  Weist auf die Transparenzpflichten der EU-KI-Verordnung (Art. 50, gilt seit
  2. August 2026) hin und liefert fertige Kennzeichnungs-Bausteine zum Einfügen.
  Trennt dabei, was der Anbieter des KI-Werkzeugs schuldet und was du selbst
  schuldest — und weist auf Irreführung nach § 5 UWG hin, die eine Kennzeichnung
  nicht heilt. Gibt Hinweise, kein Rechtsurteil. Aktivieren bei: „KI-Bild posten",
  „mit KI erstelltes Video veröffentlichen", „muss ich das als KI kennzeichnen",
  „Deepfake kennzeichnen", „Chatbot-Hinweis", „ist das AI-konform",
  „KI-Bilder auf der Webseite", „brauche ich einen Zusatz".
version: 1.1.0
license: MIT
compatible_agents: [claude-code]  # geprüft. Andere Agenten erwartet, aber ungeprüft (Decision 018).
---

# KI-Kennzeichnung — Transparenzpflichten im Blick behalten

© Skillkontor. **Rechtsstand: 2. August 2026.** Dieser Skill ist eine **Erinnerung**,
keine Rechtsberatung und **kein Konformitäts-Urteil**. Er sagt nie „das ist verboten"
oder „das ist konform", sondern: „Achtung, hier greift wahrscheinlich eine
Kennzeichnungspflicht — so kennzeichnest du es sauber." Und ebenso deutlich:
„hier greift für dich keine" — Entwarnung ist genauso Teil der Aufgabe.

## Warum dieser Skill existiert
Seit dem 2. August 2026 gelten die Transparenzpflichten aus **Artikel 50 der
EU-KI-Verordnung**: synthetische Inhalte müssen markiert, Deepfakes offengelegt und
KI-Chats als solche erkennbar sein. Das betrifft genau, was in Social Media und auf
Websites tagtäglich entsteht — wobei ein Teil dieser Pflichten den Anbieter des
Werkzeugs trifft und nicht den, der damit arbeitet.

Dieser Skill ist ein **Schnappschuss** dieses Rechtsstands — er hält das Datum fest und
erinnert an die Pflichten, ersetzt aber keine aktuelle Prüfung.

## Wann du aktiv wirst
Immer wenn KI-erzeugte oder KI-veränderte Inhalte (Bild, Video, Audio, Text) für die
Veröffentlichung entstehen — besonders zusammen mit einem Erzeugungs-Skill wie
social-content. Prüfe still im Hintergrund, ob eine der Pflichten unten greift, und sag es
dem Nutzer, bevor er veröffentlicht — auch dann, wenn das Ergebnis „keine Pflicht für dich"
lautet.

## Zuerst die Frage, die alles entscheidet: Wer schuldet was?

Artikel 50 spricht **zwei verschiedene Adressaten** an. Das zu verwechseln ist der
häufigste Fehler — er führt dazu, dass Leute Hinweise anbringen, die sie gar nicht
schulden, und die Fälle übersehen, in denen sie wirklich etwas tun müssen.

| Wer | Was |
|---|---|
| **Anbieter** des KI-Werkzeugs (Midjourney, Higgsfield, OpenAI …) | muss die Ausgabe maschinenlesbar markieren — Wasserzeichen, Metadaten |
| **Du als Verwender** | musst offenlegen, wenn du bestimmte Inhalte erzeugst oder veröffentlichst — siehe Pflicht 2 und 3 |

**Frag deshalb immer zuerst:** Geht es um die technische Markierung durch das Werkzeug,
oder um einen sichtbaren Hinweis, den der Nutzer selbst anbringen muss? Nur das Zweite ist
seine Aufgabe.

## Die Pflichten (als Erinnerung, nicht als Urteil)

**1. Maschinenlesbare Markierung — Sache des Anbieters, nicht deine**
Wer ein System bereitstellt, das synthetische Bilder, Videos, Audio oder Texte erzeugt, muss
dafür sorgen, dass die Ausgabe maschinenlesbar als KI-erzeugt markiert ist. Das schuldet der
Anbieter des Werkzeugs. → **Daraus folgt für den Nutzer keine eigene Kennzeichnungspflicht.**
Zwei praktische Hinweise trotzdem:
- Vorhandene Markierungen oder Metadaten **nicht entfernen** — auch nicht versehentlich beim
  Zuschneiden, Konvertieren oder Komprimieren.
- Ein rein dekoratives, abstraktes KI-Bild auf einer Webseite (Muster, Grafik, Symbolik)
  löst nach dieser Vorschrift **keine** Hinweispflicht für den Verwender aus.

**2. Deepfakes offenlegen — das ist deine Pflicht**
Künstlich erzeugte oder veränderte Darstellungen von Personen, Stimmen, Orten oder
Ereignissen, die **echt wirken**, musst du als Verwender klar offenlegen. Das ist der
strengste Punkt und der, auf den es meistens hinausläuft. **Der Hinweis gehört sichtbar an
den Inhalt selbst** (ins Bild bzw. Video) — nicht bloß in Bildunterschrift, Credits oder
Metadaten versteckt.
Bei erkennbar künstlerischen, kreativen oder satirischen Werken darf der Hinweis so platziert
werden, dass er die Darstellung nicht zerstört — offengelegt werden muss trotzdem.

**3. KI-Texte zu Themen von öffentlichem Interesse**
Wer KI-erzeugte Texte veröffentlicht, um die Öffentlichkeit über Angelegenheiten von
öffentlichem Interesse zu informieren, muss das offenlegen. Wird der Text redaktionell
geprüft und trägt jemand die Verantwortung dafür, greift das in der Regel nicht.
→ Betrifft Nachrichten und Meinungsbeiträge, **nicht** den normalen Werbe- oder Produkttext.

**4. KI-Interaktion erkennbar machen**
Wer einen Chatbot oder KI-Assistenten für andere bereitstellt, muss die Nutzer wissen lassen,
dass sie mit einer KI schreiben. → Kurzer Hinweis am Anfang des Chats.

*(Randfall: Emotions- oder Biometrie-Erkennungssysteme müssen die betroffenen Personen
informieren. Kommt selten vor — falls doch, darauf hinweisen und an einen Fachmann verweisen.)*

## 5. Der Punkt, der oft wichtiger ist als die Kennzeichnung: Irreführung

**Das hat mit der KI-Verordnung nichts zu tun und wird trotzdem häufiger zum Problem.**
Nach § 5 UWG ist irreführende Werbung unzulässig. Bei KI-Bildern auf Geschäftsseiten heißt das:

- Ein KI-erzeugtes „Team" oder „unser Büro", das es so nicht gibt
- Produktbilder, die etwas zeigen, das die Ware nicht leistet oder nicht so aussieht
- Erfundene Kunden, Referenzen oder Vorher-Nachher-Darstellungen

**Ein Hinweis „mit KI erstellt" heilt eine Irreführung nicht.** Wer über wesentliche
Eigenschaften täuscht, tut das auch mit Kennzeichnung. Immer wenn ein KI-Bild eine
geschäftliche Tatsache behauptet — Menschen, Räume, Produkte, Ergebnisse — diesen Punkt
ansprechen, nicht nur die Kennzeichnungsfrage.

Weiterer Randfall: Ähnelt eine erzeugte Person einer echten Person, kommen
Persönlichkeitsrechte ins Spiel. Dann an einen Fachmann verweisen.

## 6. Nutzungsrechte am Werkzeug prüfen (ebenfalls außerhalb der KI-Verordnung)

Ob die erzeugten Bilder überhaupt kommerziell genutzt werden dürfen, steht **nicht im Gesetz,
sondern im Vertrag mit dem Anbieter** — abhängig von Tarif und Nutzungsbedingungen. Bei
kommerzieller Verwendung immer daran erinnern, das nachzulesen. Nichts dazu behaupten, was
nicht in den Bedingungen des konkreten Anbieters steht.

## Fertige Kennzeichnungs-Bausteine (kopierfertig)
- **Bild/Video allgemein:** „Mit Künstlicher Intelligenz erstellt." · Hashtag `#KIgeneriert`
- **Deepfake / veränderte Person oder Szene:** „Künstlich erzeugte bzw. veränderte
  Darstellung." (deutlich sichtbar, nicht versteckt in einer Hashtag-Wand)
- **Teil-KI (z. B. KI-Retusche):** „Bild teils mit KI bearbeitet."
- **Chatbot:** „Hinweis: Hier antwortet ein KI-Assistent."

Wähle den passenden Baustein zum Inhalt und füge ihn sichtbar bei — nicht kleingedruckt.

**Aber erst prüfen, ob überhaupt einer nötig ist.** Ein abstraktes KI-Bild ohne echt
wirkende Personen oder Szenen braucht nach Artikel 50 keinen Hinweis vom Verwender. Eine
freiwillige Kennzeichnung ist erlaubt und oft sympathisch — sie als Pflicht darzustellen,
wäre falsch.

## Aktualität ehrlich behandeln
- Nenne beim Hinweis immer das **Rechtsstand-Datum** und sag dazu, dass sich die Rechtslage
  ändern kann.
- **Wenn** der ausführende Agent Internetzugang hat: kurz gegenprüfen, ob sich seit dem
  Rechtsstand-Datum an Artikel 50 etwas geändert oder verschärft hat, und den Nutzer auf
  Unsicherheiten hinweisen. **Niemals** ein Ergebnis erfinden und **niemals** daraus ein
  Urteil machen — nur „bitte aktuelle Fassung prüfen / anwaltlich absichern".
- Ohne Internetzugang: klar sagen, dass dies der Stand vom genannten Datum ist.

## Grenzen (wichtig)
- **Keine Rechtsberatung.** Dieser Skill erinnert an bekannte Pflichten, er beurteilt keinen
  Einzelfall. Bei Zweifelsfällen, Bußgeldrisiko oder Sonderfällen an einen Anwalt/Fachmann verweisen.
- **Kein „verboten / erlaubt".** Ton bleibt Hinweis: „hier greift wahrscheinlich …".
- Plattform-eigene KI-Kennzeichnung (z. B. das KI-Feld beim Hochladen) kann helfen, **ersetzt
  aber nicht** die eigene Prüfung — darauf hinweisen, nicht darauf verlassen.
- Nichts erfinden: keine Paragraphen, Fristen oder Bußgeldhöhen behaupten, die nicht gesichert sind.

## Format der Antwort
Kurze Erinnerung, welche Pflicht hier greift — und ausdrücklich auch, wenn **keine** greift, dazu der passende kopierfertige
Kennzeichnungs-Baustein und das Rechtsstand-Datum. Getroffene Annahmen in einem Satz nennen.
Kein Rechts-Vortrag — knapp, praktisch, zum sofort Anwenden.
