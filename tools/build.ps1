# QSL73 — Build-Hilfsskript (PyInstaller)
# Copyright (C) 2026 DF1DS (kainomatic) — SPDX-License-Identifier: GPL-3.0-or-later
#
# Voraussetzungen:
#   - Virtuelle Umgebung aktiviert (.venv\Scripts\activate)
#   - pip install pyinstaller (NICHT in requirements.txt)
#
# Aufruf aus dem Repo-Root:
#   powershell -ExecutionPolicy Bypass -File tools/build.ps1

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Write-Host "=== QSL73 Build ===" -ForegroundColor Cyan

Write-Host "[1/2] Icon erzeugen ..." -ForegroundColor Yellow
python tools/make_icon.py
if (-not $?) { Write-Error "make_icon.py fehlgeschlagen"; exit 1 }

Write-Host "[2/2] PyInstaller-Bundle bauen ..." -ForegroundColor Yellow
python -m PyInstaller qsl73.spec
if (-not $?) { Write-Error "PyInstaller fehlgeschlagen"; exit 1 }

Write-Host ""
Write-Host "=== Build erfolgreich ===" -ForegroundColor Green
Write-Host "Ergebnis: dist\QSL73\QSL73.exe" -ForegroundColor Green
