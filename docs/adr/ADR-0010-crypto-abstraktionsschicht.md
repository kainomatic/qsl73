# ADR-0010: Kryptographie-Abstraktionsschicht (DPAPI-Backend)

**Status:** Accepted

## Kontext

Der Paperless-Token darf nie im Klartext persistiert werden (Sicherheitsanforderung KONZEPT.md §4).
Auf Windows steht Windows DPAPI (`win32crypt`) für nutzerkontextgebundene Verschlüsselung zur
Verfügung. Testcode und CI-Runner (Linux) können nicht auf DPAPI angewiesen sein — `pywin32`
ist dort nicht verfügbar und CI läuft auf `ubuntu-latest`.

## Entscheidung

Der DPAPI-Zugriff wird hinter einem abstrakten Interface (`CryptoBackend`) gekapselt:

- **`CryptoBackend`** (ABC): zwei Methoden — `encrypt(str) → str` und `decrypt(str) → str`.
  Ciphertext wird als Base64-kodierter ASCII-String dargestellt (speicherbar in YAML).
- **`DpapiBackend`**: produktiver Windows-DPAPI-Backend. Importiert `win32crypt` **lazy**
  (erst beim Aufruf, nicht beim Modulimport) → schlägt auf Linux beim `import` nicht fehl;
  das Modul `qsl73.crypto` ist auf allen Plattformen importierbar.
- **`NullBackend`**: Base64-only, kein echter Schutz. Für Tests und Nicht-Windows-Plattformen.
- **`get_default_backend()`**: gibt `DpapiBackend` auf `sys.platform == "win32"`, sonst
  `NullBackend` zurück.

`load_config()` und `save_config()` akzeptieren ein optionales `crypto: CryptoBackend | None`-
Argument. Ohne Backend bleibt der Token-Wert unverändert (z. B. leer bei erstmaliger Einrichtung).

**`pywin32`** bleibt optionale Abhängigkeit (`[windows]` extra in `pyproject.toml`); CI
installiert sie nicht.

## Konsequenzen

- Alle Config-Logiktests (Parsing, Validierung, Migration, Round-Trip, Token-Verschlüsselung)
  laufen plattformunabhängig im CI mit `NullBackend`.
- DPAPI-Tests (`TestDpapiBackend`) skippen automatisch wenn `pywin32` nicht installiert ist —
  sowohl in CI als auch auf Windows-Entwicklungsmaschinen ohne `pywin32`.
- Ein manueller Smoke-Test des DPAPI-Backends auf Windows ist beim Schritt 8
  (Installer/Release) vorgesehen, wenn `pywin32` im Installer-Bundle enthalten ist.
- Kein Klartext-Token in der gespeicherten `config.yaml` — im Test nachgewiesen:
  `"supersecrettoken"` erscheint nach `save_config(..., crypto=NullBackend())` nicht im
  gespeicherten YAML (Base64-kodierter Wert stattdessen).
