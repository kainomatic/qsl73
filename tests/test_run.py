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


# --- Karten-Auswertung (QR→OCR) ---

def _make_mock_client(download_bytes: bytes = b"") -> MagicMock:
    """Erstellt einen PaperlessClient-Mock. Content kommt aus dem doc-Dict, nicht vom Client."""
    client = MagicMock()
    client.get_document_download.return_value = download_bytes
    return client


def test_evaluate_card_qr_found():
    """Gültiger QR im PDF → CardFields aus QR, source='qr'."""
    from qsl73.matching import CardFields
    from qsl73.run import evaluate_card

    qr_fields = CardFields("DK8NE", "DH3KR", "2025-04-02", "6m", "FT8", "19:42")

    client = _make_mock_client(download_bytes=b"%PDF-fake")
    doc = {"id": 1, "content": ""}

    with patch("qsl73.run.decode_qr_from_pdf", return_value=qr_fields):
        card, source = evaluate_card(doc, client)

    assert source == "qr"
    assert card.call_from == "DK8NE"


def test_evaluate_card_no_qr_uses_ocr():
    """Kein QR im PDF → Fallback auf OCR-Text aus doc['content']."""
    from qsl73.run import evaluate_card

    client = _make_mock_client(download_bytes=b"%PDF-no-qr")
    doc = {"id": 2, "content": "From: DL5ABC To: DH3KR Band: 40m Mode: CW Date: 2024-06-21"}

    with patch("qsl73.run.decode_qr_from_pdf", return_value=None):
        card, source = evaluate_card(doc, client)

    assert source == "ocr"
    assert card.call_from == "DL5ABC"
    assert card.band == "40m"


def test_evaluate_card_no_qr_no_ocr():
    """Kein QR, kein OCR-Inhalt → alle None, source='none'."""
    from qsl73.run import evaluate_card

    client = _make_mock_client(download_bytes=b"")
    doc = {"id": 3, "content": ""}

    with patch("qsl73.run.decode_qr_from_pdf", return_value=None):
        card, source = evaluate_card(doc, client)

    assert source == "none"
    assert card.call_from is None
    assert card.band is None


def test_evaluate_card_download_error_falls_back_to_ocr():
    """Download-Fehler → kein Absturz, Fallback auf OCR."""
    from qsl73.paperless import PaperlessConnectionError
    from qsl73.run import evaluate_card

    client = MagicMock()
    client.get_document_download.side_effect = PaperlessConnectionError("Timeout")
    doc = {"id": 4, "content": "Band: 20m Mode: FT8"}

    card, source = evaluate_card(doc, client)

    assert source == "ocr"
    assert card.band == "20m"


def test_evaluate_card_missing_content_key():
    """doc ohne 'content'-Schlüssel → kein Absturz."""
    from qsl73.run import evaluate_card

    client = _make_mock_client(download_bytes=b"")
    doc = {"id": 5}  # kein 'content'-Schlüssel

    with patch("qsl73.run.decode_qr_from_pdf", return_value=None):
        card, source = evaluate_card(doc, client)

    assert source == "none"


# --- run_pass Orchestrierung ---

def _make_config(own_callsign: str = "DH3KR"):
    """Minimalconfig für run_pass-Tests."""
    from qsl73.config import Config
    cfg = Config()
    cfg.log4om.own_callsign = own_callsign
    cfg.matching.fuzzy_enabled = True
    cfg.matching.portable_suffixes = ["P", "M", "MM", "AM", "QRP", "A", "R", "T"]
    cfg.tags.input = "qsl-card"
    return cfg


def _make_paperless_mock(docs: list[dict]) -> MagicMock:
    """PaperlessClient-Mock der docs von get_documents_by_tag zurückgibt."""
    client = MagicMock()
    client.get_documents_by_tag.return_value = docs
    client.get_document_download.return_value = b""  # kein QR
    return client


def _insert_qso(conn, qsoid, callsign, qsodate, band, mode, stationcallsign, r="No", extra=None):
    conf_json = _qsl_json(r, extra)
    conn.execute(
        "INSERT INTO Log VALUES (?,?,?,?,?,?,?)",
        (qsoid, callsign, qsodate, band, mode, stationcallsign, conf_json),
    )


def test_run_pass_certain_match(tmp_path):
    """Ein Dokument + passender Kandidat → RunResult.certain hat einen Eintrag."""
    from qsl73.run import run_pass

    conn, db_path = _make_run_db(tmp_path)
    _insert_qso(conn, "QSO1", "DK8NE", "2025-04-02 19:42:00Z", "6m", "FT8", "DH3KR")
    conn.commit(); conn.close()

    # OCR-Text mit allen vier Pflichtfeldern (parse_qr_text-Format)
    docs = [{"id": 1, "content": "From: DK8NE To: DH3KR Date: 02.04.25 Band: 6m Mode: FT8"}]
    client = _make_paperless_mock(docs)
    cfg = _make_config()

    with patch("qsl73.run.decode_qr_from_pdf", return_value=None):
        result = run_pass(client, db_path, cfg)

    assert len(result.certain) == 1
    assert result.certain[0].doc_id == 1
    assert result.certain[0].source == "ocr"


def test_run_pass_no_match(tmp_path):
    """Kein passender Kandidat → RunResult.no_match hat einen Eintrag."""
    from qsl73.run import run_pass

    conn, db_path = _make_run_db(tmp_path)
    _insert_qso(conn, "QSO1", "DK9ZZZ", "2025-04-02 19:42:00Z", "6m", "FT8", "DH3KR")
    conn.commit(); conn.close()

    docs = [{"id": 2, "content": "From: DL1ABC To: DH3KR Date: 02.04.25 Band: 6m Mode: FT8"}]
    client = _make_paperless_mock(docs)
    cfg = _make_config()

    with patch("qsl73.run.decode_qr_from_pdf", return_value=None):
        result = run_pass(client, db_path, cfg)

    assert len(result.no_match) == 1
    assert len(result.certain) == 0


def test_run_pass_uncertain_multiple_candidates(tmp_path):
    """Zwei Kandidaten, keine Zeitangabe → unsicher."""
    from qsl73.run import run_pass

    conn, db_path = _make_run_db(tmp_path)
    _insert_qso(conn, "QSO1", "DK8NE", "2025-04-02 09:00:00Z", "6m", "FT8", "DH3KR")
    _insert_qso(conn, "QSO2", "DK8NE", "2025-04-02 19:00:00Z", "6m", "FT8", "DH3KR")
    conn.commit(); conn.close()

    # OCR: kein Time-Feld → kein Tie-Breaker → two candidates → uncertain
    docs = [{"id": 3, "content": "From: DK8NE To: DH3KR Date: 02.04.25 Band: 6m Mode: FT8"}]
    client = _make_paperless_mock(docs)
    cfg = _make_config()

    with patch("qsl73.run.decode_qr_from_pdf", return_value=None):
        result = run_pass(client, db_path, cfg)

    assert len(result.uncertain) == 1
    assert len(result.certain) == 0


def test_run_pass_existing_confirmations_in_result(tmp_path):
    """existing_confirmations des gematchten QSOs wird ans CardResult gehängt."""
    from qsl73.run import run_pass

    conn, db_path = _make_run_db(tmp_path)
    _insert_qso(
        conn, "QSO1", "DK8NE", "2025-04-02 19:42:00Z", "6m", "FT8", "DH3KR",
        extra=[{"CT": "EQSL", "R": "Yes"}],
    )
    conn.commit(); conn.close()

    docs = [{"id": 1, "content": "From: DK8NE To: DH3KR Date: 02.04.25 Band: 6m Mode: FT8"}]
    client = _make_paperless_mock(docs)
    cfg = _make_config()

    with patch("qsl73.run.decode_qr_from_pdf", return_value=None):
        result = run_pass(client, db_path, cfg)

    assert len(result.certain) == 1
    assert "EQSL" in result.certain[0].existing_confirmations


def test_run_pass_fingerprint_and_expected_states_in_result(tmp_path):
    """RunResult trägt fingerprint und expected_states aus der Sammelphase."""
    from qsl73.run import run_pass

    conn, db_path = _make_run_db(tmp_path)
    _insert_qso(conn, "QSO1", "DK8NE", "2025-04-02 19:42:00Z", "6m", "FT8", "DH3KR")
    conn.commit(); conn.close()

    docs = []
    client = _make_paperless_mock(docs)
    cfg = _make_config()

    result = run_pass(client, db_path, cfg)

    assert isinstance(result.fingerprint, dict)
    assert "main_mtime" in result.fingerprint
    assert "QSO1" in result.expected_states
    assert result.expected_states["QSO1"] == "No"


def test_run_pass_progress_callback(tmp_path):
    """on_progress wird mehrfach aufgerufen."""
    from qsl73.run import run_pass

    conn, db_path = _make_run_db(tmp_path)
    conn.commit(); conn.close()

    docs = [{"id": 1, "content": ""}, {"id": 2, "content": ""}]
    client = _make_paperless_mock(docs)
    cfg = _make_config()

    calls = []
    def progress(done, total, msg):
        calls.append((done, total, msg))

    with patch("qsl73.run.decode_qr_from_pdf", return_value=None):
        run_pass(client, db_path, cfg, on_progress=progress)

    assert len(calls) >= 3  # mindestens: laden, Kandidaten, 2× Karte


def test_run_pass_r_yes_excluded_from_candidates(tmp_path):
    """QSOs mit R='Yes' sind keine Kandidaten — Karte findet keinen Match."""
    from qsl73.run import run_pass

    conn, db_path = _make_run_db(tmp_path)
    _insert_qso(conn, "QSO1", "DK8NE", "2025-04-02 19:42:00Z", "6m", "FT8", "DH3KR", r="Yes")
    conn.commit(); conn.close()

    docs = [{"id": 1, "content": "From: DK8NE To: DH3KR Date: 02.04.25 Band: 6m Mode: FT8"}]
    client = _make_paperless_mock(docs)
    cfg = _make_config()

    with patch("qsl73.run.decode_qr_from_pdf", return_value=None):
        result = run_pass(client, db_path, cfg)

    assert len(result.certain) == 0
    assert len(result.no_match) == 1


# --- write_selected ---

def _make_writable_db(tmp_path: Path, name: str = "write_test.sqlite") -> tuple[sqlite3.Connection, Path]:
    """Mini-DB mit vollständigem Schema und einem schreibbaren QSO (R='No', CT='QSL')."""
    conn, p = _make_run_db(tmp_path, name)
    qsl_json = json.dumps([{"CT": "QSL", "R": "No", "S": "No", "SV": "Electronic"}])
    conn.execute(
        "INSERT INTO Log VALUES (?,?,?,?,?,?,?)",
        ("QSO1", "DK8NE", "2025-04-02 19:42:00Z", "6m", "FT8", "DH3KR", qsl_json),
    )
    conn.commit()
    return conn, p


def test_write_selected_writes_to_db(tmp_path):
    """write_selected schreibt QSO korrekt als R='Yes' in DB-Kopie."""
    from qsl73.log4om_db import get_db_fingerprint
    from qsl73.run import write_selected

    conn, db_path = _make_writable_db(tmp_path)
    conn.close()

    fp = get_db_fingerprint(db_path)
    backup_dir = tmp_path / "backups"

    result = write_selected(
        selections=[("QSO1", "bureau")],
        db_path=db_path,
        backup_dir=backup_dir,
        snapshot_fingerprint=fp,
        expected_states={"QSO1": "No"},
        backup_count=3,
    )

    assert result.written == 1
    assert result.skipped == []

    # DB-Inhalt verifizieren
    verify_conn = sqlite3.connect(str(db_path))
    row = verify_conn.execute("SELECT qsoconfirmations FROM Log WHERE qsoid='QSO1'").fetchone()
    verify_conn.close()
    entries = json.loads(row[0])
    qsl = next(e for e in entries if e.get("CT") == "QSL")
    assert qsl["R"] == "Yes"
    assert qsl["RV"] == "Bureau"


def test_write_selected_paperless_tags_set_after_db(tmp_path):
    """Tags werden NUR nach erfolgreicher DB-Transaktion gesetzt (ADR-0003)."""
    from qsl73.config import TagsConfig
    from qsl73.log4om_db import get_db_fingerprint
    from qsl73.run import write_selected

    conn, db_path = _make_writable_db(tmp_path)
    conn.close()

    fp = get_db_fingerprint(db_path)
    mock_client = MagicMock()
    tags_cfg = TagsConfig(confirmed="qsl-bestätigt", uncertain="qsl-nicht-bestätigt")

    write_selected(
        selections=[("QSO1", "undefined")],
        db_path=db_path,
        backup_dir=tmp_path / "bak",
        snapshot_fingerprint=fp,
        expected_states={"QSO1": "No"},
        paperless_client=mock_client,
        confirmed_doc_ids=[1],
        tags_config=tags_cfg,
    )

    mock_client.add_tag_to_document.assert_called_once_with(1, "qsl-bestätigt")


def test_write_selected_tag_error_nonfatal(tmp_path):
    """Tag-Fehler wird geloggt, kein raise — DB-Schreibergebnis wird trotzdem zurückgegeben."""
    from qsl73.config import TagsConfig
    from qsl73.log4om_db import get_db_fingerprint
    from qsl73.paperless import PaperlessConnectionError
    from qsl73.run import write_selected

    conn, db_path = _make_writable_db(tmp_path)
    conn.close()

    fp = get_db_fingerprint(db_path)
    mock_client = MagicMock()
    mock_client.add_tag_to_document.side_effect = PaperlessConnectionError("Timeout")
    tags_cfg = TagsConfig()

    result = write_selected(
        selections=[("QSO1", "undefined")],
        db_path=db_path,
        backup_dir=tmp_path / "bak",
        snapshot_fingerprint=fp,
        expected_states={"QSO1": "No"},
        paperless_client=mock_client,
        confirmed_doc_ids=[1],
        tags_config=tags_cfg,
    )

    assert result.written == 1  # DB erfolgreich, Tag-Fehler ignoriert


def test_write_selected_no_paperless_no_tags(tmp_path):
    """Kein paperless_client → keine Tag-Operationen, nur DB-Schreiben."""
    from qsl73.log4om_db import get_db_fingerprint
    from qsl73.run import write_selected

    conn, db_path = _make_writable_db(tmp_path)
    conn.close()

    fp = get_db_fingerprint(db_path)

    result = write_selected(
        selections=[("QSO1", "direct")],
        db_path=db_path,
        backup_dir=tmp_path / "bak",
        snapshot_fingerprint=fp,
        expected_states={"QSO1": "No"},
        paperless_client=None,
    )

    assert result.written == 1


def test_write_selected_uncertain_tags(tmp_path):
    """uncertain_doc_ids bekommen den 'qsl-nicht-bestätigt'-Tag."""
    from qsl73.config import TagsConfig
    from qsl73.log4om_db import get_db_fingerprint
    from qsl73.run import write_selected

    conn, db_path = _make_writable_db(tmp_path)
    conn.close()

    fp = get_db_fingerprint(db_path)
    mock_client = MagicMock()
    tags_cfg = TagsConfig(confirmed="qsl-bestätigt", uncertain="qsl-nicht-bestätigt")

    write_selected(
        selections=[],  # nichts schreiben
        db_path=db_path,
        backup_dir=tmp_path / "bak",
        snapshot_fingerprint=fp,
        expected_states={},
        paperless_client=mock_client,
        uncertain_doc_ids=[99],
        tags_config=tags_cfg,
    )

    mock_client.add_tag_to_document.assert_called_once_with(99, "qsl-nicht-bestätigt")
