# ADR-0039: Erwartete Lauf-/Schreibfehler benutzerfreundlich anzeigen

**Status:** Accepted

## Kontext

Issue #18: Wenn die Log4OM-DB sich zwischen `run_pass` und `write_selected` ändert
(`DatabaseChangedError` — Optimistic Locking, ADR-0008), fängt der Controller die
Exception generisch ab und erzeugt ein `ErrorEvent` mit `str(exc)` + rohem Traceback.
Das `main_window` zeigt `show_error("Fehler", str(exc), traceback)`, was für Endnutzer
kryptisch ist und keinen Handlungshinweis gibt.

Gleiches gilt für andere erwartbare Fehlertypen (`SchemaError`, `DatabaseBusyError`,
`QslEntryNotFoundError`, `PaperlessConnectionError`, `PaperlessAuthError` u. a.),
die alle sinnvolle, verständliche Erklärungen haben.

Vorbild: ADR-0033 (Config-Fehlerdialog) — "erwarteter Fehler → verständlicher Dialog
mit Handlungsoption statt Traceback".

## Entscheidung

### 1. Mapping-Modul `gui/error_messages.py`

Eine reine (tk-freie, testbare) Funktion `classify_error(exc) → ErrorClassification`
bildet bekannte Fehlertypen auf `(title, user_message, status_message, is_expected)` ab.

Abgedeckte erwartete Fehlertypen:
- `DatabaseChangedError` → "Datenbank hat sich geändert" + Hinweis "Durchlauf neu starten"
- `SchemaError` → "Datenbankformat nicht erkannt"
- `DatabaseBusyError` → "Datenbank gesperrt"
- `QslEntryNotFoundError` → "QSL-Eintrag nicht gefunden"
- `PaperlessConnectionError` → "Paperless nicht erreichbar"
- `PaperlessAuthError` → "Paperless-Authentifizierung fehlgeschlagen"
- `PaperlessNotFoundError` / `PaperlessAPIError` → "Paperless-API-Fehler"
- alle anderen → `is_expected=False`, Titel "Unerwarteter Fehler"

### 2. `ErrorEvent` — abwärtskompatibel erweitert

Neue Felder mit Defaults (bestehende Tests konstruieren `ErrorEvent(exc, traceback_str)`
ohne die neuen Felder — weiterhin gültig):
```
user_message: str | None = None
error_title: str = "Fehler"
status_message: str | None = None
is_expected: bool = False
```

### 3. Controller befüllt die neuen Felder

Beide `except`-Blöcke (`start_run`, `start_write`) rufen `classify_error(exc)` auf
und legen das Ergebnis in das `ErrorEvent`.

### 4. `main_window._handle_event(ErrorEvent)` — differenzierte Anzeige

- `is_expected=True`: `show_error` mit Klartext-Nachricht, **ohne** aufklappbaren
  Traceback-Bereich — der Traceback ist irrelevant für den Nutzer.
- `is_expected=False`: wie bisher — Traceback im `detail`-Bereich von `show_error`.
- Status-Zeile: `event.status_message` statt "Fehler: …".

### 5. Schreibsicherheit unverändert

Das Schreib-Sicherheitsmodell (ADR-0008 Optimistic Locking) ist **nicht** betroffen:
`DatabaseChangedError` wird weiterhin geworfen und stoppt den Schreibvorgang. Geändert
wird nur die **Anzeige**, nicht das Verhalten.

## Konsequenzen

**Positiv:**
- Klarer Handlungshinweis für den häufigsten Fehler (`DatabaseChangedError`).
- Mapping-Logik tk-frei und vollständig getestet.
- Abwärtskompatibel: bestehende `ErrorEvent`-Konstruktoren funktionieren weiterhin.
- Unerwartete Fehler zeigen weiterhin den Traceback (Fehleranalyse bleibt möglich).

**Negativ / Einschränkungen:**
- Neue Fehlertypen müssen explizit in `classify_error` ergänzt werden, sonst landen
  sie im "Unerwarteter Fehler"-Zweig (ist konservativ — kein Datenverlust).
