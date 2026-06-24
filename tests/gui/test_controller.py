"""Tests für RunController — kein tk erforderlich."""
import queue
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from qsl73.config import Config
from qsl73.gui.controller import (
    ErrorEvent,
    ProgressEvent,
    RunController,
    RunDoneEvent,
    WriteDoneEvent,
)
from qsl73.run import RunResult
from qsl73.log4om_db import WriteResult
from qsl73.matching import CardFields, MatchOutcome, MatchResult
from qsl73.run import CardResult, RunResult


def _make_run_result() -> RunResult:
    card = CardResult(
        doc_id=1,
        card_fields=CardFields(call_from="DK1AA", call_to="DF1DS",
                               date="2025-04-02", band="6m", mode="FT8"),
        source="qr",
        outcome=MatchOutcome(result=MatchResult.CERTAIN, matched_qso=MagicMock(qsoid="q1")),
        existing_confirmations=[],
    )
    return RunResult(
        certain=[card],
        uncertain=[],
        no_match=[],
        fingerprint={"data_version": 42},
        expected_states={"q1": "No"},
    )


def _drain(q: queue.Queue, timeout: float = 5.0) -> list:
    events = []
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            events.append(q.get(timeout=0.1))
            if isinstance(events[-1], (RunDoneEvent, WriteDoneEvent, ErrorEvent)):
                break
        except queue.Empty:
            continue
    return events


def test_start_run_produces_progress_and_done_events():
    q = queue.Queue()
    controller = RunController(q)
    mock_result = _make_run_result()

    with patch("qsl73.gui.controller.run_pass") as mock_run:
        def _fake_run(pc, db, cfg, on_progress=None, cancel_event=None):
            if on_progress:
                on_progress(0, 2, "Start")
                on_progress(1, 2, "Mitte")
                on_progress(2, 2, "Fertig")
            return mock_result

        mock_run.side_effect = _fake_run
        controller.start_run(MagicMock(), Path("/fake/db.sqlite"), Config())
        events = _drain(q)

    progress = [e for e in events if isinstance(e, ProgressEvent)]
    done = [e for e in events if isinstance(e, RunDoneEvent)]
    assert len(progress) == 3
    assert len(done) == 1
    assert done[0].result is mock_result
    assert controller.run_result is mock_result


def test_start_run_does_not_call_write_selected():
    q = queue.Queue()
    controller = RunController(q)

    with patch("qsl73.gui.controller.run_pass", return_value=_make_run_result()), \
         patch("qsl73.gui.controller.write_selected") as mock_write:
        controller.start_run(MagicMock(), Path("/fake/db.sqlite"), Config())
        _drain(q)
        mock_write.assert_not_called()


def test_start_run_error_produces_error_event():
    q = queue.Queue()
    controller = RunController(q)

    with patch("qsl73.gui.controller.run_pass", side_effect=RuntimeError("Testfehler")):
        controller.start_run(MagicMock(), Path("/fake/db.sqlite"), Config())
        events = _drain(q)

    error_events = [e for e in events if isinstance(e, ErrorEvent)]
    assert len(error_events) == 1
    assert "Testfehler" in error_events[0].traceback_str


def test_start_write_produces_done_event():
    q = queue.Queue()
    controller = RunController(q)
    controller._run_result = _make_run_result()

    mock_write_result = WriteResult(written=1, skipped=[])

    with patch("qsl73.gui.controller.write_selected", return_value=(mock_write_result, [])):
        controller.start_write(
            selections=[("q1", "undefined")],
            db_path=Path("/fake/db.sqlite"),
            backup_dir=Path("/fake/backups"),
            backup_count=5,
            paperless_client=None,
            confirmed_doc_ids=[1],
            tags_config=None,
        )
        events = _drain(q)

    done = [e for e in events if isinstance(e, WriteDoneEvent)]
    assert len(done) == 1
    assert done[0].result.written == 1
    assert done[0].tag_warnings == []
    assert done[0].selections == [("q1", "undefined")]


def test_start_write_without_run_result_raises():
    q = queue.Queue()
    controller = RunController(q)
    with pytest.raises(RuntimeError, match="start_write"):
        controller.start_write([], Path("/fake/db.sqlite"), Path("/fake"), 5, None, [], None)


def test_start_write_uses_run_result_fingerprint():
    q = queue.Queue()
    controller = RunController(q)
    controller._run_result = _make_run_result()

    with patch("qsl73.gui.controller.write_selected", return_value=(WriteResult(0, []), [])) as mock_ws:
        controller.start_write(
            selections=[("q1", "bureau")],
            db_path=Path("/fake/db.sqlite"),
            backup_dir=Path("/fake/backups"),
            backup_count=3,
            paperless_client=None,
            confirmed_doc_ids=[],
            tags_config=None,
        )
        _drain(q)

    call_kwargs = mock_ws.call_args.kwargs
    assert call_kwargs["snapshot_fingerprint"] == {"data_version": 42}
    assert call_kwargs["expected_states"] == {"q1": "No"}


def test_start_write_db_changed_produces_expected_error_event():
    """DatabaseChangedError im Schreibthread → is_expected=True, freundliche Meldung."""
    from qsl73.log4om_db import DatabaseChangedError

    q = queue.Queue()
    controller = RunController(q)
    controller._run_result = _make_run_result()

    with patch(
        "qsl73.gui.controller.write_selected",
        side_effect=DatabaseChangedError("DB hat sich geändert"),
    ):
        controller.start_write(
            selections=[("q1", "undefined")],
            db_path=Path("/fake/db.sqlite"),
            backup_dir=Path("/fake/backups"),
            backup_count=5,
            paperless_client=None,
            confirmed_doc_ids=[1],
            tags_config=None,
        )
        events = _drain(q)

    error_events = [e for e in events if isinstance(e, ErrorEvent)]
    assert len(error_events) == 1
    e = error_events[0]
    assert e.is_expected is True
    assert e.error_title == "Datenbank hat sich geändert"
    assert "Durchlauf" in (e.user_message or "")
    assert "nichts geschrieben" in (e.user_message or "")
    assert "neu starten" in (e.status_message or "")


def test_start_run_unexpected_error_is_not_expected():
    """Generische Exception → is_expected=False (Traceback-Anzeige bleibt)."""
    q = queue.Queue()
    controller = RunController(q)

    with patch("qsl73.gui.controller.run_pass", side_effect=RuntimeError("unbekannt")):
        controller.start_run(MagicMock(), Path("/fake/db.sqlite"), Config())
        events = _drain(q)

    error_events = [e for e in events if isinstance(e, ErrorEvent)]
    assert len(error_events) == 1
    e = error_events[0]
    assert e.is_expected is False
    assert e.error_title == "Unerwarteter Fehler"
    assert "unbekannt" in e.traceback_str


# ---------------------------------------------------------------------------
# Abbruch-Mechanik (ADR-0053)
# ---------------------------------------------------------------------------

def test_cancel_run_noop_without_active_run():
    """cancel_run() ohne aktiven Lauf ist ein no-op — kein Fehler."""
    q = queue.Queue()
    controller = RunController(q)
    assert controller._cancel_event is None
    controller.cancel_run()  # darf keinen Fehler werfen


def test_cancel_run_sets_event():
    """cancel_run() setzt das _cancel_event des laufenden Laufs (threadsicher)."""
    q = queue.Queue()
    controller = RunController(q)

    evt = threading.Event()
    controller._cancel_event = evt

    assert not evt.is_set()
    controller.cancel_run()
    assert evt.is_set()


def test_cancel_run_idempotent_multiple_calls():
    """cancel_run() mehrfach aufrufen → idempotent, kein Fehler."""
    q = queue.Queue()
    controller = RunController(q)

    evt = threading.Event()
    controller._cancel_event = evt

    controller.cancel_run()
    controller.cancel_run()  # zweiter Aufruf
    assert evt.is_set()  # immer noch gesetzt, kein Fehler


def test_start_run_passes_cancel_event_to_run_pass():
    """start_run() erzeugt ein threading.Event und übergibt es an run_pass (ADR-0053)."""
    q = queue.Queue()
    controller = RunController(q)
    captured: list = []

    def _fake_run(pc, db, cfg, on_progress=None, cancel_event=None):
        captured.append(cancel_event)
        return _make_run_result()

    with patch("qsl73.gui.controller.run_pass", side_effect=_fake_run):
        controller.start_run(MagicMock(), Path("/fake/db.sqlite"), Config())
        _drain(q)

    assert len(captured) == 1
    assert isinstance(captured[0], threading.Event)
    assert not captured[0].is_set()  # Nicht gesetzt vor dem Lauf


def test_start_run_cancel_event_stored_as_instance_variable():
    """Nach start_run ist _cancel_event auf dem Controller gesetzt."""
    q = queue.Queue()
    controller = RunController(q)

    with patch("qsl73.gui.controller.run_pass", return_value=_make_run_result()):
        controller.start_run(MagicMock(), Path("/fake/db.sqlite"), Config())
        _drain(q)

    # _cancel_event wurde gesetzt (auch wenn der Lauf schon abgeschlossen ist)
    assert controller._cancel_event is not None
    assert isinstance(controller._cancel_event, threading.Event)


def test_run_done_event_carries_cancelled_flag():
    """RunDoneEvent enthält das cancelled-Flag aus dem run_pass-Ergebnis."""
    q = queue.Queue()
    controller = RunController(q)

    cancelled_result = RunResult(
        certain=[], uncertain=[], no_match=[],
        fingerprint={}, expected_states={}, cancelled=True,
    )

    with patch("qsl73.gui.controller.run_pass", return_value=cancelled_result):
        controller.start_run(MagicMock(), Path("/fake/db.sqlite"), Config())
        events = _drain(q)

    done = [e for e in events if isinstance(e, RunDoneEvent)]
    assert len(done) == 1
    assert done[0].result.cancelled is True
