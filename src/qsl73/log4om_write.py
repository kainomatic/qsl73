"""
Schreiblogik: Papier-QSL-Bestätigung in qsoconfirmations setzen.

Schritt 5a — isolierte, reine Logik ohne Transaktions-/Backup-Orchestrierung.
Die 'write_paper_qsl'-Funktion ist bewusst 'nackt'; Schritt 5b bettet sie
in die Sicherheits- und Transaktionsschicht ein.

Empirische Basis: docs/discovery.md §3, ADR-0005, ADR-0006.
"""
import json
import sqlite3

VALID_ROUTES = frozenset({"undefined", "bureau", "direct"})


class QslEntryNotFoundError(LookupError):
    """Kein CT='QSL'-Eintrag in qsoconfirmations gefunden.

    Log4OM legt diesen Eintrag normalerweise an. Fehlt er, liegt
    vermutlich eine ältere DB-Version vor — Schema-Validierung (Schritt 5b/5c)
    prüft das vor jedem Schreibvorgang. Hier wird der Fehler als Exception
    signalisiert, damit der Aufrufer ihn geordnet abfangen kann.
    Kein stiller Neuanlegen (→ ADR-0019).
    """


class InvalidRouteError(ValueError):
    """Ungültiger route-Wert; erlaubt sind 'undefined', 'bureau', 'direct'."""


def apply_paper_qsl(json_str: str, route: str) -> str:
    """Gibt neuen qsoconfirmations-JSON-String zurück, in dem der QSL-Eintrag bestätigt ist.

    Ändert ausschließlich den CT='QSL'-Eintrag (in-place):
    - R → "Yes"
    - RV: "bureau" → "Bureau", "direct" → "Direct", "undefined" → RV-Schlüssel entfernen
    - Kein RD geschrieben, kein S/SV/CT verändert
    - Alle anderen Einträge (EQSL, LOTW, QRZCOM, HAMQTH, HRDLOG, CLUBLOG) unberührt

    Args:
        json_str: qsoconfirmations als JSON-String (aus Log4OM-DB).
        route: "undefined", "bureau" oder "direct".

    Returns:
        Neuer JSON-String mit gesetzter Papier-QSL-Bestätigung.

    Raises:
        InvalidRouteError: route ist keiner der drei erlaubten Werte.
        ValueError: json_str ist kein gültiges JSON.
        QslEntryNotFoundError: Kein Eintrag mit CT='QSL' im Array.
    """
    if route not in VALID_ROUTES:
        raise InvalidRouteError(
            f"Ungültiger route-Wert {route!r}. Erlaubt: {sorted(VALID_ROUTES)}"
        )

    try:
        confirmations = json.loads(json_str)
    except json.JSONDecodeError as exc:
        raise ValueError(f"qsoconfirmations ist kein gültiges JSON: {exc}") from exc

    qsl_entry = None
    for entry in confirmations:
        if isinstance(entry, dict) and entry.get("CT") == "QSL":
            qsl_entry = entry
            break

    if qsl_entry is None:
        raise QslEntryNotFoundError(
            "Kein CT='QSL'-Eintrag in qsoconfirmations — Schema-Validierung prüfen (ADR-0019)"
        )

    qsl_entry["R"] = "Yes"

    if route == "bureau":
        qsl_entry["RV"] = "Bureau"
    elif route == "direct":
        qsl_entry["RV"] = "Direct"
    else:  # "undefined"
        qsl_entry.pop("RV", None)

    return json.dumps(confirmations, ensure_ascii=False, separators=(",", ":"))


def write_paper_qsl(conn: sqlite3.Connection, qsoid: str, route: str) -> None:
    """Liest qsoconfirmations, setzt Papier-QSL und schreibt zurück.

    Bewusstes Design Schritt 5a: KEINE Transaktion, KEIN Backup, KEINE
    Nebenläufigkeitsprüfung — das kommt in Schritt 5b. Schreibt NUR die
    qsoconfirmations-Spalte des einen QSO (per qsoid, eindeutig).

    Args:
        conn: Offene sqlite3-Verbindung.
        qsoid: Primärschlüssel des QSO (qsoid-Spalte, eindeutig).
        route: "undefined", "bureau" oder "direct".

    Raises:
        ValueError: qsoid nicht in DB oder JSON nicht parsebar.
        QslEntryNotFoundError: Kein CT='QSL'-Eintrag im Array.
        InvalidRouteError: Ungültiger route-Wert.
    """
    cur = conn.execute(
        "SELECT qsoconfirmations FROM Log WHERE qsoid = ?", (qsoid,)
    )
    row = cur.fetchone()
    if row is None:
        raise ValueError(f"QSO nicht gefunden: qsoid={qsoid!r}")

    new_json = apply_paper_qsl(row[0], route)

    conn.execute(
        "UPDATE Log SET qsoconfirmations = ? WHERE qsoid = ?",
        (new_json, qsoid),
    )
