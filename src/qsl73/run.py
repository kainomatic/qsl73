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
from dataclasses import dataclass
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
# OCR-Textextraktion (intern)
# ---------------------------------------------------------------------------

_RE_FROM = re.compile(
    r'(?i)\b(?:from|de|fm)\b\s*[:\s]\s*([A-Z0-9]{1,3}[0-9][A-Z0-9]{0,4}(?:/[A-Z0-9]+)?)'
)
_RE_TO = re.compile(
    r'(?i)\b(?:to|ur|dest)\b\s*[:\s]\s*([A-Z0-9]{1,3}[0-9][A-Z0-9]{0,4}(?:/[A-Z0-9]+)?)'
)
_RE_DATE = re.compile(r'(?i)(?:date|datum|dat)\s*[:\s]\s*(\S+)')
_RE_BAND = re.compile(r'(?i)(?:band|freq(?:uency)?)\s*[:\s]\s*(\S+)')
_RE_MODE = re.compile(r'(?i)(?:mode?|mod|emission)\s*[:\s]\s*(\S+)')
_RE_TIME = re.compile(r'(?i)(?:time|zeit|utc|gmt)\s*[:\s]\s*(\d{1,2}:\d{2})')


def _first(pattern: re.Pattern, text: str) -> Optional[str]:
    m = pattern.search(text)
    return m.group(1) if m else None


def _parse_ocr_text(ocr_text: str) -> tuple[CardFields, str]:
    """Extrahiert CardFields aus OCR-Text. Kein Absturz (ADR-0012).

    Strategie:
    1. Strukturierter Key:Value-Parse (parse_qr_text — DARC-Format u. ä.)
    2. Regex-Fallback für beschriftete Felder (From/To/Date/Band/Mode)
    3. Alle None → CardFields mit None-Feldern (lieber 'unsicher' als raten)

    Returns:
        (CardFields, source) — source ist "ocr" wenn Text vorhanden, "none" wenn leer.
    """
    if not ocr_text or not ocr_text.strip():
        return CardFields(None, None, None, None, None), "none"

    # Versuch 1: strukturierter Parse (Key:Value-Format)
    structured = parse_qr_text(ocr_text)
    if structured is not None:
        return structured, "ocr"

    # Versuch 2: Regex-Extraktion aus beschrifteten Feldern
    raw_date = _first(_RE_DATE, ocr_text)
    raw_band = _first(_RE_BAND, ocr_text)
    raw_mode = _first(_RE_MODE, ocr_text)
    raw_time = _first(_RE_TIME, ocr_text)

    return CardFields(
        call_from=_first(_RE_FROM, ocr_text),
        call_to=_first(_RE_TO, ocr_text),
        date=normalize_date(raw_date) if raw_date else None,
        band=normalize_band(raw_band) if raw_band else None,
        mode=normalize_mode(raw_mode) if raw_mode else None,
        time_utc=raw_time,  # Regex liefert bereits HH:MM
    ), "ocr"


# ---------------------------------------------------------------------------
# Karten-Auswertung (intern)
# ---------------------------------------------------------------------------


def evaluate_card(
    doc: dict,
    paperless_client: PaperlessClient,
) -> tuple[CardFields, str]:
    """Ermittelt CardFields für ein Paperless-Dokument (QR-Vorrang vor OCR).

    Reihenfolge (§6.1 / ADR-0007):
    1. QR-Code aus PDF-Bytes (get_document_download)
    2. OCR-Text (doc['content'], im Listen-Response enthalten)

    Kein Absturz bei fehlerhafter Eingabe (ADR-0012).

    Returns:
        (CardFields, source) — source: "qr" | "ocr" | "none"
    """
    doc_id = doc["id"]

    # Versuch 1: QR-Code aus heruntergeladenem PDF
    try:
        pdf_bytes = paperless_client.get_document_download(doc_id)
        qr_fields = decode_qr_from_pdf(pdf_bytes)
        if qr_fields is not None:
            return qr_fields, "qr"
    except Exception as exc:
        _log.debug("QR-Dekodierung fehlgeschlagen für Dok. %s: %s", doc_id, exc)

    # Versuch 2: OCR-Text aus dem Dokument-Dict
    ocr_text = doc.get("content") or ""
    return _parse_ocr_text(ocr_text)


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
