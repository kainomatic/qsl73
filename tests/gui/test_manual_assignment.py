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
    distinct_bands,
    distinct_modes,
    field_values_to_query,
    last_page_index,
    render_pdf_first_page,
    render_pdf_pages,
    wrap_page_index,
)
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


def _make_card_result(doc_id: int = 1) -> "object":
    """Minimales CardResult-Objekt für Dialog-Tests."""
    from qsl73.matching import MatchOutcome, MatchResult
    from qsl73.run import CardResult

    return CardResult(
        doc_id=doc_id,
        card_fields=_make_card_fields(call_from="DK1AA", band="20m"),
        source="ocr",
        outcome=MatchOutcome(result=MatchResult.UNCERTAIN, matched_qso=None),
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
    """Zeile auswählen + Übernehmen (_on_ok) → result ist (qsoid, route)."""
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
            dlg_win._on_ok()

    root.after(80, _select_and_ok)
    dlg = ManualAssignmentDialog(root, card, candidates, "bureau")

    assert dlg.result is not None
    qsoid, route = dlg.result
    assert route == "bureau"
    assert qsoid in ("Q001", "Q002")
    root.destroy()


@_tk_skip
def test_dialog_ok_without_selection_is_noop():
    """Übernehmen ohne ausgewählte Zeile → result bleibt None, Dialog bleibt offen."""
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
        # Kein Selection → _on_ok ist No-op
        dlg_win._on_ok()
        # Dialog noch offen → jetzt abbrechen
        dlg_win._on_cancel()

    root.after(80, _ok_then_cancel)
    dlg = ManualAssignmentDialog(root, card, candidates, "bureau")

    assert dlg.result is None
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
