# QSL73 -- Copyright (C) 2026 DF1DS (kainomatic) -- SPDX-License-Identifier: GPL-3.0-or-later
# Build-Hilfsskript: PyInstaller + HTML-Infodateien + Inno Setup in einem Schritt
param([switch]$SkipPyInstaller, [switch]$Beta)

if (-not $SkipPyInstaller) {
    python tools/make_icon.py
    python -m PyInstaller qsl73.spec
}

# HTML-Infodateien erzeugen (LIESMICH.html + AENDERUNGEN.html nach installer/docs/)
# Benoetigt: pip install markdown  (oder: pip install -r requirements-dev.txt)
Write-Host "Erzeuge HTML-Infodateien ..."
pip install markdown --quiet
python tools/make_docs_html.py
if ($LASTEXITCODE -ne 0) {
    Write-Error "HTML-Erzeugung fehlgeschlagen (Exit $LASTEXITCODE)"
    exit $LASTEXITCODE
}

# ISCC.exe suchen: System-Installation oder per-User-Installation (winget)
$IsccPaths = @(
    "C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
    "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe"
)
$Iscc = $IsccPaths | Where-Object { Test-Path $_ } | Select-Object -First 1

if (-not $Iscc) {
    Write-Error "ISCC.exe nicht gefunden. Inno Setup 6 installieren: https://jrsoftware.org/isdl.php"
    exit 1
}

if ($Beta) {
    & $Iscc installer\qsl73-beta.iss
    Write-Host "Installer fertig: installer\Output\QSL73-Beta-Setup.exe"
} else {
    & $Iscc installer\qsl73.iss
    Write-Host "Installer fertig: installer\Output\QSL73-Setup.exe"
}
