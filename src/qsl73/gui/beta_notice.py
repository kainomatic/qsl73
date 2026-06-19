# QSL73 — Copyright (C) 2026 DF1DS (kainomatic) — SPDX-License-Identifier: GPL-3.0-or-later
"""Beta-Start-Hinweis-Dialog (wird nur bei CHANNEL == 'beta' aufgerufen)."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

# i18n-Vorbereitung: nutzersichtbare Texte als Konstanten
_NOTICE_TITLE = "QSL73 Beta — Vorabversion — by DF1DS"
_NOTICE_BODY = (
    "Sie verwenden eine Beta-Version von QSL73.\n\n"
    "Vorabversionen können Fehler enthalten und sich unerwartet verhalten.\n\n"
    "Bitte arbeiten Sie bevorzugt gegen eine Kopie Ihrer Log4OM-Datenbank\n"
    "und melden Sie Probleme über Hilfe → Fehler melden.\n\n"
    "Das bestehende Sicherheitsnetz bleibt aktiv:\n"
    "Backup vor jedem Schreiben, Vorschau + ausdrückliche Bestätigung."
)
_NOTICE_BTN = "Verstanden"


def show_beta_notice(parent: tk.Misc) -> None:
    """Zeigt einen modalen Beta-Hinweis-Dialog über dem Elternfenster.

    Kein Systemton (eigenes Toplevel statt messagebox). Schlägt niemals fehl —
    der Beta-Hinweis ist nice-to-have; er darf den App-Start nicht blockieren.
    """
    try:
        dlg = tk.Toplevel(parent)
        dlg.title(_NOTICE_TITLE)
        dlg.resizable(False, False)
        dlg.transient(parent)
        dlg.grab_set()

        frame = ttk.Frame(dlg, padding=20)
        frame.pack(fill="both", expand=True)

        ttk.Label(
            frame,
            text=_NOTICE_BODY,
            justify=tk.LEFT,
        ).pack(anchor="w", pady=(0, 16))

        btn = ttk.Button(frame, text=_NOTICE_BTN, command=dlg.destroy)
        btn.pack()
        btn.focus_set()

        dlg.bind("<Return>", lambda _e: dlg.destroy())

        # Zentrieren über Elternfenster
        dlg.update_idletasks()
        pw = parent.winfo_width()
        ph = parent.winfo_height()
        px = parent.winfo_rootx()
        py = parent.winfo_rooty()
        dw = dlg.winfo_reqwidth()
        dh = dlg.winfo_reqheight()
        x = px + max(0, (pw - dw) // 2)
        y = py + max(0, (ph - dh) // 2)
        dlg.geometry(f"+{x}+{y}")

        dlg.wait_window()
    except Exception:
        pass  # Hinweis ist nice-to-have; Start nie blockieren
