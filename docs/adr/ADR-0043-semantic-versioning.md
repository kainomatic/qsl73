# ADR-0043: Versionierung nach Semantic Versioning (MAJOR.MINOR.PATCH)

**Status:** Accepted

## Kontext

QSL73 nennt SemVer im CHANGELOG, aber kein ADR legt verbindlich fest, wann welche
Stelle erhöht wird. Ohne explizite Regel fehlt die Grundlage für konsistente
Release-Entscheidungen — insbesondere bei einem Tool, das direkt in Nutzerdaten
(Log4OM-DB, Config-Datei) schreibt. Inkompatible Änderungen hier haben unmittelbare
Auswirkungen auf echte Logbücher.

## Entscheidung

QSL73 folgt **Semantic Versioning 2.0.0** (`MAJOR.MINOR.PATCH`):

### MAJOR (X.0.0) — inkompatible Änderung

Erhöhen, wenn ein bestehender Nutzerstand nicht mehr ohne manuelle Anpassung
weiterläuft. Für QSL73 gilt das insbesondere bei:

- **Config-Schema-Bruch:** `config.yaml` einer älteren Version lässt sich nicht mehr
  laden (kein Migrations-Pfad vorhanden oder bewusst entfernt).
- **Schreibformat-Inkompatibilität in Log4OM:** das in der DB gespeicherte Format ändert
  sich so, dass vorhandene Einträge falsch interpretiert oder überschrieben werden
  (empirisch bestätigtes Format laut `docs/discovery.md`; Änderungen dort sind major).
- **Entfernen oder Umbenennen zentraler Funktionen**, die ein Nutzer konfiguriert hat
  (z. B. Tag-Felder, DPAPI-geschützte Token-Felder, Backup-Strategie).

### MINOR (0.Y.0 oder X.Y.0) — neue Funktion, abwärtskompatibel

Erhöhen bei neuen Features, die bestehende Config/DB-Daten und bestehende Workflows
unverändert weiterführen. Beispiele: neues UI-Element, neue Paperless-Abfrage, neue
Matching-Strategie (die bestehende Ergebnisse nicht verschlechtert), neues Logging.

### PATCH (0.0.Z oder X.Y.Z) — Bugfix, keine neuen Funktionen

Erhöhen bei Korrekturen, die kein neues Verhalten einführen und keine Schema-/Format-
Änderung enthalten. Beispiele: Encoding-Fix, GUI-Renderingfehler, Tippfehler in Texten,
Performance-Tuning ohne Verhaltensänderung.

### Pre-1.0-Hinweis (aktueller Stand: 0.x.y)

Solange `MAJOR = 0`, gilt das Verhalten als noch nicht stabil. Breaking Changes
(nach SemVer eigentlich MAJOR) können in MINOR (0.x) vorkommen — bewusste Einschränkung,
solange QSL73 in der Praxis noch nicht vollständig erprobt ist. Der Übergang zu 1.0.0
erfolgt nach Praxisbewährung auf Entscheidung von DF1DS; ab 1.0.0 gilt SemVer strikt
ohne diese Ausnahme.

**Faustregel bei Unsicherheit:** MINOR für Features, PATCH für Fixes. MAJOR nur bei
echten Inkompatibilitäten (oder bei ≥ 1.0.0 auch kleinere Breaking Changes).

### Beta-Vorabversionen

Pre-Release-Tags (z. B. `v0.2.0-beta1`) gemäß ADR-0021 (Beta-Kanal). Das Beta-Suffix
ändert nichts an der SemVer-Einordnung; nur die stabile Versions-Nummer entscheidet
über MAJOR/MINOR/PATCH.

### Pflicht bei jedem Release

1. `src/qsl73/__version__.py` → `__version__` auf neue Version setzen.
2. `CHANGELOG.md` → `## [Unreleased]` in `## [X.Y.Z] — YYYY-MM-DD` umbenennen und
   neuen leeren `## [Unreleased]` darüber einfügen.
3. Committen, `dev` → `main` mergen, Tag `vX.Y.Z` setzen und pushen.
4. Der Release-Workflow (ADR-0042) prüft automatisch, dass Tag-Nummer ==
   `__version__`; Abweichung → Build-Abbruch.

Die `AppVersion` in den Installer-Skripten wird vom Release-Workflow per
`/DAPP_VERSION=x.y.z` injiziert — `__version__.py` ist die einzige Quelle.

## Konsequenzen

**Positiv:**
- Klare, nachschlagbare Regel für Release-Entscheidungen.
- QSL73-spezifische MAJOR-Fälle (DB-Schreibformat, Config-Schema) explizit benannt.
- Pre-1.0-Ausnahme dokumentiert; Übergang zu 1.0.0 definiert.
- Release-Workflow (ADR-0042) setzt Version-Tag-Konsistenz technisch durch.

**Negativ / Einschränkungen:**
- Bei `MAJOR = 0` bleibt Einschätzung (Minor vs. Patch) subjektiv; kein automatischer
  Schutz. Disziplin liegt bei DF1DS/Claude Code.

## Querverweise

- ADR-0021: Beta-Kanal und Pre-Release-Tags
- ADR-0042: Release-Workflow, Tag-Konventionen, Versions-Sync
- `docs/BUILD.md` → Abschnitt „Release-Prozess"
- `src/qsl73/__version__.py`: einzige Versions-Quelle
