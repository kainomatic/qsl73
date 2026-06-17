"""Acceptance-Tests: write_confirmations-Orchestrierung gegen echte DB-Kopie (Schritt 5b).

Erfordert: docs/testdateien/TESTDB_DF1DS_Mai24_backup.sqlite

Ausführen lokal:
    pytest tests/acceptance/test_db_orchestration_acceptance.py -m acceptance -v

Im CI (ohne DB): alle Tests werden automatisch übersprungen.

Sicherheitsleitplanken (ADR-0009):
- NUR die DB-KOPIE in tmp_path wird verändert — nie die Original-DB.
- Original-DB-Integrität wird per SHA-256 vorher/nachher verifiziert.
"""
import hashlib
import json
import shutil
import sqlite3
from pathlib import Path
from typing import Generator

import pytest

from qsl73.log4om_db import SchemaError, open_wal_connection, validate_schema, write_confirmations

DB_ORIG = Path("docs/testdateien/TESTDB_DF1DS_Mai24_backup.sqlite")

pytestmark = pytest.mark.acceptance

# Eindeutige Test-qsoids (kein Konflikt mit echten QSOs)
QSOID_A = "20230101120000900"
QSOID_B = "20230101120000901"


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _base_qso_json() -> str:
    return json.dumps(
        [
            {"CT": "QSL", "S": "No", "R": "No", "SV": "Electronic", "RV": "Electronic"},
            {"CT": "EQSL", "S": "No", "R": "No", "SV": "Electronic"},
        ],
        separators=(",", ":"),
    )


@pytest.fixture
def db_copy(tmp_path) -> Generator[tuple[Path, str], None, None]:
    """Kopiert Original-DB in tmp_path, fügt zwei Test-QSOs ein.

    Yields: (copy_path, original_sha256)
    """
    if not DB_ORIG.exists():
        pytest.skip(f"Test-DB nicht vorhanden: {DB_ORIG}")

    orig_hash = _sha256(DB_ORIG)
    dst = tmp_path / "orch_test.sqlite"
    shutil.copy2(DB_ORIG, dst)

    conn = sqlite3.connect(str(dst))
    conn.execute("PRAGMA journal_mode=WAL")
    qso_json = _base_qso_json()
    conn.execute(
        "INSERT INTO Log"
        " (qsoid, callsign, qsodate, band, mode, stationcallsign, qsoconfirmations)"
        " VALUES (?,?,?,?,?,?,?)",
        (QSOID_A, "DK8NE", "2023-01-01 12:00:00Z", "20m", "FT8", "DH3KR", qso_json),
    )
    conn.execute(
        "INSERT INTO Log"
        " (qsoid, callsign, qsodate, band, mode, stationcallsign, qsoconfirmations)"
        " VALUES (?,?,?,?,?,?,?)",
        (QSOID_B, "DL1ABC", "2023-01-01 12:30:00Z", "40m", "CW", "DH3KR", qso_json),
    )
    conn.commit()
    conn.close()

    yield dst, orig_hash


# ---------------------------------------------------------------------------
# A — Schema-Validierung auf echter DB
# ---------------------------------------------------------------------------

def test_A_real_db_schema_valid(db_copy):
    """validate_schema auf echter DB-Kopie gibt None zurück (Schema intakt)."""
    dst, _ = db_copy
    conn = open_wal_connection(dst)
    result = validate_schema(conn)
    conn.close()

    assert result is None, f"Schema-Check ergab Abweichung: {result}"


# ---------------------------------------------------------------------------
# B — Erfolgsfall: zwei QSOs bestätigt, Original unverändert
# ---------------------------------------------------------------------------

def test_B_write_two_qsos_success(db_copy, tmp_path):
    """write_confirmations bestätigt zwei QSOs korrekt auf DB-Kopie."""
    dst, orig_hash = db_copy
    backup_dir = tmp_path / "backups"

    result = write_confirmations(
        dst,
        [(QSOID_A, "bureau"), (QSOID_B, "direct")],
        backup_dir,
    )

    assert result.written == 2
    assert result.skipped == []

    conn = sqlite3.connect(str(dst))
    for qsoid, expected_rv in [(QSOID_A, "Bureau"), (QSOID_B, "Direct")]:
        row = conn.execute(
            "SELECT qsoconfirmations FROM Log WHERE qsoid=?", (qsoid,)
        ).fetchone()
        qsl = next(e for e in json.loads(row[0]) if e.get("CT") == "QSL")
        assert qsl["R"] == "Yes", f"R nicht 'Yes' für {qsoid}"
        assert qsl["RV"] == expected_rv, f"RV falsch für {qsoid}"
    conn.close()

    # Original-DB unverändert
    assert _sha256(DB_ORIG) == orig_hash, "Original-DB wurde verändert!"


# ---------------------------------------------------------------------------
# C — Rollback: ungültiger qsoid → alles zurückgerollt
# ---------------------------------------------------------------------------

def test_C_rollback_on_invalid_qsoid(db_copy, tmp_path):
    """Ungültiger qsoid → Exception, QSOID_A bleibt unverändert (ROLLBACK)."""
    dst, orig_hash = db_copy
    backup_dir = tmp_path / "backups"

    with pytest.raises(ValueError):
        write_confirmations(
            dst,
            [(QSOID_A, "bureau"), ("NONEXISTENT_99999", "bureau")],
            backup_dir,
        )

    conn = sqlite3.connect(str(dst))
    row = conn.execute(
        "SELECT qsoconfirmations FROM Log WHERE qsoid=?", (QSOID_A,)
    ).fetchone()
    conn.close()
    qsl = next(e for e in json.loads(row[0]) if e.get("CT") == "QSL")
    assert qsl["R"] == "No", "QSOID_A wurde verändert, obwohl Transaktion fehlschlagen sollte"

    # Original-DB unverändert
    assert _sha256(DB_ORIG) == orig_hash


# ---------------------------------------------------------------------------
# D — Reihenfolge: Schema-Check schlägt fehl → kein Backup
# ---------------------------------------------------------------------------

def test_D_schema_fail_no_backup(tmp_path):
    """Schema-Check fehlgeschlagen → SchemaError, kein Backup, kein Schreiben."""
    bad_db = tmp_path / "bad.sqlite"
    conn = sqlite3.connect(str(bad_db))
    conn.execute("CREATE TABLE WrongTable (x TEXT)")
    conn.commit()
    conn.close()
    backup_dir = tmp_path / "backups"

    with pytest.raises(SchemaError):
        write_confirmations(bad_db, [(QSOID_A, "bureau")], backup_dir)

    assert not any(backup_dir.glob("*.sqlite")), (
        "Backup wurde angelegt, obwohl Schema-Check fehlschlug — Reihenfolge (ADR-0003) verletzt"
    )


# ---------------------------------------------------------------------------
# E — Backup erstellt, Rotation, Original unverändert
# ---------------------------------------------------------------------------

def test_E_backup_created_and_rotation(db_copy, tmp_path):
    """Backup wird angelegt; nach 6 Aufrufen bleiben maximal 5 Backups (Rotation)."""
    dst, orig_hash = db_copy
    backup_dir = tmp_path / "backups"

    # Ersten Schreiblauf normal
    write_confirmations(dst, [(QSOID_A, "bureau")], backup_dir, backup_count=5)
    assert len(list(backup_dir.glob("log4om_*.sqlite"))) == 1

    # Weitere 5 Läufe mit frischen Kopien (damit kein Fehler wegen bereits-bestätigter QSOs)
    for i in range(5):
        fresh = tmp_path / f"fresh_{i}.sqlite"
        shutil.copy2(DB_ORIG, fresh)
        conn = sqlite3.connect(str(fresh))
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute(
            "INSERT INTO Log"
            " (qsoid, callsign, qsodate, band, mode, stationcallsign, qsoconfirmations)"
            " VALUES (?,?,?,?,?,?,?)",
            (QSOID_A, "DK8NE", "2023-01-01 12:00:00Z", "20m", "FT8", "DH3KR", _base_qso_json()),
        )
        conn.commit()
        conn.close()
        write_confirmations(fresh, [(QSOID_A, "bureau")], backup_dir, backup_count=5)

    backups = list(backup_dir.glob("log4om_*.sqlite"))
    assert len(backups) == 5, f"Erwartet 5 Backups, gefunden: {len(backups)}"

    # Original-DB unverändert
    assert _sha256(DB_ORIG) == orig_hash
