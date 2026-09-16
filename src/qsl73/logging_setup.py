# QSL73 — Copyright (C) 2026 DF1DS (kainomatic) — SPDX-License-Identifier: GPL-3.0-or-later
"""Logging-Initialisierung für QSL73 (ADR-0026).

setup_logging() einmalig beim App-Start aufrufen (vor allem anderen).
Konfiguriert den "qsl73"-Logger mit RotatingFileHandler auf
%APPDATA%/QSL73/logs/qsl73.log (Stable) bzw. QSL73-Beta/logs/ (Beta).

Level: INFO default; QSL73_DEBUG=1 hebt auf DEBUG an.
"""
from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

_LEVEL_NAMES = {"INFO": logging.INFO, "WARNING": logging.WARNING, "DEBUG": logging.DEBUG}


def _level_from_name(name: str | None) -> int:
    """Wandelt einen Config-Level-Namen in ein logging-Level um. Unbekannt → INFO."""
    if isinstance(name, str) and name.strip().upper() in _LEVEL_NAMES:
        return _LEVEL_NAMES[name.strip().upper()]
    return logging.INFO


def effective_level(env_debug: str | None, config_level_name: str) -> int:
    """Bestimmt das effektive Log-Level aus QSL73_DEBUG und app.log_level (ADR-0055).

    QSL73_DEBUG kann das Level nur ANHEBEN (gesprächiger machen), nie absenken:
    gesetzt und nicht ""/"0" → mindestens DEBUG. Sonst gilt exakt config_level_name.
    Unbekannter config_level_name → Fallback INFO.
    """
    config_level = _level_from_name(config_level_name)
    env_active = env_debug is not None and env_debug.strip() not in ("", "0")
    if env_active:
        return min(logging.DEBUG, config_level)
    return config_level


def apply_log_level(level_name: str) -> None:
    """Setzt das effektive Log-Level (ADR-0055) auf den 'qsl73'-Logger und seine Handler.

    Wird NACH dem Config-Laden aufgerufen (nachträgliches Anheben/Senken, kein Umbau
    der frühen setup_logging()-Initialisierung). Hebt QSL73_DEBUG das konfigurierte
    Level an, wird ein Hinweis ins Log geschrieben (V2) — sonst rätselt der Nutzer,
    warum trotz gewähltem Level DEBUG-Zeilen erscheinen.
    """
    env_debug = os.environ.get("QSL73_DEBUG")
    config_level = _level_from_name(level_name)
    eff = effective_level(env_debug, level_name)

    logger = logging.getLogger("qsl73")
    logger.setLevel(eff)
    for handler in logger.handlers:
        handler.setLevel(eff)

    if eff < config_level:
        logger.info(
            "Log-Level durch QSL73_DEBUG auf DEBUG angehoben (Config: %s)",
            logging.getLevelName(config_level),
        )


def get_log_dir() -> Path:
    """Gibt Log-Verzeichnis zurück — Stable: QSL73, Beta: QSL73-Beta."""
    from qsl73.__version__ import CHANNEL

    appdata = os.environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming"))
    folder = "QSL73-Beta" if CHANNEL == "beta" else "QSL73"
    return Path(appdata) / folder / "logs"


def setup_logging(log_dir: Path | None = None, debug: bool = False) -> Path:
    """Konfiguriert den 'qsl73'-Logger mit rotierendem Datei-Handler.

    Idempotent: bei erneutem Aufruf wird kein zweiter Handler hinzugefügt.

    Args:
        log_dir: Verzeichnis für qsl73.log. Default: get_log_dir().
        debug: True → Level DEBUG (überschreibt QSL73_DEBUG-Env-Variable).

    Returns:
        Absoluter Pfad zum Log-Verzeichnis (für "Log-Ordner öffnen", §9).
    """
    if log_dir is None:
        log_dir = get_log_dir()
    log_dir.mkdir(parents=True, exist_ok=True)

    log_path = log_dir / "qsl73.log"
    logger = logging.getLogger("qsl73")

    if any(isinstance(h, RotatingFileHandler) for h in logger.handlers):
        return log_dir

    use_debug = debug or os.environ.get("QSL73_DEBUG", "").strip() not in ("", "0")
    level = logging.DEBUG if use_debug else logging.INFO
    logger.setLevel(level)

    handler = RotatingFileHandler(
        log_path,
        maxBytes=1 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    handler.setLevel(level)
    handler.setFormatter(logging.Formatter(
        "%(asctime)s %(levelname)-8s %(module)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))
    logger.addHandler(handler)
    logger.propagate = False

    return log_dir
