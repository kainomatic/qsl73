# ADR-0005: „Papier-QSL bestätigt" = CT="QSL", R="Yes"; nie R="V"; andere CT-Typen unberührt

**Status:** Accepted

## Kontext

`qsoconfirmations` ist ein JSON-Array mit 7 Typen: QSL, EQSL, LOTW, QRZCOM, HAMQTH,
HRDLOG, CLUBLOG. QSL73 soll ausschließlich die Papier-QSL-Bestätigung setzen, ohne
eQSL/LoTW/QRZ zu berühren. Empirische Basis: `docs/discovery.md`.

R="V" bedeutet DXCC-verifiziert und wird vom Nutzer selbst im Award-Checker vergeben.

Das exakte Schreibformat wurde am 2026-06-17 durch einen Hand-Test empirisch bestätigt
(drei Test-QSOs je einmal undefined/bureau/direct, Vorher/Nachher-DB-Diff). Die frühere
Annahme (RD auf Bestätigungsdatum setzen) ist dabei widerlegt worden.
Befunde vollständig in `docs/discovery.md §3`.

## Entscheidung

- „Papier-QSL bestätigt" = Eintrag `CT="QSL"` mit `R="Yes"` im Array.
- QSL73 setzt **niemals** `R="V"` — das bleibt dem Nutzer vorbehalten.
- Alle anderen CT-Typen (EQSL, LOTW, QRZCOM, …) werden von QSL73 weder gelesen als
  Bestätigungsgrund noch geschrieben.
- `RD` (Empfangsdatum) wird **nicht** geschrieben. Log4OM setzt beim manuellen
  Bestätigen kein Datum — diese Annahme war falsch und wurde durch den Hand-Test widerlegt.
- `S`/`SV` bleiben unverändert — QSL73 bestätigt nur Empfang, nicht Versand.
- `RV` wird je nach `qsl_route_default` gesetzt (→ ADR-0006):
  `"bureau"` → `"Bureau"`, `"direct"` → `"Direct"`, `"undefined"` → RV-Schlüssel entfernen.

**Vorfilter:** Kandidaten für QSL73 sind QSOs mit `CT="QSL"` und `R ∈ {"No", "Requested"}`:

| `R`-Wert | Verhalten |
|----------|-----------|
| `"No"` | Kandidat — bei Treffer auf `"Yes"` setzen |
| `"Requested"` | Kandidat — Karte wurde angefordert; bei Eingang auf `"Yes"` setzen |
| `"Yes"` | Überspringen — bereits bestätigt |
| `"Invalid"` | Überspringen — Sonderzustand, nicht anfassen |

## Konsequenzen

- Klare, unidirektionale Schreibgrenze; keine unerwünschten Seiteneffekte auf eQSL/LoTW.
- Kein Datumsfeld wird geschrieben (kein RD).
- Durch den Hand-Test empirisch bestätigt (→ `docs/discovery.md §3`, Issue #1 geschlossen).
