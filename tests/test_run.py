# tests/test_run.py
"""Tests für run.py — Orchestrierung Sammeln→Auswerten→Matchen→Schreiben."""
import json
import sqlite3
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from qsl73.run import CardResult, RunResult


def test_card_result_fields():
    """CardResult ist instanziierbar mit den erwarteten Feldern."""
    from qsl73.matching import CardFields, MatchOutcome, MatchResult

    cr = CardResult(
        doc_id=42,
        card_fields=CardFields(None, None, None, None, None),
        source="none",
        outcome=MatchOutcome(MatchResult.NO_MATCH, None, []),
        existing_confirmations=[],
    )
    assert cr.doc_id == 42
    assert cr.source == "none"
    assert cr.existing_confirmations == []


def test_run_result_fields():
    """RunResult ist instanziierbar und trägt fingerprint + expected_states."""
    rr = RunResult(
        certain=[],
        uncertain=[],
        no_match=[],
        fingerprint={"main_mtime": 1.0, "main_size": 100},
        expected_states={"QSO1": "No"},
    )
    assert rr.certain == []
    assert rr.fingerprint["main_size"] == 100
    assert rr.expected_states["QSO1"] == "No"


# --- Hilfsfunktion: Mini-DB für run-Tests ---

def _make_run_db(tmp_path: Path, name: str = "run.sqlite") -> tuple[sqlite3.Connection, Path]:
    """Mini-DB mit vollem Log-Schema (qsoid, callsign, qsodate, band, mode, stationcallsign, qsoconfirmations)."""
    p = tmp_path / name
    conn = sqlite3.connect(str(p))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute(
        """CREATE TABLE Log (
               qsoid TEXT PRIMARY KEY,
               callsign TEXT,
               qsodate TEXT,
               band TEXT,
               mode TEXT,
               stationcallsign TEXT,
               qsoconfirmations TEXT
           )"""
    )
    return conn, p


def _qsl_json(r: str, extra: list | None = None) -> str:
    """QSO-Bestätigungen-JSON mit QSL-Eintrag R=<r> und optionalen Extra-Einträgen."""
    entries = [{"CT": "QSL", "R": r, "S": "No"}]
    if extra:
        entries.extend(extra)
    return json.dumps(entries)


# --- Tests ---

def test_load_candidates_r_no_included(tmp_path):
    """R='No' QSOs werden als Kandidaten geladen."""
    from qsl73.run import load_qso_candidates

    conn, p = _make_run_db(tmp_path)
    conn.execute(
        "INSERT INTO Log VALUES (?,?,?,?,?,?,?)",
        ("QSO1", "DK8NE", "2025-04-02 19:42:00Z", "6m", "FT8", "DH3KR", _qsl_json("No")),
    )
    conn.commit(); conn.close()

    data = load_qso_candidates(p)
    assert len(data.candidates) == 1
    assert data.candidates[0].qsoid == "QSO1"


def test_load_candidates_r_requested_included(tmp_path):
    """R='Requested' QSOs werden als Kandidaten geladen."""
    from qsl73.run import load_qso_candidates

    conn, p = _make_run_db(tmp_path)
    conn.execute(
        "INSERT INTO Log VALUES (?,?,?,?,?,?,?)",
        ("QSO2", "DL5XYZ", "2024-06-21 14:00:00Z", "40m", "SSB", "DH3KR", _qsl_json("Requested")),
    )
    conn.commit(); conn.close()

    data = load_qso_candidates(p)
    assert len(data.candidates) == 1
    assert data.candidates[0].callsign == "DL5XYZ"


def test_load_candidates_r_yes_excluded(tmp_path):
    """R='Yes' QSOs werden NICHT als Kandidaten geladen."""
    from qsl73.run import load_qso_candidates

    conn, p = _make_run_db(tmp_path)
    conn.execute(
        "INSERT INTO Log VALUES (?,?,?,?,?,?,?)",
        ("QSO3", "DK1AA", "2025-01-01 10:00:00Z", "20m", "CW", "DH3KR", _qsl_json("Yes")),
    )
    conn.commit(); conn.close()

    data = load_qso_candidates(p)
    assert len(data.candidates) == 0


def test_load_candidates_r_invalid_excluded(tmp_path):
    """R='Invalid' QSOs werden NICHT als Kandidaten geladen."""
    from qsl73.run import load_qso_candidates

    conn, p = _make_run_db(tmp_path)
    conn.execute(
        "INSERT INTO Log VALUES (?,?,?,?,?,?,?)",
        ("QSO4", "DK1BB", "2025-01-01 10:00:00Z", "20m", "CW", "DH3KR", _qsl_json("Invalid")),
    )
    conn.commit(); conn.close()

    data = load_qso_candidates(p)
    assert len(data.candidates) == 0


def test_load_candidates_no_qsl_entry_excluded(tmp_path):
    """QSOs ohne CT='QSL'-Eintrag werden übersprungen."""
    from qsl73.run import load_qso_candidates

    conn, p = _make_run_db(tmp_path)
    conn.execute(
        "INSERT INTO Log VALUES (?,?,?,?,?,?,?)",
        ("QSO5", "DK1CC", "2025-01-01 10:00:00Z", "20m", "CW", "DH3KR",
         json.dumps([{"CT": "EQSL", "R": "No"}])),
    )
    conn.commit(); conn.close()

    data = load_qso_candidates(p)
    assert len(data.candidates) == 0


def test_load_station_callsigns(tmp_path):
    """station_callsigns enthält alle stationcallsign-Werte aus der DB."""
    from qsl73.run import load_qso_candidates

    conn, p = _make_run_db(tmp_path)
    conn.execute(
        "INSERT INTO Log VALUES (?,?,?,?,?,?,?)",
        ("QSO1", "DK8NE", "2025-04-02 19:42:00Z", "6m", "FT8", "DH3KR", _qsl_json("No")),
    )
    conn.execute(
        "INSERT INTO Log VALUES (?,?,?,?,?,?,?)",
        ("QSO2", "DL5XYZ", "2024-06-21 14:00:00Z", "40m", "SSB", "DH3KR/P", _qsl_json("Yes")),
    )
    conn.commit(); conn.close()

    data = load_qso_candidates(p)
    assert "DH3KR" in data.station_callsigns
    assert "DH3KR/P" in data.station_callsigns


def test_load_expected_states(tmp_path):
    """expected_states bildet qsoid → R-Wert ab (nur für offene QSOs)."""
    from qsl73.run import load_qso_candidates

    conn, p = _make_run_db(tmp_path)
    conn.execute(
        "INSERT INTO Log VALUES (?,?,?,?,?,?,?)",
        ("QSO1", "DK8NE", "2025-04-02 19:42:00Z", "6m", "FT8", "DH3KR", _qsl_json("No")),
    )
    conn.execute(
        "INSERT INTO Log VALUES (?,?,?,?,?,?,?)",
        ("QSO2", "DL5XYZ", "2024-06-21 14:00:00Z", "40m", "SSB", "DH3KR", _qsl_json("Requested")),
    )
    conn.commit(); conn.close()

    data = load_qso_candidates(p)
    assert data.expected_states == {"QSO1": "No", "QSO2": "Requested"}


def test_load_existing_confirmations(tmp_path):
    """existing_confirmations: EQSL mit R='Yes' wird erfasst; QSL wird ausgeschlossen."""
    from qsl73.run import load_qso_candidates

    conn, p = _make_run_db(tmp_path)
    conn.execute(
        "INSERT INTO Log VALUES (?,?,?,?,?,?,?)",
        ("QSO1", "DK8NE", "2025-04-02 19:42:00Z", "6m", "FT8", "DH3KR",
         _qsl_json("No", extra=[{"CT": "EQSL", "R": "Yes"}, {"CT": "LOTW", "R": "No"}])),
    )
    conn.commit(); conn.close()

    data = load_qso_candidates(p)
    assert "EQSL" in data.existing_confirmations.get("QSO1", [])
    assert "LOTW" not in data.existing_confirmations.get("QSO1", [])
    assert "QSL" not in data.existing_confirmations.get("QSO1", [])


def test_load_fingerprint_returned(tmp_path):
    """load_qso_candidates gibt einen gültigen Fingerabdruck zurück."""
    from qsl73.run import load_qso_candidates

    conn, p = _make_run_db(tmp_path)
    conn.commit(); conn.close()

    data = load_qso_candidates(p)
    assert isinstance(data.fingerprint, dict)
    assert "main_mtime" in data.fingerprint


def test_load_time_utc_extracted(tmp_path):
    """time_utc wird korrekt aus qsodate extrahiert."""
    from qsl73.run import load_qso_candidates

    conn, p = _make_run_db(tmp_path)
    conn.execute(
        "INSERT INTO Log VALUES (?,?,?,?,?,?,?)",
        ("QSO1", "DK8NE", "2025-04-02 19:42:00Z", "6m", "FT8", "DH3KR", _qsl_json("No")),
    )
    conn.commit(); conn.close()

    data = load_qso_candidates(p)
    assert data.candidates[0].time_utc == "19:42"
