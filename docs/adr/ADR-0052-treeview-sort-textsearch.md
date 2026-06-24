# ADR-0052 — Treeview-Klick-Sortierung + Textsuche (Issues #28 + #29)

**Status:** Accepted  
**Datum:** 2026-06-24  
**Kontext:** Issues #28 (Treeview-Sortierung) und #29 (Textsuche)

---

## Kontext

Beide Treeviews (Hauptfenster und manueller Zuordnungs-Dialog) hatten keine
Klick-Sortierung. Das Hauptfenster fehlte eine Freitext-Suche als Ergänzung
zur Kategorie-Combobox.

---

## Entscheidungen

### 1. Operationsreihenfolge Hauptfenster (V1)

Kategorie-Filter → Textfilter → Sortierung → Treeview-Befüllung.
`self._displayed` wird nach der vollständigen Pipeline gesetzt (= sortierte Liste),
damit Shift-Klick-Bereichsauswahl die angezeigte Reihenfolge widerspiegelt.

### 2. Band-Sortierung nach normalize.py-Reihenfolge (V2)

`BAND_ORDER: list[str]` in `normalize.py` exportiert — DRY abgeleitet von der
bereits geordneten `_FREQ_TO_BAND`-Liste. Keine neue Lookup-Tabelle, kein Regex.
Unbekannte/leere Bänder werden ans Ende der jeweiligen Richtung sortiert.

### 3. Datum als echtes Datum sortiert (V3)

`datetime.date.fromisoformat()` für Sortierschlüssel. Leer/ungültig (inkl. "–")
→ ans Ende. Kein Fallback auf lexikografischen String-Vergleich.

### 4. Zweistufige Sortierung im Hauptfenster (Option A, V4)

Geschriebene Karten ("Bestätigt ✓") bleiben immer unten; das Klick-Kriterium
ist die zweite Ebene innerhalb der beiden Gruppen. Implementiert via
`sort_cards_written_last_then_by_column()`, welche `sort_cards_written_last()`
(ADR-0030) integriert und ersetzt ohne dessen Logik zu duplizieren.

### 5. Durchsuchbare Spalten (V5)

Nur `call` (call_from/call_to), `date`, `band`. `mode`, `source` und `status`
sind nicht durchsuchbar. Begründung: Call/Datum/Band sind die primären
QSO-Identifikatoren; Mode/Source/Status als Filter würden unerwartete
Massentreffer erzeugen (z. B. "FT8" matcht alle FT8-Karten).

### 6. Live-Suche ohne Such-Button

StringVar-Trace auf `_refresh_tree`. Zusätzlicher ×-Button leert das Feld.
Kein separater Such-Button (responsiver).

### 7. Einstufige Sortierung im manuellen Dialog

Keine geschriebenen Karten im Kandidaten-Dialog → einstufige Sortierung via
`sort_candidates_by_column()`. Kein written-last-Wrapper nötig.

---

## Verhältnis zu anderen ADRs

- **ADR-0030:** sort_cards_written_last bleibt konzeptuell gültig (written-last
  ist Ebene 1). Die neue Funktion integriert es, ohne es zu duplizieren.
- **ADR-0014:** normalize_band bleibt wie beschrieben; BAND_ORDER ist eine
  ergänzende Konstante, kein neues Normalisierungsverhalten.
- **ADR-0047:** Alle neuen Widgets (Suchfeld, ×-Button) haben attach_tooltip.
- **ADR-0051:** _load_image / QR-Prefill-Logik im manuellen Dialog unverändert.

---

## Konsequenzen

**Positiv:**
- Sortier- und Filterlogik vollständig tk-frei in `filter_util.py` — Unit-Tests
  ohne Display möglich.
- BAND_ORDER-Wiederverwendung vermeidet zweite Wellenlängen-Tabelle (DRY).
- Live-Textsuche + Kategorie-Filter als UND-Verknüpfung: präzise Eingrenzung
  ohne Menü-Navigation.

**Negativ / bewusst akzeptiert:**
- Mode/Source/Status nicht durchsuchbar — Nutzer muss ggf. Kategorie-Combobox
  für Status-Filter nutzen.
- StringVar-Trace feuert bei jedem Tastendruck → bei sehr großen Listen (~2000)
  kurze Neuberechnung. Akzeptabel, da Filterung in-memory und ohne DB-Zugriff.
