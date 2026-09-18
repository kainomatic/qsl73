# QSL73 — Copyright (C) 2026 DF1DS (kainomatic) — SPDX-License-Identifier: GPL-3.0-or-later
"""Ignorierte-Karten-Fenster (ADR-0059) — Bearbeiten → Ignorierte Karten….

Öffentliche API:
  format_doc_row  — Paperless-Dokument-Dict → (doc_id, title, date)-Anzeigezeile (rein, tk-frei)

tk-abhängig:
  IgnoredCardsWindow — eigenständiges Toplevel, lädt die Liste im Hintergrund neu
                       aus Paperless (Eingangs-Tag + Ignoriert-Tag), Mehrfachauswahl
                       + "Wieder aufnehmen".
"""
from __future__ import annotations

import logging
import queue
import threading
from typing import Optional

_log = logging.getLogger("qsl73")

# i18n-Vorbereitung: nutzersichtbare Texte als Konstanten
_TITLE = "Ignorierte Karten — by DF1DS"
_LBL_UNIGNORE = "Wieder aufnehmen"
_LBL_HINT = "Wieder aufgenommene Karten erscheinen beim nächsten Durchlauf."
_LBL_EMPTY = "Keine ignorierten Karten."
_LBL_LOADING = "Lade…"
_MSG_UNIGNORE_ERROR_TITLE = "Fehler beim Wieder-Aufnehmen"
_MSG_LOAD_ERROR = "Ignorierte Karten konnten nicht geladen werden: {error}"
_TT_TREE = "Doppelklick öffnet eine Bildvorschau der Karte"
_TT_UNIGNORE = "Entfernt den Ignoriert-Tag der ausgewählten Karte(n) — sofort wirksam"

_COL_DEFS = [
    ("id", "Dok-ID", 70),
    ("title", "Titel", 260),
    ("date", "Datum", 110),
]


def format_doc_row(doc: dict) -> tuple[str, str, str]:
    """Formatiert ein Paperless-Dokument-Dict als (doc_id, title, date)-Anzeigezeile.

    date bevorzugt 'created' vor 'added' (beide ISO-Zeitstempel), gekürzt auf
    YYYY-MM-DD. Fehlende Werte → "(ohne Titel)" bzw. "–". Reine Funktion, tk-frei.
    """
    doc_id = str(doc.get("id", "–"))
    title = doc.get("title") or "(ohne Titel)"
    date_raw = doc.get("created") or doc.get("added") or ""
    date = str(date_raw)[:10] if date_raw else "–"
    return doc_id, title, date


try:
    import tkinter as tk
    from tkinter import ttk
    _TK_OK = True
except ImportError:
    _TK_OK = False


if _TK_OK:
    class IgnoredCardsWindow(tk.Toplevel):
        """Eigenständiges Fenster mit der Liste aktuell ignorierter Karten (ADR-0059)."""

        def __init__(self, parent: tk.Misc, client, tags_config) -> None:
            super().__init__(parent)
            self.title(_TITLE)
            self.resizable(True, True)
            self._client = client
            self._tags_config = tags_config
            self._docs: list[dict] = []

            self._build_ui()
            self._load_async()

        # ------------------------------------------------------------------
        # UI-Aufbau
        # ------------------------------------------------------------------

        def _build_ui(self) -> None:
            from qsl73.gui.tooltip import attach_tooltip

            main = ttk.Frame(self, padding=8)
            main.pack(fill="both", expand=True)

            self._status_var = tk.StringVar(value=_LBL_LOADING)
            ttk.Label(main, textvariable=self._status_var, foreground="#555555").pack(
                anchor="w", pady=(0, 4)
            )

            tree_frame = ttk.Frame(main)
            tree_frame.pack(fill="both", expand=True)

            cols = [c[0] for c in _COL_DEFS]
            self._tree = ttk.Treeview(
                tree_frame, columns=cols, show="headings", selectmode="extended", height=14
            )
            for cid, heading, width in _COL_DEFS:
                self._tree.heading(cid, text=heading)
                self._tree.column(cid, width=width, anchor="w")
            sb = ttk.Scrollbar(tree_frame, orient="vertical", command=self._tree.yview)
            self._tree.configure(yscrollcommand=sb.set)
            sb.pack(side="right", fill="y")
            self._tree.pack(fill="both", expand=True)
            attach_tooltip(self._tree, _TT_TREE)
            self._tree.bind("<<TreeviewSelect>>", self._on_select)
            self._tree.bind("<Double-1>", self._on_double_click)

            self._empty_lbl = ttk.Label(main, text=_LBL_EMPTY, foreground="#888888")
            # wird nur bei leerer Liste per pack sichtbar gemacht

            hint_lbl = ttk.Label(main, text=_LBL_HINT, foreground="#555555", font=("", 8))
            hint_lbl.pack(anchor="w", pady=(6, 4))

            btn_frame = ttk.Frame(main)
            btn_frame.pack(fill="x")
            self._btn_unignore = ttk.Button(
                btn_frame, text=_LBL_UNIGNORE, command=self._on_unignore_selected, state="disabled"
            )
            self._btn_unignore.pack(side="left")
            attach_tooltip(self._btn_unignore, _TT_UNIGNORE)

            self.minsize(480, 360)

        # ------------------------------------------------------------------
        # Laden (Hintergrund-Thread + Queue-Polling, ADR-0023-Muster)
        # ------------------------------------------------------------------

        def _load_async(self) -> None:
            self._status_var.set(_LBL_LOADING)
            client = self._client
            tag_names = [self._tags_config.input, self._tags_config.ignored]
            result_queue: "queue.Queue" = queue.Queue()

            def _work() -> None:
                try:
                    docs = client.list_documents_with_all_tags(tag_names)
                    result_queue.put((docs, None))
                except Exception as exc:
                    result_queue.put((None, exc))

            threading.Thread(target=_work, daemon=True).start()
            self._poll_load(result_queue)

        def _poll_load(self, result_queue: "queue.Queue") -> None:
            try:
                docs, error = result_queue.get_nowait()
            except queue.Empty:
                if self.winfo_exists():
                    self.after(80, lambda: self._poll_load(result_queue))
                return
            if error is not None:
                _log.warning("Ignorierte Karten konnten nicht geladen werden: %s", error)
                self._status_var.set(_MSG_LOAD_ERROR.format(error=error))
                return
            self._docs = docs or []
            self._populate()

        def _populate(self) -> None:
            self._tree.delete(*self._tree.get_children())
            for doc in self._docs:
                doc_id, title, date = format_doc_row(doc)
                self._tree.insert("", "end", iid=str(doc.get("id")), values=(doc_id, title, date))
            if self._docs:
                self._empty_lbl.pack_forget()
                self._status_var.set(f"{len(self._docs)} ignorierte Karte(n).")
            else:
                self._empty_lbl.pack(anchor="w", pady=(4, 0))
                self._status_var.set(_LBL_EMPTY)
            self._on_select()

        # ------------------------------------------------------------------
        # Wieder aufnehmen
        # ------------------------------------------------------------------

        def _on_select(self, _event=None) -> None:
            has_sel = bool(self._tree.selection())
            self._btn_unignore.config(state="normal" if has_sel else "disabled")

        def _on_unignore_selected(self) -> None:
            sel = self._tree.selection()
            if not sel:
                return
            doc_ids = [int(iid) for iid in sel]
            self._btn_unignore.config(state="disabled")

            client = self._client
            tags_cfg = self._tags_config
            result_queue: "queue.Queue" = queue.Queue()

            def _work() -> None:
                from qsl73.ignore import unignore_card
                from qsl73.logging_setup import get_log_dir

                log_dir = get_log_dir()
                done_ids: list[int] = []
                errors: list[tuple[int, Exception]] = []
                for doc_id in doc_ids:
                    try:
                        unignore_card(client, doc_id, tags_cfg, log_dir)
                        done_ids.append(doc_id)
                    except Exception as exc:
                        errors.append((doc_id, exc))
                result_queue.put((done_ids, errors))

            threading.Thread(target=_work, daemon=True).start()
            self._poll_unignore(result_queue)

        def _poll_unignore(self, result_queue: "queue.Queue") -> None:
            try:
                done_ids, errors = result_queue.get_nowait()
            except queue.Empty:
                if self.winfo_exists():
                    self.after(80, lambda: self._poll_unignore(result_queue))
                return

            for doc_id in done_ids:
                iid = str(doc_id)
                if self._tree.exists(iid):
                    self._tree.delete(iid)
            done_set = set(done_ids)
            self._docs = [d for d in self._docs if d.get("id") not in done_set]

            if self._docs:
                self._status_var.set(f"{len(self._docs)} ignorierte Karte(n).")
            else:
                self._empty_lbl.pack(anchor="w", pady=(4, 0))
                self._status_var.set(_LBL_EMPTY)
            self._on_select()

            if errors:
                from qsl73.gui.error_dialog import show_error
                msg = "\n".join(f"Dok. {doc_id}: {exc}" for doc_id, exc in errors)
                show_error(self, _MSG_UNIGNORE_ERROR_TITLE, msg)

        # ------------------------------------------------------------------
        # Karte ansehen (Doppelklick)
        # ------------------------------------------------------------------

        def _on_double_click(self, event: "tk.Event") -> None:
            row_id = self._tree.identify_row(event.y)
            if not row_id:
                return
            try:
                doc_id = int(row_id)
            except ValueError:
                return
            self._show_preview(doc_id)

        def _show_preview(self, doc_id: int) -> None:
            """Lädt das PDF im Hintergrund und zeigt die letzte Seite (Rückseite, ADR-0029)."""
            client = self._client
            result_queue: "queue.Queue" = queue.Queue()

            def _work() -> None:
                try:
                    pdf_bytes = client.get_document_download(doc_id)
                    result_queue.put((pdf_bytes, None))
                except Exception as exc:
                    result_queue.put((None, exc))

            threading.Thread(target=_work, daemon=True).start()
            self._poll_preview(result_queue, doc_id)

        def _poll_preview(self, result_queue: "queue.Queue", doc_id: int) -> None:
            try:
                pdf_bytes, error = result_queue.get_nowait()
            except queue.Empty:
                if self.winfo_exists():
                    self.after(80, lambda: self._poll_preview(result_queue, doc_id))
                return

            from qsl73.gui.error_dialog import show_error

            if error is not None or not pdf_bytes:
                show_error(
                    self, "Bild konnte nicht geladen werden",
                    str(error) if error is not None else "Kein Bild verfügbar.",
                )
                return

            from qsl73.gui.manual_assignment import last_page_index, render_pdf_pages

            pages = render_pdf_pages(pdf_bytes)
            if not pages:
                show_error(
                    self, "Kein Bild verfügbar",
                    f"Für Dokument {doc_id} konnte kein Bild gerendert werden.",
                )
                return

            pil_img = pages[last_page_index(len(pages))].copy()
            pil_img.thumbnail((600, 800))
            try:
                from PIL import ImageTk
                photo = ImageTk.PhotoImage(pil_img)
            except Exception as exc:
                _log.debug("Vorschaubild konnte nicht erzeugt werden: %s", exc)
                return

            win = tk.Toplevel(self)
            win.title(f"QSL-Karte {doc_id} — by DF1DS")
            lbl = ttk.Label(win, image=photo)
            lbl.image = photo  # GC-Schutz
            lbl.pack()

else:
    class IgnoredCardsWindow:  # type: ignore[no-redef]
        """Stub — tk ist nicht verfügbar."""
        def __init__(self, *args, **kwargs):
            raise RuntimeError("tkinter ist nicht verfügbar")
