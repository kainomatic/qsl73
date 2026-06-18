#!/usr/bin/env python3
# QSL73 — Copyright (C) 2026 DF1DS (kainomatic) — SPDX-License-Identifier: GPL-3.0-or-later

"""
Erzeugt assets/qsl73.ico aus assets/qsl73logo.png.
Reproduzierbar, idempotent, minimal.
"""

from pathlib import Path
from PIL import Image

# Basispfad = Projektroot (tools/ ist Sibling von assets/)
project_root = Path(__file__).parent.parent
logo_path = project_root / "assets" / "qsl73logo.png"
ico_path = project_root / "assets" / "qsl73.ico"

# Logo öffnen
img = Image.open(logo_path).convert("RGBA")

# ICO mit Mindest-Auflösungen erzeugen
img.save(ico_path, sizes=[(16, 16), (32, 32), (48, 48), (256, 256)])

print(f"OK: {ico_path} erzeugt ({ico_path.stat().st_size} bytes)")
