# ADR-0041: Inno-Setup-Installer für QSL73 (Stable)

**Status:** Accepted

## Kontext

Schritt 9b: QSL73 soll als installiertes Windows-Programm verteilbar sein — mit
Startmenü-Eintrag, Deinstaller und korrektem Eintrag in „Apps & Features". Das
onedir-Bundle aus Schritt 9a (`dist\QSL73\`) bildet die Grundlage. Es werden
zwei Varianten geplant: Stable (Schritt 9b, dieser ADR) und Beta (Schritt 9c,
eigenes Skript mit separatem AppId und Pfad).

## Entscheidung

### 1. Inno Setup 6

Inno Setup 6 wird als Installer-Werkzeug gewählt: freie, etablierte Lösung für
Windows-Installer; verbreitete Community, gute Dokumentation; keine Laufzeit-
Abhängigkeit auf dem Zielsystem; einfache Integration des onedir-Bundles.

### 2. Installationspfad und Architektur

Installation nach `{autopf}\QSL73` (= `C:\Program Files\QSL73`), 64-Bit erzwungen
(`ArchitecturesAllowed=x64compatible`, `ArchitecturesInstallIn64BitMode=x64compatible`).

### 3. Einbetten des onedir-Bundles

Das gesamte Verzeichnis `dist\QSL73\*` wird zur Build-Zeit eingebettet (`Source`-
Direktive). Der Installer-Build setzt daher voraus, dass `dist\QSL73\` vor dem
Aufruf von `ISCC.exe` existiert.

### 4. AppId-GUID für Stable

AppId-GUID `{4FB91B69-CF4A-4DC9-B59D-2EA92B857D0B}` festgelegt. Diese GUID
identifiziert die Stable-Installation bei Windows eindeutig — für Updates und den
Eintrag in „Apps & Features". Die GUID darf für den Stable-Installer **niemals**
geändert werden; eine Änderung würde Windows eine Parallel-Installation statt
eines Updates erkennen lassen.

### 5. Nutzerdaten beim Deinstallieren

Der Deinstaller fragt nach `%APPDATA%\QSL73` (Default: **NEIN** — Daten behalten).
Nutzerdaten (Config, Token, Backups, Logs) bleiben damit standardmäßig erhalten.
Die Log4OM-Datenbank liegt außerhalb `%APPDATA%\QSL73` und wird vom Deinstaller
unter keinen Umständen berührt.

### 6. Beta-Installer

Der Beta-Installer (Schritt 9c) erhält ein eigenes Inno-Setup-Skript mit separatem
AppId-GUID, eigenem Installationspfad (`C:\Program Files\QSL73 Beta`) und eigenem
APPDATA-Verzeichnis (`%APPDATA%\QSL73-Beta\`) — gemäß ADR-0021.

## Konsequenzen

- `installer\Output\QSL73-Setup.exe` wird nicht versioniert (in `.gitignore`);
  das fertige Setup wird als GitHub-Release bereitgestellt.
- `installer\qsl73.iss` ist die kanonische Installer-Konfiguration für Stable.
- Die AppId-GUID `{4FB91B69-CF4A-4DC9-B59D-2EA92B857D0B}` darf für Stable
  **nie** geändert werden.
- `dist\QSL73\` muss vor dem Installer-Build vorhanden sein (zuerst PyInstaller-Build).
- Finaler Wizard-Test (Sprache, Lizenz, MsgBox-JA/NEIN-Pfad) durch DF1DS steht noch aus.
