#!/usr/bin/env bash
# Sichert auf dem Hetzner automatisch, was Claude Code dort geändert hat.
#
# Läuft alle paar Minuten und schiebt jede Änderung ins Lager. Damit ist das,
# was du unterwegs auf dem Handy machst, sofort auch für deinen Rechner da —
# ohne dass du daran denken musst.
#
# Einrichten als Zeitgeber (siehe deploy/auto-sichern.timer).
set -uo pipefail

ARBEIT="${HOME}/projekte"
LAGER="${HOME}/git"

# Wer als Urheber in der Historie steht. Das Skript bringt seine Identität
# selbst mit, statt sich auf eine globale Git-Einstellung zu verlassen — auf
# einem frisch aufgesetzten Server gibt es die nämlich nicht, und dann würde
# hier gar nichts gesichert, ohne dass es jemandem auffällt.
ALS=(-c "user.name=Hetzner-App" -c "user.email=hetzner-app@localhost")

for arbeit in "$ARBEIT"/*/; do
  projekt="$(basename "$arbeit")"
  [ -d "${arbeit}.git" ] || continue

  # Nichts zu tun?
  if [ -z "$(git -C "$arbeit" status --porcelain)" ]; then
    continue
  fi

  # Wer hat's geändert? Steht in der Nachricht, damit man später erkennt,
  # ob das eine Sitzung vom Handy war oder Handarbeit.
  git -C "$arbeit" add -A
  git -C "$arbeit" "${ALS[@]}" commit --quiet \
    -m "Automatisch gesichert vom Server ($(date '+%d.%m.%Y %H:%M'))" || continue

  # Lager fehlt noch? Dann anlegen und verbinden.
  if ! git -C "$arbeit" remote get-url hetzner >/dev/null 2>&1; then
    mkdir -p "$LAGER"
    git init --bare --quiet "${LAGER}/${projekt}.git"
    git -C "$arbeit" remote add hetzner "${LAGER}/${projekt}.git"
  fi

  if git -C "$arbeit" push --quiet hetzner HEAD 2>/dev/null; then
    echo "✓ ${projekt} gesichert."
  else
    echo "✗ ${projekt}: Sichern fehlgeschlagen." >&2
  fi
done
