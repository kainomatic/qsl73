# QSL73 — Copyright (C) 2026 DF1DS (kainomatic) — SPDX-License-Identifier: GPL-3.0-or-later
"""Tests für is_batch_writable() und build_write_selections() — kein tk erforderlich."""
from __future__ import annotations

from qsl73.gui.filter_util import build_write_selections, is_batch_writable
from qsl73.matching import CardFields, MatchOutcome, MatchResult, QsoCandidate
from qsl73.run import CardResult


def _make_qso(qsoid: str = "QSO-001") -> QsoCandidate:
    return QsoCandidate(qsoid=qsoid, callsign="DL1ABC", date="2024-01-15", band="40m", mode="SSB")


def _make_card(
    doc_id: int,
    result: MatchResult,
    matched_qso: QsoCandidate | None = None,
) -> CardResult:
    return CardResult(
        doc_id=doc_id,
        card_fields=CardFields(None, None, None, None, None),
        source="ocr",
        outcome=MatchOutcome(result=result, matched_qso=matched_qso),
        existing_confirmations=[],
    )


# --- is_batch_writable ---

def test_certain_with_match_is_batch_writable():
    card = _make_card(1, MatchResult.CERTAIN, matched_qso=_make_qso())
    assert is_batch_writable(card) is True


def test_certain_without_match_is_batch_writable():
    # Prüffunktion schaut nur auf result, nicht auf matched_qso
    card = _make_card(1, MatchResult.CERTAIN, matched_qso=None)
    assert is_batch_writable(card) is True


def test_uncertain_is_not_batch_writable():
    card = _make_card(2, MatchResult.UNCERTAIN, matched_qso=_make_qso())
    assert is_batch_writable(card) is False


def test_no_match_is_not_batch_writable():
    card = _make_card(3, MatchResult.NO_MATCH, matched_qso=None)
    assert is_batch_writable(card) is False


# --- build_write_selections ---

def test_build_write_selections_uses_only_certain():
    cards = [
        _make_card(1, MatchResult.CERTAIN, matched_qso=_make_qso("QSO-A")),
        _make_card(2, MatchResult.UNCERTAIN, matched_qso=_make_qso("QSO-B")),
        _make_card(3, MatchResult.NO_MATCH, matched_qso=None),
    ]
    selections, doc_ids = build_write_selections(cards, route="bureau")
    assert selections == [("QSO-A", "bureau")]
    assert doc_ids == [1]


def test_build_write_selections_excludes_certain_without_matched_qso():
    cards = [
        _make_card(1, MatchResult.CERTAIN, matched_qso=_make_qso("QSO-A")),
        _make_card(2, MatchResult.CERTAIN, matched_qso=None),  # kein QSO → nicht schreibbar
    ]
    selections, doc_ids = build_write_selections(cards, route="direct")
    assert selections == [("QSO-A", "direct")]
    assert doc_ids == [1]


def test_build_write_selections_empty_when_no_certain():
    cards = [
        _make_card(1, MatchResult.UNCERTAIN, matched_qso=_make_qso("QSO-X")),
        _make_card(2, MatchResult.NO_MATCH, matched_qso=None),
    ]
    selections, doc_ids = build_write_selections(cards, route="undefined")
    assert selections == []
    assert doc_ids == []


def test_build_write_selections_route_is_applied():
    cards = [
        _make_card(1, MatchResult.CERTAIN, matched_qso=_make_qso("QSO-1")),
        _make_card(2, MatchResult.CERTAIN, matched_qso=_make_qso("QSO-2")),
    ]
    selections, _ = build_write_selections(cards, route="bureau")
    assert all(route == "bureau" for _, route in selections)
