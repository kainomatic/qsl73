import pytest
from qsl73.matching import (
    CardFields,
    QsoCandidate,
    MatchResult,
    MatchOutcome,
    match_card,
    TIME_TOLERANCE_MINUTES,
)

DEFAULT_SUFFIXES = ["P", "M", "MM", "AM", "QRP", "A", "R", "T"]
OWN_CALL = "DH3KR"
STATION_CALLS: set[str] = {"DH3KR", "DO6KBO"}


def _card(**kw) -> CardFields:
    defaults = dict(
        call_from="DK8NE", call_to="DH3KR",
        date="2025-04-02", band="6m", mode="FT8", time_utc=None,
    )
    defaults.update(kw)
    return CardFields(**defaults)


def _candidate(**kw) -> QsoCandidate:
    defaults = dict(
        qsoid="20250402194200000", callsign="DK8NE",
        date="2025-04-02", band="6m", mode="FT8",
        time_utc="19:42", stationcallsign="DH3KR",
    )
    defaults.update(kw)
    return QsoCandidate(**defaults)


def _match(card, cands, **kw):
    return match_card(
        card=card, candidates=cands,
        fuzzy_enabled=kw.pop("fuzzy", True),
        portable_suffixes=DEFAULT_SUFFIXES,
        own_callsign=OWN_CALL,
        station_callsigns=STATION_CALLS,
        **kw,
    )


# Datenstruktur-Tests
def test_card_fields_creation():
    c = CardFields(call_from="DK8NE", call_to="DH3KR", date="2025-04-02", band="6m", mode="FT8")
    assert c.call_from == "DK8NE"
    assert c.time_utc is None

def test_qso_candidate_creation():
    q = QsoCandidate(qsoid="abc", callsign="DK8NE", date="2025-04-02", band="6m", mode="FT8")
    assert q.qsoid == "abc"
    assert q.time_utc is None

def test_match_result_values():
    assert MatchResult.CERTAIN.value == "sicher"
    assert MatchResult.UNCERTAIN.value == "unsicher"
    assert MatchResult.NO_MATCH.value == "kein_match"

# Zugehörigkeitsprüfung
def test_card_for_other_station_is_no_match():
    result = _match(_card(call_to="DL1XYZ"), [_candidate()])
    assert result.result == MatchResult.NO_MATCH
    assert result.candidates == []

def test_card_for_own_call_passes_ownership():
    result = _match(_card(call_to="DH3KR"), [_candidate()])
    assert result.result == MatchResult.CERTAIN

def test_card_for_own_portable_call_passes():
    result = _match(_card(call_to="SV9/DH3KR"), [_candidate()])
    assert result.result == MatchResult.CERTAIN

def test_card_for_station_callsign_in_db():
    result = _match(_card(call_to="DO6KBO"), [_candidate(callsign="DK8NE", stationcallsign="DO6KBO")])
    assert result.result == MatchResult.CERTAIN

# Kein Match
def test_no_candidates_is_no_match():
    assert _match(_card(), []).result == MatchResult.NO_MATCH

def test_wrong_callsign_is_no_match():
    assert _match(_card(call_from="DK8NE"), [_candidate(callsign="DL1ABC")]).result == MatchResult.NO_MATCH

def test_wrong_date_is_no_match():
    assert _match(_card(date="2025-04-02"), [_candidate(date="2025-04-03")]).result == MatchResult.NO_MATCH

def test_wrong_band_is_no_match():
    assert _match(_card(band="6m"), [_candidate(band="40m")]).result == MatchResult.NO_MATCH

def test_wrong_mode_is_no_match():
    assert _match(_card(mode="FT8"), [_candidate(mode="SSB")]).result == MatchResult.NO_MATCH

# Sicher-Treffer
def test_exact_match_is_certain():
    result = _match(_card(), [_candidate()])
    assert result.result == MatchResult.CERTAIN
    assert result.matched_qso is not None
    assert result.matched_qso.qsoid == "20250402194200000"

def test_fuzzy_callsign_on_is_certain():
    result = _match(_card(call_from="DK8NE"), [_candidate(callsign="DK8NF")], fuzzy=True)
    assert result.result == MatchResult.CERTAIN

def test_fuzzy_callsign_off_is_no_match():
    result = _match(_card(call_from="DK8NE"), [_candidate(callsign="DK8NF")], fuzzy=False)
    assert result.result == MatchResult.NO_MATCH

def test_fuzzy_band_on_is_certain():
    result = _match(_card(band="6m"), [_candidate(band="6n")], fuzzy=True)
    assert result.result == MatchResult.CERTAIN

def test_fuzzy_mode_on_is_certain():
    result = _match(_card(mode="FT8"), [_candidate(mode="FT9")], fuzzy=True)
    assert result.result == MatchResult.CERTAIN

# Suffix-Unterschied-Regel
def test_suffix_differ_exact_fields_is_certain():
    card = _card(call_from="DL1EJD", band="6m", mode="FT8", date="2025-04-02")
    cand = _candidate(callsign="DL1EJD/P", band="6m", mode="FT8", date="2025-04-02")
    assert _match(card, [cand]).result == MatchResult.CERTAIN

def test_suffix_differ_fuzzy_band_is_uncertain():
    card = _card(call_from="DL1EJD", band="6m", mode="FT8", date="2025-04-02")
    cand = _candidate(callsign="DL1EJD/P", band="6n", mode="FT8", date="2025-04-02")
    assert _match(card, [cand], fuzzy=True).result == MatchResult.UNCERTAIN

def test_suffix_differ_reverse_is_certain():
    card = _card(call_from="DL1EJD/P", band="6m", mode="FT8", date="2025-04-02")
    cand = _candidate(callsign="DL1EJD", band="6m", mode="FT8", date="2025-04-02")
    assert _match(card, [cand]).result == MatchResult.CERTAIN

# Unsicher-Fälle
def test_missing_date_is_uncertain():
    assert _match(_card(date=None), [_candidate()]).result == MatchResult.UNCERTAIN

def test_missing_band_is_uncertain():
    assert _match(_card(band=None), [_candidate()]).result == MatchResult.UNCERTAIN

def test_missing_mode_is_uncertain():
    assert _match(_card(mode=None), [_candidate()]).result == MatchResult.UNCERTAIN

def test_missing_call_from_is_uncertain():
    assert _match(_card(call_from=None), [_candidate()]).result == MatchResult.UNCERTAIN

def test_ambiguous_call_from_is_uncertain():
    result = _match(_card(call_from="DH3KR/IF9"), [_candidate(callsign="DH3KR")])
    assert result.result == MatchResult.UNCERTAIN

def test_two_candidates_no_time_is_uncertain():
    cand1 = _candidate(qsoid="id1", time_utc="10:00")
    cand2 = _candidate(qsoid="id2", time_utc="11:00")
    assert _match(_card(time_utc=None), [cand1, cand2]).result == MatchResult.UNCERTAIN

# ITU-Präfix im Matching
def test_itu_prefix_call_from_is_matched():
    card = _card(call_from="5Z4/UA4WHX", call_to="DH3KR")
    cand = _candidate(callsign="UA4WHX")
    assert _match(card, [cand]).result == MatchResult.CERTAIN

# Zeit-Tie-Breaker
def test_tiebreaker_resolves_to_certain():
    cand1 = _candidate(qsoid="id1", time_utc="19:42")
    cand2 = _candidate(qsoid="id2", time_utc="22:00")
    result = _match(_card(time_utc="19:45"), [cand1, cand2])
    assert result.result == MatchResult.CERTAIN
    assert result.matched_qso.qsoid == "id1"

def test_tiebreaker_both_in_window_is_uncertain():
    cand1 = _candidate(qsoid="id1", time_utc="19:42")
    cand2 = _candidate(qsoid="id2", time_utc="19:50")
    assert _match(_card(time_utc="19:45"), [cand1, cand2]).result == MatchResult.UNCERTAIN

def test_tiebreaker_none_in_window_is_uncertain():
    cand1 = _candidate(qsoid="id1", time_utc="10:00")
    cand2 = _candidate(qsoid="id2", time_utc="22:00")
    assert _match(_card(time_utc="15:00"), [cand1, cand2]).result == MatchResult.UNCERTAIN

def test_tiebreaker_at_boundary_is_certain():
    cand1 = _candidate(qsoid="id1", time_utc="19:00")
    cand2 = _candidate(qsoid="id2", time_utc="22:00")
    result = _match(_card(time_utc="19:30"), [cand1, cand2])
    assert result.result == MatchResult.CERTAIN
    assert result.matched_qso.qsoid == "id1"

def test_tiebreaker_candidates_without_time_excluded():
    cand1 = _candidate(qsoid="id1", time_utc=None)
    cand2 = _candidate(qsoid="id2", time_utc="19:42")
    result = _match(_card(time_utc="19:45"), [cand1, cand2])
    assert result.result == MatchResult.CERTAIN
    assert result.matched_qso.qsoid == "id2"
