# QSL73 — Copyright (C) 2026 DF1DS (kainomatic) — SPDX-License-Identifier: GPL-3.0-or-later
"""Tests für _compute_dialog_geometry, _resolve_dialog_height und _resolve_dialog_width (tk-frei).

Der tk-Test am Ende benötigt ein Display; er wird übersprungen wenn keines verfügbar ist.
"""
import os
import sys
import pytest

from qsl73.gui.main_window import (
    _compute_dialog_geometry,
    _resolve_dialog_height,
    _resolve_dialog_width,
)


# ---------------------------------------------------------------------------
# _compute_dialog_geometry
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("dw,dh,px,py,pw,ph,expected", [
    # Dialog kleiner als Parent → zentriert
    (340, 200, 100, 100, 800, 600, "340x200+330+300"),
    # Dialog so groß wie Parent → Position = Parent-Ursprung
    (800, 600, 100, 100, 800, 600, "800x600+100+100"),
    # Dialog größer als Parent → negative Vorwerte werden auf 0 geclippt
    (1000, 800, 50, 50, 800, 600, "1000x800+0+0"),
    # Parent nahe linkem Rand (x würde negativ) → 0
    (400, 300, 10, 200, 200, 400, "400x300+0+250"),
    # Minimalfall: alles 0
    (100, 50, 0, 0, 0, 0, "100x50+0+0"),
])
def test_compute_dialog_geometry(dw, dh, px, py, pw, ph, expected):
    assert _compute_dialog_geometry(dw, dh, px, py, pw, ph) == expected


# ---------------------------------------------------------------------------
# _resolve_dialog_height
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("inner_h,chrome,min_h,expected", [
    # Normaler Fall: Inhalt + Chrome ergibt sinnvolle Höhe über der Mindesthöhe
    (300, 40, 200, 340),
    # Fehlerfall: unrealistisch kleine Höhe (z. B. 1 vom Toplevel-minsize-Artefakt)
    # → Mindesthöhe greift, kein 1px-Fenster
    (1, 40, 300, 300),
    # Kleiner Wert + Chrome noch unterhalb der Mindesthöhe → Mindesthöhe greift
    (50, 40, 300, 300),
    # Großer Inhalt → Mindesthöhe greift nicht
    (400, 40, 300, 440),
    # Chrome = 0
    (200, 0, 150, 200),
    # Neuer Aufruf-Fall aus _on_about: chrome=90, min_h=400
    (406, 90, 400, 496),
    (1, 90, 400, 400),      # 1px-Regressionstest mit neuen Werten
    (250, 90, 400, 400),    # 340 < 400 → Mindesthöhe greift
])
def test_resolve_dialog_height(inner_h, chrome, min_h, expected):
    assert _resolve_dialog_height(inner_h, chrome=chrome, min_h=min_h) == expected


def test_resolve_dialog_height_default_prevents_1px():
    """Regressionstest: Messwert 1 (minsize-Artefakt) → finale Höhe >= Standard-Mindesthöhe."""
    result = _resolve_dialog_height(1)
    assert result >= 300


def test_resolve_dialog_height_about_dialog_min():
    """Über-Dialog-Aufruf (chrome=90, min_h=400): Mindesthöhe auch bei 1px-Messwert."""
    result = _resolve_dialog_height(1, chrome=90, min_h=400)
    assert result >= 400


# ---------------------------------------------------------------------------
# _resolve_dialog_width
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("inner_w,min_w,expected", [
    # Mindestbreite greift wenn inner_w kleiner
    (1, 360, 360),
    (200, 360, 360),
    (359, 360, 360),
    # inner_w größer → kein Clipping
    (360, 360, 360),
    (500, 360, 500),
    # Anderer min_w
    (100, 480, 480),
    (600, 480, 600),
])
def test_resolve_dialog_width(inner_w, min_w, expected):
    assert _resolve_dialog_width(inner_w, min_w=min_w) == expected


def test_resolve_dialog_width_default_prevents_1px():
    """Regressionstest: Messwert 1 → finale Breite >= Standard-Mindestbreite."""
    result = _resolve_dialog_width(1)
    assert result >= 360


def test_resolve_dialog_width_default_min():
    """Standard-Mindestbreite (360) — Logo + Texte + Buttons passen sicher hinein."""
    assert _resolve_dialog_width(0) == 360
    assert _resolve_dialog_width(359) == 360
    assert _resolve_dialog_width(361) == 361


# ---------------------------------------------------------------------------
# Tk-Test — benötigt echtes Display; skippt wenn nicht verfügbar
# ---------------------------------------------------------------------------

def _tk_available() -> bool:
    """Prüft ob Tkinter ein Fenster öffnen kann (kein Headless-Fallback)."""
    try:
        import tkinter as tk
        root = tk.Tk()
        root.withdraw()
        root.destroy()
        return True
    except Exception:
        return False


_SKIP_TK = pytest.mark.skipif(
    not _tk_available(),
    reason="Kein Display verfügbar — tk-Test übersprungen",
)


@_SKIP_TK
def test_about_dialog_opens_at_minimum_size():
    """Über-Dialog muss Mindestbreite 360 und Mindesthöhe 400 erreichen.

    Testet das reale tk-Verhalten: Dialog wird geöffnet, winfo_width/height nach
    dem Mapping gemessen. Bestätigt den SetupWizard-Dimensionierungspfad.
    """
    import tkinter as tk
    from tkinter import ttk

    root = tk.Tk()
    root.geometry("900x700+50+50")
    root.update()
    root.deiconify()
    root.update_idletasks()

    measured = {}

    dlg = tk.Toplevel(root)
    dlg.title("Test-Über-Dialog")
    dlg.resizable(False, False)
    dlg.transient(root)

    frame = ttk.Frame(dlg, padding=24)
    frame.pack(fill="both", expand=True)
    ttk.Label(frame, text="QSL73  v0.2.3  (stable)", font=("", 13, "bold")).pack(pady=(0, 14))
    ttk.Label(frame, text="Beschreibung\nmehrzeilig", justify="center").pack(pady=(0, 12))
    ttk.Separator(frame, orient="horizontal").pack(fill="x", pady=(0, 12))
    ttk.Label(frame, text="Lizenz: GPLv3").pack(pady=(0, 6))
    ttk.Button(frame, text="Schliessen", command=dlg.destroy).pack()

    dlg.minsize(360, 400)
    dlg.update_idletasks()

    def _do_center():
        if not dlg.winfo_exists():
            return
        dlg.update_idletasks()
        dw = _resolve_dialog_width(frame.winfo_reqwidth())
        dh = _resolve_dialog_height(frame.winfo_reqheight(), chrome=90, min_h=400)
        if root.winfo_ismapped():
            geom = _compute_dialog_geometry(
                dw, dh,
                root.winfo_rootx(), root.winfo_rooty(),
                root.winfo_width(), root.winfo_height(),
            )
        else:
            sw = dlg.winfo_screenwidth()
            sh = dlg.winfo_screenheight()
            x = max(0, (sw - dw) // 2)
            y = max(0, (sh - dh) // 2)
            geom = f"{dw}x{dh}+{x}+{y}"
        dlg.geometry(geom)
        root.after(50, _measure)

    def _measure():
        if dlg.winfo_exists():
            measured["w"] = dlg.winfo_width()
            measured["h"] = dlg.winfo_height()
        dlg.destroy()

    dlg.after(1, _do_center)
    root.after(2000, dlg.destroy)  # Sicherheits-Timeout
    dlg.wait_window()
    root.destroy()

    assert "w" in measured, "Dialog wurde nicht korrekt geöffnet/gemessen"
    assert measured["w"] >= 360, f"Breite {measured['w']} < Mindestbreite 360"
    assert measured["h"] >= 400, f"Höhe {measured['h']} < Mindesthöhe 400"
