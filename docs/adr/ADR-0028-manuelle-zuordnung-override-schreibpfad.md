# ADR-0028: Manuelle Zuordnung — Override der Match-Schwelle, gemeinsamer Schreibpfad

**Status:** Accepted

## Kontext

Schritt 6c führt den manuellen Zuordnungs-Bildschirm ein (KONZEPT §9): Karten, bei denen
das Auto-Matching nur „UNCERTAIN" liefert (3-von-4-Schwelle nicht erreicht), sollen vom
Nutzer manuell einem QSO zugeordnet werden können. Dabei entstehen vier Designfragen:

1. Darf die manuelle Zuordnung die Auto-Match-Schwelle überschreiben?
2. Welchen Schreibpfad nimmt die manuelle Zuordnung?
3. Worüber erstreckt sich der Suchraum?
4. Wie tief darf der Nutzer in den Suchprozess eingreifen?

## Entscheidungen

### 1. Override der 3-von-4-Schwelle ist zulässig — und der Zweck des manuellen Pfads

Die manuelle Zuordnung ist bewusst als menschlicher Override konzipiert: Der Nutzer
kann ein QSO auch dann zuordnen, wenn weniger als 3 von 4 Feldern übereinstimmen (z. B.
bei kaputter OCR). Diese Freiheit ist kein Bug, sondern das Designziel. Einschränkungen
bleiben aber erhalten: Der Nutzer wählt aus den angezeigten Kandidaten — er kann kein
beliebiges QSO aus dem Nichts eingeben.

### 2. Kein separater Schreibpfad — exakt derselbe Weg wie Auto-Treffer

Eine manuelle Zuordnung erzeugt denselben `(qsoid, route)`-Eintrag wie ein Auto-Treffer
und fließt in denselben Schreib-Korb (`write_selected` → `write_confirmations`). Der
5c-Schutz (Schema-Check, WAL, Vor-Backup, Optimistic Locking, Fingerprint) bleibt voll
aktiv. Es gibt keinen vereinfachten oder abgekürzten Schreibpfad für manuelle Einträge.

**Begründung:** Zwei Schreibpfade für dasselbe Ergebnis erzeugen doppelten Wartungsaufwand
und Divergenzrisiko. Der vorhandene Schreibpfad ist bereits vollständig abgesichert.

### 3. Suchraum ausschließlich offene Kandidaten (R='No'/'Requested')

Die Suchfunktion `search_candidates` operiert ausschließlich auf der Kandidatenmenge, die
`load_qso_candidates` bereits vorgefiltert hat. Bereits bestätigte QSOs (R='Yes') und
R='Invalid'-QSOs sind nie im Suchraum — sie gelangen gar nicht in die Kandidatenliste.
Ein direkter DB-Zugriff in `manual_match.py` findet nicht statt.

**Begründung:** Würde ein bereits bestätigtes QSO nochmals zugeordnet werden, entstünde
eine Doppelbestätigung; der 5c-Schutz würde die Transaktion zwar überspringen, aber die
Konfusion wäre nutzerseitig schwer erklärbar. Sicherheitsmodell-Konsistenz erfordert, dass
nur offene Kandidaten auswählbar sind.

### 4. Interaktionstiefe „Stufe 2" und austauschbare Suchstrategie

Der Nutzer darf OCR-vorbefüllte Suchfelder editieren, um die Suche zu steuern (z. B.
Band von Hand setzen bei kaputter OCR). Diese Korrekturen dienen **nur** dem Finden
des richtigen QSOs — die Kartenfelder selbst werden nicht in die DB geschrieben.
Geschrieben wird ausschließlich R='Yes' am gewählten bestehenden QSO-Datensatz.

Die Suchstrategie (`_rank_score`, `_matches_query`) ist in `manual_match.py` als isolierte,
tk-freie Funktion implementiert. Der nach außen sichtbare Vertrag ist `(qsoid, route)` —
stabil. Die Strategie dahinter (Filterregeln, Ranking-Gewichtung) ist bewusst flexibel
und kann ohne GUI-Änderung angepasst werden (z. B. Fuzzy-Rufzeichen-Match in Zukunft).

## Konsequenzen

**Positiv:**
- Kein Doppelpfad: Wartungsaufwand bleibt minimal.
- Sicherheitsmodell unverändert: 5c-Schutz gilt ohne Ausnahme.
- Testbarkeit: `manual_match.py` ist tk-frei und vollständig unit-testbar.
- Erweiterbarkeit: Suchstrategie austauschbar ohne GUI-Änderung.

**Negativ / Einschränkungen:**
- Nutzer kann nur aus vorgeladenen offenen Kandidaten wählen — kein Freitext-QSO-Eingabe.
  Das ist eine bewusste Sicherheitseinschränkung, kein Defizit.
- Die Kandidatenmenge ist ein Snapshot aus `load_qso_candidates` (Laufbeginn) — neue QSOs,
  die nach Laufbeginn in die DB eingetragen wurden, erscheinen erst nach einem neuen Lauf.
