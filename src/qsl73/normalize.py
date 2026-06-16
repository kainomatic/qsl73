"""Normalisierung von QSL-Karten-Feldern: Datum, Band, Mode.

Alle Funktionen geben str | None zurück.
None bedeutet: Wert nicht bestimmbar (mehrdeutig, unbekanntes Format, zerstörter Input).
Kein Absturz, kein Raten. ADR-0014.
"""
from __future__ import annotations

import re
from datetime import date as _date
from typing import Optional


def _expand_year(yy: int) -> int:
    """Zweistellige Jahreszahl → vierstellig. >= 30 → 19xx, < 30 → 20xx."""
    return 1900 + yy if yy >= 30 else 2000 + yy


def _make_iso(y: int, m: int, d: int) -> Optional[str]:
    """Prüft Gültigkeit und gibt YYYY-MM-DD zurück oder None bei ungültigem Datum."""
    try:
        _date(y, m, d)
        return f"{y:04d}-{m:02d}-{d:02d}"
    except (ValueError, OverflowError):
        return None


_MONTH_NAMES: dict[str, int] = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
    "january": 1, "february": 2, "march": 3, "june": 6, "july": 7,
    "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
    "mär": 3, "mai": 5, "okt": 10,
    "januar": 1, "februar": 2, "märz": 3, "april": 4,
    "juni": 6, "juli": 7,
    "oktober": 10, "november": 11, "dezember": 12,
}


def normalize_date(text: str) -> Optional[str]:
    """Normalisiert Datumsstring auf YYYY-MM-DD. Gibt None bei Mehrdeutigkeit/Unbekannt."""
    if not text or not text.strip():
        return None
    text = text.strip()

    # YYYY-MM-DD
    m = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", text)
    if m:
        return _make_iso(int(m.group(1)), int(m.group(2)), int(m.group(3)))

    # TT.MM.JJ oder TT.MM.JJJJ
    m = re.fullmatch(r"(\d{1,2})\.(\d{1,2})\.(\d{2,4})", text)
    if m:
        d_val, mo_val, y_str = int(m.group(1)), int(m.group(2)), m.group(3)
        y_val = _expand_year(int(y_str)) if len(y_str) == 2 else int(y_str)
        return _make_iso(y_val, mo_val, d_val)

    # TT Monatsname JJJJ
    m = re.fullmatch(r"(\d{1,2})\s*([A-Za-zäöüÄÖÜ]+)\s*(\d{4})", text)
    if m:
        d_val = int(m.group(1))
        month_str = m.group(2).lower()
        y_val = int(m.group(3))
        mo_val = _MONTH_NAMES.get(month_str)
        if mo_val is not None:
            return _make_iso(y_val, mo_val, d_val)
        return None

    # MM/DD/YYYY (US-Langform, 4-stelliges Jahr)
    m = re.fullmatch(r"(\d{1,2})/(\d{1,2})/(\d{4})", text)
    if m:
        mo_val, d_val, y_val = int(m.group(1)), int(m.group(2)), int(m.group(3))
        return _make_iso(y_val, mo_val, d_val)

    # Schrägstrich + 2-stelliges Jahr
    m = re.fullmatch(r"(\d{1,2})/(\d{1,2})/(\d{2})", text)
    if m:
        a, b, yy = int(m.group(1)), int(m.group(2)), int(m.group(3))
        y_val = _expand_year(yy)
        if a > 12:
            return _make_iso(y_val, b, a)
        if b > 12:
            return _make_iso(y_val, a, b)
        return None  # mehrdeutig

    return None


_FREQ_TO_BAND: list[tuple[float, float, str]] = [
    (1.8,    2.0,    "160m"),
    (3.5,    4.0,    "80m"),
    (7.0,    7.3,    "40m"),
    (10.1,   10.15,  "30m"),
    (14.0,   14.35,  "20m"),
    (18.068, 18.168, "17m"),
    (21.0,   21.45,  "15m"),
    (24.89,  24.99,  "12m"),
    (28.0,   29.7,   "10m"),
    (50.0,   54.0,   "6m"),
    (144.0,  148.0,  "2m"),
    (430.0,  440.0,  "70cm"),
]

_BAND_NAMES: frozenset[str] = frozenset({
    "160m", "80m", "40m", "30m", "20m", "17m",
    "15m", "12m", "10m", "6m", "2m", "70cm",
})


def normalize_band(text: str) -> Optional[str]:
    """Normalisiert Bandname oder Frequenz auf kanonischen Bandnamen. None bei Unbekannt."""
    if not text or not text.strip():
        return None
    text = text.strip()

    # Direkte Bandnamen (case-insensitiv)
    text_lower = text.lower()
    for band in _BAND_NAMES:
        if text_lower == band.lower():
            return band

    # Frequenz: MHz-Suffix entfernen, Komma als Dezimaltrenner
    freq_str = re.sub(r"(?i)\s*mhz\s*$", "", text).strip()
    freq_str = freq_str.replace(",", ".")
    try:
        freq = float(freq_str)
    except ValueError:
        return None

    # kHz → MHz-Umrechnung (> 1000 MHz wäre unrealistisch)
    if freq > 1000:
        freq /= 1000

    for lo, hi, band in _FREQ_TO_BAND:
        if lo <= freq <= hi:
            return band

    return None


_MODE_MAP: dict[str, str] = {
    "J3E": "SSB", "A3J": "SSB", "USB": "SSB", "LSB": "SSB", "PH": "SSB",
    "2×SSB": "SSB", "2xSSB": "SSB", "2XSSB": "SSB",
    "BLU": "SSB",  # Französisch: Bande Latérale Unique (Oberes Seitenband = USB = SSB)
    "A1A": "CW",
    "A3E": "AM",
    "F3E": "FM",
    "F1B": "RTTY",
}

_KNOWN_MODES: frozenset[str] = frozenset({
    "SSB", "CW", "AM", "FM", "RTTY",
    "FT8", "FT4", "JT65", "JT9",
    "PSK31", "PSK63", "SSTV", "OLIVIA",
    "JS8", "WSPR", "MSK144", "DIGI", "DATA",
})


def normalize_mode(text: str) -> Optional[str]:
    """Normalisiert Mode-Bezeichnung. Mapping-Tabelle + Fuzzy-Fallback. None bei Unbekannt."""
    if not text or not text.strip():
        return None
    stripped = text.strip()
    # Interne Leerzeichen: kein bekannter Mode (OCR-Artefakt wie "C W" → None)
    if " " in stripped:
        return None
    upper = stripped.upper()

    # Direkte Treffer in bekannten Modi
    if upper in _KNOWN_MODES:
        return upper

    # Mapping-Tabelle (historische/alternative Bezeichnungen)
    mapped = _MODE_MAP.get(upper)
    if mapped:
        return mapped

    # Fuzzy-Fallback: Levenshtein-Distanz 1
    from rapidfuzz.distance import Levenshtein
    matches = [mode for mode in _KNOWN_MODES if Levenshtein.distance(upper, mode) == 1]
    if len(matches) == 1:
        return matches[0]

    return None
