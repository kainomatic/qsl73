# src/qsl73/audit.py
# QSL73 — Copyright (C) 2026 DF1DS (kainomatic) — SPDX-License-Identifier: GPL-3.0-or-later
"""Fachliches Audit-Log für QSO-Bestätigungen (§10, ADR-0035).

audit.log ist getrennt von qsl73.log:
  qsl73.log  = Diagnose-Logging (rotierend, 1 MB / 5 Backups)
  audit.log  = dauerhaftes Fachprotokoll (kein Rotieren; wächst anhängend)

Öffentliche API:
  AuditEntry             — Dataclass für einen Bestätigungseintrag
  format_audit_line      — reine Formatierungslogik (tk-frei, testbar)
  write_audit_entries    — hängt Einträge an audit.log an
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

_log = logging.getLogger("qsl73")


@dataclass
class AuditEntry:
    """Ein Eintrag pro tatsächlich geschriebenem QSO."""

    doc_id: int
    qsoid: str
    callsign: str
    qso_date: str      # ISO-Datum, maximal 10 Zeichen (YYYY-MM-DD)
    band: str
    mode: str
    route: str         # "undefined" | "bureau" | "direct"
    source: str        # "auto" | "manuell"
    backup_path: str   # absoluter Pfad zur Backup-Datei oder "–"


def format_audit_line(entry: AuditEntry, ts: str | None = None) -> str:
    """Formatiert einen AuditEntry als einzelne Log-Zeile (kein abschließender Newline).

    Format: <ISO-Zeitstempel> | doc_id=<n> | qsoid=<id> | call=<ruf>
             | date=<datum> | band=<band> | mode=<mode> | route=<route>
             | source=<auto|manuell> | backup=<pfad|–>

    Reine Formatierungslogik — tk-frei, ohne Seiteneffekte.
    """
    if ts is None:
        ts = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    return (
        f"{ts}"
        f" | doc_id={entry.doc_id}"
        f" | qsoid={entry.qsoid}"
        f" | call={entry.callsign}"
        f" | date={entry.qso_date}"
        f" | band={entry.band}"
        f" | mode={entry.mode}"
        f" | route={entry.route}"
        f" | source={entry.source}"
        f" | backup={entry.backup_path}"
    )


@dataclass
class IgnoreAuditEntry:
    """Ein Eintrag pro Ignorieren/Wieder-Aufnehmen-Aktion (ADR-0059)."""

    doc_id: int
    callsign: str   # gelesenes Rufzeichen, oder "?" wenn nicht vorhanden
    action: str     # "ignoriert" | "wieder_aufgenommen"


def format_ignore_audit_line(entry: IgnoreAuditEntry, ts: str | None = None) -> str:
    """Formatiert einen IgnoreAuditEntry als einzelne Log-Zeile (kein abschließender Newline).

    Eigene Zeilenart, getrennt vom AuditEntry-Format für QSO-Schreibvorgänge —
    dessen Format bleibt unverändert lesbar.
    """
    if ts is None:
        ts = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    return (
        f"{ts}"
        f" | doc_id={entry.doc_id}"
        f" | call={entry.callsign}"
        f" | aktion={entry.action}"
    )


def write_ignore_audit_entry(entry: IgnoreAuditEntry, log_dir: Path) -> None:
    """Hängt einen Ignorieren/Wieder-Aufnehmen-Eintrag an audit.log im log_dir an.

    Schreibfehler werden geloggt, nicht weitergeworfen (wie write_audit_entries).
    """
    log_dir.mkdir(parents=True, exist_ok=True)
    audit_path = log_dir / "audit.log"
    line = format_ignore_audit_line(entry)
    try:
        with open(audit_path, "a", encoding="utf-8") as fh:
            fh.write(line + "\n")
        _log.debug("Audit: Ignorieren-Eintrag nach %s geschrieben", audit_path)
    except OSError as exc:
        _log.warning("Audit-Log (Ignorieren) konnte nicht geschrieben werden: %s", exc)


@dataclass
class CleanupAuditEntry:
    """Sammel-Eintrag für einen Alt-Bestand-Aufräumlauf (Eingangs-Tag entfernen, Issue #41)."""

    removed: int
    failed: int


def format_cleanup_audit_line(entry: CleanupAuditEntry, ts: str | None = None) -> str:
    """Formatiert einen CleanupAuditEntry als einzelne Log-Zeile (kein abschließender Newline)."""
    if ts is None:
        ts = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    return (
        f"{ts}"
        f" | aktion=eingangs_tag_aufraeumen"
        f" | entfernt={entry.removed}"
        f" | fehler={entry.failed}"
    )


def write_cleanup_audit_entry(entry: CleanupAuditEntry, log_dir: Path) -> None:
    """Hängt einen Sammel-Eintrag des Alt-Bestand-Aufräumens an audit.log an.

    Schreibfehler werden geloggt, nicht weitergeworfen (wie write_audit_entries).
    """
    log_dir.mkdir(parents=True, exist_ok=True)
    audit_path = log_dir / "audit.log"
    line = format_cleanup_audit_line(entry)
    try:
        with open(audit_path, "a", encoding="utf-8") as fh:
            fh.write(line + "\n")
        _log.debug("Audit: Aufräumen-Sammeleintrag nach %s geschrieben", audit_path)
    except OSError as exc:
        _log.warning("Audit-Log (Aufräumen) konnte nicht geschrieben werden: %s", exc)


def write_audit_entries(entries: list[AuditEntry], log_dir: Path) -> None:
    """Hängt Einträge an audit.log im log_dir an.

    audit.log rotiert NICHT — es ist ein dauerhaftes Fachprotokoll.
    Schreibfehler werden geloggt, nicht weitergeworfen.
    """
    if not entries:
        return
    log_dir.mkdir(parents=True, exist_ok=True)
    audit_path = log_dir / "audit.log"
    ts = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    lines = [format_audit_line(e, ts) for e in entries]
    try:
        with open(audit_path, "a", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")
        _log.debug("Audit: %d Eintrag/Einträge nach %s geschrieben", len(entries), audit_path)
    except OSError as exc:
        _log.warning("Audit-Log konnte nicht geschrieben werden: %s", exc)
