# ADR-0056: Matching bei mehreren Fremdcalls + Fuzzy erzwingt UNSICHER

**Status:** Accepted

**Verhältnis zu anderen ADRs:** Verschärft **ADR-0016** (3-von-4-Matching) im
Fuzzy-Fall — siehe „Abgrenzung zu ADR-0016" unten. Ergänzt **ADR-0013**
(Rufzeichen-Zerlegung/Zeitlogik) und **ADR-0025** (Token-basierte OCR-Extraktion)
um die Mehrfachcall-Behandlung. Setzt die Leitregel aus **ADR-0007** konsequent
fort: im Zweifel „unsicher" statt falsch auto-bestätigen.

## Kontext

Issue #33 (Teil 2): Karten mit mehreren erkannten Fremd-Rufzeichen — z. B. echter
Absender **und** ein Druckvermerk/Werbe-Call auf demselben Kartenaufdruck
(Referenzfall aus dem Issue: `M7PI` als echter Absender neben `UX5UO` als
Druckvermerk) — verloren bislang ihren Gegencall vollständig:

`run._extract_token_based` kollabierte bei mehr als einem eindeutigen Fremdcall
hart auf `call_from = None`:
```python
call_from = unique_foreign[0] if len(unique_foreign) == 1 else None
```
`matching.match_card` bekam dadurch `card.call_from is None` und stufte die Karte
sofort als UNSICHER ein — **ohne** die tatsächlich matchenden DB-Kandidaten zu
kennen. Der Nutzer sah im manuellen Dialog keinerlei Vorschlag, obwohl einer der
beiden erkannten Calls exakt zu einem offenen QSO gepasst hätte.

Zusätzlich erlaubte `match_card` bislang, dass ein **fuzzy** (Levenshtein-1)
Rufzeichen-Treffer bei erfüllter 3-von-4-Regel automatisch CERTAIN wurde
(`_fuzzy_equal` unterschied nicht zwischen exakt und fuzzy im CERTAIN-Pfad).
Das birgt ein Falsch-Positiv-Risiko: eine unscharfe Übereinstimmung (OCR-Verleser)
kann auf ein real existierendes **anderes** Rufzeichen passen — ein Falsch-Positiv
würde ein QSO als Papier-QSL bestätigen, das nie bestätigt wurde (stille
Datenverfälschung). Design-Präzisierung dazu bereits als Issue-Kommentar
festgehalten: die großzügige Fuzzy-Suche ist ausdrücklich nur für den
menschengeführten manuellen Pfad gedacht, nicht für den Auto-CERTAIN-Pfad.

## Entscheidung

### 1. Mehrere Fremdcalls werden vollständig durchgereicht

`CardFields` bekommt ein additives Feld:
```python
call_from_candidates: list[str] = field(default_factory=list)
```
`call_from` bleibt unverändert erhalten (Abwärtskompatibilität aller bestehenden
Aufrufer/Tests). Konvention: ist `call_from_candidates` nicht leer, nutzt
`match_card` diese Liste; sonst fällt es auf das einzelne `call_from` zurück.

`run._extract_token_based` reicht `unique_foreign` (bereits dedupliziert,
Reihenfolge erhalten) **immer** als `call_from_candidates` durch — unabhängig von
der Anzahl. `call_from` wird zusätzlich weiterhin gesetzt, wenn genau ein
Kandidat existiert.

### 2. Jeder Fremdcall-Kandidat wird unabhängig gematcht, dann zusammengeführt

`match_card` durchläuft für jeden Fremdcall-Kandidaten den bestehenden
Matching-Durchlauf (Stammrufzeichen-Zerlegung, Kandidatenfilter mit
Widerspruchs-Ausschluss, Zeit-Tie-Breaker **innerhalb** des jeweiligen Calls) und
führt die getroffenen DB-QSOs über alle Calls hinweg zusammen (dedupliziert nach
`qsoid`). Für jeden Treffer wird zusätzlich festgehalten, ob der
Rufzeichen-Match **exakt** oder **fuzzy** (Levenshtein-1) war.

### 3. Vollständige Wahrheitstabelle

| Fall | Bedingung | Ergebnis |
|------|-----------|----------|
| **R1** | Kein Fremdcall-Kandidat matcht ein DB-QSO | `NO_MATCH` |
| **R2** | Genau 1 DB-QSO getroffen, Rufzeichen **exakt**, 3-von-4/Suffix-Regel erfüllt | `CERTAIN` |
| **R3** | Der (einzige) Treffer beruht auf **fuzzy** Rufzeichen | `UNCERTAIN` — Kandidat zur Vorbefüllung im manuellen Dialog verfügbar, **nie** `CERTAIN` |
| **R4** | Mehrere **verschiedene** DB-QSOs getroffen (exakt oder fuzzy, über einen oder mehrere Calls) | `UNCERTAIN` (mehrdeutig), `matched_qso=None` |
| **R5** | Suffix-Unterschied-Regel (ADR-0013) | unverändert — strenger als 3-von-4, gilt pro Call unabhängig von der Anzahl der Fremdcall-Kandidaten |

**Leitlinie:** Exaktheit erlaubt Automatik (CERTAIN); Unschärfe (Fuzzy) oder
Mehrdeutigkeit (mehrere Calls treffen verschiedene QSOs) erzwingt den Menschen
(UNCERTAIN).

Der Zeit-Tie-Breaker (±30 min, ADR-0013) wirkt weiterhin nur **innerhalb** eines
einzelnen Fremdcall-Kandidaten, um dessen mehrere zeitgleiche DB-Treffer auf
einen zu reduzieren. Löst er nicht eindeutig auf, bleiben alle betroffenen
Kandidaten dieses Calls Teil der global gesammelten Treffermenge (wirkt sich auf
R4 aus).

### 4. Implementierung (intern, `matching.py`)

- `_rufzeichen_kind(a, b, fuzzy) -> "exact" | "fuzzy" | None` ersetzt das
  bisherige `_fuzzy_equal` (reiner `bool`) — match_card muss zwischen R2 und R3
  unterscheiden können.
- `_filter_candidates_for_call(...)` — Kandidatenfilter für EINEN Fremdcall
  (bisherige Logik aus `match_card`, jetzt parametrisiert über den Call).
- `_resolve_time_tiebreaker(...)` — Zeit-Tie-Breaker, jetzt als eigene Funktion,
  operiert auf `(Kandidat, kind)`-Paaren EINES Calls.
- `_fields_rule_certain(...)` — 3-von-4-/Suffix-Regel als reine Feldregel, ohne
  Rufzeichen-Exaktheit zu kennen; die Exaktheits-Gate sitzt in `match_card`
  (nur `kind == "exact"` darf überhaupt `_fields_rule_certain` befragen).

## Abgrenzung zu ADR-0016

ADR-0016 (3-von-4 mit Widerspruchs-Ausschluss) bleibt in der Sache unverändert
gültig — inklusive der Regel „Band/Mode bleiben exakt, Fuzzy nur auf
Rufzeichen". **Verschärft** wird ausschließlich der CERTAIN-Pfad: vorher durfte
ein fuzzy Rufzeichen-Treffer bei erfüllter 3-von-4-Regel CERTAIN werden; das ist
jetzt ausgeschlossen (R3). ADR-0016 bleibt maßgeblich für die Feldregel selbst,
gilt aber nur noch in Kombination mit einem exakten Rufzeichen-Treffer als
hinreichend für CERTAIN.

## Begründung (DF1DS)

Ein **exakt** passendes Rufzeichen, das zusätzlich in mindestens zwei weiteren
Feldern (Datum/Band/Mode) übereinstimmt, wäre als zufälliges Fehlmatch extrem
unwahrscheinlich — das rechtfertigt automatische Bestätigung. Eine **unscharfe**
Übereinstimmung oder eine **mehrdeutige** Fremdcall-Situation trägt dagegen eine
reale Verwechslungsgefahr (OCR-Verleser kann auf ein anderes, real
existierendes Rufzeichen passen) — das erzwingt den manuellen, menschengeführten
Pfad.

## Konsequenzen

**Positiv:**
- Der Issue-#33-Fall (Druckvermerk-/Werbe-Call neben echtem Absender) verliert
  den echten Absender nicht mehr — der Druckvermerk-Call trägt einfach 0 Treffer
  bei (R1 für diesen Call allein), während der echte Absender-Call regulär
  matcht.
- Falsch-Positiv-Schutz im Auto-Pfad ist strenger als zuvor: kein fuzzy
  Rufzeichen kann mehr automatisch bestätigen, unabhängig von der Anzahl der
  Fremdcall-Kandidaten.

**Negativ / bewusst in Kauf genommen:**
- Höhere UNSICHER-Rate: Karten, die vorher (fälschlich) über einen fuzzy Match
  automatisch bestätigt worden wären, landen jetzt im manuellen Dialog. Das ist
  gewollt (Leitregel ADR-0007) — bestehende Tests, die fuzzy→CERTAIN erwarteten,
  wurden bewusst auf UNCERTAIN angepasst.
- Der manuelle Suchpfad (kontextabhängig großzügigeres Fuzzy im
  `ManualAssignmentDialog`) ist **nicht** Teil dieser Entscheidung — er bleibt
  wie bisher und ist für ein separates, späteres Issue vorgemerkt.
