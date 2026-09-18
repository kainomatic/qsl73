# src/qsl73/ignore.py
# QSL73 — Copyright (C) 2026 DF1DS (kainomatic) — SPDX-License-Identifier: GPL-3.0-or-later
"""Ignorieren/Wieder-Aufnehmen von QSL-Karten (ADR-0059).

Ersetzt den ungenutzten Unsicher-Tag (tags.uncertain war faktisch tot — nirgends
gesetzt). Karten, die nie zuordenbar sind, können dauerhaft aus dem Lauf entfernt
und jederzeit zurückgeholt werden.

Wirkt SOFORT über einen Paperless-Tag — die Log4OM-DB wird dabei NICHT berührt
(ausdrückliche Ausnahme zur KONZEPT §5-Garantie "vor 'Jetzt schreiben' weder DB
noch Tags"; die Garantie schützt das Logbuch und bleibt dafür uneingeschränkt
gültig). QSL73 legt den Ignoriert-Tag NICHT automatisch an (ADR-0031 §5).

Öffentliche API (tk-frei):
  IgnoreTagMissingError  — tags.ignored ist leer oder existiert nicht in Paperless
  ignore_card            — setzt den Ignoriert-Tag + Audit-Eintrag
  unignore_card          — entfernt den Ignoriert-Tag + Audit-Eintrag
"""
from __future__ import annotations

import logging
from pathlib import Path

from qsl73.audit import IgnoreAuditEntry, write_ignore_audit_entry
from qsl73.config import TagsConfig
from qsl73.paperless import PaperlessClient

_log = logging.getLogger("qsl73")


class IgnoreTagMissingError(Exception):
    """Der konfigurierte Ignoriert-Tag ist leer oder existiert nicht in Paperless.

    QSL73 legt diesen Tag NICHT automatisch an (ADR-0031 §5) — der Nutzer muss ihn
    zuerst unter Bearbeiten → Einstellungen… auswählen oder anlegen.
    """

    def __init__(self, tag_name: str) -> None:
        self.tag_name = tag_name
        super().__init__(
            f"Ignoriert-Tag '{tag_name}' ist leer oder in Paperless nicht vorhanden."
            if tag_name
            else "Kein Ignoriert-Tag konfiguriert."
        )


def ignore_card(
    client: PaperlessClient,
    doc_id: int,
    tags_config: TagsConfig,
    log_dir: Path,
    callsign: str = "",
) -> None:
    """Setzt den Ignoriert-Tag für ein Dokument. Andere Tags bleiben unverändert.

    Wirft IgnoreTagMissingError wenn tags_config.ignored leer ist oder der Tag
    nicht in Paperless existiert — legt in diesem Fall KEINEN Tag an: kein
    create_tag, kein PATCH, kein Audit-Eintrag.
    """
    tag_name = (tags_config.ignored or "").strip()
    if not tag_name or client.get_tag_id(tag_name) is None:
        raise IgnoreTagMissingError(tag_name)

    client.add_tag_to_document(doc_id, tag_name)
    write_ignore_audit_entry(
        IgnoreAuditEntry(doc_id=doc_id, callsign=callsign or "?", action="ignoriert"),
        log_dir,
    )
    _log.info("doc_id=%d als ignoriert markiert (Tag '%s')", doc_id, tag_name)


def unignore_card(
    client: PaperlessClient,
    doc_id: int,
    tags_config: TagsConfig,
    log_dir: Path,
    callsign: str = "",
) -> None:
    """Entfernt den Ignoriert-Tag von einem Dokument. Andere Tags bleiben unverändert.

    Wirft IgnoreTagMissingError wenn tags_config.ignored leer ist oder der Tag
    nicht (mehr) in Paperless existiert (nichts zu entfernen) — symmetrisch zu
    ignore_card, kein Audit-Eintrag in diesem Fall.
    """
    tag_name = (tags_config.ignored or "").strip()
    if not tag_name or client.get_tag_id(tag_name) is None:
        raise IgnoreTagMissingError(tag_name)

    client.remove_tag_from_document(doc_id, tag_name)
    write_ignore_audit_entry(
        IgnoreAuditEntry(doc_id=doc_id, callsign=callsign or "?", action="wieder_aufgenommen"),
        log_dir,
    )
    _log.info("doc_id=%d wieder aufgenommen (Tag '%s' entfernt)", doc_id, tag_name)
