# ADR-0040: PyInstaller-Build — onedir-Bundle für Windows

**Status:** Accepted

## Kontext

Schritt 9a: QSL73 soll als eigenständige Windows-.exe ausgeliefert werden, die ohne
installiertes Python auf dem Zielsystem läuft. Der Build muss alle nativen Abhängigkeiten
(zxingcpp, pymupdf/fitz, pywin32, tkcalendar/babel) korrekt einbetten und auf
Windows Server 2025 (64-Bit, Python 3.12) verifiziert worden sein.

## Entscheidung

### 1. onedir statt onefile

Das Bundle wird als Verzeichnis (`dist\QSL73\`) erzeugt, nicht als einzelne `.exe`.
Gründe:
- Schnellerer Start (kein Entpack-Schritt beim ersten Aufruf)
- Einfachere Integration in Inno-Setup (Schritt 9b): Installer kopiert das Verzeichnis
  statt eine einzelne Datei zu entpacken

### 2. Entry-Point und pathex

`run_qsl73.py` im Repo-Root ist der PyInstaller-Entry-Point.
`pathex=['src']` macht das `src/`-Layout für den Analyzer sichtbar, ohne PYTHONPATH
manuell setzen zu müssen.

### 3. Explizit gebündelte Abhängigkeiten

| Abhängigkeit | Methode | Grund |
|---|---|---|
| tkcalendar + babel | `collect_all` | Reine Python, aber nicht auto-erkannt; babel braucht Locale-Daten |
| pymupdf | `collect_all` | Native DLLs (`mupdfcpp64.dll`, `_mupdf.pyd`, `_extra.pyd`) |
| fitz | `collect_all` | Namespace-Wrapper seit PyMuPDF 1.23+; PyInstaller übersieht ihn |
| zxingcpp | Manuell als `binaries` | Einzelne `.pyd`-Datei, kein Python-Package; kein `collect_all` möglich |
| pywin32 | `collect_all('win32')` + `hiddenimports` | Dynamische Imports (win32crypt, pywintypes) für DPAPI |
| Pillow | Automatisch erkannt | Kein manueller Eingriff nötig |

### 4. qsl73.spec als kanonische Build-Konfiguration

Die Datei `qsl73.spec` ist die einzige Quelle für die Build-Parameter. Da `.gitignore`
`*.spec` generell ausschließt, ist `!qsl73.spec` als Ausnahme hinzugefügt.

### 5. Verifikation

Auf Windows Server 2025 (Build-Maschine) wurden vier Punkte geprüft:
- Anwendungsstart (Setup-Assistent erscheint)
- QR-Decoding (zxingcpp-Bundle funktioniert)
- DPAPI-Verschlüsselung (pywin32-Bundle funktioniert)
- Datepicker (tkcalendar + babel-Locale-Daten vorhanden)

Finaler Realtest auf einer weiteren Windows-Maschine durch DF1DS steht noch aus.

## Konsequenzen

**Positiv:**
- Kein Python auf dem Zielsystem erforderlich
- Alle Abhängigkeiten im Bundle; keine Runtime-Überraschungen
- `qsl73.spec` im Repo → Build jederzeit reproduzierbar
- onedir erleichtert Inno-Setup-Packaging (Schritt 9b)

**Negativ / Einschränkungen:**
- `dist/QSL73/` nicht versioniert (in `.gitignore`); Bundle muss lokal gebaut oder
  als GitHub-Release bezogen werden
- Finaler Realtest auf frischem System durch DF1DS steht noch aus
- zxingcpp muss bei Python-Version- oder ABI-Wechsel neu getestet werden (`.pyd`
  ist versionsgebunden)
