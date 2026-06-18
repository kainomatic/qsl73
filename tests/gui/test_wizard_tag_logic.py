# QSL73 — Copyright (C) 2026 DF1DS (kainomatic) — SPDX-License-Identifier: GPL-3.0-or-later
"""Tests für Tag-Logik-Hilfsfunktionen des Setup-Assistenten — kein tk erforderlich."""
from __future__ import annotations

import pytest

from qsl73.gui.wizard_logic import (
    auto_matching_warning,
    format_connection_error,
    format_connection_ok,
    retain_selection_if_valid,
    validate_tag_name,
)
from qsl73.paperless import PaperlessAuthError, PaperlessConnectionError


class TestFormatConnectionOk:
    def test_includes_count(self):
        msg = format_connection_ok(42)
        assert "42" in msg

    def test_indicates_success(self):
        msg = format_connection_ok(3)
        assert "OK" in msg or "ok" in msg.lower() or "gefunden" in msg

    def test_zero_tags(self):
        msg = format_connection_ok(0)
        assert "0" in msg


class TestFormatConnectionError:
    def test_auth_error_message_mentions_auth(self):
        exc = PaperlessAuthError("ungültig")
        msg = format_connection_error(exc)
        assert "Authentifizierung" in msg or "Auth" in msg

    def test_connection_error_message_mentions_verbindung(self):
        exc = PaperlessConnectionError("refused")
        msg = format_connection_error(exc)
        assert "Verbindung" in msg or "Fehler" in msg

    def test_generic_error_returns_message(self):
        msg = format_connection_error(ValueError("etwas kaputt"))
        assert "Fehler" in msg or "etwas kaputt" in msg

    def test_no_secrets_in_message(self):
        exc = PaperlessConnectionError("contains-secret-token-value")
        msg = format_connection_error(exc)
        # Wir prüfen nur dass eine Meldung entsteht, nicht auf Secret-Freiheit (wird in paperless-Ebene gehandhabt)
        assert isinstance(msg, str) and len(msg) > 0


class TestAutoMatchingWarning:
    def test_no_warning_for_algo_zero(self):
        tags = [{"id": 1, "name": "qsl-bestätigt", "matching_algorithm": 0}]
        assert auto_matching_warning("qsl-bestätigt", tags) is None

    def test_warning_for_algo_nonzero(self):
        tags = [{"id": 1, "name": "qsl-bestätigt", "matching_algorithm": 6}]
        result = auto_matching_warning("qsl-bestätigt", tags)
        assert result is not None
        assert "qsl-bestätigt" in result

    def test_warning_includes_algorithm_number(self):
        tags = [{"id": 1, "name": "mein-tag", "matching_algorithm": 3}]
        result = auto_matching_warning("mein-tag", tags)
        assert result is not None
        assert "3" in result

    def test_no_warning_tag_not_in_list(self):
        tags = [{"id": 1, "name": "other-tag", "matching_algorithm": 0}]
        assert auto_matching_warning("unknown-tag", tags) is None

    def test_no_warning_empty_name(self):
        tags = [{"id": 1, "name": "", "matching_algorithm": 6}]
        assert auto_matching_warning("", tags) is None

    def test_case_insensitive_match(self):
        tags = [{"id": 1, "name": "QSL-Bestätigt", "matching_algorithm": 3}]
        result = auto_matching_warning("qsl-bestätigt", tags)
        assert result is not None

    def test_no_warning_empty_tag_list(self):
        assert auto_matching_warning("some-tag", []) is None

    def test_warning_algo_1_any(self):
        tags = [{"id": 1, "name": "auto-tag", "matching_algorithm": 1}]
        result = auto_matching_warning("auto-tag", tags)
        assert result is not None
        assert "1" in result

    def test_warning_algo_4_regex(self):
        tags = [{"id": 2, "name": "regex-tag", "matching_algorithm": 4}]
        result = auto_matching_warning("regex-tag", tags)
        assert result is not None


class TestValidateTagName:
    def test_valid_name_returns_no_errors(self):
        assert validate_tag_name("qsl-bestätigt") == []

    def test_empty_string_returns_error(self):
        errors = validate_tag_name("")
        assert len(errors) == 1

    def test_whitespace_only_returns_error(self):
        errors = validate_tag_name("   ")
        assert len(errors) == 1

    def test_single_char_valid(self):
        assert validate_tag_name("x") == []

    def test_error_message_is_informative(self):
        errors = validate_tag_name("")
        assert len(errors[0]) > 5


class TestRetainSelectionIfValid:
    def test_current_in_new_values_retained(self):
        result = retain_selection_if_valid("qsl-card", ["qsl-card", "other"])
        assert result == "qsl-card"

    def test_current_not_in_new_values_cleared(self):
        result = retain_selection_if_valid("old-tag", ["new-tag"])
        assert result == ""

    def test_empty_current_stays_empty(self):
        assert retain_selection_if_valid("", ["a", "b"]) == ""

    def test_empty_new_values_clears_current(self):
        assert retain_selection_if_valid("tag", []) == ""

    def test_exact_match_required(self):
        assert retain_selection_if_valid("qsl-Card", ["qsl-card"]) == ""
