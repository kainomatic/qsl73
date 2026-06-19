# QSL73 — Build-Anleitung (PyInstaller)

Diese Anleitung beschreibt, wie aus dem Quellcode eine eigenständige Windows-.exe
(`dist\QSL73\QSL73.exe`) gebaut wird. Sie setzt keine Python-Installation auf dem
Zielsystem voraus (onedir-Bundle).

---

## Voraussetzungen

| Anforderung | Hinweis |
|-------------|---------|
| Windows 64-Bit | Build und Zielplattform identisch |
| Python 3.12 64-Bit | Referenzversion (ADR-0024); **nicht** 32-Bit oder 3.13+ |
| Git | Für `git clone` |
| Internetverbindung | Für `pip install` |

---

## Schritte

### 1. Repository klonen

```
git clone https://github.com/DF1DS/qsl73.git
cd qsl73
```

### 2. Virtuelle Umgebung anlegen und Abhängigkeiten installieren

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pip install -e .
```

### 3. PyInstaller installieren

PyInstaller gehört **nicht** zu `requirements.txt` (nur Build-Zeit-Werkzeug, nicht
Laufzeit-Abhängigkeit). Separat installieren:

```
pip install pyinstaller
```

### 4. Icon erzeugen

```
python tools/make_icon.py
```

Erzeugt `assets/qsl73.ico` (16 / 32 / 48 / 256 px) aus `assets/qsl73logo.png`.

### 5. Bundle bauen

```
pyinstaller qsl73.spec
```

Alternativ über das mitgelieferte Hilfsskript:

```
powershell -ExecutionPolicy Bypass -File tools/build.ps1
```

### 6. Ergebnis

```
dist\QSL73\QSL73.exe     ← Anwendung
dist\QSL73\              ← gesamtes Bundle (Ordner neben .exe)
```

### 7. Schnelltest

`dist\QSL73\QSL73.exe` starten — der Setup-Assistent erscheint (keine Python-
Installation notwendig).

---

## Bekannte Fallstricke

### zxingcpp (QR-Decoding)

- **PyPI-Name:** `zxing-cpp` (mit Bindestrich)
- **Import-Name im Code:** `zxingcpp` (ohne Bindestrich)
- Das Paket installiert eine einzelne `.pyd`-Datei, kein Python-Package.
- PyInstaller erkennt es nicht automatisch → in `qsl73.spec` manuell als `binaries`
  eingetragen (`zxingcpp.__file__` → Zielordner `.`).

### pymupdf + fitz

- `pymupdf` enthält native DLLs (`mupdfcpp64.dll`, `_mupdf.pyd`, `_extra.pyd`) →
  `collect_all('pymupdf')` nötig.
- `fitz` ist seit PyMuPDF 1.23+ nur noch ein Namespace-Wrapper ohne eigene Dateien,
  aber PyInstaller erkennt ihn nicht automatisch → `collect_all('fitz')` zusätzlich.

### tkcalendar + babel

- Beide Pakete werden von PyInstaller nicht automatisch gesammelt (reine Python,
  aber mit Locale-Daten im Paketordner).
- `collect_all('tkcalendar')` und `collect_all('babel')` nötig — sonst fehlen
  babel-Locale-Daten zur Laufzeit.

### pywin32 (DPAPI)

- `collect_all('win32')` bündelt `win32crypt`, `win32api`, `win32con`, `pywintypes` usw.
- Zusätzlich als `hiddenimports` eingetragen, da PyInstaller die dynamischen Imports
  nicht statisch erkennt.

### qsl73.spec in .gitignore

- `.gitignore` schließt `*.spec` generell aus. `qsl73.spec` ist über
  `!qsl73.spec` als Ausnahme explizit eingecheckt.
- `dist/` bleibt ausgeschlossen und wird **nicht** committet.

---

## dist/ nicht versioniert

Das `dist/`-Verzeichnis ist in `.gitignore` eingetragen und wird nicht ins Repo
committet. Das fertige Bundle wird als GitHub-Release bereitgestellt (Schritt 9b).

---

## HTML-Infodateien erzeugen

Vor jedem Installer-Build müssen zwei HTML-Dateien aus `README.md` und `CHANGELOG.md`
erzeugt werden. Sie werden vom Installer nach `{app}` kopiert und im Startmenü verlinkt.

```
python tools/make_docs_html.py
```

| Eingabe | Ausgabe |
|---------|---------|
| `README.md` | `installer/docs/LIESMICH.html` |
| `CHANGELOG.md` | `installer/docs/AENDERUNGEN.html` |

Die HTML-Dateien sind Build-Artefakte und **nicht** im Repo eingecheckt
(`.gitignore`-Eintrag `installer/docs/`). Das Skript `tools/make_docs_html.py` ist versioniert.

### Abhängigkeit (nur Build-Zeit)

```
pip install markdown        # einmalig, oder: pip install -r requirements-dev.txt
```

`markdown` ist eine reine Build-Zeit-Abhängigkeit — nicht in `requirements.txt` der App,
nicht im PyInstaller-Bundle.

### Build-Reihenfolge (lokal und CI)

```
1. python tools/make_icon.py        # Windows-Icon erzeugen
2. pyinstaller qsl73.spec           # App-Bundle bauen
3. python tools/make_docs_html.py   # HTML-Infodateien erzeugen  ← VOR ISCC!
4. ISCC.exe installer\qsl73.iss     # Installer bauen
```

`tools/build_installer.ps1` (lokales Hilfsskript) und `.github/workflows/release.yml`
(Release-Workflow) führen Schritt 3 automatisch vor ISCC aus. Bei direktem ISCC-Aufruf
muss Schritt 3 manuell ausgeführt werden, sonst fehlen die HTML-Dateien im Installationspaket.

---

## Installer bauen (Inno Setup)

### Voraussetzungen

- Inno Setup 6 installiert (https://jrsoftware.org/isdl.php)
- `dist\QSL73\` muss vorhanden sein (zuerst PyInstaller-Build ausführen, siehe oben)

### Build ausführen

```
ISCC.exe installer\qsl73.iss
```

Ergebnis: `installer\Output\QSL73-Setup.exe`

### Pfad zu ISCC.exe

```
Windows: C:\Program Files (x86)\Inno Setup 6\ISCC.exe   (System-Installation)
Oder:    %LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe   (per-User-Installation via winget)
```

### Installer testen

`QSL73-Setup.exe` starten, Wizard durchlaufen.
Nach der Installation: `C:\Program Files\QSL73\QSL73.exe` starten.

### Bekannte Fallstricke

- `dist\QSL73\` muss vor dem Installer-Build existieren (Inno packt den Ordner zur Build-Zeit)
- `installer\Output\` ist in `.gitignore` — Setup.exe nicht ins Repo committen
- AppId-GUID (`{4FB91B69-CF4A-4DC9-B59D-2EA92B857D0B}`) **NIEMALS** ändern — sonst erkennt
  Windows den Installer nicht als Update zum bestehenden Eintrag in „Apps & Features"
- UAC-Elevation: Der Installer benötigt Admin-Rechte (`PrivilegesRequired=admin`)

### Beta-Installer lokal bauen

```
ISCC.exe /DAPP_VERSION=0.1.0 installer\qsl73-beta.iss
```

Ergebnis: `installer\Output\QSL73-Beta-Setup.exe`

Wichtig: Beta-Bundle benötigt `CHANNEL="beta"` in `__version__.py`. Für lokale Tests
vor dem Bau einmalig anpassen (Datei danach zurücksetzen — nicht committen):

```
# In src\qsl73\__version__.py:
# CHANNEL = "beta"   ← temporär für Beta-Bundle-Test
```

---

## Release-Prozess (automatisiert via GitHub Actions)

Releases werden durch Push eines Versions-Tags ausgelöst. Der Workflow
`.github/workflows/release.yml` baut dann automatisch auf `windows-latest`.

### Tag-Konventionen

| Tag-Muster | Beispiel | Release-Typ |
|------------|----------|-------------|
| `vX.Y.Z` | `v0.1.0` | Stable — normales GitHub-Release |
| `vX.Y.Z-betaN` | `v0.1.0-beta1` | Beta — GitHub-Pre-Release |

### Voraussetzungen für ein Release

1. `src/qsl73/__version__.py` enthält die Ziel-Version (z. B. `__version__ = "0.1.0"`)
2. `CHANGELOG.md` unter `## [Unreleased]` beschreibt die Änderungen
3. Alle Tests grün (lokal + CI)
4. Auf `dev` committen und pushen

### Stabiles Release auslösen (Beispiel v0.1.0)

```
# 1. dev → main mergen
git checkout main
git merge dev
git push origin main

# 2. Tag setzen und pushen → Workflow startet automatisch
git tag v0.1.0
git push origin v0.1.0
```

### Beta-Release auslösen (Beispiel v0.1.0-beta1)

```
# Direkt von dev (kein main-Merge nötig)
git tag v0.1.0-beta1
git push origin v0.1.0-beta1
```

### Was der Workflow tut

1. Versions-Sync prüfen: Tag-Nummer muss mit `__version__.py` übereinstimmen
2. Python 3.12 + Abhängigkeiten installieren
3. Icon erzeugen (`tools/make_icon.py`)
4. Bei Beta-Tag: `CHANNEL` in `__version__.py` auf `"beta"` patchen (nur im CI-Lauf)
5. PyInstaller-Bundle bauen
6. **HTML-Infodateien erzeugen** (`tools/make_docs_html.py` → `installer/docs/`)
7. Inno Setup installieren (Chocolatey)
8. ISCC mit `/DAPP_VERSION=x.y.z` für Stable oder Beta-Variante aufrufen
9. GitHub-Release erstellen und Setup-Datei als Asset anhängen

### Versionsnummer anheben (vor jedem Release)

Einzige Quelle der Wahrheit: `src/qsl73/__version__.py`

```python
__version__ = "0.2.0"   # ← hier ändern
CHANNEL = "stable"       # unverändert lassen
```

Weg zu v1.0.0: Minor-Versionen (0.2.0, 0.3.0 …) bis zur Praxisbewährung;
v1.0.0 nach stabiler Feldnutzung durch DF1DS.

### Versions-Sync-Fehler beheben

Wenn der Workflow mit „Versions-Mismatch" abbricht:

```
# Falsches Tag löschen und neu setzen:
git tag -d v0.2.0
git push origin :refs/tags/v0.2.0

# __version__.py korrigieren, committen, pushen
# Dann Tag neu setzen:
git tag v0.2.0
git push origin v0.2.0
```
