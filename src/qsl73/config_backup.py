# QSL73 — Copyright (C) 2026 DF1DS (kainomatic) — SPDX-License-Identifier: GPL-3.0-or-later
"""Rotierende Sicherungen von config.yaml vor jedem Überschreiben (ADR-0033)."""
import os
import shutil
import uuid
from datetime import datetime
from pathlib import Path


def get_config_backup_dir() -> Path:
    """Gibt %APPDATA%\\QSL73\\config_backups\\ zurück."""
    appdata = os.environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming"))
    return Path(appdata) / "QSL73" / "config_backups"


def _backup_filename(ts: datetime | None = None) -> str:
    """Format: config_YYYYMMDD_HHMMSS_<8-hex-UUID>.yaml — garantiert eindeutig."""
    t = ts or datetime.now()
    unique = uuid.uuid4().hex[:8]
    return t.strftime(f"config_%Y%m%d_%H%M%S_{unique}.yaml")


def create_config_backup(
    config_path: Path,
    backup_count: int = 5,
    backup_dir: Path | None = None,
) -> Path | None:
    """Sichert config_path in backup_dir, rotiert älteste Backups.

    Gibt Backup-Pfad zurück oder None wenn config_path nicht existiert.
    Kopiert nur die bereits verschlüsselte Datei — kein Klartext-Token.

    backup_count=0 bedeutet: kein Rotationslimit (alle behalten).
    """
    if not config_path.exists():
        return None

    target_dir = backup_dir if backup_dir is not None else get_config_backup_dir()
    target_dir.mkdir(parents=True, exist_ok=True)

    dest = target_dir / _backup_filename()
    shutil.copy2(config_path, dest)

    # Rotation: älteste überzählige Backups löschen (backup_count=0 → behalte alle)
    existing = sorted(target_dir.glob("config_*.yaml"))
    for old in existing[:-backup_count] if backup_count > 0 else []:
        old.unlink(missing_ok=True)

    return dest


def list_config_backups(backup_dir: Path | None = None) -> list[Path]:
    """Gibt Backup-Dateien zurück, neueste zuerst."""
    target_dir = backup_dir if backup_dir is not None else get_config_backup_dir()
    if not target_dir.exists():
        return []
    return list(sorted(target_dir.glob("config_*.yaml"), reverse=True))


def restore_config_backup(backup_path: Path, config_path: Path) -> None:
    """Kopiert backup_path → config_path (überschreibt aktive config.yaml)."""
    config_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(backup_path, config_path)
