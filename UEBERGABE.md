# Übergabe Hetzner-App (Relay), 18.10.2026 17:50

## Stand
Relay V188 ist ausgerollt und läuft (Commit de606bd, auf GitHub). Die Büroklammer nimmt
Android-Apps an (.apk, .apks, .xapk). Die Endung bleibt erhalten, aber nur, wenn innen ein ZIP
steckt. ZIP-Anhänge dürfen bis 200 MB, alles andere bleibt bei 30 MB. Die Grenze im Caddy und
in der App-eigenen Middleware gilt für /api/sessions/*/datei jetzt bis 210 MB, sonst weiter
35 MB, und zwar für Roli, Lorenz und Lea. Sicherung: /etc/caddy/Caddyfile.vor-apk-2026-10-18.
Baubuch (Eintrag 18.10.2026, V188) und Brain-Register sind nachgetragen.

## Nachtrag 18:55
Relay V189 (Commit 545bc1b): Eigene Schnellbefehle im Blatt „Eigene Schnellbefehle“ am Griff
ziehen, die Leiste übernimmt die Reihenfolge (Roli 18:32 „schnellwahl knöpfe verschiebbar“, „6. Ja“).
Offen: Roli probiert es am Handy. Das Blatt rollt beim Ziehen nicht von selbst mit.

## Geprüft
Testserver 8799 mit Rolis echter App aus Zerlegen und einer 120-MB-App angenommen; falsche
APK, 40-MB-PDF und 205-MB-ZIP abgelehnt. Playwright im Profil Pixel 7: Anhang-Kärtchen
erscheint, keine Konsolenfehler. Von außen: Anhang-Weg mit 120 MB kommt bis zur Anmeldung (401),
andere Wege mit 40 MB werden gesperrt (413).

## Offen
- Aufgabe 5 an Roli: am Handy eine echte App über Büroklammer und Dateien schicken und sagen,
  ob sie in der Auswahl erscheint und ankommt. Noch keine Antwort.
- Ungeprüft sind große Uploads übers Mobilnetz.
- Die Karte Zerlegen lief nicht und hat keine Nachricht bekommen. Ihr bei Gelegenheit sagen,
  dass .apk jetzt direkt geht (kein Umbenennen in .zip mehr).
- ANREGUNG-APK-ANHANG-2026-10-18.md liegt noch im Ordner. Sie ist erledigt, wird aber nur auf
  Rolis Wort gelöscht.

## Nächster Schritt
Rolis Rückmeldung zu Aufgabe 5 abwarten. Kommt die App nicht an, ins Protokoll von
hetzner-app.service schauen, ob ein POST auf /datei ankam und mit welchem Status.

## Beschlüsse
- Roli 18.10. 14:30 „57. Ja“: Die Büroklammer soll APK-Dateien annehmen.
- Roli 18.10. 17:27 „1. Deine Empfehlung, 2. Deine Empfehlung“: Die Karte bleibt im
  Hetzner-App-Ordner und baut die APK-Anregung.

## Rolis letzter Wortlaut
„Auftrag: Die Büroklammer der Relay soll APK-Dateien annehmen … 4. Mit einer echten APK am
Handy-Profil im Browser prüfen. 5. Baubuch, Register, committen. … Ausführbar wird nichts,
die Datei liegt nur im Ordner.“

## Merkhilfe für Tests
Testsitzungen müssen auf dem tmux-Kanal hz mit dem Präfix hz- liegen. Im Testserver
app.router.on_startup.clear() setzen, sonst starten Melde-Wächter und Piper mit.
