# QSL73 — Copyright (C) 2026 DF1DS (kainomatic) — SPDX-License-Identifier: GPL-3.0-or-later
"""Tests für gui/config_error_dialog.py — pure Logik tk-frei; tk-Tests skippt im CI."""
from __future__ import annotations

import sys
import time
from pathlib import Path

import pytest

from qsl73.config import Config, ConfigError, save_config
from qsl73.config_backup import create_config_backup, list_config_backups
from qsl73.crypto import NullBackend
from qsl73.gui.config_error_dialog import (
    backup_display_name,
    has_config_backups,
    try_restore_and_load,
)


# ---------------------------------------------------------------------------
# backup_display_name
# ---------------------------------------------------------------------------


class TestBackupDisplayName:
    def test_valid_name_formatted(self):
        # Format: config_YYYYMMDD_HHMMSS_<uuid8>.yaml
        p = Path("config_20260618_143022_abc12345.yaml")
        assert backup_display_name(p) == "2026-06-18  14:30:22"

    def test_another_valid_name(self):
        p = Path("config_20260101_000000_00000001.yaml")
        assert backup_display_name(p) == "2026-01-01  00:00:00"

    def test_fallback_for_malformed_name(self):
        p = Path("config_bad.yaml")
        assert backup_display_name(p) == "config_bad.yaml"

    def test_plain_yaml_fallback(self):
        p = Path("other.yaml")
        assert backup_display_name(p) == "other.yaml"


# ---------------------------------------------------------------------------
# has_config_backups
# ---------------------------------------------------------------------------


class TestHasConfigBackups:
    def test_false_when_dir_missing(self, tmp_path):
        assert has_config_backups(tmp_path / "nonexistent") is False

    def test_false_when_dir_empty(self, tmp_path):
        d = tmp_path / "bak"
        d.mkdir()
        assert has_config_backups(d) is False

    def test_true_when_backup_exists(self, tmp_path):
        config_path = tmp_path / "config.yaml"
        backup_dir = tmp_path / "bak"
        config_path.write_text("x: 1\n", encoding="utf-8")
        create_config_backup(config_path, backup_dir=backup_dir)

        assert has_config_backups(backup_dir) is True


# ---------------------------------------------------------------------------
# try_restore_and_load
# ---------------------------------------------------------------------------


class TestTryRestoreAndLoad:
    def test_valid_backup_returns_config(self, tmp_path):
        crypto = NullBackend()
        config = Config()
        config.log4om.own_callsign = "DF1DS"

        config_path = tmp_path / "config.yaml"
        backup_dir = tmp_path / "bak"

        # Gültige Config speichern
        save_config(config, config_path, crypto=crypto)

        # Backup davon anlegen
        bp = create_config_backup(config_path, backup_dir=backup_dir)
        assert bp is not None

        # Config kaputt machen
        config_path.write_text("paperless:\n  auth_mode: kaputt\n", encoding="utf-8")

        # Backup wiederherstellen und laden
        restored = try_restore_and_load(bp, config_path, crypto)
        assert isinstance(restored, Config)
        assert restored.log4om.own_callsign == "DF1DS"

    def test_invalid_backup_raises_config_error(self, tmp_path):
        crypto = NullBackend()
        config_path = tmp_path / "config.yaml"

        # Ungültiges Backup anlegen
        backup_path = tmp_path / "bak" / "config_20260618_120000.yaml"
        backup_path.parent.mkdir()
        backup_path.write_text("paperless:\n  auth_mode: ungueltig\n", encoding="utf-8")

        with pytest.raises(ConfigError):
            try_restore_and_load(backup_path, config_path, crypto)

    def test_restore_overwrites_config_path(self, tmp_path):
        crypto = NullBackend()
        config = Config()
        config_path = tmp_path / "config.yaml"
        backup_dir = tmp_path / "bak"

        save_config(config, config_path, crypto=crypto)
        bp = create_config_backup(config_path, backup_dir=backup_dir)
        assert bp is not None

        # Config ändern
        config.log4om.own_callsign = "CHANGED"
        save_config(config, config_path, crypto=crypto)

        # Backup wiederherstellen → original callsign zurück
        restored = try_restore_and_load(bp, config_path, crypto)
        assert restored.log4om.own_callsign == ""

    def test_backup_selection_identifies_correct_path(self, tmp_path):
        """Backup-Auswahl über list_config_backups liefert richtigen Pfad (neueste zuerst)."""
        backup_dir = tmp_path / "bak"
        backup_dir.mkdir()

        # Backup-Dateien mit bekannten Zeitstempeln anlegen (UUID-Suffix beliebig)
        older = backup_dir / "config_20260617_100000_aaaaaaaa.yaml"
        newer = backup_dir / "config_20260618_143022_bbbbbbbb.yaml"
        older.write_text("older: true\n", encoding="utf-8")
        newer.write_text("newer: true\n", encoding="utf-8")

        backups = list_config_backups(backup_dir)
        assert len(backups) == 2
        assert backups[0].name == newer.name   # neueste zuerst
        assert backups[1].name == older.name


# ---------------------------------------------------------------------------
# tk-Smoke-Test (skippt im CI)
# ---------------------------------------------------------------------------


def _has_display() -> bool:
    try:
        import tkinter as tk

        root = tk.Tk()
        root.destroy()
        return True
    except Exception:
        return False


_NO_DISPLAY = not _has_display()


@pytest.mark.skipif(_NO_DISPLAY, reason="kein tk-Display verfügbar")
def test_show_config_error_dialog_importable():
    from qsl73.gui.config_error_dialog import show_config_error_dialog

    assert callable(show_config_error_dialog)
