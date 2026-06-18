# QSL73 — Copyright (C) 2026 DF1DS (kainomatic) — SPDX-License-Identifier: GPL-3.0-or-later
"""Tests für config_backup.py — rein, keine tk-Abhängigkeit."""
import re
import time
from pathlib import Path

import pytest

from qsl73.config import Config, save_config
from qsl73.config_backup import (
    _backup_filename,
    create_config_backup,
    get_config_backup_dir,
    list_config_backups,
    restore_config_backup,
)
from qsl73.crypto import NullBackend


# ---------------------------------------------------------------------------
# Hilfsfunktion
# ---------------------------------------------------------------------------


def _write_yaml(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# get_config_backup_dir
# ---------------------------------------------------------------------------


class TestGetConfigBackupDir:
    def test_returns_path(self):
        assert isinstance(get_config_backup_dir(), Path)

    def test_ends_with_config_backups(self):
        assert get_config_backup_dir().name == "config_backups"

    def test_parent_is_qsl73(self):
        assert get_config_backup_dir().parent.name == "QSL73"


# ---------------------------------------------------------------------------
# _backup_filename
# ---------------------------------------------------------------------------


class TestBackupFilename:
    def test_matches_pattern(self):
        # Format: config_YYYYMMDD_HHMMSS_<8 hex>.yaml
        assert re.match(r"config_\d{8}_\d{6}_[0-9a-f]{8}\.yaml$", _backup_filename())

    def test_starts_with_config_(self):
        assert _backup_filename().startswith("config_")

    def test_ends_with_yaml(self):
        assert _backup_filename().endswith(".yaml")

    def test_unique_per_call(self):
        assert _backup_filename() != _backup_filename()


# ---------------------------------------------------------------------------
# create_config_backup
# ---------------------------------------------------------------------------


class TestCreateConfigBackup:
    def test_returns_none_when_config_missing(self, tmp_path):
        result = create_config_backup(tmp_path / "config.yaml", backup_dir=tmp_path / "bak")
        assert result is None

    def test_returns_backup_path_when_config_exists(self, tmp_path):
        config_path = tmp_path / "config.yaml"
        _write_yaml(config_path, "key: value\n")

        result = create_config_backup(config_path, backup_dir=tmp_path / "bak")
        assert result is not None
        assert result.exists()

    def test_backup_content_equals_original(self, tmp_path):
        config_path = tmp_path / "config.yaml"
        content = "key: value\nnested:\n  field: 42\n"
        _write_yaml(config_path, content)

        bp = create_config_backup(config_path, backup_dir=tmp_path / "bak")
        assert bp is not None
        assert bp.read_text(encoding="utf-8") == content

    def test_backup_filename_matches_pattern(self, tmp_path):
        config_path = tmp_path / "config.yaml"
        _write_yaml(config_path, "x: 1\n")

        bp = create_config_backup(config_path, backup_dir=tmp_path / "bak")
        assert bp is not None
        assert re.match(r"config_\d{8}_\d{6}_[0-9a-f]{8}\.yaml$", bp.name)

    def test_creates_backup_dir(self, tmp_path):
        config_path = tmp_path / "config.yaml"
        backup_dir = tmp_path / "sub" / "bak"
        _write_yaml(config_path, "x: 1\n")

        create_config_backup(config_path, backup_dir=backup_dir)
        assert backup_dir.exists()

    def test_rotation_keeps_last_n(self, tmp_path):
        config_path = tmp_path / "config.yaml"
        backup_dir = tmp_path / "bak"

        for i in range(7):
            _write_yaml(config_path, f"x: {i}\n")
            create_config_backup(config_path, backup_count=5, backup_dir=backup_dir)

        remaining = list(backup_dir.glob("config_*.yaml"))
        assert len(remaining) == 5

    def test_rotation_deletes_oldest(self, tmp_path):
        config_path = tmp_path / "config.yaml"
        backup_dir = tmp_path / "bak"

        for i in range(4):
            _write_yaml(config_path, f"x: {i}\n")
            create_config_backup(config_path, backup_count=2, backup_dir=backup_dir)

        remaining = list(backup_dir.glob("config_*.yaml"))
        # Nach 4 Backups mit backup_count=2 dürfen nur noch 2 übrig sein
        assert len(remaining) == 2

    def test_backup_count_zero_keeps_all(self, tmp_path):
        config_path = tmp_path / "config.yaml"
        backup_dir = tmp_path / "bak"

        for i in range(6):
            _write_yaml(config_path, f"x: {i}\n")
            create_config_backup(config_path, backup_count=0, backup_dir=backup_dir)

        assert len(list(backup_dir.glob("config_*.yaml"))) == 6

    def test_no_plaintext_token_in_backup(self, tmp_path):
        """Backup darf niemals den Klartext-Token enthalten."""
        crypto = NullBackend()
        config = Config()
        plaintext = "super-geheimer-token"
        config.paperless.token = plaintext

        config_path = tmp_path / "config.yaml"
        backup_dir = tmp_path / "bak"

        # Config speichern (Token wird base64-kodiert, nicht Klartext)
        save_config(config, config_path, crypto=crypto)

        # Backup anlegen (kopiert die verschlüsselte Datei)
        bp = create_config_backup(config_path, backup_dir=backup_dir)
        assert bp is not None

        content = bp.read_text(encoding="utf-8")
        assert plaintext not in content, "Klartext-Token im Backup gefunden!"


# ---------------------------------------------------------------------------
# list_config_backups
# ---------------------------------------------------------------------------


class TestListConfigBackups:
    def test_empty_when_dir_missing(self, tmp_path):
        assert list_config_backups(tmp_path / "nonexistent") == []

    def test_empty_when_dir_empty(self, tmp_path):
        d = tmp_path / "bak"
        d.mkdir()
        assert list_config_backups(d) == []

    def test_returns_sorted_newest_first(self, tmp_path):
        # Dateien mit bekannten Zeitstempeln anlegen (UUID-Teil egal für Sortierung)
        backup_dir = tmp_path / "bak"
        backup_dir.mkdir()
        oldest = backup_dir / "config_20260616_100000_aaaaaaaa.yaml"
        middle = backup_dir / "config_20260617_120000_bbbbbbbb.yaml"
        newest = backup_dir / "config_20260618_143022_cccccccc.yaml"
        for f in (oldest, middle, newest):
            f.write_text("x: 1\n", encoding="utf-8")

        result = list_config_backups(backup_dir)
        assert len(result) == 3
        assert result[0].name == newest.name   # neueste zuerst
        assert result[-1].name == oldest.name  # älteste zuletzt

    def test_ignores_non_matching_files(self, tmp_path):
        d = tmp_path / "bak"
        d.mkdir()
        (d / "other.yaml").write_text("x: 1\n", encoding="utf-8")
        (d / "config_bad.txt").write_text("x: 1\n", encoding="utf-8")

        assert list_config_backups(d) == []

    def test_counts_valid_backups(self, tmp_path):
        config_path = tmp_path / "config.yaml"
        backup_dir = tmp_path / "bak"

        for i in range(3):
            _write_yaml(config_path, f"x: {i}\n")
            create_config_backup(config_path, backup_dir=backup_dir)

        assert len(list_config_backups(backup_dir)) == 3


# ---------------------------------------------------------------------------
# restore_config_backup
# ---------------------------------------------------------------------------


class TestRestoreConfigBackup:
    def test_copies_backup_to_config_path(self, tmp_path):
        backup_path = tmp_path / "bak" / "config_20260618_120000.yaml"
        backup_path.parent.mkdir()
        backup_path.write_text("restored: true\n", encoding="utf-8")

        config_path = tmp_path / "config.yaml"
        restore_config_backup(backup_path, config_path)

        assert config_path.exists()
        assert config_path.read_text(encoding="utf-8") == "restored: true\n"

    def test_creates_parent_dirs(self, tmp_path):
        backup_path = tmp_path / "bak" / "config_20260618_120000.yaml"
        backup_path.parent.mkdir()
        backup_path.write_text("x: 1\n", encoding="utf-8")

        config_path = tmp_path / "nested" / "sub" / "config.yaml"
        restore_config_backup(backup_path, config_path)
        assert config_path.exists()

    def test_overwrites_existing_config(self, tmp_path):
        backup_path = tmp_path / "bak" / "config_20260618_120000.yaml"
        backup_path.parent.mkdir()
        backup_path.write_text("new: content\n", encoding="utf-8")

        config_path = tmp_path / "config.yaml"
        config_path.write_text("old: content\n", encoding="utf-8")

        restore_config_backup(backup_path, config_path)
        assert config_path.read_text(encoding="utf-8") == "new: content\n"
