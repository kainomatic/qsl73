# QSL73 — Copyright (C) 2026 DF1DS (kainomatic) — SPDX-License-Identifier: GPL-3.0-or-later
"""Mapping von Exceptions auf nutzersichtbare Fehlermeldungen (tk-frei, testbar)."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ErrorClassification:
    title: str
    user_message: str
    status_message: str
    is_expected: bool


def classify_error(exc: Exception) -> ErrorClassification:
    """Ordnet eine Exception einer nutzerfreundlichen Fehlermeldung zu.

    Erwartete, erklärbare Fehler (is_expected=True) bekommen einen Klartext ohne
    technischen Traceback. Unerwartete Fehler (is_expected=False) zeigen weiterhin
    die technische Meldung + Traceback (→ Fehleranalyse).
    """
    from qsl73.log4om_db import DatabaseBusyError, DatabaseChangedError, SchemaError
    from qsl73.log4om_write import QslEntryNotFoundError
    from qsl73.paperless import (
        PaperlessAPIError,
        PaperlessAuthError,
        PaperlessConnectionError,
        PaperlessNotFoundError,
    )

    if isinstance(exc, DatabaseChangedError):
        return ErrorClassification(
            title="Datenbank hat sich geändert",
            user_message=(
                "Die Log4OM-Datenbank wurde seit dem letzten Durchlauf verändert "
                "(z. B. durch Log4OM selbst).\n\n"
                "Aus Sicherheitsgründen wurde nichts geschrieben. "
                "Bitte starte den Durchlauf neu, damit QSL73 mit dem aktuellen "
                "Stand arbeitet."
            ),
            status_message="Durchlauf veraltet — bitte neu starten.",
            is_expected=True,
        )
    if isinstance(exc, SchemaError):
        return ErrorClassification(
            title="Datenbankformat nicht erkannt",
            user_message=(
                "Die Log4OM-Datenbank hat ein unerwartetes Format — möglicherweise "
                "eine andere Log4OM-Version oder eine falsche Datenbankdatei.\n\n"
                f"Details: {exc}"
            ),
            status_message="Datenbankformat nicht erkannt — Einstellungen prüfen.",
            is_expected=True,
        )
    if isinstance(exc, DatabaseBusyError):
        return ErrorClassification(
            title="Datenbank gesperrt",
            user_message=(
                "Die Log4OM-Datenbank ist gesperrt — Log4OM schreibt möglicherweise "
                "gerade. Bitte schließe Log4OM oder warte einen Moment und "
                "versuche es erneut."
            ),
            status_message="Datenbank gesperrt — Log4OM schließen und erneut versuchen.",
            is_expected=True,
        )
    if isinstance(exc, QslEntryNotFoundError):
        return ErrorClassification(
            title="QSL-Eintrag nicht gefunden",
            user_message=(
                "In einem QSO-Datensatz wurde kein QSL-Bestätigungs-Eintrag gefunden. "
                "Dies deutet auf ein ungewöhnliches Datenbankformat hin. "
                "Es wurde nichts geschrieben."
            ),
            status_message="QSL-Eintrag nicht gefunden — nichts geschrieben.",
            is_expected=True,
        )
    if isinstance(exc, PaperlessConnectionError):
        return ErrorClassification(
            title="Paperless nicht erreichbar",
            user_message=(
                "Die Verbindung zu Paperless-ngx ist fehlgeschlagen. "
                "Bitte prüfe, ob der Server erreichbar ist und die URL in den "
                "Einstellungen korrekt ist."
            ),
            status_message="Paperless nicht erreichbar — URL prüfen.",
            is_expected=True,
        )
    if isinstance(exc, PaperlessAuthError):
        return ErrorClassification(
            title="Paperless-Authentifizierung fehlgeschlagen",
            user_message=(
                "Der Zugriff auf Paperless-ngx wurde verweigert. "
                "Bitte prüfe den API-Token im Einstellungen-Dialog."
            ),
            status_message="Paperless-Token ungültig — Einstellungen prüfen.",
            is_expected=True,
        )
    if isinstance(exc, (PaperlessNotFoundError, PaperlessAPIError)):
        return ErrorClassification(
            title="Paperless-API-Fehler",
            user_message=f"Fehler beim Zugriff auf Paperless-ngx:\n{exc}",
            status_message=f"Paperless-Fehler: {exc}",
            is_expected=True,
        )
    return ErrorClassification(
        title="Unerwarteter Fehler",
        user_message=str(exc),
        status_message=f"Fehler: {exc}",
        is_expected=False,
    )
