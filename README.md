# QSL73

QSL73 ist ein Windows-Desktop-Tool, das gescannte **QSL-Karten aus Paperless-ngx**
automatisch mit den **QSOs im Log4OM-Logbuch** abgleicht und bei sicherem Treffer das
QSO als Papier-QSL bestätigt markiert. Jede Karte wird als **sicher erkannt**,
**unsicher** oder **kein Treffer** eingestuft; Zweifelsfälle löst der Nutzer über einen
manuellen Zuordnungs-Dialog mit Kartenvorschau.

Die aktuelle Version steht auf der
[Releases-Seite](https://github.com/kainomatic/qsl73/releases) zum Herunterladen bereit.

## Zweck

Funkamateure sammeln QSL-Karten als Belege für ihre Verbindungen. QSL73 schließt die
Lücke zwischen dem Papierstapel (eingescannt in Paperless-ngx) und dem digitalen Logbuch
(Log4OM), ohne dass jede Karte manuell nachgetragen werden muss.

## Kernprinzipien

- **Datensicherheit zuerst:** Kein Schreibvorgang ohne Backup und Transaktion.
- **Transparenz:** Keine Telemetrie; nur drei definierte Verbindungen (Paperless,
  Log4OM lokal, GitHub für Updates).
- **Nutzerkontrolle:** Jeder Lauf zeigt erst eine Vorschau — geschrieben wird nur nach
  ausdrücklicher Bestätigung.

## Voraussetzungen

- Windows 10 / 11 (64-Bit)
- [Log4OM](https://www.log4om.com/) mit lokaler SQLite-Datenbank
- [Paperless-ngx](https://docs.paperless-ngx.com/) Instanz mit eingescannten QSL-Karten
  (Tag frei wählbar im Setup-Assistenten, Standardvorschlag: `qsl-card`)

## Installation (Nutzer)

1. Auf der [Releases-Seite](https://github.com/kainomatic/qsl73/releases) die Datei
   **QSL73-Setup.exe** herunterladen.
2. Setup-Assistent durchlaufen (Admin-Rechte erforderlich).
3. QSL73 erscheint im Startmenü; kein Python oder weitere Software nötig.

Installiert nach: `C:\Program Files\QSL73`  
Nutzerdaten: `%APPDATA%\QSL73\`

**Beta-Variante:** Wer Vorabversionen testen möchte, installiert **QSL73-Beta-Setup.exe**
(ebenfalls auf der Releases-Seite, als Pre-Release markiert). Stable und Beta sind parallel
installierbar und verwenden getrennte Installationspfade und Nutzerdaten-Verzeichnisse
(`%APPDATA%\QSL73-Beta\`).

## Funktionen / Bedienung

### Erster Start — Setup-Assistent

Beim ersten Start öffnet sich automatisch ein Assistent, der folgende Einstellungen
abfragt:

- **Paperless-ngx:** Server-URL und Zugangsdaten (Token oder Benutzername/Passwort —
  Token wird DPAPI-verschlüsselt gespeichert, Passwort nie).
- **Log4OM-Datenbank:** Pfad zur lokalen SQLite-Datenbankdatei.
- **Eigenes Rufzeichen.**
- **Tags:** Welcher Tag markiert QSL-Karten in Paperless; welcher Tag wird nach dem
  Bestätigen gesetzt. Tags können aus bestehenden ausgewählt oder neu angelegt werden.
  Verbindungstest integriert.

Die Einstellungen sind jederzeit über **Bearbeiten → Einstellungen** erreichbar.

### Durchlauf starten

1. **Durchlauf starten** im Hauptfenster klicken.
2. QSL73 ruft alle getaggten Karten aus Paperless ab, liest den QR-Code oder den
   OCR-Text jeder Karte und gleicht sie mit den Log4OM-QSOs ab.
3. Ergebnis: Karten erscheinen als **Sicher erkannt**, **Unsicher** oder **Kein Treffer**.
4. Nichts wird ohne Bestätigung geschrieben.

### Sichere Treffer bestätigen

- Sichere Karten per Klick (Shift-Klick für Bereichsauswahl) markieren.
- **Jetzt schreiben** → Bestätigung → QSO wird in Log4OM als Papier-QSL markiert;
  Karte erhält den Bestätigungs-Tag in Paperless und wird im nächsten Durchlauf
  ausgeblendet.

### Manuelle Zuordnung (unsichere / nicht erkannte Karten)

Doppelklick auf eine unsichere oder nicht erkannte Karte öffnet den manuellen
Zuordnungs-Dialog:

- Kartenvorschau (blätterbar, Zoom per Klick), OCR-Vorbefüllung der Suchfelder.
- Suche nach passendem QSO; Ergebnis per Klick zuordnen.
- **Durcharbeiten-Workflow:** „Speichern", „Speichern und nächste" oder „Nächste" (ohne
  Zuordnung überspringen) — alle unsicheren Karten lassen sich so in einem Zug bearbeiten.

### Menü

| Menüpunkt | Funktion |
|-----------|----------|
| Bearbeiten → Einstellungen | Verbindungsdaten und Tags nachträglich ändern |
| Hilfe → Über QSL73 | Versionsinformation, Links |
| Hilfe → Log-Ordner öffnen | Diagnosedateien anzeigen |
| Hilfe → Fehler melden | Bereinigten Fehlerbericht für GitHub Issues erstellen |

### Sicherheit und Protokollierung

- **DB-Backup:** Vor jedem Schreibvorgang wird automatisch eine Sicherungskopie der
  Log4OM-Datenbank angelegt (im Ordner `QSL73_Backups` neben der Datenbankdatei).
- **Audit-Log:** Jedes tatsächlich geschriebene QSO wird in `%APPDATA%\QSL73\audit.log`
  mit Zeitstempel protokolliert (automatisch vs. manuell).

## Daten & Verzeichnisse

| Ort | Inhalt |
|-----|--------|
| `%APPDATA%\QSL73\` | Konfiguration, Logs, Audit-Log, Config-Backups |
| `%APPDATA%\QSL73\config.yaml` | Einstellungen (Token DPAPI-verschlüsselt) |
| `%APPDATA%\QSL73\audit.log` | Protokoll geschriebener Bestätigungen |
| Neben der Log4OM-DB | `QSL73_Backups\` — DB-Sicherungen vor dem Schreiben |

Der Deinstaller bietet an, `%APPDATA%\QSL73\` zu entfernen (Standard: Nein). Die
DB-Sicherungen im `QSL73_Backups`-Ordner werden beim Deinstallieren **nicht** angefasst.

---

## Installation aus dem Quellcode (Entwickler)

**Voraussetzung:** Python 3.12, 64-Bit, „Add to PATH" aktiviert.

```
git clone https://github.com/kainomatic/qsl73.git
cd qsl73
git checkout dev
py -m pip install -r requirements.txt
py -m pip install -e .
```

`pip install -e .` richtet das `src/`-Layout korrekt ein — kein manuelles PYTHONPATH-Setzen
nötig. Auf Windows werden `zxing-cpp` und `pywin32` durch PEP-508-Marker automatisch
mitinstalliert.

### Starten (aus Quellcode)

```
py -m qsl73
```

### Build (Installer erzeugen)

Siehe [`docs/BUILD.md`](docs/BUILD.md) für PyInstaller-Bundle und Inno-Setup-Installer.

## Entwicklungs-Doku

- Designentscheidungen: [`docs/adr/`](docs/adr/) (Architecture Decision Records)
- Technische Spezifikation: [`KONZEPT.md`](KONZEPT.md)
- Bau-Reihenfolge & Reviews: [`ROADMAP.md`](ROADMAP.md)
- Offene Aufgaben: [GitHub Issues](https://github.com/kainomatic/qsl73/issues)

## Inhaber & Kontakt

- Entwickler / Maintainer: **DF1DS — Stephan Dahmen (DOK: G16)**
- GitHub: [kainomatic](https://github.com/kainomatic)
- QRZ.com: [DF1DS](https://www.qrz.com/db/DF1DS)
- Issues & Feature-Requests: [GitHub Issues](https://github.com/kainomatic/qsl73/issues)

## Lizenz

[GNU General Public License v3.0 (GPLv3)](LICENSE) — siehe LICENSE.  
Weiterentwicklungen, die verbreitet werden, müssen ebenfalls unter GPLv3 offengelegt werden.
