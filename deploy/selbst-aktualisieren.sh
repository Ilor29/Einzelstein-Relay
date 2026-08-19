#!/usr/bin/env bash
# Hält DIESE Installation der App auf dem neuesten Stand — zieht die neueste
# Fassung aus dem gemeinsamen Lager (origin) und startet den Dienst neu, wenn
# sich der Server-Code geändert hat. Für Community-Installationen: der eigene
# Server holt sich Verbesserungen von selbst, ohne dass jemand etwas tun muss.
#
# WICHTIG (Sicherheit): Läuft als root (der Dienst muss neu gestartet werden).
# Darf deshalb NICHT im nutzer-schreibbaren Projektordner liegen, sonst wäre es
# eine Leiter zum Administrator (siehe CODE//GUARD). Es wird nach
# /usr/local/sbin/ installiert (root:root, 755) — das erledigt
# scripts/auto-update-einschalten.sh.
#
# WICHTIG (Entwickler): NICHT auf dem Entwickler-Server aktivieren. Dort wird
# gearbeitet, und `git reset --hard` würde die laufende, nicht committete
# Arbeit überschreiben. Der Zeitgeber wird nur auf Community-Servern
# eingeschaltet.
set -euo pipefail

ZIEL="${HETZNER_APP_DIR:?HETZNER_APP_DIR nicht gesetzt}"
ZWEIG="${HETZNER_APP_ZWEIG:-main}"

[ -d "${ZIEL}/.git" ] || { echo "Kein Repo unter ${ZIEL} — nichts zu tun."; exit 0; }

# Wem der Ordner gehört — dahin geben wir alles zurück, was root angefasst hat.
BESITZER="$(stat -c %U "$ZIEL")"

# git misstraut als root fremden Repos ("dubious ownership") — Ausnahme direkt
# in jeden Aufruf, statt in eine Konfig, die der Dienst (ohne HOME) nicht fände.
git() { command git -c safe.directory="$ZIEL" "$@"; }

if ! git -C "$ZIEL" fetch --quiet origin "$ZWEIG"; then
  echo "Kein Netz zum Lager — später wieder."      # kein Fehler, nur kein Update
  exit 0
fi

alt="$(git -C "$ZIEL" rev-parse HEAD)"
neu="$(git -C "$ZIEL" rev-parse "origin/${ZWEIG}")"
if [ "$alt" = "$neu" ]; then
  exit 0                                            # nichts Neues — leise gehen
fi

git -C "$ZIEL" reset --hard --quiet "$neu"
# Was git als root angefasst hat, gehört danach wieder dem Benutzer.
chown -R "$BESITZER":"$BESITZER" "$ZIEL"

# Neue Abhängigkeiten nachziehen — nur, wenn sich die Liste geändert hat.
if ! git -C "$ZIEL" diff --quiet "$alt" "$neu" -- requirements.txt; then
  runuser -u "$BESITZER" -- "${ZIEL}/.venv/bin/pip" install --quiet -r "${ZIEL}/requirements.txt" || true
fi

# Den Dienst nur anfassen, wenn sich der Server-Code geändert hat. Die
# Oberfläche (web/) liest der Dienst bei jedem Aufruf frisch — dafür reicht
# Neuladen im Browser. Die Claude-Sitzungen leben in tmux, unabhängig vom
# Dienst, und überstehen den Neustart ohnehin.
if ! git -C "$ZIEL" diff --quiet "$alt" "$neu" -- hetzner_app requirements.txt; then
  systemctl restart hetzner-app
  echo "Aktualisiert und Dienst neu gestartet: ${alt:0:7} → ${neu:0:7}"
else
  echo "Aktualisiert (nur Oberfläche/Sonstiges): ${alt:0:7} → ${neu:0:7}"
fi
