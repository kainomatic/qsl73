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


# --- OCR-Textextraktion ---

def test_parse_ocr_structured_format():
    """Strukturierter Key:Value-Text (DARC-Format) wird über parse_qr_text ausgewertet."""
    from qsl73.run import _parse_ocr_text

    text = "From: DK8NE To: DH3KR Date: 02.04.25 Time: 19:42 Band: 6m Mode: FT8"
    card, source = _parse_ocr_text(text)
    assert source == "ocr"
    assert card.call_from == "DK8NE"
    assert card.date == "2025-04-02"
    assert card.band == "6m"
    assert card.mode == "FT8"


def test_parse_ocr_labeled_fields():
    """Regex-Extraktion aus beschrifteten Feldern (kein vollständiges Key:Value-Format)."""
    from qsl73.run import _parse_ocr_text

    text = "BAND: 40m\nMODE: CW\nDATE: 2024-06-21"
    card, source = _parse_ocr_text(text)
    assert source == "ocr"
    assert card.band == "40m"
    assert card.mode == "CW"
    assert card.date == "2024-06-21"


def test_parse_ocr_empty_returns_none_fields():
    """Leerer OCR-Text → alle CardFields-Felder None, source='none'."""
    from qsl73.run import _parse_ocr_text

    card, source = _parse_ocr_text("")
    assert source == "none"
    assert card.call_from is None
    assert card.date is None
    assert card.band is None


def test_parse_ocr_no_labels_returns_none_fields():
    """Unlesbarer OCR-Kauderwelsch → alle None, kein Absturz."""
    from qsl73.run import _parse_ocr_text

    card, source = _parse_ocr_text("tToemvem g4rbl3d 1gxK ##!!##")
    assert source == "ocr"
    assert card.call_from is None
    assert card.band is None
    assert card.mode is None


def test_parse_ocr_partial_fields():
    """Nur Band und Mode lesbar → Datum und Rufzeichen bleiben None."""
    from qsl73.run import _parse_ocr_text

    text = "Band: 20m Mode: FT8"
    card, source = _parse_ocr_text(text)
    assert source == "ocr"
    assert card.band == "20m"
    assert card.mode == "FT8"
    assert card.call_from is None
    assert card.date is None


def test_parse_ocr_from_to_labels():
    """From: und To: Labels werden extrahiert."""
    from qsl73.run import _parse_ocr_text

    text = "From: DL5ABC To: DH3KR Band: 6m Mode: FT8 Date: 2025-04-02"
    card, source = _parse_ocr_text(text)
    assert card.call_from == "DL5ABC"
    assert card.call_to == "DH3KR"


def test_parse_ocr_date_not_overcaptured_multiline():
    """Datum wird auch dann korrekt extrahiert, wenn weitere Felder auf der nächsten Zeile folgen."""
    from qsl73.run import _parse_ocr_text

    text = "DATE: 2024-06-21\nBAND: 40m"
    card, source = _parse_ocr_text(text)
    assert card.date == "2024-06-21"
    assert card.band == "40m"


def test_parse_ocr_mode_de_not_matched_as_from():
    """'de' in 'Mode:' darf nicht als From-Label erkannt werden (\b-Fix)."""
    from qsl73.run import _parse_ocr_text

    card, _ = _parse_ocr_text("Mode: FT8")
    assert card.call_from is None
