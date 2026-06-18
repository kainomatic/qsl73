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

## 🔧 Schritt 6 — GUI — IN ARBEIT

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

### ➡️ Schritt 6c — Manueller Zuordnungs-Bildschirm (offen)

- Karten-Bild (Vorder-/Rückseite) erst beim Anklicken einer UNCERTAIN-Karte nachladen.
- Eingabefelder mit OCR-Vorschlag vorbefüllt; **Live-Suche während des Tippens** gegen
  die Log4OM-DB (passende QSOs nach Rufzeichen/Datum/Band/Mode als Vorschläge).
- Manuelle Zuordnung → QSO markieren + Tag `qsl-bestätigt` (wie Auto-Match).
- Zuordnung fließt in denselben Korb wie Auto-Treffer → gemeinsame Transaktion (§5/§7).
- **Review:** Akzeptanzkriterien §9; Live-Suche bei gültigem Rufzeichen; pytest grün, CI grün.

## 🔧 Schritt 7 — Logging & Fehler-Reporting — IN ARBEIT

### ✅ Schritt 7a — Diagnose-Logging + QR-Startwarnung (Issue #14)

- `logging_setup.py`: `setup_logging()` mit RotatingFileHandler auf
  `%APPDATA%\QSL73\logs\qsl73.log` (1 MB / 5 Backups, Stable/Beta-getrennt). ADR-0026.
- `QSL73_DEBUG=1` hebt Level auf DEBUG → Token-Scan-Ausgaben in `run.py` sichtbar.
- Log-Punkte in `run.py`: Lauf-Start/Ende, pro Karte Quelle+Ergebnis (INFO);
  Fallback-auf-OCR, per-QSO-Route (DEBUG); Schreibvorgang (INFO).
- `qr_backend_status()` in `qr.py`; fehlende QR-Libs → WARNING im Log + GUI-Hinweis.
- 16 neue Tests; pytest grün, CI grün.
- **Review:** Logdatei entsteht beim Start; kein Secret im Log; QR-Warnung sichtbar.

### ➡️ Schritt 7b — Audit-Log + Fehler-Reporting (offen)

- `audit.log`: fachliche Änderungen (Zeitstempel, Dok-ID, QSO-Rufzeichen/Datum/Band/Mode,
  auto vs. manuell, Backup ja/nein).
- On-demand-Bericht: „Auf GitHub melden" (vorausgefülltes Issue) + „Lokal speichern",
  Bericht bereinigt (keine Secrets/QSO-Inhalte; Nutzer sieht ihn vor Versand).
- „Log-Ordner öffnen"-Button in §9-GUI (nutzt `get_log_dir()` aus 7a).
- **Review:** Akzeptanzkriterien §10; Bericht ohne Secrets nachgewiesen; pytest grün, CI grün.

## Schritt 8 — Update-Lifecycle + Installer/Deinstaller

- GitHub-Releases-Check, Updater, Inno-Installer (still, aufräumend), Deinstaller mit
  Nutzerdaten-Abfrage, Config-Migration scharf schalten.
- **Beta-Kanal:** kanalabhängige Update-Prüfung — Stable prüft gegen main-Releases;
  Beta prüft nur gegen explizit getaggte GitHub-Pre-Releases (→ ADR-0021).
- **Review:** Akzeptanzkriterien §12/§13; pytest grün, CI grün.

## Schritt 9 — Build, Test, erstes Release

- PyInstaller-Build (64-Bit), Inno-Setup-Paket, Test auf Win10/11. Versionspflege +
  CHANGELOG, Tag `v0.x.0`, GitHub-Release. Logo/Icon final (Freistellen + .ico durch
  Claude Code).
- **Python 3.12** als Referenzversion für Build und Bundle (ADR-0024; Issue #16).
- **Beta-Kanal:** zweiter Installer (`QSL73-Beta-Setup.exe`) mit eigenem Installationspfad
  (`C:\Program Files\QSL73 Beta`), eigenem APPDATA-Verzeichnis (`%APPDATA%\QSL73-Beta\`),
  BETA-Kennzeichnung in Fenstertitel und „Über"-Dialog, DB-Pfad-Hinweis im Setup-Assistent
  (→ ADR-0021; Packaging-Grundlage Issue #6 unberührt).
- **Review:** Lauf Ende-zu-Ende (Vorschau → „Jetzt schreiben") auf echtem System;
  Release konsistent.

---

## Offene Punkte (laufend)

- Reale OCR-Qualität bei „gemischt" (gedruckt + handschriftlich) bestimmt den Anteil
  des manuellen Pfads im Alltag — empirisch bestätigt: handschriftliche und ältere Karten
  dominieren oft; manueller Pfad wird häufig genutzt.
- Bild-Auflösung für lesbare Handschrift (Preview vs. Original) — noch offen.
- ~~pyzbar/libzbar-64.dll auf Windows~~ — **entschärft durch zxingcpp (ADR-0017)**; kein
  nativer DLL-Ballast mehr. Offen bleibt: `zxing-cpp` + `pywin32` im PyInstaller-Bundle
  einbetten (Issue #6, Schritt 9, ADR-0024).
