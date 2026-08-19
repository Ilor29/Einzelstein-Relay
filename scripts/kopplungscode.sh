#!/usr/bin/env bash
# Zeigt einen frischen Kopplungscode an — zum Freischalten eines Geräts am Handy.
#
#   ./scripts/kopplungscode.sh
#
# Der Code ist 15 Minuten gültig und einmalig. Er ersetzt den vorherigen; es
# gibt immer nur einen gültigen Code. Gedacht für den Fall, dass der beim
# Einrichten angezeigte Code abgelaufen ist — oder man ein weiteres Gerät
# hinzufügen will und gerade kein schon freigeschaltetes zur Hand hat.
set -euo pipefail

HIER="$(cd "$(dirname "$0")/.." && pwd)"

CODE="$(cd "$HIER" && ./.venv/bin/python -c 'from hetzner_app import geraete; print(geraete.kopplung_neu())')"

echo
echo "  Kopplungscode (15 Minuten gültig):"
echo
echo "         ${CODE}"
echo
echo "  Gib ihn am Handy in der App ein."
