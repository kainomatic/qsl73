# QSL73 — Copyright (C) 2026 DF1DS (kainomatic) — SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations

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
