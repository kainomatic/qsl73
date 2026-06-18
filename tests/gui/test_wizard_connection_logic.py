# QSL73 — Copyright (C) 2026 DF1DS (kainomatic) — SPDX-License-Identifier: GPL-3.0-or-later
"""Tests für Verbindungstest-Logik des Setup-Assistenten — kein tk erforderlich."""
from __future__ import annotations

import pytest

from qsl73.config import Config
from qsl73.gui.wizard_logic import (
    MSG_AUTH_FAILED,
    MSG_SERVER_UNREACHABLE,
    MSG_URL_EMPTY,
    format_connection_error,
    format_url_error,
    resolve_effective_token,
)
from qsl73.paperless import PaperlessAuthError, PaperlessConnectionError


# ---------------------------------------------------------------------------
# format_url_error
# ---------------------------------------------------------------------------


class TestFormatUrlError:
    def test_empty_string_returns_error(self):
        assert format_url_error("") == MSG_URL_EMPTY

    def test_none_like_whitespace_returns_error(self):
        assert format_url_error("   ") == MSG_URL_EMPTY

    def test_https_placeholder_returns_error(self):
        assert format_url_error("https://") == MSG_URL_EMPTY

    def test_http_placeholder_returns_error(self):
        assert format_url_error("http://") == MSG_URL_EMPTY

    def test_valid_url_returns_none(self):
        assert format_url_error("https://paperless.example.com") is None

    def test_valid_url_with_port_returns_none(self):
        assert format_url_error("http://192.168.1.1:8080") is None

    def test_url_with_trailing_slash_returns_none(self):
        assert format_url_error("https://paperless.local/") is None

    def test_padded_placeholder_returns_error(self):
        assert format_url_error("  https://  ") == MSG_URL_EMPTY


# ---------------------------------------------------------------------------
# resolve_effective_token
# ---------------------------------------------------------------------------


class TestResolveEffectiveToken:
    def _cfg_with_token(self, token: str) -> Config:
        cfg = Config()
        cfg.paperless.token = token
        return cfg

    def test_new_token_in_field_takes_priority(self):
        cfg = self._cfg_with_token("existing-token")
        result = resolve_effective_token("new-token", cfg)
        assert result == "new-token"

    def test_empty_field_uses_existing_token(self):
        cfg = self._cfg_with_token("existing-token")
        result = resolve_effective_token("", cfg)
        assert result == "existing-token"

    def test_whitespace_field_uses_existing_token(self):
        cfg = self._cfg_with_token("existing-token")
        result = resolve_effective_token("   ", cfg)
        assert result == "existing-token"

    def test_empty_field_no_existing_config_returns_empty(self):
        result = resolve_effective_token("", None)
        assert result == ""

    def test_empty_field_existing_config_no_token_returns_empty(self):
        cfg = self._cfg_with_token("")
        result = resolve_effective_token("", cfg)
        assert result == ""

    def test_new_token_overrides_even_when_existing_present(self):
        cfg = self._cfg_with_token("old")
        result = resolve_effective_token("brand-new", cfg)
        assert result == "brand-new"

    def test_token_not_written_back_to_field(self):
        """resolve_effective_token darf nur zurückgeben, nie mutieren."""
        cfg = self._cfg_with_token("secret")
        token_field = ""
        resolve_effective_token(token_field, cfg)
        assert token_field == ""  # unveränderlich


# ---------------------------------------------------------------------------
# format_connection_error — neue differenzierte Meldungen
# ---------------------------------------------------------------------------


class TestFormatConnectionErrorMessages:
    def test_auth_error_returns_auth_failed_message(self):
        exc = PaperlessAuthError("401")
        assert format_connection_error(exc) == MSG_AUTH_FAILED

    def test_connection_error_returns_unreachable_message(self):
        exc = PaperlessConnectionError("timeout")
        assert format_connection_error(exc) == MSG_SERVER_UNREACHABLE

    def test_generic_error_contains_exception_text(self):
        msg = format_connection_error(ValueError("spezifischer Fehlertext"))
        assert "spezifischer Fehlertext" in msg

    def test_auth_error_does_not_leak_exception_details(self):
        """Fehlermeldung soll klar und einheitlich sein, keine rohen Exception-Details."""
        exc = PaperlessAuthError("secret-token-value")
        msg = format_connection_error(exc)
        assert "secret-token-value" not in msg

    def test_connection_error_does_not_leak_url(self):
        exc = PaperlessConnectionError("https://internal-server/api")
        msg = format_connection_error(exc)
        assert "https://internal-server/api" not in msg
