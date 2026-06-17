"""Tests für qsl73.logging_setup und qsl73.qr.qr_backend_status."""
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def clean_qsl73_logger():
    """Isoliert jeden Test: qsl73-Logger-Handler werden vor/nach jedem Test geleert."""
    logger = logging.getLogger("qsl73")
    for h in list(logger.handlers):
        logger.removeHandler(h)
        h.close()
    logger.setLevel(logging.NOTSET)
    yield
    for h in list(logger.handlers):
        logger.removeHandler(h)
        h.close()
    logger.setLevel(logging.NOTSET)


class TestSetupLogging:
    def test_creates_log_file(self, tmp_path):
        from qsl73.logging_setup import setup_logging

        log_dir = tmp_path / "logs"
        setup_logging(log_dir)

        assert (log_dir / "qsl73.log").exists()

    def test_writes_log_entry(self, tmp_path):
        from qsl73.logging_setup import setup_logging

        log_dir = tmp_path / "logs"
        setup_logging(log_dir)
        logger = logging.getLogger("qsl73")
        logger.info("Test-Eintrag vom Unit-Test")
        for h in logger.handlers:
            h.flush()

        content = (log_dir / "qsl73.log").read_text(encoding="utf-8")
        assert "Test-Eintrag vom Unit-Test" in content

    def test_rotation_params(self, tmp_path):
        from qsl73.logging_setup import setup_logging

        log_dir = tmp_path / "logs"
        setup_logging(log_dir)
        logger = logging.getLogger("qsl73")
        handler = next(h for h in logger.handlers if isinstance(h, RotatingFileHandler))

        assert handler.maxBytes == 1 * 1024 * 1024
        assert handler.backupCount == 5

    def test_log_format_contains_timestamp_level_module(self, tmp_path):
        from qsl73.logging_setup import setup_logging

        log_dir = tmp_path / "logs"
        setup_logging(log_dir)
        logger = logging.getLogger("qsl73")
        logger.info("FormatCheck")
        for h in logger.handlers:
            h.flush()

        content = (log_dir / "qsl73.log").read_text(encoding="utf-8")
        assert "INFO" in content
        assert "FormatCheck" in content

    def test_idempotent_single_handler(self, tmp_path):
        from qsl73.logging_setup import setup_logging

        log_dir = tmp_path / "logs"
        setup_logging(log_dir)
        setup_logging(log_dir)

        logger = logging.getLogger("qsl73")
        count = sum(1 for h in logger.handlers if isinstance(h, RotatingFileHandler))
        assert count == 1

    def test_default_level_info(self, tmp_path):
        from qsl73.logging_setup import setup_logging

        log_dir = tmp_path / "logs_info"
        setup_logging(log_dir)

        assert logging.getLogger("qsl73").level == logging.INFO

    def test_debug_level_via_param(self, tmp_path):
        from qsl73.logging_setup import setup_logging

        log_dir = tmp_path / "logs_debug"
        setup_logging(log_dir, debug=True)

        assert logging.getLogger("qsl73").level == logging.DEBUG

    def test_debug_level_via_env(self, tmp_path, monkeypatch):
        monkeypatch.setenv("QSL73_DEBUG", "1")
        from qsl73.logging_setup import setup_logging

        log_dir = tmp_path / "logs_debug_env"
        setup_logging(log_dir)

        assert logging.getLogger("qsl73").level == logging.DEBUG

    def test_debug_env_zero_keeps_info(self, tmp_path, monkeypatch):
        monkeypatch.setenv("QSL73_DEBUG", "0")
        from qsl73.logging_setup import setup_logging

        log_dir = tmp_path / "logs_zero"
        setup_logging(log_dir)

        assert logging.getLogger("qsl73").level == logging.INFO

    def test_creates_parent_dirs(self, tmp_path):
        from qsl73.logging_setup import setup_logging

        nested = tmp_path / "a" / "b" / "c" / "logs"
        setup_logging(nested)

        assert (nested / "qsl73.log").exists()

    def test_returns_log_dir_path(self, tmp_path):
        from qsl73.logging_setup import setup_logging

        log_dir = tmp_path / "logs"
        result = setup_logging(log_dir)

        assert result == log_dir

    def test_no_secrets_in_log(self, tmp_path):
        """Kein Token/Passwort gelangt in das Diagnose-Log."""
        from qsl73.logging_setup import setup_logging

        log_dir = tmp_path / "logs_secrets"
        setup_logging(log_dir)
        logger = logging.getLogger("qsl73")
        fake_token = "SUPERSECRET-TOKEN-XYZ-12345"

        # Typische run.py-Einträge — kein Token dabei
        logger.info("QSL73 0.1.0 gestartet")
        logger.info("Lauf gestartet — 3 Dokumente (Tag 'qsl-card'), 10 QSO-Kandidaten")
        logger.info("doc_id=42: quelle=ocr ergebnis=CERTAIN")
        logger.info("Lauf beendet — sicher=1 unsicher=1 kein_treffer=1")
        logger.info("Schreiben abgeschlossen — geschrieben=1 übersprungen=0")
        for h in logger.handlers:
            h.flush()

        content = (log_dir / "qsl73.log").read_text(encoding="utf-8")
        assert fake_token not in content

    def test_get_log_dir_contains_qsl73(self):
        from qsl73.logging_setup import get_log_dir

        log_dir = get_log_dir()
        assert "QSL73" in str(log_dir)
        assert "logs" in str(log_dir).lower()


class TestQrBackendStatus:
    def test_returns_dict_with_bool_values(self):
        from qsl73.qr import qr_backend_status

        status = qr_backend_status()
        assert isinstance(status, dict)
        assert "fitz" in status
        assert "zxing" in status
        assert isinstance(status["fitz"], bool)
        assert isinstance(status["zxing"], bool)

    def test_both_unavailable(self, monkeypatch):
        import qsl73.qr as qr_module

        monkeypatch.setattr(qr_module, "_FITZ_OK", False)
        monkeypatch.setattr(qr_module, "_ZXING_OK", False)

        status = qr_module.qr_backend_status()
        assert status["fitz"] is False
        assert status["zxing"] is False

    def test_both_available(self, monkeypatch):
        import qsl73.qr as qr_module

        monkeypatch.setattr(qr_module, "_FITZ_OK", True)
        monkeypatch.setattr(qr_module, "_ZXING_OK", True)

        status = qr_module.qr_backend_status()
        assert status["fitz"] is True
        assert status["zxing"] is True

    def test_fitz_missing_zxing_present(self, monkeypatch):
        import qsl73.qr as qr_module

        monkeypatch.setattr(qr_module, "_FITZ_OK", False)
        monkeypatch.setattr(qr_module, "_ZXING_OK", True)

        status = qr_module.qr_backend_status()
        assert status["fitz"] is False
        assert status["zxing"] is True
