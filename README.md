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

MIT — siehe [LICENSE](LICENSE).

## Voraussetzungen

- Windows 10 / 11 (64-Bit)
- [Log4OM](https://www.log4om.com/) mit lokaler SQLite-Datenbank
- [Paperless-ngx](https://docs.paperless-ngx.com/) Instanz mit QSL-Karten (Tag `qsl-card`)

## Konfiguration

Kopiere `config.example.yaml` nach `%APPDATA%\QSL73\config.yaml` und trage deine Werte ein. Echte Konfigurationsdateien (mit Token/Pfad) gehören **nicht ins Repo**.
