# QSL73 — Copyright (C) 2026 DF1DS (kainomatic) — SPDX-License-Identifier: GPL-3.0-or-later
"""Manueller Zuordnungs-Dialog (Schritt 6c-2/6c-UX, ADR-0037).

Öffentliche API (tk-frei, vollständig ohne Display testbar):
  card_fields_to_query   — CardFields → ManualQuery (OCR-Vorbefüllung)
  field_values_to_query  — Eingabefeld-Strings → ManualQuery
  render_pdf_pages       — PDF-Bytes → list[PIL.Image] (alle Seiten, 150 DPI, Issue #19)
  render_pdf_first_page  — PDF-Bytes → PIL.Image | None (Seite 1; Abwärtskomp.)
  distinct_bands         — list[QsoCandidate] → sortierte Band-Werte aus DB-Kandidaten
  distinct_modes         — list[QsoCandidate] → sortierte Mode-Werte aus DB-Kandidaten
  last_page_index        — Seitenanzahl → Index der letzten Seite (0-basiert)
  wrap_page_index        — Seiten-Umlauf (wrap-around), direction +1/-1
  apply_display_limit    — (candidates, limit) → (shown_list, total_count); ADR-0030

tk-abhängig:
  ManualAssignmentDialog — modales tk.Toplevel; result = (qsoid, route) | None;
                           action: "save" | "save_next" | "skip" | "cancel"
"""
from __future__ import annotations

import io
import logging
from typing import TYPE_CHECKING, Callable, Optional

from qsl73.gui.filter_util import apply_display_limit
from qsl73.gui.manual_match import ManualQuery, make_manual_selection, search_candidates
from qsl73.matching import CardFields, MatchResult, QsoCandidate
from qsl73.run import CardResult

if TYPE_CHECKING:
    pass

_log = logging.getLogger("qsl73")

# i18n-Vorbereitung: nutzersichtbare Texte als Konstanten
_LBL_STATUS_UNCERTAIN = "Unsicher"
_LBL_STATUS_NO_MATCH = "Kein Treffer"
_COLOR_UNCERTAIN = "#b36b00"
_COLOR_NO_MATCH = "#888888"
_BTN_SAVE = "Speichern"
_BTN_SAVE_NEXT = "Speichern und nächste"
_BTN_NEXT = "Nächste"
_BTN_CANCEL = "Abbrechen"

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


def render_pdf_pages(pdf_bytes: bytes) -> list:
    """Rendert alle PDF-Seiten als PIL-Image-Liste (150 DPI — Issue #19/Lesbarkeit).

    Gibt leere Liste zurück wenn pymupdf/Pillow fehlen oder ein Fehler auftritt.
    Kein Absturz; Aufrufer zeigt dann einen Platzhaltertext.
    """
    try:
        import fitz
        PIL_Image = __import__("PIL.Image", fromlist=["Image"])

        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        if doc.page_count == 0:
            return []
        mat = fitz.Matrix(150 / 72, 150 / 72)
        pages = []
        for i in range(doc.page_count):
            pix = doc[i].get_pixmap(matrix=mat)
            img = PIL_Image.open(io.BytesIO(pix.tobytes("png")))
            pages.append(img)
        return pages
    except Exception as exc:
        _log.debug("PDF-Rendering fehlgeschlagen: %s", exc)
        return []


def render_pdf_first_page(pdf_bytes: bytes):
    """Rendert erste PDF-Seite als PIL-Image für die Kartenvorschau.

    Delegiert an render_pdf_pages; gibt None zurück bei Fehler oder leerem PDF.
    Abwärtskompatibel — intern wird jetzt render_pdf_pages (150 DPI) genutzt.
    """
    pages = render_pdf_pages(pdf_bytes)
    return pages[0] if pages else None


def distinct_bands(candidates: list) -> list:
    """Gibt sortierte Liste aller eindeutigen Band-Werte aus den Kandidaten zurück.

    Leere/None-Werte werden übersprungen. Grundlage für Combobox-Vorschläge (ADR-0029).
    """
    seen: set = set()
    result = []
    for c in candidates:
        val = (getattr(c, "band", None) or "").strip()
        if val and val not in seen:
            seen.add(val)
            result.append(val)
    return sorted(result)


def distinct_modes(candidates: list) -> list:
    """Gibt sortierte Liste aller eindeutigen Mode-Werte aus den Kandidaten zurück.

    Leere/None-Werte werden übersprungen. Grundlage für Combobox-Vorschläge (ADR-0029).
    """
    seen: set = set()
    result = []
    for c in candidates:
        val = (getattr(c, "mode", None) or "").strip()
        if val and val not in seen:
            seen.add(val)
            result.append(val)
    return sorted(result)


def last_page_index(page_count: int) -> int:
    """Index der letzten Seite (0-basiert). Gibt 0 zurück wenn page_count == 0."""
    return max(0, page_count - 1)


def wrap_page_index(current: int, page_count: int, direction: int) -> int:
    """Berechnet neuen Seitenindex mit Umlauf (wrap-around).

    direction: +1 = vorwärts, -1 = rückwärts.
    Bei page_count <= 1: gibt current unverändert zurück (kein Umlauf).
    """
    if page_count <= 1:
        return current
    return (current + direction) % page_count


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
        UX: Band/Mode als editierbare Combobox, Datum per tkcalendar DateEntry (mit
        Fallback), Bildanzeige zeigt letzte Seite (Rückseite) zuerst (ADR-0029).
        """

        def __init__(
            self,
            parent: tk.Misc,
            card: CardResult,
            candidates: list[QsoCandidate],
            default_route: str,
            image_loader: Optional[Callable[[int], bytes]] = None,
            limit: int = 100,
            card_status: MatchResult = MatchResult.UNCERTAIN,
            card_index: int = 0,
            total_cards: int = 0,
            has_next: bool = False,
        ) -> None:
            super().__init__(parent)
            self.result: Optional[tuple[str, str]] = None
            self.action: str = "cancel"   # "save"|"save_next"|"skip"|"cancel"
            self._card = card
            self._candidates = candidates
            self._default_route = default_route
            self._image_loader = image_loader
            self._limit = limit           # Anzeige-Limit (ADR-0030); 0 = kein Limit
            self._card_status = card_status
            self._card_index = card_index
            self._total_cards = total_cards
            self._has_next = has_next
            self._img_ref = None          # PIL/tk PhotoImage — vor GC schützen
            self._iid_to_qsoid: dict[str, str] = {}
            self._pages: list = []        # gerenderte Seiten (PIL-Images)
            self._page_idx: int = 0       # aktuell angezeigte Seite
            self._zoom_win = None         # Zoom-Fenster (Toplevel) oder None
            self._use_datepicker: bool = False  # tkcalendar verfügbar?
            self._date_explicit: bool = False   # True sobald Nutzer/OCR Datum gesetzt hat

            self.title("Manuelle Zuordnung — by DF1DS")
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

            # --- Statusleiste: Karten-Phase + Fortschritt ---
            if self._card_index > 0:
                phase_text = (
                    _LBL_STATUS_UNCERTAIN
                    if self._card_status == MatchResult.UNCERTAIN
                    else _LBL_STATUS_NO_MATCH
                )
                phase_color = (
                    _COLOR_UNCERTAIN
                    if self._card_status == MatchResult.UNCERTAIN
                    else _COLOR_NO_MATCH
                )
                status_frame = ttk.Frame(main)
                status_frame.pack(fill="x", pady=(0, 6))
                tk.Label(
                    status_frame,
                    text=phase_text,
                    foreground=phase_color,
                    font=("", 10, "bold"),
                ).pack(side="left")
                tk.Label(
                    status_frame,
                    text=f"  —  Karte {self._card_index} von {self._total_cards}",
                    foreground="#555555",
                ).pack(side="left")

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
                cursor="hand2",
            )
            self._img_label.pack(fill="both", expand=True)
            self._img_label.bind("<Button-1>", self._on_image_click)

            # Blättern-Navigation unter dem Bild
            nav_frame = ttk.Frame(img_frame)
            nav_frame.pack(fill="x", pady=(4, 0))
            self._prev_btn = ttk.Button(
                nav_frame, text="◀", width=3,
                command=self._on_prev_page, state="disabled",
            )
            self._prev_btn.pack(side="left")
            self._page_label = ttk.Label(nav_frame, text="", anchor="center")
            self._page_label.pack(side="left", expand=True, fill="x")
            self._next_btn = ttk.Button(
                nav_frame, text="▶", width=3,
                command=self._on_next_page, state="disabled",
            )
            self._next_btn.pack(side="right")

            # Suchfelder
            fld_frame = ttk.LabelFrame(top, text="Suchfelder (editierbar)", padding=4)
            fld_frame.pack(side="left", fill="both", expand=True)

            self._var_call = tk.StringVar()
            self._var_date = tk.StringVar()   # für Fallback-Entry oder DateEntry-Textwert
            self._var_band = tk.StringVar()
            self._var_mode = tk.StringVar()

            # OCR-Vorbefüllung
            q = card_fields_to_query(self._card.card_fields)
            if q.call:
                self._var_call.set(q.call)
            if q.band:
                self._var_band.set(q.band)
            if q.mode:
                self._var_mode.set(q.mode)

            # Traces für Rufzeichen, Band, Mode
            for var in (self._var_call, self._var_band, self._var_mode):
                var.trace_add("write", self._on_field_change)

            # Row 0 — Rufzeichen
            ttk.Label(fld_frame, text="Rufzeichen:").grid(
                row=0, column=0, sticky="w", padx=(0, 4), pady=2
            )
            ttk.Entry(fld_frame, textvariable=self._var_call, width=20).grid(
                row=0, column=1, sticky="ew", pady=2
            )

            # Row 1 — Datum: DateEntry (tkcalendar) mit Fallback auf Entry
            ttk.Label(fld_frame, text="Datum:").grid(
                row=1, column=0, sticky="w", padx=(0, 4), pady=2
            )
            try:
                from tkcalendar import DateEntry
                self._date_entry = DateEntry(
                    fld_frame, width=18, date_pattern="yyyy-MM-dd"
                )
                if q.date:
                    try:
                        from datetime import datetime as _dt
                        self._date_entry.set_date(
                            _dt.strptime(q.date, "%Y-%m-%d").date()
                        )
                        self._date_explicit = True
                    except Exception:
                        pass
                self._date_entry.bind(
                    "<<DateEntrySelected>>", self._on_date_changed
                )
                self._date_entry.bind(
                    "<KeyRelease>", self._on_date_changed
                )
                self._use_datepicker = True
            except ImportError:
                _log.warning(
                    "tkcalendar nicht verfügbar — Datum als Textfeld (Format: YYYY-MM-DD)"
                )
                self._date_entry = ttk.Entry(
                    fld_frame, textvariable=self._var_date, width=20
                )
                if q.date:
                    self._var_date.set(q.date)
                self._var_date.trace_add("write", self._on_field_change)
                self._use_datepicker = False
            self._date_entry.grid(row=1, column=1, sticky="ew", pady=2)

            # Grab-Konflikt: DateEntry-Kalender-Popup vs. grab_set() auf dem Dialog.
            # Wenn der Kalender aufklappt (Map), Grab freigeben; beim Schließen (Unmap)
            # Grab neu setzen. Nur wenn tkcalendar die interne API _top_cal hat.
            if self._use_datepicker:
                try:
                    _cal = self._date_entry._top_cal
                    _cal.bind("<Map>", lambda _e: self.grab_release())
                    _cal.bind("<Unmap>", lambda _e: self.after(10, self._try_regrab))
                except AttributeError:
                    pass  # tkcalendar-interne API nicht verfügbar

            # Row 2 — Band: Combobox mit DB-Kandidaten-Werten
            bands = distinct_bands(self._candidates)
            ttk.Label(fld_frame, text="Band:").grid(
                row=2, column=0, sticky="w", padx=(0, 4), pady=2
            )
            ttk.Combobox(
                fld_frame, textvariable=self._var_band,
                values=bands, width=18,
            ).grid(row=2, column=1, sticky="ew", pady=2)

            # Row 3 — Mode: Combobox mit DB-Kandidaten-Werten
            modes = distinct_modes(self._candidates)
            ttk.Label(fld_frame, text="Mode:").grid(
                row=3, column=0, sticky="w", padx=(0, 4), pady=2
            )
            ttk.Combobox(
                fld_frame, textvariable=self._var_mode,
                values=modes, width=18,
            ).grid(row=3, column=1, sticky="ew", pady=2)

            fld_frame.columnconfigure(1, weight=1)

            # --- Trefferliste ---
            self._res_frame = ttk.LabelFrame(main, text="Gefundene QSOs", padding=4)
            self._res_frame.pack(fill="both", expand=True, pady=(0, 8))
            res_frame = self._res_frame

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
                btn_frame, text=_BTN_CANCEL, command=self._on_cancel
            ).pack(side="right", padx=(4, 0))

            self._btn_save = ttk.Button(
                btn_frame, text=_BTN_SAVE, command=self._on_save, state="disabled"
            )
            self._btn_save.pack(side="right", padx=(4, 0))

            _next_state = "normal" if self._has_next else "disabled"
            self._btn_save_next = ttk.Button(
                btn_frame, text=_BTN_SAVE_NEXT, command=self._on_save_next,
                state="disabled",
            )
            self._btn_save_next.pack(side="right", padx=(4, 0))

            self._btn_next = ttk.Button(
                btn_frame, text=_BTN_NEXT, command=self._on_next_card,
                state=_next_state,
            )
            self._btn_next.pack(side="right", padx=(4, 0))

        # ------------------------------------------------------------------
        # Event-Handler
        # ------------------------------------------------------------------

        def _on_field_change(self, *_args) -> None:
            self._update_search()

        def _on_date_changed(self, _event=None) -> None:
            """DateEntry-Event: Nutzer hat Datum explizit gesetzt → Datumsfilter aktiv."""
            self._date_explicit = True
            self._update_search()

        def _on_tree_select(self, _event=None) -> None:
            has_sel = bool(self._tree.selection())
            self._btn_save.config(state="normal" if has_sel else "disabled")
            save_next_state = "normal" if (has_sel and self._has_next) else "disabled"
            self._btn_save_next.config(state=save_next_state)

        def _resolve_selection(self) -> Optional[tuple[str, str]]:
            """Liest die gewählte Treeview-Zeile und gibt (qsoid, route) zurück, oder None."""
            sel = self._tree.selection()
            if not sel:
                return None
            qsoid = self._iid_to_qsoid.get(sel[0])
            if qsoid is None:
                return None
            try:
                return make_manual_selection(qsoid, self._default_route)
            except ValueError as exc:
                _log.warning("make_manual_selection fehlgeschlagen: %s", exc)
                return None

        def _on_save(self) -> None:
            self.result = self._resolve_selection()
            if self.result is None:
                return
            self.action = "save"
            self.destroy()

        def _on_save_next(self) -> None:
            self.result = self._resolve_selection()
            if self.result is None:
                return
            self.action = "save_next"
            self.destroy()

        def _on_next_card(self) -> None:
            self.result = None
            self.action = "skip"
            self.destroy()

        def _on_cancel(self) -> None:
            self.result = None
            self.action = "cancel"
            self.destroy()

        def _on_prev_page(self) -> None:
            n = len(self._pages)
            if n > 1:
                self._show_page(wrap_page_index(self._page_idx, n, -1))

        def _on_next_page(self) -> None:
            n = len(self._pages)
            if n > 1:
                self._show_page(wrap_page_index(self._page_idx, n, +1))

        def _try_regrab(self) -> None:
            try:
                if self.winfo_exists():
                    self.grab_set()
            except Exception:
                pass

        def _on_image_click(self, _event=None) -> None:
            """Klick auf Kartenbild: Zoom-Fenster öffnen oder schließen."""
            if not self._pages:
                return  # Noch kein Bild geladen — no-op
            if self._zoom_win is not None and self._zoom_win.winfo_exists():
                self._zoom_win.destroy()
                self._zoom_win = None
                return
            self._open_zoom_window()

        def _open_zoom_window(self) -> None:
            """Öffnet Zoom-Toplevel mit aktueller Seite in Originalgröße."""
            if not self._pages:
                return
            pil_img = self._pages[self._page_idx]
            screen_w = self.winfo_screenwidth()
            screen_h = self.winfo_screenheight()
            max_w = int(screen_w * 0.9)
            max_h = int(screen_h * 0.9)

            display_img = pil_img.copy()
            img_w, img_h = display_img.size
            if img_w > max_w or img_h > max_h:
                display_img.thumbnail((max_w, max_h))

            try:
                from PIL import ImageTk
                photo = ImageTk.PhotoImage(display_img)
            except Exception as exc:
                _log.debug("Zoom-Bild konnte nicht erzeugt werden: %s", exc)
                return

            win = tk.Toplevel(self)
            win.title(f"QSL-Karte — Seite {self._page_idx + 1}/{len(self._pages)} — by DF1DS")
            win.resizable(False, False)

            lbl = ttk.Label(win, image=photo, cursor="hand2")
            lbl.image_ref = photo  # GC-Schutz
            lbl.pack()

            def _close_zoom(_e=None):
                win.destroy()
                self._zoom_win = None

            lbl.bind("<Button-1>", _close_zoom)
            win.bind("<Escape>", _close_zoom)

            dw, dh = display_img.size
            x = max(0, (screen_w - dw) // 2)
            y = max(0, (screen_h - dh) // 2)
            win.geometry(f"+{x}+{y}")
            self._zoom_win = win

        # ------------------------------------------------------------------
        # Such-Logik
        # ------------------------------------------------------------------

        def _get_date_str(self) -> str:
            """Gibt aktuellen Datumswert als YYYY-MM-DD-String zurück.

            Bei DateEntry nur wenn der Nutzer (oder OCR-Vorbefüllung) explizit ein
            Datum gesetzt hat (_date_explicit). Sonst leer → kein Datumsfilter.
            DateEntry zeigt immer ein Datum (Standard: heute), aber das darf nicht
            als impliziter Filter gelten.
            """
            if self._use_datepicker:
                if not self._date_explicit:
                    return ""
                try:
                    return self._date_entry.get_date().strftime("%Y-%m-%d")
                except Exception:
                    return self._date_entry.get()
            return self._var_date.get()

        def _update_search(self) -> None:
            query = field_values_to_query(
                self._var_call.get(),
                self._get_date_str(),
                self._var_band.get(),
                self._var_mode.get(),
            )
            results = search_candidates(query, self._candidates)
            self._populate_tree(results)

        def _populate_tree(self, candidates: list[QsoCandidate]) -> None:
            self._tree.delete(*self._tree.get_children())
            self._iid_to_qsoid.clear()
            self._btn_save.config(state="disabled")
            self._btn_save_next.config(state="disabled")

            shown, total = apply_display_limit(candidates, self._limit)
            if total > len(shown):
                self._res_frame.config(
                    text=f"Gefundene QSOs  (zeige {len(shown)} von {total})"
                )
            else:
                self._res_frame.config(
                    text=f"Gefundene QSOs  ({total} Treffer)" if total else "Gefundene QSOs"
                )

            for cand in shown:
                date_str = cand.date[:10] if cand.date else ""
                iid = self._tree.insert(
                    "", "end",
                    values=(cand.callsign, date_str, cand.band, cand.mode),
                )
                self._iid_to_qsoid[iid] = cand.qsoid

        # ------------------------------------------------------------------
        # Bildladen und Seitennavigation (lazy, nicht-blockierend)
        # ------------------------------------------------------------------

        def _load_image(self) -> None:
            """Lädt alle PDF-Seiten; zeigt standardmäßig die letzte (Rückseite) zuerst."""
            if self._image_loader is None:
                self._img_label.config(text="[Kein Bild-Loader konfiguriert]")
                return
            try:
                pdf_bytes = self._image_loader(self._card.doc_id)
                self._pages = render_pdf_pages(pdf_bytes)
                if not self._pages:
                    self._img_label.config(text="[Kein Bild verfügbar]")
                    return
                # Rückseite zuerst (Discovery §5.3, ADR-0029)
                self._page_idx = last_page_index(len(self._pages))
                self._show_page(self._page_idx)
            except Exception as exc:
                _log.debug("Bild konnte nicht geladen werden: %s", exc)
                self._img_label.config(text="[Bild konnte nicht geladen werden]")

        def _show_page(self, idx: int) -> None:
            """Zeigt Seite idx an und aktualisiert Blättern-Buttons."""
            if not self._pages:
                return
            idx = max(0, min(idx, len(self._pages) - 1))
            self._page_idx = idx

            pil_img = self._pages[idx].copy()
            pil_img.thumbnail((300, 400))
            try:
                from PIL import ImageTk
                photo = ImageTk.PhotoImage(pil_img)
                self._img_ref = photo
                self._img_label.config(image=photo, text="")
            except Exception as exc:
                _log.debug("Bild-Anzeige fehlgeschlagen: %s", exc)
                self._img_label.config(text="[Bild-Anzeige fehlgeschlagen]")

            n = len(self._pages)
            self._page_label.config(text=f"Seite {idx + 1}/{n}")
            active = "normal" if n > 1 else "disabled"
            self._prev_btn.config(state=active)
            self._next_btn.config(state=active)

else:
    # Stub damit Tests den Import nicht brechen wenn tk fehlt
    class ManualAssignmentDialog:  # type: ignore[no-redef]
        """Stub — tk ist nicht verfügbar."""
        def __init__(self, *args, **kwargs):
            raise RuntimeError("tkinter ist nicht verfügbar")
