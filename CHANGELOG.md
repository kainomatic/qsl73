# Changelog

Alle nennenswerten Änderungen an QSL73 werden in dieser Datei dokumentiert.

Das Format basiert auf [Keep a Changelog](https://keepachangelog.com/de/1.0.0/),
das Projekt folgt [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Config-Verwaltung (`src/qsl73/config.py`): Laden/Speichern aus `%APPDATA%\QSL73\config.yaml`,
  Validierung aller Felder mit verständlichen Fehlermeldungen, Defaults, Migrations-Gerüst
  mit `config_version`-Feld
- Kryptographie-Abstraktionsschicht (`src/qsl73/crypto.py`): `CryptoBackend`-Interface mit
  `DpapiBackend` (Windows DPAPI, lazy import) und `NullBackend` (Tests/CI)
- Setup-Assistent-Logik (`src/qsl73/setup_assistant.py`): `SetupNeeded`-Exception,
  `load_or_trigger_setup()`, `create_initial_config()` mit Override-Unterstützung
- Test-Infrastruktur: pytest-Gerüst (`tests/`, `pyproject.toml`) mit 49 Unit-Tests;
  GitHub Actions CI (`/.github/workflows/ci.yml`) bei Push auf `dev` und `main`
- ADR-0010: Kryptographie-Abstraktionsschicht (DPAPI-Backend)

## [0.1.0] - 2026-06-16

### Added
- Initiales Repo-Grundgerüst (Verzeichnisstruktur, Branches `main` und `dev`)
- `KONZEPT.md` – technische Spezifikation (Datenquellen, Matching-Logik, GUI, Sicherheit)
- `ROADMAP.md` – Schrittplan mit Review-Punkten
- `config.example.yaml` – Konfigurationsvorlage ohne echte Werte
- `LICENSE` (MIT, DF1DS)
- Zentrale Versions-Stelle: `src/qsl73/__version__.py` (`0.1.0`)
- `assets/qsl73logo.png` – Logo-Originaldatei
