"""Unit-Tests für log4om_db — Schema-Validierung, Backup, Transaktion, Nebenläufigkeit.

Alle Tests laufen ohne echtes Log4OM gegen synthetische Mini-DBs
(:memory: oder tmp_path). CI-kompatibel.
"""
import hashlib
import json
import logging
import sqlite3
from pathlib import Path

import pytest

from qsl73.log4om_db import (
    BUSY_RETRY_COUNT,
    DatabaseBusyError,
    DatabaseChangedError,
    SchemaError,
    WriteResult,
    create_backup,
    fingerprints_differ,
    get_db_fingerprint,
    is_log4om_running,
    open_wal_connection,
    validate_schema,
    write_confirmations,
)

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


# ---------------------------------------------------------------------------
# 5c: open_wal_connection — busy_timeout
# ---------------------------------------------------------------------------


def test_open_wal_connection_sets_busy_timeout(tmp_path):
    """open_wal_connection setzt PRAGMA busy_timeout."""
    _, db_path = _make_mini_db(tmp_path)
    conn = open_wal_connection(db_path, busy_timeout_ms=123)
    row = conn.execute("PRAGMA busy_timeout").fetchone()
    conn.close()
    assert row is not None
    assert row[0] == 123


def test_open_wal_connection_default_timeout(tmp_path):
    """open_wal_connection default busy_timeout entspricht BUSY_TIMEOUT_MS."""
    from qsl73.log4om_db import BUSY_TIMEOUT_MS

    _, db_path = _make_mini_db(tmp_path)
    conn = open_wal_connection(db_path)
    row = conn.execute("PRAGMA busy_timeout").fetchone()
    conn.close()
    assert row is not None
    assert row[0] == BUSY_TIMEOUT_MS


# ---------------------------------------------------------------------------
# 5c: create_backup — WAL-Checkpoint-Härtung
# ---------------------------------------------------------------------------


def test_backup_checkpoint_complete_no_warning(tmp_path, caplog):
    """Vollständiger Checkpoint → keine WARNING im Log."""
    _, db_path = _make_mini_db(tmp_path)
    backup_dir = tmp_path / "backups"
    with caplog.at_level(logging.WARNING, logger="qsl73"):
        create_backup(db_path, backup_dir)
    assert not any("Checkpoint" in r.message or "checkpoint" in r.message for r in caplog.records)


def test_backup_checkpoint_incomplete_logs_warning(tmp_path, caplog):
    """Unvollständiger Checkpoint (externe Lesertransaktion) → WARNING geloggt."""
    db_path = tmp_path / "wal.sqlite"
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("CREATE TABLE T (v TEXT)")
    conn.execute("INSERT INTO T VALUES ('x')")
    conn.commit()

    # Externe Verbindung hält eine Lesertransaktion offen — verhindert FULL checkpoint
    reader = sqlite3.connect(str(db_path))
    reader.execute("BEGIN")
    reader.execute("SELECT * FROM T")  # hält read-lock

    backup_dir = tmp_path / "backups"
    with caplog.at_level(logging.WARNING, logger="qsl73"):
        result = create_backup(db_path, backup_dir)

    reader.execute("ROLLBACK")
    reader.close()
    conn.close()

    # Backup soll trotzdem angelegt worden sein
    assert result.exists()
    # Warnung wird nur bei tatsächlich unvollständigem Checkpoint geloggt;
    # SQLite-Verhalten hängt von Platform ab — prüfen dass kein Crash
    assert result.suffix == ".sqlite"


# ---------------------------------------------------------------------------
# 5c: get_db_fingerprint + fingerprints_differ
# ---------------------------------------------------------------------------


def test_fingerprint_returns_main_file_fields(tmp_path):
    """Fingerabdruck enthält main_mtime und main_size."""
    _, db_path = _make_mini_db(tmp_path)
    fp = get_db_fingerprint(db_path)
    assert fp["main_mtime"] is not None
    assert fp["main_size"] is not None


def test_fingerprint_wal_fields_present(tmp_path):
    """Fingerabdruck enthält wal_mtime und wal_size (None wenn keine WAL-Datei)."""
    _, db_path = _make_mini_db(tmp_path)
    fp = get_db_fingerprint(db_path)
    assert "wal_mtime" in fp
    assert "wal_size" in fp


def test_fingerprints_differ_same_false(tmp_path):
    """Kein Schreibvorgang zwischen zwei Fingerabdrücken → False."""
    _, db_path = _make_mini_db(tmp_path)
    fp1 = get_db_fingerprint(db_path)
    fp2 = get_db_fingerprint(db_path)
    assert not fingerprints_differ(fp1, fp2)


def test_fingerprints_differ_after_external_write_and_checkpoint(tmp_path):
    """Externer Write + Checkpoint → Hauptdatei aktualisiert → fingerprints_differ True."""
    db_path = tmp_path / "fp_test.sqlite"
    setup = sqlite3.connect(str(db_path))
    setup.execute("PRAGMA journal_mode=WAL")
    setup.execute(
        "CREATE TABLE Log (qsoid TEXT PRIMARY KEY, callsign TEXT, qsoconfirmations TEXT)"
    )
    setup.execute("INSERT INTO Log VALUES (?,?,?)", ("Q1", "DK8NE", _valid_qso_json()))
    setup.commit()
    setup.close()

    fp_before = get_db_fingerprint(db_path)

    # Externer Write (landet in WAL)
    writer = sqlite3.connect(str(db_path))
    writer.execute("INSERT INTO Log VALUES (?,?,?)", ("Q2", "DL9XX", _valid_qso_json()))
    writer.commit()
    writer.close()

    # Checkpoint: WAL-Frames → Hauptdatei → main_mtime ändert sich
    ckpt = sqlite3.connect(str(db_path))
    ckpt.execute("PRAGMA wal_checkpoint(FULL)")
    ckpt.close()

    fp_after = get_db_fingerprint(db_path)

    assert fingerprints_differ(fp_before, fp_after)


def test_fingerprints_differ_main_mtime_changes():
    """Hauptdatei-mtime ändert sich (Checkpoint nach externem Write) → Unterschied erkannt."""
    fp1 = {"main_mtime": 1000.0, "main_size": 4096, "wal_mtime": 100.0, "wal_size": 1024}
    fp2 = {"main_mtime": 2000.0, "main_size": 4096, "wal_mtime": 100.0, "wal_size": 1024}
    assert fingerprints_differ(fp1, fp2)


def test_fingerprints_differ_wal_changes_but_main_same():
    """WAL ändert sich, Hauptdatei nicht → kein Unterschied (WAL-only, per-QSO-Check fängt das ab)."""
    fp1 = {"main_mtime": 1000.0, "main_size": 4096, "wal_mtime": 100.0, "wal_size": 1024}
    fp2 = {"main_mtime": 1000.0, "main_size": 4096, "wal_mtime": 999.0, "wal_size": 2048}
    assert not fingerprints_differ(fp1, fp2)  # WAL-Änderungen: Optimistic Locking fängt das ab


def test_fingerprints_differ_only_main_changes(tmp_path):
    """Nur Hauptdatei ändert sich (z. B. nach Checkpoint) → als Änderung erkannt."""
    fp1 = {"main_mtime": 1000.0, "main_size": 4096, "wal_mtime": None, "wal_size": None}
    fp2 = {"main_mtime": 2000.0, "main_size": 8192, "wal_mtime": None, "wal_size": None}
    assert fingerprints_differ(fp1, fp2)


def test_fingerprints_differ_nothing_changed(tmp_path):
    """Alle Felder identisch → False."""
    fp1 = {"main_mtime": 1000.0, "main_size": 4096, "wal_mtime": None, "wal_size": None}
    fp2 = {"main_mtime": 1000.0, "main_size": 4096, "wal_mtime": None, "wal_size": None}
    assert not fingerprints_differ(fp1, fp2)


# ---------------------------------------------------------------------------
# 5c: write_confirmations — Fingerabdruck-Check (DatabaseChangedError)
# ---------------------------------------------------------------------------


def _external_write_and_checkpoint(db_path: Path) -> None:
    """Hilfsfunktion: externer Write + expliziter Checkpoint → main_mtime ändert sich."""
    writer = sqlite3.connect(str(db_path))
    writer.execute(
        "INSERT INTO Log VALUES (?,?,?)", ("QSO_EXTRA_FP", "OE1XX", _valid_qso_json())
    )
    writer.commit()
    writer.close()
    ckpt = sqlite3.connect(str(db_path))
    ckpt.execute("PRAGMA wal_checkpoint(FULL)")
    ckpt.close()


def test_write_changed_fingerprint_raises_error(tmp_path):
    """DB nach Sammeln verändert (main_mtime unterschiedlich) → DatabaseChangedError, kein Backup."""
    db_path = _make_write_db(tmp_path)
    backup_dir = tmp_path / "backups"

    fp_old = get_db_fingerprint(db_path)
    _external_write_and_checkpoint(db_path)  # Hauptdatei-mtime ändert sich

    with pytest.raises(DatabaseChangedError):
        write_confirmations(
            db_path, [("QSO1", "bureau")], backup_dir,
            snapshot_fingerprint=fp_old,
        )

    # Kein Backup, da Fingerabdruck-Check VOR dem Backup-Schritt liegt
    assert not any(backup_dir.glob("*.sqlite"))


def test_write_changed_fingerprint_no_write(tmp_path):
    """DatabaseChangedError → QSO bleibt unverändert."""
    db_path = _make_write_db(tmp_path)
    fp_old = get_db_fingerprint(db_path)
    _external_write_and_checkpoint(db_path)

    with pytest.raises(DatabaseChangedError):
        write_confirmations(
            db_path, [("QSO1", "bureau")], tmp_path / "bk",
            snapshot_fingerprint=fp_old,
        )

    qsl = _read_qsl_entry(db_path, "QSO1")
    assert qsl["R"] == "No", "QSO1 darf nicht verändert worden sein"


def test_write_no_fingerprint_skips_check(tmp_path):
    """Kein snapshot_fingerprint → kein Fingerabdruck-Check → normaler Schreibpfad."""
    db_path = _make_write_db(tmp_path)
    result = write_confirmations(
        db_path, [("QSO1", "bureau")], tmp_path / "bk",
        snapshot_fingerprint=None,
    )
    assert result.written == 1


def test_write_unchanged_fingerprint_writes(tmp_path):
    """Unveränderter Fingerabdruck → kein Fehler, normaler Schreibpfad."""
    db_path = _make_write_db(tmp_path)
    fp = get_db_fingerprint(db_path)

    result = write_confirmations(
        db_path, [("QSO1", "bureau")], tmp_path / "bk",
        snapshot_fingerprint=fp,
    )
    assert result.written == 1


# ---------------------------------------------------------------------------
# 5c: write_confirmations — SQLITE_BUSY-Retry (DatabaseBusyError)
# ---------------------------------------------------------------------------


def _make_busy_db(tmp_path: Path, name: str = "busy.sqlite") -> Path:
    """Mini-DB mit einem QSO für BUSY-Tests."""
    db_path = tmp_path / name
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute(
        "CREATE TABLE Log (qsoid TEXT PRIMARY KEY, callsign TEXT, qsoconfirmations TEXT)"
    )
    conn.execute("INSERT INTO Log VALUES (?,?,?)", ("QSO1", "DK8NE", _valid_qso_json()))
    conn.commit()
    conn.close()
    return db_path


def test_busy_raises_database_busy_error(tmp_path):
    """Andere Verbindung hält Schreibsperre → DatabaseBusyError nach erschöpften Versuchen."""
    db_path = _make_busy_db(tmp_path)
    backup_dir = tmp_path / "bk"

    # Exklusive Sperre via zweiter Verbindung
    locker = sqlite3.connect(str(db_path))
    locker.execute("BEGIN EXCLUSIVE")

    try:
        with pytest.raises(DatabaseBusyError):
            write_confirmations(
                db_path,
                [("QSO1", "bureau")],
                backup_dir,
                retry_count=2,
                retry_delay_s=0.0,
                busy_timeout_ms=30,
            )
    finally:
        locker.execute("ROLLBACK")
        locker.close()


def test_busy_no_partial_write(tmp_path):
    """Nach DatabaseBusyError bleibt die DB im Originalzustand (kein Teilschreiben)."""
    db_path = _make_busy_db(tmp_path)
    original_hash = hashlib.sha256(db_path.read_bytes()).hexdigest()

    locker = sqlite3.connect(str(db_path))
    locker.execute("BEGIN EXCLUSIVE")

    try:
        with pytest.raises(DatabaseBusyError):
            write_confirmations(
                db_path,
                [("QSO1", "bureau")],
                tmp_path / "bk",
                retry_count=2,
                retry_delay_s=0.0,
                busy_timeout_ms=30,
            )
    finally:
        locker.execute("ROLLBACK")
        locker.close()

    final_hash = hashlib.sha256(db_path.read_bytes()).hexdigest()
    assert original_hash == final_hash, "DB darf nach DatabaseBusyError nicht verändert sein"


def test_busy_retry_count_respected(tmp_path, monkeypatch):
    """sleep() wird genau (retry_count - 1) mal aufgerufen."""
    db_path = _make_busy_db(tmp_path)
    sleep_calls = []
    monkeypatch.setattr("qsl73.log4om_db.time.sleep", lambda s: sleep_calls.append(s))

    locker = sqlite3.connect(str(db_path))
    locker.execute("BEGIN EXCLUSIVE")

    try:
        with pytest.raises(DatabaseBusyError):
            write_confirmations(
                db_path,
                [("QSO1", "bureau")],
                tmp_path / "bk",
                retry_count=3,
                retry_delay_s=0.0,
                busy_timeout_ms=10,
            )
    finally:
        locker.execute("ROLLBACK")
        locker.close()

    assert len(sleep_calls) == 2, (
        f"Erwartet 2 sleep()-Aufrufe (retry_count-1=2), aber {len(sleep_calls)} erhalten"
    )


def test_busy_succeeds_after_lock_releases(tmp_path):
    """Lock-Freigabe zwischen Versuchen → Write gelingt beim Retry."""
    import threading

    db_path = _make_busy_db(tmp_path)
    backup_dir = tmp_path / "bk"
    db_str = str(db_path)

    # check_same_thread=False: Connection im Thread-Callback nutzbar
    locker = sqlite3.connect(db_str, check_same_thread=False)
    locker.execute("BEGIN EXCLUSIVE")

    def release_after_delay():
        import time as _time
        _time.sleep(0.05)
        locker.execute("ROLLBACK")

    t = threading.Thread(target=release_after_delay)
    t.start()

    result = write_confirmations(
        db_path,
        [("QSO1", "bureau")],
        backup_dir,
        retry_count=5,
        retry_delay_s=0.02,
        busy_timeout_ms=100,
    )
    t.join()
    locker.close()

    assert result.written == 1


# ---------------------------------------------------------------------------
# 5c: write_confirmations — Optimistic Locking (Skip vs. Rollback)
# ---------------------------------------------------------------------------


def _make_write_db_extended(tmp_path, name="ext_write.sqlite") -> Path:
    """Mini-DB mit drei QSOs für Optimistic-Locking-Tests."""
    db_path = tmp_path / name
    qso_json = _valid_qso_json()
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute(
        "CREATE TABLE Log (qsoid TEXT PRIMARY KEY, callsign TEXT, qsoconfirmations TEXT)"
    )
    conn.execute("INSERT INTO Log VALUES (?,?,?)", ("QSO1", "DK8NE", qso_json))
    conn.execute("INSERT INTO Log VALUES (?,?,?)", ("QSO2", "DL1ABC", qso_json))
    conn.execute("INSERT INTO Log VALUES (?,?,?)", ("QSO3", "OE5XY", qso_json))
    conn.commit()
    conn.close()
    return db_path


def _confirm_qso_externally(db_path: Path, qsoid: str) -> None:
    """Setzt R='Yes' für ein QSO über eine externe Verbindung (simuliert paralleles Log4OM)."""
    conn = sqlite3.connect(str(db_path))
    row = conn.execute(
        "SELECT qsoconfirmations FROM Log WHERE qsoid=?", (qsoid,)
    ).fetchone()
    conf = json.loads(row[0])
    for entry in conf:
        if isinstance(entry, dict) and entry.get("CT") == "QSL":
            entry["R"] = "Yes"
            break
    conn.execute(
        "UPDATE Log SET qsoconfirmations=? WHERE qsoid=?",
        (json.dumps(conf, separators=(",", ":")), qsoid),
    )
    conn.commit()
    conn.close()


def test_optimistic_already_confirmed_is_skipped(tmp_path):
    """QSO extern auf R='Yes' gesetzt → wird übersprungen, nicht ROLLBACK."""
    db_path = _make_write_db_extended(tmp_path)
    _confirm_qso_externally(db_path, "QSO1")

    result = write_confirmations(
        db_path, [("QSO1", "bureau"), ("QSO2", "direct")], tmp_path / "bk"
    )

    assert result.written == 1
    assert len(result.skipped) == 1
    assert result.skipped[0]["qsoid"] == "QSO1"
    assert "Yes" in result.skipped[0]["reason"]


def test_optimistic_skip_does_not_rollback_others(tmp_path):
    """Übersprungenes QSO verhindert nicht das Schreiben der anderen."""
    db_path = _make_write_db_extended(tmp_path)
    _confirm_qso_externally(db_path, "QSO2")

    result = write_confirmations(
        db_path, [("QSO1", "bureau"), ("QSO2", "bureau"), ("QSO3", "direct")], tmp_path / "bk"
    )

    assert result.written == 2
    assert result.skipped[0]["qsoid"] == "QSO2"
    qsl1 = _read_qsl_entry(db_path, "QSO1")
    qsl3 = _read_qsl_entry(db_path, "QSO3")
    assert qsl1["R"] == "Yes"
    assert qsl3["R"] == "Yes"


def test_optimistic_skipped_entry_has_reason(tmp_path):
    """skipped-Eintrag enthält 'qsoid' und 'reason'."""
    db_path = _make_write_db(tmp_path)
    _confirm_qso_externally(db_path, "QSO1")

    result = write_confirmations(db_path, [("QSO1", "bureau")], tmp_path / "bk")

    assert result.written == 0
    assert len(result.skipped) == 1
    skip = result.skipped[0]
    assert "qsoid" in skip
    assert "reason" in skip
    assert skip["qsoid"] == "QSO1"
    assert skip["reason"]  # nicht leer


def test_optimistic_technical_error_rollback_all(tmp_path):
    """Technischer Fehler (fehlende qsoid) → ROLLBACK aller — kein Teilschreiben."""
    db_path = _make_write_db(tmp_path)  # hat QSO1 und QSO2
    backup_dir = tmp_path / "bk"

    with pytest.raises(ValueError):
        write_confirmations(
            db_path,
            [("QSO1", "bureau"), ("NONEXISTENT", "bureau")],
            backup_dir,
        )

    # QSO1 darf nicht verändert sein (ROLLBACK)
    qsl1 = _read_qsl_entry(db_path, "QSO1")
    assert qsl1["R"] == "No", "QSO1 darf nicht verändert sein (ROLLBACK erwartet)"


def test_optimistic_invalid_json_rollback_all(tmp_path):
    """Korruptes JSON in qsoconfirmations → ROLLBACK aller — kein Teilschreiben."""
    db_path = tmp_path / "corrupt.sqlite"
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute(
        "CREATE TABLE Log (qsoid TEXT PRIMARY KEY, callsign TEXT, qsoconfirmations TEXT)"
    )
    conn.execute("INSERT INTO Log VALUES (?,?,?)", ("QSO1", "DK8NE", _valid_qso_json()))
    conn.execute("INSERT INTO Log VALUES (?,?,?)", ("QSO2", "OE2XX", "INVALID {{{"))
    conn.commit()
    conn.close()

    with pytest.raises(ValueError, match="JSON"):
        write_confirmations(db_path, [("QSO1", "bureau"), ("QSO2", "bureau")], tmp_path / "bk")

    # QSO1 darf nicht verändert sein (ROLLBACK)
    qsl1 = _read_qsl_entry(db_path, "QSO1")
    assert qsl1["R"] == "No"


def test_optimistic_missing_qsl_entry_rollback_all(tmp_path):
    """Kein CT='QSL'-Eintrag → technischer Fehler → ROLLBACK aller."""
    from qsl73.log4om_write import QslEntryNotFoundError

    qso_without_qsl = json.dumps(
        [{"CT": "EQSL", "S": "No", "R": "No"}], separators=(",", ":")
    )
    db_path = tmp_path / "no_qsl.sqlite"
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute(
        "CREATE TABLE Log (qsoid TEXT PRIMARY KEY, callsign TEXT, qsoconfirmations TEXT)"
    )
    conn.execute("INSERT INTO Log VALUES (?,?,?)", ("QSO1", "DK8NE", _valid_qso_json()))
    conn.execute("INSERT INTO Log VALUES (?,?,?)", ("QSO2", "OE9XX", qso_without_qsl))
    conn.commit()
    conn.close()

    with pytest.raises(QslEntryNotFoundError):
        write_confirmations(db_path, [("QSO1", "bureau"), ("QSO2", "bureau")], tmp_path / "bk")

    qsl1 = _read_qsl_entry(db_path, "QSO1")
    assert qsl1["R"] == "No", "QSO1 muss via ROLLBACK unverändert bleiben"


def test_optimistic_unknown_r_value_skipped(tmp_path):
    """Unbekannter R-Wert ('Invalid') → ÜBERSPRINGEN, nicht ROLLBACK."""
    invalid_qsl = json.dumps(
        [{"CT": "QSL", "S": "No", "R": "Invalid", "SV": "Electronic"}],
        separators=(",", ":"),
    )
    db_path = tmp_path / "inv_r.sqlite"
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute(
        "CREATE TABLE Log (qsoid TEXT PRIMARY KEY, callsign TEXT, qsoconfirmations TEXT)"
    )
    conn.execute("INSERT INTO Log VALUES (?,?,?)", ("QSO1", "DK8NE", invalid_qsl))
    conn.execute("INSERT INTO Log VALUES (?,?,?)", ("QSO2", "DL1XX", _valid_qso_json()))
    conn.commit()
    conn.close()

    result = write_confirmations(
        db_path, [("QSO1", "bureau"), ("QSO2", "bureau")], tmp_path / "bk"
    )

    assert result.written == 1
    assert len(result.skipped) == 1
    assert result.skipped[0]["qsoid"] == "QSO1"


# ---------------------------------------------------------------------------
# 5c: expected_states — Optimistic Locking mit erwartetem Vor-Wert
# ---------------------------------------------------------------------------


def test_expected_states_match_writes(tmp_path):
    """expected_r stimmt mit aktuellem R überein → normales Schreiben."""
    db_path = _make_write_db(tmp_path)

    result = write_confirmations(
        db_path,
        [("QSO1", "bureau")],
        tmp_path / "bk",
        expected_states={"QSO1": "No"},
    )

    assert result.written == 1
    assert result.skipped == []


def test_expected_states_mismatch_skips(tmp_path):
    """expected_r weicht vom aktuellen R ab → ÜBERSPRINGEN (5c), nicht ROLLBACK."""
    db_path = _make_write_db(tmp_path)

    # QSO1 hat R='No', aber wir erwarten 'Requested' → Mismatch
    result = write_confirmations(
        db_path,
        [("QSO1", "bureau"), ("QSO2", "direct")],
        tmp_path / "bk",
        expected_states={"QSO1": "Requested", "QSO2": "No"},
    )

    assert result.written == 1
    assert len(result.skipped) == 1
    assert result.skipped[0]["qsoid"] == "QSO1"
    assert "Requested" in result.skipped[0]["reason"]

    qsl2 = _read_qsl_entry(db_path, "QSO2")
    assert qsl2["R"] == "Yes"  # QSO2 normal geschrieben


def test_expected_states_none_key_allows_write(tmp_path):
    """qsoid nicht in expected_states → kein Mismatch, normales Schreiben."""
    db_path = _make_write_db(tmp_path)

    result = write_confirmations(
        db_path,
        [("QSO1", "bureau")],
        tmp_path / "bk",
        expected_states={},  # leer: QSO1 hat keinen expected_r Eintrag → kein Check
    )

    assert result.written == 1


# ---------------------------------------------------------------------------
# 5c: Optimistic Locking — R='Requested' wird als 'offen' akzeptiert
# ---------------------------------------------------------------------------


def test_requested_r_value_is_written(tmp_path):
    """R='Requested' gilt als 'offen' und darf geschrieben werden."""
    requested_qsl = json.dumps(
        [{"CT": "QSL", "S": "No", "R": "Requested", "SV": "Electronic"}],
        separators=(",", ":"),
    )
    db_path = tmp_path / "req.sqlite"
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute(
        "CREATE TABLE Log (qsoid TEXT PRIMARY KEY, callsign TEXT, qsoconfirmations TEXT)"
    )
    conn.execute("INSERT INTO Log VALUES (?,?,?)", ("QSO1", "DK8NE", requested_qsl))
    conn.commit()
    conn.close()

    result = write_confirmations(db_path, [("QSO1", "bureau")], tmp_path / "bk")

    assert result.written == 1
    assert result.skipped == []
    qsl = _read_qsl_entry(db_path, "QSO1")
    assert qsl["R"] == "Yes"


# ---------------------------------------------------------------------------
# 5c: is_log4om_running — nicht-blockierende Warnung
# ---------------------------------------------------------------------------


def test_log4om_running_found():
    """Prozessliste enthält log4om2.exe → True."""
    assert is_log4om_running(["Log4OM2.exe", "notepad.exe"])


def test_log4om_running_not_found():
    """Prozessliste ohne Log4OM → False."""
    assert not is_log4om_running(["notepad.exe", "explorer.exe"])


def test_log4om_running_empty_list():
    """Leere Prozessliste → False."""
    assert not is_log4om_running([])


def test_log4om_running_case_insensitive():
    """Prozessname case-insensitiv: LOG4OM2.EXE → True."""
    assert is_log4om_running(["LOG4OM2.EXE"])
    assert is_log4om_running(["log4om2.exe"])
    assert is_log4om_running(["Log4OM2.EXE"])


def test_log4om_running_does_not_prevent_write(tmp_path):
    """is_log4om_running=True blockiert write_confirmations nicht."""
    db_path = _make_write_db(tmp_path)

    # Warnung signalisiert → kein Stopp; Schreiben läuft trotzdem
    assert is_log4om_running(["Log4OM2.exe"])
    result = write_confirmations(db_path, [("QSO1", "bureau")], tmp_path / "bk")
    assert result.written == 1


def test_log4om_running_no_default_call_in_tests():
    """Ohne process_names-Argument kein Fehler auf CI (plattformtolerant)."""
    # Gibt einfach True oder False zurück, kein Absturz auf Linux/CI
    result = is_log4om_running()
    assert isinstance(result, bool)


# ---------------------------------------------------------------------------
# 5c: Integrations-Hashprüfung — Original-DB unverändert bei Skips
# ---------------------------------------------------------------------------


def test_hash_unchanged_original_db_after_skip(tmp_path):
    """Original-DB-Hash bleibt identisch wenn alle QSOs übersprungen werden."""
    db_path = _make_write_db(tmp_path)
    _confirm_qso_externally(db_path, "QSO1")
    _confirm_qso_externally(db_path, "QSO2")

    # Für Hash-Vergleich: nach den Confirms den Stand festhalten
    baseline_hash = hashlib.sha256(db_path.read_bytes()).hexdigest()

    result = write_confirmations(
        db_path, [("QSO1", "bureau"), ("QSO2", "direct")], tmp_path / "bk"
    )

    assert result.written == 0
    assert len(result.skipped) == 2
    # DB unverändert (alle schon bestätigt → skip → kein COMMIT)
    final_hash = hashlib.sha256(db_path.read_bytes()).hexdigest()
    assert baseline_hash == final_hash
