# QSL73 — Copyright (C) 2026 DF1DS (kainomatic) — SPDX-License-Identifier: GPL-3.0-or-later
"""Unit-Tests für gui/confirmations_view.py — tk-freie Anzeige-Hilfsfunktionen (Issue #42, Auftrag 2).

Schwerpunkt lt. Auftrag: möglichst viel Logik hier unit-testen, um die tk-Testlast
im eigentlichen Fenster klein zu halten (Bezug #40/ADR-0062).
"""
from __future__ import annotations

from datetime import date

import pytest

from qsl73.confirmations import (
    ConfirmationState,
    ServiceGroup,
    ServiceStatus,
    QsoConfirmationRow,
    compute_metrics,
)
from qsl73.gui.confirmations_view import (
    ColumnVisibility,
    METRIC_TILE_LABELS,
    MARKER_SUFFIX,
    SERVICE_COLUMN_ORDER,
    SERVICE_LABELS,
    cell_display,
    cell_symbol,
    cell_tooltip_text,
    format_detail_line,
    metric_tile_values,
    quick_range_bounds,
    row_sort_key,
    sort_rows_by_column,
)


def _row(qsoid="Q1", callsign="DK8XX", qsodate="2025-04-02 19:42:00Z", band="20m",
         mode="SSB", dxcc=230, country="Germany", cont="EU", services=None) -> QsoConfirmationRow:
    return QsoConfirmationRow(
        qsoid=qsoid, callsign=callsign, qsodate=qsodate, band=band, mode=mode,
        dxcc=dxcc, country=country, cont=cont, stationcallsign="DF1DS",
        gridsquare="JO31", qslvia="", services=services or {},
    )


def _status(ct="QSL", s=None, r=None, sv=None, rv=None, sd=None, rd=None) -> ServiceStatus:
    return ServiceStatus(ct=ct, s=s, r=r, sv=sv, rv=rv, sd=sd, rd=rd)


# ---------------------------------------------------------------------------
# cell_symbol / cell_display — Hauptsymbol nur aus harten Fakten
# ---------------------------------------------------------------------------


def test_cell_symbol_received_no_marker():
    assert cell_symbol(ConfirmationState.RECEIVED, marker=False) == "✅"


def test_cell_symbol_sent_no_marker():
    assert cell_symbol(ConfirmationState.SENT, marker=False) == "⬆️"


def test_cell_symbol_none_no_marker():
    assert cell_symbol(ConfirmationState.NONE, marker=False) == "–"


def test_cell_symbol_invalid_distinct_from_none():
    invalid = cell_symbol(ConfirmationState.INVALID, marker=False)
    none_sym = cell_symbol(ConfirmationState.NONE, marker=False)
    assert invalid != none_sym
    assert invalid == "⊘"


def test_cell_symbol_marker_adds_clock_suffix():
    """Merker-Zusatzsymbol ist jetzt eine kleine orange Uhr statt eines Punkts (Nachbesserung #42)."""
    base = cell_symbol(ConfirmationState.SENT, marker=False)
    with_marker = cell_symbol(ConfirmationState.SENT, marker=True)
    assert with_marker == base + MARKER_SUFFIX
    assert MARKER_SUFFIX == "🕐"


def test_cell_display_requested_received_shown_as_none_not_received():
    """Requested auf Empfangsseite ist ein Merker, kein hartes R=Yes (Issue #42 §3)."""
    status = _status(ct="QSL", s="No", r="Requested")
    result = cell_display(status, ServiceGroup.CONFIRMATION)
    assert result == cell_symbol(ConfirmationState.NONE, marker=True)
    assert result != cell_symbol(ConfirmationState.RECEIVED, marker=False)


def test_cell_display_queued_sent_shown_as_none_not_sent():
    status = _status(ct="QSL", s="Queued", r="No")
    result = cell_display(status, ServiceGroup.CONFIRMATION)
    assert result == cell_symbol(ConfirmationState.NONE, marker=True)
    assert result != cell_symbol(ConfirmationState.SENT, marker=False)


def test_cell_display_invalid_gets_damped_symbol():
    status = _status(ct="LOTW", s="Invalid", r="Invalid")
    result = cell_display(status, ServiceGroup.CONFIRMATION)
    assert result == cell_symbol(ConfirmationState.INVALID, marker=False)


def test_cell_display_missing_status_is_none_state():
    assert cell_display(None, ServiceGroup.CONFIRMATION) == cell_symbol(ConfirmationState.NONE, False)


# ---------------------------------------------------------------------------
# cell_tooltip_text — wörtliche Werte + neutrale Erklärung
# ---------------------------------------------------------------------------


def test_tooltip_text_shows_literal_requested_value_and_neutral_explanation():
    status = _status(ct="QSL", s="No", r="Requested")
    text = cell_tooltip_text("QSL", status, ServiceGroup.CONFIRMATION)
    assert "Requested" in text
    assert "angefordert" in text.lower() or "erwartet" in text.lower()


def test_tooltip_text_upload_service_has_no_received_line():
    status = _status(ct="CLUBLOG", s="Yes", r=None)
    text = cell_tooltip_text("CLUBLOG", status, ServiceGroup.UPLOAD)
    assert "Empfangen" not in text


def test_tooltip_text_confirmation_service_has_received_line():
    status = _status(ct="LOTW", s="Yes", r="No")
    text = cell_tooltip_text("LOTW", status, ServiceGroup.CONFIRMATION)
    assert "Empfangen" in text


def test_tooltip_text_missing_status_no_crash():
    text = cell_tooltip_text("QSL", None, ServiceGroup.CONFIRMATION)
    assert "QSL" in text or "Papier" in text
    assert "kein eintrag" in text.lower()


# ---------------------------------------------------------------------------
# Spaltenwahl (Default alle sichtbar)
# ---------------------------------------------------------------------------


def test_column_visibility_default_all_visible():
    vis = ColumnVisibility()
    assert vis.visible_services() == list(SERVICE_COLUMN_ORDER)


def test_column_visibility_hide_one_service():
    vis = ColumnVisibility()
    vis.set_visible("CLUBLOG", False)
    assert "CLUBLOG" not in vis.visible_services()
    assert "QSL" in vis.visible_services()


def test_service_labels_cover_all_columns():
    for ct in SERVICE_COLUMN_ORDER:
        assert ct in SERVICE_LABELS


# ---------------------------------------------------------------------------
# Sortierung (ADR-0052-Muster)
# ---------------------------------------------------------------------------


def test_sort_rows_by_date_ascending():
    rows = [_row(qsoid="A", qsodate="2025-06-01 00:00:00Z"), _row(qsoid="B", qsodate="2025-01-01 00:00:00Z")]
    result = sort_rows_by_column(rows, "qsodate", ascending=True)
    assert [r.qsoid for r in result] == ["B", "A"]


def test_sort_rows_by_callsign_descending():
    rows = [_row(qsoid="A", callsign="AAA"), _row(qsoid="B", callsign="ZZZ")]
    result = sort_rows_by_column(rows, "callsign", ascending=False)
    assert [r.qsoid for r in result] == ["B", "A"]


def test_sort_rows_missing_date_goes_last():
    rows = [_row(qsoid="A", qsodate=None), _row(qsoid="B", qsodate="2025-01-01 00:00:00Z")]
    result = sort_rows_by_column(rows, "qsodate", ascending=True)
    assert [r.qsoid for r in result] == ["B", "A"]


def test_sort_rows_by_service_column_progression_order():
    """NONE < INVALID < SENT < RECEIVED (aufsteigend = wachsende Bestätigung)."""
    none_row = _row(qsoid="N", services={})
    invalid_row = _row(qsoid="I", services={"QSL": _status(s="Invalid", r="Invalid")})
    sent_row = _row(qsoid="S", services={"QSL": _status(s="Yes", r="No")})
    received_row = _row(qsoid="R", services={"QSL": _status(s="Yes", r="Yes")})
    rows = [received_row, sent_row, invalid_row, none_row]
    result = sort_rows_by_column(rows, "QSL", ascending=True)
    assert [r.qsoid for r in result] == ["N", "I", "S", "R"]


def test_row_sort_key_unknown_column_stable():
    row = _row()
    assert row_sort_key(row, "unknown_column") == (0, "")


# ---------------------------------------------------------------------------
# Detailzeile — wörtliche Werte, fehlend = "–"
# ---------------------------------------------------------------------------


def test_format_detail_line_shows_literal_values_for_present_service():
    row = _row(services={"QSL": _status(s="Yes", r="Yes", sd="2025-01-01", rd="2025-01-05")})
    text = format_detail_line(row)
    assert "S=Yes" in text
    assert "R=Yes" in text
    assert "SD=2025-01-01" in text
    assert "RD=2025-01-05" in text


def test_format_detail_line_missing_service_shows_dash():
    row = _row(services={})
    text = format_detail_line(row)
    assert "S=–" in text
    assert "R=–" in text


def test_format_detail_line_includes_qslvia_and_locator():
    row = _row()
    row.qslvia = "DL0XX"
    row.gridsquare = "JO31"
    text = format_detail_line(row)
    assert "DL0XX" in text
    assert "JO31" in text


def test_format_detail_line_missing_qslvia_shows_dash():
    row = _row()
    row.qslvia = None
    text = format_detail_line(row)
    assert "QSL via: –" in text


# ---------------------------------------------------------------------------
# Zeitraum-Schnellwahl
# ---------------------------------------------------------------------------


def test_quick_range_all_returns_none_bounds():
    assert quick_range_bounds("Alle", date(2026, 9, 19)) == (None, None)


def test_quick_range_last_30_days():
    start, end = quick_range_bounds("Letzte 30 Tage", date(2026, 9, 19))
    assert end == "2026-09-19"
    assert start == "2026-08-20"


def test_quick_range_this_year():
    start, end = quick_range_bounds("Dieses Jahr", date(2026, 9, 19))
    assert start == "2026-01-01"
    assert end == "2026-09-19"


def test_quick_range_last_year():
    start, end = quick_range_bounds("Letztes Jahr", date(2026, 9, 19))
    assert start == "2025-01-01"
    assert end == "2025-12-31"


def test_quick_range_unknown_choice_returns_none_bounds():
    assert quick_range_bounds("unbekannt", date(2026, 9, 19)) == (None, None)


# ---------------------------------------------------------------------------
# Kennzahlen-Kacheln (Nachbesserung #42 — kompakt gruppiert statt einer Textzeile)
# ---------------------------------------------------------------------------


def test_metric_tile_labels_and_values_same_length():
    metrics = compute_metrics([])
    assert len(METRIC_TILE_LABELS) == len(metric_tile_values(metrics))


def test_metric_tile_values_total_and_confirmed():
    rows = [
        _row(qsoid="A", services={"QSL": _status(s="Yes", r="Yes")}),
        _row(qsoid="B", services={}),
    ]
    metrics = compute_metrics(rows)
    values = metric_tile_values(metrics)
    assert values[METRIC_TILE_LABELS.index("QSOs")] == "2"
    assert values[METRIC_TILE_LABELS.index("Bestätigt")] == "1 (50.0 %)"


def test_metric_tile_values_groups_lotw_qrz_pair():
    rows = [
        _row(qsoid="A", services={"LOTW": _status(ct="LOTW", s="Yes", r="Yes")}),
        _row(qsoid="B", services={"QRZCOM": _status(ct="QRZCOM", s="Yes", r="Yes")}),
    ]
    metrics = compute_metrics(rows)
    values = metric_tile_values(metrics)
    assert values[METRIC_TILE_LABELS.index("LoTW / QRZ")] == "1/1"


def test_metric_tile_values_groups_papier_eqsl_pair():
    rows = [_row(qsoid="A", services={"QSL": _status(s="No", r="Yes")})]
    metrics = compute_metrics(rows)
    values = metric_tile_values(metrics)
    assert values[METRIC_TILE_LABELS.index("Papier / eQSL")] == "1/0"


def test_metric_tile_values_dxcc():
    rows = [_row(qsoid="A", dxcc=230, services={"QSL": _status(s="No", r="Yes")})]
    metrics = compute_metrics(rows)
    values = metric_tile_values(metrics)
    assert values[METRIC_TILE_LABELS.index("DXCC bestätigt")] == "1 / 1"
