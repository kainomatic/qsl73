# QSL73

**Status: in Entwicklung (pre-release)**

QSL73 ist ein Windows-Desktop-Tool (installierbare .exe), das gescannte **QSL-Karten aus Paperless-ngx** automatisch mit den **QSOs im Log4OM-Logbuch** abgleicht und bei sicherem Treffer das QSO als Papier-QSL bestätigt markiert. Zweifelsfälle löst der Nutzer über einen manuellen Zuordnungs-Bildschirm mit Kartenanzeige.

## Zweck

Funkamateure sammeln QSL-Karten als Belege für ihre Verbindungen. QSL73 schließt die Lücke zwischen dem Papierstapel (eingescannt in Paperless-ngx) und dem digitalen Logbuch (Log4OM), ohne dass jede Karte manuell nachgetragen werden muss.

## Kernprinzipien

- **Datensicherheit zuerst:** Kein Schreibvorgang ohne Backup und Transaktion.
- **Transparenz:** Keine Telemetrie; nur drei definierte Verbindungen (Paperless, Log4OM lokal, GitHub für Updates).
- **Nutzerkontrolle:** Jeder Lauf zeigt erst eine Vorschau — geschrieben wird nur nach ausdrücklicher Bestätigung.

## Inhaber & Kontakt

- Entwickler / Maintainer: **DF1DS**
- GitHub: [kainomatic](https://github.com/kainomatic)
- QRZ.com: [DF1DS](https://www.qrz.com/db/DF1DS)
- Issues & Feature-Requests: [GitHub Issues](https://github.com/kainomatic/qsl73/issues)

## Lizenz

[GNU General Public License v3.0 (GPLv3)](LICENSE) — siehe LICENSE.
Weiterentwicklungen, die verbreitet werden, müssen ebenfalls unter GPLv3 offengelegt werden.

## Voraussetzungen

- Windows 10 / 11 (64-Bit)
- [Log4OM](https://www.log4om.com/) mit lokaler SQLite-Datenbank
- [Paperless-ngx](https://docs.paperless-ngx.com/) Instanz mit QSL-Karten (Tag `qsl-card`)

## Installation (Entwicklungsumgebung)

**Voraussetzung:** Python 3.12, 64-Bit, "Add to PATH" aktiviert (Referenzversion: ADR-0024).

```
git clone https://github.com/kainomatic/qsl73.git
cd qsl73
git checkout dev
py -m pip install -r requirements.txt
py -m pip install -e .
```

`pip install -e .` richtet das `src/`-Layout korrekt ein — **kein manuelles PYTHONPATH-Setzen** nötig.
Auf Windows werden `zxing-cpp` und `pywin32` durch PEP-508-Marker in `requirements.txt`
automatisch mitinstalliert; auf Linux/CI werden sie ignoriert.

Hinweis: Auf Windows ist `py` (Python-Launcher) dem direkten `python`-Aufruf vorzuziehen,
da er die richtige 64-Bit-Version auswählt.

## Starten

```
py -m qsl73
```

Beim ersten Start öffnet sich der Setup-Assistent. Die Konfiguration wird unter `%APPDATA%\QSL73\config.yaml` gespeichert (Token DPAPI-verschlüsselt).

## Konfiguration

Beim ersten Start öffnet sich automatisch der Setup-Assistent mit allen erforderlichen Feldern. Echte Konfigurationsdateien (mit Token/Pfad) gehören **nicht ins Repo**.

## Entwicklungs-Doku

- Designentscheidungen: [`docs/adr/`](docs/adr/) (Architecture Decision Records)
- Technische Spezifikation: [`KONZEPT.md`](KONZEPT.md)
- Bau-Reihenfolge & Reviews: [`ROADMAP.md`](ROADMAP.md)
- Offene Aufgaben: [GitHub Issues](https://github.com/kainomatic/qsl73/issues)
