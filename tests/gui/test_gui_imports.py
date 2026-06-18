# QSL73 — Copyright (C) 2026 DF1DS (kainomatic) — SPDX-License-Identifier: GPL-3.0-or-later
"""Import-Smoke-Tests für GUI-Module — kein Display nötig, läuft headless im CI.

Ziel: SyntaxFehler und Import-Fehler in GUI-Modulen werden hier gefangen, auch wenn
Unit-Tests die Module mangels Display nie instanziieren (tk-Tests skippen im CI).
Kein tk.Tk(), kein wait_window() — reiner `import`.

Hintergrund: In Commit 0bc7832 führte ein `nonlocal row` im Hauptkörper von
SetupWizard._build_ui zu einem SyntaxError, der alle tk-Tests übersprungen hatte,
aber zum App-Absturz beim Start führte. Diese Tests verhindern solche Regressionen.
"""
import importlib
import pytest


_GUI_MODULES = [
    "qsl73.gui.app",
    "qsl73.gui.config_error_dialog",
    "qsl73.gui.controller",
    "qsl73.gui.error_dialog",
    "qsl73.gui.error_report_dialog",
    "qsl73.gui.filter_util",
    "qsl73.gui.main_window",
    "qsl73.gui.manual_assignment",
    "qsl73.gui.manual_match",
    "qsl73.gui.setup_wizard",
    "qsl73.gui.wizard_logic",
]


@pytest.mark.parametrize("module_name", _GUI_MODULES)
def test_gui_module_imports_without_error(module_name):
    """Jedes GUI-Modul muss ohne Fehler importierbar sein — auch ohne Display."""
    importlib.import_module(module_name)
