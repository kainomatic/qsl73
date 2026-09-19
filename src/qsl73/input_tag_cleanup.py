# QSL73 — Copyright (C) 2026 DF1DS (kainomatic) — SPDX-License-Identifier: GPL-3.0-or-later
"""Alt-Bestand-Aufräumen: Eingangs-Tag bei bereits erledigten Karten entfernen (Issue #41).

Der Eingangs-Tag ist seit Issue #41 ein Arbeitskorb, keine Dauer-Kategorie — er wird
von neu bestätigten/ignorierten Karten automatisch entfernt (run.write_selected,
ignore.ignore_card). Karten, die von FRÜHEREN QSL73-Versionen bestätigt oder
ignoriert wurden, tragen den Eingangs-Tag noch. Dieses Modul zählt sie und entfernt
ihn — ausschließlich nach Rückfrage (KONZEPT §5: kein stilles/automatisches
Aufräumen), nur den Eingangs-Tag, alle anderen Tags unverändert.

Öffentliche API (tk-frei):
  CleanupResult                    — Ergebnis eines Aufräumlaufs (removed, failed)
  count_input_tag_leftovers        — Anzahl betroffener Dokumente (für Abfrage-Dialog)
  find_input_tag_leftover_doc_ids  — doc_ids der betroffenen Dokumente (dedupliziert)
  remove_input_tag_from_leftovers  — führt das Aufräumen aus, schreibt Audit-Sammelzeile
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from qsl73.audit import CleanupAuditEntry, write_cleanup_audit_entry
from qsl73.config import TagsConfig
from qsl73.paperless import PaperlessClient

_log = logging.getLogger("qsl73")


@dataclass
class CleanupResult:
    """Ergebnis eines Alt-Bestand-Aufräumlaufs."""

    removed: int
    failed: int


def count_input_tag_leftovers(client: PaperlessClient, tags_config: TagsConfig) -> int:
    """Zählt Dokumente mit Eingangs-Tag UND (Bestätigt-Tag ODER Ignoriert-Tag).

    Summe zweier count_documents_with_all_tags-Aufrufe (Issue #41, Grundentscheidung 7).
    Fehlt einer der Tags in Paperless, liefert der jeweilige Aufruf 0 (ADR-0032-Muster,
    kein Fehler). Netzwerkfehler propagieren — der Aufrufer entscheidet über Retry
    (bewusst kein Verschlucken: „Paperless nicht erreichbar" darf NICHT als
    „nichts zu tun" gewertet werden).
    """
    n_confirmed = client.count_documents_with_all_tags(
        [tags_config.input, tags_config.confirmed]
    )
    n_ignored = client.count_documents_with_all_tags(
        [tags_config.input, tags_config.ignored]
    )
    return n_confirmed + n_ignored


def find_input_tag_leftover_doc_ids(
    client: PaperlessClient, tags_config: TagsConfig
) -> list[int]:
    """Gibt die doc_ids aller betroffenen Dokumente zurück (dedupliziert, Reihenfolge erhalten)."""
    docs_confirmed = client.list_documents_with_all_tags(
        [tags_config.input, tags_config.confirmed]
    )
    docs_ignored = client.list_documents_with_all_tags(
        [tags_config.input, tags_config.ignored]
    )
    seen: dict[int, None] = {}
    for doc in docs_confirmed + docs_ignored:
        doc_id = doc.get("id")
        if doc_id is not None:
            seen.setdefault(doc_id, None)
    return list(seen.keys())


def remove_input_tag_from_leftovers(
    client: PaperlessClient, tags_config: TagsConfig, log_dir: Path
) -> CleanupResult:
    """Entfernt den Eingangs-Tag von allen betroffenen Dokumenten.

    Nur der Eingangs-Tag wird entfernt (remove_tag_from_document — bestehende,
    getestete Methode, kein neues Tag wird hinzugefügt). Fehler einzelner Dokumente
    brechen den Rest NICHT ab (Issue #41, Umsetzungshinweis 10). Schreibt danach
    EINE Audit-Sammelzeile (kein Eintrag pro Dokument).
    """
    doc_ids = find_input_tag_leftover_doc_ids(client, tags_config)
    removed = 0
    failed = 0
    for doc_id in doc_ids:
        try:
            client.remove_tag_from_document(doc_id, tags_config.input)
            removed += 1
        except Exception as exc:
            failed += 1
            _log.warning(
                "Eingangs-Tag konnte für Dok. %s nicht entfernt werden: %s", doc_id, exc
            )

    write_cleanup_audit_entry(CleanupAuditEntry(removed=removed, failed=failed), log_dir)
    _log.info("Alt-Bestand-Aufräumen abgeschlossen — entfernt=%d fehler=%d", removed, failed)
    return CleanupResult(removed=removed, failed=failed)
