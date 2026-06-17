# QSL73 — Copyright (C) 2026 DF1DS (kainomatic) — SPDX-License-Identifier: GPL-3.0-or-later
"""Tests für _reset_progress — kein tk erforderlich (Mock)."""
from __future__ import annotations

from unittest.mock import MagicMock, call

from qsl73.gui.main_window import _reset_progress


def test_reset_progress_calls_stop():
    mock_p = MagicMock()
    _reset_progress(mock_p)
    mock_p.stop.assert_called_once()


def test_reset_progress_resets_mode_and_value():
    mock_p = MagicMock()
    _reset_progress(mock_p)
    mock_p.configure.assert_called_once_with(mode="determinate", value=0)


def test_reset_progress_stop_called_before_configure():
    calls = []
    mock_p = MagicMock()
    mock_p.stop.side_effect = lambda: calls.append("stop")
    mock_p.configure.side_effect = lambda **_kw: calls.append("configure")
    _reset_progress(mock_p)
    assert calls == ["stop", "configure"]
