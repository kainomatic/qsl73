# QSL73 — Copyright (C) 2026 DF1DS (kainomatic) — SPDX-License-Identifier: GPL-3.0-or-later
"""Hauptfenster mit Treeview, Filter, Lauf- und Schreib-Integration."""
from __future__ import annotations

import logging
import queue
import threading
from pathlib import Path
from typing import Optional

import tkinter as tk
from tkinter import messagebox, ttk

from qsl73.__version__ import CHANNEL, __version__
from qsl73.config import Config
from qsl73.crypto import CryptoBackend
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
from qsl73.gui.filter_util import (
    FILTER_MODES,
    build_workflow_sequence,
    build_write_selections,
    filter_results,
    format_progress_text,
    is_batch_writable,
    merge_selections,
    qso_by_id,
    qso_display_values,
    select_range,
    sort_cards_written_last,
    workflow_card_context,
    written_doc_ids,
)
from qsl73.gui.tooltip import attach_tooltip


_log = logging.getLogger("qsl73")

# i18n-Vorbereitung: nutzersichtbare Texte als Konstanten
# Update-Meldungen (i18n-Vorbereitung)
_UPDATE_CHECKING = "Prüfe auf Updates …"
_UPDATE_AVAILABLE_STATUS = "Update auf v{version} verfügbar — Hilfe → Update-Hinweis"
_UPDATE_HINT_LABEL = "⬆ Update auf v{version} verfügbar"
_UPDATE_NONE_MSG = "Sie verwenden die neueste Version (v{version})."
_UPDATE_NONE_TITLE = "Auf dem neuesten Stand — by DF1DS"
_UPDATE_ERROR_TITLE = "Update-Prüfung — by DF1DS"
_UPDATE_CHECK_LABEL = "Nach Updates suchen"

# Hilfe-Menü Infodateien
_MENU_README = "Liesmich anzeigen"
_MENU_CHANGELOG = "Was ist neu (Änderungen)…"
_MSG_DOC_UNAVAILABLE_TITLE = "Information nicht verfügbar — by DF1DS"
_MSG_DOC_UNAVAILABLE_BODY = (
    "Diese Information ist nur in der installierten Version verfügbar.\n\n"
    "Die Seite wird stattdessen im Browser geöffnet."
)

_MSG_RESTART_TITLE = "Einstellungen gespeichert — by DF1DS"
_MSG_RESTART_BODY = (
    "Einstellungen wurden gespeichert.\n\n"
    "Bitte QSL73 neu starten, damit alle Änderungen wirksam werden."
)
_MSG_RESTART_BTN_NOW = "Jetzt beenden"
_MSG_RESTART_BTN_LATER = "Später"
_MSG_RESTART_STATUS = "⚠ Neustart ausstehend — Einstellungen wirken nach dem nächsten Start."

_MSG_WORKFLOW_NO_MATCH_TITLE = "Unsichere Karten abgearbeitet"
_MSG_WORKFLOW_NO_MATCH_BODY = (
    "Keine unsicheren Karten mehr.\n\nMit den Kein-Treffer-Karten weitermachen?"
)
_MSG_WORKFLOW_DONE_TITLE = "Workflow abgeschlossen"
_MSG_WORKFLOW_DONE_BODY = "Alle Karten wurden durchgearbeitet."

# Über-Dialog
_ABOUT_TITLE = "Über QSL73 — by DF1DS"
_ABOUT_DESC = (
    "Gleicht gescannte Papier-QSL-Karten aus Paperless-ngx\n"
    "mit QSOs im Log4OM-Logbuch ab und markiert\n"
    "bestätigte Karten automatisch."
)
_ABOUT_LICENSE = "Lizenz: GNU General Public License v3 (GPLv3)"
_ABOUT_AUTHOR_LABEL = "Autor:"
_ABOUT_AUTHOR = "DF1DS | Stephan Dahmen | DOK: G16"
_ABOUT_LINK_GITHUB = "GitHub"
_ABOUT_LINK_QRZ = "QRZ.com"
_ABOUT_BTN_CLOSE = "Schließen"
_ABOUT_URL_GITHUB = "https://github.com/kainomatic/qsl73"
_ABOUT_URL_QRZ = "https://www.qrz.com/db/DF1DS"


# Tooltip-Texte (i18n-Vorbereitung)
_TT_FILTER = "Zeigt alle Karten / nur sichere Treffer / nur unsichere / nur Karten ohne Treffer"
_TT_RUN_BTN = "Ruft QSL-Karten aus Paperless ab und gleicht sie mit dem Log4OM-Logbuch ab"
_TT_WRITE_BTN = (
    "Schreibt ausgewählte Karten als Papier-QSL bestätigt in Log4OM "
    "und setzt Paperless-Tags (Vor-Backup wird erstellt)"
)
_TT_SELECT_ALL = "Wählt alle sicheren Treffer in der aktuellen Ansicht aus"
_TT_DESELECT_ALL = "Hebt die aktuelle Auswahl auf"

# Pulsintervall für indeterminate-Fortschrittsbalken in ms.
# tk-Standard 10 ms ist sehr schnell (Pendeln wirkt nervös); 40 ms ist deutlich ruhiger.
_PROGRESS_PULSE_MS = 40


def _reset_progress(progress: ttk.Progressbar) -> None:
    """Hält indeterminate-Animation an und setzt Balken auf 0 zurück."""
    progress.stop()
    progress.configure(mode="determinate", value=0)


def _compute_dialog_geometry(dw: int, dh: int, px: int, py: int, pw: int, ph: int) -> str:
    """Gibt eine tk-Geometrie-Zeichenkette zurück, die den Dialog über dem Parent zentriert.

    Alle Parameter sind ganze Pixel-Werte; kein tk-Zugriff — vollständig testbar ohne Display.
    """
    x = max(0, px + (pw - dw) // 2)
    y = max(0, py + (ph - dh) // 2)
    return f"{dw}x{dh}+{x}+{y}"


def _resolve_dialog_height(inner_h: int, chrome: int = 40, min_h: int = 300) -> int:
    """Berechnet die finale Dialog-Höhe aus der Inhaltshöhe des inneren Frames.

    Addiert den Chrome-Overhead (Titelleiste, Fensterrand) und erzwingt eine Mindesthöhe.
    Verhindert 1px-Fenster wenn die Toplevel-Messung zu früh/zu klein ist.
    Tk-frei und vollständig testbar ohne Display.
    """
    return max(inner_h + chrome, min_h)


def _resolve_dialog_width(inner_w: int, min_w: int = 360) -> int:
    """Berechnet die finale Dialog-Breite aus der Inhaltshöhe des inneren Frames.

    Erzwingt eine Mindestbreite, damit Logo + Texte + Buttons sicher hineinpassen.
    Tk-frei und vollständig testbar ohne Display.
    """
    return max(inner_w, min_w)


# Über-Dialog — harte Mindestmaße (Logo-inklusive Summe: Logo 112px + pady 10 +
# Titel + Beschreibung + Separator + Lizenz + Autor + Links + Button + Frame-Padding 48
# + Chrome 90 ≈ 491 px; 520 px lässt sicheren Puffer für DPI-Varianz und Fontgrößen)
_ABOUT_MIN_H: int = 520
_ABOUT_MIN_W: int = 360

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

    def __init__(self, config: Config, crypto: Optional[CryptoBackend] = None) -> None:
        super().__init__()
        self._config = config
        from qsl73.crypto import get_default_backend
        self._crypto = crypto if crypto is not None else get_default_backend()
        self._event_queue: queue.Queue = queue.Queue()
        self._controller = RunController(self._event_queue)
        self._run_result: Optional[RunResult] = None
        self._selected: set[int] = set()          # doc_ids der selektierten CERTAIN-Karten
        self._selection_anchor: int | None = None  # Anker für Shift-Bereichsauswahl
        self._displayed: list[CardResult] = []  # aktuell angezeigte Karten
        self._manual_pending: dict[int, tuple[str, str]] = {}  # doc_id → (qsoid, route)
        self._written: set[int] = set()       # doc_ids die in diesem Lauf bereits geschrieben wurden
        self._written_qso: dict[int, str] = {}  # doc_id → qsoid (manuell zugeordnet + geschrieben)
        self._paperless_client = None         # wird in _on_run gesetzt, für Bildladen im Dialog
        self._pending_update_result = None    # UpdateCheckResult wenn Nutzer „Später" gewählt
        self._help_menu: Optional[tk.Menu] = None

        title = f"QSL73 v{__version__}"
        if CHANNEL == "beta":
            title += " [BETA]"
        title += " — by DF1DS"
        self.title(title)
        self.minsize(750, 450)

        from qsl73.gui._icon import apply_window_icon
        apply_window_icon(self)

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

        # Menüleiste (ADR-0036)
        self._build_menu()

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
        attach_tooltip(filter_combo, _TT_FILTER)
        # Map display label back to mode key
        self._filter_label_to_mode = {_FILTER_LABELS[m]: m for m in FILTER_MODES}

        self._run_btn = ttk.Button(toolbar, text="Durchlauf starten", command=self._on_run)
        self._run_btn.pack(side="left")
        attach_tooltip(self._run_btn, _TT_RUN_BTN)

        self._write_btn = ttk.Button(
            toolbar, text="Jetzt schreiben", command=self._on_write, state="disabled"
        )
        self._write_btn.pack(side="left", padx=(8, 0))
        attach_tooltip(self._write_btn, _TT_WRITE_BTN)

        _btn_sel_all = ttk.Button(toolbar, text="Alle auswählen", command=self._select_all)
        _btn_sel_all.pack(side="left", padx=(8, 0))
        attach_tooltip(_btn_sel_all, _TT_SELECT_ALL)
        _btn_desel_all = ttk.Button(toolbar, text="Auswahl aufheben", command=self._deselect_all)
        _btn_desel_all.pack(side="left", padx=(4, 0))
        attach_tooltip(_btn_desel_all, _TT_DESELECT_ALL)

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
        self._tree.bind("<Shift-ButtonRelease-1>", self._on_tree_shift_click)
        self._tree.bind("<Double-1>", self._on_double_click)

        # Statusleiste (Buttons "Log-Ordner öffnen" und "Fehler melden…" im Hilfe-Menü, ADR-0036)
        status_bar = ttk.Frame(self, padding=(8, 2))
        status_bar.grid(row=3, column=0, sticky="ew")

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
                # Vorbereitungsphase endet: indeterminate → determinaten Balken
                self._progress.stop()
                self._progress.configure(
                    mode="determinate",
                    maximum=event.total,
                    value=event.done,
                )
            self._status_var.set(format_progress_text(event.done, event.total, event.message))
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
            self._status_var.set(event.status_message or f"Fehler: {event.exc}")
            _reset_progress(self._progress)
            self._run_btn.configure(state="normal")
            if event.is_expected:
                show_error(
                    self,
                    event.error_title,
                    event.user_message or str(event.exc),
                )
            else:
                show_error(
                    self,
                    event.error_title,
                    event.user_message or str(event.exc),
                    event.traceback_str,
                )

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
        self._selection_anchor = doc_id  # Anker für nachfolgende Shift-Klicks
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

    def _on_tree_shift_click(self, event: tk.Event) -> None:
        """Shift-Klick: Bereichsauswahl von Anker bis Ziel (Standard-Listenverhalten)."""
        row_id = self._tree.identify_row(event.y)
        if not row_id:
            return
        try:
            target_id = int(row_id)
        except ValueError:
            return

        displayed_ids = [c.doc_id for c in self._displayed]
        selectable_ids = {
            c.doc_id for c in self._displayed
            if is_batch_writable(c) and c.doc_id not in self._written
        }

        new_selection = select_range(
            displayed_ids, selectable_ids, self._selection_anchor, target_id
        )

        # Gesamte Auswahl durch den Bereich ersetzen
        old_selected = set(self._selected)
        self._selected = new_selection

        for c in self._displayed:
            rid = str(c.doc_id)
            tags = list(self._tree.item(rid, "tags"))
            if c.doc_id in new_selection and "selected" not in tags:
                tags.append("selected")
            elif c.doc_id not in new_selection and "selected" in tags:
                tags = [t for t in tags if t != "selected"]
            # Nur aktualisieren wenn sich etwas geändert hat
            if c.doc_id in new_selection.symmetric_difference(old_selected):
                self._tree.item(rid, tags=tags)

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

        # Workflow-Kontext berechnen (Phase, X von Y, has_next)
        done = set(self._manual_pending.keys()) | self._written
        uncertain, no_match = build_workflow_sequence(self._displayed, done)
        ctx = workflow_card_context(card, uncertain, no_match)

        dlg = self._open_assignment_dialog(card, ctx)

        _log.debug("Dialog geschlossen — dlg.result=%r action=%s", dlg.result, dlg.action)

        if dlg.result is not None:
            self._manual_pending[doc_id] = dlg.result
        else:
            if dlg.action == "cancel":
                # Abbrechen = Vormerkung aufheben
                self._manual_pending.pop(doc_id, None)
            # skip = kein Speichern, Vormerkung bleibt unverändert

        if dlg.action in ("save_next", "skip"):
            self._continue_workflow(card, dlg.action)

        self._refresh_tree()
        self._update_write_btn()

    def _open_assignment_dialog(self, card: CardResult, ctx: dict):
        """Öffnet ManualAssignmentDialog mit Workflow-Kontext und gibt ihn zurück."""
        from qsl73.gui.manual_assignment import ManualAssignmentDialog

        pc = self._paperless_client
        cfg = self._config

        def _image_loader(doc_id_arg: int) -> bytes:
            if pc is None:
                raise RuntimeError("Kein Paperless-Client verfügbar")
            return pc.get_document_download(doc_id_arg)

        return ManualAssignmentDialog(
            parent=self,
            card=card,
            candidates=self._run_result.candidates,
            default_route=cfg.confirm.qsl_route_default,
            image_loader=_image_loader if pc is not None else None,
            limit=cfg.app.manual_match_limit,
            card_status=ctx.get("phase", card.outcome.result),
            card_index=ctx.get("card_index", 0),
            total_cards=ctx.get("total_cards", 0),
            has_next=ctx.get("has_next", False),
        )

    def _continue_workflow(self, just_processed: CardResult, trigger_action: str) -> None:
        """Setzt Durcharbeiten-Workflow nach just_processed fort (iterativ).

        trigger_action: "save_next" oder "skip".
        Steuert Phase-1 (UNCERTAIN) → optionaler Phase-2-Übergang (NO_MATCH).
        """
        initial_phase = just_processed.outcome.result
        initial_skip: set[int] = set()
        if trigger_action == "skip":
            initial_skip.add(just_processed.doc_id)

        if initial_phase == MatchResult.UNCERTAIN:
            result = self._run_workflow_phase(MatchResult.UNCERTAIN, extra_skip=initial_skip)
            if result == "cancel":
                return
            # UNCERTAIN-Phase abgeschlossen → ggf. NO_MATCH-Phase anbieten
            done = set(self._manual_pending.keys()) | self._written
            _, no_match_remaining = build_workflow_sequence(self._displayed, done)
            if no_match_remaining:
                if messagebox.askyesno(
                    _MSG_WORKFLOW_NO_MATCH_TITLE,
                    _MSG_WORKFLOW_NO_MATCH_BODY,
                    parent=self,
                ):
                    result = self._run_workflow_phase(MatchResult.NO_MATCH)
                    if result != "cancel":
                        messagebox.showinfo(
                            _MSG_WORKFLOW_DONE_TITLE, _MSG_WORKFLOW_DONE_BODY, parent=self
                        )
            else:
                messagebox.showinfo(
                    _MSG_WORKFLOW_DONE_TITLE, _MSG_WORKFLOW_DONE_BODY, parent=self
                )
        else:
            result = self._run_workflow_phase(MatchResult.NO_MATCH, extra_skip=initial_skip)
            if result != "cancel":
                done = set(self._manual_pending.keys()) | self._written
                _, no_match_remaining = build_workflow_sequence(self._displayed, done)
                if not no_match_remaining:
                    messagebox.showinfo(
                        _MSG_WORKFLOW_DONE_TITLE, _MSG_WORKFLOW_DONE_BODY, parent=self
                    )

    def _run_workflow_phase(
        self,
        phase_type: MatchResult,
        extra_skip: Optional[set[int]] = None,
    ) -> str:
        """Verarbeitet eine Workflow-Phase iterativ.

        Öffnet für jede verbleibende Karte einen Dialog und reagiert auf die Aktion.
        Gibt "done" (Phase abgeschlossen), "save" (früher Ausstieg) oder "cancel" zurück.
        "done" tritt auf wenn alle Karten bearbeitet ODER die letzte Karte "Speichern" gedrückt.
        """
        skipped: set[int] = set(extra_skip or ())
        processed = 0
        total_at_start: Optional[int] = None

        while True:
            done = set(self._manual_pending.keys()) | self._written
            excluded = done | skipped
            uncertain, no_match = build_workflow_sequence(self._displayed, excluded)
            seq = uncertain if phase_type == MatchResult.UNCERTAIN else no_match

            if not seq:
                return "done"

            # Initialtotal einmalig beim ersten Durchlauf merken
            if total_at_start is None:
                total_at_start = len(seq)

            card = seq[0]
            has_next = len(seq) > 1

            ctx = {
                "phase": phase_type,
                "card_index": processed + 1,
                "total_cards": total_at_start,
                "has_next": has_next,
            }

            dlg = self._open_assignment_dialog(card, ctx)

            if dlg.result is not None:
                self._manual_pending[card.doc_id] = dlg.result
            self._refresh_tree()
            self._update_write_btn()

            action = dlg.action

            if action == "cancel":
                return "cancel"

            if action == "save":
                # Karte gespeichert → prüfen ob Phase damit abgeschlossen
                done_new = set(self._manual_pending.keys()) | self._written
                excl_new = done_new | skipped
                unc_new, nm_new = build_workflow_sequence(self._displayed, excl_new)
                seq_new = unc_new if phase_type == MatchResult.UNCERTAIN else nm_new
                if not seq_new:
                    return "done"  # letzte Karte war das — Phase vollständig
                return "save"  # Abbruch mitten in der Phase

            if action == "skip":
                skipped.add(card.doc_id)
            # "save_next" oder "skip" → Schleife läuft weiter

            processed += 1

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
        self._progress.start(_PROGRESS_PULSE_MS)

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
        self._progress.start(_PROGRESS_PULSE_MS)

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
    # Menüleiste (ADR-0036)
    # ------------------------------------------------------------------

    def _build_menu(self) -> None:
        menubar = tk.Menu(self)

        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Beenden", command=self.destroy)
        menubar.add_cascade(label="Datei", menu=file_menu)

        edit_menu = tk.Menu(menubar, tearoff=0)
        edit_menu.add_command(label="Einstellungen…", command=self._on_settings)
        menubar.add_cascade(label="Bearbeiten", menu=edit_menu)

        self._help_menu = tk.Menu(menubar, tearoff=0)
        self._rebuild_help_menu()
        menubar.add_cascade(label="Hilfe", menu=self._help_menu)

        self.config(menu=menubar)

    def _rebuild_help_menu(self) -> None:
        """Baut den Hilfe-Menü-Inhalt neu auf (mit/ohne Update-Hinweis)."""
        m = self._help_menu
        if m is None:
            return
        m.delete(0, "end")
        # Update-Hinweis oben, wenn Nutzer zuvor „Später" gewählt hat
        if self._pending_update_result is not None:
            nv = self._pending_update_result.new_version or "?"
            m.add_command(
                label=_UPDATE_HINT_LABEL.format(version=nv),
                command=self._on_update_hint_click,
            )
            m.add_separator()
        m.add_command(label=_UPDATE_CHECK_LABEL, command=self._on_check_updates_manual)
        m.add_separator()
        m.add_command(label="Log-Ordner öffnen", command=self._on_open_log_folder)
        m.add_command(label="Fehler melden…", command=self._on_report_error)
        m.add_separator()
        m.add_command(label=_MENU_README, command=self._on_show_readme)
        m.add_command(label=_MENU_CHANGELOG, command=self._on_show_changelog)
        m.add_separator()
        m.add_command(label="Über QSL73", command=self._on_about)

    def _on_settings(self) -> None:
        from qsl73.gui.setup_wizard import SetupWizard
        wizard = SetupWizard(self, crypto=self._crypto, existing_config=self._config)
        if wizard.result is not None:
            self._config = wizard.result
            self._show_restart_prompt()

    def _show_restart_prompt(self) -> None:
        """Neustart-Dialog nach Einstellungs-Speichern.

        Wir beenden die App sauber statt sie sofort neu zu starten:
        Self-Restart via os.execv würde bei gleichem PID durch den Lock geblockt;
        subprocess + sys.exit hat ein Race-Window zwischen Lock-Freigabe und
        Neustart-Versuch. Sauber beenden ist zuverlässiger — der Lock wird danach
        im finally-Block von run_app() freigegeben, sodass der Neustart blockierfrei ist.
        """
        dlg = tk.Toplevel(self)
        dlg.title(_MSG_RESTART_TITLE)
        dlg.resizable(False, False)
        dlg.transient(self)
        dlg.grab_set()

        ttk.Label(dlg, text=_MSG_RESTART_BODY, padding=16, wraplength=360).pack()

        btn_frame = ttk.Frame(dlg, padding=(16, 0, 16, 12))
        btn_frame.pack(fill="x")

        _do_exit = [False]

        def _on_exit() -> None:
            _do_exit[0] = True
            dlg.destroy()

        ttk.Button(btn_frame, text=_MSG_RESTART_BTN_NOW, command=_on_exit).pack(
            side="right", padx=(4, 0)
        )
        ttk.Button(btn_frame, text=_MSG_RESTART_BTN_LATER, command=dlg.destroy).pack(
            side="right"
        )

        dlg.wait_window()

        if _do_exit[0]:
            self.destroy()
        else:
            self._status_var.set(_MSG_RESTART_STATUS)

    def _on_about(self) -> None:
        """Über-Dialog — kein Systemsound, klickbare Links, luftiges Layout."""
        import webbrowser

        dlg = tk.Toplevel(self)
        dlg.title(_ABOUT_TITLE)
        dlg.resizable(True, True)  # False,False lässt WM die geometry()-Größe ignorieren
        dlg.transient(self)
        dlg.grab_set()

        frame = ttk.Frame(dlg, padding=24)
        frame.pack(fill="both", expand=True)

        # Logo oben (transparent, 112 px)
        from qsl73.gui._icon import load_about_logo
        logo_photo = load_about_logo(size=112)
        if logo_photo is not None:
            logo_lbl = tk.Label(frame, image=logo_photo, bg=frame.cget("background"))
            logo_lbl.image = logo_photo  # GC-Schutz
            logo_lbl.pack(pady=(0, 10))

        # App-Titel und Version (klar als Überschrift)
        ttk.Label(
            frame,
            text=f"QSL73  v{__version__}  ({CHANNEL})",
            font=("", 13, "bold"),
        ).pack(pady=(0, 14))

        # Kurzbeschreibung
        ttk.Label(
            frame,
            text=_ABOUT_DESC,
            justify="center",
        ).pack(pady=(0, 12))

        ttk.Separator(frame, orient="horizontal").pack(fill="x", pady=(0, 12))

        # Lizenz
        ttk.Label(frame, text=_ABOUT_LICENSE).pack(pady=(0, 6))

        # Autor hervorgehoben
        author_row = ttk.Frame(frame)
        author_row.pack(pady=(0, 14))
        ttk.Label(author_row, text=f"{_ABOUT_AUTHOR_LABEL}  ").pack(side="left")
        tk.Label(
            author_row,
            text=_ABOUT_AUTHOR,
            font=("", 10, "bold"),
        ).pack(side="left")

        # Links nebeneinander (horizontal, mittig)
        def _make_link(parent: tk.Misc, text: str, url: str) -> tk.Label:
            lbl = tk.Label(
                parent, text=text,
                fg="#0645ad", cursor="hand2",
                font=("", 9),
            )
            lbl.bind("<Button-1>", lambda _e, u=url: webbrowser.open(u))
            lbl.bind("<Enter>", lambda _e, l=lbl: l.config(font=("", 9, "underline")))
            lbl.bind("<Leave>", lambda _e, l=lbl: l.config(font=("", 9)))
            return lbl

        link_row = ttk.Frame(frame)
        link_row.pack(pady=(0, 18))
        _make_link(link_row, _ABOUT_LINK_GITHUB, _ABOUT_URL_GITHUB).pack(
            side="left", padx=(0, 20)
        )
        _make_link(link_row, _ABOUT_LINK_QRZ, _ABOUT_URL_QRZ).pack(side="left")

        ttk.Button(frame, text=_ABOUT_BTN_CLOSE, command=dlg.destroy).pack()

        dlg.bind("<Escape>", lambda _e: dlg.destroy())
        dlg.minsize(_ABOUT_MIN_W, _ABOUT_MIN_H)

        # Layout erzwingen bevor after(1,...) scheduliert wird (wie SetupWizard._build_ui).
        dlg.update_idletasks()

        # Größe/Position exakt nach SetupWizard._adjust_window_size-Muster:
        # Bildschirm-Deckel (90 %) + hartes Logo-inklusives Minimum + Parent-Zentrierung.
        def _do_center() -> None:
            if not dlg.winfo_exists():
                return
            dlg.update_idletasks()
            screen_h = dlg.winfo_screenheight()
            needed_h = frame.winfo_reqheight() + 90
            target_h = min(needed_h, int(screen_h * 0.9))
            target_h = max(target_h, _ABOUT_MIN_H)
            target_w = max(_ABOUT_MIN_W, dlg.winfo_reqwidth())
            try:
                if self.winfo_ismapped():
                    geom = _compute_dialog_geometry(
                        target_w, target_h,
                        self.winfo_rootx(), self.winfo_rooty(),
                        self.winfo_width(), self.winfo_height(),
                    )
                else:
                    sw = dlg.winfo_screenwidth()
                    x = max(0, (sw - target_w) // 2)
                    y = max(0, (screen_h - target_h) // 2)
                    geom = f"{target_w}x{target_h}+{x}+{y}"
            except Exception:
                sw = dlg.winfo_screenwidth()
                x = max(0, (sw - target_w) // 2)
                y = max(0, (screen_h - target_h) // 2)
                geom = f"{target_w}x{target_h}+{x}+{y}"
            dlg.geometry(geom)

        dlg.after(1, _do_center)
        dlg.wait_window()

    # ------------------------------------------------------------------
    # Update-Prüfung (ADR-0045)
    # ------------------------------------------------------------------

    def schedule_update_check(self) -> None:
        """Startet die automatische Update-Prüfung nach einem kurzen Delay.

        Wird von run_app() aufgerufen, nachdem das Hauptfenster sichtbar ist.
        Nicht-blockierend: die Prüfung läuft in einem Hintergrund-Thread.
        """
        self.after(1500, self._start_update_check)

    def _start_update_check(self, manual: bool = False) -> None:
        """Startet Update-Prüfung im Hintergrund-Thread."""
        from qsl73.__version__ import CHANNEL, __version__

        if manual:
            self._status_var.set(_UPDATE_CHECKING)

        def _check() -> None:
            from qsl73.updater import check_for_update
            result = check_for_update(__version__, CHANNEL)
            self.after(0, lambda: self._handle_update_result(result, manual=manual))

        threading.Thread(target=_check, daemon=True).start()

    def _handle_update_result(self, result, *, manual: bool) -> None:
        """Verarbeitet das Update-Prüfungsergebnis im UI-Thread."""
        from qsl73.updater import UpdateStatus

        if result.status == UpdateStatus.UPDATE_AVAILABLE:
            if not manual:
                self._status_var.set(
                    _UPDATE_AVAILABLE_STATUS.format(version=result.new_version)
                )
            self._show_update_dialog(result)
        elif result.status == UpdateStatus.UP_TO_DATE:
            if manual:
                from qsl73.__version__ import __version__
                self._status_var.set("Bereit.")
                dlg = tk.Toplevel(self)
                dlg.title(_UPDATE_NONE_TITLE)
                dlg.resizable(False, False)
                dlg.transient(self)
                dlg.grab_set()
                from qsl73.gui._icon import apply_window_icon
                apply_window_icon(dlg)
                ttk.Label(
                    dlg,
                    text=_UPDATE_NONE_MSG.format(version=__version__),
                    padding=20,
                ).pack()
                ttk.Button(dlg, text="OK", command=dlg.destroy).pack(pady=(0, 14))
                dlg.bind("<Return>", lambda _e: dlg.destroy())
                dlg.bind("<Escape>", lambda _e: dlg.destroy())
                dlg.update_idletasks()
                dw = max(300, dlg.winfo_reqwidth())
                dh = dlg.winfo_reqheight()
                x = max(0, self.winfo_rootx() + (self.winfo_width() - dw) // 2)
                y = max(0, self.winfo_rooty() + (self.winfo_height() - dh) // 2)
                dlg.geometry(f"{dw}x{dh}+{x}+{y}")
        else:
            # Error: nur im manuellen Modus dem Nutzer zeigen
            if manual:
                self._status_var.set("Bereit.")
                from qsl73.gui.error_dialog import show_error
                show_error(
                    self,
                    _UPDATE_ERROR_TITLE,
                    result.error_message or "Unbekannter Fehler bei der Update-Prüfung.",
                )
            else:
                _log.debug("Automatische Update-Prüfung: %s", result.error_message)

    def _show_update_dialog(self, result) -> None:
        """Zeigt den Update-Hinweis-Dialog."""
        from qsl73.__version__ import __version__
        from qsl73.updater import launch_installer_and_exit
        from qsl73.gui.update_dialog import UpdateDialog

        def _on_install(installer_path) -> None:
            launch_installer_and_exit(installer_path, self.destroy)

        def _on_opt_out() -> None:
            from qsl73.config import get_config_path, save_config
            self._config.app.update_check = False
            try:
                save_config(self._config, get_config_path(), self._crypto)
                _log.info("update_check auf False gesetzt (Nutzer-Opt-out).")
            except Exception as exc:
                _log.warning("Konnte update_check nicht speichern: %s", exc)
            # Hinweis aus dem Menü entfernen
            self._pending_update_result = None
            self._rebuild_help_menu()

        dlg = UpdateDialog(
            parent=self,
            current_version=__version__,
            new_version=result.new_version or "?",
            asset=result.asset,
            release_url=result.release_url,
            on_install=_on_install,
            on_opt_out=_on_opt_out,
        )
        dlg.wait_window()

        # Nach Schließen des Dialogs: wenn Nutzer „Später" (ohne Opt-out) → Hint im Menü
        if self._config.app.update_check and result.new_version is not None:
            self._pending_update_result = result
        else:
            self._pending_update_result = None
        self._rebuild_help_menu()

    def _on_check_updates_manual(self) -> None:
        """Menü-Handler: „Nach Updates suchen" — auch wenn update_check aus."""
        self._start_update_check(manual=True)

    def _on_update_hint_click(self) -> None:
        """Menü-Handler: Update-Hint-Eintrag — öffnet Dialog erneut."""
        if self._pending_update_result is not None:
            self._show_update_dialog(self._pending_update_result)

    # ------------------------------------------------------------------
    # Infodateien (Liesmich / Änderungen)
    # ------------------------------------------------------------------

    def _open_doc_html(self, filename: str) -> None:
        """Öffnet HTML-Infodatei im Standardbrowser; Fallback auf GitHub-URL."""
        import webbrowser

        try:
            from qsl73.gui.doc_paths import get_fallback_url, resolve_doc_html

            path = resolve_doc_html(filename)
            if path is not None:
                webbrowser.open(path.as_uri())
            else:
                url = get_fallback_url(filename)
                if url:
                    webbrowser.open(url)
                else:
                    messagebox.showinfo(
                        _MSG_DOC_UNAVAILABLE_TITLE,
                        _MSG_DOC_UNAVAILABLE_BODY,
                        parent=self,
                    )
        except Exception:
            _log.debug("Infodatei konnte nicht geöffnet werden: %s", filename, exc_info=True)

    def _on_show_readme(self) -> None:
        self._open_doc_html("LIESMICH.html")

    def _on_show_changelog(self) -> None:
        self._open_doc_html("AENDERUNGEN.html")

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
