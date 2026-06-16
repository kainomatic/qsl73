"""Tests für qsl73.qr: QR-Text-Parser und PDF-Decode-Pfad.

Parser-Tests (Klasse TestParseQrText) laufen immer — keine externen Abhängigkeiten.
PDF-Decode-Tests (Klasse TestDecodeQrFromPdf) werden übersprungen, wenn
zxingcpp / pymupdf / qrcode nicht installiert sind.
"""
import io

import pytest

from qsl73.qr import decode_qr_from_pdf, parse_qr_text

# --- Soft-dependency check für Decode-Tests ---
_DECODE_DEPS = False
try:
    import fitz  # noqa: F401  (pymupdf)
    import qrcode  # noqa: F401
    import zxingcpp  # noqa: F401
    from PIL import Image  # noqa: F401

    _DECODE_DEPS = True
except ImportError:
    pass

# Bekanntes DK8NE-Format (empirisch an echter Karte verifiziert, docs/discovery.md §5.2)
DK8NE_QR_TEXT = (
    "From: DK8NE  To: DH3KR\n"
    "Date: 02.04.25  Time: 19:42  Band: 6m  Band_RX: 6m  Mode: FT8  "
    "Prop_Mode: TR  RST: -24  QSL: TNX"
)


class TestParseQrText:
    def test_dk8ne_known_format(self):
        card = parse_qr_text(DK8NE_QR_TEXT)
        assert card is not None
        assert card.call_from == "DK8NE"
        assert card.call_to == "DH3KR"
        assert card.date == "2025-04-02"
        assert card.band == "6m"
        assert card.mode == "FT8"
        assert card.time_utc == "19:42"

    def test_advertising_qr_no_qso_keys(self):
        assert parse_qr_text("https://www.zazzle.com/s/abc123") is None

    def test_partial_qr_missing_from(self):
        assert parse_qr_text("To: DH3KR Date: 02.04.25 Band: 6m Mode: FT8") is None

    def test_partial_qr_missing_band(self):
        assert parse_qr_text("From: DK8NE To: DH3KR Date: 02.04.25 Mode: FT8") is None

    def test_partial_qr_missing_mode(self):
        assert parse_qr_text("From: DK8NE To: DH3KR Date: 02.04.25 Band: 6m") is None

    def test_field_order_reversed(self):
        """Feldreihenfolge umgekehrt → trotzdem korrekt geparst."""
        text = "Mode: FT8 Band: 6m Date: 02.04.25 To: DH3KR From: DK8NE"
        card = parse_qr_text(text)
        assert card is not None
        assert card.call_from == "DK8NE"
        assert card.call_to == "DH3KR"
        assert card.band == "6m"
        assert card.mode == "FT8"

    def test_extra_whitespace_between_fields(self):
        text = "From:   DK8NE   To:   DH3KR   Date:  02.04.25  Band:  6m  Mode:  FT8"
        card = parse_qr_text(text)
        assert card is not None
        assert card.call_from == "DK8NE"
        assert card.band == "6m"

    def test_newlines_between_fields(self):
        text = "From: DK8NE\nTo: DH3KR\nDate: 02.04.25\nBand: 6m\nMode: FT8"
        card = parse_qr_text(text)
        assert card is not None
        assert card.call_from == "DK8NE"

    def test_unknown_extra_fields_ignored(self):
        text = (
            "From: DK8NE To: DH3KR Date: 02.04.25 Band: 6m Mode: FT8 "
            "RST: -24 QSL: TNX Foo: Bar Unknown: ignored"
        )
        card = parse_qr_text(text)
        assert card is not None
        assert card.call_from == "DK8NE"
        assert card.date == "2025-04-02"

    def test_band_rx_does_not_shadow_band(self):
        """Band_RX vor Band → band-Feld liefert trotzdem den Wert von Band:."""
        text = "From: DK8NE To: DH3KR Date: 02.04.25 Band_RX: 6m Band: 40m Mode: CW"
        card = parse_qr_text(text)
        assert card is not None
        assert card.band == "40m"

    def test_empty_string_returns_none(self):
        assert parse_qr_text("") is None

    def test_whitespace_only_returns_none(self):
        assert parse_qr_text("   \n\t  ") is None

    def test_no_time_field_gives_none_time_utc(self):
        text = "From: DK8NE To: DH3KR Date: 02.04.25 Band: 6m Mode: FT8"
        card = parse_qr_text(text)
        assert card is not None
        assert card.time_utc is None

    def test_time_field_extracted(self):
        text = "From: DK8NE To: DH3KR Date: 02.04.25 Time: 19:42 Band: 6m Mode: FT8"
        card = parse_qr_text(text)
        assert card is not None
        assert card.time_utc == "19:42"

    def test_unknown_band_returns_none_band(self):
        """Unbekanntes Band → band=None (neutral, kein Match-Ausschluss)."""
        text = "From: DK8NE To: DH3KR Date: 02.04.25 Band: tToemvem Mode: FT8"
        card = parse_qr_text(text)
        assert card is not None
        assert card.band is None

    def test_unknown_mode_returns_none_mode(self):
        text = "From: DK8NE To: DH3KR Date: 02.04.25 Band: 6m Mode: GARBAGE"
        card = parse_qr_text(text)
        assert card is not None
        assert card.mode is None

    def test_date_normalization(self):
        """Datum TT.MM.JJ → ISO YYYY-MM-DD."""
        text = "From: DK8NE To: DH3KR Date: 02.04.25 Band: 6m Mode: FT8"
        card = parse_qr_text(text)
        assert card is not None
        assert card.date == "2025-04-02"

    def test_sixty_meter_band(self):
        """60m-Band wird korrekt normalisiert."""
        text = "From: DG5MLA To: DH3KR Date: 26.04.25 Band: 60m Mode: FT8"
        card = parse_qr_text(text)
        assert card is not None
        assert card.band == "60m"


@pytest.mark.skipif(not _DECODE_DEPS, reason="zxingcpp/pymupdf/qrcode nicht installiert")
class TestDecodeQrFromPdf:
    """Decode-Tests mit selbst erzeugten QR-Bildern (keine echte Karte nötig)."""

    def _make_pdf_with_qr(self, text: str) -> bytes:
        """Erzeugt ein Minimal-PDF mit einem QR-Code-Bild."""
        qr_img = qrcode.make(text)
        qr_buf = io.BytesIO()
        qr_img.save(qr_buf, format="PNG")

        pdf = fitz.open()
        page = pdf.new_page(width=400, height=400)
        page.insert_image(fitz.Rect(50, 50, 350, 350), stream=qr_buf.getvalue())
        pdf_bytes = pdf.tobytes()
        pdf.close()
        return pdf_bytes

    def test_valid_qso_qr_in_pdf(self):
        pdf_bytes = self._make_pdf_with_qr(DK8NE_QR_TEXT)
        card = decode_qr_from_pdf(pdf_bytes)
        assert card is not None
        assert card.call_from == "DK8NE"
        assert card.call_to == "DH3KR"
        assert card.date == "2025-04-02"
        assert card.band == "6m"
        assert card.mode == "FT8"

    def test_advertising_qr_returns_none(self):
        """Werbe-QR ohne QSO-Felder → None."""
        pdf_bytes = self._make_pdf_with_qr("https://www.zazzle.com/s/abc123")
        assert decode_qr_from_pdf(pdf_bytes) is None

    def test_corrupt_bytes_returns_none(self):
        assert decode_qr_from_pdf(b"\x00\x01\x02corrupt_data") is None

    def test_empty_bytes_returns_none(self):
        assert decode_qr_from_pdf(b"") is None

    def test_pdf_without_qr_returns_none(self):
        """Leeres PDF ohne QR-Code → None."""
        pdf = fitz.open()
        pdf.new_page(width=200, height=200)
        pdf_bytes = pdf.tobytes()
        pdf.close()
        assert decode_qr_from_pdf(pdf_bytes) is None

    def test_advertising_qr_and_qso_qr_on_separate_pages(self):
        """Werbung auf Seite 1, QSO-QR auf Seite 2 → QSO-Karte wird gefunden."""
        adv_pdf = self._make_pdf_with_qr("https://www.zazzle.com/s/abc123")
        qso_pdf = self._make_pdf_with_qr(DK8NE_QR_TEXT)

        doc_adv = fitz.open(stream=adv_pdf, filetype="pdf")
        doc_qso = fitz.open(stream=qso_pdf, filetype="pdf")
        combined = fitz.open()
        combined.insert_pdf(doc_adv)
        combined.insert_pdf(doc_qso)
        combined_bytes = combined.tobytes()
        doc_adv.close()
        doc_qso.close()
        combined.close()

        card = decode_qr_from_pdf(combined_bytes)
        assert card is not None
        assert card.call_from == "DK8NE"

    def test_two_qr_codes_one_valid_one_advertising(self):
        """Zwei QR-Codes auf einer Seite: Werbung + QSO → QSO-Karte gewinnt."""
        adv_qr = qrcode.make("https://www.zazzle.com/s/abc123")
        qso_qr = qrcode.make(DK8NE_QR_TEXT)

        adv_buf = io.BytesIO()
        adv_qr.save(adv_buf, format="PNG")
        qso_buf = io.BytesIO()
        qso_qr.save(qso_buf, format="PNG")

        pdf = fitz.open()
        page = pdf.new_page(width=700, height=350)
        page.insert_image(fitz.Rect(10, 10, 340, 340), stream=adv_buf.getvalue())
        page.insert_image(fitz.Rect(360, 10, 690, 340), stream=qso_buf.getvalue())
        pdf_bytes = pdf.tobytes()
        pdf.close()

        card = decode_qr_from_pdf(pdf_bytes)
        assert card is not None
        assert card.call_from == "DK8NE"
