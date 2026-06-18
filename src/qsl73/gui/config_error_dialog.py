# QSL73 — Copyright (C) 2026 DF1DS (kainomatic) — SPDX-License-Identifier: GPL-3.0-or-later
"""Fehler-Dialog bei ungültiger Konfiguration beim App-Start (ADR-0033)."""
from __future__ import annotations

import logging
from pathlib import Path

_log = logging.getLogger("qsl73")


# ---------------------------------------------------------------------------
# Pure logic (tk-frei, testbar)
# ---------------------------------------------------------------------------


def backup_display_name(path: Path) -> str:
    """Wandelt Backup-Pfad in lesbaren Anzeigenamen um.

    config_20260618_143022_abc12345.yaml → 2026-06-18  14:30:22
    """
    parts = path.stem.split("_")  # ["config", "20260618", "143022", "<uuid>"]
    if len(parts) >= 3:
        d, t = parts[1], parts[2]
        if len(d) == 8 and len(t) == 6 and d.isdigit() and t.isdigit():
            return f"{d[:4]}-{d[4:6]}-{d[6:8]}  {t[:2]}:{t[2:4]}:{t[4:6]}"
    return path.name


def has_config_backups(backup_dir: Path) -> bool:
    """True wenn mindestens eine Sicherung im backup_dir vorhanden ist."""
    from qsl73.config_backup import list_config_backups

    return bool(list_config_backups(backup_dir))


def try_restore_and_load(
    backup_path: Path,
    config_path: Path,
    crypto,
) -> "Config":
    """Stellt Backup wieder her und lädt Config. Wirft ConfigError wenn ungültig."""
    from qsl73.config_backup import restore_config_backup
    from qsl73.config import load_config

    restore_config_backup(backup_path, config_path)
    return load_config(config_path, crypto=crypto)


# ---------------------------------------------------------------------------
# tk dialog
# ---------------------------------------------------------------------------


class _ConfigErrorDialog:
    """Interner Dialog — wird über show_config_error_dialog genutzt."""

    def __init__(
        self,
        parent,
        error_msg: str,
        config_path: Path,
        backup_dir: Path,
        crypto,
    ) -> None:
        import tkinter as tk
        from tkinter import messagebox

        from qsl73.config_backup import list_config_backups
        from qsl73.config import ConfigError

        self.action: str | None = None  # "wizard" | "restore" | "quit"
        self.result = None

        self._config_path = config_path
        self._crypto = crypto
        self._backups = list_config_backups(backup_dir)
        self._selected_backup: Path | None = None

        dlg = tk.Toplevel(parent)
        dlg.title("QSL73 – Konfigurationsfehler")
        dlg.resizable(True, False)
        dlg.grab_set()
        dlg.focus_force()
        self._dlg = dlg

        pad_x = 14
        pad_top = (8, 2)
        pad_item = (4, 2)

        # Überschrift
        tk.Label(
            dlg,
            text="Die Konfigurationsdatei ist ungültig:",
            font=("", 10, "bold"),
            anchor="w",
        ).pack(fill="x", padx=pad_x, pady=pad_top)

        # Fehlermeldung (scrollbar)
        msg_frame = tk.Frame(dlg)
        msg_frame.pack(fill="x", padx=pad_x, pady=pad_item)
        sb = tk.Scrollbar(msg_frame, orient="vertical")
        msg_text = tk.Text(
            msg_frame,
            height=6,
            wrap="word",
            yscrollcommand=sb.set,
            relief="sunken",
            borderwidth=1,
            bg="#f8f8f8",
            font=("Courier New", 9),
        )
        sb.config(command=msg_text.yview)
        sb.pack(side="right", fill="y")
        msg_text.pack(side="left", fill="x", expand=True)
        msg_text.insert("1.0", error_msg)
        msg_text.config(state="disabled")

        # Backup-Liste (nur wenn vorhanden)
        self._restore_btn: tk.Button | None = None
        if self._backups:
            tk.Label(
                dlg,
                text="Frühere Sicherungen (neueste zuerst):",
                anchor="w",
            ).pack(fill="x", padx=pad_x, pady=(6, 0))

            lb_frame = tk.Frame(dlg)
            lb_frame.pack(fill="x", padx=pad_x, pady=pad_item)
            lb_sb = tk.Scrollbar(lb_frame, orient="vertical")
            lb = tk.Listbox(
                lb_frame,
                height=min(len(self._backups), 4),
                yscrollcommand=lb_sb.set,
                selectmode="single",
                activestyle="dotbox",
            )
            lb_sb.config(command=lb.yview)
            lb_sb.pack(side="right", fill="y")
            lb.pack(side="left", fill="x", expand=True)

            for bp in self._backups:
                lb.insert("end", backup_display_name(bp))

            def _on_select(event):
                sel = lb.curselection()
                self._selected_backup = self._backups[sel[0]] if sel else None
                if self._restore_btn:
                    self._restore_btn.config(
                        state="normal" if sel else "disabled"
                    )

            lb.bind("<<ListboxSelect>>", _on_select)

        # Trennlinie
        tk.Frame(dlg, height=1, bg="#cccccc").pack(fill="x", padx=pad_x, pady=(8, 0))

        # Button-Zeile
        btn_frame = tk.Frame(dlg)
        btn_frame.pack(fill="x", padx=pad_x, pady=(6, 12))

        tk.Button(
            btn_frame,
            text="Einrichtung neu starten",
            command=self._on_wizard,
            width=22,
        ).pack(side="left", padx=(0, 6))

        if self._backups:
            self._restore_btn = tk.Button(
                btn_frame,
                text="Sicherung wiederherstellen",
                command=self._on_restore,
                state="disabled",
                width=24,
            )
            self._restore_btn.pack(side="left", padx=(0, 6))

        tk.Button(
            btn_frame,
            text="Beenden",
            command=self._on_quit,
            width=10,
        ).pack(side="right")

        dlg.protocol("WM_DELETE_WINDOW", self._on_quit)
        _center_window(dlg)
        dlg.wait_window()

    def _on_wizard(self) -> None:
        self.action = "wizard"
        self._dlg.destroy()

    def _on_quit(self) -> None:
        self.action = "quit"
        self._dlg.destroy()

    def _on_restore(self) -> None:
        import tkinter.messagebox as mb

        from qsl73.config import ConfigError

        if not self._selected_backup:
            return
        try:
            config = try_restore_and_load(
                self._selected_backup, self._config_path, self._crypto
            )
            self.result = config
            self.action = "restore"
            self._dlg.destroy()
        except ConfigError as exc:
            mb.showerror(
                "Sicherung ungültig",
                f"Die gewählte Sicherung ist ebenfalls ungültig:\n\n{exc}\n\n"
                "Bitte eine andere Sicherung wählen oder die Einrichtung neu starten.",
                parent=self._dlg,
            )


def show_config_error_dialog(
    error_msg: str,
    config_path: Path,
    backup_dir: Path,
    crypto,
) -> "Config | None":
    """Zeigt Fehler-Dialog und gibt Config zurück (Wizard/Sicherung) oder None (Beenden).

    Funktioniert vor Existenz eines MainWindow — verwendet eigenes tk.Tk()-Root.
    """
    import tkinter as tk

    root = tk.Tk()
    root.withdraw()

    dialog = _ConfigErrorDialog(root, error_msg, config_path, backup_dir, crypto)

    if dialog.action == "wizard":
        from qsl73.gui.setup_wizard import SetupWizard

        wizard = SetupWizard(root)
        config = wizard.result
        root.destroy()
        return config

    if dialog.action == "restore":
        root.destroy()
        return dialog.result

    # "quit" oder Fenster geschlossen
    root.destroy()
    return None


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------


def _center_window(widget) -> None:
    widget.update_idletasks()
    w = widget.winfo_reqwidth()
    h = widget.winfo_reqheight()
    ws = widget.winfo_screenwidth()
    hs = widget.winfo_screenheight()
    x = max(0, (ws - w) // 2)
    y = max(0, (hs - h) // 2)
    widget.geometry(f"+{x}+{y}")
