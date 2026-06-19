"""Tests für tools/make_docs_html._strip_unreleased_section."""
import sys
from pathlib import Path

# tools/ ist kein reguläres Package — Pfad für direkten Import ergänzen.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
from make_docs_html import _strip_unreleased_section  # noqa: E402


_FULL_CHANGELOG = """\
# Changelog

Einleitung.

## [Unreleased]

### Changed

- Feature-Idee

### Fixed

- Bugfix

## [0.2.0] - 2026-06-19

### Added

- Erste Funktion

## [0.1.0] - 2026-01-01

### Added

- Initial
"""

_EMPTY_UNRELEASED = """\
# Changelog

## [Unreleased]

## [0.2.0] - 2026-06-19

### Added

- Erste Funktion
"""

_ONLY_UNRELEASED = """\
# Changelog

## [Unreleased]

### Added

- Noch nicht veröffentlicht
"""


class TestStripUnreleasedSection:
    def test_removes_filled_unreleased_block(self):
        result = _strip_unreleased_section(_FULL_CHANGELOG)
        assert "## [Unreleased]" not in result
        assert "Feature-Idee" not in result
        assert "Bugfix" not in result

    def test_preserves_released_sections(self):
        result = _strip_unreleased_section(_FULL_CHANGELOG)
        assert "## [0.2.0]" in result
        assert "Erste Funktion" in result
        assert "## [0.1.0]" in result
        assert "Initial" in result

    def test_preserves_changelog_preamble(self):
        result = _strip_unreleased_section(_FULL_CHANGELOG)
        assert "# Changelog" in result
        assert "Einleitung." in result

    def test_removes_empty_unreleased_block(self):
        result = _strip_unreleased_section(_EMPTY_UNRELEASED)
        assert "## [Unreleased]" not in result
        assert "## [0.2.0]" in result

    def test_only_unreleased_leaves_preamble(self):
        """Wenn nur [Unreleased] existiert, bleibt nur der Kopfbereich."""
        result = _strip_unreleased_section(_ONLY_UNRELEASED)
        assert "## [Unreleased]" not in result
        assert "Noch nicht veröffentlicht" not in result
        assert "# Changelog" in result

    def test_no_unreleased_section_unchanged(self):
        """Ohne [Unreleased]-Abschnitt ändert sich nichts."""
        no_unrel = "# Changelog\n\n## [1.0.0] - 2026-01-01\n\n### Added\n\n- X\n"
        assert _strip_unreleased_section(no_unrel) == no_unrel

    def test_crlf_line_endings(self):
        """Windows-Zeilenenden (CRLF) werden korrekt behandelt."""
        crlf = _EMPTY_UNRELEASED.replace("\n", "\r\n")
        result = _strip_unreleased_section(crlf)
        assert "## [Unreleased]" not in result
        assert "## [0.2.0]" in result
