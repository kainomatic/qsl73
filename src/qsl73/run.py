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
