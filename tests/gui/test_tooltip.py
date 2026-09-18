# QSL73 — Copyright (C) 2026 DF1DS (kainomatic) — SPDX-License-Identifier: GPL-3.0-or-later
"""Tests für gui/tooltip.py — CI-kompatibel.

Aufbau:
  1. Reine Logik (kein tk nötig): clamp_tooltip_position — läuft immer.
  2. tk-abhängige Tests: _Tooltip, attach_tooltip — werden im CI übersprungen.
"""
from __future__ import annotations

from qsl73.gui.tooltip import clamp_tooltip_position


# ---------------------------------------------------------------------------
# 1. Reine Logik — clamp_tooltip_position (immer laufen)
# ---------------------------------------------------------------------------

def test_clamp_no_change_needed():
    assert clamp_tooltip_position(10, 10, 100, 30, 1920, 1080) == (10, 10)


def test_clamp_right_overflow():
    x, y = clamp_tooltip_position(1900, 10, 100, 30, 1920, 1080)
    assert x + 100 + 4 <= 1920


def test_clamp_bottom_overflow():
    x, y = clamp_tooltip_position(10, 1060, 100, 30, 1920, 1080)
    assert y + 30 + 4 <= 1080


def test_clamp_negative_x():
    x, _ = clamp_tooltip_position(-50, 10, 100, 30, 1920, 1080)
    assert x == 0


def test_clamp_negative_y():
    _, y = clamp_tooltip_position(10, -20, 100, 30, 1920, 1080)
    assert y == 0


def test_clamp_both_overflow():
    x, y = clamp_tooltip_position(2000, 2000, 100, 30, 1920, 1080)
    assert x == 1920 - 100 - 4
    assert y == 1080 - 30 - 4


def test_clamp_exact_right_boundary():
    # Exakt an der Grenze: kein Überlauf
    x, y = clamp_tooltip_position(1920 - 100 - 4, 10, 100, 30, 1920, 1080)
    assert x == 1920 - 100 - 4


def test_clamp_small_screen():
    x, y = clamp_tooltip_position(5, 5, 50, 20, 60, 30)
    assert x + 50 + 4 <= 60
    assert y + 20 + 4 <= 30


def test_clamp_returns_tuple_of_two():
    result = clamp_tooltip_position(10, 10, 50, 20, 800, 600)
    assert len(result) == 2


def test_clamp_zero_position():
    x, y = clamp_tooltip_position(0, 0, 100, 30, 1920, 1080)
    assert x == 0
    assert y == 0


# ---------------------------------------------------------------------------
# 2. tk-abhängige Tests (tk_child-Fixture aus conftest.py, ADR-0062)
# ---------------------------------------------------------------------------


def test_attach_tooltip_returns_tooltip_object(tk_child):
    from tkinter import ttk
    from qsl73.gui.tooltip import attach_tooltip

    btn = ttk.Button(tk_child, text="Test")
    btn.pack()
    tip = attach_tooltip(btn, "Testtext")
    assert tip is not None


def test_attach_tooltip_stores_on_widget(tk_child):
    from tkinter import ttk
    from qsl73.gui.tooltip import attach_tooltip

    btn = ttk.Button(tk_child, text="Test")
    btn.pack()
    tip = attach_tooltip(btn, "Hallo")
    assert hasattr(btn, "_qsl73_tooltip")
    assert btn._qsl73_tooltip is tip


def test_tooltip_hide_before_show_no_crash(tk_child):
    """_hide() vor _show() darf nicht abstürzen."""
    from tkinter import ttk
    from qsl73.gui.tooltip import _Tooltip

    btn = ttk.Button(tk_child, text="Test")
    btn.pack()
    tip = _Tooltip(btn, "Hallo")
    tip._hide()


def test_tooltip_double_hide_no_crash(tk_child):
    """Doppeltes _hide() darf nicht abstürzen."""
    from tkinter import ttk
    from qsl73.gui.tooltip import _Tooltip

    btn = ttk.Button(tk_child, text="Test")
    btn.pack()
    tip = _Tooltip(btn, "Hallo")
    tip._hide()
    tip._hide()


def test_tooltip_set_text_updates_stored_text(tk_child):
    """set_text() ändert den gespeicherten Text (für Button-Zustandswechsel, ADR-0059)."""
    from tkinter import ttk
    from qsl73.gui.tooltip import _Tooltip

    btn = ttk.Button(tk_child, text="Test")
    btn.pack()
    tip = _Tooltip(btn, "Alt")
    tip.set_text("Neu")
    assert tip._text == "Neu"


def test_tooltip_cancel_timer_without_timer_no_crash(tk_child):
    """_cancel_timer() ohne laufenden Timer darf nicht abstürzen."""
    from tkinter import ttk
    from qsl73.gui.tooltip import _Tooltip

    btn = ttk.Button(tk_child, text="Test")
    btn.pack()
    tip = _Tooltip(btn, "Hallo")
    tip._cancel_timer()
