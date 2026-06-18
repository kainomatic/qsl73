"""Tests für src/qsl73/audit.py."""
from pathlib import Path
import pytest


class TestFormatAuditLine:
    def test_contains_all_fields(self):
        from qsl73.audit import AuditEntry, format_audit_line

        entry = AuditEntry(
            doc_id=42,
            qsoid="qso-abc-123",
            callsign="DK1AB",
            qso_date="2025-11-01",
            band="20m",
            mode="FT8",
            route="bureau",
            source="auto",
            backup_path="/path/to/backup.sqlite",
        )
        line = format_audit_line(entry, ts="2026-06-18T14:30:00")

        assert "doc_id=42" in line
        assert "qsoid=qso-abc-123" in line
        assert "call=DK1AB" in line
        assert "date=2025-11-01" in line
        assert "band=20m" in line
        assert "mode=FT8" in line
        assert "route=bureau" in line
        assert "source=auto" in line
        assert "backup=/path/to/backup.sqlite" in line
        assert "2026-06-18T14:30:00" in line

    def test_manuell_source(self):
        from qsl73.audit import AuditEntry, format_audit_line

        entry = AuditEntry(
            doc_id=7, qsoid="q1", callsign="DL1XY", qso_date="2024-03-10",
            band="40m", mode="SSB", route="direct", source="manuell",
            backup_path="–",
        )
        line = format_audit_line(entry, ts="2026-01-01T00:00:00")
        assert "source=manuell" in line

    def test_no_ts_param_uses_current_time(self):
        from qsl73.audit import AuditEntry, format_audit_line
        import re

        entry = AuditEntry(
            doc_id=1, qsoid="q1", callsign="X", qso_date="2025-01-01",
            band="10m", mode="CW", route="undefined", source="auto",
            backup_path="–",
        )
        line = format_audit_line(entry)
        # Prüfe ISO-Zeitstempel-Muster YYYY-MM-DDTHH:MM:SS
        assert re.search(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", line)

    def test_single_line_no_newline(self):
        from qsl73.audit import AuditEntry, format_audit_line

        entry = AuditEntry(
            doc_id=1, qsoid="q1", callsign="X", qso_date="2025-01-01",
            band="10m", mode="CW", route="undefined", source="auto",
            backup_path="–",
        )
        line = format_audit_line(entry, ts="2026-01-01T00:00:00")
        assert "\n" not in line


class TestWriteAuditEntries:
    def test_creates_audit_log(self, tmp_path):
        from qsl73.audit import AuditEntry, write_audit_entries

        entries = [
            AuditEntry(
                doc_id=10, qsoid="q10", callsign="DK9ZZ", qso_date="2025-07-01",
                band="80m", mode="FT8", route="bureau", source="auto",
                backup_path="–",
            )
        ]
        write_audit_entries(entries, tmp_path)
        audit_path = tmp_path / "audit.log"
        assert audit_path.exists()

    def test_appends_on_second_call(self, tmp_path):
        from qsl73.audit import AuditEntry, write_audit_entries

        e1 = AuditEntry(doc_id=1, qsoid="q1", callsign="A", qso_date="2025-01-01",
                        band="20m", mode="FT8", route="bureau", source="auto", backup_path="–")
        e2 = AuditEntry(doc_id=2, qsoid="q2", callsign="B", qso_date="2025-02-01",
                        band="40m", mode="SSB", route="direct", source="manuell", backup_path="–")

        write_audit_entries([e1], tmp_path)
        write_audit_entries([e2], tmp_path)

        content = (tmp_path / "audit.log").read_text(encoding="utf-8")
        assert "qsoid=q1" in content
        assert "qsoid=q2" in content

    def test_skipped_qsoids_not_in_audit(self, tmp_path):
        """Übersprungene QSOs dürfen NICHT im Audit erscheinen."""
        from qsl73.audit import AuditEntry, write_audit_entries

        # Simuliert: nur q1 wurde geschrieben; q2 war skipped → Aufrufer filtert
        e1 = AuditEntry(doc_id=1, qsoid="q1", callsign="A", qso_date="2025-01-01",
                        band="20m", mode="FT8", route="bureau", source="auto", backup_path="–")
        write_audit_entries([e1], tmp_path)

        content = (tmp_path / "audit.log").read_text(encoding="utf-8")
        assert "qsoid=q1" in content
        assert "qsoid=q2" not in content

    def test_empty_list_no_file_created(self, tmp_path):
        from qsl73.audit import write_audit_entries

        write_audit_entries([], tmp_path)
        assert not (tmp_path / "audit.log").exists()

    def test_creates_log_dir_if_missing(self, tmp_path):
        from qsl73.audit import AuditEntry, write_audit_entries

        log_dir = tmp_path / "new" / "logs"
        e = AuditEntry(doc_id=1, qsoid="q1", callsign="X", qso_date="2025-01-01",
                       band="20m", mode="CW", route="undefined", source="auto", backup_path="–")
        write_audit_entries([e], log_dir)
        assert (log_dir / "audit.log").exists()

    def test_multiple_entries_each_on_own_line(self, tmp_path):
        from qsl73.audit import AuditEntry, write_audit_entries

        entries = [
            AuditEntry(doc_id=i, qsoid=f"q{i}", callsign=f"C{i}", qso_date="2025-01-01",
                       band="20m", mode="FT8", route="bureau", source="auto", backup_path="–")
            for i in range(3)
        ]
        write_audit_entries(entries, tmp_path)
        lines = [l for l in (tmp_path / "audit.log").read_text(encoding="utf-8").splitlines() if l.strip()]
        assert len(lines) == 3
