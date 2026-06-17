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
