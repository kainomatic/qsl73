# Changelog

Alle nennenswerten Änderungen an QSL73 werden in dieser Datei dokumentiert.

Das Format basiert auf [Keep a Changelog](https://keepachangelog.com/de/1.0.0/),
das Projekt folgt [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **Schritt 6b — GUI-Grundgerüst (tkinter):**
  - `python -m qsl73` startet die Anwendung; Einstiegspunkt `src/qsl73/__main__.py`
  - `InstanceLock` (PID-Lockfile, `%APPDATA%\QSL73\qsl73.lock`): verhindert mehrfache
    Instanzen ohne pywin32; stale Locks (tote PID) werden überschrieben
  - `SetupWizard` (tk.Toplevel): erster-Start-Assistent mit allen Config-Feldern;
    Token-Feld mit `show="*"` (nie Klartext sichtbar); dateiauswahl für DB-Pfad
  - `MainWindow` (tk.Tk): Treeview mit allen Karten (Rufzeichen, Datum, Band, Modus,
    Quelle, Status); Klick-Selektion; Filter (alle/sicher/unsicher/kein Treffer);
    „Durchlauf starten" / „Jetzt schreiben"-Flow mit Bestätigungs-Dialog;
    BETA-Kennzeichnung im Fenstertitel wenn `CHANNEL = "beta"`
  - `RunController` (thread-/tk-frei): Queue-Pattern (ADR-0023); `start_run()` +
    `start_write()` laufen in Daemon-Threads; GUI pollt via `root.after(100)`
  - `filter_results()`: reine Funktion, `RunResult → list[CardResult]`; testbar ohne tk
  - `show_error()`: modaler Fehler-Dialog mit aufklappbarem Traceback
  - `CHANNEL = "stable"` in `__version__.py` für Kanalsteuerung
  - ADR-0023: GUI-Architektur-Entscheidungen (Controller-Pattern, PID-Lock)
  - Unit-Tests für alle GUI-Logik-Module ohne tk-Abhängigkeit (CI-kompatibel):
    `test_filter_util.py` (6), `test_controller.py` (6), `test_instance_lock.py` (5),
    `test_setup_wizard_logic.py` (7)

- **Schritt 6a — Lauf-Orchestrierung (`src/qsl73/run.py`):**
  - `run_pass(paperless_client, db_path, config, on_progress)`: rein lesender
    Durchgang Sammeln→Auswerten→Matchen, liefert `RunResult` mit Einteilung
    `certain`/`uncertain`/`no_match`; Fortschritts-Callback für GUI (6b)
  - `write_selected(selections, db_path, backup_dir, ...)`: schreibt ausgewählte
    QSOs über `log4om_db.write_confirmations` (Schema-Check, WAL, Backup, Transaktion,
    Nebenläufigkeit); danach Paperless-Tags (DB-zuerst, ADR-0003); Tag-Fehler nicht fatal
  - `load_qso_candidates`: Vorfilter R='No'/'Requested'; R='Yes'/'Invalid' ausgeschlossen;
    liefert Fingerabdruck + expected_states für 5c-Schutz
  - `evaluate_card`: QR-Vorrang (download + zxingcpp), Fallback auf OCR-Text;
    `_parse_ocr_text`: Key:Value-Parse + Regex-Fallback für beschriftete Felder
  - `existing_confirmations` (ADR-0015): non-QSL-Bestätigungen mit R='Yes' pro gematchtem QSO
  - ADR-0022: RunResult-Struktur, Fingerabdruck-Weitergabe, Tag-Setzen-Abgrenzung
  - Kosmetik §17: zxingcpp statt pyzbar dokumentiert; libzbar-DLL-Packaging-Risiko entfällt

- **Konzept: Release-Kanäle Stable/Beta dokumentiert** (ADR-0021): Stable (main,
  `C:\Program Files\QSL73`, `%APPDATA%\QSL73\`) und Beta (dev,
  `C:\Program Files\QSL73 Beta`, `%APPDATA%\QSL73-Beta\`) als parallel installierbare
  Programme mit getrennten Daten; Update-Prüfung kanalabhängig (Stable → main-Releases;
  Beta → nur explizit getaggte GitHub-Pre-Releases); BETA-Kennzeichnung in Oberfläche;
  DB-Pfad-Hinweis bei gemeinsamem Einsatz. Umsetzung in Schritt 8 (Update-Kanal) und
  Schritt 9 (zwei Installer).

- **Schritt 5c — Nebenläufigkeit (Gastschreiber, SQLITE_BUSY, Optimistic Locking):**
  - `src/qsl73/log4om_db.py`: Nebenläufigkeits-Sicherheitsschicht für den Schreibpfad
    - Konstanten `BUSY_RETRY_COUNT=3`, `BUSY_RETRY_DELAY_S=0.3`, `BUSY_TIMEOUT_MS=500`
    - `DatabaseBusyError`: DB nach allen Versuchen gesperrt — sauberer Abbruch
    - `DatabaseChangedError`: DB-Fingerabdruck geändert — gesamter Schreibvorgang abgebrochen
    - `get_db_fingerprint(db_path)`: pfadbasierter Fingerabdruck (Hauptdatei mtime+size,
      WAL-Datei als Diagnosefelder). Primärvergleich auf Hauptdatei (WAL-Recovery-stabil).
    - `fingerprints_differ(fp1, fp2)`: Vergleich nur Hauptdatei (nicht WAL-mtime — SQLite
      WAL-Recovery schreibt neue Salts ohne neue Datenframes, wäre Falsch-Positiv)
    - `is_log4om_running(process_names)`: plattformtolerante Prozessprüfung (Windows:
      tasklist; Linux/CI: ps); mockbar über optionalen Parameter
    - `open_wal_connection` erweitert: setzt `PRAGMA busy_timeout=<ms>` (ergänzt manuellen
      Retry — SQLite wartet intern bis busy_timeout ms, dann Retry-Schleife greift)
    - `create_backup` gehärtet: Rückgabewert von `PRAGMA wal_checkpoint(FULL)` wird
      ausgewertet; unvollständiger Checkpoint (busy==1 oder log!=checkpointed) loggt
      WARNING ins qsl73-Log statt stillschweigend fortzufahren (ADR-0020-Härtung)
    - `write_confirmations` erweitert: neue Parameter `snapshot_fingerprint`,
      `expected_states`, `retry_count`, `retry_delay_s`, `busy_timeout_ms`
    - `_run_transaction`: `BEGIN IMMEDIATE` (statt deferred) — Schreibsperre sofort
      beim BEGIN angefordert; BUSY schlägt früh fehl, kein Teilschreiben-Risiko
    - Skip-vs-Rollback-Abgrenzung (ADR-0008):
      - Technisch (QSO fehlt, JSON-Fehler, kein CT='QSL') → ROLLBACK aller (5b)
      - R='Yes' oder expected_states-Mismatch → ÜBERSPRINGEN + skipped-Eintrag (5c)
  - ADR-0008 erweitert: Implementierungsdetails zu Fingerabdruck-Strategie,
    Skip-vs-Rollback-Abgrenzung, WAL-WAL-Recovery-Robustheit, Checkpoint-Härtung
  - GitHub-Issue #8: Manueller Win10-Realtest "Nebenläufigkeit gegen laufendes Log4OM"
    mit Schritt-für-Schritt-Anleitung für DF1DS angelegt
  - `tests/test_log4om_db.py`: 38 neue Unit-Tests (Gesamtanzahl: 60):
    - `open_wal_connection`: busy_timeout-Konfiguration (2 Tests)
    - `create_backup`: Checkpoint-Vollständigkeit + WARNING-Logging (2 Tests)
    - Fingerabdruck: Felder, Gleichheit, Änderung nach Checkpoint, Fallback-Logik (8 Tests)
    - `write_confirmations` Fingerabdruck-Check: DatabaseChangedError, kein Backup, kein
      Schreiben; Durchlauf bei unverändertem Fingerabdruck (4 Tests)
    - SQLITE_BUSY: DatabaseBusyError bei erschöpften Versuchen, kein Teilschreiben (Hash),
      Retry-Anzahl via monkeypatch verifiziert, Erfolg nach Lock-Freigabe (4 Tests)
    - Optimistic Locking: bestätigtes QSO übersprungen, andere geschrieben; skip hat
      Grund; technische Fehler → ROLLBACK; ungültiger R-Wert → skip (7 Tests)
    - expected_states: Match→Schreiben, Mismatch→Skip, fehlender Key→Schreiben (3 Tests)
    - R='Requested' als 'offen' akzeptiert (1 Test)
    - is_log4om_running: found/not found/leer/case-insensitiv/blockiert nicht/CI (6 Tests)
    - Integrations-Hash: Original-DB unverändert wenn alle QSOs übersprungen (1 Test)

- **Schritt 5a — Schreiblogik (isoliert):**
  - `src/qsl73/log4om_write.py`: reine JSON-Transformationslogik für Papier-QSL-Bestätigung
    - `apply_paper_qsl(json_str, route)`: setzt im CT='QSL'-Eintrag R→"Yes", RV per route
      (bureau/direct/undefined); alle anderen Einträge/Spalten unberührt; kein RD
    - `write_paper_qsl(conn, qsoid, route)`: liest qsoconfirmations, wendet Transformation
      an, schreibt zurück (bewusst ohne Transaktion/Backup — kommt in 5b)
    - Exceptions: `InvalidRouteError`, `QslEntryNotFoundError`, `ValueError`
  - ADR-0019: fehlender CT='QSL'-Eintrag → Exception, kein stilles Neuanlegen
  - `tests/test_log4om_write.py`: 38 Unit-Tests (alle Routen, Idempotenz, Fehlerfälle,
    Unversehrtheit anderer Einträge, Ausgabeformat)
  - `tests/acceptance/test_write_acceptance.py`: 9 Abnahme-Tests gegen DB-Kopie —
    bureau/direct/undefined korrekt; andere CT-Typen/Spalten/QSOs unverändert;
    Original-DB-Integrität per SHA-256 verifiziert

- **Schritt 5b — Sicherheits- & Transaktionsschicht:**
  - `src/qsl73/log4om_db.py`: Orchestrierungsmodul für sichere DB-Schreibvorgänge
    - `validate_schema(conn)`: prüft Tabelle/Spalte/Stichprobe (CT='QSL'+R-Feld);
      gibt None (ok) oder Abweichungsbeschreibung (nicht-ok) zurück (ADR-0004, §3.3)
    - `open_wal_connection(db_path)`: öffnet SQLite-Verbindung im WAL-Modus (§3.1)
    - `create_backup(db_path, backup_dir, max_count)`: WAL-Checkpoint (PRAGMA
      wal_checkpoint(FULL)) + Datei-Kopie + Rotation auf max_count (Default 5) (§7, ADR-0020)
    - `write_confirmations(db_path, items, backup_dir, backup_count)`: Reihenfolge
      Schema-Check → Backup → atomare Transaktion; jeder Fehler → ROLLBACK (ADR-0003)
    - `SchemaError`: Schema-Abweichung signalisiert Schreibsperre
    - `WriteResult`: strukturiertes Schreibergebnis (written, skipped) für GUI/audit.log
  - ADR-0020: WAL-Checkpoint-Strategie für Vor-Backup (FULL-Checkpoint vor Kopieren)
  - `tests/test_log4om_db.py`: 22 Unit-Tests gegen synthetische Mini-DBs (CI-grün):
    Schema-Check (9 Tests), Backup-Rotation/WAL-Konsistenz (6 Tests),
    Transaktion/Atomarität (7 Tests)
  - `tests/acceptance/test_db_orchestration_acceptance.py`: 5 Acceptance-Tests A–E
    gegen DB-Kopie — Schema-OK, Erfolg, Rollback, Reihenfolge, Backup-Rotation;
    Original-DB-Integrität per SHA-256; skip ohne `docs/testdateien/`
  - Abgrenzung 5c (bewusst NICHT in 5b): SQLITE_BUSY-Retry, data_version-Check,
    optimistic locking (Pro-QSO-Gegenprüfung), Log4OM-Running-Erkennung,
    Paperless-Tags (kommen mit GUI/Orchestrierung)

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
