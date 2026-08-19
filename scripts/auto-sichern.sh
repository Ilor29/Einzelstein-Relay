#!/usr/bin/env bash
# Sichert auf dem Hetzner automatisch, was Claude Code dort geändert hat.
#
# Läuft alle paar Minuten und schiebt jede Änderung ins Lager auf dem Server UND
# außer Haus zu GitHub. Damit ist das, was du unterwegs auf dem Handy machst,
# sofort auch für deinen Rechner da — er holt es sich von GitHub — ohne dass du
# an etwas denken musst.
#
# GitHub ist das Bindeglied: Server → GitHub → dein Laptop. Der Lager-Schritt
# ist nur die schnelle Kopie auf demselben Server; die ECHTE Sicherung ist die
# bei GitHub, weil sie den Server überlebt.
#
# Einrichten als Zeitgeber (siehe deploy/auto-sichern.timer).
set -uo pipefail

ARBEIT="${HOME}/projekte"
LAGER="${HOME}/git"

# Gegen die stille Sicherungs-Panne: Scheitert der GitHub-Push eines Projekts
# mehrere Läufe in Folge (kein Netz oder Stand divergiert), gibt es EINE
# Push-Nachricht aufs Handy — statt wie am 11.08. eine Woche lang unbemerkt zu
# klemmen. Der Zähler je Projekt liegt außerhalb von ~/projekte (kein Git).
FEHLER_DIR="${HOME}/.hetzner-app/sicherung-fehler"
FEHLER_SCHWELLE=3
HIER="$(cd "$(dirname "$0")/.." && pwd)"

# Eine Warnung aufs Handy schicken — über das App-Modul. Darf den Lauf nie stören.
push_warnen() {
  ( cd "$HIER" && "${HIER}/.venv/bin/python" -c \
      "import sys; from hetzner_app import melden; melden.schicken(sys.argv[1], sys.argv[2])" \
      "$1" "$2" ) >/dev/null 2>&1 || true
}

# Wer als Urheber in der Historie steht. Das Skript bringt seine Identität
# selbst mit, statt sich auf eine globale Git-Einstellung zu verlassen — auf
# einem frisch aufgesetzten Server gibt es die nämlich nicht, und dann würde
# hier gar nichts gesichert, ohne dass es jemandem auffällt.
ALS=(-c "user.name=Hetzner-App" -c "user.email=hetzner-app@localhost")

# Ordner außerhalb von ~/projekte, die trotzdem mitgesichert werden.
#
# Sie liegen bewusst nicht bei den Projekten, weil dort Geheimnisse stehen, die
# niemals zu GitHub dürfen. Das heißt aber nicht, dass ihr Code ungesichert sein
# soll: Was mitgeht und was nicht, entscheidet die `.gitignore` im jeweiligen
# Ordner — und die muss dort sitzen, bevor er hier hereinkommt.
#
# Jarvis stand bis zum 11.08.2026 ganz ohne Git da. Der Verweis
# ~/projekte/Jarvis wird unten übersprungen, und die "eigene Sitzung", die sich
# angeblich darum kümmert, hat nie gesichert — bei einem Serverausfall wäre
# alles weg gewesen.
EXTRA=("${HOME}/jarvis-voice")

sichere() {
  local arbeit="$1"
  local projekt zweig hier drueben

  arbeit="${arbeit%/}/"
  projekt="$(basename "$arbeit")"

  [ -d "${arbeit}.git" ] || return 0

  # Offene Änderungen festschreiben. Wer hat's geändert, steht in der Nachricht.
  if [ -n "$(git -C "$arbeit" status --porcelain)" ]; then
    git -C "$arbeit" add -A
    git -C "$arbeit" "${ALS[@]}" commit --quiet \
      -m "Automatisch gesichert vom Server ($(date '+%d.%m.%Y %H:%M'))" || return 0
  fi

  # Lager fehlt noch? Dann anlegen und verbinden.
  if ! git -C "$arbeit" remote get-url hetzner >/dev/null 2>&1; then
    mkdir -p "$LAGER"
    git init --bare --quiet "${LAGER}/${projekt}.git"
    git -C "$arbeit" remote add hetzner "${LAGER}/${projekt}.git"
  fi

  # Erst ins Lager auf dem Server (schnell, immer erreichbar).
  if git -C "$arbeit" push --quiet hetzner HEAD 2>/dev/null; then
    echo "✓ ${projekt} ins Lager."
  else
    echo "✗ ${projekt}: Lager fehlgeschlagen." >&2
  fi

  # Dann außer Haus zu GitHub — aber nur, wenn angebunden UND dort nicht schon
  # der gleiche Stand liegt (spart unnötige Netz-Zugriffe bei jedem Lauf).
  if git -C "$arbeit" remote get-url github >/dev/null 2>&1; then
    zweig="$(git -C "$arbeit" rev-parse --abbrev-ref HEAD 2>/dev/null)"
    hier="$(git -C "$arbeit" rev-parse HEAD 2>/dev/null)"
    drueben="$(git -C "$arbeit" rev-parse "github/${zweig}" 2>/dev/null || echo none)"
    local zaehler="${FEHLER_DIR}/${projekt}"
    if [ "$hier" != "$drueben" ]; then
      # Scheitert der Push (kein Netz, oder der GitHub-Stand ist auseinander-
      # gelaufen), bleibt der Lager-Stand trotzdem — daran lassen wir das
      # Sichern nicht scheitern. Nie mit Gewalt (--force): das zerstörte Arbeit.
      if git -C "$arbeit" push --quiet github HEAD 2>/dev/null; then
        echo "  → auch zu GitHub gesichert."
        rm -f "$zaehler"                     # Fehlschlag-Serie beendet
      else
        mkdir -p "$FEHLER_DIR"
        local n=$(( $(cat "$zaehler" 2>/dev/null || echo 0) + 1 ))
        echo "$n" > "$zaehler"
        echo "  → GitHub übersprungen (${n}. Lauf; kein Netz oder Stand divergiert)." >&2
        # Genau EINMAL warnen, wenn die Schwelle erreicht ist — nicht bei jedem Lauf.
        if [ "$n" -eq "$FEHLER_SCHWELLE" ]; then
          push_warnen "Sicherung außer Haus klemmt" \
            "Das Projekt ${projekt} wird seit mehreren Läufen nicht mehr zu GitHub gesichert. Bitte nachsehen — kein Netz oder der Stand ist auseinandergelaufen."
        fi
      fi
    else
      rm -f "$zaehler"                        # schon gleich → alles gut
    fi
  fi
}

for arbeit in "$ARBEIT"/*/; do
  # Verweise (Symlinks) überspringen. Sie zeigen auf Ordner, die anderswo "echt"
  # liegen — die stehen bei Bedarf oben in EXTRA und werden dort einmal
  # angefasst, nicht zweimal.
  [ -L "${arbeit%/}" ] && continue
  sichere "$arbeit"
done

for arbeit in "${EXTRA[@]}"; do
  [ -d "$arbeit" ] && sichere "$arbeit"
done
