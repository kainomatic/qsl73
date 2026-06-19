# ADR-0049: Git-Branch-Operationen sind ausschließlich Claude-Code-Aufgabe

**Status:** Accepted

## Kontext

Beim Rück-Merge von Hotfix v0.2.2 nach `dev` versuchte DF1DS den Merge manuell; dabei
traten CHANGELOG-, ADR-Index- und Versions-Konflikte auf, die er nicht sicher lösen
konnte. Der Versuch wurde per `git merge --abort` zurückgenommen. Die Erfahrung zeigt:
Merge-Konflikte erfordern genaue Kenntnis des Auflösungsziels (welche Version gewinnt,
welche ADR-Einträge beide Seiten behalten sollen, wie CHANGELOG-Blöcke zusammengeführt
werden). Das ist Maintainer-Wissen, das bei Claude Code liegt, nicht beim Vermittler.

## Entscheidung

**Alle Git-Branch-Operationen sind ausschließlich Aufgabe von Claude Code:**

- Merges (Feature → dev, Hotfix → dev, Hotfix → main)
- Rück-Merges (Hotfix → dev nach Release)
- Konfliktauflösung
- Tagging (im Rahmen von Release-Aufträgen)
- Branch-Pflege (Löschen lokal und remote nach abgeschlossenem Zyklus)

**DF1DS (Vermittler/Tester) führt keine Merges oder Konfliktauflösungen von Hand aus.**
Wenn ein Schritt einen Merge mit möglichen Konflikten erfordert, schneidet Desktop einen
CC-Auftrag — kein manuelles Mergen durch DF1DS.

**Ausnahme Stable-Release-Entscheidung:** Die *Entscheidung*, ein Stable-Release
auszulösen, bleibt DF1DS (ADR-0046 §5). Die technische Durchführung des Release-Merges
(dev→main, Tag setzen, pushen) wird im CC-Release-Auftrag von Claude Code erledigt.

Diese Regel ist in CLAUDE.md im Abschnitt „Git-Branch-Operationen — Zuständigkeit"
verankert.

## Konsequenzen

**Positiv:**
- Konflikte werden immer mit vollem Kontextwissen aufgelöst — kein Informationsverlust.
- DF1DS muss Git-Merge-Mechanik nicht verstehen; seine Rolle beschränkt sich auf
  Entscheidungen (Release auslösen?) und Tests (Realtest, Installer-Test).
- Konsistenter Prozess: Desktop spezifiziert Merge-Ziel, CC führt aus — gleiche
  Schleife wie bei jedem anderen Bau-Schritt.

**Negativ / Risiko:**
- Jeder Merge erfordert einen CC-Auftrag; kein „schnelles manuelles Eingreifen".
  Akzeptabel, da Merges im QSL73-Rhythmus selten und planbar sind.
