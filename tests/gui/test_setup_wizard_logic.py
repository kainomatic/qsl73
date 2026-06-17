# QSL73 — Copyright (C) 2026 DF1DS (kainomatic) — SPDX-License-Identifier: GPL-3.0-or-later
"""Tests für Setup-Wizard-Logik — kein tk erforderlich."""
from __future__ import annotations

from pathlib import Path

import pytest

from qsl73.config import Config, ConfigError
from qsl73.crypto import NullBackend
from qsl73.setup_assistant import (
    SetupNeeded,
    _OVERRIDE_MAP,
    create_initial_config,
    load_or_trigger_setup,
)


def test_load_raises_setup_needed_when_file_missing(tmp_path):
    missing = tmp_path / "nonexistent.yaml"
    with pytest.raises(SetupNeeded):
        load_or_trigger_setup(config_path=missing, crypto=NullBackend())


def test_load_raises_setup_needed_when_file_invalid(tmp_path):
    broken = tmp_path / "config.yaml"
    broken.write_text("paperless: [this is not a dict]", encoding="utf-8")
    with pytest.raises(SetupNeeded):
        load_or_trigger_setup(config_path=broken, crypto=NullBackend())


def test_load_returns_config_when_valid(tmp_path):
    cfg_path = tmp_path / "config.yaml"
    backend = NullBackend()
    create_initial_config(path=cfg_path, crypto=backend)
    result = load_or_trigger_setup(config_path=cfg_path, crypto=backend)
    assert isinstance(result, Config)


def test_create_initial_config_saves_file(tmp_path):
    cfg_path = tmp_path / "subdir" / "config.yaml"
    create_initial_config(path=cfg_path, crypto=NullBackend())
    assert cfg_path.exists()


def test_create_initial_config_applies_overrides(tmp_path):
    cfg_path = tmp_path / "config.yaml"
    overrides = {
        "paperless.url": "https://example.test",
        "log4om.own_callsign": "DL1ABC",
        "app.backup_count": 3,
    }
    cfg = create_initial_config(path=cfg_path, crypto=NullBackend(), overrides=overrides)
    assert cfg.paperless.url == "https://example.test"
    assert cfg.log4om.own_callsign == "DL1ABC"
    assert cfg.app.backup_count == 3


def test_create_initial_config_encrypts_token(tmp_path):
    cfg_path = tmp_path / "config.yaml"
    backend = NullBackend()
    create_initial_config(
        path=cfg_path,
        crypto=backend,
        overrides={"paperless.token": "geheimestoken"},
    )
    raw = cfg_path.read_text(encoding="utf-8")
    assert "geheimestoken" not in raw


def test_override_map_covers_all_expected_keys():
    expected = {
        "paperless.url",
        "paperless.auth_mode",
        "paperless.token",
        "log4om.db_path",
        "log4om.own_callsign",
        "tags.input",
        "tags.confirmed",
        "tags.uncertain",
        "matching.fuzzy_enabled",
        "confirm.qsl_route_default",
        "app.language",
        "app.backup_count",
        "app.update_check",
    }
    assert expected.issubset(set(_OVERRIDE_MAP.keys()))
