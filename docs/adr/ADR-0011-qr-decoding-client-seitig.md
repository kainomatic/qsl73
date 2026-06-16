# ADR-0011: QR-Code-Decoding erfolgt client-seitig aus dem Kartenbild, nicht aus Paperless-OCR

**Status:** Accepted

## Kontext

Schritt-3b-Verifikation (2026-06-16) hat empirisch bestätigt: Der Paperless-OCR-Text
(`GET /api/documents/{id}/?fields=content`) enthält den QR-Code-Inhalt **nicht**.
Tesseract dekodiert QR-Codes nicht — der QR-Inhalt ist nur als Bildsymbol im Dokument
vorhanden. Befund dokumentiert in `docs/discovery.md` §5.2.

Gleichzeitig sind QR-Codes auf modernen Karten (z. B. DARC-QSL-Service) die verlässlichste
Datenquelle: strukturierter Klartext mit From/To/Date/Time/Band/Mode, ohne OCR-Artefakte
wie `"6m"` → `"tToemvem"`. Der QR-Pfad (Priorität 1 in §6.1) war schon vor dieser
Erkenntnis als beste Datenquelle vorgesehen; jetzt ist der konkrete Mechanismus klar.

## Entscheidung

QSL73 dekodiert QR-Codes **client-seitig aus dem heruntergeladenen Kartenbild/PDF**:

1. Dokument-Bytes via `GET /api/documents/{id}/download/` laden.
2. PDF-Seiten mit `pymupdf` in Rasterbilder rendern.
3. Im gerenderten Bild QR-Code suchen und dekodieren via `pyzbar` (nutzt native zbar-Bibliothek).
4. Dekodierten Klartext parsen (Key-Value-Format: `From: ... Date: ... Band: ...`).
5. Schlägt Decoding fehl oder kein QR vorhanden → Fallback auf OCR-Pfad (§6.3).

Abhängigkeiten: `pyzbar` + `pymupdf` (Python); `libzbar-64.dll` (native, Windows).

## Konsequenzen

**Positiv:**
- QR-Pfad liefert saubere, OCR-unabhängige Felder (Band, Mode, Datum ohne Artefakte).
- Eindeutige, direkt parsbare Datenstruktur.

**Negativ / Risiken:**
- Zusätzliche Abhängigkeiten: `pyzbar`, `pymupdf`, und die native `libzbar-64.dll`.
- `libzbar-64.dll` muss beim PyInstaller-Build explizit mitgebündelt werden
  (→ Issue #7). Packaging-Mehraufwand, analog zu `pywin32` (Issue #6).
- Nicht jede Karte hat einen QR-Code; der Fallback auf OCR/manuell bleibt nötig.
- Zusätzlicher Bild-Download pro Karte (PDF, 400–860 KB laut Schritt-3b-Messung)
  beim QR-Versuch; akzeptabel für Batch-Lauf auf lokalem Netz zu Paperless.
