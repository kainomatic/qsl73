from pathlib import Path

from qsl73.config import Config, ConfigError, get_config_path, load_config, save_config
from qsl73.crypto import CryptoBackend, get_default_backend


class SetupNeeded(Exception):
    """Wird ausgelöst wenn keine gültige Konfiguration vorhanden ist.
    Die GUI (Schritt 6) fängt diese Exception und startet den Setup-Assistenten.
    """


def load_or_trigger_setup(
    config_path: Path | None = None,
    crypto: CryptoBackend | None = None,
) -> Config:
    """Lädt Config. Wirft SetupNeeded wenn Config fehlt oder ungültig ist."""
    path = config_path or get_config_path()
    backend = crypto if crypto is not None else get_default_backend()

    if not path.exists():
        raise SetupNeeded(
            f"Keine Konfigurationsdatei gefunden ({path}). "
            "Der Setup-Assistent wird gestartet."
        )

    try:
        return load_config(path, crypto=backend)
    except ConfigError as exc:
        raise SetupNeeded(
            f"Konfigurationsdatei fehlerhaft: {exc}. "
            "Der Setup-Assistent wird gestartet."
        ) from exc


def create_initial_config(
    path: Path | None = None,
    crypto: CryptoBackend | None = None,
    overrides: dict | None = None,
) -> Config:
    """Erstellt Default-Config, wendet optionale Overrides an, speichert und gibt sie zurück."""
    config = Config()

    if overrides:
        _apply_overrides(config, overrides)

    target = path or get_config_path()
    backend = crypto if crypto is not None else get_default_backend()
    save_config(config, target, crypto=backend)
    return config


_OVERRIDE_MAP = {
    "paperless.url": lambda cfg, v: setattr(cfg.paperless, "url", v),
    "paperless.auth_mode": lambda cfg, v: setattr(cfg.paperless, "auth_mode", v),
    "paperless.token": lambda cfg, v: setattr(cfg.paperless, "token", v),
    "log4om.db_path": lambda cfg, v: setattr(cfg.log4om, "db_path", v),
    "log4om.own_callsign": lambda cfg, v: setattr(cfg.log4om, "own_callsign", v),
    "tags.input": lambda cfg, v: setattr(cfg.tags, "input", v),
    "tags.confirmed": lambda cfg, v: setattr(cfg.tags, "confirmed", v),
    "tags.uncertain": lambda cfg, v: setattr(cfg.tags, "uncertain", v),
    "matching.fuzzy_enabled": lambda cfg, v: setattr(cfg.matching, "fuzzy_enabled", v),
    "confirm.qsl_route_default": lambda cfg, v: setattr(cfg.confirm, "qsl_route_default", v),
    "app.language": lambda cfg, v: setattr(cfg.app, "language", v),
    "app.backup_count": lambda cfg, v: setattr(cfg.app, "backup_count", v),
    "app.update_check": lambda cfg, v: setattr(cfg.app, "update_check", v),
}


def _apply_overrides(config: Config, overrides: dict) -> None:
    for key, value in overrides.items():
        if key in _OVERRIDE_MAP:
            _OVERRIDE_MAP[key](config, value)
