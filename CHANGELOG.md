# Changelog

Alle nennenswerten Änderungen an QSL73 werden in dieser Datei dokumentiert.

Das Format basiert auf [Keep a Changelog](https://keepachangelog.com/de/1.0.0/),
das Projekt folgt [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.3.0] - 2026-06-22

### Added

- **Hover-Tooltips (Issue #15, ADR-0047):** Flächendeckende, einheitliche Tooltips in allen
  Fenstern (Hauptfenster, Setup/Einstellungen, manueller Zuordnungs-Dialog, Update-Dialog,
  Fehlermelde-Dialog). Neue wiederverwendbare Infrastruktur `gui/tooltip.py` mit
  `attach_tooltip(widget, text)` — 500 ms Verzögerung, crash-sicher, Bildschirmrand-Clamp.
  Alle Tooltip-Texte als `_TT_*`-Modulkonstanten (i18n-Vorbereitung). Keine Fragezeichen-
  Icons. Konvention für künftige Fenster in CLAUDE.md und ADR-0047 verankert.

## [0.2.3] - 2026-06-20

### Fixed

- **Über-Dialog öffnet vollständig (Logo + Texte + Buttons) und korrekt dimensioniert (Hotfix — echte Wurzel via Diagnose-Skript auf Win10):**
  Der Dialog blieb auf Win10 leer und winzig. Diagnose-Skript `tools/diag_about_dialog.py` auf
  DF1DS' Win10 ergab: Die Zeile
  `tk.Label(frame, image=logo_photo, bg=frame.cget("background"))` wirft auf Win10/Tk 8.6 einen
  `_tkinter.TclError: unknown option "-background"`, weil `frame` ein `ttk.Frame` ist
  (`ttk`-Widgets kennen keine `-background`-Option). Die Exception bricht den Dialog-Aufbau
  **unmittelbar nach dem Logo** ab — Titel, Beschreibung, Lizenz, Autor, Links und Schließen-Button
  werden nie erzeugt, der Dialog bleibt leer. Auf Windows-Server-2025 (CC-Umgebung) trat der Fehler
  theme-/versionsbedingt nicht auf, daher nie reproduziert.
  **Fix:** Logo-Label auf `ttk.Label(frame, image=logo_photo)` umgestellt — `ttk.Label` übernimmt
  den Theme-Hintergrund automatisch, kein `bg`/`cget` nötig. Zusätzlich defensiv gekapselt
  (try/except um den Logo-Block): ein Logo-Fehler kann den Restdialog nicht mehr leeren.
  Die `_do_center`-Logik (`resizable(True,True)`, Bildschirm-Deckel 90 %, `ismapped`-Zentrierung)
  bleibt vollständig erhalten und greift nun auch wirklich. Neuer Regressionstest
  (`test_about_dialog_builds_completely_not_empty`) prüft, dass der Dialog nach dem Aufbau
  vollständig ist; `test_ttk_frame_logo_label_no_cget_crash` sichert ab, dass `ttk.Label` auf
  `ttk.Frame` ohne Exception durchläuft. `tools/diag_about_dialog.py` ebenfalls korrigiert
  (selbe Zeile, damit das Skript für Folge-Diagnosen nutzbar bleibt).

- **Über-Dialog Dialoghöhe enger am Inhalt (Größen-Feinschliff):**
  Auf DF1DS' Win10 (tk-scaling 1.33) ergab das Diagnose-Skript `frame.winfo_reqheight()≈411 px`.
  Mit `chrome=90` ergibt sich `needed_h=501 px`; die alte `_ABOUT_MIN_H=520` überschrieb diesen
  berechneten Wert und erzwang unnötige 19 px Leerraum am unteren Rand.
  **Fix:** `_ABOUT_MIN_H` von 520 auf 480 gesenkt — fungiert jetzt als reines Sicherheitsnetz für
  Timing-Artefakte (reqH≈1 px) und Logo-lose Frühmsesungen (reqH≈285 → needed_h=375 < 480).
  Im Normalfall gewinnt der berechnete Wert (501 px > 480), der Dialog sitzt enger am Inhalt.
  Ein kleiner Puffer gegen DPI- und Fontvarianz bleibt erhalten. `_ABOUT_MIN_W=360` unverändert.

## [0.2.2] - 2026-06-19

### Fixed

- **Über-Dialog öffnet korrekt zentriert und in richtiger Größe:** Die Größen- und
  Positionsberechnung wurde zuvor synchron direkt nach dem Widget-Aufbau ausgeführt —
  vor dem ersten Mapping des Fensters. `winfo_reqwidth()`/`winfo_reqheight()` liefern
  in diesem Moment Mini-Werte (0 oder 1), was zu einem winzig kleinen, oben links
  positionierten Dialog führte. Fix: Geometrie-Berechnung via `dlg.after(1, ...)` auf
  nach das erste Mapping verschoben (analoges Muster wie `SetupWizard._adjust_window_size`).
  Neue tk-freie Hilfsfunktion `_compute_dialog_geometry` ausgelagert (testbar ohne Display).

## [0.2.1] - 2026-06-19

### Changed

- **Installer-Dateiname versioniert (ab v0.2.1):** Installer-Assets enthalten jetzt die
  Versionsnummer im Dateinamen: `QSL73-Setup-v<VERSION>.exe` (Stable) und
  `QSL73-Beta-Setup-v<VERSION>.exe` (Beta). Beide `.iss`-Dateien, `release.yml` und
  `tools/build_installer.ps1` konsistent angepasst. Beta-Assets tragen die Ziel-Stable-Basis-
  Nummer (kein `-betaN`-Suffix, da die `.iss` nur `APP_VERSION` kennt).
- **Updater: Asset-Erkennung per Muster** (ADR-0045 §13): `_pick_asset` vergleicht nicht
  mehr exakt, sondern per Regex — erkennt altes (`QSL73-Setup.exe`) UND neues
  (`QSL73-Setup-vX.Y.Z.exe`) Schema. Stable-Muster schließt Beta-Assets explizit aus.
  Rückwärtskompatibel zu bestehenden Releases.
- **Prozess (CLAUDE.md):** Feature-Ideen, Aufgaben und Bugs müssen als GitHub Issue
  abgelegt werden — kein flüchtiger Chat-Sammeltopf. Claude Desktop legt Issues immer
  per CC-Auftrag an (kein eigener Schreibzugriff). Rollenmodell-Zeile Desktop entsprechend
  geschärft.
- **AENDERUNGEN.html:** `[Unreleased]`-Abschnitt wird beim Erzeugen der Nutzer-HTML
  vollständig ausgelassen (leer oder gefüllt); Änderungshistorie beginnt jetzt mit der
  neuesten veröffentlichten Version.

### Fixed

- **Release-Notes-Extraktion (release.yml):** Regex-Lookahead `(?=\r?\n## \[)` schlug fehl
  wenn der extrahierte CHANGELOG-Abschnitt der letzte in der Datei war (kein nachfolgendes
  `## [`-Heading). Alle drei Muster (Stable, Beta, Fallback) auf
  `(?=\r?\n## \[|\z)` erweitert; zusätzlich `\s*\r?\n` → `[^\r\n]*\r?\n` korrigiert
  (verhinderte korrektes Match-Positioning bei leerem `[Unreleased]`). Ursache des leeren
  GitHub-Release-Notes-Texts bei v0.2.0.

## [0.2.0] - 2026-06-19

### Added

- **Self-Update (Schritt 8, ADR-0045):** QSL73 prüft beim Start automatisch auf neue
  Versionen (wenn `app.update_check = true`). Stable-Kanal prüft gegen normale
  GitHub-Releases, Beta-Kanal gegen Pre-Releases. Bei verfügbarem Update erscheint ein
  modaler Dialog mit aktueller und neuer Versionsnummer sowie Link zu den Release-Notes.
  „Herunterladen und installieren" lädt das passende Setup-Asset nach `%TEMP%`, verifiziert
  die Dateigröße, startet den Installer im `/SILENT`-Modus (Fortschritts­fenster sichtbar,
  kein Klick-durch) und beendet QSL73 sauber. Der Installer startet QSL73 nach dem Update
  automatisch neu. „Später" schließt den Dialog; ein Hinweis-Eintrag im Menü Hilfe bleibt
  sichtbar. „Nicht mehr erinnern" setzt `update_check = false` dauerhaft. Hilfe →
  „Nach Updates suchen" stößt die Prüfung jederzeit manuell an (unabhängig von
  `update_check`). Modul `updater.py` tk-frei + umfassend getestet (GitHub-API gemockt).
  Inno-Setup: `CloseApplications=yes` + `AppMutex` (kanalspezifisch: `QSL73-Stable` /
  `QSL73-Beta`) + `RestartApplications=no`. Self-Update-Neustart via Custom-Flag
  `/RESTARTQSL73` in der Installer-Kommandozeile: `postinstall`-Checkbox mit `skipifsilent`
  (interaktiv) und separater `[Run]`-Eintrag mit `Check: ShouldRestartApp` (Self-Update)
  trennen beide Pfade sauber. Windows-AppMutex in `gui/app.py` via pywin32 (non-fatal),
  koexistiert mit PID-Lockfile.

- **Liesmich und Änderungshistorie über Hilfe-Menü:** `README.md` und `CHANGELOG.md`
  werden beim Build in offline-fähige HTML-Dateien (`LIESMICH.html`, `AENDERUNGEN.html`)
  konvertiert (`tools/make_docs_html.py`) und mit dem Installer nach `{app}` kopiert. In
  der installierten App sind sie über **Hilfe → Liesmich anzeigen** bzw. **Hilfe → Was ist
  neu (Änderungen)…** direkt im Standardbrowser aufrufbar. Im Dev-Lauf (ohne Build) öffnet
  sich stattdessen die jeweilige GitHub-Seite als Fallback. Am Setup-Abschluss-Bildschirm
  stehen wie bisher zwei optionale, standardmäßig nicht angehakte Checkboxen. Die HTML-
  Dateien erscheinen **nicht** mehr als separate Startmenü-Einträge.

- **Beta-Start-Hinweis-Dialog (ADR-0021):** Beim Start mit `CHANNEL="beta"` erscheint
  ein modaler, tonloser Hinweis-Dialog (eigenes Toplevel, kein Systemton) mit Vorabversions-
  Warnung, Empfehlung zur Log4OM-DB-Kopie, Verweis auf „Hilfe → Fehler melden" und
  Bestätigung, dass das Sicherheitsnetz (Backup/Vorschau) aktiv bleibt. Mit `CHANNEL="stable"`
  kein Hinweis; Stable-Start unverändert. Dialog zeigt sich bei jedem Beta-Start (kein
  „Nicht mehr anzeigen"-Flag — bewusst schlicht gehalten). Modul `gui/beta_notice.py`.
- **SmartScreen-Hinweis in README (ADR-0044):** Knapper, sachlicher Hinweis im
  Nutzer-Installationsteil erklärt, dass Windows beim nicht-signierten Installer eine
  „Unbekannter Herausgeber"-Warnung zeigt, und beschreibt den Weg durch: „Weitere
  Informationen" → „Trotzdem ausführen". Gilt für Stable und Beta.
- **ADR-0044:** Entscheidung gegen Code-Signing-Zertifikat festgehalten — unverhältnismäßige
  Kosten für ein GPLv3-Hobbyprojekt; Zielgruppe technikaffin; Quellcode öffentlich einsehbar.
  Neubewertung möglich falls Projekt wächst.
- **Versionierungs-Richtlinie (ADR-0043):** Verbindliche SemVer-Regel für QSL73: MAJOR
  bei Config-Schema-Bruch oder Log4OM-Schreibformat-Inkompatibilität; MINOR für neue
  Funktionen; PATCH für Bugfixes. Pre-1.0-Ausnahme (Breaking Changes in MINOR solange
  MAJOR=0) und Übergang zu 1.0.0 dokumentiert. Versionsregel-Abschnitt in CLAUDE.md
  ergänzt (nachschlagbar bei jedem Release).
- **Beta-Installer-Variante (ADR-0042):** `installer/qsl73-beta.iss` — separate Inno-Setup-
  Konfiguration für die Beta-Variante; eigene AppId-GUID `{A3F5C8D2-7E4B-4A91-B5C6-2D8E9F3A1B07}`;
  Installationspfad `C:\Program Files\QSL73 Beta`; Nutzerdaten in `%APPDATA%\QSL73-Beta\`;
  Ausgabedatei `QSL73-Beta-Setup.exe`. Stable und Beta sind dauerhaft parallel installierbar
  (ADR-0021).
- **GitHub-Actions-Release-Workflow (ADR-0042):** `.github/workflows/release.yml` baut bei
  Push eines Versions-Tags (`vX.Y.Z` → Stable-Release, `vX.Y.Z-betaN` → Beta-Pre-Release)
  automatisch den PyInstaller-Bundle und den passenden Installer auf `windows-latest`
  (Python 3.12, ADR-0024) und lädt die Setup-Datei als GitHub-Release-Asset hoch.
- **Versions-Sync-Prüfung im Release-Workflow (ADR-0042):** Der Workflow bricht mit
  Fehlermeldung ab, wenn der Git-Tag nicht mit `__version__` in `__version__.py` übereinstimmt.
  `AppVersion` in den .iss-Dateien wird per `/DAPP_VERSION=x.y.z` vom Workflow injiziert —
  einzige Versionsquelle ist `__version__.py`.

- **Inno-Setup-Installer Stable (Schritt 9b, ADR-0041):** `QSL73-Setup.exe`; installiert nach
  `C:\Program Files\QSL73` (64-Bit); GPLv3-Lizenzseite; Startmenü + optionale Desktop-
  Verknüpfung; Deinstaller fragt nach `%APPDATA%\QSL73` (Default NEIN).

- **PyInstaller-Build (Schritt 9a, ADR-0040):** onedir Windows-.exe; alle Abhängigkeiten
  gebündelt (zxingcpp als Einzel-.pyd manuell, pymupdf+fitz via collect_all, tkcalendar+
  babel via collect_all, pywin32 via collect_all+hiddenimports). Verifikation auf
  Windows Server 2025: Start, QR, DPAPI, Datepicker — alle grün.
- **Windows-Icon (Issue #5):** `assets/qsl73.ico` (16 / 32 / 48 / 256 px) aus
  `assets/qsl73logo.png`; erzeugt von `tools/make_icon.py`.
- **Build-Dokumentation:** `docs/BUILD.md` (kopierbare Bau-Anleitung mit Fallstricken),
  `tools/build.ps1` (PS-Hilfsskript für lokale Build-Wiederholung).

- **Durcharbeiten-Workflow für manuelle Zuordnung (ADR-0037):** Doppelklick auf
  UNCERTAIN/NO_MATCH-Karten öffnet jetzt den Dialog mit Workflow-Kontext. Neue Buttons
  „Speichern und nächste" + „Nächste" springen automatisch zur nächsten Karte; Phasen-
  übergang UNCERTAIN → NO_MATCH wird per Ja/Nein-Dialog abgefragt. Letzte Karte in der
  Phase deaktiviert die Weiter-Buttons automatisch.
- **Statusanzeige im Zuordnungs-Dialog:** Farbige Phase-Beschriftung (Unsicher/Kein Treffer)
  + Fortschritt „Karte X von Y" oben im Dialog sichtbar.
- **Über-Dialog ohne Systemsound (ADR-0037):** Custom `tk.Toplevel` statt
  `messagebox.showinfo` — kein Windows-Klingeln beim Öffnen. Dialog enthält klickbare
  Links zu GitHub und QRZ.com sowie Paperless-ngx-Beschreibung.

- **Menüleiste mit Einstellungen-Dialog (ADR-0036, Fixes #24):** Standard-Menüleiste
  Datei / Bearbeiten / Hilfe im Hauptfenster.
  - Bearbeiten → „Einstellungen…": öffnet den SetupWizard im Bearbeiten-Modus — alle
    Config-Felder (URL, Auth, DB-Pfad, Rufzeichen, Tags, Matching, Route, Sprache,
    Backup-Anzahl, Update-Check, Trefferlimit) vorbefüllt mit aktuellen Werten.
    Token-Feld bleibt leer (§4: kein Klartext); leer lassen = bestehendes Token behalten.
  - Hilfe → „Log-Ordner öffnen" / „Fehler melden…" (bisher Statusleisten-Buttons, ADR-0036)
    / „Über QSL73" (Version, Channel, GPLv3-Lizenz, Repo-Link).
  - Datei → „Beenden".
  - `wizard_logic.py`: `config_to_field_defaults`, `is_token_retain_valid`,
    `merge_wizard_overrides` — tk-freie Logik für Config → Feld-Vorbelegung und
    Token-Erhalt-Regel im Bearbeiten-Modus.

- Audit-Log (`audit.log`, getrennt von `qsl73.log`): fachliches Änderungsprotokoll
  aller tatsächlich geschriebenen QSO-Bestätigungen (Zeitstempel, Rufzeichen, Band,
  Mode, Route, Quelle auto/manuell, Backup-Pfad). Dauerhaft, nicht rotierend (ADR-0035).
- On-demand-Fehlerbericht: „Fehler melden…" im Hilfe-Menü öffnet Dialog mit bereinigter
  Bericht-Vorschau (keine Secrets, keine QSO-Daten); Buttons „Lokal speichern" und
  „Auf GitHub melden" (vorausgefüllte Issue-URL, kein Auto-Send).
- „Log-Ordner öffnen" im Hilfe-Menü öffnet `%APPDATA%\QSL73\logs\`.
- `WriteResult.backup_path`: Schreibergebnis enthält Pfad zur erstellten Backup-Datei.
- `write_selected` um `manual_qsoids` und `candidates` erweitert (abwärtskompatibel).

- **main-Branch auf aktuellen dev-Stand gebracht (ADR-0034):** Kein Release — reine
  Branch-Synchronisation per Fast-Forward, um die öffentlich sichtbare GPLv3-Lizenz und
  den aktuellen Codestand auf main herzustellen.

- **Schritt 7b-1 — Config-Robustheit: Backups + robuster Start-Check (ADR-0033):**
  `config_backup.py` mit rotierenden Sicherungen von `config.yaml` vor jedem
  Überschreiben (`%APPDATA%\QSL73\config_backups\`, Default 5 Backups, kein Klartext-Token).
  Start-Check in `gui/app.py` fängt `ConfigError` getrennt von `SetupNeeded` ab:
  zeigt Fehlerdialog mit konkreter Meldung + Auswegangeboten (Einrichtung neu starten /
  Frühere Sicherung wiederherstellen / Beenden). Backup-Auswahl nur aktiv wenn Sicherungen
  vorhanden. Reine Logik (Backup-Pfade, Rotation, Restore+Validierung) tk-frei + getestet.

- **Schritt 6e — Bestätigte Karten serverseitig ausfiltern (ADR-0032):**
  `get_documents_by_tag` akzeptiert `exclude_tag_name`; `run_pass` übergibt
  `config.tags.confirmed` als Ausschluss, damit bereits bestätigte Karten im
  zweiten Durchlauf nicht mehr als „Kein Treffer" erscheinen.

- **Schritt 6 UX-3 — Geschriebene Karten sichtbar markieren + Trefferlimit (ADR-0030):**
  - **Teil A — Bestätigt-Markierung im Hauptfenster:** Nach „Jetzt schreiben" erhalten
    bestätigte Karten das Status-Label „Bestätigt ✓", grüne Tag-Farbe (`written`) und
    werden an das Ende der Liste sortiert (`sort_cards_written_last`). Klick und Doppelklick
    auf geschriebene Karten sind no-op (verhindert Doppel-Schreiben). Markierung gilt nur
    für den laufenden Lauf — beim nächsten „Durchlauf starten" wird `_written` geleert.
    `WriteDoneEvent` trägt jetzt `confirmed_doc_ids`, damit das GUI die IDs kennt.
  - **Teil B — Trefferlimit für manuellen Zuordnungs-Dialog (ADR-0030):** Config-Feld
    `app.manual_match_limit` (Default 100; 0 = kein Limit) persistent in `config.yaml`.
    Migration: fehlendes Feld → 100 (kein Versions-Bump). Dialog begrenzt Treeview-Inhalt
    und zeigt `(zeige N von M)` im LabelFrame-Titel bei Begrenzung.
    Einstellbar im Setup-Assistenten (Einstellungen) per editierbarer Combobox
    10 / 100 / 1000 / 0 (kein Limit).
  - Reine Funktionen ausgelagert + getestet: `sort_cards_written_last`, `apply_display_limit`;
    Config: `manual_match_limit` Default/Validierung/Round-trip/Migrate-Tests.
    779 passed gesamt.

- **Schritt 6c-UX-2 — Weitere UX-Verbesserungen am manuellen Zuordnungs-Dialog:**
  - **Datepicker-Grab-Fix:** DateEntry-Kalender-Popup konfliktierte mit `grab_set()` des
    modalen Dialogs (Klick durchschlug auf Band/Mode-Feld darunter). Fix: `<Map>`/`<Unmap>`-
    Bindings auf tkcalendars `_top_cal`-Popup geben den Grab beim Öffnen frei und setzen
    ihn nach dem Schließen neu. Robust (try/except wenn tkcalendar-API fehlt).
  - **Wrap-around-Blättern:** `◀`/`▶` laufen jetzt um — letzte Seite → erste, erste →
    letzte. Bei nur einer Seite: Buttons deaktiviert, kein Absturz. Reine Hilfsfunktion
    `wrap_page_index(current, page_count, direction)` ausgelagert und getestet.
  - **Bild-Zoom per Klick:** Klick auf das Kartenbild öffnet ein eigenes Toplevel-Fenster
    mit der Seite in 150-DPI-Originalgröße (ohne `thumbnail`-Downscale). Größenbegrenzung
    auf 90% des Bildschirm-Arbeitsbereichs. Erneuter Klick (oder Escape) schließt das
    Fenster. Kein Bild vorhanden → no-op.
  - **QSO-Werte in Treeview bei manueller Zuordnung:** Manuell zugeordnete Karten zeigen
    jetzt Rufzeichen/Datum/Band/Mode des zugeordneten QSO (aus `RunResult.candidates`)
    statt der Kartenfelder (`–`). Hilfsfunktion `qso_by_id(candidates, qsoid)` in
    `filter_util.py` ausgelagert. qsoid nicht auffindbar → Fallback auf bisheriges
    Verhalten, kein Absturz.
  - Tests: +8 `wrap_page_index`-Tests (test_manual_assignment.py), +5 `qso_by_id`-Tests
    (test_filter_util.py); gesamt 763 passed.

- **Schritt 6d — Tag-Verwaltung im Setup + Verbindungstest (ADR-0031):**
  - **Paperless-Verbindungstest im Setup-Assistenten:** „Verbindung testen"-Button prüft URL +
    Zugangsdaten (Token oder User/PW); zeigt Ergebnis + Tag-Anzahl an. Erst nach erfolgreichem
    Test sind Tag-Dropdowns und „Anlegen"-Buttons aktiv.
  - **Tag-Felder als Dropdowns aus Paperless:** Die drei Schreib-Tag-Felder (input, confirmed,
    uncertain) werden von Freitext-Entries auf Dropdowns umgestellt, befüllt durch `list_tags()`
    nach Verbindungstest. Tippfehler ausgeschlossen.
  - **Tag anlegen mit Duplikat-Schutz:** Pro Tag-Feld gibt es ein Eingabefeld + „Anlegen"-Button.
    `create_tag(name, matching_algorithm=0)` legt den Tag ohne Auto-Matching an;
    Duplikat-Schutz via case-insensitivem `get_tag_id`-Check vor dem POST.
  - **Auto-Matching-Warnung für Schreib-Tags:** Ist der ausgewählte confirmed/uncertain-Tag mit
    `matching_algorithm != 0` (Auto-Matching), erscheint eine sichtbare Warnung im Wizard.
    Der input-Tag ist ausgenommen — für ihn ist Matching unbedenklich.
  - **Sichtbare Tag-Warnung beim Schreiben:** `write_selected()` gibt nun
    `tuple[WriteResult, list[str]]` zurück; fehlende Tags beim Schreiben führen zu einer
    Warnung im Abschluss-Dialog + Statuszeile (statt stilles Verschlucken). ADR-0031.
  - `paperless.py`: `list_tags()`, `create_tag()` mit `matching_algorithm=0` Default.
  - `wizard_logic.py`: tk-freie Test-Logik (Verbindungstest-Auswertung, Warnung, Validierung).
  - Tests: +XX in test_paperless.py (list_tags, create_tag); +XX in test_wizard_logic.py;
    pytest all grün.

- **Schritt 6c-UX — Drei UX-Verbesserungen im manuellen Zuordnungs-Dialog (ADR-0029):**
  - **Rückseite zuerst + Blättern (Issue #20 → geschlossen):** `render_pdf_pages()` rendert alle
    PDF-Seiten (150 DPI statt 100 — Issue #19 → geschlossen). Dialog zeigt standardmäßig die
    letzte Seite (Rückseite); Blättern per `◀`/`▶`-Buttons. `render_pdf_first_page` bleibt als
    Abwärtskompatibilitäts-Wrapper.
  - **Band/Mode als Combobox (editierbar):** `distinct_bands()` und `distinct_modes()` leiten
    Vorschlagswerte aus `RunResult.candidates` ab (nur tatsächlich vorkommende Werte, sortiert).
    Tippen weiterhin möglich (state="normal").
  - **Datum per tkcalendar DateEntry:** Kalender-Picker mit Fallback auf Textfeld wenn
    `tkcalendar` fehlt (WARNING + kein Absturz). DateEntry-Wert filtert nur wenn Nutzer oder
    OCR-Vorbefüllung ein Datum explizit gesetzt hat (`_date_explicit`-Flag).
  - `last_page_index(page_count) → int` als reine, testbare Hilfsfunktion.
  - `requirements.txt`: `tkcalendar>=1.6` ergänzt (beim PyInstaller-Bundle Schritt 9 beachten).
  - `tests/gui/test_manual_assignment.py`: +17 Tests (distinct_bands/modes, render_pdf_pages,
    last_page_index); gesamt 38 Tests.
  - ADR-0029 angelegt; README-ADR-Index auf ADR-0030.

- **Schritt 6c-3 — Integration ins Hauptfenster (Schritt 6 komplett, KONZEPT §9):**
  - `src/qsl73/gui/main_window.py`: `<Double-1>`-Handler für UNCERTAIN/NO_MATCH-Karten öffnet
    `ManualAssignmentDialog`; Ergebnis in `_manual_pending` vorgemerkt; Karte lila hervorgehoben
    und als „Manuell zugeordnet" gekennzeichnet; erneuter Doppelklick ändert/hebt auf.
    `_on_write()` führt Auto + manuell zusammen (eine Transaktion); Bestätigung zeigt
    „X auto + Y manuell = Z Karten"; nach Schreiben alles geleert.
  - `src/qsl73/gui/filter_util.py`: `merge_selections()` — dedup by qsoid, Auto hat Vorrang.
  - `src/qsl73/run.py`: `RunResult.candidates` — offene QSO-Kandidaten exponiert (Feld mit
    Default `[]`; bestehende Tests unberührt).
  - `tests/gui/test_filter_util.py`: 7 neue Tests für `merge_selections()`.
  - Offene Punkte als Issues: #19 (Bild-DPI handschriftliche Karten), #20 (Rückseite anzeigen).
  - ADR: keiner nötig (Schreibmodell in KONZEPT §5/§7 + ADR-0028).

- **Schritt 6c-2 — Manueller Zuordnungs-Dialog (`src/qsl73/gui/manual_assignment.py`):**
  Modales `ManualAssignmentDialog`-Toplevel für UNCERTAIN-Karten.
  - `card_fields_to_query`: befüllt `ManualQuery` aus OCR/QR-`CardFields` (call_from → Suche).
  - `field_values_to_query`: Eingabefeld-Strings → `ManualQuery` (leer → None).
  - `render_pdf_first_page`: PDF-Bytes → PIL-Image (100 DPI); None bei Fehler/fehlender Lib.
  - Dialog: lazy Bildladen (50 ms nach Öffnen), OCR-Vorbefüllung der Suchfelder,
    Live-Suche via `search_candidates`, Treeview-Auswahl, `make_manual_selection` → `result`;
    modal (grab_set/wait_window); injizierbarer `image_loader` für Testbarkeit.
  - Bildladefehler → Platzhaltertext, kein Absturz.
  - `tests/gui/test_manual_assignment.py`: 21 Tests (17 rein + 4 tk); CI überspringt tk-Tests.

- **Schritt 6c-1 — Manuelle Zuordnungs-Logik (`src/qsl73/gui/manual_match.py`, ADR-0028):**
  tk-freies, rein funktionales Modul für den manuellen Zuordnungs-Bildschirm (Schritt 6c).
  - `ManualQuery`-Dataclass: optionale Suchfelder call/date/band/mode (Nutzereingabe / OCR-Vorschlag).
  - `search_candidates(query, candidates)`: filtert + rankt Kandidatenliste in-memory
    (Rufzeichen case-insensitiv Teilstring/Präfix; Datum/Band/Mode normalisiert-verglichen;
    leerer query → alle; Ranking nach Anzahl exakt passender Felder).
  - `make_manual_selection(qsoid, route)`: erzeugt `(qsoid, route)`-Eintrag für Schreib-Korb —
    kein separater Schreibpfad, 5c-Schutz bleibt voll aktiv (ADR-0028).
  - Suchraum ausschließlich auf übergebene offene Kandidatenmenge beschränkt (niemals R='Yes').
  - `tests/gui/test_manual_match.py`: Such-/Filter-/Ranking-/Validierungsfälle; CI-kompatibel.

- **Schreibtest end-to-end vollständig verifiziert (Issue #8 Szenario B, geschlossen):**
  Kompletter Kreislauf Paperless → QR/OCR → Match → schreiben → Anzeige in Log4OM bestätigt.
  Schreibformat byte-identisch zu Log4OM-eigenem Format (Vergleich DN9XX vs. OE6XXX-QSO).
  Log4OM zeigt nach Neustart korrekt „Qsl Received = Yes" für alle 3 bestätigten QSOs.
  Byte-genau: R `No`→`Yes` bei exakt 3 Treffern; RV-Feld bei `route=undefined` entfernt;
  S/CT/SV/EQSL-Eintrag unberührt; 3 von 467 QSOs geändert, Rest unberührt.
  ADR-0013 real bestätigt: DL0AAA-Karten erkannt trotz `own_callsign=DF1DS`.
  DatabaseChangedError und Vor-Schreib-Backup real bestätigt (ADR-0008/ADR-0020).
  Workflow-Befund (→ ADR-0008, KONZEPT.md §7): Log4OM muss nach QSL73-Schreibvorgang
  **neugestartet** werden — externes Neu-Laden reicht nicht.
  Details: `docs/realtest-befunde-2026-06-17.md`.

- **Diagnose-Logging + QR-Startwarnung (Issue #14, ADR-0026, Schritt 7a):**
  - `src/qsl73/logging_setup.py`: neues Modul mit `setup_logging()` (RotatingFileHandler auf
    `%APPDATA%\QSL73\logs\qsl73.log`, 1 MB / 5 Backups, idempotent) und `get_log_dir()`
    (Stable/Beta-getrennt, dient als Mechanismus für „Log-Ordner öffnen"-Button §9)
  - Level INFO default; `QSL73_DEBUG=1` (Umgebungsvariable) oder `debug=True`-Parameter
    hebt auf DEBUG an — dann erscheinen auch die bestehenden Token-Scan-Ausgaben aus `run.py`
  - `setup_logging()` wird in `gui/app.py::run_app()` als erste Aktion aufgerufen (vor
    Single-Instance-Lock und Config-Laden)
  - **Log-Punkte in `run.py`** (INFO): Lauf-Start/Ende mit Mengenangaben, pro Karte
    Quelle + Ergebnis (`doc_id=%d quelle=%s ergebnis=%s`), Schreib-Start + Abschluss;
    (DEBUG): Fallback auf OCR wenn QR None liefert, per-QSO `qsoid`/`route` bei Schreiben
  - **`qr_backend_status()`** in `qr.py`: exponiert `_FITZ_OK`/`_ZXING_OK` als
    `dict[str, bool]` — testbar ohne Library-Import
  - **QR-Startwarnung**: fehlende `zxing-cpp`/`pymupdf` → `WARNING` ins Log + sichtbarer
    Hinweistext in der GUI-Statuszeile (nicht-blockierend)
  - Kein Secret im Log nachgewiesen (Negativtest): Token/Passwort sind nie Argumente der
    neuen Log-Calls
  - 16 neue Tests in `tests/test_logging_setup.py`; alle bestehenden Tests grün

- **Token-basierte OCR-Extraktion für gedruckte QSL-Karten (ADR-0025):**
  - `_extract_token_based` in `run.py`: zerlegt OCR-Text in Tokens (Whitespace + Pipe)
    und schickt jedes Token durch `normalize_band`, `normalize_mode(fuzzy=False)`,
    `normalize_date`; Rufzeichen werden per `is_own_call` als Absender/Empfänger
    klassifiziert; mehrere verschiedene gültige Bänder/Modi → Feld `None` (kein Raten)
  - Gedruckte Karten im Tabellen-/Fließtext-Layout (OE6XXX, DG5XXX) jetzt vollständig
    automatisch auswertbar ohne Key:Value-Beschriftung
  - Frequenzangabe im OCR-Text (z. B. „5,3570" MHz) wird korrekt zu Band normalisiert (60m)
  - `normalize_mode` erhält optionalen Parameter `fuzzy=True`; Token-Scan nutzt `fuzzy=False`
    (verhindert Falsch-Positive bei Tabellenköpfen wie „DATE" → „DATA")
  - Reine Ganzzahlen (ITU-Zone, Wattangabe u. ä.) werden nicht als Frequenz gewertet
    (`_RE_PURE_INT`-Guard); Bindestrich aus Tokenizer-Stripzeichen entfernt damit
    „-07" (RST-Wert) nicht zu „07" = 40m verfälscht wird
  - Echte Paperless-OCR-Texte von OE6XXX und DG5XXX als Fixtures (schmutziger als
    synthetische Tests); DEBUG-Log zeigt Band/Mode/Date/Call-Kandidaten je Karte
  - 7 reale OCR-Texte als Test-Fixtures; 14 neue Tests; alle bestehenden Tests grün

- **README: Installationsanleitung** — getestete Schritt-für-Schritt-Anleitung
  (`git clone` → `pip install -r requirements.txt` → `pip install -e .` → `py -m qsl73`);
  Hinweis auf automatische Windows-Abhängigkeiten via PEP-508-Marker; `py` vs. `python`
- **`gui/wizard_logic.py`** — reine, tk-freie Hilfsfunktionen für Auth-Feld-Logik
  (`auth_fields_for_mode`, `validate_auth_fields`); 8 neue Unit-Tests
- **`gui/main_window._reset_progress`** — testbare Hilfsfunktion; 3 Unit-Tests via Mock

- **Realtest-Befunde 2026-06-17 dokumentiert** (`docs/realtest-befunde-2026-06-17.md`):
  6 Bugs (Issues #9–#14) und 2 Verbesserungen (Issues #15–#16) aus erstem echten
  Programmstart auf Win10 festgehalten; ADR-0024 (Python 3.12 als Referenzversion).

- **Schritt 6b — GUI-Grundgerüst (tkinter):**
  - `python -m qsl73` startet die Anwendung; Einstiegspunkt `src/qsl73/__main__.py`
  - `InstanceLock` (PID-Lockfile, `%APPDATA%\QSL73\qsl73.lock`): verhindert mehrfache
    Instanzen ohne pywin32; stale Locks (tote PID) werden überschrieben
  - `SetupWizard` (tk.Toplevel): erster-Start-Assistent mit allen Config-Feldern;
    Token-Feld mit `show="*"` (nie Klartext sichtbar); Dateiauswahl für DB-Pfad
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
    E: DG5XXX (60m/FT8) + OE6XXX (20m/FT8) → CERTAIN

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

- Initiales Repo-Grundgerüst (Verzeichnisstruktur, Branches `main` und `dev`)
- `KONZEPT.md` — technische Spezifikation (Datenquellen, Matching-Logik, GUI, Sicherheit)
- `ROADMAP.md` — Schrittplan mit Review-Punkten
- `config.example.yaml` — Konfigurationsvorlage ohne echte Werte
- Zentrale Versions-Stelle: `src/qsl73/__version__.py` (`0.1.0`)
- `assets/qsl73logo.png` — Logo-Originaldatei

### Changed

- **Beta→Stable-Release-Workflow verbindlich festgelegt (ADR-0046):** `[Unreleased]` wird
  jetzt ausschließlich beim **Stable-Release** eingefroren. Während einer Beta-Phase bleibt
  `[Unreleased]` offen; Beta-Tags (`vX.Y.Z-betaN`) werden ohne CHANGELOG-Einfrieren gesetzt.
  Release-Notes-Extraktion im Workflow (`release.yml`) ist kanalabhängig: Beta → `[Unreleased]`,
  Stable → `[X.Y.Z]`. CLAUDE.md-Handgriff entsprechend auf zwei Pfade (Beta / Stable) aufgeteilt.

- **CHANGELOG-Prozess und Versionierungsregel präzisiert (Dokumentation):** CLAUDE.md um
  reproduzierbaren Release-Handgriff (5 Schritte: `__version__` setzen, `[Unreleased]`
  umbenennen, neuen leeren Block anlegen, Kategorien-Reihenfolge prüfen, Tag pushen) und
  Entscheidungsregel bei gemischten Änderungen ergänzt (höchste Stelle gewinnt; Desktop
  schlägt Versionsnummer vor; Maintainer entscheidet). CHANGELOG selbst bereinigt:
  Mehrfach-Blöcke gleicher Kategorie aus der Sammelphase zu je einem Block zusammengeführt;
  alter separater `[0.1.0]`-Abschnitt integriert.
- **Logo im Über-Dialog größer und ohne weißen Rand:** Das transparente QSL73-Logo wird
  jetzt oben im Dialog in 112 × 112 Pixeln angezeigt (`gui/_icon.py: load_about_logo`).
  Bildreferenz am Label-Widget gehalten (GC-Schutz). Laufzeitsichere Pfadauflösung wie
  beim Fenster-Icon. Dialog kann dafür etwas größer werden; Layout bleibt sauber
  (Logo → Titel/Version → Rest).
- **README für Endnutzer überarbeitet:** Nutzer-Installationsweg (QSL73-Setup.exe von
  der Releases-Seite) jetzt prominent vor der Entwickler-Installation; Beta-Variante
  erklärt; neuer Abschnitt „Funktionen / Bedienung" beschreibt Setup-Assistent,
  Durchlauf, sichere/manuelle Zuordnung, Durcharbeiten-Workflow, Backup/Audit-Log und
  Menüstruktur; Abschnitt „Daten & Verzeichnisse" hinzugefügt; „Status: in Entwicklung"
  entfernt; keine hartkodierte Versionsnummer (Verweis auf Releases-Seite).
- **Shift-Klick-Bereichsauswahl für CERTAIN-Karten:** Klick auf Karte A, dann
  Shift-Klick auf Karte B → alle auswählbaren Karten zwischen A und B (inklusive,
  in Anzeigereihenfolge) werden markiert; bereits geschriebene/nicht-auswählbare
  werden übersprungen. Normaler Klick setzt den Anker neu. Logik in `select_range`
  (tk-frei, 10 Tests).
- **Datum-Löschen-Button im manuellen Zuordnungs-Dialog:** Kompakter ✕-Button neben
  dem Datumsfeld; setzt `_date_explicit = False` → kein Datumsfilter mehr aktiv;
  Trefferliste aktualisiert sich sofort. Für DateEntry-Fallback (Textfeld): Feld leeren.
- **Echter Fortschrittsbalken beim Durchlauf (Fixes #23):** Statt Endlos-Animation
  zeigt der Balken jetzt echten Prozentfortschritt (X/N Karten) — Vorbereitungsphase
  (HTTP-Abfrage) bleibt kurzzeitig indeterminat, beim ersten ProgressEvent mit total > 0
  schaltet der Balken auf deterministischen Fortschritt um. Statuszeile zeigt „Karte X/N
  ausgewertet — P %". Schreib-Animation unverändert. Neue Hilfsfunktion
  `format_progress_text` (tk-frei, getestet, i18n-vorbereitet).
- **Ruhigere Fortschrittsbalken-Animation:** Pulsintervall von 10 ms auf 40 ms
  erhöht (`_PROGRESS_PULSE_MS = 40`) — betrifft Vorbereitungsphase beim Durchlauf
  und Schreiben; determinater Prozentbalken (ab total > 0) unverändert.
- **Benutzerfreundliche Fehlermeldungen bei erwarteten Lauf-/Schreibfehlern (ADR-0039,
  Fixes #18):** `DatabaseChangedError` (Optimistic-Locking-Konflikt), `SchemaError`,
  `DatabaseBusyError`, `QslEntryNotFoundError` sowie Paperless-Verbindungsfehler zeigen
  jetzt eine verständliche Klartexterklärung mit Handlungshinweis statt eines rohen
  Tracebacks. Unerwartete Fehler zeigen weiterhin den Traceback. Mapping-Logik in
  `gui/error_messages.py` tk-frei und vollständig getestet. Schreibsicherheitsmodell
  (ADR-0008) unverändert.
- **Autor in allen Fenstertiteln:** Jedes echte Toplevel-Fenster trägt jetzt „— by DF1DS"
  im Titel (MainWindow, SetupWizard, ManualAssignmentDialog, Zoom-Fenster, Über-Dialog,
  Neustart-Dialog, Fehler-Dialog, Fehlerbericht-Dialog, Konfigurationsfehler-Dialog).
  Format bei BETA: „QSL73 v{v} [BETA] — by DF1DS".
- **Über-Dialog — vollständiger Autor:** Autor-Zeile zeigt jetzt
  „DF1DS | Stephan Dahmen | DOK: G16" (fett hervorgehoben).
- **README:** Autor-Eintrag um Klarname und DOK ergänzt; Paperless-Tag als frei
  wählbar (Standardvorschlag `qsl-card`) formuliert; README-Feature-Doku in
  Schritt 9 (ROADMAP) vorgemerkt.
- **Über-Dialog verfeinert:** Luftigeres Layout (mehr Padding, Separator, Mindestbreite 340 px);
  Titel als klare Überschrift; Autor „DF1DS" fett hervorgehoben; Links „GitHub" und „QRZ.com"
  als kurze Texte nebeneinander mit Hover-Unterstreichung; nutzersichtbare Texte als
  Modul-Konstanten (i18n-Vorbereitung).
- Lizenz von MIT auf **GPLv3** gewechselt (ADR-0018). `LICENSE`-Datei ersetzt;
  README, KONZEPT §15, Quelldatei-Header angepasst. Copyleft sichert, dass
  Weiterentwicklungen offen bleiben.
- `crypto.py`: `get_default_backend()` wirft `CryptoUnavailableError` auf Windows ohne
  pywin32 statt still auf `NullBackend` zurückzufallen (fail closed)
- `config.py`: `save_config()` verweigert das Speichern eines Tokens ohne Crypto-Backend
- `NullBackend` als UNSICHER/nur Test-CI dokumentiert; `CryptoUnavailableError` ergänzt

### Removed

- **Wirkungslose Sprachauswahl (ADR-0038, Issue #25):** Das Feld „Sprache (de/en)" im
  Einstellungen-Dialog entfernt — es hatte keine Wirkung, da keine i18n-Infrastruktur
  existiert. `app.language` bleibt im Config-Modell (Default: `de`); bestehende
  `config.yaml`-Dateien laden weiterhin ohne Fehler. Mehrsprachigkeit → V2 (#25).

### Fixed

- **Icon-Transparenz (tools/make_icon.py, assets/qsl73.ico):** `qsl73logo.png` hat einen
  weißen statt transparenten Hintergrund. `make_icon.py` entfernt den Hintergrund jetzt
  per Flood-Fill von den Ecken (Threshold 235, konservativ — Motivanteile bleiben erhalten)
  bevor das ICO gespeichert wird. Das erzeugte `assets/qsl73.ico` hat damit transparente
  Hintergrundbereiche in allen Größen (16/32/48/256 px) — kein weißer Kasten mehr im
  Installer-/Desktop-Icon.
- **tk-Feder durch QSL73-Icon ersetzt:** Alle Programmfenster (MainWindow, SetupWizard,
  Fehlerdialog u. a.) zeigen jetzt das QSL73-Logo statt der Standard-tk-Feder in
  Titelleiste und Taskleiste. Gelöst über `iconphoto(True, photo)` auf dem jeweiligen
  tk.Tk-Root-Fenster — propagiert automatisch auf alle Kind-Toplevels (Tk 8.6+). Neues
  Modul `gui/_icon.py` (`apply_window_icon`). Transparente 256-px-PNG-Ressource wird
  laufzeitsicher aus dem PyInstaller-Bundle gefunden (datas `qsl73_icon.png` → `_MEIPASS`).
  Icon-Laden ist try/except-geschützt — Start wird bei Fehler nie blockiert.
- **Umlaute im Installer/Deinstaller-Dialog (installer/qsl73.iss):** Ersatzschreibungen
  (ae/oe/ue) durch echte Umlaute ersetzt; `qsl73.iss` als UTF-8 mit BOM gespeichert
  (Inno Setup 6 rendert Umlaute damit kodierungsunabhängig, unabhängig von der
  System-Codepage des bauenden Systems). Finale Umlaut-Verifikation durch DF1DS auf
  deutschem System ausstehend.
- **Einstellungen-Dialog — Fenstergröße nach Mapping (ADR-0037):** `_adjust_window_size`
  wird nach dem ersten Mapping via `after(1, ...)` aufgerufen; Höhe aus
  `inner_frame.winfo_reqheight()` statt `winfo_reqheight()` des Toplevels (welche vor
  dem Mapping 0 lieferte). Fenster wird jetzt korrekt über dem Parent-Fenster zentriert.
- **Einstellungen-Dialog — Attention-Handler (ADR-0037):** FocusIn/FocusOut-Ansatz
  ersetzt durch `<Button-1>`-Bindung am Parent-Fenster mit sauberem Cleanup (Funcid).
  Im Erstkonfigurationsmodus (Parent nicht sichtbar) wird kein Handler gesetzt.
- **Einstellungen-Dialog — Fenstergröße und Mausrad-Scrollen:** Dialog öffnet jetzt
  automatisch in der benötigten Höhe (max. 90 % Bildschirmhöhe); Mausrad-Scrollen
  funktioniert bei überfüllem Inhalt zuverlässig.
- **Einstellungen-Dialog — „Verbindung testen" im Bearbeiten-Modus:** Test schlug
  bisher mit 401 fehl, weil das Token-Feld absichtlich leer bleibt (§4). Lösung:
  `resolve_effective_token` — leeres Feld + bestehendes Token in `existing_config` →
  entschlüsseltes Token intern nutzen (nie im Feld anzeigen). Neue, differenzierte
  Fehlermeldungen: URL leer, Server nicht erreichbar, Auth fehlgeschlagen, sonstiges.
- **Einstellungen speichern — Neustart-Hinweis:** Statt vagem „greift beim nächsten
  Durchlauf" erscheint jetzt ein Dialog „Bitte neu starten" mit Buttons „Jetzt beenden"
  / „Später". „Jetzt beenden" schließt die App sauber (Lock-Freigabe via `finally`
  in `run_app()`); „Später" zeigt Hinweis in Statuszeile.
- **Einstellungen-Dialog — Fokus-Feedback:** Klick ins gesperrte Hauptfenster bei
  offenem Einstellungen-Dialog → Dialog piept (`bell()`) und hebt sich in den Vordergrund
  (`lift()` + `focus_force()`).
- **KONZEPT.md: Umlaut-Artefakte korrigiert (Fixes #3):**
  ae/oe/ue-Ersetzungen in §5, §7 und §17 durch korrekte Umlaute (ä/ö/ü) ersetzt —
  rein kosmetisch.
- **Nur tatsächlich geschriebene Karten werden als bestätigt markiert (#21):**
  Übersprungene QSOs (R=Yes, expected_states-Mismatch, unbekannter R-Wert) wurden
  fälschlich als „Bestätigt ✓" angezeigt. `written_doc_ids()` (filter_util.py)
  berechnet die tatsächlich geschriebenen doc_ids aus der selections/skipped-Paarung.
- **Manuell zugeordnete Karten behalten nach dem Schreiben ihre QSO-Werte:** Nach
  „Jetzt schreiben" zeigte die Treeview-Zeile für manuell zugeordnete Karten wieder „–"
  statt Rufzeichen/Datum/Band/Mode des zugeordneten QSO. Ursache: `_manual_pending`
  wurde vor `_refresh_tree` geleert, und der `written`-Zweig löste keine QSO-Werte auf.
  Fix: neues Feld `_written_qso: dict[int, str]` (doc_id → qsoid) rettet die Verknüpfung
  vor dem Clear. `_refresh_tree` nutzt es im `written`-Zweig zur QSO-Wert-Anzeige.
  `qso_display_values(matched) → (call, date, band, mode)` in `filter_util.py` als
  gemeinsame, testbare Funktion ausgelagert (Duplikat-Logik entfernt).
- **SyntaxError in `setup_wizard.py` behoben:** `nonlocal row` im Hauptkörper von
  `SetupWizard._build_ui` (eingefügt mit dem Trefferlimit-Block in 0bc7832) verursachte
  einen `SyntaxError` beim App-Start. `nonlocal` ist nur in verschachtelten Funktionen
  zulässig; im Hauptkörper ist `row` direkt verfügbar — die Zeile wurde entfernt.
- **GUI-Import-Smoke-Tests ergänzt** (`tests/gui/test_gui_imports.py`): 9 parametrisierte
  Tests importieren alle zentralen GUI-Module ohne Display (headless, CI-kompatibel).
  Deckt Syntaxfehler und Import-Fehler ab, die tk-Tests mangels Display überspringen.
- **Prozesslücke geschlossen: Push als DoD-Pflichtpunkt** — ADR-0027 und CLAUDE.md um
  Punkt 6 erweitert: Nach dem Commit muss `git push origin dev` ausgeführt und der
  resultierende `origin/dev`-Hash im Abschluss-Bericht genannt werden. Auslöser: 7 lokale
  Commits, die nie gepusht wurden, ließen DF1DS einen veralteten Stand testen
  (Realtest-Runde verloren). „working tree clean" allein gilt nicht mehr als Abschluss.
- **Diagnoseschritt: `_on_double_click`-Bugfix-Vorlauf** — Doppelklick auf UNCERTAIN/NO_MATCH
  öffnete im Realtest keinen Dialog. Lückenlosem DEBUG-Logging in `_on_double_click`
  (`main_window.py`) hinzugefügt (jeder Abbruchpfad mit Grund); bei Early-Return wird
  zusätzlich ein Statuszeilen-Hinweis gesetzt. Kein Logikeingriff — reine Diagnose
  für Realtest mit `QSL73_DEBUG=1`.
- **P1 Installations-Fixes (Issues #9, #10, #11, #12, #13):**
  - **#9 — Build-Backend** (`pyproject.toml`): `setuptools.backends.legacy:build` →
    `setuptools.build_meta`; `pip install -e .` funktioniert jetzt ohne manuelles
    PYTHONPATH-Setzen (src-Layout korrekt erkannt)
  - **#10 — pywin32** (`requirements.txt`): `# pywin32>=306` aktiviert als
    `pywin32>=306 ; sys_platform == "win32"` (PEP-508-Marker: Linux/CI ignoriert)
  - **#11 — zxing-cpp Paketname** (`requirements.txt`): falscher/inaktiver Eintrag
    `# zxingcpp>=2.0` ersetzt durch `zxing-cpp>=3.0 ; sys_platform == "win32"`
    (PyPI-Name mit Bindestrich; Import-Modul bleibt `zxingcpp`; verifiziert mit cp312-Wheel)
  - **#12 — Setup-Assistent Passwort-Modus** (`gui/setup_wizard.py`): bei Auth-Modus
    "password" erscheinen jetzt Benutzername- und Passwort-Felder; Token-Feld wird
    ausgeblendet; dynamisches Umschalten via `<<ComboboxSelected>>`; beim Speichern wird
    das Passwort via `PaperlessClient.from_password` einmalig in Token umgewandelt —
    Passwort wird nie persistiert (§4); testbare Logik in `gui/wizard_logic.py`
  - **#13 — Fortschrittsbalken endlos** (`gui/main_window.py`): nach `RunDoneEvent`,
    `WriteDoneEvent` und `ErrorEvent` wird `progress.stop()` aufgerufen und der Modus
    auf "determinate" zurückgesetzt — Balken ruht nach Abschluss
- **Schritt 6b Korrektur — nur CERTAIN-Karten sammel-bestätigbar (ADR-0007/ADR-0023):**
  - `_on_tree_click` und `_select_all` ignorieren UNCERTAIN/NO_MATCH-Karten (nicht
    selektierbar); Klick auf unsichere Zeilen ist ein No-op
  - `_on_write` nutzt neue `build_write_selections()`: filtert auf CERTAIN + matched_qso;
    bei leerer Auswahl klare Meldung ("Unsichere Karten über Zuordnungs-Bildschirm")
  - Hinweiszeile im Hauptfenster: "Nur sichere Treffer können hier bestätigt werden.
    Unsichere Karten folgen über die manuelle Zuordnung (Schritt 6c)."
  - `is_batch_writable(card)` und `build_write_selections(cards, route)` als reine
    Funktionen in `gui/filter_util.py`; 8 neue Tests in `test_batch_writable.py`
  - ADR-0023 um Punkt 4 ergänzt (GUI-Durchsetzung ADR-0007)

### Security

- `_strip_secrets`: URL-eingebettete Credentials werden jetzt zeilenweise bereinigt —
  Userinfo (`scheme://user:pass@host` → `scheme://[gefiltert]@host`) und sensible
  Query-Parameter (`?token=`, `?key=`, `?access_token=` u. a. → Wert durch `[gefiltert]`
  ersetzt). Der Diagnosewert der übrigen Zeile bleibt erhalten. Härtung zu ADR-0035.
- Kein stiller Fallback auf unsicheres NullBackend bei fehlendem pywin32 auf Windows
- Token wird nie unverschlüsselt persistiert; bei fehlendem Backend klare Exception
