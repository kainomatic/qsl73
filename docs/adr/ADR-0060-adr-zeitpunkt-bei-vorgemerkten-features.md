# ADR-0060: ADR-Zeitpunkt bei nur vorgemerkten Features

**Status:** Accepted

## Kontext

Die ADR-Pflicht (CLAUDE.md, „Entscheidungen und Aufgaben festhalten") verlangt: Fällt im
Planungsgespräch eine Design-/Grundentscheidung, enthält der zugehörige oder nächste Auftrag
an Claude Code standardmäßig den Punkt „dazu ein ADR anlegen".

Offen blieb, wie damit umzugehen ist, wenn die Entscheidungen beim Planen eines Features
fallen, das NUR als GitHub Issue vorgemerkt wird — noch nicht priorisiert, noch nicht
spezifiziert, kein Umsetzungsauftrag in Sicht. Anlass war Issue #42 (Werkzeug
„Bestätigungsübersicht"): Beim Planen fielen mehrere Grundentscheidungen (read-only-Zugriff,
Behandlung von Absichtsmerkern vs. harten Fakten, Dienst-Gruppen), aber weder Spezifikation
noch Handtest (Vorbedingung laut Issue) waren zu diesem Zeitpunkt abgeschlossen.

Ein sofort angelegtes Accepted-ADR für ein noch unspezifiziertes Feature müsste nach
Spezifikation und Handtest absehbar wieder nachgetragen oder korrigiert werden.

## Entscheidung

1. Betrifft eine Entscheidung etwas, das jetzt umgesetzt wird, oder ändert sie bestehendes
   Verhalten/Vorgehen → ADR wie bisher: im zugehörigen oder nächsten Auftrag.
2. Fällt eine Entscheidung beim Planen eines Features, das nur als GitHub Issue vorgemerkt
   wird (nicht priorisiert, nicht spezifiziert) → die Entscheidungen werden im Issue unter
   einer Überschrift „Grundentscheidungen" festgehalten; das ADR wird erst mit dem ERSTEN
   Umsetzungsauftrag angelegt (dann Status Accepted). Desktop stellt sicher, dass der
   Umsetzungsauftrag den Punkt „ADR anlegen" enthält.
3. **Ausnahme:** Wirkt die Entscheidung über das Feature hinaus — ändert sie ein allgemeines
   Prinzip, eine Sicherheits-/Datenschutz-Leitplanke oder das Arbeitsvorgehen — gilt Fall 1:
   ADR sofort, unabhängig vom Umsetzungsstand des Features.

**Konsequenz:** Wird ein solches Issue ohne Umsetzung geschlossen (verworfen), ist kein ADR
nötig; der Schließkommentar nennt den Grund.

## Begründung

Ein Accepted-ADR für ein Feature, dessen Spezifikation und Handtest-Ergebnisse noch fehlen,
wäre bei Umsetzung absehbar zu korrigieren — es entstünden ADR + Nachtrag statt eines
stimmigen Dokuments. Das GitHub Issue sichert die Entscheidungen bis dahin dauerhaft genug:
Nichts bleibt im flüchtigen Chat, „Chatverlauf ist flüchtig, das Repo ist dauerhaft" bleibt
gewahrt, ohne ein ADR vorzeitig festzuschreiben.

## Konsequenzen

- Ein GitHub Issue kann einen Abschnitt „Grundentscheidungen" enthalten, der inhaltlich wie
  ein ADR-Entwurf gelesen wird, aber erst mit der Umsetzung zum ADR wird.
- Desktop muss beim ersten Umsetzungsauftrag eines solchen Issues aktiv an „ADR anlegen"
  denken — kein automatischer Auslöser wie bei Fall 1.
- Die ADR-Nummer für ein vorgemerktes Feature ist bis zur Umsetzung nur eine Erwartung
  („voraussichtlich ADR-00NN"), keine feste Zusage — die nächste freie Nummer kann sich bis
  dahin durch andere ADRs verschieben.
