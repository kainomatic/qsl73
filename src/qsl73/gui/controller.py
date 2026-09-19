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
from qsl73.gui.error_messages import classify_error
from qsl73.input_tag_cleanup import (
    CleanupResult,
    count_input_tag_leftovers,
    remove_input_tag_from_leftovers,
)
from qsl73.log4om_db import WriteResult
from qsl73.paperless import PaperlessClient
from qsl73.run import RunResult, run_pass, write_selected
from qsl73.updater import UpdateCheckResult, check_for_update


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
class UpdateCheckDoneEvent:
    """Ergebnis einer Update-Prüfung (ADR-0063) — manual: automatisch vs. manuell ausgelöst."""
    result: UpdateCheckResult
    manual: bool = False


@dataclass
class InputTagCleanupCheckDoneEvent:
    """Ergebnis der Alt-Bestand-Zählung (Issue #41) — manual: Menü vs. automatischer Start-Check."""
    count: int
    error: bool = False
    manual: bool = False


@dataclass
class InputTagCleanupRunDoneEvent:
    """Ergebnis eines Aufräumlaufs (Issue #41). error gesetzt → result ist None."""
    result: Optional[CleanupResult]
    error: Optional[Exception] = None


@dataclass
class ErrorEvent:
    exc: Exception
    traceback_str: str
    user_message: str | None = None
    error_title: str = "Fehler"
    status_message: str | None = None
    is_expected: bool = False


class RunController:
    """Startet Hintergrund-Threads; legt Ergebnis-Events in eine Queue."""

    def __init__(self, event_queue: queue.Queue) -> None:
        self._queue = event_queue
        self._run_result: Optional[RunResult] = None
        self._cancel_event: Optional[threading.Event] = None  # ADR-0053

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
        cancel_event = threading.Event()
        self._cancel_event = cancel_event

        def _work() -> None:
            try:
                def on_progress(done: int, total: int, msg: str) -> None:
                    self._queue.put(ProgressEvent(done, total, msg))

                result = run_pass(
                    paperless_client, db_path, config,
                    on_progress=on_progress,
                    cancel_event=cancel_event,
                )
                self._run_result = result
                self._queue.put(RunDoneEvent(result))
            except Exception as exc:
                c = classify_error(exc)
                self._queue.put(ErrorEvent(
                    exc=exc,
                    traceback_str=tb.format_exc(),
                    user_message=c.user_message,
                    error_title=c.title,
                    status_message=c.status_message,
                    is_expected=c.is_expected,
                ))

        threading.Thread(target=_work, daemon=True).start()

    def start_update_check(
        self,
        current_version: str,
        channel: str,
        *,
        manual: bool = False,
    ) -> None:
        """Startet check_for_update im Daemon-Thread. Ergebnis → Queue (ADR-0063).

        Kein direkter tk-Zugriff aus dem Thread: das Ergebnis läuft über dieselbe
        Event-Queue wie ProgressEvent/RunDoneEvent/WriteDoneEvent/ErrorEvent, die
        MainWindow ohnehin per root.after(100, self._poll) abholt.
        """
        def _work() -> None:
            result = check_for_update(current_version, channel)
            self._queue.put(UpdateCheckDoneEvent(result=result, manual=manual))

        threading.Thread(target=_work, daemon=True).start()

    def start_input_tag_cleanup_check(
        self,
        paperless_client: PaperlessClient,
        tags_config: TagsConfig,
        *,
        manual: bool = False,
    ) -> None:
        """Zählt Alt-Bestand-Karten im Daemon-Thread. Ergebnis → Queue (Issue #41).

        Kein direkter tk-Zugriff aus dem Thread — folgt demselben Queue-Polling-Muster
        wie start_update_check (ADR-0023/ADR-0063). Netzwerkfehler führen zu
        error=True statt einer geworfenen Exception in der Queue.
        """
        def _work() -> None:
            try:
                n = count_input_tag_leftovers(paperless_client, tags_config)
                self._queue.put(
                    InputTagCleanupCheckDoneEvent(count=n, error=False, manual=manual)
                )
            except Exception:
                self._queue.put(
                    InputTagCleanupCheckDoneEvent(count=0, error=True, manual=manual)
                )

        threading.Thread(target=_work, daemon=True).start()

    def start_input_tag_cleanup_run(
        self,
        paperless_client: PaperlessClient,
        tags_config: TagsConfig,
        log_dir: Path,
    ) -> None:
        """Führt das Alt-Bestand-Aufräumen im Daemon-Thread aus. Ergebnis → Queue (Issue #41)."""
        def _work() -> None:
            try:
                result = remove_input_tag_from_leftovers(paperless_client, tags_config, log_dir)
                self._queue.put(InputTagCleanupRunDoneEvent(result=result, error=None))
            except Exception as exc:
                self._queue.put(InputTagCleanupRunDoneEvent(result=None, error=exc))

        threading.Thread(target=_work, daemon=True).start()

    def cancel_run(self) -> None:
        """Setzt das Abbruch-Flag für den laufenden Durchlauf.

        Threadsicher und idempotent. Aufruf ohne laufenden Lauf ist ein no-op (ADR-0053).
        """
        if self._cancel_event is not None:
            self._cancel_event.set()

    def start_write(
        self,
        selections: list[tuple[str, str]],
        db_path: Path,
        backup_dir: Path,
        backup_count: int,
        paperless_client: Optional[PaperlessClient],
        confirmed_doc_ids: list[int],
        tags_config: Optional[TagsConfig],
        manual_qsoids: Optional[set[str]] = None,   # NEU: für Audit-Logging
        candidates: Optional[list] = None,            # NEU: list[QsoCandidate], kein Import nötig
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
                    manual_qsoids=manual_qsoids,   # NEU
                    candidates=candidates,          # NEU
                )
                self._queue.put(WriteDoneEvent(result, confirmed_doc_ids, tag_warnings, selections))
            except Exception as exc:
                c = classify_error(exc)
                self._queue.put(ErrorEvent(
                    exc=exc,
                    traceback_str=tb.format_exc(),
                    user_message=c.user_message,
                    error_title=c.title,
                    status_message=c.status_message,
                    is_expected=c.is_expected,
                ))

        threading.Thread(target=_work, daemon=True).start()
