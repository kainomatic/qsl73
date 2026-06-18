# ADR-0035: Audit-Log + On-demand-Fehlerbericht

**Status:** Accepted

## Kontext

Schritt 7b-2 ergänzt QSL73 um zwei Protokoll-/Meldefähigkeiten:

1. **Audit-Log**: Fachliches Änderungsprotokoll jeder QSO-Bestätigung — welches QSO wurde
   wann mit welcher Route und auf welchem Weg (auto/manuell) bestätigt?
2. **On-demand-Fehlerbericht**: Diagnosedaten bei App-Fehlern strukturiert aufbereiten und
   dem Nutzer zur Weitergabe an GitHub anbieten — ohne automatischen Versand.

Beide Anforderungen kommen aus §10 der Spezifikation.

## Entscheidung

### Teil 1: Audit-Log (`audit.py`, `audit.log`)

**Trennung von Diagnose-Log:** `qsl73.log` ist das Diagnose-Log (technisch, rotierend,
1 MB / 5 Backups). `audit.log` ist das **fachliche Änderungsprotokoll** — dauerhaft,
nicht rotierend, nur tatsächlich geschriebene QSOs.

**Format (eine Zeile pro QSO):**
```
2026-06-18T14:30:00 | doc_id=42 | qsoid=<id> | call=DK1AB | date=2025-11-01 | band=20m | mode=FT8 | route=bureau | source=auto | backup=/path/backup.sqlite
```
Maschinenlesbar durch `|`-Trennzeichen und `key=value`-Format; gleichzeitig menschenlesbar.

**Nur geschriebene QSOs:** Übersprungene QSOs (`result.skipped`) erscheinen NICHT im
Audit-Log. Die Filterung erfolgt in `write_selected` (run.py), das `AuditEntry`-Objekte
nur für qsoids erstellt, die nicht in `result.skipped` auftauchen.

**Aufbewahrung:** `audit.log` rotiert nicht. Es ist ein dauerhaftes Fachprotokoll;
ein Verlust wäre ärgerlich und nicht reparierbar. Diagnose-Logs (qsl73.log) können
regeneriert werden; das Audit-Log nicht.

**Auto vs. Manuell:** `write_selected` erhält `manual_qsoids: set[str] | None = None`.
Qsoids in dieser Menge bekommen `source=manuell`; alle anderen `source=auto`. Default
None → alles auto (abwärtskompatibel). Der Aufrufer (GUI) berechnet die Menge aus
`_manual_pending` bevor er den Schreib-Thread startet.

**Backup-Pfad im Audit:** `WriteResult` erhält `backup_path: Path | None = None`.
`write_confirmations` setzt dieses Feld auf den Rückgabewert von `create_backup`.
`write_selected` trägt den Pfad (oder `–`) in jeden AuditEntry ein.

### Teil 2: On-demand-Fehlerbericht (`error_report.py`, `gui/error_report_dialog.py`)

**Bereinigung (kritisch):** Der Bericht enthält KEINE Secrets (Token, Passwort) und
KEINE QSO-Inhalte. `_strip_secrets` filtert Zeilen aus `qsl73.log`, die einen Secret-
Schlüsselbegriff enthalten; `audit.log` wird NICHT in den Bericht aufgenommen (Fachdaten).

**Kein automatischer Versand:** QSL73 sendet nichts selbst. `build_github_url` baut
eine URL mit URL-kodierten Parametern; `open_in_browser` öffnet den Browser; der Nutzer
entscheidet über Absenden. Dieser Ansatz vermeidet OAuth/API-Zugang und lässt den
Nutzer die Kontrolle.

**Vorschau vor Versand:** Der `ErrorReportDialog` zeigt den bereinigten Bericht in einem
schreibgeschützten ScrolledText an, bevor der Nutzer „Lokal speichern" oder
„Auf GitHub melden" klickt.

**GUI-Platzierung:** Zwei Buttons in der bestehenden Statusleiste des Hauptfensters
(`Log-Ordner öffnen` und `Fehler melden…`). Issue #24 (Menüleiste) ist noch offen;
die Buttons können bei Bedarf später in eine Menüleiste wandern.

## Konsequenzen

**Positiv:**
- Fachliches Änderungsprotokoll entsteht automatisch bei jedem Schreibvorgang
- Fehlermeldung an GitHub ist durch vorausgefüllte URL einfach, ohne API-Zugang
- Bereinigung (Secret-Filter) schützt vor versehentlicher Token-Weitergabe
- Reine Logik (audit.py, error_report.py) ist tk-frei und vollständig testbar
- write_selected bleibt abwärtskompatibel (alle neuen Parameter Optional)

**Negativ:**
- audit.log wächst unbegrenzt (kein Rotieren) — bei jahrelangem Betrieb mit vielen
  Karten kann die Datei groß werden. Angesichts erwarteter Nutzungsfrequenz
  (typ. wenige Dutzend Bestätigungen pro Session) ist das unkritisch.
- GitHub-URL hat eine praktische Längenbegrenzung (~8 KB body) — sehr lange Berichte
  werden von einigen Browsern möglicherweise abgeschnitten. Workaround: lokales Speichern.
