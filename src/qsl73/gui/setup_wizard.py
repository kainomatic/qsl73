# QSL73 — Copyright (C) 2026 DF1DS (kainomatic) — SPDX-License-Identifier: GPL-3.0-or-later
"""Setup-Assistent — Erstkonfiguration und Einstellungen-Dialog."""
from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Optional

# i18n-Vorbereitung: nutzersichtbare Texte als Konstanten
_LBL_TOKEN_RETAIN = "(leer lassen = bestehendes Token behalten)"
_LBL_TAG_INFO = (
    "ℹ QSL73 legt Schreib-Tags ohne automatisches Matching an. "
    "Bitte diese Einstellung in Paperless nicht auf 'Auto' ändern."
)
_WARN_CONN_NOT_TESTED = "Bitte zuerst 'Verbindung testen' ausführen."

from qsl73.config import Config
from qsl73.crypto import CryptoBackend, get_default_backend
from qsl73.setup_assistant import create_initial_config


class SetupWizard(tk.Toplevel):
    """Modaler Dialog für Erstkonfiguration und Einstellungen (ADR-0036).

    existing_config=None  → Erstkonfiguration: Titel "QSL73 — Erstkonfiguration",
                            Felder mit Defaults vorbefüllt.
    existing_config=cfg   → Bearbeiten-Modus: Titel "QSL73 — Einstellungen",
                            Felder mit aktuellen Config-Werten vorbefüllt.
                            Token-Feld bleibt leer (§4: kein Klartext im Feld);
                            leer lassen = bestehendes Token behalten.
    Nach Schließen: result ist Config oder None.
    """

    def __init__(
        self,
        parent: tk.Misc,
        crypto: Optional[CryptoBackend] = None,
        existing_config: Optional[Config] = None,
    ) -> None:
        super().__init__(parent)
        self._existing_config = existing_config
        self._is_edit_mode = existing_config is not None
        self.title("QSL73 — Einstellungen" if self._is_edit_mode else "QSL73 — Erstkonfiguration")
        self.resizable(True, True)
        self.result: Optional[Config] = None
        self._crypto = crypto if crypto is not None else get_default_backend()

        self._build_ui()
        self.grab_set()
        self._attach_attention_handler()
        self.protocol("WM_DELETE_WINDOW", self._on_cancel)
        self.wait_window()

    # ------------------------------------------------------------------
    # UI-Aufbau
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        self._available_tags: list = []
        self._connection_ok: bool = False
        self._tag_combos: dict = {}
        self._new_tag_vars: dict = {}
        self._tag_warning_lbls: dict = {}

        # Im Bearbeiten-Modus: Config-Werte als Feld-Defaults
        if self._is_edit_mode:
            from qsl73.gui.wizard_logic import config_to_field_defaults
            _d = config_to_field_defaults(self._existing_config)
        else:
            _d = {}

        outer = ttk.Frame(self, padding=12)
        outer.pack(fill="both", expand=True)

        canvas = tk.Canvas(outer, borderwidth=0, highlightthickness=0)
        vsb = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        self._canvas = canvas

        inner = ttk.Frame(canvas)
        self._inner_frame = inner
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
            var = tk.StringVar(value=_d.get(key, default))
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
            val = _d.get(key, default)
            var = tk.BooleanVar(value=bool(val))
            self._vars[key] = var
            ttk.Checkbutton(inner, text=label, variable=var).grid(
                row=row, column=0, columnspan=2, sticky="w"
            )
            row += 1

        def combo_field(key: str, label: str, values: list[str], default: str) -> None:
            nonlocal row
            var = tk.StringVar(value=_d.get(key, default))
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
        self._vars["paperless.token"] = tk.StringVar()  # immer leer (§4: kein Klartext im Feld)
        self._token_lbl = ttk.Label(inner, text="API-Token")
        self._token_lbl.grid(row=row, column=0, sticky="w", padx=(0, 8))
        self._token_entry = ttk.Entry(inner, textvariable=self._vars["paperless.token"], width=42, show="*")
        self._token_entry.grid(row=row, column=1, sticky="ew")
        row += 1

        # Hinweis im Bearbeiten-Modus: leeres Feld = Token behalten
        if self._is_edit_mode:
            self._token_retain_lbl = ttk.Label(
                inner,
                text=_LBL_TOKEN_RETAIN,
                foreground="#555555", font=("", 8),
            )
            self._token_retain_lbl.grid(row=row, column=1, sticky="w")
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

        ttk.Button(
            inner, text="Verbindung testen", command=self._test_connection,
        ).grid(row=row, column=1, sticky="w", pady=(6, 0))
        row += 1
        self._conn_status_lbl = ttk.Label(
            inner, text="", foreground="#555555", wraplength=380,
        )
        self._conn_status_lbl.grid(row=row, column=1, columnspan=2, sticky="w", pady=(0, 4))
        row += 1

        section("Log4OM")
        field("log4om.db_path", "Datenbank *", browse=True)
        field("log4om.own_callsign", "Eigenes Rufzeichen *")

        section("Tags")
        ttk.Label(
            inner,
            text=_LBL_TAG_INFO,
            foreground="#555555", font=("", 8), wraplength=400,
        ).grid(row=row, column=0, columnspan=3, sticky="w", pady=(0, 4))
        row += 1

        for _tag_key, _tag_label, _tag_default in [
            ("tags.input", "Eingangs-Tag", "qsl-card"),
            ("tags.confirmed", "Bestätigt-Tag", "qsl-bestätigt"),
            ("tags.uncertain", "Unsicher-Tag", "qsl-nicht-bestätigt"),
        ]:
            _var = tk.StringVar(value=_d.get(_tag_key, _tag_default))
            self._vars[_tag_key] = _var
            ttk.Label(inner, text=_tag_label).grid(
                row=row, column=0, sticky="w", padx=(0, 8)
            )
            _tag_frame = ttk.Frame(inner)
            _tag_frame.grid(row=row, column=1, columnspan=2, sticky="ew")
            _tag_frame.columnconfigure(0, weight=1)

            _combo = ttk.Combobox(
                _tag_frame, textvariable=_var, values=[], state="disabled", width=22,
            )
            _combo.grid(row=0, column=0, sticky="ew")
            self._tag_combos[_tag_key] = _combo

            _new_var = tk.StringVar()
            self._new_tag_vars[_tag_key] = _new_var
            ttk.Entry(_tag_frame, textvariable=_new_var, width=14).grid(
                row=0, column=1, padx=(4, 0)
            )
            ttk.Button(
                _tag_frame, text="Anlegen", width=8,
                command=lambda k=_tag_key: self._create_tag(k),
            ).grid(row=0, column=2, padx=(4, 0))
            row += 1

            if _tag_key != "tags.input":
                _warn_lbl = ttk.Label(
                    inner, text="", foreground="#cc4400",
                    wraplength=400, font=("", 8),
                )
                _warn_lbl.grid(
                    row=row, column=1, columnspan=2, sticky="w", pady=(0, 2)
                )
                self._tag_warning_lbls[_tag_key] = _warn_lbl
                row += 1

            _var.trace_add("write", lambda *_, k=_tag_key: self._check_tag_warning(k))

        ttk.Button(
            inner, text="Tags neu laden", command=self._reload_tags,
        ).grid(row=row, column=1, sticky="w", pady=(4, 4))
        row += 1

        section("Einstellungen")
        bool_field("matching.fuzzy_enabled", "Fuzzy-Matching aktivieren", True)
        combo_field("confirm.qsl_route_default", "QSL-Route-Default",
                    ["undefined", "bureau", "direct"], "undefined")
        combo_field("app.language", "Sprache", ["de", "en"], "de")
        field("app.backup_count", "Anzahl Backups", "5")
        bool_field("app.update_check", "Update-Prüfung beim Start", True)

        # Trefferlimit für manuellen Zuordnungs-Dialog (ADR-0030)
        var_limit = tk.StringVar(value=_d.get("app.manual_match_limit", "100"))
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

        # Korrekte Auth-Feld-Sichtbarkeit nach Initialisierung sicherstellen
        self._update_auth_fields()

        # Fenstergröße an Inhalt anpassen + Mausrad-Scrollen aktivieren (TEIL 1)
        self._adjust_window_size()
        self._bind_mousewheel()

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
            if self._is_edit_mode:
                self._token_retain_lbl.grid()
            self._pw_user_lbl.grid_remove()
            self._pw_user_entry.grid_remove()
            self._pw_pass_lbl.grid_remove()
            self._pw_pass_entry.grid_remove()
        else:
            self._token_lbl.grid_remove()
            self._token_entry.grid_remove()
            if self._is_edit_mode:
                self._token_retain_lbl.grid_remove()
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
        from qsl73.gui.wizard_logic import is_token_retain_valid, validate_auth_fields
        mode = self._vars["paperless.auth_mode"].get()
        token = self._vars["paperless.token"].get()
        # Im Bearbeiten-Modus: leeres Token-Feld + vorhandener Token = OK (Token bleibt erhalten)
        if self._is_edit_mode and is_token_retain_valid(mode, token, self._existing_config):
            pass
        else:
            errors.extend(validate_auth_fields(
                mode,
                token=token,
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

            if self._is_edit_mode:
                # Bearbeiten-Modus: bestehende Config aktualisieren (inkl. Token-Erhalt)
                from qsl73.config import get_config_path, save_config
                from qsl73.gui.wizard_logic import merge_wizard_overrides
                cfg = merge_wizard_overrides(self._existing_config, overrides)
                save_config(cfg, get_config_path(), crypto=self._crypto)
            else:
                cfg = create_initial_config(
                    crypto=self._crypto,
                    overrides=overrides,
                )
            self.result = cfg
            self._unbind_mousewheel()
            self.destroy()
        except Exception as exc:
            from qsl73.gui.error_dialog import show_error
            show_error(self, "Fehler beim Speichern", str(exc))

    def _on_cancel(self) -> None:
        self.result = None
        self._unbind_mousewheel()
        self.destroy()

    # ------------------------------------------------------------------
    # Verbindung + Tag-Verwaltung
    # ------------------------------------------------------------------

    def _test_connection(self) -> None:
        from qsl73.gui.wizard_logic import (
            format_connection_error,
            format_connection_ok,
            format_url_error,
            resolve_effective_token,
        )
        from qsl73.paperless import PaperlessClient

        url = self._vars["paperless.url"].get().strip()

        # URL-Vorab-Check: gar nicht erst verbinden wenn URL offensichtlich leer/ungültig
        url_err = format_url_error(url)
        if url_err:
            self._connection_ok = False
            self._conn_status_lbl.configure(text=url_err, foreground="#cc0000")
            self._update_tag_combos()
            return

        mode = self._vars["paperless.auth_mode"].get()

        try:
            if mode == "password":
                pc, _ = PaperlessClient.from_password(
                    url,
                    self._pw_username_var.get(),
                    self._pw_password_var.get(),
                )
            else:
                # Im Bearbeiten-Modus: leeres Token-Feld → bestehendes Token nutzen (§4)
                token = resolve_effective_token(
                    self._vars["paperless.token"].get(),
                    self._existing_config,
                )
                pc = PaperlessClient(url, token)

            tags = pc.list_tags()
            self._available_tags = tags
            self._connection_ok = True
            self._conn_status_lbl.configure(
                text=format_connection_ok(len(tags)),
                foreground="#1a7a1a",
            )
        except Exception as exc:
            self._connection_ok = False
            self._available_tags = []
            self._conn_status_lbl.configure(
                text=format_connection_error(exc),
                foreground="#cc0000",
            )
        finally:
            self._update_tag_combos()

    def _reload_tags(self) -> None:
        if not self._connection_ok:
            messagebox.showwarning("Verbindung nicht getestet", _WARN_CONN_NOT_TESTED, parent=self)
            return
        self._test_connection()

    def _update_tag_combos(self) -> None:
        from qsl73.gui.wizard_logic import retain_selection_if_valid

        tag_names = [t["name"] for t in self._available_tags]
        state = "readonly" if self._connection_ok else "disabled"

        for key in ("tags.input", "tags.confirmed", "tags.uncertain"):
            combo = self._tag_combos.get(key)
            if combo is None:
                continue
            current = self._vars[key].get()
            new_val = retain_selection_if_valid(current, tag_names)
            combo.configure(values=tag_names, state=state)
            self._vars[key].set(new_val)

        for key in ("tags.confirmed", "tags.uncertain"):
            self._check_tag_warning(key)

    def _check_tag_warning(self, key: str) -> None:
        lbl = self._tag_warning_lbls.get(key)
        if lbl is None:
            return
        from qsl73.gui.wizard_logic import auto_matching_warning

        var = self._vars.get(key)
        tag_name = var.get() if var is not None else ""
        warning = auto_matching_warning(tag_name, self._available_tags)
        lbl.configure(text=warning or "")

    def _create_tag(self, key: str) -> None:
        from qsl73.gui.wizard_logic import validate_tag_name
        from qsl73.paperless import PaperlessClient

        if not self._connection_ok:
            messagebox.showwarning("Verbindung nicht getestet", _WARN_CONN_NOT_TESTED, parent=self)
            return

        new_var = self._new_tag_vars.get(key)
        if new_var is None:
            return
        name = new_var.get().strip()

        errors = validate_tag_name(name)
        if errors:
            messagebox.showerror("Ungültiger Tag-Name", "\n".join(errors), parent=self)
            return

        url = self._vars["paperless.url"].get().strip()
        mode = self._vars["paperless.auth_mode"].get()

        try:
            if mode == "password":
                pc, _ = PaperlessClient.from_password(
                    url,
                    self._pw_username_var.get(),
                    self._pw_password_var.get(),
                )
            else:
                from qsl73.gui.wizard_logic import resolve_effective_token
                token = resolve_effective_token(
                    self._vars["paperless.token"].get(),
                    self._existing_config,
                )
                pc = PaperlessClient(url, token)

            pc.create_tag(name, matching_algorithm=0)
            new_tags = pc.list_tags()
            self._available_tags = new_tags
            self._update_tag_combos()
            self._vars[key].set(name)
            new_var.set("")
        except Exception as exc:
            from qsl73.gui.error_dialog import show_error
            show_error(self, "Fehler beim Anlegen", str(exc))

    # ------------------------------------------------------------------
    # Fenstergröße, Mausrad-Scrollen, Fokus-Attention (TEIL 1 + TEIL 4)
    # ------------------------------------------------------------------

    def _adjust_window_size(self) -> None:
        """Dimensioniert Fenster an Inhalt an (max. 90 % Bildschirmhöhe), zentriert."""
        self.update_idletasks()
        needed_h = self.winfo_reqheight()
        screen_h = self.winfo_screenheight()
        target_h = min(needed_h, int(screen_h * 0.9))
        target_h = max(target_h, 400)

        needed_w = max(560, self.winfo_reqwidth())
        screen_w = self.winfo_screenwidth()
        x = max(0, (screen_w - needed_w) // 2)
        y = max(0, (screen_h - target_h) // 2)
        self.geometry(f"{needed_w}x{target_h}+{x}+{y}")

    def _bind_mousewheel(self) -> None:
        """Aktiviert Mausrad-Scrollen für den Canvas (Windows/macOS, event.delta)."""
        canvas = self._canvas

        def _on_scroll(event: tk.Event) -> None:
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        # bind_all ist korrekt für modalen Dialog: Mausrad soll überall im Fenster reagieren.
        # Wird in _unbind_mousewheel beim Schließen sauber aufgeräumt.
        self.bind_all("<MouseWheel>", _on_scroll)

    def _unbind_mousewheel(self) -> None:
        """Löst globale Mausrad-Bindung auf — vor destroy() aufrufen."""
        try:
            self.unbind_all("<MouseWheel>")
        except Exception:
            pass

    def _attach_attention_handler(self) -> None:
        """Bell + lift wenn Nutzer versucht ins gesperrte Hauptfenster zu klicken.

        grab_set() leitet Pointer-Events zum Wizard um; Fokus-Wechsel (FocusOut → FocusIn
        am Toplevel selbst) signalisiert den Klick-Versuch. Mindestens bell() + lift() +
        focus_force() als plattformtolerante Variante.
        """
        self._focus_away = False

        def _on_focus_out(event: tk.Event) -> None:
            if event.widget == self:
                self._focus_away = True

        def _on_focus_in(event: tk.Event) -> None:
            if event.widget == self and self._focus_away:
                self._focus_away = False
                self.bell()
                self.lift()
                self.focus_force()

        self.bind("<FocusOut>", _on_focus_out)
        self.bind("<FocusIn>", _on_focus_in)
