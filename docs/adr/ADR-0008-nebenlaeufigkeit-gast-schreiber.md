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
- **Änderungserkennung:** `PRAGMA data_version` beim Sammeln merken; direkt vor dem Schreiben
  erneut prüfen (Fallback: mtime + Dateigröße).
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
