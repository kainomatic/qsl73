"""Tests für filter_results(), merge_selections(), qso_by_id(), sort_cards_written_last(), qso_display_values() — reine Funktionen."""
import pytest
from qsl73.gui.filter_util import filter_results, merge_selections, qso_by_id, qso_display_values, sort_cards_written_last, FILTER_MODES
from qsl73.run import RunResult, CardResult
from qsl73.matching import MatchOutcome, MatchResult, CardFields, QsoCandidate


def _make_card(doc_id: int, result: MatchResult) -> CardResult:
    return CardResult(
        doc_id=doc_id,
        card_fields=CardFields(None, None, None, None, None),
        source="ocr",
        outcome=MatchOutcome(result=result, matched_qso=None),
        existing_confirmations=[],
    )


def _make_run_result() -> RunResult:
    return RunResult(
        certain=[_make_card(1, MatchResult.CERTAIN), _make_card(2, MatchResult.CERTAIN)],
        uncertain=[_make_card(3, MatchResult.UNCERTAIN)],
        no_match=[_make_card(4, MatchResult.NO_MATCH), _make_card(5, MatchResult.NO_MATCH)],
        fingerprint={},
        expected_states={},
    )


def test_filter_all():
    rr = _make_run_result()
    result = filter_results(rr, "all")
    assert len(result) == 5
    assert [r.doc_id for r in result] == [1, 2, 3, 4, 5]


def test_filter_certain():
    rr = _make_run_result()
    result = filter_results(rr, "certain")
    assert len(result) == 2
    assert all(r.doc_id in (1, 2) for r in result)


def test_filter_uncertain():
    rr = _make_run_result()
    result = filter_results(rr, "uncertain")
    assert len(result) == 1
    assert result[0].doc_id == 3


def test_filter_no_match():
    rr = _make_run_result()
    result = filter_results(rr, "no_match")
    assert len(result) == 2
    assert all(r.doc_id in (4, 5) for r in result)


def test_filter_unknown_mode_returns_empty():
    rr = _make_run_result()
    assert filter_results(rr, "unbekannt") == []


def test_filter_modes_constant():
    assert "all" in FILTER_MODES
    assert "certain" in FILTER_MODES
    assert "uncertain" in FILTER_MODES
    assert "no_match" in FILTER_MODES


# ---------------------------------------------------------------------------
# Tests für merge_selections
# ---------------------------------------------------------------------------


def test_merge_auto_only():
    """Nur Auto-Einträge, keine manuellen → direkt übernommen."""
    sel, ids = merge_selections(
        auto_selections=[("Q1", "bureau"), ("Q2", "direct")],
        auto_doc_ids=[10, 20],
        manual_pending={},
    )
    assert sel == [("Q1", "bureau"), ("Q2", "direct")]
    assert ids == [10, 20]


def test_merge_manual_only():
    """Nur manuelle Einträge, keine Auto → manuell übernommen."""
    sel, ids = merge_selections(
        auto_selections=[],
        auto_doc_ids=[],
        manual_pending={30: ("Q3", "undefined")},
    )
    assert sel == [("Q3", "undefined")]
    assert ids == [30]


def test_merge_auto_and_manual_combined():
    """Auto und manuell zusammengeführt, unterschiedliche qsoids."""
    sel, ids = merge_selections(
        auto_selections=[("Q1", "bureau")],
        auto_doc_ids=[10],
        manual_pending={20: ("Q2", "direct")},
    )
    assert ("Q1", "bureau") in sel
    assert ("Q2", "direct") in sel
    assert 10 in ids
    assert 20 in ids
    assert len(sel) == 2


def test_merge_dedup_same_qsoid():
    """Dieselbe qsoid in auto und manuell → nur einmal in Ergebnis (Auto hat Vorrang)."""
    sel, ids = merge_selections(
        auto_selections=[("Q1", "bureau")],
        auto_doc_ids=[10],
        manual_pending={20: ("Q1", "direct")},  # gleiche qsoid!
    )
    assert len(sel) == 1
    assert sel[0] == ("Q1", "bureau")  # Auto-Version bleibt
    assert ids == [10]


def test_merge_empty_both():
    """Beide leer → leeres Ergebnis."""
    sel, ids = merge_selections([], [], {})
    assert sel == []
    assert ids == []


def test_merge_writable_only_manual_pending():
    """Manuelle Vormerkung allein → kann geschrieben werden (kein CERTAIN nötig)."""
    sel, ids = merge_selections(
        auto_selections=[],
        auto_doc_ids=[],
        manual_pending={99: ("Q99", "undefined")},
    )
    assert len(sel) == 1
    assert sel[0][0] == "Q99"


def test_merge_removes_pending_after_cancel():
    """Aufgehobene Vormerkung landet nicht im Ergebnis."""
    # Simuliert: Nutzer hat Vormerkung Q5 aufgehoben → nicht mehr in manual_pending
    sel, ids = merge_selections(
        auto_selections=[],
        auto_doc_ids=[],
        manual_pending={},  # leer nach Aufheben
    )
    assert sel == []


# ---------------------------------------------------------------------------
# Tests für qso_by_id
# ---------------------------------------------------------------------------


def _make_qso(qsoid: str, callsign: str = "DK1AA") -> QsoCandidate:
    return QsoCandidate(qsoid=qsoid, callsign=callsign, date="2025-01-10", band="20m", mode="SSB")


def test_qso_by_id_found():
    cands = [_make_qso("Q1", "DK1AA"), _make_qso("Q2", "OE3XYZ")]
    result = qso_by_id(cands, "Q1")
    assert result is not None
    assert result.qsoid == "Q1"
    assert result.callsign == "DK1AA"


def test_qso_by_id_second_element():
    cands = [_make_qso("Q1"), _make_qso("Q2", "OE3XYZ")]
    result = qso_by_id(cands, "Q2")
    assert result is not None
    assert result.callsign == "OE3XYZ"


def test_qso_by_id_not_found():
    cands = [_make_qso("Q1")]
    assert qso_by_id(cands, "Q99") is None


def test_qso_by_id_empty_candidates():
    assert qso_by_id([], "Q1") is None


def test_qso_by_id_returns_first_match():
    """Bei doppelter qsoid (Datenanomaie) wird der erste Treffer zurückgegeben."""
    cands = [_make_qso("Q1", "DK1AA"), _make_qso("Q1", "OE3XYZ")]
    result = qso_by_id(cands, "Q1")
    assert result is not None
    assert result.callsign == "DK1AA"


# ---------------------------------------------------------------------------
# Tests für sort_cards_written_last
# ---------------------------------------------------------------------------


def test_sort_written_last_basic():
    """Geschriebene Karte rutscht ans Ende."""
    cards = [_make_card(1, MatchResult.CERTAIN), _make_card(2, MatchResult.CERTAIN), _make_card(3, MatchResult.CERTAIN)]
    result = sort_cards_written_last(cards, {2})
    ids = [c.doc_id for c in result]
    assert ids == [1, 3, 2]


def test_sort_written_last_all_written():
    """Alle geschrieben → Reihenfolge bleibt stabil."""
    cards = [_make_card(1, MatchResult.CERTAIN), _make_card(2, MatchResult.CERTAIN)]
    result = sort_cards_written_last(cards, {1, 2})
    ids = [c.doc_id for c in result]
    assert ids == [1, 2]


def test_sort_written_last_none_written():
    """Kein Eintrag geschrieben → Liste unverändert."""
    cards = [_make_card(3, MatchResult.CERTAIN), _make_card(1, MatchResult.CERTAIN)]
    result = sort_cards_written_last(cards, set())
    ids = [c.doc_id for c in result]
    assert ids == [3, 1]


def test_sort_written_last_stable_within_groups():
    """Reihenfolge innerhalb der Gruppen bleibt stabil."""
    cards = [_make_card(i, MatchResult.CERTAIN) for i in [5, 3, 1, 4, 2]]
    result = sort_cards_written_last(cards, {3, 1})
    not_written = [c.doc_id for c in result if c.doc_id not in {3, 1}]
    written = [c.doc_id for c in result if c.doc_id in {3, 1}]
    assert not_written == [5, 4, 2]
    assert written == [3, 1]


def test_sort_written_last_empty_list():
    assert sort_cards_written_last([], {1}) == []


# ---------------------------------------------------------------------------
# Tests für qso_display_values
# ---------------------------------------------------------------------------


def test_qso_display_values_full():
    """Alle Felder gesetzt → korrekt zurückgegeben, Datum auf 10 Zeichen."""
    cand = QsoCandidate(qsoid="Q1", callsign="DK1AA", date="2025-03-15T12:00:00", band="20m", mode="SSB")
    call, date, band, mode = qso_display_values(cand)
    assert call == "DK1AA"
    assert date == "2025-03-15"
    assert band == "20m"
    assert mode == "SSB"


def test_qso_display_values_date_already_short():
    """Datum exakt 10 Zeichen → unverändert."""
    cand = QsoCandidate(qsoid="Q1", callsign="DK1AA", date="2025-03-15", band="20m", mode="SSB")
    _, date, _, _ = qso_display_values(cand)
    assert date == "2025-03-15"


def test_qso_display_values_empty_fields_become_dash():
    """Leere/None-Felder → '–'."""
    cand = QsoCandidate(qsoid="Q1", callsign=None, date=None, band="", mode=None)
    call, date, band, mode = qso_display_values(cand)
    assert call == "–"
    assert date == "–"
    assert band == "–"
    assert mode == "–"


def test_qso_display_values_partial_fields():
    """Nur Rufzeichen gesetzt, Rest leer."""
    cand = QsoCandidate(qsoid="Q1", callsign="OE3XYZ", date="", band=None, mode="")
    call, date, band, mode = qso_display_values(cand)
    assert call == "OE3XYZ"
    assert date == "–"
    assert band == "–"
    assert mode == "–"
