# QSL73 — Copyright (C) 2026 DF1DS (kainomatic) — SPDX-License-Identifier: GPL-3.0-or-later
"""Bestätigungsübersicht — read-only-Logikmodul (Issue #42, Auftrag 1).

Tk-frei: Laden (read-only, mode=ro), Normalisieren des `qsoconfirmations`-JSON in eine
flache Struktur, Kennzahlen und Filter — alles in-memory, voll unit-testbar nach dem
Muster von `gui/filter_util.py`. Das Fenster (Toplevel, Hintergrund-Thread) ist Auftrag 2.

Leitprinzip (Issue #42 Grundentscheidung 3): Fakten prominent, Merker dezent und
wörtlich, keine Interpretation der Nutzerabsicht.
- HARTE FAKTEN sind nur `S="Yes"` und `R="Yes"`. Nur sie bestimmen `confirmation_state`
  und die Kennzahlen (`compute_metrics`).
- Absichtsmerker (`"Requested"`, `"Queued"`) werden nicht gedeutet und bei allen
  Diensten gleich behandelt (`has_marker`) — unabhängig vom Hauptzustand.
- `Invalid` (Grundentscheidung 4) ist ein eigener Zustand (`ConfirmationState.INVALID`),
  kein `NONE` — verschwindet dadurch nie in "offen"/"unbestätigt"-Kennzahlen.
- Zwei Dienstgruppen (Grundentscheidung 5): Bestätigungsdienste werten S und R aus,
  Upload-Dienste nur S (`service_group`, `confirmation_state`).
- Unbekannte CT-Typen und unbekannte S/R-Werte werden wörtlich durchgereicht, nicht
  verworfen (Grundentscheidung 6). `EXT` wird nie übernommen (Grundentscheidung 7).

Empirische Basis: docs/discovery.md §2, §3, §7, §7.1.
"""
from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from qsl73.log4om_db import SchemaError, validate_schema

# ---------------------------------------------------------------------------
# Dienstgruppen-Mapping (Grundentscheidung 5)
# ---------------------------------------------------------------------------

CONFIRMATION_SERVICES: tuple[str, ...] = ("QSL", "LOTW", "EQSL", "QRZCOM")
UPLOAD_SERVICES: tuple[str, ...] = ("CLUBLOG", "HRDLOG", "HAMQTH")
KNOWN_SERVICES: tuple[str, ...] = CONFIRMATION_SERVICES + UPLOAD_SERVICES

# Merker-Werte (Absichtsmerker, keine harten Fakten) — bei allen Diensten gleich (Issue #42 §3)
_MARKER_VALUES: tuple[str, ...] = ("Requested", "Queued")


class ServiceGroup(Enum):
    CONFIRMATION = "confirmation"
    UPLOAD = "upload"
    UNKNOWN = "unknown"


def service_group(ct: str) -> ServiceGroup:
    """Ordnet einen CT-Wert seiner Dienstgruppe zu (Grundentscheidung 5).

    Unbekannte CT-Typen werden NICHT verworfen, sondern als UNKNOWN geführt
    (Grundentscheidung 6) — `confirmation_state` behandelt sie wie Bestätigungsdienste
    (S und R auswerten), da ihre Struktur nicht vorab bekannt ist.
    """
    if ct in CONFIRMATION_SERVICES:
        return ServiceGroup.CONFIRMATION
    if ct in UPLOAD_SERVICES:
        return ServiceGroup.UPLOAD
    return ServiceGroup.UNKNOWN


# ---------------------------------------------------------------------------
# Datenklassen
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ServiceStatus:
    """Ein Eintrag aus `qsoconfirmations`, wörtlich übernommen (ohne `EXT`, Grundentscheidung 7).

    Fehlende Felder (z. B. SV/RV bei Requested/Queued, §7.1 Zusatzbefund 1) sind normal
    und bleiben None — kein Rückschluss, kein Ersatzwert.
    """

    ct: str
    s: str | None = None
    r: str | None = None
    sv: str | None = None
    rv: str | None = None
    sd: str | None = None
    rd: str | None = None


@dataclass
class QsoConfirmationRow:
    """Ein QSO der Log-Tabelle, flach normalisiert für Anzeige/Filter/Kennzahlen.

    `services` ist ein CT→ServiceStatus-Mapping; fehlt ein Dienst im JSON-Array ganz
    (z. B. bei Hand-Testdaten mit nur einem Eintrag), ist er schlicht nicht im Dict —
    Aufrufer behandeln das wie "unbekannt/leer", nicht als Fehler.
    """

    qsoid: str
    callsign: str
    qsodate: str | None
    band: str | None
    mode: str | None
    dxcc: int | None
    country: str | None
    cont: str | None
    stationcallsign: str | None
    gridsquare: str | None
    qslvia: str | None
    services: dict[str, ServiceStatus] = field(default_factory=dict)
    # None wenn qsoconfirmations sauber geparst wurde; sonst Klartext-Fehlerbeschreibung
    # (ADR-0012-Geist: QSO bleibt trotzdem in der Liste, services bleibt leer).
    confirmations_error: str | None = None


@dataclass
class ServiceMetrics:
    sent: int = 0
    received: int = 0  # bei Upload-Diensten bleibt dies immer 0 (kein R-Konzept)


@dataclass
class ConfirmationMetrics:
    """Kennzahlen NUR aus harten Fakten, bezogen auf die übergebene (gefilterte) Menge."""

    total_qsos: int
    confirmed_anywhere: int
    confirmed_anywhere_pct: float
    services: dict[str, ServiceMetrics]
    dxcc_worked: int
    dxcc_confirmed: int


# ---------------------------------------------------------------------------
# Parsen von qsoconfirmations
# ---------------------------------------------------------------------------


def _parse_service_entry(entry: dict) -> ServiceStatus | None:
    ct = entry.get("CT")
    if not isinstance(ct, str) or not ct:
        return None
    return ServiceStatus(
        ct=ct,
        s=entry.get("S"),
        r=entry.get("R"),
        sv=entry.get("SV"),
        rv=entry.get("RV"),
        sd=entry.get("SD"),
        rd=entry.get("RD"),
    )


def parse_qsoconfirmations(raw: str | None) -> tuple[dict[str, ServiceStatus], str | None]:
    """Parst `qsoconfirmations`-JSON in ein CT→ServiceStatus-Mapping.

    Robuste Rückgabe (ADR-0012-Geist): leeres/fehlendes/defektes JSON oder unerwartete
    Struktur führt NIE zum Absturz — leeres Mapping + menschenlesbare Fehlerbeschreibung.
    Nicht-Dict-Einträge innerhalb eines sonst gültigen Arrays werden übersprungen statt
    das gesamte Parsen scheitern zu lassen. `EXT` wird nie übernommen (Grundentscheidung 7);
    unbekannte CT-Typen bleiben erhalten (Grundentscheidung 6); bei doppeltem CT gewinnt
    der letzte Eintrag.

    Returns:
        (services, error) — error ist None bei Erfolg, sonst Klartext-Beschreibung.
    """
    if not raw:
        return {}, "qsoconfirmations ist leer"
    try:
        parsed = json.loads(raw)
    except (json.JSONDecodeError, TypeError) as exc:
        return {}, f"ungültiges JSON: {exc}"

    if not isinstance(parsed, list):
        return {}, f"kein JSON-Array, sondern {type(parsed).__name__}"

    services: dict[str, ServiceStatus] = {}
    for entry in parsed:
        if not isinstance(entry, dict):
            continue
        status = _parse_service_entry(entry)
        if status is not None:
            services[status.ct] = status
    return services, None


# ---------------------------------------------------------------------------
# Fakten-vs-Merker-Trennung (Grundentscheidungen 3, 4)
# ---------------------------------------------------------------------------


class ConfirmationState(Enum):
    NONE = "none"
    SENT = "sent"
    RECEIVED = "received"
    INVALID = "invalid"


def confirmation_state(status: ServiceStatus | None, group: ServiceGroup) -> ConfirmationState:
    """Leitet das Hauptsymbol-Niveau eines Dienstes NUR aus harten Fakten ab.

    Reihenfolge (Grundentscheidung 3): R=Yes (bekommen) > S=Yes (gesendet/hochgeladen,
    noch nicht bekommen) > keins. Upload-Dienste (Grundentscheidung 5) werten nur S aus.
    `Invalid` ist ein eigener Zustand (Grundentscheidung 4) — wird nur geliefert, wenn
    kein Yes vorliegt, und zählt dadurch nie als offen (NONE) oder bestätigt (SENT/RECEIVED).
    """
    if status is None:
        return ConfirmationState.NONE

    if group is ServiceGroup.UPLOAD:
        if status.s == "Yes":
            return ConfirmationState.SENT
        if status.s == "Invalid":
            return ConfirmationState.INVALID
        return ConfirmationState.NONE

    # CONFIRMATION oder UNKNOWN: S und R auswerten
    if status.r == "Yes":
        return ConfirmationState.RECEIVED
    if status.s == "Yes":
        return ConfirmationState.SENT
    if status.r == "Invalid":
        return ConfirmationState.INVALID
    return ConfirmationState.NONE


def has_marker(status: ServiceStatus | None) -> bool:
    """True wenn auf Sende- oder Empfangsseite ein Absichtsmerker (Requested/Queued) steht.

    Unabhängig vom Hauptzustand; keine Interpretation der Bedeutung (Grundentscheidung 3):
    ob "Requested" bewusste Anforderung, Standardwert oder Druck-Vormerkung ist, entscheidet
    dieses Modul nicht.
    """
    if status is None:
        return False
    return status.s in _MARKER_VALUES or status.r in _MARKER_VALUES


# ---------------------------------------------------------------------------
# Read-only-Laden (Grundentscheidung 2)
# ---------------------------------------------------------------------------

# Spalten fürs MVP; um Stufe-2-Filter (z. B. cqzone, ituzone, contestid, contactreferences)
# einfach ergänzbar.
LOG_COLUMNS: tuple[str, ...] = (
    "qsoid",
    "callsign",
    "qsodate",
    "band",
    "mode",
    "dxcc",
    "country",
    "cont",
    "qsoconfirmations",
    "stationcallsign",
    "gridsquare",
    "qslvia",
)


def open_readonly_connection(db_path: str | Path) -> sqlite3.Connection:
    """Öffnet die Log4OM-DB strikt read-only (URI `mode=ro`) — kein Schreibpfad, kein Backup.

    Gefahrlos neben laufendem Log4OM nutzbar (Issue #42 Grundentscheidung 2).
    """
    db_path = Path(db_path)
    uri = f"file:{db_path.as_posix()}?mode=ro"
    return sqlite3.connect(uri, uri=True)


def load_confirmation_rows(conn: sqlite3.Connection) -> list[QsoConfirmationRow]:
    """Lädt ALLE QSOs der Log-Tabelle (nicht nur offene — anders als `run.py`) und normalisiert sie.

    Reiner Lesezugriff auf eine bereits geöffnete Verbindung; Schema-Prüfung ist Sache
    des Aufrufers (siehe `load_confirmation_data`).
    """
    columns_sql = ", ".join(LOG_COLUMNS)
    cursor = conn.execute(f"SELECT {columns_sql} FROM Log")
    rows: list[QsoConfirmationRow] = []
    for record in cursor.fetchall():
        values: dict[str, Any] = dict(zip(LOG_COLUMNS, record))
        raw_confirmations = values.pop("qsoconfirmations")
        services, error = parse_qsoconfirmations(raw_confirmations)
        rows.append(QsoConfirmationRow(services=services, confirmations_error=error, **values))
    return rows


def load_confirmation_data(db_path: str | Path) -> list[QsoConfirmationRow]:
    """Öffnet die DB read-only, prüft das Schema (wiederverwendet aus `log4om_db`) und lädt.

    Raises:
        SchemaError: wenn das Schema abweicht — sauberer Fehler statt Absturz.
    """
    conn = open_readonly_connection(db_path)
    try:
        deviation = validate_schema(conn)
        if deviation:
            raise SchemaError(deviation)
        return load_confirmation_rows(conn)
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Kennzahlen (nur harte Fakten, Grundentscheidung 3)
# ---------------------------------------------------------------------------


def compute_metrics(rows: list[QsoConfirmationRow]) -> ConfirmationMetrics:
    """Berechnet Kennzahlen NUR aus harten Fakten (S=Yes/R=Yes), bezogen auf `rows`.

    `rows` ist die bereits gefilterte Menge — die Kacheln beziehen sich immer auf das,
    was der Aufrufer übergibt, nie auf die Gesamt-DB (Issue #42, Fensteraufbau).
    """
    services = {ct: ServiceMetrics() for ct in KNOWN_SERVICES}
    confirmed_anywhere = 0
    dxcc_worked: set[int] = set()
    dxcc_confirmed: set[int] = set()

    for row in rows:
        if row.dxcc:
            dxcc_worked.add(row.dxcc)

        row_confirmed = False
        for ct in CONFIRMATION_SERVICES:
            status = row.services.get(ct)
            if status is None:
                continue
            if status.s == "Yes":
                services[ct].sent += 1
            if status.r == "Yes":
                services[ct].received += 1
                row_confirmed = True

        for ct in UPLOAD_SERVICES:
            status = row.services.get(ct)
            if status is not None and status.s == "Yes":
                services[ct].sent += 1

        if row_confirmed:
            confirmed_anywhere += 1
            if row.dxcc:
                dxcc_confirmed.add(row.dxcc)

    total = len(rows)
    pct = (confirmed_anywhere / total * 100) if total else 0.0
    return ConfirmationMetrics(
        total_qsos=total,
        confirmed_anywhere=confirmed_anywhere,
        confirmed_anywhere_pct=pct,
        services=services,
        dxcc_worked=len(dxcc_worked),
        dxcc_confirmed=len(dxcc_confirmed),
    )


# ---------------------------------------------------------------------------
# Basisfilter (reine Prädikate, UND-verknüpft über apply_filters)
# ---------------------------------------------------------------------------


def matches_text_query(row: QsoConfirmationRow, query: str | None) -> bool:
    """Freitext über Call/Land/Locator (Präfix-Suche ist als Teilstring auf Call abgedeckt)."""
    q = (query or "").strip().lower()
    if not q:
        return True
    haystacks = (row.callsign, row.country, row.gridsquare)
    return any(q in (h or "").lower() for h in haystacks)


def matches_date_range(row: QsoConfirmationRow, start: str | None, end: str | None) -> bool:
    """start/end als 'YYYY-MM-DD' (inklusive); None = unbegrenzt.

    `qsodate` hat das Format 'YYYY-MM-DD HH:MM:SSZ' (discovery.md §4).
    """
    date_part = (row.qsodate or "")[:10]
    if not date_part:
        return False
    if start and date_part < start:
        return False
    if end and date_part > end:
        return False
    return True


def matches_band(row: QsoConfirmationRow, band: str | None) -> bool:
    if not band:
        return True
    return (row.band or "").casefold() == band.casefold()


def matches_mode(row: QsoConfirmationRow, mode: str | None) -> bool:
    if not mode:
        return True
    return (row.mode or "").casefold() == mode.casefold()


def matches_continent(row: QsoConfirmationRow, cont: str | None) -> bool:
    if not cont:
        return True
    return (row.cont or "").casefold() == cont.casefold()


def matches_country(row: QsoConfirmationRow, country: str | None) -> bool:
    if not country:
        return True
    return (row.country or "").casefold() == country.casefold()


# ---------------------------------------------------------------------------
# Statusfilter (rohe Log4OM-Werte, wörtlich)
# ---------------------------------------------------------------------------


def matches_sent_status(row: QsoConfirmationRow, ct: str, value: str | None) -> bool:
    """value=None → kein Filter (Treffer). Fehlt der Dienst im QSO, matcht nur value=None."""
    if not value:
        return True
    status = row.services.get(ct)
    return status is not None and status.s == value


def matches_received_status(row: QsoConfirmationRow, ct: str, value: str | None) -> bool:
    if not value:
        return True
    status = row.services.get(ct)
    return status is not None and status.r == value


def available_status_values(rows: list[QsoConfirmationRow], ct: str, side: str) -> list[str]:
    """Sortierte Liste der tatsächlich vorkommenden Rohwerte für Dropdown-Befüllung.

    side: 's' (gesendet) oder 'r' (empfangen). Fehlende/None-Werte werden ausgelassen.
    """
    values: set[str] = set()
    for row in rows:
        status = row.services.get(ct)
        if status is None:
            continue
        raw = status.s if side == "s" else status.r
        if raw:
            values.add(raw)
    return sorted(values)


# ---------------------------------------------------------------------------
# Sammelfilter (nur harte Fakten, Grundentscheidung 5)
# ---------------------------------------------------------------------------


class CollectiveFilter(Enum):
    ANY = "any"
    CONFIRMED_ANYWHERE = "confirmed_anywhere"
    CONFIRMED_NOWHERE = "confirmed_nowhere"
    ELECTRONIC_ONLY = "electronic_only"
    PAPER_ONLY = "paper_only"
    # Nachbesserung #42 — Grundlage für Presets 5–7, ausschließlich harte Fakten
    # (S=Yes/R=Yes) je Dienst, keine Deutung der Nutzerabsicht (Issue #42 Grundentscheidung 3).
    RECEIVED_NOT_SENT_ANY = "received_not_sent_any"
    PAPER_RECEIVED_NOT_SENT = "paper_received_not_sent"
    NOT_UPLOADED_ANYWHERE = "not_uploaded_anywhere"


_ELECTRONIC_SERVICES: tuple[str, ...] = ("EQSL", "LOTW", "QRZCOM")


def _received_yes(row: QsoConfirmationRow, ct: str) -> bool:
    status = row.services.get(ct)
    return status is not None and status.r == "Yes"


def _received_not_sent(status: ServiceStatus | None) -> bool:
    """True nur bei hartem R=Yes UND S!=Yes AM SELBEN Dienst (kein automatischer Digital-Fall)."""
    return status is not None and status.r == "Yes" and status.s != "Yes"


def matches_collective_filter(row: QsoConfirmationRow, mode: CollectiveFilter) -> bool:
    if mode is CollectiveFilter.ANY:
        return True

    paper = _received_yes(row, "QSL")
    electronic = any(_received_yes(row, ct) for ct in _ELECTRONIC_SERVICES)

    if mode is CollectiveFilter.CONFIRMED_ANYWHERE:
        return paper or electronic
    if mode is CollectiveFilter.CONFIRMED_NOWHERE:
        return not (paper or electronic)
    if mode is CollectiveFilter.ELECTRONIC_ONLY:
        return electronic and not paper
    if mode is CollectiveFilter.PAPER_ONLY:
        return paper and not electronic
    if mode is CollectiveFilter.RECEIVED_NOT_SENT_ANY:
        return any(_received_not_sent(row.services.get(ct)) for ct in CONFIRMATION_SERVICES)
    if mode is CollectiveFilter.PAPER_RECEIVED_NOT_SENT:
        return _received_not_sent(row.services.get("QSL"))
    if mode is CollectiveFilter.NOT_UPLOADED_ANYWHERE:
        return not any(
            (status := row.services.get(ct)) is not None and status.s == "Yes"
            for ct in UPLOAD_SERVICES
        )
    return True


# ---------------------------------------------------------------------------
# Kombinierte Filter (alle UND-verknüpft)
# ---------------------------------------------------------------------------


@dataclass
class ConfirmationFilters:
    text_query: str = ""
    date_start: str | None = None
    date_end: str | None = None
    band: str | None = None
    mode: str | None = None
    continent: str | None = None
    country: str | None = None
    sent_status: dict[str, str] = field(default_factory=dict)
    received_status: dict[str, str] = field(default_factory=dict)
    collective: CollectiveFilter = CollectiveFilter.ANY


def apply_filters(
    rows: list[QsoConfirmationRow], filters: ConfirmationFilters
) -> list[QsoConfirmationRow]:
    """Wendet alle Basis-, Status- und Sammelfilter UND-verknüpft an."""
    result = []
    for row in rows:
        if not matches_text_query(row, filters.text_query):
            continue
        if not matches_date_range(row, filters.date_start, filters.date_end):
            continue
        if not matches_band(row, filters.band):
            continue
        if not matches_mode(row, filters.mode):
            continue
        if not matches_continent(row, filters.continent):
            continue
        if not matches_country(row, filters.country):
            continue
        if not all(matches_sent_status(row, ct, v) for ct, v in filters.sent_status.items()):
            continue
        if not all(
            matches_received_status(row, ct, v) for ct, v in filters.received_status.items()
        ):
            continue
        if not matches_collective_filter(row, filters.collective):
            continue
        result.append(row)
    return result


# ---------------------------------------------------------------------------
# Presets / Schnellansichten (Nachbesserung #42) — nur harte Fakten + Merker,
# neutral benannt (Issue #42 Grundentscheidung 3: keine Deutung der Nutzerabsicht).
# Jedes Preset ist nur ein Startpunkt für die einfachen Filter/Sammelfilter; ändert
# der Nutzer danach einen Einzelfilter, bleibt das unbeschränkt möglich.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Preset:
    label: str
    collective: CollectiveFilter = CollectiveFilter.ANY
    received_status: tuple[tuple[str, str], ...] = ()


PRESETS: tuple[Preset, ...] = (
    Preset("Alle"),
    Preset("Nirgends bestätigt", collective=CollectiveFilter.CONFIRMED_NOWHERE),
    Preset("Nur digital, Papier fehlt", collective=CollectiveFilter.ELECTRONIC_ONLY),
    Preset("Papier angefordert", received_status=(("QSL", "Requested"),)),
    Preset("Bekommen, selbst nicht gesendet", collective=CollectiveFilter.RECEIVED_NOT_SENT_ANY),
    Preset(
        "Papier bekommen, selbst noch nicht gesendet",
        collective=CollectiveFilter.PAPER_RECEIVED_NOT_SENT,
    ),
    Preset("Noch nicht hochgeladen", collective=CollectiveFilter.NOT_UPLOADED_ANYWHERE),
)


def preset_filters(preset: Preset) -> ConfirmationFilters:
    """Baut einen frischen `ConfirmationFilters`-Startpunkt aus einem Preset."""
    return ConfirmationFilters(
        collective=preset.collective,
        received_status=dict(preset.received_status),
    )
