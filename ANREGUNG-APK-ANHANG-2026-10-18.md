# Anregung aus der Karte Zerlegen: APK über die Büroklammer annehmen

Roli 18.10.2026 14:30 „57. Ja“ (Frage: Soll die Büroklammer der Relay künftig auch APK-Dateien anbieten?).

Befund vom 18.10.: Roli wollte eine App-Datei (.apk) vom Handy in die Karte Zerlegen schicken. Der erste Versuch kam nie am Server an
(im Protokoll von hetzner-app nur „senden“, kein POST auf /datei). Grund: Die Dateiauswahl in web/index.html (Zeile 584, accept=…)
nennt .apk nicht, Android bietet die Datei dann nicht an. Nach Umbenennen in .zip ging es: Der Server erkennt ZIP am Inhalt
(_endung_erraten, Kopf PK\x03\x04) und legte sie als .zip in .hetzner-dateien ab.

Vorschlag:
1. accept-Liste um .apk,.apks,.xapk ergänzen (alle drei sind ZIP-Archive).
2. Serverseitig nichts nötig, sie kommen als .zip an. Schöner wäre, .apk als Endung zu behalten, damit die Karte gleich weiß, was es ist.
3. Grenze MAX_DATEI 30 MB prüfen: Viele Apps sind 50 bis 150 MB groß. Für Zerlegen wären 200 MB gut, vielleicht nur für Dateien, die wirklich ZIP sind.
4. Lea und Lorenz bekommen die Änderung über die üblichen Aktualisierungs-Timer mit.

Ausführbar wird dabei nichts: Die Datei liegt nur im Ordner und wird auf dem Server höchstens gelesen.
