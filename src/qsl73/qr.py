# QSL73 — Copyright (C) 2026 DF1DS (kainomatic) — SPDX-License-Identifier: GPL-3.0-or-later
"""QR-Code-Dekodierung aus PDF-Bytes für QSL-Karten.

Rendert alle PDF-Seiten als Bilder (pymupdf) und sucht nach QR-Codes
(zxingcpp). Validiert den Inhalt auf QSO-Format, ignoriert Werbe-QR.
Gibt das erste gültige CardFields-Objekt zurück. ADR-0011, ADR-0012, ADR-0017.

Soft-Dependencies: pymupdf, zxingcpp, Pillow. Falls nicht installiert → None.
"""
from __future__ import annotations

import io
import re
from typing import Optional

try:
    import fitz  # pymupdf

    _FITZ_OK = True
except ImportError:  # pragma: no cover
    _FITZ_OK = False

try:
    import zxingcpp
    from PIL import Image

    _ZXING_OK = True
except ImportError:  # pragma: no cover
    _ZXING_OK = False

from qsl73.matching import CardFields
from qsl73.normalize import normalize_band, normalize_date, normalize_mode


def qr_backend_status() -> dict:
    """Gibt Verfügbarkeit der QR-Code-Bibliotheken zurück (pymupdf + zxing-cpp)."""
    return {"fitz": _FITZ_OK, "zxing": _ZXING_OK}

RENDER_DPI = 300

_REQUIRED_KEYS = frozenset({"from", "to", "date", "band", "mode"})


def _parse_qr_fields(text: str) -> dict[str, str]:
    """Parse 'Key: Value' pairs from QR text.

    Handles the DARC QSL-service format:
        From: DK8XX  To: DL0AAA
        Date: 02.04.25  Time: 19:42  Band: 6m  Band_RX: 6m  Mode: FT8  ...

    Keys with underscores (Band_RX, Prop_Mode) are supported.
    Field order and extra whitespace/newlines are ignored.
    """
    parts = re.split(r"\s+(?=[A-Za-z]\w*\s*:)", text.strip())
    result: dict[str, str] = {}
    for part in parts:
        sep = part.find(":")
        if sep > 0:
            key = part[:sep].strip().lower()
            val = part[sep + 1 :].strip()
            if key and val:
                result[key] = val
    return result


def _time_from_raw(raw: str) -> Optional[str]:
    """Extract HH:MM from '19:42' or '19:42:00'."""
    m = re.match(r"(\d{1,2}:\d{2})", raw.strip())
    return m.group(1) if m else None


def parse_qr_text(text: str) -> Optional[CardFields]:
    """Parse QR text into CardFields. Returns None if not a valid QSO QR code.

    Required keys: From, To, Date, Band, Mode (case-insensitive).
    Unknown extra keys (RST, QSL, Prop_Mode, …) are silently ignored.
    """
    if not text or not text.strip():
        return None
    fields = _parse_qr_fields(text)
    if not _REQUIRED_KEYS.issubset(fields):
        return None

    raw_time = fields.get("time", "")
    return CardFields(
        call_from=fields.get("from") or None,
        call_to=fields.get("to") or None,
        date=normalize_date(fields.get("date", "")),
        band=normalize_band(fields.get("band", "")),
        mode=normalize_mode(fields.get("mode", "")),
        time_utc=_time_from_raw(raw_time) if raw_time else None,
    )


def decode_qr_from_pdf(pdf_bytes: bytes) -> Optional[CardFields]:
    """Render all pages of a PDF, return CardFields from the first valid QSO QR.

    Searches every page. Returns None if:
    - soft-dependencies absent (pymupdf / zxingcpp)
    - input is empty or corrupt
    - no QR found, or no QR carries a valid QSO payload
    """
    if not _FITZ_OK or not _ZXING_OK:
        return None  # pragma: no cover
    if not pdf_bytes:
        return None

    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    except Exception:
        return None

    mat = fitz.Matrix(RENDER_DPI / 72, RENDER_DPI / 72)
    try:
        for page in doc:
            try:
                pix = page.get_pixmap(matrix=mat)
                pil_img = Image.open(io.BytesIO(pix.tobytes("png")))
                for result in zxingcpp.read_barcodes(pil_img):
                    card = parse_qr_text(result.text)
                    if card is not None:
                        return card
            except Exception:
                continue
    finally:
        doc.close()

    return None
