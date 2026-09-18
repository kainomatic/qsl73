# ADR-0055: Log-Level im Einstellungen-Dialog (app.log_level)

**Status:** Accepted

## Kontext

Die Log-Genauigkeit war bisher ausschließlich über die Umgebungsvariable `QSL73_DEBUG=1`
steuerbar (ADR-0026) — für Endnutzer unkomfortabel und nicht auffindbar (Issue #26).
Ziel: ein neues Config-Feld `app.log_level` (`INFO`/`WARNING`/`DEBUG`) als Combobox im
Einstellungen-Dialog, ohne den Entwickler-Override `QSL73_DEBUG` zu verlieren und ohne
die frühe Start-Reihenfolge aus ADR-0026 umzubauen.

## Entscheidung

### 1. Effektives Level = das gesprächigere aus `QSL73_DEBUG` und `app.log_level` (V1)

`QSL73_DEBUG` kann das konfigurierte Level nur **anheben** (gesprächiger machen), nie
absenken:

- `QSL73_DEBUG` gesetzt (nicht `""`/`"0"`) → erzwingt mindestens `DEBUG`.
- Sonst gilt exakt `app.log_level`.

**Begründung:** Wählt der Nutzer im Dialog ein Level, ist genau dieses aktiv — der Wert
wirkt verlässlich. `QSL73_DEBUG` bleibt als Entwickler-Override für temporäre
Debug-Sessions vollständig wirksam (kein YAML-Edit nötig, wie in ADR-0026 begründet).

Reine, testbare Funktion `effective_level(env_debug, config_level_name)` in
`logging_setup.py` kapselt diese Logik; unbekannte Config-Werte fallen auf `INFO` zurück
(robust gegen manuelle YAML-Fehler).

### 2. Hinweis-Log bei Anhebung durch `QSL73_DEBUG` (V2)

Hebt `QSL73_DEBUG` das konfigurierte Level tatsächlich an, schreibt `apply_log_level()`
einen `INFO`-Eintrag ins Log: „Log-Level durch QSL73_DEBUG auf DEBUG angehoben
(Config: %s)". Ohne diesen Hinweis wäre für den Nutzer nicht nachvollziehbar, warum trotz
gewähltem `WARNING` plötzlich `DEBUG`-Zeilen erscheinen (Diagnose-Fähigkeit, § Motivation
ADR-0026).

### 3. Nachträgliches Level-Setzen statt Startreihenfolge-Umbau (V3)

`setup_logging()` bleibt unverändert (Signatur, Default, frühe Aufrufposition in
`run_app()` vor dem Config-Laden — Lock → Start-Log → QR-Status). Eine neue Funktion
`apply_log_level(level_name)` wird **nach** erfolgreichem Config-Laden aufgerufen (an der
Stelle, wo `config` in allen drei Zweigen — normal / SetupNeeded-Wizard /
ConfigError-Dialog — feststeht), und setzt das Level nachträglich auf Logger und alle
Handler. Damit bleibt das frühe Start-Logging (inkl. Config-Fehlern) erhalten, ohne die in
ADR-0026 begründete Reihenfolge (Logging vor Config) anzutasten.

Im Einstellungen-Dialog (`SetupWizard._on_ok`) wird `apply_log_level()` zusätzlich direkt
nach dem Speichern aufgerufen — risikolos (reines Level-Setzen, kein Restart nötig) und
konsistent mit ADR-0036 §7, das einen In-Process-Neustart bewusst ausschließt: das
Log-Level wirkt so sofort, ohne dass ein Neustart der App erforderlich wäre.

### 4. Additive Migration, Default `INFO` (V4)

`app.log_level` folgt dem Muster von `manual_match_limit` (ADR-0030): fehlendes Feld in
bestehenden Configs → Default `"INFO"` beim Laden (`migrate_config`), kein
Schema-Versions-Bump, kein MAJOR/MINOR-Bump allein durch dieses Feld (ADR-0043). Gültige
Werte: `"INFO"`, `"WARNING"`, `"DEBUG"` (Großschreibung); ungültiger Wert →
Validierungsfehler beim Laden.

## Verhältnis zu ADR-0026

ADR-0026 bleibt in Kraft: `setup_logging()`, Log-Speicherort, Rotation und die
Umgebungsvariable als Entwickler-Override sind unverändert. Dieses ADR ergänzt eine
zweite, nutzersichtbare Steuerungsebene (`app.log_level`) und definiert deren
Zusammenspiel mit `QSL73_DEBUG` (max-Regel, V1).

## Konsequenzen

**Positiv:**
- Log-Genauigkeit für Endnutzer im Einstellungen-Dialog auffindbar und sofort wirksam.
- Entwickler-Override `QSL73_DEBUG` bleibt vollständig funktionsfähig und kann das
  Nutzer-Level nicht versehentlich verdecken (Anheben-only-Regel).
- Kein Umbau der bestehenden, in ADR-0026 begründeten Start-Reihenfolge.
- Additive Migration ohne Versions-Bump, analog etabliertem Muster (ADR-0030).

**Negativ / Einschränkungen:**
- Kurzes Zeitfenster zwischen `setup_logging()` (früher INFO/DEBUG-Default) und
  `apply_log_level()` (nach Config-Laden) protokolliert mit dem alten Default-Level —
  betrifft nur die wenigen frühen Start-Log-Zeilen (Lock, Start, QR-Status), unkritisch.
