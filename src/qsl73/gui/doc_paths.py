# QSL73 — Copyright (C) 2026 DF1DS (kainomatic) — SPDX-License-Identifier: GPL-3.0-or-later
"""Laufzeitsichere Pfadauflösung für HTML-Infodateien (LIESMICH / AENDERUNGEN).

Tk-frei. Sucht nach HTML neben der .exe (installiert/Bundle) und gibt None zurück,
wenn die Datei nicht gefunden wird (Dev-Lauf ohne Build).
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

# Fallback-URLs wenn HTML nicht vorhanden (Dev-Lauf)
_FALLBACK_URLS: dict[str, str] = {
    "LIESMICH.html": "https://github.com/kainomatic/qsl73#readme",
    "AENDERUNGEN.html": "https://github.com/kainomatic/qsl73/releases",
}


def resolve_doc_html(filename: str) -> Optional[Path]:
    """Gibt den Pfad zur HTML-Infodatei zurück, oder None wenn nicht gefunden.

    Suchreihenfolge:
    1. Verzeichnis der ausführbaren Datei (sys.executable) — gilt für installierte
       App und PyInstaller-Bundle (HTML liegen per [Files] neben QSL73.exe).
    2. Nicht gefunden → None (Dev-Lauf ohne Build).
    """
    exe_dir = Path(sys.executable).parent
    candidate = exe_dir / filename
    return candidate if candidate.exists() else None


def get_fallback_url(filename: str) -> Optional[str]:
    """Fallback-URL für den Fall, dass die HTML-Datei nicht lokal vorliegt."""
    return _FALLBACK_URLS.get(filename)
