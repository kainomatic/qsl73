"""Unit-Tests für log4om_write.apply_paper_qsl (pure JSON-Transformation).

Keine DB nötig — alle Tests arbeiten auf synthetischen JSON-Strings.
"""
import json

import pytest

from qsl73.log4om_write import (
    InvalidRouteError,
    QslEntryNotFoundError,
    apply_paper_qsl,
)

# ---------------------------------------------------------------------------
# Hilfsfunktionen / Fixtures
# ---------------------------------------------------------------------------

def _make_confirmations(
    r="No",
    rv="Electronic",
    include_rv=True,
    extra_entries=True,
) -> str:
    """Erzeugt einen qsoconfirmations-JSON-String (QSL-Eintrag + optional 6 weitere)."""
    qsl: dict = {"CT": "QSL", "S": "No", "R": r, "SV": "Electronic"}
    if include_rv:
        qsl["RV"] = rv
    entries = [qsl]
    if extra_entries:
        entries += [
            {"CT": "EQSL",    "S": "Yes", "R": "No",  "SV": "Electronic", "RV": "Electronic",
             "SD": "2023-03-26T00:00:00Z"},
            {"CT": "LOTW",    "S": "Yes", "R": "Yes", "SV": "Electronic", "RV": "Electronic",
             "SD": "2023-03-04T00:00:00Z", "RD": "2023-03-19T00:00:00Z"},
            {"CT": "QRZCOM",  "S": "Yes", "R": "Yes", "SV": "Electronic", "RV": "Electronic",
             "RD": "2023-10-13T00:00:00Z"},
            {"CT": "HAMQTH",  "S": "No",  "R": "No",  "SV": "Electronic", "RV": "Electronic"},
            {"CT": "HRDLOG",  "S": "No",  "R": "No",  "SV": "Electronic", "RV": "Electronic"},
            {"CT": "CLUBLOG", "S": "No",  "R": "No",  "SV": "Electronic", "RV": "Electronic"},
        ]
    return json.dumps(entries, ensure_ascii=False, separators=(",", ":"))


def _qsl(json_str: str) -> dict:
    """Extrahiert den QSL-Eintrag aus einem qsoconfirmations-JSON-String."""
    return next(e for e in json.loads(json_str) if e.get("CT") == "QSL")


def _non_qsl(json_str: str) -> list:
    """Gibt alle Nicht-QSL-Einträge zurück."""
    return [e for e in json.loads(json_str) if e.get("CT") != "QSL"]


# ---------------------------------------------------------------------------
# Korrekte Route-Ergebnisse
# ---------------------------------------------------------------------------

def test_bureau_sets_r_yes():
    result = apply_paper_qsl(_make_confirmations(), "bureau")
    assert _qsl(result)["R"] == "Yes"


def test_bureau_sets_rv_bureau():
    result = apply_paper_qsl(_make_confirmations(), "bureau")
    assert _qsl(result)["RV"] == "Bureau"


def test_direct_sets_r_yes():
    result = apply_paper_qsl(_make_confirmations(), "direct")
    assert _qsl(result)["R"] == "Yes"


def test_direct_sets_rv_direct():
    result = apply_paper_qsl(_make_confirmations(), "direct")
    assert _qsl(result)["RV"] == "Direct"


def test_undefined_sets_r_yes():
    result = apply_paper_qsl(_make_confirmations(), "undefined")
    assert _qsl(result)["R"] == "Yes"


def test_undefined_removes_rv_key():
    """Bei undefined wird der RV-Schlüssel vollständig entfernt (nicht 'Undefined' geschrieben)."""
    result = apply_paper_qsl(_make_confirmations(), "undefined")
    assert "RV" not in _qsl(result)


def test_undefined_removes_rv_when_already_present():
    """RV='Electronic' im QSL-Eintrag wird bei undefined entfernt."""
    result = apply_paper_qsl(_make_confirmations(rv="Electronic"), "undefined")
    assert "RV" not in _qsl(result)


def test_bureau_overwrites_existing_rv():
    """RV='Electronic' im QSL-Eintrag wird bei bureau mit 'Bureau' überschrieben."""
    result = apply_paper_qsl(_make_confirmations(rv="Electronic"), "bureau")
    assert _qsl(result)["RV"] == "Bureau"


def test_direct_overwrites_existing_rv():
    """RV='Electronic' im QSL-Eintrag wird bei direct mit 'Direct' überschrieben."""
    result = apply_paper_qsl(_make_confirmations(rv="Electronic"), "direct")
    assert _qsl(result)["RV"] == "Direct"


# ---------------------------------------------------------------------------
# Kein RD geschrieben
# ---------------------------------------------------------------------------

def test_no_rd_written_bureau():
    result = apply_paper_qsl(_make_confirmations(), "bureau")
    assert "RD" not in _qsl(result)


def test_no_rd_written_direct():
    result = apply_paper_qsl(_make_confirmations(), "direct")
    assert "RD" not in _qsl(result)


def test_no_rd_written_undefined():
    result = apply_paper_qsl(_make_confirmations(), "undefined")
    assert "RD" not in _qsl(result)


# ---------------------------------------------------------------------------
# S/CT/SV im QSL-Eintrag unverändert
# ---------------------------------------------------------------------------

def test_qsl_s_unchanged():
    result = apply_paper_qsl(_make_confirmations(), "bureau")
    assert _qsl(result)["S"] == "No"


def test_qsl_ct_unchanged():
    result = apply_paper_qsl(_make_confirmations(), "bureau")
    assert _qsl(result)["CT"] == "QSL"


def test_qsl_sv_unchanged():
    result = apply_paper_qsl(_make_confirmations(), "bureau")
    assert _qsl(result)["SV"] == "Electronic"


# ---------------------------------------------------------------------------
# Alle anderen Bestätigungstypen unberührt
# ---------------------------------------------------------------------------

def test_other_entries_unchanged_bureau():
    original = _make_confirmations()
    result = apply_paper_qsl(original, "bureau")
    assert _non_qsl(result) == _non_qsl(original)


def test_other_entries_unchanged_direct():
    original = _make_confirmations()
    result = apply_paper_qsl(original, "direct")
    assert _non_qsl(result) == _non_qsl(original)


def test_other_entries_unchanged_undefined():
    original = _make_confirmations()
    result = apply_paper_qsl(original, "undefined")
    assert _non_qsl(result) == _non_qsl(original)


def test_entry_order_preserved():
    """Reihenfolge der Array-Einträge bleibt erhalten."""
    original = _make_confirmations()
    result = apply_paper_qsl(original, "bureau")
    orig_cts = [e["CT"] for e in json.loads(original)]
    result_cts = [e["CT"] for e in json.loads(result)]
    assert orig_cts == result_cts


def test_lotw_rd_untouched():
    """LOTW-RD-Datum bleibt exakt erhalten."""
    result = apply_paper_qsl(_make_confirmations(), "bureau")
    lotw = next(e for e in json.loads(result) if e["CT"] == "LOTW")
    assert lotw["RD"] == "2023-03-19T00:00:00Z"


def test_eqsl_sd_untouched():
    """EQSL-SD-Datum bleibt exakt erhalten."""
    result = apply_paper_qsl(_make_confirmations(), "bureau")
    eqsl = next(e for e in json.loads(result) if e["CT"] == "EQSL")
    assert eqsl["SD"] == "2023-03-26T00:00:00Z"


# ---------------------------------------------------------------------------
# RV fehlt bereits im QSL-Eintrag (z. B. älteres Log4OM-Format)
# ---------------------------------------------------------------------------

def test_undefined_no_rv_key_still_works():
    """Wenn RV schon fehlt: undefined funktioniert problemlos."""
    json_str = _make_confirmations(include_rv=False)
    result = apply_paper_qsl(json_str, "undefined")
    assert _qsl(result)["R"] == "Yes"
    assert "RV" not in _qsl(result)


def test_bureau_adds_rv_when_missing():
    """Wenn RV fehlt: bureau fügt RV='Bureau' hinzu."""
    json_str = _make_confirmations(include_rv=False)
    result = apply_paper_qsl(json_str, "bureau")
    assert _qsl(result)["RV"] == "Bureau"


# ---------------------------------------------------------------------------
# Idempotenz bei bereits R="Yes"
# ---------------------------------------------------------------------------

def test_idempotent_already_yes_bureau():
    """R='Yes' + route='bureau' → R bleibt 'Yes', RV='Bureau' gesetzt."""
    first = apply_paper_qsl(_make_confirmations(), "bureau")
    second = apply_paper_qsl(first, "bureau")
    assert _qsl(second)["R"] == "Yes"
    assert _qsl(second)["RV"] == "Bureau"


def test_idempotent_already_yes_undefined():
    """R='Yes' + route='undefined' → R bleibt 'Yes', RV entfernt."""
    first = apply_paper_qsl(_make_confirmations(), "bureau")
    second = apply_paper_qsl(first, "undefined")
    assert _qsl(second)["R"] == "Yes"
    assert "RV" not in _qsl(second)


def test_idempotent_rv_switch_bureau_to_direct():
    """Route-Wechsel bureau→direct: RV wird überschrieben."""
    first = apply_paper_qsl(_make_confirmations(), "bureau")
    second = apply_paper_qsl(first, "direct")
    assert _qsl(second)["RV"] == "Direct"


def test_idempotent_result_is_stable():
    """Zweimalige Anwendung mit gleicher route liefert dasselbe JSON."""
    original = _make_confirmations()
    first = apply_paper_qsl(original, "direct")
    second = apply_paper_qsl(first, "direct")
    assert first == second


# ---------------------------------------------------------------------------
# Fehlerfälle
# ---------------------------------------------------------------------------

def test_invalid_route_raises():
    with pytest.raises(InvalidRouteError):
        apply_paper_qsl(_make_confirmations(), "electronic")


def test_invalid_route_empty_string():
    with pytest.raises(InvalidRouteError):
        apply_paper_qsl(_make_confirmations(), "")


def test_invalid_route_uppercase_bureau():
    """Route-Werte sind lowercase; 'Bureau' (Großbuchstabe) ist ungültig."""
    with pytest.raises(InvalidRouteError):
        apply_paper_qsl(_make_confirmations(), "Bureau")


def test_invalid_json_raises():
    with pytest.raises(ValueError):
        apply_paper_qsl("no json here", "bureau")


def test_empty_json_raises():
    with pytest.raises(ValueError):
        apply_paper_qsl("", "bureau")


def test_missing_qsl_entry_raises():
    """Array ohne CT='QSL'-Eintrag → QslEntryNotFoundError."""
    no_qsl = json.dumps([
        {"CT": "EQSL",  "S": "No", "R": "No", "SV": "Electronic", "RV": "Electronic"},
        {"CT": "LOTW",  "S": "No", "R": "No", "SV": "Electronic", "RV": "Electronic"},
    ], separators=(",", ":"))
    with pytest.raises(QslEntryNotFoundError):
        apply_paper_qsl(no_qsl, "bureau")


def test_empty_array_raises():
    with pytest.raises(QslEntryNotFoundError):
        apply_paper_qsl("[]", "bureau")


def test_invalid_route_checked_before_json_parse():
    """route-Validierung findet vor JSON-Parse statt → InvalidRouteError, nicht ValueError."""
    with pytest.raises(InvalidRouteError):
        apply_paper_qsl("broken json {{{", "invalid_route")


# ---------------------------------------------------------------------------
# Ausgabeformat
# ---------------------------------------------------------------------------

def test_output_is_valid_json():
    result = apply_paper_qsl(_make_confirmations(), "bureau")
    parsed = json.loads(result)
    assert isinstance(parsed, list)


def test_output_compact_no_spaces():
    """JSON-Ausgabe ist kompakt (kein Leerzeichen nach ':' oder ',')."""
    result = apply_paper_qsl(_make_confirmations(), "bureau")
    assert ": " not in result
    assert ", " not in result


def test_minimal_qsl_only_entry():
    """Einzelner QSL-Eintrag (ohne die anderen 6) funktioniert korrekt."""
    single = json.dumps(
        [{"CT": "QSL", "S": "No", "R": "No", "SV": "Electronic", "RV": "Electronic"}],
        separators=(",", ":"),
    )
    result = apply_paper_qsl(single, "bureau")
    parsed = json.loads(result)
    assert len(parsed) == 1
    assert parsed[0]["R"] == "Yes"
    assert parsed[0]["RV"] == "Bureau"
