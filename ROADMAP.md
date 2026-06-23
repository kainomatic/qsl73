# QSL73 – Schrittplan & Review (ROADMAP.md)

> Steuert das **Vorgehen** (Reihenfolge, Discovery, Review-Punkte) – nicht die
> Spezifikation (→ KONZEPT.md). Lebendes Dokument: erledigte Schritte abhaken,
> Reihenfolge bei Bedarf anpassen.

## Zusammenarbeit (Rollen)
- **Claude Desktop:** Architekt + Reviewer. Schreibt/aktualisiert KONZEPT.md & Prompts,
  liest nach jedem Schritt den Repo-Stand (Filesystem, nur lesend) und prüft gegen die
  Akzeptanzkriterien im KONZEPT.md. Schreibt nie selbst ins Repo.
- **User (DF1DS):** Vermittler – überbringt Prompts und Repo-Stände.
- **Claude Code:** baut, committet, testet, versioniert, macht GitHub/Releases/Doku.

**Schleife je Schritt:** Desktop formuliert Auftrag (Kontext+Aufgabe+Akzeptanzkriterien)
→ User überbringt → Claude Code baut & committet **inkl. Done-Abschluss** (siehe unten) →
Desktop liest Repo & reviewt → Korrektur-Auftrag oder Freigabe → nächster Schritt.

**Done-Abschluss** (Teil jedes Commits): pytest grün + CI grün · ROADMAP-Status
aktualisiert · CHANGELOG ergänzt · erledigte Issues geschlossen · ADR falls nötig.
→ vollständige Checkliste: **CLAUDE.md „Definition of Done je Bau-Schritt"** (ADR-0027)

**Tests ab Schritt 2:** Jeder Bau-Schritt (2–9) liefert Unit-Tests mit. Ein Schritt gilt
erst als fertig, wenn pytest grün ist und CI (GitHub Actions) durchläuft. → ADR-0009

**Voraussetzung Review-Lesezugriff:** Repo liegt unter `C:\Entwicklung\` (freigegeben),
z. B. `C:\Entwicklung\qsl73`.

---

## ✅ Schritt 0 — Discovery (vor dem ersten Code) — ABGESCHLOSSEN

Ziel: Unbekannte an echten Daten klären, damit später nichts blind gebaut wird.
- **Log4OM-DB (read-only auf Kopie):** Tabellen/Spalten gedumpt; Felder für Rufzeichen,
  Datum/Zeit (UTC), Band, Mode identifiziert; exakt ermittelt, welche Spalte/welcher
  Wert „Papier-QSL bestätigt" bedeutet (Abgrenzung zu eQSL/LoTW/QRZ); Schreibformat
  empirisch bestimmt (zuerst Schätzung, dann per RV-Hand-Test 2026-06-17 bewiesen).
- **Paperless (echte Karten):** 7 echte QSL-Karten analysiert (OCR-Qualität, QR-Pfad,
  API-Endpunkte). Befunde in `docs/discovery.md`.
- **Ergebnis:** `docs/discovery.md` mit allen Befunden inkl. empirisch bestätigtem
  Schreibformat (Issue #1 geschlossen).
- **Review:** Abgenommen; Discovery vollständig.

## ✅ Schritt 1 — Repo-Grundgerüst — ABGESCHLOSSEN

- Struktur, `.gitignore`, `config.example.yaml`, `README.md`, `CHANGELOG.md`, `LICENSE`
  (ursprünglich MIT, später auf GPLv3 gewechselt → ADR-0018), Versions-Datei `0.1.0`,
  `assets/` mit `qsl73logo.png`. Branches `main`/`dev`.
- **Review:** Vollständigkeit/Struktur bestätigt, keine Secrets, Version 0.1.0 gesetzt.

## ✅ Schritt 2 — Config & Setup-Grundlagen — ABGESCHLOSSEN

- Config-Load/Save (`%APPDATA%\QSL73\config.yaml`), DPAPI-Token, Schema-Versionsfeld +
  Migrationsgerüst. Setup-Assistent (Minimalfassung).
  pytest-Gerüst + GitHub-Actions-CI (`/.github/workflows/ci.yml`) eingerichtet.
- **Review:** Token nur verschlüsselt; fehlende Config → Assistent; Migrationsstub
  vorhanden; pytest grün; CI-Workflow grün.

## ✅ Schritt 3 — Paperless-Client — ABGESCHLOSSEN

- Auth (Token & User/PW→Token), Dokumente nach Tag holen, OCR-Text, Bild/Preview, Tag
  PATCH. 56 Unit-Tests gegen Mocks.
- **Review:** Karten lesbar, Bildabruf funktioniert, Fehler bei nicht erreichbarem Server
  sauber abgefangen; pytest grün, CI grün.

## ✅ Schritt 4 — Log4OM-Zugriff (read) + Matching — ABGESCHLOSSEN

Aufgeteilt in zwei Teilschritte:

### ✅ Schritt 4a — Matching-/Normalisierungslogik (freigegeben)

- `normalize.py`: Datum (alle §6.3-Formate), Band (15 Bänder: 160m–23cm inkl. 60m/4m;
  Frequenz-zu-Band-Umrechnung mit Zwei-Pass-Ansatz), Mode (Mapping-Tabelle + Fuzzy).
- `callsign.py`: Rufzeichen-Zerlegung, Eigenrufzeichen-Prüfung gegen own_callsign + alle
  stationcallsign-Werte der DB.
- `matching.py`: **3-von-4 + Widerspruchs-Ausschluss** (ADR-0016): Rufzeichen + mind. 2
  weitere Felder positiv; widersprechende lesbare Felder schließen Kandidaten aus; fehlende
  Felder (None) neutral. **Fuzzy (Levenshtein-1) wirkt ausschließlich auf das Rufzeichen;
  Band und Mode werden exakt normalisiert-gegen-normalisiert verglichen (In-Memory, ADR-0007).**
  Suffix-Unterschied-Regel strenger (ADR-0013). Zeit-Tie-Breaker ±30 min.
- ITU-Präfix-Datendatei (~130+ Einträge), MatchingConfig um portable_suffixes ergänzt.
- ADR-0013/0014/0015/0016 dokumentiert.
- 410+ Tests grün (OCR-Fehlerkatalog, Falsch-Positiv-Fokus, §6.4-Akzeptanzkriterien).

### ✅ Schritt 4b — QR-Decoding + DB-Abnahme (freigegeben)

- `qr.py`: client-seitige QR-Dekodierung aus PDF-Bytes (pymupdf + zxingcpp, ADR-0011/0017).
  Toleranter Key-Value-Parser; ignoriert Werbe-QR; kein Absturz bei Eingabefehlern.
- ADR-0017: zxingcpp statt pyzbar (DLL-Problem auf Windows, Issue #7).
- Abnahme-Tests A–E gegen echte DB-Kopie in tmp_path (Original unverändert, CI-kompatibel).
  A: Anker → CERTAIN · B: gelöscht → NO_MATCH · C: Band-Widerspruch → NO_MATCH ·
  D: Ambiguität → UNCERTAIN · E: gedruckte Karten → CERTAIN.
- 459 Tests gesamt grün; 3 erwartete Skips (DPAPI-Plattform).

**Review (Schritt 4 gesamt):** §6-Akzeptanzkriterien erfüllt; QR-Pfad + OCR-Normalisierung
getestet; QR→OCR→manuell-Priorität korrekt; 3-von-4-Matching mit Widerspruchs-Ausschluss
widerlegt Falsch-Positive zuverlässig; Anker-Negativtest (B) und Band-Widerspruch (C)
bestätigen Falsch-Positiv-Schutz. Freigegeben.

---

## ✅ Schritt 5 — Schreiblogik (commit) + Backup — ABGESCHLOSSEN

**Spezifikationsseitig entsperrt:** Schreibformat empirisch bestätigt (RV-Hand-Test
2026-06-17, `docs/discovery.md §3`, Issue #1 geschlossen).

### ✅ Schritt 5a — Isolierte Schreiblogik (freigegeben nach Review)

- `src/qsl73/log4om_write.py`: `apply_paper_qsl` (reine JSON-Transformation) +
  `write_paper_qsl` (nackte DB-Schreibfunktion ohne Transaktions-Orchestrierung)
- ADR-0019: fehlender CT='QSL'-Eintrag → QslEntryNotFoundError (kein stilles Neuanlegen)
- 38 Unit-Tests + 9 Abnahme-Tests gegen DB-Kopie; Original-DB-Integrität per SHA-256; grün

### ✅ Schritt 5b/5c — Transaktion, Backup, Schema-Validierung, Nebenläufigkeit, Tags

- `src/qsl73/log4om_db.py`: Schema-Check (`validate_schema`), WAL-Verbindung
  (`open_wal_connection`), Vor-Backup mit Checkpoint (`create_backup`), atomare Transaktion
  (`write_confirmations`): Reihenfolge DB-dann-Tags strikt (ADR-0003). Vor-Backup nur beim
  tatsächlichen Schreiben, Aufbewahrung Default 5 (ADR-0020).
- Nebenläufigkeit (ADR-0008): `SQLITE_BUSY`-Retry (3×/300 ms), `get_db_fingerprint` +
  `fingerprints_differ` (data_version/Fallback), Optimistic Locking (Pro-QSO-Gegenprüfung),
  `is_log4om_running`-Warnung, `BEGIN IMMEDIATE` für frühzeitige Schreibsperre.
- Schreibformat (empirisch bestätigt): `R="Yes"`; `RV`: `"Bureau"`/`"Direct"` (Großbuchstabe)
  oder RV-Feld entfernen (undefined); kein `RD`; `S`/`SV`/`CT` unverändert.
- **Realtest (Issue #8, 2026-06-18 geschlossen):** Ende-zu-Ende gegen laufendes Log4OM
  auf Win10 bestätigt; DatabaseChangedError und Vor-Backup real verifiziert.
- **Review:** Akzeptanzkriterien §5/§7 erfüllt; 60 Unit-Tests + 5 Acceptance-Tests A–E;
  pytest grün, CI grün.

## ✅ Schritt 6 — GUI — ABGESCHLOSSEN

### ✅ Schritt 6a — Lauf-Orchestrierung (`run.py`)

- `src/qsl73/run.py`: `run_pass()` (Sammeln→Auswerten→Matchen, liefert `RunResult`),
  `write_selected()` (DB über `write_confirmations`, Paperless-Tags DB-zuerst, ADR-0003),
  `load_qso_candidates()` (Vorfilter R=No/Requested, expected_states),
  `evaluate_card()` (QR-Vorrang, OCR-Fallback), `_extract_token_based()` (Token-OCR für
  gedruckte Karten ohne Key:Value-Beschriftung, ADR-0025).
- `CardResult`, `RunResult` mit Einteilung certain/uncertain/no_match; ADR-0022.
- `existing_confirmations` (non-QSL-Bestätigungen mit R='Yes' als Kontext, ADR-0015).
- ADR-0022 (RunResult-Struktur), ADR-0025 (Token-basierte OCR-Extraktion).
- Tests: `tests/test_run.py`; pytest grün, CI grün.

### ✅ Schritt 6b — tkinter-GUI-Grundgerüst

- `src/qsl73/gui/main_window.py`: `MainWindow` mit Treeview (Rufzeichen/Datum/Band/Mode/
  Quelle/Status), Filter (alle/sicher/unsicher/kein Treffer), Lauf-Starten + Jetzt-Schreiben-
  Flow; CERTAIN-Auswahl; BETA-Kennzeichnung im Fenstertitel.
- `src/qsl73/gui/controller.py`: `RunController` — Queue-Pattern, Daemon-Threads, GUI
  pollt via `root.after(100)` (ADR-0023).
- `src/qsl73/gui/filter_util.py`: `filter_results()`, `is_batch_writable()`,
  `build_write_selections()` — rein testbar, kein tk.
- `src/qsl73/gui/setup_wizard.py` + `gui/wizard_logic.py`: Setup-Assistent; Auth-Felder
  dynamisch umschaltbar; Passwort nie persistiert (§4).
- `src/qsl73/gui/error_dialog.py`: modaler Fehler-Dialog mit aufklappbarem Traceback.
- `src/qsl73/gui/app.py` + `src/qsl73/__main__.py`: Einstiegspunkte.
- `src/qsl73/logging_setup.py`: `setup_logging()` / `get_log_dir()` (Stable/Beta-getrennt;
  ADR-0026 — wird hier als erste Aktion in `app.py` aufgerufen).
- ADR-0023 (GUI-Architektur); P1-Fixes #9–#13 eingearbeitet.
- Tests: `tests/gui/` (7 Module, CI-kompatibel ohne tk); pytest grün, CI grün.
- **Hinweis:** Nur CERTAIN-Karten sind im Hauptfenster selektierbar (ADR-0007).
  UNCERTAIN-Karten folgen über den manuellen Zuordnungs-Bildschirm (Schritt 6c).

### Schritt 6c — Manueller Zuordnungs-Bildschirm

#### ✅ Schritt 6c-1 — Zuordnungs-Logik (tk-frei)

- `src/qsl73/gui/manual_match.py`: `ManualQuery`-Dataclass, `search_candidates`
  (Filter + Ranking in-memory, kein DB-Zugriff), `make_manual_selection` (route-Validierung,
  gemeinsamer Schreib-Korb wie Auto-Pfad). ADR-0028.
- Tests: `tests/gui/test_manual_match.py`; pytest grün, CI grün.

#### ✅ Schritt 6c-2 — tk-Screen

- `src/qsl73/gui/manual_assignment.py`: `ManualAssignmentDialog` (modales Toplevel);
  reine Helfer `card_fields_to_query`, `field_values_to_query`, `render_pdf_first_page`
  (alle tk-frei, vollständig ohne Display testbar).
  Kartenbild lazy nachladen (after 50 ms); OCR-Vorbefüllung; Live-Suche via
  `search_candidates`; Auswahl → `make_manual_selection` → `self.result`; modal (grab_set /
  wait_window); injizierbarer `image_loader`; Bildladefehler → Platzhalter, kein Absturz.
- Tests: `tests/gui/test_manual_assignment.py` (17 reine + 4 tk-Tests, CI-skippt tk);
  pytest grün, CI grün.

#### ✅ Schritt 6c-3 — Integration ins Hauptfenster

- `main_window.py`: Doppelklick-Handler (`<Double-1>`) für UNCERTAIN/NO_MATCH-Karten öffnet
  `ManualAssignmentDialog`; Ergebnis in `_manual_pending` (doc_id → (qsoid, route)) vorgemerkt;
  Karte als „Manuell zugeordnet" visuell markiert (lila Hervorhebung); erneuter Doppelklick
  ändert/hebt Vormerkung auf.
- `filter_util.py`: `merge_selections()` führt Auto + manuell zusammen (dedup by qsoid).
- `_on_write()`: Auto + manuell in EINER Transaktion; Bestätigung zeigt „X auto + Y manuell
  = Z Karten"; nach Schreiben Vormerkungen + Selektion geleert.
- `RunResult.candidates`: offene QSO-Kandidaten jetzt exponiert (Feld mit Default `[]`);
  GUI fasst keine DB-Logik direkt an.
- Issues: Bild-DPI für handschriftliche Karten (Issue #19), Rückseite anzeigbar (Issue #20).
- **Review:** Akzeptanzkriterien §9; pytest grün, CI grün; Schritt 6 komplett.

#### ✅ Schritt 6 UX-3 — Bestätigt-Markierung + Trefferlimit (ADR-0030)

- Nach Schreiben: bestätigte Karten zeigen „Bestätigt ✓" (grün), landen am Ende der Liste,
  sind nicht mehr anklickbar. `_written: set[int]` im MainWindow; `WriteDoneEvent` trägt
  `confirmed_doc_ids`. `sort_cards_written_last` in filter_util ausgelagert + getestet.
- `app.manual_match_limit` (Default 100; 0=kein Limit) in Config + Migration + Validierung.
  Dialog zeigt `(zeige N von M)` bei Begrenzung. `apply_display_limit` ausgelagert + getestet.
  Einstellungsfeld im Setup-Assistenten (editierbare Combobox 10/100/1000/0).
- ADR-0030 angelegt; README-Index → ADR-0031. 779 passed.

#### ✅ Schritt 6c-UX-2 — Weitere UX-Nachbesserungen manueller Zuordnungs-Dialog

- Datepicker-Grab-Fix (Klick-Durchschlag auf Band/Mode beseitigt).
- Wrap-around-Blättern (◀/▶ läuft um); `wrap_page_index` ausgelagert + getestet.
- Bild-Klick öffnet Zoom-Toplevel (150-DPI-Originalgröße, Bildschirm-Limit).
- Manuell zugeordnete Zeilen zeigen QSO-Werte; `qso_by_id` in filter_util ausgelagert.
- Kein neues ADR (UX-Details im Rahmen ADR-0029).

#### ✅ Schritt 6c-UX — UX-Nachbesserung manueller Zuordnungs-Dialog (ADR-0029)

- Realtest-Feedback umgesetzt: drei UX-Verbesserungen an `manual_assignment.py`.
- Rückseite zuerst + Blättern (`◀/▶`); 150 DPI; `render_pdf_pages()` für alle Seiten.
- Band/Mode als editierbare Combobox; Vorschläge aus DB-Kandidaten (`distinct_bands/modes`).
- Datum per tkcalendar DateEntry (Fallback Textfeld, kein Absturz ohne tkcalendar).
- Issues #19 (Bild-DPI) und #20 (Rückseite) geschlossen. ADR-0029.

#### ✅ Schritt 6d — Tag-Verwaltung im Setup + Verbindungstest (ADR-0031)

- `paperless.py`: `list_tags()` (alle Tags paginiert, inkl. `matching_algorithm`),
  `create_tag()` (immer `matching_algorithm=0`, Duplikat-Schutz).
- `wizard_logic.py`: Verbindungstest-Auswertung, Auto-Matching-Warnung, Tag-Name-Validierung,
  Auswahl-Erhalt nach Reload (alles tk-frei, getestet).
- `setup_wizard.py`: „Verbindung testen"-Button + Statusanzeige; Tag-Felder als Dropdowns
  befüllt aus Paperless; „Tags neu laden"; „Anlegen" mit Freitext (matching_algorithm=0);
  sichtbare Warnung wenn Schreib-Tag matching_algorithm != 0.
- `run.py`: `write_selected()` gibt `(WriteResult, list[str])` zurück; fehlender Tag →
  sichtbare Warnung in GUI-Dialog + Statuszeile statt stilles Verschlucken. ADR-0031.

#### ✅ Schritt 6e — Bestätigte Karten serverseitig ausfiltern (ADR-0032)

- `paperless.py`: `get_documents_by_tag` um `exclude_tag_name=None` ergänzt; bei gesetztem
  Ausschluss-Tag wird `tags__id__none={id}` an die Paperless-Query angehängt.
- `run.py`: `run_pass` übergibt `exclude_tag_name=config.tags.confirmed` → bereits bestätigte
  Karten erscheinen im zweiten Durchlauf nicht mehr als „Kein Treffer". ADR-0032.

## ✅ Schritt 7 — Logging & Fehler-Reporting — KOMPLETT (7a + 7b-1 + 7b-2)

### ✅ Schritt 7a — Diagnose-Logging + QR-Startwarnung (Issue #14)

- `logging_setup.py`: `setup_logging()` mit RotatingFileHandler auf
  `%APPDATA%\QSL73\logs\qsl73.log` (1 MB / 5 Backups, Stable/Beta-getrennt). ADR-0026.
- `QSL73_DEBUG=1` hebt Level auf DEBUG → Token-Scan-Ausgaben in `run.py` sichtbar.
- Log-Punkte in `run.py`: Lauf-Start/Ende, pro Karte Quelle+Ergebnis (INFO);
  Fallback-auf-OCR, per-QSO-Route (DEBUG); Schreibvorgang (INFO).
- `qr_backend_status()` in `qr.py`; fehlende QR-Libs → WARNING im Log + GUI-Hinweis.
- 16 neue Tests; pytest grün, CI grün.
- **Review:** Logdatei entsteht beim Start; kein Secret im Log; QR-Warnung sichtbar.

### ✅ Schritt 7b-1 — Config-Robustheit: Backups + robuster Start-Check (ADR-0033)

- `config_backup.py`: rotierende Sicherungen von `config.yaml` vor jedem `save_config`
  (`%APPDATA%\QSL73\config_backups\`, config_YYYYMMDD_HHMMSS_uuid.yaml, max N=5, kein
  Klartext-Token). `list_config_backups`, `restore_config_backup`, `get_config_backup_dir`.
- `setup_assistant.py`: `ConfigError` bei ungültiger Config propagiert direkt (nicht mehr
  in `SetupNeeded` eingewickelt) → semantische Trennung „fehlt" vs. „kaputt".
- `gui/config_error_dialog.py`: Dialog bei `ConfigError` beim Start (vor MainWindow);
  zeigt Fehlermeldung + Buttons „Einrichtung neu starten" / „Sicherung wiederherstellen"
  (nur aktiv wenn Backups vorhanden) / „Beenden"; ungültiges Backup → Meldung, kein Loop.
- `gui/app.py`: fängt `ConfigError` getrennt von `SetupNeeded` ab; ruft Fehlerdialog auf.
- 881 Tests grün (3 erwartete Skips), CI grün.

### ✅ Schritt 7b-2 — Audit-Log + Fehler-Reporting (ADR-0035)

- `audit.py`: `AuditEntry`, `write_audit_entries` — dauerhaftes Fachprotokoll in
  `audit.log` (getrennt von qsl73.log); nur tatsächlich geschriebene QSOs; auto vs. manuell.
- `error_report.py`: bereinigter Fehlerbericht (keine Secrets/QSO-Daten);
  vorausgefüllte GitHub-Issue-URL; lokal speichern; nichts automatisch gesendet.
- `gui/error_report_dialog.py`: Vorschau-Dialog mit „Lokal speichern" / „Auf GitHub melden".
- `main_window.py`: Buttons „Log-Ordner öffnen" + „Fehler melden…" in Statusleiste.
- `WriteResult.backup_path` ergänzt; `write_selected` abwärtskompatibel um
  `manual_qsoids` + `candidates` erweitert.
- **Review:** Akzeptanzkriterien §10; Bericht ohne Secrets nachgewiesen; pytest grün, CI grün.

### ✅ UX-Verbesserung #24 — Menüleiste + Einstellungen-Dialog (ADR-0036)

- `gui/setup_wizard.py`: um Bearbeiten-Modus erweitert (`existing_config`-Parameter;
  Token-Retain-Logik §4: leeres Feld = Token behalten, nie im Klartext).
- `gui/wizard_logic.py`: `config_to_field_defaults`, `is_token_retain_valid`,
  `merge_wizard_overrides` — tk-freie Logik, getestet.
- `gui/main_window.py`: Menüleiste Datei/Bearbeiten/Hilfe; „Einstellungen…" + „Über QSL73"
  neu; Buttons aus Statusleiste ins Hilfe-Menü verschoben. ADR-0036.
- Issue #24 geschlossen. 923 Tests grün.

### ✅ UX-Verbesserung — Einstellungen-Bugs + Über-Dialog + Durcharbeiten-Workflow (ADR-0037)

- **TEIL A1:** `SetupWizard._adjust_window_size` via `after(1, ...)` nach Mapping;
  Inhaltshöhe aus `inner_frame.winfo_reqheight()`; Zentrierung über Parent-Fenster.
- **TEIL A2:** Attention-Handler FocusIn/FocusOut → `<Button-1>` am Parent-Fenster
  mit Funcid-Cleanup; Erstkonfigurationsmodus (Parent nicht sichtbar) → kein Handler.
- **TEIL B:** `_on_about` als custom `tk.Toplevel` ohne Systemsound; klickbare Links
  (GitHub, QRZ.com); Paperless-ngx-Beschreibung.
- **TEIL C:** Durcharbeiten-Workflow für UNCERTAIN/NO_MATCH-Karten. `ManualAssignment
  Dialog` mit 4 Buttons (Speichern/Speichern und nächste/Nächste/Abbrechen) + `action`-
  Attribut. Statusanzeige (Phase + Fortschritt) im Dialog. Reine Logik-Funktionen
  `build_workflow_sequence` + `workflow_card_context` in `filter_util.py`. Sequenz-
  steuerung in `main_window.py` (`_continue_workflow`, `_run_workflow_phase`). ADR-0037.
- 981 Tests grün (3 erwartete Skips), CI ausstehend.

### ✅ UX-Nachbesserungen (Realtest-Feedback)

- Shift-Klick-Bereichsauswahl CERTAIN-Karten (select_range, 10 Tests).
- Ruhigere Balken-Animation (_PROGRESS_PULSE_MS=40).
- Datum-Löschen-Button im manuellen Zuordnungs-Dialog. 1007 Tests grün.

### ✅ UX — Echter Fortschrittsbalken (Issue #23)

- Balken zeigt echten Prozentfortschritt (X/N, P %) statt Endlos-Animation; kurze
  indeterminante Vorbereitungsphase beim HTTP-Laden, danach deterministisch.
  `format_progress_text` (tk-frei, 7 Tests). 997 Tests grün.

### ✅ UX/Robustheit — Benutzerfreundliche Fehlermeldungen (ADR-0039, Issue #18)

- `DatabaseChangedError` und verwandte erwartete Fehler zeigen jetzt Klartext statt
  rohem Traceback; neues Modul `gui/error_messages.py` (tk-frei, testbar). 990 Tests grün.

### ✅ UX-Verbesserung — Über-Dialog + Sprachauswahl-Entfernung (ADR-0038, Issue #25)

- **Über-Dialog verfeinert:** Luftigeres Layout, Titel als Überschrift, Autor „DF1DS"
  fett, Links „GitHub"/„QRZ.com" kurz und nebeneinander mit Hover-Unterstreichung.
  Texte als Modul-Konstanten (i18n-Vorbereitung).
- **Sprachfeld entfernt (ADR-0038):** Wirkungslose Sprach-Combo im Einstellungen-Dialog
  entfernt; `app.language` im Config-Modell erhalten (Abwärtskompatibilität). Issue #25
  vorgemerkt für V2-i18n. 958 Tests grün.

## ✅ Schritt 8 — Update-Lifecycle + Installer

- `src/qsl73/updater.py`: GitHub-Releases-API, SemVer-Vergleich (inkl. beta < stable),
  Asset-Auswahl (Stable/Beta-Kanal), Download nach %TEMP%, Größenprüfung, /SILENT-Start.
- `src/qsl73/gui/update_dialog.py`: modaler Dialog, Download-Fortschritt, „Später",
  „Nicht mehr erinnern" → update_check=False.
- `main_window.py`: Hintergrundprüfung beim Start, Menü „Nach Updates suchen",
  Update-Hinweis-Eintrag bei „Später", manuelle Prüfung immer aktiv.
- `app.py`: `schedule_update_check()` nach Fenstererstellung.
- Beide `.iss`: `CloseApplications=yes`, `AppMutex` (kanalspezifisch: `QSL73-Stable`/
  `QSL73-Beta`), `RestartApplications=no`. Self-Update-Neustart via `/RESTARTQSL73`-Flag
  aus `updater.py`; `.iss`-Pascal-Funktion `ShouldRestartApp` wertet ihn aus; `postinstall`
  mit `skipifsilent` (interaktiv) und separater `[Run]`-Eintrag (Self-Update) trennen sauber.
- `gui/app.py`: Windows-AppMutex via pywin32 (non-fatal, kanalspezifisch), koexistiert mit
  PID-Lockfile.
- ADR-0045 um Entscheidungen 11 (AppMutex) und 12 (/RESTARTQSL73-Mechanik) ergänzt.
- **Review:** Akzeptanzkriterien §12/§13; pytest grün, CI grün.

## Schritt 9 — Build, Test, erstes Release

### ✅ Schritt 9a — PyInstaller-Build + Icon + Icon-Politur (Post-Release) — ABGESCHLOSSEN

- **PyInstaller-Build (ADR-0040):** onedir-Bundle (`dist\QSL73\QSL73.exe`);
  alle Abhängigkeiten korrekt gebündelt:
  - zxingcpp: Einzel-.pyd, manuell als `binaries` in `qsl73.spec`
  - pymupdf + fitz: beide `collect_all` (native DLLs + Namespace-Wrapper)
  - tkcalendar + babel: `collect_all` (Locale-Daten erforderlich)
  - pywin32: `collect_all('win32')` + `hiddenimports` (DPAPI)
  - `!qsl73.spec` als Ausnahme in `.gitignore` eingetragen
- **Windows-Icon (Issue #5):** `assets/qsl73.ico` (16/32/48/256 px) aus
  `assets/qsl73logo.png`, erzeugt via `tools/make_icon.py`.
- **Verifikation auf Windows Server 2025:** Start, QR-Decoding, DPAPI, Datepicker — grün.
  Issue #6 (pywin32-Bundle) und Issue #16 (Python 3.12 + zxingcpp) verifiziert.
- **Build-Doku:** `docs/BUILD.md` + `tools/build.ps1`.
- **Icon-Politur (Post-v0.1.0):** Icon-Transparenz (Flood-Fill-Hintergrundentfernung in
  `make_icon.py`); tk-Feder → QSL73-Icon in allen Fenstern (`gui/_icon.py`); Logo im
  Über-Dialog transparenter + 112 px groß; laufzeitsichere Bundle-Ressource in
  `src/qsl73/assets/qsl73_icon.png` (datas in qsl73.spec). Release: v0.1.1.
- **Finaler Realtest durch DF1DS** auf frischem System: ausstehend.

### ✅ Schritt 9b — Inno-Setup-Installer (Stable) — ABGESCHLOSSEN

- `installer\qsl73.iss`: installiert `dist\QSL73\` nach `C:\Program Files\QSL73` (64-Bit);
  GPLv3-Lizenzseite; Startmenü + optionale Desktop-Verknüpfung; Deinstaller fragt nach
  `%APPDATA%\QSL73` (Default NEIN). AppId-GUID `{4FB91B69-CF4A-4DC9-B59D-2EA92B857D0B}`.
- `QSL73-Setup.exe`: 41,8 MB; Build und Verifikation B1–B4 grün.
- `tools/build_installer.ps1`: PyInstaller + Inno Setup in einem Schritt.
- `installer\Output\` in `.gitignore`; `docs/BUILD.md` um Installer-Abschnitt ergänzt.
- ADR-0041 angelegt. Finaler Wizard-Test (Sprache, Lizenz, MsgBox) durch DF1DS ausstehend.

### ✅ Schritt 9d — Liesmich/Änderungen im Installer — ABGESCHLOSSEN

- `tools/make_docs_html.py`: konvertiert `README.md` und `CHANGELOG.md` in offline-fähige,
  UTF-8-korrekte HTML-Dateien (`installer/docs/LIESMICH.html`, `AENDERUNGEN.html`).
  Abhängigkeit `markdown>=3.0` nur Build-Zeit (`requirements-dev.txt`).
- Beide `.iss`-Dateien (Stable + Beta) um [Files]-, [Icons]- und [Run]-Einträge ergänzt:
  HTML nach `{app}` kopieren, Startmenü-Verknüpfungen anlegen, am Setup-Abschluss
  optionale Checkboxen (default nicht angehakt, shellexec → Standardbrowser).
- `tools/build_installer.ps1` und `.github/workflows/release.yml` führen HTML-Erzeugung
  automatisch vor ISCC aus. `installer/docs/` in `.gitignore`.
- `docs/BUILD.md` um HTML-Infodateien-Abschnitt ergänzt (Abhängigkeit, Reihenfolge).

### ✅ Schritt 9c — Release-Automatisierung + Beta-Variante — ABGESCHLOSSEN (Release ausstehend)

- **Beta-Installer-Variante (ADR-0042):** `installer/qsl73-beta.iss` mit eigener AppId-GUID
  `{A3F5C8D2-7E4B-4A91-B5C6-2D8E9F3A1B07}`, Pfad `C:\Program Files\QSL73 Beta`,
  APPDATA `%APPDATA%\QSL73-Beta\` — Stable und Beta parallel installierbar (ADR-0021).
- **CHANNEL-Schalter:** Der Release-Workflow patcht `CHANNEL = "stable"` → `"beta"` in
  `__version__.py` ephemer (nur im CI-Lauf) vor dem PyInstaller-Bundle-Bau; kein Commit.
- **GitHub-Actions-Release-Workflow:** `.github/workflows/release.yml`; windows-latest,
  Python 3.12; baut Stable bei Tag `vX.Y.Z`, Beta-Pre-Release bei Tag `vX.Y.Z-betaN`;
  Versions-Sync-Prüfung (Tag == `__version__.py`); AppVersion-Injektion per `/DAPP_VERSION`.
- **README-Finalisierung:** ✅ Nutzer-Installationsweg, Funktionen/Bedienung, Daten &
  Verzeichnisse, Beta-Hinweis — abgeschlossen; kein „in Entwicklung"-Status mehr.
- **Beta-Start-Hinweis:** ✅ Modaler Dialog bei CHANNEL=beta (gui/beta_notice.py);
  kein Ton, kein Eingriff in Stable-Pfad.
- **Erstes echtes Release (v0.1.0):** AUSSTEHEND — durch DF1DS auszulösen (Anleitung unten);
  vollständiger Realtest vor dem Release durch DF1DS.
- **Review:** Workflow-Logik + Beta-Installer von Desktop zu reviewen; dann echtes Release.
- **v0.2.0 Stable-Release vorbereitet (CHANGELOG eingefroren, 2026-06-19):**
  `__version__ = "0.2.0"`, CHANGELOG `[Unreleased]` → `[0.2.0] - 2026-06-19` eingefroren,
  neuer leerer `[Unreleased]`-Block angelegt. dev→main-Merge + Tag `v0.2.0` durch DF1DS.
- **Beta→Stable-Workflow (ADR-0046):** Workflow verbindlich festgelegt; `release.yml`
  zieht Notes kanalabhängig; CLAUDE.md präzisiert Beta- und Stable-Handgriff getrennt.
- **Regex-Fix release.yml (Bugfix):** Lookahead `(?=\r?\n## \[)` → `(?=\r?\n## \[|\z)`
  in allen drei Extraktionsmustern; `\s*\r?\n` → `[^\r\n]*\r?\n` in `[Unreleased]`-Mustern.
  Ursache des leeren GitHub-Release-Notes-Texts bei v0.2.0. Unit-Tests in
  `tests/test_changelog_extraction.py`.
- **v0.2.1 Stable-Release vorbereitet (CHANGELOG eingefroren, 2026-06-19):**
  `__version__ = "0.2.1"`, CHANGELOG `[Unreleased]` → `[0.2.1] - 2026-06-19` eingefroren,
  neuer leerer `[Unreleased]`-Block angelegt. dev→main-Merge + Tag `v0.2.1` durch DF1DS.
- **Hotfix v0.2.2 vorbereitet (2026-06-19, ADR-0048):** Bugfix Über-Dialog-Größe/Position
  (`_on_about` via `after(1,...)`). Branch `hotfix/v0.2.2-about-dialog` von `main` (v0.2.1).
  Release durch DF1DS (Hotfix → main mergen, Tag `v0.2.2` pushen, danach Hotfix → dev mergen).
- **Hotfix v0.2.2 zurück nach dev gemergt (2026-06-19):** Über-Dialog-Fix in dev; Tooltips
  unverändert; `__version__=0.3.0`. Konflikte in `__version__`, ADR-Index, CHANGELOG
  korrekt aufgelöst. Hotfix-Branch gelöscht (lokal + remote). ADR-0049 angelegt
  (Git-Branch-Operationen sind CC-Aufgabe).
- **Hotfix v0.2.3 vorbereitet (2026-06-19):** v0.2.2-Über-Dialog-Fix war unvollständig —
  `dlg.winfo_reqheight()` lieferte durch `minsize(340, 1)` stets 1px zurück. Neuer Fix:
  Höhe aus innerem Frame (`frame.winfo_reqheight()`) + Chrome-Aufschlag + Mindesthöhe via
  `_resolve_dialog_height`, analog `SetupWizard._adjust_window_size`. Branch
  `hotfix/v0.2.3-about-dialog-height` von `main` (v0.2.2). Release durch DF1DS (Hotfix →
  main mergen, Tag `v0.2.3` pushen; danach Rück-Merge hotfix → dev als separater CC-Auftrag).
- **v0.2.3-Über-Dialog-Höhen-Fix nach dev gemergt (2026-06-19):** Wird über v0.3.0-beta2
  getestet; Stable-Release v0.2.3 folgt separat über main.
- **Verbesserter Über-Dialog-Fix (Logo-robust, 520er Mindesthöhe, mittiger Parent-Zentrierung)
  nach dev gemergt (2026-06-19):** Hotfix-Branch `hotfix/v0.2.3-about-dialog-height` →
  `dev` Rück-Merge (kein manueller Konflikt nötig — auto-aufgelöst). `dev` enthält nun:
  `_ABOUT_MIN_H=520`, `_ABOUT_MIN_W=360`, `_resolve_dialog_width`, `update_idletasks`,
  `ismapped`-Fallback (SetupWizard-Muster) + alle `attach_tooltip`-Aufrufe. `__version__=0.3.0`.
  Wird über v0.3.0-beta3 auf Win10 verifiziert; Stable v0.2.3 folgt separat über main.
  1172 Tests grün. origin/dev = 6f7f2c1. Hotfix-Branch bleibt erhalten (für Stable v0.2.3).
- **resizable(True,True)-Fix (echte Über-Dialog-Wurzel) nach dev gemergt (2026-06-20):**
  Rück-Merge `hotfix/v0.2.3-about-dialog-height` → `dev`. Echte Ursache des winzigen Dialogs:
  `dlg.resizable(False,False)` ließ den Windows-WM `geometry()`-Aufrufe ignorieren — unabhängig
  von `minsize`, Timing und `_ABOUT_MIN_H`. Fix: `dlg.resizable(True,True)` wie SetupWizard;
  die gesamte `_do_center`-Logik (`_ABOUT_MIN_H=520`, `ismapped`-Zentrierung, Tooltips) bleibt
  erhalten und greift nun wirklich. Neuer Diagnosetest `test_resizable_false_vs_true_geometry`
  belegt die Wurzelursache. `__version__=0.3.0`. Wird über v0.3.0-beta4 auf Win10 verifiziert;
  Stable v0.2.3 folgt separat über main. 1178 Tests grün. origin/dev = 6810013.
  Hotfix-Branch bleibt erhalten (für Stable v0.2.3).
- **v0.3.0-beta4 veröffentlicht (2026-06-20):** resizable(True,True)-Fix (echte Über-Dialog-
  Wurzel). Pre-Release; Asset `QSL73-Beta-Setup-v0.3.0.exe`; v0.2.2 bleibt Latest-Stable.
  Win10-Verifikation durch DF1DS ausstehend.
- **Über-Dialog-Fix vollständig nach dev gemergt; v0.2.3 Stable released + auf Win10 verifiziert (2026-06-20):**
  Rück-Merge `hotfix/v0.2.3-about-dialog-height` (660c3f1) → `dev` abgeschlossen. Enthält
  den vollständigen Über-Dialog-Fix (echte Wurzel: ttk/bg-cget `TclError` auf Win10/Tk 8.6
  bei `ttk.Frame` + `tk.Label bg=cget`; Fix: `ttk.Label` ohne `bg`-Argument, defensive
  Logo-Kapselung via try/except) sowie den Größen-Feinschliff (`_ABOUT_MIN_H` 520→480,
  damit der berechnete Wert 501 px bei Win10-scaling 1.33 greift). `resizable(True,True)` +
  `_do_center`-Logik + Tooltips (`attach_tooltip`) vollständig erhalten. `__version__=0.3.0`.
  v0.2.3 Stable auf DF1DS' Win10 verifiziert (Dialog vollständig korrekt). 1180 Tests grün.
  Hotfix-Branch `hotfix/v0.2.3-about-dialog-height` gelöscht (lokal + remote), da v0.2.3
  released und vollständig zurückgeführt.

#### Anleitung für DF1DS: Erstes Release v0.1.0 auslösen

1. Sicherstellen, dass `src/qsl73/__version__.py` `__version__ = "0.1.0"` enthält.
2. `dev` auf den aktuellen Stand bringen (`git pull`), Schritt abschließen.
3. `dev` in `main` mergen: `git checkout main && git merge dev && git push origin main`
4. Tag setzen und pushen: `git tag v0.1.0 && git push origin v0.1.0`
5. GitHub Actions startet automatisch `.github/workflows/release.yml`.
6. Nach erfolgreichem Lauf: `QSL73-Setup.exe` ist unter
   https://github.com/DF1DS/qsl73/releases als Asset verfügbar.
7. README-Feature-Doku (Menüleiste, Einstellungen, Durcharbeiten-Workflow, Audit-Log)
   als eigener Commit vor dem Release-Merge hinzufügen.

---

## Offene Punkte (laufend)

- Reale OCR-Qualität bei „gemischt" (gedruckt + handschriftlich) bestimmt den Anteil
  des manuellen Pfads im Alltag — empirisch bestätigt: handschriftliche und ältere Karten
  dominieren oft; manueller Pfad wird häufig genutzt.
- Bild-Auflösung für lesbare Handschrift (Preview vs. Original) — noch offen.
- ~~pyzbar/libzbar-64.dll auf Windows~~ — **entschärft durch zxingcpp (ADR-0017)**; kein
  nativer DLL-Ballast mehr. ~~`zxing-cpp` + `pywin32` im PyInstaller-Bundle einbetten~~
  — **erledigt in Schritt 9a (ADR-0040, Issue #6 geschlossen)**.

### ✅ Beta-Release v0.3.0-beta1 (erstes Beta-Release des Projekts)

- Tag `v0.3.0-beta1` gepusht → GitHub Actions Workflow grün (1m57s) →
  Pre-Release `v0.3.0-beta1` mit Asset `QSL73-Beta-Setup-v0.3.0.exe` und
  gefüllten Release-Notes veröffentlicht. `v0.2.1` bleibt weiterhin Stable/Latest.

### Beta-Release v0.3.0-beta2 (Über-Dialog-Höhen-Fix + erster Self-Update-Test)

- Enthält zusätzlich `_resolve_dialog_height` (Über-Dialog-Höhe aus innerem Frame +
  Mindesthöhe — Hotfix v0.2.3 bereits auf dev gemergt). Erster automatischer
  Self-Update-Test: laufende beta1 erkennt beta2 und bietet Update an.
- Tag `v0.3.0-beta2` gepusht → GitHub Actions Workflow grün (1m56s) →
  Pre-Release `v0.3.0-beta2` mit Asset `QSL73-Beta-Setup-v0.3.0.exe` und gefüllten
  Release-Notes (aus [Unreleased]) veröffentlicht. `v0.2.2` bleibt weiterhin Stable/Latest.

### Beta-Release v0.3.0-beta3 (Logo-robuster Über-Dialog-Fix — Win10-Verifikation ausstehend)

- Enthält verbesserten Über-Dialog-Fix: `_ABOUT_MIN_H=520`, `_ABOUT_MIN_W=360`,
  `_resolve_dialog_width`, `update_idletasks`, `ismapped`-Fallback (vollständiges
  SetupWizard-Muster). Rück-Merge `hotfix/v0.2.3-about-dialog-height` → `dev` war
  konfliktfrei (auto-aufgelöst); Tooltips bleiben vollständig erhalten.
- Tag `v0.3.0-beta3` gepusht → GitHub Actions Workflow grün (2m4s) →
  Pre-Release `v0.3.0-beta3` mit Asset `QSL73-Beta-Setup-v0.3.0.exe` und gefüllten
  Release-Notes (aus [Unreleased]) veröffentlicht. `v0.2.2` bleibt weiterhin Stable/Latest.
- **Win10-Verifikation durch DF1DS ausstehend:** Über-Dialog öffnet mit Logo vollständig
  sichtbar und mittig über dem Hauptfenster?

### ✅ Tooltips (Issue #15) — geplant für v0.3.0

- Flächendeckende Hover-Tooltips über alle Fenster (Haupt, Setup, manuelle Zuordnung,
  Update-Dialog, Fehlermelde-Dialog). Wiederverwendbare Infrastruktur `gui/tooltip.py`;
  Texte als `_TT_*`-Konstanten; Konvention in CLAUDE.md + ADR-0047. __version__ = 0.3.0.

### ✅ Performance-Verbesserung manueller Zuordnungs-Dialog (Issue #30, ADR-0051)

- `run_pass`: kein `get_document_download` mehr — evaluate_card nutzt nur OCR-Text.
  source ∈ {"ocr","none"}, nie "qr". Download-Zähler == 0 bei N Dokumenten (per Test).
- `manual_assignment.py`: _load_image dekodiert QR aus denselben PDF-Bytes wie das Kartenbild.
  `compute_qr_prefill` (rein, testbar) überschreibt Felder nur wenn Nutzer nicht getippt hat.
- `pdf_cache.py`: LRU-RAM-Cache (CACHE_MAX_MB=150 MB), Prefetch-Tiefe PREFETCH_DEPTH=4.
  Keine Temp-Dateien. Daemon-Threads, stoppbar via stop(). MainWindow-Lebensdauer.
- ADR-0051 angelegt; KONZEPT.md §6 präzisiert; Issue #30 geschlossen.

## V2 — Vorgemerkte Features

- **Mehrsprachigkeit (i18n) — Issue #25 (ADR-0038):** i18n-Infrastruktur einführen
  (gettext o. ä.), alle nutzersichtbaren Texte extrahieren (Modul-Konstanten bereits
  angelegt), englische Übersetzung, Sprachumschaltung im Einstellungen-Dialog reaktivieren.
  `app.language` (Default `de`) bleibt im Config-Modell reserviert.
- **Attention-Handler** (Blinken/Ton bei Klick ins gesperrte Fenster) — bewusst auf V2
  verschoben; aktuelle Implementierung entfernt (kein FocusIn/FocusOut, kein Parent-Binding
  mehr nach Klärung).
