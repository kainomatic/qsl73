# ADR-0026: Diagnose-Logging (qsl73.log) + QR-Startwarnung

**Status:** Accepted

## Kontext

Der Realtest 2026-06-17 zeigte zwei Probleme:

1. **Kein sichtbares Log:** `logging.getLogger("qsl73")` schreibt ins Leere — es war kein
   Handler konfiguriert. Der Token-Scan in `run.py` (ADR-0025) nutzt bereits `_log.debug(…)`,
   aber diese Ausgaben verschwanden spurlos. Probleme wie „OCR liefert call_from=OE6DRG,
   GUI zeigt kein Rufzeichen" ließen sich ohne Logdatei nicht nachvollziehen.

2. **Fehlende QR-Bibliothek still verschluckt:** `decode_qr_from_pdf` gibt `None` zurück
   wenn `zxing-cpp` / `pymupdf` fehlen — ohne sichtbaren Hinweis. Der Nutzer weiß nicht,
   dass QR-Auswertung deaktiviert ist.

KONZEPT §10 sieht zwei Logs vor: `qsl73.log` (technisch) und `audit.log` (fachlich).
Dieser Schritt implementiert nur `qsl73.log` (Issue #14, Schritt 7a). `audit.log` und der
On-demand-Fehler-Bericht folgen in Schritt 7b.

## Entscheidung

### Log-Speicherort

`%APPDATA%\QSL73\logs\qsl73.log` (Stable) bzw. `%APPDATA%\QSL73-Beta\logs\qsl73.log` (Beta).
Folgt der APPDATA-Logik aus §2 und §16 — Stable/Beta vollständig getrennt.

`get_log_dir()` liest `CHANNEL` aus `qsl73.__version__` — kein Config-Parameter nötig.
Der Rückgabewert dient gleichzeitig als „Log-Ordner öffnen"-Mechanismus für §9-GUI-Button
(Issue #15, Schritt 7b).

### Level-Schalter

Default: `INFO`. Anhebung auf `DEBUG` über `QSL73_DEBUG=1` (Umgebungsvariable).
Alternativ `debug=True`-Parameter in `setup_logging()` für Tests und Programmstart-Overrides.

Warum Umgebungsvariable statt Config-Option:
- Logging muss **vor** dem Config-Laden aktiv sein (damit Config-Fehler geloggt werden).
- Umgebungsvariable ist einfacher für temporäre Debug-Sessions (kein YAML-Edit nötig).
- Der bestehende `_log.debug`-Token-Scan (ADR-0025) wird damit sofort nutzbar.

### Idempotenz

`setup_logging()` prüft auf vorhandenen `RotatingFileHandler` im `"qsl73"`-Logger.
Wird er gefunden, kehrt die Funktion sofort zurück. Mehrfachaufruf fügt keinen zweiten
Handler hinzu — wichtig für Tests und Hot-Reload-Szenarien.

### Trennung Diagnose-Log vs. Audit-Log

| Log | Datei | Inhalt | Implementiert |
|-----|-------|--------|---------------|
| Diagnose-Log | `qsl73.log` | Technische Ereignisse (Level-basiert) | Schritt 7a (dieses ADR) |
| Audit-Log | `audit.log` | Fachliche Änderungen (QSO-Daten) | Schritt 7b |

### QR-Verfügbarkeitswarnung

`qr_backend_status()` in `qr.py` exponiert `_FITZ_OK`/`_ZXING_OK` als `dict[str, bool]`.
Beim App-Start (nach Single-Instance-Lock-Erwerb):

1. `WARNING` ins Diagnose-Log — maschinenlesbar, bleibt dauerhaft erhalten.
2. GUI-Statuszeile erhält initialen Hinweis-Text (nicht-blockierend, sofort sichtbar,
   verschwindet beim nächsten Lauf-Start automatisch).

Keine Funktionsänderung am QR-Pfad selbst — nur Statusabfrage + Anzeige.

### Rotation

1 MB pro Datei, 5 Backup-Dateien → max. ~6 MB Logdaten. Entspricht §10-Vorgabe.

### Was nicht geloggt wird (§10-Sicherheitsleitplanke)

Token, Passwörter, Paperless-URL mit Credentials — niemals in Log-Call-Argumenten.
Die hinzugefügten Log-Punkte in `run.py` protokollieren ausschließlich:
`doc_id`, `source` ("qr"/"ocr"/"none"), `outcome.result.name`, Mengenangaben (int).

## Konsequenzen

- `setup_logging()` wird in `gui/app.py::run_app()` als erste Aktion aufgerufen.
- `run.py`: Lauf-Start/Ende (INFO), pro Karte Quelle+Ergebnis (INFO), Schreibvorgang (INFO).
  Token-Scan-Details bereits in DEBUG (ADR-0025, mit doc_id ergänzt).
- `qr.py`: neue öffentliche Funktion `qr_backend_status()` → testbar ohne Imports.
- Tests: 16 neue Tests in `test_logging_setup.py`; darunter Negativtest (kein Secret im Log).
