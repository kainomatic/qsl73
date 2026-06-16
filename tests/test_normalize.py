import pytest
from qsl73.normalize import normalize_date, normalize_band, normalize_mode


@pytest.mark.parametrize("text,expected", [
    # ISO
    ("2024-06-21", "2024-06-21"),
    ("2025-04-02", "2025-04-02"),
    # TT.MM.JJ
    ("02.04.25", "2025-04-02"),
    ("31.12.99", "1999-12-31"),
    ("01.01.28", "2028-01-01"),
    # TT.MM.JJJJ
    ("23.04.2025", "2025-04-23"),
    ("02.04.1985", "1985-04-02"),
    # TT Monatsname JJJJ
    ("23Apr2025", "2025-04-23"),
    ("23 Apr 2025", "2025-04-23"),
    ("23 April 2025", "2025-04-23"),
    ("2 Jan 1992", "1992-01-02"),
    ("15 Okt 2019", "2019-10-15"),
    # MM/DD/YYYY
    ("06/21/2024", "2024-06-21"),
    ("01/01/2000", "2000-01-01"),
    # Schrägstrich 2-stellig: eindeutig
    ("06/21/24", "2024-06-21"),
    ("21/06/24", "2024-06-21"),
    # Schrägstrich 2-stellig: mehrdeutig
    ("03/04/25", None),
    ("01/02/99", None),
    # Unbekannt/Exotisch
    ("17-XI-93", None),
    ("tToemvem", None),
    ("", None),
    ("99/99/99", None),
    ("02-04-25", None),
])
def test_normalize_date(text, expected):
    assert normalize_date(text) == expected


@pytest.mark.parametrize("text,expected", [
    # Bandname direkt
    ("6m", "6m"),
    ("40m", "40m"),
    ("2m", "2m"),
    ("70cm", "70cm"),
    ("160m", "160m"),
    ("6M", "6m"),
    # Frequenz → Band
    ("50.100", "6m"),
    ("50.100 MHz", "6m"),
    ("144.255 MHz", "2m"),
    ("144.255", "2m"),
    ("7.050", "40m"),
    ("7.050 MHz", "40m"),
    ("14.200", "20m"),
    ("21.300", "15m"),
    ("28.500", "10m"),
    ("1.840", "160m"),
    ("3.700", "80m"),
    ("10.120", "30m"),
    ("18.100", "17m"),
    ("24.900", "12m"),
    ("430.500", "70cm"),
    # Komma-Dezimaltrenner
    ("14,200", "20m"),
    ("7,050", "40m"),
    # Zerstört → None
    ("tToemvem", None),
    ("6n", None),
    ("", None),
    ("???", None),
    ("5.357", None),
    ("500", None),
])
def test_normalize_band(text, expected):
    assert normalize_band(text) == expected


@pytest.mark.parametrize("text,expected", [
    # Direkte bekannte Modi
    ("FT8", "FT8"),
    ("FT4", "FT4"),
    ("SSB", "SSB"),
    ("CW", "CW"),
    ("AM", "AM"),
    ("FM", "FM"),
    ("RTTY", "RTTY"),
    ("JT65", "JT65"),
    ("JT9", "JT9"),
    ("ft8", "FT8"),
    # Mapping-Tabelle
    ("J3E", "SSB"),
    ("A3J", "SSB"),
    ("USB", "SSB"),
    ("LSB", "SSB"),
    ("PH", "SSB"),
    ("2×SSB", "SSB"),
    ("2xSSB", "SSB"),
    ("2XSSB", "SSB"),
    ("A1A", "CW"),
    ("A3E", "AM"),
    ("F3E", "FM"),
    ("F1B", "RTTY"),
    # Fuzzy (Distanz 1)
    ("FT8S", "FT8"),
    ("5SB", "SSB"),
    # Kein Treffer
    ("FOOBAR", None),
    ("XYZ123", None),
    ("", None),
])
def test_normalize_mode(text, expected):
    assert normalize_mode(text) == expected


# ---------------------------------------------------------------------------
# OCR-Fehlerkatalog: empirisch bestätigte Fehler
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("ocr_band,expected", [
    # Ziffern-/Buchstaben-Verwechslungen im Bandfeld (nicht in test_normalize_band)
    ("60m", None),     # Ziffer 6 statt 6m – keine gültige Bandbezeichnung mit Tausenderstelle
    ("6rn", None),     # rn statt m
    ("4Om", None),     # O (Buchstabe) statt 0
    ("2rn", None),     # rn statt m
    ("B0m", None),     # B statt 8 (kein Band "B0m")
    ("l44.255", None), # l (kleines L) statt 1
])
def test_ocr_band_errors(ocr_band, expected):
    assert normalize_band(ocr_band) == expected


@pytest.mark.parametrize("ocr_date,expected", [
    # Ziffern-/Buchstaben-Verwechslungen im Datum
    ("02.O4.25", None),       # O statt 0
    ("O2.04.25", None),       # O statt 0
    ("02.04.2S", None),       # S statt 5
    # Korrekte zweistellige Jahre (Heuristik >= 30 → 19xx)
    ("15.03.30", "1930-03-15"),
    ("15.03.29", "2029-03-15"),
    # Leerzeichen als Trenner → unbekannt
    ("02 04 25", None),
])
def test_ocr_date_errors(ocr_date, expected):
    assert normalize_date(ocr_date) == expected


@pytest.mark.parametrize("ocr_mode,expected", [
    # Leerzeichen als OCR-Artefakt → kein bekannter Mode
    ("C W", None),
    # Mehrdeutige Fuzzy-Treffer (Distanz 1 zu mehreren Modi) → None
    ("FT6", None),   # Distanz 1 zu FT8 UND zu FT4
    ("FT3", None),   # Distanz 1 zu FT4 UND zu FT8
])
def test_ocr_mode_errors(ocr_mode, expected):
    assert normalize_mode(ocr_mode) == expected
