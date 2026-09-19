# QSL73 — Copyright (C) 2026 DF1DS (kainomatic) — SPDX-License-Identifier: GPL-3.0-or-later
"""Tests für gui/ignored_window.py (ADR-0059) — CI-kompatibel.

Aufbau: reine Helfer laufen immer; tk-abhängige Tests werden im CI übersprungen
(kein Display vorhanden), analog test_manual_assignment.py.
"""
from __future__ import annotations

import time
from unittest.mock import MagicMock

from qsl73.gui.ignored_window import format_doc_row


def _pump(root, condition, timeout_s: float = 5.0) -> bool:
    """Treibt die Tk-Eventloop an, bis condition() wahr wird oder timeout_s abläuft.

    Nötig weil das Laden/Wieder-Aufnehmen im Hintergrund-Thread läuft und das
    Ergebnis per self.after()-Queue-Poll in der Haupt-Eventloop verarbeitet wird
    (ADR-0023-Muster) — ohne root.update() läuft diese Loop während des Tests nie.
    """
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        root.update()
        if condition():
            return True
        time.sleep(0.02)
    return False


# ---------------------------------------------------------------------------
# format_doc_row — reine Helfer (kein tk)
# ---------------------------------------------------------------------------


def test_format_doc_row_prefers_created_over_added():
    doc = {"id": 42, "title": "QSL Karte", "created": "2026-01-15T10:00:00Z", "added": "2026-02-01T00:00:00Z"}
    doc_id, title, date = format_doc_row(doc)
    assert doc_id == "42"
    assert title == "QSL Karte"
    assert date == "2026-01-15"


def test_format_doc_row_falls_back_to_added():
    doc = {"id": 7, "title": "Karte", "added": "2025-06-01T12:00:00Z"}
    _, _, date = format_doc_row(doc)
    assert date == "2025-06-01"


def test_format_doc_row_missing_title_uses_placeholder():
    doc = {"id": 1}
    _, title, date = format_doc_row(doc)
    assert title == "(ohne Titel)"
    assert date == "–"


def test_format_doc_row_missing_id_no_crash():
    doc = {"title": "X"}
    doc_id, _, _ = format_doc_row(doc)
    assert doc_id == "–"


# ---------------------------------------------------------------------------
# tk-abhängige Tests — tk_child-Fixture aus conftest.py (ADR-0062)
# ---------------------------------------------------------------------------


def _make_tags_config(input_="qsl-card", ignored="qsl-ignoriert"):
    from qsl73.config import TagsConfig
    return TagsConfig(input=input_, confirmed="qsl-bestätigt", ignored=ignored)


def test_populates_tree_from_client(tk_child, monkeypatch):
    from qsl73.gui.ignored_window import IgnoredCardsWindow

    client = MagicMock()
    client.list_documents_with_all_tags.return_value = [
        {"id": 1, "title": "Karte 1", "created": "2026-01-01T00:00:00Z"},
        {"id": 2, "title": "Karte 2", "created": "2026-01-02T00:00:00Z"},
    ]

    root = tk_child
    win = IgnoredCardsWindow(root, client, _make_tags_config())

    assert _pump(root, lambda: bool(win._tree.get_children()))
    assert len(win._tree.get_children()) == 2
    # Issue #41, Grundentscheidung 5: nur noch der Ignoriert-Tag — der Eingangs-Tag
    # wird von ignorierten Karten inzwischen entfernt.
    client.list_documents_with_all_tags.assert_called_once_with(["qsl-ignoriert"])


def test_empty_list_shows_hint_no_error(tk_child, monkeypatch):
    from qsl73.gui.ignored_window import IgnoredCardsWindow

    client = MagicMock()
    client.list_documents_with_all_tags.return_value = []

    root = tk_child
    win = IgnoredCardsWindow(root, client, _make_tags_config())

    assert _pump(root, lambda: win._status_var.get() != "Lade…")
    assert win._status_var.get() == "Keine ignorierten Karten."


def test_unignore_selected_removes_row_and_calls_unignore_card(tk_child, monkeypatch):
    from qsl73.gui.ignored_window import IgnoredCardsWindow

    client = MagicMock()
    client.list_documents_with_all_tags.return_value = [
        {"id": 1, "title": "Karte 1", "created": "2026-01-01T00:00:00Z"},
        {"id": 2, "title": "Karte 2", "created": "2026-01-02T00:00:00Z"},
    ]

    called = []

    def _fake_unignore_card(c, doc_id, tags_config, log_dir):
        called.append(doc_id)

    monkeypatch.setattr("qsl73.ignore.unignore_card", _fake_unignore_card)

    root = tk_child
    win = IgnoredCardsWindow(root, client, _make_tags_config())

    assert _pump(root, lambda: bool(win._tree.get_children()))

    win._tree.selection_set("1")
    win._on_select()
    assert str(win._btn_unignore.cget("state")) == "normal"

    win._on_unignore_selected()

    assert _pump(root, lambda: not win._tree.exists("1"))
    assert called == [1]
    assert win._tree.exists("2")


def test_load_error_shows_message_not_traceback(tk_child):
    from qsl73.gui.ignored_window import IgnoredCardsWindow

    client = MagicMock()
    client.list_documents_with_all_tags.side_effect = RuntimeError("Verbindung fehlgeschlagen")

    root = tk_child
    win = IgnoredCardsWindow(root, client, _make_tags_config())

    assert _pump(root, lambda: win._status_var.get() != "Lade…")
    assert "Verbindung fehlgeschlagen" in win._status_var.get()
