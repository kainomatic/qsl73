# QSL73 — Copyright (C) 2026 DF1DS (kainomatic) — SPDX-License-Identifier: GPL-3.0-or-later
"""Tests für gui/confirmations_window.py (Issue #42, Auftrag 2) — CI-kompatibel.

tk-abhängige Tests laufen über die conftest.py-Fixtures tk_root/tk_child (ADR-0062) —
kein eigenes tk.Tk() pro Test. Read-only-Laden gegen eine Mini-Log4OM-DB in tmp_path,
analog test_confirmations.py.
"""
from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path

from qsl73.confirmations import ConfirmationState
from qsl73.gui.confirmations_view import SERVICE_COLUMN_ORDER, cell_symbol


def _pump(root, condition, timeout_s: float = 5.0) -> bool:
    """Treibt die Tk-Eventloop an, bis condition() wahr wird oder timeout_s abläuft.

    Nötig weil das Laden im Hintergrund-Thread läuft und das Ergebnis per
    self.after()-Queue-Poll in der Haupt-Eventloop verarbeitet wird (ADR-0023-Muster).
    """
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        root.update()
        if condition():
            return True
        time.sleep(0.02)
    return False


def _make_db(tmp_path: Path, rows: list[dict]) -> Path:
    """Baut eine Mini-Log4OM-DB mit den gegebenen QSO-Zeilen."""
    db_path = tmp_path / "confirmations_test.sqlite"
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        "CREATE TABLE Log (qsoid TEXT PRIMARY KEY, callsign TEXT, qsodate TEXT, band TEXT,"
        " mode TEXT, dxcc INTEGER, country TEXT, cont TEXT, qsoconfirmations TEXT,"
        " stationcallsign TEXT, gridsquare TEXT, qslvia TEXT)"
    )
    for row in rows:
        conn.execute(
            "INSERT INTO Log VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                row["qsoid"],
                row.get("callsign", "DK8XX"),
                row.get("qsodate", "2025-04-02 19:42:00Z"),
                row.get("band", "20m"),
                row.get("mode", "SSB"),
                row.get("dxcc", 230),
                row.get("country", "Germany"),
                row.get("cont", "EU"),
                json.dumps(row.get("confirmations", [])),
                row.get("stationcallsign", "DF1DS"),
                row.get("gridsquare", "JO31"),
                row.get("qslvia", ""),
            ),
        )
    conn.commit()
    conn.close()
    return db_path


_SCHEMA_OK_QSL = {"CT": "QSL", "S": "No", "R": "No"}


# ---------------------------------------------------------------------------
# db_path fehlt/ungültig — klare Meldung, kein Absturz
# ---------------------------------------------------------------------------


def test_missing_db_path_shows_message_no_crash(tk_child):
    from qsl73.gui.confirmations_window import ConfirmationsWindow

    win = ConfirmationsWindow(tk_child, None)
    assert "log4om.db_path" in win._status_var.get()


def test_invalid_db_path_shows_message_no_crash(tk_child, tmp_path):
    from qsl73.gui.confirmations_window import ConfirmationsWindow

    win = ConfirmationsWindow(tk_child, str(tmp_path / "does_not_exist.sqlite"))
    assert "log4om.db_path" in win._status_var.get()


def test_schema_error_shown_as_clear_text_not_traceback(tk_child, tmp_path):
    from qsl73.gui.confirmations_window import ConfirmationsWindow

    db_path = tmp_path / "no_log_table.sqlite"
    conn = sqlite3.connect(str(db_path))
    conn.execute("CREATE TABLE Other (x TEXT)")
    conn.commit()
    conn.close()

    root = tk_child
    win = ConfirmationsWindow(root, str(db_path))
    assert _pump(root, lambda: win._status_var.get() != "Lade…")
    assert "Tabelle 'Log'" in win._status_var.get()
    assert "Traceback" not in win._status_var.get()


# ---------------------------------------------------------------------------
# Laden + Tabelle befüllen
# ---------------------------------------------------------------------------


def test_populates_tree_from_mini_db(tk_child, tmp_path):
    from qsl73.gui.confirmations_window import ConfirmationsWindow

    db_path = _make_db(
        tmp_path,
        [
            {"qsoid": "Q1", "callsign": "DK8XX", "confirmations": [_SCHEMA_OK_QSL]},
            {"qsoid": "Q2", "callsign": "DL0AAA", "confirmations": []},
        ],
    )
    root = tk_child
    win = ConfirmationsWindow(root, str(db_path))

    assert _pump(root, lambda: len(win._all_rows) == 2)
    assert _pump(root, lambda: bool(win._tree.get_children()))
    assert len(win._tree.get_children()) == 2
    assert "2 von 2 QSOs" in win._status_var.get()
    assert win._loaded_at is not None


def test_reload_button_reloads_data(tk_child, tmp_path):
    from qsl73.gui.confirmations_window import ConfirmationsWindow

    db_path = _make_db(tmp_path, [{"qsoid": "Q1", "confirmations": [_SCHEMA_OK_QSL]}])
    root = tk_child
    win = ConfirmationsWindow(root, str(db_path))
    assert _pump(root, lambda: len(win._all_rows) == 1)
    first_loaded_at = win._loaded_at

    win._all_rows = []
    win._on_reload()
    assert _pump(root, lambda: len(win._all_rows) == 1)
    assert win._loaded_at is not None
    assert first_loaded_at is not None


# ---------------------------------------------------------------------------
# Filter reduzieren die Zeilen
# ---------------------------------------------------------------------------


def test_text_filter_reduces_tree_rows(tk_child, tmp_path):
    from qsl73.gui.confirmations_window import ConfirmationsWindow

    db_path = _make_db(
        tmp_path,
        [
            {"qsoid": "Q1", "callsign": "DK8XX", "confirmations": [_SCHEMA_OK_QSL]},
            {"qsoid": "Q2", "callsign": "DL0AAA", "confirmations": []},
        ],
    )
    root = tk_child
    win = ConfirmationsWindow(root, str(db_path))
    assert _pump(root, lambda: len(win._tree.get_children()) == 2)

    win._text_var.set("DK8XX")
    assert _pump(root, lambda: len(win._tree.get_children()) == 1)
    assert win._tree.exists("Q1")
    assert not win._tree.exists("Q2")


def test_reset_filters_restores_all_rows(tk_child, tmp_path):
    from qsl73.gui.confirmations_window import ConfirmationsWindow

    db_path = _make_db(
        tmp_path,
        [
            {"qsoid": "Q1", "callsign": "DK8XX", "confirmations": [_SCHEMA_OK_QSL]},
            {"qsoid": "Q2", "callsign": "DL0AAA", "confirmations": []},
        ],
    )
    root = tk_child
    win = ConfirmationsWindow(root, str(db_path))
    assert _pump(root, lambda: len(win._tree.get_children()) == 2)

    win._text_var.set("DK8XX")
    assert _pump(root, lambda: len(win._tree.get_children()) == 1)

    win._reset_filters()
    assert _pump(root, lambda: len(win._tree.get_children()) == 2)


# ---------------------------------------------------------------------------
# Detailzeile zum gewählten QSO
# ---------------------------------------------------------------------------


def test_selecting_row_shows_detail_line(tk_child, tmp_path):
    from qsl73.gui.confirmations_window import ConfirmationsWindow

    db_path = _make_db(
        tmp_path,
        [
            {
                "qsoid": "Q1",
                "callsign": "DK8XX",
                "qslvia": "DL0XX",
                "confirmations": [
                    {"CT": "QSL", "S": "Yes", "R": "Yes", "SD": "2025-01-01", "RD": "2025-01-05"}
                ],
            }
        ],
    )
    root = tk_child
    win = ConfirmationsWindow(root, str(db_path))
    assert _pump(root, lambda: bool(win._tree.get_children()))

    win._tree.selection_set("Q1")
    win._on_select()

    detail = win._detail_var.get()
    assert "S=Yes" in detail
    assert "R=Yes" in detail
    assert "SD=2025-01-01" in detail
    assert "DL0XX" in detail


# ---------------------------------------------------------------------------
# Requested/Queued erscheinen NIE als bekommen/gesendet; Invalid gedämpft
# ---------------------------------------------------------------------------


def _qsl_cell(win, qsoid: str) -> str:
    values = win._tree.item(qsoid, "values")
    idx = list(("qsodate", "callsign", "band", "mode", "country") + SERVICE_COLUMN_ORDER).index("QSL")
    return values[idx]


def test_received_requested_not_shown_as_received(tk_child, tmp_path):
    from qsl73.gui.confirmations_window import ConfirmationsWindow

    db_path = _make_db(
        tmp_path,
        [
            {"qsoid": "SCHEMA", "confirmations": [_SCHEMA_OK_QSL]},
            {"qsoid": "Q1", "confirmations": [{"CT": "QSL", "S": "No", "R": "Requested"}]},
        ],
    )
    root = tk_child
    win = ConfirmationsWindow(root, str(db_path))
    assert _pump(root, lambda: bool(win._tree.get_children()))

    cell = _qsl_cell(win, "Q1")
    assert cell != cell_symbol(ConfirmationState.RECEIVED, marker=False)
    assert cell == cell_symbol(ConfirmationState.NONE, marker=True)


def test_sent_queued_not_shown_as_sent(tk_child, tmp_path):
    from qsl73.gui.confirmations_window import ConfirmationsWindow

    db_path = _make_db(
        tmp_path,
        [
            {"qsoid": "SCHEMA", "confirmations": [_SCHEMA_OK_QSL]},
            {"qsoid": "Q1", "confirmations": [{"CT": "QSL", "S": "Queued", "R": "No"}]},
        ],
    )
    root = tk_child
    win = ConfirmationsWindow(root, str(db_path))
    assert _pump(root, lambda: bool(win._tree.get_children()))

    cell = _qsl_cell(win, "Q1")
    assert cell != cell_symbol(ConfirmationState.SENT, marker=False)
    assert cell == cell_symbol(ConfirmationState.NONE, marker=True)


def test_invalid_gets_damped_symbol_distinct_from_none(tk_child, tmp_path):
    from qsl73.gui.confirmations_window import ConfirmationsWindow

    db_path = _make_db(
        tmp_path,
        [
            {"qsoid": "SCHEMA", "confirmations": [_SCHEMA_OK_QSL]},
            {"qsoid": "Q1", "confirmations": [{"CT": "QSL", "S": "Invalid", "R": "Invalid"}]},
        ],
    )
    root = tk_child
    win = ConfirmationsWindow(root, str(db_path))
    assert _pump(root, lambda: bool(win._tree.get_children()))

    cell = _qsl_cell(win, "Q1")
    assert cell == cell_symbol(ConfirmationState.INVALID, marker=False)
    assert cell != cell_symbol(ConfirmationState.NONE, marker=False)


# ---------------------------------------------------------------------------
# Spaltenwahl
# ---------------------------------------------------------------------------


def test_toggle_column_hides_and_shows_service_column(tk_child, tmp_path):
    from qsl73.gui.confirmations_window import ConfirmationsWindow

    db_path = _make_db(tmp_path, [{"qsoid": "Q1", "confirmations": [_SCHEMA_OK_QSL]}])
    root = tk_child
    win = ConfirmationsWindow(root, str(db_path))
    assert _pump(root, lambda: bool(win._tree.get_children()))

    assert "CLUBLOG" in win._tree["displaycolumns"]
    win._toggle_column("CLUBLOG", False)
    assert "CLUBLOG" not in win._tree["displaycolumns"]
    win._toggle_column("CLUBLOG", True)
    assert "CLUBLOG" in win._tree["displaycolumns"]
