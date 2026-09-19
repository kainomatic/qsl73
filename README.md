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

**Hinweis zur SmartScreen-Warnung:** Windows zeigt beim Ausführen des Installers eine
Meldung „Der Computer wurde durch Windows geschützt — Unbekannter Herausgeber". Das ist
bei nicht-signierten Open-Source-Projekten normal und kein Hinweis auf Schadsoftware —
der Quellcode ist auf GitHub öffentlich einsehbar. Zum Fortfahren: **„Weitere
Informationen"** anklicken, dann **„Trotzdem ausführen"**. Dies gilt für Stable und Beta.

## Funktionen / Bedienung

### Erster Start — Setup-Assistent

Beim ersten Start öffnet sich automatisch ein Assistent, der folgende Einstellungen
abfragt:

- **Paperless-ngx:** Server-URL und Zugangsdaten (Token oder Benutzername/Passwort —
  Token wird DPAPI-verschlüsselt gespeichert, Passwort nie).
- **Log4OM-Datenbank:** Pfad zur lokalen SQLite-Datenbankdatei.
- **Eigenes Rufzeichen.**
- **Tags:** Welcher Tag markiert QSL-Karten in Paperless; welcher Tag wird nach dem
  Bestätigen gesetzt; welcher Tag markiert dauerhaft ignorierte Karten
  (Ignoriert-Tag, siehe unten). Tags können aus bestehenden ausgewählt oder neu
  angelegt werden. Verbindungstest integriert.

Die Einstellungen sind jederzeit über **Bearbeiten → Einstellungen** erreichbar.

> **Hinweis nach einem Update:** Wer QSL73 von einer Version vor dem
> Ignorieren-Feature aktualisiert, sollte den Ignoriert-Tag einmalig unter
> **Bearbeiten → Einstellungen…** auswählen oder anlegen — QSL73 legt ihn nicht
> automatisch an. Bis dahin zeigt der „Ignorieren"-Button im manuellen
> Zuordnungs-Dialog einen entsprechenden Hinweis statt zu wirken.

### Durchlauf starten

1. **Durchlauf starten** im Hauptfenster klicken.
2. QSL73 ruft alle getaggten Karten aus Paperless ab, liest den QR-Code oder den
   OCR-Text jeder Karte und gleicht sie mit den Log4OM-QSOs ab.
3. Ergebnis: Karten erscheinen als **Sicher erkannt**, **Unsicher** oder **Kein Treffer**.
4. Nichts wird ohne Bestätigung geschrieben.

### Sichere Treffer bestätigen

- Sichere Karten per Klick (Shift-Klick für Bereichsauswahl) markieren.
- **Jetzt schreiben** → Bestätigung → QSO wird in Log4OM als Papier-QSL markiert;
  Karte erhält den Bestätigungs-Tag in Paperless und **verliert dabei den
  Eingangs-Tag** — der Eingangs-Tag ist ein Arbeitskorb, keine Dauer-Kategorie, und
  wird von erledigten Karten automatisch entfernt (siehe „Eingangs-Tag ist ein
  Arbeitskorb" unten).

### Manuelle Zuordnung (unsichere / nicht erkannte Karten)

Doppelklick auf eine unsichere oder nicht erkannte Karte öffnet den manuellen
Zuordnungs-Dialog:

- Kartenvorschau (blätterbar, Zoom per Klick), OCR-Vorbefüllung der Suchfelder.
- Suche nach passendem QSO; Ergebnis per Klick zuordnen.
- **Durcharbeiten-Workflow:** „Speichern", „Speichern und nächste" oder „Nächste" (ohne
  Zuordnung überspringen) — alle unsicheren Karten lassen sich so in einem Zug bearbeiten.

### Karten ignorieren (nie zuordenbare Karten)

Manche Karten sind nie zuordenbar — fremdes Log, das QSO fehlt im Logbuch, oder ein
eQSL-/LoTW-Ausdruck wurde versehentlich mit dem Eingangs-Tag versehen. Im manuellen
Zuordnungs-Dialog markiert der Button **„Ignorieren"** eine solche Karte dauerhaft:

- Wirkt sofort beim Klick, kein Bestätigungsdialog — betrifft ausschließlich
  Paperless-Tags, das Log4OM-Logbuch bleibt unberührt. Die Karte erhält den
  Ignoriert-Tag, **verliert dabei den Eingangs-Tag** und erscheint ab dem nächsten
  Durchlauf nicht mehr.
- Solange eine Karte ignoriert ist, sind „Speichern"/„Speichern und nächste" für sie
  gesperrt; ein erneuter Klick auf **„Nicht mehr ignorieren"** macht es rückgängig —
  die Karte bekommt den Eingangs-Tag zurück, sonst käme sie nie in einen Durchlauf
  zurück.
- Bereits ignorierte Karten stehen jederzeit über **Bearbeiten → Ignorierte Karten…**
  zur Verfügung (Mehrfachauswahl, „Wieder aufnehmen").

### Eingangs-Tag ist ein Arbeitskorb

> **Verhaltensänderung:** Ab dieser Version ist der Eingangs-Tag (Standardvorschlag
> `qsl-card`) ein reiner Arbeitskorb, keine Dauer-Kategorie. Bestätigte und
> ignorierte Karten verlieren ihn automatisch (siehe oben). Wer den Eingangs-Tag
> bisher zusätzlich als Dauer-Kategorie genutzt hat (z. B. für eigene Paperless-
> Filter oder -Auswertungen über alle QSL-Karten), sollte dafür einen zweiten,
> eigenen Tag anlegen — QSL73 rührt ausschließlich den in den Einstellungen
> konfigurierten Eingangs-Tag an.
>
> Beim ersten Start nach diesem Update prüft QSL73 im Hintergrund, ob bereits
> bestätigte oder ignorierte Karten aus einer früheren Version noch den
> Eingangs-Tag tragen, und fragt bei Bedarf einmalig nach, ob er entfernt werden
> soll (Ja / Später / Nicht mehr fragen). Bei „Später" fragt QSL73 beim nächsten
> Start erneut; über **Bearbeiten → Eingangs-Tag bei erledigten Karten
> entfernen…** lässt sich derselbe Aufräumvorgang jederzeit manuell auslösen.

### Menü

| Menüpunkt | Funktion |
|-----------|----------|
| Bearbeiten → Einstellungen | Verbindungsdaten und Tags nachträglich ändern |
| Bearbeiten → Ignorierte Karten… | Ignorierte Karten ansehen und wieder aufnehmen |
| Bearbeiten → Eingangs-Tag bei erledigten Karten entfernen… | Alt-Bestand aufräumen (siehe oben) |
| Hilfe → Über QSL73 | Versionsinformation, Links |
| Hilfe → Log-Ordner öffnen | Diagnosedateien anzeigen |
| Hilfe → Fehler melden | Bereinigten Fehlerbericht für GitHub Issues erstellen |

### Sicherheit und Protokollierung

- **DB-Backup:** Vor jedem Schreibvorgang wird automatisch eine Sicherungskopie der
  Log4OM-Datenbank angelegt (im Ordner `QSL73_Backups` neben der Datenbankdatei).
- **Audit-Log:** Jedes tatsächlich geschriebene QSO wird in `%APPDATA%\QSL73\audit.log`
  mit Zeitstempel protokolliert (automatisch vs. manuell); ebenso jede
  Ignorieren-/Wieder-Aufnehmen-Aktion.

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
- Aktueller Stand & priorisierte nächste Schritte: [`ROADMAP.md`](ROADMAP.md)
- Offene Aufgaben: [GitHub Issues](https://github.com/kainomatic/qsl73/issues)

## Inhaber & Kontakt

- Entwickler / Maintainer: **DF1DS — Stephan Dahmen (DOK: G16)**
- GitHub: [kainomatic](https://github.com/kainomatic)
- QRZ.com: [DF1DS](https://www.qrz.com/db/DF1DS)
- Issues & Feature-Requests: [GitHub Issues](https://github.com/kainomatic/qsl73/issues)

## Lizenz

[GNU General Public License v3.0 (GPLv3)](LICENSE) — siehe LICENSE.  
Weiterentwicklungen, die verbreitet werden, müssen ebenfalls unter GPLv3 offengelegt werden.
