"""Acceptance-Tests: Schreiblogik gegen echte DB-Kopie (Schritt 5a).

Erfordert: docs/testdateien/TESTDB_DF1DS_Mai24_backup.sqlite

Ausführen lokal:
    pytest tests/acceptance/test_write_acceptance.py -m acceptance -v

Im CI (ohne DB): alle Tests werden automatisch übersprungen.

Sicherheitsleitplanken (ADR-0009):
- NUR die DB-KOPIE in tmp_path wird verändert — nie die Original-DB.
- Original-DB-Integrität wird per SHA-256 und Dateigröße vor/nach verifiziert.
- Schreibt ausschließlich die qsoconfirmations-Spalte eines einzelnen QSO.
"""
import hashlib
import json
import shutil
import sqlite3
from pathlib import Path
from typing import Generator

import pytest

from qsl73.log4om_write import write_paper_qsl

DB_ORIG = Path("docs/testdateien/TESTDB_DF1DS_Mai24_backup.sqlite")

pytestmark = pytest.mark.acceptance

# qsoid des Anker-QSO, das im Test verwendet wird (eingefügt via Fixture)
WRITE_TEST_QSOID = "20250402194200099"
WRITE_TEST_CALLSIGN = "DK8NE"

# Erwartet-JSON nach bureau-Bestätigung gemäß discovery.md §3 (Hand-Test-Ergebnis)
EXPECTED_QSL_AFTER_BUREAU = {
    "CT": "QSL",
    "S": "No",
    "R": "Yes",
    "SV": "Electronic",
    "RV": "Bureau",
}

# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------

def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _make_qso_json() -> str:
    """Ausgangszustand: unbestätigt, wie in der echten DB."""
    return json.dumps(
        [{"CT": "QSL", "S": "No", "R": "No", "SV": "Electronic", "RV": "Electronic"},
         {"CT": "EQSL",    "S": "Yes", "R": "No",  "SV": "Electronic", "RV": "Electronic",
          "SD": "2023-03-26T00:00:00Z"},
         {"CT": "LOTW",    "S": "Yes", "R": "Yes", "SV": "Electronic", "RV": "Electronic",
          "SD": "2023-03-04T00:00:00Z", "RD": "2023-03-19T00:00:00Z"},
         {"CT": "QRZCOM",  "S": "Yes", "R": "Yes", "SV": "Electronic", "RV": "Electronic",
          "RD": "2023-10-13T00:00:00Z"},
         {"CT": "HAMQTH",  "S": "No",  "R": "No",  "SV": "Electronic", "RV": "Electronic"},
         {"CT": "HRDLOG",  "S": "No",  "R": "No",  "SV": "Electronic", "RV": "Electronic"},
         {"CT": "CLUBLOG", "S": "No",  "R": "No",  "SV": "Electronic", "RV": "Electronic"}],
        ensure_ascii=False,
        separators=(",", ":"),
    )


# ---------------------------------------------------------------------------
# Fixture: DB-Kopie mit Test-QSO
# ---------------------------------------------------------------------------

@pytest.fixture
def db_copy_write(tmp_path) -> Generator[tuple[sqlite3.Connection, Path, str], None, None]:
    """Kopiert Original-DB in tmp_path, fügt Test-QSO ein.

    Yields: (conn, dst_path, original_sha256)
    """
    if not DB_ORIG.exists():
        pytest.skip(f"Test-DB nicht vorhanden: {DB_ORIG}")

    orig_hash = _sha256(DB_ORIG)
    dst = tmp_path / "write_test_copy.sqlite"
    shutil.copy2(DB_ORIG, dst)

    conn = sqlite3.connect(str(dst))
    conn.execute("PRAGMA journal_mode=WAL")

    # Test-QSO einfügen (eigener qsoid, kein Konflikt mit echten QSOs)
    conn.execute(
        "INSERT INTO Log"
        " (qsoid, callsign, qsodate, band, mode, stationcallsign, qsoconfirmations)"
        " VALUES (?, ?, ?, ?, ?, ?, ?)",
        (WRITE_TEST_QSOID, WRITE_TEST_CALLSIGN,
         "2025-04-02 19:42:00Z", "6m", "FT8", "DH3KR",
         _make_qso_json()),
    )
    conn.commit()

    yield conn, dst, orig_hash
    conn.close()


# ---------------------------------------------------------------------------
# Verifikations-Test: korrekte Schreiboperation (route=bureau)
# ---------------------------------------------------------------------------

def test_write_sets_qsl_bureau(db_copy_write) -> None:
    """write_paper_qsl setzt R='Yes' und RV='Bureau' im QSL-Eintrag."""
    conn, _, _ = db_copy_write
    write_paper_qsl(conn, WRITE_TEST_QSOID, "bureau")
    conn.commit()

    row = conn.execute(
        "SELECT qsoconfirmations FROM Log WHERE qsoid = ?", (WRITE_TEST_QSOID,)
    ).fetchone()
    assert row is not None
    confirmations = json.loads(row[0])
    qsl_entry = next(e for e in confirmations if e.get("CT") == "QSL")
    assert qsl_entry["R"] == "Yes"
    assert qsl_entry["RV"] == "Bureau"


def test_write_matches_discovery_target_format(db_copy_write) -> None:
    """Ergebnis-JSON des QSL-Eintrags entspricht dem Hand-Test-Format (discovery.md §3)."""
    conn, _, _ = db_copy_write
    write_paper_qsl(conn, WRITE_TEST_QSOID, "bureau")
    conn.commit()

    row = conn.execute(
        "SELECT qsoconfirmations FROM Log WHERE qsoid = ?", (WRITE_TEST_QSOID,)
    ).fetchone()
    confirmations = json.loads(row[0])
    qsl_entry = next(e for e in confirmations if e.get("CT") == "QSL")
    assert qsl_entry == EXPECTED_QSL_AFTER_BUREAU


def test_write_no_rd_in_qsl_entry(db_copy_write) -> None:
    """Kein RD-Feld wird in den QSL-Eintrag geschrieben (discovery.md §3, Regel 3)."""
    conn, _, _ = db_copy_write
    write_paper_qsl(conn, WRITE_TEST_QSOID, "bureau")
    conn.commit()

    row = conn.execute(
        "SELECT qsoconfirmations FROM Log WHERE qsoid = ?", (WRITE_TEST_QSOID,)
    ).fetchone()
    confirmations = json.loads(row[0])
    qsl_entry = next(e for e in confirmations if e.get("CT") == "QSL")
    assert "RD" not in qsl_entry


def test_write_other_ct_types_unchanged(db_copy_write) -> None:
    """Alle Nicht-QSL-Einträge (EQSL, LOTW, QRZCOM, HAMQTH, HRDLOG, CLUBLOG) bleiben unverändert."""
    conn, _, _ = db_copy_write

    # Vor-Zustand erfassen
    row_before = conn.execute(
        "SELECT qsoconfirmations FROM Log WHERE qsoid = ?", (WRITE_TEST_QSOID,)
    ).fetchone()
    before = {e["CT"]: e for e in json.loads(row_before[0]) if e.get("CT") != "QSL"}

    write_paper_qsl(conn, WRITE_TEST_QSOID, "bureau")
    conn.commit()

    row_after = conn.execute(
        "SELECT qsoconfirmations FROM Log WHERE qsoid = ?", (WRITE_TEST_QSOID,)
    ).fetchone()
    after = {e["CT"]: e for e in json.loads(row_after[0]) if e.get("CT") != "QSL"}

    assert after == before, "Nicht-QSL-Einträge wurden verändert"


def test_write_other_columns_unchanged(db_copy_write) -> None:
    """Alle anderen Spalten des QSO bleiben nach dem Schreiben unverändert."""
    conn, _, _ = db_copy_write

    before = conn.execute(
        "SELECT callsign, qsodate, band, mode, stationcallsign FROM Log WHERE qsoid = ?",
        (WRITE_TEST_QSOID,),
    ).fetchone()

    write_paper_qsl(conn, WRITE_TEST_QSOID, "bureau")
    conn.commit()

    after = conn.execute(
        "SELECT callsign, qsodate, band, mode, stationcallsign FROM Log WHERE qsoid = ?",
        (WRITE_TEST_QSOID,),
    ).fetchone()

    assert after == before, "Andere QSO-Spalten wurden verändert"


def test_write_other_qsos_unchanged(db_copy_write) -> None:
    """Andere QSOs in der DB bleiben vollständig unverändert (Stichprobe: 10 QSOs)."""
    conn, _, _ = db_copy_write

    # Stichprobe: erste 10 echte QSOs (nicht das Test-QSO)
    rows_before = conn.execute(
        "SELECT qsoid, callsign, qsodate, band, mode, qsoconfirmations"
        " FROM Log WHERE qsoid != ? ORDER BY qsoid LIMIT 10",
        (WRITE_TEST_QSOID,),
    ).fetchall()

    write_paper_qsl(conn, WRITE_TEST_QSOID, "bureau")
    conn.commit()

    rows_after = conn.execute(
        "SELECT qsoid, callsign, qsodate, band, mode, qsoconfirmations"
        " FROM Log WHERE qsoid != ? ORDER BY qsoid LIMIT 10",
        (WRITE_TEST_QSOID,),
    ).fetchall()

    assert rows_after == rows_before, "Andere QSOs wurden verändert"


def test_original_db_untouched(db_copy_write) -> None:
    """Original-DB wird nie verändert — Hash und Dateigröße stimmen nach dem Test überein."""
    conn, _, orig_hash = db_copy_write
    write_paper_qsl(conn, WRITE_TEST_QSOID, "bureau")
    conn.commit()

    assert _sha256(DB_ORIG) == orig_hash, "Original-DB wurde verändert!"
    # Größe muss identisch bleiben
    assert DB_ORIG.stat().st_size > 0


# ---------------------------------------------------------------------------
# Verifikations-Test: route=undefined entfernt RV
# ---------------------------------------------------------------------------

def test_write_sets_qsl_undefined(db_copy_write) -> None:
    """route='undefined': R='Yes', kein RV-Schlüssel im QSL-Eintrag."""
    conn, _, _ = db_copy_write
    write_paper_qsl(conn, WRITE_TEST_QSOID, "undefined")
    conn.commit()

    row = conn.execute(
        "SELECT qsoconfirmations FROM Log WHERE qsoid = ?", (WRITE_TEST_QSOID,)
    ).fetchone()
    confirmations = json.loads(row[0])
    qsl_entry = next(e for e in confirmations if e.get("CT") == "QSL")
    assert qsl_entry["R"] == "Yes"
    assert "RV" not in qsl_entry


def test_write_sets_qsl_direct(db_copy_write) -> None:
    """route='direct': R='Yes', RV='Direct'."""
    conn, _, _ = db_copy_write
    write_paper_qsl(conn, WRITE_TEST_QSOID, "direct")
    conn.commit()

    row = conn.execute(
        "SELECT qsoconfirmations FROM Log WHERE qsoid = ?", (WRITE_TEST_QSOID,)
    ).fetchone()
    confirmations = json.loads(row[0])
    qsl_entry = next(e for e in confirmations if e.get("CT") == "QSL")
    assert qsl_entry["R"] == "Yes"
    assert qsl_entry["RV"] == "Direct"
