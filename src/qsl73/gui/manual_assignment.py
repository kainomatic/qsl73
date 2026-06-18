# QSL73 — Copyright (C) 2026 DF1DS (kainomatic) — SPDX-License-Identifier: GPL-3.0-or-later
"""Manueller Zuordnungs-Dialog (Schritt 6c-2).

Öffentliche API:
  card_fields_to_query   — tk-frei: CardFields → ManualQuery (OCR-Vorbefüllung)
  field_values_to_query  — tk-frei: Eingabefeld-Strings → ManualQuery
  render_pdf_first_page  — tk-frei: PDF-Bytes → PIL-Image | None (lazy-Bildhilfe)
  ManualAssignmentDialog — modales tk.Toplevel; result = (qsoid, route) | None
"""
from __future__ import annotations

import io
import logging
from typing import TYPE_CHECKING, Callable, Optional

from qsl73.gui.manual_match import ManualQuery, make_manual_selection, search_candidates
from qsl73.matching import CardFields, QsoCandidate
from qsl73.run import CardResult

if TYPE_CHECKING:
    pass

_log = logging.getLogger("qsl73")

# ---------------------------------------------------------------------------
# Reine Helfer — tk-frei, vollständig ohne Display testbar
# ---------------------------------------------------------------------------


def card_fields_to_query(card_fields: CardFields) -> ManualQuery:
    """Befüllt ManualQuery aus OCR/QR-extrahierten CardFields.

    call_from (Absender der Karte) wird als Rufzeichen-Suchfeld verwendet.
    Leere Strings und None bleiben None (kein Filter).
    """
    return ManualQuery(
        call=card_fields.call_from or None,
        date=card_fields.date or None,
        band=card_fields.band or None,
        mode=card_fields.mode or None,
    )


def field_values_to_query(call: str, date: str, band: str, mode: str) -> ManualQuery:
    """Baut ManualQuery aus rohen Eingabefeld-Strings.

    Leere Strings (auch nach strip()) werden zu None — kein Filter für das Feld.
    """
    return ManualQuery(
        call=call.strip() or None,
        date=date.strip() or None,
        band=band.strip() or None,
        mode=mode.strip() or None,
    )


def render_pdf_first_page(pdf_bytes: bytes):
    """Rendert erste PDF-Seite als PIL-Image (~100 DPI) für die Kartenvorschau.

    Gibt None zurück wenn pymupdf/Pillow fehlen oder ein Fehler auftritt.
    Kein Absturz; Aufrufer zeigt dann einen Platzhaltertext.
    """
    try:
        import fitz
        from PIL import Image  # noqa: F401 — Existenzprüfung

        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        if doc.page_count == 0:
            return None
        mat = fitz.Matrix(100 / 72, 100 / 72)
        pix = doc[0].get_pixmap(matrix=mat)
        return __import__("PIL.Image", fromlist=["Image"]).open(
            io.BytesIO(pix.tobytes("png"))
        )
    except Exception as exc:
        _log.debug("PDF-Rendering fehlgeschlagen: %s", exc)
        return None


# ---------------------------------------------------------------------------
# tk-Toplevel — nur importieren wenn tk verfügbar
# ---------------------------------------------------------------------------

try:
    import tkinter as tk
    from tkinter import ttk
    _TK_OK = True
except ImportError:
    _TK_OK = False


if _TK_OK:
    class ManualAssignmentDialog(tk.Toplevel):
        """Modaler Dialog zur manuellen Zuordnung einer UNCERTAIN-Karte.

        Konstruktor blockiert (wait_window) bis der Nutzer Übernehmen/Abbrechen klickt.
        Danach ist ``self.result`` entweder (qsoid, route) oder None.

        Kein DB-Zugriff, kein Schreiben (ADR-0028). Suchraum = übergebene candidates.
        """

        def __init__(
            self,
            parent: tk.Misc,
            card: CardResult,
            candidates: list[QsoCandidate],
            default_route: str,
            image_loader: Optional[Callable[[int], bytes]] = None,
        ) -> None:
            super().__init__(parent)
            self.result: Optional[tuple[str, str]] = None
            self._card = card
            self._candidates = candidates
            self._default_route = default_route
            self._image_loader = image_loader
            self._img_ref = None          # PIL/tk PhotoImage — vor GC schützen
            self._iid_to_qsoid: dict[str, str] = {}

            self.title("Manuelle Zuordnung")
            self.resizable(True, True)
            self.grab_set()

            self._build_ui()
            self._update_search()

            # Bild lazy nachladen — NACH Dialog-Anzeige, damit der Start nicht blockiert
            if image_loader is not None:
                self.after(50, self._load_image)

            self.wait_window()

        # ------------------------------------------------------------------
        # Layout-Aufbau
        # ------------------------------------------------------------------

        def _build_ui(self) -> None:
            main = ttk.Frame(self, padding=8)
            main.pack(fill="both", expand=True)

            # --- Obere Reihe: Kartenbild links, Suchfelder rechts ---
            top = ttk.Frame(main)
            top.pack(fill="x", pady=(0, 8))

            # Kartenbild-Bereich
            img_frame = ttk.LabelFrame(top, text="QSL-Karte", padding=4)
            img_frame.pack(side="left", fill="both", padx=(0, 8))
            self._img_label = ttk.Label(
                img_frame,
                text="Bild wird geladen…",
                width=32,
                anchor="center",
                justify="center",
            )
            self._img_label.pack(fill="both", expand=True)

            # Suchfelder
            fld_frame = ttk.LabelFrame(top, text="Suchfelder (editierbar)", padding=4)
            fld_frame.pack(side="left", fill="both", expand=True)

            self._var_call = tk.StringVar()
            self._var_date = tk.StringVar()
            self._var_band = tk.StringVar()
            self._var_mode = tk.StringVar()

            # OCR-Vorbefüllung
            q = card_fields_to_query(self._card.card_fields)
            if q.call:
                self._var_call.set(q.call)
            if q.date:
                self._var_date.set(q.date)
            if q.band:
                self._var_band.set(q.band)
            if q.mode:
                self._var_mode.set(q.mode)

            for var in (self._var_call, self._var_date, self._var_band, self._var_mode):
                var.trace_add("write", self._on_field_change)

            for row, (lbl, var) in enumerate([
                ("Rufzeichen:", self._var_call),
                ("Datum:", self._var_date),
                ("Band:", self._var_band),
                ("Mode:", self._var_mode),
            ]):
                ttk.Label(fld_frame, text=lbl).grid(
                    row=row, column=0, sticky="w", padx=(0, 4), pady=2
                )
                ttk.Entry(fld_frame, textvariable=var, width=20).grid(
                    row=row, column=1, sticky="ew", pady=2
                )
            fld_frame.columnconfigure(1, weight=1)

            # --- Trefferliste ---
            res_frame = ttk.LabelFrame(main, text="Gefundene QSOs", padding=4)
            res_frame.pack(fill="both", expand=True, pady=(0, 8))

            cols = ("callsign", "date", "band", "mode")
            self._tree = ttk.Treeview(
                res_frame, columns=cols, show="headings", height=8, selectmode="browse"
            )
            col_defs = [
                ("callsign", "Rufzeichen", 130),
                ("date",     "Datum",      100),
                ("band",     "Band",        60),
                ("mode",     "Mode",        60),
            ]
            for cid, heading, width in col_defs:
                self._tree.heading(cid, text=heading)
                self._tree.column(cid, width=width, anchor="w", stretch=True)

            sb = ttk.Scrollbar(res_frame, orient="vertical", command=self._tree.yview)
            self._tree.configure(yscrollcommand=sb.set)
            sb.pack(side="right", fill="y")
            self._tree.pack(fill="both", expand=True)
            self._tree.bind("<<TreeviewSelect>>", self._on_tree_select)

            # --- Schaltflächen ---
            btn_frame = ttk.Frame(main)
            btn_frame.pack(fill="x")

            ttk.Button(
                btn_frame, text="Abbrechen", command=self._on_cancel
            ).pack(side="right", padx=(4, 0))
            self._btn_ok = ttk.Button(
                btn_frame, text="Übernehmen", command=self._on_ok, state="disabled"
            )
            self._btn_ok.pack(side="right")

        # ------------------------------------------------------------------
        # Event-Handler
        # ------------------------------------------------------------------

        def _on_field_change(self, *_args) -> None:
            self._update_search()

        def _on_tree_select(self, _event=None) -> None:
            has_sel = bool(self._tree.selection())
            self._btn_ok.config(state="normal" if has_sel else "disabled")

        def _on_ok(self) -> None:
            sel = self._tree.selection()
            if not sel:
                return
            qsoid = self._iid_to_qsoid.get(sel[0])
            if qsoid is None:
                return
            try:
                self.result = make_manual_selection(qsoid, self._default_route)
            except ValueError as exc:
                _log.warning("make_manual_selection fehlgeschlagen: %s", exc)
                self.result = None
            self.destroy()

        def _on_cancel(self) -> None:
            self.result = None
            self.destroy()

        # ------------------------------------------------------------------
        # Such-Logik
        # ------------------------------------------------------------------

        def _update_search(self) -> None:
            query = field_values_to_query(
                self._var_call.get(),
                self._var_date.get(),
                self._var_band.get(),
                self._var_mode.get(),
            )
            results = search_candidates(query, self._candidates)
            self._populate_tree(results)

        def _populate_tree(self, candidates: list[QsoCandidate]) -> None:
            self._tree.delete(*self._tree.get_children())
            self._iid_to_qsoid.clear()
            self._btn_ok.config(state="disabled")
            for cand in candidates:
                date_str = cand.date[:10] if cand.date else ""
                iid = self._tree.insert(
                    "", "end",
                    values=(cand.callsign, date_str, cand.band, cand.mode),
                )
                self._iid_to_qsoid[iid] = cand.qsoid

        # ------------------------------------------------------------------
        # Bildladen (lazy, nicht-blockierend)
        # ------------------------------------------------------------------

        def _load_image(self) -> None:
            """Lädt Kartenbild im Hintergrund nach Dialog-Anzeige (ADR-Stufe-2)."""
            if self._image_loader is None:
                self._img_label.config(text="[Kein Bild-Loader konfiguriert]")
                return
            try:
                pdf_bytes = self._image_loader(self._card.doc_id)
                pil_img = render_pdf_first_page(pdf_bytes)
                if pil_img is None:
                    self._img_label.config(text="[Kein Bild verfügbar]")
                    return
                pil_img.thumbnail((300, 400))
                from PIL import ImageTk
                photo = ImageTk.PhotoImage(pil_img)
                self._img_ref = photo
                self._img_label.config(image=photo, text="")
            except Exception as exc:
                _log.debug("Bild konnte nicht geladen werden: %s", exc)
                self._img_label.config(text="[Bild konnte nicht geladen werden]")

else:
    # Stub damit Tests den Import nicht brechen wenn tk fehlt
    class ManualAssignmentDialog:  # type: ignore[no-redef]
        """Stub — tk ist nicht verfügbar."""
        def __init__(self, *args, **kwargs):
            raise RuntimeError("tkinter ist nicht verfügbar")
