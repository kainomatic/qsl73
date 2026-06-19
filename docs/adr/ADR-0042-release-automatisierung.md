# ADR-0042: Release-Automatisierung via GitHub Actions + Beta-Installer-Variante

**Status:** Accepted

## Kontext

Nach Abschluss des PyInstaller-Builds (ADR-0040) und des Stable-Installers (ADR-0041)
fehlten noch:

1. Eine Beta-Installer-Variante, die parallel zur Stable-Version installierbar ist
   (separate AppId-GUID, separater Installationspfad, separates APPDATA-Verzeichnis).
2. Eine automatisierte Build-Pipeline, die bei einem Versions-Tag beide Setup-Varianten
   auf einem Windows-Runner baut und als GitHub-Release-Assets bereitstellt.
3. Eine Absicherung, dass der Git-Tag immer zur Version in `__version__.py` passt
   (Versions-Synchronisation).

## Entscheidung

### Beta-Installer-Variante

Eine **separate .iss-Datei** (`installer/qsl73-beta.iss`) statt einer parametrierten
gemeinsamen Datei. Begründung: Die AppId-GUIDs dürfen sich nie ändern; eine explizite,
eigenständige Datei macht das offensichtlicher und eliminiert das Risiko, durch einen
falschen `/D`-Parameter den falschen GUID einzuspeisen. Der Mehraufwand bei Änderungen
(beide Dateien aktualisieren) ist bei diesem selten geänderten Installerskript akzeptabel.

Beta-spezifische Werte (beide fest, nie ändern):

| Eigenschaft | Wert |
|-------------|------|
| AppId GUID  | `{A3F5C8D2-7E4B-4A91-B5C6-2D8E9F3A1B07}` |
| Installationspfad | `C:\Program Files\QSL73 Beta` |
| APPDATA | `%APPDATA%\QSL73-Beta\` |
| Ausgabedatei | `QSL73-Beta-Setup.exe` |

Stable-Werte bleiben unverändert (ADR-0041).

### CHANNEL-Schalter für Beta-Build

`CHANNEL` in `src/qsl73/__version__.py` bleibt als Compile-time-Konstante (`"stable"`
im Repo). Für den Beta-Build patcht der GitHub-Actions-Workflow vor dem PyInstaller-Lauf
`CHANNEL = "stable"` → `CHANNEL = "beta"` in einer ephemeren Kopie (CI-Umgebung, kein
Commit). So ist der Wert unveränderlich im Bundle eingebettet; Nutzer können ihn nicht
über Umgebungsvariablen zur Laufzeit überschreiben. Der Repo-Stand bleibt `"stable"`.

### Tag-Konventionen

| Tag-Muster | Bedeutung | Release-Typ |
|------------|-----------|-------------|
| `vX.Y.Z` | Stable-Release (z. B. `v0.1.0`) | Normales GitHub-Release |
| `vX.Y.Z-betaN` | Beta-Pre-Release (z. B. `v0.1.0-beta1`) | GitHub-Pre-Release |

Der Workflow erkennt das Muster anhand `-beta` im Tag-Namen und steuert damit Kanal,
Installer-Datei und Release-Typ (prerelease: true/false).

### Versions-Synchronisation

Der Workflow prüft als ersten fachlichen Schritt, ob die Versions-Nummer aus dem Git-Tag
(ohne `v`-Präfix und ohne `-betaN`-Suffix) identisch mit `__version__` in
`src/qsl73/__version__.py` ist. Bei Abweichung bricht der Build mit klarer Fehlermeldung
ab. Zusätzlich injiziert der Workflow die Version per `/DAPP_VERSION=x.y.z` an ISCC;
die .iss-Dateien verwenden `{#APP_VERSION}` (mit Fallback-Default für lokale Builds).
Damit gibt es nur eine einzige Quellwahrheit für die Versionsnummer.

### GitHub-Actions-Workflow

- Runner: `windows-latest` (64-Bit Windows)
- Python: 3.12 (ADR-0024)
- Inno Setup: per Chocolatey (`choco install innosetup`)
- Release-Upload: `softprops/action-gh-release@v2`
- Release-Notes: aus `## [Unreleased]`-Abschnitt in `CHANGELOG.md` extrahiert

## Konsequenzen

**Positiv:**
- Releases werden reproduzierbar und ohne manuelle Build-Schritte erzeugt.
- Versions-Mismatch zwischen Tag und Code ist unmöglich (Workflow-Abbruch).
- Stable und Beta können dauerhaft parallel installiert sein (ADR-0021).
- Lokale Builds funktionieren weiterhin mit den vorhandenen Skripten.

**Negativ / Einschränkungen:**
- Zwei .iss-Dateien müssen bei Installer-Änderungen synchron gehalten werden.
- CHANNEL-Patching im Workflow ist eine Inline-Mutation der Quelldatei; ein Tippfehler
  im Regexp würde einen falschen Bundle erzeugen. Der Regexp ist minimal und gezielt.
- Erster Release-Lauf ohne echten Tag nicht vollständig testbar (nur Syntax-Check).
