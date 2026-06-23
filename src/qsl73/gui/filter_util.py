# QSL73 — Copyright (C) 2026 DF1DS (kainomatic) — SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations

from datetime import date as _date

from qsl73.matching import MatchResult
from qsl73.normalize import BAND_ORDER
from qsl73.run import CardResult, RunResult


# ---------------------------------------------------------------------------
# Workflow-Logik — Durcharbeiten-Reihenfolge (UNCERTAIN → optional NO_MATCH)
# ---------------------------------------------------------------------------


def build_workflow_sequence(
    displayed: list[CardResult],
    done: set[int],
) -> tuple[list[CardResult], list[CardResult]]:
    """Baut Arbeitslisten für den Durcharbeiten-Workflow.

    Phase 1: UNCERTAIN-Karten, Phase 2: NO_MATCH-Karten (in Reihenfolge von displayed).
    done: doc_ids die bereits bearbeitet wurden (manual_pending + written + skipped).
    Gibt (uncertain_offen, no_match_offen) zurück.
    """
    uncertain = [
        c for c in displayed
        if c.outcome.result == MatchResult.UNCERTAIN and c.doc_id not in done
    ]
    no_match = [
        c for c in displayed
        if c.outcome.result == MatchResult.NO_MATCH and c.doc_id not in done
    ]
    return uncertain, no_match


def workflow_card_context(
    card: CardResult,
    uncertain: list[CardResult],
    no_match: list[CardResult],
) -> dict:
    """Gibt Kontext-Dict für den manuellen Zuordnungs-Dialog zurück.

    Keys: phase, card_index (1-basiert), total_cards, has_next.
    phase: MatchResult.UNCERTAIN oder MatchResult.NO_MATCH.
    has_next: ob es in der aktuellen Phase noch eine weitere Karte gibt.
    """
    if card.outcome.result == MatchResult.UNCERTAIN:
        phase_cards = uncertain
        phase = MatchResult.UNCERTAIN
    else:
        phase_cards = no_match
        phase = MatchResult.NO_MATCH

    try:
        idx = next(i for i, c in enumerate(phase_cards) if c.doc_id == card.doc_id)
    except StopIteration:
        idx = 0

    return {
        "phase": phase,
        "card_index": idx + 1,
        "total_cards": max(len(phase_cards), 1),
        "has_next": idx + 1 < len(phase_cards),
    }

FILTER_MODES: tuple[str, ...] = ("all", "certain", "uncertain", "no_match")


def filter_results(run_result: RunResult, mode: str) -> list[CardResult]:
    """Filtert RunResult nach Modus. Unbekannte Modi → leere Liste (kein Absturz)."""
    if mode == "certain":
        return list(run_result.certain)
    if mode == "uncertain":
        return list(run_result.uncertain)
    if mode == "no_match":
        return list(run_result.no_match)
    if mode == "all":
        return list(run_result.certain) + list(run_result.uncertain) + list(run_result.no_match)
    return []


def is_batch_writable(card: CardResult) -> bool:
    """True wenn eine Karte über den Sammel-Schreibvorgang bestätigbar ist.

    Nur CERTAIN-Karten sind sammel-bestätigbar (ADR-0007, ADR-0023).
    UNCERTAIN/NO_MATCH laufen über den manuellen Zuordnungs-Bildschirm.
    """
    return card.outcome.result == MatchResult.CERTAIN


def build_write_selections(
    cards: list[CardResult],
    route: str,
) -> tuple[list[tuple[str, str]], list[int]]:
    """Bildet (selections, confirmed_doc_ids) für write_selected aus einer Kartenliste.

    Filtert auf is_batch_writable-Karten mit gesetztem matched_qso.
    """
    writable = [c for c in cards if is_batch_writable(c) and c.outcome.matched_qso is not None]
    selections = [(c.outcome.matched_qso.qsoid, route) for c in writable]
    confirmed_doc_ids = [c.doc_id for c in writable]
    return selections, confirmed_doc_ids


def qso_display_values(matched) -> tuple:
    """Gibt (call, date, band, mode) aus einem QsoCandidate für die Treeview-Anzeige zurück.

    date wird auf 10 Zeichen gekürzt (YYYY-MM-DD). Leere Felder → '–'.
    Reine Funktion — kein tk, kein DB-Zugriff.
    """
    call = getattr(matched, "callsign", None) or "–"
    raw_date = (getattr(matched, "date", None) or "")[:10]
    date = raw_date or "–"
    band = getattr(matched, "band", None) or "–"
    mode = getattr(matched, "mode", None) or "–"
    return call, date, band, mode


def sort_cards_written_last(cards: list, written: set) -> list:
    """Sortiert geschriebene Karten ans Ende; erhält Reihenfolge innerhalb der Gruppen (stabil).

    Karten in ``written`` (Menge von doc_ids) erscheinen nach allen nicht-geschriebenen.
    """
    not_written = [c for c in cards if c.doc_id not in written]
    done = [c for c in cards if c.doc_id in written]
    return not_written + done


def apply_display_limit(candidates: list, limit: int) -> tuple:
    """Begrenzt Kandidatenliste auf ``limit`` Einträge für die Anzeige.

    Gibt (angezeigte_liste, gesamt_anzahl) zurück.
    limit=0 bedeutet: kein Limit (alle anzeigen).
    """
    total = len(candidates)
    if limit > 0 and total > limit:
        return candidates[:limit], total
    return candidates, total


def qso_by_id(candidates: list, qsoid: str):
    """Gibt den QsoCandidate mit der gegebenen qsoid zurück, oder None.

    Suche in-memory (kein DB-Zugriff). Für QSO-Anzeige bei manuell zugeordneten Karten.
    """
    for c in candidates:
        if getattr(c, "qsoid", None) == qsoid:
            return c
    return None


def written_doc_ids(
    confirmed_doc_ids: list[int],
    selections: list[tuple[str, str]],
    skipped: list[dict],
) -> set[int]:
    """Gibt die Menge der tatsächlich geschriebenen doc_ids zurück.

    confirmed_doc_ids und selections sind index-paarig (merge_selections-Invariante).
    skipped enthält [{"qsoid": str, ...}, ...] aus WriteResult.
    Übersprungene qsoids werden via Mapping auf ihre doc_ids übersetzt und
    aus der Ergebnismenge ausgeschlossen. Unbekannte skip-qsoids werden ignoriert.
    """
    qsoid_to_doc_id: dict[str, int] = {
        qsoid: doc_id
        for (qsoid, _route), doc_id in zip(selections, confirmed_doc_ids)
    }
    skipped_doc_ids: set[int] = set()
    for entry in skipped:
        qsoid = entry.get("qsoid", "")
        if qsoid in qsoid_to_doc_id:
            skipped_doc_ids.add(qsoid_to_doc_id[qsoid])
    return set(confirmed_doc_ids) - skipped_doc_ids


def merge_selections(
    auto_selections: list[tuple[str, str]],
    auto_doc_ids: list[int],
    manual_pending: dict[int, tuple[str, str]],
) -> tuple[list[tuple[str, str]], list[int]]:
    """Führt Auto- und manuelle Selektionen zusammen; dedup by qsoid.

    Auto-Einträge haben Vorrang: eine qsoid wird nur einmal in selections
    aufgenommen; taucht sie bereits in auto_selections auf, wird der manuelle
    Eintrag mit derselben qsoid übersprungen.

    Args:
        auto_selections: (qsoid, route)-Liste aus build_write_selections.
        auto_doc_ids: zugehörige doc_ids (1:1 mit auto_selections).
        manual_pending: doc_id → (qsoid, route) aus manuellen Vormerkungen.

    Returns:
        (merged_selections, merged_doc_ids) — paarweise, ohne doppelte qsoid.
    """
    seen: set[str] = set()
    merged_sel: list[tuple[str, str]] = []
    merged_ids: list[int] = []

    for (qsoid, route), doc_id in zip(auto_selections, auto_doc_ids):
        if qsoid not in seen:
            seen.add(qsoid)
            merged_sel.append((qsoid, route))
            merged_ids.append(doc_id)

    for doc_id, (qsoid, route) in manual_pending.items():
        if qsoid not in seen:
            seen.add(qsoid)
            merged_sel.append((qsoid, route))
            merged_ids.append(doc_id)

    return merged_sel, merged_ids


# ---------------------------------------------------------------------------
# Shift-Klick-Bereichsauswahl (tk-frei, testbar)
# ---------------------------------------------------------------------------


def select_range(
    displayed_ids: list[int],
    selectable_ids: set[int],
    anchor_id: int | None,
    target_id: int,
) -> set[int]:
    """Berechnet die selektierten doc_ids für einen Shift-Klick-Bereich.

    Gibt alle IDs aus selectable_ids zurück, die zwischen anchor_id und target_id
    (inklusive) in der Anzeigereihenfolge liegen. Nicht-selektierbare werden
    übersprungen. Anker None oder nicht in Liste → nur target_id (falls selektierbar).
    """
    if target_id not in selectable_ids:
        return set()
    if anchor_id is None or anchor_id not in displayed_ids or target_id not in displayed_ids:
        return {target_id}
    anchor_idx = displayed_ids.index(anchor_id)
    target_idx = displayed_ids.index(target_id)
    lo, hi = min(anchor_idx, target_idx), max(anchor_idx, target_idx)
    return {did for did in displayed_ids[lo : hi + 1] if did in selectable_ids}


# ---------------------------------------------------------------------------
# Fortschritts-Formatierung (tk-frei, testbar)
# ---------------------------------------------------------------------------


def format_progress_text(done: int, total: int, message: str) -> str:
    """Ergänzt eine Fortschritts-Nachricht um den Prozent-Wert.

    Gibt 'message — X %' zurück wenn total > 0, sonst unverändert 'message'.
    Division durch 0 wird sicher vermieden.
    """
    if total <= 0:
        return message
    pct = done * 100 // total
    return f"{message} — {pct} %"


# ---------------------------------------------------------------------------
# Klick-Sortierung (#28) — tk-frei, testbar (ADR-0052)
# ---------------------------------------------------------------------------


def _date_sort_key(date_str) -> tuple:
    """Sortierschlüssel für YYYY-MM-DD. Leer/ungültig → ans Ende."""
    s = (date_str or "").strip()
    if not s or s == "–":
        return (1, "")
    try:
        _date.fromisoformat(s[:10])
        return (0, s[:10])
    except ValueError:
        return (1, "")


def _band_sort_key(band_str) -> tuple:
    """Sortierschlüssel nach BAND_ORDER-Reihenfolge. Unbekannt/leer → ans Ende."""
    s = (band_str or "").strip()
    if not s or s == "–":
        return (1, 0)
    try:
        return (0, BAND_ORDER.index(s))
    except ValueError:
        return (1, 0)


def _card_sort_key(card, column: str) -> tuple:
    """Extrakt Sortierschlüssel aus CardResult nach Spaltenname."""
    if column == "call":
        v = (card.card_fields.call_from or card.card_fields.call_to or "").upper()
        return (0 if v else 1, v)
    if column == "date":
        return _date_sort_key(card.card_fields.date)
    if column == "band":
        return _band_sort_key(card.card_fields.band)
    if column == "mode":
        v = (card.card_fields.mode or "").upper()
        return (0 if v else 1, v)
    if column == "source":
        v = (card.source or "").upper()
        return (0 if v else 1, v)
    if column == "status":
        order = {MatchResult.CERTAIN: 0, MatchResult.UNCERTAIN: 1, MatchResult.NO_MATCH: 2}
        return (0, order.get(card.outcome.result, 99))
    return (0, "")


def sort_cards_by_column(cards: list, column: str, ascending: bool = True) -> list:
    """Sortiert CardResult-Liste nach Spalte (stabil, tk-frei)."""
    return sorted(cards, key=lambda c: _card_sort_key(c, column), reverse=not ascending)


def sort_cards_written_last_then_by_column(
    cards: list,
    written: set,
    column,
    ascending: bool = True,
) -> list:
    """Zweistufige Sortierung: written-last (Ebene 1) + Klick-Kriterium (Ebene 2, V4).

    column=None → entspricht sort_cards_written_last ohne Klick-Sortierung.
    """
    not_written = [c for c in cards if c.doc_id not in written]
    written_cards = [c for c in cards if c.doc_id in written]
    if column is not None:
        not_written = sort_cards_by_column(not_written, column, ascending)
        written_cards = sort_cards_by_column(written_cards, column, ascending)
    return not_written + written_cards


def _candidate_sort_key(candidate, column: str) -> tuple:
    """Extrakt Sortierschlüssel aus QsoCandidate nach Spaltenname."""
    if column == "callsign":
        v = (getattr(candidate, "callsign", "") or "").upper()
        return (0 if v else 1, v)
    if column == "date":
        return _date_sort_key(getattr(candidate, "date", None))
    if column == "band":
        return _band_sort_key(getattr(candidate, "band", None))
    if column == "mode":
        v = (getattr(candidate, "mode", "") or "").upper()
        return (0 if v else 1, v)
    return (0, "")


def sort_candidates_by_column(candidates: list, column: str, ascending: bool = True) -> list:
    """Sortiert QsoCandidate-Liste nach Spalte (stabil, tk-frei)."""
    return sorted(
        candidates,
        key=lambda c: _candidate_sort_key(c, column),
        reverse=not ascending,
    )


# ---------------------------------------------------------------------------
# Textsuche (#29) — tk-frei, testbar (V5: call/date/band durchsuchbar)
# ---------------------------------------------------------------------------


def text_filter_cards(cards: list, query: str) -> list:
    """Filtert CardResult-Liste per Teilstring über call/date/band (V5, ADR-0052).

    case-insensitiv, Teilstring. Leerer Query → Kopie aller Karten unverändert.
    Durchsuchbare Felder: call_from/call_to, date, band. mode/source/status NICHT.
    """
    q = query.strip().lower() if query else ""
    if not q:
        return list(cards)

    def matches(card) -> bool:
        call = (card.card_fields.call_from or card.card_fields.call_to or "").lower()
        date = (card.card_fields.date or "").lower()
        band = (card.card_fields.band or "").lower()
        return q in call or q in date or q in band

    return [c for c in cards if matches(c)]
