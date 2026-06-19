# QSL73 — Copyright (C) 2026 DF1DS (kainomatic) — SPDX-License-Identifier: GPL-3.0-or-later
"""Modaler Update-Hinweis-Dialog. Kein Systemsound (ADR-0037-Konvention)."""
from __future__ import annotations

import logging
import threading
from pathlib import Path
from typing import Callable, Optional

import tkinter as tk
from tkinter import ttk

from qsl73.updater import AssetInfo, download_update

_log = logging.getLogger("qsl73.updater")

# i18n-Vorbereitung
_TITLE = "Update verfügbar — by DF1DS"
_LBL_CURRENT = "Aktuelle Version:"
_LBL_NEW = "Neue Version:"
_LBL_RELEASE_LINK = "Release-Notes auf GitHub ansehen"
_LBL_DOWNLOADING = "Lädt herunter …"
_CHK_DONT_REMIND = "Nicht mehr an Updates erinnern"
_BTN_INSTALL = "Herunterladen und installieren"
_BTN_LATER = "Später"
_ERR_PREFIX = "Download fehlgeschlagen:"


class UpdateDialog(tk.Toplevel):
    """Update-Dialog mit Download-Fortschritt.

    Callbacks:
      on_install: aufgerufen mit Pfad zur heruntergeladenen Datei → startet Installer + Exit
      on_opt_out: aufgerufen wenn „Nicht mehr erinnern" + Später → setzt update_check=False
    """

    def __init__(
        self,
        parent: tk.Misc,
        current_version: str,
        new_version: str,
        asset: AssetInfo,
        release_url: Optional[str],
        on_install: Callable[[Path], None],
        on_opt_out: Callable[[], None],
    ) -> None:
        super().__init__(parent)
        self.title(_TITLE)
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self._asset = asset
        self._on_install = on_install
        self._on_opt_out = on_opt_out
        self._dont_remind = tk.BooleanVar(value=False)
        self._downloading = False

        from qsl73.gui._icon import apply_window_icon
        apply_window_icon(self)

        self._build_ui(current_version, new_version, release_url)
        self._center(parent)
        self.bind("<Escape>", lambda _e: self._on_later())

    def _build_ui(self, current_version: str, new_version: str, release_url: Optional[str]) -> None:
        outer = ttk.Frame(self, padding=20)
        outer.pack(fill="both", expand=True)

        # Versions-Info
        info = ttk.Frame(outer)
        info.pack(fill="x", pady=(0, 10))
        ttk.Label(info, text=_LBL_CURRENT).grid(row=0, column=0, sticky="w", padx=(0, 10))
        ttk.Label(info, text=f"v{current_version}").grid(row=0, column=1, sticky="w")
        ttk.Label(info, text=_LBL_NEW).grid(row=1, column=0, sticky="w", padx=(0, 10))
        ttk.Label(info, text=f"v{new_version}", font=("", 10, "bold")).grid(row=1, column=1, sticky="w")

        # Release-Notes-Link
        if release_url:
            import webbrowser
            lnk = tk.Label(outer, text=_LBL_RELEASE_LINK, fg="#0645ad", cursor="hand2", font=("", 9))
            lnk.pack(anchor="w", pady=(4, 0))
            lnk.bind("<Button-1>", lambda _e, u=release_url: webbrowser.open(u))
            lnk.bind("<Enter>", lambda _e: lnk.config(font=("", 9, "underline")))
            lnk.bind("<Leave>", lambda _e: lnk.config(font=("", 9)))

        ttk.Separator(outer, orient="horizontal").pack(fill="x", pady=(14, 0))

        # Fortschritts-Bereich (anfangs versteckt)
        self._progress_frame = ttk.Frame(outer, padding=(0, 10, 0, 0))
        self._progress_lbl = ttk.Label(self._progress_frame, text=_LBL_DOWNLOADING)
        self._progress_lbl.pack(anchor="w", pady=(0, 4))
        self._progress = ttk.Progressbar(self._progress_frame, length=380, mode="indeterminate")
        self._progress.pack(fill="x")

        # Fehler-Label (anfangs versteckt)
        self._error_var = tk.StringVar(value="")
        self._error_lbl = ttk.Label(
            outer,
            textvariable=self._error_var,
            foreground="#cc0000",
            wraplength=380,
            padding=(0, 8, 0, 0),
        )

        # Buttons
        btn_frame = ttk.Frame(outer, padding=(0, 14, 0, 0))
        btn_frame.pack(fill="x", side="bottom")

        ttk.Checkbutton(btn_frame, text=_CHK_DONT_REMIND, variable=self._dont_remind).pack(side="left")

        self._later_btn = ttk.Button(btn_frame, text=_BTN_LATER, command=self._on_later)
        self._later_btn.pack(side="right", padx=(8, 0))

        self._install_btn = ttk.Button(btn_frame, text=_BTN_INSTALL, command=self._on_download_install)
        self._install_btn.pack(side="right")

    def _center(self, parent: tk.Misc) -> None:
        self.update_idletasks()
        dw = max(440, self.winfo_reqwidth())
        dh = self.winfo_reqheight()
        try:
            px, py = parent.winfo_rootx(), parent.winfo_rooty()
            pw, ph = parent.winfo_width(), parent.winfo_height()
        except Exception:
            px, py, pw, ph = 200, 200, 800, 600
        x = max(0, px + (pw - dw) // 2)
        y = max(0, py + (ph - dh) // 2)
        self.geometry(f"{dw}x{dh}+{x}+{y}")

    # ------------------------------------------------------------------

    def _show_progress(self) -> None:
        self._error_lbl.pack_forget()
        self._progress_frame.pack(fill="x")
        self._progress.configure(mode="indeterminate")
        self._progress.start(40)

    def _update_progress_determinate(self, done: int, total: int) -> None:
        if total > 0 and done <= total:
            self._progress.stop()
            self._progress.configure(mode="determinate", maximum=total, value=done)

    def _hide_progress(self) -> None:
        self._progress.stop()
        self._progress_frame.pack_forget()

    def _show_error(self, msg: str) -> None:
        self._hide_progress()
        self._error_var.set(f"{_ERR_PREFIX}\n{msg}")
        self._error_lbl.pack(fill="x")
        self._install_btn.configure(state="normal")
        self._later_btn.configure(state="normal")
        self._downloading = False

    # ------------------------------------------------------------------

    def _on_download_install(self) -> None:
        if self._downloading:
            return
        self._downloading = True
        self._install_btn.configure(state="disabled")
        self._later_btn.configure(state="disabled")
        self._show_progress()

        def _progress_cb(done: int, total: int) -> None:
            self.after(0, lambda d=done, t=total: self._update_progress_determinate(d, t))

        def _do_download() -> None:
            try:
                path = download_update(self._asset, on_progress=_progress_cb)
                self.after(0, lambda: self._on_download_done(path))
            except Exception as exc:
                _log.exception("Update-Download fehlgeschlagen")
                self.after(0, lambda e=str(exc): self._show_error(e))

        threading.Thread(target=_do_download, daemon=True).start()

    def _on_download_done(self, path: Path) -> None:
        self._hide_progress()
        self._on_install(path)

    def _on_later(self) -> None:
        if self._dont_remind.get():
            self._on_opt_out()
        self.destroy()
