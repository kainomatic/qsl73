# ADR-0003: Schreibreihenfolge — DB zuerst, dann Tags; Vor-Backup nur bei echtem Schreiben

**Status:** Accepted

## Kontext

QSL73 schreibt in zwei Systeme: die Log4OM-SQLite-DB (QSO-Status) und Paperless-ngx
(Tag setzen). Beide müssen konsistent bleiben. Außerdem soll ein Vor-Backup die DB
gegen inhaltliche Fehler sichern.

## Entscheidung

1. **Reihenfolge:** DB-Transaktion erfolgreich → danach Tags setzen.
2. **Vor-Backup** wird nur angelegt, wenn tatsächlich geschrieben wird (Klick „Jetzt
   schreiben"). Kein Backup bei reinem Ansehen oder Abbrechen.
3. WAL-Modus für technische Absturzsicherheit (selbstheilend bei Abbruch).

## Konsequenzen

- DB scheitert → keine Tags (kein Widerspruch möglich).
- Tags scheitern → QSO korrekt bestätigt; fehlendes Tag wird beim nächsten Lauf nachgezogen.
- Vor-Backup schützt vor inhaltlichen Fehlern (falsche Zuordnung), WAL nur vor technischen.
- Backup-Anzahl konfigurierbar, Default 5.
