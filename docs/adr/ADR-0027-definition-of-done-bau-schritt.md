# ADR-0027: Definition of Done je Bau-Schritt

**Status:** Accepted

## Kontext

Nach Abschluss der Schritte 5–7a (Juni 2026) zeigte eine Bestandsaufnahme, dass die
ROADMAP.md mehrere Schritte als „in Arbeit" auswies, obwohl der Code längst gebaut und
getestet war. Gleichzeitig standen sechs GitHub-Issues (Fixes #9–#14) trotz belegtem Fix
im Code noch als offen. Der CHANGELOG hatte vier aufeinanderfolgende `### Added`-Blöcke
angehäuft, weil kein verbindlicher Abschlussschritt existierte.

Ursache: Die Teststrategie (ADR-0009) und die ADR-Pflicht waren dokumentiert, aber es
fehlte eine explizite „Definition of Done", die alle Abschluss-Kriterien eines Bau-Schritts
an einer Stelle bündelt. Doku-Pflege lief damit von Session zu Session als implizite
Aufgabe mit, statt als fester Bestandteil jedes Commits.

## Entscheidung

Ein Bau-Schritt (bzw. Teilschritt) gilt erst als **fertig**, wenn alle fünf Punkte erfüllt
sind:

1. **pytest grün** (lokal) und **CI grün** (GitHub Actions).
2. **ROADMAP.md-Status** des Schritts/Teilschritts aktualisiert (`✅` / `➡️` / `🔧 IN ARBEIT`).
3. **CHANGELOG.md `[Unreleased]`** um die Änderung ergänzt (unter dem passenden Abschnitt).
4. **Zugehörige GitHub-Issues geschlossen** — bevorzugt per `Fixes #N` im Commit, sonst
   mit Schließkommentar inkl. belegendem Commit-Hash. Ein Issue nur schließen, wenn der
   Fix im Code belegt ist.
5. **ADR angelegt**, falls im Schritt eine Design- oder Grundentscheidung gefallen ist
   (→ bestehende ADR-Pflicht in CLAUDE.md).

Die Checkliste ist in CLAUDE.md im Abschnitt „Definition of Done je Bau-Schritt"
verankert und wird beim Onboarding jeder neuen Session mitgelesen.

## Konsequenzen

**Positiv:**
- Doku-Drift (veraltete ROADMAP-Status, offene Issues trotz Fix) wird strukturell
  verhindert, nicht nur reaktiv behoben.
- Jede neue Session liest über CLAUDE.md eine vollständige, aktuelle Projektsicht ein —
  ohne auf flüchtigen Chatverlauf angewiesen zu sein.
- Der Reviewer (Claude Desktop) kann nach jedem Schritt sofort gegen den echten Stand
  prüfen, nicht gegen einen veralteten.

**Negativ / Aufwand:**
- Jeder Commit, der einen Schritt abschließt, erfordert explizit ROADMAP- und
  CHANGELOG-Pflege sowie Issue-Schließung. Das ist leichter Mehraufwand pro Schritt.
- Bei sehr kleinen Fixes (die kein eigenes Issue haben) ist Punkt 4 ein No-op — das ist
  gewollt; die Checkliste skaliert.

**Abgrenzung:**
- Punkt 1 (Tests) ist bereits in ADR-0009 verankert; diese Liste macht ihn sichtbar,
  nicht redundant.
- Punkt 5 (ADR) ist bereits in der ADR-Pflicht (CLAUDE.md) verankert; diese Liste
  bündelt alle Punkte nur an einer Stelle.
