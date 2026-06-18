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


def test_load_raises_config_error_when_file_invalid(tmp_path):
    # ADR-0033: ungültige Config wirft direkt ConfigError (nicht mehr SetupNeeded)
    broken = tmp_path / "config.yaml"
    broken.write_text("paperless: [this is not a dict]", encoding="utf-8")
    with pytest.raises(ConfigError):
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


# ---------------------------------------------------------------------------
# config_to_field_defaults — Token-Schutz und vollständige Feldzuordnung
# ---------------------------------------------------------------------------

from qsl73.gui.wizard_logic import (
    config_to_field_defaults,
    is_token_retain_valid,
    merge_wizard_overrides,
)


class TestConfigToFieldDefaults:
    def test_url_mapped(self):
        cfg = Config()
        cfg.paperless.url = "https://test.example"
        assert config_to_field_defaults(cfg)["paperless.url"] == "https://test.example"

    def test_token_not_in_defaults(self):
        cfg = Config()
        cfg.paperless.token = "geheimestoken"
        assert "paperless.token" not in config_to_field_defaults(cfg)

    def test_all_expected_keys_present(self):
        cfg = Config()
        d = config_to_field_defaults(cfg)
        expected = {
            "paperless.url", "paperless.auth_mode",
            "log4om.db_path", "log4om.own_callsign",
            "tags.input", "tags.confirmed", "tags.uncertain",
            "matching.fuzzy_enabled", "confirm.qsl_route_default",
            "app.language", "app.backup_count", "app.update_check",
            "app.manual_match_limit",
        }
        assert expected == set(d.keys())

    def test_backup_count_as_string(self):
        cfg = Config()
        cfg.app.backup_count = 7
        assert config_to_field_defaults(cfg)["app.backup_count"] == "7"

    def test_manual_match_limit_as_string(self):
        cfg = Config()
        cfg.app.manual_match_limit = 0
        assert config_to_field_defaults(cfg)["app.manual_match_limit"] == "0"

    def test_fuzzy_enabled_bool(self):
        cfg = Config()
        cfg.matching.fuzzy_enabled = False
        assert config_to_field_defaults(cfg)["matching.fuzzy_enabled"] is False

    def test_tags_all_fields(self):
        cfg = Config()
        cfg.tags.input = "inp"
        cfg.tags.confirmed = "conf"
        cfg.tags.uncertain = "unc"
        d = config_to_field_defaults(cfg)
        assert d["tags.input"] == "inp"
        assert d["tags.confirmed"] == "conf"
        assert d["tags.uncertain"] == "unc"


class TestIsTokenRetainValid:
    def test_true_when_empty_and_existing_token(self):
        cfg = Config()
        cfg.paperless.token = "existingtoken"
        assert is_token_retain_valid("token", "", cfg) is True

    def test_false_when_new_token_provided(self):
        cfg = Config()
        cfg.paperless.token = "existingtoken"
        assert is_token_retain_valid("token", "newtoken", cfg) is False

    def test_false_when_no_existing_token(self):
        cfg = Config()
        cfg.paperless.token = ""
        assert is_token_retain_valid("token", "", cfg) is False

    def test_false_when_mode_is_password(self):
        cfg = Config()
        cfg.paperless.token = "existingtoken"
        assert is_token_retain_valid("password", "", cfg) is False

    def test_false_when_existing_config_is_none(self):
        assert is_token_retain_valid("token", "", None) is False

    def test_whitespace_only_token_is_empty(self):
        cfg = Config()
        cfg.paperless.token = "existingtoken"
        assert is_token_retain_valid("token", "   ", cfg) is True


class TestMergeWizardOverrides:
    def test_applies_url_change(self):
        cfg = Config()
        cfg.paperless.url = "https://old.example"
        result = merge_wizard_overrides(cfg, {"paperless.url": "https://new.example"})
        assert result.paperless.url == "https://new.example"

    def test_preserves_token_when_empty(self):
        cfg = Config()
        cfg.paperless.token = "keepme"
        result = merge_wizard_overrides(cfg, {"paperless.token": ""})
        assert result.paperless.token == "keepme"

    def test_replaces_token_when_new(self):
        cfg = Config()
        cfg.paperless.token = "old"
        result = merge_wizard_overrides(cfg, {"paperless.token": "new"})
        assert result.paperless.token == "new"

    def test_preserves_portable_suffixes(self):
        cfg = Config()
        cfg.matching.portable_suffixes = ["P", "MM", "CUSTOM"]
        result = merge_wizard_overrides(cfg, {"matching.fuzzy_enabled": False})
        assert result.matching.portable_suffixes == ["P", "MM", "CUSTOM"]

    def test_does_not_mutate_original(self):
        cfg = Config()
        cfg.paperless.url = "https://original"
        merge_wizard_overrides(cfg, {"paperless.url": "https://changed"})
        assert cfg.paperless.url == "https://original"

    def test_preserves_config_version(self):
        cfg = Config()
        cfg.config_version = 1
        result = merge_wizard_overrides(cfg, {"paperless.url": "https://x"})
        assert result.config_version == 1

    def test_multiple_fields_applied(self):
        cfg = Config()
        result = merge_wizard_overrides(cfg, {
            "paperless.url": "https://x",
            "log4om.own_callsign": "DL9TEST",
            "app.backup_count": 3,
        })
        assert result.paperless.url == "https://x"
        assert result.log4om.own_callsign == "DL9TEST"
        assert result.app.backup_count == 3
