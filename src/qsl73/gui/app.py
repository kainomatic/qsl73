# QSL73 — Copyright (C) 2026 DF1DS (kainomatic) — SPDX-License-Identifier: GPL-3.0-or-later
"""App-Einstiegspunkt: Single-Instance-Lock + GUI-Start-Orchestrierung."""
from __future__ import annotations

import os
import sys
from pathlib import Path


def _is_process_running(pid: int) -> bool:
    """Prüft ob ein Prozess mit dieser PID läuft (plattformtolerant)."""
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


class InstanceLock:
    """PID-Lockfile verhindert mehrere gleichzeitige QSL73-Instanzen."""

    def __init__(self, lock_path: Path) -> None:
        self._path = lock_path

    def acquire(self) -> bool:
        """True = Lock erworben; False = andere Instanz läuft."""
        if self._path.exists():
            try:
                pid = int(self._path.read_text(encoding="utf-8").strip())
                if _is_process_running(pid):
                    return False
            except (ValueError, OSError):
                pass  # staler Lock oder fehlerhafter Inhalt

        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(str(os.getpid()), encoding="utf-8")
        return True

    def release(self) -> None:
        try:
            self._path.unlink(missing_ok=True)
        except OSError:
            pass


def _lock_path() -> Path:
    appdata = os.environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming"))
    return Path(appdata) / "QSL73" / "qsl73.lock"


def run_app() -> None:
    """Startet die QSL73-Anwendung mit Single-Instance-Lock, Setup-Assistent und Hauptfenster."""
    import tkinter as tk
    from tkinter import messagebox

    # Single-Instance-Lock
    lock = InstanceLock(_lock_path())
    if not lock.acquire():
        root = tk.Tk()
        root.withdraw()
        messagebox.showwarning(
            "QSL73 läuft bereits",
            "QSL73 ist bereits geöffnet. Bitte das bestehende Fenster verwenden.",
        )
        root.destroy()
        sys.exit(0)

    try:
        from qsl73.setup_assistant import SetupNeeded, load_or_trigger_setup
        from qsl73.gui.error_dialog import show_error
        from qsl73.gui.setup_wizard import SetupWizard
        from qsl73.gui.main_window import MainWindow

        # Konfiguration laden oder Setup-Assistent starten
        try:
            config = load_or_trigger_setup()
        except SetupNeeded:
            root = tk.Tk()
            root.withdraw()
            wizard = SetupWizard(root)
            config = wizard.result
            root.destroy()
            if config is None:
                sys.exit(0)

        # Hauptfenster
        app = MainWindow(config)
        app.mainloop()
    finally:
        lock.release()
