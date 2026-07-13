#!/usr/bin/env bash
# Richtet auf dem Hetzner die Git-Lager ein — einmalig.
#
# Ein "Lager" (bare repository) ist ein Git-Verzeichnis ohne Arbeitskopie.
# Es ist der Treffpunkt: Der Server schiebt seinen Stand hinein, Windows-Rechner
# und Linux-VM holen ihn sich von dort. Nichts davon verlässt deinen Server.
#
# Auf dem Hetzner ausführen:
#   ./scripts/lager-einrichten.sh Hetzner-App Skillsradar KI-WIKI …
set -euo pipefail

LAGER="${HOME}/git"
ARBEIT="${HOME}/projekte"

if [ $# -eq 0 ]; then
  echo "Welche Projekte? Beispiel:" >&2
  echo "  ./scripts/lager-einrichten.sh Hetzner-App Skillsradar" >&2
  exit 1
fi

mkdir -p "$LAGER"

for projekt in "$@"; do
  ziel="${LAGER}/${projekt}.git"

  if [ -d "$ziel" ]; then
    echo "✓ ${projekt}: Lager gibt es schon."
  else
    git init --bare --quiet "$ziel"
    echo "✓ ${projekt}: Lager angelegt."
  fi

  # Wenn es hier schon eine Arbeitskopie gibt, gleich verbinden.
  arbeit="${ARBEIT}/${projekt}"
  if [ -d "$arbeit" ]; then
    if [ ! -d "${arbeit}/.git" ]; then
      git -C "$arbeit" init --quiet
      git -C "$arbeit" add -A
      # Identität mitbringen — auf einem frischen Server ist keine gesetzt.
      git -C "$arbeit" \
        -c "user.name=Hetzner-App" -c "user.email=hetzner-app@localhost" \
        commit --quiet -m "Erster Stand vom Server" || true
    fi
    git -C "$arbeit" remote remove hetzner 2>/dev/null || true
    git -C "$arbeit" remote add hetzner "$ziel"
    git -C "$arbeit" push --quiet --set-upstream hetzner HEAD 2>/dev/null || true
    echo "   → verbunden mit ${arbeit}"
  fi
done

echo
echo "Fertig. Auf deinen anderen Rechnern holst du dir die Projekte so:"
echo
for projekt in "$@"; do
  echo "  git clone ${USER}@<server>:git/${projekt}.git"
done
