#!/usr/bin/env bash
# Richtet die App auf einem frischen Server ein.
#
#   ./scripts/setup.sh hetzner.deine-domain.de
#
# Danach läuft der Dienst, ist über HTTPS erreichbar und startet nach einem
# Neustart von selbst wieder. Das Skript darf mehrfach laufen — was schon da
# ist, bleibt unangetastet.
#
# Für Käufer ist dies Stein 1 des Einrichtungs-Assistenten (siehe
# deploy/EINRICHTUNG-PLAN.md); die weiteren Stufen (Kopplungscode, Cloud-Init)
# bauen hierauf auf.
set -euo pipefail

DOMAIN="${1:-}"
if [ -z "$DOMAIN" ]; then
  # Keine Domain? Braucht auch niemand: sslip.io macht aus jeder Server-IP
  # eine echte Adresse (65.21.246.222 → 65-21-246-222.sslip.io), für die
  # Caddy ein ordentliches HTTPS-Zertifikat bekommt. Das funktioniert bei
  # jedem Anbieter — Hetzner, Hostinger, egal —, ganz ohne Domain-Kauf.
  echo "→ Keine Domain angegeben — die Adresse kommt aus der Server-IP …"
  IP="$(curl -4fsS --max-time 10 https://api.ipify.org || true)"
  case "$IP" in
    *[!0-9.]*|"")
      echo "Die eigene IP ließ sich nicht ermitteln. Entweder kurz später" >&2
      echo "nochmal versuchen oder die Adresse selbst angeben:" >&2
      echo "  ./scripts/setup.sh meine-adresse.de" >&2
      exit 1
      ;;
  esac
  DOMAIN="$(printf '%s' "$IP" | tr . -).sslip.io"
  echo "   Die App wird unter  https://${DOMAIN}  erreichbar sein."
fi

HIER="$(cd "$(dirname "$0")/.." && pwd)"
KONFIG="${HOME}/.hetzner-app"

echo "→ Pakete installieren …"
sudo apt-get update -qq
# git braucht die App selbst: neue Projekte werden als Git-Repo angelegt, und
# die automatische Sicherung committet damit.
sudo apt-get install -y -qq python3-venv tmux git curl debian-keyring debian-archive-keyring apt-transport-https

echo "→ Python-Umgebung anlegen …"
python3 -m venv "${HIER}/.venv"
"${HIER}/.venv/bin/pip" install --quiet --upgrade pip
"${HIER}/.venv/bin/pip" install --quiet -r "${HIER}/requirements.txt"

echo "→ Claude Code prüfen …"
if command -v claude >/dev/null || [ -x "${HOME}/.local/bin/claude" ]; then
  echo "   Claude Code ist schon da."
else
  # Der offizielle Installer — ohne Node-Gefrickel. Er legt claude nach
  # ~/.local/bin und trägt den Pfad in die Shell-Profile ein.
  #
  # </dev/null ist wichtig: Der Installer liest sonst die Standard-Eingabe
  # leer, und die E-Mail-Frage weiter unten bekommt nichts mehr — das Skript
  # brach dann mitten in der Einrichtung ab (gefunden beim Frischtest 14.08.).
  curl -fsSL https://claude.ai/install.sh | bash </dev/null
  echo "   Claude Code installiert. Die Anmeldung kommt später: In der ersten"
  echo "   Sitzung 'claude login' — den angezeigten Link am Handy öffnen."
fi

echo "→ Sprachausgabe einrichten …"
(cd "$HIER" && ./scripts/install-piper.sh)

echo "→ Server-weite Claude-Regeln hinterlegen …"
mkdir -p "${HOME}/.claude"
if [ -f "${HOME}/.claude/CLAUDE.md" ]; then
  echo "   ~/.claude/CLAUDE.md gibt es schon — bleibt unverändert."
else
  cp "${HIER}/deploy/claude-global.md" "${HOME}/.claude/CLAUDE.md"
  echo "   Arbeitsregeln nach ~/.claude/CLAUDE.md gelegt (gelten für alle Sitzungen)."
fi

echo "→ Brain anlegen (dein Überblick und erster Ansprechpartner) …"
BRAIN="${HOME}/projekte/Brain"
mkdir -p "$BRAIN"
for f in CLAUDE.md REGISTER.md; do
  # Bestehendes nie überschreiben — ein gewachsener Brain behält seine Landkarte.
  [ -f "${BRAIN}/${f}" ] || cp "${HIER}/deploy/brain-starter/${f}" "${BRAIN}/${f}"
done
[ -d "${BRAIN}/.git" ] || git init --quiet "$BRAIN"
echo "   Brain liegt unter ${BRAIN}. In der App öffnet ihn der Brain-Knopf oben."

# Kontaktadresse für die Push-Benachrichtigungen. Der Push-Dienst (Google,
# Mozilla) will wissen, wen er bei Missbrauch anschreibt — das muss der
# Betreiber DIESER Instanz sein, nicht der Entwickler.
mkdir -p "$KONFIG"
if [ ! -f "${KONFIG}/umgebung" ]; then
  : > "${KONFIG}/umgebung"
  chmod 600 "${KONFIG}/umgebung"
fi
if ! grep -q '^HETZNER_APP_KONTAKT=' "${KONFIG}/umgebung"; then
  echo
  printf "→ Deine E-Mail für die Push-Benachrichtigungen (nur der Push-Dienst sieht sie): "
  read -r KONTAKT
  if [ -n "$KONTAKT" ]; then
    printf 'HETZNER_APP_KONTAKT=%s\n' "$KONTAKT" >> "${KONFIG}/umgebung"
    echo "   Gespeichert."
  else
    echo "   Übersprungen — kannst du später in ${KONFIG}/umgebung nachtragen."
  fi
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

# Einen Kopplungscode erzeugen, damit das erste Handy sich SELBST freischalten
# kann — ohne den öffentlichen Schlüssel in die Kommandozeile zu tragen. Der
# Code ist 15 Minuten gültig und einmalig. (cd nach $HIER, damit das Modul
# hetzner_app gefunden wird.)
KOPPELCODE="$(cd "$HIER" && ./.venv/bin/python -c 'from hetzner_app import geraete; print(geraete.kopplung_neu())' 2>/dev/null || true)"

echo
echo "✓ Fertig."
echo
echo "  1. Öffne am Handy im Chrome:  https://${DOMAIN}"
if [ -n "$KOPPELCODE" ]; then
  echo "  2. Tippe in der App diesen Kopplungscode ein (15 Minuten gültig):"
  echo
  echo "         ${KOPPELCODE}"
  echo
  echo "     (Neuer Code, falls er abläuft:  ./scripts/kopplungscode.sh)"
else
  echo "  2. Schalte das Handy hier auf dem Server frei:"
  echo "       ./scripts/geraet-erlauben.sh handy <schlüssel-vom-handy>"
fi
echo "  3. Dann im Chrome-Menü: »Zum Startbildschirm hinzufügen«."
