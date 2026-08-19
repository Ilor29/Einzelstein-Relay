#!/usr/bin/env bash
# Richtet die Sprachausgabe ein: Piper und eine deutsche Stimme.
#
# Piper läuft auf dem Server, ohne Netz und ohne laufende Kosten. Die Stimme
# "Thorsten" ist die beste frei verfügbare deutsche — ruhig und gut verständlich.
set -euo pipefail

STIMMEN="${HOME}/.hetzner-app/stimmen"
NAME="de_DE-thorsten-medium"
QUELLE="https://huggingface.co/rhasspy/piper-voices/resolve/main/de/de_DE/thorsten/medium"

echo "→ Piper installieren …"
# Flask gehört dazu: Piper läuft bei uns als eigener HTTP-Dienst
# (piper.http_server), und der braucht es — ohne Flask startet er nicht.
#
# piper-tts FEST auf 1.4.2: Ab 1.6 hat Piper die Schnittstelle seines
# http_server geändert — er weist den POST-Aufruf der App dann mit HTTP 405 ab,
# und das Vorlesen bleibt stumm (genau das war bei Lorenz/Lea, 19.08.). 1.4.2
# ist die Fassung, mit der die App spricht. Bis tts.py auf die neue
# Piper-Schnittstelle umgestellt ist, bleibt die Version gepinnt.
if [ -x .venv/bin/pip ]; then
  .venv/bin/pip install --quiet "piper-tts==1.4.2" flask
else
  pip install --quiet "piper-tts==1.4.2" flask
fi

echo "→ Stimme »Thorsten« herunterladen …"
mkdir -p "$STIMMEN"
for datei in "${NAME}.onnx" "${NAME}.onnx.json"; do
  if [ -f "${STIMMEN}/${datei}" ]; then
    echo "   ${datei} ist schon da."
  else
    curl -fL --progress-bar -o "${STIMMEN}/${datei}" "${QUELLE}/${datei}"
  fi
done

echo
echo "✓ Fertig. Kurze Hörprobe:"
PIPER="$([ -x .venv/bin/piper ] && echo .venv/bin/piper || command -v piper)"
echo "Die Sprachausgabe ist eingerichtet und klingt so." \
  | "$PIPER" --model "${STIMMEN}/${NAME}.onnx" --output_file /tmp/hoerprobe.wav
echo "  → /tmp/hoerprobe.wav ($(du -h /tmp/hoerprobe.wav | cut -f1))"
