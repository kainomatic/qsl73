import pytest

from qsl73.config import Config, save_config, load_config
from qsl73.crypto import NullBackend
from qsl73.setup_assistant import SetupNeeded, load_or_trigger_setup, create_initial_config


class TestLoadOrTriggerSetup:
    def test_missing_config_raises_setup_needed(self, tmp_path, null_crypto):
        path = tmp_path / "config.yaml"
        with pytest.raises(SetupNeeded):
            load_or_trigger_setup(config_path=path, crypto=null_crypto)

    def test_setup_needed_message_mentions_path(self, tmp_path, null_crypto):
        path = tmp_path / "config.yaml"
        with pytest.raises(SetupNeeded, match="config.yaml"):
            load_or_trigger_setup(config_path=path, crypto=null_crypto)

    def test_valid_config_returns_config(self, tmp_path, null_crypto):
        path = tmp_path / "config.yaml"
        save_config(Config(), path, crypto=null_crypto)

        result = load_or_trigger_setup(config_path=path, crypto=null_crypto)
        assert isinstance(result, Config)

    def test_valid_config_values_preserved(self, tmp_path, null_crypto):
        path = tmp_path / "config.yaml"
        config = Config()
        config.log4om.own_callsign = "DF1DS"
        save_config(config, path, crypto=null_crypto)

        result = load_or_trigger_setup(config_path=path, crypto=null_crypto)
        assert result.log4om.own_callsign == "DF1DS"

    def test_invalid_config_raises_setup_needed(self, tmp_path, null_crypto):
        path = tmp_path / "config.yaml"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("paperless:\n  auth_mode: ungueltig\n", encoding="utf-8")

        with pytest.raises(SetupNeeded):
            load_or_trigger_setup(config_path=path, crypto=null_crypto)

    def test_setup_needed_is_exception(self, tmp_path, null_crypto):
        path = tmp_path / "missing.yaml"
        exc = None
        try:
            load_or_trigger_setup(config_path=path, crypto=null_crypto)
        except SetupNeeded as e:
            exc = e
        assert isinstance(exc, SetupNeeded)


class TestCreateInitialConfig:
    def test_creates_config_file(self, tmp_path, null_crypto):
        path = tmp_path / "config.yaml"
        create_initial_config(path=path, crypto=null_crypto)
        assert path.exists()

    def test_created_config_is_loadable(self, tmp_path, null_crypto):
        path = tmp_path / "config.yaml"
        create_initial_config(path=path, crypto=null_crypto)
        loaded = load_config(path)
        assert isinstance(loaded, Config)

    def test_returns_config_object(self, tmp_path, null_crypto):
        path = tmp_path / "config.yaml"
        result = create_initial_config(path=path, crypto=null_crypto)
        assert isinstance(result, Config)

    def test_overrides_applied_in_memory(self, tmp_path, null_crypto):
        path = tmp_path / "config.yaml"
        result = create_initial_config(
            path=path,
            crypto=null_crypto,
            overrides={"log4om.own_callsign": "DL1ABC"},
        )
        assert result.log4om.own_callsign == "DL1ABC"

    def test_overrides_persisted_to_disk(self, tmp_path, null_crypto):
        path = tmp_path / "config.yaml"
        create_initial_config(
            path=path,
            crypto=null_crypto,
            overrides={"log4om.own_callsign": "DL1ABC"},
        )
        loaded = load_config(path)
        assert loaded.log4om.own_callsign == "DL1ABC"

    def test_multiple_overrides(self, tmp_path, null_crypto):
        path = tmp_path / "config.yaml"
        create_initial_config(
            path=path,
            crypto=null_crypto,
            overrides={
                "log4om.own_callsign": "DF1DS",
                "confirm.qsl_route_default": "direct",
                "app.language": "en",
            },
        )
        loaded = load_config(path)
        assert loaded.log4om.own_callsign == "DF1DS"
        assert loaded.confirm.qsl_route_default == "direct"
        assert loaded.app.language == "en"

    def test_creates_parent_dirs(self, tmp_path, null_crypto):
        path = tmp_path / "nested" / "dirs" / "config.yaml"
        create_initial_config(path=path, crypto=null_crypto)
        assert path.exists()

    def test_no_overrides_uses_defaults(self, tmp_path, null_crypto):
        path = tmp_path / "config.yaml"
        result = create_initial_config(path=path, crypto=null_crypto)
        assert result.app.language == "de"
        assert result.confirm.qsl_route_default == "undefined"
        assert result.matching.fuzzy_enabled is True
