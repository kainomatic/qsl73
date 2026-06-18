# src/qsl73/gui/controller.py
# QSL73 — Copyright (C) 2026 DF1DS (kainomatic) — SPDX-License-Identifier: GPL-3.0-or-later
"""Controller — vermittelt zwischen GUI-Widgets und Businesslogik ohne tk-Abhängigkeit."""
from __future__ import annotations

import queue
import threading
import traceback as tb
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from qsl73.config import Config, TagsConfig
from qsl73.log4om_db import WriteResult
from qsl73.paperless import PaperlessClient
from qsl73.run import RunResult, run_pass, write_selected


@dataclass
class ProgressEvent:
    done: int
    total: int
    message: str


@dataclass
class RunDoneEvent:
    result: RunResult


@dataclass
class WriteDoneEvent:
    result: WriteResult
    confirmed_doc_ids: list
    tag_warnings: list[str]
    selections: list  # paarweise mit confirmed_doc_ids: [(qsoid, route), ...]


@dataclass
class ErrorEvent:
    exc: Exception
    traceback_str: str


class RunController:
    """Startet Hintergrund-Threads; legt Ergebnis-Events in eine Queue."""

    def __init__(self, event_queue: queue.Queue) -> None:
        self._queue = event_queue
        self._run_result: Optional[RunResult] = None

    @property
    def run_result(self) -> Optional[RunResult]:
        return self._run_result

    def start_run(
        self,
        paperless_client: PaperlessClient,
        db_path: Path,
        config: Config,
    ) -> None:
        """Startet run_pass im Daemon-Thread. Ergebnisse → Queue."""
        def _work() -> None:
            try:
                def on_progress(done: int, total: int, msg: str) -> None:
                    self._queue.put(ProgressEvent(done, total, msg))

                result = run_pass(
                    paperless_client, db_path, config, on_progress=on_progress
                )
                self._run_result = result
                self._queue.put(RunDoneEvent(result))
            except Exception as exc:
                self._queue.put(ErrorEvent(exc, tb.format_exc()))

        threading.Thread(target=_work, daemon=True).start()

    def start_write(
        self,
        selections: list[tuple[str, str]],
        db_path: Path,
        backup_dir: Path,
        backup_count: int,
        paperless_client: Optional[PaperlessClient],
        confirmed_doc_ids: list[int],
        tags_config: Optional[TagsConfig],
    ) -> None:
        """Startet write_selected im Daemon-Thread. Ergebnis → Queue."""
        if self._run_result is None:
            raise RuntimeError(
                "start_write() ohne vorheriges start_run() aufgerufen"
            )

        snapshot = self._run_result.fingerprint
        expected = self._run_result.expected_states

        def _work() -> None:
            try:
                result, tag_warnings = write_selected(
                    selections=selections,
                    db_path=db_path,
                    backup_dir=backup_dir,
                    snapshot_fingerprint=snapshot,
                    expected_states=expected,
                    backup_count=backup_count,
                    paperless_client=paperless_client,
                    confirmed_doc_ids=confirmed_doc_ids,
                    tags_config=tags_config,
                )
                self._queue.put(WriteDoneEvent(result, confirmed_doc_ids, tag_warnings, selections))
            except Exception as exc:
                self._queue.put(ErrorEvent(exc, tb.format_exc()))

        threading.Thread(target=_work, daemon=True).start()
