# ADR-0014: Interne Repräsentation unbestimmter/mehrdeutiger Felder als None

**Status:** Accepted

## Kontext

Normalisierungsfunktionen (Datum, Band, Mode) und die Rufzeichen-Zerlegung können
nicht immer einen eindeutigen Wert liefern:
- Mehrdeutiges Datum (z. B. `03/04/25` — Tag/Monat oder Monat/Tag?)
- Unbekanntes Format (z. B. römische Monatsziffern `17-XI-93`)
- Zerstörtes Band-Feld (z. B. `tToemvem` statt `6m`)
- Mehrdeutiger Rufzeichen-Zusatz (Fall c der Zerlegungslogik, ADR-0013)

Diese Fälle müssen intern so dargestellt werden, dass die Matching-Engine
sie von gültigen Werten unterscheiden kann, um die Leitregel (ADR-0007:
„Im Zweifel lieber unsicher als falsch auto-bestätigen") durchzusetzen.

## Entscheidung

Alle Normalisierungsfunktionen und `decompose_callsign` geben `str | None` zurück.
`None` bedeutet: „Wert nicht bestimmbar" — egal ob mehrdeutig, unbekanntes Format
oder zerstörter Input.

Die Matching-Engine (`match_card`) wertet `None`-Felder so aus:
- `call_from is None` → `UNCERTAIN` (kein Match-Schlüssel)
- `decompose_callsign` gibt `None` → `UNCERTAIN` (Rufzeichen nicht zerlegbar)
- `date is None` → Kandidaten-Filter überspringt Datum, Ergebnis maximal `UNCERTAIN`
- `band is None` → analog
- `mode is None` → analog

Ein Feld, das `None` ist, verhindert nie allein einen `NO_MATCH` — die Kandidaten
werden weiter gefiltert (nur auf bekannten Feldern). Sind nach Filterung Kandidaten
vorhanden, aber war mindestens ein Pflichtfeld `None` → `UNCERTAIN`.

## Konsequenzen

- Einfache, idiomatische Python-Typsignatur (`str | None` statt Custom-Typ).
- Die Unterscheidung zwischen „mehrdeutig" und „unbekannt" ist für die
  Matching-Engine irrelevant — beide führen zu `UNCERTAIN`. Kein Over-Engineering.
- Kein Absturz bei beliebig korruptem Input: alle Normalisierungsfunktionen
  fangen alle Ausnahmen intern ab und geben im Fehlerfall `None` zurück.
