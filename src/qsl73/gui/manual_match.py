# QSL73 — Copyright (C) 2026 DF1DS (kainomatic) — SPDX-License-Identifier: GPL-3.0-or-later
"""Manuelle Zuordnungs-Logik (tk-frei, rein funktional).

Schritt 6c-1 — Such-/Filter-Logik für den manuellen Zuordnungs-Bildschirm.
Kein GUI-Code, kein DB-Zugriff, kein Schreiben.

Öffentliche API:
  ManualQuery          — optionale Suchfelder (Nutzereingabe / OCR-Vorschlag)
  search_candidates    — filtert + rankt Kandidatenliste in-memory
  make_manual_selection — erzeugt (qsoid, route)-Eintrag für Schreib-Korb
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from qsl73.log4om_write import VALID_ROUTES
from qsl73.matching import QsoCandidate
from qsl73.normalize import normalize_band, normalize_date, normalize_mode


@dataclass
class ManualQuery:
    """Suchfelder für die manuelle Zuordnung — alle Felder optional.

    None bedeutet: Feld nicht einschränken (neutral, kein Filter).
    """

    call: Optional[str] = None
    date: Optional[str] = None
    band: Optional[str] = None
    mode: Optional[str] = None


# ---------------------------------------------------------------------------
# Ranking-Funktion — separat und austauschbar (ADR-0028 Entscheidung 4)
# ---------------------------------------------------------------------------


def _rank_score(query: ManualQuery, cand: QsoCandidate) -> int:
    """Anzahl exakt übereinstimmender gesetzter Felder (0–4).

    Höher = bessere Übereinstimmung. Wird ausschließlich für die Reihenfolge
    verwendet; der Score selbst taucht nicht in der Rückgabe auf.
    """
    score = 0

    if query.call is not None:
        q_call = query.call.upper().strip()
        if q_call and cand.callsign.upper() == q_call:
            score += 1

    if query.date is not None:
        q_date = normalize_date(query.date)
        c_date = normalize_date(cand.date[:10]) if cand.date else None
        if q_date is not None and c_date is not None and q_date == c_date:
            score += 1

    if query.band is not None:
        q_band = normalize_band(query.band)
        c_band = normalize_band(cand.band)
        if q_band is not None and c_band is not None and q_band == c_band:
            score += 1

    if query.mode is not None:
        q_mode = normalize_mode(query.mode)
        c_mode = normalize_mode(cand.mode)
        if q_mode is not None and c_mode is not None and q_mode == c_mode:
            score += 1

    return score


# ---------------------------------------------------------------------------
# Filter-Funktion
# ---------------------------------------------------------------------------


def _matches_query(query: ManualQuery, cand: QsoCandidate) -> bool:
    """True wenn der Kandidat alle gesetzten Filterfelder erfüllt."""

    if query.call is not None:
        q_call = query.call.upper().strip()
        if q_call and q_call not in cand.callsign.upper():
            return False

    if query.date is not None:
        q_date = normalize_date(query.date)
        c_date = normalize_date(cand.date[:10]) if cand.date else None
        if q_date is not None and (c_date is None or q_date != c_date):
            return False

    if query.band is not None:
        q_band = normalize_band(query.band)
        c_band = normalize_band(cand.band)
        if q_band is not None and (c_band is None or q_band != c_band):
            return False

    if query.mode is not None:
        q_mode = normalize_mode(query.mode)
        c_mode = normalize_mode(cand.mode)
        if q_mode is not None and (c_mode is None or q_mode != c_mode):
            return False

    return True


# ---------------------------------------------------------------------------
# Öffentliche API
# ---------------------------------------------------------------------------


def search_candidates(
    query: ManualQuery,
    candidates: list[QsoCandidate],
) -> list[QsoCandidate]:
    """Filtert und rankt die Kandidatenliste in-memory.

    Suchraum ist ausschließlich die übergebene Liste (offene QSOs, R='No'/'Requested').
    Kein DB-Zugriff, keine Exceptions bei leeren/teilbefüllten Eingaben.

    Args:
        query: Suchfelder; None-Felder schränken nicht ein.
        candidates: Offene QSO-Kandidaten (bereits gefiltert durch load_qso_candidates).

    Returns:
        Gefilterte + nach Trefferqualität absteigend sortierte Liste.
        Leerer query (alle Felder None) → vollständige Kandidatenliste, Eingabereihenfolge.
    """
    _is_empty = (
        query.call is None
        and query.date is None
        and query.band is None
        and query.mode is None
    )
    if _is_empty:
        return list(candidates)

    matched = [c for c in candidates if _matches_query(query, c)]
    matched.sort(key=lambda c: _rank_score(query, c), reverse=True)
    return matched


def make_manual_selection(qsoid: str, route: str) -> tuple[str, str]:
    """Erzeugt den (qsoid, route)-Eintrag für den gemeinsamen Schreib-Korb.

    Derselbe Vertrag wie Auto-Treffer — kein separater Schreibpfad (ADR-0028).

    Args:
        qsoid: QSO-Primärschlüssel.
        route: "bureau", "direct" oder "undefined".

    Returns:
        (qsoid, route) — direkt verwendbar für write_selected / write_confirmations.

    Raises:
        ValueError: route ist kein erlaubter Wert.
    """
    if route not in VALID_ROUTES:
        raise ValueError(
            f"Ungültiger route-Wert {route!r}. Erlaubt: {sorted(VALID_ROUTES)}"
        )
    return (qsoid, route)
