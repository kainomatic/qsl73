# QSL73 — Copyright (C) 2026 DF1DS (kainomatic) — SPDX-License-Identifier: GPL-3.0-or-later
"""Tests für Alt-Bestand-Aufräumen im Hauptfenster (Issue #41, ADR-0064).

Analog test_main_window_update_check.py: die Dispatch-Logik ist ohne tk-Zugriff
testbar — die Tests rufen die ungebundenen MainWindow-Methoden mit einem MagicMock
als self auf (kein Display/tk_root nötig).
"""
from __future__ import annotations

from unittest.mock import MagicMock

from qsl73.gui.controller import InputTagCleanupCheckDoneEvent, InputTagCleanupRunDoneEvent
from qsl73.gui.main_window import MainWindow
from qsl73.input_tag_cleanup import CleanupResult


# ---------------------------------------------------------------------------
# schedule_input_tag_cleanup_check — no-op wenn bereits erledigt
# ---------------------------------------------------------------------------


def test_schedule_does_nothing_when_already_done():
    fake_self = MagicMock()
    fake_self._config.app.input_tag_cleanup_done = True

    MainWindow.schedule_input_tag_cleanup_check(fake_self)

    fake_self.after.assert_not_called()


def test_schedule_schedules_check_when_not_done():
    fake_self = MagicMock()
    fake_self._config.app.input_tag_cleanup_done = False

    MainWindow.schedule_input_tag_cleanup_check(fake_self)

    fake_self.after.assert_called_once()
    args = fake_self.after.call_args[0]
    assert args[1] == fake_self._start_input_tag_cleanup_check


# ---------------------------------------------------------------------------
# _start_input_tag_cleanup_check
# ---------------------------------------------------------------------------


def test_start_check_delegates_to_controller():
    fake_self = MagicMock()
    fake_self._paperless_client = MagicMock()

    MainWindow._start_input_tag_cleanup_check(fake_self, manual=False)

    fake_self._controller.start_input_tag_cleanup_check.assert_called_once_with(
        fake_self._paperless_client, fake_self._config.tags, manual=False
    )


def test_start_check_manual_sets_status():
    fake_self = MagicMock()
    fake_self._paperless_client = MagicMock()

    MainWindow._start_input_tag_cleanup_check(fake_self, manual=True)

    fake_self._status_var.set.assert_called_once()


def test_start_check_automatic_does_not_set_status():
    fake_self = MagicMock()
    fake_self._paperless_client = MagicMock()

    MainWindow._start_input_tag_cleanup_check(fake_self, manual=False)

    fake_self._status_var.set.assert_not_called()


def test_start_check_connection_error_manual_shows_error_dialog(monkeypatch):
    fake_self = MagicMock()
    fake_self._paperless_client = None
    fake_self._config.paperless.url = "not a real client factory call"

    import qsl73.gui.main_window as mw

    class _BoomClient:
        def __init__(self, *a, **kw):
            raise RuntimeError("kein Zugriff")

    monkeypatch.setattr("qsl73.paperless.PaperlessClient", _BoomClient)
    monkeypatch.setattr(mw, "show_error", MagicMock())

    MainWindow._start_input_tag_cleanup_check(fake_self, manual=True)

    mw.show_error.assert_called_once()
    fake_self._controller.start_input_tag_cleanup_check.assert_not_called()


def test_start_check_connection_error_automatic_no_dialog(monkeypatch):
    fake_self = MagicMock()
    fake_self._paperless_client = None

    import qsl73.gui.main_window as mw

    class _BoomClient:
        def __init__(self, *a, **kw):
            raise RuntimeError("kein Zugriff")

    monkeypatch.setattr("qsl73.paperless.PaperlessClient", _BoomClient)
    monkeypatch.setattr(mw, "show_error", MagicMock())

    MainWindow._start_input_tag_cleanup_check(fake_self, manual=False)

    mw.show_error.assert_not_called()
    fake_self._controller.start_input_tag_cleanup_check.assert_not_called()


# ---------------------------------------------------------------------------
# _handle_input_tag_cleanup_check_result
# ---------------------------------------------------------------------------


def test_handle_check_result_error_automatic_does_not_mark_done_no_dialog(monkeypatch):
    fake_self = MagicMock()
    event = InputTagCleanupCheckDoneEvent(count=0, error=True, manual=False)

    import qsl73.gui.main_window as mw
    monkeypatch.setattr(mw, "show_error", MagicMock())

    MainWindow._handle_input_tag_cleanup_check_result(fake_self, event)

    fake_self._mark_input_tag_cleanup_done.assert_not_called()
    mw.show_error.assert_not_called()


def test_handle_check_result_error_manual_shows_dialog(monkeypatch):
    fake_self = MagicMock()
    event = InputTagCleanupCheckDoneEvent(count=0, error=True, manual=True)

    import qsl73.gui.main_window as mw
    monkeypatch.setattr(mw, "show_error", MagicMock())

    MainWindow._handle_input_tag_cleanup_check_result(fake_self, event)

    fake_self._mark_input_tag_cleanup_done.assert_not_called()
    mw.show_error.assert_called_once()


def test_handle_check_result_zero_marks_done_no_dialog_automatic():
    fake_self = MagicMock()
    event = InputTagCleanupCheckDoneEvent(count=0, error=False, manual=False)

    MainWindow._handle_input_tag_cleanup_check_result(fake_self, event)

    fake_self._mark_input_tag_cleanup_done.assert_called_once()
    fake_self._show_input_tag_cleanup_dialog.assert_not_called()


def test_handle_check_result_zero_manual_shows_info_messagebox(monkeypatch):
    fake_self = MagicMock()
    event = InputTagCleanupCheckDoneEvent(count=0, error=False, manual=True)

    import qsl73.gui.main_window as mw
    monkeypatch.setattr(mw.messagebox, "showinfo", MagicMock())

    MainWindow._handle_input_tag_cleanup_check_result(fake_self, event)

    fake_self._mark_input_tag_cleanup_done.assert_called_once()
    mw.messagebox.showinfo.assert_called_once()


def test_handle_check_result_positive_count_opens_dialog_does_not_mark_done():
    fake_self = MagicMock()
    event = InputTagCleanupCheckDoneEvent(count=7, error=False, manual=False)

    MainWindow._handle_input_tag_cleanup_check_result(fake_self, event)

    fake_self._mark_input_tag_cleanup_done.assert_not_called()
    fake_self._show_input_tag_cleanup_dialog.assert_called_once_with(7)


# ---------------------------------------------------------------------------
# _handle_input_tag_cleanup_run_result
# ---------------------------------------------------------------------------


def test_handle_run_result_error_shows_error_does_not_mark_done(monkeypatch):
    fake_self = MagicMock()
    event = InputTagCleanupRunDoneEvent(result=None, error=RuntimeError("boom"))

    import qsl73.gui.main_window as mw
    monkeypatch.setattr(mw, "show_error", MagicMock())

    MainWindow._handle_input_tag_cleanup_run_result(fake_self, event)

    mw.show_error.assert_called_once()
    fake_self._mark_input_tag_cleanup_done.assert_not_called()


def test_handle_run_result_success_shows_summary_and_marks_done(monkeypatch):
    fake_self = MagicMock()
    event = InputTagCleanupRunDoneEvent(result=CleanupResult(removed=5, failed=2), error=None)

    import qsl73.gui.main_window as mw
    monkeypatch.setattr(mw.messagebox, "showinfo", MagicMock())

    MainWindow._handle_input_tag_cleanup_run_result(fake_self, event)

    mw.messagebox.showinfo.assert_called_once()
    msg = mw.messagebox.showinfo.call_args[0][1]
    assert "5" in msg
    assert "2" in msg
    fake_self._mark_input_tag_cleanup_done.assert_called_once()


# ---------------------------------------------------------------------------
# _mark_input_tag_cleanup_done
# ---------------------------------------------------------------------------


def test_mark_done_sets_flag_and_saves_config(monkeypatch):
    fake_self = MagicMock()
    fake_self._config.app.input_tag_cleanup_done = False

    import qsl73.gui.main_window as mw
    save_mock = MagicMock()
    monkeypatch.setattr("qsl73.config.save_config", save_mock)

    MainWindow._mark_input_tag_cleanup_done(fake_self)

    assert fake_self._config.app.input_tag_cleanup_done is True
    save_mock.assert_called_once()


def test_mark_done_save_failure_is_nonfatal(monkeypatch):
    fake_self = MagicMock()
    fake_self._config.app.input_tag_cleanup_done = False

    monkeypatch.setattr(
        "qsl73.config.save_config", MagicMock(side_effect=RuntimeError("Disk voll"))
    )

    # darf nicht werfen
    MainWindow._mark_input_tag_cleanup_done(fake_self)
    assert fake_self._config.app.input_tag_cleanup_done is True


# ---------------------------------------------------------------------------
# _on_cleanup_input_tag_menu — Menü-Handler
# ---------------------------------------------------------------------------


def test_menu_handler_triggers_manual_check():
    fake_self = MagicMock()

    MainWindow._on_cleanup_input_tag_menu(fake_self)

    fake_self._start_input_tag_cleanup_check.assert_called_once_with(manual=True)


# ---------------------------------------------------------------------------
# _handle_event — Dispatch neuer Event-Typen (analog UpdateCheckDoneEvent)
# ---------------------------------------------------------------------------


def test_handle_event_dispatches_cleanup_check_done_event():
    fake_self = MagicMock()
    event = InputTagCleanupCheckDoneEvent(count=1, error=False, manual=False)

    MainWindow._handle_event(fake_self, event)

    fake_self._handle_input_tag_cleanup_check_result.assert_called_once_with(event)


def test_handle_event_dispatches_cleanup_run_done_event():
    fake_self = MagicMock()
    event = InputTagCleanupRunDoneEvent(result=CleanupResult(removed=1, failed=0), error=None)

    MainWindow._handle_event(fake_self, event)

    fake_self._handle_input_tag_cleanup_run_result.assert_called_once_with(event)
