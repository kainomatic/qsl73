# QSL73 — Copyright (C) 2026 DF1DS (kainomatic) — SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations

from qsl73.matching import MatchResult
from qsl73.run import CardResult, RunResult

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
