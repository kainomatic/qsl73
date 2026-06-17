"""Unit-Tests für log4om_db — Schema-Validierung, Backup, Transaktion.

Alle Tests laufen ohne echtes Log4OM gegen synthetische Mini-DBs
(:memory: oder tmp_path). CI-kompatibel.
"""
import json
import sqlite3
from pathlib import Path

import pytest

from qsl73.log4om_db import SchemaError, WriteResult, validate_schema

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
