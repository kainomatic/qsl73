# ADR-0050: Datenschutz — keine echten fremden Rufzeichen im Repo; fiktive Calls; geplante Historie-Bereinigung

**Status:** Accepted

## Kontext

Beim Aufbau von Test-Fixtures und Beispiel-Dokumentation wurden echte Amateurfunk-Rufzeichen
(DH3KR, DK8NE, DG5MLA, OE6DRG, G7JVJ u. a.) aus realen Test-QSL-Karten direkt in
versionierte Dateien übernommen — Testdaten, Parameterwerte, Kommentare, ADRs, CHANGELOG.

**Datenschutzproblem:** Rufzeichen sind über die öffentliche BNetzA-Rufzeichenliste
eindeutig natürlichen Personen zuordenbar (Name, Anschrift). Die Veröffentlichung im
öffentlichen GitHub-Repo entspricht nicht dem Zweck des ursprünglichen Funkkontakts
(ITU-Regulierung, DSGVO-Grundsatz der Zweckbindung). Eine Einwilligung der betroffenen
Funkamateure liegt nicht vor.

Betroffen waren getrackter Code und Dokumentation auf beiden öffentlichen Branches (`dev`
und `main`). Nicht betroffen: lokal abgelegte Dateien, die `.gitignore`-gesperrt sind
(echte Log4OM-DBs, QSL-PDFs in `docs/testdateien/`, `config.yaml`, `*.sqlite`).

## Entscheidung

### Fake-Call-Konvention (dauerhaft)

In versionierten Dateien sind ausschließlich folgende Rufzeichen erlaubt:

- **Eigenes Call:** `DF1DS` (Autor, Maintainer)
- **Fiktive Test-Calls:** Calls mit klar fiktivem Suffix `XXX`, `AA`, `BB` o. ä., z. B.:
  `DL0AAA`, `DK8XX`, `DK8XY`, `DG5XXX`, `OE6XXX`, `G7XXX`, `DL1XXX`, `UA4XXX`, …

Diese Konvention ist in `CLAUDE.md` (Abschnitt „Sicherheits- und Datenschutz-Leitplanken")
verankert und gilt für alle zukünftigen Commits.

### Bereinigung des aktuellen Standes (durchgeführt)

- Alle echten fremden Rufzeichen in getrackten Dateien wurden durch fiktive Calls ersetzt.
- Mapping: DH3KR→DL0AAA, DK8NE→DK8XX, DK8NF→DK8XY, DG5MLA→DG5XXX, OE6DRG→OE6XXX,
  G7JVJ→G7XXX, TM2CIN→TM2XXX, WB1CLT→WB1XXX, DN9MF→DN9XX, DL1EJD→DL1XXX,
  UA4WHX→UA4XXX, DO6KBO→DO6XXX.
- Hashes nach Bereinigung: `dev` = 3b1964a, `main` = 683b8ff.

### Git-Historie-Bereinigung (geplant, separater Schritt)

Die alten Commits auf beiden Branches enthalten die echten Calls weiterhin in der
**Git-Historie**. Bereinigung per `git filter-repo` (oder BFG Repo Cleaner) ist
ausdrücklich geplant, wurde aber bewusst als separater, dediziert freigegebener Schritt
aufgespart, weil:

- History-Rewrite ändert alle Commit-Hashes (Breaking Change für alle Klones/Forks).
- Force-Push auf `main` und `dev` erforderlich.
- Alle lokalen Klone (Entwickler-Rechner, CI-Cache) müssen danach neu geklont oder
  per `git fetch --all && git reset` angeglichen werden.
- GitHub-Tags müssen neu gesetzt werden.
- Ein Repo-Backup vor dem Rewrite ist Pflicht.

Durchführung nur nach expliziter Freigabe durch DF1DS.

### Installer und generierte Dokumentation (überprüft, sauber)

- `installer/qsl73.iss` und `installer/qsl73-beta.iss`: enthalten ausschließlich `DF1DS`,
  GUIDs, Pfade und URLs — keine fremden Calls.
- `installer/docs/` (generierte HTML-Doku): per `.gitignore` ausgeschlossen; wird beim
  Build aus den Markdown-Quellen generiert → erbt automatisch den bereinigten Stand.

## Konsequenzen

- **Datenschutzkonform:** Keine personenbezogenen Rufzeichen mehr im öffentlichen Repo-Stand.
- **Konvention muss eingehalten werden:** Jeder zukünftige Commit darf nur `DF1DS` oder
  klar fiktive Calls enthalten. Claude Code und Claude Desktop prüfen dies vor Commits.
- **Abhängigkeit Historie-Bereinigung:** Bis zum separaten Rewrite-Schritt stehen alte Calls
  noch in der Historie; öffentlich einsehbar per `git log -p`. Kein zusätzliches Risiko
  über den aktuellen Stand hinaus, aber der Schritt steht aus.
- **Kein Release ausgelöst:** Die Bereinigung betrifft ausschließlich Doku/Tests, nicht den
  ausgelieferten Installer — kein v0.2.4 nötig.

## Verweise

- `CLAUDE.md` → Abschnitt „Sicherheits- und Datenschutz-Leitplanken" (Fake-Call-Konvention)
- `.gitignore` → Ausschluss sensibler Lokaldaten (docs/testdateien/, *.sqlite, config.yaml)
- ADR-0048, ADR-0049 → Hotfix-/Branch-Operationsregeln (Bereinigung lief via
  `hotfix/callsign-cleanup` von main, danach Rück-Merge nach dev)
