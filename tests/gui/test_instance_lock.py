"""Tests für InstanceLock und _create_app_mutex — kein tk erforderlich."""
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from qsl73.gui.app import InstanceLock, _create_app_mutex


def test_first_instance_acquires_lock(tmp_path):
    lock_path = tmp_path / "qsl73.lock"
    lock = InstanceLock(lock_path)
    assert lock.acquire() is True
    assert lock_path.exists()
    pid = int(lock_path.read_text().strip())
    assert pid == os.getpid()
    lock.release()
    assert not lock_path.exists()


def test_second_instance_fails_while_first_holds(tmp_path):
    lock_path = tmp_path / "qsl73.lock"
    lock1 = InstanceLock(lock_path)
    lock2 = InstanceLock(lock_path)

    assert lock1.acquire() is True
    assert lock2.acquire() is False
    lock1.release()


def test_stale_lock_with_dead_pid_is_overwritten(tmp_path):
    lock_path = tmp_path / "qsl73.lock"
    # PID 999999 existiert mit sehr hoher Wahrscheinlichkeit nicht
    lock_path.write_text("999999")
    lock = InstanceLock(lock_path)
    result = lock.acquire()
    assert result is True
    assert int(lock_path.read_text().strip()) == os.getpid()
    lock.release()


def test_release_without_lock_is_silent(tmp_path):
    lock_path = tmp_path / "qsl73.lock"
    lock = InstanceLock(lock_path)
    lock.release()  # kein Lock gehalten — kein Absturz


def test_stale_lock_with_invalid_content_is_overwritten(tmp_path):
    lock_path = tmp_path / "qsl73.lock"
    lock_path.write_text("not_a_pid")
    lock = InstanceLock(lock_path)
    assert lock.acquire() is True
    lock.release()


class TestCreateAppMutex:
    """_create_app_mutex ist non-fatal und kanalspezifisch.

    Alle Tests über patch.dict(sys.modules) — plattformunabhängig (kein win32event auf CI).
    """

    def _make_fake_win32event(self, handle=None):
        m = MagicMock()
        m.CreateMutex.return_value = handle or MagicMock()
        return m

    def test_returns_handle_when_win32event_available(self):
        fake_handle = MagicMock()
        fake_mod = self._make_fake_win32event(fake_handle)
        with patch.dict("sys.modules", {"win32event": fake_mod}):
            result = _create_app_mutex("stable")
        assert result is fake_handle
        fake_mod.CreateMutex.assert_called_once_with(None, False, "QSL73-Stable")

    def test_beta_uses_beta_name(self):
        fake_mod = self._make_fake_win32event()
        with patch.dict("sys.modules", {"win32event": fake_mod}):
            _create_app_mutex("beta")
        fake_mod.CreateMutex.assert_called_once_with(None, False, "QSL73-Beta")

    def test_returns_none_when_import_error(self):
        # sys.modules[name] = None → Python raises ImportError beim Import
        with patch.dict("sys.modules", {"win32event": None}):
            result = _create_app_mutex("stable")
        assert result is None

    def test_returns_none_on_win32event_exception(self):
        fake_mod = self._make_fake_win32event()
        fake_mod.CreateMutex.side_effect = OSError("Access denied")
        with patch.dict("sys.modules", {"win32event": fake_mod}):
            result = _create_app_mutex("stable")
        assert result is None
