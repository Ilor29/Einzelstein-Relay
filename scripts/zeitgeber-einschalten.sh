#!/usr/bin/env bash
# Schaltet die automatische Sicherung ein.
#
# Ab dann sichert der Server alle zehn Minuten von selbst, was Claude Code an
# den Projekten geändert hat — und dein Windows-Rechner holt es sich beim
# Hochfahren ab.
#
# Wieder abschalten kannst du das jederzeit mit:
#   sudo systemctl disable --now auto-sichern.timer
set -euo pipefail

HIER="$(cd "$(dirname "$0")/.." && pwd)"

echo "→ Dienst und Zeitgeber einrichten …"
sudo sed "s|%i|${USER}|g; s|/home/${USER}/Hetzner-App|${HIER}|g" \
  "${HIER}/deploy/auto-sichern.service" \
  | sudo tee /etc/systemd/system/auto-sichern.service >/dev/null

sudo cp "${HIER}/deploy/auto-sichern.timer" /etc/systemd/system/auto-sichern.timer

sudo systemctl daemon-reload
sudo systemctl enable --now auto-sichern.timer

echo
echo "→ Ein Probelauf, damit wir sehen, dass es tut:"
sudo systemctl start auto-sichern.service
sleep 2
journalctl -u auto-sichern.service -n 20 --no-pager -o cat | sed 's|^|   |'

echo
echo "✓ Eingeschaltet."
echo "  Zustand:       $(systemctl is-active auto-sichern.timer)"
systemctl list-timers auto-sichern.timer --no-pager | sed -n '2p' | awk '{print "  Nächster Lauf: " $1, $2, $3}'
