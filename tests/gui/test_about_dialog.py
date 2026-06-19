# QSL73 — Copyright (C) 2026 DF1DS (kainomatic) — SPDX-License-Identifier: GPL-3.0-or-later
"""Tests für _compute_dialog_geometry (tk-frei, kein Display nötig)."""
import pytest

from qsl73.gui.main_window import _compute_dialog_geometry


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
