# QSL73 — Copyright (C) 2026 DF1DS (kainomatic) — SPDX-License-Identifier: GPL-3.0-or-later
"""Tests für gui/manual_match.py — CI-kompatibel (kein tk, kein DB-Zugriff)."""
from __future__ import annotations

import pytest

from qsl73.gui.manual_match import ManualQuery, make_manual_selection, search_candidates
from qsl73.matching import QsoCandidate


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------


def _make_cand(
    qsoid: str,
    callsign: str,
    date: str = "2025-03-15",
    band: str = "20m",
    mode: str = "SSB",
) -> QsoCandidate:
    return QsoCandidate(
        qsoid=qsoid,
        callsign=callsign,
        date=date,
        band=band,
        mode=mode,
    )


# ---------------------------------------------------------------------------
# Synthetische Kandidatenmenge (offene QSOs, R='No'/'Requested')
# ---------------------------------------------------------------------------

CANDIDATES = [
    _make_cand("Q001", "DK1AA", "2025-01-10", "20m", "SSB"),
    _make_cand("Q002", "DK1AA", "2025-02-20", "40m", "CW"),
    _make_cand("Q003", "OE3XYZ", "2025-03-15", "20m", "FT8"),
    _make_cand("Q004", "OE3XYZ", "2025-03-15", "10m", "SSB"),
    _make_cand("Q005", "PA3ABC", "2024-12-01", "80m", "SSB"),
]


# ---------------------------------------------------------------------------
# Leerer Query → alle Kandidaten
# ---------------------------------------------------------------------------


def test_empty_query_returns_all():
    result = search_candidates(ManualQuery(), CANDIDATES)
    assert len(result) == len(CANDIDATES)
    assert [c.qsoid for c in result] == [c.qsoid for c in CANDIDATES]


# ---------------------------------------------------------------------------
# Filter: nur Rufzeichen
# ---------------------------------------------------------------------------


def test_call_filter_case_insensitive():
    result = search_candidates(ManualQuery(call="dk1aa"), CANDIDATES)
    assert len(result) == 2
    assert all(c.callsign == "DK1AA" for c in result)


def test_call_filter_prefix_match():
    result = search_candidates(ManualQuery(call="OE3"), CANDIDATES)
    assert len(result) == 2
    assert all(c.callsign == "OE3XYZ" for c in result)


def test_call_filter_substring_match():
    result = search_candidates(ManualQuery(call="3AB"), CANDIDATES)
    assert len(result) == 1
    assert result[0].qsoid == "Q005"


def test_call_filter_no_match():
    result = search_candidates(ManualQuery(call="W1ZZZ"), CANDIDATES)
    assert result == []


# ---------------------------------------------------------------------------
# Filter: Rufzeichen + Band
# ---------------------------------------------------------------------------


def test_call_and_band():
    result = search_candidates(ManualQuery(call="dk1aa", band="40m"), CANDIDATES)
    assert len(result) == 1
    assert result[0].qsoid == "Q002"


def test_call_and_band_no_match():
    result = search_candidates(ManualQuery(call="dk1aa", band="10m"), CANDIDATES)
    assert result == []


# ---------------------------------------------------------------------------
# Editiertes Band findet QSO trotz "kaputter OCR" (ADR-0028 Stufe-2-Interaktion)
# ---------------------------------------------------------------------------


def test_corrected_band_finds_qso():
    """Nutzer korrigiert Band von Hand, da OCR es falsch gelesen hat."""
    # OCR hätte "2Om" gelesen (O statt 0) — Nutzer korrigiert auf "20m"
    candidates_with_ocr_error = [
        _make_cand("Q010", "DL5XY", "2025-06-01", "20m", "FT8"),
    ]
    result = search_candidates(ManualQuery(band="20m"), candidates_with_ocr_error)
    assert len(result) == 1
    assert result[0].qsoid == "Q010"


# ---------------------------------------------------------------------------
# Mehrdeutige Suche → mehrere Treffer
# ---------------------------------------------------------------------------


def test_ambiguous_returns_multiple():
    result = search_candidates(ManualQuery(call="OE3"), CANDIDATES)
    assert len(result) == 2


# ---------------------------------------------------------------------------
# Ranking-Reihenfolge
# ---------------------------------------------------------------------------


def test_ranking_more_fields_first():
    """Exakter Rufzeichen-Treffer rangiert vor reinem Teilstring-Treffer."""
    # "DK1AA" ist Teilstring von "DK1AAB" → beide passieren den call-Filter.
    # Im Ranking zählt aber nur der exakte Treffer (+1 Score).
    cand_exact = _make_cand("R001", "DK1AA", "2025-01-10", "20m", "SSB")
    cand_partial = _make_cand("R002", "DK1AAB", "2025-01-10", "20m", "SSB")

    result = search_candidates(
        ManualQuery(call="DK1AA", band="20m"),
        [cand_partial, cand_exact],  # partial zuerst → sort muss umkehren
    )
    assert len(result) == 2
    assert result[0].qsoid == "R001"  # exakter call + band → Score 2
    assert result[1].qsoid == "R002"  # nur band exakt → Score 1


def test_ranking_with_date():
    """Datum-Übereinstimmung erhöht Score."""
    result = search_candidates(
        ManualQuery(call="OE3XYZ", date="2025-03-15", band="20m"),
        CANDIDATES,
    )
    assert result[0].qsoid == "Q003"  # call+date+band → Score 3


# ---------------------------------------------------------------------------
# Band-Normalisierung: äquivalente Schreibweisen matchen
# ---------------------------------------------------------------------------


def test_band_normalized_match():
    """'14MHz' wird zu '20m' normalisiert und findet Q001."""
    result = search_candidates(ManualQuery(call="DK1AA", band="14000"), CANDIDATES)
    assert len(result) == 1
    assert result[0].qsoid == "Q001"


def test_mode_normalized_match():
    """'USB' wird zu 'SSB' normalisiert."""
    result = search_candidates(ManualQuery(call="DK1AA", mode="USB"), CANDIDATES)
    assert len(result) == 1
    assert result[0].qsoid == "Q001"


# ---------------------------------------------------------------------------
# Suchraum ausschließlich auf übergebene Kandidatenmenge beschränkt
# ---------------------------------------------------------------------------


def test_search_only_in_provided_candidates():
    """Bereits bestätigte QSOs sind nicht in der Kandidatenmenge → nie Treffer."""
    # Kandidatenmenge enthält ausschließlich offene QSOs (R='No'/'Requested').
    # Bereits bestätigte (R='Yes') werden von load_qso_candidates herausgefiltert
    # und gelangen gar nicht erst in diese Funktion — der Suchraum ist die Liste.
    open_candidates = [_make_cand("Q100", "DK5X")]
    result = search_candidates(ManualQuery(call="DK5X"), open_candidates)
    assert len(result) == 1
    assert result[0].qsoid == "Q100"

    # Leere Liste (alle QSOs schon bestätigt) → kein Treffer
    result_empty = search_candidates(ManualQuery(call="DK5X"), [])
    assert result_empty == []


# ---------------------------------------------------------------------------
# Robustheit: leere Strings, None-Felder, keine Exceptions
# ---------------------------------------------------------------------------


def test_empty_call_string_acts_as_no_filter():
    """Leerer call-String ('' nach strip) filtert nicht — entspricht None."""
    result = search_candidates(ManualQuery(call=""), CANDIDATES)
    assert len(result) == len(CANDIDATES)


def test_partial_query_no_exception():
    """Teilbefüllter Query wirft keine Exception."""
    result = search_candidates(ManualQuery(band="20m"), CANDIDATES)
    assert isinstance(result, list)


# ---------------------------------------------------------------------------
# make_manual_selection — route-Validierung
# ---------------------------------------------------------------------------


def test_make_selection_bureau():
    assert make_manual_selection("Q001", "bureau") == ("Q001", "bureau")


def test_make_selection_direct():
    assert make_manual_selection("Q002", "direct") == ("Q002", "direct")


def test_make_selection_undefined():
    assert make_manual_selection("Q003", "undefined") == ("Q003", "undefined")


def test_make_selection_invalid_route_raises():
    with pytest.raises(ValueError, match="Ungültiger route-Wert"):
        make_manual_selection("Q001", "email")


def test_make_selection_invalid_empty_route_raises():
    with pytest.raises(ValueError):
        make_manual_selection("Q001", "")


def test_make_selection_case_sensitive():
    """'Bureau' (Großbuchstabe) ist kein erlaubter Wert — nur Kleinschreibung."""
    with pytest.raises(ValueError):
        make_manual_selection("Q001", "Bureau")
