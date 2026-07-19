# Gleicht die Projekte auf dem Laptop mit GitHub ab — sicher und beidseitig.
#
# Für JEDES Projekt unter $WURZEL:
#   1. Offene Änderungen sichern (committen).
#   2. Den Stand von GitHub holen — aber nur, wenn er sich sauber davorsetzt
#      (--ff-only). Haben BEIDE Seiten etwas geändert, wird NICHTS überschrieben;
#      das Projekt wird gemeldet und übersprungen.
#   3. Hochladen zu GitHub — normales push, NIE mit Gewalt.
#
# Damit kann nichts verloren gehen: Wo GitHub schon weiter war, weigert git sich,
# und du siehst genau, welches Projekt du dir ansehen musst.
#
# Einmalig einrichten:
#   1. Diese Datei nach "D:\Virtual Code\abgleich-github.ps1" legen.
#   2. Unten $WURZEL prüfen (wo deine Projektordner liegen).
#   3. Aufrufen:
#        powershell.exe -ExecutionPolicy Bypass -File "D:\Virtual Code\abgleich-github.ps1"

$WURZEL = "D:\Virtual Code"   # <- wo die Projektordner liegen

# Wer als Urheber in der Historie steht, wenn das Skript etwas sichert.
$env:GIT_AUTHOR_NAME    = "Laptop"
$env:GIT_AUTHOR_EMAIL   = "laptop@localhost"
$env:GIT_COMMITTER_NAME  = "Laptop"
$env:GIT_COMMITTER_EMAIL = "laptop@localhost"

# Diese zwei haben ihren eigenen Knoten (zwei Fassungen) — bewusst außen vor,
# bis sie zusammengeführt sind.
$AUSGENOMMEN = @("FELDPULS_ONE", "KRUGMEISTER_WEBSITE", "FELDPULS-ONE", "Krugmeister-Website")

Write-Host "Gleiche mit GitHub ab ..." -ForegroundColor Cyan

Get-ChildItem -Path $WURZEL -Directory | ForEach-Object {
    $projekt = $_.Name
    $ordner  = $_.FullName

    if (-not (Test-Path (Join-Path $ordner ".git"))) { return }   # kein Git-Projekt
    if ($AUSGENOMMEN -contains $projekt) {
        Write-Host "  . $projekt uebersprungen (eigener Knoten, siehe Brain)." -ForegroundColor DarkGray
        return
    }

    Push-Location $ordner

    # Das Fernziel finden, das auf GitHub zeigt — egal ob es "github" oder
    # "origin" heisst. So funktioniert das Skript in jedem Projekt gleich.
    $fern = $null
    foreach ($r in (git remote)) {
        if ((git remote get-url $r) -match "github\.com") { $fern = $r; break }
    }
    if (-not $fern) {
        Write-Host "  . $projekt hat kein GitHub — uebersprungen." -ForegroundColor DarkGray
        Pop-Location; return
    }

    $zweig = (git rev-parse --abbrev-ref HEAD).Trim()

    # 1. Offene Aenderungen sichern.
    if (git status --porcelain) {
        git add -A
        git commit --quiet -m "Vom Laptop gesichert ($(Get-Date -Format 'dd.MM.yyyy HH:mm'))"
    }

    # 2. Stand von GitHub holen — nur sauber davorsetzen, nie mischen.
    git fetch --quiet $fern 2>$null
    $vorher = git rev-parse HEAD
    git merge --ff-only "$fern/$zweig" --quiet 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  ! $projekt : Server UND Laptop haben geaendert — bitte ansehen." -ForegroundColor Yellow
        Write-Host "    (Nichts wurde ueberschrieben. Zeig es dem Brain.)" -ForegroundColor DarkGray
        Pop-Location; return
    }

    # 3. Hochladen — normales push, nie mit Gewalt.
    git push --quiet $fern $zweig 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  + $projekt aktuell und hochgeladen." -ForegroundColor Green
    } else {
        Write-Host "  ! $projekt : Hochladen hakt — bitte ansehen." -ForegroundColor Yellow
    }

    Pop-Location
}

Write-Host "Fertig." -ForegroundColor Cyan
