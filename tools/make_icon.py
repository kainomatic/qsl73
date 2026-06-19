#!/usr/bin/env python3
# QSL73 — Copyright (C) 2026 DF1DS (kainomatic) — SPDX-License-Identifier: GPL-3.0-or-later

"""
Erzeugt assets/qsl73.ico und src/qsl73/assets/qsl73_icon.png aus assets/qsl73logo.png.
Reproduzierbar, idempotent, minimal.

Hintergrundentfernung: Flood-Fill von den vier Ecken mit Threshold 235 je Kanal.
Konservativ: nur zusammenhängende Hintergrundpixel werden transparent — Motivanteile
mit ähnlicher Farbe bleiben erhalten.
"""

from collections import deque
from pathlib import Path

from PIL import Image

project_root = Path(__file__).parent.parent
logo_path = project_root / "assets" / "qsl73logo.png"
ico_path = project_root / "assets" / "qsl73.ico"
icon_png_path = project_root / "src" / "qsl73" / "assets" / "qsl73_icon.png"


def remove_white_background(img: Image.Image, threshold: int = 235) -> Image.Image:
    """Entfernt den weißen Hintergrund per Flood-Fill von den Ecken (kein numpy nötig).

    Nur zusammenhängende Pixel, die in allen RGB-Kanälen >= threshold sind, werden
    transparent gesetzt. Isolierte helle Pixel im Motiv bleiben erhalten.
    """
    img = img.convert("RGBA")
    px = img.load()
    w, h = img.size

    visited: set[tuple[int, int]] = set()
    queue: deque[tuple[int, int]] = deque()

    def is_bg(x: int, y: int) -> bool:
        r, g, b, _ = px[x, y]
        return r >= threshold and g >= threshold and b >= threshold

    for cx, cy in [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)]:
        if (cx, cy) not in visited and is_bg(cx, cy):
            visited.add((cx, cy))
            queue.append((cx, cy))

    while queue:
        x, y = queue.popleft()
        r, g, b, _ = px[x, y]
        px[x, y] = (r, g, b, 0)
        for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < w and 0 <= ny < h and (nx, ny) not in visited and is_bg(nx, ny):
                visited.add((nx, ny))
                queue.append((nx, ny))

    return img


img_src = Image.open(logo_path)
img_transparent = remove_white_background(img_src)

# assets/qsl73.ico — für PyInstaller (exe-Icon) und Inno Setup (Installer-Icon)
img_transparent.save(ico_path, sizes=[(16, 16), (32, 32), (48, 48), (256, 256)])
print(f"OK: {ico_path} ({ico_path.stat().st_size} bytes)")

# src/qsl73/assets/qsl73_icon.png — für Runtime-Fenster-Icon + Über-Dialog
icon_png_path.parent.mkdir(parents=True, exist_ok=True)
img_transparent.resize((256, 256), Image.LANCZOS).save(icon_png_path, format="PNG")
print(f"OK: {icon_png_path} ({icon_png_path.stat().st_size} bytes)")
