# QSL73 — Copyright (C) 2026 DF1DS (kainomatic) — SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations

from qsl73.matching import MatchResult
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
