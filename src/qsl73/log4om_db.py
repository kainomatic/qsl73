"""
Orchestrierungs-/Sicherheitsschicht für Log4OM-DB-Schreibzugriff.

Schritt 5b — bettet write_paper_qsl (5a) in die Sicherheitsschicht ein:
Reihenfolge (ADR-0003): (1) Schema-Check → (2) Vor-Backup → (3) Transaktion.
Paperless-Tags (Schritt 4 in ADR-0003) sind NICHT Teil dieses Moduls.

Öffentliche Funktionen:
  validate_schema      — prüft DB-Schema gegen erwartetes Format
  open_wal_connection  — öffnet SQLite-Verbindung im WAL-Modus
  create_backup        — WAL-konsistentes Vor-Backup mit Rotation
  write_confirmations  — Sicherheits-Schreiborchester (Schema → Backup → Transaktion)

Empirische Basis: docs/discovery.md §3, ADR-0003, ADR-0004, ADR-0020.
"""
from __future__ import annotations

import json
import shutil
import sqlite3
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from qsl73.log4om_write import write_paper_qsl


class SchemaError(Exception):
    """Schema weicht vom erwarteten Format ab; Schreiben gesperrt."""


@dataclass
class WriteResult:
    written: int
    skipped: list = field(default_factory=list)  # [{"qsoid": str, "reason": str}]


def validate_schema(conn: sqlite3.Connection) -> str | None:
    """Prüft ob Log4OM-DB-Schema dem erwarteten Format entspricht.

    Ablauf:
    (1) Tabelle Log vorhanden?
    (2) Spalte qsoconfirmations vorhanden?
    (3) Stichprobe: mind. eine Zeile mit parsebarem JSON und CT='QSL'-Eintrag mit R-Feld.

    Returns:
        None wenn Schema OK; menschenlesbare Abweichungsbeschreibung sonst.
    """
    # 1. Tabelle Log vorhanden?
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='Log'"
    ).fetchone()
    if not row:
        return "Tabelle 'Log' nicht in der Datenbank gefunden"

    # 2. Spalte qsoconfirmations vorhanden?
    cols = {r[1] for r in conn.execute("PRAGMA table_info(Log)").fetchall()}
    if "qsoconfirmations" not in cols:
        return "Spalte 'qsoconfirmations' fehlt in Tabelle 'Log'"

    # 3. Stichprobe: mind. eine Zeile parsebar mit CT='QSL' + R-Feld
    rows = conn.execute(
        "SELECT qsoconfirmations FROM Log WHERE qsoconfirmations IS NOT NULL LIMIT 30"
    ).fetchall()
    if not rows:
        return None  # Leere DB: Schema-Prüfung ohne Stichprobe bestanden

    for (json_str,) in rows:
        try:
            entries = json.loads(json_str)
        except (json.JSONDecodeError, TypeError):
            return f"qsoconfirmations-Wert ist kein gültiges JSON: {json_str[:80]!r}"

        if not isinstance(entries, list):
            return (
                f"qsoconfirmations-Wert ist kein JSON-Array, "
                f"sondern {type(entries).__name__!r}"
            )

        for entry in entries:
            if isinstance(entry, dict) and entry.get("CT") == "QSL" and "R" in entry:
                return None  # Gültige Stichprobe gefunden

    return (
        "Keine Zeile in Log enthält einen CT='QSL'-Eintrag mit erwartetem R-Feld — "
        "Schema weicht ab (Log4OM-Version zu alt oder DB-Format geändert)"
    )


def open_wal_connection(db_path: str | Path) -> sqlite3.Connection:
    """Öffnet SQLite-Verbindung im WAL-Modus."""
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def create_backup(db_path: Path, backup_dir: Path, max_count: int = 5) -> Path:
    """WAL-konsistentes Vor-Backup der DB-Datei (ADR-0020).

    Strategie: PRAGMA wal_checkpoint(FULL) auf getrennter Verbindung,
    dann Datei kopieren. Danach Rotation: nur die neuesten max_count Backups behalten.

    Args:
        db_path: Pfad zur Log4OM-SQLite-Datei.
        backup_dir: Zielverzeichnis für Backups (wird angelegt wenn nötig).
        max_count: Maximale Anzahl aufbewahrter Backups (Default 5).

    Returns:
        Pfad zur erzeugten Backup-Datei.
    """
    backup_dir.mkdir(parents=True, exist_ok=True)

    # WAL-Checkpoint: alle offenen WAL-Frames in Hauptdatei schreiben (ADR-0020)
    chk_conn = sqlite3.connect(str(db_path))
    try:
        chk_conn.execute("PRAGMA wal_checkpoint(FULL)")
    finally:
        chk_conn.close()

    # Datei kopieren — uuid4-Suffix sichert Eindeutigkeit bei Schnellaufrufen
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    unique = uuid.uuid4().hex[:8]
    dst = backup_dir / f"log4om_{timestamp}_{unique}.sqlite"
    shutil.copy2(str(db_path), str(dst))

    # Rotation: älteste Backups löschen bis max_count
    backups = sorted(backup_dir.glob("log4om_*.sqlite"))
    for old in backups[:-max_count]:
        old.unlink(missing_ok=True)

    return dst


def write_confirmations(
    db_path: str | Path,
    items: list[tuple[str, str]],
    backup_dir: Path,
    backup_count: int = 5,
) -> WriteResult:
    """Sicherheits-Schreiborchester: Schema-Check → Backup → atomare Transaktion.

    Reihenfolge (ADR-0003):
      (1) Schema-Check → bei Abweichung: SchemaError, kein Backup, keine Transaktion.
      (2) Vor-Backup → WAL-konsistente Kopie vor dem Schreiben (nur wenn items nicht leer).
      (3) DB-Transaktion → BEGIN/COMMIT für alle items, bei JEDEM Fehler ROLLBACK.

    Schritt 4 (Paperless-Tags) ist NICHT Teil dieser Funktion (→ ADR-0003, GUI/5c).
    Nebenläufigkeit (SQLITE_BUSY, data_version, Pro-QSO-Check) kommt in 5c.

    Args:
        db_path: Pfad zur Log4OM-SQLite-Datei.
        items: Liste von (qsoid, route)-Paaren. Leere Liste = no-op.
        backup_dir: Zielverzeichnis für Vor-Backups.
        backup_count: Maximale Anzahl aufbewahrter Backups (Default 5).

    Returns:
        WriteResult mit Anzahl geschriebener QSOs und leerer skipped-Liste (5b).

    Raises:
        SchemaError: Schema weicht ab — kein Backup, keine Schreibung.
        ValueError: qsoid nicht in DB oder JSON-Fehler → ROLLBACK aller items.
        QslEntryNotFoundError: CT='QSL'-Eintrag fehlt → ROLLBACK aller items.
    """
    db_path = Path(db_path)
    conn = open_wal_connection(db_path)
    try:
        # (1) Schema-Check — bei Abweichung kein Backup, keine Transaktion
        deviation = validate_schema(conn)
        if deviation:
            raise SchemaError(deviation)

        # (2) Vor-Backup — nur bei tatsächlichem Schreiben (ADR-0003)
        if items:
            create_backup(db_path, backup_dir, max_count=backup_count)

        # (3) Atomare Transaktion
        try:
            conn.execute("BEGIN")
            for qsoid, route in items:
                write_paper_qsl(conn, qsoid, route)
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise

        return WriteResult(written=len(items), skipped=[])
    finally:
        conn.close()
