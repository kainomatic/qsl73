# QSL73 — Copyright (C) 2026 DF1DS (kainomatic) — SPDX-License-Identifier: GPL-3.0-or-later
"""Unit-Tests für confirmations — Bestätigungsübersicht-Logikmodul (Issue #42, Auftrag 1).

Tk-frei. Read-only-Tests gegen die realen Test-DBs in docs/testdateien/ sind mit
@pytest.mark.acceptance/@pytest.mark.slow markiert (Skip wenn Datei fehlt) und laufen
niemals schreibend gegen diese Dateien.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from qsl73.confirmations import (
    CONFIRMATION_SERVICES,
    PRESETS,
    UPLOAD_SERVICES,
    CollectiveFilter,
    ConfirmationFilters,
    ConfirmationState,
    QsoConfirmationRow,
    ServiceGroup,
    ServiceStatus,
    apply_filters,
    available_status_values,
    compute_metrics,
    confirmation_state,
    has_marker,
    load_confirmation_data,
    load_confirmation_rows,
    matches_band,
    matches_collective_filter,
    matches_continent,
    matches_country,
    matches_date_range,
    matches_mode,
    matches_received_status,
    matches_sent_status,
    matches_text_query,
    open_readonly_connection,
    parse_qsoconfirmations,
    preset_filters,
    service_group,
)
from qsl73.log4om_db import SchemaError

DB_DH3KR = Path("docs/testdateien/TESTDB_DH3KR_schreibtest.sqlite")
DB_MAI24 = Path("docs/testdateien/TESTDB_DF1DS_Mai24_backup.sqlite")


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------


def _row(
    qsoid="Q1",
    callsign="DK8XX",
    qsodate="2025-04-02 19:42:00Z",
    band="20m",
    mode="SSB",
    dxcc=230,
    country="Germany",
    cont="EU",
    stationcallsign="DF1DS",
    gridsquare="JO31",
    qslvia="",
    services=None,
    confirmations_error=None,
) -> QsoConfirmationRow:
    return QsoConfirmationRow(
        qsoid=qsoid,
        callsign=callsign,
        qsodate=qsodate,
        band=band,
        mode=mode,
        dxcc=dxcc,
        country=country,
        cont=cont,
        stationcallsign=stationcallsign,
        gridsquare=gridsquare,
        qslvia=qslvia,
        services=services or {},
        confirmations_error=confirmations_error,
    )


def _status(ct="QSL", s=None, r=None, sv=None, rv=None, sd=None, rd=None) -> ServiceStatus:
    return ServiceStatus(ct=ct, s=s, r=r, sv=sv, rv=rv, sd=sd, rd=rd)


# ---------------------------------------------------------------------------
# Dienstgruppen-Mapping (Grundentscheidung 5)
# ---------------------------------------------------------------------------


def test_confirmation_services_constants():
    assert set(CONFIRMATION_SERVICES) == {"QSL", "LOTW", "EQSL", "QRZCOM"}
    assert set(UPLOAD_SERVICES) == {"CLUBLOG", "HRDLOG", "HAMQTH"}


@pytest.mark.parametrize("ct", ["QSL", "LOTW", "EQSL", "QRZCOM"])
def test_service_group_confirmation(ct):
    assert service_group(ct) is ServiceGroup.CONFIRMATION


@pytest.mark.parametrize("ct", ["CLUBLOG", "HRDLOG", "HAMQTH"])
def test_service_group_upload(ct):
    assert service_group(ct) is ServiceGroup.UPLOAD


def test_service_group_unknown_ct_not_discarded():
    """Unbekannte CT-Typen werden generisch mitgeführt, nicht verworfen (Grundentscheidung 6)."""
    assert service_group("FUTURESERVICE") is ServiceGroup.UNKNOWN


# ---------------------------------------------------------------------------
# Parsen von qsoconfirmations (Grundentscheidungen 6, 7; ADR-0012-Geist)
# ---------------------------------------------------------------------------


def test_parse_full_seven_service_array():
    raw = json.dumps([
        {"CT": "QSL", "S": "No", "R": "No", "SV": "Electronic", "RV": "Electronic"},
        {"CT": "EQSL", "S": "Yes", "R": "No", "SV": "Electronic", "RV": "Electronic", "SD": "2023-03-26T00:00:00Z"},
        {"CT": "LOTW", "S": "Yes", "R": "Yes", "SV": "Electronic", "RV": "Electronic",
         "SD": "2023-03-04T00:00:00Z", "RD": "2023-03-19T00:00:00Z"},
    ])
    services, error = parse_qsoconfirmations(raw)
    assert error is None
    assert set(services) == {"QSL", "EQSL", "LOTW"}
    assert services["LOTW"].s == "Yes"
    assert services["LOTW"].r == "Yes"
    assert services["LOTW"].rd == "2023-03-19T00:00:00Z"


def test_parse_missing_sv_rv_after_requested():
    """§7.1 Zusatzbefund 1: bei Requested/Queued fehlen SV/RV — darf nicht abstürzen."""
    raw = json.dumps([{"CT": "QSL", "S": "No", "R": "Requested"}])
    services, error = parse_qsoconfirmations(raw)
    assert error is None
    qsl = services["QSL"]
    assert qsl.r == "Requested"
    assert qsl.sv is None
    assert qsl.rv is None


def test_parse_queued_and_invalid_literal():
    raw_queued = json.dumps([{"CT": "QSL", "S": "Queued", "R": "No"}])
    services, _ = parse_qsoconfirmations(raw_queued)
    assert services["QSL"].s == "Queued"

    raw_invalid = json.dumps([
        {"CT": "LOTW", "S": "Invalid", "R": "Invalid", "SV": "Electronic", "RV": "Electronic"}
    ])
    services, _ = parse_qsoconfirmations(raw_invalid)
    assert services["LOTW"].s == "Invalid"
    assert services["LOTW"].r == "Invalid"


def test_parse_unknown_ct_kept_generically():
    raw = json.dumps([{"CT": "FUTURESERVICE", "S": "Yes", "R": "No"}])
    services, error = parse_qsoconfirmations(raw)
    assert error is None
    assert "FUTURESERVICE" in services
    assert services["FUTURESERVICE"].s == "Yes"


def test_parse_unknown_sr_value_passed_through_literally():
    raw = json.dumps([{"CT": "QSL", "S": "SomethingNew", "R": "No"}])
    services, _ = parse_qsoconfirmations(raw)
    assert services["QSL"].s == "SomethingNew"


def test_parse_ext_never_taken_over():
    raw = json.dumps([{"CT": "HRDLOG", "S": "No", "R": "No", "EXT": "adif-snippet-with-callsign"}])
    services, _ = parse_qsoconfirmations(raw)
    hrdlog = services["HRDLOG"]
    assert not hasattr(hrdlog, "ext")
    assert "EXT" not in hrdlog.__dict__.values()


def test_parse_broken_json_no_crash_returns_error():
    services, error = parse_qsoconfirmations("{not valid json[")
    assert services == {}
    assert error is not None


def test_parse_empty_string_no_crash():
    services, error = parse_qsoconfirmations("")
    assert services == {}
    assert error is not None


def test_parse_none_no_crash():
    services, error = parse_qsoconfirmations(None)
    assert services == {}
    assert error is not None


def test_parse_non_array_json_no_crash():
    services, error = parse_qsoconfirmations(json.dumps({"CT": "QSL"}))
    assert services == {}
    assert error is not None


def test_parse_non_dict_entry_skipped_without_crash():
    raw = json.dumps(["not-a-dict", {"CT": "QSL", "S": "No", "R": "No"}])
    services, error = parse_qsoconfirmations(raw)
    assert error is None
    assert "QSL" in services


# ---------------------------------------------------------------------------
# Fakten-vs-Merker-Trennung (Grundentscheidung 3, 4)
# ---------------------------------------------------------------------------


def test_confirmation_state_received_beats_sent():
    status = _status(s="Yes", r="Yes")
    assert confirmation_state(status, ServiceGroup.CONFIRMATION) is ConfirmationState.RECEIVED


def test_confirmation_state_sent_only():
    status = _status(s="Yes", r="No")
    assert confirmation_state(status, ServiceGroup.CONFIRMATION) is ConfirmationState.SENT


def test_confirmation_state_none_when_no_hard_fact():
    status = _status(s="No", r="No")
    assert confirmation_state(status, ServiceGroup.CONFIRMATION) is ConfirmationState.NONE


def test_confirmation_state_requested_is_not_a_hard_fact():
    """Requested/Queued sind Merker, keine harten Fakten — dürfen NIE das Hauptsymbol auf SENT/RECEIVED heben."""
    status = _status(s="Requested", r="Requested")
    assert confirmation_state(status, ServiceGroup.CONFIRMATION) is ConfirmationState.NONE


def test_confirmation_state_invalid_is_its_own_state():
    status = _status(s="Invalid", r="Invalid")
    assert confirmation_state(status, ServiceGroup.CONFIRMATION) is ConfirmationState.INVALID


def test_confirmation_state_invalid_distinct_from_none():
    assert ConfirmationState.INVALID is not ConfirmationState.NONE


def test_confirmation_state_missing_status_is_none():
    assert confirmation_state(None, ServiceGroup.CONFIRMATION) is ConfirmationState.NONE


def test_confirmation_state_upload_group_ignores_r():
    """Upload-Dienste werten nur S aus (Grundentscheidung 5) — R spielt keine Rolle."""
    status = _status(ct="HRDLOG", s="Yes", r="Yes")
    assert confirmation_state(status, ServiceGroup.UPLOAD) is ConfirmationState.SENT


def test_confirmation_state_upload_group_invalid():
    status = _status(ct="HRDLOG", s="Invalid")
    assert confirmation_state(status, ServiceGroup.UPLOAD) is ConfirmationState.INVALID


def test_confirmation_state_upload_group_none():
    status = _status(ct="HRDLOG", s="No")
    assert confirmation_state(status, ServiceGroup.UPLOAD) is ConfirmationState.NONE


def test_has_marker_requested_on_receive_side():
    assert has_marker(_status(s="No", r="Requested")) is True


def test_has_marker_queued_on_send_side():
    assert has_marker(_status(s="Queued", r="No")) is True


def test_has_marker_false_for_yes_no_invalid():
    assert has_marker(_status(s="Yes", r="No")) is False
    assert has_marker(_status(s="No", r="No")) is False
    assert has_marker(_status(s="Invalid", r="Invalid")) is False


def test_has_marker_none_status_false():
    assert has_marker(None) is False


# ---------------------------------------------------------------------------
# Kennzahlen (nur harte Fakten, bezogen auf übergebene Menge)
# ---------------------------------------------------------------------------


def test_compute_metrics_total_and_confirmed_anywhere():
    rows = [
        _row(qsoid="A", dxcc=230, services={"QSL": _status(s="No", r="Yes")}),
        _row(qsoid="B", dxcc=291, services={"QSL": _status(s="No", r="No")}),
    ]
    metrics = compute_metrics(rows)
    assert metrics.total_qsos == 2
    assert metrics.confirmed_anywhere == 1
    assert metrics.confirmed_anywhere_pct == pytest.approx(50.0)


def test_compute_metrics_empty_list_no_division_by_zero():
    metrics = compute_metrics([])
    assert metrics.total_qsos == 0
    assert metrics.confirmed_anywhere == 0
    assert metrics.confirmed_anywhere_pct == 0.0


def test_compute_metrics_per_service_sent_received_independent():
    rows = [
        _row(qsoid="A", services={"LOTW": _status(ct="LOTW", s="Yes", r="No")}),
        _row(qsoid="B", services={"LOTW": _status(ct="LOTW", s="Yes", r="Yes")}),
    ]
    metrics = compute_metrics(rows)
    assert metrics.services["LOTW"].sent == 2
    assert metrics.services["LOTW"].received == 1


def test_compute_metrics_requested_queued_invalid_not_counted():
    rows = [
        _row(qsoid="A", services={"QSL": _status(s="Requested", r="Requested")}),
        _row(qsoid="B", services={"QSL": _status(s="Queued", r="No")}),
        _row(qsoid="C", services={"LOTW": _status(ct="LOTW", s="Invalid", r="Invalid")}),
    ]
    metrics = compute_metrics(rows)
    assert metrics.confirmed_anywhere == 0
    assert metrics.services["QSL"].sent == 0
    assert metrics.services["QSL"].received == 0
    assert metrics.services["LOTW"].sent == 0
    assert metrics.services["LOTW"].received == 0


def test_compute_metrics_dxcc_worked_vs_confirmed():
    rows = [
        _row(qsoid="A", dxcc=230, services={"QSL": _status(s="No", r="Yes")}),
        _row(qsoid="B", dxcc=230, services={"QSL": _status(s="No", r="No")}),
        _row(qsoid="C", dxcc=291, services={"QSL": _status(s="No", r="No")}),
    ]
    metrics = compute_metrics(rows)
    assert metrics.dxcc_worked == 2
    assert metrics.dxcc_confirmed == 1


def test_compute_metrics_upload_service_sent_only():
    rows = [_row(qsoid="A", services={"HRDLOG": _status(ct="HRDLOG", s="Yes")})]
    metrics = compute_metrics(rows)
    assert metrics.services["HRDLOG"].sent == 1
    assert metrics.services["HRDLOG"].received == 0


# ---------------------------------------------------------------------------
# Basisfilter
# ---------------------------------------------------------------------------


def test_matches_text_query_call_country_locator():
    row = _row(callsign="DK8XX", country="Germany", gridsquare="JO31")
    assert matches_text_query(row, "dk8") is True
    assert matches_text_query(row, "german") is True
    assert matches_text_query(row, "jo31") is True
    assert matches_text_query(row, "zzzz") is False


def test_matches_text_query_empty_matches_all():
    assert matches_text_query(_row(), "") is True
    assert matches_text_query(_row(), None) is True


def test_matches_date_range_inclusive_bounds():
    row = _row(qsodate="2025-04-02 19:42:00Z")
    assert matches_date_range(row, "2025-04-02", "2025-04-02") is True
    assert matches_date_range(row, "2025-04-03", None) is False
    assert matches_date_range(row, None, "2025-04-01") is False
    assert matches_date_range(row, None, None) is True


def test_matches_band_case_insensitive():
    row = _row(band="20m")
    assert matches_band(row, "20M") is True
    assert matches_band(row, "40m") is False
    assert matches_band(row, None) is True


def test_matches_mode_case_insensitive():
    row = _row(mode="FT8")
    assert matches_mode(row, "ft8") is True
    assert matches_mode(row, "SSB") is False


def test_matches_continent():
    row = _row(cont="EU")
    assert matches_continent(row, "EU") is True
    assert matches_continent(row, "NA") is False
    assert matches_continent(row, None) is True


def test_matches_country():
    row = _row(country="Germany")
    assert matches_country(row, "Germany") is True
    assert matches_country(row, "France") is False


# ---------------------------------------------------------------------------
# Statusfilter (rohe Log4OM-Werte)
# ---------------------------------------------------------------------------


def test_matches_sent_status_literal_value():
    row = _row(services={"QSL": _status(s="Requested", r="No")})
    assert matches_sent_status(row, "QSL", "Requested") is True
    assert matches_sent_status(row, "QSL", "Yes") is False
    assert matches_sent_status(row, "QSL", None) is True


def test_matches_received_status_literal_value():
    row = _row(services={"QSL": _status(s="No", r="Invalid")})
    assert matches_received_status(row, "QSL", "Invalid") is True
    assert matches_received_status(row, "QSL", "No") is False


def test_matches_status_missing_service_no_match_on_explicit_filter():
    row = _row(services={})
    assert matches_sent_status(row, "QSL", "No") is False
    assert matches_sent_status(row, "QSL", None) is True


def test_available_status_values_from_actual_data_only():
    rows = [
        _row(qsoid="A", services={"QSL": _status(s="No", r="No")}),
        _row(qsoid="B", services={"QSL": _status(s="Requested", r="Yes")}),
        _row(qsoid="C", services={}),
    ]
    assert available_status_values(rows, "QSL", "s") == ["No", "Requested"]
    assert available_status_values(rows, "QSL", "r") == ["No", "Yes"]


# ---------------------------------------------------------------------------
# Sammelfilter (nur harte Fakten)
# ---------------------------------------------------------------------------


def test_collective_confirmed_anywhere_paper():
    row = _row(services={"QSL": _status(s="No", r="Yes")})
    assert matches_collective_filter(row, CollectiveFilter.CONFIRMED_ANYWHERE) is True
    assert matches_collective_filter(row, CollectiveFilter.PAPER_ONLY) is True
    assert matches_collective_filter(row, CollectiveFilter.ELECTRONIC_ONLY) is False
    assert matches_collective_filter(row, CollectiveFilter.CONFIRMED_NOWHERE) is False


def test_collective_confirmed_anywhere_electronic():
    row = _row(services={"LOTW": _status(ct="LOTW", s="Yes", r="Yes")})
    assert matches_collective_filter(row, CollectiveFilter.ELECTRONIC_ONLY) is True
    assert matches_collective_filter(row, CollectiveFilter.PAPER_ONLY) is False


def test_collective_confirmed_nowhere():
    row = _row(services={"QSL": _status(s="No", r="No")})
    assert matches_collective_filter(row, CollectiveFilter.CONFIRMED_NOWHERE) is True
    assert matches_collective_filter(row, CollectiveFilter.CONFIRMED_ANYWHERE) is False


def test_collective_any_matches_everything():
    row = _row(services={})
    assert matches_collective_filter(row, CollectiveFilter.ANY) is True


def test_collective_both_paper_and_electronic_excludes_only_variants():
    row = _row(services={
        "QSL": _status(s="No", r="Yes"),
        "LOTW": _status(ct="LOTW", s="Yes", r="Yes"),
    })
    assert matches_collective_filter(row, CollectiveFilter.CONFIRMED_ANYWHERE) is True
    assert matches_collective_filter(row, CollectiveFilter.PAPER_ONLY) is False
    assert matches_collective_filter(row, CollectiveFilter.ELECTRONIC_ONLY) is False


# ---------------------------------------------------------------------------
# Sammelfilter — neu für Presets (Nachbesserung #42, harte Fakten je Dienst)
# ---------------------------------------------------------------------------


def test_collective_received_not_sent_any_service_true_when_paper_confirmed_not_sent():
    row = _row(services={"QSL": _status(s="No", r="Yes")})
    assert matches_collective_filter(row, CollectiveFilter.RECEIVED_NOT_SENT_ANY) is True


def test_collective_received_not_sent_any_service_false_when_same_service_also_sent():
    """Digital automatisch S+R=Yes bei LoTW darf hier NICHT anschlagen (Grenzfall Presets 5/6)."""
    row = _row(services={"LOTW": _status(ct="LOTW", s="Yes", r="Yes")})
    assert matches_collective_filter(row, CollectiveFilter.RECEIVED_NOT_SENT_ANY) is False


def test_collective_received_not_sent_any_service_false_when_nothing_received():
    row = _row(services={"QSL": _status(s="No", r="No")})
    assert matches_collective_filter(row, CollectiveFilter.RECEIVED_NOT_SENT_ANY) is False


def test_collective_received_not_sent_any_service_ignores_requested_marker():
    """Requested ist kein hartes R=Yes — darf Preset 5 nicht auslösen."""
    row = _row(services={"QSL": _status(s="No", r="Requested")})
    assert matches_collective_filter(row, CollectiveFilter.RECEIVED_NOT_SENT_ANY) is False


def test_collective_paper_received_not_sent_true():
    row = _row(services={"QSL": _status(s="No", r="Yes")})
    assert matches_collective_filter(row, CollectiveFilter.PAPER_RECEIVED_NOT_SENT) is True


def test_collective_paper_received_not_sent_false_when_paper_also_sent():
    row = _row(services={"QSL": _status(s="Yes", r="Yes")})
    assert matches_collective_filter(row, CollectiveFilter.PAPER_RECEIVED_NOT_SENT) is False


def test_collective_paper_received_not_sent_false_when_only_electronic_confirmed():
    """Preset 6 ist NUR QSL — ein bestätigter Digital-Dienst darf nicht anschlagen."""
    row = _row(services={"LOTW": _status(ct="LOTW", s="No", r="Yes")})
    assert matches_collective_filter(row, CollectiveFilter.PAPER_RECEIVED_NOT_SENT) is False


def test_collective_not_uploaded_anywhere_true_when_no_upload_service_sent():
    row = _row(services={"CLUBLOG": _status(ct="CLUBLOG", s="No")})
    assert matches_collective_filter(row, CollectiveFilter.NOT_UPLOADED_ANYWHERE) is True


def test_collective_not_uploaded_anywhere_false_when_one_uploaded():
    row = _row(services={
        "CLUBLOG": _status(ct="CLUBLOG", s="No"),
        "HRDLOG": _status(ct="HRDLOG", s="Yes"),
    })
    assert matches_collective_filter(row, CollectiveFilter.NOT_UPLOADED_ANYWHERE) is False


def test_collective_not_uploaded_anywhere_true_when_no_upload_entries_at_all():
    row = _row(services={})
    assert matches_collective_filter(row, CollectiveFilter.NOT_UPLOADED_ANYWHERE) is True


# ---------------------------------------------------------------------------
# Presets / Schnellansichten (Nachbesserung #42 — nur harte Fakten + Merker)
# ---------------------------------------------------------------------------


def test_presets_has_seven_entries_in_order():
    assert [p.label for p in PRESETS] == [
        "Alle",
        "Nirgends bestätigt",
        "Nur digital, Papier fehlt",
        "Papier angefordert",
        "Bekommen, selbst nicht gesendet",
        "Papier bekommen, selbst noch nicht gesendet",
        "Noch nicht hochgeladen",
    ]


def test_preset_alle_matches_everything():
    rows = [_row(qsoid="A"), _row(qsoid="B", services={"QSL": _status(s="No", r="Yes")})]
    filters = preset_filters(PRESETS[0])
    assert len(apply_filters(rows, filters)) == 2


def test_preset_nirgends_bestaetigt():
    rows = [
        _row(qsoid="A", services={"QSL": _status(s="No", r="No")}),
        _row(qsoid="B", services={"QSL": _status(s="No", r="Yes")}),
    ]
    filters = preset_filters(PRESETS[1])
    assert [r.qsoid for r in apply_filters(rows, filters)] == ["A"]


def test_preset_nur_digital_papier_fehlt():
    rows = [
        _row(qsoid="A", services={"LOTW": _status(ct="LOTW", s="No", r="Yes")}),
        _row(qsoid="B", services={
            "LOTW": _status(ct="LOTW", s="No", r="Yes"),
            "QSL": _status(s="No", r="Yes"),
        }),
    ]
    filters = preset_filters(PRESETS[2])
    assert [r.qsoid for r in apply_filters(rows, filters)] == ["A"]


def test_preset_papier_angefordert():
    rows = [
        _row(qsoid="A", services={"QSL": _status(s="No", r="Requested")}),
        _row(qsoid="B", services={"QSL": _status(s="No", r="Yes")}),
    ]
    filters = preset_filters(PRESETS[3])
    assert [r.qsoid for r in apply_filters(rows, filters)] == ["A"]


def test_preset_bekommen_selbst_nicht_gesendet():
    rows = [
        _row(qsoid="A", services={"EQSL": _status(ct="EQSL", s="No", r="Yes")}),
        _row(qsoid="B", services={"LOTW": _status(ct="LOTW", s="Yes", r="Yes")}),
    ]
    filters = preset_filters(PRESETS[4])
    assert [r.qsoid for r in apply_filters(rows, filters)] == ["A"]


def test_preset_papier_bekommen_selbst_noch_nicht_gesendet():
    rows = [
        _row(qsoid="A", services={"QSL": _status(s="No", r="Yes")}),
        _row(qsoid="B", services={"LOTW": _status(ct="LOTW", s="No", r="Yes")}),
    ]
    filters = preset_filters(PRESETS[5])
    assert [r.qsoid for r in apply_filters(rows, filters)] == ["A"]


def test_preset_noch_nicht_hochgeladen():
    rows = [
        _row(qsoid="A", services={}),
        _row(qsoid="B", services={"CLUBLOG": _status(ct="CLUBLOG", s="Yes")}),
    ]
    filters = preset_filters(PRESETS[6])
    assert [r.qsoid for r in apply_filters(rows, filters)] == ["A"]


# ---------------------------------------------------------------------------
# Kombinierte Filter (UND-Verknüpfung)
# ---------------------------------------------------------------------------


def test_apply_filters_combines_and():
    rows = [
        _row(qsoid="A", callsign="DK8XX", band="20m", services={"QSL": _status(s="No", r="Yes")}),
        _row(qsoid="B", callsign="DK8XX", band="40m", services={"QSL": _status(s="No", r="Yes")}),
        _row(qsoid="C", callsign="OE6XXX", band="20m", services={"QSL": _status(s="No", r="No")}),
    ]
    filters = ConfirmationFilters(text_query="dk8", band="20m")
    result = apply_filters(rows, filters)
    assert [r.qsoid for r in result] == ["A"]


def test_apply_filters_no_filters_returns_all():
    rows = [_row(qsoid="A"), _row(qsoid="B")]
    result = apply_filters(rows, ConfirmationFilters())
    assert len(result) == 2


def test_apply_filters_status_and_collective_combined():
    rows = [
        _row(qsoid="A", services={"QSL": _status(s="No", r="Requested")}),
        _row(qsoid="B", services={"QSL": _status(s="No", r="Yes")}),
    ]
    filters = ConfirmationFilters(
        received_status={"QSL": "Requested"},
        collective=CollectiveFilter.CONFIRMED_NOWHERE,
    )
    result = apply_filters(rows, filters)
    assert [r.qsoid for r in result] == ["A"]


# ---------------------------------------------------------------------------
# Read-only-Laden gegen echte Test-DBs
# ---------------------------------------------------------------------------


def test_open_readonly_connection_rejects_write(tmp_path):
    """Read-only-Verbindung (mode=ro) verweigert Schreiben (Grundentscheidung 2)."""
    db_path = tmp_path / "ro_test.sqlite"
    setup_conn = sqlite3.connect(str(db_path))
    setup_conn.execute("CREATE TABLE Log (qsoid TEXT PRIMARY KEY, qsoconfirmations TEXT)")
    setup_conn.commit()
    setup_conn.close()

    conn = open_readonly_connection(db_path)
    try:
        with pytest.raises(sqlite3.OperationalError):
            conn.execute("INSERT INTO Log VALUES ('Q1', '[]')")
    finally:
        conn.close()


def test_open_readonly_connection_missing_file_raises(tmp_path):
    missing = tmp_path / "does_not_exist.sqlite"
    with pytest.raises(sqlite3.OperationalError):
        conn = open_readonly_connection(missing)
        conn.execute("SELECT 1")


def test_load_confirmation_rows_from_mini_db(tmp_path):
    db_path = tmp_path / "mini.sqlite"
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        "CREATE TABLE Log (qsoid TEXT PRIMARY KEY, callsign TEXT, qsodate TEXT, band TEXT,"
        " mode TEXT, dxcc INTEGER, country TEXT, cont TEXT, qsoconfirmations TEXT,"
        " stationcallsign TEXT, gridsquare TEXT, qslvia TEXT)"
    )
    conn.execute(
        "INSERT INTO Log VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            "Q1", "DK8XX", "2025-04-02 19:42:00Z", "20m", "SSB", 230, "Germany", "EU",
            json.dumps([{"CT": "QSL", "S": "No", "R": "No"}]), "DF1DS", "JO31", "",
        ),
    )
    conn.commit()

    ro_conn = open_readonly_connection(db_path)
    try:
        rows = load_confirmation_rows(ro_conn)
    finally:
        ro_conn.close()
    conn.close()

    assert len(rows) == 1
    assert rows[0].qsoid == "Q1"
    assert rows[0].services["QSL"].r == "No"


def test_load_confirmation_rows_broken_json_kept_not_crashed(tmp_path):
    db_path = tmp_path / "mini_broken.sqlite"
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        "CREATE TABLE Log (qsoid TEXT PRIMARY KEY, callsign TEXT, qsodate TEXT, band TEXT,"
        " mode TEXT, dxcc INTEGER, country TEXT, cont TEXT, qsoconfirmations TEXT,"
        " stationcallsign TEXT, gridsquare TEXT, qslvia TEXT)"
    )
    conn.execute(
        "INSERT INTO Log VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        ("Q1", "DK8XX", "2025-04-02 19:42:00Z", "20m", "SSB", 230, "Germany", "EU",
         "{not valid", "DF1DS", "JO31", ""),
    )
    conn.commit()
    conn.close()

    ro_conn = open_readonly_connection(db_path)
    try:
        rows = load_confirmation_rows(ro_conn)
    finally:
        ro_conn.close()

    assert len(rows) == 1
    assert rows[0].services == {}
    assert rows[0].confirmations_error is not None


def test_load_confirmation_data_schema_error_clean(tmp_path):
    db_path = tmp_path / "no_log_table.sqlite"
    conn = sqlite3.connect(str(db_path))
    conn.execute("CREATE TABLE Other (x TEXT)")
    conn.commit()
    conn.close()

    with pytest.raises(SchemaError):
        load_confirmation_data(db_path)


@pytest.mark.acceptance
@pytest.mark.slow
def test_load_confirmation_data_real_db_dh3kr_handtest_values():
    if not DB_DH3KR.exists():
        pytest.skip(f"Test-DB nicht vorhanden: {DB_DH3KR}")
    rows = load_confirmation_data(DB_DH3KR)
    by_id = {r.qsoid: r for r in rows}

    requested_received = by_id["20250426195200002"]
    assert requested_received.services["QSL"].r == "Requested"
    assert requested_received.services["QSL"].sv is None
    assert has_marker(requested_received.services["QSL"]) is True
    assert confirmation_state(
        requested_received.services["QSL"], ServiceGroup.CONFIRMATION
    ) is ConfirmationState.NONE

    requested_sent = by_id["20250423122300001"]
    assert requested_sent.services["QSL"].s == "Requested"

    queued_sent = by_id["20250402194200003"]
    assert queued_sent.services["QSL"].s == "Queued"

    invalid_both = by_id["20250402090000004"]
    assert invalid_both.services["LOTW"].s == "Invalid"
    assert invalid_both.services["LOTW"].r == "Invalid"
    assert invalid_both.services["LOTW"].sv == "Electronic"
    assert confirmation_state(
        invalid_both.services["LOTW"], ServiceGroup.CONFIRMATION
    ) is ConfirmationState.INVALID


@pytest.mark.acceptance
@pytest.mark.slow
def test_load_confirmation_data_real_db_dh3kr_full_load_no_crash():
    if not DB_DH3KR.exists():
        pytest.skip(f"Test-DB nicht vorhanden: {DB_DH3KR}")
    rows = load_confirmation_data(DB_DH3KR)
    assert len(rows) == 432
    metrics = compute_metrics(rows)
    assert metrics.total_qsos == 432


@pytest.mark.acceptance
@pytest.mark.slow
def test_load_confirmation_data_real_db_mai24_full_load_no_crash():
    if not DB_MAI24.exists():
        pytest.skip(f"Test-DB nicht vorhanden: {DB_MAI24}")
    rows = load_confirmation_data(DB_MAI24)
    assert len(rows) > 0
    for row in rows:
        assert isinstance(row.services, dict)
