#!/usr/bin/env bash
# Legt die mitgelieferten Skills (deploy/skills/*) in ~/.claude/skills und hält
# sie aktuell. Aufgerufen von setup.sh (Einrichtung) und vom Auto-Update.
#
# Mitgelieferte Skills gehören zum Paket wie die App selbst und werden darum bei
# jedem Lauf überschrieben (so kommen Verbesserungen an). EIGENE Skills des
# Nutzers — andere Namen — bleiben unangetastet.
set -euo pipefail

HIER="$(cd "$(dirname "$0")/.." && pwd)"
QUELLE="${HIER}/deploy/skills"
ZIEL="${HOME}/.claude/skills"

[ -d "$QUELLE" ] || exit 0
mkdir -p "$ZIEL"

for skill in "$QUELLE"/*/; do
  [ -d "$skill" ] || continue
  name="$(basename "$skill")"
  rm -rf "${ZIEL:?}/${name}"
  cp -r "$skill" "${ZIEL}/${name}"
  echo "   Skill eingerichtet: ${name}"
done
