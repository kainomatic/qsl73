# QSL73 — Copyright (C) 2026 DF1DS (kainomatic) — SPDX-License-Identifier: GPL-3.0-or-later
"""Setup-Assistent — erster Start oder fehlende/ungültige Konfiguration."""
from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Optional

from qsl73.config import Config
from qsl73.crypto import CryptoBackend, get_default_backend
from qsl73.setup_assistant import create_initial_config


class SetupWizard(tk.Toplevel):
    """Modaler Dialog für Erstkonfiguration. Nach Schließen: result ist Config oder None."""

    def __init__(self, parent: tk.Misc, crypto: Optional[CryptoBackend] = None) -> None:
        super().__init__(parent)
        self.title("QSL73 — Erstkonfiguration")
        self.resizable(True, True)
        self.result: Optional[Config] = None
        self._crypto = crypto if crypto is not None else get_default_backend()

        self._build_ui()
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self._on_cancel)
        self.wait_window()

    # ------------------------------------------------------------------
    # UI-Aufbau
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        outer = ttk.Frame(self, padding=12)
        outer.pack(fill="both", expand=True)

        canvas = tk.Canvas(outer, borderwidth=0, highlightthickness=0)
        vsb = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        inner = ttk.Frame(canvas)
        inner_id = canvas.create_window((0, 0), window=inner, anchor="nw")

        def _on_frame_configure(event):
            canvas.configure(scrollregion=canvas.bbox("all"))

        def _on_canvas_configure(event):
            canvas.itemconfig(inner_id, width=event.width)

        inner.bind("<Configure>", _on_frame_configure)
        canvas.bind("<Configure>", _on_canvas_configure)

        self._vars: dict[str, tk.Variable] = {}
        row = 0

        def section(label: str) -> None:
            nonlocal row
            ttk.Separator(inner, orient="horizontal").grid(
                row=row, column=0, columnspan=3, sticky="ew", pady=(10, 2)
            )
            row += 1
            ttk.Label(inner, text=label, font=("", 10, "bold")).grid(
                row=row, column=0, columnspan=3, sticky="w", pady=(0, 4)
            )
            row += 1

        def field(key: str, label: str, default: str = "", password: bool = False,
                  browse: bool = False) -> None:
            nonlocal row
            var = tk.StringVar(value=default)
            self._vars[key] = var
            ttk.Label(inner, text=label).grid(row=row, column=0, sticky="w", padx=(0, 8))
            show = "*" if password else ""
            entry = ttk.Entry(inner, textvariable=var, width=42, show=show)
            entry.grid(row=row, column=1, sticky="ew")
            if browse:
                ttk.Button(
                    inner, text="…",
                    command=lambda: var.set(
                        filedialog.askopenfilename(
                            parent=self,
                            title="Log4OM-Datenbank auswählen",
                            filetypes=[("SQLite-Datenbank", "*.sqlite *.db"), ("Alle Dateien", "*.*")],
                        ) or var.get()
                    ),
                    width=3,
                ).grid(row=row, column=2, padx=(4, 0))
            row += 1

        def bool_field(key: str, label: str, default: bool = True) -> None:
            nonlocal row
            var = tk.BooleanVar(value=default)
            self._vars[key] = var
            ttk.Checkbutton(inner, text=label, variable=var).grid(
                row=row, column=0, columnspan=2, sticky="w"
            )
            row += 1

        def combo_field(key: str, label: str, values: list[str], default: str) -> None:
            nonlocal row
            var = tk.StringVar(value=default)
            self._vars[key] = var
            ttk.Label(inner, text=label).grid(row=row, column=0, sticky="w", padx=(0, 8))
            ttk.Combobox(inner, textvariable=var, values=values, state="readonly", width=20).grid(
                row=row, column=1, sticky="w"
            )
            row += 1

        inner.columnconfigure(1, weight=1)

        section("Paperless-ngx")
        field("paperless.url", "URL *", "https://")
        combo_field("paperless.auth_mode", "Authentifizierung", ["token", "password"], "token")

        # Token-Auth-Felder (sichtbar bei Modus "token", Standard)
        self._vars["paperless.token"] = tk.StringVar()
        self._token_lbl = ttk.Label(inner, text="API-Token")
        self._token_lbl.grid(row=row, column=0, sticky="w", padx=(0, 8))
        self._token_entry = ttk.Entry(inner, textvariable=self._vars["paperless.token"], width=42, show="*")
        self._token_entry.grid(row=row, column=1, sticky="ew")
        row += 1

        # Passwort-Auth-Felder (sichtbar bei Modus "password", initial ausgeblendet)
        self._pw_username_var = tk.StringVar()
        self._pw_user_lbl = ttk.Label(inner, text="Benutzername *")
        self._pw_user_lbl.grid(row=row, column=0, sticky="w", padx=(0, 8))
        self._pw_user_entry = ttk.Entry(inner, textvariable=self._pw_username_var, width=42)
        self._pw_user_entry.grid(row=row, column=1, sticky="ew")
        self._pw_user_lbl.grid_remove()
        self._pw_user_entry.grid_remove()
        row += 1

        self._pw_password_var = tk.StringVar()
        self._pw_pass_lbl = ttk.Label(inner, text="Passwort *")
        self._pw_pass_lbl.grid(row=row, column=0, sticky="w", padx=(0, 8))
        self._pw_pass_entry = ttk.Entry(inner, textvariable=self._pw_password_var, width=42, show="*")
        self._pw_pass_entry.grid(row=row, column=1, sticky="ew")
        self._pw_pass_lbl.grid_remove()
        self._pw_pass_entry.grid_remove()
        row += 1

        # Trace: bei Auth-Modus-Wechsel Felder dynamisch ein-/ausblenden
        self._vars["paperless.auth_mode"].trace_add(
            "write", lambda *_: self._update_auth_fields()
        )

        section("Log4OM")
        field("log4om.db_path", "Datenbank *", browse=True)
        field("log4om.own_callsign", "Eigenes Rufzeichen *")

        section("Tags")
        field("tags.input", "Eingangs-Tag", "qsl-card")
        field("tags.confirmed", "Bestätigt-Tag", "qsl-bestätigt")
        field("tags.uncertain", "Unsicher-Tag", "qsl-nicht-bestätigt")

        section("Einstellungen")
        bool_field("matching.fuzzy_enabled", "Fuzzy-Matching aktivieren", True)
        combo_field("confirm.qsl_route_default", "QSL-Route-Default",
                    ["undefined", "bureau", "direct"], "undefined")
        combo_field("app.language", "Sprache", ["de", "en"], "de")
        field("app.backup_count", "Anzahl Backups", "5")
        bool_field("app.update_check", "Update-Prüfung beim Start", True)

        # Trefferlimit für manuellen Zuordnungs-Dialog (ADR-0030)
        var_limit = tk.StringVar(value="100")
        self._vars["app.manual_match_limit"] = var_limit
        ttk.Label(inner, text="Trefferlimit Zuordnung").grid(
            row=row, column=0, sticky="w", padx=(0, 8)
        )
        limit_combo = ttk.Combobox(
            inner, textvariable=var_limit, values=["10", "100", "1000", "0 (kein Limit)"],
            width=20,
        )
        limit_combo.grid(row=row, column=1, sticky="w")
        row += 1

        # Buttons
        btn_frame = ttk.Frame(self, padding=(12, 0, 12, 12))
        btn_frame.pack(fill="x")
        ttk.Button(btn_frame, text="Abbrechen", command=self._on_cancel).pack(side="right", padx=(4, 0))
        ttk.Button(btn_frame, text="Speichern", command=self._on_ok).pack(side="right")

        self.update_idletasks()
        self.minsize(500, 400)

    # ------------------------------------------------------------------
    # Auth-Felder dynamisch umschalten
    # ------------------------------------------------------------------

    def _update_auth_fields(self) -> None:
        from qsl73.gui.wizard_logic import auth_fields_for_mode
        mode = self._vars["paperless.auth_mode"].get()
        vis = auth_fields_for_mode(mode)
        if vis["show_token"]:
            self._token_lbl.grid()
            self._token_entry.grid()
            self._pw_user_lbl.grid_remove()
            self._pw_user_entry.grid_remove()
            self._pw_pass_lbl.grid_remove()
            self._pw_pass_entry.grid_remove()
        else:
            self._token_lbl.grid_remove()
            self._token_entry.grid_remove()
            self._pw_user_lbl.grid()
            self._pw_user_entry.grid()
            self._pw_pass_lbl.grid()
            self._pw_pass_entry.grid()

    # ------------------------------------------------------------------
    # Aktionen
    # ------------------------------------------------------------------

    def _collect_overrides(self) -> dict:
        overrides: dict = {}
        for key, var in self._vars.items():
            value = var.get()
            if key == "app.backup_count":
                try:
                    overrides[key] = int(value)
                except ValueError:
                    overrides[key] = 5
            elif key == "app.manual_match_limit":
                raw = value.split()[0]  # "0 (kein Limit)" → "0"
                try:
                    overrides[key] = max(0, int(raw))
                except ValueError:
                    overrides[key] = 100
            else:
                overrides[key] = value
        return overrides

    def _validate(self) -> list[str]:
        required = {
            "paperless.url": "Paperless-URL",
            "log4om.db_path": "Log4OM-Datenbankpfad",
            "log4om.own_callsign": "Eigenes Rufzeichen",
        }
        errors = []
        for key, label in required.items():
            val = self._vars[key].get().strip()
            if not val or val == "https://":
                errors.append(f"{label} ist erforderlich.")
        from qsl73.gui.wizard_logic import validate_auth_fields
        mode = self._vars["paperless.auth_mode"].get()
        errors.extend(validate_auth_fields(
            mode,
            token=self._vars["paperless.token"].get(),
            username=self._pw_username_var.get(),
            password=self._pw_password_var.get(),
        ))
        return errors

    def _on_ok(self) -> None:
        errors = self._validate()
        if errors:
            messagebox.showerror("Fehlende Felder", "\n".join(errors), parent=self)
            return
        try:
            overrides = self._collect_overrides()
            # Passwort-Modus: Token via PaperlessClient holen; Passwort nie persistieren (§4)
            if overrides.get("paperless.auth_mode") == "password":
                from qsl73.paperless import PaperlessClient
                _pc, token = PaperlessClient.from_password(
                    overrides["paperless.url"],
                    self._pw_username_var.get(),
                    self._pw_password_var.get(),
                )
                overrides["paperless.token"] = token
                overrides["paperless.auth_mode"] = "token"
            cfg = create_initial_config(
                crypto=self._crypto,
                overrides=overrides,
            )
            self.result = cfg
            self.destroy()
        except Exception as exc:
            from qsl73.gui.error_dialog import show_error
            show_error(self, "Fehler beim Speichern", str(exc))

    def _on_cancel(self) -> None:
        self.result = None
        self.destroy()
