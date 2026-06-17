# src/qsl73/run.py
"""Lauf-Orchestrierung: Sammeln → Auswerten → Matchen → Vorschau → Schreiben.

Schritt 6a — rein lesende Phase (run_pass) und separate Schreibfunktion
(write_selected). Keine GUI-Abhängigkeiten; die GUI (Schritt 6b) ruft diese
Schicht auf.

Öffentliche API:
  run_pass          — vollständiger Lese-Lauf (Paperless + DB), liefert RunResult
  write_selected    — schreibt die bestätigte Auswahl (DB + Paperless-Tags)

Sicherheitsschicht: write_selected ruft ausschließlich log4om_db.write_confirmations
auf (Schema-Check, WAL, Backup, Transaktion, Nebenläufigkeit).
Keine neue Schreiblogik in diesem Modul.
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

from qsl73.config import Config, TagsConfig
from qsl73.log4om_db import (
    WriteResult,
    get_db_fingerprint,
    open_wal_connection,
    write_confirmations,
)
from qsl73.matching import CardFields, MatchOutcome, MatchResult, QsoCandidate, match_card
from qsl73.normalize import normalize_band, normalize_date, normalize_mode
from qsl73.paperless import PaperlessClient
from qsl73.qr import decode_qr_from_pdf, parse_qr_text

_log = logging.getLogger("qsl73")


@dataclass
class CardResult:
    """Ergebnis der Auswertung eines Paperless-Dokuments."""

    doc_id: int
    card_fields: CardFields
    source: str                        # "qr" | "ocr" | "none"
    outcome: MatchOutcome
    existing_confirmations: list[str]  # CT-Werte mit R="Yes" (ohne "QSL") — ADR-0015


@dataclass
class RunResult:
    """Vollständiges Vorschau-Ergebnis eines Lauf-Durchgangs (rein lesend)."""

    certain: list[CardResult]          # auto-bestätigbar
    uncertain: list[CardResult]        # manuell zu prüfen
    no_match: list[CardResult]         # kein Treffer
    fingerprint: dict                  # DB-Fingerabdruck aus Sammelphase → write_selected
    expected_states: dict[str, str]    # qsoid → R-Wert aus Sammelphase → write_selected


@dataclass
class _CandidatesData:
    candidates: list[QsoCandidate]
    station_callsigns: set[str]
    expected_states: dict[str, str]
    existing_confirmations: dict[str, list[str]]
    fingerprint: dict


# ---------------------------------------------------------------------------
# DB-Kandidaten laden
# ---------------------------------------------------------------------------


def load_qso_candidates(db_path: str | Path) -> _CandidatesData:
    """Lädt offene Papier-QSL-Kandidaten aus der Log4OM-DB (rein lesend).

    Vorfilter: nur QSOs mit CT='QSL' und R='No' oder R='Requested'.
    R='Yes' (bereits bestätigt) und R='Invalid' werden NICHT geladen.
    Liefert zudem station_callsigns, expected_states, existing_confirmations
    und einen Fingerabdruck für write_selected (5c-Schutz).
    """
    db_path = Path(db_path)
    fingerprint = get_db_fingerprint(db_path)

    conn = open_wal_connection(db_path)
    try:
        rows = conn.execute(
            """SELECT qsoid, callsign, qsodate, band, mode, stationcallsign, qsoconfirmations
               FROM Log WHERE qsoconfirmations IS NOT NULL"""
        ).fetchall()
    finally:
        conn.close()

    candidates: list[QsoCandidate] = []
    station_callsigns: set[str] = set()
    expected_states: dict[str, str] = {}
    existing_confirmations: dict[str, list[str]] = {}

    for row in rows:
        qsoid, callsign, qsodate, band, mode, stationcallsign, conf_json = row

        if stationcallsign:
            station_callsigns.add(stationcallsign)

        try:
            entries = json.loads(conf_json)
        except (json.JSONDecodeError, TypeError):
            _log.debug("Ungültiges JSON in qsoconfirmations für %r — übersprungen", qsoid)
            continue

        if not isinstance(entries, list):
            continue

        qsl_entry = next(
            (e for e in entries if isinstance(e, dict) and e.get("CT") == "QSL"),
            None,
        )
        if qsl_entry is None:
            continue

        r_value = qsl_entry.get("R", "")
        if r_value not in ("No", "Requested"):
            continue

        # Zeit aus qsodate-Feld extrahieren ('YYYY-MM-DD HH:MM:SSZ' → 'HH:MM')
        time_utc: str | None = None
        if qsodate and len(qsodate) >= 16:
            part = qsodate[11:16]
            if re.match(r"^\d{2}:\d{2}$", part):
                time_utc = part

        candidates.append(
            QsoCandidate(
                qsoid=qsoid,
                callsign=callsign or "",
                date=qsodate or "",
                band=band or "",
                mode=mode or "",
                time_utc=time_utc,
                stationcallsign=stationcallsign or "",
            )
        )
        expected_states[qsoid] = r_value

        # ADR-0015: nicht-QSL-Bestätigungen mit R='Yes' für Anzeige sammeln
        existing = [
            e["CT"]
            for e in entries
            if isinstance(e, dict) and e.get("CT") != "QSL" and e.get("R") == "Yes"
        ]
        if existing:
            existing_confirmations[qsoid] = existing

    return _CandidatesData(
        candidates=candidates,
        station_callsigns=station_callsigns,
        expected_states=expected_states,
        existing_confirmations=existing_confirmations,
        fingerprint=fingerprint,
    )
