# QSL73 — Copyright (C) 2026 DF1DS (kainomatic) — SPDX-License-Identifier: GPL-3.0-or-later
"""Reine Logik-Hilfsfunktionen für den Setup-Assistenten — tk-frei, testbar."""
from __future__ import annotations


def auth_fields_for_mode(mode: str) -> dict[str, bool]:
    """Gibt zurück, welche Auth-Feldgruppen für einen Modus sichtbar sein sollen."""
    if mode == "password":
        return {"show_token": False, "show_username_password": True}
    return {"show_token": True, "show_username_password": False}


def validate_auth_fields(
    mode: str,
    token: str = "",
    username: str = "",
    password: str = "",
) -> list[str]:
    """Validiert Auth-Felder passend zum Modus. Gibt Liste von Fehlermeldungen zurück."""
    errors: list[str] = []
    if mode == "token":
        if not token.strip():
            errors.append("API-Token ist erforderlich.")
    elif mode == "password":
        if not username.strip():
            errors.append("Benutzername ist erforderlich.")
        if not password.strip():
            errors.append("Passwort ist erforderlich.")
    return errors
