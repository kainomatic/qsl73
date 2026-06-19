# QSL73 — Copyright (C) 2026 DF1DS (kainomatic) — SPDX-License-Identifier: GPL-3.0-or-later
"""Fenster-Icon und About-Logo für QSL73-Fenster."""
from __future__ import annotations

import logging
import sys
from pathlib import Path
import tkinter as tk

_log = logging.getLogger("qsl73")


def _icon_path() -> Path | None:
    """Findet qsl73_icon.png — im Bundle (_MEIPASS) oder im Dev-Pfad."""
    name = "qsl73_icon.png"
    if hasattr(sys, "_MEIPASS"):
        p = Path(sys._MEIPASS) / name
    else:
        # Dev: diese Datei liegt in src/qsl73/gui/, die Assets in src/qsl73/assets/
        p = Path(__file__).parent.parent / "assets" / name
    return p if p.exists() else None


def apply_window_icon(win: tk.Misc) -> None:
    """Setzt das QSL73-Icon auf einem Tk-Root oder Toplevel. Fehler sind non-fatal.

    Bei tk.Tk-Instanzen wird iconphoto(True, …) gerufen, damit alle danach
    erzeugten Toplevels das Icon automatisch erben (Tk 8.6+).
    """
    try:
        from PIL import Image, ImageTk
        path = _icon_path()
        if path is None:
            return
        photo = ImageTk.PhotoImage(Image.open(path).resize((64, 64), Image.LANCZOS))
        if isinstance(win, tk.Tk):
            win.iconphoto(True, photo)
        else:
            win.iconphoto(False, photo)
        # Referenz am Fenster halten — tk.PhotoImage wird sonst vom GC gelöscht
        win._qsl73_icon = photo  # type: ignore[attr-defined]
    except Exception:
        _log.debug("Fenster-Icon konnte nicht gesetzt werden", exc_info=True)


def load_about_logo(size: int = 128):  # -> ImageTk.PhotoImage | None
    """Lädt das transparente Logo für den Über-Dialog. Gibt None zurück bei Fehler."""
    try:
        from PIL import Image, ImageTk
        path = _icon_path()
        if path is None:
            return None
        return ImageTk.PhotoImage(Image.open(path).resize((size, size), Image.LANCZOS))
    except Exception:
        _log.debug("About-Logo konnte nicht geladen werden", exc_info=True)
        return None
