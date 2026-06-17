# QSL73 — Copyright (C) 2026 DF1DS (kainomatic) — SPDX-License-Identifier: GPL-3.0-or-later
"""Hauptfenster mit Treeview, Filter, Lauf- und Schreib-Integration."""
from __future__ import annotations

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
from qsl73.gui.filter_util import FILTER_MODES, filter_results


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
        self._selected: set[int] = set()      # doc_ids der selektierten Karten
        self._displayed: list[CardResult] = []  # aktuell angezeigte Karten

        title = f"QSL73 v{__version__}"
        if CHANNEL == "beta":
            title += " [BETA]"
        self.title(title)
        self.minsize(750, 450)

        self._build_ui()
        self._poll()

    # ------------------------------------------------------------------
    # UI-Aufbau
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

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

        # Treeview
        tree_frame = ttk.Frame(self)
        tree_frame.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 4))
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

        self._tree.bind("<ButtonRelease-1>", self._on_tree_click)

        # Statusleiste
        status_bar = ttk.Frame(self, padding=(8, 2))
        status_bar.grid(row=2, column=0, sticky="ew")

        self._progress = ttk.Progressbar(status_bar, length=200, mode="determinate")
        self._progress.pack(side="left", padx=(0, 8))

        self._status_var = tk.StringVar(value="Bereit.")
        ttk.Label(status_bar, textvariable=self._status_var).pack(side="left")

        self._sel_count_var = tk.StringVar(value="")
        ttk.Label(status_bar, textvariable=self._sel_count_var).pack(side="right")

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
            self._progress.configure(value=0)
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
            self._status_var.set(f"Geschrieben: {res.written} QSO(s), übersprungen: {res.skipped}.")
            self._progress.configure(value=0)
            self._run_btn.configure(state="normal")
            self._write_btn.configure(state="disabled")
            messagebox.showinfo(
                "Schreiben abgeschlossen",
                f"{res.written} QSO(s) bestätigt, {res.skipped} übersprungen.",
                parent=self,
            )
        elif isinstance(event, ErrorEvent):
            self._status_var.set(f"Fehler: {event.exc}")
            self._progress.configure(value=0)
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

        self._tree.delete(*self._tree.get_children())
        for card in self._displayed:
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
            if card.doc_id in self._selected:
                tags.append("selected")

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

    def _select_all(self) -> None:
        for card in self._displayed:
            self._selected.add(card.doc_id)
        self._refresh_tree()

    def _deselect_all(self) -> None:
        self._selected.clear()
        self._refresh_tree()

    def _update_sel_count(self) -> None:
        n = len(self._selected)
        self._sel_count_var.set(f"{n} ausgewählt" if n else "")

    def _update_write_btn(self) -> None:
        can_write = bool(self._selected) and self._run_result is not None
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

        self._selected.clear()
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
        if not self._selected:
            messagebox.showwarning("Keine Auswahl", "Bitte mindestens eine Karte auswählen.", parent=self)
            return

        selected_cards = [c for c in self._displayed if c.doc_id in self._selected]
        # Nur Karten mit einem gematchten QSO können geschrieben werden
        writable = [c for c in selected_cards if c.outcome.matched_qso is not None]
        if not writable:
            messagebox.showwarning(
                "Keine schreibbaren Karten",
                "Die ausgewählten Karten haben keinen zugeordneten QSO-Eintrag.",
                parent=self,
            )
            return

        count = len(writable)
        if not messagebox.askyesno(
            "Bestätigen",
            f"{count} Karte(n) in Log4OM bestätigen und Tags in Paperless setzen?\n\n"
            "Dieser Schritt schreibt in die Datenbank und kann nicht automatisch rückgängig "
            "gemacht werden (Backup wird erstellt).",
            parent=self,
        ):
            return

        cfg = self._config
        route = cfg.confirm.qsl_route_default
        selections = [(c.outcome.matched_qso.qsoid, route) for c in writable]
        confirmed_doc_ids = [c.doc_id for c in writable]

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
        )
