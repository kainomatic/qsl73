# QSL73 — Copyright (C) 2026 DF1DS (kainomatic) — SPDX-License-Identifier: GPL-3.0-or-later
"""Tk-freie Anzeige-Hilfsfunktionen für das Bestätigungsübersicht-Fenster (Issue #42, Auftrag 2).

Zustand→Symbol/Tooltip-Mapping, Spaltenwahl-Zustand, Klick-Sortierung, Detailzeilen-
Formatierung und Zeitraum-Schnellwahl — alles tk-frei und unit-testbar, um die
tk-Testlast im Fenster (`confirmations_window.py`) klein zu halten (Issue #42
Architektur-Hinweis, Bezug #40/ADR-0062). Das Fenster wendet dieses Mapping nur an.

Symbol-/Farbkonvention: siehe ADR-0067 — farbige Unicode-Symbole statt
`tree.tag_configure`, weil eine Zeile mehrere Dienstspalten mit UNTERSCHIEDLICHEN
Zuständen gleichzeitig zeigt und ttk.Treeview-Tags nur ganze Zeilen einfärben,
keine einzelnen Zellen.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date as _date, timedelta

from qsl73.confirmations import (
    CONFIRMATION_SERVICES,
    UPLOAD_SERVICES,
    ConfirmationMetrics,
    ConfirmationState,
    QsoConfirmationRow,
    ServiceGroup,
    ServiceStatus,
    confirmation_state,
    has_marker,
    service_group,
)
from qsl73.normalize import BAND_ORDER

# ---------------------------------------------------------------------------
# Dienst-Anzeigenamen und Spaltenreihenfolge (Issue #42, Grundentscheidung 5)
# ---------------------------------------------------------------------------

SERVICE_LABELS: dict[str, str] = {
    "QSL": "Papier",
    "LOTW": "LoTW",
    "EQSL": "eQSL",
    "QRZCOM": "QRZ",
    "CLUBLOG": "Clublog",
    "HRDLOG": "HRDLog",
    "HAMQTH": "HamQTH",
}

SERVICE_COLUMN_ORDER: tuple[str, ...] = CONFIRMATION_SERVICES + UPLOAD_SERVICES


# ---------------------------------------------------------------------------
# Zustand → Symbol (farbige Unicode-Glyphen statt Zeilen-Tags, siehe Moduldoc/ADR-0067)
# ---------------------------------------------------------------------------

_STATE_SYMBOLS: dict[ConfirmationState, str] = {
    ConfirmationState.RECEIVED: "✅",  # ✅ bekommen (farbig grün)
    ConfirmationState.SENT: "⬆️",  # ⬆️ gesendet, noch nicht bekommen (farbig blau)
    ConfirmationState.NONE: "–",  # – keins von beiden
    ConfirmationState.INVALID: "⊘",  # ⊘ gedämpft über die Form, klar von „–" unterscheidbar
}
MARKER_SUFFIX = "🕐"  # kleine orange Uhr als Zusatzsymbol bei Requested/Queued (Nachbesserung #42)


def cell_symbol(state: ConfirmationState, marker: bool) -> str:
    """Hauptsymbol (nur harte Fakten) + optionaler Merker-Zusatzpunkt."""
    symbol = _STATE_SYMBOLS[state]
    return symbol + MARKER_SUFFIX if marker else symbol


def cell_display(status: ServiceStatus | None, group: ServiceGroup) -> str:
    """Kombiniert `confirmation_state` + `has_marker` zur fertigen Zellen-Anzeige."""
    state = confirmation_state(status, group)
    marker = has_marker(status)
    return cell_symbol(state, marker)


# ---------------------------------------------------------------------------
# Tooltip-Text je Zelle — wörtliche Werte + neutrale Erklärung (Grundentscheidung 3)
# ---------------------------------------------------------------------------

_VALUE_EXPLANATIONS: dict[str, str] = {
    "Yes": "bestätigt/versendet",
    "No": "nicht gesetzt",
    "Requested": "in Log4OM als angefordert/erwartet markiert",
    "Queued": "zum Versand/Upload vorgemerkt",
    "Invalid": "als ungültig markiert",
}


def _explain(value: str | None) -> str:
    if not value:
        return "kein Wert"
    return _VALUE_EXPLANATIONS.get(value, "Wert laut Log4OM")


def cell_tooltip_text(ct: str, status: ServiceStatus | None, group: ServiceGroup) -> str:
    """Wörtliche S/R-Werte + neutrale Erklärung, keine Deutung der Nutzerabsicht."""
    label = SERVICE_LABELS.get(ct, ct)
    if status is None:
        return f"{label}: kein Eintrag in Log4OM vorhanden."
    lines = [label, f"Gesendet: {status.s or '–'} — {_explain(status.s)}"]
    if group is not ServiceGroup.UPLOAD:
        lines.append(f"Empfangen: {status.r or '–'} — {_explain(status.r)}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Spaltenwahl (Sitzungszustand, Default alle sichtbar)
# ---------------------------------------------------------------------------


@dataclass
class ColumnVisibility:
    visible: dict[str, bool] = field(
        default_factory=lambda: {ct: True for ct in SERVICE_COLUMN_ORDER}
    )

    def is_visible(self, ct: str) -> bool:
        return self.visible.get(ct, True)

    def set_visible(self, ct: str, value: bool) -> None:
        self.visible[ct] = value

    def visible_services(self) -> list[str]:
        return [ct for ct in SERVICE_COLUMN_ORDER if self.visible.get(ct, True)]


# ---------------------------------------------------------------------------
# Klick-Sortierung (ADR-0052-Muster)
# ---------------------------------------------------------------------------

_STATE_ORDER: dict[ConfirmationState, int] = {
    ConfirmationState.NONE: 0,
    ConfirmationState.INVALID: 1,
    ConfirmationState.SENT: 2,
    ConfirmationState.RECEIVED: 3,
}


def _text_sort_key(value: str | None) -> tuple:
    v = (value or "").strip()
    return (0 if v else 1, v.upper())


def _date_sort_key(date_str: str | None) -> tuple:
    s = (date_str or "")[:10].strip()
    if not s:
        return (1, "")
    try:
        _date.fromisoformat(s)
        return (0, s)
    except ValueError:
        return (1, "")


def _band_sort_key(band_str: str | None) -> tuple:
    s = (band_str or "").strip()
    if not s:
        return (1, 0)
    try:
        return (0, BAND_ORDER.index(s))
    except ValueError:
        return (1, 0)


def _service_sort_key(row: QsoConfirmationRow, ct: str) -> tuple:
    status = row.services.get(ct)
    group = service_group(ct)
    state = confirmation_state(status, group)
    marker = has_marker(status)
    return (_STATE_ORDER[state], 1 if marker else 0)


def row_sort_key(row: QsoConfirmationRow, column: str) -> tuple:
    """Sortierschlüssel für eine Tabellenspalte (Basis- oder Dienstspalte)."""
    if column == "qsodate":
        return _date_sort_key(row.qsodate)
    if column == "callsign":
        return _text_sort_key(row.callsign)
    if column == "band":
        return _band_sort_key(row.band)
    if column == "mode":
        return _text_sort_key(row.mode)
    if column == "country":
        return _text_sort_key(row.country)
    if column in SERVICE_COLUMN_ORDER:
        return _service_sort_key(row, column)
    return (0, "")


def sort_rows_by_column(
    rows: list[QsoConfirmationRow], column: str, ascending: bool = True
) -> list[QsoConfirmationRow]:
    """Sortiert QsoConfirmationRow-Liste nach Spalte (stabil, tk-frei, ADR-0052-Muster)."""
    return sorted(rows, key=lambda r: row_sort_key(r, column), reverse=not ascending)


# ---------------------------------------------------------------------------
# Detailzeile (wörtliche Werte, fehlend = "–")
# ---------------------------------------------------------------------------


def format_detail_line(row: QsoConfirmationRow) -> str:
    """Ein-Zeilen-Detailtext für das gewählte QSO: je Dienst wörtliche S/R/SD/RD/SV/RV.

    Fehlende Felder als "–" (Issue #42 Fensteraufbau). qslvia/Locator ergänzt.
    """
    parts = []
    for ct in SERVICE_COLUMN_ORDER:
        status = row.services.get(ct)
        label = SERVICE_LABELS.get(ct, ct)
        s = status.s if status else None
        r = status.r if status else None
        sd = status.sd if status else None
        rd = status.rd if status else None
        sv = status.sv if status else None
        rv = status.rv if status else None
        parts.append(
            f"{label}: S={s or '–'} R={r or '–'} SD={sd or '–'} RD={rd or '–'} "
            f"SV={sv or '–'} RV={rv or '–'}"
        )
    detail = "  |  ".join(parts)
    detail += f"  |  QSL via: {row.qslvia or '–'}  |  Locator: {row.gridsquare or '–'}"
    return detail


# ---------------------------------------------------------------------------
# Zeitraum-Schnellwahl (Issue #42 Filter „Zeitraum mit Schnellwahl")
# ---------------------------------------------------------------------------

QUICK_RANGE_CHOICES: tuple[str, ...] = (
    "Alle",
    "Letzte 30 Tage",
    "Letzte 90 Tage",
    "Dieses Jahr",
    "Letztes Jahr",
)


def quick_range_bounds(choice: str, today: _date) -> tuple[str | None, str | None]:
    """Berechnet (start, end) als 'YYYY-MM-DD' für eine Schnellwahl-Option.

    "Alle" oder unbekannte Auswahl → (None, None), also unbegrenzt.
    """
    if choice == "Letzte 30 Tage":
        return (today - timedelta(days=30)).isoformat(), today.isoformat()
    if choice == "Letzte 90 Tage":
        return (today - timedelta(days=90)).isoformat(), today.isoformat()
    if choice == "Dieses Jahr":
        return f"{today.year}-01-01", today.isoformat()
    if choice == "Letztes Jahr":
        y = today.year - 1
        return f"{y}-01-01", f"{y}-12-31"
    return None, None


# ---------------------------------------------------------------------------
# Kennzahlen-Kacheln (Nachbesserung #42) — Aufteilung als tk-freie Hilfsstruktur.
#
# Labels sind statisch (unabhängig von den Daten) — das Fenster baut die Kachel-
# Widgets einmal beim Aufbau aus METRIC_TILE_LABELS und aktualisiert bei jeder
# Filteränderung nur die Werte aus metric_tile_values(). Kompakt gruppiert statt
# einer Kachel je der 7 Dienste (Auftrag Punkt 2): LoTW+QRZ und Papier+eQSL je ein
# Zahlenpaar (Empfangen), die drei Upload-Dienste eine gemeinsame Kachel (Gesendet).
# ---------------------------------------------------------------------------

METRIC_TILE_LABELS: tuple[str, ...] = (
    "QSOs",
    "Bestätigt",
    "LoTW / QRZ",
    "Papier / eQSL",
    "Hochgeladen (Clublog/HRDLog/HamQTH)",
    "DXCC bestätigt",
)


def metric_tile_values(metrics: ConfirmationMetrics) -> tuple[str, ...]:
    """Werte in derselben Reihenfolge wie `METRIC_TILE_LABELS`, bezogen auf `metrics`."""
    lotw = metrics.services["LOTW"]
    qrz = metrics.services["QRZCOM"]
    qsl = metrics.services["QSL"]
    eqsl = metrics.services["EQSL"]
    clublog = metrics.services["CLUBLOG"]
    hrdlog = metrics.services["HRDLOG"]
    hamqth = metrics.services["HAMQTH"]
    return (
        str(metrics.total_qsos),
        f"{metrics.confirmed_anywhere} ({metrics.confirmed_anywhere_pct:.1f} %)",
        f"{lotw.received}/{qrz.received}",
        f"{qsl.received}/{eqsl.received}",
        f"{clublog.sent}/{hrdlog.sent}/{hamqth.sent}",
        f"{metrics.dxcc_confirmed} / {metrics.dxcc_worked}",
    )
