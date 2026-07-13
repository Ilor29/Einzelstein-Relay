# Holt auf dem Windows-Rechner alles ab, was auf dem Hetzner entstanden ist.
#
# Einmalig einrichten:
#   1. Diese Datei nach D:\Virtual Code\abgleich.ps1 legen.
#   2. Unten SERVER und BENUTZER eintragen.
#   3. In der Aufgabenplanung eine Aufgabe "Bei Anmeldung" anlegen mit:
#        powershell.exe -ExecutionPolicy Bypass -File "D:\Virtual Code\abgleich.ps1"
#
# Danach ist dein Rechner beim Hochfahren automatisch auf dem Stand, den du
# unterwegs am Handy erarbeitet hast.

$SERVER   = "hetzner.deine-domain.de"   # <- eintragen
$BENUTZER = "roli"                      # <- eintragen
$WURZEL   = "D:\Virtual Code"

Write-Host "Gleiche mit dem Hetzner ab …" -ForegroundColor Cyan

# Alle Lager auf dem Server auflisten.
$projekte = ssh "$BENUTZER@$SERVER" "ls -1 ~/git 2>/dev/null | sed 's/\.git$//'"

if (-not $projekte) {
    Write-Host "Keine Lager auf dem Server gefunden. Läuft dort schon lager-einrichten.sh?" -ForegroundColor Yellow
    exit 1
}

foreach ($projekt in $projekte) {
    $projekt = $projekt.Trim()
    if (-not $projekt) { continue }

    $ordner = Join-Path $WURZEL $projekt

    if (Test-Path (Join-Path $ordner ".git")) {
        # Schon da — nur den neuen Stand holen.
        Push-Location $ordner

        # Erst nachsehen, ob hier ungesicherte Änderungen liegen. Die würden
        # wir sonst überfahren, und das wäre schlimmer als kein Abgleich.
        $offen = git status --porcelain
        if ($offen) {
            Write-Host "  ! $projekt hat ungesicherte Änderungen — übersprungen." -ForegroundColor Yellow
            Write-Host "    Sichere sie erst, dann läuft der Abgleich wieder." -ForegroundColor DarkGray
            Pop-Location
            continue
        }

        git pull --quiet --ff-only hetzner 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  ✓ $projekt aktualisiert." -ForegroundColor Green
        } else {
            Write-Host "  ! $projekt: Abgleich hakt, bitte von Hand ansehen." -ForegroundColor Yellow
        }
        Pop-Location
    }
    else {
        # Noch nicht da — einmal komplett holen.
        git clone --quiet "${BENUTZER}@${SERVER}:git/${projekt}.git" $ordner
        Push-Location $ordner
        git remote rename origin hetzner
        Pop-Location
        Write-Host "  + $projekt neu geholt." -ForegroundColor Green
    }
}

Write-Host "Fertig." -ForegroundColor Cyan
