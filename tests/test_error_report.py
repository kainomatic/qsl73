# tests/test_error_report.py
"""Tests für src/qsl73/error_report.py."""
import platform
import sys
from pathlib import Path
import pytest


class TestStripSecrets:
    def test_removes_token_line(self):
        from qsl73.error_report import _strip_secrets
        text = "Version: 1.0\ntoken: abc123\nOS: Windows"
        result = _strip_secrets(text)
        assert "abc123" not in result
        assert "Version: 1.0" in result
        assert "OS: Windows" in result

    def test_removes_password_line(self):
        from qsl73.error_report import _strip_secrets
        text = "App: QSL73\npassword=geheim\nStatus: ok"
        result = _strip_secrets(text)
        assert "geheim" not in result

    def test_removes_passwort_line(self):
        from qsl73.error_report import _strip_secrets
        text = "passwort: xyz"
        result = _strip_secrets(text)
        assert "xyz" not in result

    def test_keeps_normal_lines(self):
        from qsl73.error_report import _strip_secrets
        text = "QSL73 0.1.0 gestartet\nLauf beendet — sicher=1 unsicher=0"
        result = _strip_secrets(text)
        assert result == text

    def test_case_insensitive(self):
        from qsl73.error_report import _strip_secrets
        text = "TOKEN=abc"
        result = _strip_secrets(text)
        assert "abc" not in result


class TestStripUrlSecrets:
    """N3-Härtung: URL-eingebettete Credentials werden bereinigt (ADR-0035)."""

    def test_userinfo_password_removed(self):
        """Passwort in user:pass@host darf nicht im Ergebnis erscheinen."""
        from qsl73.error_report import _strip_secrets
        line = "Connecting to https://admin:pass123@paperless.local/api/"
        result = _strip_secrets(line)
        assert "pass123" not in result
        assert "admin" not in result

    def test_userinfo_replaced_with_placeholder(self):
        """userinfo-Block wird durch [gefiltert] ersetzt, Host bleibt sichtbar."""
        from qsl73.error_report import _strip_url_secrets
        line = "GET https://user:secret123@host.local/path"
        result = _strip_url_secrets(line)
        assert "[gefiltert]" in result
        assert "secret123" not in result
        assert "host.local" in result

    def test_query_token_value_removed(self):
        """Wert eines ?token=… Query-Parameters darf nicht erscheinen."""
        from qsl73.error_report import _strip_secrets
        line = "Request https://host/api?token=SECRET_VALUE_ABC&limit=10"
        result = _strip_secrets(line)
        assert "SECRET_VALUE_ABC" not in result

    def test_query_key_value_removed(self):
        """?key= wird gefiltert (nicht im Schlüsselwort-Filter, aber sensibel)."""
        from qsl73.error_report import _strip_url_secrets
        line = "GET https://host/?key=MY_API_KEY_123&format=json"
        result = _strip_url_secrets(line)
        assert "MY_API_KEY_123" not in result
        assert "format=json" in result

    def test_normal_url_unchanged(self):
        """Normale URL ohne Credentials bleibt unverändert."""
        from qsl73.error_report import _strip_secrets
        line = "Connected to https://paperless.local/api/documents/"
        result = _strip_secrets(line)
        assert result == line

    def test_keyword_lines_still_filtered(self):
        """Regression: bestehende Schlüsselwort-Filterung bleibt aktiv."""
        from qsl73.error_report import _strip_secrets
        text = "normal line\ntoken: abc\nanother line"
        result = _strip_secrets(text)
        assert "abc" not in result
        assert "normal line" in result


class TestBuildErrorReport:
    def test_contains_version(self, tmp_path):
        from qsl73.error_report import build_error_report
        report = build_error_report(
            version="0.1.0", channel="stable",
            log_dir=tmp_path, qr_status={"fitz": True, "zxing": True},
        )
        assert "0.1.0" in report

    def test_contains_channel(self, tmp_path):
        from qsl73.error_report import build_error_report
        report = build_error_report(
            version="0.1.0", channel="beta",
            log_dir=tmp_path, qr_status={"fitz": True, "zxing": True},
        )
        assert "beta" in report.lower()

    def test_contains_python_version(self, tmp_path):
        from qsl73.error_report import build_error_report
        report = build_error_report(
            version="0.1.0", channel="stable",
            log_dir=tmp_path, qr_status={"fitz": True, "zxing": True},
        )
        major_minor = f"{sys.version_info.major}.{sys.version_info.minor}"
        assert major_minor in report

    def test_contains_qr_status(self, tmp_path):
        from qsl73.error_report import build_error_report
        report = build_error_report(
            version="0.1.0", channel="stable",
            log_dir=tmp_path, qr_status={"fitz": False, "zxing": True},
        )
        assert "fitz" in report.lower() or "pymupdf" in report.lower()

    def test_no_secrets_in_report(self, tmp_path):
        """Token darf nicht im Bericht erscheinen — auch nicht wenn im Log."""
        from qsl73.error_report import build_error_report

        # Schreibe präparierten qsl73.log mit Token-Zeile
        log_dir = tmp_path
        log_file = log_dir / "qsl73.log"
        log_file.write_text(
            "2026-06-18 14:00:00 INFO app: QSL73 0.1.0 gestartet\n"
            "token=MEIN_GEHEIMER_TOKEN_12345\n"
            "2026-06-18 14:00:01 INFO run: Lauf beendet\n",
            encoding="utf-8",
        )

        report = build_error_report(
            version="0.1.0", channel="stable",
            log_dir=log_dir, qr_status={"fitz": True, "zxing": True},
        )
        assert "MEIN_GEHEIMER_TOKEN_12345" not in report

    def test_includes_log_lines(self, tmp_path):
        """Letzte N Zeilen aus qsl73.log erscheinen im Bericht."""
        from qsl73.error_report import build_error_report

        log_file = tmp_path / "qsl73.log"
        log_file.write_text(
            "INFO app: gestartet\nINFO run: Lauf beendet\n",
            encoding="utf-8",
        )

        report = build_error_report(
            version="0.1.0", channel="stable",
            log_dir=tmp_path, qr_status={"fitz": True, "zxing": True},
        )
        assert "gestartet" in report or "Lauf beendet" in report

    def test_missing_log_file_no_crash(self, tmp_path):
        """Kein Absturz wenn qsl73.log nicht existiert."""
        from qsl73.error_report import build_error_report
        report = build_error_report(
            version="0.1.0", channel="stable",
            log_dir=tmp_path / "nonexistent",
            qr_status={"fitz": True, "zxing": True},
        )
        assert "0.1.0" in report  # Bericht ist trotzdem vollständig


class TestBuildGithubUrl:
    def test_url_starts_with_github(self):
        from qsl73.error_report import build_github_url
        url = build_github_url("Test-Titel", "Test-Body")
        assert url.startswith("https://github.com/kainomatic/qsl73/issues/new")

    def test_title_is_url_encoded(self):
        from qsl73.error_report import build_github_url
        url = build_github_url("Fehler #1 / Bug", "body")
        query = url.split("?", 1)[1]
        assert " " not in query          # kein Leerzeichen im Query-Teil
        assert "%23" in query.lower()    # # → %23
        assert "%2f" in query.lower()    # / → %2F

    def test_body_is_url_encoded(self):
        from qsl73.error_report import build_github_url
        url = build_github_url("titel", "Zeile 1\nZeile 2")
        assert "Zeile" in url

    def test_custom_repo(self):
        from qsl73.error_report import build_github_url
        url = build_github_url("t", "b", repo="other/repo")
        assert "other/repo" in url


class TestSaveReportToFile:
    def test_writes_file(self, tmp_path):
        from qsl73.error_report import save_report_to_file
        path = tmp_path / "report.txt"
        save_report_to_file("Inhalt des Berichts", path)
        assert path.exists()
        assert "Inhalt des Berichts" in path.read_text(encoding="utf-8")
