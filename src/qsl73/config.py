import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from qsl73.crypto import CryptoBackend

CURRENT_VERSION = 1

VALID_AUTH_MODES = {"token", "password"}
VALID_LANGUAGES = {"de", "en"}
VALID_QSL_ROUTES = {"undefined", "bureau", "direct"}


class ConfigError(Exception):
    pass


@dataclass
class PaperlessConfig:
    url: str = ""
    auth_mode: str = "token"
    token: str = ""


@dataclass
class Log4OMConfig:
    db_path: str = ""
    own_callsign: str = ""


@dataclass
class TagsConfig:
    input: str = "qsl-card"
    confirmed: str = "qsl-bestätigt"
    uncertain: str = "qsl-nicht-bestätigt"


@dataclass
class MatchingConfig:
    fuzzy_enabled: bool = True
    portable_suffixes: list = field(default_factory=lambda: ["P", "M", "MM", "AM", "QRP", "A", "R", "T"])


@dataclass
class ConfirmConfig:
    qsl_route_default: str = "undefined"


@dataclass
class AppConfig:
    language: str = "de"
    backup_count: int = 5
    update_check: bool = True


@dataclass
class Config:
    config_version: int = CURRENT_VERSION
    paperless: PaperlessConfig = field(default_factory=PaperlessConfig)
    log4om: Log4OMConfig = field(default_factory=Log4OMConfig)
    tags: TagsConfig = field(default_factory=TagsConfig)
    matching: MatchingConfig = field(default_factory=MatchingConfig)
    confirm: ConfirmConfig = field(default_factory=ConfirmConfig)
    app: AppConfig = field(default_factory=AppConfig)


def get_config_dir() -> Path:
    appdata = os.environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming"))
    return Path(appdata) / "QSL73"


def get_config_path() -> Path:
    return get_config_dir() / "config.yaml"


def validate_config(data: dict) -> list[str]:
    """Gibt Liste von Fehlermeldungen zurück (leer = gültig)."""
    errors: list[str] = []

    paperless = data.get("paperless", {})
    if not isinstance(paperless, dict):
        errors.append("paperless: muss ein Objekt sein")
    else:
        auth_mode = paperless.get("auth_mode", "token")
        if auth_mode not in VALID_AUTH_MODES:
            errors.append(
                f"paperless.auth_mode: ungültiger Wert '{auth_mode}' "
                f"(erlaubt: {', '.join(sorted(VALID_AUTH_MODES))})"
            )

    log4om = data.get("log4om", {})
    if not isinstance(log4om, dict):
        errors.append("log4om: muss ein Objekt sein")

    tags = data.get("tags", {})
    if not isinstance(tags, dict):
        errors.append("tags: muss ein Objekt sein")

    matching = data.get("matching", {})
    if not isinstance(matching, dict):
        errors.append("matching: muss ein Objekt sein")
    else:
        fuzzy = matching.get("fuzzy_enabled", True)
        if not isinstance(fuzzy, bool):
            errors.append("matching.fuzzy_enabled: muss true oder false sein")
        ps = matching.get("portable_suffixes", [])
        if not isinstance(ps, list):
            errors.append("matching.portable_suffixes: muss eine Liste sein")

    confirm = data.get("confirm", {})
    if not isinstance(confirm, dict):
        errors.append("confirm: muss ein Objekt sein")
    else:
        route = confirm.get("qsl_route_default", "undefined")
        if route not in VALID_QSL_ROUTES:
            errors.append(
                f"confirm.qsl_route_default: ungültiger Wert '{route}' "
                f"(erlaubt: {', '.join(sorted(VALID_QSL_ROUTES))})"
            )

    app = data.get("app", {})
    if not isinstance(app, dict):
        errors.append("app: muss ein Objekt sein")
    else:
        lang = app.get("language", "de")
        if lang not in VALID_LANGUAGES:
            errors.append(
                f"app.language: ungültiger Wert '{lang}' "
                f"(erlaubt: {', '.join(sorted(VALID_LANGUAGES))})"
            )
        backup_count = app.get("backup_count", 5)
        if not isinstance(backup_count, int) or backup_count < 0:
            errors.append("app.backup_count: muss eine nicht-negative ganze Zahl sein")

    return errors


def migrate_config(data: dict) -> dict:
    """Migriert config-Dict auf CURRENT_VERSION. Verändert das übergebene Dict."""
    version = data.get("config_version", 0)

    if version < 1:
        # Version 0/fehlend → 1: nur config_version-Feld setzen
        data["config_version"] = 1

    # Künftige Migrationen: elif version < 2: ... hier einfügen

    return data


def _dict_to_config(data: dict) -> Config:
    p = data.get("paperless", {}) or {}
    lo = data.get("log4om", {}) or {}
    t = data.get("tags", {}) or {}
    m = data.get("matching", {}) or {}
    c = data.get("confirm", {}) or {}
    a = data.get("app", {}) or {}

    return Config(
        config_version=data.get("config_version", CURRENT_VERSION),
        paperless=PaperlessConfig(
            url=p.get("url", ""),
            auth_mode=p.get("auth_mode", "token"),
            token=p.get("token", ""),
        ),
        log4om=Log4OMConfig(
            db_path=lo.get("db_path", ""),
            own_callsign=lo.get("own_callsign", ""),
        ),
        tags=TagsConfig(
            input=t.get("input", "qsl-card"),
            confirmed=t.get("confirmed", "qsl-bestätigt"),
            uncertain=t.get("uncertain", "qsl-nicht-bestätigt"),
        ),
        matching=MatchingConfig(
            fuzzy_enabled=m.get("fuzzy_enabled", True),
            portable_suffixes=m.get("portable_suffixes", ["P", "M", "MM", "AM", "QRP", "A", "R", "T"]),
        ),
        confirm=ConfirmConfig(
            qsl_route_default=c.get("qsl_route_default", "undefined"),
        ),
        app=AppConfig(
            language=a.get("language", "de"),
            backup_count=a.get("backup_count", 5),
            update_check=a.get("update_check", True),
        ),
    )


def _config_to_dict(config: Config) -> dict:
    return {
        "config_version": config.config_version,
        "paperless": {
            "url": config.paperless.url,
            "auth_mode": config.paperless.auth_mode,
            "token": config.paperless.token,
        },
        "log4om": {
            "db_path": config.log4om.db_path,
            "own_callsign": config.log4om.own_callsign,
        },
        "tags": {
            "input": config.tags.input,
            "confirmed": config.tags.confirmed,
            "uncertain": config.tags.uncertain,
        },
        "matching": {
            "fuzzy_enabled": config.matching.fuzzy_enabled,
            "portable_suffixes": config.matching.portable_suffixes,
        },
        "confirm": {
            "qsl_route_default": config.confirm.qsl_route_default,
        },
        "app": {
            "language": config.app.language,
            "backup_count": config.app.backup_count,
            "update_check": config.app.update_check,
        },
    }


def load_config(path: Path, crypto: CryptoBackend | None = None) -> Config:
    """Lädt Config aus YAML-Datei. Entschlüsselt Token wenn crypto angegeben.

    Wirft ConfigError bei Lese-, Parse- oder Validierungsfehlern.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ConfigError(
            f"Konfigurationsdatei konnte nicht gelesen werden: {exc}"
        ) from exc

    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise ConfigError(
            f"Konfigurationsdatei enthält ungültiges YAML: {exc}"
        ) from exc

    if not isinstance(data, dict):
        raise ConfigError(
            "Konfigurationsdatei hat kein gültiges Format (erwartet: YAML-Objekt)"
        )

    data = migrate_config(data)

    errors = validate_config(data)
    if errors:
        msg = "Konfiguration enthält Fehler:\n" + "\n".join(f"  • {e}" for e in errors)
        raise ConfigError(msg)

    config = _dict_to_config(data)

    if crypto and config.paperless.token:
        try:
            config.paperless.token = crypto.decrypt(config.paperless.token)
        except Exception as exc:
            raise ConfigError(
                f"Paperless-Token konnte nicht entschlüsselt werden: {exc}"
            ) from exc

    return config


def save_config(config: Config, path: Path, crypto: CryptoBackend | None = None) -> None:
    """Speichert Config als YAML-Datei. Verschlüsselt Token wenn crypto angegeben.

    Legt übergeordnete Verzeichnisse an falls nötig.
    Wirft ConfigError wenn ein Token gesetzt ist aber kein Crypto-Backend übergeben wurde
    (fail closed: Token wird nie unverschlüsselt persistiert).
    """
    path.parent.mkdir(parents=True, exist_ok=True)

    data = _config_to_dict(config)

    if data["paperless"]["token"] and not crypto:
        raise ConfigError(
            "Token ist gesetzt, aber kein Verschlüsselungs-Backend angegeben. "
            "Übergebe ein CryptoBackend-Objekt (crypto=...), um den Token sicher "
            "zu speichern. Auf Windows: get_default_backend() liefert DPAPI."
        )

    if crypto and data["paperless"]["token"]:
        data["paperless"]["token"] = crypto.encrypt(data["paperless"]["token"])

    try:
        text = yaml.dump(data, allow_unicode=True, default_flow_style=False, sort_keys=True)
        path.write_text(text, encoding="utf-8")
    except OSError as exc:
        raise ConfigError(
            f"Konfigurationsdatei konnte nicht geschrieben werden: {exc}"
        ) from exc
