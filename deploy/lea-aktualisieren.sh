#!/usr/bin/env bash
# Hält Leas Kopie der App auf Rolis Stand — automatisch, alle 15 Minuten.
# Baugleich mit lorenz-aktualisieren.sh, nur für das Konto »lea«.
#
# Leas Instanz ist ein SPIEGEL: Eigene Änderungen an ihrer Kopie werden
# bewusst überschrieben (reset --hard). Entwickelt wird nur in Rolis Repo;
# Lea bekommt fertige Stände.
#
# Läuft als root (systemd-Dienst lea-aktualisieren.service), weil niemand
# sonst beide Heimatordner lesen darf — die Konten sind gegenseitig dicht,
# und das soll so bleiben.
set -euo pipefail

QUELLE=/home/roli/projekte/Hetzner-App
ZIEL=/home/lea/Hetzner-App

# Git misstraut als root Repos, die anderen gehören ("dubious ownership") —
# die Ausnahme wandert als -c direkt in jeden Aufruf, statt in eine
# Konfigurationsdatei, die der systemd-Dienst (ohne HOME) gar nicht fände.
git() { command git -c safe.directory="$QUELLE" -c safe.directory="$ZIEL" "$@"; }

neu=$(git -C "$QUELLE" rev-parse HEAD)
alt=$(git -C "$ZIEL" rev-parse HEAD)
if [ "$neu" = "$alt" ]; then
  exit 0                      # nichts Neues — leise wieder gehen
fi

git -C "$ZIEL" fetch --quiet origin
git -C "$ZIEL" reset --hard --quiet "$neu"
# Was git als root angefasst hat, gehört danach wieder Lea.
chown -R lea:lea "$ZIEL"

# Neue Abhängigkeiten nachziehen — aber nur, wenn sich die Liste geändert hat.
if ! git -C "$ZIEL" diff --quiet "$alt" "$neu" -- requirements.txt; then
  runuser -u lea -- "$ZIEL/.venv/bin/pip" install --quiet -r "$ZIEL/requirements.txt"
fi

# Den Dienst nur anfassen, wenn sich der Server-Code geändert hat. Die
# Oberfläche (web/) liest der Dienst bei jedem Aufruf frisch von der Platte —
# dafür reicht Neuladen im Browser, kein Neustart nötig. Dank KillMode=process
# überleben Leas Claude-Sitzungen den Neustart ohnehin.
if ! git -C "$ZIEL" diff --quiet "$alt" "$neu" -- hetzner_app requirements.txt; then
  systemctl restart hetzner-app-lea
  echo "Aktualisiert und Dienst neu gestartet: ${alt:0:7} → ${neu:0:7}"
else
  echo "Aktualisiert (nur Oberfläche/Sonstiges): ${alt:0:7} → ${neu:0:7}"
fi
