# ADR-0061: ROADMAP — Zweck und Struktur

**Status:** Accepted

## Kontext

`ROADMAP.md` war für die Bauphase (Schritte 0–9) als abhakbarer Schrittplan gedacht
(„erledigte Schritte abhaken, Reihenfolge bei Bedarf anpassen"). Seit v0.1.0 ist sie
faktisch zum Projekttagebuch geworden: jeder Fix, jede Beta, jeder Review-Nachtrag bekam
einen eigenen, oft langen Absatz. Stand 2026-09-18 umfasste die Datei rund 1000 Zeilen.

Das führte zu drei Problemen:

1. **Duplikation.** Dieselbe Information stand in ROADMAP, CHANGELOG und ADRs parallel —
   „was geändert" gehört ins CHANGELOG, „warum" in ADRs, „was noch offen ist" ist über
   GitHub Issues bereits vollständig abgedeckt.
2. **Drift.** Weil die ROADMAP zusätzlich offene Issues aufzählte, lief diese Aufzählung
   zwangsläufig gegen den echten GitHub-Stand auseinander. Konkreter Befund bei der
   Erstellung dieses ADRs: Issues #32/#41/#42 fehlten in der zuletzt gepflegten
   Übersicht; ein Abschnitt „V2 — Vorgemerkte Features" behauptete zum
   Attention-Handler fälschlich eine vollständige Code-Entfernung, obwohl die
   Parent-Binding-Mechanik (ADR-0037) nachweislich noch aktiv im Code steht (siehe
   Issue #43, das den tatsächlich noch offenen Rest — visueller Blinken-Effekt —
   korrekt festhält).
3. **Onboarding-Kosten.** Eine neue Session musste sich durch die gesamte Historie lesen,
   um den aktuellen Stand und die nächsten Schritte zu finden — obwohl beides in wenigen
   Zeilen darstellbar ist.

## Entscheidung

`ROADMAP.md` liefert künftig **nur noch, was keine andere Quelle liefert**, in genau drei
Abschnitten:

1. **„Aktueller Stand"** — max. ~10 Zeilen: letzte Stable-Version + Datum, laufende Beta
   (falls vorhanden), aktiver Auftrag (falls vorhanden), worauf gewartet wird. Keine
   Issue-Aufzählung, keine „enthaltene Änderungen"-Liste.
2. **„Nächste Schritte"** — priorisierte, nummerierte Liste offener Issue-Nummern mit
   einem Halbsatz Begründung je Eintrag, plus fester Verweis auf die GitHub-Issue-Liste
   als einzige vollständige Quelle offener Aufgaben.
3. **„Historie Bauphase"** — Schritte 0–9 als kompakte Tabelle (Schritt | Ergebnis in
   einem Halbsatz | maßgebliche ADRs). Keine Release-/Beta-/Hotfix-Historie.

**Offene Issues werden nicht mehr in der ROADMAP aufgezählt** — einzige Quelle dafür ist
GitHub (`gh issue list --state open`). Änderungs-Details stehen im CHANGELOG,
Begründungen in ADRs. Die ROADMAP wird ab sofort **überschrieben, nicht fortgeschrieben**:
ein abgeschlossener Schritt oder ein erledigtes Issue verschwindet aus „Nächste Schritte",
statt einen neuen Absatz zu erzeugen.

Der Rollen-/Schleifen-Abschnitt („Zusammenarbeit") entfällt aus der ROADMAP ersatzlos —
er steht bereits vollständig in `CLAUDE.md`.

### Abgrenzung zu anderen Quellen

| Frage | Quelle |
|-------|--------|
| Was wurde geändert (Version X)? | `CHANGELOG.md` |
| Warum wurde etwas so entschieden? | `docs/adr/` |
| Was ist aktuell offen? | GitHub Issues (`gh issue list --state open`) |
| Was ist der aktuelle Stand + was kommt als Nächstes (priorisiert)? | `ROADMAP.md` |
| Wie arbeiten Desktop/DF1DS/Claude Code zusammen? | `CLAUDE.md` |

### Verbleib der bisherigen Detailabsätze

Die bisherigen Detailabsätze (Schritt-für-Schritt-Historie, Beta-Release-Verlauf,
Review-Nachträge) werden **nicht** in eine separate HISTORY-Datei verschoben. Sie bleiben
über die Git-Historie vollständig erreichbar: der letzte Commit mit der vollständigen
Langfassung von `ROADMAP.md` vor dieser Umstellung ist `11d1860`
(`docs(roadmap): AKTUELLER STAND mit offenen Issues abgeglichen, Alt-Aussagen
korrigiert`) — `git show 11d1860:ROADMAP.md` liefert den vollständigen Alt-Stand.

### Konsequenz für die Definition of Done (ADR-0027)

Punkt 2 der DoD („ROADMAP.md-Status des Schritts/Teilschritts aktualisiert") wird
entsprechend präzisiert: Ein Bau-Schritt aktualisiert künftig „Aktueller Stand" und
„Nächste Schritte" (Issue ggf. aus der Liste entfernen) — **kein neuer Absatz je
Änderung**. → CLAUDE.md „Definition of Done je Bau-Schritt" Punkt 2; Nachtrag in
ADR-0027 verankert.

## Konsequenzen

**Positiv:**
- ROADMAP bleibt dauerhaft kurz und aktuell; Drift gegenüber GitHub Issues ist
  strukturell ausgeschlossen, weil die ROADMAP schlicht keine Issue-Liste mehr führt.
- Neue Sessions erfassen den Stand in unter einer Minute Lesezeit.
- Klare Verantwortlichkeit je Frage (Tabelle oben) verhindert künftige Duplikation.

**Negativ / Aufwand:**
- Die kompakte Historie-Tabelle (Abschnitt 3) ist weniger detailliert als die bisherigen
  Absätze — Details dazu müssen bei Bedarf aus CHANGELOG/ADRs/Git-Historie
  rekonstruiert werden, nicht mehr aus einem einzigen Fließtext.
- „Nächste Schritte" muss bei jedem Schritt-Abschluss aktiv gepflegt werden (Issue
  entfernen), sonst veraltet auch die neue, kurze Liste.
