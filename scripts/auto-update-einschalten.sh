#!/usr/bin/env bash
# Schaltet die automatische Aktualisierung EIN — für einen Community-Server.
#
# Ab dann holt sich dieser Server alle 15 Minuten von selbst die neueste Fassung
# der App aus dem gemeinsamen Lager (origin) und startet den Dienst neu, wenn
# nötig. Niemand muss etwas herunterladen.
#
# NICHT auf dem Entwickler-Server ausführen: Dort wird gearbeitet, und das
# automatische Zurücksetzen (git reset --hard) würde nicht committete Arbeit
# überschreiben. Darum ist das bewusst ein eigener, ausdrücklicher Schritt und
# NICHT Teil von setup.sh.
#
# Wieder abschalten jederzeit:
#   sudo systemctl disable --now selbst-aktualisieren.timer
set -euo pipefail

HIER="$(cd "$(dirname "$0")/.." && pwd)"

# Sicherung gegen den Entwickler-Server: Dort zeigt origin auf das Entwickler-
# Repo. Wer hier aus Versehen landet, soll sich nicht die Arbeit überschreiben.
if git -C "$HIER" remote get-url origin >/dev/null 2>&1; then
  URL="$(git -C "$HIER" remote get-url origin)"
else
  echo "Dieser Ordner hat kein 'origin'-Lager — von dort käme aber das Update." >&2
  echo "Erst das gemeinsame Lager als origin einrichten, dann erneut versuchen." >&2
  exit 1
fi
echo "→ Updates kommen aus:  ${URL}"
# --ohne-rueckfrage: für die automatische Einrichtung (Cloud-Init) — dort gibt
# es keine Tastatur, und ein frisch geklonter Server zeigt mit origin ohnehin
# aufs gemeinsame Lager. Von Hand aufgerufen bleibt die Rückfrage: Sie schützt
# davor, das Zurücksetzen versehentlich auf einem Arbeits-Server einzuschalten.
if [ "${1:-}" != "--ohne-rueckfrage" ]; then
  read -r -p "  Ist das das gemeinsame Community-Lager? (j/N) " ANTWORT || ANTWORT=""
  case "$ANTWORT" in
    j|J|ja|Ja|y|Y) ;;
    *) echo "Abgebrochen — nichts geändert."; exit 0 ;;
  esac
fi

echo "→ Aktualisierungs-Skript nach /usr/local/sbin legen (root-eigen) …"
sudo install -o root -g root -m 755 \
  "${HIER}/deploy/selbst-aktualisieren.sh" /usr/local/sbin/hz-selbst-aktualisieren.sh

echo "→ Dienst und Zeitgeber einrichten …"
sudo sed "s|__APPDIR__|${HIER}|g" "${HIER}/deploy/selbst-aktualisieren.service" \
  | sudo tee /etc/systemd/system/selbst-aktualisieren.service >/dev/null
sudo cp "${HIER}/deploy/selbst-aktualisieren.timer" /etc/systemd/system/selbst-aktualisieren.timer

sudo systemctl daemon-reload
sudo systemctl enable --now selbst-aktualisieren.timer

echo
echo "✓ Automatische Aktualisierung ist an. Dieser Server holt sich Neues alle"
echo "  15 Minuten von selbst. Ausschalten: sudo systemctl disable --now selbst-aktualisieren.timer"
