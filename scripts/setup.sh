#!/usr/bin/env bash
# Richtet die App auf einem frischen Hetzner-Server ein.
#
#   ./scripts/setup.sh hetzner.deine-domain.de
#
# Danach läuft der Dienst, ist über HTTPS erreichbar und startet nach einem
# Neustart von selbst wieder.
set -euo pipefail

DOMAIN="${1:-}"
if [ -z "$DOMAIN" ]; then
  echo "Bitte die Domain angeben:  ./scripts/setup.sh hetzner.deine-domain.de" >&2
  exit 1
fi

HIER="$(cd "$(dirname "$0")/.." && pwd)"
KONFIG="${HOME}/.hetzner-app"

echo "→ Pakete installieren …"
sudo apt-get update -qq
sudo apt-get install -y -qq python3-venv tmux curl debian-keyring debian-archive-keyring apt-transport-https

echo "→ Python-Umgebung anlegen …"
python3 -m venv "${HIER}/.venv"
"${HIER}/.venv/bin/pip" install --quiet --upgrade pip
"${HIER}/.venv/bin/pip" install --quiet fastapi "uvicorn[standard]" websockets

echo "→ Sprachausgabe einrichten …"
(cd "$HIER" && ./scripts/install-piper.sh)

echo "→ Zugangswort erzeugen …"
mkdir -p "$KONFIG"
if [ ! -f "${KONFIG}/umgebung" ]; then
  ZUGANG="$(openssl rand -hex 24)"
  printf 'HETZNER_APP_TOKEN=%s\n' "$ZUGANG" > "${KONFIG}/umgebung"
  chmod 600 "${KONFIG}/umgebung"
  echo
  echo "   ┌──────────────────────────────────────────────────────────────┐"
  echo "   │  Dein Zugangswort — jetzt notieren, es wird nicht wieder     │"
  echo "   │  angezeigt:                                                  │"
  echo "   │                                                              │"
  printf  "   │  %-60s│\n" "$ZUGANG"
  echo "   └──────────────────────────────────────────────────────────────┘"
  echo
else
  echo "   Es gibt schon eins in ${KONFIG}/umgebung — bleibt unverändert."
fi

echo "→ Caddy installieren (besorgt das HTTPS-Zertifikat) …"
if ! command -v caddy >/dev/null; then
  curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' \
    | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
  curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' \
    | sudo tee /etc/apt/sources.list.d/caddy-stable.list >/dev/null
  sudo apt-get update -qq
  sudo apt-get install -y -qq caddy
fi

echo "→ Caddy auf ${DOMAIN} einstellen …"
sudo sed "s/hetzner\.deine-domain\.de/${DOMAIN}/" "${HIER}/deploy/Caddyfile" \
  | sudo tee /etc/caddy/Caddyfile >/dev/null
sudo systemctl reload caddy || sudo systemctl restart caddy

echo "→ Dienst einrichten …"
sudo sed "s|%i|${USER}|g; s|/home/${USER}/Hetzner-App|${HIER}|g" \
  "${HIER}/deploy/hetzner-app.service" \
  | sudo tee /etc/systemd/system/hetzner-app.service >/dev/null
sudo systemctl daemon-reload
sudo systemctl enable --now hetzner-app

echo
echo "✓ Fertig."
echo
echo "  Öffne am Handy im Chrome:  https://${DOMAIN}"
echo "  Melde dich mit dem Zugangswort an."
echo "  Dann im Chrome-Menü: »Zum Startbildschirm hinzufügen«."
