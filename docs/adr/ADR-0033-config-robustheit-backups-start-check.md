# ADR-0033: Config-Robustheit — Backups + robuster Start-Check mit Wiederherstellen/Wizard-Neustart

**Status:** Accepted

## Kontext

Beim App-Start lädt `gui/app.py` die Config über `load_or_trigger_setup()`. Bisher wurden
zwei Ausnahme-Typen nicht korrekt unterschieden:

- **`SetupNeeded`**: Config fehlt → Wizard starten (gewünschtes Verhalten, bereits implementiert)
- **`ConfigError`**: Config existiert, ist aber ungültig (kaputtes YAML, ungültige Werte,
  fehlende Pflichtfelder) → App stürzte mit ungebremsten Traceback ab

Der zweite Fall (ungültige Config) hat keine nutzerfreundliche Behandlung erhalten: kein
erklärender Hinweis, kein Ausweg außer manuellem Eingriff in das Dateisystem.

Zusätzlich fehlte eine Backup-Strategie für `config.yaml`: bei jedem Speichern wurde die
bisherige Datei überschrieben, ohne eine Sicherungskopie anzulegen. Damit war eine
Wiederherstellung der letzten gültigen Konfiguration bei Datenverlust nicht möglich.

## Entscheidung

### Teil 1: Rotierende Config-Backups (`config_backup.py`)

Bei **jedem** `save_config()`-Aufruf wird die bisherige `config.yaml` **vor dem
Überschreiben** in `%APPDATA%\QSL73\config_backups\` mit Zeitstempel kopiert
(`config_YYYYMMDD_HHMMSS.yaml`). Alte Backups werden rotiert; die letzten N werden
behalten (Default: `config.app.backup_count = 5`; `0` = kein Limit).

**Sicherheitsregel**: Die Sicherung kopiert nur die bereits auf Disk liegende, verschlüsselte
YAML-Datei (DPAPI-Token). Niemals wird ein entschlüsselter Token in ein Backup geschrieben.
Der Backup-Vorgang findet vor der Verschlüsselung der neuen Daten statt und kopiert die
vorherige Datei, die bereits verschlüsselte Werte enthält.

Config-Backups liegen in einem **eigenen Verzeichnis** (`config_backups/`) — getrennt von
den DB-Backups (`backups/`) — um Dateiformat-Kollisionen und versehentliche
Verzeichnis-Verwechslungen zu vermeiden.

### Teil 2: Robuster Start-Check (`gui/app.py`, `gui/config_error_dialog.py`)

`load_or_trigger_setup()` in `setup_assistant.py` wickelt `ConfigError` nicht mehr in
`SetupNeeded` ein. Die Ausnahme propagiert direkt.

`run_app()` fängt beide Ausnahmen separat:

| Ausnahme | Ursache | Reaktion |
|----------|---------|----------|
| `SetupNeeded` | Config fehlt | Wizard starten (unverändert) |
| `ConfigError` | Config vorhanden, aber ungültig | Fehlerdialog + Auswegangebote |

Der Fehlerdialog bei `ConfigError`:
- Zeigt die konkrete Fehlermeldung (menschenlesbar, keine Secrets)
- Schreibt WARNING ins Log
- Bietet immer: **Einrichtung neu starten** (startet SetupWizard)
- Bietet nur wenn Backups vorhanden: **Frühere Sicherung wiederherstellen** (Listbox zur
  Backup-Auswahl; gewähltes Backup wird wiederhergestellt und erneut validiert)
  - Backup gültig → App startet damit
  - Backup ebenfalls ungültig → Fehlermeldung (kein Loop, Dialog bleibt offen für erneute Wahl)
- Bietet immer: **Beenden** (sauberer Exit)

Der Dialog funktioniert vor Existenz eines MainWindow (eigener `tk.Tk()`-Root).

## Konsequenzen

**Positiv:**
- Config-Fehler beim Start führen nicht mehr zum ungebremsten Absturz
- Nutzer sieht den konkreten Fehler und hat Auswegangebote (Wizard oder Backup)
- Jede gespeicherte Config-Version ist über ein Backup wiederherstellbar
- Reine Logik (Backup-Pfade, Rotation, Listenaufbau, Restore+Load) ist tk-frei und getestet
- Klare semantische Trennung: `SetupNeeded` = "kein Setup", `ConfigError` = "Setup kaputt"

**Negativ:**
- `load_or_trigger_setup()` wirft bei ungültiger Config nun `ConfigError` statt `SetupNeeded`
  → bestehende Tests, die `SetupNeeded` für diesen Fall erwarteten, wurden angepasst
- Jeder `save_config()`-Aufruf erzeugt eine Datei-Kopie (geringe Performance-Auswirkung;
  vernachlässigbar da selten und im Hintergrund)
