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
        def _fake_run(pc, db, cfg, on_progress=None):
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
