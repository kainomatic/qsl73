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


def format_connection_ok(tag_count: int) -> str:
    """Meldungstext bei erfolgreichem Verbindungstest."""
    return f"Verbindung OK, {tag_count} Tags gefunden"


def format_connection_error(exc: Exception) -> str:
    """Meldungstext bei fehlgeschlagenem Verbindungstest."""
    from qsl73.paperless import PaperlessAuthError, PaperlessConnectionError

    if isinstance(exc, PaperlessAuthError):
        return f"Authentifizierung fehlgeschlagen: {exc}"
    if isinstance(exc, PaperlessConnectionError):
        return f"Verbindung fehlgeschlagen: {exc}"
    return f"Fehler: {exc}"


def auto_matching_warning(tag_name: str, tags: list[dict]) -> str | None:
    """Gibt Warnmeldung zurück, wenn der genannte Tag matching_algorithm != 0 hat.

    Nur für Schreib-Tags (confirmed/uncertain) aufrufen — der Eingangs-Tag (input)
    ist auf Aufrufer-Ebene von dieser Prüfung ausgenommen.
    Gibt None zurück wenn kein Auto-Matching aktiv oder Tag nicht in der Liste.
    """
    if not tag_name:
        return None
    for tag in tags:
        if tag.get("name", "").lower() == tag_name.lower():
            algo = tag.get("matching_algorithm", 0)
            if algo != 0:
                return (
                    f"Tag '{tag_name}' hat in Paperless automatisches Matching aktiviert "
                    f"(Algorithmus {algo}). Das kann dazu führen, dass Paperless Karten "
                    "selbstständig als bestätigt/unsicher markiert. Bitte in Paperless für "
                    "diesen Tag 'kein Matching' (None) einstellen."
                )
    return None


def validate_tag_name(name: str) -> list[str]:
    """Validiert einen frei eingegebenen Tag-Namen. Gibt Fehlerliste zurück."""
    errors: list[str] = []
    if not name or not str(name).strip():
        errors.append("Tag-Name darf nicht leer sein.")
    return errors


def retain_selection_if_valid(current: str, new_values: list[str]) -> str:
    """Behält die aktuelle Auswahl wenn sie noch in new_values enthalten ist, sonst ''."""
    return current if current in new_values else ""


def config_to_field_defaults(config: "Config") -> dict:
    """Liefert Wizard-Feld-Werte für alle editierbaren Felder der Config zurück.

    Token wird NICHT zurückgegeben — leeres Feld im Bearbeiten-Modus = Token behalten.
    backup_count und manual_match_limit werden als str zurückgegeben (Entry-kompatibel).
    """
    return {
        "paperless.url": config.paperless.url,
        "paperless.auth_mode": config.paperless.auth_mode,
        "log4om.db_path": config.log4om.db_path,
        "log4om.own_callsign": config.log4om.own_callsign,
        "tags.input": config.tags.input,
        "tags.confirmed": config.tags.confirmed,
        "tags.uncertain": config.tags.uncertain,
        "matching.fuzzy_enabled": config.matching.fuzzy_enabled,
        "confirm.qsl_route_default": config.confirm.qsl_route_default,
        "app.language": config.app.language,
        "app.backup_count": str(config.app.backup_count),
        "app.update_check": config.app.update_check,
        "app.manual_match_limit": str(config.app.manual_match_limit),
    }


def is_token_retain_valid(mode: str, token: str, existing_config) -> bool:
    """Im Bearbeiten-Modus: leeres Token-Feld ist gültig wenn existing_config einen Token hat.

    Gibt True zurück wenn: mode=="token" UND token leer UND existing_config.paperless.token gesetzt.
    False in allen anderen Fällen (inkl. existing_config=None).
    """
    if mode != "token":
        return False
    if token.strip():
        return False  # neues Token eingegeben → kein Retain
    return bool(existing_config is not None and existing_config.paperless.token)


def merge_wizard_overrides(existing_config: "Config", overrides: dict) -> "Config":
    """Mergt Wizard-Felder über bestehende Config; Token-Erhalt wenn Feld leer.

    Felder außerhalb des Wizard-Scope (portable_suffixes, config_version) bleiben erhalten.
    Gibt eine neue Config-Instanz zurück — existing_config wird nicht verändert.
    """
    import copy
    from qsl73.setup_assistant import _apply_overrides

    updated = copy.deepcopy(existing_config)
    effective = dict(overrides)

    if not effective.get("paperless.token", ""):
        effective.pop("paperless.token", None)

    _apply_overrides(updated, effective)
    return updated
