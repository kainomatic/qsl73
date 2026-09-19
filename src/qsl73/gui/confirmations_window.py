# QSL73 — Copyright (C) 2026 DF1DS (kainomatic) — SPDX-License-Identifier: GPL-3.0-or-later
"""Bestätigungsübersicht-Fenster (Issue #42, Auftrag 2) — Werkzeuge → Bestätigungsübersicht….

Read-only, unabhängig vom Karten-Durchlauf: braucht nur `log4om.db_path`, funktioniert
ohne Paperless. Laden im Hintergrund-Thread mit Queue-Polling (ADR-0023-Muster, analog
`gui/ignored_window.py`). Alle Berechnungen/Filter kommen aus `qsl73.confirmations` und
`gui/confirmations_view` (beide tk-frei) — dieses Modul wendet sie nur an.
"""
from __future__ import annotations

import logging
import queue
import threading
from datetime import date, datetime
from pathlib import Path

from qsl73.confirmations import (
    CONFIRMATION_SERVICES,
    PRESETS,
    UPLOAD_SERVICES,
    CollectiveFilter,
    ConfirmationFilters,
    apply_filters,
    available_status_values,
    compute_metrics,
    load_confirmation_data,
    preset_filters,
    service_group,
)
from qsl73.gui.confirmations_view import (
    METRIC_TILE_LABELS,
    QUICK_RANGE_CHOICES,
    SERVICE_COLUMN_ORDER,
    SERVICE_LABELS,
    ColumnVisibility,
    cell_display,
    cell_tooltip_text,
    format_detail_line,
    metric_tile_values,
    quick_range_bounds,
    sort_rows_by_column,
)
from qsl73.gui.filter_util import apply_display_limit
from qsl73.log4om_db import SchemaError

_log = logging.getLogger("qsl73")

_TITLE = "Bestätigungsübersicht — by DF1DS"
_DISPLAY_LIMIT = 500

_LBL_LOADING = "Lade…"
_LBL_RELOAD = "Neu laden"
_LBL_COLUMNS = "Spalten wählen…"
_LBL_CSV_EXPORT = "CSV exportieren…"
_LBL_RESET_FILTERS = "Filter zurücksetzen"
_LBL_ALL = "Alle"
_LBL_ADVANCED_SHOW = "▶ Erweiterte Filter"
_LBL_ADVANCED_HIDE = "▼ Erweiterte Filter"
_MSG_NO_DB = "Keine gültige Log4OM-Datenbank konfiguriert (log4om.db_path fehlt oder ist ungültig)."
_MSG_LOAD_ERROR = "Bestätigungsdaten konnten nicht geladen werden: {error}"
_TT_RELOAD = "Lädt die Log4OM-Datenbank erneut (read-only)"
_TT_CSV_EXPORT = "Kommt in einer späteren Ausbaustufe (Issue #42 Stufe 2)"
_TT_TREE = "Zellen zeigen beim Hover die wörtlichen Log4OM-Werte; Zeile anklicken für Details"
_TT_COLUMNS = "Blendet ungenutzte Dienst-Spalten aus (Sitzungszustand, Default: alle sichtbar)"
_TT_RESET_FILTERS = "Setzt alle Filter auf Ausgangszustand zurück"
_TT_PRESET = "Setzt Basisfilter/Sammelfilter auf einen Startpunkt — danach frei änderbar"
_TT_ADVANCED_TOGGLE = "Kontinent, DXCC-Land, Sammelfilter und Status je Dienst (rohe Log4OM-Werte)"

_LEGEND_TEXT = (
    "✅ bekommen   ⬆️ gesendet, noch nicht bekommen   – keins   "
    "⊘ ungültig/zurückgewiesen   🕐 Merker (Requested/Queued) auf Sende- oder Empfangsseite"
)

_COLLECTIVE_LABELS: dict[str, CollectiveFilter] = {
    "Alle": CollectiveFilter.ANY,
    "Irgendwo bestätigt": CollectiveFilter.CONFIRMED_ANYWHERE,
    "Nirgends bestätigt": CollectiveFilter.CONFIRMED_NOWHERE,
    "Nur elektronisch": CollectiveFilter.ELECTRONIC_ONLY,
    "Nur Papier": CollectiveFilter.PAPER_ONLY,
    "Bekommen, nicht gesendet (irgendein Dienst)": CollectiveFilter.RECEIVED_NOT_SENT_ANY,
    "Papier bekommen, nicht gesendet": CollectiveFilter.PAPER_RECEIVED_NOT_SENT,
    "Nicht hochgeladen": CollectiveFilter.NOT_UPLOADED_ANYWHERE,
}
_COLLECTIVE_LABELS_REVERSE: dict[CollectiveFilter, str] = {
    v: k for k, v in _COLLECTIVE_LABELS.items()
}

_BASE_COLUMNS: tuple[str, ...] = ("qsodate", "callsign", "band", "mode", "country")
_BASE_HEADINGS: dict[str, str] = {
    "qsodate": "Datum",
    "callsign": "Call",
    "band": "Band",
    "mode": "Mode",
    "country": "Land",
}

# Tooltip-Farben analog gui/tooltip.py (ADR-0047), hier eigenständig für Zell-Hover
# (attach_tooltip bindet nur EIN Widget-weites <Enter>/<Leave> — für Zellen innerhalb
# derselben Treeview braucht es <Motion>-getriebene Positionierung, siehe _on_tree_motion).
_CELL_TOOLTIP_BG = "#ffffcc"
_CELL_TOOLTIP_FG = "#222222"


try:
    import tkinter as tk
    from tkinter import ttk
    _TK_OK = True
except ImportError:
    _TK_OK = False


if _TK_OK:
    class ConfirmationsWindow(tk.Toplevel):
        """Eigenständiges Fenster: Bestätigungsstatus aller QSOs über alle Dienste (read-only)."""

        def __init__(self, parent: tk.Misc, db_path: str | Path | None) -> None:
            super().__init__(parent)
            self.title(_TITLE)
            self.resizable(True, True)

            self._db_path = db_path
            self._all_rows: list = []
            self._filtered_rows: list = []
            self._row_by_iid: dict = {}
            self._column_visibility = ColumnVisibility()
            self._sort_column: str | None = None
            self._sort_ascending = True
            self._loaded_at: str | None = None
            self._last_cell_key = None
            self._cell_tooltip_win = None
            self._tile_value_vars: dict[str, tk.StringVar] = {}
            self._advanced_visible = False

            self._build_ui()
            self._load_async()

        # ------------------------------------------------------------------
        # UI-Aufbau
        # ------------------------------------------------------------------

        def _build_ui(self) -> None:
            from qsl73.gui.tooltip import attach_tooltip

            self._build_metric_tiles(self)

            content = ttk.Frame(self)
            content.pack(fill="both", expand=True)

            filter_frame = ttk.Frame(content, padding=8)
            filter_frame.pack(side="left", fill="y")
            self._build_filters(filter_frame)

            right = ttk.Frame(content, padding=(4, 8))
            right.pack(side="left", fill="both", expand=True)

            tree_frame = ttk.Frame(right)
            tree_frame.pack(fill="both", expand=True)
            self._build_tree(tree_frame)

            self._detail_var = tk.StringVar(value="")
            detail_lbl = ttk.Label(
                right, textvariable=self._detail_var, wraplength=900, justify="left",
                foreground="#333333",
            )
            detail_lbl.pack(fill="x", pady=(6, 0))

            status_outer = ttk.Frame(self, padding=(8, 4))
            status_outer.pack(fill="x")

            ttk.Label(status_outer, text=_LEGEND_TEXT, foreground="#777777", font=("", 8)).pack(
                anchor="w"
            )

            status_row = ttk.Frame(status_outer)
            status_row.pack(fill="x", pady=(2, 0))
            self._status_var = tk.StringVar(value=_LBL_LOADING)
            ttk.Label(status_row, textvariable=self._status_var, foreground="#555555").pack(
                side="left"
            )

            btns = ttk.Frame(status_row)
            btns.pack(side="right")
            self._btn_columns = ttk.Button(btns, text=_LBL_COLUMNS, command=self._on_choose_columns)
            self._btn_columns.pack(side="left", padx=(0, 6))
            attach_tooltip(self._btn_columns, _TT_COLUMNS)
            self._btn_csv = ttk.Button(btns, text=_LBL_CSV_EXPORT, state="disabled")
            self._btn_csv.pack(side="left", padx=(0, 6))
            attach_tooltip(self._btn_csv, _TT_CSV_EXPORT)
            self._btn_reload = ttk.Button(btns, text=_LBL_RELOAD, command=self._on_reload)
            self._btn_reload.pack(side="left")
            attach_tooltip(self._btn_reload, _TT_RELOAD)

            self.minsize(1100, 650)

        def _build_metric_tiles(self, parent: "tk.Misc") -> None:
            tiles_frame = ttk.Frame(parent, padding=(8, 6))
            tiles_frame.pack(fill="x")
            for label in METRIC_TILE_LABELS:
                tile = ttk.Frame(tiles_frame, relief="ridge", borderwidth=1, padding=(10, 6))
                tile.pack(side="left", padx=4, pady=2)
                value_var = tk.StringVar(value="–")
                ttk.Label(
                    tile, textvariable=value_var, font=("", 14, "bold"), anchor="center",
                ).pack()
                ttk.Label(
                    tile, text=label, foreground="#555555", font=("", 8), anchor="center",
                    wraplength=140, justify="center",
                ).pack()
                self._tile_value_vars[label] = value_var

        def _tile_value_vars_by_label(self, label: str) -> str:
            return self._tile_value_vars[label].get()

        def _build_filters(self, frame: "ttk.Frame") -> None:
            from qsl73.gui.tooltip import attach_tooltip

            ttk.Label(frame, text="Schnellansicht").pack(anchor="w")
            self._preset_var = tk.StringVar(value=PRESETS[0].label)
            self._preset_combo = ttk.Combobox(
                frame, textvariable=self._preset_var, values=[p.label for p in PRESETS],
                state="readonly", width=26,
            )
            self._preset_combo.bind("<<ComboboxSelected>>", self._on_preset_selected)
            self._preset_combo.pack(anchor="w", pady=(0, 6))
            attach_tooltip(self._preset_combo, _TT_PRESET)

            self._text_var = tk.StringVar()
            self._text_var.trace_add("write", self._on_filters_changed)
            ttk.Label(frame, text="Freitext (Call/Land/Locator)").pack(anchor="w")
            ttk.Entry(frame, textvariable=self._text_var, width=24).pack(anchor="w", pady=(0, 6))

            ttk.Label(frame, text="Zeitraum (JJJJ-MM-TT)").pack(anchor="w")
            date_frame = ttk.Frame(frame)
            date_frame.pack(anchor="w", pady=(0, 2))
            self._date_start_var = tk.StringVar()
            self._date_end_var = tk.StringVar()
            self._date_start_var.trace_add("write", self._on_filters_changed)
            self._date_end_var.trace_add("write", self._on_filters_changed)
            ttk.Entry(date_frame, textvariable=self._date_start_var, width=11).pack(side="left")
            ttk.Label(date_frame, text=" – ").pack(side="left")
            ttk.Entry(date_frame, textvariable=self._date_end_var, width=11).pack(side="left")

            self._quick_range_var = tk.StringVar(value=QUICK_RANGE_CHOICES[0])
            quick_combo = ttk.Combobox(
                frame, textvariable=self._quick_range_var, values=QUICK_RANGE_CHOICES,
                state="readonly", width=22,
            )
            quick_combo.bind("<<ComboboxSelected>>", self._on_quick_range_selected)
            quick_combo.pack(anchor="w", pady=(0, 6))

            self._band_var, self._band_combo = self._make_filter_combo(frame, "Band")
            self._mode_var, self._mode_combo = self._make_filter_combo(frame, "Mode")

            self._btn_advanced = ttk.Button(
                frame, text=_LBL_ADVANCED_SHOW, command=self._on_toggle_advanced,
            )
            self._btn_advanced.pack(anchor="w", pady=(6, 2))
            attach_tooltip(self._btn_advanced, _TT_ADVANCED_TOGGLE)

            self._advanced_frame = ttk.Frame(frame)
            self._build_advanced_filters(self._advanced_frame)

            reset_btn = ttk.Button(frame, text=_LBL_RESET_FILTERS, command=self._reset_filters)
            reset_btn.pack(anchor="w", pady=(8, 0))
            attach_tooltip(reset_btn, _TT_RESET_FILTERS)

        def _build_advanced_filters(self, frame: "ttk.Frame") -> None:
            self._cont_var, self._cont_combo = self._make_filter_combo(frame, "Kontinent")
            self._country_var, self._country_combo = self._make_filter_combo(frame, "DXCC-Land")

            self._collective_var = tk.StringVar(value=_LBL_ALL)
            ttk.Label(frame, text="Sammelfilter").pack(anchor="w")
            coll_combo = ttk.Combobox(
                frame, textvariable=self._collective_var, values=list(_COLLECTIVE_LABELS.keys()),
                state="readonly", width=30,
            )
            coll_combo.bind("<<ComboboxSelected>>", self._on_filters_changed)
            coll_combo.pack(anchor="w", pady=(0, 6))

            ttk.Separator(frame, orient="horizontal").pack(fill="x", pady=6)
            ttk.Label(frame, text="Status je Dienst (rohe Log4OM-Werte)").pack(anchor="w")

            self._sent_vars: dict[str, tk.StringVar] = {}
            self._recv_vars: dict[str, tk.StringVar] = {}
            self._sent_combos: dict[str, "ttk.Combobox"] = {}
            self._recv_combos: dict[str, "ttk.Combobox"] = {}

            for ct in CONFIRMATION_SERVICES:
                row_frame = ttk.Frame(frame)
                row_frame.pack(anchor="w", pady=1)
                ttk.Label(row_frame, text=SERVICE_LABELS[ct], width=8).pack(side="left")
                sv, sc = self._make_status_combo(row_frame)
                self._sent_vars[ct] = sv
                self._sent_combos[ct] = sc
                rv, rc = self._make_status_combo(row_frame)
                self._recv_vars[ct] = rv
                self._recv_combos[ct] = rc

            ttk.Label(frame, text="Upload-Dienste (nur Gesendet)").pack(anchor="w", pady=(6, 0))
            for ct in UPLOAD_SERVICES:
                row_frame = ttk.Frame(frame)
                row_frame.pack(anchor="w", pady=1)
                ttk.Label(row_frame, text=SERVICE_LABELS[ct], width=8).pack(side="left")
                sv, sc = self._make_status_combo(row_frame)
                self._sent_vars[ct] = sv
                self._sent_combos[ct] = sc

        def _on_toggle_advanced(self) -> None:
            self._advanced_visible = not self._advanced_visible
            if self._advanced_visible:
                self._advanced_frame.pack(anchor="w", fill="x", after=self._btn_advanced)
                self._btn_advanced.configure(text=_LBL_ADVANCED_HIDE)
            else:
                self._advanced_frame.pack_forget()
                self._btn_advanced.configure(text=_LBL_ADVANCED_SHOW)

        def _on_preset_selected(self, _event=None) -> None:
            label = self._preset_var.get()
            preset = next((p for p in PRESETS if p.label == label), PRESETS[0])
            filters = preset_filters(preset)

            self._text_var.set("")
            self._date_start_var.set("")
            self._date_end_var.set("")
            self._quick_range_var.set(QUICK_RANGE_CHOICES[0])
            self._band_var.set(_LBL_ALL)
            self._mode_var.set(_LBL_ALL)
            self._cont_var.set(_LBL_ALL)
            self._country_var.set(_LBL_ALL)
            for var in self._sent_vars.values():
                var.set(_LBL_ALL)
            for var in self._recv_vars.values():
                var.set(_LBL_ALL)

            self._collective_var.set(_COLLECTIVE_LABELS_REVERSE.get(filters.collective, _LBL_ALL))
            for ct, value in filters.received_status.items():
                self._recv_vars[ct].set(value)

            self._on_filters_changed()

        def _make_filter_combo(self, frame: "ttk.Frame", label: str):
            ttk.Label(frame, text=label).pack(anchor="w")
            var = tk.StringVar(value=_LBL_ALL)
            combo = ttk.Combobox(frame, textvariable=var, values=(_LBL_ALL,), state="readonly", width=22)
            combo.bind("<<ComboboxSelected>>", self._on_filters_changed)
            combo.pack(anchor="w", pady=(0, 6))
            return var, combo

        def _make_status_combo(self, row_frame: "ttk.Frame"):
            var = tk.StringVar(value=_LBL_ALL)
            combo = ttk.Combobox(row_frame, textvariable=var, values=(_LBL_ALL,), state="readonly", width=10)
            combo.bind("<<ComboboxSelected>>", self._on_filters_changed)
            combo.pack(side="left", padx=2)
            return var, combo

        def _build_tree(self, frame: "ttk.Frame") -> None:
            from qsl73.gui.tooltip import attach_tooltip

            all_cols = list(_BASE_COLUMNS) + list(SERVICE_COLUMN_ORDER)
            self._tree = ttk.Treeview(
                frame, columns=all_cols, show="headings", selectmode="browse", height=18
            )
            for cid in _BASE_COLUMNS:
                self._tree.heading(cid, text=_BASE_HEADINGS[cid], command=lambda c=cid: self._on_sort_click(c))
            self._tree.column("qsodate", width=140, anchor="w")
            self._tree.column("callsign", width=90, anchor="w")
            self._tree.column("band", width=60, anchor="w")
            self._tree.column("mode", width=70, anchor="w")
            self._tree.column("country", width=140, anchor="w")
            for ct in SERVICE_COLUMN_ORDER:
                self._tree.heading(ct, text=SERVICE_LABELS[ct], command=lambda c=ct: self._on_sort_click(c))
                self._tree.column(ct, width=70, anchor="center")

            self._apply_column_visibility()

            sb = ttk.Scrollbar(frame, orient="vertical", command=self._tree.yview)
            self._tree.configure(yscrollcommand=sb.set)
            sb.pack(side="right", fill="y")
            self._tree.pack(fill="both", expand=True)
            attach_tooltip(self._tree, _TT_TREE)

            self._tree.bind("<<TreeviewSelect>>", self._on_select)
            self._tree.bind("<Motion>", self._on_tree_motion)
            self._tree.bind("<Leave>", lambda _e: self._hide_cell_tooltip())

        # ------------------------------------------------------------------
        # Laden (Hintergrund-Thread + Queue-Polling, ADR-0023-Muster)
        # ------------------------------------------------------------------

        def _load_async(self) -> None:
            self._status_var.set(_LBL_LOADING)
            self._btn_reload.configure(state="disabled")

            db_path = self._db_path
            if not db_path or not Path(db_path).exists():
                self._status_var.set(_MSG_NO_DB)
                self._btn_reload.configure(state="normal")
                return

            result_queue: "queue.Queue" = queue.Queue()

            def _work() -> None:
                try:
                    rows = load_confirmation_data(db_path)
                    result_queue.put((rows, None))
                except Exception as exc:  # noqa: BLE001 — sauberer Klartext statt Absturz
                    result_queue.put((None, exc))

            threading.Thread(target=_work, daemon=True).start()
            self._poll_load(result_queue)

        def _poll_load(self, result_queue: "queue.Queue") -> None:
            try:
                rows, error = result_queue.get_nowait()
            except queue.Empty:
                if self.winfo_exists():
                    self.after(80, lambda: self._poll_load(result_queue))
                return

            self._btn_reload.configure(state="normal")
            if error is not None:
                _log.warning("Bestätigungsdaten konnten nicht geladen werden: %s", error)
                self._status_var.set(_MSG_LOAD_ERROR.format(error=error))
                return

            self._all_rows = rows or []
            self._loaded_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self._populate_filter_choices()
            self._on_filters_changed()

        def _on_reload(self) -> None:
            self._load_async()

        def _populate_filter_choices(self) -> None:
            rows = self._all_rows
            bands = sorted({r.band for r in rows if r.band})
            modes = sorted({r.mode for r in rows if r.mode})
            conts = sorted({r.cont for r in rows if r.cont})
            countries = sorted({r.country for r in rows if r.country})
            self._band_combo["values"] = (_LBL_ALL, *bands)
            self._mode_combo["values"] = (_LBL_ALL, *modes)
            self._cont_combo["values"] = (_LBL_ALL, *conts)
            self._country_combo["values"] = (_LBL_ALL, *countries)

            for ct in CONFIRMATION_SERVICES:
                self._sent_combos[ct]["values"] = (_LBL_ALL, *available_status_values(rows, ct, "s"))
                self._recv_combos[ct]["values"] = (_LBL_ALL, *available_status_values(rows, ct, "r"))
            for ct in UPLOAD_SERVICES:
                self._sent_combos[ct]["values"] = (_LBL_ALL, *available_status_values(rows, ct, "s"))

        # ------------------------------------------------------------------
        # Filter anwenden
        # ------------------------------------------------------------------

        def _build_current_filters(self) -> ConfirmationFilters:
            def _norm(value: str) -> str | None:
                v = (value or "").strip()
                return None if not v or v == _LBL_ALL else v

            sent_status = {
                ct: v for ct in self._sent_vars if (v := _norm(self._sent_vars[ct].get()))
            }
            received_status = {
                ct: v for ct in self._recv_vars if (v := _norm(self._recv_vars[ct].get()))
            }
            collective = _COLLECTIVE_LABELS.get(self._collective_var.get(), CollectiveFilter.ANY)

            return ConfirmationFilters(
                text_query=self._text_var.get(),
                date_start=_norm(self._date_start_var.get()),
                date_end=_norm(self._date_end_var.get()),
                band=_norm(self._band_var.get()),
                mode=_norm(self._mode_var.get()),
                continent=_norm(self._cont_var.get()),
                country=_norm(self._country_var.get()),
                sent_status=sent_status,
                received_status=received_status,
                collective=collective,
            )

        def _on_filters_changed(self, *_args) -> None:
            filters = self._build_current_filters()
            self._filtered_rows = apply_filters(self._all_rows, filters)
            self._refresh_tree_and_metrics()

        def _on_quick_range_selected(self, _event=None) -> None:
            choice = self._quick_range_var.get()
            start, end = quick_range_bounds(choice, date.today())
            self._date_start_var.set(start or "")
            self._date_end_var.set(end or "")

        def _reset_filters(self) -> None:
            self._preset_var.set(PRESETS[0].label)
            self._text_var.set("")
            self._date_start_var.set("")
            self._date_end_var.set("")
            self._quick_range_var.set(QUICK_RANGE_CHOICES[0])
            self._band_var.set(_LBL_ALL)
            self._mode_var.set(_LBL_ALL)
            self._cont_var.set(_LBL_ALL)
            self._country_var.set(_LBL_ALL)
            self._collective_var.set(_LBL_ALL)
            for var in self._sent_vars.values():
                var.set(_LBL_ALL)
            for var in self._recv_vars.values():
                var.set(_LBL_ALL)
            self._on_filters_changed()

        # ------------------------------------------------------------------
        # Tabelle / Kacheln / Statuszeile aktualisieren
        # ------------------------------------------------------------------

        def _row_values(self, row) -> tuple:
            base = (
                (row.qsodate or "–")[:10] if row.qsodate else "–",
                row.callsign or "–",
                row.band or "–",
                row.mode or "–",
                row.country or "–",
            )
            service_cells = tuple(
                cell_display(row.services.get(ct), service_group(ct)) for ct in SERVICE_COLUMN_ORDER
            )
            return base + service_cells

        def _refresh_tree_and_metrics(self) -> None:
            rows = self._filtered_rows
            if self._sort_column:
                rows = sort_rows_by_column(rows, self._sort_column, self._sort_ascending)
            shown, total = apply_display_limit(rows, _DISPLAY_LIMIT)

            self._tree.delete(*self._tree.get_children())
            self._row_by_iid = {}
            for row in shown:
                iid = row.qsoid
                self._tree.insert("", "end", iid=iid, values=self._row_values(row))
                self._row_by_iid[iid] = row

            metrics = compute_metrics(self._filtered_rows)
            values = metric_tile_values(metrics)
            for label, value in zip(METRIC_TILE_LABELS, values):
                self._tile_value_vars[label].set(value)

            loaded_label = self._loaded_at or "noch nicht geladen"
            status = f"{len(self._filtered_rows)} von {len(self._all_rows)} QSOs"
            if total > len(shown):
                status += f"  •  {len(shown)} von {total} angezeigt"
            status += f"  •  Gelesen: {loaded_label}"
            self._status_var.set(status)

            self._update_detail()

        # ------------------------------------------------------------------
        # Auswahl / Detailzeile
        # ------------------------------------------------------------------

        def _on_select(self, _event=None) -> None:
            self._update_detail()

        def _update_detail(self) -> None:
            sel = self._tree.selection()
            if sel:
                row = self._row_by_iid.get(sel[0])
                self._detail_var.set(format_detail_line(row) if row is not None else "")
            else:
                self._detail_var.set("")

        # ------------------------------------------------------------------
        # Klick-Sortierung (ADR-0052-Muster)
        # ------------------------------------------------------------------

        def _on_sort_click(self, column: str) -> None:
            if self._sort_column == column:
                self._sort_ascending = not self._sort_ascending
            else:
                self._sort_column = column
                self._sort_ascending = True
            self._update_sort_headings()
            self._refresh_tree_and_metrics()

        def _update_sort_headings(self) -> None:
            headings = dict(_BASE_HEADINGS)
            headings.update(SERVICE_LABELS)
            for col, base_text in headings.items():
                if col == self._sort_column:
                    arrow = " ▲" if self._sort_ascending else " ▼"
                    self._tree.heading(col, text=base_text + arrow)
                else:
                    self._tree.heading(col, text=base_text)

        # ------------------------------------------------------------------
        # Spaltenwahl (Sitzungszustand, Default alle sichtbar)
        # ------------------------------------------------------------------

        def _apply_column_visibility(self) -> None:
            visible = list(_BASE_COLUMNS) + self._column_visibility.visible_services()
            self._tree.configure(displaycolumns=visible)

        def _on_choose_columns(self) -> None:
            win = tk.Toplevel(self)
            win.title(_LBL_COLUMNS.rstrip("…"))
            win.resizable(False, False)
            for ct in SERVICE_COLUMN_ORDER:
                var = tk.BooleanVar(value=self._column_visibility.is_visible(ct))
                ttk.Checkbutton(
                    win, text=SERVICE_LABELS[ct], variable=var,
                    command=lambda ct=ct, var=var: self._toggle_column(ct, var.get()),
                ).pack(anchor="w", padx=8, pady=2)
            ttk.Button(win, text="Schließen", command=win.destroy).pack(pady=(6, 8))

        def _toggle_column(self, ct: str, value: bool) -> None:
            self._column_visibility.set_visible(ct, value)
            self._apply_column_visibility()

        # ------------------------------------------------------------------
        # Zell-Tooltip (Motion-getrieben, siehe Moduldoc)
        # ------------------------------------------------------------------

        def _on_tree_motion(self, event: "tk.Event") -> None:
            row_id = self._tree.identify_row(event.y)
            col_id = self._tree.identify_column(event.x)
            cell_key = (row_id, col_id)
            if cell_key == self._last_cell_key:
                return
            self._last_cell_key = cell_key
            self._hide_cell_tooltip()
            if not row_id or not col_id:
                return

            display_cols = self._tree["displaycolumns"]
            if display_cols in ("#all", ""):
                display_cols = self._tree["columns"]
            try:
                idx = int(col_id.replace("#", "")) - 1
                column_name = display_cols[idx]
            except (ValueError, IndexError):
                return
            if column_name not in SERVICE_COLUMN_ORDER:
                return

            row = self._row_by_iid.get(row_id)
            if row is None:
                return
            status = row.services.get(column_name)
            text = cell_tooltip_text(column_name, status, service_group(column_name))
            self._show_cell_tooltip(event.x_root, event.y_root, text)

        def _show_cell_tooltip(self, x_root: int, y_root: int, text: str) -> None:
            from qsl73.gui.tooltip import clamp_tooltip_position

            win = tk.Toplevel(self)
            win.wm_overrideredirect(True)
            win.wm_attributes("-topmost", True)
            lbl = tk.Label(
                win, text=text, background=_CELL_TOOLTIP_BG, foreground=_CELL_TOOLTIP_FG,
                relief="solid", borderwidth=1, font=("", 8), padx=4, pady=2, justify="left",
            )
            lbl.pack()
            win.update_idletasks()
            tw, th = win.winfo_reqwidth(), win.winfo_reqheight()
            sw, sh = self._tree.winfo_screenwidth(), self._tree.winfo_screenheight()
            x, y = clamp_tooltip_position(x_root + 12, y_root + 12, tw, th, sw, sh)
            win.wm_geometry(f"+{x}+{y}")
            self._cell_tooltip_win = win

        def _hide_cell_tooltip(self) -> None:
            win = self._cell_tooltip_win
            self._cell_tooltip_win = None
            if win is not None:
                try:
                    win.destroy()
                except Exception:
                    pass

else:
    class ConfirmationsWindow:  # type: ignore[no-redef]
        """Stub — tk ist nicht verfügbar."""
        def __init__(self, *args, **kwargs):
            raise RuntimeError("tkinter ist nicht verfügbar")
