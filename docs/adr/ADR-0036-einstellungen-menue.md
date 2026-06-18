# ADR-0036: Einstellungen-Dialog via SetupWizard-Wiederverwendung + Menüleiste

**Status:** Accepted

## Kontext

Issue #24: Im laufenden Betrieb gibt es keinen Zugang zu den Einstellungen. Der `SetupWizard`
läuft bisher nur beim Erststart (fehlende/ungültige Config). Zusätzlich sitzen die in
Schritt 7b-2 eingeführten Aktionen „Fehler melden…" und „Log-Ordner öffnen" provisorisch
als Buttons in der Statusleiste, die eigentlich für Statusmeldungen reserviert ist.

## Entscheidung

### 1. Einstellungen-Dialog = SetupWizard-Wiederverwendung

Der bestehende `SetupWizard` (`gui/setup_wizard.py`) wird um einen optionalen Parameter
`existing_config: Config | None = None` erweitert:

- `None` (bisheriges Verhalten) → Erstkonfiguration: Titel „QSL73 — Erstkonfiguration",
  Felder mit Defaults.
- `existing_config=cfg` → Bearbeiten-Modus: Titel „QSL73 — Einstellungen", alle Felder
  mit aktuellen Config-Werten vorbefüllt.

**Begründung:** Kein zweiter Dialog nötig, keine Doppelpflege. Der Wizard deckt bereits
alle konfigurierbaren Felder ab (URL, Auth, DB-Pfad, Rufzeichen, Tags, Matching, Route,
Sprache, Backup-Anzahl, Update-Check, Trefferlimit).

### 2. Token-Erhalt-Regel im Bearbeiten-Modus (§4)

Das Token-Feld bleibt im Bearbeiten-Modus immer leer. Ein Platzhalter-Hinweis erklärt,
dass ein leeres Feld das bestehende (verschlüsselte) Token beibehält. Nur wenn der Nutzer
ein neues Token einträgt, wird es ersetzt.

Implementierung in `gui/wizard_logic.py` (rein, testbar):
- `config_to_field_defaults(config)` — Config → Feld-Defaults ohne Token
- `is_token_retain_valid(mode, token, existing_config)` — prüft ob Token-Retain gilt
- `merge_wizard_overrides(existing_config, overrides)` — mergt Wizard-Felder über
  bestehende Config; leeres Token-Feld → bestehender Token bleibt

Felder außerhalb des Wizard-Scope (z. B. `matching.portable_suffixes`, `config_version`)
bleiben durch `copy.deepcopy` und selektive Overrides erhalten.

### 3. Menüstruktur

Drei Menüs als `tk.Menu`-Menüleiste im `MainWindow`:

| Menü | Einträge |
|------|---------|
| Datei | Beenden |
| Bearbeiten | Einstellungen… |
| Hilfe | Log-Ordner öffnen, Fehler melden…, Separator, Über QSL73 |

### 4. Verlagerung der 7b-2-Aktionen von Statusleiste ins Hilfe-Menü

Die Buttons „Log-Ordner öffnen" und „Fehler melden…" werden aus der Statusleiste entfernt
und ins Hilfe-Menü verschoben. Die Statusleiste behält Progressbar, Status-Text und
Auswahl-Zähler.

### 5. „Über QSL73"-Dialog

Schlichter `messagebox.showinfo`-Dialog mit Version, Channel, Lizenz (GPLv3) und
Repo-URL.

### 6. Crypto-Backend-Weitergabe

`MainWindow.__init__` erhält einen neuen optionalen Parameter `crypto: CryptoBackend | None`.
`app.py` übergibt das bereits initialisierte Backend, damit `_on_settings` beim Speichern
das gleiche Backend verwendet wie der Erststart.

## Konsequenzen

**Positiv:**
- Einstellungen jederzeit erreichbar (Bearbeiten → Einstellungen…).
- Keine Doppelpflege: ein Wizard für beide Anwendungsfälle.
- Token-Schutz durch explizite Retain-Regel und Test-Absicherung.
- Statusleiste übersichtlicher (nur noch Fortschritts- und Status-Anzeige).
- Standard-Menüleiste verbessert Bedienbarkeit (OS-Integration, Tastaturzugang).

**Negativ / Einschränkungen:**
- Änderungen im Einstellungen-Dialog greifen erst beim nächsten Durchlauf
  (Hinweismeldung nach Speichern). Ein „Live-Reload" der Config ist nicht implementiert
  (wäre ein separater Schritt).
- Der Wizard ist beim ersten Start ohne Erstkonfiguration weiterhin modal (kein Änderungsbedarf).
