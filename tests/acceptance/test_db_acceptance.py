"""Acceptance-Tests: QR → CardFields → match_card gegen echte DB-Kopie.

Erfordert: docs/testdateien/TESTDB_DF1DS_Mai24_backup.sqlite

Ausführen lokal:
    pytest tests/acceptance/ -m acceptance -v

Im CI (ohne DB): alle Tests werden automatisch übersprungen (DB-Datei fehlt).

Sicherheitsleitplanke (ADR-0009):
- Die Original-DB wird NIE verändert — ausschließlich Arbeit auf einer
  temporären Kopie (tmp_path, vom OS nach dem Test gelöscht).
- Kein Schreiben in Schritt 4b: Fake-QSOs nur in der Kopie, rein lesender Match.
"""
import json
import shutil
import sqlite3
from pathlib import Path
from typing import Generator

import pytest

from qsl73.matching import CardFields, MatchResult, QsoCandidate, match_card
from qsl73.qr import parse_qr_text

DB_ORIG = Path("docs/testdateien/TESTDB_DF1DS_Mai24_backup.sqlite")
OWN_CALL = "DL0AAA"
PORTABLE_SUFFIXES = ["P", "M", "MM", "AM", "QRP", "A", "R", "T"]

DK8XX_QR_TEXT = (
    "From: DK8XX  To: DL0AAA\n"
    "Date: 02.04.25  Time: 19:42  Band: 6m  Band_RX: 6m  Mode: FT8  "
    "Prop_Mode: TR  RST: -24  QSL: TNX"
)

pytestmark = [pytest.mark.acceptance, pytest.mark.slow]


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------

def _fake_qso_json() -> str:
    return json.dumps([
        {"CT": "QSL", "S": "No", "R": "No", "SV": "Electronic", "RV": "Electronic"}
    ])


def _insert_fake_qsos(conn: sqlite3.Connection) -> None:
    """Legt Anker-QSOs in der DB-Kopie an (stationcallsign=DL0AAA)."""
    rows = [
        ("20250402194200001", "DK8XX",  "2025-04-02 19:42:00Z", "6m",  "FT8", OWN_CALL),
        ("20250426195200001", "DG5XXX", "2025-04-26 19:52:00Z", "60m", "FT8", OWN_CALL),
        ("20250423122300001", "OE6XXX", "2025-04-23 12:23:00Z", "20m", "FT8", OWN_CALL),
    ]
    json_val = _fake_qso_json()
    for qsoid, callsign, qsodate, band, mode, stationcallsign in rows:
        conn.execute(
            "INSERT INTO Log"
            " (qsoid, callsign, qsodate, band, mode, stationcallsign, qsoconfirmations)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)",
            (qsoid, callsign, qsodate, band, mode, stationcallsign, json_val),
        )
    conn.commit()


def _query_candidates(conn: sqlite3.Connection, callsign: str) -> list[QsoCandidate]:
    cur = conn.execute(
        "SELECT qsoid, callsign, qsodate, band, mode, stationcallsign"
        " FROM Log WHERE UPPER(callsign) = UPPER(?)",
        (callsign,),
    )
    candidates = []
    for row in cur.fetchall():
        qsoid, cs, qsodate, band, mode, sc = row
        # HH:MM aus 'YYYY-MM-DD HH:MM:SSZ'
        time_utc = qsodate[11:16] if qsodate and len(qsodate) > 15 else None
        candidates.append(QsoCandidate(
            qsoid=qsoid,
            callsign=cs,
            date=qsodate,
            band=band or "",
            mode=mode or "",
            time_utc=time_utc,
            stationcallsign=sc or "",
        ))
    return candidates


def _load_station_callsigns(conn: sqlite3.Connection) -> set[str]:
    cur = conn.execute(
        "SELECT DISTINCT stationcallsign FROM Log WHERE stationcallsign IS NOT NULL"
    )
    return {row[0] for row in cur.fetchall()}


def _do_match(conn: sqlite3.Connection, card: CardFields, callsign: str):
    candidates = _query_candidates(conn, callsign)
    station_calls = _load_station_callsigns(conn)
    return match_card(
        card=card,
        candidates=candidates,
        fuzzy_enabled=True,
        portable_suffixes=PORTABLE_SUFFIXES,
        own_callsign=OWN_CALL,
        station_callsigns=station_calls,
    )


# ---------------------------------------------------------------------------
# Fixture: DB-Kopie mit Fake-QSOs
# ---------------------------------------------------------------------------

@pytest.fixture
def db_copy(tmp_path) -> Generator[sqlite3.Connection, None, None]:
    """Kopiert die Original-DB in tmp_path, legt Fake-QSOs an, liefert Verbindung."""
    if not DB_ORIG.exists():
        pytest.skip(f"Test-DB nicht vorhanden: {DB_ORIG}")
    dst = tmp_path / "acceptance_copy.sqlite"
    shutil.copy2(DB_ORIG, dst)
    conn = sqlite3.connect(str(dst))
    conn.execute("PRAGMA journal_mode=WAL")
    _insert_fake_qsos(conn)
    yield conn
    conn.close()


# ---------------------------------------------------------------------------
# Abnahme-Tests A–E
# ---------------------------------------------------------------------------

def test_a_anchor_positive(db_copy: sqlite3.Connection) -> None:
    """A) DK8XX-QR → CERTAIN; getroffenes QSO ist der eingefügte Anker."""
    card = parse_qr_text(DK8XX_QR_TEXT)
    assert card is not None, "QR-Text muss zu CardFields parsen"
    outcome = _do_match(db_copy, card, "DK8XX")
    assert outcome.result == MatchResult.CERTAIN
    assert outcome.matched_qso is not None
    assert outcome.matched_qso.qsoid == "20250402194200001"


def test_b_anchor_negative(db_copy: sqlite3.Connection) -> None:
    """B) Anker-QSO gelöscht → NO_MATCH (korrekte Daten, QSO fehlt in Kopie)."""
    db_copy.execute("DELETE FROM Log WHERE qsoid = '20250402194200001'")
    db_copy.commit()
    card = parse_qr_text(DK8XX_QR_TEXT)
    assert card is not None
    outcome = _do_match(db_copy, card, "DK8XX")
    assert outcome.result == MatchResult.NO_MATCH


def test_c_wrong_band(db_copy: sqlite3.Connection) -> None:
    """C) Anker-QSO auf 2m geändert → Karte sagt 6m → Widerspruch → NO_MATCH."""
    db_copy.execute(
        "UPDATE Log SET band = '2m' WHERE qsoid = '20250402194200001'"
    )
    db_copy.commit()
    card = parse_qr_text(DK8XX_QR_TEXT)
    assert card is not None
    outcome = _do_match(db_copy, card, "DK8XX")
    assert outcome.result == MatchResult.NO_MATCH


def test_d_ambiguous(db_copy: sqlite3.Connection) -> None:
    """D) Zweites DK8XX-QSO am gleichen Tag; Karte ohne Band → UNCERTAIN."""
    db_copy.execute(
        "INSERT INTO Log"
        " (qsoid, callsign, qsodate, band, mode, stationcallsign, qsoconfirmations)"
        " VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("20250402200000002", "DK8XX", "2025-04-02 20:00:00Z", "20m", "FT8",
         OWN_CALL, _fake_qso_json()),
    )
    db_copy.commit()
    card = CardFields(
        call_from="DK8XX", call_to="DL0AAA",
        date="2025-04-02", band=None, mode="FT8",
    )
    outcome = _do_match(db_copy, card, "DK8XX")
    assert outcome.result == MatchResult.UNCERTAIN


def test_e_printed_card_dg5xxx(db_copy: sqlite3.Connection) -> None:
    """E) DG5XXX gedruckte Karte (60m/FT8) → CERTAIN."""
    card = CardFields(
        call_from="DG5XXX", call_to="DL0AAA",
        date="2025-04-26", band="60m", mode="FT8",
    )
    outcome = _do_match(db_copy, card, "DG5XXX")
    assert outcome.result == MatchResult.CERTAIN


def test_e_printed_card_oe6xxx(db_copy: sqlite3.Connection) -> None:
    """E) OE6XXX gedruckte Karte (20m/FT8) → CERTAIN."""
    card = CardFields(
        call_from="OE6XXX", call_to="DL0AAA",
        date="2025-04-23", band="20m", mode="FT8",
    )
    outcome = _do_match(db_copy, card, "OE6XXX")
    assert outcome.result == MatchResult.CERTAIN
