#!/usr/bin/env bash
# Hält Lorenz' Kopie der App auf Rolis Stand — automatisch, alle 15 Minuten.
#
# Lorenz' Instanz ist ein SPIEGEL: Eigene Änderungen an seiner Kopie werden
# bewusst überschrieben (reset --hard). Entwickelt wird nur in Rolis Repo;
# Lorenz bekommt fertige Stände.
#
# Läuft als root (systemd-Dienst lorenz-aktualisieren.service), weil niemand
# sonst beide Heimatordner lesen darf — die Konten sind gegenseitig dicht,
# und das soll so bleiben.
set -euo pipefail

QUELLE=/home/roli/projekte/Hetzner-App
ZIEL=/home/lorenz/Hetzner-App

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
# Was git als root angefasst hat, gehört danach wieder Lorenz.
chown -R lorenz:lorenz "$ZIEL"

# Neue Abhängigkeiten nachziehen — aber nur, wenn sich die Liste geändert hat.
if ! git -C "$ZIEL" diff --quiet "$alt" "$neu" -- requirements.txt; then
  runuser -u lorenz -- "$ZIEL/.venv/bin/pip" install --quiet -r "$ZIEL/requirements.txt"
fi

# Den Dienst nur anfassen, wenn sich der Server-Code geändert hat. Die
# Oberfläche (web/) liest der Dienst bei jedem Aufruf frisch von der Platte —
# dafür reicht Neuladen im Browser, kein Neustart nötig. Dank KillMode=process
# überleben Lorenz' Claude-Sitzungen den Neustart ohnehin.
if ! git -C "$ZIEL" diff --quiet "$alt" "$neu" -- hetzner_app requirements.txt; then
  systemctl restart hetzner-app-lorenz
  echo "Aktualisiert und Dienst neu gestartet: ${alt:0:7} → ${neu:0:7}"
else
  echo "Aktualisiert (nur Oberfläche/Sonstiges): ${alt:0:7} → ${neu:0:7}"
fi
