#!/usr/bin/env bash
# Schaltet ein Gerät frei.
#
#   ./scripts/geraet-erlauben.sh handy MFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAE…
#
# Der Schlüssel ist der öffentliche Teil, den die App auf dem Gerät anzeigt.
# Er ist kein Geheimnis — er darf durch jeden Chat wandern.
#
# Bewusst gibt es keinen Weg, sich über das Netz selbst einzutragen: Die Tür
# öffnet nur, wer schon auf dem Server ist.
set -euo pipefail

if [ $# -ne 2 ]; then
  echo "Aufruf: $0 <name> <öffentlicher-schlüssel>" >&2
  exit 1
fi

HIER="$(cd "$(dirname "$0")/.." && pwd)"
"${HIER}/.venv/bin/python" - "$1" "$2" <<'EOF'
import sys
from hetzner_app import geraete

name, schluessel = sys.argv[1], sys.argv[2]
try:
    g = geraete.erlauben(name, schluessel)
except Exception as fehler:
    raise SystemExit(f"✗ Das ist kein brauchbarer Schlüssel: {fehler}")

print(f"✓ Gerät »{g.name}« freigeschaltet.")
print()
print("Freigeschaltete Geräte:")
for g in geraete.liste():
    print(f"  · {g.name}")
EOF
