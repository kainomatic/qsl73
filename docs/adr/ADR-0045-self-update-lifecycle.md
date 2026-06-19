# ADR-0045: Self-Update-Lifecycle

**Status:** Accepted

## Kontext

QSL73 wird als Windows-Installer verteilt. Nutzer sollen über neue Versionen informiert
werden und diese ohne manuellen Download aus der Anwendung heraus installieren können.
Die Update-Prüfung ist die einzige neue Außenverbindung (neben Paperless-ngx und
Log4OM-lokal) und muss CLAUDE.md-Leitplanke „nur 3 erlaubte Verbindungen" einhalten.
Es gibt zwei Release-Kanäle: Stable und Beta (ADR-0021).

## Entscheidungen

### 1. Quelle und Prüfung

Ausschließlich die offizielle GitHub-Releases-API (`api.github.com/repos/kainomatic/qsl73/releases`)
über HTTPS. Asset-Download nur von `github.com` oder `objects.githubusercontent.com` (HTTPS).
Keine anderen Quellen, keine vom API-Antwort vorgeschlagenen abweichenden Domains.

### 2. Kanallogik

| Kanal | Filter |
|-------|--------|
| stable | `prerelease == false`, Tag `vX.Y.Z` (kein `-betaN`-Suffix) |
| beta | `prerelease == true`, Tag `vX.Y.Z-betaN` |

SemVer-Vergleich: `vX.Y.Z-betaN < vX.Y.Z` bei gleicher Basis (Pre-Release < Release).

### 3. Asset-Namen

| Kanal | Asset-Name |
|-------|-----------|
| stable | `QSL73-Setup.exe` |
| beta | `QSL73-Beta-Setup.exe` |

### 4. Verifikation vor Ausführung

Vor dem Ausführen des heruntergeladenen Installers werden geprüft:
1. **HTTPS-Quelle**: Asset-URL muss von erlaubter GitHub-Domain kommen (überprüft beim Start des Downloads).
2. **Dateigröße**: Muss der von der API gemeldeten `assets[].size` entsprechen.

**Kein SHA256-Vergleich gegen Referenzwert**: Die GitHub-Releases-API liefert keinen
kryptografischen Hash für Release-Assets in der Releases-Liste. Der SHA256-Digest der
heruntergeladenen Datei wird für Diagnosezwecke geloggt, kann aber mangels Referenzwert
nicht verifiziert werden. Schutz erfolgt durch HTTPS-Verbindung zur offiziellen Domain
(Manipulationsschutz durch TLS) + Größenprüfung.

### 5. Installer-Start: /SILENT

Der Installer wird mit `/SILENT` gestartet:
- Zeigt das Fortschrittsfenster (UAC-Abfrage unvermeidbar und akzeptiert, ADR-0044).
- Überspringt alle Assistent-Seiten (kein Klick-durch erforderlich).
- `/VERYSILENT` wird bewusst nicht verwendet, damit der Nutzer den Fortschritt sieht.

### 6. App-Exit nach Installer-Start

Reihenfolge: Installer zuerst starten, dann App beenden.
- QSL73 gibt den Single-Instance-Lock frei (via `finally`-Block in `run_app()`).
- Der Installer kann `QSL73.exe` ersetzen, sobald sie nicht mehr läuft.
- Nach Abschluss startet der Installer QSL73 neu (Inno `[Run]`-Eintrag, s. u.).

### 7. Inno-Setup /SILENT-Neustart-Mechanik

Der `[Run]`-Eintrag für `QSL73.exe` in beiden `.iss`-Dateien hat:
- `nowait`: Installer wartet nicht auf QSL73.
- `postinstall`: Erscheint bei normalem Install als Checkbox (Standard: aktiviert).
- `runascurrentuser`: QSL73 startet mit den Rechten des eingeloggten Nutzers, nicht mit
  erhöhten Admin-Rechten des Installers — verhindert, dass QSL73 elevated läuft.
- **Kein `skipifsilent`**: Beim Self-Update (`/SILENT`) wird QSL73 automatisch neugestartet.
  Inno führt `postinstall`-Einträge ohne `skipifsilent` auch im Silent-Modus aus.

`CloseApplications=yes` in `[Setup]`: Inno schließt aktive Instanzen der zu
überschreibenden Dateien — Safety-Net, falls QSL73 sich nicht rechtzeitig beendet hat.

### 8. Opt-out / „Nicht mehr erinnern"

Wenn der Nutzer im Update-Dialog „Nicht mehr erinnern" anhakt und schließt/„Später"
klickt, wird `config.app.update_check = False` gesetzt und die Config gespeichert.
Der automatische Startcheck wird damit dauerhaft deaktiviert. Manuell über
Hilfe → „Nach Updates suchen" ist die Prüfung immer möglich.

### 9. „Später"-Verhalten

Nach Klick auf „Später" (ohne Opt-out) erscheint im Hilfe-Menü ein Hinweis
„⬆ Update auf vX.Y.Z verfügbar". Klick darauf öffnet den Dialog erneut.

### 10. Start-Verhalten

Der App-Start wird durch die Update-Prüfung nie blockiert:
- Prüfung läuft in einem Hintergrund-Thread.
- Netzwerkfehler → stilles Logging, kein Dialog beim Auto-Check.
- Timeout 8 s für die API-Abfrage.

### 11. AppMutex (Windows-Mutex zur Installer-Erkennung)

QSL73 setzt beim Start einen benannten Windows-Mutex für Inno-Setup's `CloseApplications`.

| Kanal | Mutex-Name |
|-------|-----------|
| stable | `QSL73-Stable` |
| beta | `QSL73-Beta` |

- Implementierung via `win32event.CreateMutex(None, False, name)` in `gui/app.py`.
- Koexistiert mit dem PID-Lockfile (Single-Instance): unterschiedliche Aufgaben.
- Wird früh in `run_app()` gesetzt — nach erfolgreichem Lock-Acquire, vor GUI-Start.
- **Non-fatal**: Fehlt pywin32 oder schlägt der Mutex-Aufruf fehl → nur Debug-Log, kein Crash.
- Handle bis Prozessende referenziert; Windows gibt ihn bei Prozessende frei.
- **Kanalspezifisch**: Stable und Beta sehen sich gegenseitig nicht als laufend.
- `AppMutex=QSL73-Stable` / `AppMutex=QSL73-Beta` in den `.iss`-Dateien.
- `RestartApplications=no` in `[Setup]`: Windows Restart Manager startet QSL73 nach dem
  Install nicht automatisch neu — das übernimmt der explizite `[Run]`-Eintrag.

### 12. Explizite Silent-Neustart-Mechanik via /RESTARTQSL73

Custom-Flag `/RESTARTQSL73` trennt Self-Update-Neustart von lautlosem Sysadmin-Deploy.

`updater.py` ruft auf:
```
subprocess.Popen([str(installer_path), "/SILENT", "/RESTARTQSL73"])
```

Pascal-Hilfsfunktion in `[Code]` beider `.iss`:
```pascal
function ShouldRestartApp: Boolean;
begin
  Result := WizardSilent() and (Pos('/RESTARTQSL73', UpperCase(GetCmdTail)) > 0);
end;
```

`[Run]`-Einträge:
```
; Interaktive Installation: Abschluss-Checkbox (skipifsilent → bei /SILENT übersprungen)
Filename: "{app}\QSL73.exe"; Flags: nowait postinstall runascurrentuser skipifsilent
; Self-Update (/SILENT /RESTARTQSL73): automatischer Neustart
Filename: "{app}\QSL73.exe"; Flags: nowait runascurrentuser; Check: ShouldRestartApp
```

Verhalten:

| Installationsart | Checkbox sichtbar | Auto-Neustart |
|-----------------|-------------------|---------------|
| Interaktiv | ja, default aktiviert | — |
| `/SILENT` (Sysadmin-Deploy, kein Flag) | nein | nein |
| `/SILENT /RESTARTQSL73` (Self-Update) | nein | ja |

### 13. Versioniertes Asset-Namensschema + Muster-Erkennung

Ab v0.2.1 tragen Installer-Assets die Versionsnummer im Dateinamen:

| Kanal | Altes Schema (≤ v0.2.0) | Neues Schema (ab v0.2.1) |
|-------|------------------------|--------------------------|
| stable | `QSL73-Setup.exe` | `QSL73-Setup-v<VERSION>.exe` |
| beta | `QSL73-Beta-Setup.exe` | `QSL73-Beta-Setup-v<VERSION>.exe` |

**Beta-Assets tragen die Ziel-Stable-Basis-Nummer** (z. B. `QSL73-Beta-Setup-v0.3.0.exe`),
nicht das `-betaN`-Suffix — die `.iss` kennt nur `APP_VERSION`.

`_pick_asset` verwendet Regex-Muster statt exaktem Namensvergleich:
- Stable: `^QSL73-Setup(-v\d+\.\d+\.\d+)?\.exe$` — schließt Beta-Assets explizit aus
- Beta:   `^QSL73-Beta-Setup(-v\d+\.\d+\.\d+)?\.exe$`

Der optionale `-vX.Y.Z`-Teil deckt alte (unversionierte) UND neue Assets ab.

**Einmaliger manueller Schritt (v0.2.0 → v0.2.1):** v0.2.0 wurde mit dem alten
Exakt-Vergleich (`asset.name == "QSL73-Setup.exe"`) veröffentlicht. Das erste Release
mit dem neuen Schema (`QSL73-Setup-v0.2.1.exe`) wird von v0.2.0 **nicht automatisch
gefunden** (Asset-not-found → `_ERR_NO_ASSET`). Nutzer müssen v0.2.1 einmalig manuell
herunterladen. Ab v0.2.1 (mit Muster-Erkennung) läuft das Self-Update dauerhaft wieder
automatisch — auch für spätere versionierte Releases.

## Konsequenzen

- Nur eine neue Außenverbindung (GitHub-API): CLAUDE.md-Leitplanke gewahrt.
- Kein Code-Signing verfügbar (ADR-0044) → SmartScreen ggf. bei heruntergeladenem Installer.
- SHA256-Verifikation gegen Referenzwert nicht möglich ohne GitHub-seitige Hash-API.
- Bei `CloseApplications=yes` kann Inno bei einem normalen (nicht-Self-Update-)Install
  eine laufende QSL73-Instanz schließen (Hinweis-Dialog von Inno, falls nötig).
- AppMutex beschleunigt Installer-Erkennung: Inno muss nicht alle Prozesse scannen.
