import pytest
import yaml
from pathlib import Path

from qsl73.config import (
    Config,
    ConfigError,
    CURRENT_VERSION,
    TagsConfig,
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
        assert loaded.tags.ignored == "qsl-ignoriert"
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

    def test_save_token_without_crypto_raises(self, config_path):
        """Sicherheits-Regressionstest: Token mit gesetztem Wert und fehlendem
        Crypto-Backend führt zu ConfigError — kein stilles Speichern im Klartext.
        """
        config = Config()
        config.paperless.token = "plaintexttoken"
        with pytest.raises(ConfigError, match="Verschlüsselungs-Backend"):
            save_config(config, config_path)

    def test_save_token_without_crypto_does_not_write_plaintext(self, config_path):
        """Datei darf nach fehlgeschlagenem save_config keinen Klartext-Token enthalten."""
        config = Config()
        config.paperless.token = "plaintexttoken"
        try:
            save_config(config, config_path)
        except ConfigError:
            pass
        if config_path.exists():
            assert "plaintexttoken" not in config_path.read_text(encoding="utf-8")

    def test_save_empty_token_without_crypto_is_ok(self, config_path):
        """Leerer Token: kein Crypto-Backend nötig — Config-Speichern soll funktionieren."""
        config = Config()
        config.paperless.token = ""
        save_config(config, config_path)
        assert config_path.exists()


class TestValidation:
    def test_empty_data_no_errors(self):
        assert validate_config({}) == []

    def test_valid_full_config_no_errors(self):
        data = {
            "config_version": 1,
            "paperless": {"url": "", "auth_mode": "token", "token": ""},
            "log4om": {"db_path": "", "own_callsign": ""},
            "tags": {"input": "qsl-card", "confirmed": "ok", "ignored": "no"},
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


def test_matching_config_has_portable_suffixes_default():
    from qsl73.config import MatchingConfig
    mc = MatchingConfig()
    assert mc.portable_suffixes == ["P", "M", "MM", "AM", "QRP", "A", "R", "T"]


def test_load_config_with_portable_suffixes(config_path, null_crypto):
    import yaml
    from qsl73.config import load_config
    data = {"config_version": 1, "matching": {"fuzzy_enabled": True, "portable_suffixes": ["P", "QRP"]}}
    config_path.write_text(yaml.dump(data), encoding="utf-8")
    cfg = load_config(config_path)
    assert cfg.matching.portable_suffixes == ["P", "QRP"]


def test_load_config_portable_suffixes_default(config_path):
    import yaml
    from qsl73.config import load_config
    data = {"config_version": 1}
    config_path.write_text(yaml.dump(data), encoding="utf-8")
    cfg = load_config(config_path)
    assert cfg.matching.portable_suffixes == ["P", "M", "MM", "AM", "QRP", "A", "R", "T"]


# ---------------------------------------------------------------------------
# manual_match_limit — Config-Tests (ADR-0030)
# ---------------------------------------------------------------------------


def test_manual_match_limit_default():
    from qsl73.config import AppConfig
    assert AppConfig().manual_match_limit == 100


def test_manual_match_limit_round_trip(config_path):
    from qsl73.config import Config, save_config, load_config
    cfg = Config()
    cfg.app.manual_match_limit = 10
    save_config(cfg, config_path)
    loaded = load_config(config_path)
    assert loaded.app.manual_match_limit == 10


def test_manual_match_limit_zero_allowed(config_path):
    from qsl73.config import Config, save_config, load_config
    cfg = Config()
    cfg.app.manual_match_limit = 0
    save_config(cfg, config_path)
    loaded = load_config(config_path)
    assert loaded.app.manual_match_limit == 0


def test_manual_match_limit_negative_invalid():
    from qsl73.config import validate_config
    errors = validate_config({"app": {"manual_match_limit": -1}})
    assert any("manual_match_limit" in e for e in errors)


def test_manual_match_limit_migrate_adds_default():
    from qsl73.config import migrate_config
    data = {"config_version": 1, "app": {"language": "de"}}
    result = migrate_config(data)
    assert result["app"]["manual_match_limit"] == 100


def test_manual_match_limit_migrate_preserves_existing():
    from qsl73.config import migrate_config
    data = {"config_version": 1, "app": {"language": "de", "manual_match_limit": 50}}
    result = migrate_config(data)
    assert result["app"]["manual_match_limit"] == 50


# ---------------------------------------------------------------------------
# log_level — Config-Tests (Issue #26, ADR-0055)
# ---------------------------------------------------------------------------


def test_log_level_default():
    from qsl73.config import AppConfig
    assert AppConfig().log_level == "INFO"


def test_log_level_round_trip(config_path):
    from qsl73.config import Config, save_config, load_config
    for level in ("INFO", "WARNING", "DEBUG"):
        cfg = Config()
        cfg.app.log_level = level
        save_config(cfg, config_path)
        loaded = load_config(config_path)
        assert loaded.app.log_level == level


def test_log_level_invalid_value_raises(config_path):
    import yaml
    from qsl73.config import ConfigError, load_config
    config_path.write_text(
        yaml.dump({"config_version": 1, "app": {"log_level": "TRACE"}}),
        encoding="utf-8",
    )
    with pytest.raises(ConfigError, match="log_level"):
        load_config(config_path)


def test_log_level_invalid_validation_error():
    from qsl73.config import validate_config
    errors = validate_config({"app": {"log_level": "VERBOSE"}})
    assert any("log_level" in e for e in errors)


def test_log_level_valid_values_no_errors():
    from qsl73.config import validate_config
    for level in ("INFO", "WARNING", "DEBUG"):
        assert validate_config({"app": {"log_level": level}}) == []


def test_log_level_migrate_adds_default():
    from qsl73.config import migrate_config
    data = {"config_version": 1, "app": {"language": "de"}}
    result = migrate_config(data)
    assert result["app"]["log_level"] == "INFO"


def test_log_level_migrate_preserves_existing():
    from qsl73.config import migrate_config
    data = {"config_version": 1, "app": {"language": "de", "log_level": "WARNING"}}
    result = migrate_config(data)
    assert result["app"]["log_level"] == "WARNING"


def test_log_level_missing_field_loads_as_info(config_path):
    """Additive Migration: fehlendes app.log_level lädt ohne Fehler → INFO."""
    import yaml
    from qsl73.config import load_config
    config_path.write_text(
        yaml.dump({"config_version": 1, "app": {"language": "de"}}),
        encoding="utf-8",
    )
    cfg = load_config(config_path)
    assert cfg.app.log_level == "INFO"


# ---------------------------------------------------------------------------
# tags.ignored — Config-Tests (ADR-0059, ersetzt tags.uncertain)
# ---------------------------------------------------------------------------


def test_tags_ignored_default():
    assert TagsConfig().ignored == "qsl-ignoriert"


def test_tags_config_has_no_uncertain_field():
    """tags.uncertain wurde durch tags.ignored ersetzt (ADR-0059)."""
    assert not hasattr(TagsConfig(), "uncertain")


def test_v1_config_with_uncertain_migrates_to_ignored_default(config_path):
    """Alte v1-Config mit tags.uncertain lädt fehlerfrei; alter Wert wird NICHT übernommen."""
    import yaml
    data = {
        "config_version": 1,
        "tags": {"input": "qsl-card", "confirmed": "qsl-bestätigt", "uncertain": "alter-name"},
    }
    config_path.write_text(yaml.dump(data), encoding="utf-8")
    cfg = load_config(config_path)
    assert cfg.config_version == 2
    assert cfg.tags.ignored == "qsl-ignoriert"
    assert "alter-name" not in vars(cfg.tags).values()


def test_v1_config_without_tags_migrates_cleanly(config_path):
    """v1-Config ganz ohne tags-Block lädt fehlerfrei → Default-Tags."""
    import yaml
    data = {"config_version": 1}
    config_path.write_text(yaml.dump(data), encoding="utf-8")
    cfg = load_config(config_path)
    assert cfg.config_version == 2
    assert cfg.tags.ignored == "qsl-ignoriert"
    assert cfg.tags.input == "qsl-card"


def test_migrate_config_v1_to_v2_drops_uncertain_sets_ignored():
    data = {"config_version": 1, "tags": {"uncertain": "old"}}
    result = migrate_config(data)
    assert result["config_version"] == 2
    assert "uncertain" not in result["tags"]
    assert result["tags"]["ignored"] == "qsl-ignoriert"


def test_migrate_config_v1_preserves_existing_ignored_if_present():
    """Ist tags.ignored bereits gesetzt (untypischer Fall), bleibt der Wert erhalten."""
    data = {"config_version": 1, "tags": {"ignored": "schon-gesetzt"}}
    result = migrate_config(data)
    assert result["tags"]["ignored"] == "schon-gesetzt"


def test_current_version_config_round_trips_ignored_tag(config_path):
    cfg = Config()
    cfg.tags.ignored = "meine-ignorierliste"
    save_config(cfg, config_path)
    loaded = load_config(config_path)
    assert loaded.tags.ignored == "meine-ignorierliste"


# ---------------------------------------------------------------------------
# input_tag_cleanup_done — Config-Tests (Issue #41, additives Feld wie ADR-0055)
# ---------------------------------------------------------------------------


def test_input_tag_cleanup_done_default_false():
    from qsl73.config import AppConfig
    assert AppConfig().input_tag_cleanup_done is False


def test_input_tag_cleanup_done_round_trip(config_path):
    from qsl73.config import Config, save_config, load_config
    cfg = Config()
    cfg.app.input_tag_cleanup_done = True
    save_config(cfg, config_path)
    loaded = load_config(config_path)
    assert loaded.app.input_tag_cleanup_done is True


def test_input_tag_cleanup_done_migrate_adds_default_false():
    from qsl73.config import migrate_config
    data = {"config_version": 1, "app": {"language": "de"}}
    result = migrate_config(data)
    assert result["app"]["input_tag_cleanup_done"] is False


def test_input_tag_cleanup_done_migrate_preserves_existing():
    from qsl73.config import migrate_config
    data = {"config_version": 1, "app": {"language": "de", "input_tag_cleanup_done": True}}
    result = migrate_config(data)
    assert result["app"]["input_tag_cleanup_done"] is True


def test_input_tag_cleanup_done_missing_field_loads_as_false(config_path):
    """Additive Migration: alte Config ohne das Feld lädt fehlerfrei → False."""
    import yaml
    from qsl73.config import load_config
    config_path.write_text(
        yaml.dump({"config_version": 1, "app": {"language": "de"}}),
        encoding="utf-8",
    )
    cfg = load_config(config_path)
    assert cfg.app.input_tag_cleanup_done is False


def test_input_tag_cleanup_done_invalid_type_raises(config_path):
    import yaml
    from qsl73.config import ConfigError, load_config
    config_path.write_text(
        yaml.dump({"config_version": 1, "app": {"input_tag_cleanup_done": "ja"}}),
        encoding="utf-8",
    )
    with pytest.raises(ConfigError, match="input_tag_cleanup_done"):
        load_config(config_path)


def test_input_tag_cleanup_done_invalid_validation_error():
    from qsl73.config import validate_config
    errors = validate_config({"app": {"input_tag_cleanup_done": "ja"}})
    assert any("input_tag_cleanup_done" in e for e in errors)
