# ADR-0007: Matching-Strategie — Datenpriorität, Normalisierung, Leitregel

**Status:** Accepted

## Kontext

Echte QSL-Karten zeigen drei verschiedene Datenqualitäten:
1. **QR-Code** (moderne Karten, z. B. DARC-QSL-Service): strukturierter Klartext mit From,
   To, Date, Time, Band, Mode — fehlerfrei, kein Normalisierungsbedarf.
2. **OCR-Text** (Paperless-OCR): fehleranfällig; selbst gedruckte Felder werden zerstört
   (Beispiel: `"6m"` → `"tToemvem"`); handschriftliche Karten kaum brauchbar.
3. **Manueller Zuordnungs-Bildschirm** (§ 9): Fallback wenn QR und OCR versagen.

OCR-Ausgaben enthalten inhomogene Datumsformate, Frequenzangaben statt Bandnamen und
veraltete ITU-Modekürzel — eine Normalisierung vor dem Matching ist zwingend.

## Entscheidung

### Datenpriorität

Für jede Karte werden Felder in dieser Priorität bezogen:

**QR-Code (1) → OCR-Text (2) → Manuell (3)**

- Ist ein gültiger QR-Code vorhanden und liefert er alle vier Pflichtfelder (Rufzeichen,
  Datum, Band, Mode), werden ausschließlich diese Daten verwendet.
- Ein sauberer QR-Treffer **darf auto-bestätigen**, wenn Rufzeichen + Datum + Band + Mode
  passen — gleiche Regel wie beim OCR-Match. Die Sicherheitsschleife ist die gemeinsame
  Vorschau + Bestätigung (Schreibmodell B, ADR-0002).
- `To`-Feld im QR-Code wird gegen `log4om.own_callsign` (Config) abgeglichen; Abweichung
  → Karte gehört nicht zu diesem Log → überspringen.

### Normalisierung (OCR-Pfad)

OCR-Ausgaben müssen vor dem Matching normalisiert werden:

**Datum:** Erkannte Formate: `TT.MM.JJ`, `TT/MM/JJ`, `YYYY-MM-DD`, evtl. `MM/DD/YY`.
Zweistellige Jahre: `>= 30` → 19xx, `< 30` → 20xx (Heuristik). Mehrdeutige Formate
(z. B. `03/04/25`) → Ergebnis als **unsicher** einstufen.

**Band:** Frequenzangaben (z. B. `144.255 MHz`, `50.100 MHz`) werden per Frequenzbereich
in Bandnamen (`2m`, `6m` …) umgerechnet. Nicht zuordnenbare OCR-Fetzen → Feld fehlend
→ **kein Match** oder **unsicher**.

**Mode:** Ältere ITU-Bezeichnungen werden auf moderne gängige Namen gemappt:
`J3E` / `A3J` / `USB` / `LSB` / `PH` → `SSB`; `A1A` → `CW`; `A3E` → `AM`;
`F3E` → `FM`; `F1B` → `RTTY`. Unbekannte Bezeichnungen → Fuzzy-Versuch, sonst **unsicher**.

**From/To-Logik:** `From` (QR) bzw. führendes Rufzeichen (OCR) = Gegenstation =
Match-Schlüssel. `To` (QR) bzw. `"To Radio:"` o. ä. (OCR) = eigener Call → Abgleich
gegen `log4om.own_callsign`.

### Fuzzy-Toleranz: nur für das Rufzeichen

**Fuzzy-Vergleich (Levenshtein-Distanz 1) gilt ausschließlich für das Rufzeichen (`From` /
Stammrufzeichen)**. Band und Mode werden nach Normalisierung immer **exakt** verglichen
(case-insensitiv), unabhängig von der Einstellung `fuzzy_enabled`.

Begründung: Band und Mode sind kleine, feste Wertemengen. Nach erfolgreicher Normalisierung
durch `normalize_band`/`normalize_mode` bedeutet 1 Zeichen Unterschied einen **anderen
realen Wert** (z. B. `"6m"` vs. `"2m"`, `"FT8"` vs. `"FT4"`), keinen OCR-Verleser.
OCR-Verleser bei Band/Mode werden bereits durch die Normalisierung abgefangen (unbekannte
Werte → `None` → `UNCERTAIN`). Fuzzy auf Band/Mode würde die Leitregel verletzen und
Falsch-Positive erzeugen.

### Leitregel

> **Im Zweifel lieber „unsicher" als falsch auto-bestätigen.**

Bei Mehrdeutigkeit (ambiges Datum, nicht erkanntes Band, unbekannter Mode) wird das
Ergebnis als **unsicher** eingestuft und landet im manuellen Zuordnungs-Bildschirm —
niemals wird geraten oder ein falsches QSO bestätigt.

## Konsequenzen

- Karten mit QR-Code werden zuverlässiger und schneller gematcht als per OCR.
- OCR-Normalisierung ist komplexer (Datum-Heuristiken, Band-Tabelle, Mode-Mapping),
  aber unerlässlich für ältere/handschriftliche Karten.
- Konfigurationsfeld `log4om.own_callsign` wird Pflicht für QR/OCR-Parsing.
- Manuelle Zuordnung bleibt der zuverlässige Fallback für unleserliche Karten.
- Die Leitregel schützt vor Falschbestätigungen auf Kosten einer höheren „unsicher"-Rate;
  das ist bewusst so gewählt.
- Fuzzy nur auf Rufzeichen: exaktes Band/Mode-Matching schützt vor Falsch-Positiven bei
  ähnlichen, aber verschiedenen Werten.

---

**Hinweis (2026-06-23):** Der Ort der QR-Auswertung wurde durch ADR-0051 geändert.
QR wird nicht mehr im Massen-Lauf ausgewertet, sondern im manuellen Dialog (Vorbefüllung).
Der Qualitätsrang QR > OCR > manuell bleibt gültig. → ADR-0051
