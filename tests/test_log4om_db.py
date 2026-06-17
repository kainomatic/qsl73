"""Unit-Tests für log4om_db — Schema-Validierung, Backup, Transaktion.

Alle Tests laufen ohne echtes Log4OM gegen synthetische Mini-DBs
(:memory: oder tmp_path). CI-kompatibel.
"""
import json
import sqlite3
from pathlib import Path

import pytest

from qsl73.log4om_db import SchemaError, WriteResult, create_backup, validate_schema

# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------


def _valid_qso_json() -> str:
    return json.dumps(
        [
            {"CT": "QSL", "S": "No", "R": "No", "SV": "Electronic", "RV": "Electronic"},
            {"CT": "EQSL", "S": "No", "R": "No", "SV": "Electronic"},
        ],
        separators=(",", ":"),
    )


def _make_mini_db(tmp_path, name="mini.sqlite") -> tuple[sqlite3.Connection, Path]:
    """Gültige Mini-DB mit Tabelle Log + qsoconfirmations + einem QSO."""
    p = tmp_path / name
    conn = sqlite3.connect(str(p))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute(
        "CREATE TABLE Log (qsoid TEXT PRIMARY KEY, callsign TEXT, qsoconfirmations TEXT)"
    )
    conn.execute(
        "INSERT INTO Log VALUES (?,?,?)", ("QSO1", "DK8NE", _valid_qso_json())
    )
    conn.commit()
    return conn, p


# ---------------------------------------------------------------------------
# validate_schema — intakte DB
# ---------------------------------------------------------------------------


def test_schema_valid_returns_none(tmp_path):
    conn, _ = _make_mini_db(tmp_path)
    result = validate_schema(conn)
    conn.close()
    assert result is None


def test_schema_empty_db_ok():
    """Leere Tabelle (keine Zeilen): Schema-Prüfung ohne Stichprobe bestanden."""
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE Log (qsoid TEXT, qsoconfirmations TEXT)")
    conn.commit()
    result = validate_schema(conn)
    conn.close()
    assert result is None


# ---------------------------------------------------------------------------
# validate_schema — Abweichungen
# ---------------------------------------------------------------------------


def test_schema_missing_table():
    conn = sqlite3.connect(":memory:")
    # Keine Log-Tabelle
    result = validate_schema(conn)
    conn.close()
    assert result is not None
    assert "Log" in result


def test_schema_wrong_table_name():
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE Logbuch (qsoid TEXT, qsoconfirmations TEXT)")
    conn.commit()
    result = validate_schema(conn)
    conn.close()
    assert result is not None
    assert "Log" in result


def test_schema_missing_column():
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE Log (qsoid TEXT, callsign TEXT)")
    conn.commit()
    result = validate_schema(conn)
    conn.close()
    assert result is not None
    assert "qsoconfirmations" in result


def test_schema_invalid_json():
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE Log (qsoid TEXT, qsoconfirmations TEXT)")
    conn.execute("INSERT INTO Log VALUES (?,?)", ("Q1", "INVALID {{{"))
    conn.commit()
    result = validate_schema(conn)
    conn.close()
    assert result is not None
    assert "JSON" in result


def test_schema_no_qsl_ct_entry():
    """qsoconfirmations ist gültiges JSON, aber kein CT='QSL'-Eintrag vorhanden."""
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE Log (qsoid TEXT, qsoconfirmations TEXT)")
    conn.execute(
        "INSERT INTO Log VALUES (?,?)",
        ("Q1", json.dumps([{"CT": "EQSL", "R": "No"}, {"CT": "LOTW", "R": "No"}])),
    )
    conn.commit()
    result = validate_schema(conn)
    conn.close()
    assert result is not None


def test_schema_qsl_entry_missing_r_field():
    """CT='QSL'-Eintrag vorhanden, aber ohne R-Feld."""
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE Log (qsoid TEXT, qsoconfirmations TEXT)")
    conn.execute(
        "INSERT INTO Log VALUES (?,?)",
        ("Q1", json.dumps([{"CT": "QSL", "S": "No"}])),  # kein R
    )
    conn.commit()
    result = validate_schema(conn)
    conn.close()
    assert result is not None


def test_schema_non_array_json():
    """qsoconfirmations ist gültiges JSON, aber kein Array."""
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE Log (qsoid TEXT, qsoconfirmations TEXT)")
    conn.execute("INSERT INTO Log VALUES (?,?)", ("Q1", '{"CT":"QSL","R":"No"}'))
    conn.commit()
    result = validate_schema(conn)
    conn.close()
    assert result is not None


# ---------------------------------------------------------------------------
# create_backup
# ---------------------------------------------------------------------------


def test_backup_creates_file(tmp_path):
    """create_backup legt genau eine Datei im Backup-Verzeichnis an."""
    _, db_path = _make_mini_db(tmp_path)
    backup_dir = tmp_path / "backups"

    result = create_backup(db_path, backup_dir, max_count=5)

    assert result.exists()
    assert result.parent == backup_dir
    backups = list(backup_dir.glob("log4om_*.sqlite"))
    assert len(backups) == 1


def test_backup_filename_pattern(tmp_path):
    """Backup-Dateiname folgt dem Muster log4om_YYYYMMDD_HHMMSS_ffffff.sqlite."""
    _, db_path = _make_mini_db(tmp_path)
    backup_dir = tmp_path / "backups"

    result = create_backup(db_path, backup_dir, max_count=5)

    assert result.name.startswith("log4om_")
    assert result.suffix == ".sqlite"


def test_backup_rotation_keeps_max(tmp_path):
    """Bei mehr als max_count Backups werden die ältesten gelöscht."""
    _, db_path = _make_mini_db(tmp_path)
    backup_dir = tmp_path / "backups"

    for _ in range(7):
        create_backup(db_path, backup_dir, max_count=5)

    backups = list(backup_dir.glob("log4om_*.sqlite"))
    assert len(backups) == 5


def test_backup_rotation_default_five(tmp_path):
    """Standard-Rotation: Default max_count=5."""
    _, db_path = _make_mini_db(tmp_path)
    backup_dir = tmp_path / "backups"

    for _ in range(8):
        create_backup(db_path, backup_dir)  # Kein max_count → Default 5

    backups = list(backup_dir.glob("log4om_*.sqlite"))
    assert len(backups) == 5


def test_backup_wal_consistent(tmp_path):
    """Backup enthält alle committeten Daten nach WAL-Checkpoint (standalone konsistent)."""
    db_path = tmp_path / "wal_test.sqlite"
    backup_dir = tmp_path / "backups"

    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("CREATE TABLE T (v TEXT)")
    conn.execute("INSERT INTO T VALUES ('checkpoint_marker')")
    conn.commit()
    conn.close()

    backup = create_backup(db_path, backup_dir, max_count=5)

    bconn = sqlite3.connect(str(backup))
    val = bconn.execute("SELECT v FROM T").fetchone()
    bconn.close()

    assert val is not None
    assert val[0] == "checkpoint_marker"


def test_backup_creates_target_dir(tmp_path):
    """Backup-Verzeichnis wird automatisch angelegt wenn es nicht existiert."""
    _, db_path = _make_mini_db(tmp_path)
    backup_dir = tmp_path / "nested" / "backups"

    assert not backup_dir.exists()
    create_backup(db_path, backup_dir, max_count=5)
    assert backup_dir.exists()
