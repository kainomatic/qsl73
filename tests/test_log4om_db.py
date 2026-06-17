"""Unit-Tests für log4om_db — Schema-Validierung, Backup, Transaktion.

Alle Tests laufen ohne echtes Log4OM gegen synthetische Mini-DBs
(:memory: oder tmp_path). CI-kompatibel.
"""
import json
import sqlite3
from pathlib import Path

import pytest

from qsl73.log4om_db import SchemaError, WriteResult, create_backup, validate_schema, write_confirmations

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


# ---------------------------------------------------------------------------
# write_confirmations
# ---------------------------------------------------------------------------


def _make_write_db(tmp_path, name="write_test.sqlite") -> Path:
    """Mini-DB mit zwei QSOs, je unbestätigt — für Schreib-Tests."""
    db_path = tmp_path / name
    qso_json = _valid_qso_json()
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute(
        "CREATE TABLE Log (qsoid TEXT PRIMARY KEY, callsign TEXT, qsoconfirmations TEXT)"
    )
    conn.execute("INSERT INTO Log VALUES (?,?,?)", ("QSO1", "DK8NE", qso_json))
    conn.execute("INSERT INTO Log VALUES (?,?,?)", ("QSO2", "DL1ABC", qso_json))
    conn.commit()
    conn.close()
    return db_path


def _read_qsl_entry(db_path: Path, qsoid: str) -> dict:
    """Liest den CT='QSL'-Eintrag eines QSO aus der DB."""
    conn = sqlite3.connect(str(db_path))
    row = conn.execute(
        "SELECT qsoconfirmations FROM Log WHERE qsoid=?", (qsoid,)
    ).fetchone()
    conn.close()
    return next(e for e in json.loads(row[0]) if e.get("CT") == "QSL")


def test_write_success_two_qsos(tmp_path):
    """Erfolgreich zwei QSOs in einer Transaktion schreiben."""
    db_path = _make_write_db(tmp_path)
    backup_dir = tmp_path / "backups"

    result = write_confirmations(
        db_path,
        [("QSO1", "bureau"), ("QSO2", "direct")],
        backup_dir,
    )

    assert result.written == 2
    assert result.skipped == []

    qsl1 = _read_qsl_entry(db_path, "QSO1")
    assert qsl1["R"] == "Yes"
    assert qsl1["RV"] == "Bureau"

    qsl2 = _read_qsl_entry(db_path, "QSO2")
    assert qsl2["R"] == "Yes"
    assert qsl2["RV"] == "Direct"


def test_write_creates_backup(tmp_path):
    """Backup wird bei tatsächlichem Schreiben angelegt."""
    db_path = _make_write_db(tmp_path)
    backup_dir = tmp_path / "backups"

    write_confirmations(db_path, [("QSO1", "bureau")], backup_dir)

    backups = list(backup_dir.glob("log4om_*.sqlite"))
    assert len(backups) == 1


def test_write_empty_items_no_backup(tmp_path):
    """Leere items-Liste → kein Backup, WriteResult.written == 0."""
    db_path = _make_write_db(tmp_path)
    backup_dir = tmp_path / "backups"

    result = write_confirmations(db_path, [], backup_dir)

    assert result.written == 0
    assert result.skipped == []
    assert not any(backup_dir.glob("*.sqlite"))


def test_write_atomic_rollback_on_invalid_qsoid(tmp_path):
    """Ungültiger qsoid mitten in der Liste → vollständiger ROLLBACK aller QSOs."""
    db_path = _make_write_db(tmp_path)
    backup_dir = tmp_path / "backups"

    with pytest.raises(ValueError):
        write_confirmations(
            db_path,
            [("QSO1", "bureau"), ("NONEXISTENT_ID", "bureau")],
            backup_dir,
        )

    # Backup wurde vor der Transaktion angelegt (ADR-0003: Backup → Transaktion).
    # Bei ROLLBACK bleibt das Backup erhalten — es schützt den Zustand vor dem
    # Schreibversuch, nicht nur nach erfolgreichem Commit.
    backups = list(backup_dir.glob("log4om_*.sqlite"))
    assert len(backups) == 1, "Backup soll auch nach ROLLBACK erhalten bleiben (ADR-0003)"

    # QSO1 darf NICHT verändert sein (ROLLBACK)
    qsl1 = _read_qsl_entry(db_path, "QSO1")
    assert qsl1["R"] == "No", "QSO1 wurde verändert, obwohl Transaktion fehlschlagen sollte"


def test_write_schema_fail_prevents_backup_and_write(tmp_path):
    """Schema-Check schlägt fehl → SchemaError, kein Backup, keine Schreibung."""
    db_path = tmp_path / "bad.sqlite"
    conn = sqlite3.connect(str(db_path))
    conn.execute("CREATE TABLE WrongTable (x TEXT)")
    conn.commit()
    conn.close()

    backup_dir = tmp_path / "backups"

    with pytest.raises(SchemaError):
        write_confirmations(db_path, [("QSO1", "bureau")], backup_dir)

    assert not any(backup_dir.glob("*.sqlite")), (
        "Backup wurde angelegt, obwohl Schema-Check fehlschlug — Reihenfolge verletzt"
    )


def test_write_schema_fail_missing_column(tmp_path):
    """Schema-Check schlägt fehl (fehlende Spalte) → SchemaError, kein Backup."""
    db_path = tmp_path / "no_col.sqlite"
    conn = sqlite3.connect(str(db_path))
    conn.execute("CREATE TABLE Log (qsoid TEXT)")
    conn.commit()
    conn.close()

    backup_dir = tmp_path / "backups"

    with pytest.raises(SchemaError):
        write_confirmations(db_path, [("QSO1", "bureau")], backup_dir)

    assert not any(backup_dir.glob("*.sqlite"))


def test_write_result_skipped_empty_on_success(tmp_path):
    """Bei Erfolg ist skipped eine leere Liste."""
    db_path = _make_write_db(tmp_path)
    result = write_confirmations(db_path, [("QSO1", "bureau")], tmp_path / "bk")
    assert result.skipped == []
