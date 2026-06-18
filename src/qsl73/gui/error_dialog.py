# QSL73 — Copyright (C) 2026 DF1DS (kainomatic) — SPDX-License-Identifier: GPL-3.0-or-later
"""Einfacher Fehler-Dialog mit aufklappbarem Traceback."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk


def show_error(
    parent: tk.Misc | None,
    title: str,
    message: str,
    detail: str = "",
) -> None:
    """Zeigt einen modalen Fehler-Dialog. detail wird in einem aufklappbaren Bereich angezeigt."""
    dlg = tk.Toplevel(parent)
    dlg.title(f"{title} — by DF1DS")
    dlg.resizable(False, False)
    dlg.grab_set()

    frm = ttk.Frame(dlg, padding=12)
    frm.pack(fill="both", expand=True)

    ttk.Label(frm, text=message, wraplength=400, justify="left").pack(anchor="w")

    if detail:
        expanded = tk.BooleanVar(value=False)
        detail_frame = ttk.Frame(frm)

        def _toggle():
            if expanded.get():
                detail_frame.pack(fill="both", expand=True, pady=(6, 0))
                toggle_btn.config(text="▲ Details ausblenden")
            else:
                detail_frame.pack_forget()
                toggle_btn.config(text="▼ Details anzeigen")
            dlg.update_idletasks()

        toggle_btn = ttk.Button(frm, text="▼ Details anzeigen",
                                command=lambda: [expanded.set(not expanded.get()), _toggle()])
        toggle_btn.pack(anchor="w", pady=(6, 0))

        txt = tk.Text(detail_frame, height=10, width=60, state="normal",
                      font=("Courier New", 9), wrap="none")
        sb_y = ttk.Scrollbar(detail_frame, orient="vertical", command=txt.yview)
        sb_x = ttk.Scrollbar(detail_frame, orient="horizontal", command=txt.xview)
        txt.configure(yscrollcommand=sb_y.set, xscrollcommand=sb_x.set)
        txt.insert("1.0", detail)
        txt.configure(state="disabled")
        sb_y.pack(side="right", fill="y")
        sb_x.pack(side="bottom", fill="x")
        txt.pack(fill="both", expand=True)

    ttk.Button(frm, text="OK", command=dlg.destroy).pack(pady=(12, 0))

    dlg.wait_window()
