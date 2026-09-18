# QSL73 — Copyright (C) 2026 DF1DS (kainomatic) — SPDX-License-Identifier: GPL-3.0-or-later
"""Tests für gui/manual_assignment.py — CI-kompatibel.

Aufbau:
  1. Reine Helfer (kein tk nötig): card_fields_to_query, field_values_to_query,
     render_pdf_first_page — laufen immer.
  2. tk-abhängige Tests: ManualAssignmentDialog — werden im CI übersprungen
     (kein Display vorhanden).
"""
from __future__ import annotations

import pytest

from qsl73.gui.manual_assignment import (
    card_fields_to_query,
    dialog_buttons_state,
    distinct_bands,
    distinct_modes,
    field_values_to_query,
    format_ignore_tag_missing_message,
    ignore_button_label,
    ignore_button_tooltip,
    ignore_toggle_target,
    last_page_index,
    render_pdf_first_page,
    render_pdf_pages,
    save_buttons_enabled,
    wrap_page_index,
)
from qsl73.gui.filter_util import apply_display_limit
from qsl73.matching import CardFields, QsoCandidate


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------


def _make_card_fields(
    call_from=None, call_to=None, date=None, band=None, mode=None, time_utc=None
) -> CardFields:
    return CardFields(
        call_from=call_from,
        call_to=call_to,
        date=date,
        band=band,
        mode=mode,
        time_utc=time_utc,
    )


def _make_cand(
    qsoid: str,
    callsign: str = "DK1AA",
    date: str = "2025-01-10",
    band: str = "20m",
    mode: str = "SSB",
) -> QsoCandidate:
    return QsoCandidate(
        qsoid=qsoid,
        callsign=callsign,
        date=date,
        band=band,
        mode=mode,
    )


def _tk_available() -> bool:
    try:
        import tkinter as tk
        root = tk.Tk()
        root.destroy()
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# 1. Reine Helfer — card_fields_to_query
# ---------------------------------------------------------------------------


def test_card_fields_to_query_fills_all():
    cf = _make_card_fields(call_from="DK1AA", date="2025-03-15", band="20m", mode="SSB")
    q = card_fields_to_query(cf)
    assert q.call == "DK1AA"
    assert q.date == "2025-03-15"
    assert q.band == "20m"
    assert q.mode == "SSB"


def test_card_fields_to_query_none_stays_none():
    cf = _make_card_fields()  # alle Felder None
    q = card_fields_to_query(cf)
    assert q.call is None
    assert q.date is None
    assert q.band is None
    assert q.mode is None


def test_card_fields_to_query_partial():
    cf = _make_card_fields(call_from="OE3XYZ", band="40m")
    q = card_fields_to_query(cf)
    assert q.call == "OE3XYZ"
    assert q.band == "40m"
    assert q.date is None
    assert q.mode is None


def test_card_fields_to_query_uses_call_from_not_call_to():
    """call_from = Absender der Karte; call_to = eigenes Rufzeichen (Empfänger)."""
    cf = _make_card_fields(call_from="DL5ABC", call_to="DF1DS")
    q = card_fields_to_query(cf)
    assert q.call == "DL5ABC"


def test_card_fields_to_query_empty_string_becomes_none():
    cf = _make_card_fields(call_from="", date="", band="", mode="")
    q = card_fields_to_query(cf)
    assert q.call is None
    assert q.date is None
    assert q.band is None
    assert q.mode is None


# ---------------------------------------------------------------------------
# 1b. card_fields_to_query mit outcome — Vorbefüllung aus Engine-Treffer
# (Beta4-Befund: mehrere Fremdcall-Kandidaten, ein exakter DB-Treffer)
# ---------------------------------------------------------------------------


def test_prefill_uses_call_from_when_set():
    """(a) card_fields.call_from gesetzt → dieses gewinnt, outcome wird ignoriert."""
    from qsl73.matching import MatchOutcome, MatchReason, MatchReasonCode, MatchResult, QsoCandidate

    cf = _make_card_fields(call_from="DK1AA", mode="FT8")
    cand = QsoCandidate(qsoid="q1", callsign="DL1AAA", date="2025-04-02", band="6m", mode="FT8")
    reason = MatchReason(MatchReasonCode.TOO_FEW_FIELDS, "…", {"call": "DL1AAA"})
    outcome = MatchOutcome(result=MatchResult.UNCERTAIN, matched_qso=None, candidates=[cand], reason=reason)
    q = card_fields_to_query(cf, outcome)
    assert q.call == "DK1AA"


def test_prefill_uses_engine_hit_too_few_fields():
    """(b) call_from=None, genau EIN Treffer (TOO_FEW_FIELDS) → Treffer-Call vorbefüllt."""
    from qsl73.matching import MatchOutcome, MatchReason, MatchReasonCode, MatchResult, QsoCandidate

    cf = _make_card_fields(call_from=None, mode="FT8")
    cand = QsoCandidate(qsoid="q1", callsign="DL1AAA", date="2025-04-02", band="6m", mode="FT8")
    reason = MatchReason(MatchReasonCode.TOO_FEW_FIELDS, "…", {"call": "DL1AAA", "missing": ["Datum", "Band"]})
    outcome = MatchOutcome(result=MatchResult.UNCERTAIN, matched_qso=None, candidates=[cand], reason=reason)
    q = card_fields_to_query(cf, outcome)
    assert q.call == "DL1AAA"


def test_prefill_uses_engine_hit_fuzzy_call():
    """(b) genau EIN fuzzy Treffer (FUZZY_CALL) → gelesenes Karten-Rufzeichen vorbefüllt."""
    from qsl73.matching import MatchOutcome, MatchReason, MatchReasonCode, MatchResult, QsoCandidate

    cf = _make_card_fields(call_from=None)
    cand = QsoCandidate(qsoid="q1", callsign="DK8XX", date="2025-04-02", band="6m", mode="FT8")
    reason = MatchReason(MatchReasonCode.FUZZY_CALL, "…", {"read": "DK3XX", "matched": "DK8XX"})
    outcome = MatchOutcome(result=MatchResult.UNCERTAIN, matched_qso=None, candidates=[cand], reason=reason)
    q = card_fields_to_query(cf, outcome)
    assert q.call == "DK3XX"


def test_prefill_empty_on_multi_qso():
    """(c) mehrere getroffene QSOs (MULTI_QSO) → kein Raten, Rufzeichen bleibt leer."""
    from qsl73.matching import MatchOutcome, MatchReason, MatchReasonCode, MatchResult, QsoCandidate

    cf = _make_card_fields(call_from=None)
    cand1 = QsoCandidate(qsoid="q1", callsign="DL1AAA", date="2025-04-02", band="6m", mode="FT8")
    cand2 = QsoCandidate(qsoid="q2", callsign="DL2BBB", date="2025-04-02", band="6m", mode="FT8")
    reason = MatchReason(MatchReasonCode.MULTI_QSO, "…", {"calls": ["DL1AAA", "DL2BBB"]})
    outcome = MatchOutcome(
        result=MatchResult.UNCERTAIN, matched_qso=None, candidates=[cand1, cand2], reason=reason
    )
    q = card_fields_to_query(cf, outcome)
    assert q.call is None


def test_prefill_certain_unchanged():
    """(d) CERTAIN (reason=None) → unverändertes Verhalten, kein Absturz."""
    from qsl73.matching import MatchOutcome, MatchResult, QsoCandidate

    cf = _make_card_fields(call_from=None)
    cand = QsoCandidate(qsoid="q1", callsign="DL0AAA", date="2025-04-02", band="6m", mode="FT8")
    outcome = MatchOutcome(result=MatchResult.CERTAIN, matched_qso=cand, candidates=[cand], reason=None)
    q = card_fields_to_query(cf, outcome)
    assert q.call is None


def test_prefill_no_outcome_unchanged():
    """Ohne outcome (None, Default) → unverändertes Verhalten wie zuvor."""
    cf = _make_card_fields(call_from=None)
    q = card_fields_to_query(cf)
    assert q.call is None


# ---------------------------------------------------------------------------
# 2. Reine Helfer — field_values_to_query
# ---------------------------------------------------------------------------


def test_field_values_filled():
    q = field_values_to_query("DK1AA", "2025-01-10", "20m", "SSB")
    assert q.call == "DK1AA"
    assert q.date == "2025-01-10"
    assert q.band == "20m"
    assert q.mode == "SSB"


def test_field_values_empty_string_becomes_none():
    q = field_values_to_query("", "", "", "")
    assert q.call is None
    assert q.date is None
    assert q.band is None
    assert q.mode is None


def test_field_values_strips_whitespace():
    q = field_values_to_query("  DK1AA  ", "  ", "20m ", " SSB")
    assert q.call == "DK1AA"
    assert q.date is None     # nur Whitespace → None
    assert q.band == "20m"
    assert q.mode == "SSB"


def test_field_values_partial():
    q = field_values_to_query("OE3XYZ", "", "40m", "")
    assert q.call == "OE3XYZ"
    assert q.date is None
    assert q.band == "40m"
    assert q.mode is None


# ---------------------------------------------------------------------------
# 3. Reine Helfer — render_pdf_first_page / render_pdf_pages
# ---------------------------------------------------------------------------


def test_render_pdf_returns_none_on_empty_bytes():
    result = render_pdf_first_page(b"")
    assert result is None


def test_render_pdf_returns_none_on_garbage():
    result = render_pdf_first_page(b"not a pdf at all")
    assert result is None


def test_render_pdf_no_exception_on_error():
    """Kein Absturz bei defekten Daten — gibt None zurück."""
    result = render_pdf_first_page(b"\x00\x01\x02\x03")
    assert result is None


def test_render_pdf_pages_empty_bytes_returns_empty_list():
    """render_pdf_pages gibt leere Liste zurück bei leeren Bytes."""
    pages = render_pdf_pages(b"")
    assert pages == []


def test_render_pdf_pages_garbage_returns_empty_list():
    pages = render_pdf_pages(b"not a pdf at all")
    assert pages == []


def test_render_pdf_pages_no_exception_on_corrupt():
    """Kein Absturz bei defekten Bytes — gibt leere Liste zurück."""
    pages = render_pdf_pages(b"\x00\x01\x02\x03")
    assert isinstance(pages, list)
    assert pages == []


def test_render_pdf_first_page_delegates_to_pages():
    """render_pdf_first_page und render_pdf_pages müssen konsistent sein: None ↔ []."""
    result_first = render_pdf_first_page(b"garbage")
    pages = render_pdf_pages(b"garbage")
    assert result_first is None
    assert pages == []


# ---------------------------------------------------------------------------
# 3b. Reine Helfer — last_page_index
# ---------------------------------------------------------------------------


def test_last_page_index_zero():
    """Leerfall: 0 Seiten → Index 0 (kein Absturz)."""
    assert last_page_index(0) == 0


def test_last_page_index_one_page():
    """Einseitiges PDF → letzte Seite = Seite 0."""
    assert last_page_index(1) == 0


def test_last_page_index_two_pages():
    """Zweiseitiges PDF → letzte Seite = Index 1."""
    assert last_page_index(2) == 1


def test_last_page_index_multiple_pages():
    """Mehrseitiges PDF → letzter Index ist page_count - 1."""
    assert last_page_index(5) == 4


def test_last_page_index_never_negative():
    """Negative Seitenzahl → Index 0 (Schutz gegen Laufzeitfehler)."""
    assert last_page_index(-1) == 0


# ---------------------------------------------------------------------------
# 3d. Reine Helfer — wrap_page_index
# ---------------------------------------------------------------------------


def test_wrap_page_index_forward_normal():
    assert wrap_page_index(0, 3, +1) == 1


def test_wrap_page_index_backward_normal():
    assert wrap_page_index(2, 3, -1) == 1


def test_wrap_page_index_forward_wraps():
    """Letzte Seite → erste (Umlauf vorwärts)."""
    assert wrap_page_index(2, 3, +1) == 0


def test_wrap_page_index_backward_wraps():
    """Erste Seite → letzte (Umlauf rückwärts)."""
    assert wrap_page_index(0, 3, -1) == 2


def test_wrap_page_index_single_page_forward():
    """Einseitiges PDF — kein Umlauf, bleibt bei 0."""
    assert wrap_page_index(0, 1, +1) == 0


def test_wrap_page_index_single_page_backward():
    assert wrap_page_index(0, 1, -1) == 0


def test_wrap_page_index_zero_pages():
    """Leerfall — kein Absturz, gibt current zurück."""
    assert wrap_page_index(0, 0, +1) == 0


def test_wrap_page_index_two_pages_wrap():
    """Zweiseitiges PDF: letzte → erste und erste → letzte."""
    assert wrap_page_index(1, 2, +1) == 0
    assert wrap_page_index(0, 2, -1) == 1


# ---------------------------------------------------------------------------
# 3c. Reine Helfer — distinct_bands / distinct_modes
# ---------------------------------------------------------------------------


def test_distinct_bands_basic():
    """Eindeutige Bandwerte aus Kandidaten — korrekt dedup und sortiert."""
    cands = [
        _make_cand("Q1", band="40m"),
        _make_cand("Q2", band="20m"),
        _make_cand("Q3", band="40m"),  # Duplikat
    ]
    assert distinct_bands(cands) == ["20m", "40m"]


def test_distinct_bands_empty_candidates():
    assert distinct_bands([]) == []


def test_distinct_bands_none_values_skipped():
    """None-Bandwerte werden nicht in die Vorschlagsliste aufgenommen."""
    cands = [_make_cand("Q1", band="20m")]
    # Manuell None setzen
    cands[0] = QsoCandidate(
        qsoid="Q1", callsign="DK1AA", date="2025-01-01", band=None, mode="SSB"
    )
    result = distinct_bands(cands)
    assert result == []


def test_distinct_bands_sorted():
    """Ergebnis ist alphabetisch sortiert."""
    cands = [_make_cand(f"Q{i}", band=b) for i, b in enumerate(["80m", "2m", "10m"])]
    assert distinct_bands(cands) == ["10m", "2m", "80m"]


def test_distinct_modes_basic():
    cands = [
        _make_cand("Q1", mode="SSB"),
        _make_cand("Q2", mode="CW"),
        _make_cand("Q3", mode="SSB"),  # Duplikat
    ]
    assert distinct_modes(cands) == ["CW", "SSB"]


def test_distinct_modes_empty_candidates():
    assert distinct_modes([]) == []


def test_distinct_modes_sorted():
    cands = [_make_cand(f"Q{i}", mode=m) for i, m in enumerate(["SSB", "FT8", "CW"])]
    assert distinct_modes(cands) == ["CW", "FT8", "SSB"]


def test_distinct_modes_none_values_skipped():
    cands = [
        QsoCandidate(qsoid="Q1", callsign="DK1AA", date="2025-01-01", band="20m", mode=None)
    ]
    assert distinct_modes(cands) == []


# ---------------------------------------------------------------------------
# 4. Helfer-Integration: card_fields_to_query + field_values_to_query →
#    search_candidates liefert korrektes Ergebnis
# ---------------------------------------------------------------------------


def test_prefill_and_search_finds_matching_qso():
    """End-to-end ohne tk: Vorbefüllung → Query → Suche → Treffer."""
    from qsl73.gui.manual_match import search_candidates

    candidates = [
        _make_cand("Q001", "DK1AA", "2025-01-10", "20m", "SSB"),
        _make_cand("Q002", "OE3XYZ", "2025-03-15", "40m", "CW"),
    ]

    cf = _make_card_fields(call_from="DK1AA", band="20m")
    q = card_fields_to_query(cf)
    results = search_candidates(q, candidates)

    assert len(results) == 1
    assert results[0].qsoid == "Q001"


def test_user_correction_overrides_ocr():
    """Nutzer korrigiert Band — korrigierter Wert findet anderes QSO."""
    from qsl73.gui.manual_match import search_candidates

    candidates = [
        _make_cand("Q001", "DK1AA", "2025-01-10", "20m", "SSB"),
        _make_cand("Q002", "DK1AA", "2025-01-10", "40m", "SSB"),
    ]

    # OCR las "20m", Nutzer korrigiert zu "40m"
    q = field_values_to_query("DK1AA", "", "40m", "")
    results = search_candidates(q, candidates)

    assert len(results) == 1
    assert results[0].qsoid == "Q002"


def test_make_manual_selection_correct_pair():
    """make_manual_selection liefert (qsoid, route) — gemeinsamer Schreibpfad."""
    from qsl73.gui.manual_match import make_manual_selection

    pair = make_manual_selection("Q001", "bureau")
    assert pair == ("Q001", "bureau")


def test_make_manual_selection_invalid_route():
    from qsl73.gui.manual_match import make_manual_selection
    import pytest as _pytest

    with _pytest.raises(ValueError):
        make_manual_selection("Q001", "email")


def test_empty_candidates_list_returns_empty():
    """Suchraum = [] → keine Treffer — Sicherheitsmodell ADR-0028."""
    from qsl73.gui.manual_match import search_candidates
    from qsl73.gui.manual_assignment import ManualQuery

    q = field_values_to_query("DK1AA", "", "", "")
    results = search_candidates(q, [])
    assert results == []


# ---------------------------------------------------------------------------
# 5. tk-abhängige Tests — werden im CI übersprungen
# ---------------------------------------------------------------------------

_tk_skip = pytest.mark.skipif(
    not _tk_available(),
    reason="kein Display / tk nicht verfügbar (CI-Umgebung)",
)


def _make_card_result(doc_id: int = 1, result=None) -> "object":
    """Minimales CardResult-Objekt für Dialog-Tests."""
    from qsl73.matching import MatchOutcome, MatchResult
    from qsl73.run import CardResult

    if result is None:
        result = MatchResult.UNCERTAIN

    return CardResult(
        doc_id=doc_id,
        card_fields=_make_card_fields(call_from="DK1AA", band="20m"),
        source="ocr",
        outcome=MatchOutcome(result=result, matched_qso=None),
        existing_confirmations=[],
    )


def _find_toplevel(root: "tk.Tk") -> "tk.Toplevel | None":
    """Findet das erste Toplevel-Kind von root (den geöffneten Dialog)."""
    import tkinter as tk
    for w in root.winfo_children():
        if isinstance(w, tk.Toplevel):
            return w
    return None


@_tk_skip
def test_dialog_cancel_returns_none():
    """Abbrechen (_on_cancel) → result ist None."""
    import tkinter as tk
    from qsl73.gui.manual_assignment import ManualAssignmentDialog

    root = tk.Tk()
    root.withdraw()
    card = _make_card_result()
    candidates = [_make_cand("Q001")]

    # Callback feuert WÄHREND wait_window() — ruft _on_cancel auf dem Dialog auf
    def _cancel():
        dlg_win = _find_toplevel(root)
        if dlg_win is not None:
            dlg_win._on_cancel()

    root.after(80, _cancel)
    # __init__ blockiert in wait_window() bis _cancel den Dialog schließt
    dlg = ManualAssignmentDialog(root, card, candidates, "bureau")

    assert dlg.result is None
    root.destroy()


@_tk_skip
def test_dialog_ok_with_selection_returns_pair():
    """Zeile auswählen + Speichern (_on_save) → result ist (qsoid, route)."""
    import tkinter as tk
    from qsl73.gui.manual_assignment import ManualAssignmentDialog

    root = tk.Tk()
    root.withdraw()
    card = _make_card_result()
    candidates = [_make_cand("Q001", "DK1AA"), _make_cand("Q002", "OE3XYZ")]

    def _select_and_ok():
        dlg_win = _find_toplevel(root)
        if dlg_win is None:
            return
        items = dlg_win._tree.get_children()
        if items:
            dlg_win._tree.selection_set(items[0])
            dlg_win._on_save()

    root.after(80, _select_and_ok)
    dlg = ManualAssignmentDialog(root, card, candidates, "bureau")

    assert dlg.result is not None
    qsoid, route = dlg.result
    assert route == "bureau"
    assert qsoid in ("Q001", "Q002")
    root.destroy()


@_tk_skip
def test_dialog_ok_without_selection_is_noop():
    """Speichern ohne ausgewählte Zeile → result bleibt None, Dialog bleibt offen."""
    import tkinter as tk
    from qsl73.gui.manual_assignment import ManualAssignmentDialog

    root = tk.Tk()
    root.withdraw()
    card = _make_card_result()
    candidates = [_make_cand("Q001")]

    def _ok_then_cancel():
        dlg_win = _find_toplevel(root)
        if dlg_win is None:
            return
        # Kein Selection → _on_save ist No-op
        dlg_win._on_save()
        # Dialog noch offen → jetzt abbrechen
        dlg_win._on_cancel()

    root.after(80, _ok_then_cancel)
    dlg = ManualAssignmentDialog(root, card, candidates, "bureau")

    assert dlg.result is None
    root.destroy()


# ---------------------------------------------------------------------------
# Grund + gelesene Rohfelder (ADR-0058, Issue #37)
# ---------------------------------------------------------------------------


@_tk_skip
def test_dialog_shows_reason_and_read_fields_for_uncertain():
    """UNCERTAIN-Karte mit MatchReason → Grund- und Gelesen-Zeile zeigen den Text."""
    import tkinter as tk
    from qsl73.gui.manual_assignment import ManualAssignmentDialog
    from qsl73.matching import MatchOutcome, MatchReason, MatchReasonCode, MatchResult
    from qsl73.run import CardResult

    root = tk.Tk()
    root.withdraw()
    reason = MatchReason(MatchReasonCode.FUZZY_CALL, "Rufzeichen nur unscharf erkannt.")
    card = CardResult(
        doc_id=1,
        card_fields=_make_card_fields(call_from="DK1AA", band="20m"),
        source="ocr",
        outcome=MatchOutcome(result=MatchResult.UNCERTAIN, matched_qso=None, reason=reason),
        existing_confirmations=[],
    )

    captured: dict = {}

    def _capture_and_cancel():
        dlg_win = _find_toplevel(root)
        if dlg_win is not None:
            captured["reason"] = dlg_win._reason_label.cget("text") if dlg_win._reason_label else None
            captured["fields"] = dlg_win._fields_label.cget("text") if dlg_win._fields_label else None
            dlg_win._on_cancel()

    root.after(80, _capture_and_cancel)
    ManualAssignmentDialog(root, card, [], "bureau")

    assert captured.get("reason") is not None
    assert "Rufzeichen nur unscharf erkannt." in captured["reason"]
    assert captured.get("fields") is not None
    assert "DK1AA" in captured["fields"]
    root.destroy()


@_tk_skip
def test_dialog_hides_reason_block_for_certain():
    """CERTAIN-Karte (Dialog theoretisch geöffnet) → Grund-Block entfällt komplett."""
    import tkinter as tk
    from qsl73.gui.manual_assignment import ManualAssignmentDialog
    from qsl73.matching import MatchOutcome, MatchResult
    from qsl73.run import CardResult

    root = tk.Tk()
    root.withdraw()
    card = CardResult(
        doc_id=1,
        card_fields=_make_card_fields(call_from="DK1AA", band="20m"),
        source="ocr",
        outcome=MatchOutcome(result=MatchResult.CERTAIN, matched_qso=None, reason=None),
        existing_confirmations=[],
    )

    def _cancel():
        dlg_win = _find_toplevel(root)
        if dlg_win is not None:
            dlg_win._on_cancel()

    root.after(80, _cancel)
    dlg = ManualAssignmentDialog(root, card, [], "bureau")

    assert dlg._reason_label is None
    assert dlg._fields_label is None
    root.destroy()


@_tk_skip
def test_dialog_date_field_blank_when_no_date_read():
    """Kein gelesenes Datum (OCR/QR) → DateEntry zeigt NICHT das heutige Datum (Beta4-Befund)."""
    import tkinter as tk
    from qsl73.gui.manual_assignment import ManualAssignmentDialog

    root = tk.Tk()
    root.withdraw()
    card = _make_card_result()  # date=None per _make_card_fields-Default

    captured: dict = {}

    def _capture_and_cancel():
        dlg_win = _find_toplevel(root)
        if dlg_win is not None:
            captured["date_text"] = dlg_win._date_entry.get()
            captured["date_explicit"] = dlg_win._date_explicit
            dlg_win._on_cancel()

    root.after(80, _capture_and_cancel)
    ManualAssignmentDialog(root, card, [], "bureau")

    from datetime import date as _date
    today_str = _date.today().strftime("%Y-%m-%d")
    assert captured.get("date_text") == ""
    assert captured.get("date_text") != today_str
    assert captured.get("date_explicit") is False
    root.destroy()


@_tk_skip
def test_dialog_qr_overrides_engine_prefilled_fuzzy_call():
    """Beta4-Review: FUZZY_CALL-Vorbefüllung (verlesener Call) muss von einem
    späteren QR-Rufzeichen überschrieben werden können — vorher blockierte die
    Engine-Vorbefüllung die QR-Übernahme, weil _ocr_prefill_call nicht denselben
    Wert trug wie das tatsächlich angezeigte Feld."""
    import tkinter as tk
    from qsl73.gui.manual_assignment import ManualAssignmentDialog
    from qsl73.matching import CardFields, MatchOutcome, MatchReason, MatchReasonCode, MatchResult, QsoCandidate
    from qsl73.run import CardResult

    root = tk.Tk()
    root.withdraw()
    cand = QsoCandidate(qsoid="q1", callsign="DL1AAA", date="2025-04-02", band="6m", mode="FT8")
    reason = MatchReason(MatchReasonCode.FUZZY_CALL, "…", {"read": "DLIAAA", "matched": "DL1AAA"})
    card = CardResult(
        doc_id=1,
        card_fields=CardFields(call_from=None, call_to=None, date=None, band=None, mode=None),
        source="ocr",
        outcome=MatchOutcome(result=MatchResult.UNCERTAIN, matched_qso=None, candidates=[cand], reason=reason),
        existing_confirmations=[],
    )

    captured: dict = {}

    def _check_and_apply_qr():
        dlg_win = _find_toplevel(root)
        if dlg_win is None:
            return
        captured["before_qr"] = dlg_win._var_call.get()
        qr_fields = CardFields(call_from="DL1AAA", call_to=None, date=None, band=None, mode=None)
        dlg_win._apply_qr_prefill(qr_fields)
        captured["after_qr"] = dlg_win._var_call.get()
        dlg_win._on_cancel()

    root.after(80, _check_and_apply_qr)
    ManualAssignmentDialog(root, card, [cand], "bureau")

    assert captured.get("before_qr") == "DLIAAA"
    assert captured.get("after_qr") == "DL1AAA"
    root.destroy()


@_tk_skip
def test_dialog_qr_hint_visible_after_prefill_not_before():
    """QR-Hinweiszeile erscheint erst NACH tatsächlicher QR-Übernahme, nicht vorher."""
    import tkinter as tk
    from qsl73.gui.manual_assignment import ManualAssignmentDialog
    from qsl73.matching import CardFields, MatchOutcome, MatchResult
    from qsl73.run import CardResult

    root = tk.Tk()
    root.withdraw()
    card = CardResult(
        doc_id=1,
        card_fields=CardFields(call_from="DK1AA", call_to=None, date=None, band=None, mode=None),
        source="ocr",
        outcome=MatchOutcome(result=MatchResult.UNCERTAIN, matched_qso=None),
        existing_confirmations=[],
    )

    captured: dict = {}

    def _check_before_and_after_qr():
        dlg_win = _find_toplevel(root)
        if dlg_win is None:
            return
        captured["hint_before"] = bool(dlg_win._qr_hint_label.grid_info())
        qr_fields = CardFields(call_from="DK1AA", call_to=None, date=None, band="20m", mode=None)
        dlg_win._apply_qr_prefill(qr_fields)
        captured["hint_after"] = bool(dlg_win._qr_hint_label.grid_info())
        dlg_win._on_cancel()

    root.after(80, _check_before_and_after_qr)
    ManualAssignmentDialog(root, card, [], "bureau")

    assert captured.get("hint_before") is False
    assert captured.get("hint_after") is True
    root.destroy()


@_tk_skip
def test_dialog_qr_hint_absent_without_qr_prefill():
    """Ohne jegliche QR-Übernahme bleibt die Hinweiszeile dauerhaft ausgeblendet."""
    import tkinter as tk
    from qsl73.gui.manual_assignment import ManualAssignmentDialog

    root = tk.Tk()
    root.withdraw()
    card = _make_card_result()

    captured: dict = {}

    def _capture_and_cancel():
        dlg_win = _find_toplevel(root)
        if dlg_win is not None:
            captured["hint_visible"] = bool(dlg_win._qr_hint_label.grid_info())
            dlg_win._on_cancel()

    root.after(80, _capture_and_cancel)
    ManualAssignmentDialog(root, card, [], "bureau")

    assert captured.get("hint_visible") is False
    root.destroy()


@_tk_skip
def test_dialog_image_loader_failure_no_crash():
    """Fehler beim Bildladen → Platzhaltertext, kein Absturz."""
    import tkinter as tk
    from qsl73.gui.manual_assignment import ManualAssignmentDialog

    root = tk.Tk()
    root.withdraw()
    card = _make_card_result()
    candidates = [_make_cand("Q001")]

    def _bad_loader(doc_id: int) -> bytes:
        raise RuntimeError("Serververbindung fehlgeschlagen")

    # Dialog mit schlechtem Loader erstellen; lazy-Load feuert nach 50 ms
    # → dann _on_cancel nach 200 ms aufrufen (nach dem fehlgeschlagenen Bildladen)
    def _cancel():
        dlg_win = _find_toplevel(root)
        if dlg_win is not None:
            # Platzhaltertext prüfen bevor Schließen
            lbl = dlg_win._img_label.cget("text")
            assert "konnte nicht" in lbl or "Bild" in lbl
            dlg_win._on_cancel()

    root.after(200, _cancel)
    dlg = ManualAssignmentDialog(
        root, card, candidates, "bureau", image_loader=_bad_loader
    )
    assert dlg.result is None
    root.destroy()


# ---------------------------------------------------------------------------
# 3e. Reine Helfer — apply_display_limit
# ---------------------------------------------------------------------------


def _make_simple_cand(n: int) -> QsoCandidate:
    return QsoCandidate(qsoid=f"Q{n:03}", callsign="DK1AA", date="2025-01-01", band="20m", mode="SSB")


def test_apply_limit_restricts():
    """Limit > 0 und total > limit: gibt abgeschnittene Liste zurück."""
    cands = [_make_simple_cand(i) for i in range(10)]
    shown, total = apply_display_limit(cands, limit=3)
    assert total == 10
    assert len(shown) == 3


def test_apply_limit_zero_means_no_limit():
    """Limit=0 = kein Limit — alle Kandidaten werden angezeigt."""
    cands = [_make_simple_cand(i) for i in range(200)]
    shown, total = apply_display_limit(cands, limit=0)
    assert total == 200
    assert len(shown) == 200


def test_apply_limit_total_below_limit():
    """total < limit → alle angezeigt, total wird korrekt zurückgegeben."""
    cands = [_make_simple_cand(i) for i in range(5)]
    shown, total = apply_display_limit(cands, limit=100)
    assert total == 5
    assert len(shown) == 5


def test_apply_limit_exact_match():
    """total == limit → alle angezeigt (kein Hinweis nötig)."""
    cands = [_make_simple_cand(i) for i in range(10)]
    shown, total = apply_display_limit(cands, limit=10)
    assert total == 10
    assert len(shown) == 10


def test_apply_limit_empty_list():
    shown, total = apply_display_limit([], limit=100)
    assert shown == []
    assert total == 0


# ---------------------------------------------------------------------------
# 3f. Konstanten und Dialog-API (kein tk)
# ---------------------------------------------------------------------------


def test_module_action_constants_exist():
    """i18n-Konstanten und action-Werte als Strings vorhanden."""
    from qsl73.gui import manual_assignment as ma
    assert isinstance(ma._BTN_SAVE, str) and ma._BTN_SAVE
    assert isinstance(ma._BTN_SAVE_NEXT, str) and ma._BTN_SAVE_NEXT
    assert isinstance(ma._BTN_NEXT, str) and ma._BTN_NEXT
    assert isinstance(ma._BTN_CANCEL, str) and ma._BTN_CANCEL


def test_status_color_constants_exist():
    from qsl73.gui import manual_assignment as ma
    assert ma._COLOR_UNCERTAIN.startswith("#")
    assert ma._COLOR_NO_MATCH.startswith("#")


# ---------------------------------------------------------------------------
# QR-Vorbefüllung — reine Logik (kein tk)
# ---------------------------------------------------------------------------

from qsl73.gui.manual_assignment import compute_qr_prefill


def _make_qr_fields(call_from=None, band=None, mode=None, date=None) -> CardFields:
    return CardFields(call_from=call_from, call_to=None, date=date, band=band, mode=mode)


def test_compute_qr_prefill_overwrites_ocr_value():
    """QR liefert call; aktueller Wert == OCR-Wert → QR-Wert wird gesetzt."""
    qr = _make_qr_fields(call_from="DK8XX", band="6m", mode="FT8")
    result = compute_qr_prefill(
        qr,
        current_call="DL5ABC", current_band="40m", current_mode="CW",
        ocr_call="DL5ABC", ocr_band="40m", ocr_mode="CW",
        date_explicit=False,
    )
    assert result.get("call") == "DK8XX"
    assert result.get("band") == "6m"
    assert result.get("mode") == "FT8"


def test_compute_qr_prefill_no_overwrite_user_modified_call():
    """Nutzer hat call geändert (≠ OCR-Wert) → QR darf call NICHT überschreiben."""
    qr = _make_qr_fields(call_from="DK8XX")
    result = compute_qr_prefill(
        qr,
        current_call="OE6XXX",  # Nutzer hat diesen Wert manuell eingetragen
        current_band="", current_mode="",
        ocr_call="DL5ABC",      # OCR hatte diesen Wert
        ocr_band="", ocr_mode="",
        date_explicit=False,
    )
    assert "call" not in result  # kein Überschreiben


def test_compute_qr_prefill_overwrites_engine_prefilled_call():
    """Beta4-Review: war das Feld durch einen Engine-Treffer vorbefüllt (nicht
    direkt durch card_fields.call_from, ADR-0051 §4), muss ocr_call denselben
    Wert tragen wie current_call — sonst blockiert current_call != ocr_call die
    QR-Überschreibung fälschlich, obwohl der Nutzer nichts geändert hat."""
    qr = _make_qr_fields(call_from="DL1AAA")
    result = compute_qr_prefill(
        qr,
        current_call="DLIAAA",  # Engine-Vorbefüllung: verlesenes Rufzeichen (FUZZY_CALL)
        current_band="", current_mode="",
        ocr_call="DLIAAA",      # korrekt nachgezogen — identisch mit current_call
        ocr_band="", ocr_mode="",
        date_explicit=False,
    )
    assert result.get("call") == "DL1AAA"


def test_compute_qr_prefill_overwrites_empty_field():
    """OCR hatte keinen Wert (leer); QR hat einen → QR-Wert wird gesetzt."""
    qr = _make_qr_fields(call_from="DK8XX", band="20m")
    result = compute_qr_prefill(
        qr,
        current_call="", current_band="",  # Felder noch leer
        current_mode="",
        ocr_call="", ocr_band="", ocr_mode="",
        date_explicit=False,
    )
    assert result.get("call") == "DK8XX"
    assert result.get("band") == "20m"


def test_compute_qr_prefill_date_set_when_not_explicit():
    """QR hat Datum; date_explicit=False → Datum wird in result gesetzt."""
    qr = _make_qr_fields(date="2025-04-02")
    result = compute_qr_prefill(
        qr,
        current_call="", current_band="", current_mode="",
        ocr_call="", ocr_band="", ocr_mode="",
        date_explicit=False,
    )
    assert result.get("date") == "2025-04-02"


def test_compute_qr_prefill_date_not_set_when_explicit():
    """Nutzer hat Datum gesetzt (date_explicit=True) → QR überschreibt es nicht."""
    qr = _make_qr_fields(date="2025-04-02")
    result = compute_qr_prefill(
        qr,
        current_call="", current_band="", current_mode="",
        ocr_call="", ocr_band="", ocr_mode="",
        date_explicit=True,
    )
    assert "date" not in result


def test_compute_qr_prefill_empty_qr_returns_empty():
    """QR ohne gültige Felder → leeres result-Dict."""
    qr = _make_qr_fields()  # alle None
    result = compute_qr_prefill(
        qr,
        current_call="DL5ABC", current_band="40m", current_mode="CW",
        ocr_call="DL5ABC", ocr_band="40m", ocr_mode="CW",
        date_explicit=False,
    )
    assert result == {}


def test_compute_qr_prefill_date_overrides_ocr_date():
    """QR-Datum überschreibt OCR-gesetztes Datum (QR > OCR Priorität, ADR-0051)."""
    qr = _make_qr_fields(call_from="DK8XX", date="2024-05-01", band="40m", mode="SSB")
    result = compute_qr_prefill(
        qr,
        current_call="DK8XX", current_band="40m", current_mode="SSB",
        ocr_call="DK8XX", ocr_band="40m", ocr_mode="SSB",
        date_explicit=True,          # OCR hat Datum gesetzt → date_explicit=True
        current_date="2024-04-01",   # aktuell steht OCR-Datum drin
        ocr_date="2024-04-01",       # OCR hatte dieses Datum
    )
    assert result.get("date") == "2024-05-01", "QR-Datum muss OCR-Datum überschreiben"


def test_compute_qr_prefill_date_no_override_user_modified():
    """QR-Datum überschreibt NICHT wenn Nutzer das Datum manuell geändert hat."""
    qr = _make_qr_fields(call_from="DK8XX", date="2024-05-01", band="40m", mode="SSB")
    result = compute_qr_prefill(
        qr,
        current_call="DK8XX", current_band="40m", current_mode="SSB",
        ocr_call="DK8XX", ocr_band="40m", ocr_mode="SSB",
        date_explicit=True,
        current_date="2024-03-15",   # Nutzer hat anderes Datum getippt
        ocr_date="2024-04-01",       # OCR hatte etwas anderes → current ≠ ocr_date
    )
    assert "date" not in result, "Nutzer-Datum darf nicht überschrieben werden"


# ---------------------------------------------------------------------------
# Ignorieren — reine Helfer (ADR-0059, kein tk)
# ---------------------------------------------------------------------------


def test_ignore_toggle_target_flips_state():
    assert ignore_toggle_target(False) is True
    assert ignore_toggle_target(True) is False


def test_ignore_button_label_reflects_state():
    assert ignore_button_label(False) == "Ignorieren"
    assert ignore_button_label(True) == "Nicht mehr ignorieren"


def test_save_buttons_disabled_while_ignored_regardless_of_selection():
    assert save_buttons_enabled(ignored=True, has_selection=True, has_next=True) == (False, False)
    assert save_buttons_enabled(ignored=True, has_selection=False, has_next=False) == (False, False)


def test_save_buttons_enabled_when_not_ignored_and_selected():
    assert save_buttons_enabled(ignored=False, has_selection=True, has_next=True) == (True, True)


def test_save_next_disabled_without_next_card():
    assert save_buttons_enabled(ignored=False, has_selection=True, has_next=False) == (True, False)


def test_save_buttons_disabled_without_selection():
    assert save_buttons_enabled(ignored=False, has_selection=False, has_next=True) == (False, False)


def test_format_ignore_tag_missing_message_contains_tag_name_and_hint():
    msg = format_ignore_tag_missing_message("qsl-ignoriert")
    assert "qsl-ignoriert" in msg
    assert "Einstellungen" in msg


def test_format_ignore_tag_missing_message_empty_name_no_crash():
    msg = format_ignore_tag_missing_message("")
    assert "Einstellungen" in msg
    assert "''" not in msg


def test_ignore_button_tooltip_reflects_state():
    assert ignore_button_tooltip(False) != ignore_button_tooltip(True)
    assert "ignorier" in ignore_button_tooltip(False).lower()
    assert "entfernt" in ignore_button_tooltip(True).lower()


# ---------------------------------------------------------------------------
# dialog_buttons_state — reine Helfer (ADR-0059-Nachtrag, kein tk)
# ---------------------------------------------------------------------------


def test_dialog_buttons_state_in_flight_locks_all_four():
    states = dialog_buttons_state(in_flight=True, ignored=False, has_selection=True, has_next=True)
    assert states == {"save": False, "save_next": False, "next": False, "cancel": False}


def test_dialog_buttons_state_in_flight_locks_regardless_of_other_flags():
    states = dialog_buttons_state(in_flight=True, ignored=True, has_selection=False, has_next=False)
    assert states == {"save": False, "save_next": False, "next": False, "cancel": False}


def test_dialog_buttons_state_not_in_flight_ignored_locks_save_only():
    states = dialog_buttons_state(in_flight=False, ignored=True, has_selection=True, has_next=True)
    assert states["save"] is False
    assert states["save_next"] is False
    assert states["next"] is True   # Nächste bleibt unabhängig vom Ignoriert-Zustand
    assert states["cancel"] is True


def test_dialog_buttons_state_not_in_flight_not_ignored_with_selection():
    states = dialog_buttons_state(in_flight=False, ignored=False, has_selection=True, has_next=True)
    assert states == {"save": True, "save_next": True, "next": True, "cancel": True}


def test_dialog_buttons_state_not_in_flight_no_selection():
    states = dialog_buttons_state(in_flight=False, ignored=False, has_selection=False, has_next=True)
    assert states["save"] is False
    assert states["save_next"] is False
    assert states["next"] is True
    assert states["cancel"] is True


def test_dialog_buttons_state_no_next_card():
    states = dialog_buttons_state(in_flight=False, ignored=False, has_selection=True, has_next=False)
    assert states["save"] is True
    assert states["save_next"] is False
    assert states["next"] is False
    assert states["cancel"] is True


# ---------------------------------------------------------------------------
# Ignorieren — Dialog (tk, ADR-0059)
# ---------------------------------------------------------------------------


@_tk_skip
def test_ignore_button_absent_for_certain_card():
    """Button existiert nicht für CERTAIN-Karten (defensiv — Dialog öffnet sich dafür nie)."""
    import tkinter as tk
    from qsl73.matching import MatchResult
    from qsl73.gui.manual_assignment import ManualAssignmentDialog

    root = tk.Tk()
    root.withdraw()
    card = _make_card_result(result=MatchResult.CERTAIN)

    def _check_and_cancel():
        dlg_win = _find_toplevel(root)
        if dlg_win is not None:
            assert dlg_win._ignore_btn is None
            dlg_win._on_cancel()

    root.after(80, _check_and_cancel)
    ManualAssignmentDialog(root, card, [], "bureau")
    root.destroy()


@_tk_skip
def test_ignore_button_initial_label_already_ignored():
    """already_ignored=True → Button zeigt direkt 'Nicht mehr ignorieren'."""
    import tkinter as tk
    from qsl73.gui.manual_assignment import ManualAssignmentDialog

    root = tk.Tk()
    root.withdraw()
    card = _make_card_result()

    def _check_and_cancel():
        dlg_win = _find_toplevel(root)
        if dlg_win is not None:
            assert dlg_win._ignore_btn.cget("text") == "Nicht mehr ignorieren"
            assert dlg_win.ignored is True
            dlg_win._on_cancel()

    root.after(80, _check_and_cancel)
    dlg = ManualAssignmentDialog(root, card, [], "bureau", already_ignored=True)
    assert dlg.ignored is True
    root.destroy()


@_tk_skip
def test_ignore_button_click_success_locks_save_and_toggles_label(monkeypatch):
    """Klick → ignore_card wird aufgerufen, Label wechselt, Speichern gesperrt."""
    import tkinter as tk
    from unittest.mock import MagicMock
    from qsl73.gui.manual_assignment import ManualAssignmentDialog

    called = {}

    def _fake_ignore_card(client, doc_id, tags_config, log_dir, callsign=""):
        called["doc_id"] = doc_id
        called["callsign"] = callsign

    monkeypatch.setattr("qsl73.ignore.ignore_card", _fake_ignore_card)

    root = tk.Tk()
    root.withdraw()
    card = _make_card_result(doc_id=77)
    candidates = [_make_cand("Q001")]

    def _click_ignore():
        dlg_win = _find_toplevel(root)
        if dlg_win is not None:
            dlg_win._on_toggle_ignore()

    def _check_and_cancel():
        dlg_win = _find_toplevel(root)
        if dlg_win is not None:
            assert dlg_win.ignored is True
            assert dlg_win._ignore_btn.cget("text") == "Nicht mehr ignorieren"
            save_ok, save_next_ok = save_buttons_enabled(dlg_win.ignored, True, True)
            assert (save_ok, save_next_ok) == (False, False)
            assert str(dlg_win._btn_save.cget("state")) == "disabled"
            dlg_win._on_cancel()

    root.after(80, _click_ignore)
    root.after(500, _check_and_cancel)
    dlg = ManualAssignmentDialog(
        root, card, candidates, "bureau",
        paperless_client=MagicMock(), tags_config=MagicMock(),
    )
    assert dlg.ignored is True
    assert called["doc_id"] == 77
    root.destroy()


@_tk_skip
def test_ignore_button_click_missing_tag_shows_expected_error_no_traceback(monkeypatch):
    """Fehlender Ignoriert-Tag → Hinweis ohne Traceback-Dialog; Zustand unverändert."""
    import tkinter as tk
    from unittest.mock import MagicMock
    from qsl73.ignore import IgnoreTagMissingError
    from qsl73.gui.manual_assignment import ManualAssignmentDialog

    shown = {}

    def _fake_ignore_card(client, doc_id, tags_config, log_dir, callsign=""):
        raise IgnoreTagMissingError("qsl-ignoriert")

    def _fake_show_error(parent, title, message, detail=""):
        shown["title"] = title
        shown["message"] = message
        shown["detail"] = detail

    monkeypatch.setattr("qsl73.ignore.ignore_card", _fake_ignore_card)
    monkeypatch.setattr("qsl73.gui.manual_assignment.show_error", _fake_show_error)

    root = tk.Tk()
    root.withdraw()
    card = _make_card_result(doc_id=5)

    def _click_ignore():
        dlg_win = _find_toplevel(root)
        if dlg_win is not None:
            dlg_win._on_toggle_ignore()

    def _check_and_cancel():
        dlg_win = _find_toplevel(root)
        if dlg_win is not None:
            assert dlg_win.ignored is False  # Zustand unverändert
            dlg_win._on_cancel()

    root.after(80, _click_ignore)
    root.after(500, _check_and_cancel)
    dlg = ManualAssignmentDialog(
        root, card, [], "bureau",
        paperless_client=MagicMock(), tags_config=MagicMock(),
    )
    assert dlg.ignored is False
    assert "qsl-ignoriert" in shown["message"]
    assert shown["detail"] == ""  # kein Traceback
    root.destroy()


@_tk_skip
def test_ignore_button_click_without_client_is_noop():
    """Kein paperless_client konfiguriert → Klick ist ein no-op, kein Absturz."""
    import tkinter as tk
    from qsl73.gui.manual_assignment import ManualAssignmentDialog

    root = tk.Tk()
    root.withdraw()
    card = _make_card_result()

    def _click_and_cancel():
        dlg_win = _find_toplevel(root)
        if dlg_win is not None:
            dlg_win._on_toggle_ignore()  # kein paperless_client → no-op
            assert dlg_win.ignored is False
            dlg_win._on_cancel()

    root.after(80, _click_and_cancel)
    dlg = ManualAssignmentDialog(root, card, [], "bureau")
    assert dlg.ignored is False
    root.destroy()


@_tk_skip
def test_ignore_in_flight_locks_all_four_buttons_and_blocks_window_close():
    """Race-Schutz (ADR-0059-Nachtrag): während _in_flight sind alle vier
    Workflow-Buttons gesperrt und Fenster-X schließt den Dialog nicht; danach wird
    der korrekte Zustand wiederhergestellt.

    Treibt _in_flight direkt (statt über einen echten Hintergrund-Thread) — geprüft
    wird die Sperr-/Wiederherstellungslogik selbst (_refresh_button_states/
    _on_delete_window), nicht die Thread-Zeitsteuerung; die reale End-to-End-Kette
    inkl. Hintergrund-Thread ist bereits durch
    test_ignore_button_click_success_locks_save_and_toggles_label abgedeckt.
    """
    import tkinter as tk
    from qsl73.gui.manual_assignment import ManualAssignmentDialog

    root = tk.Tk()
    root.withdraw()
    captured: dict = {}
    try:
        card = _make_card_result(doc_id=9)
        candidates = [_make_cand("Q001")]

        def _drive_race_check():
            dlg_win = _find_toplevel(root)
            if dlg_win is None:
                return
            # Zustand simulieren, wie ihn _on_toggle_ignore setzt, bevor die Antwort da ist.
            dlg_win._in_flight = True
            dlg_win._refresh_button_states()

            captured["save_state"] = str(dlg_win._btn_save.cget("state"))
            captured["save_next_state"] = str(dlg_win._btn_save_next.cget("state"))
            captured["next_state"] = str(dlg_win._btn_next.cget("state"))
            captured["cancel_state"] = str(dlg_win._btn_cancel.cget("state"))

            dlg_win._on_delete_window()  # simuliert Fenster-X-Klick
            captured["still_open_after_x"] = bool(dlg_win.winfo_exists())

            # Antwort simulieren (wie _on_ignore_done es tun würde) und Zustand prüfen.
            dlg_win._in_flight = False
            dlg_win.ignored = True
            dlg_win._refresh_button_states()

            captured["restored_cancel_state"] = str(dlg_win._btn_cancel.cget("state"))
            captured["restored_next_state"] = str(dlg_win._btn_next.cget("state"))
            dlg_win._on_cancel()

        root.after(80, _drive_race_check)

        ManualAssignmentDialog(root, card, candidates, "bureau")
    finally:
        root.destroy()

    assert captured["save_state"] == "disabled"
    assert captured["save_next_state"] == "disabled"
    assert captured["next_state"] == "disabled"
    assert captured["cancel_state"] == "disabled"
    assert captured["still_open_after_x"] is True
    assert captured["restored_cancel_state"] == "normal"
    assert captured["restored_next_state"] == "disabled"  # has_next=False in diesem Test


@_tk_skip
def test_ignore_button_tooltip_updates_with_state(monkeypatch):
    """Tooltip-Text folgt dem Ignoriert-Zustand (ADR-0059-Nachtrag)."""
    import tkinter as tk
    from unittest.mock import MagicMock
    from qsl73.gui.manual_assignment import ManualAssignmentDialog, ignore_button_tooltip

    def _fake_ignore_card(client, doc_id, tags_config, log_dir, callsign=""):
        pass

    monkeypatch.setattr("qsl73.ignore.ignore_card", _fake_ignore_card)

    root = tk.Tk()
    root.withdraw()
    try:
        card = _make_card_result(doc_id=3)

        def _check_initial_tooltip():
            dlg_win = _find_toplevel(root)
            if dlg_win is not None:
                assert dlg_win._ignore_tooltip._text == ignore_button_tooltip(False)
                dlg_win._on_toggle_ignore()

        def _check_updated_tooltip_and_cancel():
            dlg_win = _find_toplevel(root)
            if dlg_win is not None:
                assert dlg_win.ignored is True
                assert dlg_win._ignore_tooltip._text == ignore_button_tooltip(True)
                dlg_win._on_cancel()

        root.after(80, _check_initial_tooltip)
        root.after(400, _check_updated_tooltip_and_cancel)

        dlg = ManualAssignmentDialog(
            root, card, [], "bureau",
            paperless_client=MagicMock(), tags_config=MagicMock(),
        )
        assert dlg.ignored is True
    finally:
        root.destroy()
