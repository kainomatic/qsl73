# QSL73 — Copyright (C) 2026 DF1DS (kainomatic) — SPDX-License-Identifier: GPL-3.0-or-later
"""Fehlermelde-Dialog: Vorschau + Lokal-Speichern + GitHub-Melden (ADR-0035)."""
from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
from pathlib import Path


class ErrorReportDialog:
    """Modaler Dialog zur Vorschau und zum Versand eines Fehlerberichts.

    Args:
        parent: Eltern-Widget (tk.Tk oder Toplevel).
        report_text: Der bereinigte Berichtstext (kein Secret, kein QSO-Inhalt).
        version: App-Version (für GitHub-Issue-Titel).
        log_dir: Log-Verzeichnis (für Standard-Speicherpfad).
    """

    def __init__(
        self,
        parent: tk.Misc,
        report_text: str,
        version: str,
        log_dir: Path,
    ) -> None:
        self._report_text = report_text
        self._version = version
        self._log_dir = log_dir

        self._top = tk.Toplevel(parent)
        self._top.title("Fehler melden — QSL73")
        self._top.minsize(600, 400)
        self._top.resizable(True, True)
        self._build_ui()
        self._top.transient(parent)
        self._top.grab_set()
        parent.wait_window(self._top)

    def _build_ui(self) -> None:
        self._top.columnconfigure(0, weight=1)
        self._top.rowconfigure(1, weight=1)

        # Hinweis-Text
        info = ttk.Label(
            self._top,
            text=(
                "Bericht-Vorschau (keine Secrets, keine QSO-Inhalte). "
                "Nichts wird automatisch gesendet."
            ),
            wraplength=580,
            foreground="#555555",
        )
        info.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 4))

        # ScrolledText (schreibgeschützt)
        txt = scrolledtext.ScrolledText(
            self._top,
            wrap="word",
            font=("Courier New", 9),
            height=18,
        )
        txt.insert("1.0", self._report_text)
        txt.configure(state="disabled")
        txt.grid(row=1, column=0, sticky="nsew", padx=10, pady=4)

        # Button-Leiste
        btn_frame = ttk.Frame(self._top, padding=(10, 6))
        btn_frame.grid(row=2, column=0, sticky="ew")

        ttk.Button(btn_frame, text="Lokal speichern", command=self._on_save).pack(
            side="left", padx=(0, 6)
        )
        ttk.Button(btn_frame, text="Auf GitHub melden", command=self._on_github).pack(
            side="left"
        )
        ttk.Button(btn_frame, text="Schließen", command=self._top.destroy).pack(
            side="right"
        )

    def _on_save(self) -> None:
        from qsl73.error_report import save_report_to_file

        default_name = f"qsl73-fehlerbericht-{self._version}.txt"
        path = filedialog.asksaveasfilename(
            parent=self._top,
            title="Fehlerbericht speichern",
            defaultextension=".txt",
            filetypes=[("Textdatei", "*.txt"), ("Alle Dateien", "*.*")],
            initialfile=default_name,
            initialdir=str(self._log_dir),
        )
        if path:
            save_report_to_file(self._report_text, Path(path))
            messagebox.showinfo(
                "Gespeichert",
                f"Fehlerbericht gespeichert:\n{path}",
                parent=self._top,
            )

    def _on_github(self) -> None:
        from qsl73.error_report import build_github_url, open_in_browser

        title = f"Fehlerbericht QSL73 {self._version}"
        url = build_github_url(title=title, body=self._report_text)
        open_in_browser(url)
