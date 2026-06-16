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


# ---------------------------------------------------------------------------
# OCR-Fehlerkatalog × DB-Zustände (parametrisierte Matrix)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("card_call,cand_call,fuzzy,expected", [
    ("DK8NE", "DK8NE", True, MatchResult.CERTAIN),
    ("DK3NE", "DK8NE", True, MatchResult.CERTAIN),     # 8↔3
    ("DK3NE", "DK8NE", False, MatchResult.NO_MATCH),   # fuzzy aus
    ("DK0NE", "DK8NE", True, MatchResult.CERTAIN),     # 8↔0
    ("DKBNE", "DK8NE", True, MatchResult.CERTAIN),     # 8↔B
    ("DK8IE", "DK8NE", True, MatchResult.CERTAIN),     # N↔I
    ("DK8LE", "DK8NE", True, MatchResult.CERTAIN),     # N↔L
    ("DK5NE", "DK8NE", True, MatchResult.CERTAIN),     # 8↔5
    ("DK6NE", "DK8NE", True, MatchResult.CERTAIN),     # 8↔6
    ("DK00E", "DK8NE", True, MatchResult.NO_MATCH),    # Distanz 2
])
def test_ocr_callsign_errors_matrix(card_call, cand_call, fuzzy, expected):
    result = _match(_card(call_from=card_call), [_candidate(callsign=cand_call)], fuzzy=fuzzy)
    assert result.result == expected


@pytest.mark.parametrize("card_band,cand_band,fuzzy,expected", [
    ("6m", "6m", True, MatchResult.CERTAIN),
    # "6m" vs "2m": Levenshtein-Distanz 1 → Fuzzy-Match → CERTAIN (OCR-Tipp zu Fuzzy)
    ("6m", "2m", True, MatchResult.CERTAIN),
    # Ohne Fuzzy: kein Match
    ("6m", "2m", False, MatchResult.NO_MATCH),
    (None, "6m", True, MatchResult.UNCERTAIN),
])
def test_ocr_band_errors_in_matching(card_band, cand_band, fuzzy, expected):
    result = _match(_card(band=card_band), [_candidate(band=cand_band)], fuzzy=fuzzy)
    assert result.result == expected


# ---------------------------------------------------------------------------
# "Niemals falsch-positiv"-Fokus-Tests (ADR-0007 Leitregel)
# ---------------------------------------------------------------------------

class TestNeverFalsePositive:

    def test_ambiguous_date_similar_qso_is_uncertain(self):
        assert _match(_card(date=None), [_candidate()]).result == MatchResult.UNCERTAIN

    def test_missing_band_similar_qso_is_uncertain(self):
        assert _match(_card(band=None), [_candidate()]).result == MatchResult.UNCERTAIN

    def test_ambiguous_callsign_similar_qso_is_uncertain(self):
        result = _match(_card(call_from="DH3KR/IF9"), [_candidate(callsign="DH3KR")])
        assert result.result == MatchResult.UNCERTAIN

    def test_similar_qso_wrong_date_is_no_match(self):
        assert _match(_card(date="2025-04-02"), [_candidate(date="2025-04-03")]).result == MatchResult.NO_MATCH

    def test_similar_qso_wrong_band_is_no_match(self):
        assert _match(_card(band="6m"), [_candidate(band="40m")]).result == MatchResult.NO_MATCH

    def test_two_candidates_same_station_no_time_is_uncertain(self):
        cand1 = _candidate(qsoid="id1", time_utc="10:00")
        cand2 = _candidate(qsoid="id2", time_utc="14:00")
        result = _match(_card(time_utc=None), [cand1, cand2])
        assert result.result == MatchResult.UNCERTAIN
        assert result.matched_qso is None

    def test_suffix_differ_fuzzy_field_is_not_certain(self):
        card = _card(call_from="DL1EJD", band="6m", mode="FT8")
        cand = _candidate(callsign="DL1EJD/P", band="6n", mode="FT8")
        assert _match(card, [cand], fuzzy=True).result == MatchResult.UNCERTAIN

    def test_card_not_for_own_log_is_no_match(self):
        assert _match(_card(call_to="DL1ABC"), [_candidate()]).result == MatchResult.NO_MATCH

    def test_fuzzy_callsign_spec_behavior(self):
        card = _card(call_from="DK8NE")
        cand = _candidate(callsign="DK8NF")
        assert _match(card, [cand], fuzzy=True).result == MatchResult.CERTAIN
        assert _match(card, [cand], fuzzy=False).result == MatchResult.NO_MATCH

    def test_distance_2_callsign_is_never_certain(self):
        card = _card(call_from="DK8NE")
        cand = _candidate(callsign="DK00E")
        assert _match(card, [cand], fuzzy=True).result == MatchResult.NO_MATCH


# ---------------------------------------------------------------------------
# §6.4-Akzeptanzkriterien als ausführbare Tests
# ---------------------------------------------------------------------------

def test_spec_exact_match_is_certain():
    assert _match(_card(), [_candidate()]).result == MatchResult.CERTAIN

def test_spec_fuzzy_callsign_on_is_certain():
    assert _match(_card(call_from="DK8NE"), [_candidate(callsign="DK8NF")], fuzzy=True).result == MatchResult.CERTAIN

def test_spec_fuzzy_callsign_off_is_no_match():
    assert _match(_card(call_from="DK8NE"), [_candidate(callsign="DK8NF")], fuzzy=False).result == MatchResult.NO_MATCH

def test_spec_two_candidates_is_uncertain():
    cand1 = _candidate(qsoid="id1")
    cand2 = _candidate(qsoid="id2")
    assert _match(_card(time_utc=None), [cand1, cand2]).result == MatchResult.UNCERTAIN

def test_spec_band_name_and_frequency_equal():
    from qsl73.normalize import normalize_band
    assert normalize_band("6m") == normalize_band("50.100 MHz") == "6m"

def test_spec_band_2m_frequency():
    from qsl73.normalize import normalize_band
    assert normalize_band("144.255 MHz") == "2m"

def test_spec_mode_j3e_is_ssb():
    from qsl73.normalize import normalize_mode
    assert normalize_mode("J3E") == "SSB"

def test_spec_mode_2xssb_variants():
    from qsl73.normalize import normalize_mode
    assert normalize_mode("2×SSB") == "SSB"
    assert normalize_mode("2xSSB") == "SSB"

def test_spec_date_23apr2025():
    from qsl73.normalize import normalize_date
    assert normalize_date("23Apr2025") == "2025-04-23"

def test_spec_date_us_columns():
    from qsl73.normalize import normalize_date
    assert normalize_date("06/21/2024") == "2024-06-21"

def test_spec_date_roman_is_none():
    from qsl73.normalize import normalize_date
    assert normalize_date("17-XI-93") is None

def test_spec_own_call_portable_to_field():
    assert _match(_card(call_to="SV9/DH3KR"), [_candidate()]).result == MatchResult.CERTAIN

def test_spec_stationcallsign_portable_in_db():
    result = match_card(
        card=_card(call_to="DF1DS/P"),
        candidates=[_candidate()],
        fuzzy_enabled=True,
        portable_suffixes=DEFAULT_SUFFIXES,
        own_callsign="DH3KR",
        station_callsigns={"DF1DS"},
    )
    assert result.result == MatchResult.CERTAIN

def test_spec_itu_prefix_decomposition():
    assert _match(_card(call_from="5Z4/UA4WHX"), [_candidate(callsign="UA4WHX")]).result == MatchResult.CERTAIN

def test_spec_if9_ambiguous_is_uncertain():
    assert _match(_card(call_from="DH3KR/IF9"), [_candidate(callsign="DH3KR")]).result == MatchResult.UNCERTAIN

def test_spec_dl1ejd_log_card_no_suffix_certain():
    card = _card(call_from="DL1EJD")
    cand = _candidate(callsign="DL1EJD/P")
    assert _match(card, [cand]).result == MatchResult.CERTAIN

def test_spec_two_qsos_same_day_tiebreaker():
    cand1 = _candidate(qsoid="id1", time_utc="19:42")
    cand2 = _candidate(qsoid="id2", time_utc="23:00")
    result = _match(_card(time_utc="19:45"), [cand1, cand2])
    assert result.result == MatchResult.CERTAIN
    assert result.matched_qso.qsoid == "id1"

def test_spec_two_qsos_same_day_no_tiebreaker():
    cand1 = _candidate(qsoid="id1", time_utc="19:42")
    cand2 = _candidate(qsoid="id2", time_utc="23:00")
    assert _match(_card(time_utc=None), [cand1, cand2]).result == MatchResult.UNCERTAIN
