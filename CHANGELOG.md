# Changelog

Alle nennenswerten Änderungen an QSL73 werden in dieser Datei dokumentiert.

Das Format basiert auf [Keep a Changelog](https://keepachangelog.com/de/1.0.0/),
das Projekt folgt [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **RV-Hand-Test empirisch bestätigt** (2026-06-17): exaktes Schreibformat für Papier-QSL-
  Bestätigung in Log4OM bewiesen — `docs/discovery.md §3`, ADR-0005/0006 aktualisiert.
  Schritt 5 (Schreiblogik) damit spezifikationsseitig entsperrt. Issue #1 geschlossen.
  Kernbefunde: `R="No"→"Yes"` (nie `"V"`); `RV`: `"Bureau"`/`"Direct"` (Großbuchstabe),
  `undefined` → RV-Feld entfernen; kein `RD`-Datum; `R="Requested"` ebenfalls Kandidat,
  `R="Invalid"` überspringen.

- **Schritt 4b — QR-Decoding + kontrollierte DB-Abnahme** (freigegeben):
  - `src/qsl73/qr.py`: client-seitige QR-Dekodierung aus PDF-Bytes (ADR-0011, ADR-0012,
    ADR-0017)
    - `decode_qr_from_pdf(pdf_bytes)`: alle PDF-Seiten rendern (pymupdf, 300 dpi),
      QR-Codes suchen/dekodieren (zxingcpp); erstes gültiges `CardFields` zurückgeben;
      kein Absturz bei korrupten Eingaben oder fehlenden Libs
    - `parse_qr_text(text)`: toleranter Key-Value-Parser für DARC-QSL-Format;
      ignoriert Werbe-QR (fehlende Pflichtfelder `From`/`To`/`Date`/`Band`/`Mode`)
  - ADR-0017: `zxingcpp` statt `pyzbar` (pyzbar-DLL scheitert auf Windows Server 2025,
    Issue #7 dokumentiert das Packaging-Problem)
  - `tests/test_qr.py`: 23 Tests (Parser-Ebene ohne externe Deps + PDF-Decode-Pfad
    mit selbst erzeugtem QR-Bild via qrcode; skippt ohne zxingcpp)
  - `tests/acceptance/`: 6 Abnahme-Tests A–E gegen echte DB-Kopie in `tmp_path`
    (Original-DB unverändert; CI-kompatibel — skippt ohne `docs/testdateien/`):
    A: Anker → CERTAIN · B: Anker gelöscht → NO_MATCH ·
    C: Band-Widerspruch → NO_MATCH · D: Band fehlt, 2 QSOs → UNCERTAIN ·
    E: DG5MLA (60m/FT8) + OE6DRG (20m/FT8) → CERTAIN

- **Schritt 4a — Matching-/Normalisierungslogik** (freigegeben):
  - `src/qsl73/normalize.py`: Datum-Normalisierung (alle §6.3-Formate, mehrdeutig →
    `None`); Band-Normalisierung (Direktname + Frequenz, **15 Bänder**: 160m/80m/60m/40m/
    30m/20m/17m/15m/12m/10m/6m/4m/2m/70cm/23cm; Zwei-Pass: MHz → kHz-Fallback);
    Mode-Normalisierung (Mapping-Tabelle historische ITU-Bezeichnungen + Levenshtein-1-
    Fallback via rapidfuzz; USB/LSB → SSB)
  - `src/qsl73/callsign.py`: Rufzeichen-Zerlegung (3-Fall-Logik: Suffix/ITU-Präfix/
    mehrdeutig → `None`); Eigenrufzeichen-Prüfung gegen `own_callsign` und alle
    `stationcallsign`-Werte der DB (portabler Call-Toleranz)
  - `src/qsl73/matching.py`: Matching-Engine —
    **3-von-4 + Widerspruchs-Ausschluss** (ADR-0016): Rufzeichen + mindestens 2 weitere
    Felder positiv; lesbare Kartenfelder, die widersprechen, schließen Kandidaten aus;
    fehlende Felder (`None`) neutral, kein Raten. Fuzzy-Toleranz (Levenshtein-1) wirkt
    **ausschließlich auf das Rufzeichen** — Band und Mode werden exakt
    normalisiert-gegen-normalisiert verglichen (In-Memory, kein DB-Write, ADR-0007).
    Suffix-Unterschied-Regel (ADR-0013): strenger als 3-von-4. Zeit-Tie-Breaker ±30 min.
  - `src/qsl73/data/itu_prefixes.py`: ITU-Länderpräfix-Datendatei (~130+ Präfixe)
  - `src/qsl73/config.py`: `portable_suffixes` zu `MatchingConfig` ergänzt
  - ADR-0013 (Rufzeichen-Zerlegung und Zeitlogik), ADR-0014 (None für unbestimmte
    Felder), ADR-0015 (eQSL-Transparenz statt Filterung), ADR-0016 (abgestuftes
    Matching 3-von-4 + Widerspruchs-Ausschluss)
  - 459 Tests gesamt grün (parametrisierter OCR-Fehlerkatalog, Falsch-Positiv-
    Fokustests, alle §6.4-Akzeptanzkriterien); 3 erwartete Skips (DPAPI-Plattform)

- **Schritt 3 — Paperless-Client** (`src/qsl73/paperless.py`, freigegeben):
  Auth (Token + Password→Token), Dokumente nach Tag mit Paginierung, OCR-Text,
  Preview/Download/Thumb, Tag-Operationen (Name→ID, PATCH); klare Fehlerklassen ohne
  Secrets in Fehlermeldungen; 56 Unit-Tests gegen Mocks (responses)

- **Schritt 2 — Config + Kryptographie** (freigegeben):
  - `src/qsl73/config.py`: Laden/Speichern aus `%APPDATA%\QSL73\config.yaml`,
    Validierung aller Felder, Defaults, Migrations-Gerüst mit `config_version`-Feld
  - `src/qsl73/crypto.py`: `CryptoBackend`-Interface mit `DpapiBackend` (Windows DPAPI,
    lazy import) und `NullBackend` (Tests/CI)
  - `src/qsl73/setup_assistant.py`: `SetupNeeded`-Exception, `load_or_trigger_setup()`,
    `create_initial_config()` mit Override-Unterstützung
  - pytest-Gerüst (`tests/`, `pyproject.toml`); GitHub Actions CI
    (`.github/workflows/ci.yml`) bei Push auf `dev` und `main`
  - ADR-0010: Kryptographie-Abstraktionsschicht (DPAPI-Backend, fail-closed)

### Changed

- Lizenz von MIT auf **GPLv3** gewechselt (ADR-0018). `LICENSE`-Datei ersetzt;
  README, KONZEPT §15, Quelldatei-Header angepasst. Copyleft sichert, dass
  Weiterentwicklungen offen bleiben.
- `crypto.py`: `get_default_backend()` wirft `CryptoUnavailableError` auf Windows ohne
  pywin32 statt still auf `NullBackend` zurückzufallen (fail closed)
- `config.py`: `save_config()` verweigert das Speichern eines Tokens ohne Crypto-Backend
- `NullBackend` als UNSICHER/nur Test-CI dokumentiert; `CryptoUnavailableError` ergänzt

### Security

- Kein stiller Fallback auf unsicheres NullBackend bei fehlendem pywin32 auf Windows
- Token wird nie unverschlüsselt persistiert; bei fehlendem Backend klare Exception

## [0.1.0] - 2026-06-16

### Added

- Initiales Repo-Grundgerüst (Verzeichnisstruktur, Branches `main` und `dev`)
- `KONZEPT.md` – technische Spezifikation (Datenquellen, Matching-Logik, GUI, Sicherheit)
- `ROADMAP.md` – Schrittplan mit Review-Punkten
- `config.example.yaml` – Konfigurationsvorlage ohne echte Werte
- `LICENSE` (MIT, DF1DS)
- Zentrale Versions-Stelle: `src/qsl73/__version__.py` (`0.1.0`)
- `assets/qsl73logo.png` – Logo-Originaldatei
