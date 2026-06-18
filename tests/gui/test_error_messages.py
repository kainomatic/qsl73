# QSL73 — Copyright (C) 2026 DF1DS (kainomatic) — SPDX-License-Identifier: GPL-3.0-or-later
"""Tests für gui/error_messages.py — rein, kein tk erforderlich."""
from __future__ import annotations

import pytest

from qsl73.gui.error_messages import classify_error
from qsl73.log4om_db import DatabaseBusyError, DatabaseChangedError, SchemaError
from qsl73.log4om_write import QslEntryNotFoundError
from qsl73.paperless import (
    PaperlessAPIError,
    PaperlessAuthError,
    PaperlessConnectionError,
    PaperlessNotFoundError,
)


class TestDatabaseChangedError:
    def test_is_expected(self):
        c = classify_error(DatabaseChangedError("x"))
        assert c.is_expected is True

    def test_title(self):
        c = classify_error(DatabaseChangedError("x"))
        assert c.title == "Datenbank hat sich geändert"

    def test_user_message_contains_key_hint(self):
        c = classify_error(DatabaseChangedError("x"))
        assert "Durchlauf" in c.user_message
        assert "nichts geschrieben" in c.user_message

    def test_status_message_short(self):
        c = classify_error(DatabaseChangedError("x"))
        assert "neu starten" in c.status_message


class TestSchemaError:
    def test_is_expected(self):
        c = classify_error(SchemaError("Schema kaputt"))
        assert c.is_expected is True

    def test_title(self):
        c = classify_error(SchemaError("Schema kaputt"))
        assert c.title == "Datenbankformat nicht erkannt"

    def test_detail_in_user_message(self):
        c = classify_error(SchemaError("Schema kaputt"))
        assert "Schema kaputt" in c.user_message


class TestDatabaseBusyError:
    def test_is_expected(self):
        c = classify_error(DatabaseBusyError("busy"))
        assert c.is_expected is True

    def test_title(self):
        c = classify_error(DatabaseBusyError("busy"))
        assert c.title == "Datenbank gesperrt"


class TestQslEntryNotFoundError:
    def test_is_expected(self):
        c = classify_error(QslEntryNotFoundError("not found"))
        assert c.is_expected is True

    def test_title(self):
        c = classify_error(QslEntryNotFoundError("not found"))
        assert c.title == "QSL-Eintrag nicht gefunden"

    def test_nichts_geschrieben_in_message(self):
        c = classify_error(QslEntryNotFoundError("not found"))
        assert "nichts geschrieben" in c.user_message


class TestPaperlessErrors:
    def test_connection_is_expected(self):
        c = classify_error(PaperlessConnectionError("timeout"))
        assert c.is_expected is True

    def test_connection_title(self):
        c = classify_error(PaperlessConnectionError("timeout"))
        assert c.title == "Paperless nicht erreichbar"

    def test_auth_is_expected(self):
        c = classify_error(PaperlessAuthError("403"))
        assert c.is_expected is True

    def test_auth_title(self):
        c = classify_error(PaperlessAuthError("403"))
        assert c.title == "Paperless-Authentifizierung fehlgeschlagen"

    def test_auth_mentions_token(self):
        c = classify_error(PaperlessAuthError("403"))
        assert "Token" in c.user_message

    def test_not_found_is_expected(self):
        c = classify_error(PaperlessNotFoundError("404"))
        assert c.is_expected is True

    def test_api_error_is_expected(self):
        c = classify_error(PaperlessAPIError("500"))
        assert c.is_expected is True

    def test_api_error_title(self):
        c = classify_error(PaperlessAPIError("500"))
        assert c.title == "Paperless-API-Fehler"


class TestUnexpectedError:
    def test_runtime_error_not_expected(self):
        c = classify_error(RuntimeError("boom"))
        assert c.is_expected is False

    def test_runtime_error_title(self):
        c = classify_error(RuntimeError("boom"))
        assert c.title == "Unerwarteter Fehler"

    def test_str_in_user_message(self):
        c = classify_error(RuntimeError("boom"))
        assert "boom" in c.user_message

    def test_str_in_status_message(self):
        c = classify_error(RuntimeError("boom"))
        assert "boom" in c.status_message

    def test_value_error_not_expected(self):
        c = classify_error(ValueError("bad"))
        assert c.is_expected is False
