#!/usr/bin/env python3
"""Erstellt TESTDB_DH3KR_schreibtest.sqlite — Testkopie der Log4OM-DB für Schreib-Test.

Issue #8 (Szenario B): Schreib-Pfad (write_selected → log4om_db.write_confirmations)
gegen eine DB, in der stationcallsign="DH3KR" vorkommt, end-to-end testen — ohne dass
own_callsign in der Config geändert werden muss. Prüft die Zugehörigkeitserkennung über
DB-stationcallsign-Werte (ADR-0013).

WICHTIG: Diese Datenbank enthält KÜNSTLICHE, nicht-reale QSO-Daten.
NUR gegen TESTDB_DH3KR_schreibtest.sqlite testen.
NIEMALS gegen TESTDB_DF1DS_Mai24_backup.sqlite (Original) schreiben.

Eingefügte QSOs (stationcallsign="DH3KR", ownercallsign="DH3KR"):

  Callsign  Datum/Zeit UTC         Band  Mode  Erwartetes Matching
  OE6DRG    2025-04-23 12:23:00Z   20m   FT8   SICHER  (passt zu OE6DRG-Karte)
  DG5MLA    2025-04-26 19:52:00Z   60m   FT8   SICHER  (passt zu DG5MLA-Karte; EQSL bereits bestätigt → ADR-0015-Info)
  DK8NE     2025-04-02 19:42:00Z   6m    FT8   SICHER  (passt zu DK8NE-Karte; QR→Band=6m eindeutig)
  DK8NE     2025-04-02 09:00:00Z   20m   FT8   AUSGESCHLOSSEN (Band 20m widerspricht Karte 6m)

Karten-QSO-Zuordnung:
  OE6DRG-Karte → OE6DRG 2025-04-23 20m FT8  → SICHER
  DG5MLA-Karte → DG5MLA 2025-04-26 60m FT8  → SICHER (+EQSL-Bestätigung sichtbar)
  DK8NE-Karte  → DK8NE  2025-04-02 6m  FT8  → SICHER (6m-QSO)
  DK8NE-Karte  → DK8NE  2025-04-02 20m FT8  → AUSGESCHLOSSEN durch Band-Widerspruch

Nutzung:
  python tools/create_dh3kr_test_db.py

Ausgabe: docs/testdateien/TESTDB_DH3KR_schreibtest.sqlite

EINSCHRAENKUNG — Anzeige in Log4OM (Realtest-Befund 2026-06-18):
Die hier erzeugten QSOs enthalten nur die match-relevanten Minimalfelder
(dxcc=0, contactreferences=None, programid leer, qsocomplete leer).
Log4OM zeigt die QSL-Bestaetigung solcher UNVOLLSTAENDIGER QSOs NICHT in der
Bearbeitungsmaske/Liste an — obwohl das qsoconfirmations korrekt geschrieben wurde.
Dieses Skript ist daher geeignet fuer:
  - DB-Schreib-Verifikation (Schema-Check, Byte-Vergleich, load_qso_candidates)
  - Integrationstests gegen das Schreib-API
Nicht geeignet fuer:
  - Visuelle Anzeige-Tests in Log4OM (dafuer: QSOs manuell in Log4OM loggen)
QSL73 selbst ist NICHT betroffen — mit echt geloggten QSOs funktioniert die Anzeige
einwandfrei (verifiziert).
"""
from __future__ import annotations

import hashlib
import json
import shutil
import sqlite3
import sys
from pathlib import Path

# Damit qsl73-Module direkt importierbar sind (ohne pip install -e .)
_REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_REPO_ROOT / "src"))

from qsl73.log4om_db import validate_schema  # noqa: E402
from qsl73.run import load_qso_candidates  # noqa: E402

# ---------------------------------------------------------------------------
# Pfade
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).parent.parent
TESTDB_DIR = REPO_ROOT / "docs" / "testdateien"
ORIGINAL_DB = TESTDB_DIR / "TESTDB_DF1DS_Mai24_backup.sqlite"
COPY_DB = TESTDB_DIR / "TESTDB_DH3KR_schreibtest.sqlite"

EXPECTED_ORIGINAL_SHA256 = (
    "8f96afe5ade88c358a9fe3496e27e39377d24c2b58d55a6f28e6e8eb48e6a8fc"
)

# ---------------------------------------------------------------------------
# QSO-Daten
# ---------------------------------------------------------------------------

# Offener Ausgangszustand (alle 7 CT-Typen unbestätigt)
_OPEN_CONFIRMATIONS = [
    {"CT": "QSL",     "S": "No", "R": "No", "SV": "Electronic", "RV": "Electronic"},
    {"CT": "EQSL",    "S": "No", "R": "No", "SV": "Electronic", "RV": "Electronic"},
    {"CT": "LOTW",    "S": "No", "R": "No", "SV": "Electronic", "RV": "Electronic"},
    {"CT": "QRZCOM",  "S": "No", "R": "No", "SV": "Electronic", "RV": "Electronic"},
    {"CT": "HAMQTH",  "S": "No", "R": "No", "SV": "Electronic", "RV": "Electronic"},
    {"CT": "HRDLOG",  "S": "No", "R": "No", "SV": "Electronic", "RV": "Electronic"},
    {"CT": "CLUBLOG", "S": "No", "R": "No", "SV": "Electronic", "RV": "Electronic"},
]

# EQSL bereits bestätigt (für DG5MLA — testet ADR-0015-Anzeige)
_EQSL_CONFIRMED_CONFIRMATIONS = [
    {"CT": "QSL",     "S": "No", "R": "No",  "SV": "Electronic", "RV": "Electronic"},
    {"CT": "EQSL",    "S": "Yes", "R": "Yes", "SV": "Electronic", "RV": "Electronic",
     "SD": "2025-04-27T00:00:00Z", "RD": "2025-04-28T00:00:00Z"},
    {"CT": "LOTW",    "S": "No", "R": "No",  "SV": "Electronic", "RV": "Electronic"},
    {"CT": "QRZCOM",  "S": "No", "R": "No",  "SV": "Electronic", "RV": "Electronic"},
    {"CT": "HAMQTH",  "S": "No", "R": "No",  "SV": "Electronic", "RV": "Electronic"},
    {"CT": "HRDLOG",  "S": "No", "R": "No",  "SV": "Electronic", "RV": "Electronic"},
    {"CT": "CLUBLOG", "S": "No", "R": "No",  "SV": "Electronic", "RV": "Electronic"},
]

# qsoid: 17-stellig, zeitstempel-basiert (YYYYMMDDHHMMSS + 3-stellige Seriennummer)
# Alle DH3KR-QSOs — Seriennummern 001–004 zur Kollisionsvermeidung
DH3KR_QSOS = [
    {
        "qsoid":            "20250423122300001",
        "callsign":         "OE6DRG",
        "qsodate":          "2025-04-23 12:23:00Z",
        "band":             "20m",
        "mode":             "FT8",
        "stationcallsign":  "DH3KR",
        "ownercallsign":    "DH3KR",
        "qsoconfirmations": _OPEN_CONFIRMATIONS,
        # Erwartetes Matching: SICHER (passt zu OE6DRG-Karte)
    },
    {
        "qsoid":            "20250426195200002",
        "callsign":         "DG5MLA",
        "qsodate":          "2025-04-26 19:52:00Z",
        "band":             "60m",
        "mode":             "FT8",
        "stationcallsign":  "DH3KR",
        "ownercallsign":    "DH3KR",
        "qsoconfirmations": _EQSL_CONFIRMED_CONFIRMATIONS,
        # Erwartetes Matching: SICHER + EQSL-Bestätigungs-Info (ADR-0015)
    },
    {
        "qsoid":            "20250402194200003",
        "callsign":         "DK8NE",
        "qsodate":          "2025-04-02 19:42:00Z",
        "band":             "6m",
        "mode":             "FT8",
        "stationcallsign":  "DH3KR",
        "ownercallsign":    "DH3KR",
        "qsoconfirmations": _OPEN_CONFIRMATIONS,
        # Erwartetes Matching: SICHER (QR-Code-Band=6m trifft eindeutig dieses QSO)
    },
    {
        "qsoid":            "20250402090000004",
        "callsign":         "DK8NE",
        "qsodate":          "2025-04-02 09:00:00Z",
        "band":             "20m",
        "mode":             "FT8",
        "stationcallsign":  "DH3KR",
        "ownercallsign":    "DH3KR",
        "qsoconfirmations": _OPEN_CONFIRMATIONS,
        # Erwartetes Matching: AUSGESCHLOSSEN — Band 20m widerspricht Karte 6m
        # → belegt Band-Disambiguierung (Grenzfall-QSO)
    },
]


# ---------------------------------------------------------------------------
# Helfer
# ---------------------------------------------------------------------------


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _insert_qsos(conn: sqlite3.Connection) -> None:
    sql = """
        INSERT INTO Log (
            qsoid, callsign, band, mode, qsodate,
            stationcallsign, ownercallsign, qsoconfirmations,
            dxcc, freq, freqrx, qsorandom
        ) VALUES (
            :qsoid, :callsign, :band, :mode, :qsodate,
            :stationcallsign, :ownercallsign, :qsoconfirmations,
            0, 0, 0, 1
        )
    """
    for qso in DH3KR_QSOS:
        row = dict(qso)
        row["qsoconfirmations"] = json.dumps(qso["qsoconfirmations"], separators=(",", ":"))
        conn.execute(sql, row)
    conn.commit()


# ---------------------------------------------------------------------------
# Hauptprogramm
# ---------------------------------------------------------------------------


def main() -> int:
    print("=== create_dh3kr_test_db.py ===")

    # Schritt 1: Original-DB prüfen
    if not ORIGINAL_DB.exists():
        print(f"FEHLER: Original-DB nicht gefunden: {ORIGINAL_DB}")
        return 1

    sha = _sha256(ORIGINAL_DB)
    if sha != EXPECTED_ORIGINAL_SHA256:
        print(f"WARNUNG: SHA256 der Original-DB weicht ab!")
        print(f"  Erwartet: {EXPECTED_ORIGINAL_SHA256}")
        print(f"  Ist:      {sha}")
        print("  Fortfahren trotzdem (Original wird NICHT verändert).")
    else:
        print(f"Original-DB SHA256 OK: {sha[:16]}…")

    # Schritt 2: Kopie anlegen
    shutil.copy2(str(ORIGINAL_DB), str(COPY_DB))
    print(f"Kopie angelegt: {COPY_DB}")

    # Schritt 3: QSOs einfügen
    conn = sqlite3.connect(str(COPY_DB))
    try:
        _insert_qsos(conn)
        print(f"{len(DH3KR_QSOS)} QSOs eingefügt.")
    finally:
        conn.close()

    # Schritt 4a: Schema-Check
    conn2 = sqlite3.connect(str(COPY_DB))
    try:
        deviation = validate_schema(conn2)
    finally:
        conn2.close()

    if deviation:
        print(f"FEHLER: Schema-Check fehlgeschlagen: {deviation}")
        return 1
    print("Schema-Check: OK")

    # Schritt 4b: load_qso_candidates + station_callsigns prüfen
    data = load_qso_candidates(COPY_DB)

    dh3kr_candidates = [c for c in data.candidates if c.stationcallsign == "DH3KR"]
    print(f"load_qso_candidates: {len(data.candidates)} Kandidaten gesamt, "
          f"{len(dh3kr_candidates)} davon DH3KR")

    if "DH3KR" not in data.station_callsigns:
        print("FEHLER: 'DH3KR' nicht in station_callsigns!")
        return 1
    print(f"station_callsigns enthält 'DH3KR': OK  (alle: {sorted(data.station_callsigns)})")

    # Erwartete DH3KR-Kandidaten: alle 4 QSOs haben R='No' → alle sind Kandidaten
    expected_callsigns = {"OE6DRG", "DG5MLA", "DK8NE"}
    found_callsigns = {c.callsign for c in dh3kr_candidates}
    if not expected_callsigns.issubset(found_callsigns):
        print(f"FEHLER: Erwartete Rufzeichen {expected_callsigns} "
              f"nicht alle in Kandidaten {found_callsigns}")
        return 1
    print(f"Alle Ziel-Rufzeichen als Kandidaten gefunden: {sorted(found_callsigns)}")

    # ADR-0015-Check: DG5MLA sollte EQSL in existing_confirmations haben
    dg5mla_candidates = [c for c in dh3kr_candidates if c.callsign == "DG5MLA"]
    if dg5mla_candidates:
        qsoid = dg5mla_candidates[0].qsoid
        eqsl_info = data.existing_confirmations.get(qsoid, [])
        if "EQSL" in eqsl_info:
            print(f"ADR-0015 EQSL-Info für DG5MLA: OK  ({eqsl_info})")
        else:
            print(f"WARNUNG: EQSL-Info für DG5MLA erwartet, gefunden: {eqsl_info}")

    # Original-Integrität abschließend prüfen
    sha_after = _sha256(ORIGINAL_DB)
    if sha_after != sha:
        print("FEHLER: Original-DB wurde verändert!")
        return 1
    print("Original-DB unverändert: OK")

    print()
    print(f"Testkopie bereit: {COPY_DB}")
    print("Die .sqlite-Datei ist per .gitignore ausgeschlossen und wird NICHT committet.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
