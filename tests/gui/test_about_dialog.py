# QSL73 — Copyright (C) 2026 DF1DS (kainomatic) — SPDX-License-Identifier: GPL-3.0-or-later
"""Tests für _compute_dialog_geometry und _resolve_dialog_height (tk-frei, kein Display nötig)."""
import pytest

from qsl73.gui.main_window import _compute_dialog_geometry, _resolve_dialog_height


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
])
def test_resolve_dialog_height(inner_h, chrome, min_h, expected):
    assert _resolve_dialog_height(inner_h, chrome=chrome, min_h=min_h) == expected


def test_resolve_dialog_height_default_prevents_1px():
    """Regressionstest: Messwert 1 (minsize-Artefakt) → finale Höhe >= Standard-Mindesthöhe."""
    result = _resolve_dialog_height(1)
    assert result >= 300
