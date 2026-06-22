# ADR-0025: Token-basierte OCR-Extraktion für gedruckte QSL-Karten

**Status:** Accepted

## Kontext

Der Realtest 2026-06-17 zeigte: `_parse_ocr_text` wertet OCR-Text nur aus, wenn er im
„Key: Value"-Format beschriftet ist (z. B. DARC-QSL-Service). Gedruckte ausländische
Karten (OE6XXX, DG5XXX) benutzen aber ein **Tabellenlayout** (Spaltenkopf + Wertzeile)
oder Fließtext — die alte Regex-Schicht lieferte dort leere Felder, obwohl alle vier
Pflichtfelder (Rufzeichen, Datum, Band, Mode) im Text standen.

Sieben reale OCR-Texte aus dem Realtest wurden analysiert:

| Karte    | OCR-Qualität       | Besonderheit                                  |
|----------|--------------------|-----------------------------------------------|
| OE6XXX   | Tabellenlayout     | Wertzeile: „23Apr2025 12:23 20m FT8 599"      |
| DG5XXX   | Tabellenlayout     | Frequenz „5,3570" statt Bandname; Pipe-Trenner|
| DK8XX    | zerstört (OCR)     | DARC-QR hat Vorrang; OCR-Pfad irrelevant      |
| G7XXX    | teils zerstört     | Call erkennbar, Datenzeile unleserlich        |
| TM2XXX   | handschriftlich    | Call „TM 2 CIN" mit Leerzeichen zerstört      |
| WB1XXX   | handschriftlich    | Call „WBLCLT" (1→L OCR-Fehler)                |

## Entscheidung

### Mehrschichtige OCR-Extraktion

`_parse_ocr_text` arbeitet in zwei Schichten:

**Schicht 1 (bestehend):** `parse_qr_text` — strukturierter Key:Value-Parse
(DARC-Format: „From: … To: … Date: … Band: … Mode: …"). Greift bei vollständigen
Key:Value-Texten.

**Schicht 2 (neu):** `_extract_token_based` — token-basierte Breitband-Extraktion:

1. **Tokenisierung:** Text wird an Whitespace und Pipe-Zeichen aufgeteilt; umgebende
   Satzzeichen (außer `/`) werden von Tokens abgetrennt.

2. **Feld-Erkennung pro Token:** Jedes Token wird durch die vorhandenen Normalizer
   geschickt — `normalize_band`, `normalize_mode(fuzzy=False)`, `normalize_date`.
   Fuzzy-Mode ist im Token-Scan **deaktiviert**, da er bei Tabellenköpfen Falsch-
   Positive erzeugt (Beispiel: „DATE" → „DATA" via Levenshtein-1).

3. **Rufzeichen-Erkennung:** Tokens, die durch keinen Normalizer erkannt wurden, werden
   gegen das Muster `^[A-Z0-9]{0,2}[A-Z][0-9][A-Z][A-Z0-9]{0,3}(/[A-Z0-9]+)?$`
   geprüft. Dieses Muster ist bewusst enger als das ursprüngliche `[A-Z0-9]{1,3}[0-9]…`,
   weil Bandnamen wie „20m" und RST-Werte wie „599" sonst fälschlich als Rufzeichen
   erkannt werden würden.
   - Eigener Call (via `is_own_call`) → `call_to`
   - Einziger Fremd-Call → `call_from` (Absender)
   - Mehrere verschiedene Fremd-Calls → `call_from = None` (unsicher)

4. **Mehrdeutigkeitsregel (ADR-0007):** Enthält der Text mehrere **verschiedene** gültige
   Werte für Band oder Mode, wird das Feld auf `None` gesetzt — kein Raten.
   Gleichlautende Mehrfachvorkommen sind unproblematisch.

### Was sich NICHT ändert

- QR-Vorrang (ADR-0007): `decode_qr_from_pdf` wird weiterhin zuerst versucht.
- Falsch-Positiv-Schutz: Die Sicherheit liegt in `match_card` (3-von-4,
  Widerspruchs-Ausschluss, ADR-0016) — nicht in der OCR-Extraktion.
- Fuzzy-Rufzeichen im Matching (Levenshtein-1 auf `call_from`) bleibt unberührt.
- Band/Mode-Vergleich im Matching bleibt exakt (nach Normalisierung).
- Handschriftliche Karten mit zerstörtem Call: `call_from = None` → UNCERTAIN →
  manueller Pfad. Dies ist korrekt und beabsichtigt.

## Konsequenzen

- Gedruckte ausländische Karten im Tabellen-/Fließtext-Layout werden jetzt automatisch
  ausgewertet (statt alle in UNCERTAIN zu landen).
- `normalize_mode` erhält einen optionalen Parameter `fuzzy: bool = True` für die
  Abwärtskompatibilität; der Token-Scan nutzt `fuzzy=False`.
- 7 reale OCR-Texte als Test-Fixtures in `tests/test_run.py`.
- Handschriftliche Karten bleiben im manuellen Pfad (kein Regressionsproblem).
- Die Grenze des automatischen Pfads bleibt klar: strukturierte oder gedruckte
  Karten → automatisch; stark handschriftliche oder zerstörte Karten → manuell.
