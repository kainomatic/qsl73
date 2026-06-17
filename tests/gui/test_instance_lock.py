"""Tests für InstanceLock — kein tk erforderlich."""
import os
from pathlib import Path

import pytest

from qsl73.gui.app import InstanceLock


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
