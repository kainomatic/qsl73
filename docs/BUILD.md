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
