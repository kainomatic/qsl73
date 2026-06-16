"""Matching-Engine: QSL-Karten gegen Log4OM-QSO-Kandidaten.

Leitregel (ADR-0007): Im Zweifel lieber „unsicher" als falsch auto-bestätigen.
Matching-Modell (ADR-0016): Drei Feldzustände (stimmt/fehlt/widerspricht);
3-von-4-Schwelle für „sicher"; fehlende Felder neutral, widersprechende schließen aus.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from rapidfuzz.distance import Levenshtein

from qsl73.callsign import decompose_callsign, is_own_call


TIME_TOLERANCE_MINUTES: int = 30


@dataclass
class CardFields:
    call_from: Optional[str]
    call_to: Optional[str]
    date: Optional[str]
    band: Optional[str]
    mode: Optional[str]
    time_utc: Optional[str] = None


@dataclass
class QsoCandidate:
    qsoid: str
    callsign: str
    date: str
    band: str
    mode: str
    time_utc: Optional[str] = None
    stationcallsign: str = ""


class MatchResult(Enum):
    CERTAIN = "sicher"
    UNCERTAIN = "unsicher"
    NO_MATCH = "kein_match"


@dataclass
class MatchOutcome:
    result: MatchResult
    matched_qso: Optional[QsoCandidate]
    candidates: list = field(default_factory=list)


def _fuzzy_equal(a: str, b: str, fuzzy: bool) -> bool:
    if a.upper() == b.upper():
        return True
    if fuzzy and Levenshtein.distance(a.upper(), b.upper()) == 1:
        return True
    return False


def _exact_equal(a: str, b: str) -> bool:
    return a.upper() == b.upper()


def _time_to_minutes(hhmm: str) -> Optional[int]:
    try:
        parts = hhmm.split(":")
        return int(parts[0]) * 60 + int(parts[1])
    except (ValueError, IndexError, AttributeError):
        return None


def _count_positive_fields(card: CardFields, cand: QsoCandidate) -> int:
    """Zählt positive Übereinstimmungen: Rufzeichen (immer 1) + lesbare, passende Felder."""
    count = 1  # Rufzeichen: per Konstruktion übereinstimmend (Kandidatenfilter-Voraussetzung)
    if card.date is not None and card.date == cand.date:
        count += 1
    if card.band is not None and _exact_equal(card.band, cand.band):
        count += 1
    if card.mode is not None and _exact_equal(card.mode, cand.mode):
        count += 1
    return count


def _check_single_candidate(
    card: CardFields,
    cand: QsoCandidate,
    card_base: str,
    fuzzy_enabled: bool,
    portable_suffixes: list[str],
    matched: list,
) -> MatchOutcome:
    cand_base = decompose_callsign(cand.callsign, portable_suffixes) or cand.callsign.upper()
    suffix_differs = (
        card.call_from.upper() != cand.callsign.upper()
        and card_base.upper() == cand_base.upper()
    )
    if suffix_differs:
        # Suffix-Unterschied-Regel (§6.3): Datum + Band + Mode müssen alle drei
        # explizit übereinstimmen — strenger als 3-von-4, weil die Call-Identität
        # schon unsicher ist.
        fields_all_exact = (
            card.date is not None and card.date == cand.date
            and card.band is not None and _exact_equal(card.band, cand.band)
            and card.mode is not None and _exact_equal(card.mode, cand.mode)
        )
        if fields_all_exact:
            return MatchOutcome(MatchResult.CERTAIN, cand, matched)
        return MatchOutcome(MatchResult.UNCERTAIN, None, matched)

    # 3-von-4-Regel (ADR-0016): mindestens 3 der 4 Felder müssen positiv übereinstimmen.
    # Rufzeichen zählt als 1; mindestens 2 weitere Felder müssen lesbar + passend sein.
    if _count_positive_fields(card, cand) >= 3:
        return MatchOutcome(MatchResult.CERTAIN, cand, matched)
    return MatchOutcome(MatchResult.UNCERTAIN, None, matched)


def match_card(
    card: CardFields,
    candidates: list[QsoCandidate],
    fuzzy_enabled: bool,
    portable_suffixes: list[str],
    own_callsign: str,
    station_callsigns: set[str],
    time_tolerance_minutes: int = TIME_TOLERANCE_MINUTES,
) -> MatchOutcome:
    # 1. Zugehörigkeitsprüfung
    if card.call_to is not None:
        if not is_own_call(card.call_to, own_callsign, station_callsigns, portable_suffixes):
            return MatchOutcome(MatchResult.NO_MATCH, None, [])

    # 2. call_from muss vorhanden und zerlegbar sein
    if card.call_from is None:
        return MatchOutcome(MatchResult.UNCERTAIN, None, [])

    from_base = decompose_callsign(card.call_from, portable_suffixes)
    if from_base is None:
        return MatchOutcome(MatchResult.UNCERTAIN, None, [])

    # 3. Kandidaten einschränken: Rufzeichen muss passen (exakt oder fuzzy-1);
    #    für jedes weitere lesbare Kartenfeld: Kandidaten mit Widerspruch ausschließen.
    #    Fehlende Felder (None) sind neutral — sie grenzen nicht ein.
    matched: list[QsoCandidate] = []
    for cand in candidates:
        cand_base = decompose_callsign(cand.callsign, portable_suffixes) or cand.callsign.upper()
        if not _fuzzy_equal(from_base, cand_base, fuzzy_enabled):
            continue
        if card.date is not None and card.date != cand.date:
            continue
        if card.band is not None and not _exact_equal(card.band, cand.band):
            continue
        if card.mode is not None and not _exact_equal(card.mode, cand.mode):
            continue
        matched.append(cand)

    # 4. Keine Kandidaten → kein Match
    if not matched:
        return MatchOutcome(MatchResult.NO_MATCH, None, [])

    # 5. Genau 1 Kandidat → 3-von-4-Einstufung
    if len(matched) == 1:
        return _check_single_candidate(card, matched[0], from_base, fuzzy_enabled, portable_suffixes, matched)

    # 6. Mehrere Kandidaten → Uhrzeit-Tie-Breaker (±time_tolerance_minutes)
    if card.time_utc is not None:
        card_mins = _time_to_minutes(card.time_utc)
        if card_mins is not None:
            within_window = [
                c for c in matched
                if c.time_utc is not None
                and abs((_time_to_minutes(c.time_utc) or -99999) - card_mins) <= time_tolerance_minutes
            ]
            if len(within_window) == 1:
                return _check_single_candidate(
                    card, within_window[0], from_base, fuzzy_enabled, portable_suffixes, matched
                )

    return MatchOutcome(MatchResult.UNCERTAIN, None, matched)
