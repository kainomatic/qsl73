# ADR-0022: RunResult-Struktur und run-Modul-Design

**Status:** Accepted

## Kontext

Schritt 6a baut die Orchestrierungsschicht zwischen GUI (6b) und den fertigen Bausteinen
(paperless.py, qr.py, matching.py, log4om_db.py). Folgende Designfragen entstehen:

1. **Ergebnis-Struktur**: Flat-Liste mit Status-Feld vs. drei separate Listen?
2. **Fingerabdruck-Weitergabe**: Im RunResult tragen oder separat übergeben?
3. **existing_confirmations für unsichere/kein-Match-Karten**: Union der Kandidaten oder leer?
4. **Tag-Setzen in write_selected**: Obligatorisch oder optionaler Hook?

## Entscheidungen

### 1. Drei separate Listen (certain / uncertain / no_match)

Drei Listen statt einer Flat-Liste mit Status-Enum:
- Die GUI iteriert je nach Tab/Filter über genau eine Kategorie
- Keine wiederholte Enum-Filterung nötig
- Laufzeit-Assertion: `len(certain) + len(uncertain) + len(no_match) == len(docs)`

### 2. Fingerabdruck und expected_states im RunResult tragen

`RunResult.fingerprint` und `RunResult.expected_states` werden aus `load_qso_candidates`
in den Rückgabewert von `run_pass` übernommen. Die GUI übergibt sie unverändert an
`write_selected`. So ist der 5c-Schutz (Änderungserkennung, Optimistic Locking) garantiert
korrekt verdrahtet, ohne dass die GUI selbst mit DB-Internals in Berührung kommt.

### 3. existing_confirmations nur bei CERTAIN (gematchtem QSO)

`CardResult.existing_confirmations` ist nur befüllt, wenn `outcome.matched_qso is not None`
(d. h. bei CERTAIN-Matches). Bei UNCERTAIN (mehrere Kandidaten, kein eindeutiger Treffer)
und NO_MATCH ist die Liste leer.

Begründung: ADR-0015 beschreibt existing_confirmations als "Kontext-Info für das
zugeordnete QSO". Ohne eindeutige Zuordnung gibt es kein spezifisches QSO, dem die Info
gehört. Union über alle Kandidaten wäre irreführend. Die GUI zeigt existing_confirmations
nur an, wenn ein konkretes QSO zugeordnet ist.

### 4. Tag-Setzen in write_selected als optionaler Parameter

`write_selected` nimmt `paperless_client`, `confirmed_doc_ids` und `uncertain_doc_ids`
als optionale Parameter (Default: None). Wenn None → keine Tag-Operationen.

Begründung: Die GUI (6b) weiß, welche doc_ids welchem Ergebnis zugeordnet sind. In 6a
und in Tests ist Tag-Setzen optional. Tag-Fehler sind nicht fatal (ADR-0003: DB zuerst,
Tags danach; Tag-Fehler beim nächsten Lauf nachziehbar).

## Konsequenzen

- `run_pass` ist rein lesend und liefert immer einen vollständigen RunResult.
- `write_selected` hat keine eigene DB-Logik — delegiert vollständig an `write_confirmations`.
- Die GUI (6b) entscheidet, welche unsicheren Karten manuell zugeordnet werden, und
  übergibt die kombinierten selections + doc_id-Listen an write_selected.
