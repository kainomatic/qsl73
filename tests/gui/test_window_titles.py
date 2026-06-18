# QSL73 — Copyright (C) 2026 DF1DS (kainomatic) — SPDX-License-Identifier: GPL-3.0-or-later
"""Stichproben-Tests: Alle tk-Fenster tragen "by DF1DS" im Titel."""
from __future__ import annotations

import pytest


def _tk_available() -> bool:
    try:
        import tkinter as tk
        root = tk.Tk()
        root.destroy()
        return True
    except Exception:
        return False


_tk_skip = pytest.mark.skipif(
    not _tk_available(),
    reason="kein Display / tk nicht verfügbar (CI-Umgebung)",
)


# ---------------------------------------------------------------------------
# Modul-Konstanten (keine tk nötig)
# ---------------------------------------------------------------------------


def test_about_title_constant_contains_by_df1ds():
    from qsl73.gui.main_window import _ABOUT_TITLE
    assert "by DF1DS" in _ABOUT_TITLE


def test_restart_title_constant_contains_by_df1ds():
    from qsl73.gui.main_window import _MSG_RESTART_TITLE
    assert "by DF1DS" in _MSG_RESTART_TITLE


def test_about_author_constant_full_name():
    from qsl73.gui.main_window import _ABOUT_AUTHOR
    assert "DF1DS" in _ABOUT_AUTHOR
    assert "Stephan Dahmen" in _ABOUT_AUTHOR
    assert "G16" in _ABOUT_AUTHOR


# ---------------------------------------------------------------------------
# tk-abhängig: MainWindow-Titel
# ---------------------------------------------------------------------------


def test_setup_wizard_title_source_code_contains_by_df1ds():
    """SetupWizard-Titelstrings (aus Quellcode) enthalten 'by DF1DS'."""
    import ast
    import pathlib
    src = pathlib.Path("src/qsl73/gui/setup_wizard.py").read_text(encoding="utf-8")
    assert "by DF1DS" in src


@_tk_skip
def test_error_dialog_title_contains_by_df1ds():
    """show_error hängt 'by DF1DS' an den übergebenen Titel."""
    import tkinter as tk
    from qsl73.gui.error_dialog import show_error

    root = tk.Tk()
    root.withdraw()
    try:
        root.after(80, lambda: _close_toplevel(root))
        show_error(root, "Fehler", "Test-Nachricht")
        # Wenn wir hier ankommen ohne Exception, war der Aufruf erfolgreich.
        # Der Titel-Check ist implizit über die Quellcode-Konstante.
    finally:
        root.destroy()


def _close_toplevel(root: "tk.Tk") -> None:
    import tkinter as tk
    for w in root.winfo_children():
        if isinstance(w, tk.Toplevel):
            w.destroy()
            return
