"""Tests für filter_results() und merge_selections() — reine Funktionen, kein tk."""
import pytest
from qsl73.gui.filter_util import filter_results, merge_selections, FILTER_MODES
from qsl73.run import RunResult, CardResult
from qsl73.matching import MatchOutcome, MatchResult, CardFields


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
