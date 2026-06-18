"""
Orchestrierungs-/Sicherheitsschicht für Log4OM-DB-Schreibzugriff.

Schritt 5b/5c — bettet write_paper_qsl (5a) in die Sicherheitsschicht ein:
Reihenfolge (ADR-0003): (1) Schema-Check → (2) Fingerabdruck-Check (5c) →
(3) Vor-Backup → (4) Transaktion mit SQLITE_BUSY-Retry und Optimistic Locking (5c).
Paperless-Tags (Schritt 4 in ADR-0003) sind NICHT Teil dieses Moduls.

Öffentliche API:
  validate_schema        — prüft DB-Schema gegen erwartetes Format
  open_wal_connection    — öffnet SQLite-Verbindung im WAL-Modus mit busy_timeout
  create_backup          — WAL-konsistentes Vor-Backup + Checkpoint-Prüfung + Rotation
  get_db_fingerprint     — DB-Stand-Fingerabdruck (data_version; Fallback mtime+size)
  fingerprints_differ    — vergleicht zwei Fingerabdrücke auf DB-Änderung
  is_log4om_running      — prüft ob Log4OM-Prozess läuft (nicht-blockierende Warnung)
  write_confirmations    — Sicherheits-Schreiborchester (Schema → Fingerabdruck →
                           Backup → Transaktion mit Retry + Optimistic Locking)

Empirische Basis: docs/discovery.md §3, ADR-0003, ADR-0004, ADR-0008, ADR-0020.
"""
from __future__ import annotations

import json
import logging
import shutil
import sqlite3
import sys
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from qsl73.log4om_write import QslEntryNotFoundError, write_paper_qsl

_log = logging.getLogger("qsl73")

# ---------------------------------------------------------------------------
# Konstanten — Nebenläufigkeit (ADR-0008)
# ---------------------------------------------------------------------------

# Maximale Anzahl SQLITE_BUSY-Wiederholungsversuche
BUSY_RETRY_COUNT: int = 3
# Pause zwischen Versuchen in Sekunden
BUSY_RETRY_DELAY_S: float = 0.3
# SQLite PRAGMA busy_timeout in Millisekunden.
# Zusammenspiel: SQLite wartet intern bis zu busy_timeout ms vor dem OperationalError-
# Wurf; das manuelle Retry ist die äußere Schicht. Jeder Versuch hat also bis zu
# busy_timeout ms internes Warten, dann retry_delay_s Pause — zusammen defensives
# Warten ohne unbegrenzte Blockade.
BUSY_TIMEOUT_MS: int = 500

# Prozessname Log4OM (Windows, case-insensitiv verglichen)
_LOG4OM_PROCESS_NAME = "log4om2.exe"


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class SchemaError(Exception):
    """Schema weicht vom erwarteten Format ab; Schreiben gesperrt."""


class DatabaseBusyError(Exception):
    """DB bleibt nach allen Retry-Versuchen gesperrt; Abbruch ohne Teilschreibung."""


class DatabaseChangedError(Exception):
    """DB-Fingerabdruck hat sich zwischen Sammeln und Schreiben verändert."""


# ---------------------------------------------------------------------------
# Ergebnis-Datenklasse
# ---------------------------------------------------------------------------


@dataclass
class WriteResult:
    written: int
    skipped: list = field(default_factory=list)  # [{"qsoid": str, "reason": str}]
    backup_path: Path | None = None              # Pfad zur Vor-Backup-Datei (None wenn kein Backup)


# ---------------------------------------------------------------------------
# Schema-Validierung
# ---------------------------------------------------------------------------


def validate_schema(conn: sqlite3.Connection) -> str | None:
    """Prüft ob Log4OM-DB-Schema dem erwarteten Format entspricht.

    Ablauf:
    (1) Tabelle Log vorhanden?
    (2) Spalte qsoconfirmations vorhanden?
    (3) Stichprobe: mind. eine Zeile mit parsebarem JSON und CT='QSL'-Eintrag mit R-Feld.

    Returns:
        None wenn Schema OK; menschenlesbare Abweichungsbeschreibung sonst.
    """
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='Log'"
    ).fetchone()
    if not row:
        return "Tabelle 'Log' nicht in der Datenbank gefunden"

    cols = {r[1] for r in conn.execute("PRAGMA table_info(Log)").fetchall()}
    if "qsoconfirmations" not in cols:
        return "Spalte 'qsoconfirmations' fehlt in Tabelle 'Log'"

    rows = conn.execute(
        "SELECT qsoconfirmations FROM Log WHERE qsoconfirmations IS NOT NULL LIMIT 30"
    ).fetchall()
    if not rows:
        return None  # Leere DB: Schema-Prüfung ohne Stichprobe bestanden

    for (json_str,) in rows:
        try:
            entries = json.loads(json_str)
        except (json.JSONDecodeError, TypeError):
            return f"qsoconfirmations-Wert ist kein gültiges JSON: {json_str[:80]!r}"

        if not isinstance(entries, list):
            return (
                f"qsoconfirmations-Wert ist kein JSON-Array, "
                f"sondern {type(entries).__name__!r}"
            )

        for entry in entries:
            if isinstance(entry, dict) and entry.get("CT") == "QSL" and "R" in entry:
                return None  # Gültige Stichprobe gefunden

    return (
        "Keine Zeile in Log enthält einen CT='QSL'-Eintrag mit erwartetem R-Feld — "
        "Schema weicht ab (Log4OM-Version zu alt oder DB-Format geändert)"
    )


# ---------------------------------------------------------------------------
# Verbindung
# ---------------------------------------------------------------------------


def open_wal_connection(
    db_path: str | Path, busy_timeout_ms: int = BUSY_TIMEOUT_MS
) -> sqlite3.Connection:
    """Öffnet SQLite-Verbindung im WAL-Modus mit busy_timeout (ADR-0008).

    PRAGMA busy_timeout ergänzt das manuelle Retry in write_confirmations:
    SQLite wartet intern bis zu busy_timeout_ms ms vor dem SQLITE_BUSY-Fehler.
    """
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute(f"PRAGMA busy_timeout={busy_timeout_ms}")
    return conn


# ---------------------------------------------------------------------------
# Backup
# ---------------------------------------------------------------------------


def create_backup(db_path: Path, backup_dir: Path, max_count: int = 5) -> Path:
    """WAL-konsistentes Vor-Backup der DB-Datei (ADR-0020).

    Strategie: PRAGMA wal_checkpoint(FULL) auf getrennter Verbindung, dann kopieren.

    Checkpoint-Härtung (5c): Rückgabewert (busy, log, checkpointed) wird ausgewertet.
    Bei unvollständigem Checkpoint (busy==1 oder log!=checkpointed) → WARNING ins Log.
    Der Backup-Vorgang wird trotzdem fortgesetzt: die DB-Daten sind sicher (WAL-Frames
    verbleiben in der .sqlite-wal-Datei), nur das Backup erfasst ggf. nicht alle letzten
    Änderungen einer parallel laufenden Verbindung.

    Args:
        db_path: Pfad zur Log4OM-SQLite-Datei.
        backup_dir: Zielverzeichnis für Backups (wird angelegt wenn nötig).
        max_count: Maximale Anzahl aufbewahrter Backups (Default 5).

    Returns:
        Pfad zur erzeugten Backup-Datei.
    """
    backup_dir.mkdir(parents=True, exist_ok=True)

    chk_conn = sqlite3.connect(str(db_path))
    try:
        result = chk_conn.execute("PRAGMA wal_checkpoint(FULL)").fetchone()
        if result is not None:
            busy, wal_log, checkpointed = result
            if busy == 1 or wal_log != checkpointed:
                _log.warning(
                    "WAL-Checkpoint vor Backup unvollständig "
                    "(busy=%s, log=%s, checkpointed=%s) — "
                    "Backup erfasst möglicherweise nicht alle aktuellen Änderungen. "
                    "Ist Log4OM geöffnet?",
                    busy,
                    wal_log,
                    checkpointed,
                )
    finally:
        chk_conn.close()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    unique = uuid.uuid4().hex[:8]
    dst = backup_dir / f"log4om_{timestamp}_{unique}.sqlite"
    shutil.copy2(str(db_path), str(dst))

    backups = sorted(backup_dir.glob("log4om_*.sqlite"))
    for old in backups[:-max_count]:
        old.unlink(missing_ok=True)

    return dst


# ---------------------------------------------------------------------------
# DB-Stand-Fingerabdruck
# ---------------------------------------------------------------------------


def get_db_fingerprint(db_path: Path) -> dict[str, Any]:
    """Liefert pfadbasierten DB-Stand-Fingerabdruck für Änderungserkennung (ADR-0008).

    Im WAL-Modus gehen SQLite-Commits in die WAL-Datei (.sqlite-wal), NICHT in die
    Hauptdatei. PRAGMA data_version ist per-Connection und nicht für TOCTOU-Vergleiche
    über verschiedene Verbindungen geeignet (Hauptdatei-Change-Counter wird erst bei
    WAL-Checkpoint aktualisiert). Deshalb wird ein pfadbasierter Fingerabdruck verwendet:

    - WAL-Datei (db_path + '-wal'): mtime + size — ändert sich bei jedem WAL-Commit.
    - Hauptdatei: mtime + size — ändert sich bei Checkpoint oder Nicht-WAL-Writes.

    Aufrufmuster:
      fp = get_db_fingerprint(db_path)   # beim Sammeln (Vorschau)
      ...
      write_confirmations(..., snapshot_fingerprint=fp)  # beim Schreiben prüfen

    Args:
        db_path: Pfad zur SQLite-Hauptdatei.

    Returns:
        Dict mit Schlüsseln 'main_mtime', 'main_size', 'wal_mtime', 'wal_size'.
    """
    db_path = Path(db_path)
    main_mtime: float | None = None
    main_size: int | None = None
    try:
        stat = db_path.stat()
        main_mtime = stat.st_mtime
        main_size = stat.st_size
    except OSError:
        pass

    wal_path = Path(str(db_path) + "-wal")
    wal_mtime: float | None = None
    wal_size: int | None = None
    try:
        stat = wal_path.stat()
        wal_mtime = stat.st_mtime
        wal_size = stat.st_size
    except OSError:
        pass  # WAL-Datei existiert nicht (kein offener WAL-Write)

    return {
        "main_mtime": main_mtime,
        "main_size": main_size,
        "wal_mtime": wal_mtime,
        "wal_size": wal_size,
    }


def fingerprints_differ(fp1: dict[str, Any], fp2: dict[str, Any]) -> bool:
    """True wenn die Fingerabdrücke eine DB-Änderung zwischen zwei Zeitpunkten anzeigen.

    Verglichen wird NUR die Hauptdatei (main_mtime + main_size).

    Begründung: Die WAL-Datei wird von SQLite auch bei Lesevorgängen aktualisiert
    (read-marks, WAL-Recovery, SHM-Initialisierung auf Windows), was zu Falsch-Positiven
    führen würde. Die Hauptdatei ändert sich nur bei echten Checkpoint-Vorgängen nach
    externen Schreibvorgängen — das ist der verlässliche Indikator für "jemand anderes
    hat die DB verändert".

    Komplement: Änderungen die noch in der WAL liegen (nicht checkpointed) werden durch
    das Optimistic-Locking pro QSO innerhalb der Transaktion abgefangen (jedes QSO
    wird unmittelbar vor dem Schreiben neu gelesen und auf R-Wert geprüft).
    """
    return (
        fp1.get("main_mtime") != fp2.get("main_mtime")
        or fp1.get("main_size") != fp2.get("main_size")
    )


# ---------------------------------------------------------------------------
# Log4OM-Prozesserkennung
# ---------------------------------------------------------------------------


def _get_running_process_names() -> list[str]:
    """Liefert Liste laufender Prozessnamen (Windows: tasklist; Linux/CI: ps).

    Plattformtolerant: auf Linux/CI gibt ps eine Liste zurück; bei Fehler leere Liste.
    Kein Absturz bei fehlendem Prozess-Tool oder unerwarteten Ausgabeformaten.
    """
    try:
        import subprocess

        if sys.platform == "win32":
            result = subprocess.run(
                ["tasklist", "/fo", "csv", "/nh"],
                capture_output=True,
                text=True,
                timeout=5,
                creationflags=0x08000000,  # CREATE_NO_WINDOW
            )
            names = []
            for line in result.stdout.splitlines():
                stripped = line.strip().strip('"')
                parts = stripped.split('","')
                if parts and parts[0]:
                    names.append(parts[0])
            return names
        else:
            result = subprocess.run(
                ["ps", "-eo", "comm"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            lines = result.stdout.splitlines()
            return [ln.strip() for ln in lines[1:] if ln.strip()]
    except Exception:
        return []


def is_log4om_running(process_names: list[str] | None = None) -> bool:
    """Prüft ob ein Log4OM-Prozess gerade läuft (nicht-blockierende Warnung, ADR-0008).

    Liefert True/False; blockiert nie und verhindert nie das Schreiben — die
    Entscheidung trifft der Aufrufer (GUI). Kapselt den Prozess-Check so, dass
    Tests ohne echten Prozessaufruf auskommen.

    Args:
        process_names: Optionale Liste von Prozessnamen (für Tests); wenn None,
                       wird _get_running_process_names() aufgerufen.

    Returns:
        True wenn Log4OM-Prozess (log4om2.exe, case-insensitiv) erkannt wird.
    """
    if process_names is None:
        process_names = _get_running_process_names()
    return any(name.lower() == _LOG4OM_PROCESS_NAME for name in process_names)


# ---------------------------------------------------------------------------
# Interne Transaktions-Hilfsfunktionen
# ---------------------------------------------------------------------------


def _safe_rollback(conn: sqlite3.Connection) -> None:
    """ROLLBACK, ignoriert Fehler (z. B. keine aktive Transaktion nach BUSY auf BEGIN)."""
    try:
        conn.execute("ROLLBACK")
    except Exception:
        pass


def _run_transaction(
    conn: sqlite3.Connection,
    items: list[tuple[str, str]],
    expected_states: dict[str, str] | None,
) -> tuple[int, list[dict]]:
    """Führt die atomare Schreib-Transaktion mit Optimistic Locking durch.

    BEGIN IMMEDIATE: Schreibsperre wird sofort beim BEGIN angefordert — bei BUSY
    schlägt BEGIN fehl (statt erst beim ersten UPDATE); kein Teilschreiben-Risiko.

    Skip-vs-Rollback-Abgrenzung (ADR-0008):
      - QSO nicht in DB, JSON-Fehler, kein CT='QSL'-Eintrag
        → raise (ValueError / QslEntryNotFoundError) → Aufrufer macht ROLLBACK aller
      - R='Yes' (bereits bestätigt) oder expected_states-Mismatch
        → in skipped eintragen, nächstes QSO (5c-Verhalten)

    Returns:
        (written_count, skipped_list)

    Raises:
        ValueError: Technischer Fehler — QSO nicht gefunden oder JSON-Fehler.
        QslEntryNotFoundError: CT='QSL'-Eintrag fehlt — Schema-Problem.
        sqlite3.OperationalError: SQLITE_BUSY oder anderer SQLite-Fehler.
    """
    conn.execute("BEGIN IMMEDIATE")
    written = 0
    skipped: list[dict] = []

    for qsoid, route in items:
        # Optimistic locking: aktuellen Zustand innerhalb der Transaktion lesen
        row = conn.execute(
            "SELECT qsoconfirmations FROM Log WHERE qsoid = ?", (qsoid,)
        ).fetchone()
        if row is None:
            # Technischer Fehler → Aufrufer macht ROLLBACK aller (5b-Verhalten)
            raise ValueError(f"QSO nicht gefunden: qsoid={qsoid!r}")

        try:
            current_conf = json.loads(row[0])
        except (json.JSONDecodeError, TypeError) as exc:
            # Technischer Fehler → Aufrufer macht ROLLBACK aller (5b-Verhalten)
            raise ValueError(
                f"qsoconfirmations ist kein gültiges JSON für {qsoid!r}"
            ) from exc

        if not isinstance(current_conf, list):
            raise ValueError(f"qsoconfirmations ist kein JSON-Array für {qsoid!r}")

        qsl_entry = next(
            (e for e in current_conf if isinstance(e, dict) and e.get("CT") == "QSL"),
            None,
        )
        if qsl_entry is None:
            # Schema-Problem → Technischer Fehler → Aufrufer macht ROLLBACK aller
            raise QslEntryNotFoundError(
                f"CT='QSL'-Eintrag fehlt für {qsoid!r} — Schema-Validierung prüfen"
            )

        current_r = qsl_entry.get("R", "")

        # 5c-Verhalten: bereits bestätigt → ÜBERSPRINGEN (nicht ROLLBACK)
        if current_r == "Yes":
            skipped.append({"qsoid": qsoid, "reason": "bereits bestätigt (R='Yes')"})
            continue

        # 5c-Verhalten: expected_states-Mismatch → ÜBERSPRINGEN (nicht ROLLBACK)
        if expected_states is not None:
            expected_r = expected_states.get(qsoid)
            if expected_r is not None and current_r != expected_r:
                skipped.append({
                    "qsoid": qsoid,
                    "reason": (
                        f"R-Feld verändert: erwartet={expected_r!r},"
                        f" aktuell={current_r!r}"
                    ),
                })
                continue

        # Sicherheitsnetz: unbekannter R-Wert → ÜBERSPRINGEN (5c-Verhalten)
        if current_r not in ("No", "Requested"):
            skipped.append({
                "qsoid": qsoid,
                "reason": f"R-Feld hat unbekannten Wert: {current_r!r}",
            })
            continue

        # Normaler Schreibpfad; technische Fehler aus write_paper_qsl → ROLLBACK aller
        write_paper_qsl(conn, qsoid, route)
        written += 1

    conn.execute("COMMIT")
    return written, skipped


# ---------------------------------------------------------------------------
# Öffentliche Schreib-Orchestrierung
# ---------------------------------------------------------------------------


def write_confirmations(
    db_path: str | Path,
    items: list[tuple[str, str]],
    backup_dir: Path,
    backup_count: int = 5,
    snapshot_fingerprint: dict | None = None,
    expected_states: dict[str, str] | None = None,
    retry_count: int = BUSY_RETRY_COUNT,
    retry_delay_s: float = BUSY_RETRY_DELAY_S,
    busy_timeout_ms: int = BUSY_TIMEOUT_MS,
) -> WriteResult:
    """Sicherheits-Schreiborchester: Schema → Fingerabdruck → Backup → Transaktion.

    Reihenfolge (ADR-0003 + ADR-0008):
      (1) Schema-Check → SchemaError bei Abweichung (kein Backup, keine Transaktion).
      (2) Fingerabdruck-Check → DatabaseChangedError wenn DB seit Sammeln geändert.
      (3) Vor-Backup → WAL-konsistente Kopie (nur wenn items nicht leer).
      (4) Atomare Transaktion mit SQLITE_BUSY-Retry und pro-QSO Optimistic Locking.

    Skip-vs-Rollback-Abgrenzung (ADR-0008):
      Technische Fehler (QSO nicht in DB, JSON-Fehler, kein CT='QSL'-Eintrag)
        → ROLLBACK aller QSOs (kein Teilschreiben bei unbekanntem Zustand).
      QSO zwischenzeitlich bestätigt (R='Yes') oder expected_states-Mismatch
        → dieses QSO ÜBERSPRINGEN, Rest normal schreiben.

    Args:
        db_path: Pfad zur Log4OM-SQLite-Datei.
        items: Liste von (qsoid, route)-Paaren. Leere Liste = no-op.
        backup_dir: Zielverzeichnis für Vor-Backups.
        backup_count: Maximale Anzahl aufbewahrter Backups (Default 5).
        snapshot_fingerprint: Fingerabdruck beim Sammeln (get_db_fingerprint);
            wenn angegeben und abweichend → DatabaseChangedError.
        expected_states: Mapping qsoid → erwarteter R-Wert beim Sammeln;
            Mismatch → ÜBERSPRINGEN (nicht ROLLBACK).
        retry_count: Anzahl SQLITE_BUSY-Versuche (Default BUSY_RETRY_COUNT=3).
        retry_delay_s: Wartezeit zwischen Versuchen in s (Default BUSY_RETRY_DELAY_S=0.3).
        busy_timeout_ms: SQLite PRAGMA busy_timeout in ms (Default BUSY_TIMEOUT_MS=500).

    Returns:
        WriteResult mit Anzahl geschriebener und übersprungener QSOs.

    Raises:
        SchemaError: Schema weicht ab.
        DatabaseChangedError: DB seit Sammeln verändert.
        DatabaseBusyError: DB nach retry_count Versuchen noch gesperrt.
        ValueError: Technischer Fehler innerhalb der Transaktion → ROLLBACK.
        QslEntryNotFoundError: CT='QSL'-Eintrag fehlt → ROLLBACK.
    """
    db_path = Path(db_path)
    conn = open_wal_connection(db_path, busy_timeout_ms=busy_timeout_ms)
    try:
        # (1) Schema-Check
        deviation = validate_schema(conn)
        if deviation:
            raise SchemaError(deviation)

        # (2) Fingerabdruck-Check (5c): pfadbasiert — WAL + Hauptdatei
        if snapshot_fingerprint is not None:
            current_fp = get_db_fingerprint(db_path)
            if fingerprints_differ(snapshot_fingerprint, current_fp):
                raise DatabaseChangedError(
                    "Die Log4OM-DB wurde seit dem letzten Einlesen verändert — "
                    "bitte neu einlesen, um auf Basis aktueller Daten zu schreiben."
                )

        # (3) Vor-Backup (nur bei tatsächlichem Schreiben, ADR-0003)
        backup_path: Path | None = None
        if items:
            backup_path = create_backup(db_path, backup_dir, max_count=backup_count)

        # (4) Atomare Transaktion mit SQLITE_BUSY-Retry (ADR-0008)
        written = 0
        skipped: list[dict] = []

        for attempt in range(retry_count):
            try:
                written, skipped = _run_transaction(conn, items, expected_states)
                break  # Erfolg
            except sqlite3.OperationalError as exc:
                _safe_rollback(conn)
                msg = str(exc).lower()
                if "locked" in msg or "busy" in msg:
                    if attempt < retry_count - 1:
                        time.sleep(retry_delay_s)
                        continue
                    raise DatabaseBusyError(
                        f"Log4OM-DB bleibt nach {retry_count} Versuchen gesperrt — "
                        "bitte Log4OM schließen und erneut versuchen."
                    ) from exc
                raise  # anderer OperationalError (nicht BUSY) → normal weiterwerfen
            except Exception:
                _safe_rollback(conn)
                raise

        return WriteResult(written=written, skipped=skipped, backup_path=backup_path)
    finally:
        conn.close()
