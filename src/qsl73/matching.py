# QSL73 — Copyright (C) 2026 DF1DS (kainomatic) — SPDX-License-Identifier: GPL-3.0-or-later
"""Matching-Engine: QSL-Karten gegen Log4OM-QSO-Kandidaten.

Leitregel (ADR-0007): Im Zweifel lieber „unsicher" als falsch auto-bestätigen.
Matching-Modell (ADR-0016): Drei Feldzustände (stimmt/fehlt/widerspricht);
3-von-4-Schwelle für „sicher"; fehlende Felder neutral, widersprechende schließen aus.

Mehrere Fremdcall-Kandidaten + Fuzzy erzwingt „unsicher" (ADR-0056, verschärft
ADR-0016): Trägt eine Karte mehrere erkannte Fremd-Rufzeichen (`call_from_candidates`,
z. B. echter Absender + Druckvermerk), wird jeder Kandidat unabhängig gematcht und über
die getroffenen DB-QSOs zusammengeführt. Ein Rufzeichen-Treffer, der auf Unschärfe
(Levenshtein-1) beruht, darf NIE automatisch „sicher" werden — nur ein exakter Treffer
mit erfüllter 3-von-4-/Suffix-Regel darf automatisch bestätigen.

Vergleichsprinzip: Band und Mode werden normalisiert-gegen-normalisiert verglichen —
Kartenwert UND gelesener DB-Kandidatenwert werden im Speicher durch dieselbe
Normalisierungsfunktion geschickt, dann verglichen. Kein DB-Write, rein lesend.
Damit matchen äquivalente Schreibweisen (z. B. DB „USB"/„LSB" ↔ Karte „SSB") korrekt.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from rapidfuzz.distance import Levenshtein

from qsl73.callsign import decompose_callsign, is_own_call
from qsl73.normalize import normalize_band, normalize_mode


TIME_TOLERANCE_MINUTES: int = 30


@dataclass
class CardFields:
    call_from: Optional[str]
    call_to: Optional[str]
    date: Optional[str]
    band: Optional[str]
    mode: Optional[str]
    time_utc: Optional[str] = None
    # Mehrere erkannte Fremd-Rufzeichen-Kandidaten (ADR-0056). Konvention:
    # ist diese Liste nicht leer, nutzt match_card sie statt des einzelnen
    # call_from; call_from bleibt für Abwärtskompatibilität erhalten (Aufrufer,
    # die nur einen Kandidaten kennen, setzen weiterhin nur call_from).
    call_from_candidates: list[str] = field(default_factory=list)


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


class MatchReasonCode(Enum):
    """Grund-Katalog für UNCERTAIN/NO_MATCH-Einstufungen (ADR-0058, Issue #37).

    CERTAIN-Ergebnisse tragen keinen Grund (reason=None) — nur UNCERTAIN/NO_MATCH.
    """
    NOT_OWN_CALL = "not_own_call"
    NO_CALL = "no_call"
    CALL_NOT_DECOMPOSABLE = "call_not_decomposable"
    NO_CANDIDATE = "no_candidate"
    MULTI_CALL = "multi_call"
    CONTRADICTION = "contradiction"
    FUZZY_CALL = "fuzzy_call"
    TOO_FEW_FIELDS = "too_few_fields"
    MULTI_QSO = "multi_qso"


@dataclass
class MatchReason:
    """Klartext-Erklärung einer UNCERTAIN/NO_MATCH-Einstufung (ADR-0058).

    code: stabiler Reason-Code (Enum, für Logik/Tests).
    text: fertiger deutscher Klartext mit konkreten Werten (für GUI-Anzeige).
    details: strukturierte Rohdaten hinter dem Text (für spätere Auswertung/i18n).
    """
    code: MatchReasonCode
    text: str
    details: dict = field(default_factory=dict)


@dataclass
class MatchOutcome:
    result: MatchResult
    matched_qso: Optional[QsoCandidate]
    candidates: list = field(default_factory=list)
    reason: Optional[MatchReason] = None


def _rufzeichen_kind(a: str, b: str, fuzzy: bool) -> Optional[str]:
    """Vergleicht zwei bereits zerlegte Stammrufzeichen.

    Rückgabe "exact" (identisch), "fuzzy" (Levenshtein-1, nur wenn fuzzy=True)
    oder None (kein Match). match_card unterscheidet EXAKT von FUZZY, weil nur
    ein exakter Treffer automatisch „sicher" werden darf (ADR-0056/R2 vs. R3).
    """
    if a.upper() == b.upper():
        return "exact"
    if fuzzy and Levenshtein.distance(a.upper(), b.upper()) == 1:
        return "fuzzy"
    return None


def _time_to_minutes(hhmm: str) -> Optional[int]:
    try:
        parts = hhmm.split(":")
        return int(parts[0]) * 60 + int(parts[1])
    except (ValueError, IndexError, AttributeError):
        return None


def _cand_date_day(cand_date: str) -> str:
    """Schneidet Zeitanteil aus DB-Datum: 'YYYY-MM-DD HH:MM:SSZ' → 'YYYY-MM-DD'."""
    return cand_date[:10] if cand_date else ""


def _norm_bands_equal(card_band: str, cand_band: str) -> bool:
    """Normalisiert beide Werte im Speicher, dann Vergleich. None (unbekannt) → kein Match."""
    n_card = normalize_band(card_band)
    n_cand = normalize_band(cand_band)
    return n_card is not None and n_cand is not None and n_card == n_cand


def _norm_modes_equal(card_mode: str, cand_mode: str) -> bool:
    """Normalisiert beide Werte im Speicher, dann Vergleich. None (unbekannt) → kein Match."""
    n_card = normalize_mode(card_mode)
    n_cand = normalize_mode(cand_mode)
    return n_card is not None and n_cand is not None and n_card == n_cand


def _count_positive_fields(card: CardFields, cand: QsoCandidate) -> int:
    """Zählt positive Übereinstimmungen: Rufzeichen (immer 1) + lesbare, passende Felder.

    Alle Vergleiche normalisiert-gegen-normalisiert (In-Memory, kein DB-Write).
    """
    count = 1  # Rufzeichen: per Konstruktion übereinstimmend (Kandidatenfilter-Voraussetzung)
    if card.date is not None and card.date == _cand_date_day(cand.date):
        count += 1
    if card.band is not None and _norm_bands_equal(card.band, cand.band):
        count += 1
    if card.mode is not None and _norm_modes_equal(card.mode, cand.mode):
        count += 1
    return count


def _fields_rule_certain(
    card: CardFields,
    cand: QsoCandidate,
    card_call: str,
    from_base: str,
    portable_suffixes: list[str],
) -> bool:
    """3-von-4-Regel (ADR-0016) inkl. Suffix-Unterschied-Regel (ADR-0013).

    Reine Feldregel — unabhängig davon, ob der Rufzeichen-Treffer exakt oder
    fuzzy war. Die Exaktheits-Gate (nur exakt darf „sicher" werden) sitzt in
    match_card (ADR-0056/R2 vs. R3), nicht hier.
    """
    cand_base = decompose_callsign(cand.callsign, portable_suffixes) or cand.callsign.upper()
    suffix_differs = (
        card_call.upper() != cand.callsign.upper()
        and from_base.upper() == cand_base.upper()
    )
    if suffix_differs:
        # Suffix-Unterschied-Regel (§6.3): Datum + Band + Mode müssen alle drei
        # explizit übereinstimmen — strenger als 3-von-4, weil die Call-Identität
        # schon unsicher ist. Vergleiche ebenfalls normalisiert-gegen-normalisiert.
        return (
            card.date is not None and card.date == _cand_date_day(cand.date)
            and card.band is not None and _norm_bands_equal(card.band, cand.band)
            and card.mode is not None and _norm_modes_equal(card.mode, cand.mode)
        )

    # 3-von-4-Regel (ADR-0016): mindestens 3 der 4 Felder müssen positiv übereinstimmen.
    # Rufzeichen zählt als 1; mindestens 2 weitere Felder müssen lesbar + passend sein.
    return _count_positive_fields(card, cand) >= 3


def _filter_candidates_for_call(
    card: CardFields,
    candidates: list[QsoCandidate],
    from_base: str,
    fuzzy_enabled: bool,
    portable_suffixes: list[str],
) -> list[tuple[QsoCandidate, str]]:
    """Filtert Kandidaten für EINEN Fremdcall-Kandidaten der Karte.

    Rufzeichen muss passen (exakt oder fuzzy-1); für jedes weitere lesbare
    Kartenfeld: Kandidaten mit Widerspruch ausschließen. Fehlende Felder (None)
    sind neutral — sie grenzen nicht ein. Band/Mode: normalisiert-gegen-
    normalisiert (In-Memory, kein DB-Write). Datum: Zeitanteil des DB-Werts
    wird im Speicher abgeschnitten (Tagesvergleich).

    Rückgabe: Liste aus (Kandidat, "exact"|"fuzzy") — die Rufzeichen-Exaktheit
    wird mitgeführt (ADR-0056).
    """
    result: list[tuple[QsoCandidate, str]] = []
    for cand in candidates:
        cand_base = decompose_callsign(cand.callsign, portable_suffixes) or cand.callsign.upper()
        kind = _rufzeichen_kind(from_base, cand_base, fuzzy_enabled)
        if kind is None:
            continue
        if card.date is not None and card.date != _cand_date_day(cand.date):
            continue
        if card.band is not None and not _norm_bands_equal(card.band, cand.band):
            continue
        if card.mode is not None and not _norm_modes_equal(card.mode, cand.mode):
            continue
        result.append((cand, kind))
    return result


def _resolve_time_tiebreaker(
    card: CardFields,
    matched: list[tuple[QsoCandidate, str]],
    time_tolerance_minutes: int,
) -> list[tuple[QsoCandidate, str]]:
    """Reduziert mehrere Kandidaten DESSELBEN Fremdcalls per Uhrzeit-Toleranz.

    Genau 1 Kandidat im ±time_tolerance_minutes-Fenster → reduzierte Liste mit
    diesem einen Eintrag. Sonst (kein oder mehrere im Fenster) → unveränderte
    Liste zurück; die Mehrdeutigkeit bleibt bestehen und wirkt sich in
    match_card auf R4 aus.
    """
    if len(matched) <= 1 or card.time_utc is None:
        return matched
    card_mins = _time_to_minutes(card.time_utc)
    if card_mins is None:
        return matched
    within_window = [
        (cand, kind) for cand, kind in matched
        if cand.time_utc is not None
        and abs((_time_to_minutes(cand.time_utc) or -99999) - card_mins) <= time_tolerance_minutes
    ]
    if len(within_window) == 1:
        return within_window
    return matched


def _dedup_by_qsoid(cands: list[QsoCandidate]) -> list[QsoCandidate]:
    seen: set[str] = set()
    result: list[QsoCandidate] = []
    for c in cands:
        if c.qsoid not in seen:
            seen.add(c.qsoid)
            result.append(c)
    return result


# ---------------------------------------------------------------------------
# Grund-Erklärung (ADR-0058, Issue #37) — reine Textbausteine, kein Einfluss
# auf die Matching-Entscheidung selbst. Werden ausschließlich an den Stellen
# in match_card aufgerufen, an denen die Entscheidung bereits feststeht.
# ---------------------------------------------------------------------------

def _reason_not_own_call(call_to: str) -> MatchReason:
    text = f"Karte adressiert an „{call_to}\" – das entspricht nicht dem eigenen Rufzeichen."
    return MatchReason(MatchReasonCode.NOT_OWN_CALL, text, {"call_to": call_to})


def _reason_no_call() -> MatchReason:
    text = "Kein Rufzeichen im OCR-Text erkannt."
    return MatchReason(MatchReasonCode.NO_CALL, text, {})


def _reason_call_not_decomposable(all_calls: list[str], undecomposable_calls: list[str]) -> MatchReason:
    if len(undecomposable_calls) == len(all_calls):
        if len(all_calls) == 1:
            text = f"Rufzeichen „{all_calls[0]}\" hat kein gültiges Rufzeichenformat und ist nicht durchsuchbar."
        else:
            joined = ", ".join(all_calls)
            text = f"Keines der gelesenen Rufzeichen ({joined}) hat ein gültiges Rufzeichenformat."
    else:
        joined = ", ".join(undecomposable_calls)
        text = (
            f"Rufzeichen „{joined}\" hat kein gültiges Rufzeichenformat und ist nicht "
            f"durchsuchbar — die übrigen gelesenen Rufzeichen fanden ebenfalls kein "
            f"passendes offenes QSO."
        )
    return MatchReason(
        MatchReasonCode.CALL_NOT_DECOMPOSABLE, text,
        {"calls": all_calls, "undecomposable": undecomposable_calls},
    )


def _reason_no_candidate(call: str) -> MatchReason:
    text = f"Kein offenes QSO mit „{call}\" in der Datenbank."
    return MatchReason(MatchReasonCode.NO_CANDIDATE, text, {"call": call})


def _reason_multi_call(calls: list[str]) -> MatchReason:
    joined = ", ".join(calls)
    text = (
        f"{len(calls)} mögliche Rufzeichen gelesen ({joined}), keines passt exakt "
        f"zu einem offenen QSO."
    )
    return MatchReason(MatchReasonCode.MULTI_CALL, text, {"calls": calls})


def _reason_contradiction(card: CardFields, cand: QsoCandidate, call: str) -> MatchReason:
    mismatches: list[tuple[str, str, str]] = []
    if card.date is not None and card.date != _cand_date_day(cand.date):
        mismatches.append(("Datum", card.date, _cand_date_day(cand.date)))
    if card.band is not None and not _norm_bands_equal(card.band, cand.band):
        mismatches.append(("Band", card.band, cand.band))
    if card.mode is not None and not _norm_modes_equal(card.mode, cand.mode):
        mismatches.append(("Mode", card.mode, cand.mode))
    if mismatches:
        field_name, card_val, db_val = mismatches[0]
        text = (
            f"Rufzeichen „{call}\" passt zu einem offenen QSO, aber {field_name} "
            f"widerspricht (Karte {card_val}, QSO {db_val})."
        )
    else:
        # Praktisch nicht erreichbar (Filter hätte sonst einen Treffer erzeugt) —
        # defensiver Fallback, kein Absturz.
        text = f"Rufzeichen „{call}\" passt zu einem offenen QSO, aber weitere Felder passen nicht."
    return MatchReason(
        MatchReasonCode.CONTRADICTION, text,
        {"call": call, "mismatches": mismatches},
    )


def _diagnose_no_hits(
    card: CardFields,
    candidates: list[QsoCandidate],
    calls: list[str],
    fuzzy_enabled: bool,
    portable_suffixes: list[str],
) -> MatchReason:
    """Erklärt eine NO_MATCH-Entscheidung bei leerer Trefferliste (R1, ADR-0056).

    Reine Diagnose — beeinflusst die Matching-Entscheidung nicht. Prüft, ob
    mindestens ein gelesener Fremdcall überhaupt ein DB-Rufzeichen trifft
    (unabhängig von Datum/Band/Mode): wenn ja, ist der Grund ein widersprechendes
    Feld (CONTRADICTION); sonst gab es entweder mehrere gelesene Rufzeichen, für
    die keines matchte (MULTI_CALL), oder nur eines (NO_CANDIDATE).
    """
    for call in calls:
        from_base = decompose_callsign(call, portable_suffixes)
        if from_base is None:
            continue
        for cand in candidates:
            cand_base = decompose_callsign(cand.callsign, portable_suffixes) or cand.callsign.upper()
            kind = _rufzeichen_kind(from_base, cand_base, fuzzy_enabled)
            if kind is not None:
                return _reason_contradiction(card, cand, call)
    if len(calls) > 1:
        return _reason_multi_call(calls)
    return _reason_no_candidate(calls[0])


def _reason_fuzzy_call(call: str, matched_callsign: str) -> MatchReason:
    text = (
        f"Rufzeichen nur unscharf erkannt („{call}\" ≈ „{matched_callsign}\") – "
        f"unscharfe Treffer werden nie automatisch bestätigt (ADR-0056)."
    )
    return MatchReason(
        MatchReasonCode.FUZZY_CALL, text,
        {"read": call, "matched": matched_callsign},
    )


def _reason_too_few_fields(
    card: CardFields,
    cand: QsoCandidate,
    call: str,
    from_base: str,
    portable_suffixes: list[str],
) -> MatchReason:
    cand_base = decompose_callsign(cand.callsign, portable_suffixes) or cand.callsign.upper()
    suffix_differs = (
        call.upper() != cand.callsign.upper()
        and from_base.upper() == cand_base.upper()
    )
    missing = [
        name for name, val in (("Datum", card.date), ("Band", card.band), ("Mode", card.mode))
        if val is None
    ]
    missing_txt = " und ".join(missing) if missing else "keine weiteren Felder"
    if suffix_differs:
        text = (
            f"Rufzeichen-Zusatz weicht ab (Karte „{call}\", QSO „{cand.callsign}\") – "
            f"dafür müssen Datum, Band und Mode alle übereinstimmen. Fehlend: {missing_txt}."
        )
    else:
        text = (
            f"Zu wenig Felder lesbar — {missing_txt} fehlen (nötig: Rufzeichen + 2 weitere)."
        )
    return MatchReason(
        MatchReasonCode.TOO_FEW_FIELDS, text,
        {"call": call, "missing": missing, "suffix_differs": suffix_differs},
    )


def _reason_multi_qso(hits: dict[str, tuple[QsoCandidate, str, str, str]]) -> MatchReason:
    calls_used = sorted({call for _cand, _kind, call, _from_base in hits.values()})
    if len(calls_used) == 1:
        times = sorted(
            f"{_cand_date_day(cand.date)} {cand.time_utc or '?'}"
            for cand, _kind, _call, _from_base in hits.values()
        )
        joined_times = " und ".join(times)
        text = (
            f"{len(hits)} offene QSOs passen zu „{calls_used[0]}\" ({joined_times}), "
            f"Uhrzeit auf der Karte nicht eindeutig lesbar."
        )
    else:
        joined_calls = ", ".join(calls_used)
        text = (
            f"Mehrere gelesene Rufzeichen ({joined_calls}) passen jeweils zu "
            f"unterschiedlichen offenen QSOs — mehrdeutig."
        )
    return MatchReason(
        MatchReasonCode.MULTI_QSO, text,
        {"qso_count": len(hits), "calls": calls_used},
    )


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
            return MatchOutcome(MatchResult.NO_MATCH, None, [], _reason_not_own_call(card.call_to))

    # 2. Fremdcall-Kandidatenquelle bestimmen (ADR-0056): call_from_candidates
    #    hat Vorrang (mehrere erkannte Fremdcalls, z. B. echter Absender +
    #    Druckvermerk); sonst Rückfall auf das einzelne call_from (Abwärtskomp.).
    if card.call_from_candidates:
        calls = list(card.call_from_candidates)
    elif card.call_from is not None:
        calls = [card.call_from]
    else:
        calls = []
    if not calls:
        return MatchOutcome(MatchResult.UNCERTAIN, None, [], _reason_no_call())

    # 3. Für jeden Fremdcall-Kandidaten unabhängig matchen (Zerlegung, Filter,
    #    Zeit-Tie-Breaker innerhalb des Calls); Treffer über alle Calls nach
    #    qsoid zusammenführen (Wahrheitstabelle R1-R4, ADR-0056).
    hits: dict[str, tuple[QsoCandidate, str, str, str]] = {}  # qsoid -> (cand, kind, call, from_base)
    seen_candidates: list[QsoCandidate] = []
    any_undecomposable = False
    undecomposable_calls: list[str] = []

    for call in calls:
        from_base = decompose_callsign(call, portable_suffixes)
        if from_base is None:
            any_undecomposable = True
            undecomposable_calls.append(call)
            continue

        matched = _filter_candidates_for_call(card, candidates, from_base, fuzzy_enabled, portable_suffixes)
        if not matched:
            continue

        resolved = _resolve_time_tiebreaker(card, matched, time_tolerance_minutes)

        for cand, kind in resolved:
            seen_candidates.append(cand)
            existing = hits.get(cand.qsoid)
            if existing is None or (existing[1] == "fuzzy" and kind == "exact"):
                hits[cand.qsoid] = (cand, kind, call, from_base)

    # R1: kein Fremdcall-Kandidat matcht ein DB-QSO.
    if not hits:
        if any_undecomposable:
            # Rufzeichen nicht zerlegbar (ADR-0013 Fall c) — nicht durchsuchbar;
            # das ist KEIN bestätigtes "kein Match", sondern UNSICHER (ADR-0007).
            reason = _reason_call_not_decomposable(calls, undecomposable_calls)
            return MatchOutcome(MatchResult.UNCERTAIN, None, [], reason)
        reason = _diagnose_no_hits(card, candidates, calls, fuzzy_enabled, portable_suffixes)
        return MatchOutcome(MatchResult.NO_MATCH, None, [], reason)

    # R4: mehrere verschiedene DB-QSOs getroffen → mehrdeutig, kein Auto-Match.
    if len(hits) > 1:
        return MatchOutcome(
            MatchResult.UNCERTAIN, None, _dedup_by_qsoid(seen_candidates), _reason_multi_qso(hits)
        )

    # Genau 1 getroffenes DB-QSO.
    cand, kind, call, from_base = next(iter(hits.values()))

    if kind == "fuzzy":
        # R3: Fuzzy-Rufzeichen erzwingt UNSICHER — nie automatische Bestätigung,
        # Kandidat bleibt zur Vorbefüllung im manuellen Dialog verfügbar.
        return MatchOutcome(MatchResult.UNCERTAIN, None, [cand], _reason_fuzzy_call(call, cand.callsign))

    # R2: exakter Rufzeichen-Treffer — 3-von-4-/Suffix-Regel entscheidet.
    if _fields_rule_certain(card, cand, call, from_base, portable_suffixes):
        return MatchOutcome(MatchResult.CERTAIN, cand, [cand], None)
    reason = _reason_too_few_fields(card, cand, call, from_base, portable_suffixes)
    return MatchOutcome(MatchResult.UNCERTAIN, None, [cand], reason)
