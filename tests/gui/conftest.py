# QSL73 — Copyright (C) 2026 DF1DS (kainomatic) — SPDX-License-Identifier: GPL-3.0-or-later
"""Gemeinsame tk-Fixtures für tests/gui/ (ADR-0062, Issue #40).

Hunderte einzelne tk.Tk()-Erzeugungen+Zerstörungen in einem Prozess erschöpfen die
Tcl-Runtime ("Tcl_AsyncDelete: async handler deleted by the wrong thread"). Diese
Datei stellt daher genau EINEN tk.Tk()-Root pro Testprozess bereit; einzelne Tests
bekommen stattdessen ein frisches tk.Toplevel-Kind davon.
"""
from __future__ import annotations

import tkinter as tk

import pytest


@pytest.fixture(scope="session")
def tk_root():
    """Genau ein tk.Tk()-Root für den gesamten Testprozess.

    Ist kein Display/tk verfügbar (CI, Server ohne X), skippt dies jeden Test, der
    den Root (direkt oder über `tk_child`) anfordert — ersetzt die bisherigen,
    pro Testdatei duplizierten _tk_available()/_has_display()-Prüfungen.
    """
    try:
        root = tk.Tk()
    except Exception:
        pytest.skip("kein Display / tk nicht verfügbar (CI-Umgebung)")
    root.withdraw()
    yield root
    root.destroy()


@pytest.fixture
def tk_child(tk_root):
    """Frisches tk.Toplevel-Kind des Session-Roots — ein Toplevel pro Test.

    Ersetzt das bisherige `root = tk.Tk(); ...; root.destroy()`-Muster je Test.
    Nach dem Test wird nur dieses Toplevel (und seine Kinder) zerstört, nicht der
    Session-Root.
    """
    child = tk.Toplevel(tk_root)
    child.withdraw()
    yield child
    if child.winfo_exists():
        child.destroy()
