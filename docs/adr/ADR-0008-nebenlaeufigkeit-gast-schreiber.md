# ADR-0008: Nebenläufigkeit — QSL73 als „Gast" der DB; SQLITE_BUSY-Retry; Optimistic Locking

**Status:** Accepted

## Kontext

Log4OM ist der Eigentümer der SQLite-DB. Nutzer können Log4OM parallel zu QSL73 betreiben.
SQLite erlaubt im WAL-Modus beliebig viele Leser + genau einen Schreiber; kollidierende
Schreibversuche liefern SQLITE_BUSY. Zwischen Sammeln (Vorschau) und Schreiben können
Daten veralten (time-of-check/time-of-use).

## Entscheidung

- **Gastschreiber-Prinzip:** QSL73 schreibt defensiv, ohne exklusiven Zugriff vorauszusetzen.
- **SQLITE_BUSY:** Kurz warten + begrenzt wiederholen (3 Versuche, ~300 ms Pause); bleibt
  gesperrt → sauberer Abbruch mit klarer Meldung, kein Crash.
- **Änderungserkennung:** DB-Stand-Fingerabdruck beim Sammeln merken; direkt vor dem Schreiben
  erneut prüfen (Implementierungsdetails: Abschnitt „Implementierung" unten).
- **Optimistic Locking pro QSO:** In der Schreib-Transaktion für jedes QSO verifizieren,
  dass es noch unbestätigt und unverändert ist.
- **Reaktionsmodell:** Einzeln veränderte QSOs → überspringen + audit.log-Eintrag; großer
  Fingerabdruck-Unterschied → gesamten Schreibvorgang abbrechen + Neu-Einlesen anbieten.
- **Log4OM-Running-Warnung:** Prozess-Check vor dem Schreiben; nicht-blockierende Warnung;
  Nutzer entscheidet.

## Konsequenzen

- Kein Datenverlust durch Parallelzugriff; kein unvollständig geschriebener Zustand.
- Nutzer wird informiert, nicht blockiert.
- Leichter Overhead durch Änderungserkennung und pro-QSO-Check (vernachlässigbar bei ~1000 QSOs).

---

## Implementierungsdetails (Schritt 5c)

### SQLITE_BUSY-Retry und busy_timeout

`PRAGMA busy_timeout=500` (ms) + manueller Retry: busy_timeout lässt SQLite intern warten
bevor es SQLITE_BUSY wirft. Manueller Retry (3 Versuche, 300 ms Pause) ist die äußere Schicht.
Kombination gibt Log4OM genug Zeit um kurze Lock-Perioden selbst aufzulösen.

`BEGIN IMMEDIATE` statt `BEGIN` (deferred): Schreibsperre wird sofort beim Transaktionsbeginn
angefordert — BUSY schlägt früh und klar fehl, kein Risiko eines Teilschreibens (bei deferred
könnte BEGIN gelingen und erst das erste UPDATE BUSY sein).

### Fingerabdruck-Strategie (Hauptdatei-basiert)

Ursprünglich geplant: `PRAGMA data_version`. Problem in WAL-Modus: `data_version` ist
per-Verbindung und zeigt Änderungen anderer Verbindungen nur an, wenn die aktuelle Verbindung
einen neuen Snapshot öffnet. Die Hauptdatei-Change-Counter (bytes 24-27) wird in WAL-Modus erst
bei Checkpoint aktualisiert → `data_version` bei neuen Verbindungen spiegelt WAL-only-Writes
nicht zuverlässig wider.

**Implementiert: Hauptdatei mtime + size** — Checkpoint-basierte Erkennung:
- Log4OM schreibt → WAL wächst
- SQLite auto-checkpoint oder Log4OM-close löst Checkpoint aus → Hauptdatei mtime ändert sich
- `fingerprints_differ` erkennt diese mtime-Änderung zuverlässig

WAL-Datei-mtime wird NICHT verglichen: SQLite WAL-Recovery schreibt beim ersten
Verbindungsaufbau neue Salts in den WAL-Header (ändert mtime ohne neue Datenframes) → würde
Falsch-Positive erzeugen. WAL-Dateifelder (mtime, size) sind im Fingerabdruck als
Diagnosefelder enthalten, aber nicht Teil des Vergleichs.

**Komplement: Optimistic Locking** — WAL-only-Änderungen (noch kein Checkpoint) werden durch
das pro-QSO-Locking abgefangen: jedes ZielQSO wird innerhalb der Transaktion neu gelesen und
auf R-Wert geprüft. So ist die Zwei-Schichten-Verteidigung vollständig:
1. Fingerabdruck-Check: drastic/strukturelle Änderungen (nach Checkpoint)
2. Optimistic Locking: individuelle QSO-Modifikationen (auch vor Checkpoint)

### Skip-vs-Rollback-Abgrenzung

| Situation | Reaktion | Begründung |
|-----------|----------|------------|
| QSO nicht in DB | ROLLBACK alle | Technischer Fehler — unbekannter Zustand |
| qsoconfirmations JSON-Fehler | ROLLBACK alle | Technischer Fehler |
| CT='QSL'-Eintrag fehlt | ROLLBACK alle | Schema-Problem → lieber nicht schreiben |
| R='Yes' (schon bestätigt) | ÜBERSPRINGEN (skip) | Normaler Nebenläufigkeitsfall |
| expected_states-Mismatch | ÜBERSPRINGEN (skip) | QSO zwischen Sammeln und Schreiben geändert |
| R hat unbekannten Wert | ÜBERSPRINGEN (skip) | Defensiv: nicht schreiben bei unbekanntem Zustand |

### WAL-Checkpoint-Härtung (ADR-0020-Erweiterung)

`PRAGMA wal_checkpoint(FULL)` gibt `(busy, log, checkpointed)` zurück. Bei
`busy==1` oder `log != checkpointed` war der Checkpoint nicht vollständig (z. B. externe
Leser-Transaktion). Statt stillschweigend fortzufahren → WARNING ins qsl73-Log. Das Backup
wird trotzdem angelegt (die Daten sind sicher in WAL+Hauptdatei; nur das Backup hat
möglicherweise nicht den allerletzten Stand externer Verbindungen).

### Log4OM-Prozesserkennung

`is_log4om_running(process_names)`: Sucht `log4om2.exe` (case-insensitiv) in der
Prozessliste. Plattformtolerant: Windows → `tasklist /fo csv /nh`; Linux/CI → `ps -eo comm`.
`process_names`-Parameter für Test-Mockbarkeit ohne echten Prozessaufruf.
Liefert bool, blockiert nie — die Entscheidung liegt beim Aufrufer (GUI).
