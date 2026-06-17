# QSL73 — Copyright (C) 2026 DF1DS (kainomatic) — SPDX-License-Identifier: GPL-3.0-or-later
"""Tests für die Auth-Modus-Logik des Setup-Assistenten — kein tk erforderlich."""
from __future__ import annotations

from qsl73.gui.wizard_logic import auth_fields_for_mode, validate_auth_fields


class TestAuthFieldsForMode:
    def test_token_mode_shows_token_hides_password(self):
        result = auth_fields_for_mode("token")
        assert result["show_token"] is True
        assert result["show_username_password"] is False

    def test_password_mode_hides_token_shows_password(self):
        result = auth_fields_for_mode("password")
        assert result["show_token"] is False
        assert result["show_username_password"] is True

    def test_unknown_mode_defaults_to_token_behaviour(self):
        result = auth_fields_for_mode("something_else")
        assert result["show_token"] is True
        assert result["show_username_password"] is False


class TestValidateAuthFields:
    def test_token_mode_valid(self):
        assert validate_auth_fields("token", token="abc123") == []

    def test_token_mode_requires_token(self):
        errors = validate_auth_fields("token", token="")
        assert len(errors) == 1
        assert "Token" in errors[0]

    def test_token_mode_whitespace_only_token_fails(self):
        errors = validate_auth_fields("token", token="   ")
        assert len(errors) == 1

    def test_password_mode_valid(self):
        assert validate_auth_fields("password", username="user", password="pass") == []

    def test_password_mode_requires_username(self):
        errors = validate_auth_fields("password", username="", password="pass")
        assert any("Benutzername" in e for e in errors)
        assert all("Passwort" not in e for e in errors)

    def test_password_mode_requires_password(self):
        errors = validate_auth_fields("password", username="user", password="")
        assert any("Passwort" in e for e in errors)
        assert all("Benutzername" not in e for e in errors)

    def test_password_mode_requires_both(self):
        errors = validate_auth_fields("password", username="", password="")
        assert len(errors) == 2
