# ADR-0020: WAL-Checkpoint-Strategie für Vor-Backup

**Status:** Accepted

## Kontext

Beim WAL-Modus (PRAGMA journal_mode=WAL) schreibt SQLite committete Daten
zuerst in die WAL-Datei (`.sqlite-wal`), nicht sofort in die Hauptdatei.
Ein simples Kopieren der Hauptdatei ohne vorherigen WAL-Checkpoint ergibt
eine inkonsistente Sicherung: Die WAL-Daten fehlen in der Kopie.

Alternative a) Sowohl Hauptdatei als auch WAL-Datei kopieren: erfordert
atomares Kopieren beider Dateien gleichzeitig — auf Windows-Dateisystem
nicht garantiert konsistent.

Alternative b) Verbindung schließen und sofort kopieren: SQLite führt
beim Schließen einen Checkpoint durch, aber nur wenn keine anderen Leser
aktiv sind. Schließen unterbricht den Verbindungs-Lebenszyklus.

Alternative c) `PRAGMA wal_checkpoint(FULL)` auf der bestehenden Verbindung
direkt vor dem Kopieren: Zwingt SQLite, alle committeten WAL-Frames in die
Hauptdatei zu schreiben. Danach enthält die Hauptdatei alle Daten; die
Kopie davon ist standalone konsistent ohne WAL-Begleiter.

## Entscheidung

Vor jeder Backup-Kopie wird `PRAGMA wal_checkpoint(FULL)` auf der offenen
Schreibverbindung ausgeführt. Erst danach wird die Hauptdatei kopiert.
Die WAL-Datei wird NICHT kopiert (die Kopie ist standalone konsistent).

FULL-Checkpoint blockiert, bis alle aktiven Leser-Transaktionen abgeschlossen
sind, und schreibt dann alle ausstehenden WAL-Frames in die Hauptdatei.
Da QSL73 in der Backup-Phase keine offene Leser-Transaktion hält,
ist FULL in der Praxis gleichwertig mit PASSIVE (aber expliziter).

## Konsequenzen

- Backup-Datei ist standalone konsistent (kann ohne WAL-Datei geöffnet werden).
- Backup wird angelegt bevor die Schreib-Transaktion beginnt → schützt den
  Zustand VOR den geplanten Änderungen (inhaltliche Sicherung).
- Keine Datei-System-Atomarität nötig; nur die eine Hauptdatei wird kopiert.
- Bei laufendem Log4OM (externes Schreiben in die WAL) kann FULL kurz warten;
  das ist tolerierbar im Backup-Schritt (Nebenläufigkeit ist 5c-Thema).
