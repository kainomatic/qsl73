# QSL73 — Copyright (C) 2026 DF1DS (kainomatic) — SPDX-License-Identifier: GPL-3.0-or-later
"""Hauptfenster mit Treeview, Filter, Lauf- und Schreib-Integration."""
from __future__ import annotations

import logging
import queue
from pathlib import Path
from typing import Optional

import tkinter as tk
from tkinter import messagebox, ttk

from qsl73.__version__ import CHANNEL, __version__
from qsl73.config import Config
from qsl73.matching import MatchResult
from qsl73.run import CardResult, RunResult
from qsl73.gui.controller import (
    ErrorEvent,
    ProgressEvent,
    RunController,
    RunDoneEvent,
    WriteDoneEvent,
)
from qsl73.gui.error_dialog import show_error
from qsl73.gui.filter_util import FILTER_MODES, build_write_selections, filter_results, is_batch_writable, merge_selections, qso_by_id, qso_display_values, sort_cards_written_last, written_doc_ids


_log = logging.getLogger("qsl73")


def _reset_progress(progress: ttk.Progressbar) -> None:
    """Hält indeterminate-Animation an und setzt Balken auf 0 zurück."""
    progress.stop()
    progress.configure(mode="determinate", value=0)


_RESULT_LABELS = {
    MatchResult.CERTAIN: "Sicher",
    MatchResult.UNCERTAIN: "Unsicher",
    MatchResult.NO_MATCH: "Kein Treffer",
}

_FILTER_LABELS = {
    "all": "Alle",
    "certain": "Sicher",
    "uncertain": "Unsicher",
    "no_match": "Kein Treffer",
}

_TREE_COLS = ("call", "date", "band", "mode", "source", "status")


class MainWindow(tk.Tk):
    """Hauptfenster der QSL73-Anwendung."""

    def __init__(self, config: Config) -> None:
        super().__init__()
        self._config = config
        self._event_queue: queue.Queue = queue.Queue()
        self._controller = RunController(self._event_queue)
        self._run_result: Optional[RunResult] = None
        self._selected: set[int] = set()      # doc_ids der selektierten CERTAIN-Karten
        self._displayed: list[CardResult] = []  # aktuell angezeigte Karten
        self._manual_pending: dict[int, tuple[str, str]] = {}  # doc_id → (qsoid, route)
        self._written: set[int] = set()       # doc_ids die in diesem Lauf bereits geschrieben wurden
        self._written_qso: dict[int, str] = {}  # doc_id → qsoid (manuell zugeordnet + geschrieben)
        self._paperless_client = None         # wird in _on_run gesetzt, für Bildladen im Dialog

        title = f"QSL73 v{__version__}"
        if CHANNEL == "beta":
            title += " [BETA]"
        self.title(title)
        self.minsize(750, 450)

        self._build_ui()
        self._poll()

        # QR-Startwarnung (Issue #14 / ADR-0026)
        from qsl73.qr import qr_backend_status
        qr_status = qr_backend_status()
        if not (qr_status["fitz"] and qr_status["zxing"]):
            self._status_var.set(
                "⚠ QR-Code-Auswertung nicht verfügbar "
                "(zxing-cpp/pymupdf fehlt) — es wird nur OCR genutzt."
            )

    # ------------------------------------------------------------------
    # UI-Aufbau
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        # Toolbar
        toolbar = ttk.Frame(self, padding=(8, 6))
        toolbar.grid(row=0, column=0, sticky="ew")

        ttk.Label(toolbar, text="Anzeige:").pack(side="left")
        self._filter_var = tk.StringVar(value="all")
        filter_combo = ttk.Combobox(
            toolbar,
            textvariable=self._filter_var,
            values=[_FILTER_LABELS[m] for m in FILTER_MODES],
            state="readonly",
            width=14,
        )
        filter_combo.pack(side="left", padx=(4, 12))
        filter_combo.bind("<<ComboboxSelected>>", lambda _e: self._refresh_tree())
        # Map display label back to mode key
        self._filter_label_to_mode = {_FILTER_LABELS[m]: m for m in FILTER_MODES}

        self._run_btn = ttk.Button(toolbar, text="Durchlauf starten", command=self._on_run)
        self._run_btn.pack(side="left")

        self._write_btn = ttk.Button(
            toolbar, text="Jetzt schreiben", command=self._on_write, state="disabled"
        )
        self._write_btn.pack(side="left", padx=(8, 0))

        ttk.Button(toolbar, text="Alle auswählen", command=self._select_all).pack(
            side="left", padx=(8, 0)
        )
        ttk.Button(toolbar, text="Auswahl aufheben", command=self._deselect_all).pack(
            side="left", padx=(4, 0)
        )

        # Hinweis: Bedienhinweise
        hint = ttk.Frame(self, padding=(8, 0, 8, 4))
        hint.grid(row=1, column=0, sticky="ew")
        ttk.Label(
            hint,
            text="ℹ Sichere Treffer: Klick zum Auswählen. "
                 "Unsichere/Kein-Treffer-Karten: Doppelklick öffnet manuellen Zuordnungs-Dialog.",
            foreground="#555555",
            font=("", 8),
        ).pack(side="left")

        # Treeview
        tree_frame = ttk.Frame(self)
        tree_frame.grid(row=2, column=0, sticky="nsew", padx=8, pady=(0, 4))
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)

        self._tree = ttk.Treeview(
            tree_frame,
            columns=_TREE_COLS,
            show="headings",
            selectmode="none",
        )
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self._tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self._tree.xview)
        self._tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self._tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        col_cfg = {
            "call":   ("Rufzeichen", 120),
            "date":   ("Datum", 90),
            "band":   ("Band", 60),
            "mode":   ("Modus", 70),
            "source": ("Quelle", 60),
            "status": ("Status", 100),
        }
        for col, (heading, width) in col_cfg.items():
            self._tree.heading(col, text=heading)
            self._tree.column(col, width=width, minwidth=50)

        # Tag-Farben
        self._tree.tag_configure("certain", foreground="#1a7a1a")
        self._tree.tag_configure("uncertain", foreground="#b36b00")
        self._tree.tag_configure("no_match", foreground="#888888")
        self._tree.tag_configure("selected", background="#cce5ff")
        self._tree.tag_configure("manual_assigned", background="#e8d8f8", foreground="#5a0090")
        self._tree.tag_configure("written", background="#d4edda", foreground="#155724")

        self._tree.bind("<ButtonRelease-1>", self._on_tree_click)
        self._tree.bind("<Double-1>", self._on_double_click)

        # Statusleiste
        status_bar = ttk.Frame(self, padding=(8, 2))
        status_bar.grid(row=3, column=0, sticky="ew")

        self._progress = ttk.Progressbar(status_bar, length=200, mode="determinate")
        self._progress.pack(side="left", padx=(0, 8))

        self._status_var = tk.StringVar(value="Bereit.")
        ttk.Label(status_bar, textvariable=self._status_var).pack(side="left")

        self._sel_count_var = tk.StringVar(value="")
        ttk.Label(status_bar, textvariable=self._sel_count_var).pack(side="right")

        ttk.Button(
            status_bar,
            text="Fehler melden…",
            command=self._on_report_error,
            width=14,
        ).pack(side="right", padx=(4, 0))

        ttk.Button(
            status_bar,
            text="Log-Ordner öffnen",
            command=self._on_open_log_folder,
            width=16,
        ).pack(side="right", padx=(0, 4))

    # ------------------------------------------------------------------
    # Queue-Polling
    # ------------------------------------------------------------------

    def _poll(self) -> None:
        try:
            while True:
                event = self._event_queue.get_nowait()
                self._handle_event(event)
        except queue.Empty:
            pass
        self.after(100, self._poll)

    def _handle_event(self, event: object) -> None:
        if isinstance(event, ProgressEvent):
            if event.total > 0:
                self._progress.configure(maximum=event.total, value=event.done)
            self._status_var.set(event.message)
        elif isinstance(event, RunDoneEvent):
            self._run_result = event.result
            self._refresh_tree()
            _reset_progress(self._progress)
            certain = len(event.result.certain)
            uncertain = len(event.result.uncertain)
            no_match = len(event.result.no_match)
            self._status_var.set(
                f"Fertig — {certain} sicher, {uncertain} unsicher, {no_match} ohne Treffer."
            )
            self._run_btn.configure(state="normal")
            self._update_write_btn()
        elif isinstance(event, WriteDoneEvent):
            res = event.result
            actually_written = written_doc_ids(
                event.confirmed_doc_ids, event.selections, res.skipped
            )
            self._written.update(actually_written)
            for doc_id in actually_written:
                if doc_id in self._manual_pending:
                    self._written_qso[doc_id] = self._manual_pending[doc_id][0]
            self._manual_pending.clear()
            self._selected.clear()
            status = f"Geschrieben: {res.written} QSO(s), übersprungen: {len(res.skipped)}."
            if res.skipped:
                status += " Übersprungene Karten behalten ihren Status."
            if event.tag_warnings:
                status += " ⚠ Tag-Fehler — Details im Dialog."
            self._status_var.set(status)
            _reset_progress(self._progress)
            self._run_btn.configure(state="normal")
            self._write_btn.configure(state="disabled")
            self._refresh_tree()
            msg = f"{res.written} QSO(s) bestätigt, {len(res.skipped)} übersprungen."
            if event.tag_warnings:
                msg += "\n\n⚠ Tag-Warnungen:\n" + "\n".join(event.tag_warnings)
            messagebox.showinfo("Schreiben abgeschlossen", msg, parent=self)
        elif isinstance(event, ErrorEvent):
            self._status_var.set(f"Fehler: {event.exc}")
            _reset_progress(self._progress)
            self._run_btn.configure(state="normal")
            show_error(self, "Fehler", str(event.exc), event.traceback_str)

    # ------------------------------------------------------------------
    # Treeview
    # ------------------------------------------------------------------

    def _refresh_tree(self) -> None:
        mode_label = self._filter_var.get()
        mode = self._filter_label_to_mode.get(mode_label, "all")
        if self._run_result is not None:
            self._displayed = filter_results(self._run_result, mode)
        else:
            self._displayed = []

        sorted_cards = sort_cards_written_last(self._displayed, self._written)

        self._tree.delete(*self._tree.get_children())
        for card in sorted_cards:
            iid = str(card.doc_id)
            call = card.card_fields.call_from or card.card_fields.call_to or "–"
            date = card.card_fields.date or "–"
            band = card.card_fields.band or "–"
            mode_val = card.card_fields.mode or "–"
            source = card.source
            match_result = card.outcome.result
            status_label = _RESULT_LABELS.get(match_result, "?")

            tag = {
                MatchResult.CERTAIN: "certain",
                MatchResult.UNCERTAIN: "uncertain",
                MatchResult.NO_MATCH: "no_match",
            }.get(match_result, "")

            tags = [tag] if tag else []
            if card.doc_id in self._written:
                tags = ["written"]   # written überschreibt alle anderen Farbmarkierungen
                status_label = "Bestätigt ✓"
                # Manuell zugeordnete Karten: QSO-Werte aus gespeicherter qsoid anzeigen
                if card.doc_id in self._written_qso and self._run_result is not None:
                    matched = qso_by_id(self._run_result.candidates, self._written_qso[card.doc_id])
                    if matched is not None:
                        call, date, band, mode_val = qso_display_values(matched)
            else:
                if card.doc_id in self._selected:
                    tags.append("selected")
                if card.doc_id in self._manual_pending:
                    tags.append("manual_assigned")
                    status_label = "Manuell zugeordnet"
                    # QSO-Werte des zugeordneten Kandidaten anzeigen statt Kartenfelder
                    qsoid, _ = self._manual_pending[card.doc_id]
                    if self._run_result is not None:
                        matched = qso_by_id(self._run_result.candidates, qsoid)
                        if matched is not None:
                            call, date, band, mode_val = qso_display_values(matched)

            self._tree.insert(
                "",
                "end",
                iid=iid,
                values=(call, date, band, mode_val, source, status_label),
                tags=tags,
            )

        self._update_sel_count()

    def _on_tree_click(self, event: tk.Event) -> None:
        row_id = self._tree.identify_row(event.y)
        if not row_id:
            return
        try:
            doc_id = int(row_id)
        except ValueError:
            return
        # Nur CERTAIN-Karten sind selektierbar (ADR-0007, ADR-0023); geschriebene no-op
        card = next((c for c in self._displayed if c.doc_id == doc_id), None)
        if card is None or not is_batch_writable(card) or doc_id in self._written:
            return
        if doc_id in self._selected:
            self._selected.discard(doc_id)
            current_tags = list(self._tree.item(row_id, "tags"))
            current_tags = [t for t in current_tags if t != "selected"]
            self._tree.item(row_id, tags=current_tags)
        else:
            self._selected.add(doc_id)
            current_tags = list(self._tree.item(row_id, "tags"))
            if "selected" not in current_tags:
                current_tags.append("selected")
            self._tree.item(row_id, tags=current_tags)
        self._update_sel_count()
        self._update_write_btn()

    def _on_double_click(self, event: tk.Event) -> None:
        """Doppelklick auf UNCERTAIN/NO_MATCH-Karte öffnet manuellen Zuordnungs-Dialog."""
        _log.debug("_on_double_click betreten — event.y=%s", event.y)

        row_id = self._tree.identify_row(event.y)
        _log.debug("identify_row(%s) → %r", event.y, row_id or "<leer>")

        if not row_id:
            _log.debug("Early-return: row_id leer (Klick neben Zeile oder leerer Baum)")
            self._status_var.set("Doppelklick erkannt, aber keine Zeile getroffen.")
            return

        if self._run_result is None:
            _log.debug("Early-return: _run_result ist None (kein Durchlauf bisher)")
            self._status_var.set("Doppelklick erkannt — bitte zuerst einen Durchlauf starten.")
            return

        try:
            doc_id = int(row_id)
            _log.debug("row_id %r → doc_id=%s", row_id, doc_id)
        except ValueError:
            _log.debug("Early-return: row_id %r nicht als int parsbar", row_id)
            self._status_var.set("Doppelklick erkannt, aber Zeile nicht identifizierbar.")
            return

        card = next((c for c in self._displayed if c.doc_id == doc_id), None)
        if card is None:
            _log.debug("Early-return: doc_id=%s nicht in self._displayed (%d Karten)", doc_id, len(self._displayed))
            self._status_var.set(f"Doppelklick auf doc_id={doc_id} — Karte nicht in Ansicht.")
            return

        _log.debug("Karte gefunden: doc_id=%s outcome.result=%s", doc_id, card.outcome.result.name)

        if doc_id in self._written:
            _log.debug("Early-return: Karte bereits bestätigt — kein erneuter Dialog")
            self._status_var.set("Karte bereits bestätigt — kein erneuter Dialog möglich.")
            return

        if card.outcome.result == MatchResult.CERTAIN:
            _log.debug("Early-return: Karte ist CERTAIN — Einfach-Klick nutzen")
            self._status_var.set("Karte ist ein sicherer Treffer — Einfach-Klick zum Auswählen.")
            return

        from qsl73.gui.manual_assignment import ManualAssignmentDialog

        pc = self._paperless_client
        n_candidates = len(self._run_result.candidates)
        _log.debug(
            "Öffne ManualAssignmentDialog — doc_id=%s candidates=%d image_loader=%s",
            doc_id, n_candidates, "ja (pc vorhanden)" if pc is not None else "nein (pc=None)",
        )

        def _image_loader(doc_id_arg: int) -> bytes:
            if pc is None:
                raise RuntimeError("Kein Paperless-Client verfügbar")
            return pc.get_document_download(doc_id_arg)

        cfg = self._config
        dlg = ManualAssignmentDialog(
            parent=self,
            card=card,
            candidates=self._run_result.candidates,
            default_route=cfg.confirm.qsl_route_default,
            image_loader=_image_loader if pc is not None else None,
            limit=cfg.app.manual_match_limit,
        )

        _log.debug("Dialog geschlossen — dlg.result=%r", dlg.result)

        if dlg.result is not None:
            self._manual_pending[doc_id] = dlg.result
        else:
            # Abbrechen = Vormerkung aufheben (Erneuter Doppelklick → aufheben)
            self._manual_pending.pop(doc_id, None)

        self._refresh_tree()
        self._update_write_btn()

    def _select_all(self) -> None:
        for card in self._displayed:
            if is_batch_writable(card):
                self._selected.add(card.doc_id)
        self._refresh_tree()

    def _deselect_all(self) -> None:
        self._selected.clear()
        self._refresh_tree()

    def _update_sel_count(self) -> None:
        n = len(self._selected)
        self._sel_count_var.set(f"{n} ausgewählt" if n else "")

    def _update_write_btn(self) -> None:
        can_write = (bool(self._selected) or bool(self._manual_pending)) and self._run_result is not None
        self._write_btn.configure(state="normal" if can_write else "disabled")

    # ------------------------------------------------------------------
    # Aktionen
    # ------------------------------------------------------------------

    def _on_run(self) -> None:
        from qsl73.paperless import PaperlessClient

        cfg = self._config
        try:
            pc = PaperlessClient(cfg.paperless.url, cfg.paperless.token)
        except Exception as exc:
            show_error(self, "Verbindungsfehler", str(exc))
            return

        db_path = Path(cfg.log4om.db_path)
        if not db_path.exists():
            messagebox.showerror(
                "Datenbank nicht gefunden",
                f"Log4OM-Datenbank nicht gefunden:\n{db_path}",
                parent=self,
            )
            return

        self._paperless_client = pc
        self._selected.clear()
        self._manual_pending.clear()
        self._written.clear()
        self._written_qso.clear()
        self._run_result = None
        self._displayed = []
        self._tree.delete(*self._tree.get_children())
        self._run_btn.configure(state="disabled")
        self._write_btn.configure(state="disabled")
        self._status_var.set("Durchlauf läuft …")
        self._progress.configure(mode="indeterminate")
        self._progress.start(10)

        self._controller.start_run(pc, db_path, cfg)

    def _on_write(self) -> None:
        if not self._selected and not self._manual_pending:
            messagebox.showwarning(
                "Keine Auswahl",
                "Bitte mindestens eine Karte auswählen oder manuell zuordnen.",
                parent=self,
            )
            return

        cfg = self._config

        # Auto-Selektionen aus gewählten CERTAIN-Karten
        selected_cards = [c for c in self._displayed if c.doc_id in self._selected]
        auto_selections, auto_doc_ids = build_write_selections(
            selected_cards, route=cfg.confirm.qsl_route_default
        )

        # Auto + manuell zusammenführen (dedup by qsoid)
        selections, confirmed_doc_ids = merge_selections(
            auto_selections, auto_doc_ids, self._manual_pending
        )

        # Für Audit-Logging: welche qsoids wurden manuell zugeordnet?
        manual_qsoids_for_audit = {
            qsoid for _doc_id, (qsoid, _route) in self._manual_pending.items()
        }
        candidates_for_audit = (
            self._run_result.candidates if self._run_result is not None else []
        )

        if not selections:
            messagebox.showwarning(
                "Keine schreibbaren Karten",
                "Keine schreibbaren Karten gefunden.",
                parent=self,
            )
            return

        n_auto = len(auto_selections)
        n_manual = len(self._manual_pending)
        n_total = len(selections)

        detail = f"{n_auto} automatisch + {n_manual} manuell = {n_total} Karte(n)"
        if not messagebox.askyesno(
            "Bestätigen",
            f"{detail} in Log4OM bestätigen und Tags in Paperless setzen?\n\n"
            "Dieser Schritt schreibt in die Datenbank und kann nicht automatisch rückgängig "
            "gemacht werden (Backup wird erstellt).",
            parent=self,
        ):
            return

        pc = self._paperless_client
        if pc is None:
            from qsl73.paperless import PaperlessClient
            pc = PaperlessClient(cfg.paperless.url, cfg.paperless.token)

        db_path = Path(cfg.log4om.db_path)
        backup_dir = db_path.parent / "QSL73_Backups"

        self._run_btn.configure(state="disabled")
        self._write_btn.configure(state="disabled")
        self._status_var.set("Schreibe …")
        self._progress.configure(mode="indeterminate")
        self._progress.start(10)

        self._controller.start_write(
            selections=selections,
            db_path=db_path,
            backup_dir=backup_dir,
            backup_count=cfg.app.backup_count,
            paperless_client=pc,
            confirmed_doc_ids=confirmed_doc_ids,
            tags_config=cfg.tags,
            manual_qsoids=manual_qsoids_for_audit,   # NEU: für Audit-Logging
            candidates=candidates_for_audit,          # NEU: für Audit-Logging
        )

    # ------------------------------------------------------------------
    # Log-Ordner + Fehlermelden
    # ------------------------------------------------------------------

    def _on_open_log_folder(self) -> None:
        """Öffnet das Log-Verzeichnis im Datei-Explorer."""
        import os
        import subprocess
        import sys as _sys

        from qsl73.logging_setup import get_log_dir

        log_dir = get_log_dir()
        log_dir.mkdir(parents=True, exist_ok=True)

        if _sys.platform == "win32":
            os.startfile(str(log_dir))
        elif _sys.platform == "darwin":
            subprocess.run(["open", str(log_dir)], check=False)
        else:
            subprocess.run(["xdg-open", str(log_dir)], check=False)

    def _on_report_error(self) -> None:
        """Zeigt Fehlerbericht-Dialog mit Vorschau."""
        from qsl73.__version__ import CHANNEL, __version__
        from qsl73.error_report import build_error_report
        from qsl73.gui.error_report_dialog import ErrorReportDialog
        from qsl73.logging_setup import get_log_dir
        from qsl73.qr import qr_backend_status

        log_dir = get_log_dir()
        qr_status = qr_backend_status()
        report = build_error_report(__version__, CHANNEL, log_dir, qr_status)
        ErrorReportDialog(self, report, __version__, log_dir)
