"""Tests für die CHANGELOG-Notes-Extraktion (spiegelt release.yml Schritt 11).

Python-Regex mit re.DOTALL + r'\\Z' entspricht PowerShell .NET Singleline + r'\\z'.
Sichert gegen Regressionen im Lookahead-Muster ab (Bugfix: ohne |\\Z schlug
der Stable-Match fehl, wenn [APP_VERSION] der letzte Abschnitt in der Datei war).
"""
import re

import pytest

OPTS = re.DOTALL

# ---------------------------------------------------------------------------
# Hilfsfunktion: spiegelt die release.yml-Logik 1:1
# ---------------------------------------------------------------------------

def _extract(changelog: str, app_version: str | None, *, is_beta: bool) -> str:
    """Extrahiert Release-Notes wie release.yml Schritt 11."""
    if is_beta:
        pattern = r"## \[Unreleased\][^\r\n]*\r?\n(.*?)(?=\r?\n## \[|\Z)"
        source = "[Unreleased]"
    else:
        escaped = re.escape(app_version or "")
        pattern = rf"## \[{escaped}\][^\r\n]*\r?\n(.*?)(?=\r?\n## \[|\Z)"
        source = f"[{app_version}]"

    m = re.search(pattern, changelog, OPTS)
    if m:
        return m.group(1).strip()

    # Fallback 1: [Unreleased]
    fb_pattern = r"## \[Unreleased\][^\r\n]*\r?\n(.*?)(?=\r?\n## \[|\Z)"
    fb = re.search(fb_pattern, changelog, OPTS)
    if fb and fb.group(1).strip():
        return fb.group(1).strip()

    # Fallback 2: Platzhalter
    return "Siehe CHANGELOG.md für Details zu dieser Version."


# ---------------------------------------------------------------------------
# Fixture: minimaler CHANGELOG mit zwei Abschnitten
# ---------------------------------------------------------------------------

_TWO_SECTIONS = """\
## [Unreleased]

## [0.2.0] - 2026-06-19

### Added

- Feature A
- Feature B
"""

_TWO_SECTIONS_FILLED_UNREL = """\
## [Unreleased]

### Added

- Beta-Feature X

## [0.2.0] - 2026-06-19

### Added

- Feature A
"""

# Letzter Abschnitt ohne nachfolgendes ## [ — der Regressions-Fall
_SINGLE_SECTION = """\
## [Unreleased]

## [0.2.0] - 2026-06-19

### Fixed

- Bug fix Y
"""


class TestStableExtraction:
    def test_last_section_in_file(self):
        """Kernfall des Bugs: [0.2.0] ist letzter Abschnitt — kein nachfolgendes ## [."""
        notes = _extract(_SINGLE_SECTION, "0.2.0", is_beta=False)
        assert "Bug fix Y" in notes

    def test_not_last_section(self):
        """[0.2.0] hat einen Nachfolger — sollte auch vor dem Fix funktioniert haben."""
        changelog = """\
## [Unreleased]

## [0.2.0] - 2026-06-19

### Added

- Feature A

## [0.1.0] - 2026-01-01

### Added

- Initial
"""
        notes = _extract(changelog, "0.2.0", is_beta=False)
        assert "Feature A" in notes
        assert "Initial" not in notes

    def test_correct_version_section_selected(self):
        """Nur der angeforderte Abschnitt wird extrahiert."""
        changelog = """\
## [Unreleased]

## [0.2.0] - 2026-06-19

### Fixed

- Fix A

## [0.1.0] - 2026-01-01

### Added

- Initial
"""
        notes = _extract(changelog, "0.1.0", is_beta=False)
        assert "Initial" in notes
        assert "Fix A" not in notes

    def test_empty_unreleased_not_captured(self):
        """Ein leerer [Unreleased]-Block darf NICHT als Notes für Stable ausgegeben werden."""
        notes = _extract(_TWO_SECTIONS, "0.2.0", is_beta=False)
        assert "Feature A" in notes
        assert "Feature B" in notes


class TestBetaExtraction:
    def test_unreleased_with_content(self):
        notes = _extract(_TWO_SECTIONS_FILLED_UNREL, None, is_beta=True)
        assert "Beta-Feature X" in notes
        assert "Feature A" not in notes  # Nicht aus [0.2.0]

    def test_unreleased_is_last_section(self):
        """[Unreleased] ohne nachfolgendes ## [ — auch hier muss |\\Z greifen."""
        changelog = "## [Unreleased]\n\n### Added\n\n- Only Entry\n"
        notes = _extract(changelog, None, is_beta=True)
        assert "Only Entry" in notes

    def test_empty_unreleased_returns_empty_string(self):
        """Leerer [Unreleased]-Block → leerer String (Match erfolgreich, kein Inhalt).
        Fallback greift nur wenn das Muster gar nicht matcht, nicht wenn es leer matcht."""
        changelog = "## [Unreleased]\n\n## [0.2.0] - 2026-01-01\n\n### Added\n\n- Old\n"
        notes = _extract(changelog, None, is_beta=True)
        assert notes == ""


class TestFallbackBehavior:
    def test_missing_version_section_falls_back_to_unreleased(self):
        """Wenn [APP_VERSION] fehlt und [Unreleased] Inhalt hat → Fallback."""
        changelog = "## [Unreleased]\n\n### Fixed\n\n- Hot fix\n"
        notes = _extract(changelog, "9.9.9", is_beta=False)
        assert "Hot fix" in notes

    def test_both_missing_returns_placeholder(self):
        """Weder [APP_VERSION] noch nicht-leeres [Unreleased] → Platzhaltertext."""
        changelog = "# Changelog\n\nKein Abschnitt hier.\n"
        notes = _extract(changelog, "9.9.9", is_beta=False)
        assert "Siehe CHANGELOG.md" in notes
