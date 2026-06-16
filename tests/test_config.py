import pytest
import yaml
from pathlib import Path

from qsl73.config import (
    Config,
    ConfigError,
    CURRENT_VERSION,
    load_config,
    save_config,
    validate_config,
    migrate_config,
)


class TestSaveAndLoad:
    def test_round_trip_defaults(self, config_path):
        config = Config()
        save_config(config, config_path)
        loaded = load_config(config_path)

        assert loaded.config_version == CURRENT_VERSION
        assert loaded.paperless.url == ""
        assert loaded.paperless.auth_mode == "token"
        assert loaded.paperless.token == ""
        assert loaded.log4om.db_path == ""
        assert loaded.log4om.own_callsign == ""
        assert loaded.tags.input == "qsl-card"
        assert loaded.tags.confirmed == "qsl-bestätigt"
        assert loaded.tags.uncertain == "qsl-nicht-bestätigt"
        assert loaded.matching.fuzzy_enabled is True
        assert loaded.confirm.qsl_route_default == "undefined"
        assert loaded.app.language == "de"
        assert loaded.app.backup_count == 5
        assert loaded.app.update_check is True

    def test_round_trip_custom_values(self, config_path):
        config = Config()
        config.paperless.url = "https://paperless.example.com"
        config.paperless.auth_mode = "password"
        config.log4om.db_path = "C:\\Users\\test\\log4om.db"
        config.log4om.own_callsign = "DF1DS"
        config.tags.input = "meine-karten"
        config.tags.confirmed = "erledigt"
        config.matching.fuzzy_enabled = False
        config.confirm.qsl_route_default = "bureau"
        config.app.language = "en"
        config.app.backup_count = 3
        config.app.update_check = False

        save_config(config, config_path)
        loaded = load_config(config_path)

        assert loaded.paperless.url == "https://paperless.example.com"
        assert loaded.paperless.auth_mode == "password"
        assert loaded.log4om.db_path == "C:\\Users\\test\\log4om.db"
        assert loaded.log4om.own_callsign == "DF1DS"
        assert loaded.tags.input == "meine-karten"
        assert loaded.tags.confirmed == "erledigt"
        assert loaded.matching.fuzzy_enabled is False
        assert loaded.confirm.qsl_route_default == "bureau"
        assert loaded.app.language == "en"
        assert loaded.app.backup_count == 3
        assert loaded.app.update_check is False

    def test_creates_parent_directory(self, tmp_path):
        path = tmp_path / "subdir" / "nested" / "config.yaml"
        save_config(Config(), path)
        assert path.exists()

    def test_all_qsl_routes_valid(self, config_path):
        for route in ("undefined", "bureau", "direct"):
            config = Config()
            config.confirm.qsl_route_default = route
            save_config(config, config_path)
            loaded = load_config(config_path)
            assert loaded.confirm.qsl_route_default == route


class TestTokenEncryption:
    def test_token_not_stored_in_plaintext(self, config_path, null_crypto):
        config = Config()
        config.paperless.token = "supersecrettoken"
        save_config(config, config_path, crypto=null_crypto)

        content = config_path.read_text(encoding="utf-8")
        assert "supersecrettoken" not in content

    def test_token_round_trip_with_crypto(self, config_path, null_crypto):
        config = Config()
        config.paperless.token = "mysecret"
        save_config(config, config_path, crypto=null_crypto)

        loaded = load_config(config_path, crypto=null_crypto)
        assert loaded.paperless.token == "mysecret"

    def test_empty_token_not_encrypted(self, config_path, null_crypto):
        config = Config()
        config.paperless.token = ""
        save_config(config, config_path, crypto=null_crypto)
        loaded = load_config(config_path, crypto=null_crypto)
        assert loaded.paperless.token == ""

    def test_save_without_crypto_stores_token_as_is(self, config_path):
        config = Config()
        config.paperless.token = "plaintexttoken"
        save_config(config, config_path)

        content = config_path.read_text(encoding="utf-8")
        assert "plaintexttoken" in content


class TestValidation:
    def test_empty_data_no_errors(self):
        assert validate_config({}) == []

    def test_valid_full_config_no_errors(self):
        data = {
            "config_version": 1,
            "paperless": {"url": "", "auth_mode": "token", "token": ""},
            "log4om": {"db_path": "", "own_callsign": ""},
            "tags": {"input": "qsl-card", "confirmed": "ok", "uncertain": "no"},
            "matching": {"fuzzy_enabled": True},
            "confirm": {"qsl_route_default": "undefined"},
            "app": {"language": "de", "backup_count": 5, "update_check": True},
        }
        assert validate_config(data) == []

    def test_invalid_auth_mode(self):
        errors = validate_config({"paperless": {"auth_mode": "oauth2"}})
        assert any("auth_mode" in e for e in errors)

    def test_invalid_language(self):
        errors = validate_config({"app": {"language": "fr"}})
        assert any("language" in e for e in errors)

    def test_invalid_qsl_route(self):
        errors = validate_config({"confirm": {"qsl_route_default": "electronic"}})
        assert any("qsl_route_default" in e for e in errors)

    def test_negative_backup_count(self):
        errors = validate_config({"app": {"backup_count": -1}})
        assert any("backup_count" in e for e in errors)

    def test_backup_count_zero_valid(self):
        assert validate_config({"app": {"backup_count": 0}}) == []

    def test_paperless_not_dict(self):
        errors = validate_config({"paperless": "invalid"})
        assert any("paperless" in e for e in errors)

    def test_log4om_not_dict(self):
        errors = validate_config({"log4om": 42})
        assert any("log4om" in e for e in errors)

    def test_multiple_errors_returned(self):
        data = {
            "paperless": {"auth_mode": "bad"},
            "app": {"language": "xx"},
        }
        errors = validate_config(data)
        assert len(errors) >= 2

    def test_valid_auth_modes(self):
        for mode in ("token", "password"):
            errors = validate_config({"paperless": {"auth_mode": mode}})
            assert errors == [], f"auth_mode '{mode}' sollte gültig sein"

    def test_valid_languages(self):
        for lang in ("de", "en"):
            errors = validate_config({"app": {"language": lang}})
            assert errors == [], f"language '{lang}' sollte gültig sein"


class TestMigration:
    def test_no_version_set_to_current(self):
        data = {}
        result = migrate_config(data)
        assert result["config_version"] == CURRENT_VERSION

    def test_version_zero_set_to_current(self):
        data = {"config_version": 0}
        result = migrate_config(data)
        assert result["config_version"] == CURRENT_VERSION

    def test_current_version_unchanged(self):
        data = {"config_version": CURRENT_VERSION}
        result = migrate_config(data)
        assert result["config_version"] == CURRENT_VERSION

    def test_migration_preserves_other_fields(self):
        data = {"config_version": 0, "paperless": {"url": "https://test.example"}}
        result = migrate_config(data)
        assert result["paperless"]["url"] == "https://test.example"

    def test_old_config_migrated_on_load(self, config_path):
        # Datei ohne config_version simuliert eine alte Config
        old_data = {"paperless": {"url": "", "auth_mode": "token", "token": ""}}
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(yaml.dump(old_data), encoding="utf-8")

        config = load_config(config_path)
        assert config.config_version == CURRENT_VERSION


class TestLoadErrors:
    def test_missing_file(self, tmp_path):
        with pytest.raises(ConfigError, match="gelesen"):
            load_config(tmp_path / "nonexistent.yaml")

    def test_invalid_yaml(self, config_path):
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text("ungültig: yaml: [nicht geschlossen", encoding="utf-8")
        with pytest.raises(ConfigError, match="YAML"):
            load_config(config_path)

    def test_yaml_is_list_not_dict(self, config_path):
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text("- nur eine Liste\n", encoding="utf-8")
        with pytest.raises(ConfigError, match="Format"):
            load_config(config_path)

    def test_invalid_auth_mode_raises(self, config_path):
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(
            yaml.dump({"paperless": {"auth_mode": "ungültig"}}),
            encoding="utf-8",
        )
        with pytest.raises(ConfigError, match="auth_mode"):
            load_config(config_path)

    def test_error_message_lists_all_problems(self, config_path):
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(
            yaml.dump({
                "paperless": {"auth_mode": "bad"},
                "app": {"language": "xx"},
            }),
            encoding="utf-8",
        )
        with pytest.raises(ConfigError) as exc_info:
            load_config(config_path)
        msg = str(exc_info.value)
        assert "auth_mode" in msg
        assert "language" in msg
