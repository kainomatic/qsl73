# QSL73 — Copyright (C) 2026 DF1DS (kainomatic) — SPDX-License-Identifier: GPL-3.0-or-later
"""Tests für die Update-Prüfung im Hauptfenster (ADR-0063, Issue #40).

_start_update_check/_handle_event sind reine Dispatch-Logik ohne tk-Zugriff auf dem
hier getesteten Pfad — die Tests rufen die ungebundenen MainWindow-Methoden mit einem
MagicMock als self auf (kein Display/tk_root nötig, analog test_progress_reset.py).
"""
from __future__ import annotations

from unittest.mock import MagicMock, call

from qsl73.gui.controller import UpdateCheckDoneEvent
from qsl73.gui.main_window import MainWindow
from qsl73.updater import UpdateCheckResult, UpdateStatus


def test_start_update_check_delegates_to_controller_not_own_thread():
    """_start_update_check startet KEINEN eigenen Thread/self.after — nur den Controller."""
    fake_self = MagicMock()

    MainWindow._start_update_check(fake_self, manual=False)

    fake_self._controller.start_update_check.assert_called_once()
    fake_self.after.assert_not_called()


def test_start_update_check_passes_version_channel_and_manual_flag():
    from qsl73.__version__ import CHANNEL, __version__

    fake_self = MagicMock()

    MainWindow._start_update_check(fake_self, manual=True)

    fake_self._controller.start_update_check.assert_called_once_with(
        __version__, CHANNEL, manual=True
    )


def test_start_update_check_manual_sets_checking_status():
    fake_self = MagicMock()

    MainWindow._start_update_check(fake_self, manual=True)

    fake_self._status_var.set.assert_called_once()


def test_start_update_check_automatic_does_not_set_checking_status():
    fake_self = MagicMock()

    MainWindow._start_update_check(fake_self, manual=False)

    fake_self._status_var.set.assert_not_called()


def test_handle_event_dispatches_update_check_done_event_to_handler():
    """UpdateCheckDoneEvent aus der Queue wird im UI-Thread an _handle_update_result geroutet."""
    fake_self = MagicMock()
    fake_result = UpdateCheckResult(status=UpdateStatus.UP_TO_DATE)
    event = UpdateCheckDoneEvent(result=fake_result, manual=True)

    MainWindow._handle_event(fake_self, event)

    fake_self._handle_update_result.assert_called_once_with(fake_result, manual=True)


def test_handle_event_update_check_done_event_manual_false():
    fake_self = MagicMock()
    fake_result = UpdateCheckResult(status=UpdateStatus.UPDATE_AVAILABLE, new_version="9.9.9")
    event = UpdateCheckDoneEvent(result=fake_result, manual=False)

    MainWindow._handle_event(fake_self, event)

    fake_self._handle_update_result.assert_called_once_with(fake_result, manual=False)
