"""Tests für filter_results() — reine Funktion, kein tk erforderlich."""
import pytest
from qsl73.gui.filter_util import filter_results, FILTER_MODES
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
