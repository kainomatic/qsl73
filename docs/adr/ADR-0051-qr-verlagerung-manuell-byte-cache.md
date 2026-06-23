# ADR-0051 — QR-Auswertung in manuellen Dialog verlagert + RAM-Byte-Cache mit Prefetch

**Status:** Accepted  
**Datum:** 2026-06-23  
**Kontext:** Issue #30 — Performance bei ~2000 Karten

---

## Kontext

Im Massen-Lauf (`run_pass`) wurde für jede Karte `get_document_download` aufgerufen
(vollständiger PDF-Download) um per `decode_qr_from_pdf` einen QR-Code zu suchen.
Bei ~2000 Karten führt das zu 2000 HTTP-Requests à mehrere Sekunden = inakzeptabler
Gesamt-Lauf. Der OCR-Text liegt dagegen kostenlos im Listen-Response (`doc["content"]`).

---

## Entscheidung

### 1. QR aus dem Massen-Lauf entfernen

`evaluate_card` (und damit `run_pass`) wertet **ausschließlich den OCR-Text** aus.
`source` ∈ {"ocr", "none"} — "qr" tritt im Lauf nicht mehr auf.

**Bewusst akzeptierter Trade-off:** Karten mit gutem QR aber schlechtem OCR landen
auf "unsicher" oder "kein Treffer" und werden im manuellen Dialog erledigt — dort
ist der QR verfügbar und die Felder sind vorausgefüllt.

`decode_qr_from_pdf` und `parse_qr_text` in `qr.py` bleiben erhalten.

### 2. QR im manuellen Dialog

Der Dialog lädt das PDF ohnehin für das Kartenbild (`_load_image` → `image_loader`
→ Bytes). Aus **denselben Bytes** wird zusätzlich `decode_qr_from_pdf` aufgerufen.
PDF wird nur **einmal** pro Karte übertragen.

QR-Felder dienen **ausschließlich zur Vorbefüllung** der Suchfelder (call, band, mode,
date). Keine automatische Vorauswahl eines DB-Kandidaten, keine Auto-Bestätigung.
Der manuelle Schritt bleibt menschengeführt (KONZEPT §9, ADR-0028).

Überschreiben-Regel (`compute_qr_prefill`): Ein Feld wird nur dann mit dem QR-Wert
überschrieben, wenn es leer ist oder noch den OCR-Vorbefüllungswert hat. Werte, die
der Nutzer manuell getippt hat, werden nie überschrieben.

### 3. RAM-Byte-Cache (LRU) mit Prefetch

**Was gecacht wird:** rohe PDF-Bytes (`doc_id → bytes`). Nicht gerenderte Bilder.  
**Verdrängung:** LRU bis zur MB-Grenze (nicht Stückzahl — PDF-Größen variieren stark).  
**Konstanten:**
- `CACHE_MAX_MB = 150` — typische Karten (200–500 KB) → hunderte Karten; Schutz vor GB-Wachstum
- `PREFETCH_DEPTH = 4` — 4 kommende Karten im Hintergrund vorausladen; Wartegefühl ≈ 0

**Keine Temp-Dateien** (ADR-0050). Alles im RAM.  
**Lebensdauer:** `PdfByteCache` ist an `MainWindow` gebunden (erstellt in `__init__`,
gestoppt in `_on_close`). Stop setzt ein `threading.Event` — laufende Threads beenden
sich nach Erkennung des Events. Daemon-Threads blockieren das Beenden nicht.

---

## Verhältnis zu ADR-0007

ADR-0007 definiert den Qualitätsrang: QR > OCR > manuell. Dieser Rang bleibt gültig.

Geändert wird der **Ort** der QR-Auswertung:  
- Früher: QR im Massen-Lauf → mögliche Auto-Bestätigung via CERTAIN  
- Jetzt: QR im manuellen Dialog → Vorbefüllung der Suchfelder, kein Auto-Select

Der Qualitätsrang wirkt sich aus als **Vorbefüllungs-Priorität** im Dialog:
QR-Felder überschreiben OCR-Felder (wenn Nutzer noch nichts getippt hat).

ADR-0007 ist durch diesen Punkt berührt — der Verweis auf ADR-0051 wird dort ergänzt.

---

## Konsequenzen

**Positiv:**
- Massen-Lauf: kein einziger PDF-Download mehr → drastisch schneller
- Manueller Dialog: QR-Felder verfügbar ohne Extra-Request
- Cache + Prefetch: Klicken durch Karten ohne Wartezeit

**Negativ / bewusst akzeptiert:**
- Karten mit QR aber schlechtem OCR landen im Lauf auf "unsicher/kein Treffer"
  statt auf CERTAIN → mehr Arbeit im manuellen Schritt
- QR-Vorbefüllung wirkt erst nach Bildladen (50 ms After-Delay) — kurze sichtbare Verzögerung
