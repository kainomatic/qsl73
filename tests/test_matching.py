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

def test_different_band_is_no_match_regardless_of_fuzzy():
    # Band wird nach Normalisierung EXAKT verglichen — "6n" und "6m" sind verschiedene Bänder
    result = _match(_card(band="6m"), [_candidate(band="6n")], fuzzy=True)
    assert result.result == MatchResult.NO_MATCH

def test_different_mode_is_no_match_regardless_of_fuzzy():
    # Mode wird nach Normalisierung EXAKT verglichen — "FT8" und "FT9" sind verschiedene Modi
    result = _match(_card(mode="FT8"), [_candidate(mode="FT9")], fuzzy=True)
    assert result.result == MatchResult.NO_MATCH

# Suffix-Unterschied-Regel
def test_suffix_differ_exact_fields_is_certain():
    card = _card(call_from="DL1EJD", band="6m", mode="FT8", date="2025-04-02")
    cand = _candidate(callsign="DL1EJD/P", band="6m", mode="FT8", date="2025-04-02")
    assert _match(card, [cand]).result == MatchResult.CERTAIN

def test_suffix_differ_band_mismatch_is_no_match():
    # Band exakt: "6n" ≠ "6m" → Kandidat wird gefiltert → kein Match (kein Kandidat)
    card = _card(call_from="DL1EJD", band="6m", mode="FT8", date="2025-04-02")
    cand = _candidate(callsign="DL1EJD/P", band="6n", mode="FT8", date="2025-04-02")
    assert _match(card, [cand], fuzzy=True).result == MatchResult.NO_MATCH

def test_suffix_differ_reverse_is_certain():
    card = _card(call_from="DL1EJD/P", band="6m", mode="FT8", date="2025-04-02")
    cand = _candidate(callsign="DL1EJD", band="6m", mode="FT8", date="2025-04-02")
    assert _match(card, [cand]).result == MatchResult.CERTAIN

# Unsicher-Fälle
def test_missing_date_three_fields_is_certain():
    # call + band + mode stimmen überein (3/4); Datum fehlt → SICHER (ADR-0016, 3-von-4)
    assert _match(_card(date=None), [_candidate()]).result == MatchResult.CERTAIN

def test_missing_band_three_fields_is_certain():
    # call + date + mode stimmen überein (3/4); Band fehlt → SICHER (ADR-0016, 3-von-4)
    assert _match(_card(band=None), [_candidate()]).result == MatchResult.CERTAIN

def test_missing_mode_three_fields_is_certain():
    # call + date + band stimmen überein (3/4); Mode fehlt → SICHER (ADR-0016, 3-von-4)
    assert _match(_card(mode=None), [_candidate()]).result == MatchResult.CERTAIN

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
    ("6m", "6m", True, MatchResult.CERTAIN),       # exakt gleich → sicher
    ("6m", "2m", True, MatchResult.NO_MATCH),      # verschiedene Bänder → kein Match (auch mit Fuzzy)
    ("6m", "2m", False, MatchResult.NO_MATCH),     # verschiedene Bänder → kein Match
    (None, "6m", True, MatchResult.CERTAIN),       # Band fehlt, call+date+mode = 3/4 → sicher (ADR-0016)
])
def test_band_exact_comparison_in_matching(card_band, cand_band, fuzzy, expected):
    result = _match(_card(band=card_band), [_candidate(band=cand_band)], fuzzy=fuzzy)
    assert result.result == expected


# ---------------------------------------------------------------------------
# "Niemals falsch-positiv"-Fokus-Tests (ADR-0007 Leitregel)
# ---------------------------------------------------------------------------

class TestNeverFalsePositive:

    def test_missing_date_three_others_match_is_certain(self):
        # Datum fehlt, aber call+band+mode stimmen → SICHER (3/4, ADR-0016)
        # fehlend ≠ widersprechend: kein Falsch-Positiv
        assert _match(_card(date=None), [_candidate()]).result == MatchResult.CERTAIN

    def test_missing_band_three_others_match_is_certain(self):
        # Band fehlt, aber call+date+mode stimmen → SICHER (3/4, ADR-0016)
        assert _match(_card(band=None), [_candidate()]).result == MatchResult.CERTAIN

    def test_ambiguous_callsign_similar_qso_is_uncertain(self):
        result = _match(_card(call_from="DH3KR/IF9"), [_candidate(callsign="DH3KR")])
        assert result.result == MatchResult.UNCERTAIN

    def test_similar_qso_wrong_date_is_no_match(self):
        assert _match(_card(date="2025-04-02"), [_candidate(date="2025-04-03")]).result == MatchResult.NO_MATCH

    def test_similar_qso_wrong_band_is_no_match(self):
        assert _match(_card(band="6m"), [_candidate(band="40m")]).result == MatchResult.NO_MATCH

    def test_close_band_different_value_is_no_match(self):
        # "6m" und "2m" sind 1 Zeichen verschieden, aber VERSCHIEDENE Bänder → kein Match
        assert _match(_card(band="6m"), [_candidate(band="2m")], fuzzy=True).result == MatchResult.NO_MATCH

    def test_close_mode_different_value_is_no_match(self):
        # "FT8" und "FT4" sind 1 Zeichen verschieden, aber VERSCHIEDENE Modi → kein Match
        assert _match(_card(mode="FT8"), [_candidate(mode="FT4")], fuzzy=True).result == MatchResult.NO_MATCH

    def test_ssb_vs_ssb_exact_is_certain_but_different_is_no_match(self):
        # Exakter Mode-Vergleich: SSB == SSB → sicher; SSB ≠ CW → kein Match
        assert _match(_card(mode="SSB"), [_candidate(mode="SSB")]).result == MatchResult.CERTAIN
        assert _match(_card(mode="SSB"), [_candidate(mode="CW")], fuzzy=True).result == MatchResult.NO_MATCH

    def test_two_candidates_same_station_no_time_is_uncertain(self):
        cand1 = _candidate(qsoid="id1", time_utc="10:00")
        cand2 = _candidate(qsoid="id2", time_utc="14:00")
        result = _match(_card(time_utc=None), [cand1, cand2])
        assert result.result == MatchResult.UNCERTAIN
        assert result.matched_qso is None

    def test_suffix_differ_band_mismatch_is_not_certain(self):
        # Band exakt: "6n" ≠ "6m" → Kandidat gefiltert → NO_MATCH (nicht CERTAIN, nicht UNCERTAIN)
        # Noch sicherer als vorher: der falsche Kandidat kommt gar nicht durch den Filter
        card = _card(call_from="DL1EJD", band="6m", mode="FT8")
        cand = _candidate(callsign="DL1EJD/P", band="6n", mode="FT8")
        assert _match(card, [cand], fuzzy=True).result == MatchResult.NO_MATCH

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


# ===========================================================================
# Kategorie A: Mehrfachfehler im Rufzeichen (Levenshtein-Distanz ≥ 2)
# ===========================================================================
# Leitregel (ADR-0007): NIE CERTAIN bei Distanz ≥ 2, egal ob fuzzy=an

@pytest.mark.parametrize("card_call,cand_call", [
    ("DKBN3", "DK8NE"),  # 8→B und E→3 = Dist 2
    ("DL8NO", "DK8NE"),  # K→L und E→O = Dist 2
    ("DK0N3", "DK8NE"),  # 8→0 und E→3 = Dist 2
    ("DL0NE", "DK8NE"),  # K→L und 8→0 = Dist 2
    ("D00NE", "DK8NE"),  # K→0 (O/0-Verwechslung) und 8→0 = Dist 2
])
def test_double_ocr_error_callsign_is_never_certain(card_call, cand_call):
    result = _match(_card(call_from=card_call), [_candidate(callsign=cand_call)], fuzzy=True)
    assert result.result == MatchResult.NO_MATCH


# ===========================================================================
# Kategorie A+C: Matrix Fehlerklasse × DB-Zustand
# ===========================================================================
# Verschiedene Fehlerkombinationen gegen einen einzelnen Kandidaten

@pytest.mark.parametrize("card_call,card_band,card_mode,expected", [
    # Rufzeichen exakt, alle Felder vorhanden → sicher
    ("DK8NE", "6m",  "FT8", MatchResult.CERTAIN),
    # Rufzeichen 1 Verleser (Dist 1), alle Felder vorhanden → sicher (fuzzy on)
    ("DK8NF", "6m",  "FT8", MatchResult.CERTAIN),
    # Rufzeichen 2 Verleser (Dist 2), alle Felder → kein Match
    ("DKBN3", "6m",  "FT8", MatchResult.NO_MATCH),
    # Rufzeichen exakt, Band fehlt; call+date+mode = 3/4 → sicher (ADR-0016)
    ("DK8NE", None,  "FT8", MatchResult.CERTAIN),
    # Rufzeichen 1 Verleser, Band fehlt; call+date+mode = 3/4 → sicher (ADR-0016)
    ("DK8NF", None,  "FT8", MatchResult.CERTAIN),
    # Rufzeichen 2 Verleser, Band fehlt → kein Match (Kandidat kommt nicht durch Rufzeichenfilter)
    ("DKBN3", None,  "FT8", MatchResult.NO_MATCH),
])
def test_error_class_db_state_matrix(card_call, card_band, card_mode, expected):
    card = _card(call_from=card_call, band=card_band, mode=card_mode)
    assert _match(card, [_candidate()]).result == expected


# ===========================================================================
# Kategorie C: DB-Kollisionsmuster
# ===========================================================================

class TestDbCollisions:

    # ── C1: Gleiche Station, verschiedene Tage ──────────────────────────────

    def test_same_station_different_days_only_correct_date_matches(self):
        card = _card(date="2025-04-02")
        c_prev  = _candidate(qsoid="prev",  date="2025-04-01")
        c_match = _candidate(qsoid="match", date="2025-04-02")
        c_next  = _candidate(qsoid="next",  date="2025-04-03")
        result = _match(card, [c_prev, c_match, c_next])
        assert result.result == MatchResult.CERTAIN
        assert result.matched_qso.qsoid == "match"

    def test_same_station_multiple_days_no_correct_date_is_no_match(self):
        card = _card(date="2025-04-02")
        c1 = _candidate(qsoid="a", date="2025-04-01")
        c2 = _candidate(qsoid="b", date="2025-04-03")
        assert _match(card, [c1, c2]).result == MatchResult.NO_MATCH

    # ── C2: Gleiche Station, viele Bänder am selben Tag ─────────────────────

    def test_same_station_many_bands_with_correct_band_certain(self):
        card = _card(band="6m")
        cands = [
            _candidate(qsoid="b6m",  band="6m"),   # richtig
            _candidate(qsoid="b2m",  band="2m"),
            _candidate(qsoid="b40m", band="40m"),
            _candidate(qsoid="b20m", band="20m"),
        ]
        result = _match(card, cands)
        assert result.result == MatchResult.CERTAIN
        assert result.matched_qso.qsoid == "b6m"

    def test_same_station_many_bands_missing_band_on_card_is_uncertain(self):
        card = _card(band=None)
        cands = [_candidate(qsoid=f"b{i}", band=b) for i, b in enumerate(["6m", "2m", "40m"])]
        assert _match(card, cands).result == MatchResult.UNCERTAIN

    def test_same_station_single_band_in_db_missing_band_on_card_is_certain(self):
        # Nur ein Kandidat; Band auf Karte unbekannt; call+date+mode stimmen → SICHER (3/4, ADR-0016)
        assert _match(_card(band=None), [_candidate(band="6m")]).result == MatchResult.CERTAIN

    # ── C3: Zwei ähnliche Rufzeichen gleichzeitig in der DB ─────────────────

    def test_exact_card_call_with_similar_fuzzy_candidate_in_db_is_uncertain(self):
        # Karte "DK8NE" (exakt) — DB hat DK8NE UND DK8NF (Dist 1).
        # Beide passieren den Fuzzy-Filter → 2 Kandidaten → UNCERTAIN.
        # Dieses Verhalten ist korrekt: ohne externe Disambiguierung kann der Match
        # nicht automatisch bestätigt werden (Leitregel ADR-0007).
        card = _card(call_from="DK8NE")
        cand_ne = _candidate(callsign="DK8NE", qsoid="ne")
        cand_nf = _candidate(callsign="DK8NF", qsoid="nf")
        result = _match(card, [cand_ne, cand_nf])
        assert result.result == MatchResult.UNCERTAIN  # konservatives Verhalten

    def test_single_ocr_error_matches_two_similar_db_entries_is_uncertain(self):
        # "DK8N0" (E→0 oder F→0, Dist 1) matcht via Fuzzy: DK8NE (Dist 1) UND DK8NF (Dist 1)
        # → zwei Kandidaten → UNCERTAIN: der kritische Falsch-Positiv-Schutztest (ADR-0007)
        card = _card(call_from="DK8N0")
        cand_ne = _candidate(callsign="DK8NE", qsoid="ne")
        cand_nf = _candidate(callsign="DK8NF", qsoid="nf")
        result = _match(card, [cand_ne, cand_nf], fuzzy=True)
        assert result.result == MatchResult.UNCERTAIN
        assert result.result != MatchResult.CERTAIN  # NIE falsch-positiv

    def test_fuzzy_two_candidates_same_time_still_uncertain(self):
        # Selbst wenn beide Kandidaten zur exakt gleichen Zeit eingetragen sind,
        # kann der Zeit-Tie-Breaker nicht disambiguieren → UNCERTAIN
        card = _card(call_from="DK8N0", time_utc="19:42")
        cand_ne = _candidate(callsign="DK8NE", qsoid="ne", time_utc="19:42")
        cand_nf = _candidate(callsign="DK8NF", qsoid="nf", time_utc="19:42")
        result = _match(card, [cand_ne, cand_nf], fuzzy=True)
        assert result.result == MatchResult.UNCERTAIN

    def test_fuzzy_off_similar_calls_only_exact_matches(self):
        # fuzzy=aus: "DK8N0" matcht weder DK8NE noch DK8NF → NO_MATCH
        card = _card(call_from="DK8N0")
        cand_ne = _candidate(callsign="DK8NE", qsoid="ne")
        cand_nf = _candidate(callsign="DK8NF", qsoid="nf")
        assert _match(card, [cand_ne, cand_nf], fuzzy=False).result == MatchResult.NO_MATCH

    # ── C4: Verschiedene Stationen, gleiches Band/Datum ─────────────────────

    def test_different_stations_same_band_date_callsign_discriminates(self):
        # Rufzeichen mit Dist > 1 → wird nicht in matched aufgenommen
        card = _card(call_from="DK8NE")
        cand_correct = _candidate(callsign="DK8NE", qsoid="correct")
        cand_other   = _candidate(callsign="DL1ABC", qsoid="other")  # Dist >> 1
        result = _match(card, [cand_correct, cand_other])
        assert result.result == MatchResult.CERTAIN
        assert result.matched_qso.qsoid == "correct"

    def test_three_stations_same_day_band_correct_call_only_match(self):
        card = _card(call_from="DK8NE")
        c1 = _candidate(callsign="DK8NE", qsoid="correct")
        c2 = _candidate(callsign="DL1ABC", qsoid="other1")
        c3 = _candidate(callsign="OE5XYZ", qsoid="other2")
        result = _match(card, [c1, c2, c3])
        assert result.result == MatchResult.CERTAIN
        assert result.matched_qso.qsoid == "correct"


# ===========================================================================
# Kategorie C: Eigener Call (To-Feld) — Portabel-Varianten
# ===========================================================================

@pytest.mark.parametrize("call_to,expected", [
    ("DH3KR/P",  MatchResult.CERTAIN),   # Portabel-Suffix beim eigenen Call
    ("DO6KBO/P", MatchResult.CERTAIN),   # stationcallsign portabel
    ("DL1XYZ/P", MatchResult.NO_MATCH),  # fremder portabler Call
])
def test_ownership_portable_variants(call_to, expected):
    result = _match(_card(call_to=call_to), [_candidate()])
    assert result.result == expected


# ===========================================================================
# Kategorie D: Doppelter Zusatz im Rufzeichen
# ===========================================================================

def test_double_modifier_prefix_and_suffix_is_never_certain():
    # "SV9/DH3KR/P": decompose gibt "DH3KR/P" zurück (nicht None).
    # "DH3KR/P" hat Dist 2 zu "DK8NE" → kein Match; zu "DH3KR" → Dist 2 → kein Match.
    # Sicherheits-Eigenschaft: NIE CERTAIN (sicherer Ausgang).
    result = _match(_card(call_from="SV9/DH3KR/P"), [_candidate(callsign="DH3KR")])
    assert result.result != MatchResult.CERTAIN


def test_double_modifier_suffix_twice_is_uncertain():
    # "DH3KR/P/MM": decompose → Fall c (None) → from_base None → UNCERTAIN
    result = _match(_card(call_from="DH3KR/P/MM"), [_candidate(callsign="DH3KR")])
    assert result.result == MatchResult.UNCERTAIN


# ===========================================================================
# Kategorie D: Weitere ITU-Präfixe im Matching
# ===========================================================================

@pytest.mark.parametrize("card_call,cand_call", [
    ("VK2/DK8NE", "DK8NE"),  # VK: Australien
    ("JA1/DK8NE", "DK8NE"),  # JA: Japan
    ("ON4/DK8NE", "DK8NE"),  # ON: Belgien
    ("ZL2/DK8NE", "DK8NE"),  # ZL: Neuseeland
])
def test_additional_itu_prefix_matching_is_certain(card_call, cand_call):
    card = _card(call_from=card_call)
    cand = _candidate(callsign=cand_call)
    assert _match(card, [cand]).result == MatchResult.CERTAIN


# ===========================================================================
# Zeit-Tie-Breaker Grenzfälle
# ===========================================================================

def test_tiebreaker_31_minutes_beyond_boundary_is_uncertain():
    # 31 Minuten Abstand = außerhalb des ±30-min-Fensters (Grenzfall)
    cand1 = _candidate(qsoid="close",  time_utc="19:00")
    cand2 = _candidate(qsoid="remote", time_utc="22:00")
    result = _match(_card(time_utc="19:31"), [cand1, cand2])
    # |1171 - 1140| = 31 > 30 → cand1 außerhalb; cand2 weit entfernt → kein Fensterkandidat
    assert result.result == MatchResult.UNCERTAIN


def test_tiebreaker_many_candidates_single_winner():
    # Fünf Kandidaten zu verschiedenen Zeiten; nur einer im ±30-min-Fenster
    cands = [
        _candidate(qsoid="a", time_utc="10:00"),
        _candidate(qsoid="b", time_utc="11:00"),
        _candidate(qsoid="c", time_utc="19:42"),  # nächster an 19:45
        _candidate(qsoid="d", time_utc="22:00"),
        _candidate(qsoid="e", time_utc="23:00"),
    ]
    result = _match(_card(time_utc="19:45"), cands)
    assert result.result == MatchResult.CERTAIN
    assert result.matched_qso.qsoid == "c"


# ===========================================================================
# ADR-0016: Abgestuftes Matching — 3-von-4 + Widerspruchs-Ausschluss
# ===========================================================================


# --- Weniger als 3 positive Felder → UNSICHER --------------------------------

@pytest.mark.parametrize("date,band,mode,label", [
    (None, None, "FT8",       "call+mode = 2/4"),
    (None, "6m", None,        "call+band = 2/4"),
    ("2025-04-02", None, None, "call+date = 2/4"),
    (None, None, None,        "nur call = 1/4"),
])
def test_fewer_than_three_positives_is_uncertain(date, band, mode, label):
    result = _match(_card(date=date, band=band, mode=mode), [_candidate()])
    assert result.result == MatchResult.UNCERTAIN, f"erwartet UNSICHER für {label}"


# --- Widerspruchs-Ausschluss: lesbares Feld ≠ Kandidatenwert → KEIN MATCH ---

def test_band_contradiction_sole_candidate_is_no_match():
    # Band lesbar + widerspricht dem einzigen Kandidaten → Kandidat ausgeschlossen → KEIN MATCH
    # Kritischer Falsch-Positiv-Schutz (ADR-0016, ADR-0007):
    # 1 Kandidat reicht NICHT, wenn ein lesbares Feld klar widerspricht.
    card = _card(call_from="DK8NE", date="2025-04-02", band="20m", mode="FT8")
    cand = _candidate(callsign="DK8NE", date="2025-04-02", band="6m",  mode="FT8")
    assert _match(card, [cand]).result == MatchResult.NO_MATCH


def test_mode_contradiction_sole_candidate_is_no_match():
    # Mode lesbar + widerspricht → Kandidat ausgeschlossen → KEIN MATCH
    card = _card(mode="FT8")
    cand = _candidate(mode="SSB")
    assert _match(card, [cand]).result == MatchResult.NO_MATCH


def test_date_contradiction_sole_candidate_is_no_match():
    # Datum lesbar + widerspricht → Kandidat ausgeschlossen → KEIN MATCH
    card = _card(date="2025-04-02")
    cand = _candidate(date="2025-04-03")
    assert _match(card, [cand]).result == MatchResult.NO_MATCH


def test_contradiction_removes_wrong_candidate_leaving_correct_one_certain():
    # Zwei Kandidaten: einer widerspricht dem Band, einer stimmt → einziger verbleibender → SICHER
    card = _card(band="20m")
    c_wrong = _candidate(qsoid="wrong", band="6m")
    c_right = _candidate(qsoid="right", band="20m")
    result = _match(card, [c_wrong, c_right])
    assert result.result == MatchResult.CERTAIN
    assert result.matched_qso.qsoid == "right"


# --- Band-Eingrenzung bei zwei Kandidaten (konkrete Fälle aus dem Auftrag) ---

def test_band_readable_narrows_two_day_candidates_to_one_certain():
    # Karte Band=20m; DB hat 6m UND 20m QSO am selben Tag → grenzt auf 20m ein → SICHER (ADR-0016)
    card = _card(band="20m")
    c6m  = _candidate(qsoid="c6m",  band="6m")
    c20m = _candidate(qsoid="c20m", band="20m")
    result = _match(card, [c6m, c20m])
    assert result.result == MatchResult.CERTAIN
    assert result.matched_qso.qsoid == "c20m"


def test_band_missing_leaves_two_day_candidates_uncertain():
    # Band fehlt auf Karte; DB hat 6m UND 20m QSO → beide bleiben (kein Widerspruch) → UNSICHER
    card = _card(band=None)
    c6m  = _candidate(qsoid="c6m",  band="6m")
    c20m = _candidate(qsoid="c20m", band="20m")
    result = _match(card, [c6m, c20m])
    assert result.result == MatchResult.UNCERTAIN


# --- Suffix-Unterschied + fehlendes Feld → strenge Regel bleibt (UNSICHER) --

def test_suffix_differ_with_missing_mode_is_uncertain():
    # Suffix-Unterschied-Regel (§6.3): date+band+mode müssen ALLE explizit übereinstimmen.
    # Mode=None → Regel nicht erfüllt → UNSICHER (strenger als 3-von-4, ADR-0016)
    card = _card(call_from="DL1EJD", mode=None)
    cand = _candidate(callsign="DL1EJD/P")
    assert _match(card, [cand]).result == MatchResult.UNCERTAIN


def test_suffix_differ_with_missing_band_is_uncertain():
    # Suffix-Unterschied + Band=None → Regel nicht erfüllt → UNSICHER
    card = _card(call_from="DL1EJD", band=None)
    cand = _candidate(callsign="DL1EJD/P")
    assert _match(card, [cand]).result == MatchResult.UNCERTAIN
