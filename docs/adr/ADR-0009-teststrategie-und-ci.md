# ADR-0009: Teststrategie & CI

**Status:** Accepted

## Kontext

Ohne automatische Tests ist jeder Bau-Schritt ein manueller Vertrauensvorschuss. Die
Akzeptanzkriterien in KONZEPT.md sind präzise und maschinenprüfbar — sie sollen als
ausführbare Tests vorliegen, nicht nur als Prosa. Schreibzugriffe auf Log4OM erfordern
besondere Vorsicht: kein Test darf eine echte DB verändern.

## Entscheidung

**Ab Schritt 2 (erster Anwendungscode) sind automatische Unit-Tests Pflicht-Bestandteil
jedes Bau-Auftrags.** Ein Schritt gilt erst als fertig, wenn seine Tests grün sind.

**Testframework:** `pytest`. Eingerichtet in Schritt 2 zusammen mit dem ersten Code.

**CI:** GitHub Actions führt die Test-Suite bei jedem Push auf `dev` und `main` aus.
Das Workflow-File wird in Schritt 2 angelegt (`/.github/workflows/ci.yml`).
Ergebnis (grün/rot) ist im Pull-Request und auf der GitHub-Seite sichtbar.

**Schreibtests (Log4OM-DB):** Alle Tests, die Schreiboperationen gegen die DB ausführen,
laufen ausschließlich gegen eine **Wegwerf-Kopie** der Test-DB (`docs/testdateien/`).
Die Fixture erstellt die Kopie in einem temporären Verzeichnis; nach dem Test wird sie
verworfen. Die Originaldatei in `docs/testdateien/` wird nie verändert.
`docs/testdateien/` bleibt `.gitignore`-gesperrt — der CI-Runner hat keinen Zugriff
darauf; DB-Tests im CI werden gegen eine synthetisch erzeugte Minimal-DB ausgeführt.

**Testabdeckung:** Akzeptanzkriterien aus KONZEPT.md werden soweit möglich als
ausführbare Tests abgebildet. Nicht automatisierbar (UI, echte Netzwerkverbindung):
manuell im Review-Schritt abgenommen.

## Konsequenzen

- Jeder Bau-Auftrag muss Tests für den neuen Code mitliefern.
- CI schlägt fehl → kein Merge auf `main`. Kein grüner Build → kein Release.
- Test-DB nie ins Repo; CI nutzt synthetische Minimal-DB für DB-abhängige Tests.
- Testabdeckung entlastet den manuellen Review (Desktop prüft nur, was nicht testbar ist).
