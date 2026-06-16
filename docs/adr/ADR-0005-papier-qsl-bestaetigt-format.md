# ADR-0005: „Papier-QSL bestätigt" = CT="QSL", R="Yes"; nie R="V"; andere CT-Typen unberührt

**Status:** Accepted

## Kontext

`qsoconfirmations` ist ein JSON-Array mit 7 Typen: QSL, EQSL, LOTW, QRZCOM, HAMQTH,
HRDLOG, CLUBLOG. QSL73 soll ausschließlich die Papier-QSL-Bestätigung setzen, ohne
eQSL/LoTW/QRZ zu berühren. Empirische Basis: `docs/discovery.md`. R="V" bedeutet
zusätzlich DXCC-verifiziert und wird vom Nutzer selbst im Award-Checker vergeben.

## Entscheidung

- „Papier-QSL bestätigt" = Eintrag `CT="QSL"` mit `R="Yes"` im Array.
- QSL73 setzt **niemals** `R="V"` — das bleibt dem Nutzer vorbehalten.
- Alle anderen CT-Typen (EQSL, LOTW, QRZCOM, …) werden von QSL73 weder gelesen als
  Bestätigungsgrund noch geschrieben.
- `RD` wird auf das Bestätigungsdatum UTC gesetzt (`YYYY-MM-DDT00:00:00Z`).
- `S`/`SV` bleiben unverändert — QSL73 bestätigt nur Empfang, nicht Versand.

## Konsequenzen

- Klare, unidirektionale Schreibgrenze; keine unerwünschten Seiteneffekte auf eQSL/LoTW.
- Vorfilter: alle QSOs mit `CT="QSL", R="No"` sind Kandidaten; bereits `R="Yes"` → nie
  als Kandidat angezeigt.
- Exaktes Schreibformat wartet noch auf empirische Bestätigung (→ Issue #RV-Hand-Test).
