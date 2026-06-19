# QSL73 — Copyright (C) 2026 DF1DS (kainomatic) — SPDX-License-Identifier: GPL-3.0-or-later
"""Tests für den Beta-Start-Hinweis-Dialog (kein Display nötig)."""
from __future__ import annotations

from unittest.mock import MagicMock, patch


def test_notice_constants_exist():
    """Alle Textkonstanten vorhanden (i18n-Vorbereitung)."""
    from qsl73.gui import beta_notice

    assert hasattr(beta_notice, "_NOTICE_TITLE")
    assert hasattr(beta_notice, "_NOTICE_BODY")
    assert hasattr(beta_notice, "_NOTICE_BTN")


def test_notice_title_mentions_beta():
    """Titel enthält 'Beta'-Kennzeichnung."""
    from qsl73.gui.beta_notice import _NOTICE_TITLE

    assert "beta" in _NOTICE_TITLE.lower()


def test_notice_body_mentions_backup_and_report():
    """Hinweistext erwähnt Backup und Fehler-melden."""
    from qsl73.gui.beta_notice import _NOTICE_BODY

    body_lower = _NOTICE_BODY.lower()
    assert "backup" in body_lower
    assert "fehler" in body_lower


def test_show_beta_notice_callable():
    """show_beta_notice ist aufrufbar."""
    from qsl73.gui.beta_notice import show_beta_notice

    assert callable(show_beta_notice)


def test_show_beta_notice_recovers_silently_on_exception():
    """show_beta_notice stürzt nicht ab, wenn kein Display verfügbar."""
    from qsl73.gui.beta_notice import show_beta_notice

    parent = MagicMock()
    with patch("qsl73.gui.beta_notice.tk.Toplevel", side_effect=RuntimeError("no display")):
        show_beta_notice(parent)  # darf keine Exception werfen


def test_show_beta_notice_recovers_on_any_error():
    """show_beta_notice schluckt beliebige Exceptions (nice-to-have-Hinweis)."""
    from qsl73.gui.beta_notice import show_beta_notice

    parent = MagicMock()
    with patch("qsl73.gui.beta_notice.tk.Toplevel", side_effect=Exception("unexpected")):
        show_beta_notice(parent)  # darf keine Exception werfen
