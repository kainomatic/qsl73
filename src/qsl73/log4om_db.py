"""
Orchestrierungs-/Sicherheitsschicht für Log4OM-DB-Schreibzugriff.

Schritt 5b — bettet write_paper_qsl (5a) in die Sicherheitsschicht ein:
Reihenfolge (ADR-0003): (1) Schema-Check → (2) Vor-Backup → (3) Transaktion.
Paperless-Tags (Schritt 4 in ADR-0003) sind NICHT Teil dieses Moduls.

Empirische Basis: docs/discovery.md §3, ADR-0003, ADR-0004, ADR-0020.
"""
from __future__ import annotations

import json
import shutil
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from qsl73.log4om_write import write_paper_qsl


class SchemaError(Exception):
    """Schema weicht vom erwarteten Format ab; Schreiben gesperrt."""


@dataclass
class WriteResult:
    written: int
    skipped: list = field(default_factory=list)  # [{"qsoid": str, "reason": str}]


def validate_schema(conn: sqlite3.Connection) -> str | None:
    """Prüft ob Log4OM-DB-Schema dem erwarteten Format entspricht.

    Ablauf:
    (1) Tabelle Log vorhanden?
    (2) Spalte qsoconfirmations vorhanden?
    (3) Stichprobe: mind. eine Zeile mit parsebarem JSON und CT='QSL'-Eintrag mit R-Feld.

    Returns:
        None wenn Schema OK; menschenlesbare Abweichungsbeschreibung sonst.
    """
    # 1. Tabelle Log vorhanden?
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='Log'"
    ).fetchone()
    if not row:
        return "Tabelle 'Log' nicht in der Datenbank gefunden"

    # 2. Spalte qsoconfirmations vorhanden?
    cols = {r[1] for r in conn.execute("PRAGMA table_info(Log)").fetchall()}
    if "qsoconfirmations" not in cols:
        return "Spalte 'qsoconfirmations' fehlt in Tabelle 'Log'"

    # 3. Stichprobe: mind. eine Zeile parsebar mit CT='QSL' + R-Feld
    rows = conn.execute(
        "SELECT qsoconfirmations FROM Log WHERE qsoconfirmations IS NOT NULL LIMIT 30"
    ).fetchall()
    if not rows:
        return None  # Leere DB: Schema-Prüfung ohne Stichprobe bestanden

    for (json_str,) in rows:
        try:
            entries = json.loads(json_str)
        except (json.JSONDecodeError, TypeError):
            return f"qsoconfirmations-Wert ist kein gültiges JSON: {json_str[:80]!r}"

        if not isinstance(entries, list):
            return (
                f"qsoconfirmations-Wert ist kein JSON-Array, "
                f"sondern {type(entries).__name__!r}"
            )

        for entry in entries:
            if isinstance(entry, dict) and entry.get("CT") == "QSL" and "R" in entry:
                return None  # Gültige Stichprobe gefunden

    return (
        "Keine Zeile in Log enthält einen CT='QSL'-Eintrag mit erwartetem R-Feld — "
        "Schema weicht ab (Log4OM-Version zu alt oder DB-Format geändert)"
    )
