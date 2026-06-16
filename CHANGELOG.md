# Changelog

Alle nennenswerten Änderungen an QSL73 werden in dieser Datei dokumentiert.

Das Format basiert auf [Keep a Changelog](https://keepachangelog.com/de/1.0.0/),
das Projekt folgt [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Paperless-Client (`src/qsl73/paperless.py`): Auth (Token + Password→Token), Dokumente nach
  Tag mit Paginierung, OCR-Text, Preview/Download/Thumb, Tag-Operationen (Name→ID, PATCH);
  klare Fehlerklassen ohne Secrets in Fehlermeldungen; 56 Unit-Tests gegen Mocks (responses)
- Config-Verwaltung (`src/qsl73/config.py`): Laden/Speichern aus `%APPDATA%\QSL73\config.yaml`,
  Validierung aller Felder mit verständlichen Fehlermeldungen, Defaults, Migrations-Gerüst
  mit `config_version`-Feld
- Kryptographie-Abstraktionsschicht (`src/qsl73/crypto.py`): `CryptoBackend`-Interface mit
  `DpapiBackend` (Windows DPAPI, lazy import) und `NullBackend` (Tests/CI)
- Setup-Assistent-Logik (`src/qsl73/setup_assistant.py`): `SetupNeeded`-Exception,
  `load_or_trigger_setup()`, `create_initial_config()` mit Override-Unterstützung
- Test-Infrastruktur: pytest-Gerüst (`tests/`, `pyproject.toml`) mit 49 Unit-Tests;
  GitHub Actions CI (`/.github/workflows/ci.yml`) bei Push auf `dev` und `main`
- ADR-0010: Kryptographie-Abstraktionsschicht (DPAPI-Backend, fail-closed-Entscheidung)

### Changed
- `crypto.py`: `get_default_backend()` wirft `CryptoUnavailableError` auf Windows ohne pywin32
  statt silent auf `NullBackend` zurückzufallen (fail closed)
- `config.py`: `save_config()` verweigert das Speichern eines Tokens ohne Crypto-Backend
- `NullBackend` als UNSICHER/nur Test-CI dokumentiert; `CryptoUnavailableError` neu hinzugefügt

### Security
- Kein stiller Fallback auf unsicheres NullBackend bei fehlendem pywin32 auf Windows
- Token wird nie unverschlüsselt persistiert; bei fehlendem Backend klare Exception

## [0.1.0] - 2026-06-16

### Added
- Initiales Repo-Grundgerüst (Verzeichnisstruktur, Branches `main` und `dev`)
- `KONZEPT.md` – technische Spezifikation (Datenquellen, Matching-Logik, GUI, Sicherheit)
- `ROADMAP.md` – Schrittplan mit Review-Punkten
- `config.example.yaml` – Konfigurationsvorlage ohne echte Werte
- `LICENSE` (MIT, DF1DS)
- Zentrale Versions-Stelle: `src/qsl73/__version__.py` (`0.1.0`)
- `assets/qsl73logo.png` – Logo-Originaldatei
