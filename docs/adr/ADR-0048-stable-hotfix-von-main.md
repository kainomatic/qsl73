# ADR-0048: Stable-Hotfix über `hotfix/*`-Branch von `main` (bei ungereiftem `dev`-Stand)

**Status:** Accepted

## Kontext

Ein dringender Bugfix soll als PATCH-Stable-Release veröffentlicht werden, während `dev`
bereits Features für die nächste MINOR enthält, die noch nicht als Stable erscheinen sollen
(z. B. laufen sie erst als Beta-Pre-Release). Ein direkter `dev → main`-Merge würde diese
unreifen Features ungewollt in das Stable-Release ziehen.

Auslöser: v0.2.2-Hotfix für den Über-Dialog-Bug. `dev` enthält bereits v0.3.0-Features
(Tooltips, nur als `v0.3.0-beta1` veröffentlicht), die nicht nach Stable sollen.

## Entscheidung

Bei diesem Szenario gilt folgendes Vorgehen:

1. **Hotfix-Branch von `main` abzweigen** (`hotfix/<version>-<kurz>`), nicht von `dev`.
   Claude Code baut und committet; DF1DS löst den Release manuell aus (wie bei jedem
   Stable — ADR-0046 §5).
2. **Nur den Fix umsetzen** — keine Features, keine Änderungen aus `dev`.
3. **CHANGELOG auf dem Hotfix-Branch:** Einen `[X.Y.Z]`-Abschnitt anlegen, der **nur**
   den Fix enthält. Die `[Unreleased]`-Sammlung auf `dev` bleibt davon unberührt.
4. **Als PATCH-Stable releasen:** `hotfix/*` → `main` mergen, Tag `vX.Y.Z` auf `main`
   setzen, pushen → GitHub Actions baut Installer.
5. **Hotfix zurück nach `dev` mergen:** Damit `dev` den Fix enthält und kein Regress
   entsteht. CHANGELOG beim Rück-Merge sauber zusammenführen (kein Inhaltsverlust,
   keine Dopplung). Der `[X.Y.Z]`-Block landet auf `dev`; `[Unreleased]` wächst weiter.

**Versionsregel:** Hotfix ist immer PATCH (reiner Bugfix, kein neues Verhalten).

## Abgrenzung zu ADR-0046

ADR-0046 beschreibt den geraden Beta → Stable-Weg (alle Features auf `dev` → Beta →
CHANGELOG einfrieren → `dev → main`-Merge → Stable-Tag). Der vorliegende ADR ergänzt
diesen Weg um den Sonderfall: dringender Fix, wenn `dev` nicht für Stable bereit ist.
Die Auslöser-Rollen bleiben identisch: DF1DS löst Stable-Releases manuell aus; Claude
Code darf Hotfix-Branch und Fix bauen, aber keinen Tag und kein Release setzen.

## Konsequenzen

**Positiv:**
- Stable bleibt sauber — keine unreifen Features landen ungewollt im Release.
- `dev` erhält den Fix via Rück-Merge; kein Regress in der nächsten MINOR.
- CHANGELOG bleibt konsistent: `[X.Y.Z]` auf beiden Branches, `[Unreleased]` auf `dev`
  wächst ungestört weiter.

**Negativ / Risiko:**
- Rück-Merge von Hotfix nach `dev` kann CHANGELOG-Konflikte erzeugen (wenn `dev` den
  `[Unreleased]`-Block inzwischen erweitert hat). Muss manuell/sorgfältig aufgelöst werden.
- Zwei parallele Branches mit aktivem Stand — kurzer Zeitraum, aber Aufmerksamkeit nötig.
