# ADR-0007: Matching-Datenpriorität — QR-Code → OCR → manuell

**Status:** Accepted

## Kontext

Echte QSL-Karten zeigen drei verschiedene Datenqualitäten:
1. **QR-Code** (moderne Karten, z. B. DARC-QSL-Service): strukturierter Klartext mit From,
   To, Date, Time, Band, Mode — fehlerfrei, kein Normalisierungsbedarf.
2. **OCR-Text** (Paperless-OCR): fehleranfällig; selbst gedruckte Felder werden zerstört
   (Beispiel: `"6m"` → `"tToemvem"`); handschriftliche Karten kaum brauchbar.
3. **Manueller Zuordnungs-Bildschirm** (§ 9): Fallback wenn QR und OCR versagen.

Nicht jede Karte hat einen QR-Code. OCR ist kein Universalersatz.

## Entscheidung

Für jede Karte werden Felder in dieser Priorität bezogen:

**QR-Code (1) → OCR-Text (2) → Manuell (3)**

- Ist ein gültiger QR-Code vorhanden und liefert er alle vier Pflichtfelder (Rufzeichen,
  Datum, Band, Mode), werden ausschließlich diese Daten verwendet.
- Ein sauberer QR-Treffer **darf auto-bestätigen**, wenn Rufzeichen + Datum + Band + Mode
  passen — gleiche Regel wie beim OCR-Match. Die Sicherheitsschleife ist die gemeinsame
  Vorschau + Bestätigung (Schreibmodell B, ADR-0002).
- `To`-Feld im QR-Code wird gegen `log4om.own_callsign` (Config) abgeglichen; Abweichung
  → Karte gehört nicht zu diesem Log → überspringen.
- OCR-Text erfordert Normalisierung (Datum-Formate, Frequenz→Band, Mode-Mapping,
  From/To-Logik); mehrdeutige Fälle → „unsicher" statt raten.

## Konsequenzen

- Karten mit QR-Code werden zuverlässiger und schneller gematcht als per OCR.
- OCR-Normalisierung ist komplexer (Datum-Heuristiken, Band-Umrechnung, Mode-Tabelle),
  aber unerlässlich für ältere/handschriftliche Karten.
- Konfigurationsfeld `log4om.own_callsign` wird Pflicht für QR/OCR-Parsing.
- Manuelle Zuordnung bleibt der zuverlässige Fallback für unleserliche Karten.
