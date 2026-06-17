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
