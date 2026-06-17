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

from qsl73.callsign import is_own_call
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
# OCR-Textextraktion (intern) — token-basierte Strategie (ADR-0025)
# ---------------------------------------------------------------------------

# Rufzeichen-Muster: Prefix (mind. 1 Buchstabe), Zahl, Suffix (mind. 1 Buchstabe).
# Strengere Form des ursprünglichen ^[A-Z0-9]{1,3}[0-9][A-Z0-9]{1,4}$ — erzwingt
# Buchstaben in Prefix und Suffix, damit Bandnamen ("20m", "40m") und RST-Werte
# ("599") nicht fälschlich als Rufzeichen erkannt werden.
_RE_CALLSIGN = re.compile(
    r'^[A-Z0-9]{0,2}[A-Z][0-9][A-Z][A-Z0-9]{0,3}(?:/[A-Z0-9]+)?$',
    re.IGNORECASE,
)

# HH:MM oder HH:MM:SS (sekunden optional; Gruppe 1 liefert HH:MM)
_RE_TIME_TOKEN = re.compile(r'^(\d{1,2}:\d{2})(?::\d{2})?$')

# Umgebende Satzzeichen, die von Tokens abgetrennt werden (Slash NICHT hier —
# er ist Bestandteil von Portable-Suffix-Rufzeichen wie "DH3KR/P").
_STRIP_CHARS = '.,;:!?()[]{}"\'-_#@'


def _tokenize(text: str) -> list[str]:
    """Zerlegt OCR-Text in Tokens. Trenner: Whitespace und Pipe-Zeichen.

    Umgebende Satzzeichen werden entfernt; leere Tokens werden verworfen.
    """
    result = []
    for raw in re.split(r'[\s|]+', text):
        t = raw.strip(_STRIP_CHARS).strip()
        if t:
            result.append(t)
    return result


def _extract_token_based(
    ocr_text: str,
    own_callsign: Optional[str] = None,
    station_callsigns: Optional[set[str]] = None,
    portable_suffixes: Optional[list[str]] = None,
) -> CardFields:
    """Token-basierte Feldextraktion für Tabellen- und Fließtext-Layouts (ADR-0025).

    Jedes Token wird durch die vorhandenen Normalizer geschickt:
      - normalize_band    → Band-Kandidat (inkl. Frequenz→Band-Umrechnung)
      - normalize_mode    → Mode-Kandidat
      - normalize_date    → Datum-Kandidat
      - HH:MM-Muster      → Zeit-Kandidat
    Tokens, die keines der obigen Felder bedienen, werden auf das Rufzeichen-
    Muster geprüft; via is_own_call wird zwischen Empfänger (call_to) und Absender
    (call_from) unterschieden.

    Mehrdeutigkeitsregel (ADR-0007): mehrere VERSCHIEDENE gültige Werte für Band oder
    Mode → Feld = None (kein Raten; falsch-Positiv-Schutz).

    Args:
        ocr_text: OCR-Text der Karte.
        own_callsign: Eigenes Rufzeichen (aus Config) — Anker für call_to.
        station_callsigns: Alle stationcallsign-Werte aus der DB.
        portable_suffixes: Bekannte Portable-Suffixe (z. B. ["P", "M"]).

    Returns:
        CardFields mit erkannten Feldern; nicht extrahierbare Felder = None.
    """
    tokens = _tokenize(ocr_text)

    band_candidates: list[str] = []
    mode_candidates: list[str] = []
    date_candidates: list[str] = []
    time_candidates: list[str] = []
    call_to: Optional[str] = None
    foreign_calls: list[str] = []

    for t in tokens:
        b = normalize_band(t)
        m = normalize_mode(t, fuzzy=False)  # kein Fuzzy beim Breitband-Token-Scan
        d = normalize_date(t)
        tm = _RE_TIME_TOKEN.match(t)

        if b is not None:
            band_candidates.append(b)
        if m is not None:
            mode_candidates.append(m)
        if d is not None:
            date_candidates.append(d)
        if tm:
            time_candidates.append(tm.group(1))

        # Rufzeichen-Check nur für Tokens, die als kein Datenfeld erkannt wurden.
        # Das schließt "20m" / "FT8" / Datums-Tokens von der Call-Erkennung aus.
        if b is None and m is None and d is None and not tm:
            t_upper = t.upper()
            if _RE_CALLSIGN.match(t_upper):
                if own_callsign and is_own_call(
                    t_upper,
                    own_callsign,
                    station_callsigns or set(),
                    portable_suffixes or [],
                ):
                    call_to = t_upper
                else:
                    foreign_calls.append(t_upper)

    # Mehrdeutigkeitsregel: mehrere VERSCHIEDENE Werte → None.
    band = band_candidates[0] if len(set(band_candidates)) == 1 else None
    mode = mode_candidates[0] if len(set(mode_candidates)) == 1 else None
    date = date_candidates[0] if len(set(date_candidates)) == 1 else None
    time_utc = time_candidates[0] if time_candidates else None

    # call_from: genau ein eindeutiges Fremd-Rufzeichen → Absender.
    seen: set[str] = set()
    unique_foreign = [c for c in foreign_calls if not (c in seen or seen.add(c))]  # type: ignore[func-returns-value]
    call_from = unique_foreign[0] if len(unique_foreign) == 1 else None

    return CardFields(
        call_from=call_from,
        call_to=call_to,
        date=date,
        band=band,
        mode=mode,
        time_utc=time_utc,
    )


def _parse_ocr_text(
    ocr_text: str,
    own_callsign: Optional[str] = None,
    station_callsigns: Optional[set[str]] = None,
    portable_suffixes: Optional[list[str]] = None,
) -> tuple[CardFields, str]:
    """Extrahiert CardFields aus OCR-Text. Kein Absturz (ADR-0012).

    Strategie (ADR-0025):
    1. Strukturierter Key:Value-Parse (parse_qr_text — DARC-Format u. ä.)
    2. Token-basierte Extraktion über den gesamten Text (Tabellen- und Fließtext-Layout)
    3. Alle None → CardFields mit None-Feldern (lieber 'unsicher' als raten)

    Returns:
        (CardFields, source) — source ist "ocr" wenn Text vorhanden, "none" wenn leer.
    """
    if not ocr_text or not ocr_text.strip():
        return CardFields(None, None, None, None, None), "none"

    # Schicht 1: strukturierter Parse (Key:Value-Format)
    structured = parse_qr_text(ocr_text)
    if structured is not None:
        return structured, "ocr"

    # Schicht 2: token-basierte Extraktion
    return _extract_token_based(ocr_text, own_callsign, station_callsigns, portable_suffixes), "ocr"


# ---------------------------------------------------------------------------
# Karten-Auswertung (intern)
# ---------------------------------------------------------------------------


def evaluate_card(
    doc: dict,
    paperless_client: PaperlessClient,
    own_callsign: Optional[str] = None,
    station_callsigns: Optional[set[str]] = None,
    portable_suffixes: Optional[list[str]] = None,
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
    return _parse_ocr_text(ocr_text, own_callsign, station_callsigns, portable_suffixes)


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


# ---------------------------------------------------------------------------
# Öffentliche Orchestrierung — rein lesend
# ---------------------------------------------------------------------------


def run_pass(
    paperless_client: PaperlessClient,
    db_path: str | Path,
    config: Config,
    on_progress: Optional[Callable[[int, int, str], None]] = None,
) -> RunResult:
    """Rein lesender Lauf: Sammeln → Auswerten → Matchen → Vorschau.

    Kein Schreiben in dieser Funktion. Liefert RunResult mit Einteilung
    sicher/unsicher/kein Match sowie Fingerabdruck + expected_states für write_selected.
    """

    def _progress(done: int, total: int, msg: str) -> None:
        if on_progress:
            on_progress(done, total, msg)

    # 1. Paperless-Dokumente mit qsl-card-Tag laden (paginiert)
    tag_name = config.tags.input
    docs = paperless_client.get_documents_by_tag(tag_name)
    total = len(docs)
    _progress(0, total, f"{total} Dokumente mit Tag '{tag_name}' geladen")

    # 2. DB-Kandidaten laden (rein lesend); Fingerabdruck und expected_states merken
    data = load_qso_candidates(db_path)
    _progress(0, total, f"{len(data.candidates)} offene QSO-Kandidaten geladen")

    certain: list[CardResult] = []
    uncertain: list[CardResult] = []
    no_match: list[CardResult] = []

    # 3. Pro Dokument: auswerten und matchen
    for idx, doc in enumerate(docs):
        doc_id = doc["id"]

        card_fields, source = evaluate_card(
            doc,
            paperless_client,
            own_callsign=config.log4om.own_callsign,
            station_callsigns=data.station_callsigns,
            portable_suffixes=config.matching.portable_suffixes,
        )

        outcome = match_card(
            card=card_fields,
            candidates=data.candidates,
            fuzzy_enabled=config.matching.fuzzy_enabled,
            portable_suffixes=config.matching.portable_suffixes,
            own_callsign=config.log4om.own_callsign,
            station_callsigns=data.station_callsigns,
        )

        # ADR-0015: vorhandene Bestätigungen des gematchten QSOs für Anzeige
        existing: list[str] = []
        if outcome.matched_qso is not None:
            existing = data.existing_confirmations.get(outcome.matched_qso.qsoid, [])

        card_result = CardResult(
            doc_id=doc_id,
            card_fields=card_fields,
            source=source,
            outcome=outcome,
            existing_confirmations=existing,
        )

        if outcome.result == MatchResult.CERTAIN:
            certain.append(card_result)
        elif outcome.result == MatchResult.UNCERTAIN:
            uncertain.append(card_result)
        else:
            no_match.append(card_result)

        _progress(idx + 1, total, f"Karte {idx + 1}/{total} ausgewertet")

    return RunResult(
        certain=certain,
        uncertain=uncertain,
        no_match=no_match,
        fingerprint=data.fingerprint,
        expected_states=data.expected_states,
    )


# ---------------------------------------------------------------------------
# Öffentliche Schreibfunktion
# ---------------------------------------------------------------------------


def write_selected(
    selections: list[tuple[str, str]],
    db_path: str | Path,
    backup_dir: Path,
    snapshot_fingerprint: dict,
    expected_states: dict[str, str],
    backup_count: int = 5,
    paperless_client: Optional[PaperlessClient] = None,
    confirmed_doc_ids: Optional[list[int]] = None,
    uncertain_doc_ids: Optional[list[int]] = None,
    tags_config: Optional[TagsConfig] = None,
) -> WriteResult:
    """Schreibt die bestätigte Auswahl in Log4OM-DB und setzt Paperless-Tags.

    Delegiert an log4om_db.write_confirmations (Schema-Check, WAL, Backup,
    Transaktion, Nebenläufigkeit). Keine neue Schreiblogik in diesem Modul.

    Reihenfolge (ADR-0003): (1) DB-Transaktion → (2) Paperless-Tags.
    Tag-Fehler sind nicht fatal: geloggt, beim nächsten Lauf nachziehbar.

    Args:
        selections: Liste von (qsoid, route)-Paaren.
        db_path: Pfad zur Log4OM-SQLite-Datei.
        backup_dir: Zielverzeichnis für Vor-Backups.
        snapshot_fingerprint: DB-Fingerabdruck aus run_pass (get_db_fingerprint).
        expected_states: qsoid → R-Wert aus run_pass (für Optimistic Locking).
        backup_count: Maximale Anzahl aufbewahrter Backups.
        paperless_client: Optional — wenn None, werden keine Tags gesetzt.
        confirmed_doc_ids: Dok-IDs, die den bestätigten Tag erhalten.
        uncertain_doc_ids: Dok-IDs, die den unsicheren Tag erhalten.
        tags_config: Tag-Namen aus Config; erforderlich wenn paperless_client gesetzt.

    Returns:
        WriteResult mit Anzahl geschriebener und übersprungener QSOs.
    """
    result = write_confirmations(
        db_path=db_path,
        items=selections,
        backup_dir=backup_dir,
        backup_count=backup_count,
        snapshot_fingerprint=snapshot_fingerprint,
        expected_states=expected_states,
    )

    # Paperless-Tags NUR nach erfolgreicher DB-Transaktion (ADR-0003)
    if paperless_client and tags_config:
        for doc_id in (confirmed_doc_ids or []):
            try:
                paperless_client.add_tag_to_document(doc_id, tags_config.confirmed)
            except Exception as exc:
                _log.warning(
                    "Tag '%s' konnte für Dok. %s nicht gesetzt werden: %s",
                    tags_config.confirmed, doc_id, exc,
                )
        for doc_id in (uncertain_doc_ids or []):
            try:
                paperless_client.add_tag_to_document(doc_id, tags_config.uncertain)
            except Exception as exc:
                _log.warning(
                    "Tag '%s' konnte für Dok. %s nicht gesetzt werden: %s",
                    tags_config.uncertain, doc_id, exc,
                )

    return result
